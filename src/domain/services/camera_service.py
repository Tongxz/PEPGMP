"""摄像头领域服务."""

import logging
import os
import tempfile
from typing import Any, Dict, Optional

import yaml

from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.repositories.camera_repository import ICameraRepository

logger = logging.getLogger(__name__)


class CameraService:
    """摄像头领域服务.

    提供摄像头相关的业务逻辑，包括CRUD操作。
    """

    def __init__(
        self,
        camera_repository: ICameraRepository,
        cameras_yaml_path: Optional[str] = None,
    ):
        """初始化摄像头服务.

        Args:
            camera_repository: 摄像头仓储
            cameras_yaml_path: 摄像头YAML配置文件路径（可选）
        """
        self.camera_repository = camera_repository
        self.cameras_yaml_path = cameras_yaml_path

    def _read_yaml_config(self) -> Dict[str, Any]:
        """读取YAML配置文件."""
        if not self.cameras_yaml_path or not os.path.exists(self.cameras_yaml_path):
            return {"cameras": []}
        try:
            with open(self.cameras_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"读取摄像头配置失败: {e}")
            return {"cameras": []}
        if not isinstance(data.get("cameras"), list):
            data["cameras"] = []
        return data

    def _write_yaml_config(self, data: Dict[str, Any]) -> None:
        """写入YAML配置文件（原子写）."""
        if not self.cameras_yaml_path:
            raise ValueError("摄像头YAML配置文件路径未配置")

        os.makedirs(os.path.dirname(self.cameras_yaml_path), exist_ok=True)
        # 原子写
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=os.path.dirname(self.cameras_yaml_path),
        ) as tf:
            yaml.safe_dump(data, tf, allow_unicode=True, sort_keys=False)
            tmp_name = tf.name
        os.replace(tmp_name, self.cameras_yaml_path)

    async def create_camera(self, camera_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建摄像头.

        Args:
            camera_data: 摄像头数据字典

        Returns:
            包含创建结果的字典

        Raises:
            ValueError: 如果摄像头ID已存在或必填字段缺失
        """
        try:
            # 验证必填字段（id不再是必填字段，由数据库自动生成）
            required_fields = ["name", "source"]
            for field in required_fields:
                if field not in camera_data:
                    raise ValueError(f"缺少必填字段: {field}")

            # ID由数据库自动生成UUID，如果提供了id则使用（用于更新场景）
            camera_id = camera_data.get("id")

            # 如果提供了ID，检查是否已存在（用于更新场景）
            if camera_id:
                existing_camera = await self.camera_repository.find_by_id(camera_id)
                if existing_camera:
                    raise ValueError(f"摄像头ID已存在: {camera_id}")

            # 创建Camera实体（source存储在metadata中）
            # id为None时，数据库会自动生成UUID
            # 处理 status 字段：优先使用 status，如果没有则使用 active 标志
            status_value = camera_data.get("status")
            if status_value:
                try:
                    camera_status = CameraStatus(status_value)
                except ValueError:
                    # 如果 status 值无效，回退到 active 标志
                    camera_status = (
                        CameraStatus.ACTIVE
                        if camera_data.get("active", True)
                        else CameraStatus.INACTIVE
                    )
            else:
                # 如果没有提供 status，使用 active 标志（兼容旧代码）
                camera_status = (
                    CameraStatus.ACTIVE
                    if camera_data.get("active", True)
                    else CameraStatus.INACTIVE
                )

            # 处理 camera_type 字段
            camera_type_value = camera_data.get("camera_type", "fixed")
            try:
                camera_type = CameraType(camera_type_value)
            except ValueError:
                camera_type = CameraType.FIXED  # 默认类型

            camera = Camera(
                id=camera_id if camera_id else "",  # 空字符串表示自动生成
                name=camera_data["name"],
                status=camera_status,
                camera_type=camera_type,
                location=camera_data.get("location") or "unknown",
                resolution=tuple(camera_data["resolution"])
                if camera_data.get("resolution")
                else (1920, 1080),
                fps=camera_data.get("fps", 25),
                region_id=camera_data.get("region_id"),
            )
            # 将source和其他字段存储到metadata中
            if "source" in camera_data:
                camera.metadata["source"] = camera_data["source"]
            # 复制其他字段到metadata
            for key in [
                "regions_file",
                "profile",
                "device",
                "imgsz",
                "auto_tune",
                "auto_start",
                "env",
                "log_interval",  # 检测频率
                "stream_interval",  # 视频流推送间隔（已废弃，与log_interval保持一致）
                "frame_by_frame",  # 逐帧模式（已废弃）
            ]:
                if key in camera_data:
                    camera.metadata[key] = camera_data[key]

            # 保存到数据库（主要数据源），获取自动生成的ID
            generated_id = await self.camera_repository.save(camera)

            # 更新camera实体的ID（如果之前为空）
            if not camera_id:
                camera.id = generated_id

            # 同步运行时配置到Redis（如果配置了log_interval等）
            try:
                from src.infrastructure.notifications.redis_config_sync import (
                    sync_camera_config_to_redis,
                )

                # 提取需要同步的配置项（从camera_data中）
                changed_keys = [
                    key
                    for key in ["log_interval", "stream_interval"]
                    if key in camera_data
                ]
                if changed_keys:
                    sync_camera_config_to_redis(
                        camera_id=generated_id,  # 使用生成的ID
                        camera_config=camera.to_dict(),
                        changed_keys=changed_keys,
                    )
            except Exception as e:
                logger.warning(
                    f"同步相机配置到Redis失败（不影响创建）: camera_id={generated_id}, error={e}"
                )

            # 注意: YAML写入已移除，数据库是单一数据源
            # 如需备份，使用导出工具: scripts/export_cameras_to_yaml.py

            logger.info(f"摄像头创建成功: camera_id={generated_id}, name={camera.name}")
            return {"ok": True, "camera": camera.to_dict()}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"创建摄像头失败: {e}")
            raise

    async def update_camera(
        self, camera_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新摄像头.

        Args:
            camera_id: 摄像头ID
            updates: 要更新的字段字典

        Returns:
            包含更新结果的字典

        Raises:
            ValueError: 如果摄像头不存在
        """
        try:
            # 查找摄像头
            camera = await self.camera_repository.find_by_id(camera_id)
            if not camera:
                raise ValueError(f"摄像头不存在: {camera_id}")

            # 更新字段
            if "name" in updates:
                camera.name = updates["name"]
            if "source" in updates:
                camera.metadata["source"] = updates["source"]
            if "location" in updates:
                camera.location = updates["location"] or "unknown"
            if "status" in updates:
                # 处理 status 字段
                status_value = updates["status"]
                try:
                    camera.status = CameraStatus(status_value)
                except ValueError:
                    logger.warning(f"无效的status值: {status_value}，保持原值")
            elif "active" in updates:
                # 兼容旧代码：使用 active 标志
                camera.status = (
                    CameraStatus.ACTIVE if updates["active"] else CameraStatus.INACTIVE
                )
            if "camera_type" in updates:
                # 处理 camera_type 字段
                camera_type_value = updates["camera_type"]
                try:
                    camera.camera_type = CameraType(camera_type_value)
                except ValueError:
                    logger.warning(f"无效的camera_type值: {camera_type_value}，保持原值")
            if "resolution" in updates:
                camera.resolution = (
                    tuple(updates["resolution"])
                    if isinstance(updates["resolution"], list)
                    else updates["resolution"]
                )
            if "fps" in updates:
                camera.fps = updates["fps"]
            if "region_id" in updates:
                camera.region_id = updates["region_id"]
            # 更新metadata中的其他字段（包括log_interval等）
            metadata_fields = [
                "regions_file",
                "profile",
                "device",
                "imgsz",
                "auto_tune",
                "auto_start",
                "env",
                "log_interval",  # 检测频率
                "stream_interval",  # 视频流推送间隔（已废弃，与log_interval保持一致）
                "frame_by_frame",  # 逐帧模式（已废弃）
            ]
            for key in metadata_fields:
                if key in updates:
                    camera.metadata[key] = updates[key]

            # 更新到数据库（主要数据源）
            await self.camera_repository.save(camera)

            # 同步运行时配置到Redis（如果更新了运行时配置项）
            # 提取变更的运行时配置项
            runtime_config_keys = ["log_interval", "stream_interval"]
            changed_runtime_keys = [
                key for key in runtime_config_keys if key in updates
            ]

            if changed_runtime_keys:
                try:
                    from src.infrastructure.notifications.redis_config_sync import (
                        sync_camera_config_to_redis,
                    )

                    sync_camera_config_to_redis(
                        camera_id=camera_id,
                        camera_config=camera.to_dict(),
                        changed_keys=changed_runtime_keys,
                    )
                except Exception as e:
                    logger.warning(
                        f"同步相机配置到Redis失败（不影响更新）: camera_id={camera_id}, error={e}"
                    )

            # 注意: YAML写入已移除，数据库是单一数据源
            # 如需备份，使用导出工具: scripts/export_cameras_to_yaml.py

            logger.info(f"摄像头更新成功: {camera_id}, updates={updates}")
            return {"status": "success", "camera": camera.to_dict()}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新摄像头失败: {e}")
            raise

    async def delete_camera(self, camera_id: str) -> Dict[str, Any]:
        """删除摄像头（软删除）.

        Args:
            camera_id: 摄像头ID

        Returns:
            包含删除结果的字典

        Raises:
            ValueError: 如果摄像头不存在
        """
        try:
            # 查找摄像头
            camera = await self.camera_repository.find_by_id(camera_id)
            if not camera:
                raise ValueError(f"摄像头不存在: {camera_id}")

            # 从数据库删除（主要数据源）
            await self.camera_repository.delete_by_id(camera_id)

            # 从Redis删除运行时配置（如果存在）
            try:
                from src.infrastructure.notifications.redis_config_sync import (
                    delete_camera_config_from_redis,
                )

                delete_camera_config_from_redis(camera_id=camera_id)
            except Exception as e:
                logger.warning(
                    f"从Redis删除相机配置失败（不影响删除）: camera_id={camera_id}, error={e}"
                )

            # 注意: YAML写入已移除，数据库是单一数据源
            # 如需备份，使用导出工具: scripts/export_cameras_to_yaml.py

            logger.info(f"摄像头删除成功: camera_id={camera_id}")
            return {"status": "success"}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"删除摄像头失败: {e}")
            raise

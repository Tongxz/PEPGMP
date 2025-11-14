"""检测参数配置领域服务."""

import logging
from typing import Any, Dict, Optional

from src.domain.repositories.detection_config_repository import (
    IDetectionConfigRepository,
)

logger = logging.getLogger(__name__)


class DetectionConfigService:
    """检测参数配置领域服务.

    提供检测参数配置相关的业务逻辑，包括CRUD操作、配置合并等。
    """

    def __init__(self, config_repository: IDetectionConfigRepository):
        """初始化检测参数配置服务.

        Args:
            config_repository: 检测参数配置仓储
        """
        self.config_repository = config_repository

    async def get_config(
        self, camera_id: Optional[str] = None, config_type: str = "human_detection"
    ) -> Dict[str, Any]:
        """获取检测参数配置.

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型（human_detection, hairnet_detection等）

        Returns:
            Dict[str, Any]: 配置字典（键值对）
        """
        try:
            config = await self.config_repository.find_by_camera_and_type(
                camera_id, config_type
            )
            logger.debug(
                f"获取配置: camera_id={camera_id}, config_type={config_type}, "
                f"找到 {len(config)} 个配置项"
            )
            return config
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            raise

    async def get_all_configs(
        self, camera_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """获取所有检测参数配置.

        Args:
            camera_id: 摄像头ID，None表示全局默认值

        Returns:
            Dict[str, Dict[str, Any]]: 配置字典，键为config_type，值为配置字典
        """
        try:
            # 定义配置类型列表
            config_types = [
                "human_detection",
                "hairnet_detection",
                "behavior_recognition",
                "pose_detection",
                "detection_rules",
                "system",
            ]

            all_configs = {}
            for config_type in config_types:
                config = await self.config_repository.find_by_camera_and_type(
                    camera_id, config_type
                )
                if config:
                    all_configs[config_type] = config

            logger.debug(
                f"获取所有配置: camera_id={camera_id}, " f"找到 {len(all_configs)} 个配置类型"
            )
            return all_configs
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            raise

    async def save_config(
        self,
        camera_id: Optional[str],
        config_type: str,
        config_key: str,
        config_value: Any,
        description: Optional[str] = None,
    ) -> int:
        """保存检测参数配置.

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型
            config_key: 配置项名称
            config_value: 配置值
            description: 配置项描述

        Returns:
            int: 保存的配置项ID
        """
        try:
            config_id = await self.config_repository.save(
                camera_id, config_type, config_key, config_value, description
            )
            logger.info(
                f"保存配置: camera_id={camera_id}, config_type={config_type}, "
                f"config_key={config_key}, config_value={config_value}"
            )
            return config_id
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise

    async def save_configs(
        self,
        camera_id: Optional[str],
        config_type: str,
        configs: Dict[str, Any],
        description: Optional[str] = None,
    ) -> int:
        """批量保存检测参数配置.

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型
            configs: 配置字典（键值对）
            description: 配置项描述（可选）

        Returns:
            int: 保存的配置项数量
        """
        try:
            saved_count = 0
            for config_key, config_value in configs.items():
                await self.config_repository.save(
                    camera_id, config_type, config_key, config_value, description
                )
                saved_count += 1

            logger.info(
                f"批量保存配置: camera_id={camera_id}, config_type={config_type}, "
                f"保存 {saved_count} 个配置项"
            )
            return saved_count
        except Exception as e:
            logger.error(f"批量保存配置失败: {e}")
            raise

    async def delete_config(
        self, camera_id: Optional[str], config_type: str, config_key: str
    ) -> bool:
        """删除检测参数配置.

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型
            config_key: 配置项名称

        Returns:
            bool: 删除是否成功
        """
        try:
            deleted = await self.config_repository.delete(
                camera_id, config_type, config_key
            )
            logger.info(
                f"删除配置: camera_id={camera_id}, config_type={config_type}, "
                f"config_key={config_key}, 成功={deleted}"
            )
            return deleted
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            raise

    async def merge_configs(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """合并配置字典.

        Args:
            base_config: 基础配置字典
            override_config: 覆盖配置字典

        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        merged = base_config.copy()
        merged.update(override_config)
        return merged

    async def get_merged_config(
        self, camera_id: Optional[str], config_type: str
    ) -> Dict[str, Any]:
        """获取合并后的配置（全局配置 + 相机特定配置）.

        Args:
            camera_id: 摄像头ID，None表示只返回全局配置
            config_type: 配置类型

        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        try:
            # 获取全局配置
            global_config = await self.config_repository.find_by_camera_and_type(
                None, config_type
            )

            # 如果指定了camera_id，获取相机特定配置并合并
            if camera_id:
                camera_config = await self.config_repository.find_by_camera_and_type(
                    camera_id, config_type
                )
                # 相机特定配置覆盖全局配置
                merged_config = await self.merge_configs(global_config, camera_config)
            else:
                merged_config = global_config

            logger.debug(
                f"获取合并配置: camera_id={camera_id}, config_type={config_type}, "
                f"找到 {len(merged_config)} 个配置项"
            )
            return merged_config
        except Exception as e:
            logger.error(f"获取合并配置失败: {e}")
            raise

"""区域领域服务."""

import logging
from typing import Any, Dict, List, Optional

from src.core.region import Region, RegionType
from src.infrastructure.repositories.postgresql_region_repository import (
    PostgreSQLRegionRepository,
)

logger = logging.getLogger(__name__)


class RegionDomainService:
    """区域领域服务.

    提供区域相关的业务逻辑，包括CRUD操作。
    """

    def __init__(self, region_repository: PostgreSQLRegionRepository):
        """初始化区域服务.

        Args:
            region_repository: 区域仓储
        """
        self.region_repository = region_repository

    async def create_region(
        self, region_data: Dict[str, Any], camera_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建区域.

        Args:
            region_data: 区域数据字典
            camera_id: 关联的相机ID（可选）

        Returns:
            包含创建结果的字典

        Raises:
            ValueError: 如果区域ID已存在或必填字段缺失
        """
        try:
            # 验证必填字段
            required_fields = ["region_id", "region_type", "polygon", "name"]
            for field in required_fields:
                if field not in region_data:
                    raise ValueError(f"缺少必填字段: {field}")

            region_id = region_data["region_id"]

            # 检查区域ID是否已存在
            existing_region = await self.region_repository.find_by_id(region_id)
            if existing_region:
                raise ValueError(f"区域ID已存在: {region_id}")

            # 转换类型
            try:
                region_type = RegionType(region_data["region_type"])
            except ValueError:
                raise ValueError(f"无效的区域类型: {region_data['region_type']}")

            # 转换polygon
            polygon_data = region_data["polygon"]
            polygon = []
            for point in polygon_data:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    polygon.append((float(point[0]), float(point[1])))
                elif isinstance(point, dict) and "x" in point and "y" in point:
                    polygon.append((float(point["x"]), float(point["y"])))
                else:
                    raise ValueError(f"无效的多边形点: {point}")

            if not polygon:
                raise ValueError("多边形必须包含至少一个点")

            # 创建Region实体
            region = Region(
                region_id=region_id,
                region_type=region_type,
                polygon=polygon,
                name=region_data["name"],
            )
            region.is_active = region_data.get("is_active", True)

            # 复制rules
            if "rules" in region_data:
                region.rules.update(region_data["rules"])

            # 保存到数据库
            await self.region_repository.save(region, camera_id)

            logger.info(f"区域创建成功: {region_id}")
            return {"status": "success", "region_id": region_id}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"创建区域失败: {e}")
            raise

    async def update_region(
        self, region_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新区域.

        Args:
            region_id: 区域ID
            updates: 要更新的字段字典

        Returns:
            包含更新结果的字典

        Raises:
            ValueError: 如果区域不存在
        """
        try:
            # 查找区域
            region = await self.region_repository.find_by_id(region_id)
            if not region:
                raise ValueError(f"区域不存在: {region_id}")

            # 更新字段
            if "name" in updates:
                region.name = updates["name"]
            if "region_type" in updates:
                try:
                    region.region_type = RegionType(updates["region_type"])
                except ValueError:
                    raise ValueError(f"无效的区域类型: {updates['region_type']}")
            if "polygon" in updates:
                polygon_data = updates["polygon"]
                polygon = []
                for point in polygon_data:
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        polygon.append((float(point[0]), float(point[1])))
                    elif isinstance(point, dict) and "x" in point and "y" in point:
                        polygon.append((float(point["x"]), float(point["y"])))
                if polygon:
                    region.polygon = polygon
            if "is_active" in updates:
                region.is_active = updates["is_active"]
            if "rules" in updates:
                region.rules.update(updates["rules"])

            # 更新到数据库
            camera_id = updates.get("camera_id")
            await self.region_repository.save(region, camera_id)

            logger.info(f"区域更新成功: {region_id}")
            return {"status": "success", "region": self._region_to_dict(region)}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新区域失败: {e}")
            raise

    async def delete_region(self, region_id: str) -> Dict[str, Any]:
        """删除区域.

        Args:
            region_id: 区域ID

        Returns:
            包含删除结果的字典

        Raises:
            ValueError: 如果区域不存在
        """
        try:
            # 查找区域
            region = await self.region_repository.find_by_id(region_id)
            if not region:
                raise ValueError(f"区域不存在: {region_id}")

            # 从数据库删除
            await self.region_repository.delete_by_id(region_id)

            logger.info(f"区域删除成功: {region_id}")
            return {"status": "success"}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"删除区域失败: {e}")
            raise

    async def get_all_regions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有区域.

        Args:
            active_only: 是否只返回活跃区域

        Returns:
            区域信息列表
        """
        try:
            regions = await self.region_repository.find_all(active_only=active_only)
            return [self._region_to_dict(region) for region in regions]
        except Exception as e:
            logger.error(f"获取所有区域失败: {e}")
            raise

    async def get_region_by_id(self, region_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取区域.

        Args:
            region_id: 区域ID

        Returns:
            区域信息字典，如果不存在则返回None
        """
        try:
            region = await self.region_repository.find_by_id(region_id)
            if region:
                return self._region_to_dict(region)
            return None
        except Exception as e:
            logger.error(f"获取区域失败: {e}")
            raise

    async def get_regions_by_camera_id(self, camera_id: str) -> List[Dict[str, Any]]:
        """根据相机ID获取区域.

        Args:
            camera_id: 相机ID

        Returns:
            区域信息列表
        """
        try:
            regions = await self.region_repository.find_by_camera_id(camera_id)
            return [self._region_to_dict(region) for region in regions]
        except Exception as e:
            logger.error(f"根据相机ID获取区域失败: {e}")
            raise

    async def save_meta(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """保存区域meta配置.

        Args:
            meta: meta配置字典

        Returns:
            包含保存结果的字典
        """
        try:
            await self.region_repository.save_meta(meta)
            logger.info("区域meta配置已保存")
            return {"status": "success", "meta": meta}
        except Exception as e:
            logger.error(f"保存区域meta配置失败: {e}")
            raise

    async def get_meta(self) -> Optional[Dict[str, Any]]:
        """获取区域meta配置.

        Returns:
            meta配置字典，如果不存在则返回None
        """
        try:
            return await self.region_repository.get_meta()
        except Exception as e:
            logger.error(f"获取区域meta配置失败: {e}")
            return None

    async def import_from_file(
        self, file_path: str, camera_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """从配置文件导入区域到数据库.

        Args:
            file_path: 配置文件路径
            camera_id: 关联的相机ID（可选）

        Returns:
            包含导入结果的字典
        """
        try:
            import json
            import os

            if not os.path.exists(file_path):
                raise ValueError(f"配置文件不存在: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            regions_data = config.get("regions", [])
            if not regions_data:
                logger.warning(f"配置文件中没有区域数据: {file_path}")
                return {"status": "success", "imported": 0, "skipped": 0, "errors": 0}

            imported = 0
            skipped = 0
            errors = 0

            for r in regions_data:
                try:
                    # 转换数据格式
                    region_data = {
                        "region_id": r.get("region_id") or r.get("id"),
                        "region_type": r.get("region_type") or r.get("type", "custom"),
                        "name": r.get("name", ""),
                        "polygon": r.get("polygon") or r.get("points", []),
                        "is_active": r.get("is_active", True),
                        "rules": r.get("rules", {}),
                    }

                    # 检查是否已存在
                    existing = await self.region_repository.find_by_id(
                        region_data["region_id"]
                    )
                    if existing:
                        logger.debug(f"区域已存在，跳过: {region_data['region_id']}")
                        skipped += 1
                        continue

                    # 创建区域（会自动保存到数据库）
                    await self.create_region(region_data, camera_id)
                    imported += 1
                    logger.debug(f"已导入区域: {region_data['region_id']}")
                except ValueError as e:
                    # 业务逻辑错误（如ID已存在），跳过
                    logger.warning(f"跳过区域（业务错误）: {e}")
                    skipped += 1
                except Exception as e:
                    logger.error(f"导入区域失败: {e}")
                    errors += 1

            logger.info(f"从配置文件导入区域完成: 导入={imported}, 跳过={skipped}, 错误={errors}")
            return {
                "status": "success",
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "total": len(regions_data),
            }
        except Exception as e:
            logger.error(f"从配置文件导入区域失败: {e}")
            raise

    def _region_to_dict(self, region: Region) -> Dict[str, Any]:
        """将Region实体转换为字典."""
        return {
            "region_id": region.region_id,
            "region_type": region.region_type.value,
            "name": region.name,
            "polygon": [list(p) for p in region.polygon],
            "is_active": region.is_active,
            "rules": region.rules,
        }

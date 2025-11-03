"""PostgreSQL区域仓储实现."""

import json
import logging
from typing import List, Optional

from asyncpg import Pool

from src.core.region import Region, RegionType
from src.interfaces.repositories.detection_repository_interface import RepositoryError

logger = logging.getLogger(__name__)


class PostgreSQLRegionRepository:
    """PostgreSQL区域仓储实现."""

    def __init__(self, pool: Pool):
        """初始化PostgreSQL区域仓储.

        Args:
            pool: PostgreSQL连接池
        """
        self.pool = pool

    async def _get_connection(self):
        """获取数据库连接."""
        return await self.pool.acquire()

    async def _ensure_table_exists(self):
        """确保regions表存在."""
        try:
            conn = await self._get_connection()
            try:
                # 检查表是否存在
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'regions'
                    )
                    """
                )

                if not table_exists:
                    logger.warning("regions表不存在，创建表...")
                    await conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS regions (
                            region_id VARCHAR(100) PRIMARY KEY,
                            region_type VARCHAR(50) NOT NULL,
                            name VARCHAR(100) NOT NULL,
                            polygon JSONB NOT NULL,
                            is_active BOOLEAN DEFAULT true,
                            rules JSONB DEFAULT '{}'::jsonb,
                            camera_id VARCHAR(100),
                            metadata JSONB DEFAULT '{}'::jsonb,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    # 创建索引
                    await conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_regions_camera_id
                        ON regions(camera_id) WHERE camera_id IS NOT NULL;
                        CREATE INDEX IF NOT EXISTS idx_regions_type
                        ON regions(region_type);
                        CREATE INDEX IF NOT EXISTS idx_regions_active
                        ON regions(is_active);
                        """
                    )
                    logger.info("regions表已创建")

                logger.debug("regions表已确保存在")
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"确保regions表存在失败: {e}")
            raise RepositoryError(f"确保regions表存在失败: {e}")

    def _row_to_region(self, row) -> Region:
        """将数据库行转换为Region实体."""
        try:
            # 解析polygon
            polygon = []
            if row["polygon"]:
                if isinstance(row["polygon"], list):
                    polygon = [
                        tuple(point) if isinstance(point, list) else point
                        for point in row["polygon"]
                    ]
                elif isinstance(row["polygon"], str):
                    polygon_data = json.loads(row["polygon"])
                    polygon = [
                        tuple(p) if isinstance(p, list) else p for p in polygon_data
                    ]

            # 解析rules
            rules = row["rules"] or {}
            if isinstance(rules, str):
                rules = json.loads(rules)

            # 解析metadata
            metadata = row["metadata"] or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            region = Region(
                region_id=row["region_id"],
                region_type=RegionType(row["region_type"]),
                polygon=polygon,
                name=row["name"],
            )
            region.is_active = row["is_active"]
            region.rules.update(rules)

            # 将camera_id存储在metadata中
            if row["camera_id"]:
                metadata["camera_id"] = row["camera_id"]

            return region
        except Exception as e:
            logger.error(f"转换数据库行到Region实体失败: {e}, row={row}")
            raise RepositoryError(f"转换数据库行到Region实体失败: {e}")

    async def save(self, region: Region, camera_id: Optional[str] = None) -> str:
        """保存区域.

        Args:
            region: 区域实体
            camera_id: 关联的相机ID（可选）

        Returns:
            str: 保存的区域ID
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                polygon_json = json.dumps([list(p) for p in region.polygon])
                rules_json = json.dumps(region.rules)

                await conn.execute(
                    """
                    INSERT INTO regions
                    (region_id, region_type, name, polygon, is_active, rules, camera_id, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (region_id) DO UPDATE SET
                        region_type = EXCLUDED.region_type,
                        name = EXCLUDED.name,
                        polygon = EXCLUDED.polygon,
                        is_active = EXCLUDED.is_active,
                        rules = EXCLUDED.rules,
                        camera_id = EXCLUDED.camera_id,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    region.region_id,
                    region.region_type.value,
                    region.name,
                    polygon_json,
                    region.is_active,
                    rules_json,
                    camera_id,
                    json.dumps({}),
                )

                logger.debug(f"区域已保存到数据库: {region.region_id}")
                return region.region_id
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存区域失败: {e}")
            raise RepositoryError(f"保存区域失败: {e}")

    async def find_by_id(self, region_id: str) -> Optional[Region]:
        """根据ID查找区域.

        Args:
            region_id: 区域ID

        Returns:
            Optional[Region]: 区域实体，如果不存在则返回None
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                row = await conn.fetchrow(
                    """
                    SELECT region_id, region_type, name, polygon, is_active, rules, camera_id, metadata, created_at, updated_at
                    FROM regions
                    WHERE region_id = $1
                    """,
                    region_id,
                )

                if not row:
                    return None

                return self._row_to_region(row)
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询区域失败: {e}")
            raise RepositoryError(f"查询区域失败: {e}")

    async def find_by_camera_id(self, camera_id: str) -> List[Region]:
        """根据相机ID查找区域.

        Args:
            camera_id: 相机ID

        Returns:
            List[Region]: 区域列表
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT region_id, region_type, name, polygon, is_active, rules, camera_id, metadata, created_at, updated_at
                    FROM regions
                    WHERE camera_id = $1
                    ORDER BY name
                    """,
                    camera_id,
                )

                regions = []
                for row in rows:
                    regions.append(self._row_to_region(row))

                return regions
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"根据相机ID查询区域失败: {e}")
            raise RepositoryError(f"根据相机ID查询区域失败: {e}")

    async def find_all(self, active_only: bool = False) -> List[Region]:
        """查找所有区域.

        Args:
            active_only: 是否只返回活跃区域

        Returns:
            List[Region]: 区域列表
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                if active_only:
                    rows = await conn.fetch(
                        """
                        SELECT region_id, region_type, name, polygon, is_active, rules, camera_id, metadata, created_at, updated_at
                        FROM regions
                        WHERE is_active = true
                        ORDER BY name
                        """
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT region_id, region_type, name, polygon, is_active, rules, camera_id, metadata, created_at, updated_at
                        FROM regions
                        ORDER BY name
                        """
                    )

                regions = []
                for row in rows:
                    regions.append(self._row_to_region(row))

                return regions
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询所有区域失败: {e}")
            raise RepositoryError(f"查询所有区域失败: {e}")

    async def count(self) -> int:
        """统计区域数量.

        Returns:
            int: 区域数量
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                count = await conn.fetchval("SELECT COUNT(*) FROM regions")
                return count or 0
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"统计区域数量失败: {e}")
            raise RepositoryError(f"统计区域数量失败: {e}")

    async def delete_by_id(self, region_id: str) -> bool:
        """根据ID删除区域.

        Args:
            region_id: 区域ID

        Returns:
            bool: 删除是否成功
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                result = await conn.execute(
                    "DELETE FROM regions WHERE region_id = $1",
                    region_id,
                )
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"区域已从数据库删除: {region_id}")
                return deleted
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"删除区域失败: {e}")
            raise RepositoryError(f"删除区域失败: {e}")

    async def exists(self, region_id: str) -> bool:
        """检查区域是否存在.

        Args:
            region_id: 区域ID

        Returns:
            bool: 是否存在
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM regions WHERE region_id = $1)",
                    region_id,
                )
                return exists or False
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"检查区域是否存在失败: {e}")
            raise RepositoryError(f"检查区域是否存在失败: {e}")

    async def save_meta(self, meta: dict) -> None:
        """保存区域meta配置.

        Args:
            meta: meta配置字典
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                await conn.execute(
                    """
                    INSERT INTO system_configs (config_key, config_value, description)
                    VALUES ('regions_meta', $1, '区域meta配置')
                    ON CONFLICT (config_key) DO UPDATE SET
                        config_value = EXCLUDED.config_value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    json.dumps(meta),
                )
                logger.debug("区域meta配置已保存")
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存区域meta配置失败: {e}")
            raise RepositoryError(f"保存区域meta配置失败: {e}")

    async def get_meta(self) -> Optional[dict]:
        """获取区域meta配置.

        Returns:
            Optional[dict]: meta配置字典，如果不存在则返回None
        """
        try:
            conn = await self._get_connection()
            try:
                row = await conn.fetchrow(
                    """
                    SELECT config_value FROM system_configs
                    WHERE config_key = 'regions_meta'
                    """
                )
                if row:
                    meta = row["config_value"]
                    if isinstance(meta, str):
                        return json.loads(meta)
                    return meta
                return None
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"获取区域meta配置失败: {e}")
            return None

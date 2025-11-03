"""PostgreSQL摄像头仓储实现."""

import json
import logging
from typing import List, Optional

from asyncpg import Pool

from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.repositories.camera_repository import ICameraRepository
from src.domain.value_objects.timestamp import Timestamp
from src.interfaces.repositories.detection_repository_interface import RepositoryError

logger = logging.getLogger(__name__)


class PostgreSQLCameraRepository(ICameraRepository):
    """PostgreSQL摄像头仓储实现."""

    def __init__(self, pool: Pool):
        """初始化PostgreSQL摄像头仓储.

        Args:
            pool: PostgreSQL连接池
        """
        self.pool = pool

    async def _get_connection(self):
        """获取数据库连接."""
        return await self.pool.acquire()

    async def _ensure_table_exists(self):
        """确保cameras表存在."""
        try:
            conn = await self._get_connection()
            try:
                # 检查表是否存在
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'cameras'
                    )
                    """
                )

                if not table_exists:
                    logger.warning("cameras表不存在，创建表...")
                    await conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS cameras (
                            id VARCHAR(100) PRIMARY KEY,
                            name VARCHAR(100) NOT NULL,
                            location VARCHAR(200),
                            status VARCHAR(20) DEFAULT 'inactive',
                            camera_type VARCHAR(50) DEFAULT 'fixed',
                            resolution JSONB,
                            fps INTEGER,
                            region_id VARCHAR(100),
                            metadata JSONB DEFAULT '{}'::jsonb,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    logger.info("cameras表已创建")

                logger.debug("cameras表已确保存在")
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"确保cameras表存在失败: {e}")
            raise RepositoryError(f"确保cameras表存在失败: {e}")

    def _row_to_camera(self, row) -> Camera:
        """将数据库行转换为Camera实体."""
        try:
            resolution = None
            if row["resolution"]:
                if isinstance(row["resolution"], list):
                    resolution = tuple(row["resolution"])
                elif isinstance(row["resolution"], str):
                    resolution_data = json.loads(row["resolution"])
                    resolution = (
                        tuple(resolution_data)
                        if isinstance(resolution_data, list)
                        else None
                    )

            metadata = row["metadata"] or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            return Camera(
                id=row["id"],
                name=row["name"],
                location=row["location"] or "unknown",
                status=CameraStatus(row["status"]),
                camera_type=CameraType(row["camera_type"]),
                resolution=resolution,
                fps=row["fps"],
                region_id=row["region_id"],
                metadata=metadata,
                created_at=Timestamp(row["created_at"]),
                updated_at=Timestamp(row["updated_at"]),
            )
        except Exception as e:
            logger.error(f"转换数据库行到Camera实体失败: {e}, row={row}")
            raise RepositoryError(f"转换数据库行到Camera实体失败: {e}")

    async def save(self, camera: Camera) -> str:
        """保存摄像头.

        Args:
            camera: 摄像头实体

        Returns:
            str: 保存的摄像头ID
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                # 准备数据
                resolution_json = (
                    json.dumps(list(camera.resolution)) if camera.resolution else None
                )
                metadata_json = json.dumps(camera.metadata) if camera.metadata else "{}"

                await conn.execute(
                    """
                    INSERT INTO cameras
                    (id, name, location, status, camera_type, resolution, fps, region_id, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        status = EXCLUDED.status,
                        camera_type = EXCLUDED.camera_type,
                        resolution = EXCLUDED.resolution,
                        fps = EXCLUDED.fps,
                        region_id = EXCLUDED.region_id,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                    """,
                    camera.id,
                    camera.name,
                    camera.location,
                    camera.status.value,
                    camera.camera_type.value,
                    resolution_json,
                    camera.fps,
                    camera.region_id,
                    metadata_json,
                    camera.created_at.value,
                    camera.updated_at.value,
                )

                logger.debug(f"摄像头已保存到数据库: {camera.id}")
                return camera.id
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存摄像头失败: {e}")
            raise RepositoryError(f"保存摄像头失败: {e}")

    async def find_by_id(self, camera_id: str) -> Optional[Camera]:
        """根据ID查找摄像头.

        Args:
            camera_id: 摄像头ID

        Returns:
            Optional[Camera]: 摄像头实体，如果不存在则返回None
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                row = await conn.fetchrow(
                    """
                    SELECT id, name, location, status, camera_type, resolution, fps,
                           region_id, metadata, created_at, updated_at
                    FROM cameras
                    WHERE id = $1
                    """,
                    camera_id,
                )

                if not row:
                    return None

                return self._row_to_camera(row)
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询摄像头失败: {e}")
            raise RepositoryError(f"查询摄像头失败: {e}")

    async def find_by_region_id(self, region_id: str) -> List[Camera]:
        """根据区域ID查找摄像头.

        Args:
            region_id: 区域ID

        Returns:
            List[Camera]: 摄像头列表
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, name, location, status, camera_type, resolution, fps,
                           region_id, metadata, created_at, updated_at
                    FROM cameras
                    WHERE region_id = $1
                    ORDER BY name
                    """,
                    region_id,
                )

                cameras = []
                for row in rows:
                    cameras.append(self._row_to_camera(row))

                return cameras
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"根据区域ID查询摄像头失败: {e}")
            raise RepositoryError(f"根据区域ID查询摄像头失败: {e}")

    async def find_all(self) -> List[Camera]:
        """查找所有摄像头.

        Returns:
            List[Camera]: 摄像头列表
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, name, location, status, camera_type, resolution, fps,
                           region_id, metadata, created_at, updated_at
                    FROM cameras
                    ORDER BY name
                    """
                )

                cameras = []
                for row in rows:
                    cameras.append(self._row_to_camera(row))

                return cameras
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询所有摄像头失败: {e}")
            raise RepositoryError(f"查询所有摄像头失败: {e}")

    async def find_active(self) -> List[Camera]:
        """查找活跃的摄像头.

        Returns:
            List[Camera]: 活跃摄像头列表
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, name, location, status, camera_type, resolution, fps,
                           region_id, metadata, created_at, updated_at
                    FROM cameras
                    WHERE status = 'active'
                    ORDER BY name
                    """
                )

                cameras = []
                for row in rows:
                    cameras.append(self._row_to_camera(row))

                return cameras
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询活跃摄像头失败: {e}")
            raise RepositoryError(f"查询活跃摄像头失败: {e}")

    async def count(self) -> int:
        """统计摄像头数量.

        Returns:
            int: 摄像头数量
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                count = await conn.fetchval("SELECT COUNT(*) FROM cameras")
                return count or 0
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"统计摄像头数量失败: {e}")
            raise RepositoryError(f"统计摄像头数量失败: {e}")

    async def delete_by_id(self, camera_id: str) -> bool:
        """根据ID删除摄像头.

        Args:
            camera_id: 摄像头ID

        Returns:
            bool: 删除是否成功
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                result = await conn.execute(
                    "DELETE FROM cameras WHERE id = $1",
                    camera_id,
                )
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"摄像头已从数据库删除: {camera_id}")
                return deleted
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"删除摄像头失败: {e}")
            raise RepositoryError(f"删除摄像头失败: {e}")

    async def exists(self, camera_id: str) -> bool:
        """检查摄像头是否存在.

        Args:
            camera_id: 摄像头ID

        Returns:
            bool: 是否存在
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()
            try:
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM cameras WHERE id = $1)",
                    camera_id,
                )
                return exists or False
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"检查摄像头是否存在失败: {e}")
            raise RepositoryError(f"检查摄像头是否存在失败: {e}")

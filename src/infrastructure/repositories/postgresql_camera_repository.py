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
                            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                            name VARCHAR(100) NOT NULL,
                            location VARCHAR(200),
                            status VARCHAR(20) DEFAULT 'inactive',
                            camera_type VARCHAR(50) DEFAULT 'fixed',
                            resolution JSONB,
                            fps INTEGER,
                            region_id VARCHAR(100),
                            metadata JSONB DEFAULT '{}'::jsonb,
                            stream_url VARCHAR(500),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    logger.info("cameras表已创建")
                else:
                    # 表已存在，检查并添加缺失的列
                    # 注意：id列如果是VARCHAR，需要迁移到UUID（通过迁移脚本处理）
                    required_columns = {
                        "status": ("VARCHAR(20)", "'inactive'", True),
                        "region_id": ("VARCHAR(100)", "NULL", False),
                        "metadata": ("JSONB", "'{}'::jsonb", True),
                        "stream_url": ("VARCHAR(500)", "NULL", False),
                    }

                    for column_name, (
                        column_type,
                        default_value,
                        update_existing,
                    ) in required_columns.items():
                        column_exists = await conn.fetchval(
                            """
                            SELECT EXISTS (
                                SELECT FROM information_schema.columns
                                WHERE table_schema = 'public'
                                AND table_name = 'cameras'
                                AND column_name = $1
                            )
                            """,
                            column_name,
                        )

                        if not column_exists:
                            logger.warning(f"cameras表缺少{column_name}列，正在添加...")
                            try:
                                if default_value == "NULL":
                                    await conn.execute(
                                        f"""
                                        ALTER TABLE cameras
                                        ADD COLUMN {column_name} {column_type}
                                        """
                                    )
                                else:
                                    await conn.execute(
                                        f"""
                                        ALTER TABLE cameras
                                        ADD COLUMN {column_name} {column_type} DEFAULT {default_value}
                                        """
                                    )

                                    # 如果列有默认值且需要更新现有记录，为现有记录设置默认值
                                    if default_value != "NULL" and update_existing:
                                        await conn.execute(
                                            f"""
                                            UPDATE cameras
                                            SET {column_name} = {default_value}
                                            WHERE {column_name} IS NULL
                                            """  # nosec B608 - column_name from schema config
                                        )
                                logger.info(f"已添加{column_name}列到cameras表")
                            except Exception as col_error:
                                # 如果列已存在（并发情况），忽略错误
                                if "already exists" in str(col_error).lower():
                                    logger.debug(f"{column_name}列已存在，跳过")
                                else:
                                    logger.warning(f"添加{column_name}列时出错: {col_error}")
                        else:
                            logger.debug(f"{column_name}列已存在")

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

            # 将UUID转换为字符串
            camera_id = str(row["id"]) if row["id"] else None

            # 处理 status 字段，如果为空则默认为 inactive
            status_value = row.get("status") or "inactive"
            try:
                camera_status = CameraStatus(status_value)
            except ValueError:
                logger.warning(f"无效的status值: {status_value}，使用默认值 inactive")
                camera_status = CameraStatus.INACTIVE

            # 处理 camera_type 字段，如果为空则默认为 fixed
            camera_type_value = row.get("camera_type") or "fixed"
            try:
                camera_type = CameraType(camera_type_value)
            except ValueError:
                logger.warning(f"无效的camera_type值: {camera_type_value}，使用默认值 fixed")
                camera_type = CameraType.FIXED

            return Camera(
                id=camera_id,
                name=row["name"],
                location=row["location"] or "unknown",
                status=camera_status,
                camera_type=camera_type,
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

                # 从 metadata 中提取 stream_url，如果没有则使用 source 作为 stream_url
                stream_url = None
                if camera.metadata:
                    stream_url = camera.metadata.get(
                        "stream_url"
                    ) or camera.metadata.get("source")

                # 检查 id 列的类型
                id_type = await conn.fetchval(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'cameras'
                    AND column_name = 'id'
                    """
                )

                # 如果camera.id为空或空字符串，让数据库自动生成ID
                if camera.id and camera.id.strip():
                    # 更新现有记录
                    if id_type == "uuid":
                        # UUID 类型
                        await conn.execute(
                            """
                            INSERT INTO cameras
                            (id, name, location, status, camera_type, resolution, fps, region_id, metadata, stream_url, created_at, updated_at)
                            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            ON CONFLICT (id) DO UPDATE SET
                                name = EXCLUDED.name,
                                location = EXCLUDED.location,
                                status = EXCLUDED.status,
                                camera_type = EXCLUDED.camera_type,
                                resolution = EXCLUDED.resolution,
                                fps = EXCLUDED.fps,
                                region_id = EXCLUDED.region_id,
                                metadata = EXCLUDED.metadata,
                                stream_url = EXCLUDED.stream_url,
                                updated_at = EXCLUDED.updated_at
                            RETURNING id
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
                            stream_url,
                            camera.created_at.value,
                            camera.updated_at.value,
                        )
                        # 从RETURNING获取ID（确保一致性）
                        generated_id = await conn.fetchval(
                            "SELECT id FROM cameras WHERE id = $1::uuid", camera.id
                        )
                    else:
                        # VARCHAR 类型
                        await conn.execute(
                            """
                            INSERT INTO cameras
                            (id, name, location, status, camera_type, resolution, fps, region_id, metadata, stream_url, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            ON CONFLICT (id) DO UPDATE SET
                                name = EXCLUDED.name,
                                location = EXCLUDED.location,
                                status = EXCLUDED.status,
                                camera_type = EXCLUDED.camera_type,
                                resolution = EXCLUDED.resolution,
                                fps = EXCLUDED.fps,
                                region_id = EXCLUDED.region_id,
                                metadata = EXCLUDED.metadata,
                                stream_url = EXCLUDED.stream_url,
                                updated_at = EXCLUDED.updated_at
                            RETURNING id
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
                            stream_url,
                            camera.created_at.value,
                            camera.updated_at.value,
                        )
                        generated_id = camera.id
                else:
                    # 插入新记录，让数据库自动生成ID
                    if id_type == "uuid":
                        # UUID 类型，自动生成
                        generated_id = await conn.fetchval(
                            """
                            INSERT INTO cameras
                            (name, location, status, camera_type, resolution, fps, region_id, metadata, stream_url, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            RETURNING id
                            """,
                            camera.name,
                            camera.location,
                            camera.status.value,
                            camera.camera_type.value,
                            resolution_json,
                            camera.fps,
                            camera.region_id,
                            metadata_json,
                            stream_url,
                            camera.created_at.value,
                            camera.updated_at.value,
                        )
                    else:
                        # VARCHAR 类型，需要生成一个ID（使用UUID字符串）
                        import uuid

                        generated_id_str = str(uuid.uuid4())
                        await conn.execute(
                            """
                            INSERT INTO cameras
                            (id, name, location, status, camera_type, resolution, fps, region_id, metadata, stream_url, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            RETURNING id
                            """,
                            generated_id_str,
                            camera.name,
                            camera.location,
                            camera.status.value,
                            camera.camera_type.value,
                            resolution_json,
                            camera.fps,
                            camera.region_id,
                            metadata_json,
                            stream_url,
                            camera.created_at.value,
                            camera.updated_at.value,
                        )
                        generated_id = generated_id_str

                # 将生成的UUID转换为字符串
                generated_id_str = str(generated_id)
                logger.debug(f"摄像头已保存到数据库: {generated_id_str}")
                return generated_id_str
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
                # 检查 id 列的类型，如果是 UUID 则使用类型转换，否则直接比较
                id_type = await conn.fetchval(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'cameras'
                    AND column_name = 'id'
                    """
                )

                if id_type == "uuid":
                    # UUID 类型，需要类型转换
                    where_clause = "WHERE id = $1::uuid"
                else:
                    # VARCHAR 类型，直接比较
                    where_clause = "WHERE id = $1"

                row = await conn.fetchrow(
                    f"""
                    SELECT id, name, location, status, camera_type, resolution, fps,
                           region_id, metadata, stream_url, created_at, updated_at
                    FROM cameras
                    {where_clause}
                    """,  # nosec B608 - where_clause is fixed 'WHERE id = $1' or 'WHERE id = $1::uuid'
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
                           region_id, metadata, stream_url, created_at, updated_at
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
                           region_id, metadata, stream_url, created_at, updated_at
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
            # 使用上下文管理器自动管理连接
            async with self.pool.acquire() as conn:
                # 查询活跃摄像头：1) status为active/online/running，或 2) 最近1小时内有检测记录
                # 注意：cameras.id可能是UUID类型，detection_records.camera_id是VARCHAR，需要类型转换
                logger.info("执行活跃摄像头SQL查询...")
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT c.id, c.name, c.location, c.status, c.camera_type,
                           c.resolution, c.fps, c.region_id, c.metadata,
                           c.created_at, c.updated_at
                    FROM cameras c
                    LEFT JOIN detection_records dr ON c.id::text = dr.camera_id
                        AND dr.timestamp > NOW() - INTERVAL '1 hour'
                    WHERE c.status IN ('active', 'online', 'running')
                       OR dr.id IS NOT NULL
                    ORDER BY c.name
                    """
                )
                logger.info(f"SQL查询返回 {len(rows)} 行数据")

                cameras = []
                for row in rows:
                    logger.debug(
                        f"处理摄像头行: id={row['id']}, name={row['name']}, status={row['status']}"
                    )
                    cameras.append(self._row_to_camera(row))

                logger.info(f"查询到 {len(cameras)} 个活跃摄像头")
                return cameras
        except Exception as e:
            logger.error(f"查询活跃摄像头失败: {e}", exc_info=True)
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
                # 检查 id 列的类型，如果是 UUID 则使用类型转换，否则直接比较
                id_type = await conn.fetchval(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'cameras'
                    AND column_name = 'id'
                    """
                )

                if id_type == "uuid":
                    exists_query = (
                        "SELECT EXISTS(SELECT 1 FROM cameras WHERE id = $1::uuid)"
                    )
                else:
                    exists_query = "SELECT EXISTS(SELECT 1 FROM cameras WHERE id = $1)"

                exists = await conn.fetchval(exists_query, camera_id)
                return exists or False
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"检查摄像头是否存在失败: {e}")
            raise RepositoryError(f"检查摄像头是否存在失败: {e}")

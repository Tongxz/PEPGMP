"""
PostgreSQL检测记录仓储实现
使用PostgreSQL数据库存储检测记录
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# 导入领域实体
from src.domain.entities.detection_record import (
    DetectionRecord as DomainDetectionRecord,
)
from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp
from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
    RepositoryError,
)

logger = logging.getLogger(__name__)


class PostgreSQLDetectionRepository(IDetectionRepository):
    """PostgreSQL检测记录仓储实现"""

    def __init__(self, connection_string: str = None):
        """
        初始化PostgreSQL仓储

        Args:
            connection_string: 数据库连接字符串
        """
        self.connection_string = connection_string or self._get_default_connection()
        self._connection = None
        self._pool = None
        self._lock = None  # 用于并发控制

        logger.info("PostgreSQL检测记录仓储初始化")

    def _get_default_connection(self) -> str:
        """获取默认连接字符串"""
        import os

        return os.getenv(
            "DATABASE_URL",
            "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
        )

    async def _get_pool(self):
        """获取数据库连接池（线程安全）"""
        if self._pool is None:
            try:
                pass

                import asyncpg

                # 创建连接池（最小2个连接，最大10个连接）
                self._pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=2,
                    max_size=10,
                    command_timeout=30,
                )
                logger.info("PostgreSQL连接池已建立")
            except ImportError:
                raise RepositoryError("asyncpg依赖未安装")
            except Exception as e:
                raise RepositoryError(f"PostgreSQL连接池创建失败: {e}")

        return self._pool

    async def _get_connection(self):
        """获取数据库连接（使用连接池）"""
        pool = await self._get_pool()
        return await pool.acquire()

    async def _release_connection(self, conn):
        """释放数据库连接（回收到连接池）"""
        if self._pool and conn:
            await self._pool.release(conn)

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        序列化 metadata，处理枚举类型和其他不可序列化的对象

        Args:
            metadata: 元数据字典

        Returns:
            可序列化的字典
        """
        if not metadata:
            return {}

        serialized = {}
        for key, value in metadata.items():
            if value is None:
                serialized[key] = None
            elif isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            elif isinstance(value, list):
                # 处理列表中的对象
                serialized[key] = [self._serialize_value(item) for item in value]
            elif isinstance(value, dict):
                # 递归处理字典
                serialized[key] = self._serialize_metadata(value)
            else:
                # 处理其他类型（枚举、对象等）
                serialized[key] = self._serialize_value(value)

        return serialized

    def _serialize_value(self, value: Any) -> Any:
        """
        序列化单个值

        Args:
            value: 要序列化的值

        Returns:
            可序列化的值
        """
        import enum
        from datetime import datetime

        # 1. 首先处理 None 和基本类型
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        # 2. 处理枚举类型（优先级最高）
        if isinstance(value, enum.Enum):
            return value.value

        # 3. 处理字典（递归处理字典中的值）
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                result[k] = self._serialize_value(v)
            return result

        # 4. 处理列表（递归处理列表中的值）
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        # 5. 处理 Timestamp 对象
        if (
            hasattr(value, "value")
            and hasattr(value, "__class__")
            and "Timestamp" in str(value.__class__)
        ):
            if isinstance(value.value, datetime):
                return value.value.isoformat()
            return str(value.value)

        # 6. 处理 Confidence 对象
        if (
            hasattr(value, "value")
            and hasattr(value, "__class__")
            and "Confidence" in str(value.__class__)
        ):
            return float(value.value)

        # 7. 处理 BoundingBox 对象
        if (
            hasattr(value, "to_dict")
            and hasattr(value, "__class__")
            and "BoundingBox" in str(value.__class__)
        ):
            return value.to_dict()

        # 8. 处理 dataclass 对象（使用 __dict__）
        if hasattr(value, "__dict__") and not isinstance(value, dict):
            result = {}
            for k, v in value.__dict__.items():
                result[k] = self._serialize_value(v)
            return result

        # 9. 处理其他对象（尝试转换为字符串）
        try:
            # 尝试 JSON 序列化
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # 如果无法序列化，转换为字符串
            return str(value)

    async def _ensure_table_exists(self):
        """确保表存在（使用连接池）"""
        conn = None
        try:
            conn = await self._get_connection()

            create_table_sql = """
            CREATE TABLE IF NOT EXISTS detection_records (
                id VARCHAR(255) PRIMARY KEY,
                camera_id VARCHAR(255) NOT NULL,
                objects JSONB NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                confidence FLOAT NOT NULL DEFAULT 0.0,
                processing_time FLOAT NOT NULL,
                frame_id INTEGER,
                region_id VARCHAR(255),
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_detection_records_camera_id
            ON detection_records(camera_id);

            CREATE INDEX IF NOT EXISTS idx_detection_records_timestamp
            ON detection_records(timestamp);

            CREATE INDEX IF NOT EXISTS idx_detection_records_confidence
            ON detection_records(confidence);
            """

            await conn.execute(create_table_sql)

            # 检查并添加缺失的字段（用于已存在的表）
            try:
                # 检查表是否存在
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'detection_records'
                    )
                """
                )

                if table_exists:
                    # 检查 confidence 字段是否存在
                    check_column_sql = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'detection_records'
                    AND column_name = 'confidence'
                    """
                    result = await conn.fetchval(check_column_sql)

                    if result is None:
                        # 添加 confidence 字段（PostgreSQL 不支持 IF NOT EXISTS，需要先检查）
                        logger.info("检测到表缺少 confidence 字段，正在添加...")
                        try:
                            await conn.execute(
                                """
                                ALTER TABLE detection_records
                                ADD COLUMN confidence FLOAT NOT NULL DEFAULT 0.0
                            """
                            )
                            logger.info("已添加 confidence 字段")
                        except Exception as add_error:
                            # 如果字段已存在（并发情况），忽略错误
                            if "already exists" not in str(add_error).lower():
                                logger.warning(f"添加 confidence 字段失败: {add_error}")
                            else:
                                logger.debug("confidence 字段已存在（并发添加）")
            except Exception as e:
                logger.warning(f"检查/添加 confidence 字段时出错: {e}")

            logger.debug("检测记录表已确保存在")
        finally:
            if conn:
                await self._release_connection(conn)

    async def save(self, record: DomainDetectionRecord) -> str:
        """
        保存检测记录（使用连接池，线程安全）

        Args:
            record: 检测记录

        Returns:
            str: 保存的记录ID
        """
        conn = None
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()

            # 检查 id 字段类型，以适配不同的表结构
            id_type = await conn.fetchval(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'detection_records'
                AND column_name = 'id'
            """
            )

            # 转换对象列表为字典格式（用于JSON序列化）
            objects_dict = []
            for obj in record.objects:
                if hasattr(obj, "to_dict"):
                    objects_dict.append(obj.to_dict())
                elif isinstance(obj, dict):
                    objects_dict.append(obj)
                else:
                    # 尝试转换为字典
                    objects_dict.append(
                        {
                            "class_id": getattr(obj, "class_id", 0),
                            "class_name": getattr(obj, "class_name", "unknown"),
                            "confidence": float(getattr(obj, "confidence", 0.0))
                            if hasattr(obj, "confidence")
                            else 0.0,
                            "bbox": getattr(obj, "bbox", [0, 0, 0, 0]),
                            "track_id": getattr(obj, "track_id", None),
                            "metadata": getattr(obj, "metadata", {}),
                        }
                    )

            # 从objects计算统计数据（兼容旧表结构）
            person_count = sum(
                1 for obj in objects_dict if obj.get("class_name") == "person"
            )
            handwash_events = sum(
                1
                for obj in objects_dict
                if obj.get("class_name") in ["handwashing", "handwash"]
            )
            sanitize_events = sum(
                1
                for obj in objects_dict
                if obj.get("class_name") in ["sanitizing", "sanitize"]
            )
            hairnet_violations = sum(
                1 for obj in objects_dict if obj.get("class_name") == "no_hairnet"
            )

            if id_type == "bigint" or id_type == "integer":
                # 旧表结构：id 是 bigint（自增），不指定 id，让数据库自动生成
                # 同时写入统计字段以兼容旧查询
                insert_sql = """
                INSERT INTO detection_records
                (camera_id, objects, timestamp, confidence, processing_time, frame_id, region_id, metadata,
                 person_count, handwash_events, sanitize_events, hairnet_violations)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """

                # 转换 confidence 为 float（支持 Confidence 对象或 float）
                confidence_value = (
                    float(record.confidence.value)
                    if hasattr(record.confidence, "value")
                    else float(record.confidence)
                )

                # 转换 timestamp 为 datetime（支持 Timestamp 对象或 datetime）
                timestamp_value = (
                    record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp
                )

                # 移除时区信息以匹配数据库 TIMESTAMP WITHOUT TIME ZONE
                # 数据库表定义为 WITHOUT TIME ZONE，无法接受带时区的datetime
                if timestamp_value.tzinfo is not None:
                    # 先转换为UTC，再移除时区信息（确保时间值正确）
                    from datetime import timezone as tz

                    timestamp_value = timestamp_value.astimezone(tz.utc).replace(
                        tzinfo=None
                    )

                # 转换 metadata 为可序列化的字典（处理枚举类型）
                metadata_dict = (
                    self._serialize_metadata(record.metadata)
                    if record.metadata
                    else None
                )

                # 确保 metadata_dict 可以序列化
                metadata_json = None
                if metadata_dict:
                    try:
                        metadata_json = json.dumps(metadata_dict)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"metadata 序列化失败，尝试重新序列化: {e}")
                        # 如果序列化失败，尝试更彻底的序列化
                        metadata_dict = self._serialize_metadata(record.metadata)
                        metadata_json = json.dumps(metadata_dict, default=str)

                record_id = await conn.fetchval(
                    insert_sql,
                    record.camera_id,
                    json.dumps(objects_dict),
                    timestamp_value,
                    confidence_value,
                    record.processing_time,
                    record.frame_id,
                    record.region_id,
                    metadata_json,
                    person_count,
                    handwash_events,
                    sanitize_events,
                    hairnet_violations,
                )

                # 返回字符串格式的ID
                saved_id = str(record_id)
                logger.debug(f"检测记录已保存（自增ID）: {saved_id}")
                return saved_id
            else:
                # 新表结构：id 是 VARCHAR，使用字符串ID
                # 同时写入统计字段以兼容旧查询
                insert_sql = """
                INSERT INTO detection_records
                (id, camera_id, objects, timestamp, confidence, processing_time, frame_id, region_id, metadata,
                 person_count, handwash_events, sanitize_events, hairnet_violations)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    objects = EXCLUDED.objects,
                    timestamp = EXCLUDED.timestamp,
                    confidence = EXCLUDED.confidence,
                    processing_time = EXCLUDED.processing_time,
                    frame_id = EXCLUDED.frame_id,
                    region_id = EXCLUDED.region_id,
                    metadata = EXCLUDED.metadata,
                    person_count = EXCLUDED.person_count,
                    handwash_events = EXCLUDED.handwash_events,
                    sanitize_events = EXCLUDED.sanitize_events,
                    hairnet_violations = EXCLUDED.hairnet_violations
                """

                # 转换 confidence 为 float（支持 Confidence 对象或 float）
                confidence_value = (
                    float(record.confidence.value)
                    if hasattr(record.confidence, "value")
                    else float(record.confidence)
                )

                # 转换 timestamp 为 datetime（支持 Timestamp 对象或 datetime）
                timestamp_value = (
                    record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp
                )

                # 移除时区信息以匹配数据库 TIMESTAMP WITHOUT TIME ZONE
                # 数据库表定义为 WITHOUT TIME ZONE，无法接受带时区的datetime
                if timestamp_value.tzinfo is not None:
                    # 先转换为UTC，再移除时区信息（确保时间值正确）
                    from datetime import timezone as tz

                    timestamp_value = timestamp_value.astimezone(tz.utc).replace(
                        tzinfo=None
                    )

                # 转换 metadata 为可序列化的字典（处理枚举类型）
                metadata_dict = (
                    self._serialize_metadata(record.metadata)
                    if record.metadata
                    else None
                )

                # 确保 metadata_dict 可以序列化
                metadata_json = None
                if metadata_dict:
                    try:
                        metadata_json = json.dumps(metadata_dict)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"metadata 序列化失败，尝试重新序列化: {e}")
                        # 如果序列化失败，尝试更彻底的序列化
                        metadata_dict = self._serialize_metadata(record.metadata)
                        metadata_json = json.dumps(metadata_dict, default=str)

                await conn.execute(
                    insert_sql,
                    str(record.id),
                    record.camera_id,
                    json.dumps(objects_dict),
                    timestamp_value,
                    confidence_value,
                    record.processing_time,
                    record.frame_id,
                    record.region_id,
                    metadata_json,
                    person_count,
                    handwash_events,
                    sanitize_events,
                    hairnet_violations,
                )

                logger.debug(f"检测记录已保存（字符串ID）: {record.id}")
                return str(record.id)

        except Exception as e:
            logger.error(f"保存检测记录失败: {e}")
            raise RepositoryError(f"保存检测记录失败: {e}")
        finally:
            # 确保连接被释放回连接池
            if conn:
                await self._release_connection(conn)

    async def find_by_id(self, record_id: str) -> Optional[DomainDetectionRecord]:
        """
        根据ID查找记录

        Args:
            record_id: 记录ID

        Returns:
            Optional[DomainDetectionRecord]: 检测记录，如果不存在则返回None
        """
        try:
            conn = await self._get_connection()

            try:
                select_sql = """
                SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                       frame_id, region_id, metadata
                FROM detection_records
                WHERE id = $1
                """
                row = await conn.fetchrow(select_sql, record_id)
            except Exception:
                # 兼容无 objects 等旧结构
                compat_sql = """
                SELECT id, camera_id, timestamp, processing_time,
                       frame_number as frame_id,
                       NULL::VARCHAR as region_id,
                       NULL::JSONB as metadata
                FROM detection_records
                WHERE id = $1
                """
                row = await conn.fetchrow(compat_sql, record_id)

            if row is None:
                return None

            return self._row_to_record(row)

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

    async def find_by_camera_id(
        self, camera_id: str, limit: int = 100, offset: int = 0
    ) -> List[DomainDetectionRecord]:
        """
        根据摄像头ID查找记录

        Args:
            camera_id: 摄像头ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[DomainDetectionRecord]: 检测记录列表
        """
        try:
            conn = await self._get_connection()
            rows = None

            try:
                select_sql = """
                SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                       frame_id, region_id, metadata
                FROM detection_records
                WHERE camera_id = $1
                ORDER BY timestamp DESC
                LIMIT $2 OFFSET $3
                """
                rows = await conn.fetch(select_sql, camera_id, limit, offset)
            except Exception:
                # 如果查询失败，尝试兼容模式
                try:
                    compat_sql = """
                    SELECT id, camera_id, timestamp, processing_time,
                           frame_number as frame_id,
                           NULL::VARCHAR as region_id,
                           NULL::JSONB as metadata
                    FROM detection_records
                    WHERE camera_id = $1
                    ORDER BY timestamp DESC
                    LIMIT $2 OFFSET $3
                    """
                    rows = await conn.fetch(compat_sql, camera_id, limit, offset)
                except Exception as e:
                    logger.error(f"兼容模式查询也失败: {e}")
                    rows = []
            finally:
                # 确保连接被释放，避免连接泄漏
                await self._release_connection(conn)

            if rows is None:
                rows = []
            return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

    async def find_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DomainDetectionRecord]:
        """
        根据时间范围查找记录

            Args:
            start_time: 开始时间
            end_time: 结束时间
            camera_id: 摄像头ID（可选）
            limit: 限制数量
            offset: 偏移量

            Returns:
            List[DomainDetectionRecord]: 检测记录列表
        """
        try:
            # 数据库列是 TIMESTAMP WITHOUT TIME ZONE，需要naive datetime
            # 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
            from datetime import timezone as tz

            if start_time.tzinfo is not None:
                # 转换为UTC并去掉时区信息
                start_time = start_time.astimezone(tz.utc).replace(tzinfo=None)
            elif start_time.tzinfo is None:
                # 如果已经是naive，假设是UTC时间
                pass

            if end_time.tzinfo is not None:
                # 转换为UTC并去掉时区信息
                end_time = end_time.astimezone(tz.utc).replace(tzinfo=None)
            elif end_time.tzinfo is None:
                # 如果已经是naive，假设是UTC时间
                pass

            conn = await self._get_connection()
            rows = None

            try:
                if camera_id:
                    select_sql = """
                    SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                           frame_id, region_id, metadata
                    FROM detection_records
                    WHERE timestamp BETWEEN $1 AND $2 AND camera_id = $3
                    ORDER BY timestamp DESC
                    LIMIT $4 OFFSET $5
                    """
                    rows = await conn.fetch(
                        select_sql, start_time, end_time, camera_id, limit, offset
                    )
                else:
                    select_sql = """
                    SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                           frame_id, region_id, metadata
                    FROM detection_records
                    WHERE timestamp BETWEEN $1 AND $2
                    ORDER BY timestamp DESC
                    LIMIT $3 OFFSET $4
                    """
                    rows = await conn.fetch(
                        select_sql, start_time, end_time, limit, offset
                    )
            except Exception:
                # 如果查询失败，尝试兼容模式
                try:
                    if camera_id:
                        compat_sql = """
                        SELECT id, camera_id, timestamp, processing_time,
                               frame_number as frame_id,
                               NULL::VARCHAR as region_id,
                               NULL::JSONB as metadata
                        FROM detection_records
                        WHERE timestamp BETWEEN $1 AND $2 AND camera_id = $3
                        ORDER BY timestamp DESC
                        LIMIT $4 OFFSET $5
                        """
                        rows = await conn.fetch(
                            compat_sql, start_time, end_time, camera_id, limit, offset
                        )
                    else:
                        compat_sql = """
                        SELECT id, camera_id, timestamp, processing_time,
                               frame_number as frame_id,
                               NULL::VARCHAR as region_id,
                               NULL::JSONB as metadata
                        FROM detection_records
                        WHERE timestamp BETWEEN $1 AND $2
                        ORDER BY timestamp DESC
                        LIMIT $3 OFFSET $4
                        """
                        rows = await conn.fetch(
                            compat_sql, start_time, end_time, limit, offset
                        )
                except Exception as e:
                    logger.error(f"兼容模式查询也失败: {e}")
                    rows = []
            finally:
                # 确保连接被释放，避免连接泄漏
                await self._release_connection(conn)

            # 转换记录并返回
            if rows is None:
                rows = []
            records = [self._row_to_record(row) for row in rows]
            return records

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

    async def find_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DomainDetectionRecord]:
        """
        根据置信度范围查找记录

        Args:
            min_confidence: 最小置信度
            max_confidence: 最大置信度
            camera_id: 摄像头ID（可选）
            limit: 限制数量

        Returns:
            List[DomainDetectionRecord]: 检测记录列表
        """
        try:
            conn = await self._get_connection()
            rows = None

            try:
                if camera_id:
                    select_sql = """
                    SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                           frame_id, region_id, metadata
                    FROM detection_records
                    WHERE confidence BETWEEN $1 AND $2 AND camera_id = $3
                    ORDER BY timestamp DESC
                    LIMIT $4
                    """
                    rows = await conn.fetch(
                        select_sql, min_confidence, max_confidence, camera_id, limit
                    )
                else:
                    select_sql = """
                    SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                           frame_id, region_id, metadata
                    FROM detection_records
                    WHERE confidence BETWEEN $1 AND $2
                    ORDER BY timestamp DESC
                    LIMIT $3
                    """
                    rows = await conn.fetch(
                        select_sql, min_confidence, max_confidence, limit
                    )
            finally:
                # 确保连接被释放，避免连接泄漏
                await self._release_connection(conn)

            if rows is None:
                rows = []
            return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

    async def count_by_camera_id(self, camera_id: str) -> int:
        """
        统计摄像头记录数量

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 记录数量
        """
        try:
            conn = await self._get_connection()

            try:
                count_sql = (
                    "SELECT COUNT(*) FROM detection_records WHERE camera_id = $1"
                )
                result = await conn.fetchval(count_sql, camera_id)
                return result or 0
            finally:
                # 确保连接被释放，避免连接泄漏
                await self._release_connection(conn)

        except Exception as e:
            logger.error(f"统计检测记录失败: {e}")
            raise RepositoryError(f"统计检测记录失败: {e}")

    async def delete_by_id(self, record_id: str) -> bool:
        """
        根据ID删除记录

        Args:
            record_id: 记录ID

        Returns:
            bool: 删除是否成功
        """
        try:
            conn = await self._get_connection()

            delete_sql = "DELETE FROM detection_records WHERE id = $1"
            result = await conn.execute(delete_sql, record_id)

            # PostgreSQL返回格式: "DELETE 1" 或 "DELETE 0"
            deleted_count = int(result.split()[-1])
            success = deleted_count > 0

            if success:
                logger.debug(f"检测记录已删除: {record_id}")
            else:
                logger.warning(f"检测记录不存在: {record_id}")

            return success

        except Exception as e:
            logger.error(f"删除检测记录失败: {e}")
            raise RepositoryError(f"删除检测记录失败: {e}")

    async def delete_by_camera_id(self, camera_id: str) -> int:
        """
        删除摄像头的所有记录

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 删除的记录数量
        """
        try:
            conn = await self._get_connection()

            delete_sql = "DELETE FROM detection_records WHERE camera_id = $1"
            result = await conn.execute(delete_sql, camera_id)

            # PostgreSQL返回格式: "DELETE N"
            deleted_count = int(result.split()[-1])

            logger.info(f"删除了 {deleted_count} 条检测记录，摄像头: {camera_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"删除检测记录失败: {e}")
            raise RepositoryError(f"删除检测记录失败: {e}")

    async def get_statistics(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            camera_id: 摄像头ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            conn = await self._get_connection()

            # 构建WHERE条件
            where_conditions = []
            params = []
            param_count = 0

            if camera_id:
                param_count += 1
                where_conditions.append(f"camera_id = ${param_count}")
                params.append(camera_id)

            # 数据库列是 TIMESTAMP WITHOUT TIME ZONE，需要naive datetime
            from datetime import timezone as tz

            if start_time:
                param_count += 1
                where_conditions.append(f"timestamp >= ${param_count}")
                # 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
                if start_time.tzinfo is not None:
                    start_time = start_time.astimezone(tz.utc).replace(tzinfo=None)
                params.append(start_time)

            if end_time:
                param_count += 1
                where_conditions.append(f"timestamp <= ${param_count}")
                # 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
                if end_time.tzinfo is not None:
                    end_time = end_time.astimezone(tz.utc).replace(tzinfo=None)
                params.append(end_time)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            # 统计查询
            stats_sql = f"""
            SELECT
                COUNT(*) as total_records,
                AVG(confidence) as avg_confidence,
                AVG(processing_time) as avg_processing_time,
                MIN(timestamp) as earliest_record,
                MAX(timestamp) as latest_record
            FROM detection_records
            {where_clause}
            """  # nosec B608

            result = await conn.fetchrow(stats_sql, *params)

            return {
                "total_records": result["total_records"] or 0,
                "avg_confidence": float(result["avg_confidence"])
                if result["avg_confidence"]
                else 0.0,
                "avg_processing_time": float(result["avg_processing_time"])
                if result["avg_processing_time"]
                else 0.0,
                "earliest_record": result["earliest_record"].isoformat()
                if result["earliest_record"]
                else None,
                "latest_record": result["latest_record"].isoformat()
                if result["latest_record"]
                else None,
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise RepositoryError(f"获取统计信息失败: {e}")

    async def get_violations(  # noqa: C901
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        查询违规明细，返回 { violations: List[Dict], total: int }

        兼容不同历史表结构：优先使用完整字段；失败时回退到最小字段集合。
        """
        try:
            conn = await self._get_connection()

            # 统计总数
            count_where = []
            params: List[Any] = []
            p = 0
            if camera_id:
                p += 1
                count_where.append(f"camera_id = ${p}")
                params.append(camera_id)
            if status:
                p += 1
                count_where.append(f"status = ${p}")
                params.append(status)
            if violation_type:
                p += 1
                count_where.append(f"violation_type = ${p}")
                params.append(violation_type)
            where_sql = (" WHERE " + " AND ".join(count_where)) if count_where else ""

            # 优化：只在第一页（offset=0）时查询总数，避免性能问题
            if offset == 0:
                try:
                    total_sql = f"SELECT COUNT(*) AS total FROM violation_events{where_sql}"  # nosec B608
                    total = await conn.fetchval(total_sql, *params)
                except Exception as e:
                    logger.warning(f"获取违规记录总数失败，使用近似值: {e}")
                    # 如果获取总数失败，使用当前记录数作为近似值
                    total = None
            else:
                # 非第一页不查询总数，使用近似值
                total = None

            # 查询明细（完整字段集）
            try:
                detail_sql = f"""
                SELECT id, camera_id, timestamp, violation_type, track_id, confidence,
                       status, snapshot_path, bbox, handled_at, handled_by, notes,
                       created_at, updated_at
                FROM violation_events
                {where_sql}
                ORDER BY timestamp DESC
                LIMIT ${p + 1} OFFSET ${p + 2}
                """  # nosec B608
                rows = await conn.fetch(detail_sql, *params, limit, offset)

                def _row_to_obj(r):
                    item = dict(r)
                    # 反序列化 JSON
                    try:
                        if isinstance(item.get("bbox"), str):
                            item["bbox"] = json.loads(item.get("bbox") or "null")
                    except Exception:
                        pass
                    # 时间格式转换（添加时区信息）
                    # 数据库中的时间戳是 TIMESTAMP WITHOUT TIME ZONE，假设为 UTC
                    # 转换为 ISO 格式时添加 UTC 时区标记，让前端能正确转换为本地时间
                    from datetime import timezone as tz

                    for k in ("timestamp", "handled_at", "created_at", "updated_at"):
                        if item.get(k) is not None and hasattr(item[k], "isoformat"):
                            dt = item[k]
                            # 如果是 naive datetime（没有时区信息），假设为 UTC
                            if dt.tzinfo is None:
                                # 添加 UTC 时区信息
                                dt = dt.replace(tzinfo=tz.utc)
                            item[k] = dt.isoformat()
                    return item

                violations = [_row_to_obj(r) for r in rows]
                # 如果没有查询总数，使用近似值（当前记录数+offset）
                if total is None:
                    total = (
                        len(violations) + offset
                        if len(violations) == limit
                        else len(violations) + offset
                    )
                return {
                    "violations": violations,
                    "total": int(total or 0),
                    "limit": limit,
                    "offset": offset,
                }
            except Exception:
                # 兼容最小字段集合
                compat_sql = f"""
                SELECT id, camera_id, timestamp, violation_type, track_id, confidence,
                       status, snapshot_path
                FROM violation_events
                {where_sql}
                ORDER BY timestamp DESC
                LIMIT ${p + 1} OFFSET ${p + 2}
                """  # nosec B608
                rows = await conn.fetch(compat_sql, *params, limit, offset)

                def _row_to_min(r):
                    item = dict(r)
                    if item.get("timestamp") is not None and hasattr(
                        item["timestamp"], "isoformat"
                    ):
                        item["timestamp"] = item["timestamp"].isoformat()
                    # 补齐缺失字段
                    for k in (
                        "bbox",
                        "handled_at",
                        "handled_by",
                        "notes",
                        "created_at",
                        "updated_at",
                    ):
                        item.setdefault(k, None)
                    return item

                violations = [_row_to_min(r) for r in rows]
                # 如果没有查询总数，使用近似值（当前记录数+offset）
                if total is None:
                    total = (
                        len(violations) + offset
                        if len(violations) == limit
                        else len(violations) + offset
                    )
                return {
                    "violations": violations,
                    "total": int(total or 0),
                    "limit": limit,
                    "offset": offset,
                }

        except Exception as e:
            logger.error(f"查询违规明细失败: {e}")
            raise RepositoryError(f"查询违规明细失败: {e}")

    async def update_violation_status(
        self,
        violation_id: int,
        status: str,
        notes: Optional[str] = None,
        handled_by: Optional[str] = None,
    ) -> bool:
        """
        更新违规状态

        Args:
            violation_id: 违规ID
            status: 新状态（pending, confirmed, false_positive, resolved）
            notes: 备注信息（可选）
            handled_by: 处理人（可选）

        Returns:
            bool: 更新是否成功
        """
        try:
            conn = await self._get_connection()

            # 构建UPDATE语句
            update_fields = ["status = $1", "handled_at = NOW()"]
            params: List[Any] = [status]
            param_idx = 1

            if notes is not None:
                param_idx += 1
                update_fields.append(f"notes = ${param_idx}")
                params.append(notes)

            if handled_by is not None:
                param_idx += 1
                update_fields.append(f"handled_by = ${param_idx}")
                params.append(handled_by)

            param_idx += 1
            update_sql = f"""
                UPDATE violation_events
                SET {', '.join(update_fields)}
                WHERE id = ${param_idx}
            """  # nosec B608
            params.append(violation_id)

            result = await conn.execute(update_sql, *params)

            # PostgreSQL返回格式: "UPDATE N"
            updated_count = int(result.split()[-1])
            success = updated_count > 0

            if success:
                logger.info(f"违规状态已更新: {violation_id} -> {status}")
            else:
                logger.warning(f"违规记录不存在: {violation_id}")

            return success

        except Exception as e:
            logger.error(f"更新违规状态失败: {e}")
            raise RepositoryError(f"更新违规状态失败: {e}")

    def _row_to_record(self, row) -> DomainDetectionRecord:
        """将数据库行转换为领域实体DetectionRecord对象（兼容无 objects/信心度的结构）。"""
        try:
            objects_val = row.get("objects") if hasattr(row, "get") else row["objects"]
        except Exception:
            objects_val = []
        # 解析 objects JSON（保持为字典列表，领域实体会在__post_init__中处理）
        if isinstance(objects_val, str):
            try:
                objects_val = json.loads(objects_val)
            except Exception:
                objects_val = []
        # 确保是列表
        if not isinstance(objects_val, list):
            objects_val = []

        # 时间戳：转换为Timestamp值对象
        try:
            timestamp_val = row["timestamp"]
            if isinstance(timestamp_val, datetime):
                timestamp_obj = Timestamp(timestamp_val)
            elif hasattr(timestamp_val, "value"):
                timestamp_obj = Timestamp(timestamp_val.value)
            else:
                timestamp_obj = Timestamp.now()
        except Exception:
            timestamp_obj = Timestamp.now()

        # 置信度：转换为Confidence值对象
        try:
            confidence_val = (
                float(row["confidence"]) if row["confidence"] is not None else 0.0
            )
            confidence_obj = Confidence(confidence_val)
        except Exception:
            confidence_obj = Confidence(0.0)

        # 元数据兼容
        metadata_val = {}
        try:
            metadata_val = (
                row.get("metadata") if hasattr(row, "get") else row.get("metadata", {})
            )
            if isinstance(metadata_val, str):
                metadata_val = json.loads(metadata_val)
            if metadata_val is None:
                metadata_val = {}
            if not isinstance(metadata_val, dict):
                metadata_val = {}
        except Exception:
            metadata_val = {}

        # 创建领域实体（objects保持为字典列表，会在需要时通过属性访问）
        return DomainDetectionRecord(
            id=str(row["id"]),
            camera_id=str(row["camera_id"]),
            objects=objects_val,  # 保持字典列表，领域实体的属性方法会处理
            timestamp=timestamp_obj,
            confidence=confidence_obj,
            processing_time=float(row.get("processing_time", 0.0)),
            frame_id=row.get("frame_id")
            if hasattr(row, "get")
            else row.get("frame_id"),
            region_id=row.get("region_id")
            if hasattr(row, "get")
            else row.get("region_id"),
            metadata=metadata_val,
        )

    async def close(self):
        """关闭数据库连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("PostgreSQL连接已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

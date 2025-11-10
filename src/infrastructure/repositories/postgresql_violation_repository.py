"""PostgreSQL违规仓储实现."""

import json
import logging
from datetime import timezone
from typing import Any, Dict, List, Optional

import asyncpg
from asyncpg import Pool

from src.domain.repositories.violation_repository import IViolationRepository
from src.domain.services.violation_service import Violation
from src.interfaces.repositories.detection_repository_interface import RepositoryError

logger = logging.getLogger(__name__)


class PostgreSQLViolationRepository(IViolationRepository):
    """PostgreSQL违规仓储实现."""

    def __init__(
        self, pool: Optional[Pool] = None, connection_string: Optional[str] = None
    ):
        """初始化PostgreSQL违规仓储.

        Args:
            pool: PostgreSQL连接池（优先使用）
            connection_string: 数据库连接字符串（如果未提供pool）
        """
        self.pool = pool
        self.connection_string = connection_string
        self._pool = None

    async def _get_pool(self):
        """获取数据库连接池."""
        if self._pool is None:
            if self.pool:
                self._pool = self.pool
            else:
                import os

                import asyncpg

                connection_string = self.connection_string or os.getenv(
                    "DATABASE_URL",
                    "postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development",
                )
                self._pool = await asyncpg.create_pool(
                    connection_string,
                    min_size=2,
                    max_size=10,
                    command_timeout=30,
                )
                logger.info("PostgreSQL违规仓储连接池已建立")
        return self._pool

    async def _get_connection(self):
        """获取数据库连接."""
        pool = await self._get_pool()
        return await pool.acquire()

    async def _release_connection(self, conn):
        """释放数据库连接."""
        pool = await self._get_pool()
        await pool.release(conn)

    async def save(
        self, violation: Violation, detection_id: Optional[str] = None
    ) -> int:
        """保存违规事件.

        Args:
            violation: 违规实体
            detection_id: 关联的检测记录ID（可选）

        Returns:
            保存后的违规事件ID
        """
        conn = None
        try:
            conn = await self._get_connection()

            # 获取detection_id（如果未提供，尝试从violation.metadata中获取）
            if not detection_id:
                detection_id = (
                    violation.metadata.get("detection_id")
                    if violation.metadata
                    else None
                )

            # 转换detection_id为BIGINT
            # detection_records表的id是BIGSERIAL（BIGINT），但领域实体可能使用字符串ID
            # 需要查找对应的数据库记录ID
            detection_id_int = None
            if detection_id:
                try:
                    # 首先尝试直接转换为整数（如果detection_id已经是数字）
                    try:
                        detection_id_int = int(detection_id)
                    except (ValueError, TypeError):
                        # 如果转换失败，说明是字符串ID，需要查找对应的数据库记录
                        # 根据表结构，detection_records.id是BIGINT，但可能之前保存时使用了字符串ID
                        # 尝试通过timestamp和camera_id查找最近的记录
                        # 或者，如果detection_id是字符串格式的时间戳ID，尝试查找
                        try:
                            # 方法1：尝试查找最近保存的记录（通过timestamp和camera_id）
                            # 这需要从violation中获取camera_id和timestamp
                            camera_id = violation.camera_id
                            timestamp_value = violation.timestamp
                            if timestamp_value.tzinfo is not None:
                                timestamp_value = timestamp_value.astimezone(
                                    timezone.utc
                                ).replace(tzinfo=None)

                            # 查找最近1分钟内的记录（允许一定的误差）
                            detection_record = await conn.fetchrow(
                                """
                                SELECT id FROM detection_records
                                WHERE camera_id = $1
                                  AND timestamp >= $2 - INTERVAL '1 minute'
                                  AND timestamp <= $2 + INTERVAL '1 minute'
                                ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $2)))
                                LIMIT 1
                                """,
                                camera_id,
                                timestamp_value,
                            )

                            if detection_record:
                                detection_id_int = int(detection_record["id"])
                                logger.debug(
                                    f"通过时间戳找到检测记录ID: {detection_id} -> {detection_id_int}"
                                )
                            else:
                                logger.warning(
                                    f"无法找到检测记录: detection_id={detection_id}, camera={camera_id}, timestamp={timestamp_value}"
                                )
                        except Exception as e:
                            logger.warning(f"查找检测记录ID失败: {e}")
                            # 如果查找失败，使用NULL（允许violation_id为NULL）
                except Exception as e:
                    logger.warning(f"处理detection_id失败: {e}")
                    # 如果处理失败，使用NULL（允许violation_id为NULL）

            # 获取边界框
            bbox_dict = None
            if violation.detected_object and violation.detected_object.bbox:
                bbox = violation.detected_object.bbox
                bbox_dict = {
                    "x": int(bbox.x1),
                    "y": int(bbox.y1),
                    "width": int(bbox.x2 - bbox.x1),
                    "height": int(bbox.y2 - bbox.y1),
                }

            # 获取跟踪ID
            track_id = None
            if violation.detected_object and violation.detected_object.track_id:
                track_id = violation.detected_object.track_id

            # 获取置信度
            confidence = violation.confidence.value if violation.confidence else 0.0

            # 转换时间戳（数据库需要naive datetime）
            timestamp_value = violation.timestamp
            if timestamp_value.tzinfo is not None:
                timestamp_value = timestamp_value.astimezone(timezone.utc).replace(
                    tzinfo=None
                )

            # 保存违规事件
            violation_id = await conn.fetchval(
                """
                INSERT INTO violation_events (
                    detection_id, camera_id, timestamp, violation_type,
                    track_id, confidence, bbox, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                detection_id_int,
                violation.camera_id,
                timestamp_value,
                violation.violation_type.value,
                track_id,
                confidence,
                json.dumps(bbox_dict) if bbox_dict else None,
                "pending",  # 默认状态
            )

            logger.info(
                f"违规事件已保存: violation_id={violation_id}, "
                f"type={violation.violation_type.value}, camera={violation.camera_id}"
            )

            return violation_id

        except Exception as e:
            logger.error(f"保存违规事件失败: {e}", exc_info=True)
            raise RepositoryError(f"保存违规事件失败: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def find_by_id(self, violation_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查找违规事件."""
        conn = None
        try:
            conn = await self._get_connection()
            row = await conn.fetchrow(
                """
                SELECT id, detection_id, camera_id, timestamp, violation_type,
                       track_id, confidence, snapshot_path, bbox, status,
                       handled_at, handled_by, notes, created_at, updated_at
                FROM violation_events
                WHERE id = $1
                """,
                violation_id,
            )

            if not row:
                return None

            return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"查询违规事件失败: {e}")
            raise RepositoryError(f"查询违规事件失败: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def find_all(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """查询违规事件列表."""
        conn = None
        try:
            conn = await self._get_connection()

            # 构建WHERE条件
            where_clauses = []
            params: List[Any] = []
            param_idx = 0

            if camera_id:
                param_idx += 1
                where_clauses.append(f"camera_id = ${param_idx}")
                params.append(camera_id)

            if status:
                param_idx += 1
                where_clauses.append(f"status = ${param_idx}")
                params.append(status)

            if violation_type:
                param_idx += 1
                where_clauses.append(f"violation_type = ${param_idx}")
                params.append(violation_type)

            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # 查询总数（只在第一页时查询）
            total = None
            if offset == 0:
                try:
                    total = await conn.fetchval(
                        f"SELECT COUNT(*) FROM violation_events{where_sql}",  # nosec B608
                        *params,
                    )
                except Exception as e:
                    logger.warning(f"获取违规记录总数失败: {e}")

            # 查询明细
            param_idx += 1
            limit_param = param_idx
            param_idx += 1
            offset_param = param_idx

            rows = await conn.fetch(
                f"""
                SELECT id, detection_id, camera_id, timestamp, violation_type,
                       track_id, confidence, snapshot_path, bbox, status,
                       handled_at, handled_by, notes, created_at, updated_at
                FROM violation_events
                {where_sql}
                ORDER BY timestamp DESC
                LIMIT ${limit_param} OFFSET ${offset_param}
                """,  # nosec B608
                *params,
                limit,
                offset,
            )

            violations = [self._row_to_dict(row) for row in rows]

            # 如果没有查询总数，使用近似值
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
            logger.error(f"查询违规事件列表失败: {e}")
            raise RepositoryError(f"查询违规事件列表失败: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def update_status(
        self,
        violation_id: int,
        status: str,
        notes: Optional[str] = None,
        handled_by: Optional[str] = None,
    ) -> bool:
        """更新违规事件状态."""
        conn = None
        try:
            conn = await self._get_connection()

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
        finally:
            if conn:
                await self._release_connection(conn)

    def _row_to_dict(self, row: asyncpg.Record) -> Dict[str, Any]:
        """将数据库行转换为字典."""
        item = dict(row)

        # 反序列化JSON字段
        if isinstance(item.get("bbox"), str):
            try:
                item["bbox"] = json.loads(item["bbox"])
            except Exception:
                pass

        # 时间格式转换
        for key in ("timestamp", "handled_at", "created_at", "updated_at"):
            if item.get(key) is not None and hasattr(item[key], "isoformat"):
                item[key] = item[key].isoformat()

        return item

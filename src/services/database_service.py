"""数据库服务 - 处理检测结果的持久化存储."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
from asyncpg.pool import Pool

logger = logging.getLogger(__name__)


class DatabaseService:
    """数据库服务 - 负责所有数据库操作."""

    def __init__(self, database_url: Optional[str] = None):
        """初始化数据库服务.

        Args:
            database_url: 数据库连接URL，如果为None则从环境变量读取
        """
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
        )
        self.pool: Optional[Pool] = None
        self._initialized = False

    async def init(self):
        """初始化数据库连接池."""
        if self._initialized:
            logger.warning("DatabaseService already initialized")
            return

        try:
            logger.info("Connecting to database...")
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
            self._initialized = True
            logger.info("✅ Database connection pool created successfully")

            # 测试连接
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"PostgreSQL version: {version}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """关闭数据库连接池."""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("Database connection pool closed")

    async def save_detection_record(
        self,
        camera_id: str,
        frame_number: int,
        result: Any,
        fps: float = 0.0,
    ) -> int:
        """保存检测记录.

        Args:
            camera_id: 摄像头ID
            frame_number: 帧编号
            result: 检测结果对象（DetectionResult）
            fps: 当前FPS

        Returns:
            插入记录的ID
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            # 提取数据
            person_count = (
                len(result.person_detections)
                if hasattr(result, "person_detections")
                else 0
            )
            hairnet_violations = sum(
                1
                for h in (
                    result.hairnet_results if hasattr(result, "hairnet_results") else []
                )
                if not h.get("has_hairnet", True)
            )
            handwash_count = (
                len(result.handwash_results)
                if hasattr(result, "handwash_results")
                else 0
            )
            sanitize_count = (
                len(result.sanitize_results)
                if hasattr(result, "sanitize_results")
                else 0
            )

            # 计算总处理时间
            processing_time = (
                sum(result.processing_times.values())
                if hasattr(result, "processing_times")
                else 0.0
            )

            # 准备JSON数据
            person_detections_json = json.dumps(
                result.person_detections if hasattr(result, "person_detections") else []
            )
            hairnet_results_json = json.dumps(
                result.hairnet_results if hasattr(result, "hairnet_results") else []
            )
            handwash_results_json = json.dumps(
                result.handwash_results if hasattr(result, "handwash_results") else []
            )
            sanitize_results_json = json.dumps(
                result.sanitize_results if hasattr(result, "sanitize_results") else []
            )

            async with self.pool.acquire() as conn:
                record_id = await conn.fetchval(
                    """
                    INSERT INTO detection_records (
                        camera_id, frame_number,
                        person_count, hairnet_violations,
                        handwash_events, sanitize_events,
                        person_detections, hairnet_results,
                        handwash_results, sanitize_results,
                        processing_time, fps
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING id
                    """,
                    camera_id,
                    frame_number,
                    person_count,
                    hairnet_violations,
                    handwash_count,
                    sanitize_count,
                    person_detections_json,
                    hairnet_results_json,
                    handwash_results_json,
                    sanitize_results_json,
                    processing_time,
                    fps,
                )

            logger.debug(
                f"Saved detection record: camera={camera_id}, "
                f"frame={frame_number}, record_id={record_id}"
            )
            return record_id

        except Exception as e:
            logger.error(f"Failed to save detection record: {e}")
            raise

    async def save_violation_event(
        self,
        detection_id: int,
        camera_id: str,
        violation_type: str,
        track_id: Optional[int] = None,
        confidence: float = 0.0,
        snapshot_path: Optional[str] = None,
        bbox: Optional[Dict] = None,
    ) -> int:
        """保存违规事件.

        Args:
            detection_id: 关联的检测记录ID
            camera_id: 摄像头ID
            violation_type: 违规类型 (no_hairnet, no_handwash, no_sanitize)
            track_id: 跟踪ID
            confidence: 置信度
            snapshot_path: 截图路径
            bbox: 边界框 {"x": 0, "y": 0, "width": 100, "height": 100}

        Returns:
            插入记录的ID
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            bbox_json = json.dumps(bbox) if bbox else None

            async with self.pool.acquire() as conn:
                event_id = await conn.fetchval(
                    """
                    INSERT INTO violation_events (
                        detection_id, camera_id, violation_type,
                        track_id, confidence, snapshot_path, bbox
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    detection_id,
                    camera_id,
                    violation_type,
                    track_id,
                    confidence,
                    snapshot_path,
                    bbox_json,
                )

            logger.info(
                f"Saved violation event: type={violation_type}, "
                f"camera={camera_id}, event_id={event_id}"
            )
            return event_id

        except Exception as e:
            logger.error(f"Failed to save violation event: {e}")
            raise

    async def update_hourly_statistics(
        self, camera_id: str, hour_start: datetime, stats: Dict[str, Any]
    ):
        """更新小时统计数据.

        Args:
            camera_id: 摄像头ID
            hour_start: 小时开始时间（整点）
            stats: 统计数据字典
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO statistics_hourly (
                        camera_id, hour_start, total_frames, total_persons,
                        total_hairnet_violations, total_handwash_events,
                        total_sanitize_events, avg_fps, avg_processing_time
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (camera_id, hour_start) DO UPDATE SET
                        total_frames = statistics_hourly.total_frames + EXCLUDED.total_frames,
                        total_persons = statistics_hourly.total_persons + EXCLUDED.total_persons,
                        total_hairnet_violations = statistics_hourly.total_hairnet_violations + EXCLUDED.total_hairnet_violations,
                        total_handwash_events = statistics_hourly.total_handwash_events + EXCLUDED.total_handwash_events,
                        total_sanitize_events = statistics_hourly.total_sanitize_events + EXCLUDED.total_sanitize_events,
                        avg_fps = (statistics_hourly.avg_fps + EXCLUDED.avg_fps) / 2,
                        avg_processing_time = (statistics_hourly.avg_processing_time + EXCLUDED.avg_processing_time) / 2,
                        updated_at = NOW()
                    """,
                    camera_id,
                    hour_start,
                    stats.get("frames", 0),
                    stats.get("persons", 0),
                    stats.get("hairnet_violations", 0),
                    stats.get("handwash_events", 0),
                    stats.get("sanitize_events", 0),
                    stats.get("fps", 0.0),
                    stats.get("processing_time", 0.0),
                )

            logger.debug(
                f"Updated hourly statistics: camera={camera_id}, hour={hour_start}"
            )

        except Exception as e:
            logger.error(f"Failed to update hourly statistics: {e}")
            raise

    # ===================== Alerts (Rules & History) =====================

    async def save_alert_history(
        self,
        camera_id: str,
        alert_type: str,
        message: str,
        rule_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        notification_sent: bool = False,
        notification_channels_used: Optional[List[str]] = None,
    ) -> int:
        """保存告警历史记录到 alert_history 表.

        Args:
            camera_id: 摄像头ID（系统级告警可用 'system'）
            alert_type: 告警类型（例如规则名或业务类型）
            message: 告警消息
            rule_id: 关联规则ID（可选）
            details: 额外信息（JSON）
            notification_sent: 是否已发送通知
            notification_channels_used: 实际使用的通知通道列表

        Returns:
            新增记录ID
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            details_json = json.dumps(details or {})
            channels_json = (
                json.dumps(notification_channels_used)
                if notification_channels_used is not None
                else None
            )

            async with self.pool.acquire() as conn:
                new_id = await conn.fetchval(
                    """
                    INSERT INTO alert_history (
                        rule_id, camera_id, alert_type, message, details,
                        notification_sent, notification_channels_used, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    RETURNING id
                    """,
                    rule_id,
                    camera_id,
                    alert_type,
                    message,
                    details_json,
                    notification_sent,
                    channels_json,
                )
            logger.info(
                f"Saved alert history: type={alert_type}, camera={camera_id}, id={new_id}"
            )
            return new_id
        except Exception as e:
            logger.error(f"Failed to save alert history: {e}")
            raise

    async def get_alert_history(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查询告警历史记录."""
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, rule_id, camera_id, alert_type, message, details,
                           notification_sent, notification_channels_used, timestamp
                    FROM alert_history
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::VARCHAR IS NULL OR alert_type = $2)
                    ORDER BY timestamp DESC
                    LIMIT $3
                    """,
                    camera_id,
                    alert_type,
                    limit,
                )
                out: List[Dict[str, Any]] = []
                for r in rows:
                    item = dict(r)
                    # 反序列化 JSON 字段
                    try:
                        item["details"] = json.loads(item.get("details") or "{}")
                    except Exception:
                        pass
                    try:
                        item["notification_channels_used"] = json.loads(
                            item.get("notification_channels_used") or "null"
                        )
                    except Exception:
                        pass
                    out.append(item)
                return out
        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            raise

    async def list_alert_rules(
        self,
        camera_id: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """列出告警规则."""
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, name, camera_id, rule_type, conditions,
                           notification_channels, recipients, enabled, priority,
                           created_at, updated_at
                    FROM alert_rules
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::BOOLEAN IS NULL OR enabled = $2)
                    ORDER BY updated_at DESC
                    """,
                    camera_id,
                    enabled,
                )
                out: List[Dict[str, Any]] = []
                for r in rows:
                    item = dict(r)
                    for key in ("conditions", "notification_channels", "recipients"):
                        try:
                            item[key] = json.loads(item.get(key) or "null")
                        except Exception:
                            pass
                    out.append(item)
                return out
        except Exception as e:
            logger.error(f"Failed to list alert rules: {e}")
            raise

    async def create_alert_rule(self, rule: Dict[str, Any]) -> int:
        """创建告警规则."""
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")
        try:
            async with self.pool.acquire() as conn:
                new_id = await conn.fetchval(
                    """
                    INSERT INTO alert_rules (
                        name, camera_id, rule_type, conditions,
                        notification_channels, recipients, enabled, priority,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, true), COALESCE($8, 'medium'), NOW(), NOW())
                    RETURNING id
                    """,
                    rule.get("name"),
                    rule.get("camera_id"),
                    rule.get("rule_type"),
                    json.dumps(rule.get("conditions") or {}),
                    json.dumps(rule.get("notification_channels") or []),
                    json.dumps(rule.get("recipients") or []),
                    rule.get("enabled"),
                    rule.get("priority"),
                )
            return new_id
        except Exception as e:
            logger.error(f"Failed to create alert rule: {e}")
            raise

    async def update_alert_rule(self, rule_id: int, updates: Dict[str, Any]) -> bool:
        """更新告警规则（部分字段）."""
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")
        try:
            # 动态更新，限定允许的字段
            allowed = {
                "name",
                "camera_id",
                "rule_type",
                "conditions",
                "notification_channels",
                "recipients",
                "enabled",
                "priority",
            }
            fields = []
            values: List[Any] = []  # type: ignore
            idx = 1
            for k, v in updates.items():
                if k not in allowed:
                    continue
                if k in {"conditions", "notification_channels", "recipients"}:
                    v = json.dumps(v)
                fields.append(f"{k} = ${idx}")
                values.append(v)
                idx += 1
            if not fields:
                return True
            values.append(rule_id)
            async with self.pool.acquire() as conn:
                await conn.execute(
                    f"""
                    UPDATE alert_rules SET {', '.join(fields)}, updated_at = NOW()
                    WHERE id = ${idx}
                    """,
                    *values,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update alert rule: {e}")
            raise

    async def get_recent_violations(
        self,
        camera_id: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> List[Dict]:
        """获取最近的违规事件.

        Args:
            camera_id: 摄像头ID，None表示所有摄像头
            limit: 返回记录数量限制
            status: 违规状态筛选

        Returns:
            违规事件列表
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT * FROM violation_events
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::VARCHAR IS NULL OR status = $2)
                    ORDER BY timestamp DESC
                    LIMIT $3
                """
                rows = await conn.fetch(query, camera_id, status, limit)
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent violations: {e}")
            raise

    async def get_statistics(
        self, camera_id: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """获取指定时间段的统计数据.

        Args:
            camera_id: 摄像头ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计数据字典
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT
                        SUM(total_frames) as total_frames,
                        SUM(total_persons) as total_persons,
                        SUM(total_hairnet_violations) as total_hairnet_violations,
                        SUM(total_handwash_events) as total_handwash_events,
                        SUM(total_sanitize_events) as total_sanitize_events,
                        AVG(avg_fps) as avg_fps,
                        AVG(avg_processing_time) as avg_processing_time
                    FROM statistics_hourly
                    WHERE camera_id = $1
                      AND hour_start >= $2
                      AND hour_start < $3
                    """,
                    camera_id,
                    start_time,
                    end_time,
                )

                if result:
                    return {
                        "total_frames": int(result["total_frames"] or 0),
                        "total_persons": int(result["total_persons"] or 0),
                        "total_hairnet_violations": int(
                            result["total_hairnet_violations"] or 0
                        ),
                        "total_handwash_events": int(
                            result["total_handwash_events"] or 0
                        ),
                        "total_sanitize_events": int(
                            result["total_sanitize_events"] or 0
                        ),
                        "avg_fps": float(result["avg_fps"] or 0.0),
                        "avg_processing_time": float(
                            result["avg_processing_time"] or 0.0
                        ),
                    }
                else:
                    return {
                        "total_frames": 0,
                        "total_persons": 0,
                        "total_hairnet_violations": 0,
                        "total_handwash_events": 0,
                        "total_sanitize_events": 0,
                        "avg_fps": 0.0,
                        "avg_processing_time": 0.0,
                    }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise

    async def update_violation_status(
        self, violation_id: int, status: str, notes: Optional[str] = None
    ):
        """更新违规事件状态.

        Args:
            violation_id: 违规事件ID
            status: 新状态 (pending, confirmed, false_positive, resolved)
            notes: 备注信息
        """
        if not self._initialized:
            raise RuntimeError("DatabaseService not initialized")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE violation_events
                    SET status = $1, handled_at = NOW(), notes = $2
                    WHERE id = $3
                    """,
                    status,
                    notes,
                    violation_id,
                )

            logger.info(f"Updated violation {violation_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update violation status: {e}")
            raise


# 全局数据库服务实例
_db_service: Optional[DatabaseService] = None


async def get_db_service() -> DatabaseService:
    """获取全局数据库服务实例."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
        await _db_service.init()
    return _db_service


async def close_db_service():
    """关闭全局数据库服务实例."""
    global _db_service
    if _db_service is not None:
        await _db_service.close()
        _db_service = None

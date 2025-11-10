"""
使用领域模型的检测服务
演示如何使用领域驱动设计重构现有服务
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.events.detection_events import (
    DetectionCreatedEvent,
    ViolationDetectedEvent,
)
from src.domain.repositories.camera_repository import ICameraRepository
from src.domain.repositories.detection_repository import IDetectionRepository
from src.domain.repositories.violation_repository import IViolationRepository
from src.domain.services.detection_service import DetectionService
from src.domain.services.violation_service import ViolationService
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.interfaces.storage import SnapshotInfo

logger = logging.getLogger(__name__)


class DetectionServiceDomain:
    """使用领域模型的检测服务"""

    def __init__(
        self,
        detection_repository: IDetectionRepository,
        camera_repository: ICameraRepository,
        violation_repository: Optional[IViolationRepository] = None,
    ):
        """
        初始化检测服务

        Args:
            detection_repository: 检测记录仓储
            camera_repository: 摄像头仓储
            violation_repository: 违规仓储（可选）
        """
        self.detection_repository = detection_repository
        self.camera_repository = camera_repository
        self.violation_repository = violation_repository
        self.detection_service = DetectionService()
        self.violation_service = ViolationService()

        logger.info("领域模型检测服务初始化完成")

    async def process_detection(  # noqa: C901
        self,
        camera_id: str,
        detected_objects: List[Dict[str, Any]],
        processing_time: float,
        frame_id: Optional[int] = None,
        snapshots: Optional[List[SnapshotInfo]] = None,
    ) -> DetectionRecord:
        """
        处理检测结果 - 使用领域模型

        Args:
            camera_id: 摄像头ID
            detected_objects: 检测到的对象列表
            processing_time: 处理时间
            frame_id: 帧ID（可选）

        Returns:
            DetectionRecord: 检测记录
        """
        try:
            # 1. 获取摄像头信息
            camera = await self.camera_repository.find_by_id(camera_id)
            if not camera:
                raise ValueError(f"摄像头不存在: {camera_id}")

            # 2. 创建检测对象实体
            domain_objects = []
            for obj_data in detected_objects:
                # 验证和修复边界框数据
                bbox_data = obj_data.get("bbox", [0, 0, 0, 0])
                if len(bbox_data) < 4:
                    logger.warning(f"无效的边界框数据: {bbox_data}，跳过此对象")
                    continue

                x1, y1, x2, y2 = bbox_data[0], bbox_data[1], bbox_data[2], bbox_data[3]

                # 修复无效的边界框（确保 x1 < x2 和 y1 < y2）
                if x1 >= x2:
                    if x1 == 0 and x2 == 0:
                        # 如果都是0，跳过此对象
                        logger.debug(f"边界框宽度为0，跳过: {bbox_data}")
                        continue
                    else:
                        # 交换坐标
                        x1, x2 = min(x1, x2), max(x1, x2)
                        logger.debug(
                            f"修复边界框 x 坐标: {bbox_data} -> [{x1}, {y1}, {x2}, {y2}]"
                        )

                if y1 >= y2:
                    if y1 == 0 and y2 == 0:
                        # 如果都是0，跳过此对象
                        logger.debug(f"边界框高度为0，跳过: {bbox_data}")
                        continue
                    else:
                        # 交换坐标
                        y1, y2 = min(y1, y2), max(y1, y2)
                        logger.debug(
                            f"修复边界框 y 坐标: {bbox_data} -> [{x1}, {y1}, {x2}, {y2}]"
                        )

                # 确保坐标非负
                x1, y1, x2, y2 = max(0, x1), max(0, y1), max(0, x2), max(0, y2)

                try:
                    bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                except ValueError as e:
                    logger.warning(f"创建边界框失败: {e}, bbox_data={bbox_data}, 跳过此对象")
                    continue

                confidence = Confidence(obj_data.get("confidence", 0.0))

                domain_obj = DetectedObject(
                    class_id=obj_data["class_id"],
                    class_name=obj_data["class_name"],
                    confidence=confidence,
                    bbox=bbox,
                    track_id=obj_data.get("track_id"),
                    metadata=obj_data.get("metadata", {}),
                )
                domain_objects.append(domain_obj)

            # 3. 创建检测记录实体
            record = DetectionRecord(
                id=f"{camera_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                camera_id=camera_id,
                objects=domain_objects,
                timestamp=Timestamp.now(),
                processing_time=processing_time,
                frame_id=frame_id,
                region_id=camera.region_id,
            )

            if snapshots:
                record.add_metadata(
                    "snapshots",
                    [
                        {
                            "relative_path": info.relative_path,
                            "absolute_path": info.absolute_path,
                            "captured_at": info.captured_at.isoformat(),
                            "violation_type": info.violation_type,
                            "metadata": dict(info.metadata) if info.metadata else None,
                        }
                        for info in snapshots
                    ],
                )

            # 4. 分析检测质量
            quality_analysis = self.detection_service.analyze_detection_quality(record)
            record.add_metadata("quality_analysis", quality_analysis)

            # 5. 检测违规行为
            violations = self.violation_service.detect_violations(record)
            if violations:
                record.add_metadata("violations", [v.__dict__ for v in violations])
                record.add_metadata("violation_count", len(violations))

            # 6. 保存检测记录（先保存以获取数据库ID）
            saved_record_id = await self.detection_repository.save(record)

            # 7. 保存违规事件到violation_events表（如果有违规）
            if violations and self.violation_repository:
                for violation in violations:
                    try:
                        # 在violation的metadata中添加detection_id（字符串格式，用于记录）
                        if not violation.metadata:
                            violation.metadata = {}
                        violation.metadata["detection_id"] = saved_record_id

                        # 保存违规事件（传递detection_id，仓储会处理ID转换）
                        await self.violation_repository.save(
                            violation, detection_id=saved_record_id
                        )
                        logger.debug(
                            f"违规事件已保存: type={violation.violation_type.value}, "
                            f"camera={violation.camera_id}, detection_id={saved_record_id}"
                        )
                    except Exception as e:
                        logger.error(f"保存违规事件失败: {e}", exc_info=True)
                        # 不中断流程，继续处理其他违规

            # 8. 发布违规事件（如果有违规）
            if violations:
                for violation in violations:
                    event = ViolationDetectedEvent.from_violation(violation)
                    await self._publish_event(event)

            # 9. 发布检测创建事件
            detection_event = DetectionCreatedEvent.from_detection_record(record)
            await self._publish_event(detection_event)

            logger.info(
                f"检测记录已处理: {record.id}, 对象数: {record.object_count}, 违规数: {len(violations)}"
            )
            return record

        except Exception as e:
            logger.error(f"处理检测结果失败: {e}")
            raise

    async def get_detection_analytics(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取检测分析报告

        Args:
            camera_id: 摄像头ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            Dict[str, Any]: 分析报告
        """
        try:
            # 1. 获取检测记录
            if start_time and end_time:
                records = await self.detection_repository.find_by_time_range(
                    start_time, end_time, camera_id, limit=1000
                )
            elif camera_id:
                records = await self.detection_repository.find_by_camera_id(
                    camera_id, limit=1000
                )
            else:
                # 获取最近1小时的记录
                end_time = datetime.now(timezone.utc)
                from datetime import timedelta

                start_time = end_time - timedelta(hours=1)
                records = await self.detection_repository.find_by_time_range(
                    start_time, end_time, None, limit=1000
                )

            if not records:
                return {"total_records": 0, "message": "没有找到检测记录"}

            # 2. 计算统计信息
            stats = self.detection_service.calculate_detection_statistics(records)

            # 3. 检测异常
            anomalies = self.detection_service.detect_anomalies(records)

            # 4. 分析违规情况
            all_violations = []
            for record in records:
                violations = self.violation_service.detect_violations(record)
                all_violations.extend(violations)

            violation_stats = self.violation_service.get_violation_statistics(
                all_violations
            )

            # 5. 生成分析报告
            analytics = {
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None,
                    "duration_hours": (end_time - start_time).total_seconds() / 3600
                    if start_time and end_time
                    else None,
                },
                "detection_statistics": stats,
                "violation_statistics": violation_stats,
                "anomalies": anomalies,
                "quality_analysis": {
                    "excellent_quality": len(
                        [r for r in records if r.average_confidence >= 0.8]
                    ),
                    "good_quality": len(
                        [r for r in records if 0.6 <= r.average_confidence < 0.8]
                    ),
                    "fair_quality": len(
                        [r for r in records if 0.4 <= r.average_confidence < 0.6]
                    ),
                    "poor_quality": len(
                        [r for r in records if r.average_confidence < 0.4]
                    ),
                },
                "recommendations": self._generate_recommendations(
                    records, all_violations, anomalies
                ),
            }

            logger.info(
                f"检测分析报告已生成: {len(records)}条记录, {len(all_violations)}个违规, {len(anomalies)}个异常"
            )
            return analytics

        except Exception as e:
            logger.error(f"生成检测分析报告失败: {e}")
            raise

    async def get_camera_analytics(self, camera_id: str) -> Dict[str, Any]:
        """
        获取摄像头分析报告

        Args:
            camera_id: 摄像头ID

        Returns:
            Dict[str, Any]: 摄像头分析报告
        """
        try:
            # 1. 获取摄像头信息
            camera = await self.camera_repository.find_by_id(camera_id)
            if not camera:
                raise ValueError(f"摄像头不存在: {camera_id}")

            # 2. 获取最近的检测记录
            end_time = datetime.now(timezone.utc)
            from datetime import timedelta

            start_time = end_time - timedelta(hours=24)  # 最近24小时
            records = await self.detection_repository.find_by_time_range(
                start_time, end_time, camera_id, limit=1000
            )

            # 3. 计算摄像头统计
            camera_stats = {
                "camera_info": camera.get_status_info(),
                "detection_count_24h": len(records),
                "average_confidence": sum(r.average_confidence for r in records)
                / len(records)
                if records
                else 0,
                "total_objects_detected": sum(r.object_count for r in records),
                "person_count": sum(r.person_count for r in records),
                "vehicle_count": sum(r.vehicle_count for r in records),
            }

            # 4. 分析摄像头性能
            if records:
                processing_times = [
                    r.processing_time for r in records if r.processing_time > 0
                ]
                if processing_times:
                    avg_processing_time = sum(processing_times) / len(processing_times)
                    camera_stats["performance"] = {
                        "avg_processing_time": avg_processing_time,
                        "max_processing_time": max(processing_times),
                        "min_processing_time": min(processing_times),
                        "fps_estimate": 1.0 / avg_processing_time
                        if avg_processing_time > 0
                        else 0,
                    }
                else:
                    camera_stats["performance"] = {
                        "avg_processing_time": 0.0,
                        "max_processing_time": 0.0,
                        "min_processing_time": 0.0,
                        "fps_estimate": 0.0,
                    }

            # 5. 检测摄像头异常
            anomalies = self.detection_service.detect_anomalies(records)
            camera_stats["anomalies"] = anomalies

            logger.info(f"摄像头分析报告已生成: {camera_id}")
            return camera_stats

        except Exception as e:
            logger.error(f"生成摄像头分析报告失败: {e}")
            raise

    def _generate_recommendations(
        self,
        records: List[DetectionRecord],
        violations: List,
        anomalies: List[Dict[str, Any]],
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于检测质量
        poor_quality_count = len([r for r in records if r.average_confidence < 0.4])
        if poor_quality_count > len(records) * 0.3:
            recommendations.append("检测质量较低，建议检查摄像头位置和光照条件")

        # 基于违规情况
        if violations:
            recommendations.append(f"检测到{len(violations)}个违规行为，建议加强安全监管")

        # 基于异常情况
        if anomalies:
            recommendations.append(f"检测到{len(anomalies)}个异常情况，建议检查系统状态")

        # 基于检测频率
        if len(records) < 10:
            recommendations.append("检测频率较低，建议检查摄像头连接状态")

        return recommendations

    async def _publish_event(self, event) -> None:
        """发布领域事件"""
        try:
            # 这里可以集成事件总线，如Redis Pub/Sub、RabbitMQ等
            event_data = event.to_dict()
            logger.info(f"发布领域事件: {event_data['event_type']}")

            # 示例：可以发送到Redis
            # await self.redis_client.publish("domain_events", json.dumps(event_data))

        except Exception as e:
            logger.error(f"发布领域事件失败: {e}")

    async def get_domain_statistics(self) -> Dict[str, Any]:
        """获取领域模型统计信息"""
        try:
            # 获取所有摄像头
            cameras = await self.camera_repository.find_all()
            active_cameras = await self.camera_repository.find_active()

            # 获取检测记录统计
            detection_stats = await self.detection_repository.get_statistics()

            return {
                "cameras": {
                    "total": len(cameras),
                    "active": len(active_cameras),
                    "inactive": len(cameras) - len(active_cameras),
                },
                "detections": detection_stats,
                "domain_services": {
                    "detection_service": "已启用",
                    "violation_service": "已启用",
                },
            }

        except Exception as e:
            logger.error(f"获取领域统计信息失败: {e}")
            raise

    async def get_violation_details(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        获取违规明细（对仓储暴露的违规查询进行封装）。

        若当前仓储不支持违规查询，抛出异常交由上层回退。
        """
        try:
            repo = self.detection_repository
            if hasattr(repo, "get_violations") and callable(
                getattr(repo, "get_violations")
            ):
                return await getattr(repo, "get_violations")(
                    camera_id=camera_id,
                    status=status,
                    violation_type=violation_type,
                    limit=limit,
                    offset=offset,
                )
            raise NotImplementedError("当前仓储未实现违规明细查询")
        except Exception as e:
            logger.error(f"获取违规明细失败: {e}")
            raise

    async def get_detection_records_by_camera(
        self,
        camera_id: str,
        limit: int = 100,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        根据摄像头ID获取检测记录列表

        Args:
            camera_id: 摄像头ID
            limit: 返回记录数量
            offset: 偏移量
            start_time: 开始时间（可选，用于优化查询）
            end_time: 结束时间（可选，用于优化查询）

        Returns:
            Dict[str, Any]: 包含检测记录列表和总数等信息
        """
        try:
            # 完全移除COUNT查询，避免性能问题
            # 如果有时间范围，使用时间范围查询（更高效）
            if start_time and end_time:
                records = await self.detection_repository.find_by_time_range(
                    start_time=start_time,
                    end_time=end_time,
                    camera_id=camera_id,
                    limit=limit,
                    offset=offset,
                )
                # 对于时间范围查询，使用智能近似总数
                if len(records) == limit:
                    # 返回的记录数等于limit，说明可能还有更多数据
                    total = offset + len(records) + 1  # +1表示可能还有更多
                else:
                    # 返回的记录数小于limit，说明这是最后一页
                    total = offset + len(records)
            else:
                # 如果没有提供时间范围，默认查询最近1小时的数据，避免全表扫描
                # 这样可以大幅提升查询性能（减少到1小时，用户可以手动选择更长时间范围）
                if not start_time and not end_time:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=1)  # 改为1小时，大幅减少数据量
                    logger.debug(f"未提供时间范围，默认查询最近1小时: {start_time} to {end_time}")

                    records = await self.detection_repository.find_by_time_range(
                        start_time=start_time,
                        end_time=end_time,
                        camera_id=camera_id,
                        limit=limit,
                        offset=offset,
                    )
                else:
                    # 从仓储获取检测记录
                    records = await self.detection_repository.find_by_camera_id(
                        camera_id, limit=limit, offset=offset
                    )

                # 完全移除COUNT查询，使用智能近似值
                # 如果返回的记录数等于limit，说明可能还有更多数据
                if len(records) == limit:
                    # 返回的记录数等于limit，说明可能还有更多数据
                    total = offset + len(records) + 1  # +1表示可能还有更多
                else:
                    # 返回的记录数小于limit，说明这是最后一页
                    total = offset + len(records)

            # 转换为字典格式（兼容旧API响应结构）
            # 优化：减少不必要的对象属性访问，直接使用记录数据
            formatted_records = []
            for record in records:
                # 优化时间戳转换 - 直接获取datetime对象
                try:
                    if hasattr(record.timestamp, "value"):
                        ts_value = record.timestamp.value
                        if hasattr(ts_value, "isoformat"):
                            timestamp_str = ts_value.isoformat()
                        else:
                            timestamp_str = str(ts_value)
                    elif hasattr(record.timestamp, "iso_string"):
                        timestamp_str = record.timestamp.iso_string
                    else:
                        timestamp_str = str(record.timestamp)
                except Exception:
                    timestamp_str = str(record.timestamp)

                # 优化metadata访问 - 缓存结果
                metadata = record.metadata or {} if hasattr(record, "metadata") else {}

                # 优化person_count - 直接使用属性，避免重复计算
                person_count = (
                    record.person_count if hasattr(record, "person_count") else 0
                )

                formatted_records.append(
                    {
                        "id": str(record.id),
                        "camera_id": str(record.camera_id),
                        "timestamp": timestamp_str,
                        "frame_number": record.frame_id or 0
                        if hasattr(record, "frame_id")
                        else 0,
                        "person_count": person_count,
                        "hairnet_violations": metadata.get("hairnet_violations", 0)
                        if isinstance(metadata, dict)
                        else 0,
                        "handwash_events": metadata.get("handwash_events", 0)
                        if isinstance(metadata, dict)
                        else 0,
                        "sanitize_events": metadata.get("sanitize_events", 0)
                        if isinstance(metadata, dict)
                        else 0,
                        "fps": metadata.get("fps", 0.0)
                        if isinstance(metadata, dict)
                        else 0.0,
                        "processing_time": float(record.processing_time)
                        if hasattr(record, "processing_time")
                        else 0.0,
                    }
                )

            return {
                "records": formatted_records,
                "total": total,
                "camera_id": camera_id,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"获取检测记录失败: {e}")
            raise

    async def get_violation_by_id(self, violation_id: int) -> Optional[Dict[str, Any]]:
        """
        根据违规ID获取违规详情

        Args:
            violation_id: 违规ID

        Returns:
            Optional[Dict[str, Any]]: 违规详情，如果不存在则返回None
        """
        try:
            repo = self.detection_repository
            # 检查仓储是否支持违规查询
            if hasattr(repo, "get_violation_by_id") and callable(
                getattr(repo, "get_violation_by_id")
            ):
                return await getattr(repo, "get_violation_by_id")(violation_id)
            # 如果不支持，尝试通过get_violations查询
            if hasattr(repo, "get_violations") and callable(
                getattr(repo, "get_violations")
            ):
                # 查询所有违规记录，然后过滤
                violations_data = await getattr(repo, "get_violations")(
                    limit=1000, offset=0
                )
                violations = violations_data.get("violations", [])
                violation = next(
                    (v for v in violations if v.get("id") == violation_id), None
                )
                return violation
            raise NotImplementedError("当前仓储未实现违规查询")
        except Exception as e:
            logger.error(f"获取违规详情失败: {e}")
            raise

    async def get_daily_statistics(
        self, days: int = 7, camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        按天统计事件趋势

        Args:
            days: 要查询的最近天数
            camera_id: 摄像头ID（可选）

        Returns:
            List[Dict[str, Any]]: 每日统计信息列表
        """
        try:
            from datetime import timedelta

            # 计算时间范围
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            # 获取检测记录
            records = await self.detection_repository.find_by_time_range(
                start_time, end_time, camera_id, limit=10000
            )

            # 按天分组统计
            per_day: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
            total_day: Dict[str, int] = defaultdict(int)

            for record in records:
                # 获取日期字符串
                # timestamp 是 Timestamp 对象，需要获取 value 属性
                if hasattr(record.timestamp, "value"):
                    record_date = record.timestamp.value
                elif isinstance(record.timestamp, datetime):
                    record_date = record.timestamp
                else:
                    # 如果是其他格式，尝试转换
                    record_date = datetime.fromisoformat(str(record.timestamp))
                date_str = record_date.date().isoformat()

                # 统计对象类型
                for obj in record.objects:
                    # 兼容字典格式和对象格式
                    if isinstance(obj, dict):
                        class_name = obj.get("class_name", "unknown")
                    else:
                        class_name = obj.class_name
                    per_day[date_str][class_name] += 1

                total_day[date_str] += 1

            # 组装输出（按日期升序）
            today = end_time.date()
            out: List[Dict[str, Any]] = []
            for i in range(days - 1, -1, -1):
                date_str = (today - timedelta(days=i)).isoformat()
                out.append(
                    {
                        "date": date_str,
                        "total_events": total_day.get(date_str, 0),
                        "counts_by_type": dict(per_day.get(date_str, {})),
                    }
                )

            return out

        except Exception as e:
            logger.error(f"获取按天统计失败: {e}")
            raise

    async def get_event_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        查询事件列表，支持时间范围和多种过滤条件

        Args:
            start_time: 开始时间
            end_time: 结束时间
            event_type: 事件类型
            camera_id: 摄像头ID
            limit: 返回数量限制

        Returns:
            Dict[str, Any]: 包含事件列表的字典
        """
        try:
            from datetime import timedelta

            # 默认查询最近24小时
            if not end_time:
                end_time = datetime.now(timezone.utc)
            if not start_time:
                start_time = end_time - timedelta(hours=24)

            # 获取检测记录
            records = await self.detection_repository.find_by_time_range(
                start_time, end_time, camera_id, limit=limit * 2  # 获取更多记录以便过滤
            )

            # 转换为事件列表
            events = []
            for record in records:
                # 摄像头过滤
                if camera_id and record.camera_id != camera_id:
                    continue

                # 从检测记录生成事件
                # 注意：record.objects可能是字典列表（从数据库读取）或DetectedObject对象列表
                for obj in record.objects:
                    # 兼容字典格式和对象格式
                    if isinstance(obj, dict):
                        obj_class_name = obj.get("class_name", "unknown")
                        obj_confidence = obj.get("confidence", 0.0)
                        obj_track_id = obj.get("track_id")
                        obj_metadata = obj.get("metadata", {})
                    else:
                        # DetectedObject对象格式
                        obj_class_name = obj.class_name
                        obj_confidence = (
                            obj.confidence.value
                            if hasattr(obj.confidence, "value")
                            else obj.confidence
                        )
                        obj_track_id = obj.track_id
                        obj_metadata = obj.metadata or {}

                    # 事件类型过滤
                    if event_type and obj_class_name != event_type:
                        continue

                    # 获取时间戳（兼容Timestamp对象和datetime）
                    timestamp_str = (
                        record.timestamp.iso_string
                        if hasattr(record.timestamp, "iso_string")
                        else record.timestamp.isoformat()
                    )

                    events.append(
                        {
                            "id": f"{record.id}_{obj_track_id or ''}",
                            "timestamp": timestamp_str,
                            "type": obj_class_name,
                            "camera_id": record.camera_id,
                            "confidence": float(obj_confidence)
                            if obj_confidence is not None
                            else 0.0,
                            "track_id": obj_track_id,
                            "region": record.region_id,
                            "metadata": obj_metadata,
                        }
                    )

                    if len(events) >= limit:
                        break

                if len(events) >= limit:
                    break

            return {"events": events, "total": len(events)}

        except Exception as e:
            logger.error(f"获取事件列表失败: {e}")
            raise

    async def get_recent_history(
        self,
        minutes: int = 60,
        limit: int = 100,
        camera_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取近期事件历史

        Args:
            minutes: 要查询的最近分钟数
            limit: 返回事件的最大数量
            camera_id: 摄像头ID（可选）

        Returns:
            List[Dict[str, Any]]: 事件详细信息列表
        """
        try:
            from datetime import timedelta

            # 计算时间范围
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=minutes)

            # 获取检测记录
            records = await self.detection_repository.find_by_time_range(
                start_time, end_time, camera_id, limit=limit * 2
            )

            # 转换为事件列表（按时间倒序）
            events = []
            for record in sorted(
                records,
                key=lambda r: r.timestamp.value
                if hasattr(r.timestamp, "value")
                else r.timestamp,
                reverse=True,
            ):
                # 兼容字典格式和对象格式
                for obj in record.objects:
                    if isinstance(obj, dict):
                        obj_class_name = obj.get("class_name", "unknown")
                        obj_confidence = obj.get("confidence", 0.0)
                        obj_track_id = obj.get("track_id")
                        obj_metadata = obj.get("metadata", {})
                    else:
                        # DetectedObject对象格式
                        obj_class_name = obj.class_name
                        obj_confidence = (
                            obj.confidence.value
                            if hasattr(obj.confidence, "value")
                            else obj.confidence
                        )
                        obj_track_id = obj.track_id
                        obj_metadata = obj.metadata or {}

                    # 获取时间戳（兼容Timestamp对象和datetime）
                    timestamp_str = (
                        record.timestamp.iso_string
                        if hasattr(record.timestamp, "iso_string")
                        else record.timestamp.isoformat()
                    )

                    events.append(
                        {
                            "id": f"{record.id}_{obj_track_id or ''}",
                            "timestamp": timestamp_str,
                            "type": obj_class_name,
                            "camera_id": record.camera_id,
                            "confidence": float(obj_confidence)
                            if obj_confidence is not None
                            else 0.0,
                            "track_id": obj_track_id,
                            "region": record.region_id,
                            "metadata": obj_metadata,
                        }
                    )

                    if len(events) >= limit:
                        break

                if len(events) >= limit:
                    break

            return events

        except Exception as e:
            logger.error(f"获取近期历史失败: {e}")
            raise

    async def get_recent_events(
        self,
        limit: int = 100,
        minutes: int = 60,
        event_type: Optional[str] = None,
        camera_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取最近的事件列表（适配 /api/v1/events/recent 端点）

        Args:
            limit: 返回事件的最大数量
            minutes: 要查询的最近分钟数
            event_type: 事件类型过滤（可选）
            camera_id: 摄像头ID过滤（可选）

        Returns:
            List[Dict[str, Any]]: 事件列表，格式兼容旧实现
        """
        try:
            from datetime import timedelta

            # 计算时间范围
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=minutes)

            # 获取检测记录
            records = await self.detection_repository.find_by_time_range(
                start_time, end_time, camera_id, limit=limit * 2
            )

            # 转换为事件列表（按时间倒序，兼容旧格式）
            events = []
            for record in sorted(
                records,
                key=lambda r: r.timestamp.value
                if hasattr(r.timestamp, "value")
                else r.timestamp,
                reverse=True,
            ):
                # 摄像头过滤
                if camera_id and record.camera_id != camera_id:
                    continue

                for obj in record.objects:
                    # 兼容字典格式和对象格式
                    if isinstance(obj, dict):
                        obj_class_name = obj.get("class_name", "unknown")
                        obj_confidence = obj.get("confidence", 0.0)
                        obj_track_id = obj.get("track_id")
                        obj_bbox = obj.get("bbox", [])
                        obj_metadata = obj.get("metadata", {})
                    else:
                        # DetectedObject对象格式
                        obj_class_name = obj.class_name
                        obj_confidence = (
                            obj.confidence.value
                            if hasattr(obj.confidence, "value")
                            else obj.confidence
                        )
                        obj_track_id = obj.track_id
                        obj_bbox = obj.bbox
                        obj_metadata = obj.metadata or {}

                    # 事件类型过滤
                    if event_type and obj_class_name != event_type:
                        continue

                    # 获取时间戳（兼容Timestamp对象和datetime）
                    timestamp_value = (
                        record.timestamp.value
                        if hasattr(record.timestamp, "value")
                        else record.timestamp
                    )
                    ts = (
                        timestamp_value.timestamp()
                        if hasattr(timestamp_value, "timestamp")
                        else float(timestamp_value)
                    )

                    # 处理bbox（兼容BoundingBox对象和列表）
                    bbox_list = None
                    if obj_bbox:
                        if hasattr(obj_bbox, "x1"):
                            # BoundingBox对象
                            bbox_list = [
                                obj_bbox.x1,
                                obj_bbox.y1,
                                obj_bbox.x2,
                                obj_bbox.y2,
                            ]
                        elif isinstance(obj_bbox, (list, tuple)) and len(obj_bbox) >= 4:
                            # 列表格式
                            bbox_list = list(obj_bbox[:4])

                    # 转换为旧API格式（兼容events_record.jsonl格式）
                    events.append(
                        {
                            "ts": ts,
                            "type": obj_class_name,
                            "camera_id": record.camera_id,
                            "track_id": obj_track_id,
                            "evidence": {
                                "confidence": float(obj_confidence)
                                if obj_confidence is not None
                                else 0.0,
                                "region": record.region_id,
                                "bbox": bbox_list,
                                **obj_metadata,
                            },
                        }
                    )

                    if len(events) >= limit:
                        break

                if len(events) >= limit:
                    break

            return events

        except Exception as e:
            logger.error(f"获取最近事件失败: {e}")
            raise

    async def get_realtime_statistics(self) -> Dict[str, Any]:
        """
        获取实时统计信息（基于领域服务数据）

        Returns:
            Dict[str, Any]: 实时统计数据
        """
        try:
            from datetime import timedelta

            # 获取最近1小时的记录
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            # 获取检测记录
            records = await self.detection_repository.find_by_time_range(
                start_time, end_time, None, limit=1000
            )

            # 计算实时统计
            total_detections = len(records)
            violation_count = 0
            handwashing_detections = 0
            disinfection_detections = 0
            hairnet_detections = 0

            # 统计各类检测
            for record in records:
                # 统计违规
                violations = record.metadata.get("violations", [])
                if violations:
                    violation_count += len(violations)

                # 统计各类检测事件
                for obj in record.objects:
                    # 兼容字典格式和对象格式
                    if isinstance(obj, dict):
                        obj_class_name = obj.get("class_name", "unknown").lower()
                    else:
                        obj_class_name = obj.class_name.lower()

                    if obj_class_name in ["handwash", "handwashing"]:
                        handwashing_detections += 1
                    elif obj_class_name in ["sanitize", "disinfection"]:
                        disinfection_detections += 1
                    elif obj_class_name in ["hairnet", "person"]:
                        hairnet_detections += 1

            # 计算平均处理时间
            if records:
                avg_processing_time = sum(r.processing_time for r in records) / len(
                    records
                )
            else:
                avg_processing_time = 0.0

            # 获取活跃摄像头数
            active_cameras = await self.camera_repository.find_active()
            active_regions = set()
            for camera in active_cameras:
                if camera.region_id:
                    active_regions.add(camera.region_id)

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_status": "active",
                "detection_stats": {
                    "total_detections_today": total_detections,
                    "handwashing_detections": handwashing_detections,
                    "disinfection_detections": disinfection_detections,
                    "hairnet_detections": hairnet_detections,
                    "violation_count": violation_count,
                },
                "region_stats": {
                    "active_regions": len(active_regions),
                    "monitored_areas": list(active_regions),
                },
                "performance_metrics": {
                    "average_processing_time": avg_processing_time,
                    "detection_accuracy": (
                        sum(
                            r.average_confidence
                            if hasattr(r, "average_confidence")
                            else (
                                r.confidence.value
                                if hasattr(r, "confidence")
                                and hasattr(r.confidence, "value")
                                else 0.0
                            )
                            for r in records
                        )
                        / len(records)
                        if records
                        else 0.0
                    ),
                    "system_uptime": "N/A",  # 需要从系统层面获取
                },
                "alerts": {
                    "active_alerts": 0,  # 需要从告警系统获取
                    "recent_violations": [],
                },
            }

        except Exception as e:
            logger.error(f"获取实时统计失败: {e}")
            raise

    async def get_cameras(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        获取摄像头列表

        Args:
            active_only: 是否只返回活跃摄像头

        Returns:
            List[Dict[str, Any]]: 摄像头列表
        """
        try:
            if active_only:
                cameras = await self.camera_repository.find_active()
            else:
                cameras = await self.camera_repository.find_all()

            # 转换为字典格式（兼容旧API响应结构）
            formatted_cameras = []
            for camera in cameras:
                formatted_cameras.append(
                    {
                        "id": camera.id,
                        "name": camera.name,
                        "source": camera.metadata.get("source", ""),
                        "status": camera.status.value,
                        "location": camera.location,
                        "resolution": f"{camera.resolution[0]}x{camera.resolution[1]}"
                        if camera.resolution
                        else "1920x1080",
                        "fps": camera.fps or 25,
                        "region_id": camera.region_id,
                        "is_active": camera.is_active,
                        **camera.metadata,  # 包含其他元数据
                    }
                )

            return formatted_cameras

        except Exception as e:
            logger.error(f"获取摄像头列表失败: {e}")
            raise

    async def get_camera_stats_detailed(self, camera_id: str) -> Dict[str, Any]:
        """
        获取摄像头详细统计信息（整合get_camera_analytics和实时数据）

        Args:
            camera_id: 摄像头ID

        Returns:
            Dict[str, Any]: 摄像头统计信息
        """
        try:
            # 使用已有的get_camera_analytics方法
            analytics = await self.get_camera_analytics(camera_id)

            # 从analytics中提取数据（get_camera_analytics返回的结构）
            camera_info = analytics.get("camera_info", {})
            stats_data = {
                "total_frames": 0,
                "processed_frames": analytics.get("total_objects_detected", 0),
                "detected_persons": analytics.get("person_count", 0),
                "detected_hairnets": analytics.get("total_hairnet_violations", 0),
                "detected_handwash": analytics.get("total_handwash_events", 0),
                "avg_fps": 0.0,
                "avg_detection_time": 0.0,
                "last_detection_time": None,
            }

            # 如果performance信息存在，更新相关字段
            if "performance" in analytics:
                perf = analytics["performance"]
                stats_data["avg_fps"] = perf.get("fps_estimate", 0.0)
                stats_data["avg_detection_time"] = perf.get("avg_processing_time", 0.0)

            # 转换为旧API响应结构
            stats_response = {
                "camera_id": camera_id,
                "running": camera_info.get("is_active", True),
                "pid": 0,
                "log_file": "",
                "stats": stats_data,
            }

            return stats_response

        except Exception as e:
            logger.error(f"获取摄像头统计失败: {e}")
            raise

    async def get_all_cameras_summary(
        self,
        period: str = "7d",
    ) -> Dict[str, Any]:
        """
        获取所有摄像头的统计摘要

        Args:
            period: 时间段（1d, 7d, 30d）

        Returns:
            Dict[str, Any]: 所有摄像头的统计摘要
        """
        try:
            from datetime import timedelta

            # 计算时间范围
            end_time = datetime.now(timezone.utc)
            if period == "1d":
                start_time = end_time - timedelta(days=1)
            elif period == "7d":
                start_time = end_time - timedelta(days=7)
            elif period == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)

            # 获取所有摄像头
            cameras = await self.camera_repository.find_all()
            camera_ids = [c.id for c in cameras]

            # 查询每个摄像头的统计
            summary = {}
            total_stats = {
                "total_frames": 0,
                "total_persons": 0,
                "total_hairnet_violations": 0,
                "total_handwash_events": 0,
                "total_sanitize_events": 0,
                "avg_fps": 0.0,
                "avg_processing_time": 0.0,
            }

            for camera_id in camera_ids:
                try:
                    analytics = await self.get_camera_analytics(camera_id)
                    # 转换为旧API响应结构
                    stats = {
                        "total_frames": analytics.get("total_objects_detected", 0),
                        "total_persons": analytics.get("person_count", 0),
                        "total_hairnet_violations": analytics.get(
                            "total_hairnet_violations", 0
                        ),
                        "total_handwash_events": analytics.get(
                            "total_handwash_events", 0
                        ),
                        "total_sanitize_events": analytics.get(
                            "total_sanitize_events", 0
                        ),
                        "avg_fps": analytics.get("performance", {}).get(
                            "fps_estimate", 0.0
                        ),
                        "avg_processing_time": analytics.get("performance", {}).get(
                            "avg_processing_time", 0.0
                        ),
                    }
                    summary[camera_id] = stats

                    # 累加到总计
                    total_stats["total_frames"] += stats["total_frames"]
                    total_stats["total_persons"] += stats["total_persons"]
                    total_stats["total_hairnet_violations"] += stats[
                        "total_hairnet_violations"
                    ]
                    total_stats["total_handwash_events"] += stats[
                        "total_handwash_events"
                    ]
                    total_stats["total_sanitize_events"] += stats[
                        "total_sanitize_events"
                    ]
                    # FPS和processing_time取平均值（如果有数据）
                    if len(camera_ids) > 0:
                        total_stats["avg_fps"] = (
                            total_stats["avg_fps"] + stats["avg_fps"]
                        ) / len(camera_ids)
                        total_stats["avg_processing_time"] = (
                            total_stats["avg_processing_time"]
                            + stats["avg_processing_time"]
                        ) / len(camera_ids)

                except Exception as e:
                    logger.warning(f"获取摄像头统计失败 {camera_id}: {e}")
                    summary[camera_id] = {
                        "total_frames": 0,
                        "total_persons": 0,
                        "total_hairnet_violations": 0,
                        "total_handwash_events": 0,
                        "total_sanitize_events": 0,
                        "avg_fps": 0.0,
                        "avg_processing_time": 0.0,
                    }

            return {
                "period": period,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "cameras": summary,
                "total": total_stats,
            }

        except Exception as e:
            logger.error(f"获取所有摄像头统计摘要失败: {e}")
            raise

    async def update_violation_status(
        self,
        violation_id: int,
        status: str,
        notes: Optional[str] = None,
        handled_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新违规状态（写操作，需要谨慎处理）

        Args:
            violation_id: 违规ID
            status: 新状态（pending, confirmed, false_positive, resolved）
            notes: 备注信息（可选）
            handled_by: 处理人（可选）

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证状态值
            valid_statuses = ["pending", "confirmed", "false_positive", "resolved"]
            if status not in valid_statuses:
                raise ValueError(f"无效的状态值，必须是: {', '.join(valid_statuses)}")

            # 检查仓储是否支持违规状态更新
            repo = self.detection_repository
            if hasattr(repo, "update_violation_status") and callable(
                getattr(repo, "update_violation_status")
            ):
                # 如果仓储支持直接更新
                success = await getattr(repo, "update_violation_status")(
                    violation_id, status, notes, handled_by
                )
                if success:
                    logger.info(f"违规状态已更新: {violation_id} -> {status}")
                    return {"ok": True, "violation_id": violation_id, "status": status}
                else:
                    raise ValueError(f"违规记录不存在或更新失败: {violation_id}")
            else:
                # 如果不支持，需要通过DatabaseService更新
                # 这需要注入DatabaseService，但为了保持架构清晰，我们暂时抛出异常让上层回退
                # 未来可以考虑创建一个专门的ViolationRepository接口
                raise NotImplementedError("当前仓储未实现违规状态更新，请通过force_domain=false使用旧实现")

        except Exception as e:
            logger.error(f"更新违规状态失败: {e}")
            raise


# 全局服务实例（单例模式）
_detection_service_domain_instance: Optional[DetectionServiceDomain] = None


class DefaultCameraRepository(ICameraRepository):
    """简化的摄像头仓储默认实现（内存），用于试点灰度阶段。"""

    def __init__(self):
        self._store: Dict[str, Camera] = {}

    async def save(self, camera: Camera) -> str:
        self._store[camera.id] = camera
        return camera.id

    async def find_by_id(self, camera_id: str) -> Optional[Camera]:
        if camera_id in self._store:
            return self._store[camera_id]
        # 创建一个最小可用的占位摄像头，避免调用方失败
        cam = Camera(
            id=camera_id,
            name=camera_id,
            location="unknown",
            status=CameraStatus.ACTIVE,
            camera_type=CameraType.FIXED,
            resolution=(1920, 1080),
            fps=25,
            region_id=None,
        )
        # 不缓存占位，按需返回
        return cam

    async def find_by_region_id(self, region_id: str) -> List[Camera]:
        return [c for c in self._store.values() if c.region_id == region_id]

    async def find_all(self) -> List[Camera]:
        return list(self._store.values())

    async def find_active(self) -> List[Camera]:
        return [c for c in self._store.values() if c.is_active]

    async def count(self) -> int:
        return len(self._store)

    async def delete_by_id(self, camera_id: str) -> bool:
        return self._store.pop(camera_id, None) is not None

    async def exists(self, camera_id: str) -> bool:
        return camera_id in self._store


def get_detection_service_domain() -> DetectionServiceDomain:
    """
    获取领域模型检测服务实例（单例模式）

    Returns:
        DetectionServiceDomain: 领域模型检测服务实例
    """
    global _detection_service_domain_instance

    if _detection_service_domain_instance is None:
        # 直接通过工厂创建检测记录仓储；摄像头仓储采用默认内存实现
        detection_repo = RepositoryFactory.create_repository_from_env()
        camera_repo = DefaultCameraRepository()

        # 创建违规仓储
        violation_repo = None
        try:
            from src.infrastructure.repositories.postgresql_violation_repository import (
                PostgreSQLViolationRepository,
            )

            # 使用连接字符串创建违规仓储（会自动创建连接池）
            violation_repo = PostgreSQLViolationRepository(connection_string=None)
            logger.info("违规仓储已创建")
        except Exception as e:
            logger.warning(f"创建违规仓储失败: {e}，将不使用违规仓储")

        _detection_service_domain_instance = DetectionServiceDomain(
            detection_repository=detection_repo,
            camera_repository=camera_repo,
            violation_repository=violation_repo,
        )
        logger.info("领域模型检测服务单例已创建 (工厂+默认摄像头仓储+违规仓储)")

    return _detection_service_domain_instance

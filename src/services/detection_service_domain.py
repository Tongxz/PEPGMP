"""
使用领域模型的检测服务
演示如何使用领域驱动设计重构现有服务
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional


from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.events.detection_events import (
    DetectionCreatedEvent,
    ViolationDetectedEvent,
)
from src.domain.repositories.camera_repository import ICameraRepository
from src.domain.repositories.detection_repository import IDetectionRepository
from src.domain.services.detection_service import DetectionService
from src.domain.services.violation_service import ViolationService
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp

logger = logging.getLogger(__name__)


class DetectionServiceDomain:
    """使用领域模型的检测服务"""

    def __init__(
        self,
        detection_repository: IDetectionRepository,
        camera_repository: ICameraRepository,
    ):
        """
        初始化检测服务

        Args:
            detection_repository: 检测记录仓储
            camera_repository: 摄像头仓储
        """
        self.detection_repository = detection_repository
        self.camera_repository = camera_repository
        self.detection_service = DetectionService()
        self.violation_service = ViolationService()

        logger.info("领域模型检测服务初始化完成")

    async def process_detection(
        self,
        camera_id: str,
        detected_objects: List[Dict[str, Any]],
        processing_time: float,
        frame_id: Optional[int] = None,
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
                bbox = BoundingBox(
                    x1=obj_data["bbox"][0],
                    y1=obj_data["bbox"][1],
                    x2=obj_data["bbox"][2],
                    y2=obj_data["bbox"][3],
                )
                confidence = Confidence(obj_data["confidence"])

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
                id=f"{camera_id}_{int(datetime.now().timestamp() * 1000)}",
                camera_id=camera_id,
                objects=domain_objects,
                timestamp=Timestamp.now(),
                processing_time=processing_time,
                frame_id=frame_id,
                region_id=camera.region_id,
            )

            # 4. 分析检测质量
            quality_analysis = self.detection_service.analyze_detection_quality(record)
            record.add_metadata("quality_analysis", quality_analysis)

            # 5. 检测违规行为
            violations = self.violation_service.detect_violations(record)
            if violations:
                record.add_metadata("violations", [v.__dict__ for v in violations])
                record.add_metadata("violation_count", len(violations))

                # 发布违规事件
                for violation in violations:
                    event = ViolationDetectedEvent.from_violation(violation)
                    await self._publish_event(event)

            # 6. 保存检测记录
            await self.detection_repository.save(record)

            # 7. 发布检测创建事件
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
                end_time = datetime.now()
                start_time = datetime.now().replace(hour=end_time.hour - 1)
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
            end_time = datetime.now()
            start_time = datetime.now().replace(hour=end_time.hour - 24)  # 最近24小时
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
                processing_times = [r.processing_time for r in records]
                camera_stats["performance"] = {
                    "avg_processing_time": sum(processing_times)
                    / len(processing_times),
                    "max_processing_time": max(processing_times),
                    "min_processing_time": min(processing_times),
                    "fps_estimate": 1.0
                    / (sum(processing_times) / len(processing_times))
                    if processing_times
                    else 0,
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


# 全局服务实例（单例模式）
_detection_service_domain_instance: Optional[DetectionServiceDomain] = None


def get_detection_service_domain() -> DetectionServiceDomain:
    """
    获取领域模型检测服务实例（单例模式）

    Returns:
        DetectionServiceDomain: 领域模型检测服务实例
    """
    global _detection_service_domain_instance

    if _detection_service_domain_instance is None:
        # 这里需要注入实际的仓储实现
        # 示例：使用依赖注入容器
        from src.di.container import get_container

        container = get_container()

        detection_repo = container.get(IDetectionRepository)
        camera_repo = container.get(ICameraRepository)

        _detection_service_domain_instance = DetectionServiceDomain(
            detection_repository=detection_repo, camera_repository=camera_repo
        )
        logger.info("领域模型检测服务单例已创建")

    return _detection_service_domain_instance

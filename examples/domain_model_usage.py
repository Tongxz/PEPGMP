"""
领域模型使用示例
演示如何使用领域驱动设计重构后的系统

使用方法:
    python -m examples.domain_model_usage
"""

import asyncio

# 设置日志
import logging

# 导入领域模型
from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.events.detection_events import (
    DetectionCreatedEvent,
    ViolationDetectedEvent,
)
from src.domain.services.detection_service import DetectionService
from src.domain.services.violation_service import ViolationService
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_domain_models():
    """演示领域模型的使用"""
    logger.info("🚀 开始领域模型使用演示")

    # 1. 创建摄像头实体
    logger.info("\n📹 1. 创建摄像头实体")
    camera = Camera(
        id="cam_001",
        name="主入口摄像头",
        location="大楼主入口",
        status=CameraStatus.ACTIVE,
        camera_type=CameraType.PTZ,
        resolution=(1920, 1080),
        fps=30,
        region_id="region_001",
    )

    # 激活摄像头
    camera.activate()
    logger.info(f"摄像头创建完成: {camera}")
    logger.info(f"摄像头能力: {camera.get_capabilities()}")

    # 2. 创建检测对象
    logger.info("\n🎯 2. 创建检测对象")

    # 创建人体检测对象
    person_bbox = BoundingBox(100, 150, 200, 300)
    person_confidence = Confidence(0.85)
    person_obj = DetectedObject(
        class_id=0,
        class_name="person",
        confidence=person_confidence,
        bbox=person_bbox,
        track_id=123,
        metadata={"age_estimate": "adult", "gender": "unknown"},
    )

    # 创建车辆检测对象
    vehicle_bbox = BoundingBox(300, 200, 450, 350)
    vehicle_confidence = Confidence(0.92)
    vehicle_obj = DetectedObject(
        class_id=2,
        class_name="car",
        confidence=vehicle_confidence,
        bbox=vehicle_bbox,
        track_id=124,
        metadata={"color": "white", "type": "sedan"},
    )

    logger.info(f"人体对象: {person_obj}")
    logger.info(f"车辆对象: {vehicle_obj}")
    logger.info(f"人体对象是否为高置信度: {person_obj.is_high_confidence}")
    logger.info(f"车辆对象面积: {vehicle_obj.area:.0f} 像素²")

    # 3. 创建检测记录
    logger.info("\n📋 3. 创建检测记录")
    detection_record = DetectionRecord(
        id="det_001",
        camera_id=camera.id,
        objects=[person_obj, vehicle_obj],
        processing_time=0.15,
        frame_id=1001,
        region_id=camera.region_id,
    )

    logger.info(f"检测记录创建完成: {detection_record}")
    logger.info(f"检测对象数量: {detection_record.object_count}")
    logger.info(f"人体数量: {detection_record.person_count}")
    logger.info(f"车辆数量: {detection_record.vehicle_count}")
    logger.info(f"平均置信度: {detection_record.average_confidence:.3f}")

    # 4. 使用检测领域服务
    logger.info("\n🔍 4. 使用检测领域服务")
    detection_service = DetectionService()

    # 分析检测质量
    quality_analysis = detection_service.analyze_detection_quality(detection_record)
    logger.info(f"检测质量分析: {quality_analysis}")

    # 计算检测统计
    records = [detection_record]
    stats = detection_service.calculate_detection_statistics(records)
    logger.info(f"检测统计信息: {stats}")

    # 5. 使用违规检测服务
    logger.info("\n⚠️ 5. 使用违规检测服务")
    violation_service = ViolationService()

    # 检测违规行为
    violations = violation_service.detect_violations(detection_record)
    logger.info(f"检测到违规数量: {len(violations)}")

    for i, violation in enumerate(violations, 1):
        logger.info(
            f"违规 {i}: {violation.violation_type.value} - {violation.description}"
        )
        logger.info(f"严重程度: {violation.severity.value}")
        logger.info(f"置信度: {violation.confidence.value:.3f}")

    # 6. 创建领域事件
    logger.info("\n📡 6. 创建领域事件")

    # 检测创建事件
    detection_event = DetectionCreatedEvent.from_detection_record(detection_record)
    logger.info(f"检测创建事件: {detection_event.to_dict()}")

    # 违规检测事件
    if violations:
        violation_event = ViolationDetectedEvent.from_violation(violations[0])
        logger.info(f"违规检测事件: {violation_event.to_dict()}")

    # 7. 演示值对象操作
    logger.info("\n🔧 7. 演示值对象操作")

    # 边界框操作
    logger.info("边界框操作:")
    logger.info(f"原始边界框: {person_bbox}")
    logger.info(f"中心点: {person_bbox.center}")
    logger.info(f"面积: {person_bbox.area}")
    logger.info(f"宽高比: {person_bbox.aspect_ratio:.2f}")

    # 缩放边界框
    scaled_bbox = person_bbox.scale(1.5, 1.5)
    logger.info(f"缩放后边界框: {scaled_bbox}")

    # 计算IoU
    iou = person_bbox.calculate_iou(vehicle_bbox)
    logger.info(f"人体与车辆IoU: {iou:.3f}")

    # 置信度操作
    logger.info("\n置信度操作:")
    conf1 = Confidence(0.7)
    conf2 = Confidence(0.3)
    logger.info(f"置信度1: {conf1}")
    logger.info(f"置信度2: {conf2}")
    logger.info(f"置信度1 + 置信度2: {conf1 + conf2}")
    logger.info(f"置信度1 * 置信度2: {conf1 * conf2}")
    logger.info(f"置信度1 > 置信度2: {conf1 > conf2}")

    # 时间戳操作
    logger.info("\n时间戳操作:")
    timestamp1 = Timestamp.now()
    timestamp2 = timestamp1.add_minutes(5)
    logger.info(f"当前时间: {timestamp1}")
    logger.info(f"5分钟后: {timestamp2}")
    logger.info(f"时间差: {timestamp2.time_difference(timestamp1):.1f} 秒")
    logger.info(
        f"是否为同一时间(误差1秒): {timestamp1.is_same_time(timestamp2, tolerance_seconds=1)}"
    )

    # 8. 演示业务逻辑
    logger.info("\n💼 8. 演示业务逻辑")

    # 检测对象跟踪
    logger.info("对象跟踪演示:")
    logger.info(f"人体对象跟踪ID: {person_obj.track_id}")
    logger.info(f"是否为跟踪对象: {person_obj.track_id is not None}")

    # 检测记录质量分析
    logger.info("\n检测记录质量分析:")
    logger.info(f"是否有违规: {detection_record.has_violations}")
    logger.info(f"违规类型: {detection_record.violation_types}")
    logger.info(f"高置信度对象数: {len(detection_record.high_confidence_objects)}")
    logger.info(f"中等置信度对象数: {len(detection_record.medium_confidence_objects)}")
    logger.info(f"低置信度对象数: {len(detection_record.low_confidence_objects)}")

    # 9. 演示数据转换
    logger.info("\n🔄 9. 演示数据转换")

    # 转换为字典
    record_dict = detection_record.to_dict()
    logger.info(f"检测记录字典键: {list(record_dict.keys())}")

    # 从字典创建
    new_record = DetectionRecord.from_dict(record_dict)
    logger.info(f"从字典创建的记录: {new_record}")

    # 10. 演示异常检测
    logger.info("\n🚨 10. 演示异常检测")

    # 创建多个检测记录用于异常检测
    records_for_anomaly = []
    for i in range(5):
        record = DetectionRecord(
            id=f"det_{i:03d}",
            camera_id=camera.id,
            objects=[person_obj] if i % 2 == 0 else [],
            processing_time=0.1 + i * 0.05,
            frame_id=1000 + i,
        )
        records_for_anomaly.append(record)

    # 检测异常
    anomalies = detection_service.detect_anomalies(records_for_anomaly)
    logger.info(f"检测到异常数量: {len(anomalies)}")

    for i, anomaly in enumerate(anomalies, 1):
        logger.info(f"异常 {i}: {anomaly['type']} - 严重程度: {anomaly['severity']}")

    logger.info("\n✅ 领域模型使用演示完成！")

    return {
        "camera": camera,
        "detection_record": detection_record,
        "violations": violations,
        "quality_analysis": quality_analysis,
        "statistics": stats,
        "anomalies": anomalies,
    }


async def demo_domain_service_integration():
    """演示领域服务集成"""
    logger.info("\n🔗 开始领域服务集成演示")

    # 创建检测服务
    detection_service = DetectionService()
    violation_service = ViolationService()

    # 模拟检测记录序列
    records = []
    for i in range(10):
        # 创建模拟检测对象
        bbox = BoundingBox(100 + i * 10, 150, 200 + i * 10, 300)
        confidence = Confidence(0.6 + i * 0.03)
        obj = DetectedObject(
            class_id=0,
            class_name="person",
            confidence=confidence,
            bbox=bbox,
            track_id=100 + i,
        )

        record = DetectionRecord(
            id=f"batch_det_{i:03d}",
            camera_id="cam_001",
            objects=[obj],
            processing_time=0.1 + i * 0.01,
            frame_id=2000 + i,
        )
        records.append(record)

    # 分析检测质量
    logger.info("批量检测质量分析:")
    for record in records:
        quality = detection_service.analyze_detection_quality(record)
        logger.info(
            f"记录 {record.id}: 质量={quality['overall_quality']}, 置信度={quality['confidence_score']:.3f}"
        )

    # 检测违规
    logger.info("\n批量违规检测:")
    all_violations = []
    for record in records:
        violations = violation_service.detect_violations(record)
        all_violations.extend(violations)
        if violations:
            logger.info(f"记录 {record.id}: 检测到 {len(violations)} 个违规")

    # 违规统计
    violation_stats = violation_service.get_violation_statistics(all_violations)
    logger.info(f"违规统计: {violation_stats}")

    # 检测异常
    anomalies = detection_service.detect_anomalies(records)
    logger.info(f"检测到 {len(anomalies)} 个异常")

    # 生成建议
    recommendations = []
    if len(all_violations) > 0:
        recommendations.append(f"检测到{len(all_violations)}个违规行为，建议加强安全监管")
    if len(anomalies) > 0:
        recommendations.append(f"检测到{len(anomalies)}个异常情况，建议检查系统状态")

    logger.info(f"改进建议: {recommendations}")

    logger.info("✅ 领域服务集成演示完成！")


def main():
    """主函数"""
    logger.info("🎯 领域模型使用示例")
    logger.info("=" * 50)

    # 运行演示
    result = asyncio.run(demo_domain_models())
    asyncio.run(demo_domain_service_integration())

    logger.info("\n📊 演示结果摘要:")
    logger.info(f"- 摄像头: {result['camera'].name}")
    logger.info(f"- 检测记录: {result['detection_record'].id}")
    logger.info(f"- 检测对象数: {result['detection_record'].object_count}")
    logger.info(f"- 违规数量: {len(result['violations'])}")
    logger.info(f"- 异常数量: {len(result['anomalies'])}")
    logger.info(f"- 检测质量: {result['quality_analysis']['overall_quality']}")


if __name__ == "__main__":
    main()

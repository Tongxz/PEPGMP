"""
违规检测领域服务
包含违规检测相关的业务逻辑
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Tuple

from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence

logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """违规类型枚举"""

    NO_SAFETY_HELMET = "no_safety_helmet"  # 未戴安全帽
    NO_SAFETY_VEST = "no_safety_vest"  # 未穿安全背心
    UNAUTHORIZED_ACCESS = "unauthorized_access"  # 未授权进入
    IMPROPER_POSTURE = "improper_posture"  # 姿势不当
    EQUIPMENT_MISUSE = "equipment_misuse"  # 设备误用
    CROWDING = "crowding"  # 人员聚集
    SPEEDING = "speeding"  # 超速
    WRONG_DIRECTION = "wrong_direction"  # 逆行


class ViolationSeverity(Enum):
    """违规严重程度枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Violation:
    """违规记录"""

    id: str
    violation_type: ViolationType
    severity: ViolationSeverity
    camera_id: str
    detected_object: DetectedObject
    timestamp: datetime
    confidence: Confidence
    description: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ViolationService:
    """违规检测领域服务"""

    def __init__(self):
        """初始化违规检测服务"""
        self.logger = logging.getLogger(__name__)
        self.violation_rules = self._initialize_violation_rules()

    def _initialize_violation_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化违规检测规则"""
        return {
            "no_safety_helmet": {
                "min_confidence": 0.7,
                "required_objects": ["person"],
                "forbidden_objects": ["helmet", "hard_hat"],
                "severity": ViolationSeverity.HIGH,
                "description": "检测到未戴安全帽的人员",
            },
            "no_safety_vest": {
                "min_confidence": 0.6,
                "required_objects": ["person"],
                "forbidden_objects": ["safety_vest", "reflective_vest"],
                "severity": ViolationSeverity.MEDIUM,
                "description": "检测到未穿安全背心的人员",
            },
            "unauthorized_access": {
                "min_confidence": 0.8,
                "required_objects": ["person"],
                "restricted_areas": ["construction_zone", "danger_zone"],
                "severity": ViolationSeverity.CRITICAL,
                "description": "检测到未授权进入限制区域",
            },
            "crowding": {
                "min_confidence": 0.5,
                "min_person_count": 5,
                "max_area_per_person": 2.0,  # 平方米
                "severity": ViolationSeverity.MEDIUM,
                "description": "检测到人员过度聚集",
            },
            "speeding": {
                "min_confidence": 0.7,
                "max_speed": 5.0,  # 米/秒
                "required_objects": ["person", "vehicle"],
                "severity": ViolationSeverity.HIGH,
                "description": "检测到超速行为",
            },
        }

    def detect_violations(self, record: DetectionRecord) -> List[Violation]:
        """
        检测违规行为

        Args:
            record: 检测记录

        Returns:
            List[Violation]: 违规记录列表
        """
        violations = []

        for rule_name, rule_config in self.violation_rules.items():
            rule_violations = self._check_violation_rule(record, rule_name, rule_config)
            violations.extend(rule_violations)

        return violations

    def _check_violation_rule(
        self, record: DetectionRecord, rule_name: str, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查特定违规规则"""
        violations = []

        try:
            if rule_name == "no_safety_helmet":
                violations.extend(self._check_no_safety_helmet(record, rule_config))
            elif rule_name == "no_safety_vest":
                violations.extend(self._check_no_safety_vest(record, rule_config))
            elif rule_name == "unauthorized_access":
                violations.extend(self._check_unauthorized_access(record, rule_config))
            elif rule_name == "crowding":
                violations.extend(self._check_crowding(record, rule_config))
            elif rule_name == "speeding":
                violations.extend(self._check_speeding(record, rule_config))
        except Exception as e:
            self.logger.error(f"检查违规规则 {rule_name} 时出错: {e}")

        return violations

    def _check_no_safety_helmet(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未戴安全帽违规"""
        violations = []

        for obj in record.objects:
            if obj.is_person and obj.confidence.value >= rule_config["min_confidence"]:
                # 检查是否检测到安全帽
                has_helmet = self._has_object_nearby(
                    record.objects,
                    obj,
                    rule_config["forbidden_objects"],
                    max_distance=50.0,
                )

                if not has_helmet:
                    violation = Violation(
                        id=f"violation_{record.id}_{obj.track_id or 'unknown'}",
                        violation_type=ViolationType.NO_SAFETY_HELMET,
                        severity=rule_config["severity"],
                        camera_id=record.camera_id,
                        detected_object=obj,
                        timestamp=record.timestamp.value,
                        confidence=obj.confidence,
                        description=rule_config["description"],
                        metadata={
                            "rule_name": "no_safety_helmet",
                            "detection_confidence": obj.confidence.value,
                        },
                    )
                    violations.append(violation)

        return violations

    def _check_no_safety_vest(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未穿安全背心违规"""
        violations = []

        for obj in record.objects:
            if obj.is_person and obj.confidence.value >= rule_config["min_confidence"]:
                # 检查是否检测到安全背心
                has_vest = self._has_object_nearby(
                    record.objects,
                    obj,
                    rule_config["forbidden_objects"],
                    max_distance=30.0,
                )

                if not has_vest:
                    violation = Violation(
                        id=f"violation_{record.id}_{obj.track_id or 'unknown'}",
                        violation_type=ViolationType.NO_SAFETY_VEST,
                        severity=rule_config["severity"],
                        camera_id=record.camera_id,
                        detected_object=obj,
                        timestamp=record.timestamp.value,
                        confidence=obj.confidence,
                        description=rule_config["description"],
                        metadata={
                            "rule_name": "no_safety_vest",
                            "detection_confidence": obj.confidence.value,
                        },
                    )
                    violations.append(violation)

        return violations

    def _check_unauthorized_access(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未授权进入违规"""
        violations = []

        # 获取限制区域信息
        restricted_areas = record.get_metadata("restricted_areas", [])
        if not restricted_areas:
            return violations

        for obj in record.objects:
            if obj.is_person and obj.confidence.value >= rule_config["min_confidence"]:
                # 检查是否在限制区域内
                is_in_restricted_area = self._is_in_restricted_area(
                    obj, restricted_areas
                )

                if is_in_restricted_area:
                    violation = Violation(
                        id=f"violation_{record.id}_{obj.track_id or 'unknown'}",
                        violation_type=ViolationType.UNAUTHORIZED_ACCESS,
                        severity=rule_config["severity"],
                        camera_id=record.camera_id,
                        detected_object=obj,
                        timestamp=record.timestamp.value,
                        confidence=obj.confidence,
                        description=rule_config["description"],
                        metadata={
                            "rule_name": "unauthorized_access",
                            "restricted_areas": restricted_areas,
                            "detection_confidence": obj.confidence.value,
                        },
                    )
                    violations.append(violation)

        return violations

    def _check_crowding(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查人员聚集违规"""
        violations = []

        person_objects = [obj for obj in record.objects if obj.is_person]

        if len(person_objects) < rule_config["min_person_count"]:
            return violations

        # 计算人员密度
        total_area = sum(obj.area for obj in person_objects)
        if total_area > 0:
            area_per_person = total_area / len(person_objects)
            if area_per_person < rule_config["max_area_per_person"]:
                # 创建聚集违规记录
                violation = Violation(
                    id=f"violation_{record.id}_crowding",
                    violation_type=ViolationType.CROWDING,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=person_objects[0],  # 使用第一个人员对象
                    timestamp=record.timestamp.value,
                    confidence=Confidence(record.average_confidence),
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "crowding",
                        "person_count": len(person_objects),
                        "area_per_person": area_per_person,
                        "total_area": total_area,
                    },
                )
                violations.append(violation)

        return violations

    def _check_speeding(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查超速违规"""
        violations = []

        # 这里需要结合历史记录来计算速度
        # 简化实现，仅检查是否有移动对象
        moving_objects = [
            obj
            for obj in record.objects
            if obj.track_id is not None
            and obj.confidence.value >= rule_config["min_confidence"]
        ]

        for obj in moving_objects:
            # 获取移动速度（需要从历史记录计算）
            speed = obj.get_metadata("speed", 0.0)

            if speed > rule_config["max_speed"]:
                violation = Violation(
                    id=f"violation_{record.id}_{obj.track_id}",
                    violation_type=ViolationType.SPEEDING,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=obj,
                    timestamp=record.timestamp.value,
                    confidence=obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "speeding",
                        "detected_speed": speed,
                        "speed_limit": rule_config["max_speed"],
                    },
                )
                violations.append(violation)

        return violations

    def _has_object_nearby(
        self,
        objects: List[DetectedObject],
        target_obj: DetectedObject,
        object_classes: List[str],
        max_distance: float,
    ) -> bool:
        """检查附近是否有指定类别的对象"""
        for obj in objects:
            if obj == target_obj:
                continue

            if obj.class_name.lower() in [cls.lower() for cls in object_classes]:
                # 计算距离
                distance = self._calculate_distance(target_obj.center, obj.center)
                if distance <= max_distance:
                    return True

        return False

    def _is_in_restricted_area(
        self, obj: DetectedObject, restricted_areas: List[Dict[str, Any]]
    ) -> bool:
        """检查对象是否在限制区域内"""
        for area in restricted_areas:
            if "bbox" in area:
                area_bbox = BoundingBox.from_dict(area["bbox"])
                if area_bbox.contains_bbox(obj.bbox):
                    return True

        return False

    def _calculate_distance(
        self, pos1: Tuple[float, float], pos2: Tuple[float, float]
    ) -> float:
        """计算两点之间的距离"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def get_violation_statistics(self, violations: List[Violation]) -> Dict[str, Any]:
        """获取违规统计信息"""
        if not violations:
            return {
                "total_violations": 0,
                "violation_types": {},
                "severity_distribution": {},
                "camera_distribution": {},
                "time_distribution": {},
            }

        # 按类型统计
        violation_types = {}
        for violation in violations:
            violation_type = violation.violation_type.value
            violation_types[violation_type] = violation_types.get(violation_type, 0) + 1

        # 按严重程度统计
        severity_distribution = {}
        for violation in violations:
            severity = violation.severity.value
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1

        # 按摄像头统计
        camera_distribution = {}
        for violation in violations:
            camera_id = violation.camera_id
            camera_distribution[camera_id] = camera_distribution.get(camera_id, 0) + 1

        # 按时间统计（按小时）
        time_distribution = {}
        for violation in violations:
            hour = violation.timestamp.hour
            time_distribution[hour] = time_distribution.get(hour, 0) + 1

        return {
            "total_violations": len(violations),
            "violation_types": violation_types,
            "severity_distribution": severity_distribution,
            "camera_distribution": camera_distribution,
            "time_distribution": time_distribution,
        }

    def filter_violations_by_severity(
        self, violations: List[Violation], min_severity: ViolationSeverity
    ) -> List[Violation]:
        """按严重程度过滤违规记录"""
        severity_order = {
            ViolationSeverity.LOW: 1,
            ViolationSeverity.MEDIUM: 2,
            ViolationSeverity.HIGH: 3,
            ViolationSeverity.CRITICAL: 4,
        }

        min_level = severity_order[min_severity]

        return [
            violation
            for violation in violations
            if severity_order[violation.severity] >= min_level
        ]

    def group_violations_by_type(
        self, violations: List[Violation]
    ) -> Dict[str, List[Violation]]:
        """按类型分组违规记录"""
        groups = {}

        for violation in violations:
            violation_type = violation.violation_type.value
            if violation_type not in groups:
                groups[violation_type] = []
            groups[violation_type].append(violation)

        return groups

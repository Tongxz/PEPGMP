"""
违规检测领域服务
包含违规检测相关的业务逻辑
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence

logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """违规类型枚举"""

    NO_HAIRNET = "no_hairnet"  # 未戴发网
    NO_HANDWASH = "no_handwash"  # 未洗手
    NO_SANITIZE = "no_sanitize"  # 未消毒
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

    def _is_person(self, obj: Any) -> bool:
        """检查对象是否是人体（兼容字典格式和对象格式）"""
        if isinstance(obj, dict):
            class_name = obj.get("class_name", "").lower()
            return class_name in ["person", "人", "human"]
        return obj.is_person

    def _get_confidence_value(self, obj: Any) -> float:
        """获取置信度值（兼容字典格式和对象格式）"""
        if isinstance(obj, dict):
            conf_value = obj.get("confidence", 0.0)
            if isinstance(conf_value, dict):
                return conf_value.get("value", 0.0)
            elif isinstance(conf_value, (int, float)):
                return float(conf_value)
            return 0.0
        return obj.confidence.value

    def _get_track_id(self, obj: Any) -> Optional[int]:
        """获取跟踪ID（兼容字典格式和对象格式）"""
        if isinstance(obj, dict):
            return obj.get("track_id")
        return obj.track_id

    def _get_bbox(self, obj: Any) -> BoundingBox:
        """获取边界框（兼容字典格式和对象格式）"""
        if isinstance(obj, dict):
            bbox_data = obj.get("bbox")
            if isinstance(bbox_data, dict):
                return BoundingBox.from_dict(bbox_data)
            elif isinstance(bbox_data, BoundingBox):
                return bbox_data
            else:
                # 如果bbox是列表格式 [x1, y1, x2, y2]
                if isinstance(bbox_data, (list, tuple)) and len(bbox_data) >= 4:
                    return BoundingBox(
                        x1=bbox_data[0],
                        y1=bbox_data[1],
                        x2=bbox_data[2],
                        y2=bbox_data[3],
                    )
                raise ValueError(f"无法解析bbox格式: {bbox_data}")
        return obj.bbox

    def _get_center(self, obj: Any) -> Tuple[float, float]:
        """获取边界框中心点（兼容字典格式和对象格式）"""
        bbox = self._get_bbox(obj)
        return bbox.center

    def _get_area(self, obj: Any) -> float:
        """获取边界框面积（兼容字典格式和对象格式）"""
        bbox = self._get_bbox(obj)
        return bbox.area

    def _get_class_name(self, obj: Any) -> str:
        """获取类别名称（兼容字典格式和对象格式）"""
        if isinstance(obj, dict):
            return obj.get("class_name", "")
        return obj.class_name

    def _to_detected_object(self, obj: Any) -> DetectedObject:
        """将对象转换为DetectedObject实例（兼容字典格式和对象格式）"""
        if isinstance(obj, DetectedObject):
            return obj
        elif isinstance(obj, dict):
            # 处理字典格式，确保confidence和bbox格式正确
            obj_dict = obj.copy()

            # 处理confidence：可能是字典{"value": 0.8}或数值
            if "confidence" in obj_dict:
                conf_value = obj_dict["confidence"]
                if isinstance(conf_value, dict):
                    obj_dict["confidence"] = conf_value.get("value", 0.0)
                elif not isinstance(conf_value, (int, float)):
                    obj_dict["confidence"] = 0.0

            # 处理bbox：确保是字典格式（DetectedObject.from_dict期望字典）
            if "bbox" in obj_dict:
                bbox_data = obj_dict["bbox"]
                if isinstance(bbox_data, BoundingBox):
                    obj_dict["bbox"] = bbox_data.to_dict()
                elif not isinstance(bbox_data, dict):
                    # 如果bbox是列表格式 [x1, y1, x2, y2]，转换为字典
                    if isinstance(bbox_data, (list, tuple)) and len(bbox_data) >= 4:
                        obj_dict["bbox"] = {
                            "x1": bbox_data[0],
                            "y1": bbox_data[1],
                            "x2": bbox_data[2],
                            "y2": bbox_data[3],
                        }
                    else:
                        raise ValueError(f"无法解析bbox格式: {bbox_data}")

            # 确保必需的字段存在
            if "class_id" not in obj_dict:
                obj_dict["class_id"] = 0
            if "class_name" not in obj_dict:
                obj_dict["class_name"] = "unknown"

            return DetectedObject.from_dict(obj_dict)
        else:
            raise ValueError(f"无法将对象转换为DetectedObject: {type(obj)}")

    def _get_metadata(
        self, obj: Any, key: Optional[str] = None, default: Any = None
    ) -> Any:
        """获取元数据（兼容字典格式和对象格式）

        Args:
            obj: 对象（字典或对象）
            key: 元数据键（如果为None，返回整个metadata字典）
            default: 默认值

        Returns:
            元数据值或整个metadata字典
        """
        if isinstance(obj, dict):
            metadata = obj.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            if key is None:
                return metadata
            return metadata.get(key, default)
        if key is None:
            return obj.metadata if hasattr(obj, "metadata") else {}
        return (
            obj.get_metadata(key, default) if hasattr(obj, "get_metadata") else default
        )

    def _initialize_violation_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化违规检测规则

        当前系统检测发网、洗手、消毒违规
        """
        return {
            "no_hairnet": {
                "min_confidence": 0.5,
                "min_hairnet_confidence": 0.5,
                "required_objects": ["person"],
                "severity": ViolationSeverity.HIGH,
                "description": "检测到未戴发网的人员",
            },
            "no_handwash": {
                "min_confidence": 0.5,
                "min_handwash_confidence": 0.3,
                "required_objects": ["person"],
                "severity": ViolationSeverity.MEDIUM,
                "description": "检测到未洗手的人员",
            },
            "no_sanitize": {
                "min_confidence": 0.5,
                "min_sanitize_confidence": 0.3,
                "required_objects": ["person"],
                "severity": ViolationSeverity.MEDIUM,
                "description": "检测到未消毒的人员",
            },
            # 以下规则已禁用
            # "no_safety_helmet": {
            #     "min_confidence": 0.7,
            #     "required_objects": ["person"],
            #     "forbidden_objects": ["helmet", "hard_hat"],
            #     "severity": ViolationSeverity.HIGH,
            #     "description": "检测到未戴安全帽的人员",
            # },
            # "no_safety_vest": {
            #     "min_confidence": 0.6,
            #     "required_objects": ["person"],
            #     "forbidden_objects": ["safety_vest", "reflective_vest"],
            #     "severity": ViolationSeverity.MEDIUM,
            #     "description": "检测到未穿安全背心的人员",
            # },
            # "unauthorized_access": {
            #     "min_confidence": 0.8,
            #     "required_objects": ["person"],
            #     "restricted_areas": ["construction_zone", "danger_zone"],
            #     "severity": ViolationSeverity.CRITICAL,
            #     "description": "检测到未授权进入限制区域",
            # },
            # "crowding": {
            #     "min_confidence": 0.5,
            #     "min_person_count": 5,
            #     "max_area_per_person": 2.0,  # 平方米
            #     "severity": ViolationSeverity.MEDIUM,
            #     "description": "检测到人员过度聚集",
            # },
            # "speeding": {
            #     "min_confidence": 0.7,
            #     "max_speed": 5.0,  # 米/秒
            #     "required_objects": ["person", "vehicle"],
            #     "severity": ViolationSeverity.HIGH,
            #     "description": "检测到超速行为",
            # },
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
            if rule_name == "no_hairnet":
                violations.extend(self._check_no_hairnet(record, rule_config))
            elif rule_name == "no_handwash":
                violations.extend(self._check_no_handwash(record, rule_config))
            elif rule_name == "no_sanitize":
                violations.extend(self._check_no_sanitize(record, rule_config))
            elif rule_name == "no_safety_helmet":
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

    def _check_no_hairnet(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未戴发网违规"""
        violations = []

        for obj in record.objects:
            if not self._is_person(obj):
                continue

            conf_value = self._get_confidence_value(obj)
            if conf_value < rule_config["min_confidence"]:
                continue

            # 检查检测对象中的发网信息
            metadata = self._get_metadata(obj)  # 获取整个metadata字典
            if not isinstance(metadata, dict):
                metadata = {}
            has_hairnet = metadata.get("has_hairnet")
            hairnet_confidence = metadata.get("hairnet_confidence", 0.0)
            min_hairnet_confidence = rule_config.get("min_hairnet_confidence", 0.5)

            # 如果 has_hairnet 为 False（明确未佩戴）或 None（未检测到发网），都判定为违规
            # 但如果 has_hairnet 为 None，需要降低置信度要求（因为检测模型可能未检测到）
            is_violation = False
            if has_hairnet is False:
                # 明确未佩戴发网，需要满足置信度要求
                # 如果 hairnet_confidence 不够高，可以使用人体检测置信度作为补充（更宽松的条件）
                is_violation = (
                    hairnet_confidence >= min_hairnet_confidence or conf_value >= 0.7
                )
            elif has_hairnet is None:
                # 未检测到发网，降低置信度要求（使用人体检测置信度）
                # 如果人体检测置信度足够高，说明检测到人员，但未检测到发网，判定为违规
                is_violation = conf_value >= rule_config["min_confidence"]

            if is_violation:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj) or "unknown"

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}",
                    violation_type=ViolationType.NO_HAIRNET,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "no_hairnet",
                        "detection_confidence": conf_value,
                        "hairnet_confidence": hairnet_confidence,
                        "has_hairnet": has_hairnet,
                    },
                )
                violations.append(violation)
                self.logger.info(
                    f"检测到发网违规: camera_id={record.camera_id}, track_id={track_id}, "
                    f"has_hairnet={has_hairnet}, hairnet_confidence={hairnet_confidence}, "
                    f"detection_confidence={conf_value}"
                )
            elif has_hairnet is None:
                # 如果发网检测结果不明确且未达到违规条件，记录调试信息
                track_id = self._get_track_id(obj) or "unknown"
                self.logger.debug(
                    f"发网检测结果不明确，未判定为违规: has_hairnet={has_hairnet}, "
                    f"hairnet_confidence={hairnet_confidence}, "
                    f"detection_confidence={conf_value}, "
                    f"camera_id={record.camera_id}, track_id={track_id}"
                )

        return violations

    def _check_no_safety_helmet(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未戴安全帽违规"""
        violations = []

        for obj in record.objects:
            if not self._is_person(obj):
                continue

            conf_value = self._get_confidence_value(obj)
            if conf_value < rule_config["min_confidence"]:
                continue

            # 检查是否检测到安全帽
            has_helmet = self._has_object_nearby(
                record.objects,
                obj,
                rule_config["forbidden_objects"],
                max_distance=50.0,
            )

            if not has_helmet:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj) or "unknown"

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}",
                    violation_type=ViolationType.NO_SAFETY_HELMET,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "no_safety_helmet",
                        "detection_confidence": conf_value,
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
            if not self._is_person(obj):
                continue

            conf_value = self._get_confidence_value(obj)
            if conf_value < rule_config["min_confidence"]:
                continue

            # 检查是否检测到安全背心
            has_vest = self._has_object_nearby(
                record.objects,
                obj,
                rule_config["forbidden_objects"],
                max_distance=30.0,
            )

            if not has_vest:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj) or "unknown"

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}",
                    violation_type=ViolationType.NO_SAFETY_VEST,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "no_safety_vest",
                        "detection_confidence": conf_value,
                    },
                )
                violations.append(violation)

        return violations

    def _check_no_handwash(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未洗手违规"""
        violations = []

        for obj in record.objects:
            if not self._is_person(obj):
                continue

            conf_value = self._get_confidence_value(obj)
            if conf_value < rule_config["min_confidence"]:
                continue

            # 检查检测对象中的洗手信息
            metadata = self._get_metadata(obj)
            if not isinstance(metadata, dict):
                metadata = {}

            is_handwashing = metadata.get("is_handwashing")
            handwash_confidence = metadata.get("handwash_confidence", 0.0)
            min_handwash_confidence = rule_config.get("min_handwash_confidence", 0.3)

            # 如果 is_handwashing 为 False（明确未洗手）或 None（未检测到洗手），都判定为违规
            is_violation = False
            if is_handwashing is False:
                # 明确未洗手，需要满足置信度要求
                is_violation = (
                    handwash_confidence >= min_handwash_confidence or conf_value >= 0.7
                )
            elif is_handwashing is None:
                # 未检测到洗手行为，降低置信度要求（使用人体检测置信度）
                is_violation = conf_value >= rule_config["min_confidence"]

            if is_violation:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj) or "unknown"

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}_handwash",
                    violation_type=ViolationType.NO_HANDWASH,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "no_handwash",
                        "detection_confidence": conf_value,
                        "handwash_confidence": handwash_confidence,
                        "is_handwashing": is_handwashing,
                    },
                )
                violations.append(violation)
                self.logger.info(
                    f"检测到洗手违规: camera_id={record.camera_id}, track_id={track_id}, "
                    f"is_handwashing={is_handwashing}, handwash_confidence={handwash_confidence}, "
                    f"detection_confidence={conf_value}"
                )

        return violations

    def _check_no_sanitize(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查未消毒违规"""
        violations = []

        for obj in record.objects:
            if not self._is_person(obj):
                continue

            conf_value = self._get_confidence_value(obj)
            if conf_value < rule_config["min_confidence"]:
                continue

            # 检查检测对象中的消毒信息
            metadata = self._get_metadata(obj)
            if not isinstance(metadata, dict):
                metadata = {}

            is_sanitizing = metadata.get("is_sanitizing")
            sanitize_confidence = metadata.get("sanitize_confidence", 0.0)
            min_sanitize_confidence = rule_config.get("min_sanitize_confidence", 0.3)

            # 如果 is_sanitizing 为 False（明确未消毒）或 None（未检测到消毒），都判定为违规
            is_violation = False
            if is_sanitizing is False:
                # 明确未消毒，需要满足置信度要求
                is_violation = (
                    sanitize_confidence >= min_sanitize_confidence or conf_value >= 0.7
                )
            elif is_sanitizing is None:
                # 未检测到消毒行为，降低置信度要求（使用人体检测置信度）
                is_violation = conf_value >= rule_config["min_confidence"]

            if is_violation:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj) or "unknown"

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}_sanitize",
                    violation_type=ViolationType.NO_SANITIZE,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "no_sanitize",
                        "detection_confidence": conf_value,
                        "sanitize_confidence": sanitize_confidence,
                        "is_sanitizing": is_sanitizing,
                    },
                )
                violations.append(violation)
                self.logger.info(
                    f"检测到消毒违规: camera_id={record.camera_id}, track_id={track_id}, "
                    f"is_sanitizing={is_sanitizing}, sanitize_confidence={sanitize_confidence}, "
                    f"detection_confidence={conf_value}"
                )

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
            if not self._is_person(obj):
                continue

            conf_value = self._get_confidence_value(obj)
            if conf_value < rule_config["min_confidence"]:
                continue

            # 检查是否在限制区域内
            is_in_restricted_area = self._is_in_restricted_area(obj, restricted_areas)

            if is_in_restricted_area:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj) or "unknown"

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}",
                    violation_type=ViolationType.UNAUTHORIZED_ACCESS,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
                    description=rule_config["description"],
                    metadata={
                        "rule_name": "unauthorized_access",
                        "restricted_areas": restricted_areas,
                        "detection_confidence": conf_value,
                    },
                )
                violations.append(violation)

        return violations

    def _check_crowding(
        self, record: DetectionRecord, rule_config: Dict[str, Any]
    ) -> List[Violation]:
        """检查人员聚集违规"""
        violations = []

        person_objects = [obj for obj in record.objects if self._is_person(obj)]

        if len(person_objects) < rule_config["min_person_count"]:
            return violations

        # 计算人员密度
        total_area = sum(self._get_area(obj) for obj in person_objects)
        if total_area > 0:
            area_per_person = total_area / len(person_objects)
            if area_per_person < rule_config["max_area_per_person"]:
                # 转换为DetectedObject实例（使用第一个人员对象）
                detected_obj = self._to_detected_object(person_objects[0])

                # 获取平均置信度
                avg_confidence = (
                    record.average_confidence
                    if hasattr(record, "average_confidence")
                    else 0.0
                )

                # 创建聚集违规记录
                violation = Violation(
                    id=f"violation_{record.id}_crowding",
                    violation_type=ViolationType.CROWDING,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=Confidence(avg_confidence),
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
        moving_objects = []
        for obj in record.objects:
            track_id = self._get_track_id(obj)
            conf_value = self._get_confidence_value(obj)
            if track_id is not None and conf_value >= rule_config["min_confidence"]:
                moving_objects.append(obj)

        for obj in moving_objects:
            # 获取移动速度（需要从历史记录计算）
            speed = self._get_metadata(obj, "speed", 0.0)

            if speed > rule_config["max_speed"]:
                # 转换为DetectedObject实例
                detected_obj = self._to_detected_object(obj)
                track_id = self._get_track_id(obj)

                violation = Violation(
                    id=f"violation_{record.id}_{track_id}",
                    violation_type=ViolationType.SPEEDING,
                    severity=rule_config["severity"],
                    camera_id=record.camera_id,
                    detected_object=detected_obj,
                    timestamp=record.timestamp.value
                    if hasattr(record.timestamp, "value")
                    else record.timestamp,
                    confidence=detected_obj.confidence,
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
        objects: List[Any],
        target_obj: Any,
        object_classes: List[str],
        max_distance: float,
    ) -> bool:
        """检查附近是否有指定类别的对象（兼容字典格式和对象格式）"""
        target_center = self._get_center(target_obj)

        for obj in objects:
            # 简单比较，避免深度比较
            if obj is target_obj:
                continue

            obj_class_name = self._get_class_name(obj).lower()
            if obj_class_name in [cls.lower() for cls in object_classes]:
                # 计算距离
                obj_center = self._get_center(obj)
                distance = self._calculate_distance(target_center, obj_center)
                if distance <= max_distance:
                    return True

        return False

    def _is_in_restricted_area(
        self, obj: Any, restricted_areas: List[Dict[str, Any]]
    ) -> bool:
        """检查对象是否在限制区域内（兼容字典格式和对象格式）"""
        obj_bbox = self._get_bbox(obj)

        for area in restricted_areas:
            if "bbox" in area:
                area_bbox_data = area["bbox"]
                if isinstance(area_bbox_data, dict):
                    area_bbox = BoundingBox.from_dict(area_bbox_data)
                elif isinstance(area_bbox_data, BoundingBox):
                    area_bbox = area_bbox_data
                else:
                    continue

                if area_bbox.contains_bbox(obj_bbox):
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

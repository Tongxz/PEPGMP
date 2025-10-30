"""
检测领域服务
包含检测相关的业务逻辑
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from src.domain.entities.detection_record import DetectionRecord

logger = logging.getLogger(__name__)


class DetectionService:
    """检测领域服务"""

    def __init__(self):
        """初始化检测服务"""
        self.logger = logging.getLogger(__name__)

    def analyze_detection_quality(self, record: DetectionRecord) -> Dict[str, Any]:
        """
        分析检测质量

        Args:
            record: 检测记录

        Returns:
            Dict[str, Any]: 质量分析结果
        """
        analysis = {
            "overall_quality": "unknown",
            "confidence_score": 0.0,
            "object_density": 0.0,
            "quality_issues": [],
            "recommendations": [],
        }

        if not record.objects:
            analysis["overall_quality"] = "poor"
            analysis["quality_issues"].append("no_objects_detected")
            analysis["recommendations"].append("check_camera_positioning")
            return analysis

        # 计算置信度分数
        avg_confidence = record.average_confidence
        analysis["confidence_score"] = avg_confidence

        # 计算对象密度（每平方米的对象数量）
        total_area = sum(obj.area for obj in record.objects)
        if total_area > 0:
            analysis["object_density"] = len(record.objects) / (
                total_area / 1000000
            )  # 转换为每平方米

        # 分析质量
        if avg_confidence >= 0.8:
            analysis["overall_quality"] = "excellent"
        elif avg_confidence >= 0.6:
            analysis["overall_quality"] = "good"
        elif avg_confidence >= 0.4:
            analysis["overall_quality"] = "fair"
        else:
            analysis["overall_quality"] = "poor"

        # 检查质量问题
        low_confidence_objects = record.low_confidence_objects
        if len(low_confidence_objects) > len(record.objects) * 0.5:
            analysis["quality_issues"].append("too_many_low_confidence_objects")
            analysis["recommendations"].append("improve_lighting_conditions")

        if record.object_count > 10:
            analysis["quality_issues"].append("too_many_objects")
            analysis["recommendations"].append("reduce_detection_area")

        if analysis["object_density"] > 5.0:
            analysis["quality_issues"].append("high_object_density")
            analysis["recommendations"].append("increase_camera_height")

        return analysis

    def detect_anomalies(self, records: List[DetectionRecord]) -> List[Dict[str, Any]]:
        """
        检测异常情况

        Args:
            records: 检测记录列表

        Returns:
            List[Dict[str, Any]]: 异常情况列表
        """
        anomalies = []

        if len(records) < 2:
            return anomalies

        # 按时间排序
        sorted_records = sorted(records, key=lambda r: r.timestamp.value)

        # 检测突然的对象数量变化
        for i in range(1, len(sorted_records)):
            prev_record = sorted_records[i - 1]
            curr_record = sorted_records[i]

            object_count_diff = abs(curr_record.object_count - prev_record.object_count)
            if object_count_diff > 5:  # 对象数量变化超过5个
                anomalies.append(
                    {
                        "type": "sudden_object_count_change",
                        "timestamp": curr_record.timestamp.iso_string,
                        "camera_id": curr_record.camera_id,
                        "previous_count": prev_record.object_count,
                        "current_count": curr_record.object_count,
                        "difference": object_count_diff,
                        "severity": "high" if object_count_diff > 10 else "medium",
                    }
                )

        # 检测置信度异常下降
        for i in range(1, len(sorted_records)):
            prev_record = sorted_records[i - 1]
            curr_record = sorted_records[i]

            confidence_diff = (
                prev_record.average_confidence - curr_record.average_confidence
            )
            if confidence_diff > 0.3:  # 置信度下降超过0.3
                anomalies.append(
                    {
                        "type": "confidence_drop",
                        "timestamp": curr_record.timestamp.iso_string,
                        "camera_id": curr_record.camera_id,
                        "previous_confidence": prev_record.average_confidence,
                        "current_confidence": curr_record.average_confidence,
                        "difference": confidence_diff,
                        "severity": "high" if confidence_diff > 0.5 else "medium",
                    }
                )

        # 检测长时间无检测
        for i in range(1, len(sorted_records)):
            prev_record = sorted_records[i - 1]
            curr_record = sorted_records[i]

            time_diff = curr_record.timestamp.time_difference(prev_record.timestamp)
            if time_diff > 300:  # 超过5分钟无检测
                anomalies.append(
                    {
                        "type": "long_detection_gap",
                        "timestamp": curr_record.timestamp.iso_string,
                        "camera_id": curr_record.camera_id,
                        "gap_duration": time_diff,
                        "severity": "high" if time_diff > 600 else "medium",
                    }
                )

        return anomalies

    def calculate_detection_statistics(
        self, records: List[DetectionRecord]
    ) -> Dict[str, Any]:
        """
        计算检测统计信息

        Args:
            records: 检测记录列表

        Returns:
            Dict[str, Any]: 统计信息
        """
        if not records:
            return {
                "total_records": 0,
                "total_objects": 0,
                "average_confidence": 0.0,
                "average_processing_time": 0.0,
                "object_distribution": {},
                "confidence_distribution": {},
                "time_range": None,
            }

        # 基本统计
        total_records = len(records)
        total_objects = sum(record.object_count for record in records)
        average_confidence = (
            sum(record.average_confidence for record in records) / total_records
        )
        average_processing_time = (
            sum(record.processing_time for record in records) / total_records
        )

        # 对象分布
        object_distribution = {}
        for record in records:
            for obj in record.objects:
                class_name = obj.class_name
                object_distribution[class_name] = (
                    object_distribution.get(class_name, 0) + 1
                )

        # 置信度分布
        confidence_ranges = {"high": 0, "medium": 0, "low": 0}
        for record in records:
            confidence_ranges["high"] += len(record.high_confidence_objects)
            confidence_ranges["medium"] += len(record.medium_confidence_objects)
            confidence_ranges["low"] += len(record.low_confidence_objects)

        # 时间范围
        timestamps = [record.timestamp for record in records]
        time_range = {
            "start": min(timestamps).iso_string,
            "end": max(timestamps).iso_string,
            "duration_seconds": max(timestamps).time_difference(min(timestamps)),
        }

        return {
            "total_records": total_records,
            "total_objects": total_objects,
            "average_confidence": average_confidence,
            "average_processing_time": average_processing_time,
            "object_distribution": object_distribution,
            "confidence_distribution": confidence_ranges,
            "time_range": time_range,
        }

    def filter_high_quality_detections(
        self,
        records: List[DetectionRecord],
        min_confidence: float = 0.7,
        min_object_count: int = 1,
    ) -> List[DetectionRecord]:
        """
        过滤高质量检测记录

        Args:
            records: 检测记录列表
            min_confidence: 最小置信度
            min_object_count: 最小对象数量

        Returns:
            List[DetectionRecord]: 过滤后的记录列表
        """
        filtered_records = []

        for record in records:
            if (
                record.average_confidence >= min_confidence
                and record.object_count >= min_object_count
            ):
                filtered_records.append(record)

        return filtered_records

    def group_detections_by_time_window(
        self, records: List[DetectionRecord], window_minutes: int = 5
    ) -> Dict[str, List[DetectionRecord]]:
        """
        按时间窗口分组检测记录

        Args:
            records: 检测记录列表
            window_minutes: 时间窗口（分钟）

        Returns:
            Dict[str, List[DetectionRecord]]: 分组后的记录
        """
        if not records:
            return {}

        # 按时间排序
        sorted_records = sorted(records, key=lambda r: r.timestamp.value)

        groups = {}
        current_group = []
        current_window_start = sorted_records[0].timestamp.value

        for record in sorted_records:
            time_diff = record.timestamp.value - current_window_start
            if time_diff.total_seconds() <= window_minutes * 60:
                current_group.append(record)
            else:
                # 保存当前组
                if current_group:
                    group_key = current_window_start.strftime("%Y-%m-%d %H:%M")
                    groups[group_key] = current_group

                # 开始新组
                current_group = [record]
                current_window_start = record.timestamp.value

        # 保存最后一组
        if current_group:
            group_key = current_window_start.strftime("%Y-%m-%d %H:%M")
            groups[group_key] = current_group

        return groups

    def detect_object_movement(
        self, records: List[DetectionRecord], track_id: int
    ) -> List[Dict[str, Any]]:
        """
        检测对象移动轨迹

        Args:
            records: 检测记录列表
            track_id: 跟踪ID

        Returns:
            List[Dict[str, Any]]: 移动轨迹点
        """
        trajectory = []

        for record in records:
            obj = record.find_object_by_track_id(track_id)
            if obj:
                trajectory.append(
                    {
                        "timestamp": record.timestamp.iso_string,
                        "camera_id": record.camera_id,
                        "position": obj.center,
                        "bbox": obj.bbox.to_dict(),
                        "confidence": obj.confidence.value,
                    }
                )

        return trajectory

    def calculate_movement_speed(
        self, trajectory: List[Dict[str, Any]], pixels_per_meter: float = 100.0
    ) -> float:
        """
        计算移动速度

        Args:
            trajectory: 移动轨迹
            pixels_per_meter: 每米像素数

        Returns:
            float: 移动速度（米/秒）
        """
        if len(trajectory) < 2:
            return 0.0

        total_distance = 0.0
        total_time = 0.0

        for i in range(1, len(trajectory)):
            prev_point = trajectory[i - 1]
            curr_point = trajectory[i]

            # 计算距离（像素）
            prev_pos = prev_point["position"]
            curr_pos = curr_point["position"]
            distance_pixels = (
                (curr_pos[0] - prev_pos[0]) ** 2 + (curr_pos[1] - prev_pos[1]) ** 2
            ) ** 0.5

            # 转换为米
            distance_meters = distance_pixels / pixels_per_meter
            total_distance += distance_meters

            # 计算时间差
            prev_time = datetime.fromisoformat(prev_point["timestamp"])
            curr_time = datetime.fromisoformat(curr_point["timestamp"])
            time_diff = (curr_time - prev_time).total_seconds()
            total_time += time_diff

        if total_time == 0:
            return 0.0

        return total_distance / total_time

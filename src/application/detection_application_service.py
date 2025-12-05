"""
检测应用服务

该服务协调基础设施层（检测管道）和领域层（业务逻辑），
实现完整的检测流程，包括智能保存策略。
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.core.optimized_detection_pipeline import (
    DetectionResult,
    OptimizedDetectionPipeline,
)
from src.interfaces.storage import SnapshotInfo, SnapshotStorageProtocol
from src.services.detection_service_domain import DetectionServiceDomain

logger = logging.getLogger(__name__)


class SaveStrategy(Enum):
    """保存策略"""

    ALL = "all"  # 保存所有检测结果（按间隔）
    VIOLATIONS_ONLY = "violations_only"  # 仅保存违规记录
    INTERVAL = "interval"  # 按固定间隔保存
    SMART = "smart"  # 智能保存（违规必保存 + 定期保存正常样本）


@dataclass
class SavePolicy:
    """保存策略配置"""

    # 保存策略类型
    strategy: SaveStrategy = SaveStrategy.SMART

    # INTERVAL策略：保存间隔（帧数）
    save_interval: int = 30

    # SMART策略：正常样本采样间隔（帧数）
    normal_sample_interval: int = 300  # 每300帧（约10秒）保存一次正常样本

    # 是否保存统计摘要
    save_normal_summary: bool = True

    # 违规严重程度阈值（0.0-1.0）
    violation_severity_threshold: float = 0.5


class DetectionMode(Enum):
    """检测模式"""

    SINGLE_IMAGE = "single_image"  # 单张图片
    VIDEO_FILE = "video_file"  # 视频文件
    REALTIME_STREAM = "realtime_stream"  # 实时流


class DetectionApplicationService:
    """检测应用服务 - 支持多种场景和智能保存策略"""

    def __init__(
        self,
        detection_pipeline: OptimizedDetectionPipeline,
        detection_domain_service: DetectionServiceDomain,
        snapshot_storage: Optional[SnapshotStorageProtocol] = None,
        save_policy: Optional[SavePolicy] = None,
    ):
        """
        初始化检测应用服务

        Args:
            detection_pipeline: 检测管道（基础设施层）
            detection_domain_service: 检测领域服务（领域层）
            save_policy: 保存策略配置
        """
        self.detection_pipeline = detection_pipeline
        self.detection_domain_service = detection_domain_service
        self.snapshot_storage = snapshot_storage
        self.save_policy = save_policy or SavePolicy()  # 默认SMART策略
        self.logger = logging.getLogger(__name__)

        # 统计缓冲（用于生成周期性摘要）
        self.stats_buffer = {
            "total_frames": 0,
            "normal_frames": 0,
            "violation_frames": 0,
            "last_summary_save": 0,
        }

        self.logger.info(
            f"DetectionApplicationService initialized with strategy: {self.save_policy.strategy.value}"
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 智能保存决策
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _should_save_detection(
        self,
        frame_count: int,
        has_violations: bool,
        violation_severity: float = 0.0,
    ) -> bool:
        """
        决定是否保存检测结果

        Args:
            frame_count: 当前帧数
            has_violations: 是否有违规
            violation_severity: 违规严重程度（0.0-1.0）

        Returns:
            是否应该保存
        """
        strategy = self.save_policy.strategy

        # 策略1: 保存所有（按间隔）
        if strategy == SaveStrategy.ALL:
            return frame_count % self.save_policy.save_interval == 0

        # 策略2: 仅保存违规
        if strategy == SaveStrategy.VIOLATIONS_ONLY:
            if not has_violations:
                return False
            # 检查违规严重程度
            return violation_severity >= self.save_policy.violation_severity_threshold

        # 策略3: 按间隔保存
        if strategy == SaveStrategy.INTERVAL:
            return frame_count % self.save_policy.save_interval == 0

        # 策略4: 智能保存（推荐）
        if strategy == SaveStrategy.SMART:
            # 1. 违规必保存
            if (
                has_violations
                and violation_severity >= self.save_policy.violation_severity_threshold
            ):
                return True

            # 2. 定期保存正常样本（用于基线对比和模型训练）
            if frame_count % self.save_policy.normal_sample_interval == 0:
                return True

            return False

        return False

    def _analyze_violations(
        self, detection_result: DetectionResult
    ) -> Tuple[bool, float]:
        """
        分析违规情况

        Args:
            detection_result: 检测结果

        Returns:
            (是否有违规, 违规严重程度)
        """
        violations = []

        # 1. 检查发网违规
        # 创建发网检测结果映射（按person_id或bbox匹配）
        hairnet_map = {}
        for hairnet in detection_result.hairnet_results:
            person_id = hairnet.get("person_id")
            person_bbox = hairnet.get("person_bbox", hairnet.get("bbox", [0, 0, 0, 0]))
            # 使用person_id或bbox作为键
            if person_id:
                hairnet_map[person_id] = hairnet
            else:
                bbox_key = tuple(person_bbox) if len(person_bbox) >= 4 else None
                if bbox_key:
                    hairnet_map[bbox_key] = hairnet

        # 遍历所有检测到的人员，确保每个人员都被检查
        for i, person in enumerate(detection_result.person_detections):
            person_bbox = person.get("bbox", [0, 0, 0, 0])
            person_confidence = person.get("confidence", 0.0)
            track_id = person.get("track_id", i)

            # 查找对应的发网检测结果
            hairnet_info = None
            # 首先尝试通过person_id匹配
            person_id = i + 1
            if person_id in hairnet_map:
                hairnet_info = hairnet_map[person_id]
            else:
                # 尝试通过bbox匹配
                bbox_key = tuple(person_bbox) if len(person_bbox) >= 4 else None
                if bbox_key and bbox_key in hairnet_map:
                    hairnet_info = hairnet_map[bbox_key]

            # 获取发网检测结果
            if hairnet_info:
                has_hairnet = hairnet_info.get("has_hairnet", None)
                hairnet_confidence = hairnet_info.get("hairnet_confidence", 0.0)
            else:
                # 如果没有匹配到发网检测结果，默认判定为未检测到发网
                has_hairnet = None
                hairnet_confidence = 0.0

            # 如果 has_hairnet 为 False（明确未佩戴）或 None（未检测到发网），都判定为违规
            # 但如果 has_hairnet 为 None，需要降低置信度要求
            is_violation = False
            if has_hairnet is False:
                # 明确未佩戴发网，需要满足置信度要求
                is_violation = hairnet_confidence > 0.5 or person_confidence > 0.7
            elif has_hairnet is None:
                # 未检测到发网，降低置信度要求（使用人体检测置信度）
                # 如果人体检测置信度足够高，说明检测到人员，但未检测到发网，判定为违规
                is_violation = person_confidence > 0.5

            if is_violation:
                violations.append(
                    {
                        "type": "no_hairnet",
                        "confidence": person_confidence,
                        "severity": 0.8,  # 发网违规严重程度高
                        "track_id": track_id,
                    }
                )
                self.logger.info(
                    f"检测到发网违规: track_id={track_id}, has_hairnet={has_hairnet}, "
                    f"hairnet_confidence={hairnet_confidence}, "
                    f"person_confidence={person_confidence}"
                )
            elif has_hairnet is None or has_hairnet is False:
                # 如果发网检测结果不明确且未达到违规条件，记录调试信息
                self.logger.debug(
                    f"发网检测结果不明确，未判定为违规: track_id={track_id}, has_hairnet={has_hairnet}, "
                    f"hairnet_confidence={hairnet_confidence}, "
                    f"person_confidence={person_confidence}"
                )

        # 2. 可以扩展更多违规检测规则
        # 例如：未洗手、未消毒等

        if not violations:
            return False, 0.0

        # 3. 计算综合严重程度（取最高严重程度）
        max_severity = max(v["severity"] for v in violations)

        return True, max_severity

    def _extract_violations_summary(
        self, detection_result: DetectionResult
    ) -> List[Dict[str, Any]]:
        """提取违规摘要（轻量级）"""
        violations = []

        # 创建发网检测结果映射（按person_id或bbox匹配）
        hairnet_map = {}
        for hairnet in detection_result.hairnet_results:
            person_id = hairnet.get("person_id")
            person_bbox = hairnet.get("person_bbox", hairnet.get("bbox", [0, 0, 0, 0]))
            # 使用person_id或bbox作为键
            if person_id:
                hairnet_map[person_id] = hairnet
            else:
                bbox_key = tuple(person_bbox) if len(person_bbox) >= 4 else None
                if bbox_key:
                    hairnet_map[bbox_key] = hairnet

        # 遍历所有检测到的人员，确保每个人员都被检查
        for i, person in enumerate(detection_result.person_detections):
            person_bbox = person.get("bbox", [0, 0, 0, 0])
            person_confidence = person.get("confidence", 0.0)
            track_id = person.get("track_id", i)

            # 查找对应的发网检测结果
            hairnet_info = None
            # 首先尝试通过person_id匹配
            person_id = i + 1
            if person_id in hairnet_map:
                hairnet_info = hairnet_map[person_id]
            else:
                # 尝试通过bbox匹配
                bbox_key = tuple(person_bbox) if len(person_bbox) >= 4 else None
                if bbox_key and bbox_key in hairnet_map:
                    hairnet_info = hairnet_map[bbox_key]

            # 获取发网检测结果
            if hairnet_info:
                has_hairnet = hairnet_info.get("has_hairnet", None)
                hairnet_confidence = hairnet_info.get("hairnet_confidence", 0.0)
            else:
                # 如果没有匹配到发网检测结果，默认判定为未检测到发网
                has_hairnet = None
                hairnet_confidence = 0.0

            # 如果 has_hairnet 为 False（明确未佩戴）或 None（未检测到发网），都判定为违规
            # 但如果 has_hairnet 为 None，需要降低置信度要求
            is_violation = False
            if has_hairnet is False:
                # 明确未佩戴发网，需要满足置信度要求
                is_violation = hairnet_confidence > 0.5 or person_confidence > 0.7
            elif has_hairnet is None:
                # 未检测到发网，降低置信度要求（使用人体检测置信度）
                is_violation = person_confidence > 0.5

            if is_violation:
                violations.append(
                    {
                        "type": "no_hairnet",
                        "confidence": person_confidence,
                        "track_id": track_id,
                        "bbox": person_bbox,
                    }
                )

        return violations

    def _get_primary_violation_type(
        self, detection_result: DetectionResult
    ) -> Optional[str]:
        """获取主要违规类型"""
        violations = self._extract_violations_summary(detection_result)
        if violations:
            return violations[0].get("type")
        return None

    async def _save_snapshot_if_possible(
        self,
        frame: np.ndarray,
        camera_id: str,
        *,
        violation_type: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        annotated_image: Optional[np.ndarray] = None,
    ) -> Optional[SnapshotInfo]:
        """尝试保存快照并返回结果

        Args:
            frame: 原始视频帧
            camera_id: 摄像头ID
            violation_type: 违规类型（如果有）
            metadata: 元数据
            annotated_image: 标注后的图片（优先使用，如果提供）

        Returns:
            快照信息，如果保存失败则返回None
        """
        if self.snapshot_storage is None:
            self.logger.warning(
                f"快照存储未配置: camera={camera_id}, violation_type={violation_type}"
            )
            return None

        metadata_mapping = None
        if metadata:
            metadata_mapping = {str(k): str(v) for k, v in metadata.items()}

        # 优先使用标注后的图片，如果没有则使用原始帧
        # 违规记录中应该显示标注框，方便查看违规详情
        image_to_save = annotated_image if annotated_image is not None else frame

        try:
            snapshot_info = await self.snapshot_storage.save_frame(
                image_to_save,
                camera_id,
                captured_at=datetime.utcnow(),
                violation_type=violation_type,
                metadata=metadata_mapping,
            )
            self.logger.debug(
                f"快照保存成功: camera={camera_id}, violation_type={violation_type}, "
                f"path={snapshot_info.relative_path if snapshot_info else None}, "
                f"使用标注图片={annotated_image is not None}"
            )
            return snapshot_info
        except Exception as exc:
            self.logger.warning(
                f"保存快照失败: camera={camera_id}, violation_type={violation_type}, error={exc}",
                exc_info=True,
            )
            return None

    def _get_save_reason(
        self,
        frame_count: int,
        has_violations: bool,
        violation_severity: float,
        was_saved: bool,
    ) -> Optional[str]:
        """获取保存原因（用于日志和调试）"""
        if not was_saved:
            return None

        strategy = self.save_policy.strategy

        if strategy == SaveStrategy.VIOLATIONS_ONLY:
            return f"violation_detected (severity={violation_severity:.2f})"

        if strategy == SaveStrategy.SMART:
            if has_violations:
                return f"violation_detected (severity={violation_severity:.2f})"
            else:
                return f"normal_sample (interval={self.save_policy.normal_sample_interval})"

        if strategy == SaveStrategy.ALL or strategy == SaveStrategy.INTERVAL:
            return f"interval_save (interval={self.save_policy.save_interval})"

        return "unknown"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 数据转换
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """解码图像字节为numpy数组"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法解码图像")
        return image

    def _convert_to_domain_format(
        self, detection_result: DetectionResult
    ) -> List[Dict[str, Any]]:
        """将检测结果转换为领域模型格式"""
        objects = []

        # 创建发网检测结果映射（按索引或bbox匹配）
        hairnet_map = {}
        for i, hairnet in enumerate(detection_result.hairnet_results):
            person_bbox = hairnet.get("person_bbox", hairnet.get("bbox", [0, 0, 0, 0]))
            # 使用 bbox 作为键（转换为元组以便哈希）
            bbox_key = tuple(person_bbox) if len(person_bbox) >= 4 else (i,)
            hairnet_map[bbox_key] = hairnet

        # 创建洗手和消毒检测结果映射（按track_id或person_id匹配）
        handwash_map = {}
        sanitize_map = {}
        for result in detection_result.handwash_results:
            track_id = result.get("track_id")
            person_id = result.get("person_id")
            # 优先使用track_id，其次使用person_id
            key = track_id if track_id is not None else person_id
            if key is not None:
                handwash_map[key] = result

        for result in detection_result.sanitize_results:
            track_id = result.get("track_id")
            person_id = result.get("person_id")
            key = track_id if track_id is not None else person_id
            if key is not None:
                sanitize_map[key] = result

        # 转换人体检测结果，并将发网检测结果关联到对应的人员对象
        for i, person in enumerate(detection_result.person_detections):
            person_bbox = person.get("bbox", [0, 0, 0, 0])
            bbox_key = tuple(person_bbox) if len(person_bbox) >= 4 else (i,)
            track_id = person.get("track_id")
            person_id = i + 1  # person_id从1开始

            # 查找对应的发网检测结果
            hairnet_info = None
            # 首先尝试通过 bbox 匹配
            if bbox_key in hairnet_map:
                hairnet_info = hairnet_map[bbox_key]
            # 如果 bbox 匹配失败，尝试通过索引匹配
            elif i < len(detection_result.hairnet_results):
                hairnet_info = detection_result.hairnet_results[i]

            # 查找对应的洗手检测结果
            handwash_info = None
            # 优先通过track_id匹配
            if track_id is not None and track_id in handwash_map:
                handwash_info = handwash_map[track_id]
            # 其次通过person_id匹配
            elif person_id in handwash_map:
                handwash_info = handwash_map[person_id]
            # 最后通过索引匹配
            elif i < len(detection_result.handwash_results):
                handwash_info = detection_result.handwash_results[i]

            # 查找对应的消毒检测结果
            sanitize_info = None
            if track_id is not None and track_id in sanitize_map:
                sanitize_info = sanitize_map[track_id]
            elif person_id in sanitize_map:
                sanitize_info = sanitize_map[person_id]
            elif i < len(detection_result.sanitize_results):
                sanitize_info = detection_result.sanitize_results[i]

            # 构建人员对象的 metadata
            person_metadata = {
                "source": "human_detector",
                **person.get("metadata", {}),
            }

            # 如果有发网检测结果，将发网信息添加到 metadata 中
            # 如果没有匹配到发网检测结果，默认 has_hairnet=False（未佩戴）
            if hairnet_info:
                has_hairnet = hairnet_info.get("has_hairnet")
                hairnet_confidence = hairnet_info.get("hairnet_confidence", 0.0)
                person_metadata["has_hairnet"] = has_hairnet
                person_metadata["hairnet_confidence"] = hairnet_confidence
                # 保留其他发网检测信息
                if "hairnet_bbox" in hairnet_info:
                    person_metadata["hairnet_bbox"] = hairnet_info["hairnet_bbox"]
                if "head_bbox" in hairnet_info:
                    person_metadata["head_bbox"] = hairnet_info["head_bbox"]
            else:
                # 如果没有匹配到发网检测结果，默认判定为未佩戴发网
                # 这样违规检测逻辑可以统一处理
                person_metadata["has_hairnet"] = False
                person_metadata["hairnet_confidence"] = 0.0
                self.logger.debug(
                    f"人员 {i} (track_id={person.get('track_id')}) 未匹配到发网检测结果，"
                    f"默认判定为未佩戴发网"
                )

            # 如果有洗手检测结果，将洗手信息添加到 metadata 中
            if handwash_info:
                is_handwashing = handwash_info.get("is_handwashing", False)
                handwash_confidence = handwash_info.get("handwash_confidence", 0.0)
                person_metadata["is_handwashing"] = is_handwashing
                person_metadata["handwash_confidence"] = handwash_confidence
            else:
                # 如果没有匹配到洗手检测结果，默认判定为未洗手
                person_metadata["is_handwashing"] = False
                person_metadata["handwash_confidence"] = 0.0

            # 如果有消毒检测结果，将消毒信息添加到 metadata 中
            if sanitize_info:
                is_sanitizing = sanitize_info.get("is_sanitizing", False)
                sanitize_confidence = sanitize_info.get("sanitize_confidence", 0.0)
                person_metadata["is_sanitizing"] = is_sanitizing
                person_metadata["sanitize_confidence"] = sanitize_confidence
            else:
                # 如果没有匹配到消毒检测结果，默认判定为未消毒
                person_metadata["is_sanitizing"] = False
                person_metadata["sanitize_confidence"] = 0.0

            objects.append(
                {
                    "class_id": 0,
                    "class_name": "person",
                    "confidence": person.get("confidence", 0.0),
                    "bbox": person_bbox,
                    "track_id": person.get("track_id"),
                    "metadata": person_metadata,
                }
            )

        # 转换行为检测结果（洗手、消毒）
        for behavior in detection_result.handwash_results:
            objects.append(
                {
                    "class_id": 2,
                    "class_name": "handwashing",
                    "confidence": behavior.get("confidence", 0.0),
                    "bbox": behavior.get("bbox", [0, 0, 0, 0]),
                    "track_id": behavior.get("track_id"),
                    "metadata": {
                        "source": "behavior_recognizer",
                        "behavior_type": "handwashing",
                        **behavior.get("metadata", {}),
                    },
                }
            )

        for behavior in detection_result.sanitize_results:
            objects.append(
                {
                    "class_id": 3,
                    "class_name": "sanitizing",
                    "confidence": behavior.get("confidence", 0.0),
                    "bbox": behavior.get("bbox", [0, 0, 0, 0]),
                    "track_id": behavior.get("track_id"),
                    "metadata": {
                        "source": "behavior_recognizer",
                        "behavior_type": "sanitizing",
                        **behavior.get("metadata", {}),
                    },
                }
            )

        return objects

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 场景1: 单张图片检测
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def process_image_detection(
        self, camera_id: str, image_bytes: bytes, save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        处理单张图片检测

        Args:
            camera_id: 摄像头ID
            image_bytes: 图像字节数据
            save_to_db: 是否保存到数据库（默认True）

        Returns:
            检测结果字典
        """
        self.logger.info(f"开始单张图片检测: camera={camera_id}")

        # 1. 图像解码
        image = self._decode_image(image_bytes)

        # 2. 执行检测（基础设施层）
        start_time = time.time()
        detection_result = self.detection_pipeline.detect_comprehensive(image)
        processing_time = time.time() - start_time

        # 3. 分析违规
        has_violations, violation_severity = self._analyze_violations(detection_result)
        violations_summary = self._extract_violations_summary(detection_result)

        # 4. 转换为领域模型格式
        detected_objects = self._convert_to_domain_format(detection_result)

        # 5. 业务处理（领域层）
        record = None
        snapshot_info: Optional[SnapshotInfo] = None
        if save_to_db:
            # 获取标注后的图片（如果存在）
            annotated_image = (
                detection_result.annotated_image
                if hasattr(detection_result, "annotated_image")
                and detection_result.annotated_image is not None
                else None
            )

            snapshot_info = await self._save_snapshot_if_possible(
                image,
                camera_id,
                violation_type=violations_summary[0]["type"]
                if violations_summary
                else None,
                metadata={
                    "mode": DetectionMode.SINGLE_IMAGE.value,
                    "has_violations": has_violations,
                },
                annotated_image=annotated_image,
            )
            record = await self.detection_domain_service.process_detection(
                camera_id=camera_id,
                detected_objects=detected_objects,
                processing_time=processing_time,
                snapshots=[snapshot_info] if snapshot_info else None,
            )
            detection_id = record.id
            self.logger.info(f"检测记录已保存: {detection_id}")
        else:
            detection_id = f"temp_{int(time.time() * 1000)}"

        # 6. 构建响应
        return {
            "ok": True,
            "mode": DetectionMode.SINGLE_IMAGE.value,
            "camera_id": camera_id,
            "detection_id": detection_id,
            "processing_time": processing_time,
            "result": {
                "person_count": len(detection_result.person_detections),
                "has_violations": has_violations,
                "violation_severity": violation_severity,
                "hairnet_results": detection_result.hairnet_results,
                "handwash_results": detection_result.handwash_results,
                "sanitize_results": detection_result.sanitize_results,
            },
            "quality": record.metadata.get("quality_analysis") if record else None,
            "violations": record.metadata.get("violations", []) if record else [],
            "saved_to_db": save_to_db,
            "snapshots": record.metadata.get("snapshots", []) if record else [],
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 场景3: 实时视频流处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def process_realtime_stream(
        self,
        camera_id: str,
        frame: np.ndarray,
        frame_count: int,
    ) -> Dict[str, Any]:
        """
        处理实时流帧（智能保存版本）

        Args:
            camera_id: 摄像头ID
            frame: 视频帧
            frame_count: 帧计数

        Returns:
            检测结果字典（轻量级）
        """
        # 1. 执行检测（基础设施层）
        start_time = time.time()
        detection_result = self.detection_pipeline.detect_comprehensive(frame)
        processing_time = time.time() - start_time

        # 2. 分析违规
        has_violations, violation_severity = self._analyze_violations(detection_result)

        # 3. 更新统计
        self.stats_buffer["total_frames"] += 1
        if has_violations:
            self.stats_buffer["violation_frames"] += 1
        else:
            self.stats_buffer["normal_frames"] += 1

        # 4. 智能保存决策
        should_save = self._should_save_detection(
            frame_count=frame_count,
            has_violations=has_violations,
            violation_severity=violation_severity,
        )

        # 5. 如果需要保存
        record = None
        snapshot_info: Optional[SnapshotInfo] = None
        if should_save:
            detected_objects = self._convert_to_domain_format(detection_result)

            # 使用 _analyze_violations 的结果获取违规类型（已使用与 ViolationService 相同的逻辑）
            # 这里使用 _get_primary_violation_type 获取违规类型，该方法已使用与 ViolationService 相同的逻辑
            primary_violation_type = self._get_primary_violation_type(detection_result)

            # 保存快照（使用违规类型）
            # 优先使用标注后的图片，这样违规记录中可以显示标注框
            annotated_image = (
                detection_result.annotated_image
                if hasattr(detection_result, "annotated_image")
                and detection_result.annotated_image is not None
                else None
            )

            snapshot_info = await self._save_snapshot_if_possible(
                frame,
                camera_id,
                violation_type=primary_violation_type,
                metadata={
                    "mode": DetectionMode.REALTIME_STREAM.value,
                    "frame_count": frame_count,
                    "has_violations": has_violations,
                },
                annotated_image=annotated_image,
            )

            # 记录快照保存结果
            if snapshot_info:
                self.logger.info(
                    f"快照已保存: camera={camera_id}, frame={frame_count}, "
                    f"relative_path={snapshot_info.relative_path}, "
                    f"violation_type={primary_violation_type}"
                )
            else:
                self.logger.warning(
                    f"快照保存失败: camera={camera_id}, frame={frame_count}, "
                    f"violation_type={primary_violation_type}, "
                    f"snapshot_storage={'已配置' if self.snapshot_storage else '未配置'}"
                )

            # 保存检测记录（传入快照信息）
            record = await self.detection_domain_service.process_detection(
                camera_id=camera_id,
                detected_objects=detected_objects,
                processing_time=processing_time,
                frame_id=frame_count,
                snapshots=[snapshot_info] if snapshot_info else None,
            )

            self.logger.info(
                f"保存检测记录: camera={camera_id}, frame={frame_count}, "
                f"violations={has_violations}, severity={violation_severity:.2f}, "
                f"violation_type={primary_violation_type}, "
                f"has_snapshot={snapshot_info is not None}, "
                f"snapshot_path={snapshot_info.relative_path if snapshot_info else None}"
            )

        # 6. 构建轻量级响应
        return {
            "ok": True,
            "mode": DetectionMode.REALTIME_STREAM.value,
            "camera_id": camera_id,
            "frame_count": frame_count,
            "processing_time": processing_time,
            "fps": 1.0 / processing_time if processing_time > 0 else 0,
            # 检测结果
            "result": {
                "person_count": len(detection_result.person_detections),
                "has_violations": has_violations,
                "violation_severity": violation_severity,
                "persons": [
                    {
                        "bbox": p.get("bbox", [0, 0, 0, 0]),
                        "confidence": p.get("confidence", 0.0),
                        "track_id": p.get("track_id"),
                    }
                    for p in detection_result.person_detections
                ],
                "violations": self._extract_violations_summary(detection_result),
            },
            # 保存状态
            "saved_to_db": should_save,
            "detection_id": record.id if record else None,
            "save_reason": self._get_save_reason(
                frame_count, has_violations, violation_severity, should_save
            ),
            "snapshots": record.metadata.get("snapshots", []) if record else [],
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工厂函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_save_policy_from_env() -> SavePolicy:
    """从环境变量创建保存策略"""
    strategy_str = os.getenv("DETECTION_SAVE_STRATEGY", "smart")
    try:
        strategy = SaveStrategy[strategy_str.upper()]
    except KeyError:
        logger.warning(
            f"Invalid save strategy: {strategy_str}, using default SMART strategy"
        )
        strategy = SaveStrategy.SMART

    return SavePolicy(
        strategy=strategy,
        save_interval=int(os.getenv("DETECTION_SAVE_INTERVAL", "30")),
        normal_sample_interval=int(
            os.getenv("DETECTION_NORMAL_SAMPLE_INTERVAL", "300")
        ),
        save_normal_summary=os.getenv("DETECTION_SAVE_SUMMARY", "true").lower()
        == "true",
        violation_severity_threshold=float(
            os.getenv("DETECTION_VIOLATION_THRESHOLD", "0.5")
        ),
    )

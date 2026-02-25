"""
批量检测管道 - 扩展OptimizedDetectionPipeline支持多帧批处理

主要功能：
1. 多帧批量人体检测
2. 跨帧ROI批处理
3. 批量发网检测
4. 批量行为检测
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.core.batch_processor import (
    BatchPerformanceMonitor,
    BatchResult,
    BatchScheduler,
    BatchUtils,
)
from src.core.optimized_detection_pipeline import DetectionResult, OptimizedDetectionPipeline

logger = logging.getLogger(__name__)


class BatchDetectionPipeline(OptimizedDetectionPipeline):
    """
    批量检测管道 - 支持多帧批处理的检测管道

    继承自OptimizedDetectionPipeline，添加批处理能力
    """

    def __init__(self, *args, **kwargs):
        """初始化批量检测管道"""
        enable_batch_processing = kwargs.pop("enable_batch_processing", True)
        max_batch_size = kwargs.pop("max_batch_size", 16)
        max_wait_time = kwargs.pop("max_wait_time", 0.05)

        super().__init__(*args, **kwargs)

        # 批处理配置
        self.enable_batch_processing = enable_batch_processing
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time  # 50ms

        # 性能监控
        self.batch_monitor = BatchPerformanceMonitor()

        # 批处理调度器（可选，用于异步批处理）
        self.batch_scheduler = None

        logger.info(
            f"批量检测管道初始化完成，批处理: {'启用' if self.enable_batch_processing else '禁用'}, "
            f"最大批大小: {self.max_batch_size}"
        )

    def detect_batch(
        self,
        frames: List[np.ndarray],
        camera_ids: Optional[List[str]] = None,
        batch_size: Optional[int] = None,
        **kwargs,
    ) -> List[DetectionResult]:
        """
        批量检测多帧

        Args:
            frames: 帧列表
            camera_ids: 摄像头ID列表（可选）
            batch_size: 批大小（可选，默认使用self.max_batch_size）
            **kwargs: 其他参数

        Returns:
            检测结果列表
        """
        if not frames:
            return []

        start_time = time.time()

        # 如果禁用批处理，逐帧处理
        if not self.enable_batch_processing or not self._supports_batch_detection():
            return self._detect_frames_sequentially(frames, camera_ids, **kwargs)

        # 确定批大小
        effective_batch_size = batch_size if batch_size is not None else self.max_batch_size
        if effective_batch_size <= 0:
            effective_batch_size = self.max_batch_size

        # 如果帧数小于等于批大小，直接处理
        if len(frames) <= effective_batch_size:
            results = self._detect_frames_batch(frames, camera_ids, batch_size=effective_batch_size, **kwargs)
        else:
            # 分批处理
            results = []
            num_frames = len(frames)
            
            for i in range(0, num_frames, effective_batch_size):
                batch_end = min(i + effective_batch_size, num_frames)
                batch_frames = frames[i:batch_end]
                
                # 分批camera_ids
                batch_camera_ids = None
                if camera_ids:
                    batch_camera_ids = camera_ids[i:batch_end]
                
                # 处理批次
                batch_results = self._detect_frames_batch(
                    batch_frames, batch_camera_ids, batch_size=effective_batch_size, **kwargs
                )
                results.extend(batch_results)
                
                logger.debug(f"检测分批: {batch_end}/{num_frames} 帧")

        # 记录性能
        total_time = time.time() - start_time
        per_frame_time = total_time / len(frames)
        self.batch_monitor.record_batch(len(frames), total_time, per_frame_time)

        return results

    def _supports_batch_detection(self) -> bool:
        """检查是否支持批处理"""
        # 检查人体检测器是否支持批处理
        if not self.human_detector:
            return False

        return hasattr(self.human_detector, "detect_batch")

    def _detect_frames_sequentially(
        self,
        frames: List[np.ndarray],
        camera_ids: Optional[List[str]] = None,
        **kwargs,
    ) -> List[DetectionResult]:
        """逐帧检测（后备方案）"""
        results = []
        num_frames = len(frames)

        for i, frame in enumerate(frames):
            camera_id = camera_ids[i] if camera_ids and i < len(camera_ids) else "default"
            result = self.detect_comprehensive(frame, camera_id=camera_id, **kwargs)
            results.append(result)

        logger.debug(f"逐帧检测完成: {num_frames} 帧")
        return results

    def _detect_frames_batch(
        self,
        frames: List[np.ndarray],
        camera_ids: Optional[List[str]] = None,
        batch_size: Optional[int] = None,
        **kwargs,
    ) -> List[DetectionResult]:
        """
        批量检测多帧（核心逻辑）

        策略：
        1. 批量人体检测
        2. 跨帧批量发网检测
        3. 批量行为检测
        """
        start_time = time.time()
        processing_times = {"total": 0.0}

        # 确定批大小
        effective_batch_size = batch_size if batch_size is not None else self.max_batch_size
        if effective_batch_size <= 0:
            effective_batch_size = self.max_batch_size

        # 阶段1: 批量人体检测
        person_start = time.time()
        all_person_detections = self._batch_detect_persons(frames, batch_size=effective_batch_size)
        processing_times["person_detection"] = time.time() - person_start

        logger.info(
            f"批量人体检测完成: {len(frames)} 帧, "
            f"检测到 {sum(len(d) for d in all_person_detections)} 人"
        )

        # 阶段2: 批量发网检测
        hairnet_start = time.time()
        enable_hairnet = kwargs.get("enable_hairnet", True)
        
        if enable_hairnet:
            all_hairnet_results = self._batch_detect_hairnet(
                frames, all_person_detections
            )
        else:
            # 返回与帧数相同长度的空列表列表
            all_hairnet_results = [[] for _ in frames]

        processing_times["hairnet_detection"] = time.time() - hairnet_start

        logger.debug(
            f"批量发网检测完成: 处理了 {sum(len(r) for r in all_hairnet_results)} 人"
        )

        # 阶段3: 批量行为检测
        behavior_start = time.time()
        enable_handwash = kwargs.get("enable_handwash", True)
        enable_sanitize = kwargs.get("enable_sanitize", True)
        
        if enable_handwash or enable_sanitize:
            all_handwash_results, all_sanitize_results = self._batch_detect_behavior(
                frames, all_person_detections, enable_handwash, enable_sanitize
            )
        else:
            # 返回与帧数相同长度的空列表列表
            all_handwash_results = [[] for _ in frames]
            all_sanitize_results = [[] for _ in frames]

        processing_times["behavior_detection"] = time.time() - behavior_start

        logger.debug(
            f"批量行为检测完成: 洗手={sum(len(r) for r in all_handwash_results)}, "
            f"消毒={sum(len(r) for r in all_sanitize_results)}"
        )

        # 阶段4: 结果组装
        assembly_start = time.time()
        results = []

        for i, frame in enumerate(frames):
            camera_id = camera_ids[i] if camera_ids and i < len(camera_ids) else "default"

            # 创建可视化图片
            min_confidence = 0.5
            if hasattr(self, "params") and self.params is not None:
                human_conf = self.params.human_detection.confidence_threshold
                min_confidence = max(0.5, human_conf)

            annotated_image = self._create_annotated_image(
                frame,
                all_person_detections[i],
                all_hairnet_results[i],
                all_handwash_results[i],
                all_sanitize_results[i],
                hand_regions=None,
                min_confidence=min_confidence,
            )

            result = DetectionResult(
                person_detections=all_person_detections[i],
                hairnet_results=all_hairnet_results[i],
                handwash_results=all_handwash_results[i],
                sanitize_results=all_sanitize_results[i],
                processing_times={},  # 每帧单独的时间可以后续添加
                hand_regions=None,
                annotated_image=annotated_image,
            )
            results.append(result)

        processing_times["assembly"] = time.time() - assembly_start
        processing_times["total"] = time.time() - start_time

        return results

    def _batch_detect_persons(self, frames: List[np.ndarray], batch_size: Optional[int] = None) -> List[List[Dict]]:
        """
        批量人体检测

        Args:
            frames: 帧列表
            batch_size: 批大小（可选，默认使用self.max_batch_size）

        Returns:
            每帧的人体检测结果列表
        """
        if not self.human_detector or not hasattr(self.human_detector, "detect_batch"):
            # 回退到逐帧检测
            return [self._detect_persons(frame) for frame in frames]

        # 确定批大小
        effective_batch_size = batch_size if batch_size is not None else self.max_batch_size
        if effective_batch_size <= 0:
            effective_batch_size = self.max_batch_size

        try:
            # 如果帧数小于等于批大小，直接批量检测
            if len(frames) <= effective_batch_size:
                results = self.human_detector.detect_batch(frames)
                return self._normalize_batch_results(results, len(frames))
            
            # 分批处理
            all_results = []
            num_frames = len(frames)
            
            for i in range(0, num_frames, effective_batch_size):
                batch_frames = frames[i:i + effective_batch_size]
                batch_results = self.human_detector.detect_batch(batch_frames)
                all_results.extend(
                    self._normalize_batch_results(batch_results, len(batch_frames))
                )
                
                logger.debug(f"人体检测分批: {i+len(batch_frames)}/{num_frames} 帧")
            
            return self._normalize_batch_results(all_results, len(frames))
        except Exception as e:
            logger.error(f"批量人体检测失败，回退到逐帧检测: {e}")
            return [self._detect_persons(frame) for frame in frames]

    @staticmethod
    def _normalize_batch_results(
        results: Optional[List[List[Dict]]], expected_len: int
    ) -> List[List[Dict]]:
        """确保批处理结果长度与输入一致."""
        if results is None:
            results = []

        actual_len = len(results)
        if actual_len == expected_len:
            return results

        logger.warning(
            "批处理结果长度不匹配: actual=%s expected=%s, 将进行填充/截断",
            actual_len,
            expected_len,
        )

        if actual_len < expected_len:
            results = results + ([[]] * (expected_len - actual_len))
        else:
            results = results[:expected_len]

        return results

    def _batch_detect_hairnet(
        self,
        frames: List[np.ndarray],
        all_person_detections: List[List[Dict]],
    ) -> List[List[Dict]]:
        """
        批量发网检测

        Args:
            frames: 帧列表
            all_person_detections: 每帧的人体检测结果

        Returns:
            每帧的发网检测结果列表
        """
        all_hairnet_results = [[] for _ in frames]

        # 如果没有发网检测器，返回空结果
        if not self.hairnet_detector:
            return all_hairnet_results

        # 收集所有头部ROI
        all_rois = []
        roi_mappings = []  # (frame_idx, person_idx, bbox)

        for frame_idx, (frame, persons) in enumerate(zip(frames, all_person_detections)):
            for person_idx, person in enumerate(persons):
                bbox = person.get("bbox", [0, 0, 0, 0])
                head_roi = self._get_head_roi(frame, bbox)

                if head_roi is not None and head_roi.size > 0:
                    all_rois.append(head_roi)
                    roi_mappings.append((frame_idx, person_idx, bbox))

        # 如果没有ROI，返回空结果
        if not all_rois:
            return all_hairnet_results

        # 批量发网检测
        hairnet_detections = self._detect_hairnet_for_rois_batch(all_rois)

        # 映射回原始帧
        for mapping, detection in zip(roi_mappings, hairnet_detections):
            frame_idx, person_idx, bbox = mapping
            person = all_person_detections[frame_idx][person_idx]

            # 创建发网检测结果
            hairnet_result = {
                "person_id": person_idx + 1,
                "bbox": bbox,
                "hairnet_confidence": detection.get("confidence", 0.0),
                "has_hairnet": detection.get("has_hairnet", False),
            }
            all_hairnet_results[frame_idx].append(hairnet_result)

        return all_hairnet_results

    def _detect_hairnet_for_rois_batch(
        self, rois: List[np.ndarray]
    ) -> List[Dict]:
        """
        批量发网检测（跨帧ROI）

        Args:
            rois: 头部ROI列表

        Returns:
            发网检测结果列表
        """
        # 如果检测器不支持批处理，逐个检测
        if not hasattr(self.hairnet_detector, "detect_batch"):
            results = []
            for roi in rois:
                result = self.hairnet_detector.detect(roi)
                results.append(result[0] if result else {})
            return results

        # 按尺寸分组ROI（可选优化）
        groups = BatchUtils.group_rois_by_size(rois, max_size_diff=0.3)

        # 批量检测每组
        all_results = [{}] * len(rois)

        for group in groups:
            indices = [idx for idx, _ in group]
            group_rois = [roi for _, roi in group]

            # 批量检测
            try:
                group_results = self.hairnet_detector.detect_batch(group_rois)

                # 映射回原始顺序
                for orig_idx, result in zip(indices, group_results):
                    all_results[orig_idx] = result[0] if result else {}
            except Exception as e:
                logger.error(f"ROI组批处理失败: {e}")
                # 回退到逐个检测
                for idx, roi in group:
                    result = self.hairnet_detector.detect(roi)
                    all_results[idx] = result[0] if result else {}

        return all_results

    def _batch_detect_behavior(
        self,
        frames: List[np.ndarray],
        all_person_detections: List[List[Dict]],
        enable_handwash: bool,
        enable_sanitize: bool,
    ) -> Tuple[List[List[Dict]], List[List[Dict]]]:
        """
        批量行为检测

        Args:
            frames: 帧列表
            all_person_detections: 每帧的人体检测结果
            enable_handwash: 是否启用洗手检测
            enable_sanitize: 是否启用消毒检测

        Returns:
            (所有洗手结果, 所有消毒结果)
        """
        all_handwash_results = [[] for _ in frames]
        all_sanitize_results = [[] for _ in frames]

        # 如果没有行为识别器，返回空结果
        if not self.behavior_recognizer:
            return all_handwash_results, all_sanitize_results

        # 收集所有手部ROI
        all_hand_rois = []
        roi_mappings = []  # (frame_idx, person_idx, bbox, is_left)

        for frame_idx, (frame, persons) in enumerate(zip(frames, all_person_detections)):
            for person_idx, person in enumerate(persons):
                bbox = person.get("bbox", [0, 0, 0, 0])
                hand_regions = self._get_hand_regions(frame, bbox)

                for hand_roi, is_left in hand_regions:
                    if hand_roi is not None and hand_roi.size > 0:
                        all_hand_rois.append(hand_roi)
                        roi_mappings.append((frame_idx, person_idx, bbox, is_left))

        # 批量行为检测（目前DeepBehaviorRecognizer不支持批处理）
        # 这里保持逐个检测，待后续优化
        for mapping in roi_mappings:
            frame_idx, person_idx, bbox, is_left = mapping
            frame = frames[frame_idx]
            person = all_person_detections[frame_idx][person_idx]

            # 行为检测（暂时逐个）
            handwash_result, sanitize_result = self._detect_behavior_for_person(
                frame, person
            )

            if enable_handwash and handwash_result:
                all_handwash_results[frame_idx].append(handwash_result)

            if enable_sanitize and sanitize_result:
                all_sanitize_results[frame_idx].append(sanitize_result)

        return all_handwash_results, all_sanitize_results

    def _detect_behavior_for_person(
        self, frame: np.ndarray, person: Dict
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        单个人体的行为检测

        Args:
            frame: 输入帧
            person: 人体检测结果

        Returns:
            (洗手结果, 消毒结果)
        """
        # 如果有行为识别器，使用它
        if self.behavior_recognizer:
            # 提取运动特征（简化实现）
            motion_data = self._extract_motion_features(frame, person)

            # 更新特征
            self.behavior_recognizer.update_features(motion_data)

            # 预测行为
            predictions = self.behavior_recognizer.predict_behavior()

            handwash_result = (
                {
                    "person_id": person.get("person_id", 0),
                    "handwash_confidence": predictions.get("handwash", 0.0),
                }
                if predictions.get("handwash", 0.0) > 0.5
                else None
            )

            sanitize_result = (
                {
                    "person_id": person.get("person_id", 0),
                    "sanitize_confidence": predictions.get("sanitize", 0.0),
                }
                if predictions.get("sanitize", 0.0) > 0.5
                else None
            )

            return handwash_result, sanitize_result

        return None, None

    def _extract_motion_features(self, frame: np.ndarray, person: Dict) -> Dict:
        """提取运动特征（简化实现）"""
        # 这里应该从帧序列中提取运动特征
        # 简化实现：返回默认值
        return {
            "avg_speed": 0.0,
            "max_speed": 0.0,
            "speed_variance": 0.0,
            "avg_acceleration": 0.0,
            "position_variance_x": 0.0,
            "position_variance_y": 0.0,
            "trajectory_length": 0.0,
            "displacement": 0.0,
            "tortuosity": 0.0,
            "convex_hull_area": 0.0,
            "direction_changes": 0,
            "dominant_frequency_x": 0.0,
            "dominant_frequency_y": 0.0,
            "spectral_centroid_x": 0.0,
            "spectral_centroid_y": 0.0,
            "spectral_rolloff_x": 0.0,
            "spectral_rolloff_y": 0.0,
            "periodicity_score": 0.0,
            "smoothness_index": 0.0,
            "directional_consistency": 0.0,
            "pause_ratio": 0.0,
            "anomaly_score": 0.0,
            "outlier_ratio": 0.0,
        }

    def get_batch_stats(self) -> Dict[str, Any]:
        """获取批处理性能统计"""
        stats = self.batch_monitor.get_stats()
        return stats

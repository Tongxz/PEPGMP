"""
异步检测管道

负责：
1. 异步检测任务管理
2. 并行检测执行
3. 结果聚合
4. 使用FrameMetadata作为数据载体，确保异步结果正确关联
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import numpy as np

from src.core.frame_metadata import FrameMetadata
from src.core.frame_metadata_manager import FrameMetadataManager

logger = logging.getLogger(__name__)


class AsyncDetectionPipeline:
    """异步检测管道 - 使用FrameMetadata作为数据载体

    功能：
    1. 异步检测任务管理
    2. 并行检测执行（发网检测和姿态检测可以并行）
    3. 结果聚合
    4. 通过frame_id确保结果关联
    """

    def __init__(
        self,
        human_detector,
        hairnet_detector,
        pose_detector,
        behavior_recognizer,
        frame_metadata_manager: Optional[FrameMetadataManager] = None,
        max_workers: int = 2,
    ):
        """
        初始化异步检测管道

        Args:
            human_detector: 人体检测器
            hairnet_detector: 发网检测器
            pose_detector: 姿态检测器
            behavior_recognizer: 行为识别器
            frame_metadata_manager: 帧元数据管理器（可选）
            max_workers: 最大并行工作线程数
        """
        self.human_detector = human_detector
        self.hairnet_detector = hairnet_detector
        self.pose_detector = pose_detector
        self.behavior_recognizer = behavior_recognizer
        self.frame_metadata_manager = frame_metadata_manager or FrameMetadataManager()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        logger.info(f"AsyncDetectionPipeline initialized: max_workers={max_workers}")

    async def detect_comprehensive_async(
        self,
        frame_meta: FrameMetadata,
        enable_hairnet: bool = True,
        enable_handwash: bool = True,
        enable_sanitize: bool = True,
    ) -> FrameMetadata:
        """异步综合检测 - 输入和输出都是FrameMetadata

        Args:
            frame_meta: 帧元数据（包含frame_id, timestamp, frame等）
            enable_hairnet: 是否启用发网检测
            enable_handwash: 是否启用洗手检测
            enable_sanitize: 是否启用消毒检测

        Returns:
            更新后的FrameMetadata（包含所有检测结果）
        """
        # 更新处理阶段
        frame_meta = self.frame_metadata_manager.update_processing_stage(
            frame_meta.frame_id, "processing"
        )

        # 阶段1: 人体检测（必须串行，其他检测依赖此结果）
        person_detections = await asyncio.to_thread(
            self._detect_persons_with_frame_id, frame_meta.frame_id, frame_meta.frame
        )

        # 更新检测结果（通过frame_id关联）
        frame_meta = self.frame_metadata_manager.update_detection_results(
            frame_meta.frame_id, person_detections=person_detections
        )

        if not person_detections:
            return self.frame_metadata_manager.update_processing_stage(
                frame_meta.frame_id, "completed"
            )

        # 阶段2-3: 并行执行发网检测和姿态检测
        # 关键：所有异步任务都携带frame_id，确保结果关联
        futures = {}

        if enable_hairnet:
            futures["hairnet"] = asyncio.to_thread(
                self._detect_hairnet_with_frame_id,
                frame_meta.frame_id,
                frame_meta.frame,
                person_detections,
            )

        if self.pose_detector:
            person_bboxes = [det.get("bbox") for det in person_detections]
            futures["pose"] = asyncio.to_thread(
                self._detect_pose_with_frame_id,
                frame_meta.frame_id,
                frame_meta.frame,
                person_bboxes,
            )

        # 等待所有并行任务完成
        results = await asyncio.gather(*futures.values(), return_exceptions=True)

        # 处理结果并更新frame_meta（通过frame_id关联）
        hairnet_results = []
        pose_detections = []

        result_idx = 0
        if "hairnet" in futures:
            if isinstance(results[result_idx], Exception):
                logger.error(f"Hairnet detection failed: {results[result_idx]}")
            else:
                hairnet_results = results[result_idx]
            result_idx += 1

        if "pose" in futures:
            if isinstance(results[result_idx], Exception):
                logger.error(f"Pose detection failed: {results[result_idx]}")
            else:
                pose_detections = results[result_idx]
            result_idx += 1

        frame_meta = self.frame_metadata_manager.update_detection_results(
            frame_meta.frame_id,  # 使用frame_id确保关联
            hairnet_results=hairnet_results,
            pose_detections=pose_detections,
        )

        # 阶段4: 行为检测（依赖姿态检测结果）
        handwash_results = []
        sanitize_results = []

        if (enable_handwash or enable_sanitize) and self.behavior_recognizer:
            if enable_handwash:
                handwash_results = await asyncio.to_thread(
                    self._detect_handwash_with_frame_id,
                    frame_meta.frame_id,
                    person_detections,
                    pose_detections,
                    frame_meta.frame,
                )

            if enable_sanitize:
                sanitize_results = await asyncio.to_thread(
                    self._detect_sanitize_with_frame_id,
                    frame_meta.frame_id,
                    person_detections,
                    pose_detections,
                    frame_meta.frame,
                )

        # 更新行为检测结果
        frame_meta = self.frame_metadata_manager.update_detection_results(
            frame_meta.frame_id,
            handwash_results=handwash_results,
            sanitize_results=sanitize_results,
        )

        return self.frame_metadata_manager.update_processing_stage(
            frame_meta.frame_id, "completed"
        )

    def _detect_persons_with_frame_id(
        self,
        frame_id: str,
        image: np.ndarray,
    ) -> List[Dict]:
        """人体检测（携带frame_id）"""
        if self.human_detector is None:
            return []

        try:
            detections = self.human_detector.detect(image)
            # 在结果中添加frame_id
            for det in detections:
                det["frame_id"] = frame_id
            return detections
        except Exception as e:
            logger.error(f"Person detection failed for frame {frame_id}: {e}")
            return []

    def _detect_hairnet_with_frame_id(
        self,
        frame_id: str,
        image: np.ndarray,
        person_detections: List[Dict],
    ) -> List[Dict]:
        """发网检测（携带frame_id）"""
        if self.hairnet_detector is None:
            return []

        try:
            if hasattr(self.hairnet_detector, "detect_hairnet_compliance"):
                compliance_result = self.hairnet_detector.detect_hairnet_compliance(
                    image, person_detections
                )
                detections = compliance_result.get("detections", [])
            else:
                detections = []

            # 在结果中添加frame_id
            for det in detections:
                det["frame_id"] = frame_id

            return detections
        except Exception as e:
            logger.error(f"Hairnet detection failed for frame {frame_id}: {e}")
            return []

    def _detect_pose_with_frame_id(
        self,
        frame_id: str,
        image: np.ndarray,
        person_bboxes: List[List[int]],
    ) -> List[Dict]:
        """姿态检测（携带frame_id）"""
        if self.pose_detector is None:
            return []

        try:
            # 如果支持ROI检测，使用ROI检测（优化性能）
            if hasattr(self.pose_detector, "detect_in_rois"):
                detections = self.pose_detector.detect_in_rois(image, person_bboxes)
            else:
                # 否则使用全帧检测
                detections = self.pose_detector.detect(image)
                # 如果提供了person_bboxes，可以过滤结果
                if person_bboxes and detections:
                    # 简单过滤：只保留与person_bboxes重叠的检测结果
                    filtered_detections = []
                    for det in detections:
                        det_bbox = det.get("bbox", [0, 0, 0, 0])
                        for person_bbox in person_bboxes:
                            if self._boxes_overlap(det_bbox, person_bbox):
                                filtered_detections.append(det)
                                break
                    detections = filtered_detections

            # 在结果中添加frame_id
            for det in detections:
                det["frame_id"] = frame_id

            return detections
        except Exception as e:
            logger.error(f"Pose detection failed for frame {frame_id}: {e}")
            return []

    def _boxes_overlap(self, box1: List[float], box2: List[float]) -> bool:
        """检查两个边界框是否重叠"""
        try:
            x1_1, y1_1, x2_1, y2_1 = box1
            x1_2, y1_2, x2_2, y2_2 = box2
            return not (x2_1 < x1_2 or x2_2 < x1_1 or y2_1 < y1_2 or y2_2 < y1_1)
        except Exception:
            return False

    def _detect_handwash_with_frame_id(
        self,
        frame_id: str,
        person_detections: List[Dict],
        pose_detections: List[Dict],
        frame: np.ndarray,
    ) -> List[Dict]:
        """洗手检测（携带frame_id）"""
        if self.behavior_recognizer is None:
            return []

        try:
            results = []
            for i, person_det in enumerate(person_detections):
                person_bbox = person_det.get("bbox", [0, 0, 0, 0])
                track_id = person_det.get("track_id", i)

                # 提取手部区域（简化处理）
                hand_regions = []  # 可以从pose_detections中提取

                confidence = self.behavior_recognizer.detect_handwashing(
                    person_bbox,
                    hand_regions,
                    track_id=track_id,
                    frame=frame,
                )

                results.append(
                    {
                        "person_id": i + 1,
                        "track_id": track_id,
                        "person_bbox": person_bbox,
                        "confidence": confidence,
                        "frame_id": frame_id,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Handwash detection failed for frame {frame_id}: {e}")
            return []

    def _detect_sanitize_with_frame_id(
        self,
        frame_id: str,
        person_detections: List[Dict],
        pose_detections: List[Dict],
        frame: np.ndarray,
    ) -> List[Dict]:
        """消毒检测（携带frame_id）"""
        if self.behavior_recognizer is None:
            return []

        try:
            results = []
            for i, person_det in enumerate(person_detections):
                person_bbox = person_det.get("bbox", [0, 0, 0, 0])
                track_id = person_det.get("track_id", i)

                # 提取手部区域（简化处理）
                hand_regions = []  # 可以从pose_detections中提取

                confidence = self.behavior_recognizer.detect_sanitize(
                    person_bbox,
                    hand_regions,
                    track_id=track_id,
                    frame=frame,
                )

                results.append(
                    {
                        "person_id": i + 1,
                        "track_id": track_id,
                        "person_bbox": person_bbox,
                        "confidence": confidence,
                        "frame_id": frame_id,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Sanitize detection failed for frame {frame_id}: {e}")
            return []

    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)
        logger.info("AsyncDetectionPipeline shutdown")

"""
基于 MediaPipe 的姿态关键点提取实现。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.interfaces.services.pose_extractor import PoseExtractorProtocol, PoseSequence

logger = logging.getLogger(__name__)


@dataclass
class MediapipePoseExtractorConfig:
    frame_interval: float = 0.5
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5


class MediapipePoseExtractor(PoseExtractorProtocol):
    """使用 MediaPipe Pose 提取人体关键点。"""

    def __init__(self, config: Optional[MediapipePoseExtractorConfig] = None) -> None:
        self._config = config or MediapipePoseExtractorConfig()

        try:
            from mediapipe import solutions as mp_solutions
        except ImportError as exc:  # pragma: no cover - 运行环境依赖 mediapipe
            raise RuntimeError(
                "未安装 mediapipe 库，无法执行姿态提取。请运行 `pip install mediapipe`。"
            ) from exc

        self._mp_pose = mp_solutions.pose

    def extract_from_video(
        self,
        video_path: Path,
        *,
        frame_interval: float = 0.5,
        start_offset: float = 0.0,
        end_offset: float | None = None,
    ) -> PoseSequence:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        interval = max(frame_interval, 0.05)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total_frames / fps if total_frames > 0 else None

        start_frame = int(max(0.0, start_offset) * fps)
        end_frame = (
            int(min(end_offset, duration) * fps)
            if end_offset is not None and duration is not None
            else total_frames
        )

        frame_step = max(1, int(fps * interval))

        timestamps: list[float] = []
        landmarks: list[np.ndarray] = []

        with self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=self._config.min_detection_confidence,
            min_tracking_confidence=self._config.min_tracking_confidence,
        ) as pose:
            current_frame = 0
            target_frame = start_frame

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if current_frame < start_frame:
                    current_frame += 1
                    continue

                if end_frame and current_frame > end_frame:
                    break

                if current_frame < target_frame:
                    current_frame += 1
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)

                if results.pose_landmarks:
                    landmark_array = self._landmarks_to_array(results.pose_landmarks)
                    landmarks.append(landmark_array)
                    timestamps.append(current_frame / fps)

                target_frame += frame_step
                current_frame += 1

        cap.release()

        if not landmarks:
            logger.warning("未在视频中检测到姿态关键点: %s", video_path)
            return PoseSequence(
                timestamps=np.asarray([], dtype=np.float32),
                landmarks=np.asarray([], dtype=np.float32),
            )

        return PoseSequence(
            timestamps=np.asarray(timestamps, dtype=np.float32),
            landmarks=np.stack(landmarks, axis=0),
        )

    @staticmethod
    def _landmarks_to_array(pose_landmarks) -> np.ndarray:
        coords = []
        for landmark in pose_landmarks.landmark:
            coords.append([landmark.x, landmark.y, landmark.z, landmark.visibility])
        return np.asarray(coords, dtype=np.float32)

"""
MediaPipe检测策略实现
使用MediaPipe进行人体姿态检测
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from src.interfaces.detection.detector_interface import (
    DetectedObject,
    DetectionError,
    DetectionResult,
    IDetector,
)

logger = logging.getLogger(__name__)


class MediaPipeStrategy(IDetector):
    """MediaPipe检测策略"""

    def __init__(self, model_complexity: int = 1, confidence_threshold: float = 0.5):
        """
        初始化MediaPipe策略

        Args:
            model_complexity: 模型复杂度 (0, 1, 2)
            confidence_threshold: 置信度阈值
        """
        self.model_complexity = model_complexity
        self.confidence_threshold = confidence_threshold
        self.pose = None
        self._model_loaded = False

        # MediaPipe支持的类别
        self.class_names = ["person"]

        logger.info(
            f"MediaPipe策略初始化: 复杂度={model_complexity}, 阈值={confidence_threshold}"
        )

    def _load_model(self):
        """延迟加载模型"""
        if self._model_loaded:
            return

        try:
            import mediapipe as mp

            logger.info("加载MediaPipe姿态检测模型")
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=self.model_complexity,
                enable_segmentation=False,
                min_detection_confidence=self.confidence_threshold,
                min_tracking_confidence=0.5,
            )

            self._model_loaded = True
            logger.info("MediaPipe模型加载成功")

        except ImportError as e:
            raise DetectionError(f"MediaPipe依赖未安装: {e}")
        except Exception as e:
            raise DetectionError(f"MediaPipe模型加载失败: {e}")

    async def detect(self, image: np.ndarray) -> DetectionResult:
        """
        检测图像中的人体姿态

        Args:
            image: 输入图像

        Returns:
            DetectionResult: 检测结果
        """
        if not self.is_available():
            raise DetectionError("MediaPipe检测器不可用")

        start_time = time.time()

        try:
            # 确保模型已加载
            self._load_model()

            # 转换图像格式
            import cv2

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 执行检测
            results = self.pose.process(rgb_image)

            # 解析结果
            objects = []
            if results.pose_landmarks:
                # 计算人体边界框
                landmarks = results.pose_landmarks.landmark

                # 获取关键点坐标
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]

                # 计算边界框
                x_min = min(x_coords)
                y_min = min(y_coords)
                x_max = max(x_coords)
                y_max = max(y_coords)

                # 转换为像素坐标
                h, w = image.shape[:2]
                x1 = int(x_min * w)
                y1 = int(y_min * h)
                x2 = int(x_max * w)
                y2 = int(y_max * h)

                # 计算置信度（基于可见关键点的数量）
                visible_landmarks = sum(1 for lm in landmarks if lm.visibility > 0.5)
                confidence = visible_landmarks / len(landmarks)

                if confidence >= self.confidence_threshold:
                    obj = DetectedObject(
                        class_id=0,
                        class_name="person",
                        confidence=confidence,
                        bbox=[float(x1), float(y1), float(x2), float(y2)],
                    )
                    objects.append(obj)

            processing_time = time.time() - start_time

            result = DetectionResult(
                objects=objects,
                processing_time=processing_time,
                timestamp=datetime.now(),
            )

            logger.debug(
                f"MediaPipe检测完成: {len(objects)}个对象, 耗时: {processing_time:.3f}s"
            )
            return result

        except Exception as e:
            logger.error(f"MediaPipe检测失败: {e}")
            raise DetectionError(f"MediaPipe检测失败: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "type": "MediaPipe",
            "model_complexity": self.model_complexity,
            "confidence_threshold": self.confidence_threshold,
            "class_names": self.class_names,
            "loaded": self._model_loaded,
        }

    def is_available(self) -> bool:
        """检查检测器是否可用"""
        try:
            pass

            return True
        except ImportError:
            return False
        except Exception:
            return False

    def get_supported_classes(self) -> List[str]:
        """获取支持的类别列表"""
        return self.class_names.copy()

    def set_confidence_threshold(self, threshold: float) -> None:
        """设置置信度阈值"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("置信度阈值必须在0.0-1.0之间")
        self.confidence_threshold = threshold
        logger.info(f"MediaPipe置信度阈值已更新: {threshold}")

    def get_confidence_threshold(self) -> float:
        """获取当前置信度阈值"""
        return self.confidence_threshold

    def get_detection_statistics(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        return {
            "model_type": "MediaPipe",
            "model_complexity": self.model_complexity,
            "confidence_threshold": self.confidence_threshold,
            "supported_classes": len(self.class_names),
            "model_loaded": self._model_loaded,
        }

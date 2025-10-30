"""
YOLO检测策略实现
使用YOLO模型进行目标检测
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


class YOLOStrategy(IDetector):
    """YOLO检测策略"""

    def __init__(
        self, model_path: str, device: str = "auto", confidence_threshold: float = 0.5
    ):
        """
        初始化YOLO策略

        Args:
            model_path: 模型文件路径
            device: 计算设备 (auto, cpu, cuda, mps)
            confidence_threshold: 置信度阈值
        """
        self.model_path = model_path
        self.device = self._get_device(device)
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.class_names = []

        # 延迟加载模型
        self._model_loaded = False

        logger.info(f"YOLO策略初始化: {model_path}, 设备: {self.device}")

    def _get_device(self, device: str) -> str:
        """获取计算设备"""
        if device == "auto":
            try:
                import torch

                # 优先 MPS (Apple Silicon) → CUDA → CPU
                mps_built = bool(getattr(torch.backends, "mps", None))
                mps_available = mps_built and bool(torch.backends.mps.is_available())
                if mps_available:
                    return "mps"
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        return device

    def _load_model(self):
        """延迟加载模型"""
        if self._model_loaded:
            return

        try:
            from ultralytics import YOLO

            logger.info(f"加载YOLO模型: {self.model_path}")
            self.model = YOLO(self.model_path)

            # 获取类别名称
            if hasattr(self.model, "names"):
                self.class_names = list(self.model.names.values())
            else:
                self.class_names = [
                    "person",
                    "bicycle",
                    "car",
                    "motorcycle",
                    "airplane",
                    "bus",
                    "train",
                    "truck",
                ]

            self._model_loaded = True
            logger.info(f"YOLO模型加载成功，支持类别: {self.class_names}")

        except ImportError as e:
            raise DetectionError(f"YOLO依赖未安装: {e}")
        except Exception as e:
            raise DetectionError(f"YOLO模型加载失败: {e}")

    async def detect(self, image: np.ndarray) -> DetectionResult:
        """
        检测图像中的对象

        Args:
            image: 输入图像

        Returns:
            DetectionResult: 检测结果
        """
        if not self.is_available():
            raise DetectionError("YOLO检测器不可用")

        start_time = time.time()

        try:
            # 确保模型已加载
            self._load_model()

            # 执行检测
            results = self.model(
                image, device=self.device, conf=self.confidence_threshold
            )

            # 解析结果
            objects = []
            for r in results:
                if r.boxes is not None:
                    for box in r.boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())

                        # 获取类别名称
                        class_name = (
                            self.class_names[class_id]
                            if class_id < len(self.class_names)
                            else f"class_{class_id}"
                        )

                        # 创建检测对象
                        obj = DetectedObject(
                            class_id=class_id,
                            class_name=class_name,
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

            logger.debug(f"YOLO检测完成: {len(objects)}个对象, 耗时: {processing_time:.3f}s")
            return result

        except Exception as e:
            logger.error(f"YOLO检测失败: {e}")
            raise DetectionError(f"YOLO检测失败: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "type": "YOLO",
            "model_path": self.model_path,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "class_names": self.class_names,
            "loaded": self._model_loaded,
        }

    def is_available(self) -> bool:
        """检查检测器是否可用"""
        try:
            # 检查依赖是否安装
            # 检查模型文件是否存在
            import os


            if not os.path.exists(self.model_path):
                return False
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def get_supported_classes(self) -> List[str]:
        """获取支持的类别列表"""
        if not self._model_loaded:
            self._load_model()
        return self.class_names.copy()

    def set_confidence_threshold(self, threshold: float) -> None:
        """设置置信度阈值"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("置信度阈值必须在0.0-1.0之间")
        self.confidence_threshold = threshold
        logger.info(f"YOLO置信度阈值已更新: {threshold}")

    def get_confidence_threshold(self) -> float:
        """获取当前置信度阈值"""
        return self.confidence_threshold

    def get_detection_statistics(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        return {
            "model_type": "YOLO",
            "model_path": self.model_path,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "supported_classes": len(self.class_names),
            "model_loaded": self._model_loaded,
        }

from typing import Optional

from fastapi import Request

from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector


def get_optimized_pipeline(request: Request) -> Optional[OptimizedDetectionPipeline]:
    return getattr(request.app.state, "optimized_pipeline", None)


def get_hairnet_pipeline(request: Request) -> Optional[YOLOHairnetDetector]:
    return getattr(request.app.state, "hairnet_pipeline", None)

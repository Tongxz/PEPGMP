"""
模型训练配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelTrainingConfig:
    """模型训练相关配置"""

    output_dir: Path
    report_dir: Path
    test_size: float = 0.2
    random_state: int = 42
    max_iterations: int = 200
    yolo_model: str = "yolov8n-cls.pt"
    yolo_epochs: int = 30
    yolo_image_size: int = 224
    yolo_batch_size: int = 32
    yolo_device: str = "auto"
    yolo_patience: int = 10


def get_model_training_config() -> ModelTrainingConfig:
    """
    从环境变量加载模型训练配置。
    """

    output_dir = Path(os.getenv("MODEL_TRAINING_OUTPUT_DIR", "models/mlops"))
    report_dir = Path(os.getenv("MODEL_TRAINING_REPORT_DIR", "models/mlops/reports"))
    test_size = float(os.getenv("MODEL_TRAINING_TEST_SIZE", "0.2"))
    random_state = int(os.getenv("MODEL_TRAINING_RANDOM_STATE", "42"))
    max_iterations = int(os.getenv("MODEL_TRAINING_MAX_ITER", "200"))
    yolo_model = os.getenv("YOLO_TRAIN_MODEL", "yolov8n-cls.pt")
    yolo_epochs = int(os.getenv("YOLO_TRAIN_EPOCHS", "30"))
    yolo_image_size = int(os.getenv("YOLO_TRAIN_IMAGE_SIZE", "224"))
    yolo_batch_size = int(os.getenv("YOLO_TRAIN_BATCH_SIZE", "32"))
    yolo_device = os.getenv("YOLO_TRAIN_DEVICE", "auto")
    yolo_patience = int(os.getenv("YOLO_TRAIN_PATIENCE", "10"))

    return ModelTrainingConfig(
        output_dir=output_dir,
        report_dir=report_dir,
        test_size=test_size,
        random_state=random_state,
        max_iterations=max_iterations,
        yolo_model=yolo_model,
        yolo_epochs=yolo_epochs,
        yolo_image_size=yolo_image_size,
        yolo_batch_size=yolo_batch_size,
        yolo_device=yolo_device,
        yolo_patience=yolo_patience,
    )

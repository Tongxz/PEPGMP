"""
多行为训练配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MultiBehaviorTrainingConfig:
    output_dir: Path
    report_dir: Path
    yolo_model: str = "yolov8n.pt"
    epochs: int = 50
    image_size: int = 640
    batch_size: int = 16
    device: str = "auto"  # 默认使用auto，允许自动选择设备，可通过环境变量或训练参数覆盖
    patience: int = 15
    validation_split: float = 0.2


def get_multi_behavior_training_config() -> MultiBehaviorTrainingConfig:
    output_dir = Path(
        os.getenv("MULTI_BEHAVIOR_MODEL_DIR", "models/multi_behavior")
    ).expanduser()
    report_dir = Path(
        os.getenv("MULTI_BEHAVIOR_REPORT_DIR", "models/multi_behavior/reports")
    ).expanduser()
    yolo_model = os.getenv("MULTI_BEHAVIOR_YOLO_MODEL", "yolov8n.pt")
    epochs = int(os.getenv("MULTI_BEHAVIOR_EPOCHS", "50"))
    image_size = int(os.getenv("MULTI_BEHAVIOR_IMAGE_SIZE", "640"))
    batch_size = int(os.getenv("MULTI_BEHAVIOR_BATCH_SIZE", "16"))
    # 默认使用auto，允许自动选择设备（MPS → CUDA → CPU）
    # 可以通过环境变量MULTI_BEHAVIOR_DEVICE或工作流training_params.device覆盖
    device = os.getenv("MULTI_BEHAVIOR_DEVICE", "auto")
    patience = int(os.getenv("MULTI_BEHAVIOR_PATIENCE", "15"))
    val_split = float(os.getenv("MULTI_BEHAVIOR_VAL_SPLIT", "0.2"))

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    return MultiBehaviorTrainingConfig(
        output_dir=output_dir,
        report_dir=report_dir,
        yolo_model=yolo_model,
        epochs=epochs,
        image_size=image_size,
        batch_size=batch_size,
        device=device,
        patience=patience,
        validation_split=val_split,
    )

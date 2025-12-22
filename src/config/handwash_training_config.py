"""
洗手训练配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HandwashTrainingConfig:
    output_dir: Path
    report_dir: Path
    epochs: int = 20
    batch_size: int = 8
    learning_rate: float = 1e-3
    device: str = "auto"
    validation_split: float = 0.2
    seed: int = 42


def get_handwash_training_config() -> HandwashTrainingConfig:
    # 生产环境约束：
    # - docker-compose.prod.yml 将 ./models 挂载为只读（/app/models:ro），因此不能把训练/报告写到 models/ 下。
    # - 默认写到 /app/output（命名 volume，可读写持久化）
    if os.getenv("ENVIRONMENT", "development") == "production":
        default_output_dir = "/app/output/handwash"
        default_report_dir = "/app/output/handwash/reports"
    else:
        default_output_dir = "models/handwash"
        default_report_dir = "models/handwash/reports"

    output_dir = Path(
        os.getenv("HANDWASH_TRAINING_OUTPUT_DIR", default_output_dir)
    ).expanduser()
    report_dir = Path(
        os.getenv("HANDWASH_TRAINING_REPORT_DIR", default_report_dir)
    ).expanduser()
    epochs = int(os.getenv("HANDWASH_TRAINING_EPOCHS", "20"))
    batch_size = int(os.getenv("HANDWASH_TRAINING_BATCH_SIZE", "8"))
    learning_rate = float(os.getenv("HANDWASH_TRAINING_LR", "0.001"))
    device = os.getenv("HANDWASH_TRAINING_DEVICE", "auto")
    validation_split = float(os.getenv("HANDWASH_TRAINING_VAL_SPLIT", "0.2"))
    seed = int(os.getenv("HANDWASH_TRAINING_SEED", "42"))

    # 生产环境必需：目录不可写应当显式失败，避免隐性降级
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    return HandwashTrainingConfig(
        output_dir=output_dir,
        report_dir=report_dir,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        device=device,
        validation_split=validation_split,
        seed=seed,
    )

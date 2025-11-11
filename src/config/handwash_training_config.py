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
    output_dir = Path(
        os.getenv("HANDWASH_TRAINING_OUTPUT_DIR", "models/handwash")
    ).expanduser()
    report_dir = Path(
        os.getenv("HANDWASH_TRAINING_REPORT_DIR", "models/handwash/reports")
    ).expanduser()
    epochs = int(os.getenv("HANDWASH_TRAINING_EPOCHS", "20"))
    batch_size = int(os.getenv("HANDWASH_TRAINING_BATCH_SIZE", "8"))
    learning_rate = float(os.getenv("HANDWASH_TRAINING_LR", "0.001"))
    device = os.getenv("HANDWASH_TRAINING_DEVICE", "auto")
    validation_split = float(os.getenv("HANDWASH_TRAINING_VAL_SPLIT", "0.2"))
    seed = int(os.getenv("HANDWASH_TRAINING_SEED", "42"))

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

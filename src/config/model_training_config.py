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


def get_model_training_config() -> ModelTrainingConfig:
    """
    从环境变量加载模型训练配置。
    """

    output_dir = Path(os.getenv("MODEL_TRAINING_OUTPUT_DIR", "models/mlops"))
    report_dir = Path(os.getenv("MODEL_TRAINING_REPORT_DIR", "models/mlops/reports"))
    test_size = float(os.getenv("MODEL_TRAINING_TEST_SIZE", "0.2"))
    random_state = int(os.getenv("MODEL_TRAINING_RANDOM_STATE", "42"))
    max_iterations = int(os.getenv("MODEL_TRAINING_MAX_ITER", "200"))

    return ModelTrainingConfig(
        output_dir=output_dir,
        report_dir=report_dir,
        test_size=test_size,
        random_state=random_state,
        max_iterations=max_iterations,
    )

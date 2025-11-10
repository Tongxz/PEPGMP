"""
模型训练应用服务。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config.model_training_config import ModelTrainingConfig

logger = logging.getLogger(__name__)


@dataclass
class ModelTrainingResult:
    """模型训练结果"""

    model_path: Path
    report_path: Path
    metrics: Dict[str, Any]
    samples_used: int


class ModelTrainingService:
    """基于生成数据集的模型训练服务。"""

    def __init__(self, config: ModelTrainingConfig) -> None:
        self._config = config

    async def train_from_dataset(
        self,
        dataset_dir: Path,
        annotations_file: Optional[Path] = None,
        training_params: Optional[Dict[str, Any]] = None,
    ) -> ModelTrainingResult:
        """
        从指定数据集目录训练分类模型。
        """

        dataset_dir = Path(dataset_dir)
        if annotations_file is None:
            annotations_file = dataset_dir / "annotations.csv"
        else:
            annotations_file = Path(annotations_file)

        if not annotations_file.exists():
            raise FileNotFoundError(f"未找到标注文件: {annotations_file}")

        logger.info("加载数据集: %s", dataset_dir)
        image_paths, labels = self._load_dataset_entries(annotations_file, dataset_dir)

        if len(image_paths) < 2:
            raise ValueError("数据集样本不足，无法训练模型")

        features, valid_indices = self._extract_features(image_paths)
        labels = labels[valid_indices]
        metrics, model = self._train_classifier(
            features,
            labels,
            training_params or {},
        )
        samples_used = int(features.shape[0])

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_filename = f"mlops_model_{timestamp}.joblib"
        report_filename = f"mlops_training_report_{timestamp}.json"

        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        self._config.report_dir.mkdir(parents=True, exist_ok=True)

        model_path = self._config.output_dir / model_filename
        report_path = self._config.report_dir / report_filename

        joblib.dump(model, model_path)
        logger.info("模型已保存: %s", model_path)

        report_content = {
            "dataset_dir": str(dataset_dir),
            "annotations_file": str(annotations_file),
            "samples": samples_used,
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat(),
            "model_path": str(model_path),
            "training_params": training_params or {},
        }

        report_path.write_text(json.dumps(report_content, indent=2, ensure_ascii=False))
        logger.info("训练报告已生成: %s", report_path)

        return ModelTrainingResult(
            model_path=model_path,
            report_path=report_path,
            metrics=metrics,
            samples_used=samples_used,
        )

    def _load_dataset_entries(
        self,
        annotations_file: Path,
        dataset_dir: Path,
    ) -> Tuple[List[Path], np.ndarray]:
        import csv

        image_paths: List[Path] = []
        labels: List[int] = []

        with annotations_file.open("r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                image_rel = row.get("image_path")
                if not image_rel:
                    continue
                image_path = dataset_dir / image_rel
                if not image_path.exists():
                    logger.debug("跳过缺失的图像: %s", image_path)
                    continue
                label = (
                    1
                    if row.get("has_violation") in {"1", "true", "True", "TRUE"}
                    else 0
                )
                image_paths.append(image_path)
                labels.append(label)

        return image_paths, np.asarray(labels, dtype=np.int32)

    def _extract_features(
        self, image_paths: Iterable[Path]
    ) -> Tuple[np.ndarray, List[int]]:
        import cv2

        features: List[np.ndarray] = []
        valid_indices: List[int] = []
        for idx, path in enumerate(image_paths):
            img = cv2.imread(str(path))
            if img is None:
                logger.debug("无法读取图像: %s", path)
                continue
            resized = cv2.resize(img, (64, 64))
            feature_vector = resized.astype(np.float32).reshape(-1) / 255.0
            features.append(feature_vector)
            valid_indices.append(idx)

        if not features:
            raise ValueError("无法从图像中提取特征，检查数据集是否有效")

        return np.stack(features, axis=0), valid_indices

    def _train_classifier(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        training_params: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Pipeline]:
        unique_labels = np.unique(labels)
        if unique_labels.size < 2:
            logger.warning("数据集中只有一个类别，使用 DummyClassifier")
            classifier = DummyClassifier(strategy="most_frequent")
            classifier.fit(features, labels)
            metrics = {
                "strategy": "most_frequent",
                "class": int(unique_labels[0]) if unique_labels.size == 1 else 0,
                "accuracy": 1.0,
            }
            pipeline = Pipeline([("model", classifier)])
            return metrics, pipeline

        test_size = training_params.get("test_size", self._config.test_size)
        random_state = training_params.get("random_state", self._config.random_state)

        X_train, X_val, y_train, y_val = train_test_split(
            features,
            labels,
            test_size=test_size,
            random_state=random_state,
            stratify=labels,
        )

        max_iter = training_params.get("max_iter", self._config.max_iterations)
        C = float(training_params.get("regularization", 1.0))

        pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=max_iter, C=C)),
            ]
        )

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        report = classification_report(
            y_val, y_pred, target_names=["normal", "violation"], output_dict=True
        )

        metrics = {
            "accuracy": accuracy,
            "classification_report": report,
            "train_samples": int(X_train.shape[0]),
            "validation_samples": int(X_val.shape[0]),
        }

        return metrics, pipeline

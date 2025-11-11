"""
模型训练应用服务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from sklearn.model_selection import train_test_split

from src.application.model_registry_service import (
    ModelRegistrationInfo,
    ModelRegistryService,
)
from src.config.model_training_config import ModelTrainingConfig

logger = logging.getLogger(__name__)


@dataclass
class ModelTrainingResult:
    """模型训练结果"""

    model_path: Path
    report_path: Path
    metrics: Dict[str, Any]
    samples_used: int
    version: str
    artifacts: Dict[str, Any]


class ModelTrainingService:
    """基于生成数据集的 YOLO 模型训练服务。"""

    def __init__(
        self,
        config: ModelTrainingConfig,
        model_registry_service: Optional[ModelRegistryService] = None,
    ) -> None:
        self._config = config
        self._model_registry = model_registry_service

    async def train_from_dataset(
        self,
        dataset_dir: Path,
        annotations_file: Optional[Path] = None,
        training_params: Optional[Dict[str, Any]] = None,
        dataset_metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelTrainingResult:
        """
        从指定数据集目录训练深度学习模型（YOLO 分类）。
        """

        dataset_dir = Path(dataset_dir)
        annotations_file = (
            Path(annotations_file)
            if annotations_file is not None
            else dataset_dir / "annotations.csv"
        )

        if not annotations_file.exists():
            raise FileNotFoundError(f"未找到标注文件: {annotations_file}")

        logger.info("加载数据集: %s", dataset_dir)
        image_paths, labels = self._load_dataset_entries(annotations_file, dataset_dir)

        if len(image_paths) < 2:
            raise ValueError("数据集样本不足，无法训练模型")

        training_params = training_params or {}
        logger.info(
            "开始 YOLO 训练，样本数: %s，包含违规样本: %s",
            len(image_paths),
            int(labels.sum()),
        )

        result = await asyncio.to_thread(
            self._run_yolo_training,
            dataset_dir,
            annotations_file,
            image_paths,
            labels,
            training_params,
        )

        if self._model_registry:
            try:
                dataset_info = dataset_metadata or {}
                registration = ModelRegistrationInfo(
                    name=training_params.get(
                        "model_name", f"hairnet_classifier_{result.version}"
                    ),
                    model_type=training_params.get(
                        "model_type", "hairnet_classification"
                    ),
                    version=result.version,
                    model_path=result.model_path,
                    report_path=result.report_path,
                    dataset_id=dataset_info.get("dataset_id"),
                    dataset_path=dataset_info.get("dataset_path"),
                    metrics=result.metrics,
                    artifacts=result.artifacts,
                    training_params=training_params,
                    description=training_params.get("description"),
                )
                await self._model_registry.register_model(registration)
            except Exception as exc:  # pragma: no cover - 注册失败不影响训练
                logger.warning("模型注册失败: %s", exc)

        return result

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

    def _run_yolo_training(
        self,
        dataset_dir: Path,
        annotations_file: Path,
        image_paths: List[Path],
        labels: np.ndarray,
        training_params: Dict[str, Any],
    ) -> ModelTrainingResult:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - ultralytics 在运行时安装
            raise RuntimeError(
                "未安装 ultralytics 库，无法执行 YOLO 训练。请运行 `pip install ultralytics`。"
            ) from exc

        unique_labels = np.unique(labels)
        if unique_labels.size < 2:
            raise ValueError("数据集中只有一个类别，请收集更多正负样本后再训练")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        workspace_dir = dataset_dir / f"yolo_cls_workspace_{timestamp}"
        train_split_dir = workspace_dir / "train"
        val_split_dir = workspace_dir / "val"

        # 准备分类数据集目录结构
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)

        class_mapping = {0: "normal", 1: "violation"}
        train_indices, val_indices = self._split_dataset(labels, training_params)
        self._populate_split(
            train_split_dir, image_paths, labels, train_indices, class_mapping
        )
        self._populate_split(
            val_split_dir, image_paths, labels, val_indices, class_mapping
        )

        # YOLO 训练参数
        model_name = training_params.get("yolo_model", self._config.yolo_model)
        epochs = int(training_params.get("epochs", self._config.yolo_epochs))
        imgsz = int(training_params.get("image_size", self._config.yolo_image_size))
        batch_size = int(
            training_params.get("batch_size", self._config.yolo_batch_size)
        )
        device = training_params.get("device", self._config.yolo_device)
        patience = int(training_params.get("patience", self._config.yolo_patience))
        run_name = training_params.get("run_name", f"hairnet_{timestamp}")

        project_dir = self._config.output_dir / "runs"
        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "加载 YOLO 模型: %s (epochs=%s, imgsz=%s, batch=%s, device=%s)",
            model_name,
            epochs,
            imgsz,
            batch_size,
            device,
        )

        model = YOLO(model_name)
        model.train(
            data=str(workspace_dir),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch_size,
            device=device,
            patience=patience,
            project=str(project_dir),
            name=run_name,
            exist_ok=True,
            verbose=False,
        )

        trainer = getattr(model, "trainer", None)
        save_dir = Path(getattr(trainer, "save_dir", project_dir / run_name))
        best_model_path = Path(getattr(trainer, "best", save_dir / "best.pt"))
        if not best_model_path.exists():
            candidate = save_dir / "best.pt"
            if candidate.exists():
                best_model_path = candidate
            else:
                raise FileNotFoundError(f"未找到 YOLO 最优权重文件: {best_model_path}")

        metrics = self._extract_metrics(trainer, save_dir)
        class_distribution = self._build_class_distribution(labels, class_mapping)

        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        self._config.report_dir.mkdir(parents=True, exist_ok=True)

        model_filename = f"hairnet_yolo_{timestamp}.pt"
        report_filename = f"mlops_training_report_{timestamp}.json"
        target_model_path = self._config.output_dir / model_filename
        report_path = self._config.report_dir / report_filename

        shutil.copy2(best_model_path, target_model_path)
        logger.info("YOLO 模型已保存: %s", target_model_path)

        report_content = {
            "dataset_dir": str(dataset_dir),
            "annotations_file": str(annotations_file),
            "samples": len(image_paths),
            "class_distribution": class_distribution,
            "training_params": {
                "model": model_name,
                "epochs": epochs,
                "image_size": imgsz,
                "batch_size": batch_size,
                "device": device,
                "patience": patience,
                **{
                    k: v
                    for k, v in training_params.items()
                    if k
                    not in {
                        "yolo_model",
                        "epochs",
                        "image_size",
                        "batch_size",
                        "device",
                        "patience",
                    }
                },
            },
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat(),
            "model_path": str(target_model_path),
            "yolo_run_directory": str(save_dir),
        }

        report_path.write_text(json.dumps(report_content, indent=2, ensure_ascii=False))
        logger.info("训练报告已生成: %s", report_path)

        # 清理临时分类数据集目录，保留原始数据集
        shutil.rmtree(workspace_dir, ignore_errors=True)

        return ModelTrainingResult(
            model_path=target_model_path,
            report_path=report_path,
            metrics=metrics,
            samples_used=len(image_paths),
            version=timestamp,
            artifacts={"yolo_run_directory": str(save_dir)},
        )

    def _split_dataset(
        self,
        labels: np.ndarray,
        training_params: Dict[str, Any],
    ) -> Tuple[np.ndarray, np.ndarray]:
        test_size = float(training_params.get("test_size", self._config.test_size))
        random_state = int(
            training_params.get("random_state", self._config.random_state)
        )
        indices = np.arange(labels.shape[0])
        train_indices, val_indices = train_test_split(
            indices,
            test_size=test_size,
            random_state=random_state,
            stratify=labels,
        )
        return train_indices, val_indices

    def _populate_split(
        self,
        split_dir: Path,
        image_paths: Iterable[Path],
        labels: np.ndarray,
        indices: Iterable[int],
        class_mapping: Dict[int, str],
    ) -> None:
        split_dir.mkdir(parents=True, exist_ok=True)
        for idx in indices:
            class_id = int(labels[idx])
            class_name = class_mapping.get(class_id, f"class_{class_id}")
            class_dir = split_dir / class_name
            class_dir.mkdir(parents=True, exist_ok=True)

            source_path = image_paths[idx]
            if not source_path.exists():
                logger.debug("跳过缺失的图像: %s", source_path)
                continue

            destination = class_dir / source_path.name
            if destination.exists():
                destination = (
                    class_dir
                    / f"{source_path.stem}_{uuid.uuid4().hex[:8]}{source_path.suffix}"
                )
            shutil.copy2(source_path, destination)

    def _build_class_distribution(
        self,
        labels: np.ndarray,
        class_mapping: Dict[int, str],
    ) -> Dict[str, int]:
        distribution: Dict[str, int] = {}
        for class_id, class_name in class_mapping.items():
            distribution[class_name] = int(np.sum(labels == class_id))
        return distribution

    def _extract_metrics(
        self,
        trainer: Any,
        save_dir: Path,
    ) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        if trainer is not None:
            trainer_metrics = getattr(trainer, "metrics", None)
            if isinstance(trainer_metrics, dict):
                for key, value in trainer_metrics.items():
                    metrics[key] = self._to_serializable(value)

        results_json = save_dir / "results.json"
        if results_json.exists():
            try:
                results_data = json.loads(results_json.read_text())
                metrics.setdefault("results", results_data)
            except json.JSONDecodeError:
                logger.debug("无法解析 YOLO 结果文件: %s", results_json)

        return metrics

    def _to_serializable(self, value: Any) -> Any:
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:  # pragma: no cover - 安全转换
                return str(value)
        return value

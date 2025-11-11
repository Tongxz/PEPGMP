"""
多行为检测模型训练服务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.config.multi_behavior_training_config import MultiBehaviorTrainingConfig

logger = logging.getLogger(__name__)


@dataclass
class MultiBehaviorTrainingResult:
    model_path: Path
    report_path: Path
    metrics: Dict[str, Any]
    samples_used: int


class MultiBehaviorTrainingService:
    """调用 YOLOv8 进行多行为检测模型训练。"""

    def __init__(self, config: MultiBehaviorTrainingConfig) -> None:
        self._config = config

    async def train(
        self,
        dataset_dir: Path,
        data_config: Optional[Path] = None,
        training_params: Optional[Dict[str, Any]] = None,
    ) -> MultiBehaviorTrainingResult:
        dataset_dir = Path(dataset_dir)
        data_config = (
            Path(data_config) if data_config is not None else dataset_dir / "data.yaml"
        )
        if not data_config.exists():
            raise FileNotFoundError(f"未找到 data.yaml: {data_config}")

        training_params = training_params or {}
        return await asyncio.to_thread(
            self._run_training,
            dataset_dir,
            data_config,
            training_params,
        )

    def _run_training(
        self,
        dataset_dir: Path,
        data_config: Path,
        training_params: Dict[str, Any],
    ) -> MultiBehaviorTrainingResult:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "未安装 ultralytics 库，无法执行多行为训练。请运行 `pip install ultralytics`。"
            ) from exc

        model_name = training_params.get("model", self._config.yolo_model)
        epochs = int(training_params.get("epochs", self._config.epochs))
        imgsz = int(training_params.get("image_size", self._config.image_size))
        batch_size = int(training_params.get("batch_size", self._config.batch_size))
        device = training_params.get("device", self._config.device)
        patience = int(training_params.get("patience", self._config.patience))
        run_name = training_params.get(
            "run_name", f"multi_behavior_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        project_dir = self._config.output_dir / "runs"
        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "开始 YOLO 检测训练: model=%s epochs=%s imgsz=%s batch=%s device=%s",
            model_name,
            epochs,
            imgsz,
            batch_size,
            device,
        )

        model = YOLO(model_name)
        model.train(
            data=str(data_config),
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
                raise FileNotFoundError(f"未找到最优权重文件: {best_model_path}")

        metrics = self._extract_metrics(trainer, save_dir)

        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        self._config.report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_path = self._config.output_dir / f"multi_behavior_{timestamp}.pt"
        report_path = (
            self._config.report_dir / f"multi_behavior_report_{timestamp}.json"
        )

        shutil.copy2(best_model_path, model_path)
        logger.info("多行为模型已保存: %s", model_path)

        dataset_info = json.loads((dataset_dir / "annotations.json").read_text())
        report_content = {
            "dataset_dir": str(dataset_dir),
            "data_config": str(data_config),
            "samples": len(dataset_info),
            "training_params": {
                "model": model_name,
                "epochs": epochs,
                "image_size": imgsz,
                "batch_size": batch_size,
                "device": device,
                "patience": patience,
                **training_params,
            },
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat(),
            "model_path": str(model_path),
        }

        report_path.write_text(json.dumps(report_content, indent=2, ensure_ascii=False))

        return MultiBehaviorTrainingResult(
            model_path=model_path,
            report_path=report_path,
            metrics=metrics,
            samples_used=len(dataset_info),
        )

    def _extract_metrics(self, trainer: Any, save_dir: Path) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        if trainer is not None:
            trainer_metrics = getattr(trainer, "metrics", None)
            if isinstance(trainer_metrics, dict):
                for key, value in trainer_metrics.items():
                    metrics[key] = self._to_serializable(value)

        results_json = save_dir / "results.json"
        if results_json.exists():
            try:
                metrics.setdefault("results", json.loads(results_json.read_text()))
            except json.JSONDecodeError:
                logger.debug("无法解析 YOLO 结果文件: %s", results_json)
        return metrics

    @staticmethod
    def _to_serializable(value: Any) -> Any:
        import numpy as np

        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:  # pragma: no cover
                return str(value)
        return value

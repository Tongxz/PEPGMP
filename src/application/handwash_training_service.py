"""
洗手合规模型训练服务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, random_split

from src.config.handwash_training_config import HandwashTrainingConfig

logger = logging.getLogger(__name__)


@dataclass
class HandwashTrainingResult:
    model_path: Path
    report_path: Path
    metrics: Dict[str, Any]
    samples_used: int


class _HandwashSequenceDataset(Dataset):
    def __init__(self, annotations: List[Dict[str, Any]], root_dir: Path):
        self.annotations = annotations
        self.root_dir = root_dir

    def __len__(self) -> int:
        return len(self.annotations)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        entry = self.annotations[idx]
        skeleton_path = self.root_dir / entry["skeleton_path"]
        array = np.load(skeleton_path, allow_pickle=False)
        # shape: (T, K, D)
        sequence = array.reshape(array.shape[0], -1)  # (T, features)
        sequence_tensor = torch.from_numpy(sequence).float()
        label = torch.tensor(float(entry.get("compliant", False)), dtype=torch.float32)
        return sequence_tensor, label


class _TemporalCNN(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Conv1d(input_dim, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Conv1d(128, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.AdaptiveAvgPool1d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, time, features)
        x = x.transpose(1, 2)  # (batch, features, time)
        features = self.network(x)
        logits = self.classifier(features)
        return logits.squeeze(-1)


class HandwashTrainingService:
    """基于姿态序列的洗手合规训练服务。"""

    def __init__(self, config: HandwashTrainingConfig) -> None:
        self._config = config

    async def train(
        self,
        dataset_dir: Path,
        annotations_file: Optional[Path] = None,
        training_params: Optional[Dict[str, Any]] = None,
    ) -> HandwashTrainingResult:
        dataset_dir = Path(dataset_dir)
        annotations_file = (
            Path(annotations_file)
            if annotations_file is not None
            else dataset_dir / "annotations.json"
        )
        if not annotations_file.exists():
            raise FileNotFoundError(f"未找到标注文件: {annotations_file}")

        training_params = training_params or {}
        return await asyncio.to_thread(
            self._run_training,
            dataset_dir,
            annotations_file,
            training_params,
        )

    def _run_training(
        self,
        dataset_dir: Path,
        annotations_file: Path,
        training_params: Dict[str, Any],
    ) -> HandwashTrainingResult:
        self._set_seed(int(training_params.get("seed", self._config.seed)))
        annotations = json.loads(annotations_file.read_text())
        if not annotations:
            raise ValueError("标注文件为空，无法训练模型")

        dataset = _HandwashSequenceDataset(annotations, dataset_dir)
        val_split = float(
            training_params.get("validation_split", self._config.validation_split)
        )
        val_size = max(1, int(len(dataset) * val_split))
        train_size = len(dataset) - val_size
        train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

        batch_size = int(training_params.get("batch_size", self._config.batch_size))
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True, drop_last=False
        )
        val_loader = DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False, drop_last=False
        )

        sample_sequence, _ = dataset[0]
        input_dim = sample_sequence.shape[1]
        model = _TemporalCNN(input_dim=input_dim)

        device = self._resolve_device(
            training_params.get("device", self._config.device)
        )
        model.to(device)

        criterion = nn.BCEWithLogitsLoss()
        learning_rate = float(
            training_params.get("learning_rate", self._config.learning_rate)
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        epochs = int(training_params.get("epochs", self._config.epochs))
        metrics_log: List[Dict[str, float]] = []
        best_val_loss = float("inf")

        for epoch in range(1, epochs + 1):
            train_loss = self._train_one_epoch(
                model, train_loader, criterion, optimizer, device
            )
            val_loss, val_accuracy = self._evaluate(
                model, val_loader, criterion, device
            )
            metrics_log.append(
                {
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "val_accuracy": val_accuracy,
                }
            )
            logger.info(
                "Epoch %s/%s - train_loss: %.4f val_loss: %.4f val_acc: %.4f",
                epoch,
                epochs,
                train_loss,
                val_loss,
                val_accuracy,
            )
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_weights = model.state_dict()

        model.load_state_dict(best_weights)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_dir = self._config.output_dir
        report_dir = self._config.report_dir
        model_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        model_path = model_dir / f"handwash_tcn_{timestamp}.pt"
        report_path = report_dir / f"handwash_training_report_{timestamp}.json"
        torch.save(model.state_dict(), model_path)

        report_content = {
            "dataset_dir": str(dataset_dir),
            "annotations_file": str(annotations_file),
            "samples": len(dataset),
            "train_samples": train_size,
            "validation_samples": val_size,
            "metrics": {
                "history": metrics_log,
                "best_val_loss": best_val_loss,
                "best_val_accuracy": max(m["val_accuracy"] for m in metrics_log),
            },
            "training_params": {
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "device": device,
                **training_params,
            },
            "generated_at": datetime.utcnow().isoformat(),
            "model_path": str(model_path),
        }

        report_path.write_text(json.dumps(report_content, indent=2, ensure_ascii=False))

        return HandwashTrainingResult(
            model_path=model_path,
            report_path=report_path,
            metrics=report_content["metrics"],
            samples_used=len(dataset),
        )

    @staticmethod
    def _train_one_epoch(model, loader, criterion, optimizer, device) -> float:
        model.train()
        total_loss = 0.0
        for sequences, labels in loader:
            sequences = sequences.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(sequences)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * sequences.size(0)
        return total_loss / len(loader.dataset)

    @staticmethod
    def _evaluate(model, loader, criterion, device) -> Tuple[float, float]:
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for sequences, labels in loader:
                sequences = sequences.to(device)
                labels = labels.to(device)
                logits = model(sequences)
                loss = criterion(logits, labels)
                total_loss += loss.item() * sequences.size(0)
                predictions = torch.sigmoid(logits) > 0.5
                correct += (predictions.float() == labels).sum().item()
                total += labels.numel()
        val_loss = total_loss / len(loader.dataset)
        accuracy = correct / total if total > 0 else 0.0
        return val_loss, accuracy

    def _resolve_device(self, device_setting: str) -> str:
        if device_setting == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device_setting

    @staticmethod
    def _set_seed(seed: int) -> None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

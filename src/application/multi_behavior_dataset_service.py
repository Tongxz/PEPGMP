"""
多行为数据集生成服务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import cv2
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.multi_behavior_dataset_config import MultiBehaviorDatasetConfig
from src.database.dao import DatasetDAO
from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class MultiBehaviorDatasetRequest:
    dataset_name: str
    violation_types: Optional[Sequence[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    camera_ids: Optional[Sequence[str]] = None
    max_records: Optional[int] = None


class MultiBehaviorDatasetGenerationService:
    """生成 YOLO 多类别检测数据集。"""

    def __init__(
        self,
        detection_repository: IDetectionRepository,
        config: MultiBehaviorDatasetConfig,
    ) -> None:
        self._detection_repository = detection_repository
        self._config = config
        self._class_to_id = {name: idx for idx, name in enumerate(config.classes)}

    async def generate_dataset(
        self,
        request: MultiBehaviorDatasetRequest,
        session: AsyncSession,
    ) -> Dict[str, object]:
        dataset_dir = self._prepare_dataset_directory(request.dataset_name)
        images_dir = dataset_dir / "images"
        labels_dir = dataset_dir / "labels"
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        records = await self._collect_detection_records(request)
        entries = self._extract_snapshot_entries(records, request.violation_types)

        if not entries:
            shutil.rmtree(dataset_dir, ignore_errors=True)
            raise ValueError("未找到符合条件的快照，无法生成多行为数据集")

        tasks = []
        annotations: List[Dict[str, object]] = []
        for entry in entries:
            tasks.append(
                asyncio.to_thread(
                    self._process_entry,
                    entry,
                    images_dir,
                    labels_dir,
                    annotations,
                )
            )

        await asyncio.gather(*tasks)

        yaml_data = {
            "path": str(dataset_dir),
            "train": "images/train",
            "val": "images/val",
            "names": {idx: name for name, idx in self._class_to_id.items()},
        }
        (dataset_dir / "data.yaml").write_text(
            json.dumps(yaml_data, indent=2, ensure_ascii=False)
        )
        (dataset_dir / "annotations.json").write_text(
            json.dumps(annotations, indent=2, ensure_ascii=False)
        )

        dataset_size = sum(file.stat().st_size for file in images_dir.rglob("*"))
        dataset = await DatasetDAO.create(
            session,
            {
                "id": f"multibeh_{int(datetime.utcnow().timestamp())}",
                "name": request.dataset_name,
                "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
                "status": "active",
                "size": dataset_size,
                "sample_count": len(annotations),
                "description": "Generated multi-behavior detection dataset",
                "tags": ["multi_behavior", "generated"],
                "file_path": str(dataset_dir),
            },
        )

        return {
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "dataset_path": str(dataset_dir),
            "annotations_path": str(dataset_dir / "annotations.json"),
            "yaml_path": str(dataset_dir / "data.yaml"),
            "samples": len(annotations),
            "size": dataset_size,
        }

    def _prepare_dataset_directory(self, dataset_name: str) -> Path:
        normalized = dataset_name.strip().replace(" ", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dataset_dir = self._config.output_dir / f"{normalized}_{timestamp}"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        (dataset_dir / "images/train").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "images/val").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "labels/train").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "labels/val").mkdir(parents=True, exist_ok=True)
        return dataset_dir

    async def _collect_detection_records(
        self,
        request: MultiBehaviorDatasetRequest,
    ) -> List[Dict]:
        start_time = request.start_time or datetime.utcnow() - timedelta(days=1)
        end_time = request.end_time or datetime.utcnow()
        limit = request.max_records or self._config.max_records

        collected: List[Dict] = []
        camera_ids = request.camera_ids or [None]

        for camera_id in camera_ids:
            records = await self._detection_repository.find_by_time_range(
                start_time=start_time,
                end_time=end_time,
                camera_id=camera_id,
                limit=limit,
            )
            for record in records:
                collected.append(self._normalize_record(record))

        return collected[:limit]

    def _normalize_record(self, record: Any) -> Dict[str, object]:
        if isinstance(record, dict):
            return record
        if hasattr(record, "to_dict"):
            return record.to_dict()
        raise TypeError("不支持的记录类型")

    def _extract_snapshot_entries(
        self,
        records: Iterable[Dict[str, object]],
        violation_filter: Optional[Sequence[str]],
    ) -> List[Dict[str, object]]:
        entries: List[Dict[str, object]] = []
        violation_filter_set = (
            {vf.strip() for vf in violation_filter} if violation_filter else None
        )

        for record in records:
            metadata = record.get("metadata") or {}
            snapshots = metadata.get("snapshots") or []
            if not snapshots:
                continue

            for snapshot in snapshots:
                violation_type = snapshot.get("violation_type")
                if violation_filter_set and violation_type not in violation_filter_set:
                    continue
                source_path = self._config.snapshot_base_dir / snapshot.get(
                    "relative_path", ""
                )
                entries.append(
                    {
                        "record_id": record.get("id"),
                        "camera_id": record.get("camera_id"),
                        "timestamp": record.get("timestamp"),
                        "objects": record.get("objects", []),
                        "source_path": source_path,
                        "relative_path": snapshot.get("relative_path"),
                    }
                )
        return entries

    def _process_entry(
        self,
        entry: Dict[str, object],
        images_dir: Path,
        labels_dir: Path,
        annotations: List[Dict[str, object]],
    ) -> None:
        source: Path = entry["source_path"]  # type: ignore[assignment]
        if not source.exists():
            return

        target_name = f"{entry.get('record_id')}_{Path(entry['relative_path']).name}"
        subset_dir = "train"
        if hash(entry.get("record_id")) % 5 == 0:
            subset_dir = "val"

        image_target = images_dir / subset_dir / target_name
        label_target = labels_dir / subset_dir / f"{Path(target_name).stem}.txt"

        shutil.copy2(source, image_target)

        width, height = self._get_image_size(image_target)
        labels = self._build_labels(entry.get("objects", []), width, height)
        if not labels and not self._config.include_normal:
            image_target.unlink(missing_ok=True)
            return

        label_lines = [
            f"{label['class_id']} {label['x_center']} {label['y_center']} {label['width']} {label['height']}"
            for label in labels
        ]
        label_target.write_text("\n".join(label_lines))

        annotations.append(
            {
                "image": str(image_target.relative_to(images_dir.parent)),
                "label": str(label_target.relative_to(labels_dir.parent)),
                "camera_id": entry.get("camera_id"),
                "timestamp": entry.get("timestamp"),
                "objects": len(labels),
            }
        )

    @staticmethod
    def _get_image_size(image_path: Path) -> tuple[int, int]:
        image = cv2.imread(str(image_path))
        if image is None:
            raise RuntimeError(f"无法读取图像: {image_path}")
        height, width = image.shape[:2]
        return width, height

    def _build_labels(
        self,
        objects: Iterable[Dict[str, object]],
        width: int,
        height: int,
    ) -> List[Dict[str, float]]:
        labels: List[Dict[str, float]] = []
        for obj in objects:
            violation_type = None
            metadata = obj.get("metadata") or {}
            if isinstance(metadata, dict):
                violation_type = metadata.get("violation_type") or metadata.get(
                    "behavior_type"
                )
            violation_type = violation_type or obj.get("class_name")
            if not violation_type:
                continue
            if violation_type not in self._class_to_id:
                continue
            bbox = obj.get("bbox") or metadata.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = bbox
            x_center = ((x1 + x2) / 2) / width
            y_center = ((y1 + y2) / 2) / height
            box_width = abs(x2 - x1) / width
            box_height = abs(y2 - y1) / height
            labels.append(
                {
                    "class_id": self._class_to_id[violation_type],
                    "x_center": x_center,
                    "y_center": y_center,
                    "width": box_width,
                    "height": box_height,
                }
            )
        return labels

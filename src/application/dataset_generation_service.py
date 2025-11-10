"""
数据集生成应用服务。
"""

from __future__ import annotations

import asyncio
import csv
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.dataset_config import DatasetGenerationConfig
from src.database.dao import DatasetDAO
from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
)


@dataclass
class DatasetGenerationRequest:
    """生成数据集请求参数。"""

    dataset_name: str
    camera_ids: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    include_normal_samples: bool = False
    max_records: int = 2000


class DatasetGenerationService:
    """根据检测记录生成可用于训练的数据集。"""

    def __init__(
        self,
        detection_repository: IDetectionRepository,
        config: DatasetGenerationConfig,
    ) -> None:
        self._detection_repository = detection_repository
        self._config = config

    async def generate_dataset(
        self,
        request: DatasetGenerationRequest,
        session: AsyncSession,
    ) -> Dict[str, object]:
        """
        生成数据集并注册到 MLOps 数据集列表。
        """

        dataset_dir = self._prepare_dataset_directory(request.dataset_name)
        images_dir = dataset_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        records = await self._collect_detection_records(request)
        snapshot_entries = self._extract_snapshot_entries(records, request)

        if not snapshot_entries:
            raise ValueError("未找到符合条件的检测快照，无法生成数据集")

        copied_files = await self._copy_snapshots(snapshot_entries, images_dir)
        annotation_path = await self._write_annotations(
            dataset_dir,
            snapshot_entries,
        )

        dataset_size = sum(dest.stat().st_size for _, dest in copied_files)

        dataset_data = {
            "id": f"dataset_{int(datetime.utcnow().timestamp())}",
            "name": request.dataset_name,
            "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            "status": "active",
            "size": dataset_size,
            "description": "Generated from detection snapshots",
            "file_path": str(dataset_dir),
            "tags": ["generated"],
        }

        dataset = await DatasetDAO.create(session, dataset_data)

        return {
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "records": len(snapshot_entries),
            "files_copied": len(copied_files),
            "dataset_path": str(dataset_dir),
            "annotations_path": str(annotation_path),
            "size": dataset_size,
        }

    def _prepare_dataset_directory(self, dataset_name: str) -> Path:
        normalized_name = dataset_name.strip().replace(" ", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dataset_dir = self._config.output_dir / f"{normalized_name}_{timestamp}"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        return dataset_dir

    async def _collect_detection_records(
        self,
        request: DatasetGenerationRequest,
    ) -> List[Dict]:
        start_time = request.start_time or datetime.utcnow() - timedelta(days=1)
        end_time = request.end_time or datetime.utcnow()
        max_records = request.max_records

        collected: List[Dict] = []
        camera_ids = request.camera_ids or [None]

        for camera_id in camera_ids:
            records = await self._detection_repository.find_by_time_range(
                start_time=start_time,
                end_time=end_time,
                camera_id=camera_id,
                limit=max_records,
            )
            for record in records:
                collected.append(self._normalize_record(record))

        return collected

    def _normalize_record(self, record: Any) -> Dict[str, Any]:
        if isinstance(record, dict):
            metadata = record.get("metadata") or {}
            if hasattr(metadata, "to_dict"):
                record["metadata"] = metadata.to_dict()
            return record

        if hasattr(record, "to_dict"):
            try:
                return record.to_dict()
            except AttributeError:
                pass

        metadata = getattr(record, "metadata", {}) or {}
        if hasattr(metadata, "to_dict"):
            metadata = metadata.to_dict()

        timestamp = getattr(record, "timestamp", None)
        if hasattr(timestamp, "isoformat"):
            timestamp_value = timestamp.isoformat()
        elif hasattr(timestamp, "value"):
            timestamp_inner = timestamp.value
            timestamp_value = (
                timestamp_inner.isoformat()
                if hasattr(timestamp_inner, "isoformat")
                else timestamp_inner
            )
        else:
            timestamp_value = timestamp

        confidence = getattr(record, "confidence", 0.0)
        if hasattr(confidence, "value"):
            confidence = confidence.value

        objects = []
        for obj in getattr(record, "objects", []) or []:
            if isinstance(obj, dict):
                objects.append(obj)
            elif hasattr(obj, "to_dict"):
                try:
                    objects.append(obj.to_dict())
                except AttributeError:
                    objects.append(self._object_to_dict(obj))
            else:
                objects.append(self._object_to_dict(obj))

        return {
            "id": getattr(record, "id", None),
            "camera_id": getattr(record, "camera_id", None),
            "objects": objects,
            "timestamp": timestamp_value,
            "confidence": confidence,
            "processing_time": getattr(record, "processing_time", 0.0),
            "frame_id": getattr(record, "frame_id", None),
            "region_id": getattr(record, "region_id", None),
            "metadata": metadata,
        }

    def _object_to_dict(self, obj: Any) -> Dict[str, Any]:
        confidence = getattr(obj, "confidence", 0.0)
        if hasattr(confidence, "value"):
            confidence = confidence.value
        bbox = getattr(obj, "bbox", None)
        if bbox is None and hasattr(obj, "bounding_box"):
            bbox = getattr(obj, "bounding_box")
            if hasattr(bbox, "to_dict"):
                bbox = bbox.to_dict()
        metadata = getattr(obj, "metadata", {}) or {}
        if hasattr(metadata, "to_dict"):
            metadata = metadata.to_dict()
        return {
            "class_id": getattr(obj, "class_id", None),
            "class_name": getattr(obj, "class_name", None),
            "confidence": confidence,
            "bbox": bbox,
            "track_id": getattr(obj, "track_id", None),
            "metadata": metadata,
        }

    def _extract_snapshot_entries(
        self,
        records: Iterable[Dict],
        request: DatasetGenerationRequest,
    ) -> List[Dict[str, object]]:
        entries: List[Dict[str, object]] = []
        for record in records:
            metadata = record.get("metadata") or {}
            snapshots = metadata.get("snapshots") or []
            if not snapshots:
                if request.include_normal_samples:
                    continue
                else:
                    continue

            has_violation = metadata.get("violation_count", 0) > 0
            if not has_violation and not request.include_normal_samples:
                continue

            for snapshot in snapshots:
                entries.append(
                    {
                        "record_id": record.get("id"),
                        "camera_id": record.get("camera_id"),
                        "timestamp": record.get("timestamp"),
                        "violation_type": snapshot.get("violation_type"),
                        "source_path": self._config.snapshot_base_dir
                        / snapshot.get("relative_path", ""),
                        "relative_path": snapshot.get("relative_path"),
                        "metadata": snapshot.get("metadata"),
                        "has_violation": has_violation,
                    }
                )

        return entries

    async def _copy_snapshots(
        self,
        entries: Iterable[Dict[str, object]],
        images_dir: Path,
    ) -> List[tuple[Path, Path]]:
        tasks = []
        copied: List[tuple[Path, Path]] = []

        for entry in entries:
            source: Path = entry["source_path"]
            if not source.exists():
                continue

            target_name = (
                f"{entry.get('record_id')}_{Path(entry['relative_path']).name}"
            )
            target = images_dir / target_name
            entry["dataset_image_name"] = target_name
            tasks.append(
                asyncio.to_thread(
                    shutil.copy2,
                    source,
                    target,
                )
            )
            copied.append((source, target))

        if tasks:
            await asyncio.gather(*tasks)

        return copied

    async def _write_annotations(
        self,
        dataset_dir: Path,
        entries: Iterable[Dict[str, object]],
    ) -> Path:
        annotation_path = dataset_dir / self._config.annotation_filename

        def write_csv() -> None:
            with open(annotation_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    [
                        "image_path",
                        "camera_id",
                        "timestamp",
                        "violation_type",
                        "has_violation",
                        "record_id",
                    ]
                )
                for entry in entries:
                    writer.writerow(
                        [
                            f"images/{entry.get('dataset_image_name', Path(entry['relative_path']).name)}",
                            entry.get("camera_id"),
                            entry.get("timestamp"),
                            entry.get("violation_type"),
                            entry.get("has_violation"),
                            entry.get("record_id"),
                        ]
                    )

        await asyncio.to_thread(write_csv)
        return annotation_path

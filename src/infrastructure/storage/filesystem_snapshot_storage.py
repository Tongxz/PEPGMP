"""
基于本地文件系统的检测帧快照存储实现。
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional

import cv2
import numpy as np

from src.interfaces.storage import SnapshotInfo, SnapshotStorageProtocol


@dataclass
class SnapshotStorageConfig:
    """快照存储配置。"""

    base_dir: Path
    image_format: str = "jpg"
    image_quality: int = 90


class FileSystemSnapshotStorage(SnapshotStorageProtocol):
    """使用本地文件系统持久化检测帧。"""

    def __init__(
        self,
        config: SnapshotStorageConfig,
    ) -> None:
        self._config = config
        self._base_dir = config.base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save_frame(
        self,
        frame: np.ndarray,
        camera_id: str,
        *,
        captured_at: Optional[datetime] = None,
        violation_type: Optional[str] = None,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> SnapshotInfo:
        captured_at = captured_at or datetime.utcnow()
        relative_path = self._build_relative_path(
            camera_id=camera_id,
            captured_at=captured_at,
            violation_type=violation_type,
        )
        absolute_path = self._base_dir / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(
            self._write_image,
            absolute_path,
            frame,
        )

        return SnapshotInfo(
            relative_path=str(relative_path),
            absolute_path=str(absolute_path),
            camera_id=camera_id,
            captured_at=captured_at,
            violation_type=violation_type,
            metadata=metadata,
        )

    def _build_relative_path(
        self,
        *,
        camera_id: str,
        captured_at: datetime,
        violation_type: Optional[str],
    ) -> Path:
        date_path = Path(
            camera_id,
            captured_at.strftime("%Y"),
            captured_at.strftime("%m"),
            captured_at.strftime("%d"),
        )
        filename_parts = [
            captured_at.strftime("%H%M%S"),
            f"{captured_at.microsecond:06d}",
        ]
        if violation_type:
            filename_parts.append(violation_type)
        filename_parts.append(uuid.uuid4().hex[:8])
        filename = "_".join(filename_parts) + f".{self._config.image_format}"
        return date_path / filename

    def _write_image(self, path: Path, frame: np.ndarray) -> None:
        if frame is None or not isinstance(frame, np.ndarray):
            raise ValueError("frame must be a valid numpy.ndarray")

        image_format = self._config.image_format.lower()
        encode_params: list[int] = []
        if image_format in {"jpg", "jpeg"}:
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self._config.image_quality]
        elif image_format == "png":
            encode_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]

        success, buffer = cv2.imencode(f".{image_format}", frame, encode_params)
        if not success:
            raise RuntimeError("failed to encode frame")

        with open(path, "wb") as file:
            file.write(buffer.tobytes())

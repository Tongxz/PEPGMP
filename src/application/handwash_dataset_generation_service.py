"""
洗手数据集生成服务。
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
from typing import Dict, List, Optional, Sequence

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.handwash_dataset_config import HandwashDatasetConfig
from src.database.dao import DatasetDAO
from src.domain.entities.handwash_session import HandwashSession
from src.domain.repositories.handwash_session_repository import (
    IHandwashSessionRepository,
)
from src.interfaces.services.pose_extractor import PoseExtractorProtocol

logger = logging.getLogger(__name__)


@dataclass
class HandwashDatasetRequest:
    dataset_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    camera_ids: Optional[Sequence[str]] = None
    max_sessions: Optional[int] = None
    frame_interval: Optional[float] = None


class HandwashDatasetGenerationService:
    """从洗手会话生成用于时序模型训练的数据集。"""

    def __init__(
        self,
        session_repository: IHandwashSessionRepository,
        pose_extractor: PoseExtractorProtocol,
        config: HandwashDatasetConfig,
    ) -> None:
        self._sessions = session_repository
        self._pose_extractor = pose_extractor
        self._config = config

    async def generate_dataset(
        self,
        request: HandwashDatasetRequest,
        session: AsyncSession,
    ) -> Dict[str, object]:
        dataset_dir = self._prepare_dataset_directory(request.dataset_name)
        skeleton_dir = dataset_dir / "skeletons"
        skeleton_dir.mkdir(parents=True, exist_ok=True)

        sessions = await self._sessions.list_sessions(
            start_time=request.start_time,
            end_time=request.end_time,
            camera_ids=request.camera_ids,
            limit=request.max_sessions or self._config.max_sessions,
        )

        filtered_sessions = [
            s for s in sessions if s.duration >= self._config.min_session_duration
        ]

        if not filtered_sessions:
            raise ValueError("未找到符合条件的洗手会话，无法生成数据集")

        annotations: List[Dict[str, object]] = []
        tasks = []

        for handwash_session in filtered_sessions:
            tasks.append(
                asyncio.to_thread(
                    self._process_session,
                    handwash_session,
                    skeleton_dir,
                    request.frame_interval or self._config.default_frame_interval,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("处理洗手会话失败: %s", result)
                continue
            annotations.extend(result)

        if not annotations:
            shutil.rmtree(dataset_dir, ignore_errors=True)
            raise ValueError("洗手会话未能生成有效序列，请检查数据质量")

        annotation_path = dataset_dir / "annotations.json"
        annotation_path.write_text(
            json.dumps(annotations, indent=2, ensure_ascii=False)
        )

        dataset_size = sum(file.stat().st_size for file in skeleton_dir.glob("*.npy"))
        dataset_id = f"handwash_{int(datetime.utcnow().timestamp())}"
        dataset_data = {
            "id": dataset_id,
            "name": request.dataset_name,
            "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            "status": "active",
            "size": dataset_size,
            "sample_count": len(annotations),
            "description": "Handwash dataset generated from recorded sessions",
            "tags": ["handwash", "generated"],
            "file_path": str(dataset_dir),
        }

        dataset = await DatasetDAO.create(session, dataset_data)

        return {
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "samples": len(annotations),
            "dataset_path": str(dataset_dir),
            "annotations_path": str(annotation_path),
            "size": dataset_size,
        }

    def _prepare_dataset_directory(self, dataset_name: str) -> Path:
        normalized = dataset_name.strip().replace(" ", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dataset_dir = self._config.output_dir / f"{normalized}_{timestamp}"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        return dataset_dir

    def _process_session(
        self,
        session: HandwashSession,
        skeleton_dir: Path,
        frame_interval: float,
    ) -> List[Dict[str, object]]:
        pose_sequence = self._pose_extractor.extract_from_video(
            session.video_path,
            frame_interval=frame_interval,
            start_offset=0.0,
            end_offset=session.duration,
        )

        if pose_sequence.frame_count == 0:
            logger.debug("会话无有效姿态数据: %s", session.session_id)
            return []

        sequence_id = f"seq_{uuid.uuid4().hex}"
        skeleton_path = skeleton_dir / f"{sequence_id}.npy"
        np.save(skeleton_path, pose_sequence.landmarks, allow_pickle=False)

        annotation = {
            "sequence_id": sequence_id,
            "session_id": session.session_id,
            "camera_id": session.camera_id,
            "skeleton_path": f"skeletons/{skeleton_path.name}",
            "frame_count": pose_sequence.frame_count,
            "timestamps": pose_sequence.timestamps.tolist(),
            "steps": [
                {
                    "name": label.step.value,
                    "start": label.start_offset,
                    "end": label.end_offset,
                    "compliant": label.compliant,
                    "metadata": label.metadata or {},
                }
                for label in session.step_labels
            ],
            "compliant": session.is_compliant(),
            "metadata": session.metadata,
        }

        return [annotation]

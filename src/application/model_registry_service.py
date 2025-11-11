"""
模型注册管理服务。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database.connection import AsyncSessionLocal
from src.database.dao import ModelRegistryDAO

logger = logging.getLogger(__name__)


@dataclass
class ModelRegistrationInfo:
    name: str
    model_type: str
    version: str
    model_path: Path
    report_path: Optional[Path] = None
    dataset_id: Optional[str] = None
    dataset_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    training_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    status: str = "active"


class ModelRegistryService:
    """模型注册与查询服务。"""

    async def register_model(self, info: ModelRegistrationInfo) -> Dict[str, Any]:
        """注册新模型并返回记录。"""
        async with AsyncSessionLocal() as session:
            model_id = f"model_{uuid.uuid4().hex[:12]}"
            model_data = {
                "id": model_id,
                "name": info.name,
                "model_type": info.model_type,
                "version": info.version,
                "status": info.status,
                "model_path": str(info.model_path),
                "report_path": str(info.report_path) if info.report_path else None,
                "dataset_id": info.dataset_id,
                "dataset_path": info.dataset_path,
                "metrics": info.metrics,
                "artifacts": info.artifacts,
                "training_params": info.training_params,
                "description": info.description,
            }
            model = await ModelRegistryDAO.create(session, model_data)
            return model.to_dict()

    async def list_models(
        self,
        *,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出模型记录。"""
        async with AsyncSessionLocal() as session:
            models = await ModelRegistryDAO.list_models(
                session,
                model_type=model_type,
                status=status,
                limit=limit,
                offset=offset,
            )
            return [model.to_dict() for model in models]

    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取单个模型记录。"""
        async with AsyncSessionLocal() as session:
            model = await ModelRegistryDAO.get_by_id(session, model_id)
            return model.to_dict() if model else None

    async def update_status(
        self, model_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        """更新模型状态。"""
        async with AsyncSessionLocal() as session:
            model = await ModelRegistryDAO.update(session, model_id, {"status": status})
            return model.to_dict() if model else None

    async def update_model(
        self, model_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新模型信息。"""
        sanitized = dict(update_data)
        if "model_path" in sanitized and isinstance(sanitized["model_path"], Path):
            sanitized["model_path"] = str(sanitized["model_path"])
        if "report_path" in sanitized and isinstance(sanitized["report_path"], Path):
            sanitized["report_path"] = str(sanitized["report_path"])

        async with AsyncSessionLocal() as session:
            model = await ModelRegistryDAO.update(session, model_id, sanitized)
            return model.to_dict() if model else None

    async def delete_model(self, model_id: str) -> bool:
        """删除模型记录。"""
        async with AsyncSessionLocal() as session:
            return await ModelRegistryDAO.delete(session, model_id)

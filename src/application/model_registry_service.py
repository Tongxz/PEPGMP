"""
模型注册管理服务。
"""

from __future__ import annotations

import json
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
            if models:
                return [model.to_dict() for model in models]

        synced = await self._sync_artifacts_from_disk()
        if synced:
            async with AsyncSessionLocal() as session:
                models = await ModelRegistryDAO.list_models(
                    session,
                    model_type=model_type,
                    status=status,
                    limit=limit,
                    offset=offset,
                )
                return [model.to_dict() for model in models]

        return []

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

    async def _sync_artifacts_from_disk(self) -> int:
        """
        从已有的模型工件目录同步缺失的注册记录。

        Returns:
            int: 新增的模型记录数量
        """

        models_root = Path("models/mlops")
        reports_root = models_root / "reports"

        if not reports_root.exists():
            logger.debug("未找到模型报告目录，跳过同步: %s", reports_root)
            return 0

        # 获取已有模型路径，避免重复注册
        async with AsyncSessionLocal() as session:
            existing_models = await ModelRegistryDAO.list_models(
                session, limit=1000, offset=0
            )
            existing_paths = {model.model_path for model in existing_models}

        created = 0
        for report_file in sorted(reports_root.glob("*.json")):
            try:
                payload = json.loads(report_file.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - 防御性
                logger.warning("解析模型报告失败 [%s]: %s", report_file, exc)
                continue

            model_path_str = payload.get("model_path")
            if not model_path_str:
                logger.warning("模型报告缺少 model_path 字段，已跳过: %s", report_file)
                continue

            if model_path_str in existing_paths:
                continue

            model_file = Path(model_path_str)
            if not model_file.is_absolute():
                model_file = Path.cwd() / model_file

            if not model_file.exists():
                logger.warning("模型文件不存在，无法同步: %s", model_file)
                continue

            metrics = payload.get("metrics")
            if not isinstance(metrics, dict):
                metrics = None

            training_params = payload.get("training_params")
            if not isinstance(training_params, dict):
                training_params = None

            dataset_dir = payload.get("dataset_path") or payload.get("dataset_dir")
            dataset_id = payload.get("dataset_id")
            if not dataset_id and dataset_dir:
                dataset_id = Path(dataset_dir).name

            version = payload.get("model_version")
            if not version:
                stem = Path(model_path_str).stem
                version = stem.split("mlops_model_", 1)[-1] if "mlops_model_" in stem else stem

            name = payload.get("model_name") or Path(model_path_str).stem

            model_type = payload.get("model_type")
            if not model_type and training_params:
                model_type = training_params.get("model_type")
            if not model_type:
                model_type = "classification"

            artifacts = payload.get("artifacts")
            if not isinstance(artifacts, dict):
                artifacts = {}
            artifacts.setdefault("report", str(report_file))

            description = payload.get("description")
            status = payload.get("status", "active")

            registration = ModelRegistrationInfo(
                name=name,
                model_type=model_type,
                version=version,
                model_path=Path(model_path_str),
                report_path=report_file,
                dataset_id=dataset_id,
                dataset_path=dataset_dir,
                metrics=metrics,
                artifacts=artifacts,
                training_params=training_params,
                description=description,
                status=status,
            )

            try:
                await self.register_model(registration)
                existing_paths.add(model_path_str)
                created += 1
            except Exception as exc:  # pragma: no cover - 注册失败不影响流程
                logger.warning("同步模型记录失败 [%s]: %s", report_file, exc)

        if created:
            logger.info("已从模型工件目录同步 %s 个模型记录", created)

        return created

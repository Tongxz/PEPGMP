"""
MLOps API路由
提供数据集管理、模型部署、工作流管理等功能
"""

import asyncio
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dataset_generation_service import (
    DatasetGenerationRequest,
    DatasetGenerationService,
)
from src.application.model_registry_service import (
    ModelRegistrationInfo,
    ModelRegistryService,
)
from src.container.service_container import get_service
from src.database.connection import get_async_session
from src.database.dao import DatasetDAO, DeploymentDAO, WorkflowDAO, WorkflowRunDAO

try:
    from src.deployment.docker_manager import DockerManager
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    DockerManager = None  # type: ignore[assignment]

from src.workflow.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mlops", tags=["MLOps"])

if DockerManager is None:
    logger.warning("DockerManager 模块未找到，部署相关接口将不可用")


def _get_docker_manager():
    if DockerManager is None:
        raise HTTPException(
            status_code=503,
            detail="部署管理模块未启用，无法执行此操作",
        )
    return DockerManager()


def _normalize_step_config(step: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(step)
    config = normalized.get("config")
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError:
            logger.warning("步骤配置JSON解析失败，已忽略: %s", config)
            config = {}
    elif not isinstance(config, dict) or config is None:
        config = {}

    dataset_params = normalized.get("dataset_params")
    if isinstance(dataset_params, str):
        try:
            dataset_params = json.loads(dataset_params)
        except json.JSONDecodeError:
            logger.warning("dataset_params JSON解析失败，已忽略: %s", dataset_params)
            dataset_params = {}
    elif dataset_params is None and normalized.get("type") == "dataset_generation":
        dataset_params = dict(config)
    elif not isinstance(dataset_params, dict):
        dataset_params = {}

    if dataset_params:
        camera_ids = dataset_params.get("camera_ids")
        if isinstance(camera_ids, str):
            dataset_params["camera_ids"] = [
                cid.strip() for cid in camera_ids.split(",") if cid.strip()
            ]
        elif isinstance(camera_ids, list):
            dataset_params["camera_ids"] = [
                str(cid).strip() for cid in camera_ids if str(cid).strip()
            ]

        if "max_records" in dataset_params:
            try:
                dataset_params["max_records"] = int(dataset_params["max_records"])
            except (TypeError, ValueError):
                dataset_params["max_records"] = 1000

        normalized["dataset_params"] = dataset_params
        config.update(dataset_params)

    normalized["config"] = config
    return normalized


# 数据模型
class DatasetInfo(BaseModel):
    id: str
    name: str
    version: str
    status: str
    size: int
    sample_count: Optional[int] = None
    label_count: Optional[int] = None
    quality_score: Optional[float] = None
    quality_metrics: Optional[Dict[str, float]] = None
    created_at: str
    updated_at: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DeploymentInfo(BaseModel):
    id: str
    name: str
    model_version: str
    environment: str
    status: str
    replicas: int
    cpu_usage: float
    memory_usage: float
    gpu_usage: Optional[float] = None
    requests_per_minute: int
    avg_response_time: float
    error_rate: float
    total_requests: int
    success_rate: float
    deployed_at: str
    updated_at: str


class WorkflowInfo(BaseModel):
    id: str
    name: str
    type: str
    status: str
    trigger: str
    schedule: Optional[str] = None
    description: str
    steps: List[Dict[str, Any]]
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int
    success_rate: float
    avg_duration: float
    created_at: str
    recent_runs: List[Dict[str, Any]]


class DatasetGenerateRequestModel(BaseModel):
    dataset_name: str
    camera_ids: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    include_normal_samples: bool = False
    max_records: int = 2000


class ModelInfo(BaseModel):
    id: str
    name: str
    model_type: str
    version: str
    status: str
    model_path: str
    report_path: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    training_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ModelRegisterRequest(BaseModel):
    name: str
    model_type: str
    model_path: str
    version: Optional[str] = None
    report_path: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    training_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    status: str = "active"


class ModelStatusUpdate(BaseModel):
    status: str


# 数据集管理API
@router.get("/datasets", response_model=List[DatasetInfo])
async def get_datasets(
    status: Optional[str] = Query(None, description="数据集状态筛选"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取数据集列表"""
    try:
        datasets = await DatasetDAO.get_all(
            session, status=status, limit=limit, offset=offset
        )
        return [dataset.to_dict() for dataset in datasets]
    except Exception as e:
        logger.error(f"获取数据集列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取数据集列表失败")


@router.post("/datasets/upload")
async def upload_dataset(
    files: List[UploadFile] = File(...),
    dataset_name: str = Form(...),
    dataset_type: str = Form("detection"),
    description: str = Form(""),
    session: AsyncSession = Depends(get_async_session),
):
    """上传数据集"""
    try:
        dataset_id = f"dataset_{int(datetime.utcnow().timestamp())}"
        base_dir = Path("data/datasets")
        dataset_dir = base_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []
        total_size = 0

        for file in files:
            file_path = dataset_dir / file.filename
            with file_path.open("wb") as buffer:
                content = await file.read()
                buffer.write(content)
                total_size += len(content)
                uploaded_files.append(file.filename)

        # 保存数据集元数据到数据库
        dataset_data = {
            "id": dataset_id,
            "name": dataset_name,
            "version": "1.0.0",
            "status": "active",
            "size": total_size,
            "description": description,
            "file_path": str(dataset_dir),
            "tags": [dataset_type],
        }

        dataset = await DatasetDAO.create(session, dataset_data)
        logger.info(
            f"数据集上传成功: {dataset_name}, 文件数: {len(uploaded_files)}, 总大小: {total_size}"
        )

        return {
            "message": "数据集上传成功",
            "dataset_id": dataset.id,
            "dataset_name": dataset_name,
            "uploaded_files": uploaded_files,
            "total_size": total_size,
        }
    except Exception as e:
        logger.error(f"数据集上传失败: {e}")
        raise HTTPException(status_code=500, detail="数据集上传失败")


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str, session: AsyncSession = Depends(get_async_session)
):
    """获取数据集详情"""
    try:
        dataset = await DatasetDAO.get_by_id(session, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        return dataset.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据集详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取数据集详情失败")


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """删除数据集"""
    try:
        dataset = await DatasetDAO.get_by_id(session, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")

        dataset_path = Path(dataset.file_path) if dataset.file_path else None

        if dataset_path and dataset_path.exists():
            try:
                await asyncio.to_thread(shutil.rmtree, dataset_path)
                logger.info(f"数据集文件已删除: {dataset_path}")
            except Exception as file_error:
                logger.warning(f"删除数据集文件失败: {file_error}")

        await DatasetDAO.delete(session, dataset_id)
        logger.info(f"数据集删除成功: {dataset_id}")
        return {"message": "数据集删除成功"}
    except Exception as e:
        logger.error(f"数据集删除失败: {e}")
        raise HTTPException(status_code=500, detail="数据集删除失败")


@router.get("/datasets/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    format: str = Query("zip", description="下载格式: zip, tar, individual"),
    session: AsyncSession = Depends(get_async_session),
):
    """下载数据集"""
    try:
        dataset = await DatasetDAO.get_by_id(session, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        dataset_path = Path(dataset.file_path) if dataset.file_path else None
        if not dataset_path or not dataset_path.exists():
            raise HTTPException(status_code=404, detail="数据集文件不存在")

        if format == "zip":
            # 创建ZIP文件
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            zip_path = temp_dir / f"{dataset_id}.zip"

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(dataset_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, dataset_path)
                        zipf.write(file_path, arcname)

            return FileResponse(
                path=zip_path,
                filename=f"{dataset_id}.zip",
                media_type="application/zip",
            )

        elif format == "individual":
            # 返回文件列表，让前端逐个下载
            files = []
            for root, dirs, filenames in os.walk(dataset_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, dataset_path)
                    files.append(
                        {
                            "name": filename,
                            "path": relative_path,
                            "size": os.path.getsize(file_path),
                            "download_url": f"/api/v1/mlops/datasets/{dataset_id}/files/{relative_path}",
                        }
                    )

            return {"files": files}

        else:
            raise HTTPException(status_code=400, detail="不支持的下载格式")

    except Exception as e:
        logger.error(f"数据集下载失败: {e}")
        raise HTTPException(status_code=500, detail="数据集下载失败")


@router.get("/datasets/{dataset_id}/files/{file_path:path}")
async def download_dataset_file(
    dataset_id: str,
    file_path: str,
    session: AsyncSession = Depends(get_async_session),
):
    """下载数据集中的单个文件"""
    try:
        dataset = await DatasetDAO.get_by_id(session, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")

        dataset_path = Path(dataset.file_path) if dataset.file_path else None
        if not dataset_path or not dataset_path.exists():
            raise HTTPException(status_code=404, detail="数据集文件不存在")

        full_path = dataset_path / file_path

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")

        return FileResponse(path=str(full_path), filename=full_path.name)

    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail="文件下载失败")


@router.get("/datasets/{dataset_id}/samples")
async def get_dataset_samples(
    dataset_id: str,
    file_type: Optional[str] = Query("image", description="文件类型筛选: image, all"),
    limit: int = Query(20, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    session: AsyncSession = Depends(get_async_session),
):
    """获取数据集中的样本文件列表（用于预览）"""
    try:
        import csv

        dataset = await DatasetDAO.get_by_id(session, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")

        dataset_path = Path(dataset.file_path) if dataset.file_path else None
        if not dataset_path or not dataset_path.exists():
            raise HTTPException(status_code=404, detail="数据集文件不存在")

        # 读取标注文件
        annotations_file = dataset_path / "annotations.csv"
        annotations_map: Dict[str, Dict[str, Any]] = {}
        if annotations_file.exists():
            try:
                with annotations_file.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        image_path = row.get("image_path", "")
                        if image_path:
                            # 标准化路径（统一使用 / 分隔符）
                            normalized_path = image_path.replace("\\", "/")
                            annotations_map[normalized_path] = {
                                "has_violation": row.get("has_violation", "False").lower()
                                in ("true", "1", "yes"),
                                "violation_type": row.get("violation_type", ""),
                                "camera_id": row.get("camera_id", ""),
                                "timestamp": row.get("timestamp", ""),
                                "record_id": row.get("record_id", ""),
                            }
            except Exception as e:
                logger.warning(f"读取标注文件失败: {e}")

        # 支持的图片格式
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}

        samples = []
        for root, dirs, filenames in os.walk(dataset_path):
            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(dataset_path)

                # 筛选文件类型
                if file_type == "image":
                    if file_path.suffix.lower() not in image_extensions:
                        continue

                # 跳过 annotations.csv 等非样本文件
                if filename in {"annotations.csv", "data.yaml"} or filename.startswith("."):
                    continue

                # 标准化路径用于匹配标注
                normalized_path = str(relative_path).replace("\\", "/")
                annotation = annotations_map.get(normalized_path, {})

                sample_data = {
                    "name": filename,
                    "path": normalized_path,
                    "size": file_path.stat().st_size,
                    "url": f"/api/v1/mlops/datasets/{dataset_id}/files/{relative_path.as_posix()}",
                    "has_violation": annotation.get("has_violation", False),
                    "violation_type": annotation.get("violation_type", ""),
                    "camera_id": annotation.get("camera_id", ""),
                    "timestamp": annotation.get("timestamp", ""),
                    "record_id": annotation.get("record_id", ""),
                }
                samples.append(sample_data)

        # 排序并分页
        samples.sort(key=lambda x: x["name"])
        total = len(samples)
        paginated_samples = samples[offset : offset + limit]

        return {
            "samples": paginated_samples,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据集样本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取数据集样本失败")


@router.post("/datasets/generate")
async def generate_dataset(
    request: DatasetGenerateRequestModel,
    session: AsyncSession = Depends(get_async_session),
):
    """根据检测快照生成数据集"""
    try:
        dataset_service = get_service(DatasetGenerationService)
        generation_request = DatasetGenerationRequest(
            dataset_name=request.dataset_name,
            camera_ids=request.camera_ids,
            start_time=request.start_time,
            end_time=request.end_time,
            include_normal_samples=request.include_normal_samples,
            max_records=request.max_records,
        )
        result = await dataset_service.generate_dataset(
            generation_request,
            session,
        )
        return result
    except Exception as e:
        logger.error(f"生成数据集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成数据集失败: {e}")


# 模型注册管理 API
@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    model_type: Optional[str] = Query(None, description="模型类型筛选"),
    status: Optional[str] = Query(None, description="模型状态筛选"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
):
    try:
        service = get_service(ModelRegistryService)
        models = await service.list_models(
            model_type=model_type, status=status, limit=limit, offset=offset
        )
        return models
    except ValueError:
        raise HTTPException(status_code=503, detail="模型注册服务不可用")
    except Exception as exc:
        logger.error("获取模型列表失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取模型列表失败")


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    try:
        service = get_service(ModelRegistryService)
        model = await service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="模型不存在")
        return model
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=503, detail="模型注册服务不可用")
    except Exception as exc:
        logger.error("获取模型详情失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取模型详情失败")


@router.post("/models/register", response_model=ModelInfo)
async def register_model(payload: ModelRegisterRequest):
    try:
        service = get_service(ModelRegistryService)
        version = payload.version or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        registration = ModelRegistrationInfo(
            name=payload.name,
            model_type=payload.model_type,
            version=version,
            model_path=Path(payload.model_path),
            report_path=Path(payload.report_path) if payload.report_path else None,
            dataset_id=payload.dataset_id,
            dataset_path=payload.dataset_path,
            metrics=payload.metrics,
            artifacts=payload.artifacts,
            training_params=payload.training_params,
            description=payload.description,
            status=payload.status,
        )
        model = await service.register_model(registration)
        return model
    except ValueError:
        raise HTTPException(status_code=503, detail="模型注册服务不可用")
    except Exception as exc:
        logger.error("注册模型失败: %s", exc)
        raise HTTPException(status_code=500, detail="注册模型失败")


@router.post("/models/{model_id}/status", response_model=ModelInfo)
async def update_model_status(model_id: str, request: ModelStatusUpdate):
    try:
        service = get_service(ModelRegistryService)
        model = await service.update_status(model_id, request.status)
        if not model:
            raise HTTPException(status_code=404, detail="模型不存在")
        return model
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=503, detail="模型注册服务不可用")
    except Exception as exc:
        logger.error("更新模型状态失败: %s", exc)
        raise HTTPException(status_code=500, detail="更新模型状态失败")


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    try:
        service = get_service(ModelRegistryService)
        deleted = await service.delete_model(model_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="模型不存在")
        return {"message": "模型删除成功"}
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=503, detail="模型注册服务不可用")
    except Exception as exc:
        logger.error("删除模型失败: %s", exc)
        raise HTTPException(status_code=500, detail="删除模型失败")


# 模型部署管理API
@router.get("/deployments", response_model=List[DeploymentInfo])
async def get_deployments(session: AsyncSession = Depends(get_async_session)):
    """获取部署列表"""
    try:
        deployments = await DeploymentDAO.get_all(session)
        return [deployment.to_dict() for deployment in deployments]
    except Exception as e:
        logger.error(f"获取部署列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取部署列表失败")


@router.post("/deployments")
async def create_deployment(
    deployment: Dict[str, Any], session: AsyncSession = Depends(get_async_session)
):
    """创建部署"""
    try:
        # 生成部署ID
        deployment_id = f"deployment_{int(datetime.utcnow().timestamp())}"
        deployment["id"] = deployment_id

        # 设置默认值
        deployment.setdefault("image", "pyt-api:latest")
        deployment.setdefault("environment", "production")
        deployment.setdefault("replicas", 1)
        deployment.setdefault("status", "deploying")

        # 保存到数据库
        deployment_obj = await DeploymentDAO.create(session, deployment)
        logger.info(f"数据库记录创建成功: {deployment_obj.id}")

        # 创建真实的Docker部署
        docker_manager = _get_docker_manager()
        docker_result = await docker_manager.create_deployment(deployment)

        if docker_result["success"]:
            # 更新数据库状态
            await DeploymentDAO.update(
                session,
                deployment_id,
                {"status": "running", "deployment_config": docker_result},
            )

            logger.info(f"✅ 部署创建成功: {deployment_obj.name}")
            return {
                "message": "部署创建成功",
                "deployment_id": deployment_obj.id,
                "status": "running",
                "containers": docker_result.get("containers", []),
            }
        else:
            # 更新数据库状态为失败
            await DeploymentDAO.update(
                session,
                deployment_id,
                {
                    "status": "error",
                    "deployment_config": {"error": docker_result.get("error", "未知错误")},
                },
            )

            logger.error(f"❌ Docker部署创建失败: {docker_result.get('error')}")
            raise HTTPException(
                status_code=500, detail=f"部署创建失败: {docker_result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建部署失败: {e}")
        raise HTTPException(status_code=500, detail="创建部署失败")


@router.put("/deployments/{deployment_id}/scale")
async def scale_deployment(
    deployment_id: str,
    replicas: int,
    session: AsyncSession = Depends(get_async_session),
):
    """扩缩容部署"""
    try:
        # 检查部署是否存在
        deployment = await DeploymentDAO.get_by_id(session, deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="部署不存在")

        # 执行Docker扩缩容
        docker_manager = _get_docker_manager()
        scale_result = await docker_manager.scale_deployment(deployment_id, replicas)

        if scale_result["success"]:
            # 更新数据库
            await DeploymentDAO.update(
                session,
                deployment_id,
                {"replicas": replicas, "updated_at": datetime.utcnow()},
            )

            logger.info(f"✅ 扩缩容成功: {deployment_id} -> {replicas} 副本")
            return {
                "message": "扩缩容成功",
                "deployment_id": deployment_id,
                "replicas": replicas,
            }
        else:
            logger.error(f"❌ 扩缩容失败: {scale_result.get('error')}")
            raise HTTPException(
                status_code=500, detail=f"扩缩容失败: {scale_result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扩缩容失败: {e}")
        raise HTTPException(status_code=500, detail="扩缩容失败")


@router.put("/deployments/{deployment_id}")
async def update_deployment(
    deployment_id: str,
    deployment: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
):
    """更新部署"""
    try:
        # 更新数据库中的部署信息
        updated_deployment = await DeploymentDAO.update(
            session, deployment_id, deployment
        )
        if not updated_deployment:
            raise HTTPException(status_code=404, detail="部署不存在")

        logger.info(f"更新部署 {deployment_id}: {deployment}")
        return {"message": "部署更新成功", "deployment_id": deployment_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新部署失败: {e}")
        raise HTTPException(status_code=500, detail="更新部署失败")


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: str, session: AsyncSession = Depends(get_async_session)
):
    """删除部署"""
    try:
        # 检查部署是否存在
        deployment = await DeploymentDAO.get_by_id(session, deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="部署不存在")

        # 执行Docker删除
        docker_manager = _get_docker_manager()
        delete_result = await docker_manager.delete_deployment(deployment_id)

        if delete_result["success"]:
            # 从数据库删除记录
            await DeploymentDAO.delete(session, deployment_id)

            logger.info(f"✅ 部署删除成功: {deployment_id}")
            return {"message": "部署删除成功", "deployment_id": deployment_id}
        else:
            logger.error(f"❌ 部署删除失败: {delete_result.get('error')}")
            raise HTTPException(
                status_code=500, detail=f"部署删除失败: {delete_result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除部署失败: {e}")
        raise HTTPException(status_code=500, detail="删除部署失败")


# 工作流管理API
@router.get("/workflows", response_model=List[WorkflowInfo])
async def get_workflows(session: AsyncSession = Depends(get_async_session)):
    """获取工作流列表"""
    try:
        workflows = await WorkflowDAO.get_all(session)
        result = []
        for workflow in workflows:
            # 获取最近运行记录
            recent_runs = await WorkflowRunDAO.get_by_workflow_id(
                session, workflow.id, limit=5
            )
            workflow_dict = workflow.to_dict()
            workflow_dict["recent_runs"] = [run.to_dict() for run in recent_runs]
            result.append(workflow_dict)
        return result
    except Exception as e:
        logger.error(f"获取工作流列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取工作流列表失败")


@router.post("/workflows")
async def create_workflow(
    workflow: Dict[str, Any], session: AsyncSession = Depends(get_async_session)
):
    """创建工作流"""
    try:
        # 生成工作流ID
        workflow_id = f"workflow_{int(datetime.utcnow().timestamp())}"
        workflow["id"] = workflow_id

        # 设置默认值
        workflow.setdefault("status", "inactive")
        workflow.setdefault("trigger", "manual")
        workflow.setdefault("run_count", 0)
        workflow.setdefault("success_rate", 0.0)
        workflow.setdefault("avg_duration", 0.0)

        steps = workflow.get("steps", [])
        workflow["steps"] = [_normalize_step_config(step) for step in steps]

        # 保存到数据库
        workflow_obj = await WorkflowDAO.create(session, workflow)
        logger.info(f"数据库记录创建成功: {workflow_obj.id}")

        # 创建工作流引擎实例
        engine_result = await workflow_engine.create_workflow(workflow)

        if engine_result["success"]:
            # 更新数据库状态
            await WorkflowDAO.update(
                session,
                workflow_id,
                {"status": "active", "workflow_config": engine_result},
            )

            logger.info(f"✅ 工作流创建成功: {workflow_obj.name}")
            return {
                "message": "工作流创建成功",
                "workflow_id": workflow_obj.id,
                "status": "active",
                "engine_status": engine_result.get("status", "created"),
            }
        else:
            # 更新数据库状态为失败
            await WorkflowDAO.update(
                session,
                workflow_id,
                {
                    "status": "error",
                    "workflow_config": {"error": engine_result.get("error", "未知错误")},
                },
            )

            logger.error(f"❌ 工作流引擎创建失败: {engine_result.get('error')}")
            raise HTTPException(
                status_code=500, detail=f"工作流创建失败: {engine_result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工作流失败: {e}")
        raise HTTPException(status_code=500, detail="创建工作流失败")


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
):
    """更新工作流"""
    try:
        # 如果工作流状态从 active 变为 inactive，且工作流正在运行，先停止运行
        if "status" in workflow:
            new_status = workflow["status"]
            if new_status == "inactive":
                # 检查工作流是否正在运行
                try:
                    stop_result = await workflow_engine.stop_workflow(workflow_id)
                    if stop_result.get("success"):
                        logger.info(f"工作流 {workflow_id} 正在运行，已停止")
                except Exception as e:
                    logger.warning(f"停止工作流 {workflow_id} 失败（可能未在运行）: {e}")
        
        if "steps" in workflow:
            workflow["steps"] = [
                _normalize_step_config(step) for step in workflow.get("steps", [])
            ]

        # 更新数据库中的工作流信息
        updated_workflow = await WorkflowDAO.update(session, workflow_id, workflow)
        if not updated_workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")

        logger.info(f"更新工作流 {workflow_id}: {workflow}")
        return {"message": "工作流更新成功", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工作流失败: {e}")
        raise HTTPException(status_code=500, detail="更新工作流失败")


@router.post("/workflows/{workflow_id}/run")
async def run_workflow(
    workflow_id: str, session: AsyncSession = Depends(get_async_session)
):
    """运行工作流"""
    try:
        # 检查工作流是否存在
        workflow = await WorkflowDAO.get_by_id(session, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在")

        # 创建工作流运行记录
        run_data = {
            "id": f"run_{int(datetime.utcnow().timestamp())}",
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": datetime.utcnow(),
            "run_config": workflow.to_dict(),
        }

        run_record = await WorkflowRunDAO.create(session, run_data)
        logger.info(f"工作流运行记录创建成功: {run_record.id}")

        # 执行工作流
        workflow_dict = workflow.to_dict()
        workflow_dict["steps"] = [
            _normalize_step_config(step) for step in workflow_dict.get("steps", [])
        ]
        engine_result = await workflow_engine.run_workflow(workflow_id, workflow_dict)

        if engine_result["success"]:
            # 更新运行记录状态
            outputs_json = json.dumps(
                engine_result.get("outputs", []), ensure_ascii=False
            )
            await WorkflowRunDAO.finish_run(
                session,
                run_record.id,
                "success",
                additional_data={
                    "run_log": outputs_json,
                },
            )

            # 更新工作流统计
            await WorkflowDAO.update(
                session,
                workflow_id,
                {"run_count": workflow.run_count + 1, "last_run": datetime.utcnow()},
            )

            logger.info(f"✅ 工作流运行成功: {workflow_id}")
            return {
                "message": "工作流运行成功",
                "workflow_id": workflow_id,
                "run_id": run_record.id,
                "status": "success",
                "outputs": engine_result.get("outputs", []),
            }
        else:
            # 更新运行记录状态为失败
            outputs_json = json.dumps(
                engine_result.get("outputs", []), ensure_ascii=False
            )
            await WorkflowRunDAO.finish_run(
                session,
                run_record.id,
                "failed",
                engine_result.get("error"),
                additional_data={"run_log": outputs_json},
            )

            logger.error(f"❌ 工作流运行失败: {engine_result.get('error')}")
            raise HTTPException(
                status_code=500, detail=f"工作流运行失败: {engine_result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行工作流失败: {e}")
        raise HTTPException(status_code=500, detail="运行工作流失败")


@router.post("/workflows/{workflow_id}/stop")
async def stop_workflow(workflow_id: str):
    """停止正在运行的工作流"""
    try:
        result = await workflow_engine.stop_workflow(workflow_id)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "停止工作流失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止工作流失败: {e}")
        raise HTTPException(status_code=500, detail="停止工作流失败")


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """删除工作流"""
    try:
        # 如果工作流正在运行，先停止
        try:
            await workflow_engine.stop_workflow(workflow_id)
        except Exception:
            pass  # 如果停止失败，继续删除
        
        # 这里应该从工作流引擎删除
        logger.info(f"删除工作流: {workflow_id}")
        return {"message": "工作流删除成功"}
    except Exception as e:
        logger.error(f"删除工作流失败: {e}")
        raise HTTPException(status_code=500, detail="删除工作流失败")


# 健康检查
@router.get("/health")
async def health_check():
    """MLOps服务健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "dataset_manager": "healthy",
            "deployment_manager": "healthy",
            "workflow_manager": "healthy",
        },
    }

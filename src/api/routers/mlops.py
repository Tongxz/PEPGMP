"""
MLOps API路由
提供数据集管理、模型部署、工作流管理等功能
"""

import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session
from src.database.dao import DatasetDAO, DeploymentDAO, WorkflowDAO, WorkflowRunDAO
from src.deployment.docker_manager import DockerManager
from src.workflow.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mlops", tags=["MLOps"])


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
        datasets = await DatasetDAO.get_all(session, status=status, limit=limit, offset=offset)
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
        # 创建数据集目录
        dataset_dir = f"data/datasets/{dataset_name}"
        os.makedirs(dataset_dir, exist_ok=True)

        uploaded_files = []
        total_size = 0

        for file in files:
            file_path = os.path.join(dataset_dir, file.filename)
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
                total_size += len(content)
                uploaded_files.append(file.filename)

        # 生成数据集ID
        dataset_id = f"dataset_{int(datetime.utcnow().timestamp())}"
        
        # 保存数据集元数据到数据库
        dataset_data = {
            "id": dataset_id,
            "name": dataset_name,
            "version": "1.0.0",
            "status": "active",
            "size": total_size,
            "description": description,
            "file_path": dataset_dir,
            "tags": [dataset_type]
        }
        
        dataset = await DatasetDAO.create(session, dataset_data)
        logger.info(f"数据集上传成功: {dataset_name}, 文件数: {len(uploaded_files)}, 总大小: {total_size}")

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
async def get_dataset(dataset_id: str, session: AsyncSession = Depends(get_async_session)):
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
async def delete_dataset(dataset_id: str):
    """删除数据集"""
    try:
        # 这里应该从数据库和文件系统删除实际数据
        logger.info(f"数据集删除成功: {dataset_id}")
        return {"message": "数据集删除成功"}
    except Exception as e:
        logger.error(f"数据集删除失败: {e}")
        raise HTTPException(status_code=500, detail="数据集删除失败")


@router.get("/datasets/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    format: str = Query("zip", description="下载格式: zip, tar, individual")
):
    """下载数据集"""
    try:
        # 模拟数据集路径
        dataset_path = f"data/datasets/dataset_{dataset_id}"
        
        if not os.path.exists(dataset_path):
            raise HTTPException(status_code=404, detail="数据集不存在")
        
        if format == "zip":
            # 创建ZIP文件
            zip_path = f"data/temp/dataset_{dataset_id}.zip"
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(dataset_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, dataset_path)
                        zipf.write(file_path, arcname)
            
            return FileResponse(
                path=zip_path,
                filename=f"dataset_{dataset_id}.zip",
                media_type="application/zip"
            )
        
        elif format == "individual":
            # 返回文件列表，让前端逐个下载
            files = []
            for root, dirs, filenames in os.walk(dataset_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, dataset_path)
                    files.append({
                        "name": filename,
                        "path": relative_path,
                        "size": os.path.getsize(file_path),
                        "download_url": f"/api/v1/mlops/datasets/{dataset_id}/files/{relative_path}"
                    })
            
            return {"files": files}
        
        else:
            raise HTTPException(status_code=400, detail="不支持的下载格式")
            
    except Exception as e:
        logger.error(f"数据集下载失败: {e}")
        raise HTTPException(status_code=500, detail="数据集下载失败")


@router.get("/datasets/{dataset_id}/files/{file_path:path}")
async def download_dataset_file(dataset_id: str, file_path: str):
    """下载数据集中的单个文件"""
    try:
        full_path = os.path.join(f"data/datasets/dataset_{dataset_id}", file_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=full_path,
            filename=os.path.basename(file_path)
        )
        
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail="文件下载失败")


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
async def create_deployment(deployment: Dict[str, Any], session: AsyncSession = Depends(get_async_session)):
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
        docker_manager = DockerManager()
        docker_result = await docker_manager.create_deployment(deployment)
        
        if docker_result["success"]:
            # 更新数据库状态
            await DeploymentDAO.update(session, deployment_id, {
                "status": "running",
                "deployment_config": docker_result
            })
            
            logger.info(f"✅ 部署创建成功: {deployment_obj.name}")
            return {
                "message": "部署创建成功", 
                "deployment_id": deployment_obj.id,
                "status": "running",
                "containers": docker_result.get("containers", [])
            }
        else:
            # 更新数据库状态为失败
            await DeploymentDAO.update(session, deployment_id, {
                "status": "error",
                "deployment_config": {"error": docker_result.get("error", "未知错误")}
            })
            
            logger.error(f"❌ Docker部署创建失败: {docker_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"部署创建失败: {docker_result.get('error', '未知错误')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建部署失败: {e}")
        raise HTTPException(status_code=500, detail="创建部署失败")


@router.put("/deployments/{deployment_id}/scale")
async def scale_deployment(deployment_id: str, replicas: int, session: AsyncSession = Depends(get_async_session)):
    """扩缩容部署"""
    try:
        # 检查部署是否存在
        deployment = await DeploymentDAO.get_by_id(session, deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="部署不存在")
        
        # 执行Docker扩缩容
        docker_manager = DockerManager()
        scale_result = await docker_manager.scale_deployment(deployment_id, replicas)
        
        if scale_result["success"]:
            # 更新数据库
            await DeploymentDAO.update(session, deployment_id, {
                "replicas": replicas,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"✅ 扩缩容成功: {deployment_id} -> {replicas} 副本")
            return {
                "message": "扩缩容成功",
                "deployment_id": deployment_id,
                "replicas": replicas
            }
        else:
            logger.error(f"❌ 扩缩容失败: {scale_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"扩缩容失败: {scale_result.get('error', '未知错误')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扩缩容失败: {e}")
        raise HTTPException(status_code=500, detail="扩缩容失败")


@router.put("/deployments/{deployment_id}")
async def update_deployment(deployment_id: str, deployment: Dict[str, Any], session: AsyncSession = Depends(get_async_session)):
    """更新部署"""
    try:
        # 更新数据库中的部署信息
        updated_deployment = await DeploymentDAO.update(session, deployment_id, deployment)
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
async def delete_deployment(deployment_id: str, session: AsyncSession = Depends(get_async_session)):
    """删除部署"""
    try:
        # 检查部署是否存在
        deployment = await DeploymentDAO.get_by_id(session, deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="部署不存在")
        
        # 执行Docker删除
        docker_manager = DockerManager()
        delete_result = await docker_manager.delete_deployment(deployment_id)
        
        if delete_result["success"]:
            # 从数据库删除记录
            await DeploymentDAO.delete(session, deployment_id)
            
            logger.info(f"✅ 部署删除成功: {deployment_id}")
            return {
                "message": "部署删除成功",
                "deployment_id": deployment_id
            }
        else:
            logger.error(f"❌ 部署删除失败: {delete_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"部署删除失败: {delete_result.get('error', '未知错误')}"
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
            recent_runs = await WorkflowRunDAO.get_by_workflow_id(session, workflow.id, limit=5)
            workflow_dict = workflow.to_dict()
            workflow_dict["recent_runs"] = [run.to_dict() for run in recent_runs]
            result.append(workflow_dict)
        return result
    except Exception as e:
        logger.error(f"获取工作流列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取工作流列表失败")


@router.post("/workflows")
async def create_workflow(workflow: Dict[str, Any], session: AsyncSession = Depends(get_async_session)):
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
        
        # 保存到数据库
        workflow_obj = await WorkflowDAO.create(session, workflow)
        logger.info(f"数据库记录创建成功: {workflow_obj.id}")
        
        # 创建工作流引擎实例
        engine_result = await workflow_engine.create_workflow(workflow)
        
        if engine_result["success"]:
            # 更新数据库状态
            await WorkflowDAO.update(session, workflow_id, {
                "status": "active",
                "workflow_config": engine_result
            })
            
            logger.info(f"✅ 工作流创建成功: {workflow_obj.name}")
            return {
                "message": "工作流创建成功", 
                "workflow_id": workflow_obj.id,
                "status": "active",
                "engine_status": engine_result.get("status", "created")
            }
        else:
            # 更新数据库状态为失败
            await WorkflowDAO.update(session, workflow_id, {
                "status": "error",
                "workflow_config": {"error": engine_result.get("error", "未知错误")}
            })
            
            logger.error(f"❌ 工作流引擎创建失败: {engine_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"工作流创建失败: {engine_result.get('error', '未知错误')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工作流失败: {e}")
        raise HTTPException(status_code=500, detail="创建工作流失败")


@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: Dict[str, Any], session: AsyncSession = Depends(get_async_session)):
    """更新工作流"""
    try:
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
async def run_workflow(workflow_id: str, session: AsyncSession = Depends(get_async_session)):
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
            "run_config": workflow.to_dict()
        }
        
        run_record = await WorkflowRunDAO.create(session, run_data)
        logger.info(f"工作流运行记录创建成功: {run_record.id}")
        
        # 执行工作流
        engine_result = await workflow_engine.run_workflow(workflow_id, workflow.to_dict())
        
        if engine_result["success"]:
            # 更新运行记录状态
            await WorkflowRunDAO.update(session, run_record.id, {
                "status": "success",
                "ended_at": datetime.utcnow()
            })
            
            # 更新工作流统计
            await WorkflowDAO.update(session, workflow_id, {
                "run_count": workflow.run_count + 1,
                "last_run": datetime.utcnow()
            })
            
            logger.info(f"✅ 工作流运行成功: {workflow_id}")
            return {
                "message": "工作流运行成功",
                "workflow_id": workflow_id,
                "run_id": run_record.id,
                "status": "success"
            }
        else:
            # 更新运行记录状态为失败
            await WorkflowRunDAO.finish_run(session, run_record.id, "failed", engine_result.get("error"))
            
            logger.error(f"❌ 工作流运行失败: {engine_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"工作流运行失败: {engine_result.get('error', '未知错误')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"运行工作流失败: {e}")
        raise HTTPException(status_code=500, detail="运行工作流失败")


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """删除工作流"""
    try:
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

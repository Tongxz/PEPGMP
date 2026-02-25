"""
Task management API endpoints for PEPGMP background task processing.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from src.api.schemas.tasks import (
    BatchTaskCreateRequest,
    BatchTaskResponse,
    TaskCancelRequest,
    TaskCancelResponse,
    TaskCreateRequest,
    TaskFilter,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskStatusResponse,
    TaskType,
    VideoProcessingConfig,
    WorkflowParameters,
    DatasetConfig,
    TrainingConfig,
)
from src.worker.celery_app import celery_app
from src.worker.tasks import (
    batch_process_videos,
    generate_dataset,
    health_check,
    process_video,
    run_detection_workflow,
    train_model,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 内存中的任务状态跟踪（生产环境应该使用Redis）
_task_store: Dict[str, Dict[str, Any]] = {}


def _create_task_response(task_id: str, task_type: TaskType, async_result: AsyncResult) -> TaskResponse:
    """创建任务响应对象"""
    task_info = async_result.info if async_result.info else {}
    
    # 获取任务状态
    celery_status = async_result.status
    status_map = {
        'PENDING': TaskStatus.PENDING,
        'STARTED': TaskStatus.STARTED,
        'RETRY': TaskStatus.RETRY,
        'FAILURE': TaskStatus.FAILURE,
        'SUCCESS': TaskStatus.SUCCESS,
        'REVOKED': TaskStatus.REVOKED,
        'PROGRESS': TaskStatus.PROGRESS,
    }
    
    task_status = status_map.get(celery_status, TaskStatus.PENDING)
    
    # 获取进度
    progress = None
    if task_status == TaskStatus.PROGRESS:
        meta = async_result.info if async_result.info else {}
        if isinstance(meta, dict) and 'current' in meta and 'total' in meta:
            progress = meta['current'] / meta['total']
    
    # 获取结果
    result = None
    if task_status == TaskStatus.SUCCESS:
        result = async_result.result
    
    # 获取错误信息
    error = None
    if task_status == TaskStatus.FAILURE:
        error = str(async_result.info) if async_result.info else "任务执行失败"
    
    return TaskResponse(
        task_id=task_id,
        task_type=task_type,
        status=task_status,
        created_at=datetime.now(),
        started_at=async_result.date_started,
        completed_at=async_result.date_done,
        result=result,
        error=error,
        progress=progress,
    )


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(request: TaskCreateRequest) -> TaskResponse:
    """
    创建新的后台任务
    
    Args:
        request: 任务创建请求
        
    Returns:
        创建的任务响应
    """
    logger.info(f"创建任务: {request.task_type}")
    
    try:
        task_id = str(uuid.uuid4())
        
        # 根据任务类型调用相应的Celery任务
        if request.task_type == TaskType.HEALTH_CHECK:
            async_result = health_check.apply_async(task_id=task_id)
            
        elif request.task_type == TaskType.VIDEO_PROCESSING:
            # 提取视频处理参数
            video_path = request.parameters.get("video_path")
            if not video_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="视频处理任务需要video_path参数"
                )
            config = request.parameters.get("config", {})
            async_result = process_video.apply_async(
                args=[video_path, config],
                task_id=task_id
            )
            
        elif request.task_type == TaskType.WORKFLOW_EXECUTION:
            # 提取工作流参数
            workflow_id = request.parameters.get("workflow_id")
            if not workflow_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="工作流执行任务需要workflow_id参数"
                )
            parameters = request.parameters.get("parameters", {})
            async_result = run_detection_workflow.apply_async(
                args=[workflow_id, parameters],
                task_id=task_id
            )
            
        elif request.task_type == TaskType.BATCH_PROCESSING:
            # 提取批量处理参数
            video_paths = request.parameters.get("video_paths", [])
            if not video_paths:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="批量处理任务需要video_paths参数"
                )
            config = request.parameters.get("config", {})
            async_result = batch_process_videos.apply_async(
                args=[video_paths, config],
                task_id=task_id
            )
            
        elif request.task_type == TaskType.DATASET_GENERATION:
            # 提取数据集生成参数
            dataset_config = request.parameters.get("dataset_config", {})
            output_dir = request.parameters.get("output_dir")
            if not output_dir:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="数据集生成任务需要output_dir参数"
                )
            async_result = generate_dataset.apply_async(
                args=[dataset_config, output_dir],
                task_id=task_id
            )
            
        elif request.task_type == TaskType.MODEL_TRAINING:
            # 提取模型训练参数
            training_config = request.parameters.get("training_config", {})
            dataset_path = request.parameters.get("dataset_path")
            if not dataset_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="模型训练任务需要dataset_path参数"
                )
            async_result = train_model.apply_async(
                args=[training_config, dataset_path],
                task_id=task_id
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的任务类型: {request.task_type}"
            )
        
        # 存储任务信息
        _task_store[task_id] = {
            "task_type": request.task_type,
            "async_result": async_result,
            "created_at": datetime.now(),
        }
        
        # 返回任务响应
        return _create_task_response(task_id, request.task_type, async_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态响应
    """
    logger.info(f"查询任务状态: {task_id}")
    
    try:
        # 从Celery获取任务结果
        async_result = AsyncResult(task_id, app=celery_app)
        
        # 获取任务类型
        task_type = TaskType.HEALTH_CHECK  # 默认值
        if task_id in _task_store:
            task_type = _task_store[task_id]["task_type"]
        
        # 创建响应
        task_response = _create_task_response(task_id, task_type, async_result)
        
        return TaskStatusResponse(
            task_id=task_response.task_id,
            status=task_response.status,
            progress=task_response.progress,
            result=task_response.result,
            error=task_response.error,
            created_at=task_response.created_at,
            updated_at=datetime.now(),
        )
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(task_id: str, request: TaskCancelRequest) -> TaskCancelResponse:
    """
    取消任务
    
    Args:
        task_id: 任务ID
        request: 取消请求
        
    Returns:
        取消响应
    """
    logger.info(f"取消任务: {task_id}, force={request.force}")
    
    try:
        # 从Celery获取任务结果
        async_result = AsyncResult(task_id, app=celery_app)
        
        # 尝试取消任务
        if request.force:
            # 强制取消（立即终止）
            celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')
            cancelled = True
            message = "任务已强制取消"
        else:
            # 正常取消
            celery_app.control.revoke(task_id, terminate=False)
            cancelled = True
            message = "任务已取消"
        
        return TaskCancelResponse(
            task_id=task_id,
            cancelled=cancelled,
            message=message,
        )
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {str(e)}"
        )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    task_type: Optional[TaskType] = Query(None, description="任务类型"),
    status: Optional[TaskStatus] = Query(None, description="任务状态"),
    limit: int = Query(100, le=1000, description="限制数量"),
    offset: int = Query(0, description="偏移量"),
) -> TaskListResponse:
    """
    列出任务
    
    Args:
        task_type: 任务类型过滤
        status: 任务状态过滤
        limit: 限制数量
        offset: 偏移量
        
    Returns:
        任务列表响应
    """
    logger.info(f"列出任务: type={task_type}, status={status}, limit={limit}, offset={offset}")
    
    try:
        # 获取所有任务
        tasks: List[TaskResponse] = []
        
        # 这里应该从Redis或数据库获取任务列表
        # 暂时返回空列表，因为Celery没有提供直接获取所有任务的方法
        
        return TaskListResponse(
            tasks=tasks,
            total=len(tasks),
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit,
            total_pages=1 if len(tasks) == 0 else (len(tasks) + limit - 1) // limit,
        )
        
    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出任务失败: {str(e)}"
        )


@router.post("/tasks/batch", response_model=BatchTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_tasks(request: BatchTaskCreateRequest) -> BatchTaskResponse:
    """
    创建批量任务
    
    Args:
        request: 批量任务创建请求
        
    Returns:
        批量任务响应
    """
    logger.info(f"创建批量任务: {len(request.tasks)}个任务, parallel={request.parallel}")
    
    try:
        batch_id = str(uuid.uuid4())
        task_responses: List[TaskResponse] = []
        
        # 创建所有任务
        for task_request in request.tasks:
            try:
                # 创建单个任务
                task_response = await create_task(task_request)
                task_responses.append(task_response)
            except Exception as e:
                logger.error(f"创建批量任务中的单个任务失败: {e}")
                # 创建失败的任务响应
                task_responses.append(TaskResponse(
                    task_id=str(uuid.uuid4()),
                    task_type=task_request.task_type,
                    status=TaskStatus.FAILURE,
                    created_at=datetime.now(),
                    error=str(e),
                ))
        
        # 统计成功和失败的任务数
        successful_tasks = sum(1 for t in task_responses if t.status == TaskStatus.SUCCESS or t.status == TaskStatus.PENDING)
        failed_tasks = len(task_responses) - successful_tasks
        
        return BatchTaskResponse(
            batch_id=batch_id,
            tasks=task_responses,
            total_tasks=len(task_responses),
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            created_at=datetime.now(),
        )
        
    except Exception as e:
        logger.error(f"创建批量任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建批量任务失败: {str(e)}"
        )


@router.post("/tasks/video/process", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def process_video_task(
    video_path: str,
    config: Optional[VideoProcessingConfig] = None,
) -> TaskResponse:
    """
    创建视频处理任务（简化接口）
    
    Args:
        video_path: 视频文件路径
        config: 视频处理配置
        
    Returns:
        任务响应
    """
    logger.info(f"创建视频处理任务: {video_path}")
    
    try:
        # 创建任务请求
        task_request = TaskCreateRequest(
            task_type=TaskType.VIDEO_PROCESSING,
            parameters={
                "video_path": video_path,
                "config": config.dict() if config else {},
            },
        )
        
        # 调用通用创建接口
        return await create_task(task_request)
        
    except Exception as e:
        logger.error(f"创建视频处理任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建视频处理任务失败: {str(e)}"
        )


@router.post("/tasks/workflow/execute", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def execute_workflow_task(
    workflow_id: str,
    parameters: Optional[WorkflowParameters] = None,
) -> TaskResponse:
    """
    创建工作流执行任务（简化接口）
    
    Args:
        workflow_id: 工作流ID
        parameters: 工作流参数
        
    Returns:
        任务响应
    """
    logger.info(f"创建工作流执行任务: {workflow_id}")
    
    try:
        # 创建任务请求
        task_request = TaskCreateRequest(
            task_type=TaskType.WORKFLOW_EXECUTION,
            parameters={
                "workflow_id": workflow_id,
                "parameters": parameters.dict() if parameters else {},
            },
        )
        
        # 调用通用创建接口
        return await create_task(task_request)
        
    except Exception as e:
        logger.error(f"创建工作流执行任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工作流执行任务失败: {str(e)}"
        )


@router.get("/tasks/health", response_model=Dict[str, Any])
async def health_check_task() -> Dict[str, Any]:
    """
    执行健康检查任务
    
    Returns:
        健康检查结果
    """
    logger.info("执行健康检查任务")
    
    try:
        # 创建任务请求
        task_request = TaskCreateRequest(
            task_type=TaskType.HEALTH_CHECK,
        )
        
        # 调用通用创建接口
        task_response = await create_task(task_request)
        
        # 等待任务完成（避免阻塞事件循环）
        async_result = AsyncResult(task_response.task_id, app=celery_app)
        result = await run_in_threadpool(async_result.get, timeout=10)
        
        return {
            "task_id": task_response.task_id,
            "status": task_response.status.value,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"执行健康检查任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行健康检查任务失败: {str(e)}"
        )

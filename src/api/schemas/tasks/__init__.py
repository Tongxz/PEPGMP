# Task schemas for PEPGMP API
# 任务相关的数据模型

from .task_schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskStatusResponse,
    BatchTaskCreateRequest,
    BatchTaskResponse,
    TaskCancelRequest,
    TaskCancelResponse,
    TaskListResponse,
    TaskFilter,
    TaskProgress,
    VideoProcessingConfig,
    WorkflowParameters,
    DatasetConfig,
    TrainingConfig,
    TaskType,
    TaskStatus,
)

__all__ = [
    "TaskCreateRequest",
    "TaskResponse",
    "TaskStatusResponse",
    "BatchTaskCreateRequest",
    "BatchTaskResponse",
    "TaskCancelRequest",
    "TaskCancelResponse",
    "TaskListResponse",
    "TaskFilter",
    "TaskProgress",
    "VideoProcessingConfig",
    "WorkflowParameters",
    "DatasetConfig",
    "TrainingConfig",
    "TaskType",
    "TaskStatus",
]
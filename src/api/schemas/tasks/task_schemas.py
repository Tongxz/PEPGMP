"""
Task schemas for PEPGMP background task processing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """任务类型枚举"""
    VIDEO_PROCESSING = "video_processing"
    WORKFLOW_EXECUTION = "workflow_execution"
    BATCH_PROCESSING = "batch_processing"
    DATASET_GENERATION = "dataset_generation"
    MODEL_TRAINING = "model_training"
    HEALTH_CHECK = "health_check"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    STARTED = "STARTED"
    RETRY = "RETRY"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    REVOKED = "REVOKED"
    PROGRESS = "PROGRESS"


class VideoProcessingConfig(BaseModel):
    """视频处理配置"""
    model_name: Optional[str] = Field(default="handwash_detector", description="模型名称")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度阈值")
    output_format: str = Field(default="json", description="输出格式")
    save_video: bool = Field(default=False, description="是否保存处理后的视频")
    save_annotations: bool = Field(default=True, description="是否保存标注")


class WorkflowParameters(BaseModel):
    """工作流参数"""
    workflow_id: str = Field(description="工作流ID")
    steps: List[str] = Field(default_factory=list, description="工作流步骤")
    timeout: Optional[int] = Field(default=300, description="超时时间（秒）")
    retry_count: int = Field(default=3, description="重试次数")


class DatasetConfig(BaseModel):
    """数据集配置"""
    dataset_type: str = Field(description="数据集类型")
    augmentation: bool = Field(default=True, description="是否启用数据增强")
    train_split: float = Field(default=0.7, ge=0.0, le=1.0, description="训练集比例")
    val_split: float = Field(default=0.2, ge=0.0, le=1.0, description="验证集比例")
    test_split: float = Field(default=0.1, ge=0.0, le=1.0, description="测试集比例")
    image_size: List[int] = Field(default=[640, 640], description="图像尺寸")


class TrainingConfig(BaseModel):
    """训练配置"""
    epochs: int = Field(default=50, description="训练轮数")
    batch_size: int = Field(default=16, description="批次大小")
    learning_rate: float = Field(default=0.001, description="学习率")
    optimizer: str = Field(default="adam", description="优化器")
    early_stopping_patience: int = Field(default=10, description="早停耐心值")


class TaskCreateRequest(BaseModel):
    """任务创建请求"""
    task_type: TaskType = Field(description="任务类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    priority: int = Field(default=0, description="任务优先级")
    timeout: Optional[int] = Field(default=None, description="任务超时时间（秒）")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(description="任务ID")
    task_type: TaskType = Field(description="任务类型")
    status: TaskStatus = Field(description="任务状态")
    created_at: datetime = Field(description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="进度")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(description="任务ID")
    status: TaskStatus = Field(description="任务状态")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="进度")
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class BatchTaskCreateRequest(BaseModel):
    """批量任务创建请求"""
    tasks: List[TaskCreateRequest] = Field(description="任务列表")
    parallel: bool = Field(default=False, description="是否并行执行")


class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    batch_id: str = Field(description="批量任务ID")
    tasks: List[TaskResponse] = Field(description="任务列表")
    total_tasks: int = Field(description="总任务数")
    successful_tasks: int = Field(description="成功任务数")
    failed_tasks: int = Field(description="失败任务数")
    created_at: datetime = Field(description="创建时间")


class TaskCancelRequest(BaseModel):
    """任务取消请求"""
    task_id: str = Field(description="任务ID")
    force: bool = Field(default=False, description="是否强制取消")


class TaskCancelResponse(BaseModel):
    """任务取消响应"""
    task_id: str = Field(description="任务ID")
    cancelled: bool = Field(description="是否取消成功")
    message: str = Field(description="取消结果消息")


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse] = Field(description="任务列表")
    total: int = Field(description="总任务数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class TaskFilter(BaseModel):
    """任务过滤器"""
    task_type: Optional[TaskType] = Field(default=None, description="任务类型")
    status: Optional[TaskStatus] = Field(default=None, description="任务状态")
    created_after: Optional[datetime] = Field(default=None, description="创建时间之后")
    created_before: Optional[datetime] = Field(default=None, description="创建时间之前")
    limit: int = Field(default=100, le=1000, description="限制数量")
    offset: int = Field(default=0, description="偏移量")


class TaskProgress(BaseModel):
    """任务进度"""
    current: int = Field(description="当前进度")
    total: int = Field(description="总进度")
    percentage: float = Field(ge=0.0, le=1.0, description="进度百分比")
    status: str = Field(description="状态描述")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细进度信息")
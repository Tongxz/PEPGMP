"""
MLOps数据库模型
定义数据集、部署、工作流等实体的数据模型
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Dataset(Base):
    """数据集模型"""

    __tablename__ = "datasets"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    status = Column(
        String(20), nullable=False, default="active"
    )  # active, archived, processing, error
    size = Column(BigInteger, nullable=False, default=0)
    sample_count = Column(Integer, nullable=True)
    label_count = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    quality_metrics = Column(JSON, nullable=True)  # 存储质量指标JSON
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # 存储标签列表JSON
    file_path = Column(String(500), nullable=True)  # 数据集文件路径
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            """格式化datetime为带时区的ISO格式"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假设是UTC时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 生成带时区的ISO格式（如 2025-11-13T01:20:16+00:00）
            return dt.isoformat()

        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "size": self.size,
            "sample_count": self.sample_count,
            "label_count": self.label_count,
            "quality_score": self.quality_score,
            "quality_metrics": self.quality_metrics,
            "description": self.description,
            "tags": self.tags,
            "file_path": self.file_path,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


class Deployment(Base):
    """模型部署模型"""

    __tablename__ = "deployments"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    environment = Column(String(20), nullable=False)  # production, staging, development
    status = Column(
        String(20), nullable=False, default="stopped"
    )  # running, stopped, deploying, error, scaling
    replicas = Column(Integer, nullable=False, default=1)
    cpu_limit = Column(String(20), nullable=True)  # CPU限制，如 "1" 表示1核
    memory_limit = Column(String(20), nullable=True)  # 内存限制，如 "2Gi" 表示2GB
    gpu_count = Column(Integer, nullable=True, default=0)
    gpu_memory = Column(String(20), nullable=True)  # GPU内存限制
    auto_scaling = Column(Boolean, nullable=False, default=False)
    min_replicas = Column(Integer, nullable=True, default=1)
    max_replicas = Column(Integer, nullable=True, default=5)
    update_strategy = Column(
        String(20), nullable=True, default="rolling"
    )  # rolling, recreate, blue_green
    # 运行时指标
    cpu_usage = Column(Float, nullable=True, default=0.0)
    memory_usage = Column(Float, nullable=True, default=0.0)
    gpu_usage = Column(Float, nullable=True, default=0.0)
    requests_per_minute = Column(Integer, nullable=True, default=0)
    avg_response_time = Column(Float, nullable=True, default=0.0)
    error_rate = Column(Float, nullable=True, default=0.0)
    total_requests = Column(Integer, nullable=True, default=0)
    success_rate = Column(Float, nullable=True, default=0.0)
    # 部署信息
    deployment_config = Column(JSON, nullable=True)  # 存储完整部署配置
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            """格式化datetime为带时区的ISO格式"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假设是UTC时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 生成带时区的ISO格式（如 2025-11-13T01:20:16+00:00）
            return dt.isoformat()

        return {
            "id": self.id,
            "name": self.name,
            "model_version": self.model_version,
            "environment": self.environment,
            "status": self.status,
            "replicas": self.replicas,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "gpu_count": self.gpu_count,
            "gpu_memory": self.gpu_memory,
            "auto_scaling": self.auto_scaling,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "update_strategy": self.update_strategy,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "gpu_usage": self.gpu_usage,
            "requests_per_minute": self.requests_per_minute,
            "avg_response_time": self.avg_response_time,
            "error_rate": self.error_rate,
            "total_requests": self.total_requests,
            "success_rate": self.success_rate,
            "deployment_config": self.deployment_config,
            "deployed_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


class Workflow(Base):
    """工作流模型"""

    __tablename__ = "workflows"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    type = Column(
        String(20), nullable=False
    )  # training, evaluation, deployment, data_processing
    status = Column(
        String(20), nullable=False, default="inactive"
    )  # active, inactive, error
    trigger = Column(
        String(20), nullable=False
    )  # manual, schedule, webhook, data_change
    schedule = Column(String(100), nullable=True)  # cron表达式
    description = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False)  # 存储工作流步骤配置
    # 运行统计
    run_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=False, default=0.0)
    avg_duration = Column(Float, nullable=False, default=0.0)  # 平均运行时间（分钟）
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    # 工作流配置
    workflow_config = Column(JSON, nullable=True)  # 存储完整工作流配置
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            """格式化datetime为带时区的ISO格式"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假设是UTC时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 生成带时区的ISO格式（如 2025-11-13T01:20:16+00:00）
            return dt.isoformat()

        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "trigger": self.trigger,
            "schedule": self.schedule,
            "description": self.description,
            "steps": self.steps,
            "run_count": self.run_count,
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
            "last_run": format_datetime(self.last_run),
            "next_run": format_datetime(self.next_run),
            "workflow_config": self.workflow_config,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
            "recent_runs": [],  # 需要单独查询运行记录
        }


class WorkflowRun(Base):
    """工作流运行记录模型"""

    __tablename__ = "workflow_runs"

    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # success, failed, running, pending
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    ended_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # 运行时长（分钟）
    error_message = Column(Text, nullable=True)
    run_log = Column(Text, nullable=True)  # 运行日志
    run_config = Column(JSON, nullable=True)  # 运行时的配置快照
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            """格式化datetime为带时区的ISO格式"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假设是UTC时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 生成带时区的ISO格式（如 2025-11-13T01:20:16+00:00）
            return dt.isoformat()

        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "started_at": format_datetime(self.started_at),
            "ended_at": format_datetime(self.ended_at),
            "duration": self.duration,
            "error_message": self.error_message,
            "run_log": self.run_log,
            "run_config": self.run_config,
            "created_at": format_datetime(self.created_at),
        }


class ModelRegistry(Base):
    """模型注册表"""

    __tablename__ = "model_registry"

    id = Column(String(60), primary_key=True)
    name = Column(String(120), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(
        String(20), nullable=False, default="active"
    )  # active, archived, deprecated
    model_path = Column(String(500), nullable=False)
    report_path = Column(String(500), nullable=True)
    dataset_id = Column(String(50), nullable=True)
    dataset_path = Column(String(500), nullable=True)
    metrics = Column(JSON, nullable=True)
    artifacts = Column(JSON, nullable=True)
    training_params = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            """格式化datetime为带时区的ISO格式"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假设是UTC时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 生成带时区的ISO格式（如 2025-11-13T01:20:16+00:00）
            return dt.isoformat()

        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type,
            "version": self.version,
            "status": self.status,
            "model_path": self.model_path,
            "report_path": self.report_path,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "training_params": self.training_params,
            "description": self.description,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


# ============================================
# 核心业务表（从 SQL 脚本迁移到 SQLAlchemy）
# ============================================


class Camera(Base):
    """摄像头配置模型"""

    __tablename__ = "cameras"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=True)
    stream_url = Column(String(500), nullable=False)
    camera_type = Column(String(50), nullable=True, default="ip_camera")
    resolution = Column(String(20), nullable=True, default="1920x1080")
    fps = Column(Integer, nullable=True, default=30)
    is_active = Column(Boolean, nullable=True, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=True,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )
    status = Column(String(20), nullable=True, default="inactive")
    region_id = Column(String(100), nullable=True)
    meta_data = Column("metadata", JSON, nullable=True, default={})

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "stream_url": self.stream_url,
            "camera_type": self.camera_type,
            "resolution": self.resolution,
            "fps": self.fps,
            "is_active": self.is_active,
            "config": self.config,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
            "status": self.status,
            "region_id": self.region_id,
            "metadata": self.meta_data,
        }


class Region(Base):
    """区域配置模型"""

    __tablename__ = "regions"

    region_id = Column(String(100), primary_key=True)
    region_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    polygon = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=True, default=True)
    rules = Column(JSON, nullable=True, default={})
    camera_id = Column(String(100), nullable=True)
    meta_data = Column("metadata", JSON, nullable=True, default={})
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=True,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "region_id": self.region_id,
            "region_type": self.region_type,
            "name": self.name,
            "polygon": self.polygon,
            "is_active": self.is_active,
            "rules": self.rules,
            "camera_id": self.camera_id,
            "metadata": self.meta_data,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


class DetectionRecord(Base):
    """检测记录模型"""

    __tablename__ = "detection_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    camera_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), index=True
    )
    frame_number = Column(Integer, nullable=True)
    person_count = Column(Integer, nullable=True, default=0)
    hairnet_violations = Column(Integer, nullable=True, default=0)
    handwash_events = Column(Integer, nullable=True, default=0)
    sanitize_events = Column(Integer, nullable=True, default=0)
    person_detections = Column(JSON, nullable=True)
    hairnet_results = Column(JSON, nullable=True)
    handwash_results = Column(JSON, nullable=True)
    sanitize_results = Column(JSON, nullable=True)
    processing_time = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.utcnow())
    confidence = Column(Float, nullable=True)
    objects = Column(JSON, nullable=True)
    frame_id = Column(String(100), nullable=True)
    region_id = Column(String(50), nullable=True)
    meta_data = Column("metadata", JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "timestamp": format_datetime(self.timestamp),
            "frame_number": self.frame_number,
            "person_count": self.person_count,
            "hairnet_violations": self.hairnet_violations,
            "handwash_events": self.handwash_events,
            "sanitize_events": self.sanitize_events,
            "person_detections": self.person_detections,
            "hairnet_results": self.hairnet_results,
            "handwash_results": self.handwash_results,
            "sanitize_results": self.sanitize_results,
            "processing_time": self.processing_time,
            "fps": self.fps,
            "created_at": format_datetime(self.created_at),
            "confidence": self.confidence,
            "objects": self.objects,
            "frame_id": self.frame_id,
            "region_id": self.region_id,
            "metadata": self.meta_data,
        }


class ViolationEvent(Base):
    """违规事件模型"""

    __tablename__ = "violation_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    detection_id = Column(BigInteger, nullable=True)
    camera_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), index=True
    )
    violation_type = Column(String(50), nullable=False, index=True)
    track_id = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    snapshot_path = Column(String(500), nullable=True)
    bbox = Column(JSON, nullable=True)
    status = Column(String(20), nullable=True, default="pending", index=True)
    handled_at = Column(DateTime, nullable=True)
    handled_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=True,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "detection_id": self.detection_id,
            "camera_id": self.camera_id,
            "timestamp": format_datetime(self.timestamp),
            "violation_type": self.violation_type,
            "track_id": self.track_id,
            "confidence": self.confidence,
            "snapshot_path": self.snapshot_path,
            "bbox": self.bbox,
            "status": self.status,
            "handled_at": format_datetime(self.handled_at),
            "handled_by": self.handled_by,
            "notes": self.notes,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


class AlertRule(Base):
    """告警规则模型"""

    __tablename__ = "alert_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    alert_type = Column(String(50), nullable=False, index=True)
    conditions = Column(JSON, nullable=False)
    notification_channels = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True, index=True)
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime,
        nullable=True,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "name": self.name,
            "alert_type": self.alert_type,
            "conditions": self.conditions,
            "notification_channels": self.notification_channels,
            "is_active": self.is_active,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


class AlertHistory(Base):
    """告警历史模型"""

    __tablename__ = "alert_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(BigInteger, nullable=True)
    camera_id = Column(String(50), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    notification_sent = Column(Boolean, nullable=True, default=False)
    notification_channels_used = Column(JSON, nullable=True)
    timestamp = Column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), index=True
    )
    status = Column(String(20), nullable=True, default="pending", index=True)
    handled_at = Column(DateTime, nullable=True)
    handled_by = Column(String(100), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "camera_id": self.camera_id,
            "alert_type": self.alert_type,
            "message": self.message,
            "details": self.details,
            "notification_sent": self.notification_sent,
            "notification_channels_used": self.notification_channels_used,
            "timestamp": format_datetime(self.timestamp),
            "status": self.status,
            "handled_at": format_datetime(self.handled_at),
            "handled_by": self.handled_by,
        }

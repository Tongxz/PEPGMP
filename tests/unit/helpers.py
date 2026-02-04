"""
测试辅助函数
提供工厂函数和mock对象构建器，简化测试数据创建
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


def create_test_violation(
    violation_id: Optional[str] = None,
    camera_id: str = "test_camera_001",
    violation_type: str = "no_hairnet",
    confidence: float = 0.95,
    timestamp: Optional[datetime] = None,
    status: str = "pending",
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    创建测试违规记录

    Args:
        violation_id: 违规ID（默认自动生成）
        camera_id: 摄像头ID
        violation_type: 违规类型
        confidence: 置信度
        timestamp: 时间戳（默认当前时间）
        status: 状态
        **kwargs: 其他字段

    Returns:
        违规记录字典
    """
    return {
        "id": violation_id or str(uuid4()),
        "camera_id": camera_id,
        "violation_type": violation_type,
        "confidence": confidence,
        "timestamp": timestamp or datetime.now(),
        "status": status,
        "frame_id": kwargs.get("frame_id", 1),
        "image_url": kwargs.get("image_url"),
        "bbox": kwargs.get("bbox", [100, 100, 200, 200]),
        "note": kwargs.get("note"),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["frame_id", "image_url", "bbox", "note"]
        },
    }


def create_test_region(
    region_id: Optional[str] = None,
    camera_id: str = "test_camera_001",
    name: str = "测试区域",
    region_type: str = "polygon",
    polygon: Optional[List[Tuple[float, float]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    创建测试区域

    Args:
        region_id: 区域ID（默认自动生成）
        camera_id: 摄像头ID
        name: 区域名称
        region_type: 区域类型（polygon/line/box）
        polygon: 多边形点列表
        **kwargs: 其他字段

    Returns:
        区域字典
    """
    if polygon is None:
        polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    return {
        "id": region_id or str(uuid4()),
        "camera_id": camera_id,
        "name": name,
        "region_type": region_type,
        "polygon": polygon,
        "is_active": kwargs.get("is_active", True),
        "created_at": kwargs.get("created_at", datetime.now()),
        "updated_at": kwargs.get("updated_at", datetime.now()),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["is_active", "created_at", "updated_at"]
        },
    }


def create_test_detection(
    detection_id: Optional[str] = None,
    camera_id: str = "test_camera_001",
    frame_id: int = 1,
    timestamp: Optional[datetime] = None,
    detected_objects: int = 2,
    has_violation: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    创建测试检测记录

    Args:
        detection_id: 检测ID（默认自动生成）
        camera_id: 摄像头ID
        frame_id: 帧ID
        timestamp: 时间戳
        detected_objects: 检测到的对象数
        has_violation: 是否有违规
        **kwargs: 其他字段

    Returns:
        检测记录字典
    """
    return {
        "id": detection_id or str(uuid4()),
        "camera_id": camera_id,
        "frame_id": frame_id,
        "timestamp": timestamp or datetime.now(),
        "detected_objects": detected_objects,
        "has_violation": has_violation,
        "confidence": kwargs.get("confidence", 0.9),
        "processing_time": kwargs.get("processing_time", 0.1),
        "image_url": kwargs.get("image_url"),
        "objects": kwargs.get("objects", []),
        "violations": kwargs.get("violations", []),
        **{
            k: v
            for k, v in kwargs.items()
            if k
            not in [
                "confidence",
                "processing_time",
                "image_url",
                "objects",
                "violations",
            ]
        },
    }


def create_test_camera(
    camera_id: str = "test_camera_001",
    name: str = "测试摄像头",
    rtsp_url: str = "rtsp://test.example.com/stream",
    status: str = "online",
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    创建测试摄像头

    Args:
        camera_id: 摄像头ID
        name: 摄像头名称
        rtsp_url: RTSP地址
        status: 状态
        **kwargs: 其他字段

    Returns:
        摄像头字典
    """
    return {
        "id": camera_id,
        "name": name,
        "rtsp_url": rtsp_url,
        "status": status,
        "location": kwargs.get("location", "测试位置"),
        "enabled": kwargs.get("enabled", True),
        "created_at": kwargs.get("created_at", datetime.now()),
        "updated_at": kwargs.get("updated_at", datetime.now()),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["location", "enabled", "created_at", "updated_at"]
        },
    }


def create_test_detection_config(**kwargs: Any) -> Dict[str, Any]:
    """
    创建测试检测配置

    Args:
        **kwargs: 配置字段

    Returns:
        检测配置字典
    """
    return {
        "hairnet_detection": {
            "enabled": kwargs.get("hairnet_enabled", True),
            "confidence_threshold": kwargs.get("hairnet_confidence", 0.5),
            "detection_classes": kwargs.get("hairnet_classes", ["person", "head"]),
        },
        "behavior_recognition": {
            "enabled": kwargs.get("behavior_enabled", True),
            "confidence_threshold": kwargs.get("behavior_confidence", 0.6),
            "behaviors": kwargs.get("behaviors", ["handwash", "smoking"]),
        },
        **{
            k: v
            for k, v in kwargs.items()
            if not k.startswith(("hairnet_", "behavior_"))
        },
    }


class AsyncMockContext:
    """
    异步上下文管理器Mock
    用于mock数据库连接的async with语句和async acquire()调用
    """

    def __init__(self, return_value: Any):
        self.return_value = return_value

    def __await__(self):
        """使对象可以被await"""

        async def _await():
            return self.return_value

        return _await().__await__()

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass

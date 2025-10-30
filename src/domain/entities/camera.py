"""
摄像头实体
表示一个摄像头设备
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.domain.value_objects.timestamp import Timestamp


class CameraStatus(Enum):
    """摄像头状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class CameraType(Enum):
    """摄像头类型枚举"""

    FIXED = "fixed"
    PTZ = "ptz"  # Pan-Tilt-Zoom
    MOBILE = "mobile"
    THERMAL = "thermal"


@dataclass
class Camera:
    """摄像头实体"""

    id: str
    name: str
    location: str
    status: CameraStatus = CameraStatus.INACTIVE
    camera_type: CameraType = CameraType.FIXED
    resolution: Optional[tuple[int, int]] = None
    fps: Optional[int] = None
    region_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Timestamp = field(default_factory=Timestamp.now)
    updated_at: Timestamp = field(default_factory=Timestamp.now)

    @property
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.status == CameraStatus.ACTIVE

    @property
    def is_ptz(self) -> bool:
        """是否为PTZ摄像头"""
        return self.camera_type == CameraType.PTZ

    @property
    def is_thermal(self) -> bool:
        """是否为热成像摄像头"""
        return self.camera_type == CameraType.THERMAL

    @property
    def resolution_string(self) -> str:
        """获取分辨率字符串"""
        if self.resolution:
            return f"{self.resolution[0]}x{self.resolution[1]}"
        return "Unknown"

    @property
    def fps_string(self) -> str:
        """获取帧率字符串"""
        if self.fps:
            return f"{self.fps} FPS"
        return "Unknown"

    def activate(self) -> None:
        """激活摄像头"""
        self.status = CameraStatus.ACTIVE
        self.updated_at = Timestamp.now()

    def deactivate(self) -> None:
        """停用摄像头"""
        self.status = CameraStatus.INACTIVE
        self.updated_at = Timestamp.now()

    def set_maintenance(self) -> None:
        """设置为维护状态"""
        self.status = CameraStatus.MAINTENANCE
        self.updated_at = Timestamp.now()

    def set_error(self) -> None:
        """设置为错误状态"""
        self.status = CameraStatus.ERROR
        self.updated_at = Timestamp.now()

    def update_resolution(self, width: int, height: int) -> None:
        """
        更新分辨率

        Args:
            width: 宽度
            height: 高度
        """
        if width <= 0 or height <= 0:
            raise ValueError("Resolution dimensions must be positive")

        self.resolution = (width, height)
        self.updated_at = Timestamp.now()

    def update_fps(self, fps: int) -> None:
        """
        更新帧率

        Args:
            fps: 帧率
        """
        if fps <= 0:
            raise ValueError("FPS must be positive")

        self.fps = fps
        self.updated_at = Timestamp.now()

    def update_location(self, location: str) -> None:
        """
        更新位置

        Args:
            location: 新位置
        """
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")

        self.location = location.strip()
        self.updated_at = Timestamp.now()

    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据

        Args:
            key: 键
            value: 值
        """
        self.metadata[key] = value
        self.updated_at = Timestamp.now()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据

        Args:
            key: 键
            default: 默认值

        Returns:
            Any: 元数据值
        """
        return self.metadata.get(key, default)

    def remove_metadata(self, key: str) -> bool:
        """
        移除元数据

        Args:
            key: 键

        Returns:
            bool: 是否成功移除
        """
        if key in self.metadata:
            del self.metadata[key]
            self.updated_at = Timestamp.now()
            return True
        return False

    def get_capabilities(self) -> List[str]:
        """
        获取摄像头能力列表

        Returns:
            List[str]: 能力列表
        """
        capabilities = []

        if self.is_ptz:
            capabilities.append("pan_tilt_zoom")

        if self.is_thermal:
            capabilities.append("thermal_imaging")

        if self.resolution and self.resolution[0] >= 1920:
            capabilities.append("high_resolution")

        if self.fps and self.fps >= 30:
            capabilities.append("high_fps")

        # 从元数据中获取其他能力
        if "night_vision" in self.metadata and self.metadata["night_vision"]:
            capabilities.append("night_vision")

        if "audio" in self.metadata and self.metadata["audio"]:
            capabilities.append("audio")

        return capabilities

    def is_capable_of(self, capability: str) -> bool:
        """
        检查是否具有指定能力

        Args:
            capability: 能力名称

        Returns:
            bool: 是否具有该能力
        """
        return capability in self.get_capabilities()

    def get_status_info(self) -> Dict[str, Any]:
        """
        获取状态信息

        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "camera_type": self.camera_type.value,
            "location": self.location,
            "resolution": self.resolution_string,
            "fps": self.fps_string,
            "region_id": self.region_id,
            "capabilities": self.get_capabilities(),
            "is_active": self.is_active,
            "created_at": self.created_at.iso_string,
            "updated_at": self.updated_at.iso_string,
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "status": self.status.value,
            "camera_type": self.camera_type.value,
            "resolution": self.resolution,
            "fps": self.fps,
            "region_id": self.region_id,
            "metadata": self.metadata,
            "created_at": self.created_at.iso_string,
            "updated_at": self.updated_at.iso_string,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Camera":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            name=data["name"],
            location=data["location"],
            status=CameraStatus(data["status"]),
            camera_type=CameraType(data["camera_type"]),
            resolution=tuple(data["resolution"]) if data.get("resolution") else None,
            fps=data.get("fps"),
            region_id=data.get("region_id"),
            metadata=data.get("metadata", {}),
            created_at=Timestamp.from_iso(data["created_at"]),
            updated_at=Timestamp.from_iso(data["updated_at"]),
        )

    def __str__(self) -> str:
        return f"Camera(id={self.id}, name={self.name}, status={self.status.value})"

    def __repr__(self) -> str:
        return self.__str__()

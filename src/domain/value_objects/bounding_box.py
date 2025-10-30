"""
边界框值对象
表示检测对象的边界框
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class BoundingBox:
    """边界框值对象（不可变）"""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self):
        """验证边界框数据"""
        if self.x1 >= self.x2:
            raise ValueError("x1 must be less than x2")
        if self.y1 >= self.y2:
            raise ValueError("y1 must be less than y2")
        if self.x1 < 0 or self.y1 < 0:
            raise ValueError("Coordinates must be non-negative")

    @property
    def width(self) -> float:
        """获取宽度"""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """获取高度"""
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        """获取面积"""
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        """获取中心点"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def aspect_ratio(self) -> float:
        """获取宽高比"""
        if self.height == 0:
            return float("inf")
        return self.width / self.height

    def calculate_iou(self, other: "BoundingBox") -> float:
        """
        计算与另一个边界框的IoU

        Args:
            other: 另一个边界框

        Returns:
            float: IoU值
        """
        if not isinstance(other, BoundingBox):
            return 0.0

        # 计算交集
        x1_i = max(self.x1, other.x1)
        y1_i = max(self.y1, other.y1)
        x2_i = min(self.x2, other.x2)
        y2_i = min(self.y2, other.y2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # 计算并集
        union = self.area + other.area - intersection

        if union == 0:
            return 0.0

        return intersection / union

    def calculate_overlap_ratio(self, other: "BoundingBox") -> float:
        """
        计算与另一个边界框的重叠比例

        Args:
            other: 另一个边界框

        Returns:
            float: 重叠比例
        """
        if not isinstance(other, BoundingBox):
            return 0.0

        # 计算交集
        x1_i = max(self.x1, other.x1)
        y1_i = max(self.y1, other.y1)
        x2_i = min(self.x2, other.x2)
        y2_i = min(self.y2, other.y2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # 返回交集与当前边界框面积的比值
        return intersection / self.area

    def contains_point(self, x: float, y: float) -> bool:
        """
        判断是否包含指定点

        Args:
            x: X坐标
            y: Y坐标

        Returns:
            bool: 是否包含
        """
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def contains_bbox(self, other: "BoundingBox") -> bool:
        """
        判断是否包含另一个边界框

        Args:
            other: 另一个边界框

        Returns:
            bool: 是否包含
        """
        if not isinstance(other, BoundingBox):
            return False

        return (
            self.x1 <= other.x1
            and self.y1 <= other.y1
            and self.x2 >= other.x2
            and self.y2 >= other.y2
        )

    def is_intersecting(self, other: "BoundingBox") -> bool:
        """
        判断是否与另一个边界框相交

        Args:
            other: 另一个边界框

        Returns:
            bool: 是否相交
        """
        if not isinstance(other, BoundingBox):
            return False

        return not (
            self.x2 <= other.x1
            or other.x2 <= self.x1
            or self.y2 <= other.y1
            or other.y2 <= self.y1
        )

    def scale(self, scale_x: float, scale_y: float) -> "BoundingBox":
        """
        缩放边界框

        Args:
            scale_x: X方向缩放比例
            scale_y: Y方向缩放比例

        Returns:
            BoundingBox: 缩放后的边界框
        """
        return BoundingBox(
            x1=self.x1 * scale_x,
            y1=self.y1 * scale_y,
            x2=self.x2 * scale_x,
            y2=self.y2 * scale_y,
        )

    def translate(self, dx: float, dy: float) -> "BoundingBox":
        """
        平移边界框

        Args:
            dx: X方向平移距离
            dy: Y方向平移距离

        Returns:
            BoundingBox: 平移后的边界框
        """
        return BoundingBox(
            x1=self.x1 + dx, y1=self.y1 + dy, x2=self.x2 + dx, y2=self.y2 + dy
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height,
            "area": self.area,
            "center": self.center,
            "aspect_ratio": self.aspect_ratio,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundingBox":
        """从字典创建实例"""
        return cls(x1=data["x1"], y1=data["y1"], x2=data["x2"], y2=data["y2"])

    @classmethod
    def from_xywh(
        cls, x: float, y: float, width: float, height: float
    ) -> "BoundingBox":
        """
        从x, y, width, height创建边界框

        Args:
            x: 左上角X坐标
            y: 左上角Y坐标
            width: 宽度
            height: 高度

        Returns:
            BoundingBox: 边界框实例
        """
        return cls(x1=x, y1=y, x2=x + width, y2=y + height)

    def __str__(self) -> str:
        return (
            f"BoundingBox({self.x1:.1f}, {self.y1:.1f}, {self.x2:.1f}, {self.y2:.1f})"
        )

    def __repr__(self) -> str:
        return self.__str__()

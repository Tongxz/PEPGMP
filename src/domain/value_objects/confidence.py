"""
置信度值对象
表示检测的置信度
"""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Confidence:
    """置信度值对象（不可变）"""

    value: float

    def __post_init__(self):
        """验证置信度值"""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("Confidence value must be between 0.0 and 1.0")

    @property
    def is_high(self) -> bool:
        """是否为高置信度"""
        return self.value >= 0.8

    @property
    def is_medium(self) -> bool:
        """是否为中等置信度"""
        return 0.5 <= self.value < 0.8

    @property
    def is_low(self) -> bool:
        """是否为低置信度"""
        return self.value < 0.5

    @property
    def percentage(self) -> float:
        """获取百分比形式"""
        return self.value * 100

    def __add__(self, other: Union["Confidence", float, int]) -> "Confidence":
        """加法运算"""
        if isinstance(other, Confidence):
            return Confidence(min(1.0, self.value + other.value))
        elif isinstance(other, (int, float)):
            return Confidence(min(1.0, self.value + other))
        else:
            return NotImplemented

    def __sub__(self, other: Union["Confidence", float, int]) -> "Confidence":
        """减法运算"""
        if isinstance(other, Confidence):
            return Confidence(max(0.0, self.value - other.value))
        elif isinstance(other, (int, float)):
            return Confidence(max(0.0, self.value - other))
        else:
            return NotImplemented

    def __mul__(self, other: Union["Confidence", float, int]) -> "Confidence":
        """乘法运算"""
        if isinstance(other, Confidence):
            return Confidence(self.value * other.value)
        elif isinstance(other, (int, float)):
            return Confidence(self.value * other)
        else:
            return NotImplemented

    def __truediv__(self, other: Union["Confidence", float, int]) -> "Confidence":
        """除法运算"""
        if isinstance(other, Confidence):
            if other.value == 0:
                raise ZeroDivisionError("Cannot divide by zero confidence")
            return Confidence(self.value / other.value)
        elif isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return Confidence(self.value / other)
        else:
            return NotImplemented

    def __lt__(self, other: Union["Confidence", float, int]) -> bool:
        """小于比较"""
        if isinstance(other, Confidence):
            return self.value < other.value
        elif isinstance(other, (int, float)):
            return self.value < other
        else:
            return NotImplemented

    def __le__(self, other: Union["Confidence", float, int]) -> bool:
        """小于等于比较"""
        if isinstance(other, Confidence):
            return self.value <= other.value
        elif isinstance(other, (int, float)):
            return self.value <= other
        else:
            return NotImplemented

    def __gt__(self, other: Union["Confidence", float, int]) -> bool:
        """大于比较"""
        if isinstance(other, Confidence):
            return self.value > other.value
        elif isinstance(other, (int, float)):
            return self.value > other
        else:
            return NotImplemented

    def __ge__(self, other: Union["Confidence", float, int]) -> bool:
        """大于等于比较"""
        if isinstance(other, Confidence):
            return self.value >= other.value
        elif isinstance(other, (int, float)):
            return self.value >= other
        else:
            return NotImplemented

    def __eq__(self, other: Union["Confidence", float, int]) -> bool:
        """等于比较"""
        if isinstance(other, Confidence):
            return abs(self.value - other.value) < 1e-9
        elif isinstance(other, (int, float)):
            return abs(self.value - other) < 1e-9
        else:
            return NotImplemented

    def __ne__(self, other: Union["Confidence", float, int]) -> bool:
        """不等于比较"""
        return not (self == other)

    def __str__(self) -> str:
        return f"Confidence({self.value:.3f})"

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.value)

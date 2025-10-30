"""
时间戳值对象
表示时间戳
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Timestamp:
    """时间戳值对象（不可变）"""

    value: datetime

    def __post_init__(self):
        """验证时间戳值"""
        if not isinstance(self.value, datetime):
            raise ValueError("Timestamp value must be a datetime object")

    @classmethod
    def now(cls) -> "Timestamp":
        """创建当前时间戳"""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_iso(cls, iso_string: str) -> "Timestamp":
        """从ISO字符串创建时间戳"""
        return cls(datetime.fromisoformat(iso_string))

    @classmethod
    def from_timestamp(cls, timestamp: float) -> "Timestamp":
        """从Unix时间戳创建时间戳"""
        return cls(datetime.fromtimestamp(timestamp, tz=timezone.utc))

    @property
    def iso_string(self) -> str:
        """获取ISO格式字符串"""
        return self.value.isoformat()

    @property
    def unix_timestamp(self) -> float:
        """获取Unix时间戳"""
        return self.value.timestamp()

    @property
    def year(self) -> int:
        """获取年份"""
        return self.value.year

    @property
    def month(self) -> int:
        """获取月份"""
        return self.value.month

    @property
    def day(self) -> int:
        """获取日期"""
        return self.value.day

    @property
    def hour(self) -> int:
        """获取小时"""
        return self.value.hour

    @property
    def minute(self) -> int:
        """获取分钟"""
        return self.value.minute

    @property
    def second(self) -> int:
        """获取秒"""
        return self.value.second

    def is_before(self, other: "Timestamp") -> bool:
        """判断是否在另一个时间戳之前"""
        if not isinstance(other, Timestamp):
            return False
        return self.value < other.value

    def is_after(self, other: "Timestamp") -> bool:
        """判断是否在另一个时间戳之后"""
        if not isinstance(other, Timestamp):
            return False
        return self.value > other.value

    def is_same_time(self, other: "Timestamp", tolerance_seconds: float = 1.0) -> bool:
        """
        判断是否为同一时间（允许误差）

        Args:
            other: 另一个时间戳
            tolerance_seconds: 容忍的秒数误差

        Returns:
            bool: 是否为同一时间
        """
        if not isinstance(other, Timestamp):
            return False

        diff = abs((self.value - other.value).total_seconds())
        return diff <= tolerance_seconds

    def time_difference(self, other: "Timestamp") -> float:
        """
        计算与另一个时间戳的时间差（秒）

        Args:
            other: 另一个时间戳

        Returns:
            float: 时间差（秒）
        """
        if not isinstance(other, Timestamp):
            return 0.0

        return (self.value - other.value).total_seconds()

    def add_seconds(self, seconds: float) -> "Timestamp":
        """
        添加秒数

        Args:
            seconds: 要添加的秒数

        Returns:
            Timestamp: 新的时间戳
        """
        from datetime import timedelta

        return Timestamp(self.value + timedelta(seconds=seconds))

    def add_minutes(self, minutes: float) -> "Timestamp":
        """
        添加分钟数

        Args:
            minutes: 要添加的分钟数

        Returns:
            Timestamp: 新的时间戳
        """
        from datetime import timedelta

        return Timestamp(self.value + timedelta(minutes=minutes))

    def add_hours(self, hours: float) -> "Timestamp":
        """
        添加小时数

        Args:
            hours: 要添加的小时数

        Returns:
            Timestamp: 新的时间戳
        """
        from datetime import timedelta

        return Timestamp(self.value + timedelta(hours=hours))

    def add_days(self, days: float) -> "Timestamp":
        """
        添加天数

        Args:
            days: 要添加的天数

        Returns:
            Timestamp: 新的时间戳
        """
        from datetime import timedelta

        return Timestamp(self.value + timedelta(days=days))

    def to_local_time(self) -> "Timestamp":
        """转换为本地时间"""
        local_time = self.value.astimezone()
        return Timestamp(local_time)

    def to_utc_time(self) -> "Timestamp":
        """转换为UTC时间"""
        utc_time = self.value.astimezone(timezone.utc)
        return Timestamp(utc_time)

    def __str__(self) -> str:
        return f"Timestamp({self.value.isoformat()})"

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.value)

    def __lt__(self, other: "Timestamp") -> bool:
        """小于比较"""
        if not isinstance(other, Timestamp):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "Timestamp") -> bool:
        """小于等于比较"""
        if not isinstance(other, Timestamp):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "Timestamp") -> bool:
        """大于比较"""
        if not isinstance(other, Timestamp):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "Timestamp") -> bool:
        """大于等于比较"""
        if not isinstance(other, Timestamp):
            return NotImplemented
        return self.value >= other.value

    def __eq__(self, other: "Timestamp") -> bool:
        """等于比较"""
        if not isinstance(other, Timestamp):
            return NotImplemented
        return self.value == other.value

    def __ne__(self, other: "Timestamp") -> bool:
        """不等于比较"""
        return not (self == other)

"""分页工具模块.

提供统一的分页参数和响应模型，用于API分页功能。
"""

import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

# 泛型类型变量
T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页参数模型.

    用于接收和验证API分页参数。

    Attributes:
        page: 页码（从1开始）
        page_size: 每页大小（1-100）

    Example:
        >>> params = PaginationParams(page=1, page_size=20)
        >>> params.offset  # 0
        >>> params.limit   # 20

        >>> params = PaginationParams(page=3, page_size=50)
        >>> params.offset  # 100
        >>> params.limit   # 50
    """

    page: int = Field(1, ge=1, description="页码（从1开始）")
    page_size: int = Field(20, ge=1, le=100, description="每页大小（1-100）")

    @property
    def offset(self) -> int:
        """计算SQL OFFSET值.

        Returns:
            跳过的记录数

        Example:
            page=1, page_size=20 → offset=0
            page=2, page_size=20 → offset=20
            page=3, page_size=50 → offset=100
        """
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """计算SQL LIMIT值.

        Returns:
            每页记录数（等于page_size）
        """
        return self.page_size

    class Config:
        """Pydantic配置."""

        frozen = False  # 允许修改


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型.

    统一的分页响应格式，包含数据和分页元数据。

    Attributes:
        items: 当前页的数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        total_pages: 总页数

    Example:
        >>> response = PaginatedResponse(
        ...     items=[{"id": 1}, {"id": 2}],
        ...     total=100,
        ...     page=1,
        ...     page_size=20,
        ...     total_pages=5
        ... )
    """

    items: List[T] = Field(description="当前页的数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(ge=1, description="当前页码")
    page_size: int = Field(ge=1, le=100, description="每页大小")
    total_pages: int = Field(ge=0, description="总页数")

    @staticmethod
    def create(
        items: List[T], total: int, pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        """创建分页响应对象的工厂方法.

        Args:
            items: 当前页的数据列表
            total: 总记录数
            pagination: 分页参数

        Returns:
            分页响应对象

        Example:
            >>> params = PaginationParams(page=1, page_size=20)
            >>> items = [{"id": 1}, {"id": 2}]
            >>> response = PaginatedResponse.create(items, 100, params)
            >>> response.total_pages  # 5
        """
        total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0

        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        )

    class Config:
        """Pydantic配置."""

        # 支持泛型
        arbitrary_types_allowed = True


# 辅助函数


def calculate_offset(page: int, page_size: int) -> int:
    """计算SQL OFFSET值.

    Args:
        page: 页码（从1开始）
        page_size: 每页大小

    Returns:
        OFFSET值

    Example:
        >>> calculate_offset(1, 20)  # 0
        >>> calculate_offset(2, 20)  # 20
        >>> calculate_offset(3, 50)  # 100
    """
    if page < 1:
        page = 1
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    """计算总页数.

    Args:
        total: 总记录数
        page_size: 每页大小

    Returns:
        总页数

    Example:
        >>> calculate_total_pages(100, 20)  # 5
        >>> calculate_total_pages(105, 20)  # 6
        >>> calculate_total_pages(0, 20)    # 0
    """
    if total <= 0 or page_size <= 0:
        return 0
    return math.ceil(total / page_size)


def validate_pagination_params(
    page: int, page_size: int, max_page_size: int = 100
) -> tuple:
    """验证并修正分页参数.

    Args:
        page: 页码
        page_size: 每页大小
        max_page_size: 最大每页大小

    Returns:
        (修正后的page, 修正后的page_size)

    Example:
        >>> validate_pagination_params(0, 20)     # (1, 20)
        >>> validate_pagination_params(5, 200)    # (5, 100)
        >>> validate_pagination_params(-1, -10)   # (1, 20)
    """
    # 修正page
    if page < 1:
        page = 1

    # 修正page_size
    if page_size < 1:
        page_size = 20  # 默认值
    elif page_size > max_page_size:
        page_size = max_page_size

    return page, page_size

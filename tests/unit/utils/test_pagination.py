"""分页工具单元测试."""

import pytest
from pydantic import ValidationError

from src.utils.pagination import (
    PaginatedResponse,
    PaginationParams,
    calculate_offset,
    calculate_total_pages,
    validate_pagination_params,
)


class TestPaginationParams:
    """测试分页参数模型."""

    def test_default_values(self):
        """测试默认值."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        """测试自定义值."""
        params = PaginationParams(page=5, page_size=50)
        assert params.page == 5
        assert params.page_size == 50

    def test_offset_calculation(self):
        """测试offset计算."""
        # 第1页
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0
        assert params.limit == 20

        # 第2页
        params = PaginationParams(page=2, page_size=20)
        assert params.offset == 20
        assert params.limit == 20

        # 第3页
        params = PaginationParams(page=3, page_size=50)
        assert params.offset == 100
        assert params.limit == 50

        # 第10页
        params = PaginationParams(page=10, page_size=10)
        assert params.offset == 90
        assert params.limit == 10

    def test_page_validation_minimum(self):
        """测试page最小值验证."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page=0)
        assert "page" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page=-1)
        assert "page" in str(exc_info.value)

    def test_page_size_validation_minimum(self):
        """测试page_size最小值验证."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=0)
        assert "page_size" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=-1)
        assert "page_size" in str(exc_info.value)

    def test_page_size_validation_maximum(self):
        """测试page_size最大值验证."""
        # 100是允许的最大值
        params = PaginationParams(page_size=100)
        assert params.page_size == 100

        # 101超过最大值
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=101)
        assert "page_size" in str(exc_info.value)

        # 1000超过最大值
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=1000)
        assert "page_size" in str(exc_info.value)

    def test_edge_cases(self):
        """测试边界情况."""
        # 最小有效值
        params = PaginationParams(page=1, page_size=1)
        assert params.offset == 0
        assert params.limit == 1

        # 最大有效page_size
        params = PaginationParams(page=1, page_size=100)
        assert params.offset == 0
        assert params.limit == 100

        # 大page值
        params = PaginationParams(page=1000, page_size=20)
        assert params.offset == 19980
        assert params.limit == 20


class TestPaginatedResponse:
    """测试分页响应模型."""

    def test_create_basic(self):
        """测试基本创建."""
        params = PaginationParams(page=1, page_size=20)
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        total = 100

        response = PaginatedResponse.create(items, total, params)

        assert response.items == items
        assert response.total == 100
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 5  # ceil(100/20)

    def test_create_exact_page(self):
        """测试刚好整页的情况."""
        params = PaginationParams(page=1, page_size=20)
        items = list(range(20))
        total = 100  # 刚好5页

        response = PaginatedResponse.create(items, total, params)
        assert response.total_pages == 5

    def test_create_partial_page(self):
        """测试不足一页的情况."""
        params = PaginationParams(page=1, page_size=20)
        items = list(range(15))
        total = 105  # 5页零5条

        response = PaginatedResponse.create(items, total, params)
        assert response.total_pages == 6  # ceil(105/20)

    def test_create_empty_result(self):
        """测试空结果."""
        params = PaginationParams(page=1, page_size=20)
        items = []
        total = 0

        response = PaginatedResponse.create(items, total, params)

        assert response.items == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 0

    def test_create_last_page(self):
        """测试最后一页."""
        params = PaginationParams(page=6, page_size=20)
        items = list(range(5))  # 最后一页只有5条
        total = 105

        response = PaginatedResponse.create(items, total, params)
        assert response.page == 6
        assert response.total_pages == 6
        assert len(response.items) == 5

    def test_create_beyond_last_page(self):
        """测试超出最后一页."""
        params = PaginationParams(page=10, page_size=20)
        items = []  # 超出范围，无数据
        total = 100  # 只有5页

        response = PaginatedResponse.create(items, total, params)
        assert response.page == 10
        assert response.total_pages == 5
        assert response.items == []

    def test_direct_instantiation(self):
        """测试直接实例化."""
        response = PaginatedResponse(
            items=[1, 2, 3], total=100, page=2, page_size=20, total_pages=5
        )

        assert response.items == [1, 2, 3]
        assert response.total == 100
        assert response.page == 2
        assert response.page_size == 20
        assert response.total_pages == 5


class TestHelperFunctions:
    """测试辅助函数."""

    def test_calculate_offset(self):
        """测试offset计算函数."""
        assert calculate_offset(1, 20) == 0
        assert calculate_offset(2, 20) == 20
        assert calculate_offset(3, 50) == 100
        assert calculate_offset(10, 10) == 90

    def test_calculate_offset_invalid_page(self):
        """测试无效page的offset计算."""
        # page < 1时自动修正为1
        assert calculate_offset(0, 20) == 0
        assert calculate_offset(-1, 20) == 0

    def test_calculate_total_pages(self):
        """测试总页数计算函数."""
        assert calculate_total_pages(100, 20) == 5
        assert calculate_total_pages(105, 20) == 6
        assert calculate_total_pages(99, 20) == 5
        assert calculate_total_pages(1, 20) == 1
        assert calculate_total_pages(20, 20) == 1
        assert calculate_total_pages(21, 20) == 2

    def test_calculate_total_pages_edge_cases(self):
        """测试总页数计算的边界情况."""
        assert calculate_total_pages(0, 20) == 0
        assert calculate_total_pages(-10, 20) == 0
        assert calculate_total_pages(100, 0) == 0
        assert calculate_total_pages(100, -20) == 0

    def test_validate_pagination_params(self):
        """测试参数验证和修正函数."""
        # 正常值
        page, page_size = validate_pagination_params(1, 20)
        assert page == 1
        assert page_size == 20

        # page < 1 修正为 1
        page, page_size = validate_pagination_params(0, 20)
        assert page == 1
        assert page_size == 20

        page, page_size = validate_pagination_params(-5, 20)
        assert page == 1
        assert page_size == 20

        # page_size < 1 修正为 20（默认值）
        page, page_size = validate_pagination_params(1, 0)
        assert page == 1
        assert page_size == 20

        page, page_size = validate_pagination_params(1, -10)
        assert page == 1
        assert page_size == 20

        # page_size > 100 修正为 100
        page, page_size = validate_pagination_params(1, 200)
        assert page == 1
        assert page_size == 100

        page, page_size = validate_pagination_params(5, 1000)
        assert page == 5
        assert page_size == 100

    def test_validate_pagination_params_custom_max(self):
        """测试自定义最大page_size的参数验证."""
        # 自定义max_page_size=50
        page, page_size = validate_pagination_params(1, 80, max_page_size=50)
        assert page == 1
        assert page_size == 50

        page, page_size = validate_pagination_params(1, 30, max_page_size=50)
        assert page == 1
        assert page_size == 30


class TestRealWorldScenarios:
    """测试真实场景."""

    def test_large_dataset_pagination(self):
        """测试大数据集分页."""
        # 假设有100,000条记录
        total = 100000
        page_size = 100

        # 第1页
        params = PaginationParams(page=1, page_size=page_size)
        response = PaginatedResponse.create([], total, params)
        assert response.total_pages == 1000
        assert response.page == 1

        # 中间某页
        params = PaginationParams(page=500, page_size=page_size)
        response = PaginatedResponse.create([], total, params)
        assert response.page == 500
        assert params.offset == 49900

        # 最后一页
        params = PaginationParams(page=1000, page_size=page_size)
        response = PaginatedResponse.create([], total, params)
        assert response.page == 1000
        assert params.offset == 99900

    def test_small_dataset_pagination(self):
        """测试小数据集分页."""
        # 只有15条记录，page_size=20
        total = 15
        params = PaginationParams(page=1, page_size=20)
        response = PaginatedResponse.create(list(range(15)), total, params)

        assert response.total == 15
        assert response.total_pages == 1
        assert len(response.items) == 15

    def test_api_typical_usage(self):
        """测试典型API使用场景."""
        # 模拟API接收参数
        page = 2
        page_size = 50

        # 创建分页参数
        params = PaginationParams(page=page, page_size=page_size)

        # 使用offset和limit查询数据库
        # SELECT * FROM table LIMIT {params.limit} OFFSET {params.offset}
        assert params.limit == 50
        assert params.offset == 50  # 跳过第一页的50条

        # 假设查询到48条数据，总共148条
        items = [{"id": i} for i in range(51, 99)]  # 48条
        total = 148

        # 创建响应
        response = PaginatedResponse.create(items, total, params)

        assert len(response.items) == 48
        assert response.total == 148
        assert response.page == 2
        assert response.total_pages == 3  # ceil(148/50)

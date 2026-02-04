"""区域配置API数据模型单元测试."""

import pytest
from pydantic import ValidationError

from src.api.schemas.region_schemas import RegionCreateRequest, RegionUpdateRequest


class TestRegionCreateRequest:
    """测试RegionCreateRequest模型."""

    def test_valid_region_create(self):
        """测试有效的区域创建请求."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "is_active": True,
            "camera_id": "camera_001",
        }
        region = RegionCreateRequest(**data)
        assert region.name == "测试区域"
        assert region.region_type == "work_area"
        assert len(region.polygon) == 4
        assert region.is_active is True

    def test_minimum_valid_polygon(self):
        """测试最小有效polygon（3个点）."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0], [50, 50]],
        }
        region = RegionCreateRequest(**data)
        assert len(region.polygon) == 3

    def test_polygon_missing(self):
        """测试缺少polygon字段."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            # polygon缺失
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "polygon" in str(exc_info.value)

    def test_polygon_null(self):
        """测试polygon为None."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": None,
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "polygon" in str(exc_info.value)

    def test_polygon_empty_list(self):
        """测试polygon为空列表."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "at least 3 items" in str(exc_info.value).lower()

    def test_polygon_insufficient_points(self):
        """测试polygon点数不足（少于3个）."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0]],  # 只有2个点
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        # Pydantic的min_items会先触发
        assert "at least 3 items" in str(exc_info.value).lower()

    def test_polygon_invalid_point_format(self):
        """测试polygon点格式错误（不是2个坐标）."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0], [50]],  # 第3个点只有1个值
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        # Pydantic会报告缺少字段
        assert (
            "Field required" in str(exc_info.value)
            or "missing" in str(exc_info.value).lower()
        )

    def test_polygon_non_numeric_coordinates(self):
        """测试polygon坐标不是数字."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], ["invalid", 0], [100, 100]],
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        # 类型错误
        assert (
            "type_error" in str(exc_info.value).lower()
            or "float" in str(exc_info.value).lower()
        )

    def test_polygon_extreme_coordinates(self):
        """测试极端坐标值."""
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], [1e11, 0], [0, 1e11]],  # 超出范围
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "超出有效范围" in str(exc_info.value)

    def test_region_type_invalid(self):
        """测试无效的region_type."""
        data = {
            "name": "测试区域",
            "region_type": "invalid_type",  # 无效类型
            "polygon": [[0, 0], [100, 0], [100, 100]],
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "无效的区域类型" in str(exc_info.value)

    def test_region_type_valid_values(self):
        """测试所有有效的region_type值."""
        valid_types = [
            "work_area",
            "restricted",
            "entrance",
            "exit",
            "dangerous",
            "monitoring",
            "custom",
        ]
        for region_type in valid_types:
            data = {
                "name": "测试区域",
                "region_type": region_type,
                "polygon": [[0, 0], [100, 0], [100, 100]],
            }
            region = RegionCreateRequest(**data)
            assert region.region_type == region_type

    def test_name_too_short(self):
        """测试name过短."""
        data = {
            "name": "",  # 空字符串
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0], [100, 100]],
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "name" in str(exc_info.value).lower()

    def test_name_too_long(self):
        """测试name过长."""
        data = {
            "name": "x" * 101,  # 超过100字符
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0], [100, 100]],
        }
        with pytest.raises(ValidationError) as exc_info:
            RegionCreateRequest(**data)
        assert "name" in str(exc_info.value).lower()

    def test_optional_fields(self):
        """测试可选字段."""
        # 只提供必填字段
        data = {
            "name": "测试区域",
            "region_type": "work_area",
            "polygon": [[0, 0], [100, 0], [100, 100]],
        }
        region = RegionCreateRequest(**data)
        assert region.is_active is True  # 默认值
        assert region.rules is None
        assert region.camera_id is None
        assert region.description is None

        # 提供所有字段
        data_full = {
            **data,
            "region_id": "region_001",
            "is_active": False,
            "rules": {"requireHairnet": True},
            "camera_id": "camera_001",
            "description": "测试描述",
        }
        region_full = RegionCreateRequest(**data_full)
        assert region_full.region_id == "region_001"
        assert region_full.is_active is False
        assert region_full.rules == {"requireHairnet": True}
        assert region_full.camera_id == "camera_001"
        assert region_full.description == "测试描述"


class TestRegionUpdateRequest:
    """测试RegionUpdateRequest模型."""

    def test_valid_update_all_fields(self):
        """测试更新所有字段."""
        data = {
            "name": "更新的区域",
            "region_type": "restricted",
            "polygon": [[10, 10], [110, 10], [110, 110]],
            "is_active": False,
            "rules": {"limitOccupancy": True},
            "camera_id": "camera_002",
            "description": "更新的描述",
        }
        region = RegionUpdateRequest(**data)
        assert region.name == "更新的区域"
        assert region.region_type == "restricted"
        assert len(region.polygon) == 3
        assert region.is_active is False

    def test_update_partial_fields(self):
        """测试只更新部分字段."""
        # 只更新name
        data = {"name": "新名称"}
        region = RegionUpdateRequest(**data)
        assert region.name == "新名称"
        assert region.region_type is None
        assert region.polygon is None

        # 只更新polygon
        data = {"polygon": [[0, 0], [50, 0], [50, 50]]}
        region = RegionUpdateRequest(**data)
        # Pydantic返回tuple而不是list
        assert len(region.polygon) == 3
        assert region.polygon[0] == (0, 0)
        assert region.name is None

    def test_update_empty_request(self):
        """测试空更新请求（所有字段都可选）."""
        data = {}
        region = RegionUpdateRequest(**data)
        assert region.name is None
        assert region.polygon is None
        assert region.is_active is None

    def test_update_polygon_invalid(self):
        """测试更新时polygon验证."""
        # polygon点数不足
        data = {"polygon": [[0, 0], [100, 0]]}
        with pytest.raises(ValidationError) as exc_info:
            RegionUpdateRequest(**data)
        # Pydantic会先报告min_length错误
        assert "at least 3 items" in str(exc_info.value).lower()

        # polygon格式错误
        data = {"polygon": [[0, 0], [100], [50, 50]]}
        with pytest.raises(ValidationError) as exc_info:
            RegionUpdateRequest(**data)
        # Pydantic会报告缺少字段
        assert (
            "Field required" in str(exc_info.value)
            or "missing" in str(exc_info.value).lower()
        )

    def test_update_region_type_invalid(self):
        """测试更新时region_type验证."""
        data = {"region_type": "invalid_type"}
        with pytest.raises(ValidationError) as exc_info:
            RegionUpdateRequest(**data)
        assert "无效的区域类型" in str(exc_info.value)


class TestRealWorldScenarios:
    """测试真实场景."""

    def test_create_typical_work_area(self):
        """测试创建典型的工作区域."""
        data = {
            "name": "车间A-1区",
            "region_type": "work_area",
            "polygon": [[50, 50], [950, 50], [950, 550], [50, 550]],  # 矩形
            "is_active": True,
            "rules": {
                "requireHairnet": True,
                "limitOccupancy": False,
                "timeRestriction": False,
            },
            "camera_id": "camera_workshop_a_1",
            "description": "车间A的主要工作区域，需要佩戴发网",
        }
        region = RegionCreateRequest(**data)
        assert region.name == "车间A-1区"
        assert len(region.polygon) == 4
        assert region.rules["requireHairnet"] is True

    def test_create_complex_polygon(self):
        """测试创建复杂多边形区域."""
        # 八边形
        data = {
            "name": "复杂区域",
            "region_type": "monitoring",
            "polygon": [
                [100, 0],
                [200, 0],
                [300, 100],
                [300, 200],
                [200, 300],
                [100, 300],
                [0, 200],
                [0, 100],
            ],
        }
        region = RegionCreateRequest(**data)
        assert len(region.polygon) == 8

    def test_update_to_disable_region(self):
        """测试禁用区域."""
        data = {"is_active": False, "description": "临时禁用"}
        region = RegionUpdateRequest(**data)
        assert region.is_active is False

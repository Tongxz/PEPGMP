"""
区域配置API数据模型

使用Pydantic进行请求验证和响应序列化
"""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class RegionCreateRequest(BaseModel):
    """创建区域请求模型.

    强制验证points/polygon字段，确保数据完整性。
    """

    region_id: Optional[str] = Field(None, description="区域ID（可选，系统自动生成）")
    name: str = Field(..., min_length=1, max_length=100, description="区域名称")
    region_type: str = Field(..., description="区域类型（如work_area, restricted等）")
    polygon: List[Tuple[float, float]] = Field(
        ..., min_length=3, description="区域坐标点（至少3个），格式：[[x,y], [x,y], ...]"
    )
    is_active: bool = Field(True, description="是否启用")
    rules: Optional[Dict[str, Any]] = Field(None, description="区域规则配置")
    camera_id: Optional[str] = Field(None, description="关联的摄像头ID")
    description: Optional[str] = Field(None, max_length=500, description="区域描述")

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v):
        """验证polygon字段."""
        if not v or len(v) < 3:
            raise ValueError("区域至少需要3个坐标点")

        for i, point in enumerate(v):
            if len(point) != 2:
                raise ValueError(f"第{i+1}个坐标点格式错误，应为[x, y]")

            x, y = point
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError(f"第{i+1}个坐标点的值必须是数字")

            # 检查坐标是否为NaN或Infinity
            if not (-1e10 < x < 1e10) or not (-1e10 < y < 1e10):
                raise ValueError(f"第{i+1}个坐标点的值超出有效范围")

        return v

    @field_validator("region_type")
    @classmethod
    def validate_region_type(cls, v):
        """验证region_type字段."""
        valid_types = {
            "work_area",
            "restricted",
            "entrance",
            "exit",
            "dangerous",
            "monitoring",
            "custom",
        }
        if v not in valid_types:
            raise ValueError(f"无效的区域类型: {v}, 有效值为: {', '.join(valid_types)}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "车间A工作区",
                "region_type": "work_area",
                "polygon": [[0, 0], [640, 0], [640, 480], [0, 480]],
                "is_active": True,
                "rules": {"requireHairnet": True, "limitOccupancy": False},
                "camera_id": "camera_001",
                "description": "车间A的主要工作区域",
            }
        }
    }


class RegionUpdateRequest(BaseModel):
    """更新区域请求模型."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    region_type: Optional[str] = None
    polygon: Optional[List[Tuple[float, float]]] = Field(None, min_length=3)
    is_active: Optional[bool] = None
    rules: Optional[Dict[str, Any]] = None
    camera_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v):
        """验证polygon字段（如果提供）."""
        if v is not None:
            if len(v) < 3:
                raise ValueError("区域至少需要3个坐标点")

            for i, point in enumerate(v):
                if len(point) != 2:
                    raise ValueError(f"第{i+1}个坐标点格式错误，应为[x, y]")

                x, y = point
                if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                    raise ValueError(f"第{i+1}个坐标点的值必须是数字")

                if not (-1e10 < x < 1e10) or not (-1e10 < y < 1e10):
                    raise ValueError(f"第{i+1}个坐标点的值超出有效范围")

        return v

    @field_validator("region_type")
    @classmethod
    def validate_region_type(cls, v):
        """验证region_type字段（如果提供）."""
        if v is not None:
            valid_types = {
                "work_area",
                "restricted",
                "entrance",
                "exit",
                "dangerous",
                "monitoring",
                "custom",
            }
            if v not in valid_types:
                raise ValueError(f"无效的区域类型: {v}, 有效值为: {', '.join(valid_types)}")
        return v


class RegionResponse(BaseModel):
    """区域响应模型."""

    region_id: str
    name: str
    region_type: str
    polygon: List[Tuple[float, float]]
    is_active: bool
    rules: Optional[Dict[str, Any]] = None
    camera_id: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "region_id": "region_001",
                "name": "车间A工作区",
                "region_type": "work_area",
                "polygon": [[0, 0], [640, 0], [640, 480], [0, 480]],
                "is_active": True,
                "rules": {"requireHairnet": True},
                "camera_id": "camera_001",
                "description": "车间A的主要工作区域",
                "created_at": "2026-01-26T10:00:00+00:00",
                "updated_at": "2026-01-26T10:00:00+00:00",
            }
        }
    }


class RegionListResponse(BaseModel):
    """区域列表响应模型."""

    regions: List[RegionResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "regions": [
                    {
                        "region_id": "region_001",
                        "name": "车间A工作区",
                        "region_type": "work_area",
                        "polygon": [[0, 0], [640, 0], [640, 480], [0, 480]],
                        "is_active": True,
                    }
                ],
                "total": 1,
            }
        }
    }


class RegionMetaUpdateRequest(BaseModel):
    """区域元信息更新请求模型."""

    canvas_width: Optional[int] = Field(None, ge=1, le=10000)
    canvas_height: Optional[int] = Field(None, ge=1, le=10000)
    background_image: Optional[str] = None
    scale: Optional[float] = Field(None, ge=0.1, le=10.0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "canvas_width": 1920,
                "canvas_height": 1080,
                "background_image": "/path/to/background.jpg",
                "scale": 1.0,
            }
        }
    }

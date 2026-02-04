"""
配置管理API路由

提供运行时配置调整功能，包括保存策略、检测参数等。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import get_detection_app_service
from src.application.detection_application_service import (
    DetectionApplicationService,
    SaveStrategy,
)

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

router = APIRouter()
logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pydantic模型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SavePolicyUpdateRequest(BaseModel):
    """保存策略更新请求"""

    strategy: Optional[str] = Field(
        None,
        description="保存策略: all, violations_only, interval, smart",
        example="violations_only",
    )
    save_interval: Optional[int] = Field(None, gt=0, description="保存间隔（帧数）", example=30)
    violation_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="违规严重程度阈值", example=0.7
    )
    normal_sample_interval: Optional[int] = Field(
        None, gt=0, description="正常样本采样间隔（帧数）", example=300
    )
    save_normal_summary: Optional[bool] = Field(
        None, description="是否保存统计摘要", example=True
    )


class SavePolicyResponse(BaseModel):
    """保存策略响应"""

    ok: bool = True
    strategy: str
    save_interval: int
    violation_threshold: float
    normal_sample_interval: int
    save_normal_summary: bool


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API端点
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/save-policy", summary="获取当前保存策略", response_model=SavePolicyResponse)
async def get_save_policy(
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> SavePolicyResponse:
    """
    获取当前的保存策略配置

    Returns:
        当前保存策略配置
    """
    if app_service is None:
        raise raise_http_exception(
            status_code=503,
            message="检测应用服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    policy = app_service.save_policy

    return SavePolicyResponse(
        ok=True,
        strategy=policy.strategy.value,
        save_interval=policy.save_interval,
        violation_threshold=policy.violation_severity_threshold,
        normal_sample_interval=policy.normal_sample_interval,
        save_normal_summary=policy.save_normal_summary,
    )


@router.put("/save-policy", summary="更新保存策略", response_model=SavePolicyResponse)
async def update_save_policy(
    request: SavePolicyUpdateRequest,
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> SavePolicyResponse:
    """
    运行时更新保存策略配置

    支持部分更新，只需提供需要修改的字段。

    Args:
        request: 保存策略更新请求
        app_service: 检测应用服务

    Returns:
        更新后的保存策略配置

    Examples:
        ```bash
        # 只保存违规
        curl -X PUT http://localhost:8000/api/v1/config/save-policy \
          -H "Content-Type: application/json" \
          -d '{"strategy": "violations_only", "violation_threshold": 0.8}'

        # 智能保存，调整采样间隔
        curl -X PUT http://localhost:8000/api/v1/config/save-policy \
          -H "Content-Type: application/json" \
          -d '{"strategy": "smart", "normal_sample_interval": 600}'
        ```
    """
    if app_service is None:
        raise raise_http_exception(
            status_code=503,
            message="检测应用服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    current_policy = app_service.save_policy

    try:
        # 更新策略（部分更新）
        if request.strategy is not None:
            try:
                current_policy.strategy = SaveStrategy[request.strategy.upper()]
            except KeyError:
                raise raise_http_exception(
                    status_code=400,
                    message=f"无效的保存策略: {request.strategy}，"
                    f"有效值: all, violations_only, interval, smart",
                )

        if request.save_interval is not None:
            current_policy.save_interval = request.save_interval

        if request.violation_threshold is not None:
            current_policy.violation_severity_threshold = request.violation_threshold

        if request.normal_sample_interval is not None:
            current_policy.normal_sample_interval = request.normal_sample_interval

        if request.save_normal_summary is not None:
            current_policy.save_normal_summary = request.save_normal_summary

        logger.info(
            f"保存策略已更新: strategy={current_policy.strategy.value}, "
            f"violation_threshold={current_policy.violation_severity_threshold}"
        )

        return SavePolicyResponse(
            ok=True,
            strategy=current_policy.strategy.value,
            save_interval=current_policy.save_interval,
            violation_threshold=current_policy.violation_severity_threshold,
            normal_sample_interval=current_policy.normal_sample_interval,
            save_normal_summary=current_policy.save_normal_summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新保存策略失败: {e}")
        raise raise_http_exception(
            status_code=500,
            message="更新保存策略失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.get("/detection-stats", summary="获取检测统计")
async def get_detection_stats(
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> Dict[str, Any]:
    """
    获取检测统计信息

    包括总帧数、正常帧数、违规帧数、保存率等。

    Returns:
        检测统计信息
    """
    if app_service is None:
        raise raise_http_exception(
            status_code=503,
            message="检测应用服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    stats = app_service.stats_buffer

    total_frames = stats.get("total_frames", 0)
    normal_frames = stats.get("normal_frames", 0)
    violation_frames = stats.get("violation_frames", 0)

    violation_rate = violation_frames / total_frames if total_frames > 0 else 0.0

    return {
        "ok": True,
        "stats": {
            "total_frames": total_frames,
            "normal_frames": normal_frames,
            "violation_frames": violation_frames,
            "violation_rate": round(violation_rate, 4),
            "last_summary_save": stats.get("last_summary_save", 0),
        },
        "save_policy": {
            "strategy": app_service.save_policy.strategy.value,
            "violation_threshold": app_service.save_policy.violation_severity_threshold,
        },
    }


@router.post("/detection-stats/reset", summary="重置检测统计")
async def reset_detection_stats(
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> Dict[str, Any]:
    """
    重置检测统计信息

    Returns:
        操作结果
    """
    if app_service is None:
        raise raise_http_exception(
            status_code=503,
            message="检测应用服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    # 重置统计缓冲
    app_service.stats_buffer = {
        "total_frames": 0,
        "normal_frames": 0,
        "violation_frames": 0,
        "last_summary_save": 0,
    }

    logger.info("检测统计已重置")

    return {"ok": True, "message": "检测统计已重置"}

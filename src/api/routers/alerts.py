from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from ...services.database_service import get_db_service
from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception


class BatchUpdateStatusRequest(BaseModel):
    """批量更新状态请求模型."""

    alert_ids: List[int]
    status: str
    handled_by: Optional[str] = None


try:
    from src.domain.services.alert_rule_service import AlertRuleService
    from src.domain.services.alert_service import AlertService
    from src.infrastructure.repositories.postgresql_alert_repository import (
        PostgreSQLAlertRepository,
    )
    from src.infrastructure.repositories.postgresql_alert_rule_repository import (
        PostgreSQLAlertRuleRepository,
    )

    async def get_alert_service() -> Optional[AlertService]:
        """获取告警服务实例."""
        try:
            db = await get_db_service()
            alert_repo = PostgreSQLAlertRepository(db.pool)
            return AlertService(alert_repo)
        except Exception:
            return None

    async def get_alert_rule_service() -> Optional[AlertRuleService]:
        """获取告警规则服务实例."""
        try:
            db = await get_db_service()
            alert_rule_repo = PostgreSQLAlertRuleRepository(db.pool)
            return AlertRuleService(alert_rule_repo)
        except Exception:
            return None

except Exception:
    get_alert_service = None  # type: ignore
    get_alert_rule_service = None  # type: ignore

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_alert_service():
    """确保告警服务可用，如果不可用则抛出HTTP异常."""
    if get_alert_service is None:
        raise raise_http_exception(
            status_code=503,
            message="告警领域服务不可用，请联系系统管理员",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )
    return get_alert_service


def _ensure_alert_rule_service():
    """确保告警规则服务可用，如果不可用则抛出HTTP异常."""
    if get_alert_rule_service is None:
        raise raise_http_exception(
            status_code=503,
            message="告警规则领域服务不可用，请联系系统管理员",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )
    return get_alert_rule_service


@router.get("/alerts/history-db", summary="查询告警历史（数据库）")
async def get_alert_history_db(
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量（用于分页）"),
    page: Optional[int] = Query(None, ge=1, description="页码（如果提供，将覆盖offset）"),
    camera_id: Optional[str] = Query(None, description="摄像头ID过滤"),
    alert_type: Optional[str] = Query(None, description="告警类型过滤"),
    sort_by: Optional[str] = Query(
        None, description="排序字段: timestamp, camera_id, alert_type, id"
    ),
    sort_order: str = Query("desc", description="排序方向: asc 或 desc"),
):
    """从 alert_history 表查询告警历史（支持分页和排序）."""
    try:
        get_service = _ensure_alert_service()
        alert_service = await get_service()
        if alert_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        # 如果提供了page参数，计算offset
        actual_offset = offset
        if page is not None:
            actual_offset = (page - 1) * limit

        result = await alert_service.get_alert_history(
            limit=limit,
            offset=actual_offset,
            camera_id=camera_id,
            alert_type=alert_type,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询告警历史失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="查询告警历史失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/alerts/rules", summary="列出告警规则")
async def list_alert_rules(
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量（用于分页）"),
    page: Optional[int] = Query(None, ge=1, description="页码（如果提供，将覆盖offset）"),
    camera_id: Optional[str] = Query(None, description="摄像头ID过滤"),
    enabled: Optional[bool] = Query(None, description="是否启用过滤"),
):
    """列出告警规则（支持分页）."""
    try:
        get_service = _ensure_alert_rule_service()
        alert_rule_service = await get_service()
        if alert_rule_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警规则领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        # 如果提供了page参数，计算offset
        actual_offset = offset
        if page is not None:
            actual_offset = (page - 1) * limit

        result = await alert_rule_service.list_alert_rules(
            limit=limit,
            offset=actual_offset,
            camera_id=camera_id,
            enabled=enabled,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出告警规则失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="列出告警规则失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.post("/alerts/rules", summary="创建告警规则")
async def create_alert_rule(
    payload: Dict[str, Any],
):
    """创建一条告警规则。"""
    try:
        get_service = _ensure_alert_rule_service()
        alert_rule_service = await get_service()
        if alert_rule_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警规则领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await alert_rule_service.create_alert_rule(payload)
        return result
    except ValueError as e:
        # 业务逻辑错误（如必填字段缺失），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建告警规则失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="创建告警规则失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.put("/alerts/rules/{rule_id}", summary="更新告警规则")
async def update_alert_rule(
    rule_id: int = Path(..., ge=1),
    updates: Dict[str, Any] = {},
):
    """部分更新告警规则（仅允许字段见后端实现）。"""
    try:
        get_service = _ensure_alert_rule_service()
        alert_rule_service = await get_service()
        if alert_rule_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警规则领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await alert_rule_service.update_alert_rule(rule_id, updates)
        return result
    except ValueError as e:
        # 业务逻辑错误（如告警规则不存在），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="更新告警规则失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.put("/alerts/history/{alert_id}/status", summary="更新告警状态")
async def update_alert_status(
    alert_id: int = Path(..., ge=1, description="告警ID"),
    payload: Dict[str, Any] = {},
):
    """更新告警状态（confirmed, false_positive, resolved）。

    Args:
        alert_id: 告警ID
        payload: 请求体，包含 status (必需) 和 handled_by (可选)
            - status: 新状态，必须是 confirmed, false_positive, resolved 之一
            - handled_by: 处理人（可选）
    """
    try:
        get_service = _ensure_alert_service()
        alert_service = await get_service()
        if alert_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        status = payload.get("status")
        if not status:
            raise raise_http_exception(
                status_code=400,
                message="缺少必需字段: status",
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
            )

        handled_by = payload.get("handled_by")

        result = await alert_service.update_alert_status(
            alert_id=alert_id,
            status=status,
            handled_by=handled_by,
        )
        return result
    except ValueError as e:
        # 业务逻辑错误（如告警不存在或状态值无效），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警状态失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="更新告警状态失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/alerts/statistics", summary="获取告警统计")
async def get_alert_statistics(
    start_time: Optional[str] = Query(None, description="开始时间 (ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO格式)"),
    camera_id: Optional[str] = Query(None, description="摄像头ID过滤"),
):
    """获取告警统计数据。

    返回告警的统计信息，包括：
    - 总告警数
    - 各状态的告警数（待处理、已确认、误报、已解决）
    - 各类型的告警数
    - 各摄像头的告警数
    """
    try:
        get_service = _ensure_alert_service()
        alert_service = await get_service()
        if alert_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        # 解析时间参数
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                raise raise_http_exception(
                    status_code=400,
                    message="无效的开始时间格式",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                raise raise_http_exception(
                    status_code=400,
                    message="无效的结束时间格式",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )

        result = await alert_service.get_alert_statistics(
            start_time=start_dt,
            end_time=end_dt,
            camera_id=camera_id,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警统计失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取告警统计失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/alerts/{alert_id}", summary="获取告警详情")
async def get_alert_detail(
    alert_id: int = Path(..., ge=1, description="告警ID"),
):
    """获取单个告警的详细信息。"""
    try:
        get_service = _ensure_alert_service()
        alert_service = await get_service()
        if alert_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await alert_service.get_alert_by_id(alert_id)
        if result is None:
            raise raise_http_exception(
                status_code=404,
                message=f"告警不存在: {alert_id}",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警详情失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取告警详情失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.post("/alerts/batch-update-status", summary="批量更新告警状态")
async def batch_update_alert_status(
    payload: BatchUpdateStatusRequest,
):
    """批量更新多个告警的状态。

    Args:
        payload: 请求体，包含:
            - alert_ids: 告警ID列表
            - status: 新状态 (confirmed, false_positive, resolved)
            - handled_by: 处理人（可选）
    """
    try:
        get_service = _ensure_alert_service()
        alert_service = await get_service()
        if alert_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        if not payload.alert_ids:
            raise raise_http_exception(
                status_code=400,
                message="告警ID列表不能为空",
                error_code=ErrorCode.VALIDATION_ERROR,
            )

        result = await alert_service.batch_update_status(
            alert_ids=payload.alert_ids,
            status=payload.status,
            handled_by=payload.handled_by,
        )
        return result
    except ValueError as e:
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新告警状态失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="批量更新告警状态失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.delete("/alerts/rules/{rule_id}", summary="删除告警规则")
async def delete_alert_rule(
    rule_id: int = Path(..., ge=1, description="规则ID"),
):
    """删除告警规则。"""
    try:
        get_service = _ensure_alert_rule_service()
        alert_rule_service = await get_service()
        if alert_rule_service is None:
            raise raise_http_exception(
                status_code=503,
                message="告警规则领域服务未初始化，请联系系统管理员",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await alert_rule_service.delete_alert_rule(rule_id)
        return result
    except ValueError as e:
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警规则失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="删除告警规则失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )

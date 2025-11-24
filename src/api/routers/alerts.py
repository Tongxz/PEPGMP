from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from ...services.database_service import get_db_service

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
        raise HTTPException(status_code=503, detail="告警领域服务不可用，请联系系统管理员")
    return get_alert_service


def _ensure_alert_rule_service():
    """确保告警规则服务可用，如果不可用则抛出HTTP异常."""
    if get_alert_rule_service is None:
        raise HTTPException(status_code=503, detail="告警规则领域服务不可用，请联系系统管理员")
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
            raise HTTPException(status_code=503, detail="告警领域服务未初始化，请联系系统管理员")

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
        raise HTTPException(status_code=500, detail=f"查询告警历史失败: {str(e)}")


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
            raise HTTPException(status_code=503, detail="告警规则领域服务未初始化，请联系系统管理员")

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
        raise HTTPException(status_code=500, detail=f"列出告警规则失败: {str(e)}")


@router.post("/alerts/rules", summary="创建告警规则")
async def create_alert_rule(
    payload: Dict[str, Any],
):
    """创建一条告警规则。"""
    try:
        get_service = _ensure_alert_rule_service()
        alert_rule_service = await get_service()
        if alert_rule_service is None:
            raise HTTPException(status_code=503, detail="告警规则领域服务未初始化，请联系系统管理员")

        result = await alert_rule_service.create_alert_rule(payload)
        return result
    except ValueError as e:
        # 业务逻辑错误（如必填字段缺失），直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建告警规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建告警规则失败: {str(e)}")


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
            raise HTTPException(status_code=503, detail="告警规则领域服务未初始化，请联系系统管理员")

        result = await alert_rule_service.update_alert_rule(rule_id, updates)
        return result
    except ValueError as e:
        # 业务逻辑错误（如告警规则不存在），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新告警规则失败: {str(e)}")

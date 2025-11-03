from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from src.api.utils.rollout import should_use_domain

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


@router.get("/alerts/history-db", summary="查询告警历史（数据库）")
async def get_alert_history_db(
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
):
    """从 alert_history 表查询告警历史."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_alert_service is not None:
            alert_service = await get_alert_service()  # type: ignore
            if alert_service:
                result = await alert_service.get_alert_history(
                    limit=limit, camera_id=camera_id, alert_type=alert_type
                )
                return result
    except Exception as e:
        logger.warning(f"告警服务查询历史失败，回退到数据库查询: {e}")
        import traceback

        logger.debug(traceback.format_exc())

    # 旧实现（回退）
    try:
        db = await get_db_service()
        rows = await db.get_alert_history(
            limit=limit, camera_id=camera_id, alert_type=alert_type
        )
        return {"count": len(rows), "items": rows}
    except Exception as e:
        logger.error(f"查询告警历史失败: {e}")
        raise HTTPException(status_code=500, detail="查询告警历史失败")


@router.get("/alerts/rules", summary="列出告警规则")
async def list_alert_rules(
    camera_id: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
):
    """列出告警规则."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_alert_rule_service is not None:
            alert_rule_service = await get_alert_rule_service()  # type: ignore
            if alert_rule_service:
                result = await alert_rule_service.list_alert_rules(
                    camera_id=camera_id, enabled=enabled
                )
                return result
    except Exception as e:
        logger.warning(f"告警规则服务列表查询失败，回退到数据库查询: {e}")

    # 旧实现（回退）
    try:
        db = await get_db_service()
        rules = await db.list_alert_rules(camera_id=camera_id, enabled=enabled)
        return {"count": len(rules), "items": rules}
    except Exception as e:
        logger.error(f"列出告警规则失败: {e}")
        raise HTTPException(status_code=500, detail="列出告警规则失败")


@router.post("/alerts/rules", summary="创建告警规则")
async def create_alert_rule(
    payload: Dict[str, Any],
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
):
    """创建一条告警规则。"""
    # 灰度：写操作需要更谨慎，使用should_use_domain进行灰度控制
    try:
        if should_use_domain(force_domain) and get_alert_rule_service is not None:
            alert_rule_service = await get_alert_rule_service()  # type: ignore
            if alert_rule_service:
                result = await alert_rule_service.create_alert_rule(payload)
                return result
    except ValueError as e:
        # 业务逻辑错误（如必填字段缺失），直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"告警规则服务创建失败，回退到数据库操作: {e}")

    # 旧实现（回退）
    try:
        required = ["name", "rule_type", "conditions"]
        for k in required:
            if k not in payload:
                raise HTTPException(status_code=400, detail=f"缺少必填字段: {k}")

        db = await get_db_service()
        new_id = await db.create_alert_rule(payload)
        return {"ok": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建告警规则失败: {e}")
        raise HTTPException(status_code=500, detail="创建告警规则失败")


@router.put("/alerts/rules/{rule_id}", summary="更新告警规则")
async def update_alert_rule(
    rule_id: int = Path(..., ge=1),
    updates: Dict[str, Any] = {},
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
):
    """部分更新告警规则（仅允许字段见后端实现）。"""
    # 灰度：写操作需要更谨慎，使用should_use_domain进行灰度控制
    try:
        if should_use_domain(force_domain) and get_alert_rule_service is not None:
            alert_rule_service = await get_alert_rule_service()  # type: ignore
            if alert_rule_service:
                result = await alert_rule_service.update_alert_rule(rule_id, updates)
                return result
    except ValueError as e:
        # 业务逻辑错误（如告警规则不存在），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"告警规则服务更新失败，回退到数据库操作: {e}")

    # 旧实现（回退）
    try:
        if not updates:
            return {"ok": True}
        db = await get_db_service()
        ok = await db.update_alert_rule(rule_id, updates)
        return {"ok": bool(ok)}
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}")
        raise HTTPException(status_code=500, detail="更新告警规则失败")

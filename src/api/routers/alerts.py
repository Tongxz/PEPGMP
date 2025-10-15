from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from ...services.database_service import get_db_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/alerts/history-db", summary="查询告警历史（数据库）")
async def get_alert_history_db(
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
):
    """从 alert_history 表查询告警历史。"""
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
):
    """列出告警规则。"""
    try:
        db = await get_db_service()
        rules = await db.list_alert_rules(camera_id=camera_id, enabled=enabled)
        return {"count": len(rules), "items": rules}
    except Exception as e:
        logger.error(f"列出告警规则失败: {e}")
        raise HTTPException(status_code=500, detail="列出告警规则失败")


@router.post("/alerts/rules", summary="创建告警规则")
async def create_alert_rule(payload: Dict[str, Any]):
    """创建一条告警规则。"""
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
):
    """部分更新告警规则（仅允许字段见后端实现）。"""
    try:
        if not updates:
            return {"ok": True}
        db = await get_db_service()
        ok = await db.update_alert_rule(rule_id, updates)
        return {"ok": bool(ok)}
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}")
        raise HTTPException(status_code=500, detail="更新告警规则失败")

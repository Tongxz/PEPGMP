"""
错误监控API路由
Error Monitoring API Routes

提供错误监控、健康检查和告警管理的API接口
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...utils.error_handler import ErrorCategory, ErrorSeverity, get_error_handler
from ...utils.error_monitor import AlertLevel, get_error_monitor, get_health_checker

router = APIRouter(prefix="/monitoring", tags=["错误监控"])
logger = logging.getLogger(__name__)


# Pydantic模型
class ErrorStatsResponse(BaseModel):
    """错误统计响应"""

    total_errors: int
    error_counts: Dict[str, int]
    severity_counts: Dict[str, int]
    category_counts: Dict[str, int]
    recent_errors: List[Dict[str, Any]]
    health_status: str
    recommendations: List[str]


class HealthStatusResponse(BaseModel):
    """健康状态响应"""

    health_score: int
    status: str
    active_alerts: int
    critical_alerts: int
    error_alerts: int
    warning_alerts: int
    error_stats: Dict[str, Any]
    monitoring_enabled: bool


class AlertResponse(BaseModel):
    """告警响应"""

    alert_id: str
    rule_name: str
    level: str
    message: str
    timestamp: float
    data: Dict[str, Any]
    resolved: bool
    resolved_at: Optional[float] = None


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    overall_health: Dict[str, Any]
    detailed_checks: Dict[str, Any]
    timestamp: float


# API端点
@router.get("/errors/stats", response_model=ErrorStatsResponse, summary="获取错误统计")
async def get_error_stats():
    """获取错误统计信息"""
    try:
        error_handler = get_error_handler()
        stats = error_handler.get_error_report()

        return ErrorStatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取错误统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取错误统计失败")


@router.get("/errors/by-category/{category}", summary="根据分类获取错误")
async def get_errors_by_category(
    category: str, limit: int = Query(50, ge=1, le=1000, description="返回错误数量限制")
):
    """根据错误分类获取错误列表"""
    try:
        # 验证分类
        try:
            error_category = ErrorCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的错误分类: {category}")

        error_handler = get_error_handler()
        errors = error_handler.error_tracker.get_errors_by_category(error_category)

        # 限制返回数量
        errors = errors[-limit:] if len(errors) > limit else errors

        # 转换为字典格式
        error_list = []
        for error in errors:
            error_dict = {
                "error_id": error.error_id,
                "severity": error.severity.value,
                "category": error.category.value,
                "message": error.message,
                "timestamp": error.context.timestamp,
                "function_name": error.context.function_name,
                "module_name": error.context.module_name,
                "line_number": error.context.line_number,
                "recovery_successful": error.recovery_successful,
                "retry_count": error.retry_count,
            }
            error_list.append(error_dict)

        return {
            "category": category,
            "total_count": len(
                error_handler.error_tracker.get_errors_by_category(error_category)
            ),
            "returned_count": len(error_list),
            "errors": error_list,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分类错误失败: {e}")
        raise HTTPException(status_code=500, detail="获取分类错误失败")


@router.get("/errors/by-severity/{severity}", summary="根据严重程度获取错误")
async def get_errors_by_severity(
    severity: str, limit: int = Query(50, ge=1, le=1000, description="返回错误数量限制")
):
    """根据错误严重程度获取错误列表"""
    try:
        # 验证严重程度
        try:
            error_severity = ErrorSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的错误严重程度: {severity}")

        error_handler = get_error_handler()
        errors = error_handler.error_tracker.get_errors_by_severity(error_severity)

        # 限制返回数量
        errors = errors[-limit:] if len(errors) > limit else errors

        # 转换为字典格式
        error_list = []
        for error in errors:
            error_dict = {
                "error_id": error.error_id,
                "severity": error.severity.value,
                "category": error.category.value,
                "message": error.message,
                "timestamp": error.context.timestamp,
                "function_name": error.context.function_name,
                "module_name": error.context.module_name,
                "line_number": error.context.line_number,
                "recovery_successful": error.recovery_successful,
                "retry_count": error.retry_count,
            }
            error_list.append(error_dict)

        return {
            "severity": severity,
            "total_count": len(
                error_handler.error_tracker.get_errors_by_severity(error_severity)
            ),
            "returned_count": len(error_list),
            "errors": error_list,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取严重程度错误失败: {e}")
        raise HTTPException(status_code=500, detail="获取严重程度错误失败")


@router.get("/health", response_model=HealthStatusResponse, summary="获取系统健康状态")
async def get_system_health():
    """获取系统健康状态"""
    try:
        error_monitor = get_error_monitor()
        health_status = error_monitor.get_health_status()

        return HealthStatusResponse(**health_status)

    except Exception as e:
        logger.error(f"获取健康状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取健康状态失败")


@router.get("/health/detailed", response_model=HealthCheckResponse, summary="获取详细健康检查")
async def get_detailed_health_check():
    """获取详细的健康检查结果"""
    try:
        from ...utils.error_monitor import get_system_health

        health_data = get_system_health()
        return HealthCheckResponse(**health_data)

    except Exception as e:
        logger.error(f"获取详细健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="获取详细健康检查失败")


@router.get("/alerts/active", summary="获取活跃告警")
async def get_active_alerts():
    """获取当前活跃的告警"""
    try:
        error_monitor = get_error_monitor()
        active_alerts = error_monitor.get_active_alerts()

        alert_list = []
        for alert in active_alerts:
            alert_dict = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "data": alert.data,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at,
            }
            alert_list.append(alert_dict)

        return {"active_alerts": alert_list, "total_count": len(alert_list)}

    except Exception as e:
        logger.error(f"获取活跃告警失败: {e}")
        raise HTTPException(status_code=500, detail="获取活跃告警失败")


@router.get("/alerts/history", summary="获取告警历史")
async def get_alert_history(
    limit: int = Query(100, ge=1, le=1000, description="返回告警数量限制")
):
    """获取告警历史"""
    try:
        error_monitor = get_error_monitor()
        alert_history = error_monitor.get_alert_history(limit)

        alert_list = []
        for alert in alert_history:
            alert_dict = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "data": alert.data,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at,
            }
            alert_list.append(alert_dict)

        return {"alert_history": alert_list, "total_count": len(alert_list)}

    except Exception as e:
        logger.error(f"获取告警历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取告警历史失败")


@router.post("/alerts/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(alert_id: str):
    """解决指定的告警"""
    try:
        error_monitor = get_error_monitor()
        error_monitor.resolve_alert(alert_id)

        return {
            "message": f"告警 {alert_id} 已解决",
            "alert_id": alert_id,
            "resolved_at": error_monitor.active_alerts.get(alert_id, {}).get(
                "resolved_at"
            ),
        }

    except Exception as e:
        logger.error(f"解决告警失败: {e}")
        raise HTTPException(status_code=500, detail="解决告警失败")


@router.get("/performance", summary="获取性能统计")
async def get_performance_stats():
    """获取性能统计信息"""
    try:
        # 这里可以集成性能监控数据
        # 暂时返回基础信息
        return {
            "message": "性能统计功能开发中",
            "timestamp": error_monitor.active_alerts.get(alert_id, {}).get(
                "resolved_at"
            ),
        }

    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能统计失败")


@router.post("/monitoring/start", summary="启动错误监控")
async def start_monitoring():
    """启动错误监控"""
    try:
        error_monitor = get_error_monitor()
        error_monitor.start_monitoring()

        return {"message": "错误监控已启动", "status": "started"}

    except Exception as e:
        logger.error(f"启动监控失败: {e}")
        raise HTTPException(status_code=500, detail="启动监控失败")


@router.post("/monitoring/stop", summary="停止错误监控")
async def stop_monitoring():
    """停止错误监控"""
    try:
        error_monitor = get_error_monitor()
        error_monitor.stop_monitoring()

        return {"message": "错误监控已停止", "status": "stopped"}

    except Exception as e:
        logger.error(f"停止监控失败: {e}")
        raise HTTPException(status_code=500, detail="停止监控失败")


@router.get("/monitoring/status", summary="获取监控状态")
async def get_monitoring_status():
    """获取监控状态"""
    try:
        error_monitor = get_error_monitor()

        return {
            "monitoring_enabled": error_monitor.monitoring,
            "alert_rules_count": len(error_monitor.alert_rules),
            "alert_channels_count": len(error_monitor.alert_channels),
            "active_alerts_count": len(error_monitor.get_active_alerts()),
            "error_tracker_stats": error_monitor.error_handler.error_tracker.get_error_stats(),
        }

    except Exception as e:
        logger.error(f"获取监控状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取监控状态失败")


# 错误分类和严重程度枚举端点
@router.get("/errors/categories", summary="获取错误分类列表")
async def get_error_categories():
    """获取所有可用的错误分类"""
    return {
        "categories": [category.value for category in ErrorCategory],
        "descriptions": {
            "detection": "检测相关错误",
            "model": "模型相关错误",
            "gpu": "GPU相关错误",
            "network": "网络相关错误",
            "database": "数据库相关错误",
            "file_io": "文件IO错误",
            "configuration": "配置相关错误",
            "validation": "验证相关错误",
            "timeout": "超时错误",
            "resource": "资源相关错误",
            "unknown": "未知错误",
        },
    }


@router.get("/errors/severities", summary="获取错误严重程度列表")
async def get_error_severities():
    """获取所有可用的错误严重程度"""
    return {
        "severities": [severity.value for severity in ErrorSeverity],
        "descriptions": {
            "low": "低严重性，不影响核心功能",
            "medium": "中等严重性，影响部分功能",
            "high": "高严重性，影响核心功能",
            "critical": "严重错误，系统可能不可用",
        },
    }


@router.get("/alerts/levels", summary="获取告警级别列表")
async def get_alert_levels():
    """获取所有可用的告警级别"""
    return {
        "levels": [level.value for level in AlertLevel],
        "descriptions": {
            "info": "信息级别告警",
            "warning": "警告级别告警",
            "error": "错误级别告警",
            "critical": "严重级别告警",
        },
    }

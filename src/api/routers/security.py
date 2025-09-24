"""
安全API路由
Security API Routes

提供安全相关的API接口，包括认证、授权、威胁检测和安全报告
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ...security.security_manager import (
    AccessControlRule,
    SecurityLevel,
    ThreatType,
    get_security_manager,
)

router = APIRouter(prefix="/security", tags=["安全管理"])
logger = logging.getLogger(__name__)

# 安全认证
security_scheme = HTTPBearer()


# Pydantic模型
class LoginRequest(BaseModel):
    """登录请求"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class UserInfo(BaseModel):
    """用户信息"""

    user_id: str
    username: str
    roles: List[str]
    session_id: Optional[str] = None


class SecurityEventResponse(BaseModel):
    """安全事件响应"""

    event_id: str
    threat_type: str
    severity: str
    source_ip: str
    user_agent: str
    request_path: str
    timestamp: float
    details: Dict[str, Any]
    blocked: bool
    resolved: bool


class SecurityReportResponse(BaseModel):
    """安全报告响应"""

    total_events_24h: int
    threat_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    blocked_ips: int
    active_sessions: int
    security_score: int


class AccessControlRuleRequest(BaseModel):
    """访问控制规则请求"""

    name: str
    pattern: str
    methods: List[str]
    allowed_roles: List[str]
    denied_ips: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    rate_limit: Optional[int] = None


# API端点
@router.post("/auth/login", response_model=LoginResponse, summary="用户登录")
async def login(request: LoginRequest, http_request: Request):
    """用户登录"""
    try:
        security_manager = get_security_manager()

        # 获取客户端信息
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 这里应该验证用户名和密码
        # 简化实现，实际项目中需要查询数据库
        if request.username == "admin" and request.password == "admin123":
            # 创建用户数据
            user_data = {
                "user_id": "admin_001",
                "username": request.username,
                "roles": ["admin"],
            }

            # 创建访问令牌
            access_token = security_manager.create_access_token(user_data)

            # 创建刷新令牌
            refresh_token = security_manager.jwt_manager.create_refresh_token(user_data)

            # 创建会话
            session_id = security_manager.create_user_session(
                user_id=user_data["user_id"],
                ip_address=client_ip,
                user_agent=user_agent,
            )

            logger.info(f"用户登录成功: {request.username} - {client_ip}")

            return LoginResponse(
                access_token=access_token, refresh_token=refresh_token, expires_in=1800
            )
        else:
            # 记录登录失败事件
            security_manager.record_security_event(
                threat_type=ThreatType.BRUTE_FORCE,
                severity=SecurityLevel.MEDIUM,
                source_ip=client_ip,
                user_agent=user_agent,
                request_path="/security/auth/login",
                details={"username": request.username, "reason": "invalid_credentials"},
            )

            raise HTTPException(status_code=401, detail="用户名或密码错误")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise HTTPException(status_code=500, detail="登录失败")


@router.post("/auth/logout", summary="用户登出")
async def logout(http_request: Request):
    """用户登出"""
    try:
        get_security_manager()

        # 获取会话ID
        session_id = http_request.cookies.get("session_id")
        if session_id:
            # 这里应该删除会话
            # 简化实现
            logger.info(f"用户登出: {session_id}")

        return {"message": "登出成功"}

    except Exception as e:
        logger.error(f"登出失败: {e}")
        raise HTTPException(status_code=500, detail="登出失败")


@router.get("/auth/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    """获取当前用户信息"""
    try:
        security_manager = get_security_manager()

        # 验证令牌
        payload = security_manager.verify_access_token(credentials.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="无效的访问令牌")

        return UserInfo(
            user_id=payload.get("user_id", ""),
            username=payload.get("username", ""),
            roles=payload.get("roles", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户信息失败")


@router.get("/events", summary="获取安全事件")
async def get_security_events(
    limit: int = 100, threat_type: Optional[str] = None, severity: Optional[str] = None
):
    """获取安全事件列表"""
    try:
        security_manager = get_security_manager()

        # 过滤事件
        events = (
            security_manager.security_events[-limit:]
            if limit > 0
            else security_manager.security_events
        )

        if threat_type:
            events = [e for e in events if e.threat_type.value == threat_type]

        if severity:
            events = [e for e in events if e.severity.value == severity]

        # 转换为响应格式
        event_list = []
        for event in events:
            event_list.append(
                {
                    "event_id": event.event_id,
                    "threat_type": event.threat_type.value,
                    "severity": event.severity.value,
                    "source_ip": event.source_ip,
                    "user_agent": event.user_agent,
                    "request_path": event.request_path,
                    "timestamp": event.timestamp,
                    "details": event.details,
                    "blocked": event.blocked,
                    "resolved": event.resolved,
                }
            )

        return {"events": event_list, "total_count": len(event_list)}

    except Exception as e:
        logger.error(f"获取安全事件失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全事件失败")


@router.get("/report", response_model=SecurityReportResponse, summary="获取安全报告")
async def get_security_report():
    """获取安全报告"""
    try:
        security_manager = get_security_manager()
        report = security_manager.get_security_report()

        return SecurityReportResponse(**report)

    except Exception as e:
        logger.error(f"获取安全报告失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全报告失败")


@router.get("/rules", summary="获取访问控制规则")
async def get_access_control_rules():
    """获取访问控制规则列表"""
    try:
        security_manager = get_security_manager()
        rules = security_manager.access_control.rules

        rule_list = []
        for rule in rules.values():
            rule_list.append(
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "methods": rule.methods,
                    "allowed_roles": rule.allowed_roles,
                    "denied_ips": rule.denied_ips,
                    "allowed_ips": rule.allowed_ips,
                    "rate_limit": rule.rate_limit,
                    "enabled": rule.enabled,
                }
            )

        return {"rules": rule_list, "total_count": len(rule_list)}

    except Exception as e:
        logger.error(f"获取访问控制规则失败: {e}")
        raise HTTPException(status_code=500, detail="获取访问控制规则失败")


@router.post("/rules", summary="创建访问控制规则")
async def create_access_control_rule(rule_request: AccessControlRuleRequest):
    """创建访问控制规则"""
    try:
        security_manager = get_security_manager()

        # 创建规则
        rule = AccessControlRule(
            rule_id=f"rule_{int(time.time())}",
            name=rule_request.name,
            pattern=rule_request.pattern,
            methods=rule_request.methods,
            allowed_roles=rule_request.allowed_roles,
            denied_ips=rule_request.denied_ips or [],
            allowed_ips=rule_request.allowed_ips or [],
            rate_limit=rule_request.rate_limit,
        )

        # 添加规则
        security_manager.access_control.add_rule(rule)

        logger.info(f"访问控制规则已创建: {rule.name}")

        return {"message": "规则创建成功", "rule_id": rule.rule_id}

    except Exception as e:
        logger.error(f"创建访问控制规则失败: {e}")
        raise HTTPException(status_code=500, detail="创建访问控制规则失败")


@router.delete("/rules/{rule_id}", summary="删除访问控制规则")
async def delete_access_control_rule(rule_id: str):
    """删除访问控制规则"""
    try:
        security_manager = get_security_manager()

        # 删除规则
        security_manager.access_control.remove_rule(rule_id)

        logger.info(f"访问控制规则已删除: {rule_id}")

        return {"message": "规则删除成功"}

    except Exception as e:
        logger.error(f"删除访问控制规则失败: {e}")
        raise HTTPException(status_code=500, detail="删除访问控制规则失败")


@router.get("/sessions", summary="获取活跃会话")
async def get_active_sessions():
    """获取活跃会话列表"""
    try:
        security_manager = get_security_manager()
        sessions = security_manager.access_control.sessions

        session_list = []
        for session in sessions.values():
            session_list.append(
                {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "expires_at": session.expires_at,
                    "is_active": session.is_active,
                }
            )

        return {"sessions": session_list, "total_count": len(session_list)}

    except Exception as e:
        logger.error(f"获取活跃会话失败: {e}")
        raise HTTPException(status_code=500, detail="获取活跃会话失败")


@router.post("/block-ip/{ip_address}", summary="阻止IP地址")
async def block_ip_address(ip_address: str, duration: int = 3600):
    """阻止IP地址"""
    try:
        security_manager = get_security_manager()

        # 阻止IP
        security_manager.access_control.block_ip(ip_address, duration)

        logger.warning(f"IP地址被阻止: {ip_address}, 持续时间: {duration}秒")

        return {"message": f"IP地址 {ip_address} 已被阻止", "duration": duration}

    except Exception as e:
        logger.error(f"阻止IP地址失败: {e}")
        raise HTTPException(status_code=500, detail="阻止IP地址失败")


@router.delete("/block-ip/{ip_address}", summary="解除IP阻止")
async def unblock_ip_address(ip_address: str):
    """解除IP阻止"""
    try:
        security_manager = get_security_manager()

        # 解除IP阻止
        security_manager.access_control.blocked_ips.discard(ip_address)

        logger.info(f"IP地址解除阻止: {ip_address}")

        return {"message": f"IP地址 {ip_address} 已解除阻止"}

    except Exception as e:
        logger.error(f"解除IP阻止失败: {e}")
        raise HTTPException(status_code=500, detail="解除IP阻止失败")


@router.get("/blocked-ips", summary="获取被阻止的IP列表")
async def get_blocked_ips():
    """获取被阻止的IP列表"""
    try:
        security_manager = get_security_manager()
        blocked_ips = list(security_manager.access_control.blocked_ips)

        return {"blocked_ips": blocked_ips, "total_count": len(blocked_ips)}

    except Exception as e:
        logger.error(f"获取被阻止IP列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取被阻止IP列表失败")


@router.post("/threat-detection/test", summary="测试威胁检测")
async def test_threat_detection(data: Dict[str, Any]):
    """测试威胁检测功能"""
    try:
        security_manager = get_security_manager()

        # 检测威胁
        threats = security_manager.detect_threats(data)

        return {
            "input_data": data,
            "detected_threats": [threat.value for threat in threats],
            "threat_count": len(threats),
        }

    except Exception as e:
        logger.error(f"威胁检测测试失败: {e}")
        raise HTTPException(status_code=500, detail="威胁检测测试失败")


@router.get("/threat-types", summary="获取威胁类型列表")
async def get_threat_types():
    """获取所有可用的威胁类型"""
    return {
        "threat_types": [threat_type.value for threat_type in ThreatType],
        "descriptions": {
            "brute_force": "暴力破解攻击",
            "sql_injection": "SQL注入攻击",
            "xss": "跨站脚本攻击",
            "csrf": "跨站请求伪造",
            "path_traversal": "路径遍历攻击",
            "rate_limit": "速率限制违规",
            "suspicious_activity": "可疑活动",
            "unauthorized_access": "未授权访问",
        },
    }


@router.get("/security-levels", summary="获取安全级别列表")
async def get_security_levels():
    """获取所有可用的安全级别"""
    return {
        "security_levels": [level.value for level in SecurityLevel],
        "descriptions": {
            "low": "低风险",
            "medium": "中等风险",
            "high": "高风险",
            "critical": "严重风险",
        },
    }


@router.get("/stats", summary="获取安全统计")
async def get_security_stats():
    """获取安全统计信息"""
    try:
        security_manager = get_security_manager()

        # 获取安全报告
        report = security_manager.get_security_report()

        # 获取访问控制统计
        access_control_stats = {
            "total_rules": len(security_manager.access_control.rules),
            "active_sessions": len(security_manager.access_control.sessions),
            "blocked_ips": len(security_manager.access_control.blocked_ips),
            "rate_limits": len(security_manager.access_control.rate_limits),
        }

        return {
            "security_report": report,
            "access_control_stats": access_control_stats,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"获取安全统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全统计失败")

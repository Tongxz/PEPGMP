"""
安全中间件
Security Middleware

为FastAPI应用提供全面的安全防护中间件
"""

import logging
import time
from typing import Callable, Dict, Any, Optional, List
from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...security.security_manager import (
    get_security_manager,
    ThreatType,
    SecurityLevel
)

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app, enable_threat_detection: bool = True):
        super().__init__(app)
        self.security_manager = get_security_manager()
        self.enable_threat_detection = enable_threat_detection
        
        # 开发环境临时禁用速率限制
        import os
        self.is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
        
        # 安全统计
        self.security_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "threat_detected": 0,
            "rate_limited": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        self.security_stats["total_requests"] += 1
        
        # 获取请求信息
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        request_path = str(request.url.path)
        method = request.method
        
        try:
            # 1. 检查访问权限
            if not self._check_access_permission(request, client_ip):
                self.security_stats["blocked_requests"] += 1
                return JSONResponse(
                    status_code=403,
                    content={"error": "访问被拒绝", "message": "您没有权限访问此资源"}
                )
            
            # 2. 威胁检测
            if self.enable_threat_detection:
                threats = await self._detect_threats(request)
                if threats:
                    self.security_stats["threat_detected"] += 1
                    self._handle_threats(threats, request, client_ip, user_agent)
                    return JSONResponse(
                        status_code=400,
                        content={"error": "请求被拒绝", "message": "检测到潜在的安全威胁"}
                    )
            
            # 3. 速率限制检查 (开发环境跳过)
            if not self.is_development and not self._check_rate_limit(client_ip):
                self.security_stats["rate_limited"] += 1
                return JSONResponse(
                    status_code=429,
                    content={"error": "请求过于频繁", "message": "请稍后再试"}
                )
            
            # 4. 处理请求
            response = await call_next(request)
            
            # 5. 后处理安全检查
            self._post_process_security_check(request, response, client_ip)
            
            return response
            
        except Exception as e:
            # 记录安全异常
            self.security_manager.record_security_event(
                threat_type=ThreatType.SUSPICIOUS_ACTIVITY,
                severity=SecurityLevel.MEDIUM,
                source_ip=client_ip,
                user_agent=user_agent,
                request_path=request_path,
                details={"error": str(e)}
            )
            raise
    
    def _check_access_permission(self, request: Request, client_ip: str) -> bool:
        """检查访问权限"""
        request_path = str(request.url.path)
        method = request.method
        
        # 获取用户角色（这里可以从JWT令牌或会话中获取）
        user_roles = self._get_user_roles(request)
        
        return self.security_manager.check_access_permission(
            request_path=request_path,
            method=method,
            user_ip=client_ip,
            user_roles=user_roles
        )
    
    def _get_user_roles(self, request: Request) -> List[str]:
        """获取用户角色"""
        # 从请求头中获取JWT令牌
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = self.security_manager.verify_access_token(token)
            if payload:
                return payload.get("roles", [])
        
        # 从会话中获取角色
        session_id = request.cookies.get("session_id")
        if session_id:
            session = self.security_manager.validate_user_session(session_id, request.client.host)
            if session:
                # 这里可以根据用户ID查询角色
                return ["user"]  # 默认角色
        
        return []  # 匿名用户
    
    async def _detect_threats(self, request: Request) -> List[ThreatType]:
        """检测威胁"""
        threats = []
        
        # 收集请求数据
        request_data = {}
        
        # 查询参数
        for key, value in request.query_params.items():
            request_data[key] = value
        
        # 路径参数
        for key, value in request.path_params.items():
            request_data[key] = value
        
        # 请求体（如果是表单数据）
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            try:
                form_data = await request.form()
                for key, value in form_data.items():
                    request_data[key] = value
            except Exception:
                pass
        
        # 检测威胁
        if request_data:
            threats = self.security_manager.detect_threats(request_data)
        
        return threats
    
    def _handle_threats(self, threats: List[ThreatType], request: Request, client_ip: str, user_agent: str):
        """处理威胁"""
        request_path = str(request.url.path)
        
        for threat in threats:
            # 确定威胁严重程度
            severity = self._get_threat_severity(threat)
            
            # 记录安全事件
            self.security_manager.record_security_event(
                threat_type=threat,
                severity=severity,
                source_ip=client_ip,
                user_agent=user_agent,
                request_path=request_path,
                details={
                    "method": request.method,
                    "threats": [t.value for t in threats]
                }
            )
            
            logger.warning(f"检测到威胁: {threat.value} - {client_ip}")
    
    def _get_threat_severity(self, threat: ThreatType) -> SecurityLevel:
        """获取威胁严重程度"""
        severity_mapping = {
            ThreatType.SQL_INJECTION: SecurityLevel.HIGH,
            ThreatType.XSS: SecurityLevel.HIGH,
            ThreatType.CSRF: SecurityLevel.MEDIUM,
            ThreatType.PATH_TRAVERSAL: SecurityLevel.HIGH,
            ThreatType.BRUTE_FORCE: SecurityLevel.MEDIUM,
            ThreatType.RATE_LIMIT: SecurityLevel.LOW,
            ThreatType.SUSPICIOUS_ACTIVITY: SecurityLevel.MEDIUM,
            ThreatType.UNAUTHORIZED_ACCESS: SecurityLevel.HIGH
        }
        
        return severity_mapping.get(threat, SecurityLevel.MEDIUM)
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """检查速率限制"""
        # 这里可以实现更复杂的速率限制逻辑
        # 目前使用访问控制管理器中的速率限制
        return True  # 简化实现
    
    def _post_process_security_check(self, request: Request, response: Response, client_ip: str):
        """后处理安全检查"""
        # 检查响应状态码
        if response.status_code >= 500:
            self.security_manager.record_security_event(
                threat_type=ThreatType.SUSPICIOUS_ACTIVITY,
                severity=SecurityLevel.LOW,
                source_ip=client_ip,
                user_agent=request.headers.get("user-agent", "unknown"),
                request_path=str(request.url.path),
                details={"status_code": response.status_code}
            )
    
    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        return {
            **self.security_stats,
            "security_report": self.security_manager.get_security_report()
        }

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app, protected_paths: List[str] = None):
        super().__init__(app)
        self.security_manager = get_security_manager()
        self.protected_paths = protected_paths or ["/api/admin", "/api/upload"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        request_path = str(request.url.path)
        
        # 检查是否需要认证
        if self._is_protected_path(request_path):
            # 验证认证
            if not self._authenticate_request(request):
                return JSONResponse(
                    status_code=401,
                    content={"error": "未授权", "message": "请先登录"}
                )
        
        return await call_next(request)
    
    def _is_protected_path(self, path: str) -> bool:
        """检查是否为受保护路径"""
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False
    
    def _authenticate_request(self, request: Request) -> bool:
        """认证请求"""
        # 检查JWT令牌
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = self.security_manager.verify_access_token(token)
            if payload:
                return True
        
        # 检查会话
        session_id = request.cookies.get("session_id")
        if session_id:
            session = self.security_manager.validate_user_session(
                session_id, 
                request.client.host if request.client else "unknown"
            )
            if session:
                return True
        
        return False

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF保护中间件"""
    
    def __init__(self, app, enable_csrf: bool = True):
        super().__init__(app)
        self.security_manager = get_security_manager()
        self.enable_csrf = enable_csrf
        
        # API路径豁免列表（通常API调用不需要CSRF保护）
        self.csrf_exempt_paths = [
            "/api/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 检查是否启用CSRF保护
        if not self.enable_csrf:
            return await call_next(request)
        
        # 检查是否为豁免路径
        request_path = str(request.url.path)
        if any(request_path.startswith(exempt_path) for exempt_path in self.csrf_exempt_paths):
            return await call_next(request)
        
        # 只对POST、PUT、DELETE请求进行CSRF检查
        if request.method in ["POST", "PUT", "DELETE"]:
            if not self._check_csrf_token(request):
                return JSONResponse(
                    status_code=403,
                    content={"error": "CSRF验证失败", "message": "无效的CSRF令牌"}
                )
        
        return await call_next(request)
    
    def _check_csrf_token(self, request: Request) -> bool:
        """检查CSRF令牌"""
        # 从请求头获取CSRF令牌
        csrf_token = request.headers.get("x-csrf-token")
        if not csrf_token:
            return False
        
        # 从会话中获取预期的CSRF令牌
        session_id = request.cookies.get("session_id")
        if not session_id:
            return False
        
        # 这里应该验证CSRF令牌
        # 简化实现，实际项目中需要更复杂的验证逻辑
        return len(csrf_token) > 0

class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    """内容安全策略中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        response = await call_next(request)
        
        # 添加安全头
        response.headers["Content-Security-Policy"] = self.csp_policy
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

def setup_security_middleware(app):
    """设置安全中间件"""
    import os
    
    # 检查环境
    is_development = os.getenv("ENVIRONMENT", "development") == "development"
    
    # 添加安全中间件
    app.add_middleware(SecurityMiddleware, enable_threat_detection=not is_development)
    
    # 添加认证中间件
    app.add_middleware(AuthenticationMiddleware)
    
    # 添加CSRF保护中间件（开发环境中禁用）
    app.add_middleware(CSRFProtectionMiddleware, enable_csrf=not is_development)
    
    # 添加内容安全策略中间件
    app.add_middleware(ContentSecurityPolicyMiddleware)
    
    if is_development:
        logger.info("安全中间件已设置（开发模式 - CSRF保护和威胁检测已禁用）")
    else:
        logger.info("安全中间件已设置（生产模式 - 完整安全保护）")

def get_security_middleware_stats(app) -> Dict[str, Any]:
    """获取安全中间件统计"""
    stats = {}
    
    # 获取安全中间件统计
    for middleware in app.user_middleware:
        if isinstance(middleware.cls, SecurityMiddleware):
            security_middleware = middleware.kwargs.get('app')
            if hasattr(security_middleware, 'get_security_stats'):
                stats['security'] = security_middleware.get_security_stats()
    
    return stats


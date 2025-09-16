"""
安全管理系统
Security Management System

提供全面的安全防护、访问控制、数据保护和威胁检测功能
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """威胁类型"""

    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    PATH_TRAVERSAL = "path_traversal"
    RATE_LIMIT = "rate_limit"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityEvent:
    """安全事件"""

    event_id: str
    threat_type: ThreatType
    severity: SecurityLevel
    source_ip: str
    user_agent: str
    request_path: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    resolved: bool = False


@dataclass
class AccessControlRule:
    """访问控制规则"""

    rule_id: str
    name: str
    pattern: str  # URL模式
    methods: List[str]  # HTTP方法
    allowed_roles: List[str]
    denied_ips: List[str] = field(default_factory=list)
    allowed_ips: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None  # 每分钟请求数限制
    enabled: bool = True


@dataclass
class UserSession:
    """用户会话"""

    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: float
    last_activity: float
    expires_at: float
    is_active: bool = True


class PasswordManager:
    """密码管理器"""

    def __init__(self):
        self.salt_length = 32
        self.hash_algorithm = "sha256"
        self.iterations = 100000

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_hex(self.salt_length)
        password_hash = hashlib.pbkdf2_hmac(
            self.hash_algorithm,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            self.iterations,
        )
        return f"{salt}:{password_hash.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, hash_hex = password_hash.split(":")
            password_hash_check = hashlib.pbkdf2_hmac(
                self.hash_algorithm,
                password.encode("utf-8"),
                salt.encode("utf-8"),
                self.iterations,
            )
            return hmac.compare_digest(hash_hex, password_hash_check.hex())
        except Exception:
            return False

    def generate_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)


class EncryptionManager:
    """加密管理器"""

    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = Fernet.generate_key()

        self.fernet = Fernet(self.master_key)

    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        encrypted_data = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise ValueError("解密失败")

    def encrypt_file(self, file_path: str, output_path: str):
        """加密文件"""
        with open(file_path, "rb") as f:
            data = f.read()

        encrypted_data = self.fernet.encrypt(data)

        with open(output_path, "wb") as f:
            f.write(encrypted_data)

    def decrypt_file(self, encrypted_file_path: str, output_path: str):
        """解密文件"""
        with open(encrypted_file_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = self.fernet.decrypt(encrypted_data)

        with open(output_path, "wb") as f:
            f.write(decrypted_data)


class JWTManager:
    """JWT令牌管理器"""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("令牌已过期")
            return None
        except jwt.InvalidTokenError:
            logger.warning("无效令牌")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """刷新访问令牌"""
        payload = self.verify_token(refresh_token)
        if payload and payload.get("type") == "refresh":
            # 移除过期时间和类型字段
            data = {k: v for k, v in payload.items() if k not in ["exp", "type"]}
            return self.create_access_token(data)
        return None


class ThreatDetector:
    """威胁检测器"""

    def __init__(self):
        self.sql_injection_patterns = [
            r"('|(\\')|(;)|(\\;)|(--)|(\\/\\*)|(\\*\\/)|(xp_)|(sp_))",
            r"(union|select|insert|update|delete|drop|create|alter)",
            r"(script|javascript|vbscript|onload|onerror)",
            r"(<|>|&lt;|&gt;|&amp;|&quot;|&#)",
        ]

        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]

        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"\.\.%2f",
            r"\.\.%5c",
        ]

    def detect_sql_injection(self, input_string: str) -> bool:
        """检测SQL注入"""
        import re

        input_lower = input_string.lower()

        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return True
        return False

    def detect_xss(self, input_string: str) -> bool:
        """检测XSS攻击"""
        import re

        for pattern in self.xss_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True
        return False

    def detect_path_traversal(self, input_string: str) -> bool:
        """检测路径遍历攻击"""
        import re

        for pattern in self.path_traversal_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True
        return False

    def detect_threats(self, request_data: Dict[str, Any]) -> List[ThreatType]:
        """检测威胁"""
        threats = []

        # 检查请求参数
        for key, value in request_data.items():
            if isinstance(value, str):
                if self.detect_sql_injection(value):
                    threats.append(ThreatType.SQL_INJECTION)
                if self.detect_xss(value):
                    threats.append(ThreatType.XSS)
                if self.detect_path_traversal(value):
                    threats.append(ThreatType.PATH_TRAVERSAL)

        return threats


class AccessControlManager:
    """访问控制管理器"""

    def __init__(self):
        self.rules: Dict[str, AccessControlRule] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.blocked_ips: Set[str] = set()
        self.rate_limits: Dict[str, List[float]] = {}

        # 设置默认规则
        self._setup_default_rules()

    def _setup_default_rules(self):
        """设置默认访问控制规则"""
        import os

        # 根据环境调整速率限制
        is_development = os.getenv("ENVIRONMENT", "development") == "development"
        api_rate_limit = 1000 if is_development else 100

        default_rules = [
            AccessControlRule(
                rule_id="admin_protection",
                name="管理员保护",
                pattern="/admin/*",
                methods=["GET", "POST", "PUT", "DELETE"],
                allowed_roles=["admin"],
                rate_limit=50 if is_development else 10,
            ),
            AccessControlRule(
                rule_id="api_protection",
                name="API保护",
                pattern="/api/*",
                methods=["GET", "POST", "PUT", "DELETE"],
                allowed_roles=["user", "admin"],
                rate_limit=api_rate_limit,
            ),
            AccessControlRule(
                rule_id="upload_protection",
                name="上传保护",
                pattern="/upload/*",
                methods=["POST"],
                allowed_roles=["user", "admin"],
                rate_limit=100 if is_development else 20,
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: AccessControlRule):
        """添加访问控制规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"访问控制规则已添加: {rule.name}")

    def remove_rule(self, rule_id: str):
        """移除访问控制规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"访问控制规则已移除: {rule_id}")

    def check_access(
        self, request_path: str, method: str, user_ip: str, user_roles: List[str] = None
    ) -> bool:
        """检查访问权限"""
        # 检查IP是否被阻止
        if user_ip in self.blocked_ips:
            return False

        # 查找匹配的规则
        matching_rules = []
        for rule in self.rules.values():
            if rule.enabled and self._match_pattern(rule.pattern, request_path):
                if method in rule.methods:
                    matching_rules.append(rule)

        if not matching_rules:
            return True  # 没有规则限制，允许访问

        # 检查规则
        for rule in matching_rules:
            # 检查IP白名单
            if rule.allowed_ips and user_ip not in rule.allowed_ips:
                continue

            # 检查IP黑名单
            if user_ip in rule.denied_ips:
                return False

            # 检查角色权限
            if rule.allowed_roles and user_roles:
                if not any(role in rule.allowed_roles for role in user_roles):
                    continue

            # 检查速率限制
            if rule.rate_limit and not self._check_rate_limit(user_ip, rule.rate_limit):
                return False

            return True

        return False

    def _match_pattern(self, pattern: str, path: str) -> bool:
        """匹配URL模式"""
        import fnmatch

        return fnmatch.fnmatch(path, pattern)

    def _check_rate_limit(self, user_ip: str, limit: int) -> bool:
        """检查速率限制"""
        import os

        # 开发环境跳过速率限制
        if os.getenv("ENVIRONMENT", "development") == "development":
            return True

        current_time = time.time()
        minute_ago = current_time - 60

        # 清理过期的请求记录
        if user_ip in self.rate_limits:
            self.rate_limits[user_ip] = [
                req_time
                for req_time in self.rate_limits[user_ip]
                if req_time > minute_ago
            ]
        else:
            self.rate_limits[user_ip] = []

        # 检查是否超过限制
        if len(self.rate_limits[user_ip]) >= limit:
            return False

        # 记录当前请求
        self.rate_limits[user_ip].append(current_time)
        return True

    def create_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """创建用户会话"""
        session_id = secrets.token_urlsafe(32)
        current_time = time.time()

        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=current_time,
            last_activity=current_time,
            expires_at=current_time + 3600,  # 1小时过期
        )

        self.sessions[session_id] = session
        return session_id

    def validate_session(
        self, session_id: str, ip_address: str
    ) -> Optional[UserSession]:
        """验证会话"""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # 检查会话是否过期
        if time.time() > session.expires_at:
            del self.sessions[session_id]
            return None

        # 检查IP地址是否匹配
        if session.ip_address != ip_address:
            logger.warning(f"会话IP地址不匹配: {session_id}")
            return None

        # 更新最后活动时间
        session.last_activity = time.time()

        return session

    def block_ip(self, ip: str, duration: int = 3600):
        """阻止IP地址"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP地址被阻止: {ip}, 持续时间: {duration}秒")

        # 设置自动解封
        def unblock_after_duration():
            time.sleep(duration)
            self.blocked_ips.discard(ip)
            logger.info(f"IP地址自动解封: {ip}")

        import threading

        threading.Thread(target=unblock_after_duration, daemon=True).start()


class SecurityManager:
    """安全管理器"""

    def __init__(self):
        self.password_manager = PasswordManager()
        self.encryption_manager = EncryptionManager()
        self.jwt_manager = JWTManager()
        self.threat_detector = ThreatDetector()
        self.access_control = AccessControlManager()

        self.security_events: List[SecurityEvent] = []
        self.max_events = 10000

        # 安全配置
        self.max_login_attempts = 5
        self.login_lockout_duration = 900  # 15分钟
        self.session_timeout = 3600  # 1小时

        logger.info("安全管理系统已初始化")

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.password_manager.hash_password(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self.password_manager.verify_password(password, password_hash)

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        return self.jwt_manager.create_access_token(user_data)

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证访问令牌"""
        return self.jwt_manager.verify_token(token)

    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        return self.encryption_manager.encrypt_data(data)

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        return self.encryption_manager.decrypt_data(encrypted_data)

    def detect_threats(self, request_data: Dict[str, Any]) -> List[ThreatType]:
        """检测威胁"""
        return self.threat_detector.detect_threats(request_data)

    def check_access_permission(
        self, request_path: str, method: str, user_ip: str, user_roles: List[str] = None
    ) -> bool:
        """检查访问权限"""
        return self.access_control.check_access(
            request_path, method, user_ip, user_roles
        )

    def create_user_session(
        self, user_id: str, ip_address: str, user_agent: str
    ) -> str:
        """创建用户会话"""
        return self.access_control.create_session(user_id, ip_address, user_agent)

    def validate_user_session(
        self, session_id: str, ip_address: str
    ) -> Optional[UserSession]:
        """验证用户会话"""
        return self.access_control.validate_session(session_id, ip_address)

    def record_security_event(
        self,
        threat_type: ThreatType,
        severity: SecurityLevel,
        source_ip: str,
        user_agent: str,
        request_path: str,
        details: Dict[str, Any] = None,
    ):
        """记录安全事件"""
        event = SecurityEvent(
            event_id=secrets.token_urlsafe(16),
            threat_type=threat_type,
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            request_path=request_path,
            timestamp=time.time(),
            details=details or {},
        )

        self.security_events.append(event)

        # 限制事件数量
        if len(self.security_events) > self.max_events:
            self.security_events = self.security_events[-self.max_events :]

        # 根据严重程度采取行动
        if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            self.access_control.block_ip(source_ip)
            event.blocked = True

        logger.warning(f"安全事件记录: {threat_type.value} - {source_ip}")

    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告"""
        current_time = time.time()
        last_24h = current_time - 86400

        # 统计最近24小时的安全事件
        recent_events = [
            event for event in self.security_events if event.timestamp >= last_24h
        ]

        # 按威胁类型统计
        threat_stats = {}
        for event in recent_events:
            threat_type = event.threat_type.value
            threat_stats[threat_type] = threat_stats.get(threat_type, 0) + 1

        # 按严重程度统计
        severity_stats = {}
        for event in recent_events:
            severity = event.severity.value
            severity_stats[severity] = severity_stats.get(severity, 0) + 1

        # 被阻止的IP统计
        blocked_ips = len(self.access_control.blocked_ips)

        return {
            "total_events_24h": len(recent_events),
            "threat_distribution": threat_stats,
            "severity_distribution": severity_stats,
            "blocked_ips": blocked_ips,
            "active_sessions": len(self.access_control.sessions),
            "security_score": self._calculate_security_score(recent_events),
        }

    def _calculate_security_score(self, events: List[SecurityEvent]) -> int:
        """计算安全分数"""
        if not events:
            return 100

        score = 100

        # 根据威胁类型扣分
        for event in events:
            if event.threat_type == ThreatType.SQL_INJECTION:
                score -= 20
            elif event.threat_type == ThreatType.XSS:
                score -= 15
            elif event.threat_type == ThreatType.BRUTE_FORCE:
                score -= 10
            elif event.threat_type == ThreatType.RATE_LIMIT:
                score -= 5

        # 根据严重程度扣分
        for event in events:
            if event.severity == SecurityLevel.CRITICAL:
                score -= 30
            elif event.severity == SecurityLevel.HIGH:
                score -= 20
            elif event.severity == SecurityLevel.MEDIUM:
                score -= 10
            elif event.severity == SecurityLevel.LOW:
                score -= 5

        return max(0, min(100, score))


# 全局安全管理器实例
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """获取全局安全管理器"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# 便捷函数
def hash_password(password: str) -> str:
    """哈希密码（便捷函数）"""
    return get_security_manager().hash_password(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码（便捷函数）"""
    return get_security_manager().verify_password(password, password_hash)


def create_access_token(user_data: Dict[str, Any]) -> str:
    """创建访问令牌（便捷函数）"""
    return get_security_manager().create_access_token(user_data)


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """验证访问令牌（便捷函数）"""
    return get_security_manager().verify_access_token(token)


def encrypt_data(data: str) -> str:
    """加密数据（便捷函数）"""
    return get_security_manager().encrypt_sensitive_data(data)


def decrypt_data(encrypted_data: str) -> str:
    """解密数据（便捷函数）"""
    return get_security_manager().decrypt_sensitive_data(encrypted_data)


# 使用示例
if __name__ == "__main__":
    # 获取安全管理器
    security = get_security_manager()

    # 密码管理
    password = "test_password"
    hashed = security.hash_password(password)
    print(f"密码哈希: {hashed}")
    print(f"密码验证: {security.verify_password(password, hashed)}")

    # JWT令牌
    user_data = {"user_id": "123", "username": "test_user"}
    token = security.create_access_token(user_data)
    print(f"访问令牌: {token}")

    payload = security.verify_access_token(token)
    print(f"令牌验证: {payload}")

    # 数据加密
    sensitive_data = "sensitive_information"
    encrypted = security.encrypt_sensitive_data(sensitive_data)
    print(f"加密数据: {encrypted}")

    decrypted = security.decrypt_sensitive_data(encrypted)
    print(f"解密数据: {decrypted}")

    # 威胁检测
    threats = security.detect_threats({"input": "'; DROP TABLE users; --"})
    print(f"检测到的威胁: {[t.value for t in threats]}")

    # 安全报告
    report = security.get_security_report()
    print(f"安全报告: {report}")

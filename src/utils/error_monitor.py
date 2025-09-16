"""
错误监控和告警系统
Error Monitoring and Alerting System

提供实时错误监控、告警通知、健康检查和错误分析功能
"""

import time
import logging
import threading
import smtplib
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict, deque
from enum import Enum

from .error_handler import ErrorInfo, ErrorSeverity, ErrorCategory, UnifiedErrorHandler

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: str  # 条件表达式
    threshold: int  # 阈值
    time_window: int  # 时间窗口（秒）
    alert_level: AlertLevel
    enabled: bool = True
    cooldown: int = 300  # 冷却时间（秒）
    last_triggered: float = 0

@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    rule_name: str
    level: AlertLevel
    message: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[float] = None

class AlertChannel:
    """告警通道基类"""
    
    def send_alert(self, alert: Alert) -> bool:
        """发送告警"""
        raise NotImplementedError

class EmailAlertChannel(AlertChannel):
    """邮件告警通道"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, 
                 from_email: str, to_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    def send_alert(self, alert: Alert) -> bool:
        """发送邮件告警"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.message}"
            
            body = f"""
告警ID: {alert.alert_id}
规则: {alert.rule_name}
级别: {alert.level.value}
时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp))}
消息: {alert.message}

详细信息:
{json.dumps(alert.data, indent=2, ensure_ascii=False)}
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"邮件告警发送成功: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"邮件告警发送失败: {e}")
            return False

class WebhookAlertChannel(AlertChannel):
    """Webhook告警通道"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
    
    def send_alert(self, alert: Alert) -> bool:
        """发送Webhook告警"""
        try:
            import requests
            
            payload = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "data": alert.data
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook告警发送成功: {alert.alert_id}")
                return True
            else:
                logger.error(f"Webhook告警发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook告警发送失败: {e}")
            return False

class LogAlertChannel(AlertChannel):
    """日志告警通道"""
    
    def send_alert(self, alert: Alert) -> bool:
        """记录日志告警"""
        log_message = (
            f"ALERT [{alert.level.value.upper()}] {alert.alert_id}: "
            f"{alert.message} (规则: {alert.rule_name})"
        )
        
        if alert.level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif alert.level == AlertLevel.ERROR:
            logger.error(log_message)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        return True

class ErrorMonitor:
    """错误监控器"""
    
    def __init__(self, error_handler: UnifiedErrorHandler):
        self.error_handler = error_handler
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_channels: List[AlertChannel] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.error_history: deque = deque(maxlen=10000)
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # 默认告警规则
        self._setup_default_rules()
        
        # 默认告警通道
        self._setup_default_channels()
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                name="critical_errors",
                condition="severity == 'critical'",
                threshold=1,
                time_window=60,
                alert_level=AlertLevel.CRITICAL,
                cooldown=60
            ),
            AlertRule(
                name="high_error_rate",
                condition="severity == 'high'",
                threshold=5,
                time_window=300,
                alert_level=AlertLevel.ERROR,
                cooldown=300
            ),
            AlertRule(
                name="gpu_errors",
                condition="category == 'gpu'",
                threshold=3,
                time_window=300,
                alert_level=AlertLevel.WARNING,
                cooldown=600
            ),
            AlertRule(
                name="model_errors",
                condition="category == 'model'",
                threshold=2,
                time_window=300,
                alert_level=AlertLevel.ERROR,
                cooldown=300
            ),
            AlertRule(
                name="network_errors",
                condition="category == 'network'",
                threshold=10,
                time_window=300,
                alert_level=AlertLevel.WARNING,
                cooldown=300
            ),
            AlertRule(
                name="detection_failures",
                condition="category == 'detection'",
                threshold=20,
                time_window=600,
                alert_level=AlertLevel.WARNING,
                cooldown=600
            )
        ]
        
        for rule in default_rules:
            self.add_alert_rule(rule)
    
    def _setup_default_channels(self):
        """设置默认告警通道"""
        # 添加日志告警通道
        self.add_alert_channel(LogAlertChannel())
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.alert_rules[rule.name] = rule
        logger.info(f"添加告警规则: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"移除告警规则: {rule_name}")
    
    def add_alert_channel(self, channel: AlertChannel):
        """添加告警通道"""
        self.alert_channels.append(channel)
        logger.info(f"添加告警通道: {type(channel).__name__}")
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("错误监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("错误监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                self._check_alert_rules()
                time.sleep(10)  # 每10秒检查一次
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(30)  # 出错时等待更长时间
    
    def _check_alert_rules(self):
        """检查告警规则"""
        current_time = time.time()
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # 检查冷却时间
            if current_time - rule.last_triggered < rule.cooldown:
                continue
            
            # 检查规则条件
            if self._evaluate_rule(rule):
                self._trigger_alert(rule)
                rule.last_triggered = current_time
    
    def _evaluate_rule(self, rule: AlertRule) -> bool:
        """评估告警规则"""
        try:
            # 获取时间窗口内的错误
            cutoff_time = time.time() - rule.time_window
            recent_errors = [
                error for error in self.error_handler.error_tracker.errors
                if error.context.timestamp >= cutoff_time
            ]
            
            # 根据条件计算匹配的错误数量
            if rule.condition == "severity == 'critical'":
                count = len([e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL])
            elif rule.condition == "severity == 'high'":
                count = len([e for e in recent_errors if e.severity == ErrorSeverity.HIGH])
            elif rule.condition == "category == 'gpu'":
                count = len([e for e in recent_errors if e.category == ErrorCategory.GPU])
            elif rule.condition == "category == 'model'":
                count = len([e for e in recent_errors if e.category == ErrorCategory.MODEL])
            elif rule.condition == "category == 'network'":
                count = len([e for e in recent_errors if e.category == ErrorCategory.NETWORK])
            elif rule.condition == "category == 'detection'":
                count = len([e for e in recent_errors if e.category == ErrorCategory.DETECTION])
            else:
                # 默认条件：总错误数
                count = len(recent_errors)
            
            return count >= rule.threshold
            
        except Exception as e:
            logger.error(f"评估告警规则失败: {rule.name}: {e}")
            return False
    
    def _trigger_alert(self, rule: AlertRule):
        """触发告警"""
        alert_id = f"ALERT_{int(time.time())}_{rule.name}"
        
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            level=AlertLevel(rule.alert_level.value),
            message=f"告警规则 '{rule.name}' 被触发",
            timestamp=time.time(),
            data={
                "rule_condition": rule.condition,
                "threshold": rule.threshold,
                "time_window": rule.time_window
            }
        )
        
        # 发送告警
        self._send_alert(alert)
        
        # 记录活跃告警
        with self.lock:
            self.active_alerts[alert_id] = alert
        
        logger.warning(f"告警触发: {alert_id}")
    
    def _send_alert(self, alert: Alert):
        """发送告警到所有通道"""
        for channel in self.alert_channels:
            try:
                channel.send_alert(alert)
            except Exception as e:
                logger.error(f"告警通道发送失败: {type(channel).__name__}: {e}")
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = time.time()
                logger.info(f"告警已解决: {alert_id}")
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        with self.lock:
            return [alert for alert in self.active_alerts.values() if not alert.resolved]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        with self.lock:
            alerts = list(self.active_alerts.values())
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            return alerts[:limit]
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        stats = self.error_handler.get_error_report()
        active_alerts = self.get_active_alerts()
        
        # 计算健康分数
        health_score = 100
        critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
        error_alerts = [a for a in active_alerts if a.level == AlertLevel.ERROR]
        warning_alerts = [a for a in active_alerts if a.level == AlertLevel.WARNING]
        
        health_score -= len(critical_alerts) * 30
        health_score -= len(error_alerts) * 15
        health_score -= len(warning_alerts) * 5
        
        health_score = max(0, health_score)
        
        # 确定健康状态
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "fair"
        elif health_score >= 30:
            status = "poor"
        else:
            status = "critical"
        
        return {
            "health_score": health_score,
            "status": status,
            "active_alerts": len(active_alerts),
            "critical_alerts": len(critical_alerts),
            "error_alerts": len(error_alerts),
            "warning_alerts": len(warning_alerts),
            "error_stats": stats,
            "monitoring_enabled": self.monitoring
        }

class HealthChecker:
    """健康检查器"""
    
    def __init__(self, error_monitor: ErrorMonitor):
        self.error_monitor = error_monitor
        self.health_checks: Dict[str, Callable] = {}
        self._setup_default_checks()
    
    def _setup_default_checks(self):
        """设置默认健康检查"""
        self.health_checks.update({
            "error_rate": self._check_error_rate,
            "gpu_status": self._check_gpu_status,
            "model_status": self._check_model_status,
            "memory_usage": self._check_memory_usage,
            "disk_space": self._check_disk_space
        })
    
    def add_health_check(self, name: str, check_func: Callable):
        """添加健康检查"""
        self.health_checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": str(e),
                    "timestamp": time.time()
                }
        
        return results
    
    def _check_error_rate(self) -> Dict[str, Any]:
        """检查错误率"""
        stats = self.error_monitor.error_handler.get_error_report()
        total_errors = stats.get("total_errors", 0)
        
        # 计算最近1小时的错误率
        recent_errors = len([
            e for e in self.error_monitor.error_handler.error_tracker.errors
            if e.context.timestamp >= time.time() - 3600
        ])
        
        error_rate = recent_errors / 3600 if recent_errors > 0 else 0
        
        return {
            "status": "healthy" if error_rate < 1 else "warning" if error_rate < 5 else "critical",
            "error_rate": error_rate,
            "total_errors": total_errors,
            "recent_errors": recent_errors,
            "timestamp": time.time()
        }
    
    def _check_gpu_status(self) -> Dict[str, Any]:
        """检查GPU状态"""
        try:
            import torch
            
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_utilization = torch.cuda.utilization(0) if gpu_count > 0 else 0
                memory_info = torch.cuda.mem_get_info(0) if gpu_count > 0 else (0, 0)
                memory_used = (memory_info[1] - memory_info[0]) / (1024**3)
                memory_total = memory_info[1] / (1024**3)
                
                return {
                    "status": "healthy" if gpu_utilization < 90 and memory_used / memory_total < 0.9 else "warning",
                    "gpu_count": gpu_count,
                    "gpu_utilization": gpu_utilization,
                    "memory_used_gb": memory_used,
                    "memory_total_gb": memory_total,
                    "memory_usage_percent": (memory_used / memory_total) * 100,
                    "timestamp": time.time()
                }
            else:
                return {
                    "status": "warning",
                    "message": "CUDA不可用",
                    "timestamp": time.time()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
    
    def _check_model_status(self) -> Dict[str, Any]:
        """检查模型状态"""
        # 这里可以检查模型文件是否存在、是否可加载等
        return {
            "status": "healthy",
            "message": "模型状态检查未实现",
            "timestamp": time.time()
        }
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """检查内存使用"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            
            return {
                "status": "healthy" if memory.percent < 80 else "warning" if memory.percent < 90 else "critical",
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            import psutil
            
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy" if disk.percent < 80 else "warning" if disk.percent < 90 else "critical",
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }

# 全局监控器实例
_error_monitor = None
_health_checker = None

def get_error_monitor() -> ErrorMonitor:
    """获取全局错误监控器"""
    global _error_monitor
    if _error_monitor is None:
        error_handler = UnifiedErrorHandler()
        _error_monitor = ErrorMonitor(error_handler)
    return _error_monitor

def get_health_checker() -> HealthChecker:
    """获取全局健康检查器"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(get_error_monitor())
    return _health_checker

def start_error_monitoring():
    """启动错误监控（便捷函数）"""
    get_error_monitor().start_monitoring()

def stop_error_monitoring():
    """停止错误监控（便捷函数）"""
    get_error_monitor().stop_monitoring()

def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态（便捷函数）"""
    monitor = get_error_monitor()
    checker = get_health_checker()
    
    health_status = monitor.get_health_status()
    health_checks = checker.run_health_checks()
    
    return {
        "overall_health": health_status,
        "detailed_checks": health_checks,
        "timestamp": time.time()
    }


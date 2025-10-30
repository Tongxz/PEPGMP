"""
依赖注入容器
提供服务的注册和解析功能
"""

from .service_container import ServiceContainer, container

__all__ = ["ServiceContainer", "container"]

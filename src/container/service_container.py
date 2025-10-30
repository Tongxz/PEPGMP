"""
依赖注入服务容器
提供服务的注册、解析和生命周期管理
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ServiceContainer:
    """简单的依赖注入容器"""

    def __init__(self):
        self._services: Dict[Type, Type] = {}  # 接口 -> 实现类
        self._factories: Dict[Type, Callable] = {}  # 接口 -> 工厂函数
        self._singletons: Dict[Type, Any] = {}  # 接口 -> 单例实例
        self._instances: Dict[Type, Any] = {}  # 接口 -> 预注册实例
        self._transient_cache: Dict[Type, Any] = {}  # 瞬态服务缓存（用于循环依赖检测）

        logger.info("服务容器初始化完成")

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """
        注册单例服务

        Args:
            interface: 接口类型
            implementation: 实现类型
        """
        self._services[interface] = implementation
        logger.info(f"注册单例服务: {interface.__name__} -> {implementation.__name__}")

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        注册工厂服务

        Args:
            interface: 接口类型
            factory: 工厂函数
        """
        self._factories[interface] = factory
        logger.info(f"注册工厂服务: {interface.__name__}")

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        注册预创建实例

        Args:
            interface: 接口类型
            instance: 实例对象
        """
        self._instances[interface] = instance
        logger.info(f"注册实例: {interface.__name__}")

    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """
        注册瞬态服务（每次获取都创建新实例）

        Args:
            interface: 接口类型
            implementation: 实现类型
        """
        self._factories[interface] = lambda: implementation()
        logger.info(f"注册瞬态服务: {interface.__name__} -> {implementation.__name__}")

    def get(self, interface: Type[T]) -> T:
        """
        获取服务实例

        Args:
            interface: 接口类型

        Returns:
            T: 服务实例

        Raises:
            ValueError: 服务未注册时抛出
        """
        # 1. 优先返回预注册实例
        if interface in self._instances:
            return self._instances[interface]

        # 2. 检查单例缓存
        if interface in self._singletons:
            return self._singletons[interface]

        # 3. 检查瞬态服务缓存（用于循环依赖检测）
        if interface in self._transient_cache:
            logger.warning(f"检测到循环依赖: {interface.__name__}")
            return self._transient_cache[interface]

        # 4. 创建新实例
        instance = self._create_instance(interface)

        # 5. 如果是单例服务，缓存实例
        if interface in self._services:
            self._singletons[interface] = instance

        return instance

    def _create_instance(self, interface: Type[T]) -> T:
        """创建服务实例"""
        # 检查工厂服务
        if interface in self._factories:
            return self._factories[interface]()

        # 检查单例服务
        if interface in self._services:
            implementation = self._services[interface]
            return implementation()

        # 服务未找到
        available_services = (
            list(self._services.keys())
            + list(self._factories.keys())
            + list(self._instances.keys())
        )
        available_names = [s.__name__ for s in available_services]
        raise ValueError(f"未找到服务: {interface.__name__}. 可用服务: {available_names}")

    def is_registered(self, interface: Type[T]) -> bool:
        """
        检查服务是否已注册

        Args:
            interface: 接口类型

        Returns:
            bool: 是否已注册
        """
        return (
            interface in self._services
            or interface in self._factories
            or interface in self._instances
        )

    def get_registered_services(self) -> Dict[str, str]:
        """
        获取已注册的服务列表

        Returns:
            Dict[str, str]: 服务名称 -> 服务类型
        """
        services = {}

        for interface in self._services:
            services[
                interface.__name__
            ] = f"Singleton -> {self._services[interface].__name__}"

        for interface in self._factories:
            services[interface.__name__] = "Factory"

        for interface in self._instances:
            services[interface.__name__] = "Instance"

        return services

    def clear_cache(self) -> None:
        """清空单例缓存"""
        self._singletons.clear()
        self._transient_cache.clear()
        logger.info("服务缓存已清空")

    def reset(self) -> None:
        """重置容器"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._instances.clear()
        self._transient_cache.clear()
        logger.info("服务容器已重置")


# 全局容器实例
container = ServiceContainer()


def inject(interface: Type[T]) -> T:
    """
    依赖注入装饰器

    Args:
        interface: 要注入的接口类型

    Returns:
        T: 服务实例
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从容器获取服务实例
            service_instance = container.get(interface)
            # 将服务实例作为参数传递给函数
            return func(service_instance, *args, **kwargs)

        return wrapper

    return decorator


def get_service(interface: Type[T]) -> T:
    """
    获取服务实例的便捷函数

    Args:
        interface: 接口类型

    Returns:
        T: 服务实例
    """
    return container.get(interface)

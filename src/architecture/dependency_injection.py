"""
依赖注入容器
Dependency Injection Container

提供依赖注入功能，降低模块耦合度，提高可测试性和可维护性
"""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Callable, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class ServiceDefinition:
    """服务定义"""
    service_type: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    singleton: bool = True
    dependencies: List[Type] = field(default_factory=list)
    instance: Optional[Any] = None

class ServiceContainer:
    """服务容器"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDefinition] = {}
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        
    def register_singleton(self, service_type: Type[T], implementation: Optional[Type[T]] = None) -> 'ServiceContainer':
        """注册单例服务"""
        self._services[service_type] = ServiceDefinition(
            service_type=service_type,
            implementation=implementation or service_type,
            singleton=True
        )
        return self
    
    def register_transient(self, service_type: Type[T], implementation: Optional[Type[T]] = None) -> 'ServiceContainer':
        """注册瞬态服务"""
        self._services[service_type] = ServiceDefinition(
            service_type=service_type,
            implementation=implementation or service_type,
            singleton=False
        )
        return self
    
    def register_factory(self, service_type: Type[T], factory: Callable[[], T]) -> 'ServiceContainer':
        """注册工厂服务"""
        self._services[service_type] = ServiceDefinition(
            service_type=service_type,
            factory=factory,
            singleton=False
        )
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """注册实例服务"""
        self._instances[service_type] = instance
        return self
    
    def get(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        # 检查是否已有实例
        if service_type in self._instances:
            return self._instances[service_type]
        
        # 检查服务定义
        if service_type not in self._services:
            raise ValueError(f"服务 {service_type.__name__} 未注册")
        
        definition = self._services[service_type]
        
        # 使用工厂创建实例
        if definition.factory:
            instance = definition.factory()
        else:
            # 使用构造函数创建实例
            instance = self._create_instance(definition)
        
        # 如果是单例，缓存实例
        if definition.singleton:
            self._instances[service_type] = instance
        
        return instance
    
    def _create_instance(self, definition: ServiceDefinition) -> Any:
        """创建服务实例"""
        implementation = definition.implementation or definition.service_type
        
        # 获取构造函数参数
        signature = inspect.signature(implementation.__init__)
        kwargs = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            
            # 检查参数类型注解
            if param.annotation != inspect.Parameter.empty:
                # 递归解析依赖
                dependency = self.get(param.annotation)
                kwargs[param_name] = dependency
        
        return implementation(**kwargs)
    
    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services or service_type in self._instances
    
    def clear(self):
        """清空容器"""
        self._services.clear()
        self._instances.clear()
        self._factories.clear()

# 全局容器实例
_container: Optional[ServiceContainer] = None

def get_container() -> ServiceContainer:
    """获取全局容器实例"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container

def register_singleton(service_type: Type[T], implementation: Optional[Type[T]] = None) -> ServiceContainer:
    """注册单例服务（便捷函数）"""
    return get_container().register_singleton(service_type, implementation)

def register_transient(service_type: Type[T], implementation: Optional[Type[T]] = None) -> ServiceContainer:
    """注册瞬态服务（便捷函数）"""
    return get_container().register_transient(service_type, implementation)

def register_factory(service_type: Type[T], factory: Callable[[], T]) -> ServiceContainer:
    """注册工厂服务（便捷函数）"""
    return get_container().register_factory(service_type, factory)

def register_instance(service_type: Type[T], instance: T) -> ServiceContainer:
    """注册实例服务（便捷函数）"""
    return get_container().register_instance(service_type, instance)

def resolve(service_type: Type[T]) -> T:
    """解析服务（便捷函数）"""
    return get_container().get(service_type)

# 装饰器支持
def injectable(cls: Type[T]) -> Type[T]:
    """可注入类装饰器"""
    cls._is_injectable = True
    return cls

def inject(service_type: Type[T]) -> T:
    """依赖注入装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 注入依赖
            dependency = resolve(service_type)
            return func(dependency, *args, **kwargs)
        return wrapper
    return decorator

# 服务接口定义
class ILogger(ABC):
    """日志服务接口"""
    
    @abstractmethod
    def info(self, message: str):
        pass
    
    @abstractmethod
    def warning(self, message: str):
        pass
    
    @abstractmethod
    def error(self, message: str):
        pass

class IConfigService(ABC):
    """配置服务接口"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any):
        pass

class IDetectionService(ABC):
    """检测服务接口"""
    
    @abstractmethod
    def detect(self, image: Any) -> Dict[str, Any]:
        pass

class IModelService(ABC):
    """模型服务接口"""
    
    @abstractmethod
    def load_model(self, model_path: str) -> Any:
        pass
    
    @abstractmethod
    def predict(self, model: Any, data: Any) -> Any:
        pass

# 具体实现
@injectable
class LoggerService(ILogger):
    """日志服务实现"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)

@injectable
class ConfigService(IConfigService):
    """配置服务实现"""
    
    def __init__(self):
        self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        self._config[key] = value

# 服务注册器
class ServiceRegistrar:
    """服务注册器"""
    
    @staticmethod
    def register_core_services(container: ServiceContainer):
        """注册核心服务"""
        # 注册日志服务
        container.register_singleton(ILogger, LoggerService)
        
        # 注册配置服务
        container.register_singleton(IConfigService, ConfigService)
        
        logger.info("核心服务注册完成")
    
    @staticmethod
    def register_detection_services(container: ServiceContainer):
        """注册检测服务"""
        # 这里可以注册各种检测器服务
        # container.register_singleton(IDetectionService, DetectionService)
        logger.info("检测服务注册完成")
    
    @staticmethod
    def register_model_services(container: ServiceContainer):
        """注册模型服务"""
        # 这里可以注册模型相关服务
        # container.register_singleton(IModelService, ModelService)
        logger.info("模型服务注册完成")

# 服务定位器模式
class ServiceLocator:
    """服务定位器"""
    
    def __init__(self, container: ServiceContainer):
        self._container = container
    
    def get_service(self, service_type: Type[T]) -> T:
        """获取服务"""
        return self._container.get(service_type)
    
    def get_optional_service(self, service_type: Type[T]) -> Optional[T]:
        """获取可选服务"""
        try:
            return self._container.get(service_type)
        except ValueError:
            return None

# 模块初始化器
class ModuleInitializer:
    """模块初始化器"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
    
    def initialize_all_modules(self):
        """初始化所有模块"""
        # 注册核心服务
        ServiceRegistrar.register_core_services(self.container)
        
        # 注册检测服务
        ServiceRegistrar.register_detection_services(self.container)
        
        # 注册模型服务
        ServiceRegistrar.register_model_services(self.container)
        
        logger.info("所有模块初始化完成")
    
    def initialize_detection_module(self):
        """初始化检测模块"""
        ServiceRegistrar.register_detection_services(self.container)
    
    def initialize_model_module(self):
        """初始化模型模块"""
        ServiceRegistrar.register_model_services(self.container)

# 便捷函数
def setup_dependency_injection():
    """设置依赖注入（便捷函数）"""
    container = get_container()
    initializer = ModuleInitializer(container)
    initializer.initialize_all_modules()
    return container

def get_service(service_type: Type[T]) -> T:
    """获取服务（便捷函数）"""
    return resolve(service_type)

def get_optional_service(service_type: Type[T]) -> Optional[T]:
    """获取可选服务（便捷函数）"""
    try:
        return resolve(service_type)
    except ValueError:
        return None

# 使用示例
if __name__ == "__main__":
    # 设置依赖注入
    container = setup_dependency_injection()
    
    # 使用服务
    logger_service = get_service(ILogger)
    logger_service.info("依赖注入测试")
    
    config_service = get_service(IConfigService)
    config_service.set("test_key", "test_value")
    print(f"配置值: {config_service.get('test_key')}")


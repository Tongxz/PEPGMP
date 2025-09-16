"""
插件化架构系统
Plugin Architecture System

提供插件加载、管理和扩展机制，实现系统的模块化和可扩展性
"""

import importlib
import importlib.util
import logging
import os
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)

class PluginStatus(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"

class PluginType(Enum):
    """插件类型"""
    DETECTOR = "detector"
    PROCESSOR = "processor"
    EXPORTER = "exporter"
    ANALYZER = "analyzer"
    UTILITY = "utility"
    CUSTOM = "custom"

@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    entry_point: str = "main"
    config_schema: Optional[Dict[str, Any]] = None
    status: PluginStatus = PluginStatus.UNLOADED
    load_time: Optional[float] = None
    error_message: Optional[str] = None

class PluginInterface(ABC):
    """插件接口"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def execute(self, data: Any) -> Any:
        """执行插件功能"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """清理插件资源"""
        pass
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass

class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dirs: List[str] = None):
        self.plugin_dirs = plugin_dirs or ["plugins"]
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.hooks: Dict[str, List[Callable]] = defaultdict(list)
        
    def discover_plugins(self) -> List[PluginInfo]:
        """发现插件"""
        discovered_plugins = []
        
        for plugin_dir in self.plugin_dirs:
            plugin_path = Path(plugin_dir)
            if not plugin_path.exists():
                continue
            
            for plugin_file in plugin_path.rglob("*.py"):
                if plugin_file.name == "__init__.py":
                    continue
                
                try:
                    plugin_info = self._extract_plugin_info(plugin_file)
                    if plugin_info:
                        discovered_plugins.append(plugin_info)
                        self.plugin_info[plugin_info.name] = plugin_info
                except Exception as e:
                    logger.warning(f"解析插件信息失败: {plugin_file}, 错误: {e}")
        
        logger.info(f"发现 {len(discovered_plugins)} 个插件")
        return discovered_plugins
    
    def _extract_plugin_info(self, plugin_file: Path) -> Optional[PluginInfo]:
        """提取插件信息"""
        try:
            # 读取文件内容
            with open(plugin_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的元数据提取（实际项目中可以使用更复杂的方法）
            lines = content.split('\n')
            metadata = {}
            
            for line in lines:
                if line.strip().startswith('#'):
                    continue
                
                if 'PLUGIN_NAME' in line:
                    metadata['name'] = line.split('=')[1].strip().strip('"\'')
                elif 'PLUGIN_VERSION' in line:
                    metadata['version'] = line.split('=')[1].strip().strip('"\'')
                elif 'PLUGIN_DESCRIPTION' in line:
                    metadata['description'] = line.split('=')[1].strip().strip('"\'')
                elif 'PLUGIN_AUTHOR' in line:
                    metadata['author'] = line.split('=')[1].strip().strip('"\'')
                elif 'PLUGIN_TYPE' in line:
                    plugin_type_str = line.split('=')[1].strip().strip('"\'')
                    metadata['plugin_type'] = PluginType(plugin_type_str)
            
            if 'name' in metadata:
                return PluginInfo(
                    name=metadata['name'],
                    version=metadata.get('version', '1.0.0'),
                    description=metadata.get('description', ''),
                    author=metadata.get('author', ''),
                    plugin_type=metadata.get('plugin_type', PluginType.CUSTOM),
                    entry_point=plugin_file.stem
                )
            
        except Exception as e:
            logger.error(f"提取插件信息失败: {plugin_file}, 错误: {e}")
        
        return None
    
    def load_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> bool:
        """加载插件"""
        if plugin_name not in self.plugin_info:
            logger.error(f"插件不存在: {plugin_name}")
            return False
        
        plugin_info = self.plugin_info[plugin_name]
        
        if plugin_info.status == PluginStatus.LOADED:
            logger.warning(f"插件已加载: {plugin_name}")
            return True
        
        try:
            with self.lock:
                plugin_info.status = PluginStatus.LOADING
                
                # 检查依赖
                if not self._check_dependencies(plugin_info):
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "依赖检查失败"
                    return False
                
                # 加载插件模块
                plugin_module = self._load_plugin_module(plugin_name, plugin_info)
                if not plugin_module:
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "模块加载失败"
                    return False
                
                # 创建插件实例
                plugin_class = getattr(plugin_module, plugin_info.entry_point, None)
                if not plugin_class:
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "找不到插件入口点"
                    return False
                
                plugin_instance = plugin_class()
                
                # 初始化插件
                if not plugin_instance.initialize(config or {}):
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "插件初始化失败"
                    return False
                
                # 注册插件
                self.plugins[plugin_name] = plugin_instance
                self.plugin_modules[plugin_name] = plugin_module
                plugin_info.status = PluginStatus.LOADED
                plugin_info.load_time = time.time()
                
                # 触发加载钩子
                self._trigger_hooks('plugin_loaded', plugin_name, plugin_instance)
                
                logger.info(f"插件加载成功: {plugin_name}")
                return True
                
        except Exception as e:
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            logger.error(f"插件加载失败: {plugin_name}, 错误: {e}")
            return False
    
    def _load_plugin_module(self, plugin_name: str, plugin_info: PluginInfo) -> Optional[Any]:
        """加载插件模块"""
        try:
            # 查找插件文件
            plugin_file = None
            for plugin_dir in self.plugin_dirs:
                plugin_path = Path(plugin_dir) / f"{plugin_info.entry_point}.py"
                if plugin_path.exists():
                    plugin_file = plugin_path
                    break
            
            if not plugin_file:
                logger.error(f"找不到插件文件: {plugin_name}")
                return None
            
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}", 
                plugin_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            logger.error(f"加载插件模块失败: {plugin_name}, 错误: {e}")
            return None
    
    def _check_dependencies(self, plugin_info: PluginInfo) -> bool:
        """检查插件依赖"""
        for dependency in plugin_info.dependencies:
            if dependency not in self.plugins:
                logger.error(f"插件依赖未满足: {plugin_info.name} -> {dependency}")
                return False
        
        for requirement in plugin_info.requirements:
            try:
                importlib.import_module(requirement)
            except ImportError:
                logger.error(f"插件要求未满足: {plugin_info.name} -> {requirement}")
                return False
        
        return True
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name not in self.plugins:
            logger.warning(f"插件未加载: {plugin_name}")
            return True
        
        try:
            with self.lock:
                plugin_instance = self.plugins[plugin_name]
                
                # 清理插件资源
                plugin_instance.cleanup()
                
                # 触发卸载钩子
                self._trigger_hooks('plugin_unloaded', plugin_name, plugin_instance)
                
                # 移除插件
                del self.plugins[plugin_name]
                del self.plugin_modules[plugin_name]
                
                plugin_info = self.plugin_info[plugin_name]
                plugin_info.status = PluginStatus.UNLOADED
                plugin_info.load_time = None
                plugin_info.error_message = None
                
                logger.info(f"插件卸载成功: {plugin_name}")
                return True
                
        except Exception as e:
            logger.error(f"插件卸载失败: {plugin_name}, 错误: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        return self.plugins.get(plugin_name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        return list(self.plugin_info.values())
    
    def list_loaded_plugins(self) -> List[str]:
        """列出已加载的插件"""
        return list(self.plugins.keys())
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        total_plugins = len(self.plugin_info)
        loaded_plugins = len(self.plugins)
        error_plugins = len([
            info for info in self.plugin_info.values()
            if info.status == PluginStatus.ERROR
        ])
        
        plugin_types = defaultdict(int)
        for info in self.plugin_info.values():
            plugin_types[info.plugin_type.value] += 1
        
        return {
            "total_plugins": total_plugins,
            "loaded_plugins": loaded_plugins,
            "error_plugins": error_plugins,
            "plugin_types": dict(plugin_types),
            "plugin_dirs": self.plugin_dirs
        }
    
    def register_hook(self, hook_name: str, callback: Callable):
        """注册钩子函数"""
        self.hooks[hook_name].append(callback)
    
    def _trigger_hooks(self, hook_name: str, *args, **kwargs):
        """触发钩子函数"""
        for callback in self.hooks[hook_name]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"钩子函数执行失败: {hook_name}, 错误: {e}")

# 插件基类
class BasePlugin(PluginInterface):
    """插件基类"""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        self.config = config
        self.initialized = True
        return True
    
    def cleanup(self):
        """清理插件资源"""
        self.initialized = False
    
    @abstractmethod
    def execute(self, data: Any) -> Any:
        """执行插件功能"""
        pass
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass

# 具体插件示例
class DetectionPlugin(BasePlugin):
    """检测插件示例"""
    
    PLUGIN_NAME = "detection_plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "示例检测插件"
    PLUGIN_AUTHOR = "AI Assistant"
    PLUGIN_TYPE = "detector"
    
    def execute(self, data: Any) -> Any:
        """执行检测"""
        if not self.initialized:
            raise RuntimeError("插件未初始化")
        
        # 这里实现具体的检测逻辑
        logger.info(f"执行检测插件: {data}")
        return {"detected": True, "count": 1}
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.PLUGIN_NAME,
            version=self.PLUGIN_VERSION,
            description=self.PLUGIN_DESCRIPTION,
            author=self.PLUGIN_AUTHOR,
            plugin_type=PluginType(self.PLUGIN_TYPE)
        )

class ProcessingPlugin(BasePlugin):
    """处理插件示例"""
    
    PLUGIN_NAME = "processing_plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "示例处理插件"
    PLUGIN_AUTHOR = "AI Assistant"
    PLUGIN_TYPE = "processor"
    
    def execute(self, data: Any) -> Any:
        """执行处理"""
        if not self.initialized:
            raise RuntimeError("插件未初始化")
        
        # 这里实现具体的处理逻辑
        logger.info(f"执行处理插件: {data}")
        return {"processed": True, "result": "success"}
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.PLUGIN_NAME,
            version=self.PLUGIN_VERSION,
            description=self.PLUGIN_DESCRIPTION,
            author=self.PLUGIN_AUTHOR,
            plugin_type=PluginType(self.PLUGIN_TYPE)
        )

# 插件注册器
class PluginRegistrar:
    """插件注册器"""
    
    @staticmethod
    def register_builtin_plugins(manager: PluginManager):
        """注册内置插件"""
        # 注册检测插件
        detection_plugin = DetectionPlugin()
        manager.plugins[detection_plugin.PLUGIN_NAME] = detection_plugin
        manager.plugin_info[detection_plugin.PLUGIN_NAME] = detection_plugin.get_info()
        
        # 注册处理插件
        processing_plugin = ProcessingPlugin()
        manager.plugins[processing_plugin.PLUGIN_NAME] = processing_plugin
        manager.plugin_info[processing_plugin.PLUGIN_NAME] = processing_plugin.get_info()
        
        logger.info("内置插件注册完成")

# 全局插件管理器
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager

def initialize_plugin_system(plugin_dirs: List[str] = None) -> PluginManager:
    """初始化插件系统（便捷函数）"""
    manager = get_plugin_manager()
    
    if plugin_dirs:
        manager.plugin_dirs = plugin_dirs
    
    # 发现插件
    manager.discover_plugins()
    
    # 注册内置插件
    PluginRegistrar.register_builtin_plugins(manager)
    
    logger.info("插件系统初始化完成")
    return manager

def load_plugin(plugin_name: str, config: Dict[str, Any] = None) -> bool:
    """加载插件（便捷函数）"""
    manager = get_plugin_manager()
    return manager.load_plugin(plugin_name, config)

def get_plugin(plugin_name: str) -> Optional[PluginInterface]:
    """获取插件（便捷函数）"""
    manager = get_plugin_manager()
    return manager.get_plugin(plugin_name)

# 使用示例
if __name__ == "__main__":
    # 初始化插件系统
    manager = initialize_plugin_system()
    
    # 列出所有插件
    plugins = manager.list_plugins()
    print(f"发现插件: {[p.name for p in plugins]}")
    
    # 加载插件
    for plugin_info in plugins:
        if plugin_info.status == PluginStatus.UNLOADED:
            success = manager.load_plugin(plugin_info.name)
            print(f"加载插件 {plugin_info.name}: {'成功' if success else '失败'}")
    
    # 执行插件
    loaded_plugins = manager.list_loaded_plugins()
    for plugin_name in loaded_plugins:
        plugin = manager.get_plugin(plugin_name)
        if plugin:
            result = plugin.execute("test_data")
            print(f"插件 {plugin_name} 执行结果: {result}")
    
    # 获取统计信息
    stats = manager.get_plugin_stats()
    print(f"插件统计: {stats}")


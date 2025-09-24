"""
事件驱动架构系统
Event-Driven Architecture System

提供事件发布/订阅机制，实现模块间的松耦合通信
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """事件基类"""

    event_type: str
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class EventHandler:
    """事件处理器"""

    handler_id: str
    handler_func: Callable[[Event], Any]
    event_types: Set[str]
    priority: EventPriority = EventPriority.NORMAL
    async_handler: bool = False
    max_retries: int = 3
    retry_delay: float = 1.0


class EventBus:
    """事件总线"""

    def __init__(self, max_queue_size: int = 10000):
        self.max_queue_size = max_queue_size
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._event_queue: deque = deque(maxlen=max_queue_size)
        self._async_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._lock = threading.Lock()
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_registered": 0,
        }

    def register_handler(
        self,
        handler_id: str,
        handler_func: Callable[[Event], Any],
        event_types: Union[str, List[str]],
        priority: EventPriority = EventPriority.NORMAL,
        async_handler: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """注册事件处理器"""
        if isinstance(event_types, str):
            event_types = [event_types]

        handler = EventHandler(
            handler_id=handler_id,
            handler_func=handler_func,
            event_types=set(event_types),
            priority=priority,
            async_handler=async_handler,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        with self._lock:
            for event_type in event_types:
                self._handlers[event_type].append(handler)
                # 按优先级排序
                self._handlers[event_type].sort(
                    key=lambda h: h.priority.value, reverse=True
                )

            self._stats["handlers_registered"] += 1

        logger.info(f"事件处理器注册成功: {handler_id}, 事件类型: {event_types}")

    def unregister_handler(self, handler_id: str):
        """注销事件处理器"""
        with self._lock:
            for event_type, handlers in self._handlers.items():
                self._handlers[event_type] = [
                    h for h in handlers if h.handler_id != handler_id
                ]

        logger.info(f"事件处理器注销成功: {handler_id}")

    def publish(self, event: Event) -> bool:
        """发布事件"""
        if not self._running:
            logger.warning("事件总线未启动，无法发布事件")
            return False

        try:
            with self._lock:
                self._event_queue.append(event)
                self._stats["events_published"] += 1

            logger.debug(f"事件发布成功: {event.event_type}")
            return True

        except Exception as e:
            logger.error(f"事件发布失败: {e}")
            return False

    async def publish_async(self, event: Event) -> bool:
        """异步发布事件"""
        try:
            await self._async_queue.put(event)
            self._stats["events_published"] += 1
            logger.debug(f"异步事件发布成功: {event.event_type}")
            return True
        except Exception as e:
            logger.error(f"异步事件发布失败: {e}")
            return False

    def start(self):
        """启动事件总线"""
        if self._running:
            return

        self._running = True

        # 启动同步事件处理线程
        self._sync_thread = threading.Thread(target=self._process_events, daemon=True)
        self._sync_thread.start()

        # 启动异步事件处理
        asyncio.create_task(self._process_async_events())

        logger.info("事件总线已启动")

    def stop(self):
        """停止事件总线"""
        self._running = False
        logger.info("事件总线已停止")

    def _process_events(self):
        """处理同步事件"""
        while self._running:
            try:
                if self._event_queue:
                    with self._lock:
                        event = self._event_queue.popleft()

                    self._handle_event(event)
                else:
                    time.sleep(0.01)  # 避免CPU占用过高

            except Exception as e:
                logger.error(f"事件处理错误: {e}")
                time.sleep(0.1)

    async def _process_async_events(self):
        """处理异步事件"""
        while self._running:
            try:
                event = await self._async_queue.get()
                await self._handle_event_async(event)
            except Exception as e:
                logger.error(f"异步事件处理错误: {e}")
                await asyncio.sleep(0.1)

    def _handle_event(self, event: Event):
        """处理事件"""
        handlers = self._handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                if handler.async_handler:
                    # 异步处理器，创建任务
                    asyncio.create_task(self._execute_handler_async(handler, event))
                else:
                    # 同步处理器
                    self._execute_handler(handler, event)

            except Exception as e:
                logger.error(f"事件处理器执行失败: {handler.handler_id}, 错误: {e}")
                self._stats["events_failed"] += 1

    async def _handle_event_async(self, event: Event):
        """异步处理事件"""
        handlers = self._handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                await self._execute_handler_async(handler, event)
            except Exception as e:
                logger.error(f"异步事件处理器执行失败: {handler.handler_id}, 错误: {e}")
                self._stats["events_failed"] += 1

    def _execute_handler(self, handler: EventHandler, event: Event):
        """执行同步处理器"""
        for attempt in range(handler.max_retries):
            try:
                handler.handler_func(event)
                self._stats["events_processed"] += 1
                break
            except Exception as e:
                if attempt < handler.max_retries - 1:
                    logger.warning(
                        f"处理器重试 {attempt + 1}/{handler.max_retries}: {handler.handler_id}"
                    )
                    time.sleep(handler.retry_delay)
                else:
                    raise e

    async def _execute_handler_async(self, handler: EventHandler, event: Event):
        """执行异步处理器"""
        for attempt in range(handler.max_retries):
            try:
                if asyncio.iscoroutinefunction(handler.handler_func):
                    await handler.handler_func(event)
                else:
                    handler.handler_func(event)
                self._stats["events_processed"] += 1
                break
            except Exception as e:
                if attempt < handler.max_retries - 1:
                    logger.warning(
                        f"异步处理器重试 {attempt + 1}/{handler.max_retries}: {handler.handler_id}"
                    )
                    await asyncio.sleep(handler.retry_delay)
                else:
                    raise e

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "queue_size": len(self._event_queue),
            "async_queue_size": self._async_queue.qsize(),
            "handlers_count": sum(
                len(handlers) for handlers in self._handlers.values()
            ),
            "event_types_count": len(self._handlers),
        }


# 具体事件类型
class DetectionEvent(Event):
    """检测事件"""

    def __init__(self, detection_type: str, **kwargs):
        super().__init__(event_type=f"detection.{detection_type}", **kwargs)


class ModelEvent(Event):
    """模型事件"""

    def __init__(self, model_action: str, **kwargs):
        super().__init__(event_type=f"model.{model_action}", **kwargs)


class SystemEvent(Event):
    """系统事件"""

    def __init__(self, system_action: str, **kwargs):
        super().__init__(event_type=f"system.{system_action}", **kwargs)


class ErrorEvent(Event):
    """错误事件"""

    def __init__(self, error_type: str, **kwargs):
        super().__init__(
            event_type=f"error.{error_type}", priority=EventPriority.HIGH, **kwargs
        )


# 事件处理器基类
class BaseEventHandler(ABC):
    """事件处理器基类"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.handler_id = self.__class__.__name__

    @abstractmethod
    def handle(self, event: Event):
        """处理事件"""

    def register(
        self,
        event_types: Union[str, List[str]],
        priority: EventPriority = EventPriority.NORMAL,
    ):
        """注册处理器"""
        self.event_bus.register_handler(
            handler_id=self.handler_id,
            handler_func=self.handle,
            event_types=event_types,
            priority=priority,
        )


# 具体事件处理器示例
class DetectionEventHandler(BaseEventHandler):
    """检测事件处理器"""

    def handle(self, event: Event):
        """处理检测事件"""
        logger.info(f"处理检测事件: {event.event_type}, 数据: {event.data}")

        # 这里可以添加具体的检测事件处理逻辑
        if "detection.completed" in event.event_type:
            self._handle_detection_completed(event)
        elif "detection.failed" in event.event_type:
            self._handle_detection_failed(event)

    def _handle_detection_completed(self, event: Event):
        """处理检测完成事件"""
        logger.info(f"检测完成: {event.data.get('detection_count', 0)} 个目标")

    def _handle_detection_failed(self, event: Event):
        """处理检测失败事件"""
        logger.error(f"检测失败: {event.data.get('error', '未知错误')}")


class ModelEventHandler(BaseEventHandler):
    """模型事件处理器"""

    def handle(self, event: Event):
        """处理模型事件"""
        logger.info(f"处理模型事件: {event.event_type}")

        if "model.loaded" in event.event_type:
            self._handle_model_loaded(event)
        elif "model.error" in event.event_type:
            self._handle_model_error(event)

    def _handle_model_loaded(self, event: Event):
        """处理模型加载事件"""
        logger.info(f"模型加载成功: {event.data.get('model_path', '未知路径')}")

    def _handle_model_error(self, event: Event):
        """处理模型错误事件"""
        logger.error(f"模型错误: {event.data.get('error', '未知错误')}")


class SystemEventHandler(BaseEventHandler):
    """系统事件处理器"""

    def handle(self, event: Event):
        """处理系统事件"""
        logger.info(f"处理系统事件: {event.event_type}")

        if "system.startup" in event.event_type:
            self._handle_system_startup(event)
        elif "system.shutdown" in event.event_type:
            self._handle_system_shutdown(event)

    def _handle_system_startup(self, event: Event):
        """处理系统启动事件"""
        logger.info("系统启动完成")

    def _handle_system_shutdown(self, event: Event):
        """处理系统关闭事件"""
        logger.info("系统关闭完成")


# 事件总线管理器
class EventBusManager:
    """事件总线管理器"""

    def __init__(self):
        self._event_bus = EventBus()
        self._handlers: List[BaseEventHandler] = []

    def initialize(self):
        """初始化事件总线"""
        # 注册默认事件处理器
        self._register_default_handlers()

        # 启动事件总线
        self._event_bus.start()

        logger.info("事件总线管理器初始化完成")

    def shutdown(self):
        """关闭事件总线"""
        self._event_bus.stop()
        logger.info("事件总线管理器已关闭")

    def _register_default_handlers(self):
        """注册默认事件处理器"""
        # 检测事件处理器
        detection_handler = DetectionEventHandler(self._event_bus)
        detection_handler.register(
            ["detection.completed", "detection.failed", "detection.started"]
        )
        self._handlers.append(detection_handler)

        # 模型事件处理器
        model_handler = ModelEventHandler(self._event_bus)
        model_handler.register(["model.loaded", "model.error", "model.unloaded"])
        self._handlers.append(model_handler)

        # 系统事件处理器
        system_handler = SystemEventHandler(self._event_bus)
        system_handler.register(["system.startup", "system.shutdown", "system.error"])
        self._handlers.append(system_handler)

    def publish_event(self, event: Event) -> bool:
        """发布事件"""
        return self._event_bus.publish(event)

    async def publish_event_async(self, event: Event) -> bool:
        """异步发布事件"""
        return await self._event_bus.publish_async(event)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._event_bus.get_stats()


# 全局事件总线管理器
_event_manager: Optional[EventBusManager] = None


def get_event_manager() -> EventBusManager:
    """获取全局事件总线管理器"""
    global _event_manager
    if _event_manager is None:
        _event_manager = EventBusManager()
    return _event_manager


def initialize_event_system():
    """初始化事件系统（便捷函数）"""
    manager = get_event_manager()
    manager.initialize()
    return manager


def publish_event(event: Event) -> bool:
    """发布事件（便捷函数）"""
    manager = get_event_manager()
    return manager.publish_event(event)


async def publish_event_async(event: Event) -> bool:
    """异步发布事件（便捷函数）"""
    manager = get_event_manager()
    return await manager.publish_event_async(event)


# 使用示例
if __name__ == "__main__":
    # 初始化事件系统
    manager = initialize_event_system()

    # 发布事件
    detection_event = DetectionEvent(
        detection_type="completed", data={"detection_count": 5, "confidence": 0.95}
    )
    publish_event(detection_event)

    # 发布模型事件
    model_event = ModelEvent(
        model_action="loaded", data={"model_path": "/path/to/model.pt", "size": "100MB"}
    )
    publish_event(model_event)

    # 获取统计信息
    stats = manager.get_stats()
    print(f"事件统计: {stats}")

    # 关闭事件系统
    manager.shutdown()

# 渐进式重构方案 - 具体实施计划

## 📋 **重构目标**

将当前项目从**过程式架构**逐步重构为**面向对象架构**，遵循SOLID原则，提高代码质量和可维护性。

## 🎯 **重构原则**

1. **渐进式**: 每次只重构一个模块，不影响现有功能
2. **向后兼容**: 保持API接口不变
3. **测试驱动**: 每个阶段都有对应的测试
4. **业务优先**: 优先重构核心业务逻辑

## 📅 **阶段1: 提取接口抽象 (1-2周)**

### 目标
定义核心接口，为后续重构奠定基础。

### 具体步骤

#### 1.1 创建接口目录
```bash
mkdir -p src/interfaces
mkdir -p src/interfaces/detection
mkdir -p src/interfaces/tracking
mkdir -p src/interfaces/repositories
```

#### 1.2 定义检测器接口
```python
# src/interfaces/detection/detector_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np

class DetectionResult:
    def __init__(self, objects: List[Dict[str, Any]], confidence: float, processing_time: float):
        self.objects = objects
        self.confidence = confidence
        self.processing_time = processing_time

class IDetector(ABC):
    """检测器接口"""

    @abstractmethod
    async def detect(self, image: np.ndarray) -> DetectionResult:
        """检测图像中的对象"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查检测器是否可用"""
        pass
```

#### 1.3 定义跟踪器接口
```python
# src/interfaces/tracking/tracker_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np

class TrackingResult:
    def __init__(self, tracks: List[Dict[str, Any]], frame_id: int):
        self.tracks = tracks
        self.frame_id = frame_id

class ITracker(ABC):
    """跟踪器接口"""

    @abstractmethod
    async def track(self, detections: List[Dict[str, Any]], frame: np.ndarray) -> TrackingResult:
        """跟踪检测到的对象"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """重置跟踪器状态"""
        pass
```

#### 1.4 定义仓储接口
```python
# src/interfaces/repositories/detection_repository_interface.py
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class DetectionRecord:
    def __init__(self, id: str, camera_id: str, objects: List[Dict], timestamp: datetime):
        self.id = id
        self.camera_id = camera_id
        self.objects = objects
        self.timestamp = timestamp

class IDetectionRepository(ABC):
    """检测记录仓储接口"""

    @abstractmethod
    async def save(self, record: DetectionRecord) -> str:
        """保存检测记录"""
        pass

    @abstractmethod
    async def find_by_camera_id(self, camera_id: str, limit: int = 100) -> List[DetectionRecord]:
        """根据摄像头ID查找记录"""
        pass

    @abstractmethod
    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        """根据ID查找记录"""
        pass
```

### 实施检查点
- [ ] 接口定义完成
- [ ] 接口文档编写完成
- [ ] 单元测试覆盖接口定义

---

## 📅 **阶段2: 实现依赖注入 (2-3周)**

### 目标
创建服务容器，实现依赖注入，解耦模块间依赖。

### 具体步骤

#### 2.1 创建依赖注入容器
```python
# src/container/service_container.py
from typing import Dict, Any, Type, TypeVar, Callable
import logging

T = TypeVar('T')

class ServiceContainer:
    """简单的依赖注入容器"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self.logger = logging.getLogger(__name__)

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """注册单例服务"""
        self._services[interface] = implementation
        self.logger.info(f"注册单例服务: {interface.__name__} -> {implementation.__name__}")

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """注册工厂服务"""
        self._factories[interface] = factory
        self.logger.info(f"注册工厂服务: {interface.__name__}")

    def get(self, interface: Type[T]) -> T:
        """获取服务实例"""
        # 优先返回单例
        if interface in self._singletons:
            return self._singletons[interface]

        # 创建新实例
        if interface in self._services:
            implementation = self._services[interface]
            instance = implementation()
            self._singletons[interface] = instance
            return instance

        if interface in self._factories:
            instance = self._factories[interface]()
            return instance

        raise ValueError(f"未找到服务: {interface.__name__}")

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """注册实例"""
        self._singletons[interface] = instance
        self.logger.info(f"注册实例: {interface.__name__}")

# 全局容器实例
container = ServiceContainer()
```

#### 2.2 创建服务配置
```python
# src/container/service_config.py
from src.container.service_container import container
from src.interfaces.detection.detector_interface import IDetector
from src.interfaces.tracking.tracker_interface import ITracker
from src.interfaces.repositories.detection_repository_interface import IDetectionRepository

# 检测器实现
from src.detection.detector import HumanDetector
from src.detection.hairnet_detector import HairnetDetector
from src.core.tracker import MultiObjectTracker

# 仓储实现
from src.database.dao import DetectionDAO

def configure_services():
    """配置所有服务"""

    # 注册检测器
    container.register_singleton(IDetector, HumanDetector)

    # 注册跟踪器
    container.register_singleton(ITracker, MultiObjectTracker)

    # 注册仓储
    container.register_singleton(IDetectionRepository, DetectionDAO)

    print("服务配置完成")

# 在应用启动时调用
configure_services()
```

#### 2.3 重构检测服务
```python
# src/services/detection_service_refactored.py
from src.container.service_container import container
from src.interfaces.detection.detector_interface import IDetector, DetectionResult
from src.interfaces.tracking.tracker_interface import ITracker
from src.interfaces.repositories.detection_repository_interface import IDetectionRepository, DetectionRecord
import logging

logger = logging.getLogger(__name__)

class DetectionService:
    """重构后的检测服务"""

    def __init__(self):
        # 通过依赖注入获取服务
        self.detector: IDetector = container.get(IDetector)
        self.tracker: ITracker = container.get(ITracker)
        self.repository: IDetectionRepository = container.get(IDetectionRepository)

    async def process_image(self, image, camera_id: str) -> DetectionResult:
        """处理图像"""
        try:
            # 检测
            detection_result = await self.detector.detect(image)

            # 跟踪
            tracking_result = await self.tracker.track(detection_result.objects, image)

            # 保存记录
            record = DetectionRecord(
                id=f"{camera_id}_{int(time.time())}",
                camera_id=camera_id,
                objects=detection_result.objects,
                timestamp=datetime.now()
            )
            await self.repository.save(record)

            return detection_result

        except Exception as e:
            logger.error(f"检测处理失败: {e}")
            raise
```

### 实施检查点
- [ ] 依赖注入容器实现完成
- [ ] 服务配置完成
- [ ] 检测服务重构完成
- [ ] 单元测试通过

---

## 📅 **阶段3: 策略模式重构 (3-4周)**

### 目标
使用策略模式重构检测器和跟踪器，实现开闭原则。

### 具体步骤

#### 3.1 创建检测器策略
```python
# src/strategies/detection/yolo_strategy.py
from src.interfaces.detection.detector_interface import IDetector, DetectionResult
from ultralytics import YOLO
import numpy as np

class YOLOStrategy(IDetector):
    """YOLO检测策略"""

    def __init__(self, model_path: str, device: str = "auto"):
        self.model_path = model_path
        self.device = device
        self.model = self._load_model()

    def _load_model(self):
        return YOLO(self.model_path)

    async def detect(self, image: np.ndarray) -> DetectionResult:
        results = self.model(image, device=self.device)
        objects = []
        for r in results:
            for box in r.boxes:
                objects.append({
                    'class': int(box.cls),
                    'confidence': float(box.conf),
                    'bbox': box.xyxy.tolist()[0]
                })

        return DetectionResult(
            objects=objects,
            confidence=float(results[0].speed['inference']),
            processing_time=float(results[0].speed['inference'])
        )

    def get_model_info(self) -> dict:
        return {
            'type': 'YOLO',
            'path': self.model_path,
            'device': self.device
        }

    def is_available(self) -> bool:
        try:
            return self.model is not None
        except:
            return False
```

#### 3.2 创建检测器工厂
```python
# src/strategies/detection/detector_factory.py
from src.interfaces.detection.detector_interface import IDetector
from src.strategies.detection.yolo_strategy import YOLOStrategy
from src.strategies.detection.mediapipe_strategy import MediaPipeStrategy
from src.config.unified_params import get_unified_params

class DetectorFactory:
    """检测器工厂"""

    @staticmethod
    def create_detector(detector_type: str, **kwargs) -> IDetector:
        """创建检测器实例"""
        config = get_unified_params()

        if detector_type == "yolo":
            model_path = kwargs.get('model_path', config.get('yolo_model_path'))
            return YOLOStrategy(model_path, kwargs.get('device', 'auto'))

        elif detector_type == "mediapipe":
            return MediaPipeStrategy(**kwargs)

        else:
            raise ValueError(f"不支持的检测器类型: {detector_type}")

    @staticmethod
    def get_available_detectors() -> list:
        """获取可用的检测器列表"""
        available = []

        # 检查YOLO
        try:
            YOLOStrategy("dummy").is_available()
            available.append("yolo")
        except:
            pass

        # 检查MediaPipe
        try:
            MediaPipeStrategy().is_available()
            available.append("mediapipe")
        except:
            pass

        return available
```

#### 3.3 重构检测服务使用策略
```python
# src/services/detection_service_with_strategy.py
from src.strategies.detection.detector_factory import DetectorFactory
from src.interfaces.detection.detector_interface import IDetector

class DetectionServiceWithStrategy:
    """使用策略模式的检测服务"""

    def __init__(self, detector_type: str = "yolo"):
        self.detector: IDetector = DetectorFactory.create_detector(detector_type)

    async def process_image(self, image, camera_id: str):
        """处理图像"""
        if not self.detector.is_available():
            raise RuntimeError("检测器不可用")

        return await self.detector.detect(image)

    def switch_detector(self, detector_type: str):
        """切换检测器"""
        self.detector = DetectorFactory.create_detector(detector_type)
```

### 实施检查点
- [ ] 检测器策略实现完成
- [ ] 检测器工厂实现完成
- [ ] 检测服务重构完成
- [ ] 策略切换功能测试通过

---

## 📅 **阶段4: 仓储模式重构 (4-5周)**

### 目标
实现仓储模式，分离数据访问逻辑。

### 具体步骤

#### 4.1 创建领域实体
```python
# src/domain/entities/detection_record.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class DetectionRecord:
    """检测记录实体"""
    id: str
    camera_id: str
    objects: List[Dict[str, Any]]
    timestamp: datetime
    confidence: float
    processing_time: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'objects': self.objects,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'processing_time': self.processing_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionRecord':
        """从字典创建"""
        return cls(
            id=data['id'],
            camera_id=data['camera_id'],
            objects=data['objects'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            confidence=data['confidence'],
            processing_time=data['processing_time']
        )
```

#### 4.2 实现仓储实现
```python
# src/infrastructure/repositories/detection_repository_impl.py
from src.interfaces.repositories.detection_repository_interface import IDetectionRepository, DetectionRecord
from src.database.connection import get_db_session
import logging

logger = logging.getLogger(__name__)

class PostgreSQLDetectionRepository(IDetectionRepository):
    """PostgreSQL检测记录仓储实现"""

    def __init__(self):
        self.db_session = get_db_session()

    async def save(self, record: DetectionRecord) -> str:
        """保存检测记录"""
        try:
            # 这里实现具体的数据库保存逻辑
            # 使用现有的数据库连接
            query = """
                INSERT INTO detection_records
                (id, camera_id, objects, timestamp, confidence, processing_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # 执行数据库操作
            # await self.db_session.execute(query, ...)
            logger.info(f"保存检测记录: {record.id}")
            return record.id
        except Exception as e:
            logger.error(f"保存检测记录失败: {e}")
            raise

    async def find_by_camera_id(self, camera_id: str, limit: int = 100) -> List[DetectionRecord]:
        """根据摄像头ID查找记录"""
        try:
            # 实现查询逻辑
            # query = "SELECT * FROM detection_records WHERE camera_id = %s LIMIT %s"
            # results = await self.db_session.fetch_all(query, camera_id, limit)
            # return [DetectionRecord.from_dict(row) for row in results]
            return []
        except Exception as e:
            logger.error(f"查询检测记录失败: {e}")
            raise

    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        """根据ID查找记录"""
        try:
            # 实现查询逻辑
            return None
        except Exception as e:
            logger.error(f"查询检测记录失败: {e}")
            raise
```

#### 4.3 更新服务容器配置
```python
# src/container/service_config.py (更新)
from src.infrastructure.repositories.detection_repository_impl import PostgreSQLDetectionRepository

def configure_services():
    """配置所有服务"""

    # 注册检测器
    container.register_singleton(IDetector, HumanDetector)

    # 注册跟踪器
    container.register_singleton(ITracker, MultiObjectTracker)

    # 注册仓储 - 使用新的实现
    container.register_singleton(IDetectionRepository, PostgreSQLDetectionRepository)

    print("服务配置完成")
```

### 实施检查点
- [ ] 领域实体定义完成
- [ ] 仓储实现完成
- [ ] 数据库操作测试通过
- [ ] 服务容器配置更新

---

## 📅 **阶段5: 领域模型重构 (5-6周)**

### 目标
重构业务逻辑，实现领域驱动设计。

### 具体步骤

#### 5.1 创建领域服务
```python
# src/domain/services/detection_domain_service.py
from src.domain.entities.detection_record import DetectionRecord
from src.interfaces.detection.detector_interface import IDetector
from src.interfaces.tracking.tracker_interface import ITracker
from src.interfaces.repositories.detection_repository_interface import IDetectionRepository
import logging

logger = logging.getLogger(__name__)

class DetectionDomainService:
    """检测领域服务"""

    def __init__(self, detector: IDetector, tracker: ITracker, repository: IDetectionRepository):
        self.detector = detector
        self.tracker = tracker
        self.repository = repository

    async def process_detection_pipeline(self, image, camera_id: str) -> DetectionRecord:
        """处理检测管道"""
        # 1. 检测
        detection_result = await self.detector.detect(image)

        # 2. 跟踪
        tracking_result = await self.tracker.track(detection_result.objects, image)

        # 3. 创建领域实体
        record = DetectionRecord(
            id=f"{camera_id}_{int(time.time())}",
            camera_id=camera_id,
            objects=detection_result.objects,
            timestamp=datetime.now(),
            confidence=detection_result.confidence,
            processing_time=detection_result.processing_time
        )

        # 4. 业务规则验证
        self._validate_detection_record(record)

        # 5. 保存
        await self.repository.save(record)

        return record

    def _validate_detection_record(self, record: DetectionRecord) -> None:
        """验证检测记录的业务规则"""
        if record.confidence < 0.5:
            logger.warning(f"检测置信度过低: {record.confidence}")

        if len(record.objects) == 0:
            logger.info("未检测到任何对象")

        if record.processing_time > 1.0:
            logger.warning(f"处理时间过长: {record.processing_time}s")
```

#### 5.2 创建应用服务
```python
# src/application/services/detection_app_service.py
from src.domain.services.detection_domain_service import DetectionDomainService
from src.container.service_container import container
from src.interfaces.detection.detector_interface import IDetector
from src.interfaces.tracking.tracker_interface import ITracker
from src.interfaces.repositories.detection_repository_interface import IDetectionRepository

class DetectionAppService:
    """检测应用服务"""

    def __init__(self):
        # 获取依赖
        detector = container.get(IDetector)
        tracker = container.get(ITracker)
        repository = container.get(IDetectionRepository)

        # 创建领域服务
        self.domain_service = DetectionDomainService(detector, tracker, repository)

    async def process_image(self, image, camera_id: str):
        """处理图像 - 应用层入口"""
        try:
            return await self.domain_service.process_detection_pipeline(image, camera_id)
        except Exception as e:
            # 应用层异常处理
            logger.error(f"应用服务处理失败: {e}")
            raise
```

#### 5.3 更新API层
```python
# src/api/routers/detection_refactored.py
from fastapi import APIRouter, Depends
from src.application.services.detection_app_service import DetectionAppService

router = APIRouter()

def get_detection_service() -> DetectionAppService:
    """获取检测服务依赖"""
    return DetectionAppService()

@router.post("/detect")
async def detect_objects(
    image: bytes,
    camera_id: str,
    service: DetectionAppService = Depends(get_detection_service)
):
    """检测对象 - 重构后的API"""
    try:
        result = await service.process_image(image, camera_id)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 实施检查点
- [ ] 领域服务实现完成
- [ ] 应用服务实现完成
- [ ] API层更新完成
- [ ] 端到端测试通过

---

## 📊 **重构进度跟踪**

### 每周检查点
- **第1周**: 接口定义完成，单元测试编写
- **第2周**: 依赖注入容器实现，服务配置完成
- **第3周**: 检测器策略实现，工厂模式完成
- **第4周**: 仓储模式实现，数据库操作测试
- **第5周**: 领域模型重构，业务逻辑分离
- **第6周**: 端到端测试，性能验证

### 质量指标
- **代码覆盖率**: > 80%
- **圈复杂度**: < 10
- **重复代码率**: < 5%
- **API响应时间**: 无显著增加

### 回滚计划
每个阶段都有独立的回滚点，如果出现问题可以快速回退到上一个稳定版本。

## 🎯 **预期收益**

1. **可维护性**: 代码结构清晰，职责分离
2. **可扩展性**: 新功能添加无需修改现有代码
3. **可测试性**: 依赖注入使单元测试更容易
4. **代码质量**: 遵循SOLID原则，代码更规范
5. **团队协作**: 清晰的架构边界，便于团队协作

这个渐进式重构方案确保了每个阶段都是可验证的，风险可控的，并且不会影响现有功能的正常运行。

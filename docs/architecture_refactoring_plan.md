# 架构重构计划 - 符合软件工程理论标准

## 当前架构问题分析

### 1. 违反SOLID原则的问题

#### 单一职责原则 (SRP) 违反
- `src/core/` 目录混合了多种职责
- 单个文件包含多个不相关的功能

#### 依赖倒置原则 (DIP) 违反
- 高层模块直接依赖具体实现
- 缺乏抽象接口层

#### 开闭原则 (OCP) 违反
- 添加新功能需要修改现有代码
- 缺乏可扩展的插件机制

### 2. 架构层次不清晰
- 业务逻辑与基础设施代码混合
- 缺乏清晰的边界定义

## 重构方案

### 1. 重新组织目录结构

```
src/
├── domain/                    # 领域层 - 业务核心
│   ├── entities/             # 实体
│   │   ├── detection_result.py
│   │   ├── camera.py
│   │   └── region.py
│   ├── value_objects/        # 值对象
│   │   ├── coordinates.py
│   │   └── confidence.py
│   ├── services/             # 领域服务
│   │   ├── detection_service.py
│   │   └── tracking_service.py
│   └── repositories/         # 仓储接口
│       ├── detection_repository.py
│       └── camera_repository.py
├── application/              # 应用层 - 用例
│   ├── use_cases/           # 用例
│   │   ├── detect_objects.py
│   │   ├── track_objects.py
│   │   └── manage_cameras.py
│   ├── services/            # 应用服务
│   │   ├── detection_app_service.py
│   │   └── camera_app_service.py
│   └── dto/                 # 数据传输对象
│       ├── detection_dto.py
│       └── camera_dto.py
├── infrastructure/          # 基础设施层
│   ├── persistence/         # 持久化
│   │   ├── postgresql/
│   │   └── redis/
│   ├── external_services/   # 外部服务
│   │   ├── mlflow/
│   │   └── dvc/
│   ├── ai_models/          # AI模型
│   │   ├── yolo/
│   │   ├── mediapipe/
│   │   └── custom/
│   └── monitoring/         # 监控
│       ├── logging/
│       └── metrics/
├── interfaces/             # 接口层
│   ├── api/               # REST API
│   ├── websocket/         # WebSocket
│   └── cli/               # 命令行接口
└── shared/                # 共享层
    ├── config/            # 配置
    ├── utils/             # 工具
    └── exceptions/        # 异常
```

### 2. 实现依赖倒置

#### 定义抽象接口
```python
# domain/repositories/detection_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.detection_result import DetectionResult

class DetectionRepository(ABC):
    @abstractmethod
    async def save(self, detection: DetectionResult) -> None:
        pass

    @abstractmethod
    async def find_by_camera_id(self, camera_id: str) -> List[DetectionResult]:
        pass

    @abstractmethod
    async def find_by_id(self, detection_id: str) -> Optional[DetectionResult]:
        pass
```

#### 实现具体仓储
```python
# infrastructure/persistence/postgresql/detection_repository_impl.py
from domain.repositories.detection_repository import DetectionRepository
from domain.entities.detection_result import DetectionResult

class PostgreSQLDetectionRepository(DetectionRepository):
    def __init__(self, db_session):
        self.db_session = db_session

    async def save(self, detection: DetectionResult) -> None:
        # PostgreSQL实现
        pass

    async def find_by_camera_id(self, camera_id: str) -> List[DetectionResult]:
        # PostgreSQL实现
        pass
```

### 3. 实现开闭原则

#### 使用策略模式
```python
# domain/services/detection_strategy.py
from abc import ABC, abstractmethod
from domain.entities.detection_result import DetectionResult

class DetectionStrategy(ABC):
    @abstractmethod
    async def detect(self, image: np.ndarray) -> DetectionResult:
        pass

# infrastructure/ai_models/yolo/yolo_strategy.py
class YOLOStrategy(DetectionStrategy):
    async def detect(self, image: np.ndarray) -> DetectionResult:
        # YOLO实现
        pass

# infrastructure/ai_models/mediapipe/mediapipe_strategy.py
class MediaPipeStrategy(DetectionStrategy):
    async def detect(self, image: np.ndarray) -> DetectionResult:
        # MediaPipe实现
        pass
```

#### 使用工厂模式
```python
# application/factories/detection_factory.py
from domain.services.detection_strategy import DetectionStrategy
from infrastructure.ai_models.yolo.yolo_strategy import YOLOStrategy
from infrastructure.ai_models.mediapipe.mediapipe_strategy import MediaPipeStrategy

class DetectionStrategyFactory:
    @staticmethod
    def create_strategy(strategy_type: str) -> DetectionStrategy:
        strategies = {
            "yolo": YOLOStrategy,
            "mediapipe": MediaPipeStrategy,
        }

        if strategy_type not in strategies:
            raise ValueError(f"Unknown strategy: {strategy_type}")

        return strategies[strategy_type]()
```

### 4. 实现单一职责原则

#### 分离关注点
```python
# domain/entities/detection_result.py
@dataclass
class DetectionResult:
    id: str
    camera_id: str
    objects: List[DetectedObject]
    timestamp: datetime
    confidence: float

# domain/value_objects/coordinates.py
@dataclass
class Coordinates:
    x: float
    y: float
    width: float
    height: float

# domain/services/detection_service.py
class DetectionService:
    def __init__(self, strategy: DetectionStrategy, repository: DetectionRepository):
        self.strategy = strategy
        self.repository = repository

    async def detect_and_save(self, image: np.ndarray, camera_id: str) -> DetectionResult:
        # 只负责检测和保存的业务逻辑
        detection = await self.strategy.detect(image)
        detection.camera_id = camera_id
        await self.repository.save(detection)
        return detection
```

### 5. 实现接口隔离原则

#### 定义细粒度接口
```python
# domain/repositories/read_only_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional

class ReadOnlyRepository(ABC):
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def find_all(self) -> List[Any]:
        pass

# domain/repositories/write_repository.py
class WriteRepository(ABC):
    @abstractmethod
    async def save(self, entity: Any) -> None:
        pass

    @abstractmethod
    async def update(self, entity: Any) -> None:
        pass

    @abstractmethod
    async def delete(self, id: str) -> None:
        pass
```

## 实施步骤

### 阶段1: 重构核心领域层
1. 提取实体和值对象
2. 定义仓储接口
3. 实现领域服务

### 阶段2: 重构应用层
1. 实现用例
2. 创建应用服务
3. 定义DTO

### 阶段3: 重构基础设施层
1. 实现具体仓储
2. 集成外部服务
3. 实现AI模型策略

### 阶段4: 重构接口层
1. 重构API控制器
2. 实现依赖注入
3. 添加错误处理

## 预期收益

1. **可维护性提升**: 清晰的层次结构，单一职责
2. **可扩展性提升**: 开闭原则，策略模式
3. **可测试性提升**: 依赖注入，接口隔离
4. **代码质量提升**: 符合SOLID原则
5. **团队协作提升**: 清晰的架构边界

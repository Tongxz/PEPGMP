# main.py run_detection() 重构计划

## 当前实现分析

### 当前流程
```python
def run_detection(args, logger):
    # 1. 初始化检测管道
    pipeline = OptimizedDetectionPipeline(...)

    # 2. 视频循环
    while True:
        frame = cap.read()

        # 3. 执行检测
        result = pipeline.detect_comprehensive(frame)

        # 4. 每N帧保存（直接调用数据库服务）
        if frame_count % save_interval == 0:
            asyncio.run(db_service.save_detection_record(...))
```

### 问题
- ❌ 直接调用数据库服务，绕过领域层
- ❌ 未使用领域模型（DetectionRecord）
- ❌ 未使用应用服务（DetectionApplicationService）
- ❌ 未使用智能保存策略
- ❌ 保存频率硬编码

## 目标实现

### 新流程
```python
def run_detection(args, logger):
    # 1. 创建保存策略（从命令行参数）
    save_policy = SavePolicy(
        strategy=SaveStrategy[args.save_strategy.upper()],
        save_interval=args.save_interval,
        ...
    )

    # 2. 创建应用服务
    app_service = DetectionApplicationService(
        detection_pipeline=pipeline,
        detection_domain_service=domain_service,
        save_policy=save_policy
    )

    # 3. 视频循环
    while True:
        frame = cap.read()

        # 4. 使用应用服务处理（自动应用智能保存策略）
        result = asyncio.run(
            app_service.process_realtime_stream(
                camera_id=args.camera_id,
                frame=frame,
                frame_count=frame_count
            )
        )

        # 5. 根据结果进行可视化
        if result["saved_to_db"]:
            logger.info(f"✓ 已保存: {result['save_reason']}")
```

### 优势
- ✅ 使用应用服务，架构清晰
- ✅ 使用领域服务，业务逻辑完整
- ✅ 智能保存策略，节省存储
- ✅ 配置灵活，支持命令行参数
- ✅ 保存原因追踪，便于调试

## 新增命令行参数

```python
# 保存策略相关
parser.add_argument(
    "--save-strategy",
    choices=["all", "violations_only", "interval", "smart"],
    default="smart",
    help="保存策略"
)

parser.add_argument(
    "--save-interval",
    type=int,
    default=30,
    help="保存间隔（帧数）"
)

parser.add_argument(
    "--violation-threshold",
    type=float,
    default=0.5,
    help="违规严重程度阈值（0.0-1.0）"
)

parser.add_argument(
    "--normal-sample-interval",
    type=int,
    default=300,
    help="正常样本采样间隔（帧数）"
)
```

## 使用示例

```bash
# 只保存违规（生产环境）
python main.py detection \
    --source rtsp://camera1 \
    --save-strategy violations_only \
    --violation-threshold 0.7

# 智能保存（推荐）
python main.py detection \
    --source rtsp://camera2 \
    --save-strategy smart \
    --normal-sample-interval 300

# 保存所有（测试）
python main.py detection \
    --source 0 \
    --save-strategy all \
    --save-interval 30
```

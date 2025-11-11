# main.py 简化方案

## 📊 当前状态

**main.py**: 1226 行 ⚠️

**问题**：
1. `_run_detection_loop()` 函数（600+行）应该被移除，但仍然作为回退方案保留
2. `run_detection()` 函数（200+行）包含太多初始化逻辑
3. 辅助函数散落在文件各处
4. 缺少模块化组织

---

## 🎯 优化目标

将 main.py 压缩到 **300 行以内**，只保留：
- 命令行参数解析
- 模式分发
- 简单的初始化逻辑

---

## 📋 重构计划

### 阶段 1: 移除旧的检测循环（立即执行）

**目标**：完全移除 `_run_detection_loop()` 函数

**原因**：
- 新架构 `DetectionLoopService` 已经实现
- 保留旧代码会增加维护负担
- 回退机制应该足够健壮，不需要保留旧代码

**操作**：
```python
# 删除第 329-932 行的 _run_detection_loop() 函数
# 如果新架构失败，应该：
# 1. 记录详细错误日志
# 2. 提示用户检查配置
# 3. 退出程序
```

**节省**：~600 行

---

### 阶段 2: 抽取检测初始化逻辑

**创建**: `src/application/detection_initializer.py`

**职责**：
- 初始化检测管线
- 初始化应用服务
- 配置参数加载

```python
class DetectionInitializer:
    """检测服务初始化器"""

    @staticmethod
    def initialize_pipeline(args, logger) -> OptimizedDetectionPipeline:
        """初始化检测管线"""
        # 移动 run_detection() 中的管线初始化代码
        ...

    @staticmethod
    def initialize_services(
        args, logger, pipeline
    ) -> tuple[DetectionApplicationService, VideoStreamApplicationService]:
        """初始化应用服务"""
        # 移动服务初始化代码
        ...
```

**节省**：~150 行

---

### 阶段 3: 抽取配置加载逻辑

**创建**: `src/config/config_loader.py`

```python
class ConfigLoader:
    """统一配置加载器"""

    @staticmethod
    def load_and_merge(args, logger):
        """加载并合并配置"""
        # 移动 load_unified_params() 等函数
        ...

    @staticmethod
    def apply_optimizations(args, logger):
        """应用自适应优化"""
        # 移动 apply_adaptive_optimizations()
        # 移动 apply_hardware_probe_fallback()
        ...
```

**节省**：~100 行

---

### 阶段 4: 简化 main.py

**最终的 main.py 结构**（预计 ~250 行）：

```python
#!/usr/bin/env python3
"""人体行为检测系统主入口"""

import argparse
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.logger import setup_project_logger


def create_argument_parser():
    """创建命令行参数解析器（~150行）"""
    parser = argparse.ArgumentParser(...)
    # ... 参数定义 ...
    return parser


def run_detection(args, logger):
    """运行检测模式（简化为~50行）"""
    from src.application.detection_initializer import DetectionInitializer
    from src.application.detection_loop_service import DetectionLoopService
    from src.config.config_loader import ConfigLoader

    # 1. 加载配置
    config = ConfigLoader.load_and_merge(args, logger)
    if not config:
        return

    # 2. 应用优化
    ConfigLoader.apply_optimizations(args, logger)

    # 3. 初始化管线
    pipeline = DetectionInitializer.initialize_pipeline(args, logger)

    # 4. 初始化服务
    app_service, stream_service = DetectionInitializer.initialize_services(
        args, logger, pipeline
    )

    # 5. 创建并运行检测循环
    loop_service = DetectionLoopService(
        config=DetectionInitializer.create_loop_config(args),
        detection_pipeline=pipeline,
        detection_app_service=app_service,
        video_stream_service=stream_service,
    )

    logger.info("🚀 启动检测循环")
    import asyncio
    asyncio.run(loop_service.run())


def run_api_server(args, logger):
    """运行API服务器（~20行）"""
    import uvicorn
    uvicorn.run(
        "src.api.app:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        reload=args.debug,
    )


def run_supervisor(args, logger):
    """运行Supervisor模式（~10行）"""
    from src.services.process_manager import get_process_manager
    pm = get_process_manager()
    pm.start_all()
    # 保持运行
    ...


def run_training(args, logger):
    """运行训练模式（~5行）"""
    logger.info("训练模式暂未实现")


def run_demo(args, logger):
    """运行演示模式（~5行）"""
    logger.info("演示模式暂未实现")


def main():
    """主函数（~20行）"""
    parser = create_argument_parser()
    args = parser.parse_args()
    logger = setup_project_logger()

    # 设置日志级别
    if args.debug:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel(args.log_level)

    logger.info("=" * 50)
    logger.info("人体行为检测系统启动")
    logger.info(f"运行模式: {args.mode}")
    logger.info("=" * 50)

    # 模式分发
    mode_handlers = {
        "detection": run_detection,
        "api": run_api_server,
        "training": run_training,
        "demo": run_demo,
        "supervisor": run_supervisor,
    }

    handler = mode_handlers.get(args.mode)
    if not handler:
        logger.error(f"未知的运行模式: {args.mode}")
        sys.exit(1)

    try:
        handler(args, logger)
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("程序结束")


if __name__ == "__main__":
    main()
```

---

## 📊 优化效果对比

| 指标 | 重构前 | 重构后 | 改进 |
|-----|--------|--------|------|
| **main.py 总行数** | 1226 | ~250 | ⬇️ -976 行 (80%) |
| **最长函数** | 604 行 | ~50 行 | ⬇️ -554 行 (92%) |
| **可读性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | 大幅提升 |
| **可维护性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | 大幅提升 |

---

## 📂 新的文件结构

```
src/
├── application/
│   ├── detection_loop_service.py          # 检测循环服务（已创建）
│   ├── detection_application_service.py   # 检测应用服务（已存在）
│   ├── video_stream_application_service.py # 视频流服务（已创建）
│   └── detection_initializer.py           # 检测初始化器（新建）✨
├── config/
│   ├── config_loader.py                   # 配置加载器（新建）✨
│   ├── unified_params.py                  # 统一参数（已存在）
│   └── model_config.py                    # 模型配置（已存在）
└── ...

main.py                                     # 主入口（简化）✨
```

---

## 🚀 实施步骤

### 立即执行（高优先级）

1. **创建 `detection_initializer.py`**
   - 抽取检测管线初始化逻辑
   - 抽取应用服务初始化逻辑

2. **创建 `config_loader.py`**
   - 抽取配置加载函数
   - 抽取自适应优化函数

3. **简化 `main.py`**
   - 移除 `_run_detection_loop()` 函数
   - 简化 `run_detection()` 函数
   - 使用新的初始化器和配置加载器

4. **测试**
   - 确保所有模式仍然正常工作
   - 特别测试检测模式

### 中期（可选）

5. **进一步模块化**
   - 将命令行参数解析抽取为独立模块
   - 创建更清晰的模式处理器

---

## ✅ 验证标准

重构成功的标准：
- [ ] main.py 少于 300 行
- [ ] 没有超过 50 行的函数
- [ ] 所有功能正常工作
- [ ] 代码更易读、更易维护
- [ ] 测试全部通过

---

## 📝 注意事项

1. **保持向后兼容**：确保所有现有功能仍然工作
2. **充分测试**：每个重构步骤后都要测试
3. **清晰文档**：为新模块添加文档注释
4. **逐步迁移**：不要一次性改动太多

---

## 🎯 最终目标

```python
# main.py - 简洁、清晰、易维护

def main():
    args = parse_arguments()
    logger = setup_logging(args)

    # 简单的模式分发
    run_mode(args, logger)
```

**原则**：main.py 应该只是一个"入口"，不应该包含复杂的业务逻辑。

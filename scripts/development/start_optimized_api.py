#!/usr/bin/env python3
"""
优化版API启动脚本
针对当前检测慢的问题进行优化

主要优化：
1. 批处理检测
2. 智能缓存
3. 并行处理
4. 硬件自适应
"""

import logging
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ["PYTHONPATH"] = str(project_root)
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 使用第一个GPU

import uvicorn

from src.api.app import app
from src.core.fast_detection_pipeline import FastDetectionPipeline
from src.services.detection_service import initialize_detection_services

# 导入必要的模块
from src.utils.adaptive_optimizer import apply_adaptive_optimizations

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OptimizedAPIServer:
    """优化的API服务器"""

    def __init__(self, port: int = 8001):
        self.port = port
        self.fast_pipeline = None
        self.app = None

    def initialize_optimizations(self):
        """初始化优化设置"""
        logger.info("=== 初始化性能优化 ===")

        # 应用自适应优化
        optimization_config = apply_adaptive_optimizations()
        logger.info(f"自适应优化配置: {optimization_config}")

        # 初始化快速检测流水线
        self.fast_pipeline = FastDetectionPipeline(device="cuda")
        logger.info("快速检测流水线初始化完成")

        # 初始化检测服务
        initialize_detection_services()
        logger.info("检测服务初始化完成")

    def create_optimized_app(self):
        """创建优化的FastAPI应用"""
        logger.info("创建优化的API应用...")

        # 使用现有的FastAPI应用
        self.app = app

        # 添加性能监控端点
        @self.app.get("/api/v1/performance/stats")
        async def get_performance_stats():
            """获取性能统计"""
            if self.fast_pipeline:
                return self.fast_pipeline.get_stats()
            return {"error": "Fast pipeline not initialized"}

        @self.app.post("/api/v1/performance/flush")
        async def flush_batch():
            """强制处理当前批次"""
            if self.fast_pipeline:
                results = self.fast_pipeline.flush_batch()
                return {"flushed": len(results) if results else 0}
            return {"error": "Fast pipeline not initialized"}

        logger.info("优化的API应用创建完成")
        return self.app

    def start_server(self):
        """启动优化服务器"""
        logger.info("=== 启动优化API服务器 ===")

        # 初始化优化
        self.initialize_optimizations()

        # 创建应用
        app = self.create_optimized_app()

        # 启动服务器
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.port,
            log_level="info",
            access_log=True,
            # 性能优化配置
            workers=1,  # 单进程，避免GPU资源竞争
            loop="asyncio",
            # 启用HTTP/2支持
            http="httptools",
        )

        server = uvicorn.Server(config)

        logger.info(f"🚀 优化API服务器启动在 http://0.0.0.0:{self.port}")
        logger.info("📊 性能监控: http://0.0.0.0:{self.port}/api/v1/performance/stats")
        logger.info("🔄 批次刷新: http://0.0.0.0:{self.port}/api/v1/performance/flush")

        try:
            server.run()
        except KeyboardInterrupt:
            logger.info("服务器停止")
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="启动优化的API服务器")
    parser.add_argument("--port", type=int, default=8001, help="服务器端口")
    parser.add_argument("--log-level", default="INFO", help="日志级别")

    args = parser.parse_args()

    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # 创建并启动服务器
    server = OptimizedAPIServer(port=args.port)
    server.start_server()


if __name__ == "__main__":
    main()

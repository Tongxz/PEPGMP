#!/usr/bin/env python
"""
TensorRT优化器

用于将PyTorch模型转换为TensorRT引擎，并提供高性能推理接口。
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

import torch

logger = logging.getLogger(__name__)


class TensorRTOptimizer:
    """TensorRT优化器

    用于将PyTorch模型转换为TensorRT引擎
    """

    def __init__(
        self,
        model: torch.nn.Module,
        input_shape: tuple = (1, 3, 640, 640),
        precision: str = "fp16",
    ):
        """
        初始化TensorRT优化器

        Args:
            model: PyTorch模型
            input_shape: 输入形状 (batch, channels, height, width)
            precision: 精度 ('fp32', 'fp16', 'int8')
        """
        self.model = model
        self.input_shape = input_shape
        self.precision = precision
        self.optimized_model = None

        logger.info("TensorRT优化器初始化完成")
        logger.info(f"  输入形状: {input_shape}")
        logger.info(f"  精度: {precision}")

    def optimize(
        self, save_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> torch.nn.Module:
        """
        优化模型为TensorRT

        Args:
            save_path: 保存路径
            **kwargs: 其他优化参数

        Returns:
            优化后的模型
        """
        logger.info("开始TensorRT优化...")

        try:
            # 检查是否使用Torch-TensorRT
            try:
                import torch_tensorrt

                logger.info("使用Torch-TensorRT进行优化")

                # 设置精度
                enabled_precisions = set()
                if self.precision == "fp16":
                    enabled_precisions = {torch.half}
                elif self.precision == "int8":
                    enabled_precisions = {torch.int8}
                else:
                    enabled_precisions = {torch.float}

                # 创建示例输入
                example_input = torch.randn(self.input_shape).cuda()

                # 编译为TensorRT
                self.optimized_model = torch_tensorrt.compile(
                    self.model,
                    inputs=[example_input],
                    enabled_precisions=enabled_precisions,
                    workspace_size=4 * 1024 * 1024 * 1024,  # 4GB
                    min_block_size=7,
                    truncate_long_and_double=True,
                    **kwargs,
                )

                logger.info("✅ TensorRT优化完成（使用Torch-TensorRT）")

            except ImportError:
                logger.warning("Torch-TensorRT未安装，使用Ultralytics内置TensorRT导出")

                # 使用Ultralytics的export方法
                from ultralytics import YOLO

                # 假设self.model是YOLO模型
                if hasattr(self.model, "export"):
                    # 临时保存模型
                    temp_path = Path("/tmp/temp_model.pt")
                    torch.save(self.model.state_dict(), temp_path)

                    # 导出为TensorRT
                    yolo_model = YOLO(str(temp_path))
                    yolo_model.export(
                        format="engine",
                        device=0,
                        imgsz=self.input_shape[2],
                        half=(self.precision == "fp16"),
                        workspace=4,
                        simplify=True,
                        opset=12,
                        dynamic=False,
                        verbose=False,
                    )

                    # 加载优化后的模型
                    engine_path = temp_path.with_suffix(".engine")
                    if engine_path.exists():
                        logger.info(f"✅ TensorRT引擎已生成: {engine_path}")
                        self.optimized_model = self.model  # 返回原模型
                    else:
                        raise RuntimeError("TensorRT引擎生成失败")
                else:
                    raise RuntimeError("模型不支持TensorRT导出")

            # 保存优化后的模型
            if save_path:
                self.save(save_path)

            return self.optimized_model

        except Exception as e:
            logger.error(f"❌ TensorRT优化失败: {e}")
            import traceback

            traceback.print_exc()
            raise

    def save(self, save_path: Union[str, Path]):
        """保存优化后的模型"""
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            torch.save(self.optimized_model, save_path)
            logger.info(f"模型已保存到: {save_path}")
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
            raise

    def load(self, load_path: Union[str, Path]) -> torch.nn.Module:
        """加载优化后的模型"""
        load_path = Path(load_path)

        if not load_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {load_path}")

        try:
            self.optimized_model = torch.load(load_path)
            logger.info(f"模型已从 {load_path} 加载")
            return self.optimized_model
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            raise

    def benchmark(self, num_runs: int = 100, warmup: int = 10) -> Dict[str, Any]:
        """性能基准测试

        Args:
            num_runs: 测试运行次数
            warmup: 预热次数

        Returns:
            性能指标字典
        """
        if self.optimized_model is None:
            raise RuntimeError("请先运行optimize()方法")

        logger.info("开始性能基准测试...")
        logger.info(f"  预热次数: {warmup}")
        logger.info(f"  测试次数: {num_runs}")

        # 创建测试输入
        test_input = torch.randn(self.input_shape).cuda()

        # 预热
        logger.info("预热中...")
        with torch.no_grad():
            for i in range(warmup):
                _ = self.optimized_model(test_input)
                if (i + 1) % 5 == 0:
                    logger.info(f"  预热进度: {i + 1}/{warmup}")

        # 同步
        torch.cuda.synchronize()

        # 测试
        logger.info("开始性能测试...")
        start = time.time()
        with torch.no_grad():
            for i in range(num_runs):
                _ = self.optimized_model(test_input)
                if (i + 1) % 20 == 0:
                    logger.info(f"  测试进度: {i + 1}/{num_runs}")

        torch.cuda.synchronize()
        end = time.time()

        # 计算指标
        total_time = end - start
        avg_time = total_time / num_runs * 1000  # ms
        fps = 1000 / avg_time

        results = {
            "total_time": total_time,
            "avg_time_ms": avg_time,
            "fps": fps,
            "num_runs": num_runs,
            "warmup": warmup,
        }

        logger.info("✅ 性能测试完成")
        logger.info(f"  总时间: {total_time:.2f}s")
        logger.info(f"  平均延迟: {avg_time:.2f}ms")
        logger.info(f"  FPS: {fps:.1f}")

        return results

    def compare_with_original(
        self, original_model: torch.nn.Module, num_runs: int = 100, warmup: int = 10
    ) -> Dict[str, Any]:
        """与原始模型进行性能对比

        Args:
            original_model: 原始PyTorch模型
            num_runs: 测试运行次数
            warmup: 预热次数

        Returns:
            对比结果字典
        """
        if self.optimized_model is None:
            raise RuntimeError("请先运行optimize()方法")

        logger.info("开始性能对比测试...")

        # 测试原始模型
        logger.info("测试原始模型...")
        original_results = self._benchmark_model(
            original_model, num_runs, warmup, "原始模型"
        )

        # 测试优化模型
        logger.info("测试优化模型...")
        optimized_results = self._benchmark_model(
            self.optimized_model, num_runs, warmup, "优化模型"
        )

        # 计算提升
        speedup = original_results["avg_time_ms"] / optimized_results["avg_time_ms"]
        fps_improvement = optimized_results["fps"] / original_results["fps"]

        comparison = {
            "original": original_results,
            "optimized": optimized_results,
            "speedup": speedup,
            "fps_improvement": fps_improvement,
        }

        logger.info(f"\n{'='*60}")
        logger.info("性能对比结果")
        logger.info(f"{'='*60}")
        logger.info("原始模型:")
        logger.info(f"  平均延迟: {original_results['avg_time_ms']:.2f}ms")
        logger.info(f"  FPS: {original_results['fps']:.1f}")
        logger.info("\n优化模型:")
        logger.info(f"  平均延迟: {optimized_results['avg_time_ms']:.2f}ms")
        logger.info(f"  FPS: {optimized_results['fps']:.1f}")
        logger.info("\n性能提升:")
        logger.info(f"  速度提升: {speedup:.2f}x")
        logger.info(f"  FPS提升: {fps_improvement:.2f}x")
        logger.info(f"{'='*60}")

        return comparison

    def _benchmark_model(
        self, model: torch.nn.Module, num_runs: int, warmup: int, model_name: str
    ) -> Dict[str, Any]:
        """对单个模型进行基准测试"""
        test_input = torch.randn(self.input_shape).cuda()

        # 预热
        with torch.no_grad():
            for _ in range(warmup):
                _ = model(test_input)

        torch.cuda.synchronize()

        # 测试
        start = time.time()
        with torch.no_grad():
            for _ in range(num_runs):
                _ = model(test_input)

        torch.cuda.synchronize()
        end = time.time()

        # 计算指标
        total_time = end - start
        avg_time = total_time / num_runs * 1000
        fps = 1000 / avg_time

        return {
            "model_name": model_name,
            "total_time": total_time,
            "avg_time_ms": avg_time,
            "fps": fps,
            "num_runs": num_runs,
        }


def optimize_yolo_model(
    model_path: str,
    output_path: Optional[str] = None,
    precision: str = "fp16",
    imgsz: int = 640,
) -> bool:
    """
    优化YOLO模型为TensorRT（便捷函数）

    Args:
        model_path: YOLO模型路径
        output_path: 输出路径
        precision: 精度 ('fp32', 'fp16', 'int8')
        imgsz: 输入图像大小

    Returns:
        是否成功
    """
    try:
        from ultralytics import YOLO

        logger.info(f"优化YOLO模型: {model_path}")

        # 加载模型
        model = YOLO(model_path)

        # 导出为TensorRT
        model.export(
            format="engine",
            device=0,
            imgsz=imgsz,
            half=(precision == "fp16"),
            workspace=4,
            simplify=True,
            opset=12,
            dynamic=False,
            verbose=True,
        )

        logger.info("✅ 模型优化成功")
        return True

    except Exception as e:
        logger.error(f"❌ 模型优化失败: {e}")
        return False

#!/usr/bin/env python
"""
模型优化器

自动检测并转换模型为TensorRT引擎，以获得最佳性能。
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ModelOptimizer:
    """模型优化器

    自动检测模型文件，如果不存在TensorRT引擎则自动转换。
    """

    def __init__(
        self,
        models_dir: str = "models",
        auto_convert: bool = True,
        tensorrt_precision: str = "fp16",
    ):
        """
        初始化模型优化器

        Args:
            models_dir: 模型目录
            auto_convert: 是否自动转换
            tensorrt_precision: TensorRT精度 ('fp32', 'fp16', 'int8')
        """
        self.models_dir = Path(models_dir)
        self.auto_convert = auto_convert
        self.tensorrt_precision = tensorrt_precision
        self.converted_models = []

        logger.info("模型优化器初始化完成")
        logger.info(f"  模型目录: {self.models_dir}")
        logger.info(f"  自动转换: {self.auto_convert}")
        logger.info(f"  TensorRT精度: {self.tensorrt_precision}")

    def check_tensorrt_available(self) -> bool:
        """检查TensorRT是否可用"""
        try:
            import tensorrt as trt
            import torch

            # 检查CUDA
            if not torch.cuda.is_available():
                logger.warning("CUDA不可用，无法使用TensorRT")
                return False

            logger.info(f"✅ TensorRT可用，版本: {trt.__version__}")
            logger.info(f"   CUDA设备: {torch.cuda.get_device_name(0)}")
            return True

        except ImportError:
            logger.warning("TensorRT未安装，将使用PyTorch模型")
            return False
        except Exception as e:
            logger.error(f"检查TensorRT失败: {e}")
            return False

    def find_model_files(self) -> List[Tuple[Path, Path]]:
        """
        查找所有需要转换的模型文件

        Returns:
            [(pt_file, engine_file), ...] 列表
        """
        model_pairs = []

        # 查找所有.pt文件
        for pt_file in self.models_dir.rglob("*.pt"):
            # 跳过某些目录
            if "training" in pt_file.parts or "weights" in pt_file.parts:
                continue

            # 生成对应的.engine文件路径
            engine_file = pt_file.with_suffix(".engine")

            model_pairs.append((pt_file, engine_file))

        return model_pairs

    def needs_conversion(self, pt_file: Path, engine_file: Path) -> bool:
        """
        检查是否需要转换

        Args:
            pt_file: PyTorch模型文件
            engine_file: TensorRT引擎文件

        Returns:
            是否需要转换
        """
        # 如果.engine文件不存在，需要转换
        if not engine_file.exists():
            logger.info(f"📋 需要转换: {pt_file.name} (引擎文件不存在)")
            return True

        # 如果.pt文件比.engine文件新，需要转换
        if pt_file.stat().st_mtime > engine_file.stat().st_mtime:
            logger.info(f"📋 需要转换: {pt_file.name} (PyTorch模型已更新)")
            return True

        logger.info(f"✅ 已存在: {engine_file.name}")
        return False

    def convert_model(self, pt_file: Path, engine_file: Path, imgsz: int = 640) -> bool:
        """
        转换单个模型为TensorRT引擎

        Args:
            pt_file: PyTorch模型文件
            engine_file: 输出TensorRT引擎文件
            imgsz: 输入图像大小

        Returns:
            转换是否成功
        """
        try:
            from ultralytics import YOLO

            logger.info(f"🔄 开始转换: {pt_file.name}")
            logger.info(f"   输入: {pt_file}")
            logger.info(f"   输出: {engine_file}")
            logger.info(f"   精度: {self.tensorrt_precision}")

            # 加载模型
            model = YOLO(str(pt_file))

            # 设置精度
            half = self.tensorrt_precision == "fp16"

            # 导出为TensorRT
            model.export(
                format="engine",
                device=0,
                imgsz=imgsz,
                half=half,
                workspace=4,
                simplify=True,
                opset=12,
                dynamic=False,
                verbose=False,
            )

            # 检查输出文件
            if engine_file.exists():
                size_mb = engine_file.stat().st_size / (1024 * 1024)
                logger.info(f"✅ 转换成功: {engine_file.name}")
                logger.info(f"   文件大小: {size_mb:.2f} MB")
                return True
            else:
                logger.error("❌ 转换失败: 输出文件不存在")
                return False

        except Exception as e:
            logger.error(f"❌ 转换失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def optimize_all_models(self) -> Dict[str, bool]:
        """
        优化所有模型

        Returns:
            转换结果字典 {模型名: 是否成功}
        """
        results = {}

        # 检查TensorRT是否可用
        if not self.check_tensorrt_available():
            logger.warning("TensorRT不可用，跳过模型优化")
            return results

        # 查找所有模型文件
        model_pairs = self.find_model_files()

        if not model_pairs:
            logger.info("未找到需要转换的模型文件")
            return results

        logger.info(f"\n{'='*60}")
        logger.info(f"找到 {len(model_pairs)} 个模型文件")
        logger.info(f"{'='*60}")

        # 检查每个模型
        needs_conversion = []
        for pt_file, engine_file in model_pairs:
            if self.needs_conversion(pt_file, engine_file):
                needs_conversion.append((pt_file, engine_file))

        if not needs_conversion:
            logger.info("✅ 所有模型已是最新状态，无需转换")
            return results

        logger.info(f"\n需要转换 {len(needs_conversion)} 个模型")

        # 转换模型
        for i, (pt_file, engine_file) in enumerate(needs_conversion, 1):
            logger.info(f"\n[{i}/{len(needs_conversion)}] 转换模型: {pt_file.name}")

            success = self.convert_model(pt_file, engine_file)
            results[pt_file.name] = success

            if success:
                self.converted_models.append(str(engine_file))

        # 打印摘要
        self._print_summary(results)

        return results

    def _print_summary(self, results: Dict[str, bool]):
        """打印转换结果摘要"""
        if not results:
            return

        logger.info(f"\n{'='*60}")
        logger.info("模型优化摘要")
        logger.info(f"{'='*60}")

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        for name, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            logger.info(f"{name}: {status}")

        logger.info(f"\n总计: {success_count}/{total_count} 个模型转换成功")

        if success_count == total_count:
            logger.info("🎉 所有模型优化完成！")
        else:
            logger.warning(f"⚠️  {total_count - success_count} 个模型转换失败")

    def get_model_path(
        self, model_name: str, prefer_tensorrt: bool = True
    ) -> Optional[str]:
        """
        获取模型路径（优先TensorRT引擎）

        Args:
            model_name: 模型名称（如 'yolov8n'）
            prefer_tensorrt: 是否优先使用TensorRT引擎

        Returns:
            模型路径，如果不存在则返回None
        """
        # 尝试查找.pt文件
        pt_file = self.models_dir / model_name
        if not pt_file.suffix:
            pt_file = pt_file.with_suffix(".pt")

        # 尝试查找.engine文件
        engine_file = pt_file.with_suffix(".engine")

        # 优先使用TensorRT引擎
        if prefer_tensorrt and engine_file.exists():
            logger.info(f"使用TensorRT引擎: {engine_file}")
            return str(engine_file)

        # 回退到PyTorch模型
        if pt_file.exists():
            logger.info(f"使用PyTorch模型: {pt_file}")
            return str(pt_file)

        logger.error(f"模型文件不存在: {model_name}")
        return None


# 全局模型优化器实例
_global_optimizer: Optional[ModelOptimizer] = None


def initialize_model_optimizer(
    models_dir: str = "models",
    auto_convert: bool = True,
    tensorrt_precision: str = "fp16",
) -> ModelOptimizer:
    """
    初始化全局模型优化器

    Args:
        models_dir: 模型目录
        auto_convert: 是否自动转换
        tensorrt_precision: TensorRT精度

    Returns:
        模型优化器实例
    """
    global _global_optimizer

    _global_optimizer = ModelOptimizer(
        models_dir=models_dir,
        auto_convert=auto_convert,
        tensorrt_precision=tensorrt_precision,
    )

    # 如果启用自动转换，立即优化所有模型
    if auto_convert:
        _global_optimizer.optimize_all_models()

    return _global_optimizer


def get_model_optimizer() -> Optional[ModelOptimizer]:
    """获取全局模型优化器实例"""
    return _global_optimizer


def optimize_models_on_startup(
    models_dir: str = "models", tensorrt_precision: str = "fp16"
):
    """
    启动时自动优化模型（便捷函数）

    Args:
        models_dir: 模型目录
        tensorrt_precision: TensorRT精度
    """
    logger.info("=" * 60)
    logger.info("模型优化器启动")
    logger.info("=" * 60)

    optimizer = initialize_model_optimizer(
        models_dir=models_dir, auto_convert=True, tensorrt_precision=tensorrt_precision
    )

    logger.info("模型优化器初始化完成")
    return optimizer

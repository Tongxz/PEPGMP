#!/usr/bin/env python
"""
CoreML模型转换脚本 - Mac优化方案

将YOLO模型转换为CoreML格式，以获得在Mac上的最佳性能。
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_coremltools_installation() -> bool:
    """检查coremltools是否已安装"""
    try:
        import coremltools as ct

        logger.info(f"✅ coremltools已安装，版本: {ct.__version__}")
        return True
    except ImportError:
        logger.error("❌ coremltools未安装")
        logger.info("请运行: pip install coremltools")
        return False


def check_mps_available() -> bool:
    """检查MPS是否可用"""
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("✅ MPS (Metal Performance Shaders) 可用")
            return True
        else:
            logger.warning("⚠️  MPS不可用，将在CPU上运行")
            return False
    except Exception as e:
        logger.error(f"❌ 检查MPS失败: {e}")
        return False


def convert_model_to_coreml(
    model_path: str, output_path: str = None, imgsz: int = 640
) -> bool:
    """
    将YOLO模型转换为CoreML格式

    Args:
        model_path: PyTorch模型路径
        output_path: 输出路径（可选）
        imgsz: 输入图像大小

    Returns:
        转换是否成功
    """
    try:
        from ultralytics import YOLO

        # 检查模型文件是否存在
        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"❌ 模型文件不存在: {model_path}")
            return False

        logger.info(f"开始转换模型: {model_path}")
        logger.info(f"输出路径: {output_path}")
        logger.info(f"图像大小: {imgsz}")

        # 加载模型
        model = YOLO(str(model_path))

        # 导出为CoreML
        model.export(
            format="coreml",
            imgsz=imgsz,
            nms=True,  # 包含NMS
            simplify=True,  # 简化模型
            verbose=True,
        )

        # 检查输出文件
        if output_path:
            output_path = Path(output_path)
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info("✅ 模型转换成功！")
                logger.info(f"   输出文件: {output_path}")
                logger.info(f"   文件大小: {size_mb:.2f} MB")
                return True
        else:
            # 默认输出路径
            default_output = model_path.with_suffix(".mlpackage")
            if default_output.exists():
                size_mb = default_output.stat().st_size / (1024 * 1024)
                logger.info("✅ 模型转换成功！")
                logger.info(f"   输出文件: {default_output}")
                logger.info(f"   文件大小: {size_mb:.2f} MB")
                return True

        logger.error("❌ 输出文件不存在")
        return False

    except Exception as e:
        logger.error(f"❌ 模型转换失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def convert_all_models(models: list, imgsz: int = 640) -> dict:
    """
    批量转换所有模型

    Args:
        models: 模型配置列表
        imgsz: 输入图像大小

    Returns:
        转换结果字典
    """
    results = {}

    logger.info(f"开始批量转换 {len(models)} 个模型...")
    logger.info(f"配置: 图像大小={imgsz}")

    for i, model_info in enumerate(models, 1):
        name = model_info["name"]
        path = model_info["path"]
        output = model_info.get("output")

        logger.info(f"\n{'='*60}")
        logger.info(f"[{i}/{len(models)}] 转换模型: {name}")
        logger.info(f"{'='*60}")

        success = convert_model_to_coreml(
            model_path=path, output_path=output, imgsz=imgsz
        )

        results[name] = success

        if success:
            logger.info(f"✅ {name} 转换成功")
        else:
            logger.error(f"❌ {name} 转换失败")

    return results


def print_summary(results: dict):
    """打印转换结果摘要"""
    logger.info(f"\n{'='*60}")
    logger.info("转换结果摘要")
    logger.info(f"{'='*60}")

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        logger.info(f"{name}: {status}")

    logger.info(f"\n总计: {success_count}/{total_count} 个模型转换成功")

    if success_count == total_count:
        logger.info("🎉 所有模型转换成功！")
    else:
        logger.warning(f"⚠️  {total_count - success_count} 个模型转换失败")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("CoreML模型转换工具 - Mac优化方案")
    logger.info("=" * 60)

    # 检查环境
    logger.info("\n1. 检查环境...")
    if not check_coremltools_installation():
        logger.error("请先安装coremltools")
        return 1

    check_mps_available()

    # 定义要转换的模型
    logger.info("\n2. 准备转换模型列表...")
    models = [
        {
            "name": "人体检测 (YOLOv8n)",
            "path": "models/yolo/yolov8n.pt",
            "output": "models/yolo/yolov8n.mlpackage",
        },
        {
            "name": "发网检测",
            "path": "models/hairnet_detection/hairnet_detection.pt",
            "output": "models/hairnet_detection/hairnet_detection.mlpackage",
        },
        {
            "name": "姿态检测 (YOLOv8n-pose)",
            "path": "models/yolo/yolov8n-pose.pt",
            "output": "models/yolo/yolov8n-pose.mlpackage",
        },
    ]

    # 打印模型列表
    logger.info("将转换以下模型:")
    for i, model in enumerate(models, 1):
        logger.info(f"  {i}. {model['name']}")
        logger.info(f"     输入: {model['path']}")
        logger.info(f"     输出: {model['output']}")

    # 转换模型
    logger.info("\n3. 开始转换模型...")
    results = convert_all_models(models=models, imgsz=640)

    # 打印摘要
    print_summary(results)

    # 返回退出码
    success_count = sum(1 for success in results.values() if success)
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

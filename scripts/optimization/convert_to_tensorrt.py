#!/usr/bin/env python
"""
TensorRT模型转换脚本

将项目中的YOLO模型转换为TensorRT引擎，以获得最佳性能。
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_tensorrt_installation() -> bool:
    """检查TensorRT是否已安装"""
    try:
        import tensorrt as trt

        logger.info(f"✅ TensorRT已安装，版本: {trt.__version__}")
        return True
    except ImportError:
        logger.error("❌ TensorRT未安装")
        logger.info("请运行: pip install nvidia-tensorrt")
        return False


def check_cuda_available() -> bool:
    """检查CUDA是否可用"""
    try:
        import torch

        if torch.cuda.is_available():
            logger.info(f"✅ CUDA可用，设备: {torch.cuda.get_device_name(0)}")
            logger.info(f"   CUDA版本: {torch.version.cuda}")
            return True
        else:
            logger.error("❌ CUDA不可用")
            return False
    except Exception as e:
        logger.error(f"❌ 检查CUDA失败: {e}")
        return False


def convert_model_to_tensorrt(
    model_path: str,
    output_path: Optional[str] = None,
    imgsz: int = 640,
    precision: str = "fp16",
    workspace: int = 4,
    device: int = 0,
) -> bool:
    """
    将YOLO模型转换为TensorRT引擎

    Args:
        model_path: PyTorch模型路径
        output_path: 输出路径（可选，默认与输入路径相同，扩展名为.engine）
        imgsz: 输入图像大小
        precision: 精度 ('fp32', 'fp16', 'int8')
        workspace: 工作空间大小(GB)
        device: GPU设备编号

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

        # 确定输出路径
        if output_path is None:
            output_path = model_path.with_suffix(".engine")
        else:
            output_path = Path(output_path)

        logger.info(f"开始转换模型: {model_path}")
        logger.info(f"输出路径: {output_path}")
        logger.info(f"精度: {precision}, 图像大小: {imgsz}, 工作空间: {workspace}GB")

        # 加载模型
        model = YOLO(str(model_path))

        # 设置精度标志
        half = precision == "fp16"

        # 导出为TensorRT
        model.export(
            format="engine",
            device=device,
            imgsz=imgsz,
            half=half,
            workspace=workspace,
            simplify=True,
            opset=12,
            dynamic=False,
            verbose=True,
        )

        # 检查输出文件
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info("✅ 模型转换成功！")
            logger.info(f"   输出文件: {output_path}")
            logger.info(f"   文件大小: {size_mb:.2f} MB")
            return True
        else:
            logger.error(f"❌ 输出文件不存在: {output_path}")
            return False

    except Exception as e:
        logger.error(f"❌ 模型转换失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def convert_all_models(
    models: List[Dict[str, str]],
    imgsz: int = 640,
    precision: str = "fp16",
    workspace: int = 4,
    device: int = 0,
) -> Dict[str, bool]:
    """
    批量转换所有模型

    Args:
        models: 模型配置列表，每个元素包含 'name', 'path', 'output'
        imgsz: 输入图像大小
        precision: 精度
        workspace: 工作空间大小(GB)
        device: GPU设备编号

    Returns:
        转换结果字典 {模型名: 是否成功}
    """
    results = {}

    logger.info(f"开始批量转换 {len(models)} 个模型...")
    logger.info(f"配置: 精度={precision}, 图像大小={imgsz}, 工作空间={workspace}GB")

    for i, model_info in enumerate(models, 1):
        name = model_info["name"]
        path = model_info["path"]
        output = model_info.get("output")

        logger.info(f"\n{'='*60}")
        logger.info(f"[{i}/{len(models)}] 转换模型: {name}")
        logger.info(f"{'='*60}")

        success = convert_model_to_tensorrt(
            model_path=path,
            output_path=output,
            imgsz=imgsz,
            precision=precision,
            workspace=workspace,
            device=device,
        )

        results[name] = success

        if success:
            logger.info(f"✅ {name} 转换成功")
        else:
            logger.error(f"❌ {name} 转换失败")

    return results


def print_summary(results: Dict[str, bool]):
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
    logger.info("TensorRT模型转换工具")
    logger.info("=" * 60)

    # 检查环境
    logger.info("\n1. 检查环境...")
    if not check_tensorrt_installation():
        logger.error("请先安装TensorRT")
        return 1

    if not check_cuda_available():
        logger.error("请确保CUDA可用")
        return 1

    # 定义要转换的模型
    logger.info("\n2. 准备转换模型列表...")
    models = [
        {
            "name": "人体检测 (YOLOv8n)",
            "path": "models/yolo/yolov8n.pt",
            "output": "models/yolo/yolov8n.engine",
        },
        {
            "name": "发网检测",
            "path": "models/hairnet_detection/hairnet_detection.pt",
            "output": "models/hairnet_detection/hairnet_detection.engine",
        },
        {
            "name": "姿态检测 (YOLOv8n-pose)",
            "path": "models/yolo/yolov8n-pose.pt",
            "output": "models/yolo/yolov8n-pose.engine",
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
    results = convert_all_models(
        models=models,
        imgsz=640,
        precision="fp16",  # 使用FP16精度以获得最佳性能
        workspace=4,  # 4GB工作空间
        device=0,  # 使用第一个GPU
    )

    # 打印摘要
    print_summary(results)

    # 返回退出码
    success_count = sum(1 for success in results.values() if success)
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

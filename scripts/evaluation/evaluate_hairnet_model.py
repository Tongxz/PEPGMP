#!/usr/bin/env python
"""
发网检测模型评估脚本

用法:
    python scripts/evaluation/evaluate_hairnet_model.py \
        --model models/hairnet_detection/hairnet_detection.pt \
        --data datasets/hairnet/data.yaml \
        --output evaluation_results.json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("错误: 未安装ultralytics库，请使用以下命令安装:")
    print("pip install ultralytics")
    sys.exit(1)


def evaluate_model(model_path: str, data_yaml: str, output_path: str = None):
    """评估发网检测模型"""
    print(f"加载模型: {model_path}")
    model = YOLO(model_path)

    print(f"加载数据集配置: {data_yaml}")
    print("开始评估...")

    # 在验证集上评估
    results = model.val(
        data=data_yaml,
        imgsz=640,
        conf=0.25,  # 与检测时保持一致
        iou=0.45,
        save_json=True,
        plots=True,
        verbose=True,
    )

    # 提取指标
    metrics = {
        "mAP50": float(results.box.map50) if hasattr(results.box, "map50") else 0.0,
        "mAP50_95": float(results.box.map) if hasattr(results.box, "map") else 0.0,
        "precision": float(results.box.mp) if hasattr(results.box, "mp") else 0.0,
        "recall": float(results.box.mr) if hasattr(results.box, "mr") else 0.0,
    }

    # 计算F1分数
    if metrics["precision"] + metrics["recall"] > 0:
        metrics["f1_score"] = (
            2
            * (metrics["precision"] * metrics["recall"])
            / (metrics["precision"] + metrics["recall"])
        )
    else:
        metrics["f1_score"] = 0.0

    # 评估标准
    metrics["evaluation"] = {
        "mAP50_status": "优秀"
        if metrics["mAP50"] >= 0.90
        else ("良好" if metrics["mAP50"] >= 0.80 else "需要改进"),
        "precision_status": "优秀"
        if metrics["precision"] >= 0.85
        else ("良好" if metrics["precision"] >= 0.75 else "需要改进"),
        "recall_status": "优秀"
        if metrics["recall"] >= 0.85
        else ("良好" if metrics["recall"] >= 0.75 else "需要改进"),
        "f1_status": "优秀"
        if metrics["f1_score"] >= 0.85
        else ("良好" if metrics["f1_score"] >= 0.75 else "需要改进"),
    }

    # 打印结果
    print("\n" + "=" * 50)
    print("评估结果:")
    print("=" * 50)
    print(
        f"mAP@0.5:        {metrics['mAP50']:.4f} ({metrics['evaluation']['mAP50_status']})"
    )
    print(f"mAP@0.5:0.95:   {metrics['mAP50_95']:.4f}")
    print(
        f"Precision:      {metrics['precision']:.4f} ({metrics['evaluation']['precision_status']})"
    )
    print(
        f"Recall:         {metrics['recall']:.4f} ({metrics['evaluation']['recall_status']})"
    )
    print(
        f"F1-Score:       {metrics['f1_score']:.4f} ({metrics['evaluation']['f1_status']})"
    )
    print("=" * 50)

    # 保存结果
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"\n评估结果已保存到: {output_path}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="评估发网检测模型")
    parser.add_argument("--model", type=str, required=True, help="模型文件路径")
    parser.add_argument("--data", type=str, required=True, help="数据集配置文件路径(data.yaml)")
    parser.add_argument("--output", type=str, default=None, help="输出JSON文件路径（可选）")

    args = parser.parse_args()

    # 检查文件是否存在
    if not Path(args.model).exists():
        print(f"错误: 模型文件不存在: {args.model}")
        return 1

    if not Path(args.data).exists():
        print(f"错误: 数据集配置文件不存在: {args.data}")
        return 1

    try:
        metrics = evaluate_model(args.model, args.data, args.output)

        # 判断模型是否需要改进
        if (
            metrics["mAP50"] < 0.75
            or metrics["precision"] < 0.70
            or metrics["recall"] < 0.70
        ):
            print("\n⚠️  警告: 模型性能需要改进，建议:")
            print("  1. 增加训练数据")
            print("  2. 调整超参数")
            print("  3. 增强数据增强")
            print("  4. 检查数据标注质量")
            return 1
        else:
            print("\n✅ 模型性能良好!")
            return 0

    except Exception as e:
        print(f"\n评估过程中出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

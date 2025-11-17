#!/usr/bin/env python
"""
手部检测模型评估脚本

用法:
    python scripts/evaluation/evaluate_handwash_model.py \
        --model models/handwash_model.pt \
        --data datasets/handwash \
        --output evaluation_results.json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    import numpy as np
except ImportError:
    print("错误: 未安装PyTorch，请使用以下命令安装:")
    print("pip install torch")
    sys.exit(1)


class HandwashDataset(Dataset):
    """手部检测数据集"""
    def __init__(self, data_dir, annotations_file):
        self.data_dir = Path(data_dir)
        self.annotations = json.loads(Path(annotations_file).read_text())
        self.sequences = []
        self.labels = []
        
        for session in self.annotations.get("sessions", []):
            sequence_file = self.data_dir / session["sequence_file"]
            if sequence_file.exists():
                sequence = np.load(sequence_file)
                self.sequences.append(sequence)
                self.labels.append(session["label"])
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        sequence = torch.FloatTensor(self.sequences[idx])
        label = torch.FloatTensor([self.labels[idx]])
        return sequence, label


def evaluate_model(model_path: str, data_dir: str, annotations_file: str, 
                   device: str = "cuda:0", output_path: str = None):
    """评估手部检测模型"""
    print(f"加载模型: {model_path}")
    model = torch.load(model_path, map_location=device)
    model.eval()
    
    print(f"加载数据集: {data_dir}")
    dataset = HandwashDataset(data_dir, annotations_file)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    print("开始评估...")
    
    total_correct = 0
    total_samples = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    
    with torch.no_grad():
        for sequences, labels in dataloader:
            sequences = sequences.to(device)
            labels = labels.to(device)
            
            logits = model(sequences)
            predictions = torch.sigmoid(logits) > 0.5
            
            # 计算准确率
            correct = (predictions.float() == labels).sum().item()
            total_correct += correct
            total_samples += labels.numel()
            
            # 计算混淆矩阵
            true_positives += ((predictions == 1) & (labels == 1)).sum().item()
            false_positives += ((predictions == 1) & (labels == 0)).sum().item()
            false_negatives += ((predictions == 0) & (labels == 1)).sum().item()
            true_negatives += ((predictions == 0) & (labels == 0)).sum().item()
    
    # 计算指标
    accuracy = total_correct / total_samples if total_samples > 0 else 0.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": {
            "true_positives": int(true_positives),
            "false_positives": int(false_positives),
            "false_negatives": int(false_negatives),
            "true_negatives": int(true_negatives)
        },
        "total_samples": int(total_samples)
    }
    
    # 评估标准
    metrics["evaluation"] = {
        "accuracy_status": "优秀" if accuracy >= 0.90 else ("良好" if accuracy >= 0.80 else "需要改进"),
        "precision_status": "优秀" if precision >= 0.85 else ("良好" if precision >= 0.75 else "需要改进"),
        "recall_status": "优秀" if recall >= 0.85 else ("良好" if recall >= 0.75 else "需要改进"),
        "f1_status": "优秀" if f1 >= 0.85 else ("良好" if f1 >= 0.75 else "需要改进"),
    }
    
    # 打印结果
    print("\n" + "="*50)
    print("评估结果:")
    print("="*50)
    print(f"Accuracy:       {accuracy:.4f} ({metrics['evaluation']['accuracy_status']})")
    print(f"Precision:      {precision:.4f} ({metrics['evaluation']['precision_status']})")
    print(f"Recall:         {recall:.4f} ({metrics['evaluation']['recall_status']})")
    print(f"F1-Score:       {f1:.4f} ({metrics['evaluation']['f1_status']})")
    print("\n混淆矩阵:")
    print(f"  TP (真正例): {true_positives}")
    print(f"  FP (假正例): {false_positives}")
    print(f"  FN (假负例): {false_negatives}")
    print(f"  TN (真负例): {true_negatives}")
    print("="*50)
    
    # 保存结果
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"\n评估结果已保存到: {output_path}")
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="评估手部检测模型")
    parser.add_argument("--model", type=str, required=True, help="模型文件路径")
    parser.add_argument("--data", type=str, required=True, help="数据集目录路径")
    parser.add_argument("--annotations", type=str, required=True, help="标注文件路径")
    parser.add_argument("--device", type=str, default="cuda:0", help="设备 (cuda:0, cpu)")
    parser.add_argument("--output", type=str, default=None, help="输出JSON文件路径（可选）")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not Path(args.model).exists():
        print(f"错误: 模型文件不存在: {args.model}")
        return 1
    
    if not Path(args.data).exists():
        print(f"错误: 数据集目录不存在: {args.data}")
        return 1
    
    if not Path(args.annotations).exists():
        print(f"错误: 标注文件不存在: {args.annotations}")
        return 1
    
    try:
        metrics = evaluate_model(
            args.model, 
            args.data, 
            args.annotations,
            args.device,
            args.output
        )
        
        # 判断模型是否需要改进
        if metrics["accuracy"] < 0.75 or metrics["precision"] < 0.70 or metrics["recall"] < 0.70:
            print("\n⚠️  警告: 模型性能需要改进，建议:")
            print("  1. 增加训练数据")
            print("  2. 调整超参数（学习率、批次大小）")
            print("  3. 增强数据增强（时间扭曲、噪声）")
            print("  4. 检查数据标注质量")
            print("  5. 考虑使用更复杂的模型架构（Transformer）")
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


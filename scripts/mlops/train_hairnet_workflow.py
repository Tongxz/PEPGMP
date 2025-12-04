#!/usr/bin/env python
"""
通过MLOps API创建和运行发网检测训练工作流

用法:
    python scripts/mlops/train_hairnet_workflow.py

注意: 请确保后端服务正在运行:
    python -m src.api.app
    或
    uvicorn src.api.app:app --reload
"""

import json
import sys
import time
from pathlib import Path

import requests

# API基础URL
BASE_URL = "http://localhost:8000/api/v1/mlops"

# 请求超时时间（秒）
REQUEST_TIMEOUT = 30


def create_training_workflow(dataset_path: str, data_yaml_path: str) -> dict:
    """创建工作流"""
    url = f"{BASE_URL}/workflows"

    workflow = {
        "name": "发网检测模型训练（Roboflow v15）",
        "type": "multi_behavior_training",
        "trigger": "manual",
        "description": "使用Roboflow发网检测数据集训练YOLOv8模型（v15，2类别）",
        "steps": [
            {
                "type": "multi_behavior_training",
                "name": "训练发网检测模型",
                "config": {
                    "dataset_dir": dataset_path,
                    "data_config": data_yaml_path,
                    "training_params": {
                        "model": "yolov8s.pt",
                        "epochs": 150,
                        "batch_size": 16,
                        "image_size": 640,
                        "device": "cuda:0",
                        "patience": 50,
                        "lr0": 0.01,
                        "lrf": 0.01,
                        "momentum": 0.937,
                        "weight_decay": 0.0005,
                        "warmup_epochs": 3.0,
                    },
                },
            }
        ],
    }

    print("📝 创建工作流...")
    print(f"数据集路径: {dataset_path}")
    print(f"配置文件: {data_yaml_path}")

    try:
        response = requests.post(url, json=workflow, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到API服务器")
        print("   请确保后端服务正在运行:")
        print("   python -m src.api.app")
        print("   或")
        print("   uvicorn src.api.app:app --reload")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\n❌ API请求超时")
        print("   请检查后端服务是否正常运行")
        sys.exit(1)

    print(f"✅ 工作流创建成功: {result['workflow_id']}")
    return result


def run_workflow(workflow_id: str) -> dict:
    """运行工作流"""
    url = f"{BASE_URL}/workflows/{workflow_id}/run"

    print(f"\n🚀 运行工作流: {workflow_id}...")

    try:
        response = requests.post(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到API服务器")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\n❌ API请求超时")
        sys.exit(1)

    print(f"✅ 工作流已启动: {result['run_id']}")
    return result


def monitor_workflow(workflow_id: str, run_id: str = None) -> dict:
    """监控工作流状态"""
    url = f"{BASE_URL}/workflows/{workflow_id}"

    print("\n📊 监控工作流状态...")
    print("=" * 60)

    last_status = None
    while True:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            workflow = response.json()
        except requests.exceptions.ConnectionError:
            print("\n❌ 无法连接到API服务器")
            sys.exit(1)
        except requests.exceptions.Timeout:
            print("\n⚠️  请求超时，继续监控...")
            time.sleep(5)
            continue

        status = workflow.get("status", "unknown")

        # 只在状态变化时打印
        if status != last_status:
            print(f"⏱️  {time.strftime('%Y-%m-%d %H:%M:%S')} - 状态: {status}")
            last_status = status

        if status in ["success", "failed", "error"]:
            print("=" * 60)
            break

        time.sleep(10)  # 每10秒检查一次

    return workflow


def get_training_results(workflow_id: str) -> tuple:
    """获取训练结果"""
    url = f"{BASE_URL}/workflows/{workflow_id}"

    print("\n📈 获取训练结果...")

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        workflow = response.json()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        return None, None
    except requests.exceptions.Timeout:
        print("❌ API请求超时")
        return None, None

    # 获取最后一次运行
    last_run = workflow.get("last_run")
    if not last_run:
        print("⚠️  未找到运行记录")
        return None, None

    # 获取运行详情
    run_url = f"{BASE_URL}/workflows/{workflow_id}/runs/{last_run}"
    try:
        response = requests.get(run_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        run_info = response.json()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        return None, None
    except requests.exceptions.Timeout:
        print("❌ API请求超时")
        return None, None

    # 从输出中提取训练结果
    outputs = run_info.get("outputs", [])
    for output in outputs:
        if output.get("step_name") == "训练发网检测模型":
            step_output = output.get("output", {})
            model_path = step_output.get("model_path")
            metrics = step_output.get("metrics", {})
            report_path = step_output.get("report_path")

            print("\n✅ 训练完成！")
            print(f"📁 模型路径: {model_path}")
            print(f"📄 报告路径: {report_path}")
            print("\n📊 评估指标:")
            print(
                f"  mAP@0.5:        {metrics.get('mAP50', 'N/A'):.4f}"
                if isinstance(metrics.get("mAP50"), (int, float))
                else f"  mAP@0.5:        {metrics.get('mAP50', 'N/A')}"
            )
            print(
                f"  mAP@0.5:0.95:   {metrics.get('mAP50_95', 'N/A'):.4f}"
                if isinstance(metrics.get("mAP50_95"), (int, float))
                else f"  mAP@0.5:0.95:   {metrics.get('mAP50_95', 'N/A')}"
            )
            print(
                f"  Precision:      {metrics.get('precision', 'N/A'):.4f}"
                if isinstance(metrics.get("precision"), (int, float))
                else f"  Precision:      {metrics.get('precision', 'N/A')}"
            )
            print(
                f"  Recall:         {metrics.get('recall', 'N/A'):.4f}"
                if isinstance(metrics.get("recall"), (int, float))
                else f"  Recall:         {metrics.get('recall', 'N/A')}"
            )

            # 计算F1分数
            precision = metrics.get("precision", 0)
            recall = metrics.get("recall", 0)
            if isinstance(precision, (int, float)) and isinstance(recall, (int, float)):
                if precision + recall > 0:
                    f1_score = 2 * (precision * recall) / (precision + recall)
                    print(f"  F1-Score:       {f1_score:.4f}")

            # 评估模型性能
            mAP50 = metrics.get("mAP50", 0)
            if isinstance(mAP50, (int, float)):
                if mAP50 >= 0.90:
                    print("\n🎉 模型性能优秀！可以部署到生产环境。")
                elif mAP50 >= 0.80:
                    print("\n✅ 模型性能良好，建议继续优化。")
                else:
                    print("\n⚠️  模型性能需要改进，建议:")
                    print("  1. 增加训练数据")
                    print("  2. 调整超参数")
                    print("  3. 增强数据增强")

            return model_path, metrics

    print("⚠️  未找到训练结果")
    return None, None


def main():
    """主函数"""
    # 数据集路径
    dataset_path = "/Users/zhou/Code/PEPGMP/data/datasets/hairnet.v15i.yolov8"
    data_yaml_path = (
        "/Users/zhou/Code/PEPGMP/data/datasets/hairnet.v15i.yolov8/data.yaml"
    )

    # 验证数据集存在
    dataset_dir = Path(dataset_path)
    data_yaml = Path(data_yaml_path)

    if not dataset_dir.exists():
        print(f"❌ 数据集目录不存在: {dataset_path}")
        return 1

    if not data_yaml.exists():
        print(f"❌ data.yaml 文件不存在: {data_yaml_path}")
        return 1

    print("✅ 数据集验证通过")
    print(f"   数据集目录: {dataset_path}")
    print(f"   配置文件: {data_yaml_path}")

    try:
        # 1. 创建工作流
        workflow_result = create_training_workflow(dataset_path, data_yaml_path)
        workflow_id = workflow_result["workflow_id"]

        # 2. 运行工作流
        run_result = run_workflow(workflow_id)
        run_id = run_result.get("run_id")

        # 3. 监控工作流
        monitor_workflow(workflow_id, run_id)

        # 4. 获取训练结果
        model_path, metrics = get_training_results(workflow_id)

        if model_path:
            print("\n📋 训练结果摘要:")
            print(f"   工作流ID: {workflow_id}")
            print(f"   运行ID: {run_id}")
            print(f"   模型路径: {model_path}")
            print(f"   评估指标: {json.dumps(metrics, indent=2, ensure_ascii=False)}")
            return 0
        else:
            print("\n❌ 未能获取训练结果")
            return 1

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API请求失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return 1
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

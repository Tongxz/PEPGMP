# 快速开始：使用Roboflow数据集训练发网检测模型

## 📋 前置条件

1. ✅ 数据集已复制到 `data/datasets/hairnet_roboflow_v6/`
2. ✅ `data.yaml` 已修改为正确的路径配置
3. ✅ 后端服务正在运行

## 🚀 快速开始

### 方法1: 使用Python脚本（推荐）

```bash
# 1. 确保后端服务运行
python -m src.api.app

# 2. 在另一个终端运行训练脚本
python scripts/mlops/train_hairnet_workflow.py
```

### 方法2: 使用curl命令

#### 步骤1: 创建工作流

```bash
curl -X POST "http://localhost:8000/api/v1/mlops/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "发网检测模型训练（Roboflow v6）",
    "type": "multi_behavior_training",
    "trigger": "manual",
    "description": "使用Roboflow发网检测数据集训练YOLOv8模型",
    "steps": [
      {
        "type": "multi_behavior_training",
        "name": "训练发网检测模型",
        "config": {
          "dataset_dir": "/Users/zhou/Code/Pyt/data/datasets/hairnet_roboflow_v6",
          "data_config": "/Users/zhou/Code/Pyt/data/datasets/hairnet_roboflow_v6/data.yaml",
          "training_params": {
            "model": "yolov8s.pt",
            "epochs": 150,
            "batch_size": 16,
            "image_size": 640,
            "device": "cuda:0",
            "patience": 50
          }
        }
      }
    ]
  }'
```

**响应示例**:
```json
{
  "message": "工作流创建成功",
  "workflow_id": "workflow_1731823456",
  "status": "active"
}
```

#### 步骤2: 运行工作流

```bash
# 替换 {workflow_id} 为实际的工作流ID
curl -X POST "http://localhost:8000/api/v1/mlops/workflows/{workflow_id}/run"
```

#### 步骤3: 查看工作流状态

```bash
# 替换 {workflow_id} 为实际的工作流ID
curl "http://localhost:8000/api/v1/mlops/workflows/{workflow_id}"
```

#### 步骤4: 获取训练结果

```bash
# 替换 {workflow_id} 和 {run_id} 为实际的值
curl "http://localhost:8000/api/v1/mlops/workflows/{workflow_id}/runs/{run_id}"
```

### 方法3: 使用Python交互式脚本

```python
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1/mlops"

# 1. 创建工作流
workflow = {
    "name": "发网检测模型训练（Roboflow v6）",
    "type": "multi_behavior_training",
    "trigger": "manual",
    "steps": [{
        "type": "multi_behavior_training",
        "name": "训练发网检测模型",
        "config": {
            "dataset_dir": "/Users/zhou/Code/Pyt/data/datasets/hairnet_roboflow_v6",
            "data_config": "/Users/zhou/Code/Pyt/data/datasets/hairnet_roboflow_v6/data.yaml",
            "training_params": {
                "model": "yolov8s.pt",
                "epochs": 150,
                "batch_size": 16,
                "image_size": 640,
                "device": "cuda:0"
            }
        }
    }]
}

response = requests.post(f"{BASE_URL}/workflows", json=workflow)
workflow_id = response.json()["workflow_id"]
print(f"工作流ID: {workflow_id}")

# 2. 运行工作流
response = requests.post(f"{BASE_URL}/workflows/{workflow_id}/run")
run_id = response.json()["run_id"]
print(f"运行ID: {run_id}")

# 3. 监控状态（每10秒检查一次）
while True:
    response = requests.get(f"{BASE_URL}/workflows/{workflow_id}")
    status = response.json().get("status")
    print(f"状态: {status}")
    if status in ["success", "failed"]:
        break
    time.sleep(10)

# 4. 获取结果
response = requests.get(f"{BASE_URL}/workflows/{workflow_id}/runs/{run_id}")
outputs = response.json().get("outputs", [])
for output in outputs:
    if output.get("step_name") == "训练发网检测模型":
        metrics = output.get("output", {}).get("metrics", {})
        print(f"评估指标: {json.dumps(metrics, indent=2)}")
```

## 📊 数据集信息

- **数据集名称**: Hairnet Data v6
- **训练集**: 3947 张图像
- **验证集**: 963 张图像
- **测试集**: 491 张图像
- **类别数**: 4
  - `hairnet` (发网)
  - `no_hairnet` (未戴发网)
  - `nonveg_board` (非素食标识牌)
  - `veg_board` (素食标识牌)

## ⚙️ 训练参数说明

- **model**: `yolov8s.pt` - 使用YOLOv8 Small模型（平衡速度和精度）
- **epochs**: `150` - 训练150轮
- **batch_size**: `16` - 批次大小（根据GPU内存调整）
- **image_size**: `640` - 图像尺寸（与检测时保持一致）
- **device**: `cuda:0` - 使用GPU训练（如果有）
- **patience**: `50` - 早停耐心值（验证损失50轮不下降则停止）

## 🔍 评估指标

训练完成后，查看以下指标：

- **mAP@0.5**: 平均精度（IoU=0.5），目标 ≥ 0.90
- **mAP@0.5:0.95**: 平均精度（IoU=0.5-0.95），目标 ≥ 0.75
- **Precision**: 精确率，目标 ≥ 0.85
- **Recall**: 召回率，目标 ≥ 0.85
- **F1-Score**: F1分数，目标 ≥ 0.85

## 📁 训练输出

训练完成后，模型和报告保存在：

- **模型路径**: `models/runs/multi_behavior_YYYYMMDD_HHMMSS/weights/best.pt`
- **训练报告**: `models/reports/multi_behavior_report_YYYYMMDD_HHMMSS.json`
- **训练曲线**: `models/runs/multi_behavior_YYYYMMDD_HHMMSS/results.png`

## ❓ 常见问题

### Q: API连接失败怎么办？

**A**: 确保后端服务正在运行：
```bash
# 检查服务是否运行
curl http://localhost:8000/api/v1/mlops/health

# 如果失败，启动服务
python -m src.api.app
```

### Q: 训练需要多长时间？

**A**: 
- 取决于数据集大小和GPU性能
- 对于3947张训练图像，使用GPU（CUDA）大约需要1-3小时
- 使用CPU可能需要10-20小时

### Q: 如何查看训练进度？

**A**: 
- 通过API: `GET /api/v1/mlops/workflows/{workflow_id}`
- 查看训练日志: `models/runs/{run_name}/` 目录
- 查看训练曲线: `models/runs/{run_name}/results.png`


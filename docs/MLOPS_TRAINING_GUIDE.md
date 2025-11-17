# MLOps 训练与评估指南

## 📋 目录

1. [使用 Roboflow 数据集](#使用-roboflow-数据集)
2. [上传数据集到 MLOps](#上传数据集到-mlops)
3. [创建工作流进行训练](#创建工作流进行训练)
4. [评估训练结果](#评估训练结果)
5. [发网检测训练示例](#发网检测训练示例)
6. [手部检测训练示例](#手部检测训练示例)

---

## 🌐 使用 Roboflow 数据集

### 1. 在 Roboflow 上选择数据集

**访问 Roboflow**: https://roboflow.com

**搜索数据集**:
- 搜索关键词: `hairnet detection`, `safety helmet`, `PPE detection`, `handwashing detection`
- 筛选条件:
  - **格式**: YOLOv8 / YOLOv5 (推荐)
  - **类别**: 包含发网、头部、人体等类别
  - **数据量**: 建议 ≥ 500 张图像
  - **标注质量**: 查看数据集预览，确保标注准确

**推荐数据集**:
- **发网检测**: 搜索 "hairnet" 或 "PPE detection"
- **手部检测**: 搜索 "handwashing" 或 "hand detection"

### 2. 下载数据集

**步骤**:
1. 在 Roboflow 上选择数据集
2. 点击 "Download" 按钮
3. 选择格式: **YOLOv8** (推荐) 或 **YOLOv5**
4. 选择版本: 最新版本
5. 下载 ZIP 文件

**数据集结构** (YOLO格式):
```
dataset_name/
├── train/
│   ├── images/        # 训练图像
│   └── labels/        # YOLO格式标注文件 (.txt)
├── valid/             # 验证集
│   ├── images/
│   └── labels/
├── test/              # 测试集（可选）
│   ├── images/
│   └── labels/
└── data.yaml          # 数据集配置文件
```

**data.yaml 格式**:
```yaml
path: /path/to/dataset
train: train/images
val: valid/images
test: test/images  # 可选

nc: 3  # 类别数
names:
  0: hairnet    # 发网
  1: head       # 头部
  2: person     # 人体
```

### 3. 准备数据集

**解压数据集**:
```bash
unzip dataset_name.zip -d datasets/
```

**验证数据集结构**:
```bash
# 检查文件结构
ls -R datasets/dataset_name/

# 检查标注文件数量
find datasets/dataset_name/train/labels -name "*.txt" | wc -l
find datasets/dataset_name/valid/labels -name "*.txt" | wc -l
```

**修改 data.yaml** (如果需要):
```yaml
# 修改路径为相对路径或绝对路径
path: datasets/dataset_name  # 或使用绝对路径
train: train/images
val: valid/images
nc: 3
names:
  0: hairnet
  1: head
  2: person
```

---

## 📤 上传数据集到 MLOps

### 方法1: 通过 API 上传

**API 端点**: `POST /api/v1/mlops/datasets/upload`

**请求示例** (使用 curl):
```bash
curl -X POST "http://localhost:8000/api/v1/mlops/datasets/upload" \
  -F "files=@datasets/dataset_name/data.yaml" \
  -F "files=@datasets/dataset_name/train/images/image1.jpg" \
  -F "files=@datasets/dataset_name/train/labels/image1.txt" \
  -F "dataset_name=hairnet_roboflow_v1" \
  -F "dataset_type=detection" \
  -F "description=发网检测数据集，来自Roboflow"
```

**Python 示例** (推荐: 直接复制数据集目录):
```python
import shutil
from pathlib import Path
import requests

# 方法1: 直接复制数据集到data/datasets目录（推荐，适合大文件）
source_dir = Path("datasets/hairnet_roboflow_v1")
target_dir = Path("data/datasets/hairnet_roboflow_v1")

# 复制整个数据集目录
if source_dir.exists():
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    print(f"数据集已复制到: {target_dir}")

# 然后通过API注册数据集（可选，如果需要在MLOps系统中管理）
url = "http://localhost:8000/api/v1/mlops/datasets"
data = {
    "id": f"dataset_{int(time.time())}",
    "name": "hairnet_roboflow_v1",
    "version": "1.0.0",
    "status": "active",
    "file_path": str(target_dir),
    "tags": ["detection", "roboflow", "hairnet"]
}

response = requests.post(url, json=data)
print(response.json())
```

**注意**: 
- 对于大型数据集（>100MB），建议直接复制到 `data/datasets/` 目录，而不是通过API上传
- API上传适合小文件或单个文件
- 确保 `data.yaml` 文件中的路径配置正确

### 方法2: 直接复制到数据集目录

**数据集目录**: `data/datasets/`

**步骤**:
1. 将数据集复制到 `data/datasets/` 目录
2. 通过 API 注册数据集到数据库

**Python 脚本**:
```python
import shutil
from pathlib import Path
import requests

# 复制数据集
source_dir = Path("datasets/dataset_name")
target_dir = Path("data/datasets/hairnet_roboflow_v1")
shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

# 注册数据集到数据库
url = "http://localhost:8000/api/v1/mlops/datasets"
data = {
    "id": f"dataset_{int(time.time())}",
    "name": "hairnet_roboflow_v1",
    "version": "1.0.0",
    "status": "active",
    "file_path": str(target_dir),
    "tags": ["detection", "roboflow"]
}

response = requests.post(url, json=data)
```

### 方法3: 通过前端界面上传

1. 访问 MLOps 前端界面
2. 进入 "数据集管理" 页面
3. 点击 "上传数据集"
4. 选择文件或拖拽文件
5. 填写数据集信息（名称、类型、描述）
6. 点击 "上传"

---

## 🔄 创建工作流进行训练

### 1. 工作流结构

**工作流配置** (发网检测):
```json
{
  "name": "发网检测模型训练",
  "type": "multi_behavior_training",
  "trigger": "manual",
  "description": "使用Roboflow数据集训练发网检测模型",
  "steps": [
    {
      "type": "multi_behavior_training",
      "name": "训练发网检测模型",
      "config": {
        "dataset_dir": "data/datasets/hairnet_roboflow_v1",
        "data_config": "data/datasets/hairnet_roboflow_v1/data.yaml",
        "training_params": {
          "model": "yolov8s.pt",
          "epochs": 150,
          "batch_size": 16,
          "image_size": 640,
          "device": "cuda:0",
          "patience": 50
        }
      }
    },
    {
      "type": "model_evaluation",
      "name": "评估模型性能",
      "config": {
        "model_path": "{{steps[0].outputs.model_path}}",
        "test_data": "data/datasets/hairnet_roboflow_v1/valid",
        "metrics": ["mAP50", "precision", "recall", "f1_score"]
      }
    }
  ]
}
```

**注意**: 
- 发网检测使用 `multi_behavior_training` 步骤类型（支持YOLO格式）
- 手部检测使用 `handwash_training` 步骤类型（时序模型）

### 2. 通过 API 创建工作流

**API 端点**: `POST /api/v1/mlops/workflows`

**请求示例** (发网检测):
```python
import requests
import json

url = "http://localhost:8000/api/v1/mlops/workflows"

workflow = {
    "name": "发网检测模型训练",
    "type": "multi_behavior_training",
    "trigger": "manual",
    "description": "使用Roboflow数据集训练发网检测模型",
    "steps": [
        {
            "type": "multi_behavior_training",
            "name": "训练发网检测模型",
            "config": {
                "dataset_dir": "data/datasets/hairnet_roboflow_v1",
                "data_config": "data/datasets/hairnet_roboflow_v1/data.yaml",
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
}

response = requests.post(url, json=workflow)
result = response.json()
print(f"工作流ID: {result['workflow_id']}")
```

### 3. 运行工作流

**API 端点**: `POST /api/v1/mlops/workflows/{workflow_id}/run`

**请求示例**:
```python
workflow_id = result["workflow_id"]
run_url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}/run"

response = requests.post(run_url)
run_result = response.json()
print(f"运行ID: {run_result['run_id']}")
print(f"状态: {run_result['status']}")
```

### 4. 查看工作流状态

**API 端点**: `GET /api/v1/mlops/workflows/{workflow_id}`

**请求示例**:
```python
status_url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}"
response = requests.get(status_url)
workflow_status = response.json()
print(json.dumps(workflow_status, indent=2))
```

---

## 📊 评估训练结果

### 1. 查看训练报告

**训练完成后，系统会自动生成训练报告**:
- **位置**: `models/runs/multi_behavior_YYYYMMDD_HHMMSS/` (发网检测)
- **文件**:
  - `results.csv`: 训练指标CSV（包含每轮的loss、mAP、Precision、Recall等）
  - `results.png`: 训练曲线图（loss曲线、mAP曲线等）
  - `confusion_matrix.png`: 混淆矩阵
  - `weights/best.pt`: 最佳模型（验证集上性能最好的模型）
  - `weights/last.pt`: 最后一轮模型

**训练报告位置** (从工作流输出获取):
- 工作流运行完成后，可以从 `outputs` 中获取 `report_path`
- 报告文件: `models/reports/multi_behavior_report_YYYYMMDD_HHMMSS.json`

### 2. 从工作流输出获取评估结果

**训练完成后，评估指标会自动包含在工作流输出中**:

```python
# 获取工作流运行结果
workflow_id = "workflow_xxx"
run_id = "run_xxx"

url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}/runs/{run_id}"
response = requests.get(url)
run_info = response.json()

# 从输出中提取评估指标
outputs = run_info.get("outputs", [])
for output in outputs:
    if output.get("step_name") == "训练发网检测模型":
        step_output = output.get("output", {})
        metrics = step_output.get("metrics", {})
        
        print(f"mAP@0.5: {metrics.get('mAP50', 'N/A')}")
        print(f"mAP@0.5:0.95: {metrics.get('mAP50_95', 'N/A')}")
        print(f"Precision: {metrics.get('precision', 'N/A')}")
        print(f"Recall: {metrics.get('recall', 'N/A')}")
        
        # 模型路径
        model_path = step_output.get("model_path")
        print(f"模型路径: {model_path}")
        
        # 报告路径
        report_path = step_output.get("report_path")
        print(f"报告路径: {report_path}")
```

### 3. 通过模型注册表获取评估结果

**如果模型已注册到模型注册表**:

```python
# 获取模型列表
url = "http://localhost:8000/api/v1/mlops/models"
response = requests.get(url)
models = response.json()

# 查找最新训练的模型
latest_model = max(models, key=lambda m: m.get("created_at", ""))
model_id = latest_model["id"]

# 获取模型详情
url = f"http://localhost:8000/api/v1/mlops/models/{model_id}"
response = requests.get(url)
model_info = response.json()

# 查看评估指标
metrics = model_info.get("metrics", {})
print(f"mAP@0.5: {metrics.get('mAP50', 'N/A')}")
print(f"Precision: {metrics.get('precision', 'N/A')}")
print(f"Recall: {metrics.get('recall', 'N/A')}")
print(f"F1-Score: {metrics.get('f1_score', 'N/A')}")
```

### 3. 评估标准

**优秀模型**:
- mAP@0.5 ≥ 0.90
- Precision ≥ 0.85
- Recall ≥ 0.85
- F1-Score ≥ 0.85

**良好模型**:
- mAP@0.5 ≥ 0.80
- Precision ≥ 0.75
- Recall ≥ 0.75
- F1-Score ≥ 0.75

**需要改进**:
- mAP@0.5 < 0.75
- Precision < 0.70
- Recall < 0.70

---

## 🎯 发网检测训练示例

### 完整工作流配置

**重要**: 发网检测使用 `multi_behavior_training` 步骤类型，因为它支持YOLO格式的 `data.yaml` 配置文件。

```json
{
  "name": "发网检测模型训练（Roboflow）",
  "type": "multi_behavior_training",
  "trigger": "manual",
  "description": "使用Roboflow发网检测数据集训练YOLOv8模型",
  "steps": [
    {
      "type": "multi_behavior_training",
      "name": "训练发网检测模型",
      "config": {
        "dataset_dir": "data/datasets/hairnet_roboflow_v1",
        "data_config": "data/datasets/hairnet_roboflow_v1/data.yaml",
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
          "warmup_epochs": 3.0
        }
      }
    },
    {
      "type": "model_evaluation",
      "name": "评估模型性能",
      "config": {
        "model_path": "{{steps[0].outputs.model_path}}",
        "test_data": "data/datasets/hairnet_roboflow_v1/valid",
        "metrics": ["mAP50", "mAP50_95", "precision", "recall", "f1_score"]
      }
    }
  ]
}
```

### 关键配置说明

**步骤类型**: `multi_behavior_training`
- 支持YOLO格式数据集（train/valid/test + data.yaml）
- 自动提取训练指标（mAP、Precision、Recall等）
- 生成训练报告和可视化图表

**数据集路径**: 
- `dataset_dir`: 数据集根目录（包含train/valid目录）
- `data_config`: data.yaml文件路径（必须）

**训练参数**:
- `model`: 预训练模型（yolov8n.pt, yolov8s.pt, yolov8m.pt等）
- `epochs`: 训练轮数（建议100-200）
- `batch_size`: 批次大小（根据GPU内存调整）
- `image_size`: 图像尺寸（建议640，与检测时保持一致）
- `device`: 训练设备（cuda:0, cpu等）
- `patience`: 早停耐心值（验证损失不下降的轮数）

### Python 完整示例

```python
import requests
import json
import time
from pathlib import Path

# 1. 上传数据集（如果还没有上传）
def upload_dataset(dataset_dir: Path):
    url = "http://localhost:8000/api/v1/mlops/datasets/upload"
    
    files = []
    # 添加 data.yaml
    data_yaml = dataset_dir / "data.yaml"
    if data_yaml.exists():
        files.append(("files", ("data.yaml", open(data_yaml, "rb"))))
    
    data = {
        "dataset_name": "hairnet_roboflow_v1",
        "dataset_type": "detection",
        "description": "发网检测数据集，来自Roboflow"
    }
    
    response = requests.post(url, files=files, data=data)
    return response.json()

# 2. 创建工作流
def create_training_workflow(dataset_path: str):
    url = "http://localhost:8000/api/v1/mlops/workflows"
    
    workflow = {
        "name": "发网检测模型训练（Roboflow）",
        "type": "multi_behavior_training",
        "trigger": "manual",
        "description": "使用Roboflow发网检测数据集训练YOLOv8模型",
        "steps": [
            {
                "type": "multi_behavior_training",
                "name": "训练发网检测模型",
                "config": {
                    "dataset_dir": dataset_path,
                    "data_config": f"{dataset_path}/data.yaml",
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
    }
    
    response = requests.post(url, json=workflow)
    return response.json()

# 3. 运行工作流
def run_workflow(workflow_id: str):
    url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}/run"
    response = requests.post(url)
    return response.json()

# 4. 监控工作流状态
def monitor_workflow(workflow_id: str):
    url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}"
    
    while True:
        response = requests.get(url)
        workflow = response.json()
        status = workflow.get("status")
        
        print(f"工作流状态: {status}")
        
        if status in ["success", "failed"]:
            break
        
        time.sleep(10)  # 每10秒检查一次
    
    return workflow

# 5. 获取训练结果
def get_training_results(workflow_id: str):
    url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}"
    response = requests.get(url)
    workflow = response.json()
    
    # 从工作流输出中获取模型信息
    last_run = workflow.get("last_run")
    if last_run:
        run_url = f"http://localhost:8000/api/v1/mlops/workflows/{workflow_id}/runs/{last_run}"
        response = requests.get(run_url)
        run_info = response.json()
        
        outputs = run_info.get("outputs", [])
        for output in outputs:
            if output.get("step_name") == "训练发网检测模型":
                model_path = output.get("output", {}).get("model_path")
                metrics = output.get("output", {}).get("metrics", {})
                print(f"模型路径: {model_path}")
                print(f"评估指标: {json.dumps(metrics, indent=2)}")
                return model_path, metrics
    
    return None, None

# 主流程
if __name__ == "__main__":
    dataset_path = "data/datasets/hairnet_roboflow_v1"
    
    # 1. 创建工作流
    workflow_result = create_training_workflow(dataset_path)
    workflow_id = workflow_result["workflow_id"]
    print(f"工作流创建成功: {workflow_id}")
    
    # 2. 运行工作流
    run_result = run_workflow(workflow_id)
    print(f"工作流运行中: {run_result['run_id']}")
    
    # 3. 监控工作流
    final_workflow = monitor_workflow(workflow_id)
    
    # 4. 获取训练结果
    model_path, metrics = get_training_results(workflow_id)
    if model_path:
        print(f"\n训练完成！")
        print(f"模型路径: {model_path}")
        print(f"评估指标: {json.dumps(metrics, indent=2)}")
```

---

## 🤲 手部检测训练示例

### 工作流配置

```json
{
  "name": "手部检测模型训练",
  "type": "handwash_training",
  "trigger": "manual",
  "description": "训练手部检测时序模型",
  "steps": [
    {
      "type": "handwash_training",
      "name": "训练手部检测模型",
      "config": {
        "dataset_dir": "data/datasets/handwash_roboflow_v1",
        "annotations_file": "data/datasets/handwash_roboflow_v1/annotations.json",
        "training_params": {
          "epochs": 100,
          "batch_size": 32,
          "learning_rate": 0.001,
          "validation_split": 0.2,
          "device": "cuda:0"
        }
      }
    },
    {
      "type": "model_evaluation",
      "name": "评估模型性能",
      "config": {
        "model_path": "{{steps[0].outputs.model_path}}",
        "test_data": "data/datasets/handwash_roboflow_v1/test",
        "metrics": ["accuracy", "precision", "recall", "f1_score"]
      }
    }
  ]
}
```

---

## 🔍 选择 Roboflow 数据集的建议

### 发网检测数据集选择标准

1. **数据量**:
   - 训练集: ≥ 500 张图像
   - 验证集: ≥ 100 张图像
   - 测试集: ≥ 50 张图像（可选）

2. **类别覆盖**:
   - 必须包含: `hairnet` (发网)
   - 建议包含: `head` (头部), `person` (人体)
   - 类别数量: 2-4 个类别（避免过多类别）

3. **场景多样性**:
   - 不同光照条件
   - 不同角度（正面、侧面、背面）
   - 不同发网类型（颜色、材质）
   - 不同背景环境

4. **标注质量**:
   - 边界框准确
   - 类别标签正确
   - 无遗漏标注

### 手部检测数据集选择标准

1. **数据格式**:
   - 如果是图像序列: 需要时序标注
   - 如果是单张图像: 需要手部关键点标注

2. **动作覆盖**:
   - 标准洗手动作
   - 快速洗手动作
   - 非洗手动作（负样本）

3. **环境多样性**:
   - 不同水池类型
   - 不同光照条件
   - 不同视角

---

## 📝 总结

### 使用 Roboflow 数据集的完整流程

1. **选择数据集**: 在 Roboflow 上搜索并选择合适的数据集
2. **下载数据集**: 下载 YOLOv8 格式的数据集
3. **准备数据集**: 解压并验证数据集结构
4. **上传数据集**: 通过 API 或前端界面上传到 MLOps 系统
5. **创建工作流**: 配置训练工作流（包含训练和评估步骤）
6. **运行工作流**: 执行训练工作流
7. **监控训练**: 查看训练进度和日志
8. **评估结果**: 查看训练报告和评估指标
9. **部署模型**: 如果性能满足要求，部署模型到生产环境

### 关键 API 端点

**数据集管理**:
- `POST /api/v1/mlops/datasets/upload` - 上传数据集（小文件）
- `GET /api/v1/mlops/datasets` - 获取数据集列表
- `GET /api/v1/mlops/datasets/{dataset_id}` - 获取数据集详情
- `DELETE /api/v1/mlops/datasets/{dataset_id}` - 删除数据集

**工作流管理**:
- `POST /api/v1/mlops/workflows` - 创建工作流
- `GET /api/v1/mlops/workflows` - 获取工作流列表
- `GET /api/v1/mlops/workflows/{workflow_id}` - 查看工作流详情
- `POST /api/v1/mlops/workflows/{workflow_id}/run` - 运行工作流
- `GET /api/v1/mlops/workflows/{workflow_id}/runs/{run_id}` - 获取工作流运行结果
- `PUT /api/v1/mlops/workflows/{workflow_id}` - 更新工作流
- `DELETE /api/v1/mlops/workflows/{workflow_id}` - 删除工作流

**模型管理**:
- `GET /api/v1/mlops/models` - 获取模型列表
- `GET /api/v1/mlops/models/{model_id}` - 获取模型详情
- `POST /api/v1/mlops/models/{model_id}/deploy` - 部署模型

### 工作流步骤类型

**训练相关**:
- `multi_behavior_training` - 多行为检测训练（YOLO格式，用于发网检测）
- `handwash_training` - 手部检测训练（时序模型）
- `model_training` - 通用模型训练（分类任务）

**数据集相关**:
- `dataset_generation` - 从检测记录生成数据集
- `multi_behavior_dataset` - 生成多行为检测数据集
- `handwash_dataset` - 生成手部检测数据集

**评估和部署**:
- `model_evaluation` - 模型评估
- `model_deployment` - 模型部署

---

## ❓ 常见问题

### Q1: 如何选择使用哪个训练步骤类型？

**A**: 
- **发网检测**: 使用 `multi_behavior_training`（YOLO格式数据集，支持data.yaml）
- **手部检测**: 使用 `handwash_training`（时序模型，需要annotations.json）
- **分类任务**: 使用 `model_training`（二分类：违规/正常）

### Q2: Roboflow数据集下载后如何使用？

**A**: 
1. 解压数据集到本地
2. 复制到 `data/datasets/` 目录
3. 检查并修改 `data.yaml` 中的路径配置（使用绝对路径或相对路径）
4. 在工作流中指定 `dataset_dir` 和 `data_config` 路径

### Q3: data.yaml 路径配置错误怎么办？

**A**: 
修改 `data.yaml` 中的路径为绝对路径或相对于数据集目录的路径:
```yaml
# 方式1: 绝对路径（推荐）
path: /Users/zhou/Code/Pyt/data/datasets/hairnet_roboflow_v1

# 方式2: 相对路径（相对于data.yaml所在目录）
path: .
train: train/images
val: valid/images
```

### Q4: 训练过程中如何查看进度？

**A**: 
- 通过工作流运行状态API: `GET /api/v1/mlops/workflows/{workflow_id}`
- 查看训练日志: `models/runs/{run_name}/` 目录
- 查看训练曲线: `models/runs/{run_name}/results.png`
- 查看实时日志: 训练过程中会输出到控制台

### Q5: 如何判断模型训练是否成功？

**A**: 
检查评估指标:
- **优秀**: mAP@0.5 ≥ 0.90, Precision ≥ 0.85, Recall ≥ 0.85
- **良好**: mAP@0.5 ≥ 0.80, Precision ≥ 0.75, Recall ≥ 0.75
- **需要改进**: mAP@0.5 < 0.75

### Q6: 训练完成后如何部署模型？

**A**: 
1. 从工作流输出获取模型路径（`outputs[0].output.model_path`）
2. 复制模型到 `models/hairnet_detection/` 目录
3. 更新配置文件中的模型路径
4. 重启检测服务

### Q7: 训练时GPU内存不足怎么办？

**A**: 
- 减小 `batch_size`（如从16改为8）
- 减小 `image_size`（如从640改为512）
- 使用更小的模型（如yolov8n.pt而不是yolov8s.pt）

### Q8: 如何从训练结果中获取最佳模型？

**A**: 
- 最佳模型路径: `models/runs/{run_name}/weights/best.pt`
- 从工作流输出中获取: `outputs[0].output.model_path`
- 训练报告路径: `outputs[0].output.report_path`

### Q9: 工作流运行失败怎么办？

**A**: 
1. 查看工作流运行日志: `GET /api/v1/mlops/workflows/{workflow_id}/runs/{run_id}`
2. 检查数据集路径是否正确
3. 检查 `data.yaml` 文件格式是否正确
4. 检查训练参数是否合理（batch_size、epochs等）
5. 查看后端日志文件

### Q10: 如何评估训练程度？

**A**: 
**发网检测评估指标**:
- **mAP@0.5**: 平均精度（IoU=0.5），目标 ≥ 0.90
- **Precision**: 精确率，目标 ≥ 0.85
- **Recall**: 召回率，目标 ≥ 0.85
- **F1-Score**: F1分数，目标 ≥ 0.85

**手部检测评估指标**:
- **Accuracy**: 准确率，目标 ≥ 0.90
- **Precision**: 精确率，目标 ≥ 0.85
- **Recall**: 召回率，目标 ≥ 0.85
- **F1-Score**: F1分数，目标 ≥ 0.85

**训练曲线分析**:
- Loss曲线应该持续下降
- mAP曲线应该持续上升
- 验证集和训练集的指标应该接近（避免过拟合）

---

## 🔗 相关文档

- [训练与评估指南](./TRAINING_AND_EVALUATION_GUIDE.md)
- [MLOps API 文档](../src/api/routers/mlops.py)
- [工作流引擎文档](../src/workflow/workflow_engine.py)
- [Roboflow 官网](https://roboflow.com)
- [YOLOv8 文档](https://docs.ultralytics.com/)


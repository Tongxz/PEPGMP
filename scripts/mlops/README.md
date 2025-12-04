# MLOps 训练脚本使用说明

## 📁 数据集准备

1. **数据集位置**: `data/datasets/hairnet_roboflow_v6/`
2. **配置文件**: `data/datasets/hairnet_roboflow_v6/data.yaml`

### data.yaml 配置说明

```yaml
path: /Users/zhou/Code/PEPGMP/data/datasets/hairnet_roboflow_v6
train: train/images
val: valid/images
test: test/images

nc: 4
names: ['hairnet', 'no_hairnet', 'nonveg_board', 'veg_board']
```

✅ **已配置完成** - 路径已修正为绝对路径

## 🚀 快速开始

### 步骤1: 启动后端服务

```bash
# 在终端1中运行
python -m src.api.app
```

### 步骤2: 运行训练脚本

```bash
# 在终端2中运行
python scripts/mlops/train_hairnet_workflow.py
```

脚本会自动：
1. ✅ 验证数据集存在
2. ✅ 创建工作流
3. ✅ 运行工作流
4. ✅ 监控训练进度
5. ✅ 获取并显示评估指标

## 📊 训练参数

- **模型**: YOLOv8 Small (`yolov8s.pt`)
- **训练轮数**: 150 epochs
- **批次大小**: 16
- **图像尺寸**: 640x640
- **设备**: CUDA (GPU) 或 CPU
- **早停耐心**: 50 epochs

## 📈 评估指标

训练完成后会显示：
- **mAP@0.5**: 平均精度（IoU=0.5）
- **mAP@0.5:0.95**: 平均精度（IoU=0.5-0.95）
- **Precision**: 精确率
- **Recall**: 召回率
- **F1-Score**: F1分数

## 📁 输出文件

- **模型**: `models/runs/multi_behavior_YYYYMMDD_HHMMSS/weights/best.pt`
- **报告**: `models/reports/multi_behavior_report_YYYYMMDD_HHMMSS.json`
- **训练曲线**: `models/runs/multi_behavior_YYYYMMDD_HHMMSS/results.png`

## ❓ 常见问题

### Q: API连接失败？

**A**: 确保后端服务正在运行：
```bash
curl http://localhost:8000/api/v1/mlops/health
```

### Q: 如何查看训练日志？

**A**: 查看训练输出目录：
```bash
ls -la models/runs/
```

### Q: 训练需要多长时间？

**A**:
- GPU: 1-3小时
- CPU: 10-20小时

## 📚 更多信息

详细文档请参考：
- `docs/MLOPS_TRAINING_GUIDE.md` - 完整的MLOps训练指南
- `scripts/mlops/quick_start_training.md` - 快速开始指南

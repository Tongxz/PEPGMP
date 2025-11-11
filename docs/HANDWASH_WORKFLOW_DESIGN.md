# 洗手合规训练工作流设计

本文档基于《深度学习训练工作流实施规划》中第 3.2 节的总体要求，细化洗手合规检测工作流（Handwash Workflow）的实现方案，指导后续编码与联调。

---

## 1. 工作流目标

1. 从实时检测/历史录像中采集洗手片段，构建可追溯的数据资产。
2. 通过姿态估计与时序模型刻画洗手流程（覆盖开启水龙头、搓洗、冲洗、关阀等关键步骤）。
3. 输出评估报告（每步骤召回率、合规率、错误示例），并将训练成果登记到模型注册中心。
4. 在 MLOps 工作流中实现“一键执行”：数据采集 → 数据清洗 → 数据集生成 → 模型训练 → 评估与注册。

---

## 2. 数据流与组件

### 2.1 数据来源

| 来源 | 说明 | 输出 |
|------|------|------|
| 实时检测服务 | `DetectionApplicationService.process_realtime_stream` 产出的快照/视频帧 | 违规/正常帧、metadata 中的 `handwash_events` |
| 历史录像导入 | 待实现的批量导入接口，从摄像头归档中抽取洗手片段 | 原始视频段 (`mp4`) |
| 人工上传 | 前端手动上传标注好的洗手视频 | 标注前的视频资产 |

### 2.2 数据标准化

引入统一的 **Handwash Session** 抽象，每个 Session 包含：

- `session_id`
- `camera_id`
- `started_at` / `ended_at`
- `video_path`（原始视频）
- `key_frames`（关键帧快照）
- `labels`: 按步骤的时间戳标注（JSON）

数据仓储拟新增表 `handwash_sessions` 与 `handwash_labels`，并在 `DatasetDAO` 中扩展 CRUD。

### 2.3 数据集生成

新增 `HandwashDatasetGenerationService`，职责：

1. 将 Session 切分为固定长度的片段或定步长帧序列。
2. 运行姿态估计（YOLOv8-Pose 或 Mediapipe Pose）转换为关键点序列。
3. 根据标注输出：
   - `frames/`：关键帧或裁剪后的单帧图片（可选）。
   - `skeletons/`：关键点时序数据（`.npy` 或 `.json`）。
   - `annotations.json`：步骤标签、时间段、合规标记。
   - `metadata.json`：数据来源、采样策略、统计信息。

---

## 3. 模型训练设计

### 3.1 特征提取

优先使用 **方案 A**：YOLOv8-Pose + Temporal CNN。

- 运行姿态估计得到 `K × T × D` 的关键点矩阵（K：关节点数，T：时间帧数，D：维度）。
- 归一化骨架坐标（关节点相对坐标、尺度归一）。
- 可选提取派生特征（速度、夹角）。

保留接口以支持 **方案 B**（传统 CV 特征）作为回退或混合特征。

### 3.2 时序模型

采用 **Temporal Convolutional Network (TCN)** 初版实现，后续可扩展为 Transformer：

- 输入：`(batch_size, time_steps, feature_dim)`
- 输出：每个步骤的概率 + 全流程合规分数。
- Loss：交叉熵（步骤分类）+ BCE（合规状态）。

训练逻辑位于新模块 `src/application/handwash_training_service.py`，与 `ModelTrainingService` 并列。

### 3.3 评估指标

- 每步骤 Precision / Recall / F1。
- 整体流程合规率（全部步骤通过）。
- 步骤顺序错误/缺失的统计。
- 随机抽样的失败案例列表（用于标注复审）。

输出统一的 `handwash_training_report_<timestamp>.json`，结构包含：

```json
{
  "dataset_id": "...",
  "samples": 128,
  "steps": ["wet", "soap", "scrub", "rinse", "dry"],
  "metrics": {
    "step_metrics": {
      "wet": {"precision": 0.93, "recall": 0.90, "f1": 0.915},
      "...": {}
    },
    "workflow_compliance": 0.82
  },
  "confusion_matrix": {...},
  "failed_examples": [
    {"session_id": "...", "step": "rinse", "prediction": "missing", "timestamp": "..."}
  ]
}
```

---

## 4. 工作流编排（MLOps）

### 4.1 后端 API

| 模块 | 新增/修改 |
|------|-----------|
| `src/api/routers/mlops.py` | 扩展工作流模板定义，增加 `handwash_workflow` |
| `src/workflow/workflow_engine.py` | 新增步骤类型：`HANDWASH_DATA_PREP`、`HANDWASH_TRAINING` |
| `src/application/dataset_generation_service.py` | 与 `HandwashDatasetGenerationService` 协作 |
| `src/application/model_training_service.py` | 保留 YOLO 训练接口；新增手洗训练入口透传 |

### 4.2 前端

- `WorkflowManager.vue`：新增工作流模板配置，允许选择“洗手合规训练”。
- 参数表单：
  - 数据采集窗口（时间范围、摄像头选择）。
  - 姿态提取开关、关键点选择。
  - 时序模型参数（time window、batch size、epochs）。
- 运行日志展示关键阶段输出（采样统计、训练进度、指标摘要）。

---

## 5. 实施步骤

### 5.1 准备阶段

1. 建立数据库表 `handwash_sessions`、`handwash_labels`（迁移脚本）。
2. 定义姿态估计服务接口，评估 YOLOv8-Pose 与 Mediapipe 性能。
3. 整理数据目录结构 (`data/handwash/raw`, `data/handwash/processed` 等)。

### 5.2 迭代一（MVP）

- [ ] 实现 Handwash Session ingestion API（支持上传视频 + 标注）。
- [ ] 编写 `HandwashDatasetGenerationService`，产出姿态序列与标注。
- [ ] 初版 `HandwashTrainingService`（TCN），输出 JSON 报告。
- [ ] 工作流中串联步骤：数据准备 → 数据集生成 → 训练 → 报告。
- [ ] 前端新增模板，展示运行日志与性能指标。

### 5.3 迭代二（增强）

- [ ] 引入自动/半自动标注辅助工具（基于阈值或简单规则初标）。
- [ ] 增强评估：PR 曲线、关键步骤可视化、错误示例截图。
- [ ] 模型注册中心整合（注册版本、下载、灰度部署）。
- [ ] 性能优化：GPU 分布式训练、持续训练（fine-tuning）。

---

## 6. 依赖与风险

| 风险 | 应对措施 |
|------|----------|
| 姿态估计推理耗时 | 缓存关键点结果，统一批处理；提供离线前处理脚本 |
| 标注代价高 | 设计复用机制（模板、默认时间窗口），引入标注工具 |
| 数据隐私/合规 | 数据脱敏（马赛克）、访问控制日志、到期清理策略 |
| 时序模型预测不稳定 | 增加数据增强、投票机制、在线校验 |

---

## 7. 下一步

1. 提交数据库迁移草案与数据目录规范，征求 DBA/运维意见。
2. 编写 `HandwashDatasetGenerationService` 与单元测试，确保输出结构稳定。
3. 增量开发 `HandwashTrainingService`（TCN 模型），跑通最小闭环。
4. 更新 MLOps 工作流与前端表单，支持洗手流程的参数配置。

完成上述步骤后，进入集成测试阶段，与实时检测服务联调并验证评估报告，为后续上线打下基础。

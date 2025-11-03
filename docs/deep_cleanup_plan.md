# 深度清理计划 - 重构后遗留代码

## 日期
2025-11-03

## 概述

在完成DDD重构、依赖注入、策略模式、仓储模式实施后，项目中仍有一些已被重构替代、不再使用的代码和文件。本文档提供深度清理计划。

## 🔍 识别的废弃代码

### 1. Archive目录（已归档但可完全删除）

#### Phase 1 归档（架构优化相关）
```
archive/phase1/
├── architecture/           # 架构分析器（已被DDD替代）
├── mlops/                 # MLOps集成示例（已重构）
├── optimization/          # TensorRT优化器（已重构）
└── utils/                 # 旧工具函数（已重构）
```
**状态**: 已归档超过30天，可安全删除
**原因**: 这些代码已被新的DDD架构完全替代

#### Phase 2 归档（服务重构相关）
```
archive/phase2/
├── core/                  # 旧核心组件（已废弃）
├── services/              # 旧服务层（已被domain services替代）
└── strategies/            # 旧策略实现（已重构）
```
**状态**: 已归档，被domain层替代
**原因**: 这些服务已被domain/services/完全替代

#### Phase 3 归档（配置和工具）
```
archive/phase3/
├── config/                # 旧配置加载器（已被src/config替代）
└── utils/                 # 旧工具函数（已被src/utils替代）
```
**状态**: 已归档，有新实现
**原因**: 配置系统已完全重构

#### Deployment Legacy 归档
```
archive/deployment_legacy/
├── deployment/            # 旧部署脚本
├── scripts_deployment/    # 旧部署脚本
└── src_deployment/        # 旧部署代码
```
**状态**: 已归档，有新的scripts/
**原因**: 部署系统已完全重构

**建议**: 删除整个archive/目录（或保留最近30天的备份）

### 2. Examples目录（示例代码）

| 文件 | 状态 | 建议 |
|------|------|------|
| `examples/demo_camera_direct.py` | 未被引用 | ❌ 删除（已有新示例）|
| `examples/example_usage.py` | 未被引用 | ❌ 删除（过时）|
| `examples/integrate_yolo_detector.py` | 未被引用 | ❌ 删除（已集成）|
| `examples/use_yolo_hairnet_detector.py` | 未被引用 | ❌ 删除（已集成）|
| `examples/domain_model_usage.py` | 有价值的示例 | ✅ 保留（更新）|

**原因**:
- 大部分示例已过时，功能已集成到主代码
- `domain_model_usage.py`是唯一展示新DDD架构的示例

### 3. 示例服务文件（已被重构替代）

| 文件 | 状态 | 被替代者 | 建议 |
|------|------|----------|------|
| `src/services/detection_service_di.py` | 仅2处引用 | domain/services/ | ⚠️ 检查后删除 |

**原因**:
- 这是DI容器的示例实现
- 实际使用的是domain/services/detection_service.py

### 4. 备份文件

| 文件 | 说明 | 建议 |
|------|------|------|
| `Dockerfile.prod.old` | 旧Dockerfile备份 | ❌ 删除（已验证新版本）|
| `models/handwash_xgb.joblib.backup` | 模型备份 | ⚠️ 评估后删除 |

### 5. 测试工具文件（已整理到tools/）

在tools/目录中，以下文件可能需要评估：

| 文件 | 状态 | 建议 |
|------|------|------|
| `tools/test_mlops_integration.py` | 测试MLOps集成 | ⚠️ 评估是否还需要 |
| `tools/test_intelligent_features.py` | 测试智能特性 | ⚠️ 评估是否还需要 |

### 6. 重复的Requirements文件

| 文件 | 状态 | 建议 |
|------|------|------|
| `requirements.prod.txt` | 与requirements.txt对比 | ⚠️ 对比后决定 |
| `requirements.supervisor.txt` | Supervisor相关 | ⚠️ 如不使用可删除 |

### 7. Legacy目录（如存在）

检查是否还有其他legacy、old、backup等命名的目录。

## 📋 详细清理清单

### 阶段1：安全删除（高优先级）✅

**Archive目录完全删除**
```bash
# 1. 创建最终备份（可选）
tar -czf archive_final_backup_$(date +%Y%m%d).tar.gz archive/

# 2. 删除archive目录
rm -rf archive/
```

**预计释放空间**: ~10-50MB

**Examples目录清理**
```bash
# 删除过时的示例
rm -f examples/demo_camera_direct.py
rm -f examples/example_usage.py
rm -f examples/integrate_yolo_detector.py
rm -f examples/use_yolo_hairnet_detector.py

# 保留并更新domain_model_usage.py
```

**预计释放空间**: ~50-100KB

**删除备份文件**
```bash
rm -f Dockerfile.prod.old
```

### 阶段2：检查后删除（中优先级）⚠️

**检查detection_service_di.py的使用**
```bash
# 查找所有引用
grep -r "detection_service_di" --include="*.py" src/ tests/ main.py

# 如果只是测试引用，可以移动到examples/
# 如果没有实际使用，可以删除
```

**检查测试工具**
```bash
# 检查是否在CI/CD中使用
grep -r "test_mlops_integration\|test_intelligent_features" .github/ scripts/ci/

# 如果不使用，移动到archive_tests/
mkdir -p archive_tests/
mv tools/test_mlops_integration.py archive_tests/
mv tools/test_intelligent_features.py archive_tests/
```

**对比requirements文件**
```bash
# 对比差异
diff requirements.txt requirements.prod.txt

# 如果一致，删除重复的
# rm -f requirements.prod.txt
```

### 阶段3：整理优化（低优先级）📝

**更新domain_model_usage.py**
- 确保示例代码反映最新的DDD架构
- 添加更多实用示例

**整理模型文件**
```bash
# 检查模型备份
ls -lh models/*.backup

# 如果不需要，删除
# rm -f models/*.backup
```

**清理__pycache__和.pyc文件**
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

## 🚀 执行计划

### 步骤1：创建完整备份

```bash
# 备份当前状态
tar -czf project_before_deep_cleanup_$(date +%Y%m%d).tar.gz \
    archive/ \
    examples/ \
    Dockerfile.prod.old \
    src/services/detection_service_di.py \
    models/*.backup
```

### 步骤2：执行阶段1清理

```bash
# 运行自动化清理脚本
./scripts/deep_cleanup.sh --stage 1
```

### 步骤3：验证应用功能

```bash
# 运行测试
pytest tests/ -v

# 启动应用
./scripts/start_dev.sh
```

### 步骤4：执行阶段2和3

```bash
# 执行剩余清理
./scripts/deep_cleanup.sh --stage 2
./scripts/deep_cleanup.sh --stage 3
```

### 步骤5：提交更改

```bash
git add .
git commit -m "chore: 深度清理重构后遗留代码

- 删除archive/目录（所有已归档代码）
- 清理examples/目录（过时示例）
- 删除示例服务文件
- 移除备份文件
- 清理Python缓存

预计释放空间: ~50-100MB
"
```

## 📊 预期收益

### 空间节省

| 项目 | 预计节省 |
|------|----------|
| archive/ | 10-50MB |
| examples/ | 50-100KB |
| 备份文件 | 5-10MB |
| __pycache__ | 5-10MB |
| **总计** | **~20-70MB** |

### 代码质量

- ✅ 消除所有重构遗留代码
- ✅ 清晰的代码库结构
- ✅ 减少混淆
- ✅ 更快的搜索和导航

### 维护性

- ✅ 明确哪些代码在使用
- ✅ 减少技术债务
- ✅ 更好的新人引导
- ✅ 降低维护成本

## ⚠️ 风险评估

### 低风险（可直接执行）✅

- 删除archive/目录（有Git历史）
- 删除过时的examples/
- 删除.old备份文件
- 清理__pycache__

### 中风险（需要验证）⚠️

- 删除detection_service_di.py（检查引用）
- 删除测试工具（确认不在CI中使用）
- 删除requirements重复文件（对比差异）

### 高风险（谨慎处理）🔴

- 删除模型备份（确认有原始模型）

## 🔙 回滚方案

### 方式1：从备份恢复
```bash
tar -xzf project_before_deep_cleanup_YYYYMMDD.tar.gz
```

### 方式2：从Git恢复
```bash
git log --oneline
git reset --hard <commit-hash>
```

## ✅ 检查清单

### 清理前
- [ ] 创建完整备份
- [ ] 所有测试通过
- [ ] 应用正常运行
- [ ] 团队成员已通知

### 清理中
- [ ] 按阶段执行
- [ ] 每步后验证
- [ ] 记录删除内容

### 清理后
- [ ] 测试全部通过
- [ ] 应用正常启动
- [ ] 构建成功
- [ ] Git提交清理记录
- [ ] 文档更新

## 📝 决策记录

### 保留的文件

| 文件 | 原因 |
|------|------|
| `examples/domain_model_usage.py` | 展示DDD架构的唯一示例 |
| `tests/unit/` 所有测试 | 确保代码质量 |
| `tools/` 工具脚本 | 可能在CI/CD中使用 |

### 删除的文件

| 文件/目录 | 原因 |
|----------|------|
| `archive/` | 所有内容已被重构替代 |
| `examples/`（部分）| 过时且无引用 |
| `.old`备份文件 | 新版本已验证 |

## 🎯 预期结果

清理完成后，项目将：
- ✅ 只包含活跃使用的代码
- ✅ 无重构遗留代码
- ✅ 清晰的文件组织
- ✅ 更小的代码库体积
- ✅ 更快的CI/CD
- ✅ 更好的开发体验

---

**状态**: 📋 待执行
**优先级**: 中
**预计时间**: 30-45分钟
**风险等级**: 低-中

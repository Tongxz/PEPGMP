# 检测流程完整梳理与分析

## 📋 问题分析

### 当前检测流程

```
视频帧
  ↓
DetectionApplicationService.process_realtime_stream()
  ├─ detect_comprehensive() → DetectionResult
  │   ├─ person_detections
  │   ├─ hairnet_results (has_hairnet)
  │   ├─ handwash_results
  │   └─ sanitize_results
  │
  ├─ _analyze_violations() → (has_violations, violation_severity)
  │   └─ 检查 hairnet_results 中的 has_hairnet
  │   └─ 返回 no_hairnet 违规
  │
  ├─ _should_save_detection() → should_save
  │
  ├─ _convert_to_domain_format() → detected_objects
  │   └─ 转换 person_detections 为 person 对象
  │   └─ 转换 hairnet_results 为 hairnet/no_hairnet 对象
  │
  ├─ _save_snapshot_if_possible() → snapshot_info
  │   └─ violation_type = _get_primary_violation_type()
  │   └─ 从 _extract_violations_summary() 获取 no_hairnet
  │
  └─ DetectionServiceDomain.process_detection()
      ├─ 创建 DetectionRecord
      ├─ 添加快照信息到 metadata.snapshots
      ├─ ViolationService.detect_violations() → violations
      │   └─ 检查 no_safety_helmet、no_safety_vest 等规则
      │   └─ ❌ 没有检查发网违规规则
      │
      └─ 保存检测记录
```

### 问题根源

1. **双重违规检测逻辑不匹配**：
   - `DetectionApplicationService._analyze_violations` 检查 `hairnet_results`，返回 `no_hairnet`
   - `ViolationService.detect_violations` 检查通用规则（安全帽、安全背心），没有发网规则
   - 两个逻辑不一致，导致违规检测结果不匹配

2. **快照保存的 violation_type 来源不正确**：
   - `_get_primary_violation_type` 从 `_extract_violations_summary` 获取违规类型
   - `_extract_violations_summary` 检查 `hairnet_results` 中的 `has_hairnet`
   - 但 `ViolationService` 检测到的是 `no_safety_helmet` 等规则
   - 导致快照的 `violation_type` 与 `ViolationService` 检测到的违规类型不一致

3. **数据集生成依赖错误的违规类型**：
   - 数据集生成服务从检测记录的 `metadata.snapshots` 中提取快照
   - 快照的 `violation_type` 来自 `_get_primary_violation_type`
   - 但 `ViolationService` 检测到的违规类型是 `no_safety_helmet` 等
   - 导致数据集中的违规类型不准确

## 🔧 解决方案

### 方案1：统一违规检测逻辑（推荐）

**目标**：将发网违规检测逻辑统一到 `ViolationService` 中

**步骤**：
1. 在 `ViolationService` 中添加 `no_hairnet` 违规检测规则
2. 修改 `ViolationService.detect_violations` 检查发网检测结果
3. 修改 `DetectionApplicationService._analyze_violations` 使用 `ViolationService` 的结果
4. 修改 `_get_primary_violation_type` 使用 `ViolationService` 的结果

**优点**：
- 统一违规检测逻辑，避免重复代码
- 违规检测结果一致
- 易于扩展新的违规检测规则

**缺点**：
- 需要重构 `ViolationService`
- 需要修改 `DetectionApplicationService`

### 方案2：移除 ViolationService 的发网检测（不推荐）

**目标**：只在 `DetectionApplicationService` 中检测发网违规

**步骤**：
1. 移除 `ViolationService` 中的通用违规检测规则
2. 只在 `DetectionApplicationService` 中检测发网违规
3. 将发网违规信息直接保存到检测记录的 metadata 中

**优点**：
- 不需要重构 `ViolationService`
- 发网检测逻辑集中在一个地方

**缺点**：
- 违规检测逻辑分散
- 难以扩展新的违规检测规则
- 不符合单一职责原则

### 方案3：在 ViolationService 中检查发网检测结果（推荐）

**目标**：在 `ViolationService` 中检查检测对象中的发网信息

**步骤**：
1. 在 `ViolationService` 中添加 `no_hairnet` 违规检测规则
2. 检查检测对象中的 `metadata.has_hairnet` 字段
3. 如果 `has_hairnet = False`，则判定为 `no_hairnet` 违规
4. 修改 `DetectionApplicationService._analyze_violations` 使用 `ViolationService` 的结果

**优点**：
- 统一违规检测逻辑
- 基于检测对象的 metadata 进行判断
- 易于扩展新的违规检测规则

**缺点**：
- 需要修改 `ViolationService`
- 需要确保检测对象的 metadata 中包含发网信息

## 📝 实施计划

### 阶段1：修复 ViolationService

1. 在 `ViolationService` 中添加 `no_hairnet` 违规检测规则
2. 实现 `_check_no_hairnet` 方法，检查检测对象中的 `metadata.has_hairnet` 字段
3. 如果 `has_hairnet = False` 且置信度足够高，则判定为 `no_hairnet` 违规

### 阶段2：统一违规检测逻辑

1. 修改 `DetectionApplicationService._analyze_violations` 使用 `ViolationService` 的结果
2. 修改 `_get_primary_violation_type` 使用 `ViolationService` 的结果
3. 确保快照保存的 `violation_type` 与 `ViolationService` 检测到的违规类型一致

### 阶段3：验证和测试

1. 验证检测记录中的违规类型是否正确
2. 验证快照保存的 `violation_type` 是否正确
3. 验证数据集生成服务是否正确提取违规类型

## 🔍 关键代码位置

### DetectionApplicationService
- `src/application/detection_application_service.py`
  - `_analyze_violations()`: 检查 `hairnet_results` 中的 `has_hairnet`
  - `_extract_violations_summary()`: 提取违规摘要
  - `_get_primary_violation_type()`: 获取主要违规类型
  - `_convert_to_domain_format()`: 转换检测结果为领域格式

### ViolationService
- `src/domain/services/violation_service.py`
  - `detect_violations()`: 检测违规行为
  - `_initialize_violation_rules()`: 初始化违规检测规则
  - `_check_violation_rule()`: 检查特定违规规则

### DetectionServiceDomain
- `src/services/detection_service_domain.py`
  - `process_detection()`: 处理检测结果
  - 调用 `ViolationService.detect_violations()` 检测违规

### DatasetGenerationService
- `src/application/dataset_generation_service.py`
  - `_extract_snapshot_entries()`: 从检测记录中提取快照
  - 从 `metadata.snapshots` 中获取 `violation_type`

## 📊 数据流图

### 当前数据流（有问题）

```
DetectionResult (hairnet_results)
  ↓
_analyze_violations() → no_hairnet
  ↓
_get_primary_violation_type() → no_hairnet
  ↓
_save_snapshot_if_possible() → violation_type = no_hairnet
  ↓
DetectionRecord (metadata.snapshots[0].violation_type = no_hairnet)
  ↓
ViolationService.detect_violations() → no_safety_helmet, no_safety_vest
  ↓
DetectionRecord (metadata.violations = [no_safety_helmet, ...])
  ↓
DatasetGenerationService → violation_type = no_hairnet (来自 snapshots)
  ↓
数据集 (violation_type = no_hairnet)
```

### 修复后的数据流（预期）

```
DetectionResult (hairnet_results)
  ↓
_convert_to_domain_format() → detected_objects (metadata.has_hairnet)
  ↓
DetectionRecord (objects[].metadata.has_hairnet)
  ↓
ViolationService.detect_violations() → no_hairnet (检查 metadata.has_hairnet)
  ↓
DetectionRecord (metadata.violations = [no_hairnet, ...])
  ↓
_get_primary_violation_type() → no_hairnet (来自 ViolationService)
  ↓
_save_snapshot_if_possible() → violation_type = no_hairnet
  ↓
DetectionRecord (metadata.snapshots[0].violation_type = no_hairnet)
  ↓
DatasetGenerationService → violation_type = no_hairnet (来自 snapshots)
  ↓
数据集 (violation_type = no_hairnet)
```

## ✅ 验收标准

1. **违规检测一致性**：
   - `DetectionApplicationService._analyze_violations` 的结果与 `ViolationService.detect_violations` 的结果一致
   - 快照保存的 `violation_type` 与 `ViolationService` 检测到的违规类型一致

2. **数据集准确性**：
   - 数据集中的 `violation_type` 正确反映实际的违规类型
   - 数据集中的样本正确标记为正负样本

3. **检测逻辑正确性**：
   - 发网检测结果正确转换为违规检测结果
   - 违规检测规则正确应用
   - 快照保存时机正确

## 🚀 下一步行动

1. 实施方案3：在 `ViolationService` 中添加 `no_hairnet` 违规检测规则
2. 修改 `DetectionApplicationService` 使用 `ViolationService` 的结果
3. 验证修复后的检测流程
4. 重新生成数据集并验证准确性



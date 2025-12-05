# 违规检测问题分析

## 问题描述

日志显示有违规情况："❌ 人员 2 (track_id=1) 未检测到发网"，但API返回的违规记录仍然是旧的，`snapshot_path` 为 `null`。

## 问题分析

### 问题1: `has_hairnet=None` 时未判定为违规

**当前逻辑**（`ViolationService._check_no_hairnet`，第293行）：
```python
if has_hairnet is False and hairnet_confidence >= min_hairnet_confidence:
    # 判定为违规
elif has_hairnet is None:
    # 不判定为违规，只记录调试信息
```

**问题**：
- 当发网检测结果为 `None`（未检测到发网）时，系统不判定为违规
- 但实际上，如果检测模型没有检测到发网，说明很可能没有佩戴发网，应该判定为违规

### 问题2: `hairnet_results` 可能不包含所有人员

**当前逻辑**（`DetectionApplicationService._convert_to_domain_format`，第352行）：
```python
if hairnet_info:
    has_hairnet = hairnet_info.get("has_hairnet")
    person_metadata["has_hairnet"] = has_hairnet
```

**问题**：
- 只有当 `hairnet_info` 存在时，才会添加 `has_hairnet` 到 metadata
- 如果某个人员没有对应的 `hairnet_info`（bbox匹配失败或索引不匹配），`has_hairnet` 就不会被添加到 metadata
- 导致 `ViolationService._check_no_hairnet` 中 `metadata.get("has_hairnet")` 返回 `None`，但实际上是缺少字段，而不是检测结果为 `None`

### 问题3: `_analyze_violations` 逻辑与 `ViolationService` 不一致

**当前逻辑**（`DetectionApplicationService._analyze_violations`，第180行）：
```python
if has_hairnet is False and hairnet_confidence > 0.5:
    violations.append({"type": "no_hairnet", ...})
elif has_hairnet is None:
    # 不判定为违规，只记录调试信息
```

**问题**：
- `_analyze_violations` 和 `ViolationService._check_no_hairnet` 的逻辑一致，都要求 `has_hairnet is False`
- 但日志显示 `has_hairnet=None` 的情况更多，这种情况下应该也判定为违规

## 解决方案

### 方案1: 将 `has_hairnet=None` 也判定为违规（推荐）

**修改 `ViolationService._check_no_hairnet`**：
```python
# 如果 has_hairnet 为 None（未检测到发网），也判定为违规
if has_hairnet is False or has_hairnet is None:
    if hairnet_confidence >= min_hairnet_confidence or has_hairnet is None:
        # 判定为违规
```

**修改 `DetectionApplicationService._analyze_violations`**：
```python
# 如果 has_hairnet 为 None 或 False，都判定为违规
if (has_hairnet is False or has_hairnet is None) and hairnet_confidence > 0.5:
    violations.append({"type": "no_hairnet", ...})
```

### 方案2: 确保所有人员都有发网检测结果

**修改 `DetectionApplicationService._convert_to_domain_format`**：
```python
# 确保所有人员都有 has_hairnet 字段
if hairnet_info:
    has_hairnet = hairnet_info.get("has_hairnet")
    person_metadata["has_hairnet"] = has_hairnet
else:
    # 如果没有发网检测结果，默认判定为未佩戴
    person_metadata["has_hairnet"] = False
    person_metadata["hairnet_confidence"] = 0.0
```

## 推荐方案

**采用方案1+方案2的组合**：
1. 确保所有人员都有 `has_hairnet` 字段（如果没有匹配到发网检测结果，默认为 `False`）
2. 将 `has_hairnet=None` 也判定为违规（但置信度要求可能不同）

这样可以确保：
- 所有人员都有明确的发网状态
- 未检测到发网的情况也会被判定为违规
- 减少误判（因为置信度要求）

# 重复测试检测报告

生成时间: 2025-09-05 16:48:16

## 总体统计

- 测试文件总数: 16
- 测试函数总数: 130
- 疑似重复测试对: 7

## 重复测试详情

### 1. 相似度: 88.0%

**测试1:** `test_detector.py:33` - `test_init`
**测试2:** `test_motion_analyzer.py:23` - `test_init`

**描述1:** 测试初始化

**描述2:** 测试初始化

**共同关键词:** assertEqual, self, 测试初始化

---

### 2. 相似度: 87.1%

**测试1:** `test_data_manager.py:44` - `test_init`
**测试2:** `test_detector.py:33` - `test_init`

**描述1:** 测试初始化

**描述2:** 测试初始化

**共同关键词:** assertEqual, assertIsNotNone, self, 测试初始化

---

### 3. 相似度: 81.2%

**测试1:** `test_data_manager.py:44` - `test_init`
**测试2:** `test_motion_analyzer.py:23` - `test_init`

**描述1:** 测试初始化

**描述2:** 测试初始化

**共同关键词:** assertEqual, self, 测试初始化

---

### 4. 相似度: 78.6%

**测试1:** `test_hairnet_detector.py:164` - `test_confidence_threshold`
**测试2:** `test_detector.py:140` - `test_confidence_threshold`

**描述1:** 测试置信度阈值

**描述2:** 测试置信度阈值

**共同关键词:** assertGreater, assertLess, self, 测试置信度阈值

---

### 5. 相似度: 74.0%

**测试1:** `test_detector.py:33` - `test_init`
**测试2:** `test_pose_detector.py:63` - `test_init`

**描述1:** 测试初始化

**描述2:** 测试初始化

**共同关键词:** assertIsNotNone, self, 测试初始化

---

### 6. 相似度: 71.9%

**测试1:** `test_data_manager.py:44` - `test_init`
**测试2:** `test_pose_detector.py:63` - `test_init`

**描述1:** 测试初始化

**描述2:** 测试初始化

**共同关键词:** assertIsNotNone, self, 测试初始化

---

### 7. 相似度: 70.5%

**测试1:** `test_pose_detector.py:63` - `test_init`
**测试2:** `test_motion_analyzer.py:23` - `test_init`

**描述1:** 测试初始化

**描述2:** 测试初始化

**共同关键词:** self, 测试初始化

---


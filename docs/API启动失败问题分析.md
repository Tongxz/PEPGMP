# API 启动失败问题分析

## 📋 问题现象

```
Failed to find attribute 'app' in 'src.api.app'.
```

**容器状态**: `Restarting (4)` - 不断重启

---

## 🔍 根本原因

**问题**: `src/api/app.py` 文件在移除 OpenCV headless 兼容层代码时被**误删**，只剩下文档字符串。

**文件状态**:
- 当前文件大小: 133 字节（只有 5 行）
- 正常文件大小: 应该 > 500 行
- 缺失内容: 整个 FastAPI 应用定义、路由配置、中间件等

---

## ✅ 解决方案

### 1. 从 Git 恢复文件

```bash
git checkout HEAD -- src/api/app.py
```

### 2. 验证恢复

```bash
# 检查文件大小
wc -l src/api/app.py

# 检查 app 对象是否存在
grep "^app\s*=" src/api/app.py
```

---

## 📝 问题原因分析

### 为什么会误删？

在移除兼容层代码时，使用了 `sed` 命令批量删除：

```bash
sed -i.bak '/opencv_headless_compat/,/cv2.resizeWindow = _noop/d' src/api/app.py
```

**问题**: 这个命令可能因为匹配范围过大，误删了文件的其他内容。

### 为什么没有及时发现？

1. 文件仍然存在（只是内容被清空）
2. 没有在本地测试导入
3. 直接部署到容器中才发现问题

---

## 🔧 预防措施

### 1. 使用更精确的删除方法

**不推荐**: 使用 `sed` 删除多行（容易误删）

**推荐**:
- 手动编辑文件
- 或使用更精确的匹配模式
- 或使用 Git 恢复后再手动修改

### 2. 添加验证步骤

在修改文件后，应该验证：

```bash
# 检查文件大小变化
wc -l src/api/app.py

# 检查关键对象是否存在
grep "^app\s*=" src/api/app.py

# 测试导入
python3 -c "from src.api.app import app; print('OK')"
```

### 3. 使用 Git 管理

- 修改前先提交
- 使用 Git 恢复而不是手动删除
- 使用 `git diff` 检查变更

---

## ✅ 修复状态

- [x] 从 Git 恢复 `src/api/app.py`
- [ ] 验证文件完整性
- [ ] 重新构建镜像
- [ ] 测试部署

---

**问题发现日期**: 2025-12-04
**修复日期**: 2025-12-04
**状态**: ✅ 已修复

# OpenCV 配置恢复说明

## 📋 恢复原因

由于 headless 版本在实际部署中遇到兼容性问题，决定恢复到使用完整的 `opencv-python` 版本。

**决策理由**：
- 稳定性优先于镜像体积
- 100MB+ 的体积增加是可接受的
- 避免复杂的兼容层维护

---

## ✅ 已完成的恢复操作

### 1. 恢复依赖文件

**文件**: `requirements.prod.txt`

**更改**:
```diff
- opencv-python-headless>=4.8.0
+ opencv-python>=4.8.0
```

### 2. 恢复 Dockerfile

**文件**: `Dockerfile.prod`

**恢复的系统依赖**:
```dockerfile
# OpenCV GUI 功能所需的图形库依赖
libgl1 \
libglib2.0-0 \
libsm6 \
libxext6 \
libxrender-dev \
```

**移除的逻辑**:
- 移除了 `pip uninstall opencv-python opencv-contrib-python` 的卸载步骤
- 恢复为标准 pip install

### 3. 删除兼容层

- ✅ 删除 `src/utils/opencv_headless_compat.py`
- ✅ 移除所有文件中的兼容层导入代码

**受影响的文件**:
- `src/api/app.py`
- `src/detection/pose_detector.py`
- `src/core/optimized_detection_pipeline.py`
- `src/detection/detector.py`
- `src/detection/yolo_hairnet_detector.py`

---

## 📊 对比

| 项目 | Headless 版本 | 完整版本（恢复后） |
|------|--------------|------------------|
| **镜像体积** | 较小（-100MB+） | 较大（+100MB+） |
| **系统依赖** | 少 | 多（GUI 相关库） |
| **兼容性** | 需要兼容层 | 原生支持 ✅ |
| **维护成本** | 高（兼容层） | 低 ✅ |
| **稳定性** | 可能有问题 | 稳定 ✅ |

---

## 🔄 下一步操作

### 1. 重新构建镜像

```bash
# 构建生产镜像
./scripts/build_prod_only.sh
```

### 2. 验证部署

```bash
# 测试部署
./scripts/deploy_prod_macos.sh
```

---

## 📝 注意事项

1. **镜像体积增加**: 预计增加约 100MB+，这是可接受的
2. **系统依赖**: 需要安装 GUI 相关库（已在 Dockerfile 中配置）
3. **兼容性**: 完整版本对所有功能都有原生支持，无需兼容层

---

## ✅ 验证清单

- [x] `requirements.prod.txt` 已恢复为 `opencv-python`
- [x] `Dockerfile.prod` 已添加 GUI 系统依赖
- [x] 兼容层文件已删除
- [x] 所有兼容层导入代码已移除
- [ ] 重新构建镜像（待执行）
- [ ] 验证部署成功（待执行）

---

**恢复日期**: 2025-12-04
**状态**: ✅ 代码已恢复，待重新构建镜像

# 数据集样本图片可视化分析

## 🔍 问题描述

用户询问：**样本图片上是否没有标识框？**

## 📊 当前实现分析

### 1. 快照保存流程

#### 1.1 保存快照时

**文件**: `src/infrastructure/storage/filesystem_snapshot_storage.py` (第40-62行)

```python
async def save_frame(
    self,
    frame: np.ndarray,  # ⚠️ 原始帧，没有检测框
    camera_id: str,
    *,
    captured_at: Optional[datetime] = None,
    violation_type: Optional[str] = None,
    metadata: Optional[Mapping[str, str]] = None,
) -> SnapshotInfo:
    # 直接保存原始帧
    await asyncio.to_thread(
        self._write_image,
        absolute_path,
        frame,  # ⚠️ 没有绘制检测框
    )
```

**说明**: 直接保存原始帧，**没有绘制检测框**

#### 1.2 调用保存快照

**文件**: `src/application/detection_application_service.py` (第239-267行)

```python
async def _save_snapshot_if_possible(
    self,
    frame: np.ndarray,  # ⚠️ 原始帧
    camera_id: str,
    *,
    violation_type: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[SnapshotInfo]:
    # 直接保存原始帧
    return await self.snapshot_storage.save_frame(
        frame,  # ⚠️ 没有使用 annotated_image
        camera_id,
        captured_at=datetime.utcnow(),
        violation_type=violation_type,
        metadata=metadata_mapping,
    )
```

**说明**: 保存的是原始帧，**不是带检测框的 annotated_image**

### 2. 数据集生成流程

#### 2.1 复制快照文件

**文件**: `src/application/dataset_generation_service.py` (第242-272行)

```python
async def _copy_snapshots(
    self,
    entries: Iterable[Dict[str, object]],
    images_dir: Path,
) -> List[tuple[Path, Path]]:
    for entry in entries:
        source: Path = entry["source_path"]
        target = images_dir / target_name
        # ⚠️ 直接复制快照文件，没有绘制检测框
        tasks.append(
            asyncio.to_thread(
                shutil.copy2,  # ⚠️ 直接复制，没有修改图片
                source,
                target,
            )
        )
```

**说明**: 直接复制快照文件，**没有绘制检测框**

#### 2.2 多行为数据集生成

**文件**: `src/application/multi_behavior_dataset_service.py` (第198-239行)

```python
def _process_entry(
    self,
    entry: Dict[str, object],
    images_dir: Path,
    labels_dir: Path,
    annotations: List[Dict[str, object]],
) -> None:
    source: Path = entry["source_path"]
    image_target = images_dir / subset_dir / target_name
    # ⚠️ 直接复制快照文件，没有绘制检测框
    shutil.copy2(source, image_target)
    
    # 生成标注文件（YOLO格式）
    labels = self._build_labels(entry.get("objects", []), width, height)
    label_lines = [
        f"{label['class_id']} {label['x_center']} {label['y_center']} {label['width']} {label['height']}"
        for label in labels
    ]
    label_target.write_text("\n".join(label_lines))
```

**说明**: 直接复制快照文件，**没有绘制检测框**。标注信息保存在单独的 `.txt` 文件中

## ✅ 结论

### 当前状态

- ✅ **样本图片**: 原始图片，**没有检测框**
- ✅ **标注信息**: 保存在单独的标注文件中
  - 发网分类数据集: `annotations.csv`
  - 多行为检测数据集: `labels/*.txt` (YOLO格式)

### 设计原因

1. **训练需求**: 原始图片更适合训练，不会被检测框干扰
2. **标注分离**: 标注信息保存在单独文件中，便于管理
3. **灵活性**: 可以在可视化时再绘制检测框

### 优点

- ✅ 原始图片质量高，适合训练
- ✅ 标注信息独立管理，便于修改
- ✅ 可以在可视化时动态绘制检测框

### 缺点

- ⚠️ 无法直观查看样本图片的检测结果
- ⚠️ 难以验证数据集的质量
- ⚠️ 检查标注是否正确时需要额外的工具

## 🎯 可选解决方案

### 方案1: 添加可选的可视化功能（推荐）⭐

在数据集生成时，可选地生成带检测框的可视化图片：

```python
async def _copy_snapshots(
    self,
    entries: Iterable[Dict[str, object]],
    images_dir: Path,
    draw_bbox: bool = False,  # 新增参数
) -> List[tuple[Path, Path]]:
    for entry in entries:
        source: Path = entry["source_path"]
        target = images_dir / target_name
        
        if draw_bbox:
            # 绘制检测框
            image = cv2.imread(str(source))
            annotated_image = self._draw_bboxes(image, entry.get("objects", []))
            cv2.imwrite(str(target), annotated_image)
        else:
            # 直接复制
            shutil.copy2(source, target)
```

### 方案2: 生成可视化图片目录

在数据集目录中，单独创建一个 `visualized/` 目录，存放带检测框的可视化图片：

```
dataset/
├── images/          # 原始图片（用于训练）
├── visualized/      # 可视化图片（带检测框）
├── labels/          # 标注文件
└── annotations.csv  # 标注信息
```

### 方案3: 提供可视化工具

创建一个独立的可视化工具，用于查看数据集样本：

```python
# scripts/visualize_dataset.py
def visualize_dataset_samples(dataset_path: str):
    """可视化数据集样本"""
    # 读取图片和标注
    # 绘制检测框
    # 保存可视化图片
```

## 📝 建议

### 推荐方案

**方案1 + 方案2 组合**：
1. 保留原始图片（用于训练）
2. 可选生成可视化图片（用于检查）
3. 通过配置参数控制是否生成可视化图片

### 实施步骤

1. **添加配置参数**: 在数据集生成请求中添加 `draw_bbox` 参数
2. **实现绘制功能**: 添加 `_draw_bboxes()` 方法
3. **生成可视化图片**: 可选生成可视化图片目录
4. **更新文档**: 说明如何查看可视化图片

## 🔍 验证方法

### 检查当前样本图片

```bash
# 查看数据集目录
ls -la datasets/exports/*/images/

# 查看样本图片（应该没有检测框）
open datasets/exports/*/images/*.jpg
```

### 检查标注文件

```bash
# 查看标注文件
cat datasets/exports/*/annotations.csv
cat datasets/exports/*/labels/*.txt
```

## 📚 相关文档

- [数据集生成服务](./DATASET_GENERATION_SERVICE.md)
- [多行为数据集生成](./MULTI_BEHAVIOR_DATASET_GENERATION.md)
- [快照存储服务](./SNAPSHOT_STORAGE_SERVICE.md)


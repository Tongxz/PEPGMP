# 系统完善改进计划

## 📋 用户需求

1. **前端配置视频流的检测帧率**
2. **前端配置实时视频是否逐帧**
3. **检查所有记录时间是否统一**
4. **完善系统细节开发**

## 🔍 当前状态分析

### 1. 视频流配置现状

**当前实现**:
- 检测帧率通过环境变量 `VIDEO_STREAM_INTERVAL` 配置（默认3帧）
- 视频流推送间隔通过 `stream_interval` 配置
- 检测间隔通过 `log_interval` 配置
- **问题**: 无法在前端动态配置，只能通过环境变量或命令行参数

**配置位置**:
- `src/application/detection_loop_service.py`: `DetectionLoopConfig`
- `src/application/detection_initializer.py`: 从环境变量读取
- `config/unified_params.yaml`: 运行时配置

### 2. 时间记录现状

**当前实现**:
- 工作流运行时间: 已修复，使用UTC时间并添加时区信息
- 数据库模型: 部分使用 `func.now()`，部分使用 `datetime.utcnow()`
- **问题**: 时间记录不统一，部分使用UTC，部分使用数据库服务器时间

**时间使用情况**:
- `src/database/dao.py`: 使用 `datetime.utcnow()` ✅
- `src/database/models.py`: 使用 `func.now()` ⚠️
- `src/database/init_db.py`: 使用 `datetime.utcnow()` ✅

### 3. 系统细节问题

**发现的问题**:
- 缺少前端配置界面
- 缺少API接口支持动态配置
- 时间记录不统一
- 配置管理不完善

## ✅ 改进方案

### 方案1: 前端配置视频流检测帧率和逐帧模式

#### 1.1 添加API接口

**文件**: `src/api/routers/video_stream.py`

**新增接口**:
```python
@router.post("/config/{camera_id}", summary="配置视频流参数")
async def update_video_stream_config(
    camera_id: str,
    config: VideoStreamConfigRequest,
):
    """更新视频流配置"""
    # 保存配置到数据库或Redis
    # 通知检测进程更新配置
    pass

@router.get("/config/{camera_id}", summary="获取视频流配置")
async def get_video_stream_config(camera_id: str):
    """获取当前视频流配置"""
    pass
```

#### 1.2 前端添加配置界面

**文件**: `frontend/src/components/VideoStreamCard.vue`

**新增功能**:
- 检测帧率配置滑块（1-30帧）
- 逐帧模式开关
- 配置保存按钮
- 实时应用配置

#### 1.3 支持动态配置更新

**文件**: `src/application/detection_loop_service.py`

**修改内容**:
- 支持运行时更新 `stream_interval`
- 支持运行时更新 `log_interval`
- 支持逐帧模式（`stream_interval=1`）

### 方案2: 统一所有记录时间

#### 2.1 检查所有时间记录

**需要检查的文件**:
- `src/database/models.py`: 所有模型的 `created_at`、`updated_at`
- `src/database/dao.py`: 所有DAO方法中的时间操作
- `src/infrastructure/repositories/*.py`: 所有仓储实现中的时间操作

#### 2.2 统一使用UTC时间

**修改策略**:
- 所有 `func.now()` 改为使用 `datetime.utcnow()`
- 所有时间序列化添加时区信息
- 确保前端正确显示本地时间

### 方案3: 完善系统细节

#### 3.1 配置管理完善

- 添加配置验证
- 添加配置历史记录
- 添加配置回滚功能

#### 3.2 错误处理完善

- 统一错误处理
- 添加错误恢复机制
- 完善错误日志

#### 3.3 性能监控完善

- 添加性能指标收集
- 添加性能告警
- 添加性能优化建议

## 🎯 实施优先级

### 高优先级（立即实施）

1. ✅ **统一所有记录时间** - 影响数据一致性
2. ✅ **前端配置视频流检测帧率** - 用户直接需求
3. ✅ **前端配置逐帧模式** - 用户直接需求

### 中优先级（后续实施）

4. **配置管理完善** - 提升系统可维护性
5. **错误处理完善** - 提升系统稳定性
6. **性能监控完善** - 提升系统可观测性

## 📝 实施步骤

### 步骤1: 统一所有记录时间

1. 检查所有时间记录位置
2. 统一使用UTC时间
3. 添加时区信息到序列化
4. 测试验证

### 步骤2: 添加视频流配置API

1. 创建配置模型
2. 添加API接口
3. 实现配置存储
4. 实现配置更新通知

### 步骤3: 前端添加配置界面

1. 添加配置组件
2. 连接API接口
3. 实现实时更新
4. 测试验证

### 步骤4: 支持动态配置更新

1. 修改检测循环服务
2. 实现配置热更新
3. 测试验证

## 🔍 验证方法

### 1. 时间统一验证

```python
# 检查所有时间记录
python scripts/check_timestamps.py
```

### 2. 配置功能验证

1. 前端配置检测帧率
2. 观察视频流变化
3. 验证配置生效

### 3. 系统细节验证

1. 检查错误处理
2. 检查性能监控
3. 检查配置管理


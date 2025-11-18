# 摄像头状态字段分析

## 状态字段说明

### 1. 配置状态（`status` 字段）

**存储位置**：数据库 `cameras` 表的 `status` 列（VARCHAR(20)）

**字段含义**：摄像头是否被激活（是否允许启动检测）

**可能的值**：
- `active`：激活 - 允许启动检测
- `inactive`：停用 - 禁止启动检测
- `maintenance`：维护中 - 暂时不可用
- `error`：错误 - 配置或硬件错误

**使用场景**：
- 前端列表中的"配置状态"列显示的就是这个字段
- 当 `status = inactive` 时，即使点击"启动"按钮，也会被阻止
- 通过"激活"/"停用"按钮可以修改这个状态

**对应关系**：
- 前端列表中的"配置状态" = 数据库 `status` 字段
- "激活"按钮 → 设置 `status = 'active'`
- "停用"按钮 → 设置 `status = 'inactive'`

### 2. 运行状态（`runtime_status`）

**存储位置**：**不在数据库中存储**，通过进程管理器实时查询

**字段含义**：检测进程是否正在运行

**数据结构**：
```typescript
{
  running: boolean,  // 是否运行中
  pid: number,      // 进程ID
  log?: string      // 日志内容（可选）
}
```

**获取方式**：
1. **实时查询**：通过 `scheduler.get_status(camera_id)` 查询
2. **批量查询**：通过 `scheduler.get_batch_status(camera_ids)` 批量查询
3. **WebSocket推送**：前端通过WebSocket接收实时状态更新
4. **轮询**：前端每5秒轮询一次（当WebSocket未连接时）

**使用场景**：
- 前端列表中的"运行状态"列显示的就是这个字段
- 显示检测进程是否正在运行（🟢 运行中 / ⚪ 已停止）
- 显示进程ID（PID）

### 3. 状态关系

```
配置状态（status）         运行状态（runtime_status）
─────────────────         ──────────────────────
active（激活）    →        可以启动检测进程
                         ├─ running: true  （进程运行中）
                         └─ running: false （进程已停止）

inactive（停用）  →        禁止启动检测进程
                         └─ running: false （无法启动）

maintenance（维护）→       禁止启动检测进程
                         └─ running: false （无法启动）

error（错误）     →        禁止启动检测进程
                         └─ running: false （无法启动）
```

### 4. 前端显示

**配置状态列**：
- 显示：`active` → "●激活"（绿色）
- 显示：`inactive` → "○停用"（灰色）

**运行状态列**：
- 如果 `status = inactive`：显示 "🚫 禁止启动（请先激活）"
- 如果 `status = active` 且 `runtime_status.running = true`：显示 "🟢 运行中 PID: xxx"
- 如果 `status = active` 且 `runtime_status.running = false`：显示 "⚪ 已停止"

### 5. 数据库表结构

```sql
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),              -- 摄像头位置（可选）
    status VARCHAR(20) DEFAULT 'inactive',  -- 配置状态（是否允许启动检测）
    camera_type VARCHAR(50) DEFAULT 'fixed', -- 摄像头类型
    resolution JSONB,
    fps INTEGER,
    region_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,  -- source 等字段存储在 metadata 中
    stream_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
```

### 6. 总结

- **配置状态（status）**：存储在数据库中，表示摄像头是否被激活（是否允许启动检测）
- **运行状态（runtime_status）**：不在数据库中存储，通过进程管理器实时查询，表示检测进程是否正在运行
- **两者关系**：`status = active` 是启动检测的前提条件，但 `status = active` 不意味着进程一定在运行


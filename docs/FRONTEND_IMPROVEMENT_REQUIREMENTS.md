# 前端功能完善需求清单

## 📋 目录

1. [数据接口完善需求](#数据接口完善需求)
2. [功能完善需求](#功能完善需求)
3. [前端代码修复需求](#前端代码修复需求)
4. [优先级分类](#优先级分类)

---

## 数据接口完善需求

### 🔴 高优先级 - 必须立即实现

#### 1. 智能检测实时统计接口

**问题**: 首页智能检测面板使用假数据

**需要的接口**:
```typescript
GET /statistics/detection-realtime
```

**响应数据结构**:
```typescript
interface DetectionRealtimeStats {
  // 处理统计
  processing_efficiency: number;      // 处理效率 (0-100)
  avg_fps: number;                    // 平均FPS
  processed_frames: number;           // 已处理帧数
  skipped_frames: number;             // 已跳过帧数
  
  // 场景分布
  scene_distribution: {
    static: number;                   // 静态场景数
    dynamic: number;                  // 动态场景数
    critical: number;                 // 关键场景数
  };
  
  // 性能监控
  performance: {
    cpu_usage: number;                // CPU使用率 (0-100)
    memory_usage: number;             // 内存使用率 (0-100)
    gpu_usage: number;                // GPU使用率 (0-100)
  };
  
  // 连接状态
  connection_status: {
    connected: boolean;                // 是否连接
    active_cameras: number;           // 活跃摄像头数
  };
  
  timestamp: string;                   // 时间戳
}
```

**使用场景**: 
- 首页 `IntelligentDetectionPanel` 组件
- 实时监控页面（可选）

**实现建议**:
- 可以复用现有的 `/statistics/realtime` 接口，扩展返回数据
- 或创建新接口专门用于检测面板
- 建议支持 WebSocket 实时推送更新

---

#### 2. 摄像头列表接口（用于下拉选项）

**问题**: 检测记录页面摄像头选项硬编码

**现有接口**: `GET /cameras` 已存在

**问题分析**:
- 接口已存在，但前端未使用
- 需要在前端代码中调用此接口获取摄像头列表

**前端修复需求**:
- 在 `DetectionRecords.vue` 中调用 `cameraStore.fetchCameras()`
- 动态生成摄像头选项

**接口使用**:
```typescript
// 现有接口，无需新增
GET /cameras
```

---

### 🟡 中优先级 - 建议实现

#### 3. 告警历史分页接口

**问题**: 告警中心缺少分页功能

**需要的接口增强**:
```typescript
GET /alerts/history-db
```

**需要支持的参数**:
```typescript
{
  limit?: number;        // 每页数量 (默认: 100)
  offset?: number;        // 偏移量 (默认: 0)
  page?: number;          // 页码 (可选，与offset二选一)
  camera_id?: string;     // 摄像头ID筛选
  alert_type?: string;    // 告警类型筛选
  start_time?: string;    // 开始时间
  end_time?: string;      // 结束时间
}
```

**响应数据结构增强**:
```typescript
{
  items: AlertHistoryItem[];
  total: number;         // 总记录数
  limit: number;         // 每页数量
  offset: number;        // 当前偏移量
  page?: number;         // 当前页码（如果使用page参数）
  total_pages?: number;  // 总页数（可选）
}
```

**使用场景**: 
- 告警中心历史告警表格

---

#### 4. 告警历史排序接口

**问题**: 告警中心排序仅前端实现

**需要的接口增强**:
```typescript
GET /alerts/history-db
```

**需要支持的参数**:
```typescript
{
  sort_by?: string;      // 排序字段: 'timestamp', 'camera_id', 'alert_type'
  sort_order?: 'asc' | 'desc';  // 排序方向 (默认: 'desc')
  // ... 其他现有参数
}
```

**使用场景**: 
- 告警中心历史告警表格排序

---

#### 5. 告警规则分页接口

**问题**: 告警规则列表可能也需要分页

**需要的接口增强**:
```typescript
GET /alerts/rules
```

**需要支持的参数**:
```typescript
{
  limit?: number;        // 每页数量
  offset?: number;       // 偏移量
  camera_id?: string;    // 摄像头ID筛选
  enabled?: boolean;     // 启用状态筛选
}
```

**响应数据结构增强**:
```typescript
{
  items: AlertRuleItem[];
  total: number;         // 总记录数
  limit: number;
  offset: number;
}
```

---

### 🟢 低优先级 - 可选实现

#### 6. 检测记录详情接口

**问题**: 检测记录详情使用列表数据，无独立详情接口

**需要的接口** (可选):
```typescript
GET /records/detection-records/{record_id}
```

**响应数据结构**:
```typescript
interface DetectionRecordDetail {
  id: string;
  camera_id: string;
  timestamp: string;
  frame_id: number;
  person_count: number;
  hairnet_violations: number;
  handwash_events: number;
  sanitize_events: number;
  processing_time: number;
  fps: number;
  confidence: number;
  objects: DetectedObject[];
  metadata: Record<string, any>;
  // 可能包含更多详细信息
}
```

**使用场景**: 
- 检测记录详情弹窗（当前使用列表数据，可能不完整）

---

#### 7. 违规记录详情接口

**问题**: 违规记录详情使用列表数据

**需要的接口** (可选):
```typescript
GET /records/violations/{violation_id}
```

**响应数据结构**:
```typescript
interface ViolationDetail {
  id: string;
  camera_id: string;
  timestamp: string;
  violation_type: string;
  status: string;
  confidence: number;
  track_id: string;
  // 可能包含更多详细信息，如截图、视频片段等
}
```

---

#### 8. 统计数据缓存接口

**问题**: 统计数据可能需要缓存以提高性能

**需要的接口** (可选):
```typescript
GET /statistics/cache/clear
POST /statistics/cache/warmup
```

**使用场景**: 
- 优化统计页面加载性能
- 预加载常用统计数据

---

## 功能完善需求

### 🔴 高优先级 - 必须立即修复

#### 1. 首页智能检测面板 - 使用真实数据

**文件**: `frontend/src/components/IntelligentDetectionPanelSimple.vue`

**当前问题**:
- 所有数据都是硬编码的假数据
- 无法反映真实系统状态

**修复方案**:
1. 调用新的 `/statistics/detection-realtime` 接口
2. 或从 WebSocket 状态更新中获取数据
3. 添加加载状态和错误处理

**需要修改的代码**:
```typescript
// 需要添加
import { statisticsApi } from '@/api/statistics'
import { useWebSocket } from '@/composables/useWebSocket'

// 需要替换硬编码数据
const stats = ref<DetectionRealtimeStats | null>(null)
const loading = ref(false)

// 需要添加数据获取逻辑
async function loadRealtimeStats() {
  loading.value = true
  try {
    stats.value = await statisticsApi.getDetectionRealtime()
  } catch (error) {
    console.error('获取实时统计失败:', error)
  } finally {
    loading.value = false
  }
}
```

---

#### 2. 检测记录页面 - 动态获取摄像头列表

**文件**: `frontend/src/views/DetectionRecords.vue`

**当前问题**:
- 摄像头选项硬编码（第237-241行）
- 无法动态获取实际摄像头列表

**修复方案**:
1. 在 `onMounted` 中调用 `cameraStore.fetchCameras()`
2. 动态生成摄像头选项
3. 移除硬编码的选项

**需要修改的代码**:
```typescript
// 需要添加
import { useCameraStore } from '@/stores/camera'

const cameraStore = useCameraStore()

// 需要修改
const cameraOptions = computed(() => {
  const options = [
    { label: '全部摄像头', value: 'all' }
  ]
  cameraStore.cameras.forEach(cam => {
    options.push({
      label: `${cam.name || cam.id} (${cam.id})`,
      value: cam.id
    })
  })
  return options
})

// 在 onMounted 中
onMounted(async () => {
  await cameraStore.fetchCameras()
  loadRecords()
  loadViolations()
})
```

---

### 🟡 中优先级 - 建议实现

#### 3. 告警中心 - 添加分页功能

**文件**: `frontend/src/views/Alerts.vue`

**当前问题**:
- 告警历史表格无分页功能
- 可能数据量大时性能问题

**修复方案**:
1. 后端接口支持分页参数（见接口需求 #3）
2. 前端添加分页组件
3. 实现分页逻辑

**需要修改的代码**:
```typescript
// 需要添加分页状态
const historyPagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 需要修改查询逻辑
async function fetchHistory() {
  loading.history = true
  try {
    const res = await alertsApi.getHistory({
      limit: historyPagination.value.pageSize,
      offset: (historyPagination.value.page - 1) * historyPagination.value.pageSize,
      camera_id: filters.cameraId || undefined,
      alert_type: filters.alertType || undefined,
    })
    history.items = res.items
    historyPagination.value.total = res.total
  } catch (e: any) {
    message.error(e?.message || '获取历史告警失败')
  } finally {
    loading.history = false
  }
}
```

---

#### 4. 告警中心 - 后端排序支持

**文件**: `frontend/src/views/Alerts.vue`

**当前问题**:
- 排序仅前端实现（第313-316行）
- 大数据量时性能问题

**修复方案**:
1. 后端接口支持排序参数（见接口需求 #4）
2. 前端传递排序参数
3. 移除前端排序逻辑

---

#### 5. 告警规则 - 添加分页功能

**文件**: `frontend/src/views/Alerts.vue`

**当前问题**:
- 告警规则列表无分页功能

**修复方案**:
1. 后端接口支持分页参数（见接口需求 #5）
2. 前端添加分页组件

---

### 🟢 低优先级 - 可选实现

#### 6. 检测记录 - 添加更多筛选条件

**文件**: `frontend/src/views/DetectionRecords.vue`

**建议添加的筛选**:
- 违规类型筛选（已有）
- 置信度范围筛选
- 处理时间范围筛选
- 对象数量筛选

---

#### 7. 统计分析 - 添加更多图表类型

**文件**: `frontend/src/views/Statistics.vue`

**建议添加的图表**:
- 时间序列折线图（按小时/天）
- 热力图（摄像头 × 时间）
- 散点图（置信度分布）
- 雷达图（多维度对比）

---

#### 8. 数据自动刷新机制

**涉及文件**: 多个页面

**建议实现**:
- 为需要实时数据的页面添加自动刷新
- 可配置刷新间隔
- 支持暂停/继续自动刷新

**需要添加自动刷新的页面**:
- 首页（智能检测面板）
- 实时监控（摄像头状态）
- 统计分析（实时统计）
- 告警中心（新告警）

---

## 前端代码修复需求

### 🔴 高优先级

#### 1. 修复 IntelligentDetectionPanelSimple.vue

**文件**: `frontend/src/components/IntelligentDetectionPanelSimple.vue`

**需要修改**:
- 移除所有硬编码数据
- 添加接口调用逻辑
- 添加加载状态
- 添加错误处理

**代码行数**: 约 95 行，需要重写大部分逻辑

---

#### 2. 修复 DetectionRecords.vue 摄像头选项

**文件**: `frontend/src/views/DetectionRecords.vue`

**需要修改**:
- 第237-241行：移除硬编码选项
- 添加 `cameraStore` 导入和使用
- 在 `onMounted` 中获取摄像头列表

**代码行数**: 约 10-15 行修改

---

### 🟡 中优先级

#### 3. 增强 Alerts.vue 分页功能

**文件**: `frontend/src/views/Alerts.vue`

**需要修改**:
- 添加分页状态管理
- 修改 `fetchHistory` 和 `fetchRules` 方法
- 添加分页组件到表格

**代码行数**: 约 30-50 行修改

---

#### 4. 增强 Alerts.vue 排序功能

**文件**: `frontend/src/views/Alerts.vue`

**需要修改**:
- 修改 `fetchHistory` 方法支持排序参数
- 移除前端排序逻辑（第313-316行）
- 添加排序UI控件

**代码行数**: 约 20-30 行修改

---

## 优先级分类

### 🔴 P0 - 紧急（必须立即修复）

1. ✅ **智能检测实时统计接口** - `GET /statistics/detection-realtime`
2. ✅ **首页智能检测面板使用真实数据** - 修复 `IntelligentDetectionPanelSimple.vue`
3. ✅ **检测记录页面动态获取摄像头列表** - 修复 `DetectionRecords.vue`

**预计工作量**: 
- 后端接口: 1-2 天
- 前端修复: 1 天
- **总计**: 2-3 天

---

### 🟡 P1 - 重要（建议尽快实现）

4. ✅ **告警历史分页接口** - 增强 `GET /alerts/history-db`
5. ✅ **告警历史排序接口** - 增强 `GET /alerts/history-db`
6. ✅ **告警规则分页接口** - 增强 `GET /alerts/rules`
7. ✅ **告警中心添加分页功能** - 修复 `Alerts.vue`
8. ✅ **告警中心后端排序支持** - 修复 `Alerts.vue`

**预计工作量**: 
- 后端接口增强: 1-2 天
- 前端修复: 1-2 天
- **总计**: 2-4 天

---

### 🟢 P2 - 一般（可选实现）

9. ⚪ **检测记录详情接口** - `GET /records/detection-records/{record_id}`
10. ⚪ **违规记录详情接口** - `GET /records/violations/{violation_id}`
11. ⚪ **统计数据缓存接口** - 缓存相关接口
12. ⚪ **检测记录添加更多筛选条件** - 前端增强
13. ⚪ **统计分析添加更多图表类型** - 前端增强
14. ⚪ **数据自动刷新机制** - 前端增强

**预计工作量**: 
- 根据具体需求确定
- **总计**: 5-10 天（如果全部实现）

---

## 实施建议

### 第一阶段（P0 - 紧急）

**目标**: 修复假数据问题，确保所有页面显示真实数据

**任务**:
1. 后端实现 `GET /statistics/detection-realtime` 接口
2. 前端修复 `IntelligentDetectionPanelSimple.vue`
3. 前端修复 `DetectionRecords.vue` 摄像头选项

**时间**: 2-3 天

---

### 第二阶段（P1 - 重要）

**目标**: 完善告警中心功能，提升用户体验

**任务**:
1. 后端增强告警相关接口（分页、排序）
2. 前端实现告警中心分页和排序功能

**时间**: 2-4 天

---

### 第三阶段（P2 - 可选）

**目标**: 功能增强和性能优化

**任务**:
1. 根据实际需求选择实现
2. 性能优化
3. 用户体验提升

**时间**: 根据需求确定

---

## 接口设计规范

### 统一响应格式

所有接口应遵循统一的响应格式：

```typescript
// 列表接口响应
interface ListResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  page?: number;
  total_pages?: number;
}

// 分页参数
interface PaginationParams {
  limit?: number;
  offset?: number;
  page?: number;
}

// 排序参数
interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// 筛选参数
interface FilterParams {
  camera_id?: string;
  start_time?: string;
  end_time?: string;
  // ... 其他筛选条件
}
```

---

## 总结

### 必须实现的接口（P0）

1. `GET /statistics/detection-realtime` - 智能检测实时统计

### 必须修复的前端代码（P0）

1. `IntelligentDetectionPanelSimple.vue` - 使用真实数据
2. `DetectionRecords.vue` - 动态获取摄像头列表

### 建议实现的接口（P1）

1. `GET /alerts/history-db` - 支持分页和排序
2. `GET /alerts/rules` - 支持分页

### 建议修复的前端代码（P1）

1. `Alerts.vue` - 添加分页和排序功能

---

**文档生成时间**: 2025年
**文档版本**: v1.0.0


# 前端功能详细分析文档

## 📋 目录

1. [项目架构概览](#项目架构概览)
2. [路由与页面结构](#路由与页面结构)
3. [核心功能模块](#核心功能模块)
4. [组件体系](#组件体系)
5. [状态管理](#状态管理)
6. [API 接口层](#api-接口层)
7. [实时通信](#实时通信)
8. [UI/UX 特性](#uiux-特性)

---

## 项目架构概览

### 技术栈
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **UI 组件库**: Naive UI
- **路由**: Vue Router
- **状态管理**: Pinia
- **TypeScript**: 全面使用 TypeScript
- **实时通信**: WebSocket

### 目录结构
```
frontend/src/
├── api/              # API 接口层
├── components/       # 组件库
│   ├── common/      # 通用组件
│   └── MLOps/       # MLOps 专用组件
├── composables/     # 组合式函数
├── layouts/         # 布局组件
├── router/          # 路由配置
├── stores/          # Pinia 状态管理
├── views/           # 页面视图
└── lib/             # 工具库
```

---

## 路由与页面结构

### 路由配置 (`src/router/index.ts`)

系统采用单布局嵌套路由结构，所有页面都在 `MainLayout` 下：

| 路由路径 | 页面名称 | 组件文件 | 功能描述 |
|---------|---------|---------|---------|
| `/` | 首页 | `Home.vue` | 系统概览、健康检查、系统信息 |
| `/camera-config` | 相机配置 | `CameraConfig.vue` | 摄像头管理、添加/编辑/删除 |
| `/region-config` | 区域配置 | `RegionConfig.vue` | 检测区域配置 |
| `/statistics` | 统计分析 | `Statistics.vue` | 数据统计、图表展示 |
| `/detection-records` | 检测记录 | `DetectionRecords.vue` | 检测历史、违规记录查询 |
| `/alerts` | 告警中心 | `Alerts.vue` | 告警历史、规则管理 |
| `/mlops` | MLOps管理 | `MLOpsManagementNew.vue` | 模型管理、数据集、部署、工作流 |
| `/realtime-monitor` | 实时监控 | `RealtimeMonitor.vue` | 多摄像头实时画面监控 |
| `/detection-config` | 检测配置 | `DetectionConfig.vue` | 检测参数配置 |
| `/system-info` | 系统信息 | `SystemInfo.vue` | 系统详细信息展示 |

---

## 核心功能模块

### 1. 首页 (Home.vue)

**功能特性**:
- ✅ 系统健康检查
- ✅ 系统信息获取与展示
- ✅ 智能检测状态面板（`IntelligentDetectionPanel`）
- ✅ 系统状态卡片展示

**主要功能**:
```typescript
// 健康检查
async function onCheckHealth() {
  await systemStore.checkHealth()
}

// 获取系统信息
async function onGetSystemInfo() {
  await systemStore.getSystemInfo()
}
```

**UI 组件**:
- `PageHeader`: 页面头部组件
- `IntelligentDetectionPanel`: 智能检测状态面板
- `DataCard`: 数据卡片组件
- `StatusIndicator`: 状态指示器

---

### 2. 实时监控 (RealtimeMonitor.vue)

**功能特性**:
- ✅ 多摄像头实时视频流展示
- ✅ 网格/单屏布局切换
- ✅ 摄像头选择与过滤
- ✅ 全屏模式
- ✅ 连接状态监控
- ✅ FPS 和延迟显示

**核心实现**:
- 使用 `VideoStreamCard` 组件展示每个摄像头
- WebSocket 实时接收视频帧数据
- Canvas + ImageBitmap 优化渲染性能
- 支持暂停/继续、重连、配置调整

**布局模式**:
- **网格模式**: 可配置列数（2/3/4列），自动排列
- **单屏模式**: 全屏显示单个摄像头

**状态管理**:
```typescript
const layoutMode = ref<'grid' | 'single'>('grid')
const gridColumns = ref(3)
const selectedCameraIds = ref<string[]>([])
```

---

### 3. 检测记录 (DetectionRecords.vue)

**功能特性**:
- ✅ 检测历史记录查询
- ✅ 违规事件记录查询
- ✅ 多维度筛选（摄像头、时间范围、状态、类型）
- ✅ 统计信息展示（总帧数、人数、违规数、平均FPS）
- ✅ 记录详情查看
- ✅ 数据导出（检测记录、违规记录）
- ✅ 违规状态更新

**数据表格列**:
- **检测记录表**: ID、时间、摄像头、帧号、人数、发网违规、FPS
- **违规记录表**: ID、时间、摄像头、违规类型、状态、操作

**主要功能函数**:
```typescript
async function loadRecords()        // 加载检测记录
async function loadViolations()     // 加载违规记录
function viewRecordDetail(record)   // 查看记录详情
async function updateViolationStatus(violation)  // 更新违规状态
async function exportDetectionRecords()  // 导出检测记录
async function exportViolations()   // 导出违规记录
```

---

### 4. 统计分析 (Statistics.vue)

**功能特性**:
- ✅ 实时统计数据展示
- ✅ 历史事件查询
- ✅ 时间范围筛选（1小时/24小时/7天）
- ✅ 事件类型筛选
- ✅ 摄像头筛选
- ✅ 图表数据展示
- ✅ 数据导出

**API 接口** (`src/api/statistics.ts`):
```typescript
statisticsApi.getSummary()           // 获取统计摘要
statisticsApi.getDailyStats()        // 获取每日统计
statisticsApi.getEvents()            // 获取事件列表
statisticsApi.getEventsByTimeRange() // 按时间范围获取事件
statisticsApi.getRealtimeStats()     // 获取实时统计
statisticsApi.getHistory()           // 获取历史事件
statisticsApi.exportData()           // 导出数据
```

**数据展示**:
- 统计卡片（总事件数、各类型事件数）
- 时间线图表
- 事件列表表格

---

### 5. 告警中心 (Alerts.vue)

**功能特性**:
- ✅ 告警历史查询
- ✅ 告警规则管理（CRUD）
- ✅ 多维度筛选（摄像头、告警类型、启用状态）
- ✅ 告警详情查看
- ✅ 规则详情查看
- ✅ 规则启用/禁用

**数据结构**:
```typescript
interface AlertHistoryItem {
  id: number
  rule_id?: number
  camera_id: string
  alert_type: string
  message: string
  details?: any
  notification_sent?: boolean
  notification_channels_used?: string[]
  timestamp: string
}

interface AlertRuleItem {
  id: number
  name: string
  camera_id?: string
  rule_type: string
  conditions: any
  notification_channels?: string[]
  recipients?: string[]
  enabled: boolean
  priority?: string
}
```

**主要功能**:
- `fetchHistory()`: 获取告警历史
- `fetchRules()`: 获取告警规则
- `createRule()`: 创建规则
- `updateRule()`: 更新规则
- `deleteRule()`: 删除规则

---

### 6. MLOps 管理 (MLOpsManagementNew.vue)

**功能特性**:
- ✅ 模型管理（模型注册、版本管理）
- ✅ 数据管理（数据集上传、验证、管理）
- ✅ 模型部署（部署配置、扩缩容、状态监控）
- ✅ 工作流管理（工作流创建、执行、监控）

**标签页结构**:
```vue
<n-tabs type="line" animated>
  <n-tab-pane name="model-registry" tab="模型管理">
    <ModelRegistry />
  </n-tab-pane>
  <n-tab-pane name="datasets" tab="数据管理">
    <DatasetManager />
  </n-tab-pane>
  <n-tab-pane name="deployments" tab="模型部署">
    <ModelDeployment />
  </n-tab-pane>
  <n-tab-pane name="workflows" tab="工作流管理">
    <WorkflowManager />
  </n-tab-pane>
</n-tabs>
```

**子组件**:
- `ModelRegistry.vue`: 模型注册表管理
- `DatasetManager.vue`: 数据集管理（上传、验证、列表）
- `ModelDeployment.vue`: 模型部署管理
- `WorkflowManager.vue`: 工作流管理

---

### 7. 相机配置 (CameraConfig.vue)

**功能特性**:
- ✅ 摄像头列表展示
- ✅ 摄像头添加/编辑/删除
- ✅ 摄像头启用/禁用
- ✅ 摄像头配置管理

---

### 8. 区域配置 (RegionConfig.vue)

**功能特性**:
- ✅ 检测区域配置
- ✅ 区域绘制与管理

---

### 9. 检测配置 (DetectionConfig.vue)

**功能特性**:
- ✅ 检测参数配置
- ✅ 检测规则设置

---

## 组件体系

### 通用组件 (`src/components/common/`)

#### 1. VideoStreamCard.vue
**功能**: 视频流展示卡片

**特性**:
- ✅ WebSocket 实时视频流接收
- ✅ Canvas 渲染优化（使用 ImageBitmap）
- ✅ 连接状态显示（已连接/未连接）
- ✅ FPS 和延迟监控
- ✅ 暂停/继续控制
- ✅ 重连功能
- ✅ 配置对话框（检测帧率、图像质量等）
- ✅ 全屏模式支持

**Props**:
```typescript
interface Props {
  cameraId: string
  cameraName: string
  fullSize?: boolean
}
```

**核心方法**:
```typescript
async function connect()      // 连接 WebSocket
function disconnect()         // 断开连接
function togglePause()        // 暂停/继续
function reconnect()           // 重连
function updateConfig()        // 更新配置
```

#### 2. IntelligentDetectionPanel.vue
**功能**: 智能检测状态面板

**展示内容**:
- 处理效率统计
- 平均 FPS
- 已处理/已跳过帧数
- 场景分布（静态/动态/关键场景）
- 性能监控（CPU/内存/GPU 使用率）

#### 3. PageHeader.vue
**功能**: 页面头部组件

**特性**:
- 标题、副标题、图标
- 操作按钮插槽
- 面包屑导航

#### 4. DataCard.vue
**功能**: 数据卡片容器

#### 5. StatusIndicator.vue
**功能**: 状态指示器组件

---

### MLOps 组件 (`src/components/MLOps/`)

- `ModelRegistry.vue`: 模型注册表
- `DatasetManager.vue`: 数据集管理
- `ModelDeployment.vue`: 模型部署
- `WorkflowManager.vue`: 工作流管理

---

## 状态管理

### Pinia Stores (`src/stores/`)

#### 1. SystemStore (`stores/system.ts`)
**功能**: 系统状态管理

**状态**:
```typescript
interface SystemState {
  health: string | null
  systemInfo: any | null
  loading: boolean
  error: string | null
}
```

**方法**:
- `checkHealth()`: 健康检查
- `getSystemInfo()`: 获取系统信息

#### 2. CameraStore (`stores/camera.ts`)
**功能**: 摄像头状态管理

**状态**:
- 摄像头列表
- 当前选中的摄像头
- 加载状态
- 错误信息

#### 3. RegionStore (`stores/region.ts`)
**功能**: 区域配置状态管理

#### 4. StatisticsStore (`stores/statistics.ts`)
**功能**: 统计数据管理

#### 5. UIStore (`stores/ui.ts`)
**功能**: UI 状态管理

**状态**:
```typescript
interface UIState {
  loading: LoadingState
  notifications: Notification[]
  modals: ModalState[]
  sidebar: SidebarState
  breadcrumbs: BreadcrumbItem[]
}
```

---

## API 接口层

### API 文件列表 (`src/api/`)

| 文件 | 功能描述 |
|-----|---------|
| `camera.ts` | 摄像头相关 API |
| `detectionConfig.ts` | 检测配置 API |
| `videoStream.ts` | 视频流 API |
| `mlops.ts` | MLOps 相关 API |
| `export.ts` | 数据导出 API |
| `statistics.ts` | 统计数据 API |
| `alerts.ts` | 告警相关 API |
| `region.ts` | 区域配置 API |
| `system.ts` | 系统信息 API |

### HTTP 客户端 (`src/lib/http.ts`)

统一使用 `http` 实例进行 API 调用，支持：
- 请求/响应拦截器
- 错误处理
- Token 管理
- 加载状态管理

---

## 实时通信

### WebSocket 实现

#### 1. 视频流 WebSocket (`VideoStreamCard.vue`)
**连接地址**: `ws://host/ws/video/{camera_id}`

**消息格式**:
```typescript
interface VideoFrameMessage {
  type: 'frame'
  camera_id: string
  frame_id: number
  timestamp: number
  image_data: string  // Base64 编码的图像数据
}
```

**功能**:
- 实时接收视频帧
- 自动重连机制
- 连接状态监控

#### 2. 状态更新 WebSocket (`useWebSocket.ts`)
**连接地址**: `ws://host/ws/status`

**消息格式**:
```typescript
interface StatusUpdate {
  type: 'status_update'
  camera_id?: string
  data: Record<string, any>
  timestamp: number
}
```

**功能**:
- 接收系统状态更新
- 摄像头状态更新
- 自动重连（最多5次，间隔3秒）

**使用方式**:
```typescript
import { useWebSocket } from '@/composables/useWebSocket'

const { connected, statusData, connect, disconnect } = useWebSocket()
```

---

## UI/UX 特性

### 主题系统
- ✅ 亮色/暗色主题切换
- ✅ 主题持久化（localStorage）
- ✅ 响应式设计（移动端适配）

### 布局系统 (`MainLayout.vue`)
**特性**:
- ✅ 侧边栏导航（可折叠）
- ✅ 顶部导航栏（面包屑、系统状态、通知、全屏）
- ✅ 底部信息栏（版本、在线用户、系统时间）
- ✅ 移动端适配（遮罩层、响应式菜单）

**菜单项**:
- 🏠 首页
- 📹 实时监控
- 📊 统计分析
- 📝 检测记录
- 🚨 告警中心
- ⚙️ 相机配置
- 🎯 区域配置
- 🔧 检测配置
- 🤖 MLOps管理
- ℹ️ 系统信息

### 响应式设计
- 移动端侧边栏自动折叠
- 移动端遮罩层
- 响应式网格布局

### 交互优化
- ✅ 加载状态提示
- ✅ 错误提示（Alert 组件）
- ✅ 成功/失败消息提示（Message 组件）
- ✅ 确认对话框（Dialog 组件）
- ✅ 页面过渡动画

---

## 技术亮点

### 1. 视频流渲染优化
- 使用 `ImageBitmap` API 优化图像解码
- Canvas 渲染避免 DOM 重排
- 帧率控制防止内存泄漏

### 2. WebSocket 自动重连
- 指数退避重连策略
- 连接状态监控
- 错误处理机制

### 3. 类型安全
- 全面使用 TypeScript
- 接口类型定义完整
- API 响应类型定义

### 4. 组件化设计
- 高度可复用的组件
- 组合式 API 设计
- Props/Emits 类型定义

### 5. 状态管理
- Pinia 集中式状态管理
- 模块化 Store 设计
- 响应式状态更新

---

## 待优化项

### 1. 性能优化
- [ ] 虚拟滚动（大数据表格）
- [ ] 图片懒加载
- [ ] 路由懒加载优化

### 2. 功能增强
- [ ] 数据导出格式扩展（PDF、Excel）
- [ ] 图表交互增强
- [ ] 实时监控录制功能

### 3. 用户体验
- [ ] 快捷键支持
- [ ] 操作历史记录
- [ ] 个性化设置

### 4. 错误处理
- [ ] 全局错误边界
- [ ] 错误上报机制
- [ ] 离线状态处理

---

## 总结

前端系统采用现代化的 Vue 3 + TypeScript 技术栈，实现了完整的智能监控管理功能。系统架构清晰，组件化程度高，实时通信稳定，用户体验良好。MLOps 管理模块提供了完整的机器学习工作流管理能力，与后端 DDD 架构完美配合。

**核心优势**:
1. ✅ 模块化设计，易于维护和扩展
2. ✅ 类型安全，减少运行时错误
3. ✅ 实时通信，响应迅速
4. ✅ UI/UX 优化，交互流畅
5. ✅ 响应式设计，多端适配

---

**文档生成时间**: 2024年
**文档版本**: v1.0.0


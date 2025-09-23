<template>
  <div class="system-info-page">
    <!-- 页面头部 -->
    <PageHeader
      title="系统信息"
      subtitle="查看系统运行状态和硬件信息"
      icon="💻"
    >
      <template #actions>
        <n-space>
          <n-button type="primary" @click="refreshSystemInfo" :loading="loading">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新信息
          </n-button>
          <n-button @click="exportSystemInfo">
            <template #icon>
              <n-icon><DownloadOutline /></n-icon>
            </template>
            导出报告
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 系统状态概览 -->
    <div class="status-overview">
      <DataCard
        title="系统状态"
        :value="systemInfo?.status || 'Unknown'"
        class="status-card"
        :class="getStatusCardClass(systemInfo?.status)"
      >
        <template #icon>
          <n-icon size="24" :color="getStatusColor(systemInfo?.status)">
            <CheckmarkCircleOutline v-if="systemInfo?.status === 'running'" />
            <WarningOutline v-else-if="systemInfo?.status === 'warning'" />
            <CloseCircleOutline v-else />
          </n-icon>
        </template>
        <template #extra>
          <StatusIndicator
            :status="getStatusType(systemInfo?.status)"
            :text="getStatusText(systemInfo?.status)"
            size="medium"
          />
        </template>
      </DataCard>
    </div>

    <!-- 主要内容区 -->
    <div class="system-content">
      <n-tabs v-model:value="activeTab" type="line" size="large">
        <!-- 基本信息标签页 -->
        <n-tab-pane name="basic" tab="📋 基本信息">
          <div class="basic-info-content">
            <div class="info-grid">
              <!-- 系统信息卡片 -->
              <DataCard title="系统信息" class="info-card">
                <template #extra>
                  <n-tag type="info" size="small">
                    <template #icon>
                      <n-icon><DesktopOutline /></n-icon>
                    </template>
                    操作系统
                  </n-tag>
                </template>

                <div class="info-list">
                  <div class="info-item">
                    <n-text strong>操作系统:</n-text>
                    <n-text>{{ systemInfo?.os || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>系统版本:</n-text>
                    <n-text>{{ systemInfo?.version || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>架构:</n-text>
                    <n-text>{{ systemInfo?.architecture || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>主机名:</n-text>
                    <n-text>{{ systemInfo?.hostname || 'N/A' }}</n-text>
                  </div>
                </div>
              </DataCard>

              <!-- 运行时信息卡片 -->
              <DataCard title="运行时信息" class="info-card">
                <template #extra>
                  <n-tag type="success" size="small">
                    <template #icon>
                      <n-icon><TimeOutline /></n-icon>
                    </template>
                    运行时间
                  </n-tag>
                </template>

                <div class="info-list">
                  <div class="info-item">
                    <n-text strong>启动时间:</n-text>
                    <n-text>{{ formatDateTime(systemInfo?.boot_time) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>运行时长:</n-text>
                    <n-text>{{ formatUptime(systemInfo?.uptime) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>当前时间:</n-text>
                    <n-text>{{ formatDateTime(currentTime) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>时区:</n-text>
                    <n-text>{{ systemInfo?.timezone || 'N/A' }}</n-text>
                  </div>
                </div>
              </DataCard>

              <!-- 网络信息卡片 -->
              <DataCard title="网络信息" class="info-card">
                <template #extra>
                  <n-tag type="warning" size="small">
                    <template #icon>
                      <n-icon><GlobeOutline /></n-icon>
                    </template>
                    网络
                  </n-tag>
                </template>

                <div class="info-list">
                  <div class="info-item">
                    <n-text strong>IP 地址:</n-text>
                    <n-text>{{ systemInfo?.ip_address || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>MAC 地址:</n-text>
                    <n-text>{{ systemInfo?.mac_address || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>网络状态:</n-text>
                    <StatusIndicator
                      :status="systemInfo?.network_status === 'connected' ? 'success' : 'error'"
                      :text="systemInfo?.network_status || 'Unknown'"
                      size="small"
                    />
                  </div>
                </div>
              </DataCard>
            </div>
          </div>
        </n-tab-pane>

        <!-- 硬件信息标签页 -->
        <n-tab-pane name="hardware" tab="🔧 硬件信息">
          <div class="hardware-info-content">
            <div class="hardware-grid">
              <!-- CPU 信息 -->
              <DataCard title="处理器 (CPU)" class="hardware-card">
                <template #extra>
                  <n-progress
                    type="circle"
                    :percentage="systemInfo?.cpu?.usage || 0"
                    :color="getUsageColor(systemInfo?.cpu?.usage)"
                    size="small"
                  />
                </template>

                <div class="hardware-details">
                  <div class="info-item">
                    <n-text strong>型号:</n-text>
                    <n-text>{{ systemInfo?.cpu?.model || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>核心数:</n-text>
                    <n-text>{{ systemInfo?.cpu?.cores || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>频率:</n-text>
                    <n-text>{{ systemInfo?.cpu?.frequency || 'N/A' }} MHz</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>使用率:</n-text>
                    <n-text>{{ systemInfo?.cpu?.usage || 0 }}%</n-text>
                  </div>
                </div>
              </DataCard>

              <!-- 内存信息 -->
              <DataCard title="内存 (RAM)" class="hardware-card">
                <template #extra>
                  <n-progress
                    type="circle"
                    :percentage="getMemoryUsagePercentage()"
                    :color="getUsageColor(getMemoryUsagePercentage())"
                    size="small"
                  />
                </template>

                <div class="hardware-details">
                  <div class="info-item">
                    <n-text strong>总内存:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.memory?.total) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>已使用:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.memory?.used) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>可用:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.memory?.available) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>使用率:</n-text>
                    <n-text>{{ getMemoryUsagePercentage() }}%</n-text>
                  </div>
                </div>
              </DataCard>

              <!-- 存储信息 -->
              <DataCard title="存储空间" class="hardware-card">
                <template #extra>
                  <n-progress
                    type="circle"
                    :percentage="getDiskUsagePercentage()"
                    :color="getUsageColor(getDiskUsagePercentage())"
                    size="small"
                  />
                </template>

                <div class="hardware-details">
                  <div class="info-item">
                    <n-text strong>总空间:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.disk?.total) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>已使用:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.disk?.used) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>可用:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.disk?.free) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>使用率:</n-text>
                    <n-text>{{ getDiskUsagePercentage() }}%</n-text>
                  </div>
                </div>
              </DataCard>

              <!-- GPU 信息 -->
              <DataCard title="图形处理器 (GPU)" class="hardware-card" v-if="systemInfo?.gpu">
                <template #extra>
                  <n-tag type="info" size="small">
                    <template #icon>
                      <n-icon><HardwareChipOutline /></n-icon>
                    </template>
                    GPU
                  </n-tag>
                </template>

                <div class="hardware-details">
                  <div class="info-item">
                    <n-text strong>型号:</n-text>
                    <n-text>{{ systemInfo?.gpu?.model || 'N/A' }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>显存:</n-text>
                    <n-text>{{ formatBytes(systemInfo?.gpu?.memory) }}</n-text>
                  </div>
                  <div class="info-item">
                    <n-text strong>驱动版本:</n-text>
                    <n-text>{{ systemInfo?.gpu?.driver_version || 'N/A' }}</n-text>
                  </div>
                </div>
              </DataCard>
            </div>
          </div>
        </n-tab-pane>

        <!-- 服务状态标签页 -->
        <n-tab-pane name="services" tab="⚙️ 服务状态">
          <div class="services-content">
            <DataCard title="系统服务" class="services-card">
              <template #extra>
                <n-space>
                  <n-tag type="info" size="small">
                    共 {{ services.length }} 个服务
                  </n-tag>
                  <n-button size="small" @click="refreshServices">
                    <template #icon>
                      <n-icon><RefreshOutline /></n-icon>
                    </template>
                    刷新
                  </n-button>
                </n-space>
              </template>

              <n-data-table
                :columns="serviceColumns"
                :data="services"
                :loading="loading"
                :pagination="{ pageSize: 10, showSizePicker: true }"
                striped
                :bordered="false"
                size="medium"
                class="services-table"
              />
            </DataCard>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import {
  NCard, NButton, NTabs, NTabPane, NDataTable, NProgress,
  NSpace, NText, NTag, NIcon
} from 'naive-ui'
import {
  RefreshOutline, DownloadOutline, CheckmarkCircleOutline, WarningOutline,
  CloseCircleOutline, DesktopOutline, TimeOutline, GlobeOutline,
  HardwareChipOutline
} from '@vicons/ionicons5'
import { PageHeader, DataCard, StatusIndicator } from '@/components/common'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

// 响应式数据
const activeTab = ref('basic')
const currentTime = ref(Date.now())
const timeInterval = ref<NodeJS.Timeout | null>(null)

// 计算属性
const systemInfo = computed(() => systemStore.systemInfo)
const loading = computed(() => systemStore.loading)
const services = computed(() => [
  { name: 'Web服务', status: 'running', description: '前端Web服务' },
  { name: 'API服务', status: 'running', description: '后端API服务' },
  { name: '检测服务', status: 'running', description: '人体检测服务' }
])

// 服务表格列定义
const serviceColumns = [
  {
    title: '服务名称',
    key: 'name'
  },
  {
    title: '状态',
    key: 'status',
    render: (row: any) => {
      const status = row.status === 'running' ? 'success' : 'error'
      const text = row.status === 'running' ? '运行中' : '已停止'
      return h(StatusIndicator, { status, text, size: 'small' })
    }
  },
  {
    title: '描述',
    key: 'description'
  }
]

// 生命周期
onMounted(async () => {
  await refreshSystemInfo()
  // 每秒更新当前时间
  timeInterval.value = setInterval(() => {
    currentTime.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval.value) {
    clearInterval(timeInterval.value)
  }
})

// 方法
async function refreshSystemInfo() {
  try {
    await systemStore.fetchSystemInfo()
  } catch (error) {
    console.error('获取系统信息失败:', error)
  }
}

async function refreshServices() {
  try {
    // 模拟刷新服务状态
    console.log('刷新服务状态')
  } catch (error) {
    console.error('获取服务信息失败:', error)
  }
}

const getStatusCardClass = (status: string) => {
  const classes = {
    'running': 'status-success',
    'warning': 'status-warning',
    'error': 'status-error'
  }
  return classes[status] || 'status-default'
}

const getStatusColor = (status: string) => {
  const colors = {
    'running': 'var(--success-color)',
    'warning': 'var(--warning-color)',
    'error': 'var(--error-color)'
  }
  return colors[status] || 'var(--text-color-3)'
}

const getStatusType = (status: string) => {
  const types = {
    'running': 'success',
    'warning': 'warning',
    'error': 'error'
  }
  return types[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts = {
    'running': '正常运行',
    'warning': '警告状态',
    'error': '错误状态'
  }
  return texts[status] || '未知状态'
}

const getUsageColor = (percentage: number) => {
  if (percentage < 60) return 'var(--success-color)'
  if (percentage < 80) return 'var(--warning-color)'
  return 'var(--error-color)'
}

const getMemoryUsagePercentage = () => {
  if (!systemInfo.value?.memory) return 0
  const { total, used } = systemInfo.value.memory
  return Math.round((used / total) * 100)
}

const getDiskUsagePercentage = () => {
  if (!systemInfo.value?.disk) return 0
  const { total, used } = systemInfo.value.disk
  return Math.round((used / total) * 100)
}

const formatBytes = (bytes: number) => {
  if (!bytes) return 'N/A'
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

const formatDateTime = (timestamp: string | number) => {
  if (!timestamp) return 'N/A'
  return new Date(timestamp).toLocaleString('zh-CN')
}

const formatUptime = (seconds: number) => {
  if (!seconds) return 'N/A'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${days}天 ${hours}小时 ${minutes}分钟`
}

const exportSystemInfo = () => {
  // 导出系统信息逻辑
  console.log('导出系统信息')
}
</script>

<style scoped>
.system-info-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-large);
}

.status-overview {
  flex-shrink: 0;
}

.status-card {
  min-height: 120px;
}

.status-success {
  background: linear-gradient(135deg, var(--success-color-suppl), var(--success-color));
  color: white;
}

.status-warning {
  background: linear-gradient(135deg, var(--warning-color-suppl), var(--warning-color));
  color: white;
}

.status-error {
  background: linear-gradient(135deg, var(--error-color-suppl), var(--error-color));
  color: white;
}

.system-content {
  flex: 1;
  min-height: 0;
}

.basic-info-content {
  height: 100%;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-large);
}

.info-card {
  min-height: 200px;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-medium);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-small) 0;
  border-bottom: 1px solid var(--border-color);
}

.info-item:last-child {
  border-bottom: none;
}

.hardware-info-content {
  height: 100%;
}

.hardware-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-large);
}

.hardware-card {
  min-height: 220px;
}

.hardware-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-medium);
}

.services-content {
  height: 100%;
}

.services-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.services-table {
  flex: 1;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .info-grid,
  .hardware-grid {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  }
}

@media (max-width: 768px) {
  .info-grid,
  .hardware-grid {
    grid-template-columns: 1fr;
  }

  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-tiny);
  }
}

@media (max-width: 480px) {
  .status-card {
    min-height: 100px;
  }

  .info-card,
  .hardware-card {
    min-height: 180px;
  }
}
</style>

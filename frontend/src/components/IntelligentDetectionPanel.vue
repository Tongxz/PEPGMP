<template>
  <n-card title="智能检测状态" class="intelligent-detection-panel">
    <template #header-extra>
      <n-tag :type="wsConnected ? 'success' : 'error'" size="small">
        {{ wsConnected ? '实时连接' : '离线模式' }}
      </n-tag>
    </template>

    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <!-- 处理统计 -->
      <n-gi>
        <n-statistic label="处理效率" :value="processingEfficiency" suffix="%" />
      </n-gi>
      <n-gi>
        <n-statistic label="平均FPS" :value="avgFps" :precision="2" />
      </n-gi>
      <n-gi>
        <n-statistic label="已处理帧" :value="processedFrames" />
      </n-gi>
      <n-gi>
        <n-statistic label="已跳过帧" :value="skippedFrames" />
      </n-gi>
    </n-grid>

    <!-- 场景分布 -->
    <n-divider />
    <div class="scene-distribution">
      <h4>场景分布</h4>
      <n-space>
        <n-tag v-for="(count, scene) in sceneDistribution" :key="scene" type="info">
          {{ scene }}: {{ count }}
        </n-tag>
      </n-space>
    </div>

    <!-- 性能监控 -->
    <n-divider />
    <div class="performance-monitoring">
      <h4>性能监控</h4>
      <n-grid :cols="3" :x-gap="12" :y-gap="12">
        <n-gi>
          <n-progress
            type="line"
            :percentage="cpuUsage"
            :color="getProgressColor(cpuUsage)"
            :show-indicator="false"
          />
          <div class="progress-label">CPU: {{ cpuUsage }}%</div>
        </n-gi>
        <n-gi>
          <n-progress
            type="line"
            :percentage="memoryUsage"
            :color="getProgressColor(memoryUsage)"
            :show-indicator="false"
          />
          <div class="progress-label">内存: {{ memoryUsage }}%</div>
        </n-gi>
        <n-gi>
          <n-progress
            type="line"
            :percentage="gpuUsage"
            :color="getProgressColor(gpuUsage)"
            :show-indicator="false"
          />
          <div class="progress-label">GPU: {{ gpuUsage }}%</div>
        </n-gi>
      </n-grid>
    </div>

    <!-- 告警信息 -->
    <n-divider v-if="alerts.length > 0" />
    <div class="alerts" v-if="alerts.length > 0">
      <h4>系统告警</h4>
      <n-alert
        v-for="alert in alerts"
        :key="alert.id"
        :type="alert.type"
        :title="alert.title"
        :description="alert.message"
        closable
        @close="removeAlert(alert.id)"
      />
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { NCard, NTag, NGrid, NGi, NStatistic, NDivider, NSpace, NProgress, NAlert } from 'naive-ui'
import { useWebSocket } from '@/composables/useWebSocket'
import { useCameraStore } from '@/stores/camera'

interface Alert {
  id: string
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
}

const { connected: wsConnected, statusData } = useWebSocket()
const cameraStore = useCameraStore()
const alerts = ref<Alert[]>([])

// 同步WebSocket状态到store
let interval: number | null = null

onMounted(() => {
  // 监听WebSocket状态变化并更新store
  const updateStore = () => {
    cameraStore.updateWebSocketStatus(wsConnected.value)
    cameraStore.updateWebSocketData(statusData.value)
  }

  // 立即更新一次
  updateStore()

  // 使用定时器定期更新store
  interval = setInterval(updateStore, 1000)
})

onUnmounted(() => {
  if (interval) {
    clearInterval(interval)
  }
})

// 计算属性
const processingEfficiency = computed(() => {
  const data = getLatestStatusData()
  return data?.processing_efficiency ? Math.round(data.processing_efficiency * 100) : 0
})

const avgFps = computed(() => {
  const data = getLatestStatusData()
  return data?.avg_fps || 0
})

const processedFrames = computed(() => {
  const data = getLatestStatusData()
  return data?.processed_frames || 0
})

const skippedFrames = computed(() => {
  const data = getLatestStatusData()
  return data?.skipped_frames || 0
})

const sceneDistribution = computed(() => {
  const data = getLatestStatusData()
  return data?.scene_distribution || {}
})

const cpuUsage = computed(() => {
  const data = getLatestStatusData()
  return data?.cpu_usage || 0
})

const memoryUsage = computed(() => {
  const data = getLatestStatusData()
  return data?.memory_usage || 0
})

const gpuUsage = computed(() => {
  const data = getLatestStatusData()
  return data?.gpu_usage || 0
})

// 获取最新的状态数据
function getLatestStatusData() {
  const allData = Object.values(statusData.value)
  if (allData.length === 0) return null

  // 返回最新的数据
  return allData[allData.length - 1]
}

// 进度条颜色
function getProgressColor(percentage: number) {
  if (percentage < 50) return '#18a058'
  if (percentage < 80) return '#f0a020'
  return '#d03050'
}

// 移除告警
function removeAlert(id: string) {
  const index = alerts.value.findIndex(alert => alert.id === id)
  if (index > -1) {
    alerts.value.splice(index, 1)
  }
}

// 添加告警
function addAlert(alert: Omit<Alert, 'id'>) {
  const id = Date.now().toString()
  alerts.value.push({ ...alert, id })
}

// 监听性能告警
function checkPerformanceAlerts() {
  const data = getLatestStatusData()
  if (!data) return

  // CPU告警
  if (data.cpu_usage > 80) {
    addAlert({
      type: 'warning',
      title: 'CPU使用率过高',
      message: `当前CPU使用率: ${data.cpu_usage}%，建议优化检测参数`
    })
  }

  // 内存告警
  if (data.memory_usage > 85) {
    addAlert({
      type: 'warning',
      title: '内存使用率过高',
      message: `当前内存使用率: ${data.memory_usage}%，建议重启检测进程`
    })
  }

  // FPS告警
  if (data.avg_fps < 5) {
    addAlert({
      type: 'error',
      title: '检测性能过低',
      message: `当前平均FPS: ${data.avg_fps}，检测可能存在问题`
    })
  }
}

// 定期检查告警
setInterval(checkPerformanceAlerts, 10000)
</script>

<style scoped>
.intelligent-detection-panel {
  margin-bottom: 16px;
}

.scene-distribution h4,
.performance-monitoring h4,
.alerts h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.progress-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.alerts {
  max-height: 200px;
  overflow-y: auto;
}
</style>

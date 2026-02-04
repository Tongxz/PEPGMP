<template>
  <div class="professional-monitor">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">实时监控</h1>
        <p class="page-subtitle">多路视频流实时监控与异常行为即时告警</p>
      </div>
      <div class="header-actions">
        <n-select
          v-model:value="selectedCameraIds"
          :options="cameraOptions"
          placeholder="选择摄像头"
          multiple
          clearable
          filterable
          style="width: 280px"
          size="medium"
        />
        <n-button-group>
          <n-button @click="layoutMode = 'grid'" :type="layoutMode === 'grid' ? 'primary' : 'default'">
            <template #icon><n-icon><GridOutline /></n-icon></template>
            网格
          </n-button>
          <n-button @click="layoutMode = 'single'" :type="layoutMode === 'single' ? 'primary' : 'default'">
            <template #icon><n-icon><SquareOutline /></n-icon></template>
            单屏
          </n-button>
        </n-button-group>
        <n-button @click="refreshCameras" :loading="loading">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新
        </n-button>
      </div>
    </div>

    <!-- 统计卡片区 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon stat-icon-online">
          <n-icon size="24"><VideocamOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ onlineCameras }}</div>
          <div class="stat-label">在线摄像头</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-detection">
          <n-icon size="24"><EyeOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ detectionCount }}</div>
          <div class="stat-label">实时检测数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-fps">
          <n-icon size="24"><SpeedometerOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ avgFps }}fps</div>
          <div class="stat-label">平均帧率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-alert">
          <n-icon size="24"><WarningOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ alertCount }}</div>
          <div class="stat-label">实时告警</div>
        </div>
      </div>
    </div>

    <!-- 视频网格 -->
    <div class="video-grid" :class="`grid-${gridSize}`" v-if="layoutMode === 'grid'">
      <div
        v-for="camera in displayedCameras"
        :key="camera.id"
        class="video-card"
        @click="selectCamera(camera)"
      >
        <div class="video-wrapper">
          <!-- WebSocket视频流 -->
          <VideoStream
            :camera-id="camera.id"
            :auto-connect="camera.status === 'active'"
            :show-fps="true"
          />

          <!-- 视频信息覆盖层 -->
          <div class="video-overlay">
            <div class="video-header">
              <div class="camera-name">{{ camera.name }}</div>
              <div class="camera-status" :class="camera.status">
                <div class="status-dot"></div>
                {{ camera.status === 'online' ? '在线' : '离线' }}
              </div>
            </div>
            <div class="video-footer">
              <div class="video-info">
                <span class="info-item">
                  <n-icon size="14"><TimeOutline /></n-icon>
                  {{ formatTime(camera.last_update) }}
                </span>
                <span class="info-item">
                  <n-icon size="14"><PeopleOutline /></n-icon>
                  {{ camera.detection_count || 0 }}
                </span>
              </div>
              <div class="video-controls" @click.stop>
                <n-button
                  v-if="camera.status === 'inactive' || camera.status === 'offline'"
                  size="small"
                  type="success"
                  @click="handleCameraControl(camera.id, 'start')"
                  :loading="controlLoading[camera.id]"
                >
                  <template #icon><n-icon><PlayOutline /></n-icon></template>
                </n-button>
                <n-button
                  v-if="camera.status === 'active' || camera.status === 'online'"
                  size="small"
                  type="warning"
                  @click="handleCameraControl(camera.id, 'stop')"
                  :loading="controlLoading[camera.id]"
                >
                  <template #icon><n-icon><StopOutline /></n-icon></template>
                </n-button>
                <n-button
                  size="small"
                  type="info"
                  @click="handleCameraControl(camera.id, 'restart')"
                  :loading="controlLoading[camera.id]"
                >
                  <template #icon><n-icon><RefreshOutline /></n-icon></template>
                </n-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="displayedCameras.length === 0" class="empty-state">
        <n-icon size="64" color="#8C9BAB"><VideocamOffOutline /></n-icon>
        <p class="empty-text">暂无摄像头数据</p>
        <n-button type="primary" @click="refreshCameras">刷新数据</n-button>
      </div>
    </div>

    <!-- 单屏模式 -->
    <div class="single-view" v-if="layoutMode === 'single' && selectedCamera">
      <div class="single-video-card">
        <div class="single-video-wrapper">
          <!-- WebSocket视频流 -->
          <VideoStream
            :camera-id="selectedCamera.id"
            :auto-connect="selectedCamera.status === 'active'"
            :show-fps="true"
            :width="1920"
            :height="1080"
          />
        </div>
        <div class="single-video-info">
          <div class="single-video-header">
            <h3>{{ selectedCamera.name }}</h3>
            <div class="single-video-controls">
              <n-button
                v-if="selectedCamera.status === 'inactive' || selectedCamera.status === 'offline'"
                type="success"
                @click="handleCameraControl(selectedCamera.id, 'start')"
                :loading="controlLoading[selectedCamera.id]"
              >
                <template #icon><n-icon><PlayOutline /></n-icon></template>
                启动摄像头
              </n-button>
              <n-button
                v-if="selectedCamera.status === 'active' || selectedCamera.status === 'online'"
                type="warning"
                @click="handleCameraControl(selectedCamera.id, 'stop')"
                :loading="controlLoading[selectedCamera.id]"
              >
                <template #icon><n-icon><StopOutline /></n-icon></template>
                停止摄像头
              </n-button>
              <n-button
                type="info"
                @click="handleCameraControl(selectedCamera.id, 'restart')"
                :loading="controlLoading[selectedCamera.id]"
              >
                <template #icon><n-icon><RefreshOutline /></n-icon></template>
                重启摄像头
              </n-button>
            </div>
          </div>
          <n-descriptions :column="2" size="medium" bordered>
            <n-descriptions-item label="位置">{{ selectedCamera.location }}</n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="selectedCamera.status === 'active' || selectedCamera.status === 'online' ? 'success' : 'error'" size="small">
                {{ selectedCamera.status === 'active' || selectedCamera.status === 'online' ? '在线' : '离线' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="检测数">{{ selectedCamera.detection_count || 0 }}</n-descriptions-item>
            <n-descriptions-item label="最后更新">{{ formatTime(selectedCamera.last_update) }}</n-descriptions-item>
          </n-descriptions>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { NButton, NButtonGroup, NSelect, NIcon, NTag, NDescriptions, NDescriptionsItem, useMessage } from 'naive-ui'
import {
  VideocamOutline,
  VideocamOffOutline,
  EyeOutline,
  SpeedometerOutline,
  WarningOutline,
  RefreshOutline,
  GridOutline,
  SquareOutline,
  TimeOutline,
  PeopleOutline,
  PlayOutline,
  StopOutline
} from '@vicons/ionicons5'

// 导入组件
import VideoStream from '@/components/VideoStream.vue'

// 导入 API
import { getRealtimeStatistics, getDetectionRealtimeStatistics } from '@/api/modules/statistics'
import { getCameras, startCamera, stopCamera, restartCamera } from '@/api/modules/cameras'

const message = useMessage()

// 布局模式
const layoutMode = ref<'grid' | 'single'>('grid')
const gridSize = ref(4)
const loading = ref(false)

// 摄像头数据
const cameras = ref<any[]>([])
const selectedCameraIds = ref<string[]>([])
const selectedCamera = ref<any>(null)
const controlLoading = ref<Record<string, boolean>>({})

// 统计数据
const onlineCameras = ref(0)
const detectionCount = ref(0)
const avgFps = ref(0)
const alertCount = ref(0)

// 计算属性
const cameraOptions = computed(() =>
  cameras.value.map(c => ({ label: c.name, value: c.id }))
)

const displayedCameras = computed(() => {
  console.log('displayedCameras计算:', {
    totalCameras: cameras.value.length,
    selectedIds: selectedCameraIds.value,
    cameras: cameras.value
  })

  if (selectedCameraIds.value.length > 0) {
    const filtered = cameras.value.filter(c => selectedCameraIds.value.includes(c.id))
    console.log('过滤后的摄像头:', filtered)
    return filtered
  }
  return cameras.value
})

// 方法
const selectCamera = (camera: any) => {
  selectedCamera.value = camera
  layoutMode.value = 'single'
}

// 获取监控数据
const fetchMonitoringData = async () => {
  console.log('🔄 开始获取监控数据, loading:', loading.value)

  if (loading.value) {
    console.log('⚠️ 已经在加载中，跳过')
    return
  }

  loading.value = true

  try {
    // 获取摄像头列表
    const camerasResponse = await getCameras()
    cameras.value = (camerasResponse.cameras || []).map((cam: any) => ({
      id: cam.id,
      name: cam.name,
      location: cam.location || '未知位置',
      status: cam.status || 'offline',
      detection_count: 0,
      last_update: cam.updated_at || new Date().toISOString(),
      stream_url: `/api/v1/video-stream/${cam.id}`
    }))

    // 获取统计数据（可选，失败不影响摄像头显示）
    try {
      // 同时获取实时统计和检测统计
      const [realtimeStats, detectionStats] = await Promise.all([
        getRealtimeStatistics(),
        getDetectionRealtimeStatistics()
      ])

      // 从不同的API组合数据
      onlineCameras.value = detectionStats.connection_status?.active_cameras || 0
      detectionCount.value = realtimeStats.detection_stats?.total_detections_today || 0
      avgFps.value = Math.round(detectionStats.avg_fps || 0)
      alertCount.value = realtimeStats.alerts?.active_alerts || 0
    } catch (statsError: any) {
      console.warn('统计数据获取失败，使用默认值:', statsError.message)
      // 使用默认统计值
      onlineCameras.value = cameras.value.filter(c => c.status === 'active' || c.status === 'online').length
      detectionCount.value = 0
      avgFps.value = 0
      alertCount.value = 0
    }
  } catch (error: any) {
    console.error('获取监控数据失败:', error)
    message.error(error.message || '获取监控数据失败，请稍后重试')

    // 使用默认值
    onlineCameras.value = 0
    detectionCount.value = 0
    avgFps.value = 0
    alertCount.value = 0
    cameras.value = []
  } finally {
    loading.value = false
  }
}

const refreshCameras = async () => {
  await fetchMonitoringData()
  message.success('刷新成功')
}

// 摄像头控制
const handleCameraControl = async (cameraId: string, action: 'start' | 'stop' | 'restart') => {
  controlLoading.value[cameraId] = true

  try {
    let actionText = ''
    switch (action) {
      case 'start':
        await startCamera(cameraId)
        actionText = '启动'
        break
      case 'stop':
        await stopCamera(cameraId)
        actionText = '停止'
        break
      case 'restart':
        await restartCamera(cameraId)
        actionText = '重启'
        break
    }

    message.success(`${actionText}成功`)

    // 延迟刷新，等待状态更新
    setTimeout(async () => {
      await fetchMonitoringData()
    }, 1000)
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    controlLoading.value[cameraId] = false
  }
}

const handleImageError = (e: Event) => {
  console.error('Image load error:', e)
}

const formatTime = (timestamp: string | Date) => {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// 定时刷新
let updateInterval: NodeJS.Timeout

onMounted(() => {
  // 首次加载
  fetchMonitoringData()

  // 每30秒刷新一次
  updateInterval = setInterval(() => {
    fetchMonitoringData()
  }, 30000)
})

onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
})
</script>

<style scoped lang="scss">
/**
 * 实时监控页面 - 专业版
 */

// 颜色变量
$color-bg: #F7FAFC;
$color-white: #FFFFFF;
$color-border: #E6EDF5;
$color-text-primary: #1F2D3D;
$color-text-secondary: #6B778C;
$color-text-tertiary: #8C9BAB;

$color-online: #52C41A;
$color-offline: #FF4D4F;
$color-detection: #1E9FFF;
$color-alert: #FF6B6B;

.professional-monitor {
  padding: 24px;
  background: $color-bg;
  min-height: 100vh;
}

// ===== 页面头部 =====
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: $color-text-secondary;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

// ===== 统计卡片 =====
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;

  &.stat-icon-online {
    background: rgba(82, 196, 26, 0.1);
    color: $color-online;
  }

  &.stat-icon-detection {
    background: rgba(30, 159, 255, 0.1);
    color: $color-detection;
  }

  &.stat-icon-fps {
    background: rgba(43, 201, 201, 0.1);
    color: #2BC9C9;
  }

  &.stat-icon-alert {
    background: rgba(255, 107, 107, 0.1);
    color: $color-alert;
  }
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 13px;
  color: $color-text-secondary;
}

// ===== 视频网格 =====
.video-grid {
  display: grid;
  gap: 16px;

  &.grid-2 {
    grid-template-columns: repeat(2, 1fr);
  }

  &.grid-3 {
    grid-template-columns: repeat(3, 1fr);
  }

  &.grid-4 {
    grid-template-columns: repeat(4, 1fr);
  }
}

.video-card {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    border-color: $color-detection;

    .video-overlay {
      opacity: 1;
    }
  }
}

.video-wrapper {
  position: relative;
  width: 100%;
  padding-top: 56.25%; // 16:9
  background: #000;
  overflow: hidden;
}

.video-stream {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.05);

  p {
    margin: 0;
    font-size: 14px;
    color: $color-text-tertiary;
  }
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.6) 0%, transparent 30%, transparent 70%, rgba(0, 0, 0, 0.6) 100%);
  opacity: 0;
  transition: opacity 0.2s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 12px;
  pointer-events: none; // 允许点击穿透到VideoStream组件
}

.video-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.camera-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.camera-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #FFFFFF;
  padding: 4px 8px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.3);

  &.online .status-dot {
    background: $color-online;
  }

  &.offline .status-dot {
    background: $color-offline;
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.video-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.video-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #FFFFFF;
}

.video-controls {
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: auto; // 恢复按钮的点击事件

  .n-button {
    padding: 4px 8px;
    height: 28px;
  }
}

.video-card:hover .video-controls {
  opacity: 1;
}

// ===== 空状态 =====
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
}

.empty-text {
  margin: 16px 0 24px 0;
  font-size: 16px;
  color: $color-text-secondary;
}

// ===== 单屏模式 =====
.single-view {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  overflow: hidden;
}

.single-video-card {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  padding: 24px;
}

.single-video-wrapper {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;

  // VideoStream组件绝对定位填充容器
  > * {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }
}

.single-video-stream {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.single-video-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.single-video-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: $color-text-primary;
    margin: 0;
  }
}

.single-video-controls {
  display: flex;
  gap: 8px;
}

// ===== 响应式 =====
@media (max-width: 1400px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .video-grid.grid-4 {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1024px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .video-grid.grid-3,
  .video-grid.grid-4 {
    grid-template-columns: repeat(2, 1fr);
  }

  .single-video-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .professional-monitor {
    padding: 16px;
  }

  .stats-cards {
    grid-template-columns: 1fr;
  }

  .video-grid {
    grid-template-columns: 1fr !important;
  }
}
</style>

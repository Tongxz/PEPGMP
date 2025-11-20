<template>
  <div class="realtime-monitor-container">
    <!-- 页面头部 -->
    <PageHeader
      title="实时监控大屏"
      subtitle="多摄像头实时画面监控"
      icon="📹"
    >
      <template #actions>
        <n-space>
          <n-select
            v-model:value="selectedCameraIds"
            :options="cameraOptions"
            placeholder="选择摄像头"
            multiple
            clearable
            filterable
            style="width: 300px"
            @update:value="handleCameraSelectionChange"
          />
          <n-button @click="toggleFullscreen" :type="isFullscreen ? 'primary' : 'default'">
            <template #icon>
              <n-icon>
                <component :is="isFullscreen ? 'ContractOutline' : 'ExpandOutline'" />
              </n-icon>
            </template>
            {{ isFullscreen ? '退出全屏' : '全屏' }}
          </n-button>
          <n-button @click="refreshCameras" :loading="loading">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 加载状态 -->
    <n-spin :show="cameraStore.loading">
      <n-card class="control-card" :bordered="false">
        <n-space align="center" justify="space-between">
          <n-space align="center">
            <n-text strong>布局模式:</n-text>
            <n-radio-group v-model:value="layoutMode" size="small">
              <n-radio-button value="grid">网格</n-radio-button>
              <n-radio-button value="single">单屏</n-radio-button>
            </n-radio-group>
            <n-text strong style="margin-left: 16px">网格大小:</n-text>
            <n-select
              v-model:value="gridColumns"
              :options="gridColumnOptions"
              size="small"
              style="width: 100px"
              :disabled="layoutMode !== 'grid'"
            />
          </n-space>
          <n-space align="center">
            <n-tag type="info" size="small">
              总摄像头: {{ cameras.length }} 个
            </n-tag>
            <n-tag type="warning" size="small">
              已启用: {{ enabledCameras.length }} 个
            </n-tag>
            <n-tag type="info" size="small">
              已选择: {{ selectedCameraIds.length }} 个
            </n-tag>
            <n-tag type="success" size="small">
              已连接: {{ connectedCount }} 个
            </n-tag>
          </n-space>
        </n-space>
      </n-card>
    </n-spin>

    <!-- 错误提示 -->
    <n-alert
      v-if="cameraStore.error"
      type="error"
      closable
      @close="cameraStore.clearError"
      style="margin: 16px 0"
    >
      {{ cameraStore.error }}
    </n-alert>

    <!-- 提示信息 -->
    <n-alert
      v-if="cameras.length === 0 && !cameraStore.loading"
      type="warning"
      style="margin: 16px 0"
    >
      <template #header>没有摄像头</template>
      系统中还没有配置摄像头，请先前往"相机配置"页面添加摄像头。
    </n-alert>

    <n-alert
      v-else-if="enabledCameras.length === 0 && !cameraStore.loading && cameras.length > 0"
      type="warning"
      style="margin: 16px 0"
    >
      <template #header>没有启用的摄像头</template>
      所有摄像头都未启用，请在"相机配置"页面启用摄像头后再查看实时画面。
    </n-alert>

    <n-alert
      v-if="selectedCameraIds.length > 0 && connectedCount === 0 && !cameraStore.loading"
      type="info"
      style="margin: 16px 0"
    >
      <template #header>视频流连接提示</template>
      <div style="white-space: pre-line;">
        已选择摄像头但未连接到视频流，可能的原因：
        <br />1. 摄像头检测进程未运行（请前往"相机配置"页面启动摄像头）
        <br />2. 后端视频流服务未启动或异常
        <br />3. WebSocket连接失败（请查看浏览器控制台获取详细错误）
        <br />
        <br />请检查：
        <br />- 摄像头是否正在运行（查看"相机配置"页面中的运行状态）
        <br />- 浏览器控制台是否有错误信息
        <br />- 后端服务日志是否有异常
      </div>
    </n-alert>

    <!-- 视频网格区域 -->
    <div class="video-grid-container" :class="{ 'fullscreen': isFullscreen }">
      <!-- 调试信息 -->
      <div v-if="displayedCameras.length === 0" class="empty-state">
        <n-empty description="请选择要监控的摄像头">
          <template #extra>
            <n-button type="primary" @click="selectAllCameras">
              选择所有摄像头
            </n-button>
          </template>
        </n-empty>
      </div>

      <!-- 网格布局 -->
      <div v-else-if="layoutMode === 'grid'" class="video-grid" :style="gridStyle">
        <div
          v-for="cameraId in displayedCameras"
          :key="cameraId"
          class="video-item"
        >
          <VideoStreamCard
            :camera-id="cameraId"
            :camera-name="getCameraName(cameraId)"
            @connected="handleVideoConnected(cameraId)"
            @disconnected="handleVideoDisconnected(cameraId)"
          />
        </div>
      </div>

      <!-- 单屏布局 -->
      <div v-else class="video-single">
        <VideoStreamCard
          :camera-id="selectedCameraIds[0]"
          :camera-name="getCameraName(selectedCameraIds[0])"
          :full-size="true"
          @connected="handleVideoConnected(selectedCameraIds[0])"
          @disconnected="handleVideoDisconnected(selectedCameraIds[0])"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import {
  NCard,
  NSpace,
  NSelect,
  NButton,
  NIcon,
  NTag,
  NText,
  NRadioGroup,
  NRadioButton,
  NEmpty,
  NSpin,
  NAlert,
  useMessage,
} from 'naive-ui'
import {
  RefreshOutline,
  ExpandOutline,
  ContractOutline,
} from '@vicons/ionicons5'
import { PageHeader } from '@/components/common'
import { useCameraStore } from '@/stores/camera'
import VideoStreamCard from '@/components/VideoStreamCard.vue'

const message = useMessage()
const cameraStore = useCameraStore()

// 响应式数据
const loading = ref(false)
const selectedCameraIds = ref<string[]>([])
const layoutMode = ref<'grid' | 'single'>('grid')
const gridColumns = ref(2)
const isFullscreen = ref(false)
const connectedCameras = ref<Set<string>>(new Set())

// 网格列选项
const gridColumnOptions = [
  { label: '1列', value: 1 },
  { label: '2列', value: 2 },
  { label: '3列', value: 3 },
  { label: '4列', value: 4 },
]

// 计算属性
const cameras = computed(() => cameraStore.cameras)
// 检查摄像头是否启用：同时检查 enabled 和 active 字段，以及是否正在运行
const enabledCameras = computed(() => {
  return cameras.value.filter((cam) => {
    // 检查 enabled 或 active 字段（兼容不同的字段名）
    const isEnabled = cam.enabled === true || cam.active === true
    // 也可以认为正在运行的摄像头是"启用"的
    const isRunning = cameraStore.runtimeStatus[cam.id]?.running === true
    return isEnabled || isRunning
  })
})

// 摄像头选项：显示所有摄像头，但标注启用状态
const cameraOptions = computed(() =>
  cameras.value.map((cam) => ({
    label: `${cam.name || cam.id} (${cam.id})${(cam.enabled || cam.active) ? ' ✓' : ' [未启用]'}`,
    value: cam.id,
    disabled: false, // 允许选择未启用的摄像头（用户可能想查看）
  }))
)

const displayedCameras = computed(() => {
  if (layoutMode.value === 'single') {
    return selectedCameraIds.value.slice(0, 1)
  }
  return selectedCameraIds.value
})

const gridStyle = computed(() => {
  return {
    gridTemplateColumns: `repeat(${gridColumns.value}, 1fr)`,
  }
})

const connectedCount = computed(() => connectedCameras.value.size)

// 方法
function getCameraName(cameraId: string): string {
  const camera = cameras.value.find((cam) => cam.id === cameraId)
  return camera?.name || cameraId
}

function handleCameraSelectionChange(cameraIds: string[]) {
  // 如果单屏模式，只保留第一个
  if (layoutMode.value === 'single' && cameraIds.length > 1) {
    selectedCameraIds.value = [cameraIds[0]]
    message.info('单屏模式只能显示一个摄像头')
  } else {
    selectedCameraIds.value = cameraIds
  }
}

function selectAllCameras() {
  selectedCameraIds.value = enabledCameras.value.map((cam) => cam.id)
  message.success(`已选择 ${selectedCameraIds.value.length} 个摄像头`)
}

function handleVideoConnected(cameraId: string) {
  connectedCameras.value.add(cameraId)
}

function handleVideoDisconnected(cameraId: string) {
  connectedCameras.value.delete(cameraId)
}

async function refreshCameras() {
  loading.value = true
  try {
    await cameraStore.fetchCameras()
    await cameraStore.refreshRuntimeStatus()

    console.log('摄像头列表刷新完成:', {
      total: cameras.value.length,
      enabled: enabledCameras.value.length,
      selected: selectedCameraIds.value.length,
      running: Object.values(cameraStore.runtimeStatus).filter((s: any) => s?.running).length
    })

    // 如果当前没有选中的摄像头，但有了启用的摄像头，自动选择
    if (selectedCameraIds.value.length === 0 && enabledCameras.value.length > 0) {
      selectedCameraIds.value = enabledCameras.value.map((cam) => cam.id)
    }

    const runningCount = Object.values(cameraStore.runtimeStatus).filter((s: any) => s?.running).length
    message.success(`摄像头列表已刷新: 共 ${cameras.value.length} 个，已启用 ${enabledCameras.value.length} 个，运行中 ${runningCount} 个`)
  } catch (error: any) {
    console.error('刷新摄像头列表失败:', error)
    message.error('刷新失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function toggleFullscreen() {
  if (!isFullscreen.value) {
    // 进入全屏
    const container = document.querySelector('.realtime-monitor-container')
    if (container) {
      if ((container as any).requestFullscreen) {
        ;(container as any).requestFullscreen()
      } else if ((container as any).webkitRequestFullscreen) {
        ;(container as any).webkitRequestFullscreen()
      } else if ((container as any).mozRequestFullScreen) {
        ;(container as any).mozRequestFullScreen()
      } else if ((container as any).msRequestFullscreen) {
        ;(container as any).msRequestFullscreen()
      }
    }
  } else {
    // 退出全屏
    if (document.exitFullscreen) {
      document.exitFullscreen()
    } else if ((document as any).webkitExitFullscreen) {
      ;(document as any).webkitExitFullscreen()
    } else if ((document as any).mozCancelFullScreen) {
      ;(document as any).mozCancelFullScreen()
    } else if ((document as any).msExitFullscreen) {
      ;(document as any).msExitFullscreen()
    }
  }
}

// 监听全屏状态变化
function handleFullscreenChange() {
  isFullscreen.value = !!(
    document.fullscreenElement ||
    (document as any).webkitFullscreenElement ||
    (document as any).mozFullScreenElement ||
    (document as any).msFullscreenElement
  )
}

// 监听布局模式变化
watch(layoutMode, (newMode) => {
  if (newMode === 'single' && selectedCameraIds.value.length > 1) {
    selectedCameraIds.value = [selectedCameraIds.value[0]]
  }
})

// 生命周期
onMounted(async () => {
  try {
    // 先加载摄像头列表
    await cameraStore.fetchCameras()
    // 然后刷新摄像头运行状态
    await cameraStore.refreshRuntimeStatus()

    // 💡 优化：使用 nextTick 等待 DOM 和响应性更新完成
    // 确保所有计算属性基于最新的 store 状态完成计算
    await nextTick()

    console.log('摄像头列表加载完成:', {
      total: cameras.value.length,
      enabled: enabledCameras.value.length,
      cameras: cameras.value.map(c => ({
        id: c.id,
        name: c.name,
        enabled: c.enabled,
        active: c.active,
        running: cameraStore.runtimeStatus[c.id]?.running || false,
        isEnabled: c.enabled === true || c.active === true || cameraStore.runtimeStatus[c.id]?.running === true
      }))
    })

    // 默认选择所有启用的摄像头，如果没有启用的，则选择所有摄像头
    if (enabledCameras.value.length > 0) {
      selectedCameraIds.value = enabledCameras.value.map((cam) => cam.id)
      console.log('已选择启用的摄像头:', selectedCameraIds.value)

      // 检查是否有正在运行的摄像头
      const runningCameras = enabledCameras.value.filter(
        cam => cameraStore.runtimeStatus[cam.id]?.running
      )
      if (runningCameras.length === 0) {
        // 不显示警告，因为可能刚启动，摄像头还在连接中
        console.log('摄像头已启用但未运行，可能在启动中...')
      }
    } else if (cameras.value.length > 0) {
      // 如果没有启用的摄像头，选择所有摄像头（用户可以选择要查看的）
      selectedCameraIds.value = cameras.value.map((cam) => cam.id)
      console.log('没有启用的摄像头，已选择所有摄像头:', selectedCameraIds.value)
      // 不显示警告，因为用户可能想查看未启用的摄像头
    } else {
      console.log('摄像头列表为空')
    }
  } catch (error: any) {
    console.error('加载摄像头列表失败:', error)
    message.error('加载摄像头列表失败: ' + (error.message || '未知错误'))
  }

  // 监听全屏状态变化
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.addEventListener('mozfullscreenchange', handleFullscreenChange)
  document.addEventListener('MSFullscreenChange', handleFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
  document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
})
</script>

<style scoped>
.realtime-monitor-container {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 200px);
  width: 100%;
  padding: 16px;
}

.control-card {
  margin: 16px 0;
  flex-shrink: 0;
}

.video-grid-container {
  flex: 1;
  overflow: auto;
  background: var(--body-color);
}

.video-grid-container.fullscreen {
  padding: 0;
  background: #000;
}

.video-grid {
  display: grid;
  gap: 16px;
  height: 100%;
}

.video-item {
  position: relative;
  min-height: 300px;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-single {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 全屏模式样式 */
:fullscreen .video-grid-container,
:-webkit-full-screen .video-grid-container,
:-moz-full-screen .video-grid-container,
:-ms-fullscreen .video-grid-container {
  padding: 8px;
  background: #000;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .video-grid {
    grid-template-columns: 1fr !important;
  }

  .control-card {
    margin: 8px 0;
  }
}
</style>

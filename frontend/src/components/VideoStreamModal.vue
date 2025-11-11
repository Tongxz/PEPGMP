<template>
  <n-modal
    v-model:show="visible"
    :mask-closable="false"
    preset="card"
    :title="`📹 ${cameraName} - 实时画面`"
    style="width: 90%; max-width: 1200px"
    @after-leave="handleClose"
  >
    <template #header-extra>
      <n-space>
        <n-tag :type="connected ? 'success' : 'error'" size="small">
          {{ connected ? '🟢 已连接' : '⚪ 未连接' }}
        </n-tag>
        <n-button text @click="toggleFullscreen">
          <template #icon>
            <n-icon><ExpandOutline /></n-icon>
          </template>
          全屏
        </n-button>
      </n-space>
    </template>

    <div class="video-container">
      <!-- 视频显示区 -->
      <div ref="videoWrapper" class="video-wrapper">
        <img
          v-if="currentFrame"
          :src="currentFrame"
          alt="实时视频"
          class="video-frame"
        />
        <div v-else class="video-placeholder">
          <n-spin size="large" />
          <p style="margin-top: 16px; color: #fff">正在连接视频流...</p>
        </div>

        <!-- 覆盖层信息 -->
        <div v-if="currentFrame" class="video-overlay">
          <n-space>
            <n-tag size="small" :type="fpsColor">
              FPS: {{ currentFps.toFixed(1) }}
            </n-tag>
            <n-tag size="small" type="info">
              延迟: {{ latency.toFixed(1) }}s
            </n-tag>
            <n-tag size="small" type="default">
              帧数: {{ frameCount }}
            </n-tag>
          </n-space>
        </div>
      </div>

      <!-- 控制栏 -->
      <n-space justify="space-between" style="margin-top: 12px">
        <n-space>
          <n-button
            size="small"
            :type="paused ? 'primary' : 'default'"
            @click="togglePause"
            :disabled="!connected"
          >
            {{ paused ? '▶️ 继续' : '⏸️ 暂停' }}
          </n-button>
          <n-button size="small" @click="reconnect">
            🔄 重连
          </n-button>
        </n-space>

        <n-space align="center">
          <n-text depth="3" style="font-size: 12px">
            质量:
          </n-text>
          <n-select
            v-model:value="quality"
            size="small"
            :options="qualityOptions"
            style="width: 100px"
            disabled
          />
        </n-space>
      </n-space>

      <!-- 统计信息 -->
      <n-card size="small" style="margin-top: 12px" v-if="connected">
        <n-space>
          <n-statistic label="连接时长" :value="connectionDuration" />
          <n-statistic label="接收帧数" :value="frameCount" />
          <n-statistic label="平均FPS" :value="currentFps.toFixed(1)" />
        </n-space>
      </n-card>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import {
  NModal,
  NSpace,
  NTag,
  NButton,
  NIcon,
  NSpin,
  NText,
  NSelect,
  NCard,
  NStatistic,
  useMessage
} from 'naive-ui'
import { ExpandOutline } from '@vicons/ionicons5'

const props = defineProps<{
  cameraId: string
  cameraName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const message = useMessage()

// 状态
const visible = ref(true)
const connected = ref(false)
const currentFrame = ref<string | null>(null)
const frameCount = ref(0)
const currentFps = ref(0)
const latency = ref(0)
const paused = ref(false)
const quality = ref('medium')
const connectionStartTime = ref<number>(0)
const connectionDuration = ref('00:00')

// WebSocket
let ws: WebSocket | null = null
let lastFrameTime = 0
let fpsCounter = 0
let fpsInterval: number | null = null
let durationInterval: number | null = null
let frameQueue: string[] = []  // 帧队列，用于优化渲染
let isRendering = false  // 渲染状态标志

// 质量选项（暂时禁用，后续可扩展）
const qualityOptions = [
  { label: '低质量', value: 'low' },
  { label: '中等质量', value: 'medium' },
  { label: '高质量', value: 'high' },
]

const fpsColor = computed(() => {
  if (currentFps.value > 7) return 'success'
  if (currentFps.value > 4) return 'warning'
  return 'error'
})

const videoWrapper = ref<HTMLElement>()

// 连接WebSocket
function connect() {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/video-stream/ws/${props.cameraId}`

    console.log('连接视频流WebSocket:', wsUrl)

    ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      connected.value = true
      connectionStartTime.value = Date.now()
      message.success('视频流已连接')
      startFpsCounter()
      startDurationCounter()
    }

    ws.onmessage = (event) => {
      if (paused.value) return

      // 接收JPEG帧
      const blob = new Blob([event.data], { type: 'image/jpeg' })
      const url = URL.createObjectURL(blob)

      // 将帧加入队列（最多保留2帧，丢弃旧的）
      if (frameQueue.length >= 2) {
        const oldUrl = frameQueue.shift()
        if (oldUrl) {
          URL.revokeObjectURL(oldUrl)
        }
      }
      frameQueue.push(url)

      // 使用requestAnimationFrame优化渲染
      if (!isRendering) {
        requestAnimationFrame(() => {
          renderNextFrame()
        })
      }

      // 计算延迟
      const now = Date.now()
      if (lastFrameTime > 0) {
        latency.value = (now - lastFrameTime) / 1000
      }
      lastFrameTime = now

      // FPS计数
      fpsCounter++
    }

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      message.error('视频流连接错误')
    }

    ws.onclose = () => {
      connected.value = false
      stopFpsCounter()
      stopDurationCounter()
      message.warning('视频流已断开')
    }
  } catch (error) {
    console.error('创建WebSocket连接失败:', error)
    message.error('无法连接视频流')
  }
}

// 渲染下一帧（优化版本）
function renderNextFrame() {
  if (frameQueue.length === 0) {
    isRendering = false
    return
  }

  isRendering = true

  // 释放旧的URL
  if (currentFrame.value) {
    URL.revokeObjectURL(currentFrame.value)
  }

  // 获取最新帧（跳过中间帧以保持流畅）
  const url = frameQueue.pop() || frameQueue[0]
  if (url) {
    // 清空队列，只保留当前帧
    frameQueue.forEach(oldUrl => {
      if (oldUrl !== url) {
        URL.revokeObjectURL(oldUrl)
      }
    })
    frameQueue = [url]

    currentFrame.value = url
    frameCount.value++
  }

  isRendering = false

  // 如果还有新帧，继续渲染
  if (frameQueue.length > 1) {
    requestAnimationFrame(() => {
      renderNextFrame()
    })
  }
}

// FPS计数器
function startFpsCounter() {
  fpsInterval = window.setInterval(() => {
    currentFps.value = fpsCounter
    fpsCounter = 0
  }, 1000)
}

function stopFpsCounter() {
  if (fpsInterval) {
    clearInterval(fpsInterval)
    fpsInterval = null
  }
}

// 连接时长计数器
function startDurationCounter() {
  durationInterval = window.setInterval(() => {
    const elapsed = Math.floor((Date.now() - connectionStartTime.value) / 1000)
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    connectionDuration.value = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }, 1000)
}

function stopDurationCounter() {
  if (durationInterval) {
    clearInterval(durationInterval)
    durationInterval = null
  }
}

// 控制函数
function togglePause() {
  paused.value = !paused.value
  if (paused.value) {
    message.info('视频已暂停')
  } else {
    message.info('视频已继续')
  }
}

function reconnect() {
  if (ws) {
    ws.close()
  }
  currentFrame.value = null
  frameCount.value = 0
  currentFps.value = 0
  fpsCounter = 0
  connect()
}

function toggleFullscreen() {
  const elem = videoWrapper.value
  if (!elem) return

  if (!document.fullscreenElement) {
    elem.requestFullscreen().catch(err => {
      message.error(`全屏模式失败: ${err.message}`)
    })
  } else {
    document.exitFullscreen()
  }
}

function handleClose() {
  emit('close')
}

// 生命周期
watch(visible, (val) => {
  if (val) {
    connect()
  } else {
    if (ws) {
      ws.close()
      ws = null
    }
  }
})

onBeforeUnmount(() => {
  if (ws) {
    ws.close()
  }
  stopFpsCounter()
  stopDurationCounter()
  if (currentFrame.value) {
    URL.revokeObjectURL(currentFrame.value)
  }
  // 清理帧队列
  frameQueue.forEach(url => {
    URL.revokeObjectURL(url)
  })
  frameQueue = []
})
</script>

<style scoped>
.video-container {
  position: relative;
}

.video-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-frame {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #fff;
}

.video-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.6);
  padding: 8px;
  border-radius: 4px;
}
</style>

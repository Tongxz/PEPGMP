<template>
  <div class="video-stream-card" :class="{ 'full-size': fullSize }">
    <!-- 摄像头标题栏 -->
    <div class="video-header">
      <n-space justify="space-between" align="center">
        <n-space align="center">
          <n-tag :type="connected ? 'success' : 'error'" size="small">
            {{ connected ? '🟢 已连接' : '⚪ 未连接' }}
          </n-tag>
          <n-text strong>{{ cameraName }}</n-text>
          <n-text depth="3" style="font-size: 12px">{{ cameraId }}</n-text>
          <n-tooltip v-if="!connected" trigger="hover">
            <template #trigger>
              <n-icon :size="16" style="cursor: help; color: var(--error-color)">
                <WarningOutline />
              </n-icon>
            </template>
            <span style="white-space: pre-line;">
              未连接到视频流服务器，请检查：{'\n'}
              1. 摄像头是否正在运行{'\n'}
              2. 后端服务是否正常{'\n'}
              3. 网络连接是否正常{'\n'}
              4. 查看浏览器控制台获取详细错误信息
            </span>
          </n-tooltip>
        </n-space>
        <n-space>
          <n-tag v-if="currentFps > 0" size="small" :type="fpsColor">
            FPS: {{ currentFps.toFixed(1) }}
          </n-tag>
          <n-tag v-else-if="connected" size="small" type="warning">
            等待数据...
          </n-tag>
          <n-tag v-if="latency > 0" size="small" type="info">
            延迟: {{ latency.toFixed(1) }}s
          </n-tag>
        </n-space>
      </n-space>
    </div>

    <!-- 视频显示区 -->
    <div class="video-wrapper" ref="videoWrapper">
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
    </div>

    <!-- 控制栏 -->
    <div class="video-controls">
      <n-space justify="space-between" align="center">
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
        <n-text depth="3" style="font-size: 12px">
          帧数: {{ frameCount }}
        </n-text>
      </n-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { NSpace, NTag, NText, NButton, NSpin, NIcon, NTooltip, useMessage } from 'naive-ui'
import { WarningOutline } from '@vicons/ionicons5'

const message = useMessage()

// Props
interface Props {
  cameraId: string
  cameraName: string
  fullSize?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  fullSize: false,
})

// Emits
const emit = defineEmits<{
  connected: []
  disconnected: []
}>()

// 响应式数据
const connected = ref(false)
const paused = ref(false)
const currentFrame = ref<string | null>(null)
const currentFps = ref(0)
const latency = ref(0)
const frameCount = ref(0)
const connectionStartTime = ref(0)

// WebSocket
let ws: WebSocket | null = null
let lastFrameTime = 0
let fpsCounter = 0
let fpsInterval: number | null = null
let heartbeatInterval: number | null = null
let frameQueue: string[] = []
let isRendering = false

const videoWrapper = ref<HTMLElement>()

const fpsColor = computed(() => {
  if (currentFps.value > 7) return 'success'
  if (currentFps.value > 4) return 'warning'
  return 'error'
})

// 连接WebSocket
function connect() {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/video-stream/ws/${props.cameraId}`

    console.log(`[VideoStreamCard] 正在连接摄像头 ${props.cameraId} 的视频流:`, wsUrl)

    ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      console.log(`[VideoStreamCard] WebSocket连接成功: ${props.cameraId}`)
      connected.value = true
      connectionStartTime.value = Date.now()
      emit('connected')
      startFpsCounter()

      // 启动心跳检测（每30秒发送一次ping）
      startHeartbeat()
    }

    ws.onmessage = (event) => {
      if (paused.value) return

      // 检查是否是文本消息（心跳响应）
      if (typeof event.data === 'string') {
        if (event.data === 'pong') {
          console.debug(`[VideoStreamCard] 收到心跳响应: ${props.cameraId}`)
        }
        return
      }

      // 处理二进制数据（JPEG帧）
      try {
        const blob = new Blob([event.data], { type: 'image/jpeg' })
        const url = URL.createObjectURL(blob)

        if (frameQueue.length >= 2) {
          const oldUrl = frameQueue.shift()
          if (oldUrl) {
            URL.revokeObjectURL(oldUrl)
          }
        }
        frameQueue.push(url)

        if (!isRendering) {
          requestAnimationFrame(() => {
            renderNextFrame()
          })
        }

        const now = Date.now()
        if (lastFrameTime > 0) {
          latency.value = (now - lastFrameTime) / 1000
        }
        lastFrameTime = now
        fpsCounter++
      } catch (error) {
        console.error(`[VideoStreamCard] 处理视频帧失败 (${props.cameraId}):`, error)
      }
    }

    ws.onerror = (error) => {
      console.error(`[VideoStreamCard] WebSocket错误 (${props.cameraId}):`, error)
      console.error(`[VideoStreamCard] WebSocket状态:`, ws?.readyState)
      console.error(`[VideoStreamCard] WebSocket URL:`, wsUrl)
      connected.value = false
      stopFpsCounter()
      stopHeartbeat()
      emit('disconnected')
    }

    ws.onclose = (event) => {
      console.log(`[VideoStreamCard] WebSocket连接关闭 (${props.cameraId}):`, {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      })
      connected.value = false
      stopFpsCounter()
      stopHeartbeat()
      emit('disconnected')

      // 如果不是正常关闭，尝试重连（延迟5秒）
      if (event.code !== 1000) {
        console.log(`[VideoStreamCard] 连接异常关闭，5秒后尝试重连: ${props.cameraId}`)
        setTimeout(() => {
          if (!connected.value) {
            console.log(`[VideoStreamCard] 尝试重连: ${props.cameraId}`)
            reconnect()
          }
        }, 5000)
      }
    }
  } catch (error) {
    console.error(`[VideoStreamCard] 创建WebSocket连接失败 (${props.cameraId}):`, error)
    connected.value = false
    emit('disconnected')
  }
}

function renderNextFrame() {
  if (frameQueue.length === 0) {
    isRendering = false
    return
  }

  isRendering = true

  if (currentFrame.value) {
    URL.revokeObjectURL(currentFrame.value)
  }

  const url = frameQueue.pop() || frameQueue[0]
  if (url) {
    frameQueue.forEach((oldUrl) => {
      if (oldUrl !== url) {
        URL.revokeObjectURL(oldUrl)
      }
    })
    frameQueue = [url]
    currentFrame.value = url
    frameCount.value++
  }

  isRendering = false

  if (frameQueue.length > 1) {
    requestAnimationFrame(() => {
      renderNextFrame()
    })
  }
}

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

function startHeartbeat() {
  // 每30秒发送一次心跳
  heartbeatInterval = window.setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send('ping')
        console.debug(`[VideoStreamCard] 发送心跳: ${props.cameraId}`)
      } catch (error) {
        console.error(`[VideoStreamCard] 发送心跳失败: ${props.cameraId}`, error)
      }
    }
  }, 30000)
}

function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
    heartbeatInterval = null
  }
}

function togglePause() {
  paused.value = !paused.value
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

// 生命周期
onMounted(() => {
  connect()
})

onBeforeUnmount(() => {
  stopHeartbeat()
  stopFpsCounter()
  if (ws) {
    ws.close(1000, 'Component unmounting')
    ws = null
  }
  if (currentFrame.value) {
    URL.revokeObjectURL(currentFrame.value)
    currentFrame.value = null
  }
  frameQueue.forEach((url) => {
    URL.revokeObjectURL(url)
  })
  frameQueue = []
})
</script>

<style scoped>
.video-stream-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.video-stream-card.full-size {
  width: 100%;
  height: 100%;
}

.video-header {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.8);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.video-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #000;
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
  color: #fff;
  width: 100%;
  height: 100%;
}

.video-controls {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.8);
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}
</style>

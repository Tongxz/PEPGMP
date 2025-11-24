<template>
  <div class="video-stream-card" :class="{ 'full-size': fullSize }">
    <!-- 摄像头标题栏 -->
    <div class="video-header">
      <div class="header-wrap-container">
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
            帧间隔: {{ latency.toFixed(1) }}s
          </n-tag>
        </n-space>
      </div>
    </div>

    <!-- 视频显示区 -->
    <div class="video-wrapper" ref="videoWrapper">
      <canvas
        ref="canvasRef"
        class="video-frame"
        v-show="hasFirstFrame"
      ></canvas>
      <div v-if="!hasFirstFrame" class="video-placeholder">
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
          <n-button size="small" @click="showConfigModal = true">
            ⚙️ 配置
          </n-button>
        </n-space>
        <n-text depth="3" style="font-size: 12px">
          帧数: {{ frameCount }}
        </n-text>
      </n-space>
    </div>

    <!-- 配置对话框 -->
    <n-modal
      v-model:show="showConfigModal"
      preset="card"
      title="视频流配置"
      style="width: 500px"
      :bordered="false"
      size="small"
    >
      <n-form
        :model="configForm"
        label-placement="left"
        label-width="120px"
        :show-feedback="false"
      >
        <n-form-item label="检测帧率" path="stream_interval">
          <n-slider
            v-model:value="configForm.stream_interval"
            :min="1"
            :max="30"
            :step="1"
            :marks="streamIntervalMarks"
            :disabled="configForm.frame_by_frame"
          />
          <n-text depth="3" style="margin-left: 12px; font-size: 12px">
            {{ configForm.stream_interval }} 帧/次
          </n-text>
        </n-form-item>

        <n-form-item label="检测间隔" path="log_interval">
          <n-input-number
            v-model:value="configForm.log_interval"
            :min="1"
            :max="1000"
            :step="10"
            style="width: 100%"
          />
          <n-text depth="3" style="margin-left: 12px; font-size: 12px">
            每 {{ configForm.log_interval }} 帧检测一次
          </n-text>
        </n-form-item>

        <n-form-item label="逐帧模式" path="frame_by_frame">
          <n-switch v-model:value="configForm.frame_by_frame" />
          <n-text depth="3" style="margin-left: 12px; font-size: 12px">
            {{ configForm.frame_by_frame ? '开启（最高帧率）' : '关闭（使用检测帧率）' }}
          </n-text>
        </n-form-item>

        <n-form-item label="当前配置">
          <n-space vertical size="small">
            <n-text depth="3" style="font-size: 12px">
              推送间隔: {{ currentConfig.stream_interval }} 帧
            </n-text>
            <n-text depth="3" style="font-size: 12px">
              检测间隔: {{ currentConfig.log_interval }} 帧
            </n-text>
            <n-text depth="3" style="font-size: 12px">
              逐帧模式: {{ currentConfig.frame_by_frame ? '开启' : '关闭' }}
            </n-text>
          </n-space>
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showConfigModal = false">取消</n-button>
          <n-button type="primary" @click="saveConfig" :loading="savingConfig">
            保存
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  NSpace,
  NTag,
  NText,
  NButton,
  NSpin,
  NIcon,
  NTooltip,
  NModal,
  NForm,
  NFormItem,
  NSlider,
  NInputNumber,
  NSwitch,
  useMessage
} from 'naive-ui'
import { WarningOutline } from '@vicons/ionicons5'
import { videoStreamApi, type VideoStreamConfig, type VideoStreamConfigRequest } from '../api/videoStream'

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
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hasFirstFrame = ref(false)
const currentFps = ref(0)
const latency = ref(0)
const frameCount = ref(0)
const connectionStartTime = ref(0)
const reconnectAttempts = ref(0)
const MAX_RECONNECT_ATTEMPTS = 10 // 最大重连次数

// Canvas 上下文
let ctx: CanvasRenderingContext2D | null = null
let pendingFrame: ImageBitmap | null = null

// 配置相关
const showConfigModal = ref(false)
const savingConfig = ref(false)
const currentConfig = ref<VideoStreamConfig>({
  camera_id: props.cameraId,
  stream_interval: 3,
  log_interval: 120,
  frame_by_frame: false,
})

// 配置表单（所有字段必需，用于表单绑定）
interface ConfigForm {
  stream_interval: number
  log_interval: number
  frame_by_frame: boolean
}

const configForm = ref<ConfigForm>({
  stream_interval: 3,
  log_interval: 120,
  frame_by_frame: false,
})

// 检测帧率标记
const streamIntervalMarks = computed(() => {
  return {
    1: '1',
    5: '5',
    10: '10',
    15: '15',
    20: '20',
    25: '25',
    30: '30',
  }
})

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
      reconnectAttempts.value = 0 // 💡 优化：连接成功后重置重连尝试次数
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

        // 💡 优化 1：使用 createImageBitmap 替代 URL.createObjectURL
        // 异步创建位图，性能更好且无需手动管理 URL 生命周期
        createImageBitmap(blob).then(bitmap => {
          // 流量控制：如果有积压的帧，关闭旧的，保留新的
          if (pendingFrame) {
            pendingFrame.close()
          }
          pendingFrame = bitmap

          if (!isRendering) {
            requestAnimationFrame(renderLoop)
          }
        }).catch(err => {
          console.error(`[VideoStreamCard] 创建位图失败:`, err)
        })

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

      // 💡 优化 2：如果不是正常关闭，且重试次数未达上限，尝试重连（延迟5秒）
      if (event.code !== 1000 && reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS) {
        console.log(`[VideoStreamCard] 连接异常关闭，5秒后尝试重连 (${reconnectAttempts.value + 1}/${MAX_RECONNECT_ATTEMPTS}): ${props.cameraId}`)
        reconnectAttempts.value++ // 增加尝试次数
        setTimeout(() => {
          if (!connected.value) {
            reconnect() // reconnect 函数内部会调用 connect()
          }
        }, 5000)
      } else if (event.code !== 1000) {
        console.error(`[VideoStreamCard] 已达到最大重连次数 (${MAX_RECONNECT_ATTEMPTS} 次)，停止重试: ${props.cameraId}`)
      }
    }
  } catch (error) {
    console.error(`[VideoStreamCard] 创建WebSocket连接失败 (${props.cameraId}):`, error)
    connected.value = false
    emit('disconnected')
  }
}

function renderLoop() {
  if (!pendingFrame || !canvasRef.value) {
    isRendering = false
    return
  }

  isRendering = true
  const canvas = canvasRef.value

  // 初始化上下文
  if (!ctx) {
    ctx = canvas.getContext('2d', { alpha: false }) // alpha: false 优化性能
  }

  if (ctx && pendingFrame) {
    // 💡 优化：自动调整 Canvas 分辨率以匹配视频源
    // 这确保了绘制清晰度，同时由 CSS 控制显示大小
    if (canvas.width !== pendingFrame.width || canvas.height !== pendingFrame.height) {
      canvas.width = pendingFrame.width
      canvas.height = pendingFrame.height
    }

    // 绘制帧
    ctx.drawImage(pendingFrame, 0, 0)

    // 释放位图资源（关键！防止显存泄漏）
    pendingFrame.close()
    pendingFrame = null

    // 标记已收到首帧
    if (!hasFirstFrame.value) {
      hasFirstFrame.value = true
    }

    frameCount.value++
  }

  isRendering = false

  // 如果在渲染期间又有新帧到达（虽然我们主要靠 onmessage 触发，但检查一下是个好习惯）
  if (pendingFrame) {
     requestAnimationFrame(renderLoop)
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
  // 重置状态
  hasFirstFrame.value = false
  if (pendingFrame) {
    pendingFrame.close()
    pendingFrame = null
  }
  // 清空 Canvas
  if (ctx && canvasRef.value) {
    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  }

  frameCount.value = 0
  currentFps.value = 0
  fpsCounter = 0
  // 💡 优化：手动重连时重置重连次数（允许重新尝试）
  reconnectAttempts.value = 0
  connect()
}

// 加载配置
async function loadConfig() {
  try {
    const config = await videoStreamApi.getConfig(props.cameraId)
    currentConfig.value = config
    configForm.value = {
      stream_interval: config.stream_interval,
      log_interval: config.log_interval,
      frame_by_frame: config.frame_by_frame,
    }
    console.log(`[VideoStreamCard] 加载配置成功:`, config)
  } catch (error) {
    console.error(`[VideoStreamCard] 加载配置失败:`, error)
    message.error('加载配置失败')
  }
}

// 保存配置
async function saveConfig() {
  try {
    savingConfig.value = true

    // 如果开启逐帧模式，确保stream_interval为1
    if (configForm.value.frame_by_frame) {
      configForm.value.stream_interval = 1
    }

    // 转换为API请求格式（可选字段）
    const request: VideoStreamConfigRequest = {
      stream_interval: configForm.value.stream_interval,
      log_interval: configForm.value.log_interval,
      frame_by_frame: configForm.value.frame_by_frame,
    }

    const response = await videoStreamApi.updateConfig(props.cameraId, request)
    currentConfig.value = {
      camera_id: response.camera_id,
      stream_interval: response.stream_interval,
      log_interval: response.log_interval,
      frame_by_frame: response.frame_by_frame,
    }

    message.success('配置已保存，检测进程将在下次读取时应用新配置')
    showConfigModal.value = false
    console.log(`[VideoStreamCard] 保存配置成功:`, response)
  } catch (error) {
    console.error(`[VideoStreamCard] 保存配置失败:`, error)
    message.error('保存配置失败')
  } finally {
    savingConfig.value = false
  }
}

// 监听逐帧模式变化
watch(
  () => configForm.value.frame_by_frame,
  (newVal) => {
    if (newVal) {
      configForm.value.stream_interval = 1
    }
  }
)

// 监听配置对话框显示，加载配置
watch(
  () => showConfigModal.value,
  (newVal) => {
    if (newVal) {
      // 打开对话框时重新加载配置，确保显示最新配置
      loadConfig()
    }
  }
)

// 生命周期
onMounted(() => {
  connect()
  loadConfig()
})

onBeforeUnmount(() => {
  stopHeartbeat()
  stopFpsCounter()
  if (ws) {
    ws.close(1000, 'Component unmounting')
    ws = null
  }

  // 清理 Canvas 资源
  if (pendingFrame) {
    pendingFrame.close()
    pendingFrame = null
  }
  ctx = null
  hasFirstFrame.value = false
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

/* 💡 优化：响应式布局容器，支持自动换行 */
.header-wrap-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
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

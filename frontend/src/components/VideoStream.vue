<template>
  <div class="video-stream-container">
    <!-- Canvas用于显示视频帧 -->
    <canvas
      ref="canvasRef"
      class="video-canvas"
      :class="{ 'canvas-loading': status === 'connecting' }"
    ></canvas>

    <!-- 连接状态覆盖层 -->
    <div v-if="status !== 'connected'" class="video-overlay-status">
      <div class="status-content">
        <n-spin v-if="status === 'connecting'" size="large" />
        <n-icon v-else-if="status === 'error'" size="48" color="#FF4D4F">
          <AlertCircleOutline />
        </n-icon>
        <n-icon v-else size="48" color="#8C9BAB">
          <VideocamOffOutline />
        </n-icon>

        <p class="status-text">{{ statusText }}</p>
        <p v-if="error" class="error-text">{{ error }}</p>

        <n-button
          v-if="status === 'disconnected' || status === 'error'"
          type="primary"
          size="small"
          @click="handleReconnect"
        >
          重新连接
        </n-button>
      </div>
    </div>

    <!-- 视频信息覆盖层（连接成功时显示） -->
    <div v-if="status === 'connected'" class="video-info-overlay">
      <div class="video-status-badge" :class="`status-${status}`">
        <div class="status-dot"></div>
        <span>{{ statusText }}</span>
      </div>
      <div v-if="showFps && fps > 0" class="fps-badge">
        {{ fps }} FPS
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { NSpin, NButton, NIcon } from 'naive-ui'
import { VideocamOffOutline, AlertCircleOutline } from '@vicons/ionicons5'
import { useVideoStream } from '@/composables/useVideoStream'

const props = withDefaults(defineProps<{
  cameraId: string
  autoConnect?: boolean
  showFps?: boolean
  width?: number
  height?: number
}>(), {
  autoConnect: true,
  showFps: true,
  width: 640,
  height: 360
})

const canvasRef = ref<HTMLCanvasElement>()
const { status, error, fps, connect, disconnect, onFrame, resetReconnectAttempts } = useVideoStream(
  props.cameraId,
  { autoConnect: false }
)

const statusText = computed(() => {
  switch (status.value) {
    case 'connecting': return '连接中...'
    case 'connected': return '播放中'
    case 'disconnected': return '未连接'
    case 'error': return '连接错误'
    default: return '未知状态'
  }
})

// 绘制视频帧到Canvas
const drawFrame = (frameBase64: string) => {
  if (!canvasRef.value) return

  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const img = new Image()
  img.onload = () => {
    // 设置canvas尺寸（首次）
    if (canvas.width === 0 || canvas.height === 0) {
      canvas.width = img.width
      canvas.height = img.height
    }

    // 绘制图片
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  }
  img.onerror = (err) => {
    console.error('图片加载失败:', err)
  }
  img.src = `data:image/jpeg;base64,${frameBase64}`
}

// 重新连接
const handleReconnect = () => {
  resetReconnectAttempts()
  connect()
}

// 注册帧回调
onMounted(() => {
  // 设置canvas初始尺寸
  if (canvasRef.value) {
    canvasRef.value.width = props.width
    canvasRef.value.height = props.height
  }

  // 注册帧回调
  onFrame(drawFrame)

  // 自动连接
  if (props.autoConnect) {
    connect()
  }
})

// 监听cameraId变化，重新连接
watch(() => props.cameraId, (newId, oldId) => {
  if (newId !== oldId) {
    disconnect()
    setTimeout(() => {
      connect()
    }, 100)
  }
})

// 暴露方法给父组件
defineExpose({
  connect,
  disconnect,
  status,
  fps
})
</script>

<style scoped lang="scss">
.video-stream-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;

  &.canvas-loading {
    opacity: 0.5;
  }
}

.video-overlay-status {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
}

.status-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 24px;
  text-align: center;
}

.status-text {
  font-size: 16px;
  font-weight: 500;
  color: #FFFFFF;
  margin: 0;
}

.error-text {
  font-size: 14px;
  color: #FF7875;
  margin: 0;
  max-width: 300px;
}

.video-info-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  pointer-events: none;
}

.video-status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  backdrop-filter: blur(8px);

  &.status-connected {
    background: rgba(82, 196, 26, 0.9);
    color: white;
  }

  &.status-connecting {
    background: rgba(255, 169, 64, 0.9);
    color: white;
  }

  &.status-disconnected,
  &.status-error {
    background: rgba(255, 77, 79, 0.9);
    color: white;
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.fps-badge {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  font-family: 'Monaco', 'Courier New', monospace;
  background: rgba(0, 0, 0, 0.7);
  color: #52C41A;
  backdrop-filter: blur(8px);
}
</style>

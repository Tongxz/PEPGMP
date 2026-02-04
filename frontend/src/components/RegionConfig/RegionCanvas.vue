<template>
  <div class="region-canvas-container">
    <!-- 工具栏 -->
    <div class="canvas-toolbar">
      <n-space align="center" justify="space-between">
        <n-space align="center" size="small">
          <!-- 显示选项 -->
          <n-space size="small">
            <n-checkbox
              :checked="showGrid"
              size="small"
              @update:checked="(value: boolean) => emit('update:showGrid', value)"
            >
              网格
            </n-checkbox>
            <n-checkbox
              :checked="showLabels"
              size="small"
              @update:checked="(value: boolean) => emit('update:showLabels', value)"
            >
              标签
            </n-checkbox>
            <n-checkbox
              :checked="showCoordinates"
              size="small"
              @update:checked="(value: boolean) => emit('update:showCoordinates', value)"
            >
              坐标
            </n-checkbox>
          </n-space>
        </n-space>

        <n-space align="center" size="small">
          <!-- 画布状态 -->
          <n-tag
            v-if="isDrawing"
            type="info"
            size="small"
          >
            <template #icon>
              <n-icon><BrushOutline /></n-icon>
            </template>
            绘制模式
          </n-tag>

          <n-tag
            v-if="selectedRegionId"
            type="success"
            size="small"
          >
            <template #icon>
              <n-icon><CheckmarkCircleOutline /></n-icon>
            </template>
            已选择区域
          </n-tag>

          <!-- 清除所有 -->
          <n-button
            v-if="regions.length > 0"
            size="small"
            type="error"
            @click="$emit('clearAll')"
          >
            <template #icon>
              <n-icon><TrashOutline /></n-icon>
            </template>
            清除所有
          </n-button>
        </n-space>
      </n-space>
    </div>

    <!-- 画布主体 -->
    <div class="canvas-main" ref="canvasContainer">
      <canvas
        ref="canvas"
        class="region-canvas"
        @mousedown="handleCanvasMouseDown"
        @mousemove="handleCanvasMouseMove"
        @mouseup="handleCanvasMouseUp"
        @dblclick.stop="handleCanvasDoubleClick"
        @wheel="handleCanvasWheel"
        @contextmenu.prevent
      ></canvas>

      <!-- 画布覆盖层 -->
      <div class="canvas-overlay">
        <!-- 坐标显示 -->
        <div
          v-if="showCoordinates && mousePosition"
          class="coordinate-display"
          :style="{
            left: mousePosition.x + 10 + 'px',
            top: mousePosition.y - 30 + 'px'
          }"
        >
          ({{ mousePosition.canvasX.toFixed(0) }}, {{ mousePosition.canvasY.toFixed(0) }})
        </div>

        <!-- 绘制提示 -->
        <div
          v-if="isDrawing && currentPoints.length > 0"
          class="drawing-hint"
        >
          点击继续绘制，双击完成
        </div>

        <!-- 空状态 -->
        <div
          v-if="!backgroundImage && !selectedCamera"
          class="empty-state"
        >
          <n-icon size="48" color="#d0d0d0">
            <ImageOutline />
          </n-icon>
          <n-text depth="2" style="margin-top: 8px;">
            请先选择摄像头或上传背景图片
          </n-text>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import type { Region } from '@/api/region'
import { RegionConfigManager } from '@/utils/RegionConfigManager'

// Icons
import {
  BrushOutline,
  CheckmarkCircleOutline,
  TrashOutline,
  ImageOutline,
} from '@vicons/ionicons5'

// Props
interface Props {
  regions: Region[]
  selectedRegionId?: string
  backgroundImage?: HTMLImageElement | null
  selectedCamera?: string
  isDrawing: boolean
  currentPoints: Array<{ x: number; y: number }>
  showGrid: boolean
  showLabels: boolean
  showCoordinates: boolean
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  canvasClick: [point: { x: number; y: number }]
  canvasDoubleClick: []
  regionSelect: [regionId: string]
  mouseMove: [position: any]
  'update:showGrid': [value: boolean]
  'update:showLabels': [value: boolean]
  'update:showCoordinates': [value: boolean]
  clearAll: []
}>()

// Refs
const canvas = ref<HTMLCanvasElement>()
const canvasContainer = ref<HTMLElement>()

// State
const mousePosition = ref<{
  x: number
  y: number
  canvasX: number
  canvasY: number
} | null>(null)

// Canvas manager
let canvasManager: RegionConfigManager | null = null

// Watchers
watch(() => props.backgroundImage, (newImage) => {
  if (canvasManager && newImage) {
    canvasManager.setBackgroundImage(newImage)
    resizeCanvas()
  }
}, { immediate: true })

watch(() => props.regions, () => {
  if (canvasManager) {
    canvasManager.clearRegions()
    canvasManager.importConfig({ regions: props.regions })
    drawCanvas()
  }
}, { deep: true })

watch(() => props.currentPoints, () => {
  // currentPoints will be updated through drawing operations
  drawCanvas()
}, { deep: true })

watch(() => props.selectedRegionId, (newId) => {
  if (canvasManager) {
    canvasManager.setSelectedRegionId(newId || '')
    drawCanvas()
  }
})

watch(() => [props.showGrid, props.showLabels, props.showCoordinates], () => {
  if (canvasManager) {
    canvasManager.setDisplayOptions({
      showGrid: props.showGrid,
      showLabels: props.showLabels,
      showCoordinates: props.showCoordinates,
    })
    drawCanvas()
  }
})

// Methods
const resizeCanvas = () => {
  if (!canvas.value || !canvasContainer.value) return

  const container = canvasContainer.value
  const canvasEl = canvas.value

  // Set canvas size to match container
  const rect = container.getBoundingClientRect()
  canvasEl.width = rect.width
  canvasEl.height = rect.height

  // Redraw after resize
  drawCanvas()
}

const drawCanvas = () => {
  if (!canvasManager) return
  canvasManager.render()
}

const getCanvasCoordinates = (event: MouseEvent): { x: number; y: number } => {
  if (!canvas.value) return { x: 0, y: 0 }

  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvas.value.width / rect.width
  const scaleY = canvas.value.height / rect.height

  return {
    x: (event.clientX - rect.left) * scaleX,
    y: (event.clientY - rect.top) * scaleY,
  }
}

// Event handlers
const handleCanvasMouseDown = (event: MouseEvent) => {
  const point = getCanvasCoordinates(event)
  emit('canvasClick', point)
}

const handleCanvasMouseMove = (event: MouseEvent) => {
  if (!canvas.value) return

  const rect = canvas.value.getBoundingClientRect()
  const point = getCanvasCoordinates(event)

  mousePosition.value = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
    canvasX: point.x,
    canvasY: point.y,
  }

  emit('mouseMove', mousePosition.value)
}

const handleCanvasMouseUp = (event: MouseEvent) => {
  // Handle mouse up if needed
}

const handleCanvasDoubleClick = () => {
  emit('canvasDoubleClick')
}

const handleCanvasWheel = (event: WheelEvent) => {
  event.preventDefault()
  // Handle zoom if needed
}

// Lifecycle
onMounted(async () => {
  await nextTick()

  if (canvas.value && canvasContainer.value) {
    canvasManager = new RegionConfigManager(canvas.value)

    // Initialize canvas manager
    canvasManager.importConfig({ regions: props.regions })
    canvasManager.selectRegion(props.selectedRegionId || null)

    if (props.backgroundImage) {
      canvasManager.setBackgroundImage(props.backgroundImage)
    }

    // Resize and draw
    resizeCanvas()

    // Add resize listener
    window.addEventListener('resize', resizeCanvas)
  }
})

onUnmounted(() => {
  canvasManager = null
  window.removeEventListener('resize', resizeCanvas)
})

// Expose methods
defineExpose({
  resizeCanvas,
  drawCanvas,
})
</script>

<style scoped>
.region-canvas-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.canvas-toolbar {
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.canvas-main {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.region-canvas {
  width: 100%;
  height: 100%;
  cursor: crosshair;
  display: block;
}

.canvas-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.coordinate-display {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  pointer-events: none;
  z-index: 1000;
}

.drawing-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(24, 144, 255, 0.9);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  pointer-events: none;
  z-index: 1000;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
  z-index: 100;
}
</style>

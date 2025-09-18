<template>
  <div class="region-config-page">
    <!-- 操作引导提示 -->
    <n-alert
      v-if="showGuide && !selectedCamera"
      type="info"
      closable
      @close="showGuide = false"
      class="guide-alert"
    >
      <template #icon>
        <n-icon><InformationCircleOutline /></n-icon>
      </template>
      <template #header>配置向导</template>
      <div class="guide-content">
        <p>欢迎使用区域配置功能！请按以下步骤操作：</p>
        <ol>
          <li>首先选择要配置的摄像头</li>
          <li>在预览画面中绘制检测区域</li>
          <li>设置区域类型和检测参数</li>
          <li>保存配置并测试效果</li>
        </ol>
      </div>
    </n-alert>

    <!-- 页面头部 -->
    <PageHeader
      title="区域配置"
      subtitle="配置检测区域和规则设置"
      icon="🎯"
    >
      <template #actions>
        <n-space>
          <!-- 批量操作 -->
          <n-dropdown
            v-if="regions.length > 0"
            :options="batchOptions"
            @select="handleBatchAction"
            trigger="click"
          >
            <n-button>
              <template #icon>
                <n-icon><LayersOutline /></n-icon>
              </template>
              批量操作
              <template #suffix>
                <n-icon><ChevronDownOutline /></n-icon>
              </template>
            </n-button>
          </n-dropdown>

          <!-- 导入/导出 -->
          <n-button @click="exportConfig">
            <template #icon>
              <n-icon><DownloadOutline /></n-icon>
            </template>
            导出配置
          </n-button>

          <n-upload
            :show-file-list="false"
            accept=".json"
            @change="importConfig"
          >
            <n-button>
              <template #icon>
                <n-icon><CloudUploadOutline /></n-icon>
              </template>
              导入配置
            </n-button>
          </n-upload>

          <n-button @click="loadExistingConfig">
            <template #icon>
              <n-icon><SettingsOutline /></n-icon>
            </template>
            加载已有配置
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 主要内容区域 -->
    <div class="region-config-content">
      <div class="config-panels">
        <!-- 左侧配置面板 -->
        <div class="left-panel">
          <!-- 摄像头选择 -->
          <DataCard title="摄像头选择" class="camera-select-card">
            <template #extra>
              <n-button size="small" quaternary @click="refreshCameras">
                <template #icon>
                  <n-icon><RefreshOutline /></n-icon>
                </template>
                刷新
              </n-button>
            </template>

            <n-select
              v-model:value="selectedCamera"
              :options="cameraOptions"
              placeholder="选择要配置的摄像头"
              @update:value="onCameraChange"
              size="large"
              filterable
            />

            <!-- 摄像头信息 -->
            <div v-if="selectedCamera" class="camera-info">
              <n-space vertical size="small">
                <n-text depth="3">
                  <n-icon><VideocamOutline /></n-icon>
                  分辨率: {{ getCameraResolution(selectedCamera) }}
                </n-text>
                <n-text depth="3">
                  <n-icon><LocationOutline /></n-icon>
                  位置: {{ getCameraLocation(selectedCamera) }}
                </n-text>
              </n-space>
            </div>
          </DataCard>

          <!-- 区域配置 -->
          <DataCard title="检测区域" class="region-config-card" v-if="selectedCamera">
            <template #extra>
              <n-space>
                <n-tag type="info" size="small">
                  {{ regions.length }} 个区域
                </n-tag>
                <n-button size="small" type="primary" @click="startDrawingMode">
                  <template #icon>
                    <n-icon><AddOutline /></n-icon>
                  </template>
                  绘制区域
                </n-button>
              </n-space>
            </template>

            <div class="regions-list">
              <div
                v-for="region in regions"
                :key="region.id"
                class="region-item"
                :class="{
                  active: selectedRegion?.id === region.id,
                  disabled: !region.enabled
                }"
                @click="selectRegion(region)"
                @mouseenter="hoveredRegion = region"
                @mouseleave="hoveredRegion = null"
              >
                <div class="region-header">
                  <n-space align="center" justify="space-between">
                    <div class="region-info">
                      <n-text strong>{{ region.name || `区域 ${region.id}` }}</n-text>
                      <n-tag
                        :type="getRegionTypeColor(region.type)"
                        size="small"
                        style="margin-left: 8px;"
                      >
                        {{ getRegionTypeText(region.type) }}
                      </n-tag>
                    </div>

                    <n-space size="small">
                      <n-button size="tiny" quaternary @click.stop="editRegion(region)">
                        <template #icon>
                          <n-icon><CreateOutline /></n-icon>
                        </template>
                      </n-button>
                      <n-button size="tiny" quaternary type="error" @click.stop="deleteRegion(region.id)">
                        <template #icon>
                          <n-icon><TrashOutline /></n-icon>
                        </template>
                      </n-button>
                    </n-space>
                  </n-space>
                </div>

                <div class="region-details">
                  <n-space size="small">
                    <n-text depth="3" style="font-size: 12px;">
                      坐标: ({{ region.x }}, {{ region.y }}) - {{ region.width }}×{{ region.height }}
                    </n-text>
                    <n-text depth="3" style="font-size: 12px;">
                      置信度: {{ region.threshold }}
                    </n-text>
                  </n-space>

                  <!-- 区域问题提示 -->
                  <div v-if="hasRegionIssues(region)" class="region-issues">
                    <n-text type="warning" style="font-size: 12px;">
                      <n-icon><WarningOutline /></n-icon>
                      {{ getRegionIssues(region) }}
                    </n-text>
                  </div>
                </div>
              </div>
            </div>
          </DataCard>

          <!-- 规则配置 -->
          <DataCard title="检测规则" class="rules-config-card" v-if="selectedRegion">
            <template #extra>
              <n-space>
                <n-tag type="warning" size="small">
                  <template #icon>
                    <n-icon><SettingsOutline /></n-icon>
                  </template>
                  高级设置
                </n-tag>
                <!-- 预设配置 -->
                <n-dropdown
                  :options="presetOptions"
                  @select="applyPreset"
                  trigger="click"
                >
                  <n-button size="small" quaternary>
                    <template #icon>
                      <n-icon><SparklesOutline /></n-icon>
                    </template>
                    预设
                  </n-button>
                </n-dropdown>
              </n-space>
            </template>

            <n-form :model="currentRegion" label-placement="top" size="medium">
              <n-form-item label="区域名称" :feedback="getNameFeedback(currentRegion.name)">
                <n-input
                  v-model:value="currentRegion.name"
                  placeholder="输入区域名称"
                  @blur="validateRegionName"
                />
              </n-form-item>

              <n-form-item label="检测类型">
                <n-select
                  v-model:value="currentRegion.type"
                  :options="regionTypeOptions"
                  placeholder="选择检测类型"
                  @update:value="onTypeChange"
                />
                <!-- 类型说明 -->
                <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block;">
                  {{ getTypeDescription(currentRegion.type) }}
                </n-text>
              </n-form-item>

              <n-form-item label="敏感度" :feedback="getSensitivityFeedback(currentRegion.sensitivity)">
                <n-slider
                  v-model:value="currentRegion.sensitivity"
                  :min="0"
                  :max="100"
                  :step="1"
                  :marks="{ 0: '低', 50: '中', 100: '高' }"
                  @update:value="onSensitivityChange"
                />
              </n-form-item>

              <n-form-item label="置信度阈值" :feedback="getThresholdFeedback(currentRegion.threshold)">
                <n-input-number
                  v-model:value="currentRegion.threshold"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  placeholder="0.0 - 1.0"
                  style="width: 100%"
                  @update:value="onThresholdChange"
                />
              </n-form-item>

              <!-- 高级选项 -->
              <n-collapse>
                <n-collapse-item title="高级选项" name="advanced">
                  <n-form-item label="检测间隔 (秒)">
                    <n-input-number
                      v-model:value="currentRegion.interval"
                      :min="1"
                      :max="60"
                      placeholder="检测间隔"
                      style="width: 100%"
                    />
                  </n-form-item>

                  <n-form-item label="最小目标尺寸">
                    <n-input-number
                      v-model:value="currentRegion.minSize"
                      :min="10"
                      :max="1000"
                      placeholder="像素"
                      style="width: 100%"
                    />
                  </n-form-item>

                  <n-form-item label="报警延迟 (秒)">
                    <n-input-number
                      v-model:value="currentRegion.alertDelay"
                      :min="0"
                      :max="300"
                      placeholder="延迟时间"
                      style="width: 100%"
                    />
                  </n-form-item>
                </n-collapse-item>
              </n-collapse>

              <n-form-item label="启用状态">
                <n-switch v-model:value="currentRegion.enabled">
                  <template #checked>启用</template>
                  <template #unchecked>禁用</template>
                </n-switch>
              </n-form-item>
            </n-form>
          </DataCard>
        </div>

        <!-- 右侧预览区域 -->
        <div class="preview-panel">
          <DataCard title="预览画面" class="preview-card">
            <template #extra>
              <n-space>
                <n-tag v-if="isDrawing" type="success" size="small">
                  <template #icon>
                    <n-icon><BrushOutline /></n-icon>
                  </template>
                  绘制模式
                </n-tag>

                <n-button-group size="small">
                  <n-button @click="zoomIn" :disabled="!selectedCamera && !regionStore.backgroundImage">
                    <template #icon>
                      <n-icon><AddOutline /></n-icon>
                    </template>
                  </n-button>
                  <n-button @click="zoomOut" :disabled="!selectedCamera && !regionStore.backgroundImage">
                    <template #icon>
                      <n-icon><RemoveOutline /></n-icon>
                    </template>
                  </n-button>
                  <n-button @click="resetZoom" :disabled="!selectedCamera && !regionStore.backgroundImage">
                    <template #icon>
                      <n-icon><RefreshOutline /></n-icon>
                    </template>
                  </n-button>
                </n-button-group>
                <n-upload
                  :show-file-list="false"
                  :default-upload="false"
                  accept="image/*"
                  @change="onUploadImage"
                >
                  <n-button>
                    <template #icon>
                      <n-icon><CloudUploadOutline /></n-icon>
                    </template>
                    上传图片
                  </n-button>
                </n-upload>
              </n-space>
            </template>

            <div class="preview-container" v-if="selectedCamera || regionStore.backgroundImage">
              <div
                class="canvas-container"
                ref="canvasContainer"
                @click="onCanvasClick"
                @dblclick="onCanvasDblClick"
                @mousemove="onCanvasMouseMove"
              >
                <canvas
                  ref="previewCanvas"
                  class="preview-canvas"
                  :width="canvasWidth"
                  :height="canvasHeight"
                />

                <!-- 区域工具提示 -->
                <div
                  v-if="hoveredRegion"
                  class="region-tooltip"
                  :style="tooltipStyle"
                >
                  <n-card size="small">
                    <n-text strong>{{ hoveredRegion.name }}</n-text>
                    <br>
                    <n-text depth="3" style="font-size: 12px;">
                      类型: {{ getRegionTypeText(hoveredRegion.type) }}
                    </n-text>
                    <br>
                    <n-text depth="3" style="font-size: 12px;">
                      状态: {{ hoveredRegion.enabled ? '启用' : '禁用' }}
                    </n-text>
                  </n-card>
                </div>
              </div>
            </div>

            <div class="no-camera-placeholder" v-else>
              <n-empty description="请先选择摄像头">
                <template #icon>
                  <n-icon size="48" color="var(--text-color-3)">
                    <VideocamOutline />
                  </n-icon>
                </template>
                <template #extra>
                  <n-button type="primary" @click="showCameraSetup">
                    设置摄像头
                  </n-button>
                </template>
              </n-empty>
            </div>
          </DataCard>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <n-modal v-model:show="showConfirmDialog">
      <n-card
        style="width: 400px"
        title="确认操作"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <n-text>{{ confirmMessage }}</n-text>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showConfirmDialog = false">取消</n-button>
            <n-button type="primary" @click="confirmAction">确认</n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>

    <!-- 无障碍访问面板 -->
    <AccessibilityPanel />

    <!-- 测试面板 -->
    <TestPanel />

    <!-- 性能监控面板 -->
    <PerformanceMonitor />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import {
  NAlert, NIcon, NButton, NSpace, NDropdown, NSelect, NTag, NText,
  NForm, NFormItem, NInput, NInputNumber, NSlider, NSwitch, NCollapse,
  NCollapseItem, NButtonGroup, NCard, NModal, NEmpty, NUpload,
  useMessage, useDialog
} from 'naive-ui'
import {
  InformationCircleOutline,
  LayersOutline,
  ChevronDownOutline,
  DownloadOutline,
  CloudUploadOutline,
  RefreshOutline,
  VideocamOutline,
  LocationOutline,
  AddOutline,
  CreateOutline,
  TrashOutline,
  WarningOutline,
  SettingsOutline,
  SparklesOutline,
  BrushOutline,
  RemoveOutline
} from '@vicons/ionicons5'

// 组件导入
import PageHeader from '@/components/common/PageHeader.vue'
import DataCard from '@/components/common/DataCard.vue'
import AccessibilityPanel from '@/components/common/AccessibilityPanel.vue'
import TestPanel from '@/components/common/TestPanel.vue'
import PerformanceMonitor from '@/components/common/PerformanceMonitor.vue'
import { useCameraStore } from '@/stores/camera'
import { useRegionStore } from '@/stores/region'
import type { Region } from '@/api/region'
import { storeToRefs } from 'pinia'

// Composables
import { useAccessibility } from '@/composables/useAccessibility'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { usePerformance } from '@/composables/usePerformance'

// 响应式数据
const message = useMessage()
const dialog = useDialog()
const regionStore = useRegionStore()
const cameraStore = useCameraStore()
const { regions, selectedRegion, isDrawing, currentDrawingPoints } = storeToRefs(regionStore)

const cameraOptions = computed(() =>
  (cameraStore.cameras || []).map((cam: any) => ({
    label: cam.name,
    value: cam.id,
  }))
)

// 无障碍功能
const {
  announceMessage,
  setFocusToElement,
  enableKeyboardNavigation
} = useAccessibility()

// 键盘快捷键
const { registerShortcut, unregisterShortcut } = useKeyboardShortcuts()

// 性能监控
const { startMonitoring, stopMonitoring } = usePerformance()

// 组件状态
const showGuide = ref(true)
const selectedCamera = ref<string>('')
const hoveredRegion = ref<Region | null>(null)
const showConfirmDialog = ref(false)
const confirmMessage = ref('')
const confirmAction = ref(() => {})

watch(selectedRegion, (newRegion) => {
  if (newRegion) {
    // Note: This is a shallow copy. For deep reactivity, consider a deep copy.
    Object.assign(currentRegion, newRegion)
  } else {
    // Reset when no region is selected
    Object.assign(currentRegion, {
      id: '',
      name: '',
      type: 'custom',
      points: [],
      rules: {
        requireHairnet: false,
        limitOccupancy: false,
        timeRestriction: false
      },
      enabled: true
    })
  }
})

// 区域数据
const currentRegion = reactive<Partial<Region>>({
  id: '',
  name: '',
  type: 'detection',
  points: [],
  enabled: true
})

// 画布相关
const canvasContainer = ref<HTMLElement>()
const previewCanvas = ref<HTMLCanvasElement>()
const canvasWidth = ref(800)
const canvasHeight = ref(600)
const scale = ref(1)

// 画布工具函数
function getCtx() {
  if (!previewCanvas.value) return null
  return previewCanvas.value.getContext('2d')
}

function clearCanvas() {
  const ctx = getCtx()
  if (!ctx) return
  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
}

function renderCanvas() {
  const ctx = getCtx()
  if (!ctx) return
  // 背景
  clearCanvas()
  ctx.save()
  ctx.scale(scale.value, scale.value)
  const img = regionStore.backgroundImage as unknown as HTMLImageElement | null
  if (img) {
    ctx.drawImage(img, 0, 0, canvasWidth.value, canvasHeight.value)
  } else {
    // 无背景图时填充灰底
    ctx.fillStyle = '#fafafa'
    ctx.fillRect(0, 0, canvasWidth.value, canvasHeight.value)
  }
  // 绘制已存在区域
  drawRegions(ctx)
  // 绘制进行中的多边形
  if (isDrawing.value && currentDrawingPoints.value.length > 0) {
    ctx.strokeStyle = '#18a058' // green
    ctx.lineWidth = 2

    // Draw lines between points
    ctx.beginPath()
    ctx.moveTo(currentDrawingPoints.value[0].x, currentDrawingPoints.value[0].y)
    for (let i = 1; i < currentDrawingPoints.value.length; i++) {
      ctx.lineTo(currentDrawingPoints.value[i].x, currentDrawingPoints.value[i].y)
    }

    // Draw line to current mouse position
    ctx.lineTo(currentMousePos.value.x, currentMousePos.value.y)
    ctx.stroke()

    // Draw a faint line back to the start to show closure
    if (currentDrawingPoints.value.length > 1) {
      ctx.save()
      ctx.strokeStyle = 'rgba(24, 160, 88, 0.5)'
      ctx.setLineDash([2, 4])
      ctx.beginPath()
      ctx.moveTo(currentMousePos.value.x, currentMousePos.value.y)
      ctx.lineTo(currentDrawingPoints.value[0].x, currentDrawingPoints.value[0].y)
      ctx.stroke()
      ctx.restore()
    }
  }
  ctx.restore()
}

function drawRegions(ctx: CanvasRenderingContext2D) {
  ctx.save()
  ctx.lineWidth = 2

  for (const r of regions.value) {
    if (r.points && r.points.length > 1) {
      ctx.strokeStyle = 'rgba(64,158,255,0.9)'
      ctx.fillStyle = 'rgba(64,158,255,0.2)'

      ctx.beginPath()
      ctx.moveTo(r.points[0].x, r.points[0].y)
      for (let i = 1; i < r.points.length; i++) {
        ctx.lineTo(r.points[i].x, r.points[i].y)
      }
      ctx.closePath()
      ctx.fill()
      ctx.stroke()
    } else if ('x' in r && 'y' in r && 'width' in r && 'height' in r) {
      // Fallback for old rectangle regions
      ctx.strokeStyle = 'rgba(255, 0, 0, 0.9)' // Different color for old data
      ctx.fillStyle = 'rgba(255, 0, 0, 0.1)'
      ctx.strokeRect(r.x, r.y, r.width, r.height)
      ctx.fillRect(r.x, r.y, r.width, r.height)
    }
  }
  ctx.restore()
}

function fitCanvasToImage(img: HTMLImageElement) {
  // 根据容器尺寸等比适配
  const container = canvasContainer.value
  if (!container) {
    canvasWidth.value = img.naturalWidth
    canvasHeight.value = img.naturalHeight
  } else {
    const maxW = container.clientWidth || img.naturalWidth
    const maxH = container.clientHeight || img.naturalHeight
    const ratio = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight)
    canvasWidth.value = Math.max(10, Math.floor(img.naturalWidth * ratio))
    canvasHeight.value = Math.max(10, Math.floor(img.naturalHeight * ratio))
  }
  regionStore.setCanvasSize(canvasWidth.value, canvasHeight.value)
  nextTick().then(renderCanvas)
}

// 上传图片作为背景以进行离线配置
function onUploadImage(options: any) {
  const file: File | undefined = options?.file?.file
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      regionStore.setBackgroundImage(img)
      scale.value = 1
      nextTick(() => {
        fitCanvasToImage(img)
      })
      announceMessage('图片已加载，可在画布中绘制区域')
    }
    img.src = reader.result as string
  }
  reader.readAsDataURL(file)
}

// 交互：缩放
function zoomIn() {
  scale.value = Math.min(3, parseFloat((scale.value + 0.1).toFixed(2)))
  renderCanvas()
}
function zoomOut() {
  scale.value = Math.max(0.3, parseFloat((scale.value - 0.1).toFixed(2)))
  renderCanvas()
}
function resetZoom() {
  scale.value = 1
  renderCanvas()
}

// 画布坐标换算
function getCanvasPos(e: MouseEvent) {
  if (!previewCanvas.value) return { x: 0, y: 0 }
  const rect = previewCanvas.value.getBoundingClientRect()
  const x = (e.clientX - rect.left) / scale.value
  const y = (e.clientY - rect.top) / scale.value
  return { x, y }
}

// 画布事件处理
const currentMousePos = ref({ x: 0, y: 0 });

function onCanvasClick(e: MouseEvent) {
  if (!regionStore.isDrawing) return;
  const point = getCanvasPos(e);
  regionStore.addDrawingPoint(point);
  renderCanvas();
}

async function onCanvasDblClick(e: MouseEvent) {
  if (!regionStore.isDrawing) return
  e.preventDefault()
  try {
    await regionStore.finishDrawing()
    announceMessage('区域已创建', 'success')
  } catch (error: any) {
    announceMessage(error.message || '创建区域失败', 'error')
  } finally {
    renderCanvas()
  }
}

function onCanvasMouseMove(e: MouseEvent) {
    const p = getCanvasPos(e);
    currentMousePos.value = p;
    if (regionStore.isDrawing) {
        renderCanvas();
    }
}

// 辅助：区域类型显示
function getRegionTypeText(t: string) {
  const m: Record<string, string> = {
    detection: '人员检测',
    intrusion: '入侵检测',
    loitering: '滞留检测',
    counting: '人数统计',
    custom: '自定义'
  }
  return m[t] || t
}

function hasRegionIssues(region: Region): boolean {
  if (!region.name) {
    return true
  }
  if (region.points && region.points.length > 0) {
    const xs = region.points.map(p => p.x)
    const ys = region.points.map(p => p.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    if (maxX - minX < 10 || maxY - minY < 10) {
      return true
    }
  } else if ('width' in region && 'height' in region && (region.width < 10 || region.height < 10)) {
    return true
  }
  return false
}

function getRegionIssues(region: Region): string {
  if (!region.name) {
    return '区域未命名'
  }
  if (region.points && region.points.length > 0) {
    const xs = region.points.map(p => p.x)
    const ys = region.points.map(p => p.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    if (maxX - minX < 10 || maxY - minY < 10) {
      return '区域尺寸过小'
    }
  } else if ('width' in region && 'height' in region && (region.width < 10 || region.height < 10)) {
    return '区域尺寸过小'
  }
  return ''
}

// 无摄像头时的处理
function showCameraSetup() {
  message.info('请在左侧下拉框选择摄像头，或前往“摄像头管理”添加摄像头')
}

function onCameraChange(value: string) {
  console.log('selected camera:', value)
  regionStore.selectRegion(null)
  regionStore.fetchRegions(value) // Fetch regions for the new camera
  message.success(`已选择摄像头: ${value}`)
  renderCanvas()
}

function getCameraResolution(cameraId: string): string {
  const cam = cameraStore.cameras.find((c: any) => c.id === cameraId)
  return cam ? cam.resolution : '未知'
}

function getCameraLocation(cameraId: string): string {
  const cam = cameraStore.cameras.find((c: any) => c.id === cameraId)
  return cam ? cam.location : '未知'
}

function loadExistingConfig() {
  message.info('加载已有配置功能待实现')
}

// 新增：进入绘制模式
function startDrawingMode() {
  if (!selectedCamera.value && !regionStore.backgroundImage) {
    message.warning('请先选择摄像头或上传图片后再绘制')
    return
  }
  regionStore.startDrawing()
  announceMessage('已进入绘制模式：在画布上单击添加点，双击结束绘制')
  nextTick(() => {
    const el = previewCanvas.value as any
    if (el && typeof el.focus === 'function') el.focus()
  })
}

// 工具提示样式，避免未定义
const tooltipStyle = computed(() => ({ left: '0px', top: '0px' }))
// 监听变化自动重绘
watch([regions, scale, canvasWidth, canvasHeight], () => {
  renderCanvas()
}, { deep: true })

watch(() => regionStore.backgroundImage, () => {
  // 背景图变化时重绘
  renderCanvas()
})

// 刷新摄像头列表（真实接口）
const refreshCameras = async () => {
  try {
    await cameraStore.fetchCameras()
    announceMessage('摄像头列表已刷新')
  } catch (error) {
    message.error('刷新摄像头列表失败')
  }
}

onMounted(async () => {
  // 启用无障碍功能
  enableKeyboardNavigation()
  // 初始绘制
  nextTick().then(renderCanvas)
  // 注册键盘快捷键
  registerShortcut({
    id: 'save-config',
    keys: ['Ctrl', 's'],
    description: '保存配置',
    callback: () => {
      // 保存配置逻辑
      announceMessage('配置已保存')
    }
  })

  registerShortcut({
    id: 'new-region',
    keys: ['Ctrl', 'n'],
    description: '新建区域',
    callback: startDrawingMode
  })

  // 启动性能监控
  startMonitoring()

  // 拉取摄像头列表
  try { await cameraStore.fetchCameras() } catch {}

  // 公告页面信息
  await nextTick()
  announceMessage('区域配置页面已加载，请选择摄像头开始配置')
})

onUnmounted(() => {
  // 清理快捷键
  unregisterShortcut('save-config')
  unregisterShortcut('new-region')

  // 停止性能监控
  stopMonitoring()
})
</script>

<style scoped>
.region-config-page {
  padding: 20px;
  min-height: 100vh;
  background: var(--body-color);
}

.guide-alert {
  margin-bottom: 20px;
}

.guide-content {
  margin-top: 12px;
}

.guide-content ol {
  margin: 8px 0;
  padding-left: 20px;
}

.region-config-content {
  margin-top: 20px;
}

.config-panels {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  height: calc(100vh - 220px);
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.preview-panel {
  display: flex;
  flex-direction: column;
}

.camera-select-card,
.region-config-card,
.rules-config-card,
.preview-card {
  height: fit-content;
}

.camera-info {
  margin-top: 12px;
  padding: 12px;
  background: var(--card-color);
  border-radius: 6px;
}

.regions-list {
  max-height: 300px;
  overflow-y: auto;
}

.region-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.region-item:hover {
  border-color: var(--primary-color);
  background: var(--hover-color);
}

.region-item.active {
  border-color: var(--primary-color);
  background: var(--primary-color-hover);
}

.region-item.disabled {
  opacity: 0.6;
}

.region-header {
  margin-bottom: 8px;
}

.region-info {
  display: flex;
  align-items: center;
}

.region-details {
  font-size: 12px;
  color: var(--text-color-3);
}

.region-issues {
  margin-top: 4px;
  color: var(--warning-color);
}

.preview-container {
  position: relative;
  height: 100%;
  min-height: 400px;
  background: #f5f5f5;
  border-radius: 6px;
  overflow: hidden;
}

.canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-canvas {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: white;
  cursor: crosshair;
}

.region-tooltip {
  position: absolute;
  z-index: 1000;
  pointer-events: none;
}

.no-camera-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .config-panels {
    grid-template-columns: 350px 1fr;
  }
}

@media (max-width: 768px) {
  .region-config-page {
    padding: 12px;
  }

  .config-panels {
    grid-template-columns: 1fr;
    height: auto;
  }

  .left-panel {
    order: 2;
  }

  .preview-panel {
    order: 1;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .region-item {
    border-width: 2px;
  }

  .preview-canvas {
    border-width: 2px;
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .region-item {
    transition: none;
  }
}
</style>

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
      <template #extra>
        <n-space>
          <!-- 摄像头选择 -->
          <n-select
            ref="cameraSelectRef"
            v-model:value="selectedCamera"
            :options="cameraOptions"
            placeholder="选择摄像头"
            style="width: 200px"
            clearable
            :loading="cameraStore.loading"
          >
            <template #empty>
              <div style="text-align: center; padding: 12px;">
                <n-text depth="3">暂无可用摄像头</n-text>
              </div>
            </template>
          </n-select>

          <!-- 上传图片 -->
          <n-upload
            :show-file-list="false"
            accept="image/*"
            @change="handleImageUpload"
          >
            <n-button>
              <template #icon>
                <n-icon><ImageOutline /></n-icon>
              </template>
              上传图片
            </n-button>
          </n-upload>

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

          <!-- 导入/导出配置 -->
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

          <!-- 保存配置 -->
          <n-button
            type="primary"
            @click="saveAllRegions"
            :loading="saving"
            :disabled="regions.length === 0"
          >
            <template #icon>
              <n-icon><SaveOutline /></n-icon>
            </template>
            保存配置
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 主要内容区域 -->
    <div class="region-config-content">
      <!-- 使用 n-layout 实现左右分栏布局 -->
      <n-layout has-sider class="config-layout">
        <!-- 左侧面板 -->
        <n-layout-sider
          bordered
          collapse-mode="width"
          :collapsed-width="0"
          :width="leftPanelWidth"
          :native-scrollbar="true"
          class="left-panel"
          @update:width="onLeftPanelResize"
        >
          <div class="left-panel-content">
            <!-- Tabs 容器 -->
            <n-tabs
              type="line"
              animated
              :tab-style="{ padding: '12px 16px' }"
              class="region-tabs"
            >
              <!-- Tab 1: 区域表单 -->
              <n-tab-pane name="form" tab="区域配置">
                <template #tab>
                  <n-space align="center" size="small">
                    <n-icon><CreateOutline /></n-icon>
                    <span>区域配置</span>
                    <n-badge
                      v-if="currentRegion.id || isDrawing"
                      dot
                      type="success"
                    />
                  </n-space>
                </template>

                <!-- 区域配置表单 -->
                <div v-if="currentRegion.id || isDrawing">
                  <RegionForm
                    :current-region="currentRegion"
                    :is-drawing="isDrawing"
                    :selected-camera="selectedCamera"
                    :background-image="regionStore.backgroundImage"
                    :saving="saving"
                    @start-drawing="startDrawingMode"
                    @submit="handleRegionSubmit"
                    @cancel="cancelRegionEdit"
                  />
                </div>

                <!-- 空状态提示 -->
                <n-empty
                  v-else
                  description="请绘制或选择一个区域进行配置"
                  size="medium"
                  style="margin-top: 40px;"
                >
                  <template #icon>
                    <n-icon size="48" color="#d0d0d0">
                      <CreateOutline />
                    </n-icon>
                  </template>
                </n-empty>
              </n-tab-pane>

              <!-- Tab 2: 区域列表 -->
              <n-tab-pane name="list" tab="区域列表">
                <template #tab>
                  <n-space align="center" size="small">
                    <n-icon><ListOutline /></n-icon>
                    <span>区域列表</span>
                    <n-badge
                      v-if="regions.length > 0"
                      :value="regions.length"
                      type="info"
                    />
                  </n-space>
                </template>

                <RegionList
                  :regions="regions"
                  :selected-region-id="selectedRegionId"
                  :selected-camera="selectedCamera"
                  :background-image="regionStore.backgroundImage"
                  :saving="saving"
                  @select-region="selectRegion"
                  @edit-region="selectRegion"
                  @delete-region="handleDeleteRegion"
                  @save-all="saveAllRegions"
                  @start-drawing="startDrawingMode"
                  @batch-action="handleRegionBatchAction"
                />
              </n-tab-pane>
            </n-tabs>
          </div>
        </n-layout-sider>

        <!-- 右侧画布区域 -->
        <n-layout-content class="canvas-container">
          <RegionCanvas
            :regions="regions"
            :selected-region-id="selectedRegionId"
            :background-image="regionStore.backgroundImage"
            :selected-camera="selectedCamera"
            :is-drawing="isDrawing"
            :current-points="currentPoints"
            v-model:show-grid="showGrid"
            v-model:show-labels="showLabels"
            v-model:show-coordinates="showCoordinates"
            @canvas-click="handleCanvasClick"
            @canvas-double-click="handleCanvasDoubleClick"
            @region-select="selectRegion"
            @mouse-move="handleMouseMove"
            @clear-all="clearAllRegions"
          />
        </n-layout-content>
      </n-layout>
    </div>

    <!-- 批量操作对话框 -->
    <n-modal
      v-model:show="showBatchModal"
      preset="dialog"
      title="批量操作"
      positive-text="确认"
      negative-text="取消"
      @positive-click="confirmBatchAction"
    >
      <div v-if="batchAction === 'enable'">
        确定要启用所有选中的区域吗？
      </div>
      <div v-else-if="batchAction === 'disable'">
        确定要禁用所有选中的区域吗？
      </div>
      <div v-else-if="batchAction === 'delete'">
        <n-alert type="warning" style="margin-bottom: 16px;">
          <template #icon>
            <n-icon><WarningOutline /></n-icon>
          </template>
          此操作不可撤销！
        </n-alert>
        确定要删除所有区域吗？这将永久删除所有配置的区域。
      </div>
    </n-modal>

    <!-- 导入配置对话框 -->
    <n-modal
      v-model:show="showImportModal"
      preset="dialog"
      title="导入配置"
      positive-text="导入"
      negative-text="取消"
      @positive-click="confirmImport"
    >
      <n-space vertical size="medium">
        <n-alert type="info">
          <template #icon>
            <n-icon><InformationCircleOutline /></n-icon>
          </template>
          导入配置将覆盖当前所有区域设置，请确认操作。
        </n-alert>

        <div v-if="importData">
          <n-text strong>配置预览：</n-text>
          <n-code
            :code="JSON.stringify(importData, null, 2)"
            language="json"
            style="max-height: 200px; overflow-y: auto; margin-top: 8px;"
          />
        </div>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { useRegionStore } from '@/stores/region'
import { useCameraStore } from '@/stores/camera'
import PageHeader from '@/components/common/PageHeader.vue'
import RegionForm from '@/components/RegionConfig/RegionForm.vue'
import RegionList from '@/components/RegionConfig/RegionList.vue'
import RegionCanvas from '@/components/RegionConfig/RegionCanvas.vue'
import type { Region } from '@/api/region'
import type { UploadFileInfo, SelectInst } from 'naive-ui'

type RegionType = Region['type']
type UIRegionExtras = {
  sensitivity?: number
  minDuration?: number
  alertEnabled?: boolean
  alertLevel?: 'low' | 'medium' | 'high' | 'critical'
}

// Icons
import {
  InformationCircleOutline,
  CreateOutline,
  AddOutline,
  BrushOutline,
  WarningOutline,
  SaveOutline,
  CloseOutline,
  TrashOutline,
  ListOutline,
  LayersOutline,
  EllipsisVerticalOutline,
  RemoveOutline,
  CheckmarkCircleOutline,
  LocationOutline,
  CameraOutline,
  ImageOutline,
  ChevronDownOutline,
  DownloadOutline,
  CloudUploadOutline
} from '@vicons/ionicons5'

// Stores
const regionStore = useRegionStore()
const cameraStore = useCameraStore()

// UI
const message = useMessage()
const dialog = useDialog()

// Refs
const canvas = ref<HTMLCanvasElement>()
const canvasContainer = ref<HTMLElement>()
const formRef = ref()
const cameraSelectRef = ref<SelectInst | null>(null)

// State
const showGuide = ref(true)
const selectedCamera = ref<string>('')
const leftPanelWidth = ref(400)
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)

// Canvas state
// Removed zoomLevel as canvas zoom functionality is disabled
const showGrid = ref(true)
const showLabels = ref(true)
const showCoordinates = ref(true)
const mousePosition = ref<{
  x: number
  y: number
  canvasX: number
  canvasY: number
} | null>(null)

// Drawing state
const isDrawing = ref(false)
const currentPoints = ref<Array<{ x: number; y: number }>>([])
const selectedRegionId = ref<string>('')
// 缓存已加载的背景图片，避免 drawCanvas 中重复创建 Image 导致白屏
const bgImage = ref<HTMLImageElement | null>(null)
const drawingAnimationFrame = ref<number | null>(null)

// Form state
const currentRegion = ref<Partial<Region & UIRegionExtras>>({
  name: '',
  type: 'work_area' as RegionType,
  description: '',
  enabled: true,
  sensitivity: 0.8,
  minDuration: 5,
  alertEnabled: true,
  alertLevel: 'medium',
  points: []
})

// Batch operations
const showBatchModal = ref(false)
const batchAction = ref<string>('')

// Import/Export
const showImportModal = ref(false)
const importData = ref<any>(null)

// Computed
const regions = computed(() => regionStore.regions)

const cameraOptions = computed(() =>
  cameraStore.cameras.map(camera => ({
    label: camera.name,
    value: camera.id
  }))
)

const regionTypeOptions = [
  { label: '入口区域', value: 'entrance' },
  { label: '洗手区域', value: 'handwash' },
  { label: '消毒区域', value: 'sanitize' },
  { label: '工作区域', value: 'work_area' },
  { label: '限制区域', value: 'restricted' },
  { label: '监控区域', value: 'monitoring' },
  { label: '自定义区域', value: 'custom' }
]

const alertLevelOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'critical' }
]

const batchOptions = [
  {
    label: '启用所有区域',
    key: 'enable',
    icon: () => h('n-icon', null, { default: () => h(CheckmarkCircleOutline) })
  },
  {
    label: '禁用所有区域',
    key: 'disable',
    icon: () => h('n-icon', null, { default: () => h(CloseOutline) })
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: '删除所有区域',
    key: 'delete',
    icon: () => h('n-icon', null, { default: () => h(TrashOutline) })
  }
]



const formRules = {
  name: [
    { required: true, message: '请输入区域名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择区域类型', trigger: 'change' }
  ]
}

// Methods
const onLeftPanelResize = (width: number) => {
  leftPanelWidth.value = width
  nextTick(() => {
    resizeCanvas()
  })
}

const startDrawingMode = () => {
  if (!selectedCamera.value && !regionStore.backgroundImage) {
    message.warning('请先选择摄像头或上传图片')
    return
  }

  isDrawing.value = true
  currentPoints.value = []
  selectedRegionId.value = ''

  // Reset current region
  currentRegion.value = {
    name: '',
    type: 'work_area' as RegionType,
    description: '',
    enabled: true,
    sensitivity: 0.8,
    minDuration: 5,
    alertEnabled: true,
    alertLevel: 'medium',
    points: []
  }
}

const findRegionAtPoint = (canvasX: number, canvasY: number): Region | null => {
  // 从后往前遍历，优先选择最后绘制的区域（在上层的区域）
  for (let i = regions.value.length - 1; i >= 0; i--) {
    const region = regions.value[i]
    // 防御性检查：确保 points 存在且为数组
    if (!region.points || !Array.isArray(region.points)) continue
    // 将区域的图片坐标转换为画布坐标进行点击检测
    const canvasPoints = region.points.map(point => imageToCanvasCoords(point.x, point.y))
    if (isPointInPolygon(canvasX, canvasY, canvasPoints)) {
      return region
    }
  }
  return null
}

const isPointInPolygon = (x: number, y: number, points: Array<{ x: number; y: number }>): boolean => {
  if (!points || points.length < 3) return false

  let inside = false
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const xi = points[i].x
    const yi = points[i].y
    const xj = points[j].x
    const yj = points[j].y

    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside
    }
  }
  return inside
}

// 坐标转换函数：画布坐标 -> 图片实际坐标
const canvasToImageCoords = (canvasX: number, canvasY: number): { x: number; y: number } => {
  if (!canvas.value?.dataset.imageScale) {
    return { x: canvasX, y: canvasY }
  }

  const scaleInfo = JSON.parse(canvas.value.dataset.imageScale)
  const { offsetX, offsetY, drawWidth, drawHeight, originalWidth, originalHeight } = scaleInfo

  // 将画布坐标转换为图片显示区域内的相对坐标
  const relativeX = Math.max(0, Math.min(1, (canvasX - offsetX) / drawWidth))
  const relativeY = Math.max(0, Math.min(1, (canvasY - offsetY) / drawHeight))

  // 转换为图片原始尺寸的坐标
  const imageX = Math.round(relativeX * originalWidth)
  const imageY = Math.round(relativeY * originalHeight)

  return { x: imageX, y: imageY }
}

// 坐标转换函数：图片实际坐标 -> 画布坐标
const imageToCanvasCoords = (imageX: number, imageY: number): { x: number; y: number } => {
  if (!canvas.value?.dataset.imageScale) {
    return { x: imageX, y: imageY }
  }

  const scaleInfo = JSON.parse(canvas.value.dataset.imageScale)
  const { offsetX, offsetY, drawWidth, drawHeight, originalWidth, originalHeight } = scaleInfo

  // 将图片坐标转换为相对坐标
  const relativeX = Math.max(0, Math.min(1, imageX / originalWidth))
  const relativeY = Math.max(0, Math.min(1, imageY / originalHeight))

  // 转换为画布坐标
  const canvasX = Math.round(relativeX * drawWidth + offsetX)
  const canvasY = Math.round(relativeY * drawHeight + offsetY)

  return { x: canvasX, y: canvasY }
}

const handleCanvasMouseDown = (event: MouseEvent) => {
  // 只阻止默认行为，不阻止事件冒泡，让双击事件能正常触发
  event.preventDefault()

  console.log('鼠标点击事件，绘制状态:', isDrawing.value)

  const rect = canvas.value!.getBoundingClientRect()
  const canvasX = event.clientX - rect.left
  const canvasY = event.clientY - rect.top

  if (isDrawing.value) {
    // 绘制模式：将画布坐标转换为图片坐标后添加点
    const imageCoords = canvasToImageCoords(canvasX, canvasY)
    currentPoints.value.push(imageCoords)
    console.log('添加点:', imageCoords, '总点数:', currentPoints.value.length)

    // 使用节流重绘
    if (!drawingAnimationFrame.value) {
      drawingAnimationFrame.value = requestAnimationFrame(() => {
        drawCanvas()
        drawingAnimationFrame.value = null
      })
    }
  } else {
    // 选择模式：检查是否点击了某个区域
    const clickedRegion = findRegionAtPoint(canvasX, canvasY)
    if (clickedRegion) {
      selectRegion(clickedRegion)
    } else {
      // 点击空白处，取消选择
      selectedRegionId.value = ''
      currentRegion.value = {
        name: '',
        type: 'work_area' as RegionType,
        description: '',
        enabled: true,
        sensitivity: 0.8,
        minDuration: 5,
        alertEnabled: true,
        alertLevel: 'medium',
        points: []
      }
      drawCanvas()
    }
  }
}

const handleCanvasMouseMove = (event: MouseEvent) => {
  const rect = canvas.value!.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const canvasX = x
  const canvasY = y

  mousePosition.value = { x, y, canvasX, canvasY }

  // 只在绘制模式下且有点时才重绘，使用节流避免频繁重绘
  if (isDrawing.value && currentPoints.value.length > 0) {
    // 使用 requestAnimationFrame 节流重绘
    if (!drawingAnimationFrame.value) {
      drawingAnimationFrame.value = requestAnimationFrame(() => {
        drawCanvas()
        drawingAnimationFrame.value = null
      })
    }
  }
}

const handleCanvasMouseUp = () => {
  // Mouse up logic if needed
}

const handleCanvasDoubleClick = (event: MouseEvent) => {
  // 阻止事件冒泡和默认行为
  event.preventDefault()
  event.stopPropagation()

  console.log('双击事件触发，当前绘制状态:', isDrawing.value, '点数:', currentPoints.value.length)

  if (isDrawing.value && currentPoints.value.length >= 3) {
    console.log('完成绘制')
    finishDrawing()
  } else if (isDrawing.value) {
    message.warning('至少需要3个点才能完成绘制')
  }
}

const handleCanvasWheel = (event: WheelEvent) => {
  event.preventDefault()
  // 禁用缩放功能，只阻止默认滚动行为
}

const finishDrawing = async () => {
  if (currentPoints.value.length < 3) {
    message.warning('至少需要3个点才能形成区域')
    return
  }

  // 复制当前点到区域
  currentRegion.value.points = [...currentPoints.value]

  // 重置绘制状态
  isDrawing.value = false
  currentPoints.value = []

  // Auto-generate name if empty
  if (!currentRegion.value.name) {
    const typeLabel = regionTypeOptions.find(opt => opt.value === currentRegion.value.type)?.label || '区域'
    currentRegion.value.name = `${typeLabel}_${Date.now().toString().slice(-4)}`
  }

  // 重新绘制画布，显示完成的区域
  await nextTick()
  drawCanvas()

  // 完成绘制后自动保存
  try {
    await saveCurrentRegion()
  } catch (e) {
    console.error('自动保存失败:', e)
  }
}

const selectRegion = (region: Region) => {
  selectedRegionId.value = region.id
  currentRegion.value = { ...region }
  drawCanvas()
}

const saveCurrentRegion = async () => {
  try {
    await formRef.value?.validate()

    if (!currentRegion.value.points || currentRegion.value.points.length < 3) {
      message.error('请先绘制区域')
      return
    }

    saving.value = true

    if (currentRegion.value.id) {
      await regionStore.updateRegion(currentRegion.value.id, currentRegion.value as Region)
      message.success('区域更新成功')
    } else {
      await regionStore.createRegion(currentRegion.value as Omit<Region, 'id'>)
      message.success('区域创建成功')
    }

    // Reset form
    currentRegion.value = {
      name: '',
      type: 'work_area' as RegionType,
      description: '',
      enabled: true,
      sensitivity: 0.8,
      minDuration: 5,
      alertEnabled: true,
      alertLevel: 'medium',
      points: []
    }
    selectedRegionId.value = ''

    drawCanvas()
  } catch (error) {
    console.error('Save region error:', error)
    message.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const cancelEdit = () => {
  currentRegion.value = {
    name: '',
    type: 'work_area' as RegionType,
    description: '',
    enabled: true,
    sensitivity: 0.8,
    minDuration: 5,
    alertEnabled: true,
    alertLevel: 'medium',
    points: []
  }
  selectedRegionId.value = ''
  isDrawing.value = false
  currentPoints.value = []
  drawCanvas()
}

const deleteCurrentRegion = async () => {
  if (!currentRegion.value.id) return

  dialog.warning({
    title: '确认删除',
    content: `确定要删除区域"${currentRegion.value.name}"吗？此操作不可撤销。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        deleting.value = true
        await regionStore.deleteRegion(currentRegion.value.id!)
        message.success('区域删除成功')
        cancelEdit()
      } catch (error) {
        console.error('Delete region error:', error)
        message.error('删除失败，请重试')
      } finally {
        deleting.value = false
      }
    }
  })
}

const saveAllRegions = async () => {
  try {
    saving.value = true
    await regionStore.saveRegions(regions.value as Region[])
    message.success('配置保存成功')
  } catch (error) {
    console.error('Save all regions error:', error)
    message.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const handleBatchAction = (key: string) => {
  batchAction.value = key
  showBatchModal.value = true
}

const confirmBatchAction = async () => {
  try {
    if (batchAction.value === 'enable') {
      regions.value.forEach(region => {
        regionStore.updateRegion(region.id, { ...region, enabled: true })
      })
      message.success('已启用所有区域')
    } else if (batchAction.value === 'disable') {
      regions.value.forEach(region => {
        regionStore.updateRegion(region.id, { ...region, enabled: false })
      })
      message.success('已禁用所有区域')
    } else if (batchAction.value === 'delete') {
      await regionStore.clearRegions()
      message.success('已删除所有区域')
      cancelEdit()
    }

    drawCanvas()
  } catch (error) {
    console.error('Batch action error:', error)
    message.error('操作失败，请重试')
  }
}

const exportConfig = () => {
  const config = {
    regions: regions.value,
    camera: selectedCamera.value,
    timestamp: new Date().toISOString()
  }

  const blob = new Blob([JSON.stringify(config, null, 2)], {
    type: 'application/json'
  })

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `region-config-${Date.now()}.json`
  a.click()

  URL.revokeObjectURL(url)
  message.success('配置导出成功')
}

const importConfig = (options: { file: UploadFileInfo }) => {
  const file = options.file.file
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const config = JSON.parse(e.target?.result as string)
      importData.value = config
      showImportModal.value = true
    } catch (error) {
      message.error('配置文件格式错误')
    }
  }
  reader.readAsText(file)
}

const confirmImport = async () => {
  try {
    if (importData.value?.regions) {
      await regionStore.clearRegions()

      for (const region of importData.value.regions) {
        await regionStore.createRegion(region)
      }

      if (importData.value.camera) {
        selectedCamera.value = importData.value.camera
      }

      message.success('配置导入成功')
      drawCanvas()
    }
  } catch (error) {
    console.error('Import config error:', error)
    message.error('导入失败，请重试')
  }
}

const handleImageUpload = (options: { file: UploadFileInfo }) => {
  const file = options.file.file
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const imageUrl = e.target?.result as string
    const img = new Image()
    img.onload = () => {
      regionStore.setBackgroundImage(img)
      selectedCamera.value = ''
      // 图片加载后重新调整画布大小
      nextTick(() => {
        resizeCanvas()
      })
      message.success('图片上传成功')
    }
    img.src = imageUrl
  }
  reader.readAsDataURL(file)
}

const clearAllRegions = () => {
  dialog.warning({
    title: '确认清除',
    content: '确定要清除所有区域吗？此操作不可撤销。',
    positiveText: '清除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await regionStore.clearRegions()
      cancelEdit()
      drawCanvas()
      message.success('已清除所有区域')
    }
  })
}

const resizeCanvas = () => {
  if (!canvas.value || !canvasContainer.value) return

  const container = canvasContainer.value

  // 如果已缓存背景图片，直接以图片尺寸调整画布大小；否则使用容器尺寸
  if (bgImage.value) {
    setCanvasSize(bgImage.value.width, bgImage.value.height)
  } else {
    const rect = container.getBoundingClientRect()
    setCanvasSize(rect.width, rect.height)
  }
}

const setCanvasSize = (targetWidth: number, targetHeight: number) => {
  if (!canvas.value || !canvasContainer.value) return

  const container = canvasContainer.value
  const containerRect = container.getBoundingClientRect()

  // 计算最大可用尺寸（考虑容器的padding和margin）
  const maxWidth = containerRect.width - 20 // 留出一些边距
  const maxHeight = containerRect.height - 20

  // 计算缩放比例，保持图片宽高比
  const scaleX = maxWidth / targetWidth
  const scaleY = maxHeight / targetHeight
  const scale = Math.min(scaleX, scaleY, 1) // 不放大，只缩小

  const canvasWidth = targetWidth * scale
  const canvasHeight = targetHeight * scale

  // 获取设备像素比，确保高DPI屏幕下的清晰度
  const dpr = window.devicePixelRatio || 1

  // 设置画布的实际像素尺寸
  canvas.value.width = canvasWidth * dpr
  canvas.value.height = canvasHeight * dpr

  // 设置画布的CSS显示尺寸
  canvas.value.style.width = canvasWidth + 'px'
  canvas.value.style.height = canvasHeight + 'px'

  // 居中显示画布
  canvas.value.style.margin = 'auto'
  canvas.value.style.display = 'block'

  // 缩放绘图上下文以匹配设备像素比（重置变换，避免重复 scale 累积）
  const ctx = canvas.value.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  drawCanvas()
}

const drawCanvas = () => {
  if (!canvas.value) return

  const ctx = canvas.value.getContext('2d')!
  // 获取设备像素比，并重置坐标变换为 dpr，避免累积导致绘制异常/白屏
  const dpr = window.devicePixelRatio || 1
  if (ctx.setTransform) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  } else {
    // 兼容旧浏览器
    // @ts-ignore
    ctx.resetTransform?.()
    ctx.scale(dpr, dpr)
  }

  // 使用CSS显示尺寸作为绘制尺寸，确保坐标转换的一致性
  const width = (parseFloat(canvas.value.style.width) || canvas.value.width / dpr)
  const height = (parseFloat(canvas.value.style.height) || canvas.value.height / dpr)

  // 清空画布（使用CSS尺寸）
  ctx.clearRect(0, 0, width, height)

  // 优先使用已缓存的背景图片，避免在重绘流程中重复异步加载导致瞬时白屏
  if (bgImage.value) {
    const img = bgImage.value
    const imgAspect = img.width / img.height
    const canvasAspect = width / height

    let drawWidth: number, drawHeight: number, offsetX: number, offsetY: number

    if (imgAspect > canvasAspect) {
      // 图片更宽，以画布宽度为准
      drawWidth = width
      drawHeight = width / imgAspect
      offsetX = 0
      offsetY = (height - drawHeight) / 2
    } else {
      // 图片更高，以画布高度为准
      drawHeight = height
      drawWidth = height * imgAspect
      offsetX = (width - drawWidth) / 2
      offsetY = 0
    }

    // 绘制图片
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight)

    // 存储缩放信息，用于坐标转换（使用CSS显示尺寸）
    canvas.value!.dataset.imageScale = JSON.stringify({
      offsetX: Math.round(offsetX * 100) / 100,
      offsetY: Math.round(offsetY * 100) / 100,
      drawWidth: Math.round(drawWidth * 100) / 100,
      drawHeight: Math.round(drawHeight * 100) / 100,
      originalWidth: img.width,
      originalHeight: img.height
    })

    drawRegionsAndOverlays()
  } else {
    // 无已加载图片时绘制占位背景，避免白屏
    ctx.fillStyle = '#f5f5f5'
    ctx.fillRect(0, 0, width, height)
    drawRegionsAndOverlays()
  }
}

const drawRegionsAndOverlays = () => {
  if (!canvas.value) return

  const ctx = canvas.value.getContext('2d')!

  // Draw grid if enabled
  if (showGrid.value) {
    drawGrid(ctx)
  }

  // Draw existing regions
  regions.value.forEach(region => {
    drawRegion(ctx, region, region.id === selectedRegionId.value)
  })

  // Draw current drawing
  if (isDrawing.value && currentPoints.value.length > 0) {
    drawCurrentDrawing(ctx)
  }
}

const drawGrid = (ctx: CanvasRenderingContext2D) => {
  const gridSize = 20
  // 使用CSS显示尺寸作为网格绘制的基准
  const width = parseFloat(canvas.value!.style.width) || canvas.value!.width
  const height = parseFloat(canvas.value!.style.height) || canvas.value!.height

  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 0.5

  for (let x = 0; x <= width; x += gridSize) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }

  for (let y = 0; y <= height; y += gridSize) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }
}

const drawRegion = (ctx: CanvasRenderingContext2D, region: Region, isSelected: boolean) => {
  // 防御性检查：确保 points 存在、为数组且至少有3个点
  if (!region.points || !Array.isArray(region.points) || region.points.length < 3) return

  // 将区域的图片坐标转换为画布坐标进行绘制
  const canvasPoints = region.points.map(point => imageToCanvasCoords(point.x, point.y))

  const color = getRegionTypeColor(region.type)
  const alpha = region.enabled ? 0.3 : 0.1

  // Draw filled polygon
  ctx.fillStyle = color + Math.round(alpha * 255).toString(16).padStart(2, '0')
  ctx.beginPath()
  ctx.moveTo(canvasPoints[0].x, canvasPoints[0].y)

  for (let i = 1; i < canvasPoints.length; i++) {
    ctx.lineTo(canvasPoints[i].x, canvasPoints[i].y)
  }

  ctx.closePath()
  ctx.fill()

  // Draw border
  ctx.strokeStyle = isSelected ? '#ff6b6b' : color
  ctx.lineWidth = isSelected ? 3 : 2
  ctx.stroke()

  // Draw points
  canvasPoints.forEach((point, index) => {
    ctx.fillStyle = isSelected ? '#ff6b6b' : color
    ctx.beginPath()
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2)
    ctx.fill()

    // Draw point index
    if (showLabels.value) {
      ctx.fillStyle = '#333'
      ctx.font = '12px sans-serif'
      ctx.fillText(index.toString(), point.x + 6, point.y - 6)
    }
  })

  // Draw region label
  if (showLabels.value) {
    const centerX = canvasPoints.reduce((sum, p) => sum + p.x, 0) / canvasPoints.length
    const centerY = canvasPoints.reduce((sum, p) => sum + p.y, 0) / canvasPoints.length

    ctx.fillStyle = '#333'
    ctx.font = 'bold 14px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(region.name, centerX, centerY)

    ctx.font = '12px sans-serif'
    ctx.fillText(getRegionTypeLabel(region.type), centerX, centerY + 16)
  }
}

const drawCurrentDrawing = (ctx: CanvasRenderingContext2D) => {
  if (currentPoints.value.length === 0) return

  // 将当前绘制点的图片坐标转换为画布坐标进行绘制
  const canvasPoints = currentPoints.value.map(point => imageToCanvasCoords(point.x, point.y))

  ctx.strokeStyle = '#2080f0'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])

  // Draw lines between points
  if (canvasPoints.length > 1) {
    ctx.beginPath()
    ctx.moveTo(canvasPoints[0].x, canvasPoints[0].y)

    for (let i = 1; i < canvasPoints.length; i++) {
      ctx.lineTo(canvasPoints[i].x, canvasPoints[i].y)
    }

    ctx.stroke()
  }

  // Draw points
  canvasPoints.forEach((point, index) => {
    ctx.fillStyle = '#2080f0'
    ctx.beginPath()
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = '#333'
    ctx.font = '12px sans-serif'
    ctx.fillText(index.toString(), point.x + 6, point.y - 6)
  })

  // Draw line to mouse if drawing
  if (mousePosition.value && canvasPoints.length > 0) {
    const lastPoint = canvasPoints[canvasPoints.length - 1]
    ctx.beginPath()
    ctx.moveTo(lastPoint.x, lastPoint.y)
    ctx.lineTo(mousePosition.value.canvasX, mousePosition.value.canvasY)
    ctx.stroke()
  }

  ctx.setLineDash([])
}

const getRegionTypeColor = (type: RegionType): string => {
  const colors: Partial<Record<RegionType, string>> = {
    entrance: '#52c41a',
    handwash: '#1890ff',
    sanitize: '#722ed1',
    work_area: '#fa8c16',
    restricted: '#f5222d',
    monitoring: '#13c2c2',
    custom: '#eb2f96'
  }
  return colors[type] ?? '#666666'
}

const getRegionTypeLabel = (type: RegionType): string => {
  const labels: Partial<Record<RegionType, string>> = {
    entrance: '入口区域',
    handwash: '洗手区域',
    sanitize: '消毒区域',
    work_area: '工作区域',
    restricted: '限制区域',
    monitoring: '监控区域',
    custom: '自定义区域'
  }
  return labels[type] ?? '未知类型'
}

const getRegionTypeIcon = (type: RegionType) => {
  // Return appropriate icon component based on type
  return LocationOutline
}

const getRegionTypeTagType = (type: RegionType) => {
  const types: Partial<Record<RegionType, string>> = {
    entrance: 'success',
    handwash: 'info',
    sanitize: 'warning',
    work_area: 'default',
    restricted: 'error',
    monitoring: 'info',
    custom: 'default'
  }
  return types[type] ?? 'default'
}

// 工具函数：敏感度滑块提示格式化
const formatSensitivityTooltip = (value: number) => `${(value * 100).toFixed(0)}%`

// 告警级别映射函数
const getAlertLevelType = (level: Region['alertLevel'] | undefined) => {
  switch (level) {
    case 'low':
      return 'info'
    case 'medium':
      return 'warning'
    case 'high':
    case 'critical':
      return 'error'
    default:
      return 'warning'
  }
}

const getAlertLevelLabel = (level: Region['alertLevel'] | undefined) => {
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '紧急'
  }
  return map[level ?? 'medium']
}

// 聚焦摄像头选择器方法
const focusCameraSelect = () => {
  nextTick(() => {
    cameraSelectRef.value?.focus?.()
  })
}

// removed duplicate getAlertLevelLabel (unified above)

const getRegionActions = (region: Region) => [
  {
    label: '编辑',
    key: 'edit',
    icon: () => h('n-icon', null, { default: () => h(CreateOutline) })
  },
  {
    label: region.enabled ? '禁用' : '启用',
    key: 'toggle',
    icon: () => h('n-icon', null, {
      default: () => h(region.enabled ? CloseOutline : CheckmarkCircleOutline)
    })
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: '删除',
    key: 'delete',
    icon: () => h('n-icon', null, { default: () => h(TrashOutline) })
  }
]

const handleDeleteRegion = (region: Region) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除区域"${region.name}"吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await regionStore.deleteRegion(region.id)
      message.success('区域删除成功')
      if (selectedRegionId.value === region.id) {
        cancelEdit()
      }
      drawCanvas()
    }
  })
}

// 子组件事件处理方法
const handleRegionSubmit = async (region: any) => {
  if (currentRegion.value.id) {
    // 更新现有区域
    await updateRegion(region)
  } else {
    // 创建新区域
    await createRegion(region)
  }
}

const handleCanvasClick = (point: { x: number; y: number }) => {
  handleCanvasMouseDown({ clientX: point.x, clientY: point.y } as MouseEvent)
}

const handleMouseMove = (position: any) => {
  mousePosition.value = position
}

const cancelRegionEdit = () => {
  cancelEdit()
}

const handleRegionBatchAction = (action: string) => {
  if (action.startsWith('enable_')) {
    const regionId = action.replace('enable_', '')
    regionStore.updateRegion(regionId, { enabled: true })
  } else if (action.startsWith('disable_')) {
    const regionId = action.replace('disable_', '')
    regionStore.updateRegion(regionId, { enabled: false })
  } else {
    batchAction.value = action
    showBatchModal.value = true
  }
}

const handleRegionAction = async (key: string, region: Region) => {
  switch (key) {
    case 'edit':
      selectRegion(region)
      break
    case 'toggle':
      await regionStore.updateRegion(region.id, {
        ...region,
        enabled: !region.enabled
      })
      message.success(`区域已${region.enabled ? '禁用' : '启用'}`)
      drawCanvas()
      break
    case 'delete':
      dialog.warning({
        title: '确认删除',
        content: `确定要删除区域"${region.name}"吗？`,
        positiveText: '删除',
        negativeText: '取消',
        onPositiveClick: async () => {
          await regionStore.deleteRegion(region.id)
          message.success('区域删除成功')
          if (selectedRegionId.value === region.id) {
            cancelEdit()
          }
          drawCanvas()
        }
      })
      break
  }
}



// 新增：下拉菜单选择事件处理，避免模板中隐式 any
const onRegionActionSelect = (key: string, region: Region) => {
  handleRegionAction(key, region)
}



// Lifecycle
onMounted(async () => {
  await cameraStore.fetchCameras()
  await regionStore.fetchRegions()

  nextTick(() => {
    resizeCanvas()
    drawCanvas()
  })

  window.addEventListener('resize', resizeCanvas)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
})

// Watchers
watch(selectedCamera, async (newCamera) => {
  if (newCamera) {
    regionStore.setBackgroundImage(null)
    loading.value = true

    try {
      // Load camera stream or snapshot
      // This would typically fetch a snapshot from the camera
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate loading
      drawCanvas()
    } catch (error) {
      console.error('Load camera error:', error)
      message.error('加载摄像头失败')
    } finally {
      loading.value = false
    }
  }
})

// 当背景图地址变更时，仅在此处加载一次并缓存，避免 drawCanvas 中重复 new Image
watch(() => regionStore.backgroundImage, (val) => {
  const urlOrEl = val as any
  if (!urlOrEl || (typeof urlOrEl === 'string' && urlOrEl.trim() === '')) {
    bgImage.value = null
    // 占位背景即可，避免白屏
    nextTick(() => {
      console.debug('[RegionConfig] 背景图清空，使用占位背景绘制')
      drawCanvas()
    })
    return
  }

  if (urlOrEl instanceof HTMLImageElement) {
    bgImage.value = urlOrEl
    setCanvasSize(urlOrEl.width, urlOrEl.height)
    console.debug('[RegionConfig] 使用已有的 HTMLImageElement 背景图绘制')
    drawCanvas()
    return
  }

  // 其余情况按字符串 URL/DataURL 处理
  const img = new Image()
  img.onload = () => {
    bgImage.value = img
    setCanvasSize(img.width, img.height)
    console.debug('[RegionConfig] 背景图加载完成，开始绘制')
    drawCanvas()
  }
  img.onerror = () => {
    bgImage.value = null
    console.warn('[RegionConfig] 背景图加载失败，使用占位背景绘制')
    drawCanvas()
  }
  img.src = String(urlOrEl)
}, { immediate: true })

watch([showGrid, showLabels], () => {
  drawCanvas()
})
</script>

<style scoped>
.region-config-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.guide-alert {
  margin-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 16px;
}

.guide-content ol {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.guide-content li {
  margin: 4px 0;
}

.region-config-content {
  flex: 1;
  overflow: hidden;
  border-top: 2px solid #e0e0e0;
}

.config-layout {
  height: 100%;
}

.left-panel {
  background: white;
  border-right: 1px solid #e0e0e0;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin: 8px;
}

.left-panel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.region-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  /* 确保与n-scrollbar-container高度一致 */
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.region-tabs :deep(.n-tabs-content) {
  height: 100%;
  /* 允许内容区滚动，避免滚动条被隐藏 */
  overflow: auto;
}

.region-tabs :deep(.n-tab-pane) {
  height: 100%;
  /* 允许面板滚动 */
  overflow: auto;
  display: flex;
  flex-direction: column;
}

    .region-form {
      max-width: 100%;
      padding: 16px;
      /* 保持表单可滚动 */
      overflow-y: auto;
      flex: 1;
    }
    .region-list-section {
      height: 100%;
      overflow-y: auto;
      background: white;
      padding: 16px;
      flex: 1;
      min-height: 0;
    }

    .left-panel-content {
      height: 100%;
      display: flex;
      flex-direction: column;
      /* 避免整体隐藏滚动，交给内部容器管理 */
      overflow: visible;
    }

    .region-card {
      cursor: pointer;
      transition: all 0.2s;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      margin-bottom: 8px;
    }

    .region-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      border-color: #d0d0d0;
    }

    .region-card {
      transition: all 0.3s ease;
      cursor: default;
    }

    .region-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .region-card-selected {
      border-color: #2080f0;
      box-shadow: 0 0 0 2px rgba(32, 128, 240, 0.2);
      background: rgba(32, 128, 240, 0.05);
    }

    .region-card-disabled {
      opacity: 0.6;
    }

    .canvas-container {
      background: #f5f5f5;
      position: relative;
      min-height: calc(100vh - 120px);
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      margin: 8px;
    }

    .canvas-wrapper {
      height: 100%;
      min-height: calc(100vh - 120px);
      display: flex;
      flex-direction: column;
    }

    .canvas-toolbar {
      background: white;
      padding: 12px 16px;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .canvas-main {
      flex: 1;
      position: relative;
      overflow: auto; /* 改为auto，支持滚动 */
      min-height: 500px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px;
    }

    .region-canvas {
      cursor: crosshair;
      border: 1px solid #ddd;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      background: white;
    }

    .canvas-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
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
      z-index: 10;
    }

    .draw-hint {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(32, 128, 240, 0.9);
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      display: flex;
       align-items: center;
       gap: 8px;
       font-size: 14px;
       z-index: 10;
     }

     .canvas-loading {
       position: absolute;
       top: 0;
       left: 0;
       right: 0;
       bottom: 0;
       display: flex;
       align-items: center;
       justify-content: center;
       background: rgba(255, 255, 255, 0.8);
       z-index: 20;
     }

     .canvas-empty {
       position: absolute;
       top: 0;
       left: 0;
       right: 0;
       bottom: 0;
       display: flex;
       align-items: center;
       justify-content: center;
       background: #f5f5f5;
     }

     /* 响应式设计 */
     @media (max-width: 1200px) {
       .config-layout .n-layout-sider {
         width: 350px !important;
       }
     }

     @media (max-width: 768px) {
       .region-config-page {
         padding: 12px;
       }

       .config-layout {
         flex-direction: column;
       }

       .left-panel {
         width: 100% !important;
         order: 2;
       }

       .canvas-container {
         order: 1;
         min-height: 300px;
       }

       .left-panel-content {
         padding: 12px;
       }
     }

     /* 高对比度模式 */
     @media (prefers-contrast: high) {
       .region-card {
         border-width: 2px;
       }

       .region-canvas {
         border-width: 2px;
       }
     }

     /* 减少动画模式 */
     @media (prefers-reduced-motion: reduce) {
       .region-card {
        transition: none;
      }
    }
     </style>

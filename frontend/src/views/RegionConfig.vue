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

                <!-- 绘制区域按钮 -->
                <div class="draw-region-section" style="margin-bottom: 16px; margin-left: 12px; margin-right: 12px;">
                  <n-button
                    type="primary"
                    size="large"
                    @click="startDrawingMode"
                    :disabled="isDrawing || (!selectedCamera && !regionStore.backgroundImage)"
                    block
                  >
                    <template #icon>
                      <n-icon><AddOutline /></n-icon>
                    </template>
                    {{ isDrawing ? '正在绘制...' : '绘制新区域' }}
                  </n-button>

                  <n-alert v-if="isDrawing" type="info" size="small" style="margin-top: 8px;">
                    <template #icon>
                      <n-icon><BrushOutline /></n-icon>
                    </template>
                    在右侧画布上点击绘制区域，双击完成绘制
                  </n-alert>

                  <n-alert
                    v-if="!selectedCamera && !regionStore.backgroundImage"
                    type="warning"
                    size="small"
                    style="margin-top: 8px;"
                  >
                    <template #icon>
                      <n-icon><WarningOutline /></n-icon>
                    </template>
                    请先在页面顶部选择摄像头或上传图片
                  </n-alert>
                </div>

                <!-- 区域配置表单 -->
                <div class="region-form-section" v-if="currentRegion.id || isDrawing">
                  <n-divider>
                    {{ currentRegion.id ? '编辑区域' : '新区域配置' }}
                  </n-divider>

                  <n-form
                    ref="formRef"
                    :model="currentRegion"
                    :rules="formRules"
                    label-placement="top"
                    require-mark-placement="right-hanging"
                    size="medium"
                    class="region-form"
                  >
                    <!-- 基本信息 -->
                    <n-form-item label="区域名称" path="name">
                      <n-input
                        v-model:value="currentRegion.name"
                        placeholder="请输入区域名称"
                        clearable
                      />
                    </n-form-item>

                    <n-form-item label="区域类型" path="type">
                      <n-select
                        v-model:value="currentRegion.type"
                        :options="regionTypeOptions"
                        placeholder="选择区域类型"
                      />
                    </n-form-item>

                    <n-form-item label="区域描述" path="description">
                      <n-input
                        v-model:value="currentRegion.description"
                        type="textarea"
                        placeholder="请输入区域描述（可选）"
                        :autosize="{ minRows: 2, maxRows: 4 }"
                      />
                    </n-form-item>

                    <!-- 检测参数 -->
                    <n-divider title-placement="left">
                      <n-text depth="2">检测参数</n-text>
                    </n-divider>

                    <n-form-item label="启用检测" path="enabled">
                      <n-switch
                        v-model:value="currentRegion.enabled"
                        size="medium"
                      >
                        <template #checked>启用</template>
                        <template #unchecked>禁用</template>
                      </n-switch>
                    </n-form-item>

                    <n-form-item
                      v-if="currentRegion.enabled"
                      label="检测敏感度"
                      path="sensitivity"
                    >
                      <n-slider
                        v-model:value="currentRegion.sensitivity"
                        :min="0.1"
                        :max="1.0"
                        :step="0.1"
                        :format-tooltip="(value) => `${(value * 100).toFixed(0)}%`"
                      />
                      <n-text depth="3" style="font-size: 12px; margin-top: 4px;">
                        敏感度越高，检测越严格
                      </n-text>
                    </n-form-item>

                    <n-form-item
                      v-if="currentRegion.enabled"
                      label="最小停留时间（秒）"
                      path="minDuration"
                    >
                      <n-input-number
                        v-model:value="currentRegion.minDuration"
                        :min="1"
                        :max="300"
                        placeholder="最小停留时间"
                        style="width: 100%"
                      />
                    </n-form-item>

                    <!-- 告警设置 -->
                    <n-divider title-placement="left">
                      <n-text depth="2">告警设置</n-text>
                    </n-divider>

                    <n-form-item label="启用告警" path="alertEnabled">
                      <n-switch
                        v-model:value="currentRegion.alertEnabled"
                        size="medium"
                      >
                        <template #checked>启用</template>
                        <template #unchecked>禁用</template>
                      </n-switch>
                    </n-form-item>

                    <n-form-item
                      v-if="currentRegion.alertEnabled"
                      label="告警级别"
                      path="alertLevel"
                    >
                      <n-select
                        v-model:value="currentRegion.alertLevel"
                        :options="alertLevelOptions"
                        placeholder="选择告警级别"
                      />
                    </n-form-item>

                    <!-- 操作按钮 -->
                    <n-form-item>
                      <n-space>
                        <n-button
                          type="primary"
                          @click="saveCurrentRegion"
                          :loading="saving"
                        >
                          <template #icon>
                            <n-icon><SaveOutline /></n-icon>
                          </template>
                          {{ currentRegion.id ? '更新区域' : '保存区域' }}
                        </n-button>

                        <n-button @click="cancelEdit">
                          <template #icon>
                            <n-icon><CloseOutline /></n-icon>
                          </template>
                          取消
                        </n-button>

                        <n-button
                          v-if="currentRegion.id"
                          type="error"
                          @click="deleteCurrentRegion"
                          :loading="deleting"
                        >
                          <template #icon>
                            <n-icon><TrashOutline /></n-icon>
                          </template>
                          删除
                        </n-button>
                      </n-space>
                    </n-form-item>
                  </n-form>
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

                <!-- 区域列表 -->
                <div class="region-list-section">
                  <n-space vertical size="medium">
                    <n-card
                      v-for="region in regions"
                      :key="region.id"
                      size="small"
                      hoverable
                      :class="{
                        'region-card': true,
                        'region-card-selected': selectedRegionId === region.id,
                        'region-card-disabled': !region.enabled
                      }"
                      @click="selectRegion(region)"
                    >
                      <template #header>
                        <n-space align="center" justify="space-between">
                          <n-space align="center" size="small">
                            <n-icon
                              :color="getRegionTypeColor(region.type)"
                              size="16"
                            >
                              <component :is="getRegionTypeIcon(region.type)" />
                            </n-icon>
                            <n-text strong>{{ region.name }}</n-text>
                            <n-tag
                              :type="region.enabled ? 'success' : 'default'"
                              size="small"
                            >
                              {{ region.enabled ? '启用' : '禁用' }}
                            </n-tag>
                          </n-space>

                          <n-space align="center" size="small">
                            <n-dropdown
                              :options="getRegionActions(region)"
                              @select="(key) => handleRegionAction(key, region)"
                              trigger="click"
                              @click.stop
                            >
                              <n-button
                                size="small"
                                quaternary
                                circle
                                @click.stop
                              >
                                <template #icon>
                                  <n-icon><EllipsisVerticalOutline /></n-icon>
                                </template>
                              </n-button>
                            </n-dropdown>
                          </n-space>
                        </n-space>
                      </template>

                      <n-space vertical size="small">
                        <n-text depth="3">
                          类型：{{ getRegionTypeLabel(region.type) }}
                        </n-text>
                        <n-text v-if="region.description" depth="3">
                          {{ region.description }}
                        </n-text>
                        <n-space size="small" justify="space-between" align="center">
                          <n-space size="small">
                            <n-tag size="small" type="info">
                              敏感度：{{ (region.sensitivity * 100).toFixed(0) }}%
                            </n-tag>
                            <n-tag size="small" type="warning">
                              停留：{{ region.minDuration }}s
                            </n-tag>
                            <n-tag
                              v-if="region.alertEnabled"
                              size="small"
                              :type="getAlertLevelType(region.alertLevel)"
                            >
                              {{ getAlertLevelLabel(region.alertLevel) }}
                            </n-tag>
                          </n-space>
                          
                          <!-- 编辑和删除按钮放在右下角，与n-tag水平对齐 -->
                          <n-space size="small">
                            <n-button
                              size="small"
                              type="primary"
                              quaternary
                              @click.stop="selectRegion(region)"
                            >
                              <template #icon>
                                <n-icon><CreateOutline /></n-icon>
                              </template>
                              编辑
                            </n-button>
                            
                            <n-button
                              size="small"
                              type="error"
                              quaternary
                              @click.stop="handleDeleteRegion(region)"
                            >
                              <template #icon>
                                <n-icon><TrashOutline /></n-icon>
                              </template>
                              删除
                            </n-button>
                          </n-space>
                        </n-space>
                      </n-space>
                    </n-card>

                    <!-- 空状态 -->
                    <n-empty
                      v-if="regions.length === 0"
                      description="暂无配置的区域"
                      size="medium"
                    >
                      <template #icon>
                        <n-icon size="48" color="#d0d0d0">
                          <LayersOutline />
                        </n-icon>
                      </template>
                      <template #extra>
                        <n-button
                          type="primary"
                          @click="startDrawingMode"
                          :disabled="!selectedCamera && !regionStore.backgroundImage"
                        >
                          绘制第一个区域
                        </n-button>
                      </template>
                    </n-empty>
                  </n-space>
                </div>
              </n-tab-pane>
            </n-tabs>
          </div>
        </n-layout-sider>

        <!-- 右侧画布区域 -->
        <n-layout-content class="canvas-container">
          <div class="canvas-wrapper">
            <!-- 工具栏 -->
            <div class="canvas-toolbar">
              <n-space align="center" justify="space-between">
                <n-space align="center" size="small">
                  <!-- 显示选项 -->
                  <n-space size="small">
                    <n-checkbox
                      v-model:checked="showGrid"
                      size="small"
                    >
                      网格
                    </n-checkbox>
                    <n-checkbox
                      v-model:checked="showLabels"
                      size="small"
                    >
                      标签
                    </n-checkbox>
                    <n-checkbox
                      v-model:checked="showCoordinates"
                      size="small"
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
                    @click="clearAllRegions"
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
                @dblclick="handleCanvasDoubleClick"
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
                  {{ Math.round(mousePosition.canvasX) }}, {{ Math.round(mousePosition.canvasY) }}
                </div>

                <!-- 绘制提示 -->
                <div
                  v-if="isDrawing && currentPoints.length === 0"
                  class="draw-hint"
                >
                  <n-icon size="24"><LocationOutline /></n-icon>
                  <span>点击开始绘制区域</span>
                </div>

                <div
                  v-if="isDrawing && currentPoints.length > 0"
                  class="draw-hint"
                >
                  <n-icon size="24"><BrushOutline /></n-icon>
                  <span>继续点击绘制，双击完成</span>
                </div>
              </div>

              <!-- 加载状态 -->
              <div v-if="loading" class="canvas-loading">
                <n-spin size="large">
                  <template #description>
                    加载画面中...
                  </template>
                </n-spin>
              </div>

              <!-- 空状态 -->
              <div
                v-if="!selectedCamera && !regionStore.backgroundImage && !loading"
                class="canvas-empty"
              >
                <n-empty
                  description="请选择摄像头或上传图片开始配置"
                  size="large"
                >
                  <template #icon>
                    <n-icon size="64" color="#d0d0d0">
                      <CameraOutline />
                    </n-icon>
                  </template>
                  <template #extra>
                    <n-space>
                      <n-button
                        type="primary"
                        @click="$refs.cameraSelect?.focus()"
                      >
                        选择摄像头
                      </n-button>
                      <n-upload
                        :show-file-list="false"
                        accept="image/*"
                        @change="handleImageUpload"
                      >
                        <n-button>上传图片</n-button>
                      </n-upload>
                    </n-space>
                  </template>
                </n-empty>
              </div>
            </div>
          </div>
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
import type { Region, RegionType } from '@/types/region'
import type { UploadFileInfo } from 'naive-ui'

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

// Form state
const currentRegion = ref<Partial<Region>>({
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

const handleCanvasMouseDown = (event: MouseEvent) => {
  if (!isDrawing.value) return

  const rect = canvas.value!.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  currentPoints.value.push({ x, y })
  drawCanvas()
}

const handleCanvasMouseMove = (event: MouseEvent) => {
  const rect = canvas.value!.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const canvasX = x
  const canvasY = y

  mousePosition.value = { x, y, canvasX, canvasY }

  if (isDrawing.value && currentPoints.value.length > 0) {
    drawCanvas()
  }
}

const handleCanvasMouseUp = () => {
  // Mouse up logic if needed
}

const handleCanvasDoubleClick = () => {
  if (isDrawing.value && currentPoints.value.length >= 3) {
    finishDrawing()
  }
}

const handleCanvasWheel = (event: WheelEvent) => {
  event.preventDefault()
  // 禁用缩放功能，只阻止默认滚动行为
}

const finishDrawing = () => {
  if (currentPoints.value.length < 3) {
    message.warning('至少需要3个点才能形成区域')
    return
  }

  currentRegion.value.points = [...currentPoints.value]
  isDrawing.value = false
  currentPoints.value = []

  // Auto-generate name if empty
  if (!currentRegion.value.name) {
    const typeLabel = regionTypeOptions.find(opt => opt.value === currentRegion.value.type)?.label || '区域'
    currentRegion.value.name = `${typeLabel}_${Date.now().toString().slice(-4)}`
  }

  drawCanvas()
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
    await regionStore.saveRegions(selectedCamera.value)
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
    regionStore.setBackgroundImage(imageUrl)
    selectedCamera.value = ''
    drawCanvas()
    message.success('图片上传成功')
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
  canvas.value.width = container.clientWidth
  canvas.value.height = container.clientHeight

  drawCanvas()
}

const drawCanvas = () => {
  if (!canvas.value) return

  const ctx = canvas.value.getContext('2d')!
  const width = canvas.value.width
  const height = canvas.value.height

  // Clear canvas
  ctx.clearRect(0, 0, width, height)

  // Draw background
  if (regionStore.backgroundImage) {
    const img = new Image()
    img.onload = () => {
      ctx.drawImage(img, 0, 0, width, height)
      drawRegionsAndOverlays()
    }
    img.src = regionStore.backgroundImage
  } else {
    // Draw placeholder background
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
  const width = canvas.value!.width
  const height = canvas.value!.height

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
  if (!region.points || region.points.length < 3) return

  const color = getRegionTypeColor(region.type)
  const alpha = region.enabled ? 0.3 : 0.1

  // Draw filled polygon
  ctx.fillStyle = color + Math.round(alpha * 255).toString(16).padStart(2, '0')
  ctx.beginPath()
  ctx.moveTo(region.points[0].x, region.points[0].y)

  for (let i = 1; i < region.points.length; i++) {
    ctx.lineTo(region.points[i].x, region.points[i].y)
  }

  ctx.closePath()
  ctx.fill()

  // Draw border
  ctx.strokeStyle = isSelected ? '#ff6b6b' : color
  ctx.lineWidth = isSelected ? 3 : 2
  ctx.stroke()

  // Draw points
  region.points.forEach((point, index) => {
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
    const centerX = region.points.reduce((sum, p) => sum + p.x, 0) / region.points.length
    const centerY = region.points.reduce((sum, p) => sum + p.y, 0) / region.points.length

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

  ctx.strokeStyle = '#2080f0'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])

  // Draw lines between points
  if (currentPoints.value.length > 1) {
    ctx.beginPath()
    ctx.moveTo(currentPoints.value[0].x, currentPoints.value[0].y)

    for (let i = 1; i < currentPoints.value.length; i++) {
      ctx.lineTo(currentPoints.value[i].x, currentPoints.value[i].y)
    }

    ctx.stroke()
  }

  // Draw points
  currentPoints.value.forEach((point, index) => {
    ctx.fillStyle = '#2080f0'
    ctx.beginPath()
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = '#333'
    ctx.font = '12px sans-serif'
    ctx.fillText(index.toString(), point.x + 6, point.y - 6)
  })

  // Draw line to mouse if drawing
  if (mousePosition.value && currentPoints.value.length > 0) {
    const lastPoint = currentPoints.value[currentPoints.value.length - 1]
    ctx.beginPath()
    ctx.moveTo(lastPoint.x, lastPoint.y)
    ctx.lineTo(mousePosition.value.canvasX, mousePosition.value.canvasY)
    ctx.stroke()
  }

  ctx.setLineDash([])
}

const getRegionTypeColor = (type: RegionType): string => {
  const colors = {
    entrance: '#52c41a',
    handwash: '#1890ff',
    sanitize: '#722ed1',
    work_area: '#fa8c16',
    restricted: '#f5222d',
    monitoring: '#13c2c2',
    custom: '#eb2f96'
  }
  return colors[type] || '#666666'
}

const getRegionTypeLabel = (type: RegionType): string => {
  const labels = {
    entrance: '入口区域',
    handwash: '洗手区域',
    sanitize: '消毒区域',
    work_area: '工作区域',
    restricted: '限制区域',
    monitoring: '监控区域',
    custom: '自定义区域'
  }
  return labels[type] || '未知类型'
}

const getRegionTypeIcon = (type: RegionType) => {
  // Return appropriate icon component based on type
  return LocationOutline
}

const getRegionTypeTagType = (type: RegionType) => {
  const types = {
    entrance: 'success',
    handwash: 'info',
    sanitize: 'warning',
    work_area: 'default',
    restricted: 'error',
    monitoring: 'info',
    custom: 'default'
  }
  return types[type] || 'default'
}

const getAlertLevelType = (level: string) => {
  const types = {
    low: 'info',
    medium: 'warning',
    high: 'error',
    critical: 'error'
  }
  return types[level] || 'default'
}

const getAlertLevelLabel = (level: string): string => {
  const labels = {
    low: '低级告警',
    medium: '中级告警',
    high: '高级告警',
    critical: '紧急告警'
  }
  return labels[level] || '未知级别'
}

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
    regionStore.setBackgroundImage('')
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

watch(() => regionStore.backgroundImage, () => {
  drawCanvas()
})

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
  overflow: hidden;
}

.region-tabs :deep(.n-tab-pane) {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.region-form {
  max-width: 100%;
  padding: 16px;
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

.region-card-selected {
  border-color: #2080f0;
  box-shadow: 0 0 0 2px rgba(32, 128, 240, 0.2);
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
  overflow: hidden;
  min-height: 500px;
}

.region-canvas {
  width: 100%;
  height: 100%;
  min-height: 500px;
  cursor: crosshair;
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

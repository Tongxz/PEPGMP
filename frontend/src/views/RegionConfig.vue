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
      <!-- 使用 n-layout 实现左右分栏布局 -->
      <n-layout has-sider class="config-layout">
        <!-- 左侧面板 -->
        <n-layout-sider
          bordered
          collapse-mode="width"
          :collapsed-width="0"
          :width="400"
          :native-scrollbar="false"
          class="left-panel"
        >
          <div class="left-panel-content">
            <!-- 摄像头选择区域 -->
            <DataCard title="摄像头选择" class="camera-selection-card">
              <div class="camera-select-section">
                <n-space vertical>
                  <n-space align="center">
                    <n-select
                      v-model:value="selectedCamera"
                      :options="cameraOptions"
                      placeholder="选择摄像头"
                      style="flex: 1"
                      @update:value="onCameraChange"
                    />
                    <n-button @click="refreshCameras" :loading="loadingCameras">
                      <template #icon>
                        <n-icon><RefreshOutline /></n-icon>
                      </template>
                    </n-button>
                  </n-space>

                  <!-- 摄像头信息卡片 -->
                  <div v-if="selectedCameraInfo" class="camera-info-card">
                    <n-card size="small">
                      <template #header>
                        <n-space align="center">
                          <n-icon><VideocamOutline /></n-icon>
                          <span>{{ selectedCameraInfo.name }}</span>
                        </n-space>
                      </template>
                      <n-descriptions :column="1" size="small">
                        <n-descriptions-item label="分辨率">
                          {{ selectedCameraInfo.width }}×{{ selectedCameraInfo.height }}
                        </n-descriptions-item>
                        <n-descriptions-item label="状态">
                          <n-tag :type="selectedCameraInfo.status === 'online' ? 'success' : 'error'" size="small">
                            {{ selectedCameraInfo.status === 'online' ? '在线' : '离线' }}
                          </n-tag>
                        </n-descriptions-item>
                        <n-descriptions-item label="位置">
                          {{ selectedCameraInfo.location || '未设置' }}
                        </n-descriptions-item>
                      </n-descriptions>
                    </n-card>
                  </div>

                  <!-- 图片上传区域 -->
                  <n-divider>或上传图片</n-divider>
                  <n-upload
                    :show-file-list="false"
                    accept="image/*"
                    @change="handleImageUpload"
                    class="image-upload"
                  >
                    <n-upload-dragger>
                      <div style="margin-bottom: 12px">
                        <n-icon size="48" :depth="3">
                          <ImageOutline />
                        </n-icon>
                      </div>
                      <n-text style="font-size: 16px">
                        点击或者拖动图片到该区域来上传
                      </n-text>
                      <n-p depth="3" style="margin: 8px 0 0 0">
                        支持 JPG、PNG、GIF 格式，建议尺寸不超过 10MB
                      </n-p>
                    </n-upload-dragger>
                  </n-upload>

                  <!-- 图片信息卡片 -->
                  <div v-if="uploadedImage" class="image-info-card">
                    <n-card size="small">
                      <template #header>
                        <n-space align="center">
                          <n-icon><ImageOutline /></n-icon>
                          <span>{{ uploadedImage.name }}</span>
                        </n-space>
                      </template>
                      <n-descriptions :column="1" size="small">
                        <n-descriptions-item label="尺寸">
                          {{ uploadedImage.width }}×{{ uploadedImage.height }}
                        </n-descriptions-item>
                        <n-descriptions-item label="大小">
                          {{ formatFileSize(uploadedImage.size) }}
                        </n-descriptions-item>
                      </n-descriptions>
                    </n-card>
                  </div>
                </n-space>
              </div>
            </DataCard>

            <!-- 绘制区域按钮 -->
            <DataCard title="区域绘制" class="region-draw-card">
              <div class="draw-region-section" v-if="selectedCamera">
                <n-space vertical>
                  <n-button
                    type="primary"
                    size="large"
                    @click="startDrawingMode"
                    :disabled="isDrawing"
                    block
                  >
                    <template #icon>
                      <n-icon><AddOutline /></n-icon>
                    </template>
                    {{ isDrawing ? '正在绘制...' : '绘制新区域' }}
                  </n-button>

                  <n-alert v-if="isDrawing" type="info" size="small">
                    <template #icon>
                      <n-icon><BrushOutline /></n-icon>
                    </template>
                    在右侧画布上点击绘制区域，双击完成绘制
                  </n-alert>
                </n-space>
              </div>
            </DataCard>

            <!-- 区域配置表单 -->
            <DataCard title="区域配置" class="region-config-card">
              <div class="region-form-section" v-if="currentRegion.id || isDrawing">
                <n-divider>
                  {{ currentRegion.id ? '编辑区域' : '新区域配置' }}
                </n-divider>

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

                      <!-- 预设配置 -->
                      <n-form-item label="预设配置">
                        <n-space>
                          <n-button size="small" @click="applyPreset('high-precision')">
                            高精度
                          </n-button>
                          <n-button size="small" @click="applyPreset('balanced')">
                            平衡
                          </n-button>
                          <n-button size="small" @click="applyPreset('high-efficiency')">
                            高效率
                          </n-button>
                        </n-space>
                      </n-form-item>

                      <!-- 操作按钮 -->
                      <n-form-item>
                        <n-space>
                          <n-button
                            v-if="currentRegion.id"
                            type="primary"
                            @click="saveRegionEdit"
                          >
                            <template #icon>
                              <n-icon><SaveOutline /></n-icon>
                            </template>
                            保存
                          </n-button>
                          <n-button
                            v-if="currentRegion.id"
                            @click="cancelEdit"
                          >
                            <template #icon>
                              <n-icon><CloseOutline /></n-icon>
                            </template>
                            取消
                          </n-button>
                          <n-button
                            v-if="isDrawing"
                            type="primary"
                            @click="finishDrawing"
                          >
                            <template #icon>
                              <n-icon><CheckmarkDoneOutline /></n-icon>
                            </template>
                            完成绘制
                          </n-button>
                        </n-space>
                      </n-form-item>
                </n-form>
              </div>

              <!-- 无选择状态提示 -->
              <div v-if="!currentRegion.id && !isDrawing" class="no-selection-hint">
                <n-empty description="请选择一个区域进行编辑，或绘制新区域">
                  <template #icon>
                    <n-icon size="48" color="var(--text-color-3)">
                      <CreateOutline />
                    </n-icon>
                  </template>
                </n-empty>
              </div>
            </DataCard>

            <!-- 区域列表 -->
            <DataCard title="区域列表" class="region-list-card">
              <!-- 区域统计 -->
              <div class="region-stats">
                <n-space justify="space-between" align="center">
                  <n-statistic label="总区域数" :value="regions.length" />
                  <n-statistic
                    label="启用区域"
                    :value="regions.filter(r => r.enabled).length"
                  />
                  <n-dropdown
                    :options="batchOptions"
                    @select="handleBatchAction"
                    trigger="click"
                  >
                    <n-button size="small">
                      <template #icon>
                        <n-icon><LayersOutline /></n-icon>
                      </template>
                      批量操作
                    </n-button>
                  </n-dropdown>
                </n-space>
              </div>

              <n-divider />

                  <!-- 区域列表 -->
                  <div class="regions-list">
                    <div
                      v-for="region in regions"
                      :key="region.id"
                      class="region-item"
                      :class="{
                        active: selectedRegion?.id === region.id,
                        disabled: !region.enabled
                      }"
                      @click="regionStore.selectRegion(region)"
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
                            <template v-if="region.points && region.points.length > 0">
                              多边形区域 ({{ region.points.length }} 个点)
                            </template>
                            <template v-else-if="region.x !== undefined && region.y !== undefined">
                              坐标: ({{ region.x }}, {{ region.y }}) - {{ region.width }}×{{ region.height }}
                            </template>
                            <template v-else>
                              区域信息不完整
                            </template>
                          </n-text>
                          <n-text depth="3" style="font-size: 12px;">
                            置信度: {{ region.threshold || '未设置' }}
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

                    <!-- 空状态 -->
                    <div v-if="regions.length === 0" class="empty-regions">
                      <n-empty description="暂无区域，请先绘制区域">
                        <template #icon>
                          <n-icon size="48" color="var(--text-color-3)">
                            <LayersOutline />
                          </n-icon>
                        </template>
                        <template #extra>
                          <n-button type="primary" @click="startDrawingMode">
                            绘制第一个区域
                          </n-button>
                        </template>
                      </n-empty>
                    </div>
                  </div>
                </div>

                <!-- 空状态 -->
                <div v-if="regions.length === 0" class="empty-regions">
                  <n-empty description="暂无区域，请先绘制区域">
                    <template #icon>
                      <n-icon size="48" color="var(--text-color-3)">
                        <LayersOutline />
                      </n-icon>
                    </template>
                    <template #extra>
                      <n-button type="primary" @click="startDrawingMode">
                        绘制第一个区域
                      </n-button>
                    </template>
                  </n-empty>
                </div>
              </div>
            </DataCard>

            <!-- 配置管理 -->
            <DataCard title="配置管理" class="config-management-card">
              <n-space vertical>
                <n-button @click="exportConfig" block>
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
                  <n-button block>
                    <template #icon>
                      <n-icon><CloudUploadOutline /></n-icon>
                    </template>
                    导入配置
                  </n-button>
                </n-upload>
              </n-space>
            </DataCard>
          </div>
        </n-layout-sider>

        <!-- 右侧预览区域 -->
        <n-layout-content class="right-panel">
          <DataCard title="预览画面" class="preview-card">
            <template #extra>
              <n-space>
                <n-tag v-if="isDrawing" type="success" size="small">
                  <template #icon>
                    <n-icon><BrushOutline /></n-icon>
                  </template>
                  绘制模式
                </n-tag>

                <n-button
                  v-if="isDrawing"
                  size="small"
                  type="primary"
                  @click="finishDrawing"
                >
                  <template #icon>
                    <n-icon><CheckmarkDoneOutline /></n-icon>
                  </template>
                  完成绘制
                </n-button>

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
              <n-empty description="请先选择摄像头或上传图片">
                <template #icon>
                  <n-icon size="48" color="var(--text-color-3)">
                    <VideocamOutline />
                  </n-icon>
                </template>
                <template #extra>
                  <n-space>
                    <n-button type="primary" @click="showCameraSetup">
                      选择摄像头
                    </n-button>
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
              </n-empty>
            </div>
          </DataCard>
        </n-layout-content>
      </n-layout>
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
  RemoveOutline,
  SaveOutline,
  CloseOutline,
  CheckmarkDoneOutline
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
  sensitivity: 60,
  threshold: 0.7,
  interval: 2,
  minSize: 30,
  alertDelay: 2,
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

async function finishDrawing() {
  if (!regionStore.isDrawing) return
  try {
    await regionStore.finishDrawing()
    announceMessage('区域已创建', 'success')
  } catch (error: any) {
    announceMessage(error.message || '创建区域失败', 'error')
  } finally {
    renderCanvas()
  }
}

async function onCanvasDblClick(e: MouseEvent) {
  if (!regionStore.isDrawing) return
  e.preventDefault()
  await finishDrawing()
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
    entrance: '入口区域',
    handwash: '洗手区域',
    sanitize: '消毒区域',
    work_area: '工作区域',
    restricted: '限制区域',
    monitoring: '监控区域',
    detection: '人员检测',
    intrusion: '入侵检测',
    loitering: '滞留检测',
    counting: '人数统计',
    custom: '自定义'
  }
  return m[t] || t
}

function getRegionTypeColor(type: string) {
  const colorMap: Record<string, string> = {
    entrance: 'success',
    handwash: 'info',
    sanitize: 'warning',
    work_area: 'info',
    restricted: 'error',
    monitoring: 'warning',
    custom: 'default',
    detection: 'info',
    intrusion: 'error',
    loitering: 'warning',
    counting: 'success'
  }
  return colorMap[type] || 'default'
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

async function onCameraChange(value: string) {
  console.log('selected camera:', value)
  regionStore.selectRegion(null)
  try {
    await regionStore.fetchRegions(value) // Fetch regions for the new camera
    const cam = cameraStore.cameras.find((c: any) => c.id === value)
    message.success(`已选择摄像头: ${cam ? cam.name : value}`)
  } catch (error) {
    message.error('加载区域列表失败')
  }
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
  // 重置当前区域表单为新区域
  resetCurrentRegion()
  announceMessage('已进入绘制模式：在画布上单击添加点，双击结束绘制')
  nextTick(() => {
    const el = previewCanvas.value as any
    if (el && typeof el.focus === 'function') el.focus()
  })
}

// 清除背景图片
function clearBackgroundImage() {
  regionStore.clearBackgroundImage()
  message.success('已清除背景图片')
  renderCanvas()
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

// 区域类型选项
const regionTypeOptions = computed(() => [
  { label: '入口区域', value: 'entrance' },
  { label: '洗手区域', value: 'handwash' },
  { label: '消毒区域', value: 'sanitize' },
  { label: '工作区域', value: 'work_area' },
  { label: '限制区域', value: 'restricted' },
  { label: '监控区域', value: 'monitoring' }
])

// 表单验证和反馈函数
function getNameFeedback(name?: string): string {
  if (!name || name.trim() === '') {
    return '请输入区域名称'
  }
  if (name.length < 2) {
    return '区域名称至少需要2个字符'
  }
  if (name.length > 50) {
    return '区域名称不能超过50个字符'
  }
  return ''
}

function validateRegionName() {
  const feedback = getNameFeedback(currentRegion.name)
  if (feedback) {
    message.warning(feedback)
  }
}

function getTypeDescription(type?: string): string {
  const descriptions: Record<string, string> = {
    entrance: '检测人员进出入口区域',
    handwash: '监控洗手行为和时长',
    sanitize: '检测消毒操作是否规范',
    work_area: '监控工作区域人员活动',
    restricted: '检测是否有人员进入限制区域',
    monitoring: '通用监控区域，记录所有活动'
  }
  return descriptions[type || ''] || '请选择检测类型'
}

function getSensitivityFeedback(sensitivity?: number): string {
  if (sensitivity === undefined || sensitivity === null) {
    return '请设置检测敏感度'
  }
  if (sensitivity < 30) {
    return '低敏感度：减少误报，可能漏检'
  }
  if (sensitivity > 70) {
    return '高敏感度：提高检测率，可能误报'
  }
  return '中等敏感度：平衡检测率和误报率'
}

function getThresholdFeedback(threshold?: number): string {
  if (threshold === undefined || threshold === null) {
    return '请设置置信度阈值'
  }
  if (threshold < 0.3) {
    return '阈值过低，可能产生大量误报'
  }
  if (threshold > 0.9) {
    return '阈值过高，可能漏检重要事件'
  }
  return '阈值设置合理'
}

// 表单事件处理函数
function onTypeChange(value: string) {
  currentRegion.type = value
  // 根据类型设置默认参数
  switch (value) {
    case 'entrance':
      currentRegion.sensitivity = 60
      currentRegion.threshold = 0.7
      break
    case 'handwash':
      currentRegion.sensitivity = 70
      currentRegion.threshold = 0.6
      break
    case 'sanitize':
      currentRegion.sensitivity = 65
      currentRegion.threshold = 0.65
      break
    case 'work_area':
      currentRegion.sensitivity = 50
      currentRegion.threshold = 0.75
      break
    case 'restricted':
      currentRegion.sensitivity = 80
      currentRegion.threshold = 0.8
      break
    case 'monitoring':
      currentRegion.sensitivity = 55
      currentRegion.threshold = 0.7
      break
  }
  announceMessage(`已选择检测类型: ${getRegionTypeText(value)}`)
}

function onSensitivityChange(value: number) {
  currentRegion.sensitivity = value
}

function onThresholdChange(value: number) {
  currentRegion.threshold = value
}

// 预设配置选项
const presetOptions = computed(() => [
  {
    label: '高精度模式',
    key: 'high-precision',
    props: {
      onClick: () => applyPreset('high-precision')
    }
  },
  {
    label: '平衡模式',
    key: 'balanced',
    props: {
      onClick: () => applyPreset('balanced')
    }
  },
  {
    label: '高效率模式',
    key: 'high-efficiency',
    props: {
      onClick: () => applyPreset('high-efficiency')
    }
  }
])

function applyPreset(preset: string) {
  switch (preset) {
    case 'high-precision':
      currentRegion.sensitivity = 80
      currentRegion.threshold = 0.85
      currentRegion.interval = 1
      currentRegion.minSize = 50
      currentRegion.alertDelay = 0
      message.success('已应用高精度预设')
      break
    case 'balanced':
      currentRegion.sensitivity = 60
      currentRegion.threshold = 0.7
      currentRegion.interval = 2
      currentRegion.minSize = 30
      currentRegion.alertDelay = 2
      message.success('已应用平衡模式预设')
      break
    case 'high-efficiency':
      currentRegion.sensitivity = 40
      currentRegion.threshold = 0.6
      currentRegion.interval = 5
      currentRegion.minSize = 20
      currentRegion.alertDelay = 5
      message.success('已应用高效率预设')
      break
  }
  announceMessage(`已应用预设配置: ${preset}`)
}

// 批量操作选项
const batchOptions = computed(() => [
  {
    label: '全部启用',
    key: 'enable-all',
    props: {
      onClick: () => handleBatchAction('enable-all')
    }
  },
  {
    label: '全部禁用',
    key: 'disable-all',
    props: {
      onClick: () => handleBatchAction('disable-all')
    }
  },
  {
    label: '删除全部',
    key: 'delete-all',
    props: {
      onClick: () => handleBatchAction('delete-all')
    }
  }
])

async function handleBatchAction(action: string) {
  switch (action) {
    case 'enable-all':
      try {
        for (const region of regions.value) {
          if (!region.enabled) {
            await regionStore.updateRegion(region.id, { enabled: true })
          }
        }
        message.success('已启用所有区域')
        renderCanvas()
      } catch (error: any) {
        message.error('批量启用失败: ' + error.message)
      }
      break
    case 'disable-all':
      try {
        for (const region of regions.value) {
          if (region.enabled) {
            await regionStore.updateRegion(region.id, { enabled: false })
          }
        }
        message.success('已禁用所有区域')
        renderCanvas()
      } catch (error: any) {
        message.error('批量禁用失败: ' + error.message)
      }
      break
    case 'delete-all':
      dialog.warning({
        title: '确认删除',
        content: `确定要删除所有 ${regions.value.length} 个区域吗？此操作不可撤销。`,
        positiveText: '删除',
        negativeText: '取消',
        onPositiveClick: async () => {
          try {
            for (const region of regions.value) {
              await regionStore.deleteRegion(region.id)
            }
            message.success('已删除所有区域')
            renderCanvas()
          } catch (error: any) {
            message.error('批量删除失败: ' + error.message)
          }
        }
      })
      break
  }
}

// 导入导出功能
function exportConfig() {
  const config = {
    camera: selectedCamera.value,
    regions: regions.value,
    timestamp: new Date().toISOString()
  }
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `region-config-${selectedCamera.value || 'default'}-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  message.success('配置已导出')
}

function importConfig(options: any) {
  const file = options.file.file
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const config = JSON.parse(e.target?.result as string)
      if (config.regions && Array.isArray(config.regions)) {
        // 导入区域配置
        regions.value = config.regions
        if (config.camera) {
          selectedCamera.value = config.camera
        }
        message.success(`已导入 ${config.regions.length} 个区域配置`)
        renderCanvas()
      } else {
        message.error('配置文件格式不正确')
      }
    } catch (error) {
      message.error('配置文件解析失败')
    }
  }
  reader.readAsText(file)
}

// 编辑区域
function editRegion(region: Region) {
  // 选中区域
  regionStore.selectRegion(region)

  // 将区域数据复制到当前编辑表单
  currentRegion.id = region.id
  currentRegion.name = region.name
  currentRegion.type = region.type
  currentRegion.points = [...(region.points || [])]
  currentRegion.sensitivity = region.sensitivity || 60
  currentRegion.threshold = region.threshold || 0.7
  currentRegion.interval = region.interval || 2
  currentRegion.minSize = region.minSize || 30
  currentRegion.alertDelay = region.alertDelay || 2
  currentRegion.enabled = region.enabled

  // 重新渲染画布，高亮选中的区域
  renderCanvas()

  // 滚动到配置表单
  nextTick(() => {
    const configSection = document.querySelector('.rules-config-card')
    if (configSection) {
      configSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })

  message.info(`正在编辑区域: ${region.name || region.id}`)
  announceMessage(`已选择编辑区域: ${region.name || region.id}，类型: ${getRegionTypeText(region.type)}`)
}

// 保存区域编辑
async function saveRegionEdit() {
  try {
    // 验证表单数据
    const nameValidation = getNameFeedback(currentRegion.name)
    if (nameValidation) {
      message.error(nameValidation)
      return
    }

    if (!currentRegion.type) {
      message.error('请选择检测类型')
      return
    }

    if (!currentRegion.points || currentRegion.points.length < 3) {
      message.error('区域至少需要3个点')
      return
    }

    // 构建更新数据
    const updateData = {
      name: currentRegion.name?.trim(),
      type: currentRegion.type,
      points: currentRegion.points,
      sensitivity: currentRegion.sensitivity,
      threshold: currentRegion.threshold,
      interval: currentRegion.interval,
      minSize: currentRegion.minSize,
      alertDelay: currentRegion.alertDelay,
      enabled: currentRegion.enabled
    }

    // 调用 API 更新区域
    await regionStore.updateRegion(currentRegion.id!, updateData)

    // 重置表单
    resetCurrentRegion()

    // 重新渲染画布
    renderCanvas()

    message.success('区域更新成功')
    announceMessage('区域配置已保存')

  } catch (error: any) {
    console.error('保存区域失败:', error)
    message.error('保存失败: ' + (error.message || '未知错误'))
  }
}

// 取消编辑
function cancelEdit() {
  regionStore.selectRegion(null)
  resetCurrentRegion()
  renderCanvas()
  message.info('已取消编辑')
  announceMessage('已取消区域编辑')
}

// 重置当前区域表单
function resetCurrentRegion() {
  currentRegion.id = ''
  currentRegion.name = ''
  currentRegion.type = 'detection'
  currentRegion.points = []
  currentRegion.sensitivity = 60
  currentRegion.threshold = 0.7
  currentRegion.interval = 2
  currentRegion.minSize = 30
  currentRegion.alertDelay = 2
  currentRegion.enabled = true
}

// 删除区域
async function deleteRegion(regionId: string) {
  const region = regionStore.getRegionById(regionId)
  if (!region) {
    message.error('区域不存在')
    return
  }

  dialog.warning({
    title: '确认删除',
    content: `确定要删除区域 "${region.name || region.id}" 吗？此操作不可撤销。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await regionStore.deleteRegion(regionId)
        message.success('区域删除成功')
        announceMessage(`区域 ${region.name || region.id} 已删除`)
        renderCanvas() // 重新渲染画布
      } catch (error: any) {
        message.error(error.message || '删除区域失败')
      }
    }
  })
}

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

/* 主布局样式 */
.main-layout {
  height: calc(100vh - 120px);
  min-height: 600px;
}

.left-panel {
  padding: 16px;
  background: var(--body-color);
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
}

.right-panel {
  padding: 16px;
  background: var(--body-color);
}

/* 左侧面板卡片样式 */
.camera-selection-card,
.region-config-card,
.region-list-card,
.config-management-card {
  margin-bottom: 16px;
}

.camera-selection-card:last-child,
.region-config-card:last-child,
.region-list-card:last-child,
.config-management-card:last-child {
  margin-bottom: 0;
}

/* 摄像头选择区域 */
.camera-select-section {
  margin-bottom: 16px;
}

.camera-info {
  margin-top: 12px;
}

/* 区域配置表单 */
.region-form {
  padding: 16px 0;
}

.form-section {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-color-1);
}

/* 区域列表 */
.region-stats {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--card-color);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.region-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--card-color);
}

.region-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.region-item.selected {
  border-color: var(--primary-color);
  background: var(--primary-color-hover);
}

.region-item.disabled {
  opacity: 0.6;
}

.region-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.region-info {
  flex: 1;
}

.region-actions {
  display: flex;
  gap: 4px;
}

.region-issues {
  margin-top: 8px;
  padding: 8px;
  background: var(--warning-color-hover);
  border-radius: 4px;
}

.empty-regions {
  text-align: center;
  padding: 32px 16px;
}

/* 右侧预览区域 */
.preview-card {
  height: 100%;
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
  .main-layout .n-layout-sider {
    width: 350px !important;
  }
}

@media (max-width: 768px) {
  .region-config-page {
    padding: 12px;
  }

  .main-layout {
    height: auto;
    flex-direction: column;
  }

  .main-layout .n-layout-sider {
    width: 100% !important;
    order: 2;
  }

  .right-panel {
    order: 1;
    min-height: 300px;
  }

  .left-panel {
    padding: 12px;
  }

  .camera-selection-card,
  .region-config-card,
  .region-list-card,
  .config-management-card {
    margin-bottom: 12px;
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

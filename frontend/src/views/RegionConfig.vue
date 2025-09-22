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
          :native-scrollbar="false"
          class="left-panel"
          show-trigger="bar"
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
                <div class="draw-region-section" style="margin-bottom: 16px;">
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

                    <n-form-item label="区域颜色">
                      <n-color-picker
                        v-model:value="currentRegion.color"
                        :modes="['hex']"
                        :show-alpha="false"
                        size="medium"
                      />
                    </n-form-item>

                    <n-form-item label="区域描述">
                      <n-input
                        v-model:value="currentRegion.description"
                        type="textarea"
                        placeholder="输入区域描述（可选）"
                        :rows="2"
                      />
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
                    <template #extra>
                      <n-button
                        type="primary"
                        @click="startDrawingMode"
                        :disabled="!selectedCamera && !regionStore.backgroundImage"
                      >
                        绘制新区域
                      </n-button>
                    </template>
                  </n-empty>
                </div>
              </n-tab-pane>

              <!-- Tab 2: 区域列表 -->
              <n-tab-pane name="list" tab="区域列表">
                <template #tab>
                  <n-space align="center" size="small">
                    <n-icon><LayersOutline /></n-icon>
                    <span>区域列表</span>
                    <n-badge
                      v-if="regions.length > 0"
                      :value="regions.length"
                      :max="99"
                      type="info"
                    />
                  </n-space>
                </template>

                <!-- 区域统计 -->
                <div class="region-stats" style="margin-bottom: 16px;">
                  <n-space justify="space-between" align="center">
                    <n-statistic label="总区域数" :value="regions.length" />
                    <n-statistic
                      label="启用区域"
                      :value="regions.filter(r => r.enabled).length"
                    />
                    <n-dropdown
                      v-if="regions.length > 0"
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
                      disabled: !region.enabled,
                      editing: currentRegion.id === region.id
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
                          <n-tag
                            v-if="!region.enabled"
                            type="default"
                            size="small"
                            style="margin-left: 4px;"
                          >
                            已禁用
                          </n-tag>
                        </div>

                        <n-space size="small">
                          <n-button
                            size="tiny"
                            quaternary
                            :type="currentRegion.id === region.id ? 'warning' : 'default'"
                            @click.stop="editRegion(region)"
                          >
                            <template #icon>
                              <n-icon><CreateOutline /></n-icon>
                            </template>
                            {{ currentRegion.id === region.id ? '编辑中' : '' }}
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
                      <n-space size="small" vertical>
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
                          置信度: {{ region.threshold || '未设置' }} | 敏感度: {{ region.sensitivity || '未设置' }}
                        </n-text>
                        <n-text v-if="region.description" depth="3" style="font-size: 12px;">
                          {{ region.description }}
                        </n-text>
                      </n-space>

                      <!-- 区域问题提示 -->
                      <div v-if="hasRegionIssues(region)" class="region-issues" style="margin-top: 8px;">
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
                        <n-button
                          type="primary"
                          @click="startDrawingMode"
                          :disabled="!selectedCamera && !regionStore.backgroundImage"
                        >
                          绘制第一个区域
                        </n-button>
                      </template>
                    </n-empty>
                  </div>
                </div>
              </n-tab-pane>
            </n-tabs>
          </div>
        </n-layout-sider>

        <!-- 右侧预览区域 -->
        <n-layout-content class="right-panel">
          <DataCard title="预览画面" class="preview-card">
            <template #extra>
              <n-space>
                <!-- 操作引导按钮 -->
                <n-button
                  size="small"
                  type="info"
                  ghost
                  @click="showOperationGuide"
                >
                  <template #icon>
                    <n-icon><HelpCircleOutline /></n-icon>
                  </template>
                  操作指南
                </n-button>

                <!-- 绘制状态指示器 -->
                <n-tag
                  v-if="isDrawing"
                  type="success"
                  size="small"
                  :bordered="false"
                >
                  <template #icon>
                    <n-icon><BrushOutline /></n-icon>
                  </template>
                  绘制模式
                </n-tag>

                <!-- 编辑状态指示器 -->
                <n-tag
                  v-if="currentRegion.id && !isDrawing"
                  type="warning"
                  size="small"
                  :bordered="false"
                >
                  <template #icon>
                    <n-icon><CreateOutline /></n-icon>
                  </template>
                  编辑模式: {{ currentRegion.name || currentRegion.id }}
                </n-tag>

                <!-- 画布工具栏 -->
                <n-button-group size="small" class="canvas-toolbar">
                  <!-- 绘制控制 -->
                  <n-button
                    v-if="!isDrawing && selectedCamera && regionStore.backgroundImage"
                    type="primary"
                    @click="startDrawingGuide"
                  >
                    <template #icon>
                      <n-icon><BrushOutline /></n-icon>
                    </template>
                    开始绘制
                  </n-button>

                  <n-button
                    v-if="isDrawing"
                    type="primary"
                    @click="finishDrawing"
                    :disabled="currentDrawingPoints.length < 3"
                  >
                    <template #icon>
                      <n-icon><CheckmarkDoneOutline /></n-icon>
                    </template>
                    完成绘制
                  </n-button>

                  <n-button
                    v-if="isDrawing"
                    @click="cancelDrawing"
                  >
                    <template #icon>
                      <n-icon><CloseOutline /></n-icon>
                    </template>
                    取消
                  </n-button>

                  <!-- 缩放控制 -->
                  <n-button
                    @click="zoomOut"
                    :disabled="scale <= 0.3 || (!selectedCamera && !regionStore.backgroundImage)"
                    title="缩小"
                  >
                    <template #icon>
                      <n-icon><RemoveOutline /></n-icon>
                    </template>
                  </n-button>

                  <n-button
                    @click="resetZoom"
                    class="zoom-display"
                    title="重置缩放"
                    :disabled="!selectedCamera && !regionStore.backgroundImage"
                  >
                    {{ Math.round(scale * 100) }}%
                  </n-button>

                  <n-button
                    @click="zoomIn"
                    :disabled="scale >= 3 || (!selectedCamera && !regionStore.backgroundImage)"
                    title="放大"
                  >
                    <template #icon>
                      <n-icon><AddOutline /></n-icon>
                    </template>
                  </n-button>

                  <!-- 画布操作 -->
                  <n-button
                    @click="clearCanvas"
                    title="清空画布"
                    :disabled="isDrawing || (!selectedCamera && !regionStore.backgroundImage)"
                  >
                    <template #icon>
                      <n-icon><RefreshOutline /></n-icon>
                    </template>
                  </n-button>
                </n-button-group>
              </n-space>
            </template>

            <!-- 预览容器 -->
            <div
              class="preview-container"
              :class="{
                'drawing-mode': isDrawing,
                'has-background': regionStore.backgroundImage || selectedCamera
              }"
              v-if="selectedCamera || regionStore.backgroundImage"
            >
              <!-- 操作引导提示 -->
              <div
                v-if="showGuide && !isDrawing"
                class="operation-guide"
              >
                <n-alert
                  type="info"
                  closable
                  @close="showGuide = false"
                >
                  <template #icon>
                    <n-icon><InformationCircleOutline /></n-icon>
                  </template>
                  <template #header>操作提示</template>
                  点击"开始绘制"按钮开始创建区域，或点击"操作指南"查看详细说明
                </n-alert>
              </div>

              <!-- 交互反馈提示 -->
              <n-alert
                v-if="showFeedback"
                :type="feedbackType"
                class="feedback-alert"
                :show-icon="true"
              >
                {{ feedbackMessage }}
              </n-alert>

              <div
                class="canvas-container"
                ref="canvasContainer"
                @click="onCanvasClick"
                @dblclick="onCanvasDblClick"
                @mousemove="onCanvasMouseMove"
                @mouseup="onCanvasMouseUp"
                @mouseleave="onCanvasMouseLeave"
              >
                <!-- 画布 -->
                <canvas
                  ref="previewCanvas"
                  class="preview-canvas"
                  :width="canvasWidth"
                  :height="canvasHeight"
                  :style="{
                    cursor: isDrawing ? 'crosshair' : 'default',
                    transform: `scale(${scale})`
                  }"
                />

                <!-- 绘制提示 -->
                <div
                  v-if="isDrawing"
                  class="drawing-hint"
                >
                  <n-text depth="3">
                    <template v-if="currentDrawingPoints.length === 0">
                      点击画布开始绘制区域
                    </template>
                    <template v-else-if="currentDrawingPoints.length < 3">
                      继续点击添加顶点 (至少需要3个点)
                    </template>
                    <template v-else>
                      双击完成绘制，或继续添加顶点
                    </template>
                  </n-text>
                </div>

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

                <!-- 画布信息显示 -->
                <div class="canvas-info">
                  <n-space size="small">
                    <n-text depth="3" size="small">
                      {{ canvasWidth }} × {{ canvasHeight }}
                    </n-text>
                    <n-text depth="3" size="small">
                      缩放: {{ Math.round(scale * 100) }}%
                    </n-text>
                    <n-text depth="3" size="small">
                      区域: {{ regions.length }}
                    </n-text>
                  </n-space>
                </div>
              </div>
            </div>

            <!-- 无摄像头/图片时的空状态 -->
            <div class="no-camera-placeholder" v-else>
              <n-empty
                description="请在页面顶部选择摄像头或上传图片开始配置区域"
                size="large"
                class="canvas-empty-state"
              >
                <template #icon>
                  <n-icon size="48" color="#d0d0d0">
                    <VideocamOutline />
                  </n-icon>
                </template>
                <template #extra>
                  <n-text depth="3" size="small">
                    使用页面顶部的按钮选择摄像头或上传图片
                  </n-text>
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
  HelpCircleOutline,
  SaveOutline,
  CloseOutline,
  CheckmarkDoneOutline,
  ImageOutline
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
import { RegionConfigManager, type RegionConfig, type Point } from '@/utils/RegionConfigManager'

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
const saving = ref(false)
const uploadedImage = ref<any>(null)

// 左侧面板宽度控制
const leftPanelWidth = ref(400)
const minPanelWidth = 300
const maxPanelWidth = 600

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

// RegionConfigManager 实例
let regionConfigManager: RegionConfigManager | null = null

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

  // 如果有 RegionConfigManager，让它处理渲染
  if (regionConfigManager) {
    regionConfigManager.render()
    return
  }

  // 原有的渲染逻辑作为备用
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
    // 判断是否为编辑中的区域
    const isEditing = currentRegion.id === r.id
    // 判断是否为选中的区域
    const isSelected = selectedRegion?.id === r.id
    // 判断是否为悬停的区域
    const isHovered = hoveredRegion?.id === r.id

    if (r.points && r.points.length > 1) {
      // 根据状态设置不同的颜色
      if (isEditing) {
        ctx.strokeStyle = 'rgba(255, 193, 7, 0.9)' // 编辑状态：橙色
        ctx.fillStyle = 'rgba(255, 193, 7, 0.2)'
      } else if (isSelected) {
        ctx.strokeStyle = 'rgba(24, 160, 88, 0.9)' // 选中状态：绿色
        ctx.fillStyle = 'rgba(24, 160, 88, 0.2)'
      } else if (isHovered) {
        ctx.strokeStyle = 'rgba(64, 158, 255, 1)' // 悬停状态：蓝色加深
        ctx.fillStyle = 'rgba(64, 158, 255, 0.3)'
      } else {
        ctx.strokeStyle = 'rgba(64, 158, 255, 0.9)' // 默认状态：蓝色
        ctx.fillStyle = 'rgba(64, 158, 255, 0.2)'
      }

      // 绘制区域多边形
      ctx.beginPath()
      ctx.moveTo(r.points[0].x, r.points[0].y)
      for (let i = 1; i < r.points.length; i++) {
        ctx.lineTo(r.points[i].x, r.points[i].y)
      }
      ctx.closePath()
      ctx.fill()
      ctx.stroke()

      // 如果是编辑状态，绘制控制点
      if (isEditing) {
        ctx.fillStyle = 'rgba(255, 193, 7, 0.8)'
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 1

        for (const point of r.points) {
          ctx.beginPath()
          ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI)
          ctx.fill()
          ctx.stroke()
        }
      }

      // 绘制区域标签
      if (r.name && (isSelected || isHovered || isEditing)) {
        const centerX = r.points.reduce((sum, p) => sum + p.x, 0) / r.points.length
        const centerY = r.points.reduce((sum, p) => sum + p.y, 0) / r.points.length

        ctx.fillStyle = isEditing ? 'rgba(255, 193, 7, 0.9)' : 'rgba(64, 158, 255, 0.9)'
        ctx.font = '12px Arial'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'

        // 绘制背景
        const textWidth = ctx.measureText(r.name).width
        ctx.fillRect(centerX - textWidth/2 - 4, centerY - 8, textWidth + 8, 16)

        // 绘制文字
        ctx.fillStyle = '#fff'
        ctx.fillText(r.name, centerX, centerY)
      }

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
const isDraggingPoint = ref(false);
const dragPointIndex = ref(-1);
const dragRegionId = ref('');

function onCanvasClick(e: MouseEvent) {
  const point = getCanvasPos(e);

  // 如果正在绘制模式
  if (regionStore.isDrawing) {
    regionStore.addDrawingPoint(point);

    // 同时通知 RegionConfigManager
    if (regionConfigManager) {
      regionConfigManager.handleCanvasClick(e)
    }

    renderCanvas();
    showDrawingFeedback('点击添加成功');
    return;
  }

  // 如果在编辑模式，检查是否点击了控制点
  if (currentRegion.id && currentRegion.points) {
    const clickedPointIndex = findClickedPoint(point, currentRegion.points);
    if (clickedPointIndex !== -1) {
      // 开始拖拽控制点
      isDraggingPoint.value = true;
      dragPointIndex.value = clickedPointIndex;
      dragRegionId.value = currentRegion.id;
      showDrawingFeedback('拖拽控制点调整区域形状', 'info');
      return;
    }
  }

  // 检查是否点击了某个区域
  const clickedRegion = findClickedRegion(point);
  if (clickedRegion) {
    regionStore.selectRegion(clickedRegion);

    // 同时通知 RegionConfigManager
    if (regionConfigManager) {
      regionConfigManager.selectRegion(clickedRegion.id)
    }

    renderCanvas();
  }
}

// 查找点击的控制点
function findClickedPoint(clickPos: {x: number, y: number}, points: Array<{x: number, y: number}>): number {
  const threshold = 8; // 点击阈值
  for (let i = 0; i < points.length; i++) {
    const distance = Math.sqrt(
      Math.pow(clickPos.x - points[i].x, 2) +
      Math.pow(clickPos.y - points[i].y, 2)
    );
    if (distance <= threshold) {
      return i;
    }
  }
  return -1;
}

// 查找点击的区域
function findClickedRegion(clickPos: {x: number, y: number}) {
  for (const region of regions.value) {
    if (region.points && region.points.length > 2) {
      if (isPointInPolygon(clickPos, region.points)) {
        return region;
      }
    }
  }
  return null;
}

// 判断点是否在多边形内
function isPointInPolygon(point: {x: number, y: number}, polygon: Array<{x: number, y: number}>): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    if (((polygon[i].y > point.y) !== (polygon[j].y > point.y)) &&
        (point.x < (polygon[j].x - polygon[i].x) * (point.y - polygon[i].y) / (polygon[j].y - polygon[i].y) + polygon[i].x)) {
      inside = !inside;
    }
  }
  return inside;
}

async function finishDrawing() {
  if (!regionStore.isDrawing) return

  try {
    if (regionConfigManager) {
      regionConfigManager.finishDrawing()
    }

    await regionStore.finishDrawing()
    announceMessage('区域已创建', 'success')
    showDrawingFeedback('区域创建成功', 'success');
  } catch (error: any) {
    announceMessage(error.message || '创建区域失败', 'error')
    showDrawingFeedback(error.message || '创建区域失败', 'error');
  } finally {
    renderCanvas()
  }
}

async function onCanvasDblClick(e: MouseEvent) {
  if (!regionStore.isDrawing) return
  e.preventDefault()
  showDrawingFeedback('双击完成绘制', 'info');
  await finishDrawing()
}

function onCanvasMouseMove(e: MouseEvent) {
    const p = getCanvasPos(e);
    currentMousePos.value = p;

    // 如果正在拖拽控制点
    if (isDraggingPoint.value && dragPointIndex.value !== -1 && currentRegion.points) {
      // 更新控制点位置
      currentRegion.points[dragPointIndex.value] = { x: p.x, y: p.y };
      renderCanvas();
      return;
    }

    // 如果正在绘制
    if (regionStore.isDrawing) {
        renderCanvas();
    }
}

// 鼠标抬起事件 - 结束拖拽
function onCanvasMouseUp(e: MouseEvent) {
  if (isDraggingPoint.value) {
    isDraggingPoint.value = false;
    dragPointIndex.value = -1;
    dragRegionId.value = '';
    showDrawingFeedback('控制点调整完成', 'success');

    // 自动保存编辑的区域
    if (currentRegion.id) {
      saveRegionEdit();
    }
  }
}

// 鼠标离开画布 - 取消拖拽
function onCanvasMouseLeave(e: MouseEvent) {
  if (isDraggingPoint.value) {
    isDraggingPoint.value = false;
    dragPointIndex.value = -1;
    dragRegionId.value = '';
    showDrawingFeedback('已取消拖拽', 'warning');
  }
}

// 操作引导和反馈
const feedbackMessage = ref('');
const feedbackType = ref<'info' | 'success' | 'warning' | 'error'>('info');
const showFeedback = ref(false);

function showDrawingFeedback(message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') {
  feedbackMessage.value = message;
  feedbackType.value = type;
  showFeedback.value = true;
  setTimeout(() => {
    showFeedback.value = false;
  }, 2000);
}

function startDrawingGuide() {
  if (!selectedCamera.value) {
    announceMessage('请先在页面顶部选择摄像头', 'warning');
    return;
  }
  if (!regionStore.backgroundImage) {
    announceMessage('请先在页面顶部上传背景图片', 'warning');
    return;
  }

  showGuide.value = false;
  regionStore.startDrawing();
  showDrawingFeedback('开始绘制区域，点击画布添加顶点，双击完成绘制', 'info');
}

function cancelDrawing() {
  regionStore.cancelDrawing();
  showDrawingFeedback('已取消绘制', 'warning');
  renderCanvas();
}

function showOperationGuide() {
  const guide = `
操作指南：
1. 选择摄像头或上传背景图片
2. 点击"开始绘制"按钮
3. 在画布上点击添加区域顶点
4. 双击完成区域绘制
5. 填写区域信息并保存

编辑模式：
- 点击区域列表中的编辑按钮进入编辑模式
- 在编辑模式下，点击画布上的控制点可拖拽调整
- 拖拽完成后自动保存修改
- 点击其他区域或取消按钮退出编辑模式
  `;
  announceMessage(guide, 'info');
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
  message.info('请在页面顶部选择摄像头，或前往"摄像头管理"添加摄像头')
}

async function onCameraChange(value: string) {
  console.log('selected camera:', value)
  regionStore.selectRegion(null)

  // 切换摄像头时清空区域列表
  if (regions.value.length > 0) {
    dialog.warning({
      title: '切换摄像头',
      content: '切换摄像头将清空当前区域列表，是否继续？',
      positiveText: '继续',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          // 清空当前区域
          regionStore.clearRegions()
          // 加载新摄像头的区域
          await regionStore.fetchRegions(value)
          const cam = cameraStore.cameras.find((c: any) => c.id === value)
          message.success(`已切换到摄像头: ${cam ? cam.name : value}`)
          renderCanvas()
        } catch (error) {
          message.error('加载区域列表失败')
        }
      },
      onNegativeClick: () => {
        // 恢复之前的选择
        selectedCamera.value = selectedCamera.value
      }
    })
  } else {
    try {
      await regionStore.fetchRegions(value) // Fetch regions for the new camera
      const cam = cameraStore.cameras.find((c: any) => c.id === value)
      message.success(`已选择摄像头: ${cam ? cam.name : value}`)
      renderCanvas()
    } catch (error) {
      message.error('加载区域列表失败')
    }
  }
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
    message.warning('请先在页面顶部选择摄像头或上传图片后再绘制')
    return
  }

  if (regionConfigManager) {
    regionConfigManager.startDrawing()
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

// 上传图片功能
function handleImageUpload(options: any) {
  const file = options.file.file
  if (!file) return

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }

  // 验证文件大小 (限制为10MB)
  if (file.size > 10 * 1024 * 1024) {
    message.error('图片文件大小不能超过10MB')
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const img = new Image()
      img.onload = () => {
        // 设置画布尺寸
        canvasWidth.value = img.width
        canvasHeight.value = img.height

        // 设置背景图片
        regionStore.setBackgroundImage(img)

        // 清空当前选择的摄像头（使用上传的图片）
        selectedCamera.value = ''

        // 重新渲染画布
        renderCanvas()

        message.success('图片上传成功')
        announceMessage('背景图片已更新，可以开始绘制区域')
      }
      img.onerror = () => {
        message.error('图片加载失败')
      }
      img.src = e.target?.result as string
    } catch (error) {
      message.error('图片处理失败')
    }
  }
  reader.readAsDataURL(file)
}

// 编辑区域
function editRegion(region: Region) {
  // 选中区域
  regionStore.selectRegion(region)

  // 同时通知 RegionConfigManager
  if (regionConfigManager) {
    regionConfigManager.selectRegion(region.id)
  }

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

  // 清除 RegionConfigManager 的选择
  if (regionConfigManager) {
    regionConfigManager.clearSelection()
  }
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
        // 通知 RegionConfigManager 删除区域
        if (regionConfigManager) {
          regionConfigManager.deleteRegion(regionId)
        }

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

// 左侧面板宽度调整
function onLeftPanelResize(width: number) {
  // 限制面板宽度在合理范围内
  const constrainedWidth = Math.max(minPanelWidth, Math.min(maxPanelWidth, width))
  leftPanelWidth.value = constrainedWidth

  // 保存用户偏好到本地存储
  localStorage.setItem('regionConfig_leftPanelWidth', constrainedWidth.toString())

  // 重新渲染画布以适应新的布局
  nextTick(() => {
    renderCanvas()
  })
}

// 文件大小格式化函数
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 从本地存储恢复面板宽度
function restorePanelWidth() {
  const savedWidth = localStorage.getItem('regionConfig_leftPanelWidth')
  if (savedWidth) {
    const width = parseInt(savedWidth, 10)
    if (!isNaN(width) && width >= minPanelWidth && width <= maxPanelWidth) {
      leftPanelWidth.value = width
    }
  }
}

onMounted(async () => {
  // 恢复面板宽度设置
  restorePanelWidth()

  // 初始化 RegionConfigManager
  if (previewCanvas.value) {
    regionConfigManager = new RegionConfigManager(previewCanvas.value)

    // 设置背景图片（如果有的话）
    if (regionStore.backgroundImage) {
      regionConfigManager.setBackgroundImage(regionStore.backgroundImage as HTMLImageElement)
    }

    // 加载现有区域到 RegionConfigManager
    regions.value.forEach(region => {
      if (region.points && region.points.length > 0) {
        regionConfigManager?.addRegion({
          id: region.id,
          name: region.name || `区域${region.id}`,
          type: region.type || 'detection',
          points: region.points,
          color: region.color || '#18a058',
          enabled: region.enabled !== false
        })
      }
    })

    // 设置事件回调
    regionConfigManager.onRegionCreated = (region) => {
      // 将新创建的区域添加到 store
      regionStore.addRegion({
        id: region.id,
        name: region.name,
        type: region.type,
        points: region.points,
        color: region.color,
        enabled: region.enabled,
        sensitivity: 60,
        threshold: 0.7,
        interval: 2,
        minSize: 30,
        alertDelay: 2
      })
      announceMessage(`区域 ${region.name} 已创建`)
    }

    regionConfigManager.onRegionChanged = (regionId) => {
      // 区域变更时的处理
      const region = regionConfigManager?.getRegion(regionId)
      if (region) {
        regionStore.updateRegion(regionId, region)
        announceMessage(`区域 ${region.name} 已更新`)
      }
    }

    regionConfigManager.onRegionDeleted = (regionId) => {
      // 区域删除时的处理
      regionStore.deleteRegion(regionId)
      announceMessage('区域已删除')
    }

    regionConfigManager.onRegionSelected = (regionId) => {
      // 区域选择时的处理
      const region = regionStore.getRegionById(regionId)
      if (region) {
        regionStore.selectRegion(region)
        Object.assign(currentRegion, region)
      }
    }
  }

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
  announceMessage('区域配置页面已加载，请在页面顶部选择摄像头开始配置')
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

.region-item.editing {
  border-color: var(--warning-color);
  background: var(--warning-color-hover);
  box-shadow: 0 0 0 2px var(--warning-color-opacity);
}

.region-item.editing .region-header {
  position: relative;
}

.region-item.editing .region-header::before {
  content: '编辑中';
  position: absolute;
  top: -8px;
  right: 0;
  background: var(--warning-color);
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  z-index: 1;
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
  display: flex;
  flex-direction: column;
}

.preview-container {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: var(--card-color);
  border-radius: 6px;
  overflow: hidden;
}

.preview-container.drawing-mode {
  cursor: crosshair;
}

.preview-container.has-background {
  background: #f5f5f5;
}

.canvas-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.preview-canvas {
  max-width: 100%;
  max-height: 100%;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease;
  transform-origin: center;
  background: white;
}

.preview-canvas:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 画布工具栏样式 */
.canvas-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
}

.canvas-toolbar .n-button {
  transition: all 0.3s ease;
}

.canvas-toolbar .n-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.zoom-display {
  min-width: 60px;
  font-weight: 500;
}

/* 状态标签动画 */
.n-tag {
  transition: all 0.3s ease;
  animation: fadeInScale 0.3s ease-out;
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 绘制提示样式 */
.drawing-hint {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(24, 160, 88, 0.9);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  z-index: 10;
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.region-tooltip {
  position: absolute;
  z-index: 100;
  pointer-events: none;
  transform: translate(-50%, -100%);
  margin-top: -8px;
}

/* 画布信息显示 */
.canvas-info {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .main-layout {
    flex-direction: column;
    gap: 16px;
  }

  .left-panel {
    width: 100%;
    max-width: none;
  }

  .right-panel {
    width: 100%;
  }

  .preview-container {
    min-height: 300px;
  }
}

@media (max-width: 768px) {
  .region-config-container {
    padding: 12px;
  }

  .main-layout {
    gap: 12px;
  }

  .left-panel .arco-card {
    margin-bottom: 12px;
  }

  .camera-selection {
    flex-direction: column;
    gap: 8px;
  }

  .camera-selection .arco-select {
    width: 100%;
  }

  .region-form {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .region-form .form-row {
    flex-direction: column;
    gap: 8px;
  }

  .region-form .form-row .arco-input-number,
  .region-form .form-row .arco-select {
    width: 100%;
  }

  .region-actions {
    flex-direction: column;
    gap: 8px;
  }

  .region-actions .arco-btn {
    width: 100%;
  }

  .preview-card .arco-card-header {
    padding: 12px;
  }

  .preview-card .arco-card-body {
    padding: 12px;
  }

  .preview-container {
    min-height: 250px;
  }

  .canvas-toolbar {
    flex-wrap: wrap;
    gap: 8px;
  }

  .canvas-toolbar .arco-btn-group {
    flex: 1;
    min-width: 120px;
  }

  .drawing-hint {
    font-size: 12px;
    padding: 6px 12px;
  }

  .canvas-info {
    bottom: 8px;
    right: 8px;
    font-size: 11px;
    padding: 6px 8px;
  }
}

@media (max-width: 480px) {
  .region-config-container {
    padding: 8px;
  }

  .main-layout {
    gap: 8px;
  }

  .left-panel .arco-card {
    margin-bottom: 8px;
  }

  .region-form {
    gap: 8px;
  }

  .region-item {
    padding: 8px;
  }

  .region-actions {
    gap: 6px;
  }

  .preview-container {
    min-height: 200px;
  }

  .canvas-toolbar .arco-btn {
    padding: 4px 8px;
    font-size: 12px;
  }

  .drawing-hint {
    font-size: 11px;
    padding: 4px 8px;
  }
}

/* 平板端适配 */
@media (min-width: 769px) and (max-width: 1024px) {
  .main-layout {
    gap: 20px;
  }

  .left-panel {
    width: 400px;
  }

  .region-form {
    grid-template-columns: 1fr 1fr;
  }

  .preview-container {
    min-height: 350px;
  }
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .region-item {
    padding: 16px;
  }

  .arco-btn {
    min-height: 44px;
    padding: 8px 16px;
  }

  .canvas-toolbar .arco-btn {
    min-height: 40px;
    min-width: 40px;
  }

  .preview-canvas {
    cursor: pointer;
  }

  .preview-container.drawing-mode {
    cursor: pointer;
  }
}

/* 操作引导和反馈样式 */
.operation-guide {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  z-index: 20;
}

.feedback-alert {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  min-width: 200px;
  max-width: 400px;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* 空状态样式 */
.canvas-empty-state {
  padding: 60px 20px;
}

.no-camera-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
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

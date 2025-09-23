<template>
  <div class="performance-monitor">
    <!-- 性能监控触发按钮 -->
    <n-button
      v-if="!showMonitor"
      class="monitor-trigger"
      circle
      size="small"
      type="info"
      @click="toggleMonitor"
    >
      <template #icon>
        <n-icon><DashboardOutlined /></n-icon>
      </template>
    </n-button>

    <!-- 性能监控面板 -->
    <n-drawer
      v-model:show="showMonitor"
      :width="400"
      placement="right"
      :trap-focus="false"
      :block-scroll="false"
    >
      <n-drawer-content title="性能监控" closable>
        <div class="monitor-content">
          <!-- 性能评分 -->
          <n-card class="score-card" size="small">
            <div class="performance-score">
              <div class="score-circle" :class="getScoreClass(performanceScore)">
                <span class="score-value">{{ performanceScore }}</span>
                <span class="score-label">分</span>
              </div>
              <div class="score-info">
                <h4>性能评分</h4>
                <p class="score-description">{{ getScoreDescription(performanceScore) }}</p>
              </div>
            </div>
          </n-card>

          <!-- 关键指标 -->
          <n-card class="metrics-card" size="small">
            <template #header>
              <div class="card-header">
                <n-icon><SpeedOutlined /></n-icon>
                <span>关键指标</span>
              </div>
            </template>

            <div class="metrics-grid">
              <div class="metric-item">
                <div class="metric-label">加载时间</div>
                <div class="metric-value">
                  {{ formatTime(metrics.loadTime) }}
                </div>
              </div>

              <div class="metric-item">
                <div class="metric-label">首次绘制</div>
                <div class="metric-value">
                  {{ formatTime(metrics.firstContentfulPaint) }}
                </div>
              </div>

              <div class="metric-item">
                <div class="metric-label">帧率</div>
                <div class="metric-value">
                  {{ metrics.frameRate || 0 }} FPS
                </div>
              </div>

              <div class="metric-item">
                <div class="metric-label">内存使用</div>
                <div class="metric-value">
                  {{ formatMemory(metrics.memoryUsage) }}
                </div>
              </div>
            </div>
          </n-card>

          <!-- 帧率图表 -->
          <n-card class="chart-card" size="small">
            <template #header>
              <div class="card-header">
                <n-icon><LineChartOutlined /></n-icon>
                <span>帧率趋势</span>
              </div>
            </template>

            <div class="frame-rate-chart">
              <canvas
                ref="chartCanvas"
                :width="chartWidth"
                :height="chartHeight"
              ></canvas>
            </div>
          </n-card>

          <!-- 资源分析 -->
          <n-card class="resources-card" size="small">
            <template #header>
              <div class="card-header">
                <n-icon><FileOutlined /></n-icon>
                <span>资源分析</span>
              </div>
            </template>

            <div class="resource-summary">
              <div class="summary-item">
                <span class="summary-label">总资源数:</span>
                <span class="summary-value">{{ resources.length }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">缓存命中:</span>
                <span class="summary-value">{{ cachedResourcesCount }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">总大小:</span>
                <span class="summary-value">{{ formatSize(totalResourceSize) }}</span>
              </div>
            </div>

            <div class="resource-types">
              <div
                v-for="type in resourceTypes"
                :key="type.name"
                class="resource-type"
              >
                <div class="type-info">
                  <span class="type-name">{{ type.name }}</span>
                  <span class="type-count">{{ type.count }}</span>
                </div>
                <div class="type-bar">
                  <div
                    class="type-fill"
                    :style="{ width: `${(type.count / resources.length) * 100}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </n-card>

          <!-- 性能建议 -->
          <n-card class="suggestions-card" size="small">
            <template #header>
              <div class="card-header">
                <n-icon><BulbOutlined /></n-icon>
                <span>优化建议</span>
              </div>
            </template>

            <div class="suggestions-list">
              <div
                v-for="(suggestion, index) in suggestions"
                :key="index"
                class="suggestion-item"
              >
                <n-icon class="suggestion-icon"><InfoCircleOutlined /></n-icon>
                <span class="suggestion-text">{{ suggestion }}</span>
              </div>

              <div v-if="suggestions.length === 0" class="no-suggestions">
                <n-icon><CheckCircleOutlined /></n-icon>
                <span>性能表现良好，暂无优化建议</span>
              </div>
            </div>
          </n-card>

          <!-- 操作按钮 -->
          <div class="monitor-actions">
            <n-button
              type="primary"
              size="small"
              @click="refreshMetrics"
              :loading="isRefreshing"
            >
              <template #icon>
                <n-icon><ReloadOutlined /></n-icon>
              </template>
              刷新数据
            </n-button>

            <n-button
              size="small"
              @click="exportReport"
            >
              <template #icon>
                <n-icon><DownloadOutlined /></n-icon>
              </template>
              导出报告
            </n-button>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import {
  NButton,
  NIcon,
  NDrawer,
  NDrawerContent,
  NCard
} from 'naive-ui'
import {
  SpeedometerOutline as DashboardOutlined,
  FlashOutline as SpeedOutlined,
  TrendingUpOutline as LineChartOutlined,
  DocumentOutline as FileOutlined,
  BulbOutline as BulbOutlined,
  InformationCircleOutline as InfoCircleOutlined,
  CheckmarkCircleOutline as CheckCircleOutlined,
  RefreshOutline as ReloadOutlined,
  DownloadOutline as DownloadOutlined
} from '@vicons/ionicons5'
import { usePerformance } from '@/composables/usePerformance'

// 性能监控
const {
  metrics,
  resources,
  frameRateHistory,
  getPerformanceScore,
  getPerformanceSuggestions,
  exportReport: exportPerformanceReport,
  startMonitoring
} = usePerformance()

// 组件状态
const showMonitor = ref(false)
const isRefreshing = ref(false)
const chartCanvas = ref<HTMLCanvasElement>()
const chartWidth = 350
const chartHeight = 120

// 计算属性
const performanceScore = computed(() => getPerformanceScore())
const suggestions = computed(() => getPerformanceSuggestions())

const cachedResourcesCount = computed(() =>
  resources.value.filter(r => r.cached).length
)

const totalResourceSize = computed(() =>
  resources.value.reduce((total, r) => total + r.size, 0)
)

const resourceTypes = computed(() => {
  const types: { [key: string]: number } = {}

  resources.value.forEach(resource => {
    types[resource.type] = (types[resource.type] || 0) + 1
  })

  return Object.entries(types)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})

// 方法
const toggleMonitor = () => {
  showMonitor.value = !showMonitor.value
}

const getScoreClass = (score: number): string => {
  if (score >= 90) return 'score-excellent'
  if (score >= 70) return 'score-good'
  if (score >= 50) return 'score-fair'
  return 'score-poor'
}

const getScoreDescription = (score: number): string => {
  if (score >= 90) return '优秀'
  if (score >= 70) return '良好'
  if (score >= 50) return '一般'
  return '需要优化'
}

const formatTime = (time?: number): string => {
  if (!time) return '-'
  if (time < 1000) return `${Math.round(time)}ms`
  return `${(time / 1000).toFixed(1)}s`
}

const formatMemory = (memory?: number): string => {
  if (!memory) return '-'
  return `${memory.toFixed(1)}MB`
}

const formatSize = (size: number): string => {
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
  return `${(size / 1024 / 1024).toFixed(1)}MB`
}

const drawFrameRateChart = () => {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const data = frameRateHistory.value
  if (data.length === 0) return

  // 清空画布
  ctx.clearRect(0, 0, chartWidth, chartHeight)

  // 设置样式
  ctx.strokeStyle = '#18a058'
  ctx.fillStyle = 'rgba(24, 160, 88, 0.1)'
  ctx.lineWidth = 2

  // 计算坐标
  const maxFps = Math.max(...data, 60)
  const minFps = Math.min(...data, 0)
  const range = maxFps - minFps || 1

  const stepX = chartWidth / (data.length - 1 || 1)
  const stepY = chartHeight / range

  // 绘制区域
  ctx.beginPath()
  ctx.moveTo(0, chartHeight)

  data.forEach((fps, index) => {
    const x = index * stepX
    const y = chartHeight - ((fps - minFps) * stepY)

    if (index === 0) {
      ctx.lineTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })

  ctx.lineTo(chartWidth, chartHeight)
  ctx.closePath()
  ctx.fill()

  // 绘制线条
  ctx.beginPath()
  data.forEach((fps, index) => {
    const x = index * stepX
    const y = chartHeight - ((fps - minFps) * stepY)

    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  ctx.stroke()

  // 绘制参考线 (60fps)
  if (maxFps > 60) {
    const y60 = chartHeight - ((60 - minFps) * stepY)
    ctx.strokeStyle = '#f0a020'
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(0, y60)
    ctx.lineTo(chartWidth, y60)
    ctx.stroke()
    ctx.setLineDash([])
  }
}

const refreshMetrics = async () => {
  isRefreshing.value = true
  try {
    await startMonitoring()
    await nextTick()
    drawFrameRateChart()
  } finally {
    isRefreshing.value = false
  }
}

const exportReport = () => {
  exportPerformanceReport()
}

// 监听器
watch(frameRateHistory, () => {
  nextTick(() => {
    drawFrameRateChart()
  })
}, { deep: true })

watch(showMonitor, (show) => {
  if (show) {
    nextTick(() => {
      drawFrameRateChart()
    })
  }
})

// 生命周期
onMounted(() => {
  // 延迟绘制图表
  setTimeout(() => {
    drawFrameRateChart()
  }, 1000)
})
</script>

<style scoped>
.performance-monitor {
  position: relative;
}

.monitor-trigger {
  position: fixed;
  top: 100px;
  right: var(--space-medium);
  z-index: 1000;
  box-shadow: var(--box-shadow);
}

.monitor-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-medium);
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-small);
}

/* 性能评分 */
.score-card {
  background: linear-gradient(135deg, var(--primary-color-suppl), var(--info-color-suppl));
}

.performance-score {
  display: flex;
  align-items: center;
  gap: var(--space-large);
}

.score-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  background: var(--card-color);
  box-shadow: var(--box-shadow);
}

.score-circle::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  padding: 3px;
  background: conic-gradient(from 0deg, var(--success-color), var(--warning-color), var(--error-color));
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: xor;
}

.score-excellent::before {
  background: conic-gradient(from 0deg, var(--success-color) 0%, var(--success-color) 100%);
}

.score-good::before {
  background: conic-gradient(from 0deg, var(--success-color) 0%, var(--warning-color) 100%);
}

.score-fair::before {
  background: conic-gradient(from 0deg, var(--warning-color) 0%, var(--warning-color) 100%);
}

.score-poor::before {
  background: conic-gradient(from 0deg, var(--error-color) 0%, var(--error-color) 100%);
}

.score-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color-1);
}

.score-label {
  font-size: 12px;
  color: var(--text-color-3);
}

.score-info h4 {
  margin: 0 0 var(--space-tiny) 0;
  color: var(--text-color-1);
}

.score-description {
  margin: 0;
  color: var(--text-color-2);
  font-size: 14px;
}

/* 指标网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-medium);
}

.metric-item {
  text-align: center;
  padding: var(--space-small);
  background: var(--hover-color);
  border-radius: var(--border-radius);
}

.metric-label {
  font-size: 12px;
  color: var(--text-color-3);
  margin-bottom: var(--space-tiny);
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-1);
}

/* 图表 */
.frame-rate-chart {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--hover-color);
  border-radius: var(--border-radius);
}

/* 资源分析 */
.resource-summary {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-medium);
  padding: var(--space-small);
  background: var(--hover-color);
  border-radius: var(--border-radius);
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-tiny);
}

.summary-label {
  font-size: 12px;
  color: var(--text-color-3);
}

.summary-value {
  font-weight: 600;
  color: var(--text-color-1);
}

.resource-types {
  display: flex;
  flex-direction: column;
  gap: var(--space-small);
}

.resource-type {
  display: flex;
  align-items: center;
  gap: var(--space-small);
}

.type-info {
  display: flex;
  justify-content: space-between;
  min-width: 100px;
  font-size: 14px;
}

.type-name {
  color: var(--text-color-2);
}

.type-count {
  color: var(--text-color-1);
  font-weight: 600;
}

.type-bar {
  flex: 1;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}

.type-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

/* 建议列表 */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-small);
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-small);
  padding: var(--space-small);
  background: var(--warning-color-suppl);
  border-radius: var(--border-radius);
  border-left: 3px solid var(--warning-color);
}

.suggestion-icon {
  color: var(--warning-color);
  margin-top: 2px;
  flex-shrink: 0;
}

.suggestion-text {
  color: var(--text-color-2);
  font-size: 14px;
  line-height: 1.4;
}

.no-suggestions {
  display: flex;
  align-items: center;
  gap: var(--space-small);
  padding: var(--space-medium);
  color: var(--success-color);
  text-align: center;
  justify-content: center;
}

/* 操作按钮 */
.monitor-actions {
  display: flex;
  gap: var(--space-small);
  margin-top: auto;
  padding-top: var(--space-medium);
  border-top: 1px solid var(--border-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .monitor-trigger {
    top: 80px;
    right: var(--space-small);
  }

  .performance-score {
    flex-direction: column;
    text-align: center;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .resource-summary {
    flex-direction: column;
    gap: var(--space-small);
  }

  .monitor-actions {
    flex-direction: column;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .score-circle {
    border: 2px solid var(--text-color-1);
  }

  .metric-item,
  .resource-summary,
  .suggestion-item {
    border: 1px solid var(--border-color);
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .type-fill {
    transition: none;
  }
}
</style>

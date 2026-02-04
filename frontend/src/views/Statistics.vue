<template>
  <div class="professional-statistics">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">数据分析</h1>
        <p class="page-subtitle">多维度数据统计与趋势分析，辅助决策优化</p>
      </div>
      <div class="header-actions">
        <n-date-picker
          v-model:value="dateRange"
          type="daterange"
          clearable
          style="width: 280px"
        />
        <n-button type="primary" @click="handleExport">
          <template #icon><n-icon><DownloadOutline /></n-icon></template>
          导出报表
        </n-button>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <div class="metrics-grid">
      <div class="metric-card metric-card-blue">
        <div class="metric-header">
          <div class="metric-icon">
            <n-icon size="28"><EyeOutline /></n-icon>
          </div>
          <div class="metric-trend trend-up">
            <n-icon size="16"><TrendingUpOutline /></n-icon>
            <span>+12.5%</span>
          </div>
        </div>
        <div class="metric-value">{{ totalDetections.toLocaleString() }}</div>
        <div class="metric-label">总检测次数</div>
        <div class="metric-footer">
          <span class="metric-period">较上周</span>
        </div>
      </div>

      <div class="metric-card metric-card-red">
        <div class="metric-header">
          <div class="metric-icon">
            <n-icon size="28"><WarningOutline /></n-icon>
          </div>
          <div class="metric-trend trend-down">
            <n-icon size="16"><TrendingDownOutline /></n-icon>
            <span>-8.3%</span>
          </div>
        </div>
        <div class="metric-value">{{ violationCount.toLocaleString() }}</div>
        <div class="metric-label">违规事件</div>
        <div class="metric-footer">
          <span class="metric-period">较上周</span>
        </div>
      </div>

      <div class="metric-card metric-card-green">
        <div class="metric-header">
          <div class="metric-icon">
            <n-icon size="28"><CheckmarkCircleOutline /></n-icon>
          </div>
          <div class="metric-trend trend-up">
            <n-icon size="16"><TrendingUpOutline /></n-icon>
            <span>+5.2%</span>
          </div>
        </div>
        <div class="metric-value">{{ complianceRate }}%</div>
        <div class="metric-label">合规率</div>
        <div class="metric-footer">
          <span class="metric-period">较上周</span>
        </div>
      </div>

      <div class="metric-card metric-card-orange">
        <div class="metric-header">
          <div class="metric-icon">
            <n-icon size="28"><TimeOutline /></n-icon>
          </div>
          <div class="metric-trend trend-down">
            <n-icon size="16"><TrendingDownOutline /></n-icon>
            <span>-15.7%</span>
          </div>
        </div>
        <div class="metric-value">{{ avgResponseTime }}s</div>
        <div class="metric-label">平均响应时间</div>
        <div class="metric-footer">
          <span class="metric-period">较上周</span>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 检测趋势图 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">检测趋势</h3>
          <n-radio-group v-model:value="trendPeriod" size="small">
            <n-radio-button value="day">日</n-radio-button>
            <n-radio-button value="week">周</n-radio-button>
            <n-radio-button value="month">月</n-radio-button>
          </n-radio-group>
        </div>
        <div class="chart-content">
          <div class="chart-placeholder">
            <n-icon size="48" color="#8C9BAB"><BarChartOutline /></n-icon>
            <p>检测趋势图表</p>
          </div>
        </div>
      </div>

      <!-- 违规类型分布 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">违规类型分布</h3>
        </div>
        <div class="chart-content">
          <div class="violation-types">
            <div class="type-item" v-for="item in violationTypes" :key="item.type">
              <div class="type-info">
                <span class="type-name">{{ item.type }}</span>
                <span class="type-count">{{ item.count }}</span>
              </div>
              <div class="type-bar">
                <div class="type-bar-fill" :style="{ width: item.percentage + '%', background: item.color }"></div>
              </div>
              <span class="type-percentage">{{ item.percentage }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 摄像头统计 -->
    <div class="camera-stats-card">
      <div class="card-header">
        <h3 class="card-title">摄像头检测统计</h3>
        <n-input
          v-model:value="searchCamera"
          placeholder="搜索摄像头"
          clearable
          style="width: 200px"
        >
          <template #prefix>
            <n-icon><SearchOutline /></n-icon>
          </template>
        </n-input>
      </div>
      <div class="camera-list">
        <div class="camera-item" v-for="camera in filteredCameras" :key="camera.id">
          <div class="camera-info">
            <div class="camera-name">{{ camera.name }}</div>
            <div class="camera-location">{{ camera.location }}</div>
          </div>
          <div class="camera-metrics">
            <div class="camera-metric">
              <span class="metric-label">检测次数</span>
              <span class="metric-value">{{ camera.detections }}</span>
            </div>
            <div class="camera-metric">
              <span class="metric-label">违规次数</span>
              <span class="metric-value metric-value-danger">{{ camera.violations }}</span>
            </div>
            <div class="camera-metric">
              <span class="metric-label">合规率</span>
              <span class="metric-value" :class="camera.compliance >= 95 ? 'metric-value-success' : ''">
                {{ camera.compliance }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 时段分析 -->
    <div class="time-analysis-card">
      <div class="card-header">
        <h3 class="card-title">时段分析</h3>
        <p class="card-subtitle">24小时违规事件分布热力图</p>
      </div>
      <div class="heatmap-container">
        <div class="heatmap-placeholder">
          <n-icon size="48" color="#8C9BAB"><GridOutline /></n-icon>
          <p>时段热力图</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NButton, NDatePicker, NIcon, NRadioGroup, NRadioButton, NInput, useMessage } from 'naive-ui'
import {
  DownloadOutline,
  EyeOutline,
  WarningOutline,
  CheckmarkCircleOutline,
  TimeOutline,
  TrendingUpOutline,
  TrendingDownOutline,
  BarChartOutline,
  SearchOutline,
  GridOutline
} from '@vicons/ionicons5'

// 导入 API
import { getRealtimeStatistics, getViolationTypes } from '@/api/modules/statistics'
import { getCameras } from '@/api/modules/cameras'
import { exportStatistics } from '@/api/modules/export'

const message = useMessage()

// 日期范围
const dateRange = ref<[number, number] | null>(null)
const trendPeriod = ref('week')
const loading = ref(false)

// 核心指标
const totalDetections = ref(0)
const violationCount = ref(0)
const complianceRate = ref(0)
const avgResponseTime = ref(0)

// 违规类型分布
const violationTypes = ref<any[]>([])

// 摄像头统计
const searchCamera = ref('')
const cameras = ref<any[]>([])

const filteredCameras = computed(() => {
  if (!searchCamera.value) return cameras.value
  return cameras.value.filter(c =>
    c.name.toLowerCase().includes(searchCamera.value.toLowerCase()) ||
    c.location.toLowerCase().includes(searchCamera.value.toLowerCase())
  )
})

// 获取统计数据
const fetchStatistics = async () => {
  if (loading.value) return

  loading.value = true
  try {
    // 并发请求多个接口
    const [realtimeStats, violationTypesData, camerasData] = await Promise.all([
      getRealtimeStatistics(),
      getViolationTypes(7), // 最近7天的违规类型分布
      getCameras()
    ])

    // 更新核心指标
    totalDetections.value = realtimeStats.detection_stats.total_detections_today
    violationCount.value = realtimeStats.detection_stats.violation_count

    // 计算合规率
    if (totalDetections.value > 0) {
      complianceRate.value = Number(
        (((totalDetections.value - violationCount.value) / totalDetections.value) * 100).toFixed(1)
      )
    } else {
      complianceRate.value = 0
    }

    // 平均响应时间
    avgResponseTime.value = Number(realtimeStats.performance_metrics.average_processing_time.toFixed(1))

    // 违规类型分布（添加颜色）
    const colors = ['#FF6B6B', '#FF9F43', '#FAAD14', '#8C9BAB', '#1E9FFF', '#52C41A']
    violationTypes.value = violationTypesData.map((item, index) => ({
      ...item,
      color: colors[index % colors.length]
    }))

    // 摄像头统计（简化版，实际应该有每个摄像头的统计数据）
    cameras.value = camerasData.cameras.map(cam => ({
      id: cam.id,
      name: cam.name,
      location: cam.location,
      detections: 0, // 暂无此数据
      violations: 0, // 暂无此数据
      compliance: 0  // 暂无此数据
    }))

    console.log('统计数据加载成功:', {
      detections: totalDetections.value,
      violations: violationCount.value,
      compliance: complianceRate.value,
      types: violationTypes.value.length,
      cameras: cameras.value.length
    })
  } catch (error: any) {
    console.error('获取统计数据失败:', error)
    message.error(error.message || '获取统计数据失败，请稍后重试')

    // 使用默认值
    totalDetections.value = 0
    violationCount.value = 0
    complianceRate.value = 0
    avgResponseTime.value = 0
    violationTypes.value = []
    cameras.value = []
  } finally {
    loading.value = false
  }
}

// 方法
const handleExport = async () => {
  try {
    message.loading('正在导出统计数据...')

    const params: any = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = new Date(dateRange.value[0]).toISOString().split('T')[0]
      params.end_date = new Date(dateRange.value[1]).toISOString().split('T')[0]
    }
    params.format = 'xlsx'

    await exportStatistics(params)
    message.success('导出成功')
  } catch (error: any) {
    console.error('导出失败:', error)
    message.error(error.message || '导出失败')
  }
}

// 初始化
onMounted(() => {
  fetchStatistics()
})
</script>

<style scoped lang="scss">
/**
 * 统计分析页面 - 专业版
 */

// 颜色变量
$color-bg: #F7FAFC;
$color-white: #FFFFFF;
$color-border: #E6EDF5;
$color-text-primary: #1F2D3D;
$color-text-secondary: #6B778C;
$color-text-tertiary: #8C9BAB;

$color-blue: #1E9FFF;
$color-red: #FF6B6B;
$color-green: #52C41A;
$color-orange: #FF9F43;

.professional-statistics {
  padding: 24px;
  background: $color-bg;
  min-height: 100vh;
}

// ===== 页面头部 =====
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: $color-text-secondary;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

// ===== 核心指标卡片 =====
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  padding: 24px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  border-left-width: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  &.metric-card-blue {
    border-left-color: $color-blue;

    .metric-icon {
      color: $color-blue;
      background: rgba(30, 159, 255, 0.1);
    }
  }

  &.metric-card-red {
    border-left-color: $color-red;

    .metric-icon {
      color: $color-red;
      background: rgba(255, 107, 107, 0.1);
    }
  }

  &.metric-card-green {
    border-left-color: $color-green;

    .metric-icon {
      color: $color-green;
      background: rgba(82, 196, 26, 0.1);
    }
  }

  &.metric-card-orange {
    border-left-color: $color-orange;

    .metric-icon {
      color: $color-orange;
      background: rgba(255, 159, 67, 0.1);
    }
  }
}

.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;

  &.trend-up {
    color: $color-green;
  }

  &.trend-down {
    color: $color-red;
  }
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
  margin-bottom: 8px;
  font-variant-numeric: tabular-nums;
}

.metric-label {
  font-size: 14px;
  color: $color-text-secondary;
  margin-bottom: 8px;
}

.metric-footer {
  padding-top: 12px;
  border-top: 1px solid $color-border;
}

.metric-period {
  font-size: 12px;
  color: $color-text-tertiary;
}

// ===== 图表区域 =====
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.chart-card {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid $color-border;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0;
}

.chart-content {
  padding: 24px;
  min-height: 300px;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;

  p {
    margin: 0;
    font-size: 14px;
    color: $color-text-tertiary;
  }
}

// ===== 违规类型分布 =====
.violation-types {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.type-item {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 12px;
  align-items: center;
}

.type-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-name {
  font-size: 14px;
  color: $color-text-primary;
  font-weight: 500;
}

.type-count {
  font-size: 14px;
  color: $color-text-secondary;
  font-variant-numeric: tabular-nums;
}

.type-bar {
  height: 8px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.type-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.type-percentage {
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  font-variant-numeric: tabular-nums;
  min-width: 50px;
  text-align: right;
}

// ===== 摄像头统计 =====
.camera-stats-card {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  margin-bottom: 24px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid $color-border;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0;
}

.card-subtitle {
  font-size: 13px;
  color: $color-text-secondary;
  margin: 4px 0 0 0;
}

.camera-list {
  display: flex;
  flex-direction: column;
}

.camera-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid $color-border;
  transition: background 0.2s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: rgba(0, 0, 0, 0.02);
  }
}

.camera-info {
  flex: 1;
}

.camera-name {
  font-size: 15px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 4px;
}

.camera-location {
  font-size: 13px;
  color: $color-text-secondary;
}

.camera-metrics {
  display: flex;
  gap: 32px;
}

.camera-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;

  .metric-label {
    font-size: 12px;
    color: $color-text-tertiary;
  }

  .metric-value {
    font-size: 16px;
    font-weight: 600;
    color: $color-text-primary;
    font-variant-numeric: tabular-nums;

    &.metric-value-danger {
      color: $color-red;
    }

    &.metric-value-success {
      color: $color-green;
    }
  }
}

// ===== 时段分析 =====
.time-analysis-card {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.heatmap-container {
  padding: 24px;
  min-height: 300px;
}

.heatmap-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;

  p {
    margin: 0;
    font-size: 14px;
    color: $color-text-tertiary;
  }
}

// ===== 响应式 =====
@media (max-width: 1400px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .professional-statistics {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;

    :deep(.n-date-picker) {
      width: 100% !important;
    }
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .camera-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .camera-metrics {
    width: 100%;
    justify-content: space-between;
  }
}
</style>

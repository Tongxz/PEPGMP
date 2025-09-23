<template>
  <div class="statistics-page">
    <!-- 页面头部 -->
    <PageHeader
      title="统计分析"
      subtitle="查看系统检测统计数据和趋势分析"
      icon="📊"
    >
      <template #actions>
        <n-space>
          <n-button type="primary" @click="onRefresh" :loading="loading">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新数据
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 控制栏 -->
    <div class="controls-section">
      <DataCard class="controls-card">
        <n-space align="center" justify="space-between" wrap>
          <n-space align="center" wrap>
            <div class="control-group">
              <n-text strong>摄像头:</n-text>
              <n-select
                v-model:value="selectedCamera"
                :options="cameraOptions"
                placeholder="选择摄像头"
                clearable
                @update:value="onCameraChange"
                style="min-width: 160px"
              />
            </div>
            <div class="control-group">
              <n-text strong>时间范围:</n-text>
              <n-select
                v-model:value="selectedTimeRange"
                :options="timeRangeOptions"
                @update:value="onTimeRangeChange"
                style="min-width: 120px"
              />
            </div>
          </n-space>

          <StatusIndicator
            v-if="summary"
            :status="'success'"
            :text="`共 ${summary.total_events} 条记录`"
            size="medium"
          />
        </n-space>
      </DataCard>
    </div>

    <!-- 主要内容区 -->
    <div class="statistics-content">
      <!-- 标签页 -->
      <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange" size="large">
        <!-- 概览标签页 -->
        <n-tab-pane name="overview" tab="📈 概览">
          <div class="overview-content">
            <!-- 统计卡片 -->
            <div class="stats-cards" v-if="summary">
              <DataCard
                title="总检测次数"
                :value="summary.total_events"
                class="stat-card primary-card"
              >
                <template #icon>
                  <n-icon size="24" color="var(--primary-color)">
                    <StatsChartOutline />
                  </n-icon>
                </template>
              </DataCard>

              <DataCard
                v-for="(count, type) in summary.counts_by_type"
                :key="type"
                :title="getEventTypeText(type)"
                :value="count"
                class="stat-card"
              >
                <template #icon>
                  <n-icon size="24" :color="getEventTypeColor(type)">
                    <CheckmarkCircleOutline />
                  </n-icon>
                </template>
              </DataCard>
            </div>

            <!-- 今日统计图表 -->
            <DataCard title="事件类型分布" class="chart-card">
              <template #extra>
                <n-tag type="info" size="small">
                  <template #icon>
                    <n-icon><PieChartOutline /></n-icon>
                  </template>
                  饼图
                </n-tag>
              </template>

              <div class="chart-container">
                <canvas id="overviewChart" width="400" height="300"></canvas>
              </div>
            </DataCard>
          </div>
        </n-tab-pane>

        <!-- 趋势分析标签页 -->
        <n-tab-pane name="trend" tab="📉 趋势分析">
          <div class="trend-content">
            <div class="chart-grid">
              <DataCard title="合规率趋势" class="chart-card">
                <template #extra>
                  <n-tag type="success" size="small">
                    <template #icon>
                      <n-icon><TrendingUpOutline /></n-icon>
                    </template>
                    趋势
                  </n-tag>
                </template>

                <div class="chart-container">
                  <canvas id="complianceChart" width="400" height="300"></canvas>
                </div>
              </DataCard>

              <DataCard title="检测量统计" class="chart-card">
                <template #extra>
                  <n-tag type="info" size="small">
                    <template #icon>
                      <n-icon><BarChartOutline /></n-icon>
                    </template>
                    柱状图
                  </n-tag>
                </template>

                <div class="chart-container">
                  <canvas id="trendChart" width="400" height="300"></canvas>
                </div>
              </DataCard>
            </div>
          </div>
        </n-tab-pane>

        <!-- 历史记录标签页 -->
        <n-tab-pane name="history" tab="📋 历史记录">
          <div class="history-content">
            <DataCard title="检测记录" class="history-card">
              <template #extra>
                <n-space>
                  <n-tag type="info" size="small">
                    共 {{ events.length }} 条记录
                  </n-tag>
                  <n-button size="small" quaternary @click="exportData">
                    <template #icon>
                      <n-icon><DownloadOutline /></n-icon>
                    </template>
                    导出
                  </n-button>
                </n-space>
              </template>

              <n-data-table
                :columns="historyColumns"
                :data="events"
                :loading="loading"
                :pagination="{ pageSize: 20, showSizePicker: true }"
                striped
                :bordered="false"
                size="medium"
                :scroll-x="1000"
                class="history-table"
              />
            </DataCard>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  NCard, NButton, NSelect, NTabs, NTabPane, NDataTable,
  NSpace, NText, NTag, NIcon
} from 'naive-ui'
import {
  RefreshOutline,
  StatsChartOutline,
  CheckmarkCircleOutline,
  PieChartOutline,
  TrendingUpOutline,
  BarChartOutline,
  DownloadOutline
} from '@vicons/ionicons5'
import { Chart, registerables } from 'chart.js'
import { PageHeader, DataCard, StatusIndicator } from '@/components/common'
import { useStatisticsStore } from '@/stores/statistics'
import { useCameraStore } from '@/stores/camera'

Chart.register(...registerables)

const statisticsStore = useStatisticsStore()
const cameraStore = useCameraStore()

// 响应式数据
const activeTab = ref('overview')
const selectedCamera = ref('')
const selectedTimeRange = ref('24h')
const historyLoading = ref(false)
const overviewChart = ref<Chart | null>(null)
const trendChart = ref<Chart | null>(null)
const complianceChart = ref<Chart | null>(null)

// 计算属性
const cameras = computed(() => cameraStore.cameras)
const summary = computed(() => statisticsStore.summary)
const events = computed(() => statisticsStore.events)
const dailyStats = computed(() => statisticsStore.dailyStats)
const loading = computed(() => statisticsStore.loading)

const cameraOptions = computed(() => [
  { label: '全部摄像头', value: '' },
  ...cameras.value.map(camera => ({
    label: camera.name,
    value: camera.id
  }))
])

const timeRangeOptions = [
  { label: '最近1小时', value: '1h' },
  { label: '最近24小时', value: '24h' },
  { label: '最近7天', value: '7d' }
]

const historyColumns = [
  {
    title: '时间',
    key: 'timestamp',
    render: (row: any) => formatTime(row.timestamp)
  },
  {
    title: '摄像头',
    key: 'camera_name'
  },
  {
    title: '事件类型',
    key: 'event_type',
    render: (row: any) => getEventTypeText(row.event_type)
  },
  {
    title: '置信度',
    key: 'confidence',
    render: (row: any) => (row.confidence * 100).toFixed(1) + '%'
  }
]

// 生命周期
onMounted(async () => {
  await cameraStore.fetchCameras()
  await loadData()
})

onUnmounted(() => {
  destroyCharts()
})

// 方法
async function loadData() {
  try {
    await statisticsStore.fetchSummary(selectedCamera.value || undefined)
    await statisticsStore.fetchEventsByTimeRange(selectedTimeRange.value, selectedCamera.value || undefined)

    if (activeTab.value === 'overview') {
      await nextTick()
      renderOverviewChart()
    } else if (activeTab.value === 'trend') {
      await nextTick()
      renderTrendCharts()
    }
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

function onCameraChange() {
  loadData()
}

function onTimeRangeChange() {
  loadData()
}

function onRefresh() {
  loadData()
}

async function onTabChange(tab: string) {
  activeTab.value = tab

  if (tab === 'overview') {
    await nextTick()
    renderOverviewChart()
  } else if (tab === 'trend') {
    await nextTick()
    renderTrendCharts()
  } else if (tab === 'history') {
    await loadHistoryData()
  }
}

function renderOverviewChart() {
  const canvas = document.getElementById('overviewChart') as HTMLCanvasElement
  if (!canvas || !summary.value) return

  destroyChart('overview')

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const data = summary.value.counts_by_type
  const labels = Object.keys(data)
  const values = Object.values(data)

  overviewChart.value = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom'
        }
      }
    }
  })
}

async function renderTrendCharts() {
  // 获取趋势数据
  await statisticsStore.fetchDailyStats(7, selectedCamera.value || undefined)

  const canvas1 = document.getElementById('complianceChart') as HTMLCanvasElement
  const canvas2 = document.getElementById('trendChart') as HTMLCanvasElement

  if (!canvas1 || !canvas2 || !dailyStats.value.length) return

  destroyChart('compliance')
  destroyChart('trend')

  const stats = dailyStats.value
  const labels = stats.map((stat: any) => stat.date)
  const totalEvents = stats.map((stat: any) => stat.total_events)

  // 合规率趋势图
  const ctx1 = canvas1.getContext('2d')
  if (ctx1) {
    complianceChart.value = new Chart(ctx1, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: '合规率',
          data: stats.map((stat: any) => {
            const handwashing = stat.counts_by_type?.handwashing || 0
            const total = stat.total_events || 1
            return Number(((handwashing / total) * 100).toFixed(1))
          }),
          borderColor: '#36A2EB',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: {
              callback: function(value: any) {
                return value + '%'
              }
            }
          }
        }
      }
    })
  }

  // 检测量统计图
  const ctx2 = canvas2.getContext('2d')
  if (ctx2) {
    trendChart.value = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '检测事件数',
          data: totalEvents,
          backgroundColor: '#4BC0C0'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true
          }
        }
      }
    })
  }
}

function destroyChart(type: string) {
  if (type === 'overview' && overviewChart.value) {
    overviewChart.value.destroy()
    overviewChart.value = null
  } else if (type === 'compliance' && complianceChart.value) {
    complianceChart.value.destroy()
    complianceChart.value = null
  } else if (type === 'trend' && trendChart.value) {
    trendChart.value.destroy()
    trendChart.value = null
  }
}

function destroyCharts() {
  destroyChart('overview')
  destroyChart('compliance')
  destroyChart('trend')
}

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleString('zh-CN')
}

function getEventTypeText(type: string) {
  const typeMap: Record<string, string> = {
    'handwashing': '洗手',
    'no_handwashing': '未洗手',
    'person_detected': '人员检测',
    'hand_detected': '手部检测'
  }
  return typeMap[type] || type
}

async function loadHistoryData() {
  historyLoading.value = true
  try {
    const timeRange = selectedTimeRange.value
    let startTime: string
    const now = new Date()

    if (timeRange === '1h') {
      startTime = new Date(now.getTime() - 60 * 60 * 1000).toISOString()
    } else if (timeRange === '24h') {
      startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()
    } else {
      startTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()
    }

    await statisticsStore.fetchEvents({
      start_time: startTime,
      end_time: now.toISOString(),
      camera_id: selectedCamera.value || undefined,
      limit: 100
    })
  } catch (error) {
    console.error('加载历史数据失败:', error)
  } finally {
    historyLoading.value = false
  }
}

const getEventTypeColor = (type: string) => {
  const colors = {
    'handwashing': 'var(--success-color)',
    'violation': 'var(--error-color)',
    'normal': 'var(--info-color)',
    'warning': 'var(--warning-color)'
  }
  return colors[type] || 'var(--text-color)'
}

const exportData = () => {
  // 导出数据逻辑
  console.log('导出数据')
}
</script>

<style scoped>
.statistics-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-large);
}

.controls-section {
  flex-shrink: 0;
}

.controls-card {
  padding: var(--space-medium);
}

.control-group {
  display: flex;
  align-items: center;
  gap: var(--space-small);
}

.statistics-content {
  flex: 1;
  min-height: 0;
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-large);
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-large);
}

.stat-card {
  min-height: 120px;
}

.primary-card {
  background: linear-gradient(135deg, var(--primary-color-suppl), var(--primary-color));
  color: white;
}

.chart-card {
  flex: 1;
  min-height: 400px;
}

.chart-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: var(--space-medium);
}

.trend-content {
  height: 100%;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--space-large);
  height: 100%;
}

.history-content {
  height: 100%;
}

.history-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-table {
  flex: 1;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }

  .control-group {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-tiny);
  }

  .chart-container {
    min-height: 250px;
  }
}

@media (max-width: 480px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <div class="professional-home">
    <!-- ① 系统状态区 - 全局态势 -->
    <section class="system-status-bar">
      <div class="status-container">
        <div class="status-item status-primary">
          <div class="status-indicator" :class="statusClass"></div>
          <span class="status-label">{{ systemStatus }}</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item">
          <span class="status-label">在线摄像头</span>
          <span class="status-value">{{ onlineCameras }}</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item">
          <span class="status-label">实时检测</span>
          <span class="status-value">{{ detectionRate }}fps</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item status-warning" v-if="pendingAlerts > 0">
          <span class="status-label">待处理异常</span>
          <span class="status-value alert">{{ pendingAlerts }}</span>
        </div>
      </div>
    </section>

    <!-- ② 核心能力入口区 -->
    <section class="core-capabilities">
      <div class="capabilities-grid">
        <!-- 智能检测 -->
        <div class="capability-card card-detection">
          <div class="card-header">
            <div class="card-icon">
              <n-icon size="28"><EyeOutline /></n-icon>
            </div>
            <div class="card-title-group">
              <h3 class="card-title">智能检测</h3>
              <span class="card-badge">AI POWERED</span>
            </div>
          </div>
          <p class="card-description">基于深度学习的人体行为检测与合规分析</p>
          <div class="card-divider"></div>
          <div class="card-metrics">
            <div class="metric-item">
              <span class="metric-value">98.7%</span>
              <span class="metric-label">准确率</span>
            </div>
            <div class="metric-item">
              <span class="metric-value">&lt;50ms</span>
              <span class="metric-label">响应时间</span>
            </div>
          </div>
          <n-button type="primary" class="card-action" @click="router.push('/detection-config')">
            配置检测规则
            <template #icon>
              <n-icon><ArrowForwardOutline /></n-icon>
            </template>
          </n-button>
        </div>

        <!-- 实时监控 -->
        <div class="capability-card card-monitor">
          <div class="card-header">
            <div class="card-icon">
              <n-icon size="28"><TvOutline /></n-icon>
            </div>
            <div class="card-title-group">
              <h3 class="card-title">实时监控</h3>
              <span class="card-badge">LIVE</span>
            </div>
          </div>
          <p class="card-description">多路视频流实时监控与异常行为即时告警</p>
          <div class="card-divider"></div>
          <div class="card-metrics">
            <div class="metric-item">
              <span class="metric-value">{{ onlineCameras }}</span>
              <span class="metric-label">在线摄像头</span>
            </div>
            <div class="metric-item">
              <span class="metric-value">60fps</span>
              <span class="metric-label">视频流畅度</span>
            </div>
          </div>
          <n-button type="primary" class="card-action" @click="router.push('/realtime-monitor')">
            进入监控中心
            <template #icon>
              <n-icon><ArrowForwardOutline /></n-icon>
            </template>
          </n-button>
        </div>

        <!-- 数据分析 -->
        <div class="capability-card card-analytics">
          <div class="card-header">
            <div class="card-icon">
              <n-icon size="28"><StatsChartOutline /></n-icon>
            </div>
            <div class="card-title-group">
              <h3 class="card-title">数据分析</h3>
              <span class="card-badge">ANALYTICS</span>
            </div>
          </div>
          <p class="card-description">多维度数据统计与趋势分析，辅助决策优化</p>
          <div class="card-divider"></div>
          <div class="card-metrics">
            <div class="metric-item">
              <span class="metric-value">1.2M+</span>
              <span class="metric-label">历史记录</span>
            </div>
            <div class="metric-item">
              <span class="metric-value">90天</span>
              <span class="metric-label">存储周期</span>
            </div>
          </div>
          <n-button type="primary" class="card-action" @click="router.push('/statistics')">
            查看统计报表
            <template #icon>
              <n-icon><ArrowForwardOutline /></n-icon>
            </template>
          </n-button>
        </div>

        <!-- 告警管理 -->
        <div class="capability-card card-alert">
          <div class="card-header">
            <div class="card-icon">
              <n-icon size="28"><NotificationsOutline /></n-icon>
            </div>
            <div class="card-title-group">
              <h3 class="card-title">告警管理</h3>
              <span class="card-badge">ALERT</span>
            </div>
          </div>
          <p class="card-description">智能告警分级与处理流程，确保快速响应</p>
          <div class="card-divider"></div>
          <div class="card-metrics">
            <div class="metric-item">
              <span class="metric-value">{{ pendingAlerts }}</span>
              <span class="metric-label">未处理告警</span>
            </div>
            <div class="metric-item">
              <span class="metric-value">&lt;3s</span>
              <span class="metric-label">响应时间</span>
            </div>
          </div>
          <n-button type="primary" class="card-action" @click="router.push('/alerts')">
            查看告警列表
            <template #icon>
              <n-icon><ArrowForwardOutline /></n-icon>
            </template>
          </n-button>
        </div>
      </div>
    </section>

    <!-- ③ 风险 & 告警概览 -->
    <section class="risk-overview" v-if="recentViolations.length > 0">
      <div class="section-header">
        <h2 class="section-title">最近违规事件</h2>
        <n-button text @click="router.push('/detection-records')">
          查看全部
          <template #icon>
            <n-icon><ArrowForwardOutline /></n-icon>
          </template>
        </n-button>
      </div>
      <div class="violations-list">
        <div class="violation-item" v-for="item in recentViolations" :key="item.id">
          <div class="violation-time">{{ formatTime(item.timestamp) }}</div>
          <div class="violation-camera">{{ item.camera }}</div>
          <div class="violation-type">{{ item.type }}</div>
          <div class="violation-status" :class="item.status">{{ item.statusText }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, useMessage } from 'naive-ui'
import {
  EyeOutline,
  TvOutline,
  StatsChartOutline,
  NotificationsOutline,
  ArrowForwardOutline
} from '@vicons/ionicons5'

// 导入 API
import { getSystemStatus } from '@/api/modules/statistics'
import { getRealtimeStatistics } from '@/api/modules/statistics'
import { getCameras } from '@/api/modules/cameras'

const router = useRouter()
const message = useMessage()

// 系统状态
const systemStatus = ref<'ONLINE' | 'WARNING' | 'OFFLINE'>('ONLINE')
const onlineCameras = ref(0)
const detectionRate = ref(0)
const pendingAlerts = ref(0)
const loading = ref(false)

const statusClass = computed(() => ({
  'status-online': systemStatus.value === 'ONLINE',
  'status-warning': systemStatus.value === 'WARNING',
  'status-offline': systemStatus.value === 'OFFLINE'
}))

// 最近违规事件
const recentViolations = ref<any[]>([])

const formatTime = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return `${diff}秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// 获取首页数据
const fetchHomeData = async () => {
  if (loading.value) return

  loading.value = true
  try {
    // 并发请求多个接口
    const [statusData, realtimeStats, camerasData] = await Promise.all([
      getSystemStatus(),
      getRealtimeStatistics(),
      getCameras()
    ])

    // 更新系统状态
    systemStatus.value = statusData.status === 'online' ? 'ONLINE' :
                         statusData.status === 'warning' ? 'WARNING' : 'OFFLINE'
    onlineCameras.value = statusData.onlineCameras
    detectionRate.value = statusData.realtimeFps
    pendingAlerts.value = statusData.activeAlerts

    // 更新最近违规事件
    if (realtimeStats.alerts?.recent_violations?.length > 0) {
      recentViolations.value = realtimeStats.alerts.recent_violations.map((v: any) => ({
        id: v.id || Math.random().toString(36).substr(2, 9),
        timestamp: v.timestamp || new Date().toISOString(),
        camera: v.camera_name || v.camera_id || '未知摄像头',
        type: v.violation_type || v.type || '违规行为',
        status: v.status || 'pending',
        statusText: getStatusText(v.status || 'pending')
      }))
    } else {
      recentViolations.value = []
    }

    console.log('首页数据加载成功:', {
      status: systemStatus.value,
      cameras: onlineCameras.value,
      fps: detectionRate.value,
      alerts: pendingAlerts.value,
      violations: recentViolations.value.length
    })
  } catch (error: any) {
    console.error('获取首页数据失败:', error)
    message.error(error.message || '获取数据失败，请稍后重试')

    // 使用默认值，避免页面空白
    systemStatus.value = 'OFFLINE'
    onlineCameras.value = 0
    detectionRate.value = 0
    pendingAlerts.value = 0
    recentViolations.value = []
  } finally {
    loading.value = false
  }
}

// 状态文本映射
const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    'pending': '待处理',
    'processing': '处理中',
    'resolved': '已处理',
    'false_positive': '误报'
  }
  return statusMap[status] || '未知'
}

// 定时刷新
let updateInterval: NodeJS.Timeout

onMounted(() => {
  // 首次加载
  fetchHomeData()

  // 每30秒刷新一次
  updateInterval = setInterval(() => {
    fetchHomeData()
  }, 30000)
})

onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
})
</script>

<style scoped lang="scss">
/**
 * PEPGMP 专业版首页
 * 设计原则：可信、理性、智能、可操作
 * 不炫、不重、不花、不吵
 */

// ===== 颜色系统 =====
$color-bg: #F7FAFC;
$color-white: #FFFFFF;
$color-border: #E6EDF5;
$color-text-primary: #1F2D3D;
$color-text-secondary: #6B778C;
$color-text-tertiary: #8C9BAB;

// 功能色
$color-detection: #1E9FFF;
$color-monitor: #2BC9C9;
$color-analytics: #FF9F43;
$color-alert: #FF6B6B;

// 状态色
$color-online: #52C41A;
$color-warning: #FAAD14;
$color-offline: #FF4D4F;

// ===== 整体布局 =====
.professional-home {
  min-height: 100vh;
  background: $color-bg;
  padding: 24px 32px;
}

// ===== ① 系统状态区 =====
.system-status-bar {
  margin-bottom: 32px;
  animation: slideDown 0.4s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.status-container {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 24px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;

  &.status-primary {
    font-weight: 600;
  }

  &.status-warning .status-value.alert {
    color: $color-alert;
    font-weight: 600;
  }
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;

  &.status-online {
    background: $color-online;
  }

  &.status-warning {
    background: $color-warning;
  }

  &.status-offline {
    background: $color-offline;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.status-label {
  font-size: 14px;
  color: $color-text-secondary;
}

.status-value {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-primary;
  font-variant-numeric: tabular-nums;
}

.status-divider {
  width: 1px;
  height: 20px;
  background: $color-border;
}

// ===== ② 核心能力入口区 =====
.core-capabilities {
  margin-bottom: 32px;
}

.capabilities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
}

.capability-card {
  background: $color-white;
  border-radius: 14px;
  border: 1px solid $color-border;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.05);
  padding: 24px;
  transition: all 0.2s ease;
  animation: fadeInUp 0.5s ease-out backwards;

  &:nth-child(1) { animation-delay: 0.1s; }
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.3s; }
  &:nth-child(4) { animation-delay: 0.4s; }

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
  }

  // 左侧功能色条
  &.card-detection {
    border-left: 4px solid $color-detection;

    &:hover {
      border-color: $color-detection;
    }

    .card-icon {
      color: $color-detection;
    }

    .card-badge {
      color: $color-detection;
      background: rgba(30, 159, 255, 0.1);
    }

    .metric-value {
      color: $color-detection;
    }
  }

  &.card-monitor {
    border-left: 4px solid $color-monitor;

    &:hover {
      border-color: $color-monitor;
    }

    .card-icon {
      color: $color-monitor;
    }

    .card-badge {
      color: $color-monitor;
      background: rgba(43, 201, 201, 0.1);
    }

    .metric-value {
      color: $color-monitor;
    }
  }

  &.card-analytics {
    border-left: 4px solid $color-analytics;

    &:hover {
      border-color: $color-analytics;
    }

    .card-icon {
      color: $color-analytics;
    }

    .card-badge {
      color: $color-analytics;
      background: rgba(255, 159, 67, 0.1);
    }

    .metric-value {
      color: $color-analytics;
    }
  }

  &.card-alert {
    border-left: 4px solid $color-alert;

    &:hover {
      border-color: $color-alert;
    }

    .card-icon {
      color: $color-alert;
    }

    .card-badge {
      color: $color-alert;
      background: rgba(255, 107, 107, 0.1);
    }

    .metric-value {
      color: $color-alert;
    }
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.card-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.02);
}

.card-title-group {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0;
  line-height: 1.4;
}

.card-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.card-description {
  font-size: 14px;
  color: $color-text-secondary;
  line-height: 1.6;
  margin: 0 0 16px 0;
}

.card-divider {
  height: 1px;
  background: $color-border;
  margin: 16px 0;
}

.card-metrics {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
}

.metric-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.metric-label {
  font-size: 12px;
  color: $color-text-tertiary;
}

.card-action {
  width: 100%;
  height: 40px;
  border-radius: 10px;
  font-weight: 500;
}

// ===== ③ 风险 & 告警概览 =====
.risk-overview {
  animation: fadeInUp 0.5s ease-out 0.5s backwards;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin: 0;
}

.violations-list {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  overflow: hidden;
}

.violation-item {
  display: grid;
  grid-template-columns: 120px 1fr 1fr 100px;
  gap: 16px;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid $color-border;
  transition: background 0.2s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: rgba(0, 0, 0, 0.02);
  }
}

.violation-time {
  font-size: 13px;
  color: $color-text-tertiary;
  font-variant-numeric: tabular-nums;
}

.violation-camera {
  font-size: 14px;
  color: $color-text-primary;
  font-weight: 500;
}

.violation-type {
  font-size: 14px;
  color: $color-text-secondary;
}

.violation-status {
  font-size: 13px;
  font-weight: 500;
  text-align: right;

  &.pending {
    color: $color-alert;
  }

  &.processing {
    color: $color-warning;
  }

  &.resolved {
    color: $color-text-tertiary;
  }
}

// ===== 响应式 =====
@media (max-width: 1200px) {
  .capabilities-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .professional-home {
    padding: 16px;
  }

  .capabilities-grid {
    grid-template-columns: 1fr;
  }

  .status-container {
    flex-wrap: wrap;
    gap: 12px;
  }

  .violation-item {
    grid-template-columns: 1fr;
    gap: 8px;
  }
}
</style>

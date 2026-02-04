<template>
  <n-card title="智能检测状态" class="intelligent-detection-panel">
    <template #header-extra>
      <n-tag :type="stats?.connection_status?.connected ? 'success' : 'error'" size="small">
        {{ stats?.connection_status?.connected ? '实时连接' : '未连接' }}
      </n-tag>
    </template>

    <n-spin :show="loading">
      <n-empty v-if="!loading && !stats" description="暂无数据">
        <template #extra>
          <n-button size="small" @click="loadStats">刷新</n-button>
        </template>
      </n-empty>

      <div v-else>
        <n-grid :cols="2" :x-gap="16" :y-gap="16">
          <!-- 处理统计 -->
          <n-gi>
            <n-statistic
              label="处理效率"
              :value="stats?.processing_efficiency || 0"
              suffix="%"
            />
          </n-gi>
          <n-gi>
            <n-statistic
              label="平均FPS"
              :value="stats?.avg_fps || 0"
              :precision="2"
            />
          </n-gi>
          <n-gi>
            <n-statistic
              label="已处理帧"
              :value="stats?.processed_frames || 0"
            />
          </n-gi>
          <n-gi>
            <n-statistic
              label="已跳过帧"
              :value="stats?.skipped_frames || 0"
            />
          </n-gi>
        </n-grid>

        <!-- 场景分布 -->
        <n-divider />
        <div class="scene-distribution">
          <h4>场景分布</h4>
          <n-space>
            <n-tag type="info">
              静态场景: {{ stats?.scene_distribution?.static || 0 }}
            </n-tag>
            <n-tag type="info">
              动态场景: {{ stats?.scene_distribution?.dynamic || 0 }}
            </n-tag>
            <n-tag type="info">
              关键场景: {{ stats?.scene_distribution?.critical || 0 }}
            </n-tag>
          </n-space>
        </div>

        <!-- 性能监控 -->
        <n-divider />
        <div class="performance-monitoring">
          <h4>性能监控</h4>
          <n-grid :cols="3" :x-gap="12" :y-gap="12">
            <n-gi>
              <n-progress
                type="line"
                :percentage="stats?.performance?.cpu_usage || 0"
                color="#18a058"
                :show-indicator="false"
              />
              <div class="progress-label">
                CPU: {{ stats?.performance?.cpu_usage?.toFixed(1) || 0 }}%
              </div>
            </n-gi>
            <n-gi>
              <n-progress
                type="line"
                :percentage="stats?.performance?.memory_usage || 0"
                color="#18a058"
                :show-indicator="false"
              />
              <div class="progress-label">
                内存: {{ stats?.performance?.memory_usage?.toFixed(1) || 0 }}%
              </div>
            </n-gi>
            <n-gi>
              <n-progress
                type="line"
                :percentage="stats?.performance?.gpu_usage || 0"
                color="#18a058"
                :show-indicator="false"
              />
              <div class="progress-label">
                GPU: {{ stats?.performance?.gpu_usage?.toFixed(1) || 0 }}%
              </div>
            </n-gi>
          </n-grid>
        </div>
      </div>
    </n-spin>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  NCard,
  NTag,
  NGrid,
  NGi,
  NStatistic,
  NDivider,
  NSpace,
  NProgress,
  NSpin,
  NEmpty,
  NButton,
  useMessage,
} from 'naive-ui'
import { statisticsApi } from '@/api/statistics'

const message = useMessage()

// 响应式数据
const loading = ref(false)
const stats = ref<{
  processing_efficiency?: number
  avg_fps?: number
  processed_frames?: number
  skipped_frames?: number
  scene_distribution?: {
    static: number
    dynamic: number
    critical: number
  }
  performance?: {
    cpu_usage: number
    memory_usage: number
    gpu_usage: number
  }
  connection_status?: {
    connected: boolean
    active_cameras: number
  }
  timestamp?: string
} | null>(null)

// 自动刷新定时器
let refreshInterval: number | null = null

// 加载统计数据
async function loadStats() {
  loading.value = true
  try {
    stats.value = await statisticsApi.getDetectionRealtimeStats()
  } catch (error: any) {
    console.error('获取检测实时统计失败:', error)
    message.error('获取检测实时统计失败: ' + (error.message || '未知错误'))
    stats.value = null
  } finally {
    loading.value = false
  }
}

// 启动自动刷新（每30秒）
function startAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  refreshInterval = setInterval(() => {
    loadStats()
  }, 30000) // 30秒刷新一次
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

onMounted(() => {
  loadStats()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.intelligent-detection-panel {
  margin-bottom: 16px;
}

.scene-distribution h4,
.performance-monitoring h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.progress-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style>

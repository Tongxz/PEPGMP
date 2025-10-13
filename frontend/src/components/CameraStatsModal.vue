<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="实时检测监控"
    style="width: 900px"
    :mask-closable="false"
  >
    <template #header-extra>
      <n-space>
        <n-tag :type="stats.running ? 'success' : 'default'" size="small">
          {{ stats.running ? '运行中' : '已停止' }}
        </n-tag>
        <n-button size="small" quaternary circle @click="refreshData">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
        </n-button>
      </n-space>
    </template>

    <n-spin :show="loading">
      <n-space vertical size="large">
        <!-- 基本信息 -->
        <n-descriptions bordered :column="2" size="small">
          <n-descriptions-item label="摄像头ID">
            <n-text code>{{ cameraId }}</n-text>
          </n-descriptions-item>
          <n-descriptions-item label="进程PID">
            <n-text code>{{ stats.pid || '-' }}</n-text>
          </n-descriptions-item>
          <n-descriptions-item label="日志文件">
            <n-text depth="3" style="font-size: 11px">{{ stats.log_file || '-' }}</n-text>
          </n-descriptions-item>
          <n-descriptions-item label="最后更新">
            <n-text depth="3">{{ stats.stats?.last_detection_time || '-' }}</n-text>
          </n-descriptions-item>
        </n-descriptions>

        <!-- 检测统计 -->
        <n-card title="检测统计" size="small" v-if="stats.running">
          <n-grid cols="4" x-gap="12" y-gap="12" responsive="screen">
            <n-gi>
              <n-statistic label="检测人数">
                <n-number-animation :from="0" :to="stats.stats?.detected_persons || 0" />
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="发网检测">
                <n-number-animation :from="0" :to="stats.stats?.detected_hairnets || 0" />
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="洗手检测">
                <n-number-animation :from="0" :to="stats.stats?.detected_handwash || 0" />
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="处理帧数">
                <n-number-animation :from="0" :to="stats.stats?.processed_frames || 0" />
              </n-statistic>
            </n-gi>
          </n-grid>

          <n-divider style="margin: 16px 0" />

          <n-grid cols="3" x-gap="12">
            <n-gi>
              <n-statistic label="处理FPS">
                <template #default>
                  <n-text>{{ (stats.stats?.avg_fps || 0).toFixed(2) }}</n-text>
                </template>
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="平均检测时间">
                <template #default>
                  <n-text>{{ (stats.stats?.avg_detection_time || 0).toFixed(3) }}s</n-text>
                </template>
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="总帧数">
                <n-number-animation :from="0" :to="stats.stats?.total_frames || 0" />
              </n-statistic>
            </n-gi>
          </n-grid>
        </n-card>

        <!-- 进程已停止提示 -->
        <n-alert v-else type="info" title="检测进程未运行">
          当前摄像头的检测进程未启动，请先启动检测进程。
        </n-alert>

        <!-- 实时日志 -->
        <n-card size="small">
          <template #header>
            <n-space justify="space-between" align="center">
              <n-text>实时日志</n-text>
              <n-space>
                <n-select
                  v-model:value="logLines"
                  :options="logLineOptions"
                  size="small"
                  style="width: 120px"
                  @update:value="loadLogs"
                />
                <n-button size="small" @click="loadLogs">
                  <template #icon>
                    <n-icon><RefreshOutline /></n-icon>
                  </template>
                  刷新
                </n-button>
              </n-space>
            </n-space>
          </template>

          <n-scrollbar style="max-height: 400px">
            <n-code
              :code="logContent"
              language="text"
              :word-wrap="true"
              show-line-numbers
            />
          </n-scrollbar>

          <template #footer>
            <n-text depth="3" style="font-size: 12px">
              共 {{ logs.total_lines || 0 }} 行，显示最新 {{ logs.lines?.length || 0 }} 行
            </n-text>
          </template>
        </n-card>
      </n-space>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-switch v-model:value="autoRefresh" size="small">
          <template #checked>自动刷新</template>
          <template #unchecked>手动刷新</template>
        </n-switch>
        <n-button @click="visible = false">关闭</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import {
  NModal,
  NCard,
  NSpin,
  NSpace,
  NDescriptions,
  NDescriptionsItem,
  NText,
  NStatistic,
  NNumberAnimation,
  NGrid,
  NGi,
  NDivider,
  NAlert,
  NScrollbar,
  NCode,
  NButton,
  NIcon,
  NTag,
  NSwitch,
  NSelect,
  useMessage
} from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { cameraApi } from '@/api/camera'

const props = defineProps<{
  modelValue: boolean
  cameraId: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const message = useMessage()

// 状态
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const stats = ref<any>({
  running: false,
  pid: 0,
  log_file: '',
  stats: {
    total_frames: 0,
    processed_frames: 0,
    detected_persons: 0,
    detected_hairnets: 0,
    detected_handwash: 0,
    avg_fps: 0,
    avg_detection_time: 0,
    last_detection_time: null
  }
})

const logs = ref<any>({
  total_lines: 0,
  lines: []
})

const autoRefresh = ref(false)
const logLines = ref(50)
const logLineOptions = [
  { label: '最新 20 行', value: 20 },
  { label: '最新 50 行', value: 50 },
  { label: '最新 100 行', value: 100 },
  { label: '最新 200 行', value: 200 }
]

let refreshInterval: number | null = null

// 计算属性
const logContent = computed(() => {
  if (!logs.value.lines || logs.value.lines.length === 0) {
    return '暂无日志内容'
  }
  return logs.value.lines.join('\n')
})

// 方法
async function loadStats() {
  if (!props.cameraId) return

  try {
    const data = await cameraApi.getCameraStats(props.cameraId)
    stats.value = data
  } catch (error: any) {
    console.error('获取统计信息失败:', error)
    message.error(error.message || '获取统计信息失败')
  }
}

async function loadLogs() {
  if (!props.cameraId) return

  try {
    const data = await cameraApi.getCameraLogs(props.cameraId, logLines.value)
    logs.value = data
  } catch (error: any) {
    console.error('获取日志失败:', error)
    message.error(error.message || '获取日志失败')
  }
}

async function refreshData() {
  loading.value = true
  try {
    await Promise.all([loadStats(), loadLogs()])
  } finally {
    loading.value = false
  }
}

// 监听弹窗显示
watch(visible, async (show) => {
  if (show) {
    await refreshData()
  }
})

// 监听自动刷新
watch(autoRefresh, (enabled) => {
  if (enabled) {
    refreshInterval = window.setInterval(refreshData, 5000)
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
})

// 清理
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
:deep(.n-statistic .n-statistic-value__content) {
  font-size: 24px;
  font-weight: 600;
}
</style>


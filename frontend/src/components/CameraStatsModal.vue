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
        <n-card title="检测统计" size="small">
          <!-- 运行状态提示 -->
          <n-alert
            v-if="!stats.running"
            type="warning"
            style="margin-bottom: 16px"
            :bordered="false"
          >
            <template #icon>
              <n-icon><InformationCircleOutline /></n-icon>
            </template>
            <n-text>检测进程未运行，显示的是最近一次运行的统计数据</n-text>
          </n-alert>

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
              v-if="logContent && logContent !== '暂无日志内容'"
              :code="logContent"
              language="text"
              :word-wrap="true"
              show-line-numbers
            />
            <n-empty v-else description="暂无日志内容" />
          </n-scrollbar>

          <template #footer>
            <n-text depth="3" style="font-size: 12px">
              <span v-if="logs.message">{{ logs.message }}</span>
              <span v-else>共 {{ logs.total_lines || 0 }} 行，显示最新 {{ logs.lines?.length || 0 }} 行</span>
            </n-text>
          </template>
        </n-card>

        <!-- 违规记录 -->
        <n-card title="违规记录" size="small" v-if="stats.running">
          <n-spin :show="violationsLoading">
            <div v-if="violations.length === 0" style="text-align: center; padding: 20px;">
              <n-empty description="暂无违规记录" />
            </div>
            <n-grid v-else :cols="4" :x-gap="12" :y-gap="12" responsive="screen">
              <n-gi v-for="violation in violations" :key="violation.id">
                <n-card size="small" hoverable class="violation-card">
                  <div class="violation-image-container">
                    <img
                      v-if="violation.snapshot_path"
                      :src="getViolationImageUrl(violation.snapshot_path)"
                      :alt="`违规${violation.id}`"
                      class="violation-image"
                      @error="handleImageError"
                      @click="viewViolationImage(violation)"
                    />
                    <n-empty v-else description="无图片" size="small" />
                    <n-tag
                      :type="getViolationTypeColor(violation.violation_type)"
                      size="small"
                      class="violation-type-tag"
                    >
                      {{ formatViolationType(violation.violation_type) }}
                    </n-tag>
                  </div>
                  <template #footer>
                    <n-space vertical size="small">
                      <n-text depth="3" style="font-size: 11px">
                        {{ formatViolationTime(violation.timestamp) }}
                      </n-text>
                      <n-text depth="3" style="font-size: 10px">
                        置信度: {{ (violation.confidence * 100).toFixed(1) }}%
                      </n-text>
                    </n-space>
                  </template>
                </n-card>
              </n-gi>
            </n-grid>
            <n-pagination
              v-if="violationTotal > violationPageSize"
              v-model:page="violationCurrentPage"
              :page-size="violationPageSize"
              :item-count="violationTotal"
              show-size-picker
              :page-sizes="[12, 24, 48]"
              @update:page="loadViolations"
              @update:page-size="violationPageSize = $event; loadViolations()"
              style="margin-top: 16px; justify-content: center"
            />
          </n-spin>
        </n-card>
      </n-space>
    </n-spin>

    <!-- 违规图片查看对话框 -->
    <n-modal v-model:show="showViolationImageDialog" preset="card" title="违规图片" style="width: 90%; max-width: 1200px;">
      <div v-if="currentViolationImage" class="violation-image-viewer">
        <div style="position: relative; margin-bottom: 16px; text-align: center;">
          <img
            :src="getViolationImageUrl(currentViolationImage.snapshot_path)"
            :alt="`违规${currentViolationImage.id}`"
            style="max-width: 100%; max-height: 60vh; height: auto; display: block; margin: 0 auto; border-radius: 4px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);"
            @error="handleImageError"
          />
          <n-space style="position: absolute; top: 12px; left: 12px; background: rgba(255, 255, 255, 0.9); padding: 4px 8px; border-radius: 4px;" :size="8">
            <n-tag
              :type="getViolationTypeColor(currentViolationImage.violation_type)"
              size="medium"
            >
              {{ formatViolationType(currentViolationImage.violation_type) }}
            </n-tag>
            <n-tag type="info" size="medium">
              置信度: {{ (currentViolationImage.confidence * 100).toFixed(1) }}%
            </n-tag>
          </n-space>
        </div>
        <n-divider />
        <n-descriptions :column="2" size="small" bordered>
          <n-descriptions-item label="违规ID">
            {{ currentViolationImage.id }}
          </n-descriptions-item>
          <n-descriptions-item label="违规类型">
            {{ formatViolationType(currentViolationImage.violation_type) }}
          </n-descriptions-item>
          <n-descriptions-item label="时间">
            {{ formatViolationTime(currentViolationImage.timestamp) }}
          </n-descriptions-item>
          <n-descriptions-item label="置信度">
            {{ (currentViolationImage.confidence * 100).toFixed(1) }}%
          </n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="getStatusTypeColor(currentViolationImage.status)" size="small">
              {{ formatStatus(currentViolationImage.status) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="摄像头ID">
            {{ currentViolationImage.camera_id }}
          </n-descriptions-item>
        </n-descriptions>
      </div>
    </n-modal>

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
  NEmpty,
  NPagination,
  useMessage
} from 'naive-ui'
import { RefreshOutline, InformationCircleOutline } from '@vicons/ionicons5'
import { cameraApi } from '@/api/camera'
import { http } from '@/lib/http'

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

// 违规记录相关
const violations = ref<any[]>([])
const violationsLoading = ref(false)
const violationCurrentPage = ref(1)
const violationPageSize = ref(12)
const violationTotal = ref(0)
const showViolationImageDialog = ref(false)
const currentViolationImage = ref<any>(null)

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
    console.log('[CameraStatsModal] 获取统计信息:', data)
    // 确保数据结构正确
    stats.value = {
      running: data.running ?? false,
      pid: data.pid ?? 0,
      log_file: data.log_file ?? '',
      stats: data.stats ?? {
        total_frames: 0,
        processed_frames: 0,
        detected_persons: 0,
        detected_hairnets: 0,
        detected_handwash: 0,
        avg_fps: 0,
        avg_detection_time: 0,
        last_detection_time: null
      }
    }
    console.log('[CameraStatsModal] 更新后的stats:', stats.value)
  } catch (error: any) {
    console.error('获取统计信息失败:', error)
    message.error(error.message || '获取统计信息失败')
  }
}

async function loadLogs() {
  if (!props.cameraId) return

  try {
    const data = await cameraApi.getCameraLogs(props.cameraId, logLines.value)
    console.log('[CameraStatsModal] 获取日志数据:', data)
    // 确保数据结构正确
    logs.value = {
      total_lines: data.total_lines ?? 0,
      lines: data.lines ?? [],
      log_file: data.log_file ?? '',
      message: data.message ?? ''
    }
    console.log('[CameraStatsModal] 更新后的logs:', logs.value)
  } catch (error: any) {
    console.error('获取日志失败:', error)
    // 如果日志文件不存在，不显示错误，而是显示提示信息
    if (error.response?.status === 404) {
      logs.value = {
        total_lines: 0,
        lines: [],
        log_file: '',
        message: '日志文件不存在（进程可能尚未启动）'
      }
    } else {
      message.error(error.message || '获取日志失败')
    }
  }
}

async function loadViolations() {
  if (!props.cameraId || !stats.value.running) return

  violationsLoading.value = true
  try {
    const params: any = {
      camera_id: props.cameraId,
      limit: violationPageSize.value,
      offset: (violationCurrentPage.value - 1) * violationPageSize.value,
    }

    const res = await http.get('/records/violations', { params })
    violations.value = res.data.violations || []
    violationTotal.value = res.data.total || 0
    console.log('[CameraStatsModal] 加载违规记录:', violations.value.length, '条')
    console.log('[CameraStatsModal] 违规记录详情:', violations.value.map(v => ({
      id: v.id,
      type: v.violation_type,
      snapshot_path: v.snapshot_path,
      confidence: v.confidence
    })))
  } catch (error: any) {
    console.error('加载违规记录失败:', error)
    violations.value = []
    violationTotal.value = 0
  } finally {
    violationsLoading.value = false
  }
}

async function refreshData() {
  loading.value = true
  try {
    console.log('[CameraStatsModal] 开始刷新数据: cameraId=', props.cameraId)
    await Promise.all([loadStats(), loadLogs()])
    // 如果运行中，加载违规记录
    if (stats.value.running) {
      await loadViolations()
    }
    console.log('[CameraStatsModal] 数据刷新完成')
  } catch (error) {
    console.error('[CameraStatsModal] 刷新数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 违规图片相关方法
function getViolationImageUrl(snapshotPath: string): string {
  if (!snapshotPath) return ''
  console.log('[CameraStatsModal] 原始snapshot_path:', snapshotPath)

  // 如果路径是绝对路径（HTTP/HTTPS），直接返回
  if (snapshotPath.startsWith('http://') || snapshotPath.startsWith('https://')) {
    return snapshotPath
  }

  // 处理相对路径（快照路径通常是相对路径，如 "camera_id/2025/11/13/123456_123456_no_hairnet_abc123.jpg"）
  // 直接使用相对路径，后端会尝试在多个目录中查找
  const url = `/api/v1/download/image/${encodeURIComponent(snapshotPath.replace(/\\/g, '/'))}`
  console.log('[CameraStatsModal] 生成的图片URL:', url)
  return url
}

function viewViolationImage(violation: any) {
  currentViolationImage.value = violation
  showViolationImageDialog.value = true
}

function handleImageError(event: Event) {
  console.error('图片加载失败:', event)
  // 可以设置默认图片或隐藏图片
}

function formatViolationType(type: string): string {
  if (!type) return '未知违规'
  const typeMap: Record<string, string> = {
    'no_hairnet': '未戴发网',
    'no_handwash': '未洗手',
    'no_sanitize': '未消毒',
    'no_safety_helmet': '未戴安全帽',
    'no_safety_vest': '未穿安全背心',
    'unauthorized_access': '未授权进入',
    'improper_posture': '姿势不当',
    'equipment_misuse': '设备误用',
    'crowding': '人员聚集',
    'speeding': '超速',
    'wrong_direction': '逆行',
    // 实际检测中可能使用的类型
    'missing_required_behavior': '缺少必需行为',
    'forbidden_behavior_detected': '检测到禁止行为'
  }
  // 如果类型不在映射中，尝试显示原始值或返回"未知违规"
  return typeMap[type] || type || '未知违规'
}

function getViolationTypeColor(type: string): string {
  const colorMap: Record<string, string> = {
    'no_hairnet': 'error',
    'no_handwash': 'warning',
    'no_sanitize': 'warning',
    'no_safety_helmet': 'error',
    'no_safety_vest': 'error',
    'unauthorized_access': 'error',
    'improper_posture': 'warning',
    'equipment_misuse': 'warning',
    'crowding': 'warning',
    'speeding': 'error',
    'wrong_direction': 'error'
  }
  return colorMap[type] || 'default'
}

function formatViolationTime(timestamp: string): string {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timestamp
  }
}

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    'pending': '待处理',
    'confirmed': '已确认',
    'false_positive': '误报',
    'resolved': '已解决'
  }
  return statusMap[status] || status
}

function getStatusTypeColor(status: string): string {
  const colorMap: Record<string, string> = {
    'pending': 'warning',
    'confirmed': 'error',
    'false_positive': 'info',
    'resolved': 'success'
  }
  return colorMap[status] || 'default'
}

// 监听弹窗显示
watch(visible, async (show) => {
  if (show) {
    console.log('[CameraStatsModal] 弹窗打开，刷新数据: cameraId=', props.cameraId)
    // 立即刷新数据，不使用缓存
    await refreshData()
  } else {
    // 弹窗关闭时清理定时器
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
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

.violation-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.violation-card:hover {
  transform: scale(1.02);
}

.violation-image-container {
  position: relative;
  width: 100%;
  height: 150px;
  overflow: hidden;
  border-radius: 4px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.violation-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
}

.violation-type-tag {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 1;
}

.violation-image-viewer {
  max-width: 100%;
}
</style>

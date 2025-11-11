<template>
  <div class="detection-records-container">
    <n-card title="📊 检测历史记录" :bordered="false">
      <!-- 筛选器 -->
      <n-space vertical :size="16">
        <n-space :size="12">
          <n-select
            v-model:value="selectedCamera"
            :options="cameraOptions"
            placeholder="选择摄像头"
            style="width: 200px"
            @update:value="loadRecords"
          />
          <n-date-picker
            v-model:value="dateRange"
            type="datetimerange"
            clearable
            placeholder="选择时间范围"
            @update:value="loadRecords"
          />
          <n-button type="primary" @click="loadRecords" :loading="loading">
            <template #icon>
              <n-icon><Search /></n-icon>
            </template>
            查询
          </n-button>
          <n-button @click="resetFilters">
            <template #icon>
              <n-icon><Refresh /></n-icon>
            </template>
            重置
          </n-button>
          <n-button type="success" @click="exportDetectionRecords" :loading="exporting">
            <template #icon>
              <n-icon><DownloadOutline /></n-icon>
            </template>
            导出检测记录
          </n-button>
        </n-space>

        <!-- 统计卡片 -->
        <n-grid :cols="4" :x-gap="12">
          <n-gi>
            <n-statistic label="总检测帧数" :value="statistics.total_frames">
              <template #prefix>
                <n-icon><FilmOutline /></n-icon>
              </template>
            </n-statistic>
          </n-gi>
          <n-gi>
            <n-statistic label="检测到的人数" :value="statistics.total_persons">
              <template #prefix>
                <n-icon><PeopleCircleOutline /></n-icon>
              </template>
            </n-statistic>
          </n-gi>
          <n-gi>
            <n-statistic
              label="发网违规"
              :value="statistics.total_hairnet_violations"
            >
              <template #prefix>
                <n-icon :style="{ color: 'red' }"><AlertCircleOutline /></n-icon>
              </template>
            </n-statistic>
          </n-gi>
          <n-gi>
            <n-statistic label="平均FPS" :value="statistics.avg_fps?.toFixed(2) || '0.00'">
              <template #prefix>
                <n-icon><TimerOutline /></n-icon>
              </template>
            </n-statistic>
          </n-gi>
        </n-grid>

        <!-- 数据表格 -->
        <n-data-table
          :columns="columns"
          :data="records"
          :loading="loading"
          :pagination="pagination"
          :bordered="false"
          size="small"
          :max-height="500"
        />
      </n-space>
    </n-card>

    <!-- 违规记录卡片 -->
    <n-card title="🚨 违规事件记录" :bordered="false" style="margin-top: 16px">
      <n-space vertical :size="12">
        <n-space :size="12">
          <n-select
            v-model:value="violationStatus"
            :options="statusOptions"
            placeholder="违规状态"
            style="width: 150px"
            @update:value="loadViolations"
          />
          <n-select
            v-model:value="violationType"
            :options="typeOptions"
            placeholder="违规类型"
            style="width: 150px"
            @update:value="loadViolations"
          />
          <n-button type="primary" @click="loadViolations" :loading="violationsLoading">
            查询违规
          </n-button>
          <n-button
            type="success"
            @click="exportViolations"
            :loading="exportingViolations"
            :disabled="violations.length === 0"
          >
            <template #icon>
              <n-icon><DownloadOutline /></n-icon>
            </template>
            导出违规记录
          </n-button>
        </n-space>

        <n-data-table
          :columns="violationColumns"
          :data="violations"
          :loading="violationsLoading"
          :pagination="violationPagination"
          :bordered="false"
          size="small"
          :max-height="400"
        />
      </n-space>
    </n-card>

    <!-- 记录详情弹窗 -->
    <n-modal
      v-model:show="showRecordDetail"
      preset="card"
      title="检测记录详情"
      style="max-width: 800px"
    >
      <n-descriptions :column="2" bordered v-if="selectedRecord">
        <n-descriptions-item label="记录ID">{{ selectedRecord.id }}</n-descriptions-item>
        <n-descriptions-item label="时间">
          {{ new Date(selectedRecord.timestamp).toLocaleString('zh-CN') }}
        </n-descriptions-item>
        <n-descriptions-item label="摄像头ID">{{ selectedRecord.camera_id }}</n-descriptions-item>
        <n-descriptions-item label="帧号">{{ selectedRecord.frame_id || '-' }}</n-descriptions-item>
        <n-descriptions-item label="人数">{{ selectedRecord.person_count || 0 }}</n-descriptions-item>
        <n-descriptions-item label="发网违规">{{ selectedRecord.hairnet_violations || 0 }}</n-descriptions-item>
        <n-descriptions-item label="洗手事件">{{ selectedRecord.handwash_events || 0 }}</n-descriptions-item>
        <n-descriptions-item label="消毒事件">{{ selectedRecord.sanitize_events || 0 }}</n-descriptions-item>
        <n-descriptions-item label="处理时间(ms)">
          {{ (selectedRecord.processing_time * 1000).toFixed(1) }}
        </n-descriptions-item>
        <n-descriptions-item label="置信度">
          {{ selectedRecord.confidence ? (selectedRecord.confidence.value || selectedRecord.confidence) : '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="检测对象" :span="2">
          <pre style="max-height: 200px; overflow: auto;">
            {{ JSON.stringify(selectedRecord.objects || [], null, 2) }}
          </pre>
        </n-descriptions-item>
        <n-descriptions-item label="元数据" :span="2" v-if="selectedRecord.metadata">
          <pre style="max-height: 200px; overflow: auto;">
            {{ JSON.stringify(selectedRecord.metadata, null, 2) }}
          </pre>
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>

    <!-- 状态更新弹窗 -->
    <n-modal
      v-model:show="showStatusUpdate"
      preset="dialog"
      title="更新违规记录状态"
      positive-text="确认"
      negative-text="取消"
      @positive-click="confirmStatusUpdate"
    >
      <n-select
        v-model:value="newStatus"
        :options="statusOptions.filter((opt: any) => opt.value)"
        placeholder="选择新状态"
      />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref, computed } from 'vue'
import {
  NCard,
  NSpace,
  NSelect,
  NDatePicker,
  NButton,
  NIcon,
  NGrid,
  NGi,
  NStatistic,
  NDataTable,
  NTag,
  NModal,
  NDescriptions,
  NDescriptionsItem,
  useMessage,
  useDialog,
  type DataTableColumns,
} from 'naive-ui'
import {
  Search,
  Refresh,
  FilmOutline,
  PeopleCircleOutline,
  AlertCircleOutline,
  TimerOutline,
  DownloadOutline,
  RefreshOutline,
} from '@vicons/ionicons5'
import { http } from '@/lib/http'
import { exportApi, downloadBlob } from '@/api/export'

const message = useMessage()
const dialog = useDialog()

// 详情弹窗
const showRecordDetail = ref(false)
const selectedRecord = ref<any>(null)

// 状态更新弹窗
const showStatusUpdate = ref(false)
const selectedViolation = ref<any>(null)
const newStatus = ref<string>('')

// 摄像头选项
const cameraOptions = ref([
  { label: '全部摄像头', value: 'all' },
  { label: 'USB0', value: 'cam0' },
  { label: '测试视频', value: 'vid1' },
])

// 筛选条件
const selectedCamera = ref('cam0')
// 默认时间范围：最近1小时（优化性能，避免首次加载超时）
const defaultDateRange: [number, number] = [
  Date.now() - 60 * 60 * 1000, // 1小时前
  Date.now() // 当前时间
]
const dateRange = ref<[number, number] | null>(defaultDateRange)

// 违规筛选
const violationStatus = ref<string | undefined>(undefined)
const violationType = ref<string | undefined>(undefined)

const statusOptions = [
  { label: '全部状态', value: undefined },
  { label: '待处理', value: 'pending' },
  { label: '已确认', value: 'confirmed' },
  { label: '误报', value: 'false_positive' },
  { label: '已解决', value: 'resolved' },
]

const typeOptions = [
  { label: '全部类型', value: undefined },
  { label: '未戴发网', value: 'no_hairnet' },
  { label: '未洗手', value: 'no_handwash' },
  { label: '未消毒', value: 'no_sanitize' },
]

// 数据
const records = ref<any[]>([])
const violations = ref<any[]>([])
const statistics = ref({
  total_frames: 0,
  total_persons: 0,
  total_hairnet_violations: 0,
  total_handwash_events: 0,
  total_sanitize_events: 0,
  avg_fps: 0.0,
  avg_processing_time: 0.0,
})

const loading = ref(false)
const violationsLoading = ref(false)
const exporting = ref(false)
const exportingViolations = ref(false)

// 表格列定义
const columns: DataTableColumns<any> = [
  {
    title: 'ID',
    key: 'id',
    width: 60,
  },
  {
    title: '时间',
    key: 'timestamp',
    width: 180,
    render: (row) => new Date(row.timestamp).toLocaleString('zh-CN'),
  },
  {
    title: '帧号',
    key: 'frame_number',
    width: 80,
  },
  {
    title: '人数',
    key: 'person_count',
    width: 70,
  },
  {
    title: '发网违规',
    key: 'hairnet_violations',
    width: 90,
    render: (row) => {
      if (row.hairnet_violations > 0) {
        return h(
          NTag,
          { type: 'error', size: 'small' },
          { default: () => row.hairnet_violations }
        )
      }
      return h(
        NTag,
        { type: 'success', size: 'small' },
        { default: () => '0' }
      )
    },
  },
  {
    title: '洗手事件',
    key: 'handwash_events',
    width: 90,
  },
  {
    title: '消毒事件',
    key: 'sanitize_events',
    width: 90,
  },
  {
    title: 'FPS',
    key: 'fps',
    width: 80,
    render: (row) => row.fps?.toFixed(2) || '0.00',
  },
  {
    title: '处理时间(ms)',
    key: 'processing_time',
    width: 120,
    render: (row) => (row.processing_time * 1000).toFixed(1),
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render: (row) => {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => viewRecordDetail(row),
        },
        { default: () => '详情' }
      )
    },
  },
]

const violationColumns: DataTableColumns<any> = [
  {
    title: 'ID',
    key: 'id',
    width: 60,
  },
  {
    title: '时间',
    key: 'timestamp',
    width: 180,
    render: (row) => new Date(row.timestamp).toLocaleString('zh-CN'),
  },
  {
    title: '摄像头',
    key: 'camera_id',
    width: 120,
  },
  {
    title: '违规类型',
    key: 'violation_type',
    width: 120,
    render: (row) => {
      const typeMap: Record<string, { label: string; type: any }> = {
        no_hairnet: { label: '未戴发网', type: 'error' },
        no_handwash: { label: '未洗手', type: 'warning' },
        no_sanitize: { label: '未消毒', type: 'info' },
      }
      const info = typeMap[row.violation_type] || { label: row.violation_type, type: 'default' }
      return h(NTag, { type: info.type, size: 'small' }, { default: () => info.label })
    },
  },
  {
    title: '置信度',
    key: 'confidence',
    width: 90,
    render: (row) => (row.confidence * 100).toFixed(1) + '%',
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const statusMap: Record<string, { label: string; type: any }> = {
        pending: { label: '待处理', type: 'warning' },
        confirmed: { label: '已确认', type: 'error' },
        false_positive: { label: '误报', type: 'default' },
        resolved: { label: '已解决', type: 'success' },
      }
      const info = statusMap[row.status] || { label: row.status, type: 'default' }
      return h(NTag, { type: info.type, size: 'small' }, { default: () => info.label })
    },
  },
  {
    title: '跟踪ID',
    key: 'track_id',
    width: 80,
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render: (row) => {
      return h(NSpace, { size: 'small' }, () => [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            onClick: () => updateViolationStatus(row),
          },
          { default: () => '更新状态' }
        ),
      ])
    },
  },
]

// 分页状态
const currentPage = ref(1)
const pageSize = ref(20)
const totalRecords = ref(0)

const violationCurrentPage = ref(1)
const violationPageSize = ref(20)
const violationTotalRecords = ref(0)

// 分页配置
const pagination = computed(() => ({
  page: currentPage.value,
  pageSize: pageSize.value,
  itemCount: totalRecords.value,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    currentPage.value = page
    loadRecords()
  },
  onUpdatePageSize: (newPageSize: number) => {
    pageSize.value = newPageSize
    currentPage.value = 1
    loadRecords()
  },
}))

const violationPagination = computed(() => ({
  page: violationCurrentPage.value,
  pageSize: violationPageSize.value,
  itemCount: violationTotalRecords.value,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    violationCurrentPage.value = page
    loadViolations()
  },
  onUpdatePageSize: (newPageSize: number) => {
    violationPageSize.value = newPageSize
    violationCurrentPage.value = 1
    loadViolations()
  },
}))

// 加载检测记录
async function loadRecords() {
  if (selectedCamera.value === 'all') {
    message.warning('暂不支持查询所有摄像头，请选择具体摄像头')
    return
  }

  loading.value = true
  try {
    const params: any = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    }

    // 添加时间范围筛选（用于优化查询性能）
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = new Date(dateRange.value[0]).toISOString()
      params.end_time = new Date(dateRange.value[1]).toISOString()
    }

    // 1. 加载检测记录
    const recordsRes = await http.get(`/records/detection-records/${selectedCamera.value}`, {
      params,
    })
    records.value = recordsRes.data.records || []
    totalRecords.value = recordsRes.data.total || records.value.length

    // 2. 加载统计数据
    const statsRes = await http.get(`/records/statistics/${selectedCamera.value}`, {
      params: {
        period: '7d',
      },
    })
    statistics.value = statsRes.data.statistics || {}

    if (records.value.length > 0) {
      message.success(`加载成功：${records.value.length} 条记录`)
    } else {
      // 如果没有数据，提示用户调整时间范围
      // 检查是否是默认时间范围（最近24小时）
      const isDefaultRange = dateRange.value &&
        dateRange.value[1] - dateRange.value[0] <= 25 * 60 * 60 * 1000 // 大约24小时
      if (isDefaultRange) {
        message.info('默认显示最近24小时的数据，如未找到数据，请尝试选择更长时间范围')
      } else {
        message.warning('未找到符合条件的记录')
      }
    }
  } catch (error: any) {
    message.error('加载失败: ' + (error.response?.data?.detail || error.message))
    console.error('加载记录失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载违规记录
async function loadViolations() {
  violationsLoading.value = true
  try {
    const params: any = {
      limit: violationPageSize.value,
      offset: (violationCurrentPage.value - 1) * violationPageSize.value,
    }

    if (selectedCamera.value && selectedCamera.value !== 'all') {
      params.camera_id = selectedCamera.value
    }

    if (violationStatus.value) {
      params.status = violationStatus.value
    }

    if (violationType.value) {
      params.violation_type = violationType.value
    }

    const res = await http.get('/records/violations', { params })
    violations.value = res.data.violations || []
    violationTotalRecords.value = res.data.total || violations.value.length

    if (violations.value.length > 0) {
      message.success(`查询到 ${violations.value.length} 条违规记录`)
    }
  } catch (error: any) {
    message.error('加载违规记录失败: ' + (error.response?.data?.detail || error.message))
    console.error('加载违规记录失败:', error)
  } finally {
    violationsLoading.value = false
  }
}

// 重置筛选
function resetFilters() {
  selectedCamera.value = 'cam0'
  dateRange.value = null
  violationStatus.value = undefined
  violationType.value = undefined
  currentPage.value = 1
  violationCurrentPage.value = 1
  loadRecords()
  loadViolations()
}

// 查看记录详情
function viewRecordDetail(record: any) {
  selectedRecord.value = record
  showRecordDetail.value = true
}

// 更新违规记录状态
async function updateViolationStatus(violation: any) {
  selectedViolation.value = violation
  newStatus.value = violation.status || 'pending'
  showStatusUpdate.value = true
}

// 确认更新状态
async function confirmStatusUpdate() {
  if (!selectedViolation.value) return

  try {
    await http.put(`/records/violations/${selectedViolation.value.id}/status`, {
      status: newStatus.value,
    })
    message.success('状态更新成功')
    showStatusUpdate.value = false
    await loadViolations()
  } catch (error: any) {
    message.error('更新失败: ' + (error.response?.data?.detail || error.message))
    console.error('更新状态失败:', error)
  }
}

// 导出检测记录
async function exportDetectionRecords() {
  if (!selectedCamera.value || selectedCamera.value === 'all') {
    message.warning('请先选择具体的摄像头')
    return
  }

  exporting.value = true
  try {
    const params: any = {
      camera_id: selectedCamera.value,
      format: 'csv',
      limit: 5000, // 默认5000条，避免超时
    }

    // 添加时间范围
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = new Date(dateRange.value[0]).toISOString()
      params.end_time = new Date(dateRange.value[1]).toISOString()
    }

    const blob = await exportApi.exportDetectionRecords(params)
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
    downloadBlob(blob, `detection_records_${selectedCamera.value}_${timestamp}.csv`)
    message.success('导出成功')
  } catch (error: any) {
    console.error('导出失败:', error)
    message.error('导出失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    exporting.value = false
  }
}

// 导出违规记录
async function exportViolations() {
  exportingViolations.value = true
  try {
    const params: any = {
      format: 'csv',
      limit: 5000, // 默认5000条，避免超时
    }

    if (selectedCamera.value && selectedCamera.value !== 'all') {
      params.camera_id = selectedCamera.value
    }
    if (violationStatus.value) {
      params.status = violationStatus.value
    }
    if (violationType.value) {
      params.violation_type = violationType.value
    }

    const blob = await exportApi.exportViolations(params)
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
    downloadBlob(blob, `violations_${timestamp}.csv`)
    message.success('导出成功')
  } catch (error: any) {
    console.error('导出失败:', error)
    message.error('导出失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    exportingViolations.value = false
  }
}

onMounted(() => {
  loadRecords()
  loadViolations()
})
</script>


<style scoped>
.detection-records-container {
  padding: 16px;
}
</style>

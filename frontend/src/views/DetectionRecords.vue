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
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import {
  Search,
  Refresh,
  FilmOutline,
  PeopleCircleOutline,
  AlertCircleOutline,
  TimerOutline,
} from '@vicons/ionicons5'
import { http } from '@/lib/http'

const message = useMessage()

// 摄像头选项
const cameraOptions = ref([
  { label: '全部摄像头', value: 'all' },
  { label: 'USB0', value: 'cam0' },
  { label: '测试视频', value: 'vid1' },
])

// 筛选条件
const selectedCamera = ref('cam0')
const dateRange = ref<[number, number] | null>(null)

// 违规筛选
const violationStatus = ref<string | null>(null)
const violationType = ref<string | null>(null)

const statusOptions = [
  { label: '全部状态', value: null },
  { label: '待处理', value: 'pending' },
  { label: '已确认', value: 'confirmed' },
  { label: '误报', value: 'false_positive' },
  { label: '已解决', value: 'resolved' },
]

const typeOptions = [
  { label: '全部类型', value: null },
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
]

// 分页配置
const pagination = computed(() => ({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    // 处理翻页
  },
  onUpdatePageSize: (pageSize: number) => {
    // 处理页大小变更
  },
}))

const violationPagination = computed(() => ({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
}))

// 加载检测记录
async function loadRecords() {
  if (selectedCamera.value === 'all') {
    message.warning('暂不支持查询所有摄像头，请选择具体摄像头')
    return
  }

  loading.value = true
  try {
    // 1. 加载检测记录
    const recordsRes = await http.get(`/records/detection-records/${selectedCamera.value}`, {
      params: {
        limit: 100,
        offset: 0,
      },
    })
    records.value = recordsRes.data.records || []

    // 2. 加载统计数据
    const statsRes = await http.get(`/records/statistics/${selectedCamera.value}`, {
      params: {
        period: '7d',
      },
    })
    statistics.value = statsRes.data.statistics || {}

    message.success(`加载成功：${records.value.length} 条记录`)
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
      limit: 100,
      offset: 0,
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
    
    message.success(`查询到 ${violations.value.length} 条违规记录`)
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
  violationStatus.value = null
  violationType.value = null
  loadRecords()
  loadViolations()
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


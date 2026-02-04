<template>
  <div class="professional-records">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">检测记录</h1>
        <p class="page-subtitle">历史检测记录查询与违规事件管理</p>
      </div>
      <div class="header-actions">
        <n-button type="primary" @click="handleExport">
          <template #icon><n-icon><DownloadOutline /></n-icon></template>
          导出记录
        </n-button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-card">
      <div class="filter-row">
        <div class="filter-item">
          <label class="filter-label">时间范围</label>
          <n-date-picker
            v-model:value="dateRange"
            type="datetimerange"
            clearable
            style="width: 360px"
          />
        </div>
        <div class="filter-item">
          <label class="filter-label">摄像头</label>
          <n-select
            v-model:value="filterCamera"
            :options="cameraOptions"
            placeholder="全部摄像头"
            clearable
            style="width: 200px"
          />
        </div>
        <div class="filter-item">
          <label class="filter-label">违规类型</label>
          <n-select
            v-model:value="filterType"
            :options="typeOptions"
            placeholder="全部类型"
            clearable
            style="width: 200px"
          />
        </div>
        <div class="filter-item">
          <label class="filter-label">处理状态</label>
          <n-select
            v-model:value="filterStatus"
            :options="statusOptions"
            placeholder="全部状态"
            clearable
            style="width: 160px"
          />
        </div>
        <div class="filter-actions">
          <n-button type="primary" @click="handleSearch">
            <template #icon><n-icon><SearchOutline /></n-icon></template>
            查询
          </n-button>
          <n-button @click="handleReset">
            <template #icon><n-icon><RefreshOutline /></n-icon></template>
            重置
          </n-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon stat-icon-total">
          <n-icon size="24"><DocumentTextOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ totalRecords }}</div>
          <div class="stat-label">总记录数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-violation">
          <n-icon size="24"><WarningOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ violationRecords }}</div>
          <div class="stat-label">违规记录</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-pending">
          <n-icon size="24"><TimeOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ pendingRecords }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-resolved">
          <n-icon size="24"><CheckmarkCircleOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ resolvedRecords }}</div>
          <div class="stat-label">已处理</div>
        </div>
      </div>
    </div>

    <!-- 记录列表 -->
    <div class="records-card">
      <n-data-table
        :columns="columns"
        :data="records"
        :loading="loading"
        :pagination="pagination"
        :bordered="false"
        :single-line="false"
        striped
      />
    </div>

    <!-- 详情抽屉 -->
    <n-drawer v-model:show="showDetail" :width="600" placement="right">
      <n-drawer-content title="记录详情" closable>
        <div class="detail-content" v-if="selectedRecord">
          <div class="detail-section">
            <h4 class="section-title">基本信息</h4>
            <n-descriptions :column="1" label-placement="left" bordered>
              <n-descriptions-item label="记录ID">{{ selectedRecord.id }}</n-descriptions-item>
              <n-descriptions-item label="摄像头">{{ selectedRecord.camera }}</n-descriptions-item>
              <n-descriptions-item label="检测时间">{{ formatDateTime(selectedRecord.timestamp) }}</n-descriptions-item>
              <n-descriptions-item label="违规类型">
                <n-tag :type="getViolationTypeColor(selectedRecord.type)" size="small">
                  {{ selectedRecord.type }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="处理状态">
                <n-tag :type="getStatusTypeColor(selectedRecord.status)" size="small">
                  {{ getStatusText(selectedRecord.status) }}
                </n-tag>
              </n-descriptions-item>
            </n-descriptions>
          </div>

          <div class="detail-section" v-if="selectedRecord.image">
            <h4 class="section-title">检测图像</h4>
            <div class="detection-image">
              <img :src="selectedRecord.image" alt="检测图像" />
            </div>
          </div>

          <div class="detail-section" v-if="selectedRecord.description">
            <h4 class="section-title">详细描述</h4>
            <p class="description-text">{{ selectedRecord.description }}</p>
          </div>

          <div class="detail-actions">
            <n-button type="primary" @click="handleProcess" v-if="selectedRecord.status === 'pending'">
              标记为处理中
            </n-button>
            <n-button type="success" @click="handleResolve" v-if="selectedRecord.status === 'processing'">
              标记为已处理
            </n-button>
            <n-button @click="showDetail = false">关闭</n-button>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NIcon, NSelect, NDatePicker, NDataTable, NDrawer, NDrawerContent, NDescriptions, NDescriptionsItem, useMessage, useDialog } from 'naive-ui'
import { getRecords, updateRecordStatus } from '@/api/modules/records'
import { exportViolations } from '@/api/modules/export'
import {
  DownloadOutline,
  SearchOutline,
  RefreshOutline,
  DocumentTextOutline,
  WarningOutline,
  TimeOutline,
  CheckmarkCircleOutline,
  EyeOutline
} from '@vicons/ionicons5'
import type { DataTableColumns } from 'naive-ui'

// 筛选条件
const dateRange = ref<[number, number] | null>(null)
const filterCamera = ref<string | null>(null)
const filterType = ref<string | null>(null)
const filterStatus = ref<string | null>(null)

// 选项
const cameraOptions = [
  { label: '车间A-01', value: 'camera-1' },
  { label: '车间A-02', value: 'camera-2' },
  { label: '车间B-01', value: 'camera-3' },
  { label: '车间B-02', value: 'camera-4' }
]

const typeOptions = [
  { label: '未佩戴口罩', value: 'no-mask' },
  { label: '违规操作', value: 'violation' },
  { label: '区域越界', value: 'trespass' },
  { label: '异常行为', value: 'abnormal' }
]

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已处理', value: 'resolved' }
]

// 统计数据
const totalRecords = ref(0)
const violationRecords = ref(0)
const pendingRecords = ref(0)
const resolvedRecords = ref(0)

// 表格数据
const loading = ref(false)
const records = ref<any[]>([])

const pagination = ref({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    pagination.value.page = page
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.value.pageSize = pageSize
    pagination.value.page = 1
  }
})

// 详情抽屉
const showDetail = ref(false)
const selectedRecord = ref<any>(null)
const showExportDialog = ref(false)

// 表格列定义
const columns: DataTableColumns<any> = [
  {
    title: '记录ID',
    key: 'id',
    width: 140,
    ellipsis: { tooltip: true }
  },
  {
    title: '摄像头',
    key: 'camera',
    width: 120
  },
  {
    title: '检测时间',
    key: 'timestamp',
    width: 180,
    render: (row) => formatDateTime(row.timestamp)
  },
  {
    title: '违规类型',
    key: 'type',
    width: 120,
    render: (row) => h(NTag, { type: getViolationTypeColor(row.type), size: 'small' }, { default: () => row.type })
  },
  {
    title: '置信度',
    key: 'confidence',
    width: 100,
    render: (row) => `${(row.confidence * 100).toFixed(1)}%`
  },
  {
    title: '处理状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { type: getStatusTypeColor(row.status), size: 'small' }, { default: () => getStatusText(row.status) })
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) => h(
      NButton,
      {
        size: 'small',
        onClick: () => handleViewDetail(row)
      },
      { default: () => '查看详情', icon: () => h(NIcon, null, { default: () => h(EyeOutline) }) }
    )
  }
]

const message = useMessage()
const dialog = useDialog()

// 获取记录数据
const fetchRecords = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }

    // 添加筛选条件
    if (filterCamera.value) params.camera_id = filterCamera.value
    if (filterType.value) params.violation_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = new Date(dateRange.value[0]).toISOString()
      params.end_time = new Date(dateRange.value[1]).toISOString()
    }

    const response = await getRecords(params)

    // 防御性检查：确保records是数组
    const recordsArray = Array.isArray(response.records) ? response.records : []

    // 更新数据
    records.value = recordsArray.map(r => ({
      id: r.id,
      camera: r.camera_name || r.camera_id,
      timestamp: new Date(r.timestamp),
      type: (Array.isArray(r.violations) && r.violations[0]?.type) || '未知类型',
      status: r.status,
      confidence: r.confidence
    }))

    // 更新统计
    totalRecords.value = response.total || 0
    violationRecords.value = response.total_violations || 0
    pendingRecords.value = response.pending_count || 0
    resolvedRecords.value = response.resolved_count || 0
    pagination.value.itemCount = response.total || 0

    console.log('检测记录加载成功:', { total: totalRecords.value, records: records.value.length })
  } catch (error: any) {
    console.error('获取检测记录失败:', error)
    message.error(error.message || '获取检测记录失败')
    records.value = []
  } finally {
    loading.value = false
  }
}

// 方法
const handleSearch = () => {
  pagination.value.page = 1
  fetchRecords()
}

const handleReset = () => {
  dateRange.value = null
  filterCamera.value = null
  filterType.value = null
  filterStatus.value = null
  pagination.value.page = 1
  fetchRecords()
}

// 导出记录
const handleExport = async () => {
  try {
    message.loading('正在导出...')

    const params: any = {}
    if (filterCamera.value) params.camera_id = filterCamera.value
    if (filterType.value) params.violation_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = new Date(dateRange.value[0]).toISOString().split('T')[0]
      params.end_date = new Date(dateRange.value[1]).toISOString().split('T')[0]
    }
    params.format = 'xlsx'

    await exportViolations(params)
    message.success('导出成功')
  } catch (error: any) {
    console.error('导出失败:', error)
    message.error(error.message || '导出失败')
  }
}

// 初始化
onMounted(() => {
  fetchRecords()
})

const handleViewDetail = (record: any) => {
  selectedRecord.value = record
  showDetail.value = true
}

// 更新记录状态
const handleUpdateStatus = async (status: 'resolved' | 'processing' | 'pending') => {
  if (!selectedRecord.value) return

  try {
    message.loading('正在更新状态...')
    await updateRecordStatus(selectedRecord.value.id, { status })
    message.success('状态更新成功')

    // 更新本地数据
    selectedRecord.value.status = status
    const record = records.value.find(r => r.id === selectedRecord.value.id)
    if (record) {
      record.status = status
    }

    // 刷新列表
    await fetchRecords()
    showDetail.value = false
  } catch (error: any) {
    console.error('更新状态失败:', error)
    message.error(error.message || '更新状态失败')
  }
}

const handleProcess = () => {
  handleUpdateStatus('processing')
}

const handleResolve = () => {
  handleUpdateStatus('resolved')
}

const handleIgnore = () => {
  dialog.warning({
    title: '忽略记录',
    content: '确定要忽略这条记录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: () => {
      handleUpdateStatus('pending')
    }
  })
}

const formatDateTime = (date: Date) => {
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getViolationTypeColor = (type: string) => {
  const colors: Record<string, any> = {
    '未佩戴口罩': 'error',
    '违规操作': 'warning',
    '区域越界': 'info',
    '异常行为': 'default'
  }
  return colors[type] || 'default'
}

const getStatusTypeColor = (status: string) => {
  const colors: Record<string, any> = {
    'pending': 'error',
    'processing': 'warning',
    'resolved': 'success'
  }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'pending': '待处理',
    'processing': '处理中',
    'resolved': '已处理'
  }
  return texts[status] || status
}
</script>

<style scoped lang="scss">
/**
 * 检测记录页面 - 专业版
 */

// 颜色变量
$color-bg: #F7FAFC;
$color-white: #FFFFFF;
$color-border: #E6EDF5;
$color-text-primary: #1F2D3D;
$color-text-secondary: #6B778C;
$color-text-tertiary: #8C9BAB;

.professional-records {
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
  gap: 12px;
}

// ===== 筛选区域 =====
.filter-card {
  margin-bottom: 24px;
  padding: 20px 24px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: $color-text-secondary;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

// ===== 统计卡片 =====
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;

  &.stat-icon-total {
    background: rgba(30, 159, 255, 0.1);
    color: #1E9FFF;
  }

  &.stat-icon-violation {
    background: rgba(255, 107, 107, 0.1);
    color: #FF6B6B;
  }

  &.stat-icon-pending {
    background: rgba(250, 173, 20, 0.1);
    color: #FAAD14;
  }

  &.stat-icon-resolved {
    background: rgba(82, 196, 26, 0.1);
    color: #52C41A;
  }
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 13px;
  color: $color-text-secondary;
}

// ===== 记录列表 =====
.records-card {
  background: $color-white;
  border-radius: 12px;
  border: 1px solid $color-border;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

// ===== 详情抽屉 =====
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section {
  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: $color-text-primary;
    margin: 0 0 12px 0;
  }
}

.detection-image {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid $color-border;

  img {
    width: 100%;
    height: auto;
    display: block;
  }
}

.description-text {
  font-size: 14px;
  color: $color-text-secondary;
  line-height: 1.6;
  margin: 0;
}

.detail-actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid $color-border;
}

// ===== 响应式 =====
@media (max-width: 1200px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .professional-records {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .filter-row {
    flex-direction: column;
    align-items: stretch;

    .filter-item {
      width: 100%;

      :deep(.n-select),
      :deep(.n-date-picker) {
        width: 100% !important;
      }
    }

    .filter-actions {
      margin-left: 0;
      width: 100%;

      button {
        flex: 1;
      }
    }
  }

  .stats-cards {
    grid-template-columns: 1fr;
  }
}
</style>

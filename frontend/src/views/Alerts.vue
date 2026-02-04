<template>
  <div>
    <n-page-header title="告警中心" subtitle="历史告警与规则管理" />
    <n-space vertical size="large">
      <n-card title="历史告警" size="small">
        <n-space align="center" wrap>
          <n-input v-model:value="filters.cameraId" placeholder="摄像头ID(可选)" style="width: 200px" @keyup.enter="fetchHistory" />
          <n-input v-model:value="filters.alertType" placeholder="告警类型(可选)" style="width: 200px" @keyup.enter="fetchHistory" />
          <n-select
            v-model:value="historySort.sortBy"
            :options="[
              { label: '按时间', value: 'timestamp' },
              { label: '按摄像头', value: 'camera_id' },
              { label: '按类型', value: 'alert_type' },
            ]"
            placeholder="排序字段"
            style="width: 120px"
            @update:value="() => handleHistorySort(historySort.sortBy || 'timestamp')"
          />
          <n-button
            :type="historySort.sortOrder === 'desc' ? 'primary' : 'default'"
            @click="handleHistorySort(historySort.sortBy || 'timestamp')"
          >
            {{ historySort.sortOrder === 'desc' ? '↓ 降序' : '↑ 升序' }}
          </n-button>
          <n-button type="primary" :loading="loading.history" @click="fetchHistory">刷新</n-button>
        </n-space>
        <n-data-table
          :columns="historyColumns"
          :data="history.items"
          :loading="loading.history"
          :bordered="false"
          size="small"
          :pagination="historyPaginationConfig"
        />
      </n-card>

      <n-card title="告警规则" size="small">
        <template #header-extra>
          <n-button type="primary" size="small" @click="openCreateRuleDialog">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            创建规则
          </n-button>
        </template>
        <n-space align="center" wrap>
          <n-input v-model:value="ruleFilters.cameraId" placeholder="摄像头ID(可选)" style="width: 200px" />
          <n-switch v-model:value="ruleFilters.enabled" :round="false">
            <template #checked>启用</template>
            <template #unchecked>全部</template>
          </n-switch>
          <n-button :loading="loading.rules" @click="fetchRules">刷新</n-button>
        </n-space>
        <n-data-table
          :columns="rulesColumns"
          :data="rules.items"
          :loading="loading.rules"
          :bordered="false"
          size="small"
          :pagination="rulePaginationConfig"
        />
      </n-card>
    </n-space>

    <!-- 告警详情弹窗 -->
    <n-modal
      v-model:show="showAlertDetail"
      preset="card"
      title="告警详情"
      style="max-width: 700px"
    >
      <n-descriptions :column="2" bordered v-if="selectedAlert">
        <n-descriptions-item label="告警ID">{{ selectedAlert.id }}</n-descriptions-item>
        <n-descriptions-item label="时间">
          {{ new Date(selectedAlert.timestamp).toLocaleString('zh-CN') }}
        </n-descriptions-item>
        <n-descriptions-item label="摄像头ID">{{ selectedAlert.camera_id }}</n-descriptions-item>
        <n-descriptions-item label="告警类型">{{ selectedAlert.alert_type }}</n-descriptions-item>
        <n-descriptions-item label="规则ID" :span="2">
          {{ selectedAlert.rule_id || '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="消息" :span="2">
          {{ selectedAlert.message }}
        </n-descriptions-item>
        <n-descriptions-item label="通知已发送" :span="1">
          <n-tag :type="selectedAlert.notification_sent ? 'success' : 'default'">
            {{ selectedAlert.notification_sent ? '是' : '否' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="通知渠道" :span="1">
          {{ selectedAlert.notification_channels_used?.join(', ') || '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="详细信息" :span="2" v-if="selectedAlert.details">
          <pre style="max-height: 200px; overflow: auto; background: #f5f5f5; padding: 8px; border-radius: 4px;">
            {{ JSON.stringify(selectedAlert.details, null, 2) }}
          </pre>
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>

    <!-- 规则详情弹窗 -->
    <n-modal
      v-model:show="showRuleDetail"
      preset="card"
      title="告警规则详情"
      style="max-width: 700px"
    >
      <n-descriptions :column="2" bordered v-if="selectedRule">
        <n-descriptions-item label="规则ID">{{ selectedRule.id }}</n-descriptions-item>
        <n-descriptions-item label="规则名称">{{ selectedRule.name }}</n-descriptions-item>
        <n-descriptions-item label="摄像头ID">{{ selectedRule.camera_id || '全部' }}</n-descriptions-item>
        <n-descriptions-item label="规则类型">{{ selectedRule.rule_type }}</n-descriptions-item>
        <n-descriptions-item label="启用状态">
          <n-tag :type="selectedRule.enabled ? 'success' : 'default'">
            {{ selectedRule.enabled ? '启用' : '禁用' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="优先级">{{ selectedRule.priority || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间" :span="1">
          {{ selectedRule.created_at ? new Date(selectedRule.created_at).toLocaleString('zh-CN') : '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="更新时间" :span="1">
          {{ selectedRule.updated_at ? new Date(selectedRule.updated_at).toLocaleString('zh-CN') : '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="触发条件" :span="2">
          <pre style="max-height: 200px; overflow: auto; background: #f5f5f5; padding: 8px; border-radius: 4px;">
            {{ JSON.stringify(selectedRule.conditions, null, 2) }}
          </pre>
        </n-descriptions-item>
        <n-descriptions-item label="通知渠道" :span="1">
          {{ selectedRule.notification_channels?.join(', ') || '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="接收人" :span="1">
          {{ selectedRule.recipients?.join(', ') || '-' }}
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>

    <!-- 删除确认弹窗 -->
    <n-modal
      v-model:show="showDeleteConfirm"
      preset="dialog"
      title="确认删除"
      content="确定要删除这条告警规则吗？此操作不可恢复。"
      positive-text="确认删除"
      negative-text="取消"
      type="warning"
      @positive-click="confirmDeleteRule"
    />

    <!-- 创建/编辑规则弹窗 -->
    <n-modal
      v-model:show="showRuleFormDialog"
      preset="card"
      :title="editingRule ? '编辑告警规则' : '创建告警规则'"
      style="max-width: 800px"
      :bordered="false"
    >
      <n-form
        ref="ruleFormRef"
        :model="ruleForm"
        :rules="ruleFormRules"
        label-placement="left"
        label-width="120"
        require-mark-placement="right-hanging"
      >
        <n-form-item label="规则名称" path="name">
          <n-input v-model:value="ruleForm.name" placeholder="请输入规则名称" />
        </n-form-item>
        <n-form-item label="规则类型" path="rule_type">
          <n-select
            v-model:value="ruleForm.rule_type"
            :options="ruleTypeOptions"
            placeholder="请选择规则类型"
          />
        </n-form-item>
        <n-form-item label="摄像头ID" path="camera_id">
          <n-input
            v-model:value="ruleForm.camera_id"
            placeholder="留空表示应用于所有摄像头"
            clearable
          />
        </n-form-item>
        <n-form-item label="优先级" path="priority">
          <n-select
            v-model:value="ruleForm.priority"
            :options="priorityOptions"
            placeholder="请选择优先级"
          />
        </n-form-item>
        <n-form-item label="启用状态" path="enabled">
          <n-switch v-model:value="ruleForm.enabled" />
        </n-form-item>
        <n-form-item label="触发条件" path="conditions">
          <n-input
            v-model:value="ruleFormConditionsText"
            type="textarea"
            :rows="6"
            placeholder='请输入JSON格式的触发条件，例如: {"violation_type": "no_hairnet", "threshold": 1}'
            @update:value="handleConditionsTextChange"
          />
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            提示：条件应为有效的JSON对象
          </n-text>
        </n-form-item>
        <n-form-item label="通知渠道" path="notification_channels">
          <n-select
            v-model:value="ruleForm.notification_channels"
            :options="notificationChannelOptions"
            multiple
            placeholder="请选择通知渠道"
            clearable
          />
        </n-form-item>
        <n-form-item label="接收人" path="recipients">
          <n-input
            v-model:value="ruleFormRecipientsText"
            type="textarea"
            :rows="3"
            placeholder="请输入接收人列表，多个接收人用逗号分隔"
            @update:value="handleRecipientsTextChange"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRuleFormDialog = false">取消</n-button>
          <n-button type="primary" @click="submitRuleForm" :loading="savingRule">
            {{ editingRule ? '更新' : '创建' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref, computed } from 'vue'
import {
  NButton,
  NTag,
  NModal,
  NDescriptions,
  NDescriptionsItem,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
  NText,
  NSpace,
  NIcon,
  useMessage,
  useDialog,
  type DataTableColumns,
  type FormInst,
  type FormRules
} from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import {
  getAlertHistory,
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  updateAlertStatus,
  type AlertHistory,
  type AlertRule
} from '@/api/modules/alerts'
import { useCameraStore } from '@/stores/camera'

const message = useMessage()
const dialog = useDialog()
const cameraStore = useCameraStore()

const loading = reactive({ history: false, rules: false })
const savingRule = ref(false)

// 告警历史筛选和分页
const filters = reactive({ limit: 20, cameraId: '', alertType: '' })
const historyPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})
const historySort = reactive({
  sortBy: 'timestamp' as string | undefined,
  sortOrder: 'desc' as 'asc' | 'desc',
})
const history = reactive<{ items: AlertHistory[] }>({ items: [] })

// 告警规则筛选和分页
const ruleFilters = reactive<{ cameraId: string; enabled: boolean | null }>({ cameraId: '', enabled: null })
const rulePagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})
const rules = reactive<{ items: AlertRule[] }>({ items: [] })

// 弹窗状态
const showAlertDetail = ref(false)
const showRuleDetail = ref(false)
const showDeleteConfirm = ref(false)
const showRuleFormDialog = ref(false)
const selectedAlert = ref<AlertHistory | null>(null)
const selectedRule = ref<AlertRule | null>(null)
const ruleToDelete = ref<number | null>(null)
const editingRule = ref<AlertRuleItem | null>(null)
const ruleFormRef = ref<FormInst | null>(null)

// 规则表单数据
const ruleForm = reactive({
  name: '',
  rule_type: '',
  camera_id: '',
  priority: 'medium',
  enabled: true,
  conditions: {} as any,
  notification_channels: [] as string[],
  recipients: [] as string[],
})

// 规则表单文本字段（用于JSON编辑）
const ruleFormConditionsText = ref('{}')
const ruleFormRecipientsText = ref('')

// 规则类型选项
const ruleTypeOptions = [
  { label: '违规检测', value: 'violation' },
  { label: '性能告警', value: 'performance' },
  { label: '系统告警', value: 'system' },
  { label: '自定义', value: 'custom' },
]

// 优先级选项
const priorityOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'critical' },
]

// 通知渠道选项
const notificationChannelOptions = [
  { label: '邮件', value: 'email' },
  { label: '短信', value: 'sms' },
  { label: 'Webhook', value: 'webhook' },
  { label: '系统通知', value: 'system' },
]

// 表单验证规则
const ruleFormRules: FormRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' }
  ],
  rule_type: [
    { required: true, message: '请选择规则类型', trigger: 'change' }
  ],
  conditions: [
    { required: true, message: '请输入触发条件', trigger: 'blur' },
    {
      validator: () => {
        try {
          JSON.parse(ruleFormConditionsText.value)
          return true
        } catch {
          return false
        }
      },
      message: '触发条件必须是有效的JSON格式',
      trigger: 'blur'
    }
  ],
}

const historyColumns: DataTableColumns<AlertHistoryItem> = [
  {
    title: '时间',
    key: 'timestamp',
    width: 180,
    render: (row) => new Date(row.timestamp).toLocaleString('zh-CN')
  },
  { title: '摄像头', key: 'camera_id', width: 120 },
  {
    title: '类型',
    key: 'alert_type',
    width: 160,
    render: (row) => {
      const typeMap: Record<string, { label: string; type: any }> = {
        violation: { label: '违规', type: 'error' },
        warning: { label: '警告', type: 'warning' },
        info: { label: '信息', type: 'info' },
      }
      const info = typeMap[row.alert_type] || { label: row.alert_type, type: 'default' }
      return h(NTag, { type: info.type, size: 'small' }, { default: () => info.label })
    }
  },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const status = (row as any).status || 'pending'
      const statusMap: Record<string, { label: string; type: any }> = {
        pending: { label: '待处理', type: 'warning' },
        confirmed: { label: '已确认', type: 'error' },
        false_positive: { label: '误报', type: 'default' },
        resolved: { label: '已解决', type: 'success' },
      }
      const info = statusMap[status] || { label: status, type: 'default' }
      return h(NTag, { type: info.type, size: 'small' }, { default: () => info.label })
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row) => {
      return h('div', { style: 'display: flex; gap: 8px;' }, [
        h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => viewAlertDetail(row),
        },
        { default: () => '详情' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'info',
            onClick: () => handleAlert(row, 'confirmed'),
            disabled: (row as any).status === 'confirmed',
          },
          { default: () => '确认' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'default',
            onClick: () => handleAlert(row, 'false_positive'),
            disabled: (row as any).status === 'false_positive',
          },
          { default: () => '误报' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'success',
            onClick: () => handleAlert(row, 'resolved'),
            disabled: (row as any).status === 'resolved',
          },
          { default: () => '解决' }
        ),
      ])
    },
  },
]

const rulesColumns: DataTableColumns<AlertRuleItem> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name', width: 180 },
  { title: '摄像头', key: 'camera_id', width: 120, render: (row) => row.camera_id || '全部' },
  { title: '类型', key: 'rule_type', width: 160 },
  {
    title: '启用',
    key: 'enabled',
    width: 80,
    render: (row) => {
      return h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, {
        default: () => row.enabled ? '启用' : '禁用'
      })
    }
  },
  { title: '优先级', key: 'priority', width: 100 },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row) => {
      return h('div', { style: 'display: flex; gap: 8px;' }, [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            onClick: () => viewRuleDetail(row),
          },
          { default: () => '详情' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'info',
            onClick: () => openEditRuleDialog(row),
          },
          { default: () => '编辑' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            onClick: () => deleteRule(row.id),
          },
          { default: () => '删除' }
        ),
      ])
    },
  },
]

// 告警历史分页配置
const historyPaginationConfig = computed(() => ({
  page: historyPagination.page,
  pageSize: historyPagination.pageSize,
  itemCount: historyPagination.total,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    historyPagination.page = page
    fetchHistory()
  },
  onUpdatePageSize: (pageSize: number) => {
    historyPagination.pageSize = pageSize
    historyPagination.page = 1
    fetchHistory()
  },
}))

// 告警规则分页配置
const rulePaginationConfig = computed(() => ({
  page: rulePagination.page,
  pageSize: rulePagination.pageSize,
  itemCount: rulePagination.total,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    rulePagination.page = page
    fetchRules()
  },
  onUpdatePageSize: (pageSize: number) => {
    rulePagination.pageSize = pageSize
    rulePagination.page = 1
    fetchRules()
  },
}))

async function fetchHistory() {
  loading.history = true
  try {
    const res = await getAlertHistory({
      limit: historyPagination.pageSize,
      page: historyPagination.page,
      sort_by: historySort.sortBy,
      sort_order: historySort.sortOrder,
    })
    history.items = res.items
    historyPagination.total = res.total
  } catch (e: any) {
    message.error(e?.message || '获取历史告警失败')
  } finally {
    loading.history = false
  }
}

async function fetchRules() {
  loading.rules = true
  try {
    const res = await getAlertRules({
      limit: rulePagination.pageSize,
      page: rulePagination.page,
    })
    rules.items = res.items
    rulePagination.total = res.total
  } catch (e: any) {
    message.error(e?.message || '获取规则失败')
  } finally {
    loading.rules = false
  }
}

// 查看告警详情
function viewAlertDetail(alert: AlertHistory) {
  selectedAlert.value = alert
  showAlertDetail.value = true
}

// 处理告警（确认、误报、解决）
async function handleAlert(alert: AlertHistory, action: 'resolved' | 'ignored') {
  try {
    await updateAlertStatus(alert.id, action)
    const actionText = action === 'resolved' ? '已解决' : '已忽略'
    message.success(`告警${actionText}`)
    await fetchHistory()
  } catch (e: any) {
    const errorMsg = e?.message || '处理告警失败'
    message.error(errorMsg)
    console.error('处理告警失败:', e)
  }
}

// 查看规则详情
async function viewRuleDetail(rule: AlertRule) {
  // 直接使用列表中的规则数据
  selectedRule.value = rule
  showRuleDetail.value = true
}

// 删除规则
function deleteRule(ruleId: number) {
  ruleToDelete.value = ruleId
  showDeleteConfirm.value = true
}

// 确认删除规则
async function confirmDeleteRule() {
  if (!ruleToDelete.value) return

  try {
    await deleteAlertRule(ruleToDelete.value)
    message.success('规则删除成功')
    showDeleteConfirm.value = false
    ruleToDelete.value = null
    await fetchRules()
  } catch (e: any) {
    message.error(e?.message || '删除规则失败')
    console.error('删除规则失败:', e)
  }
}

// 处理历史记录排序（通过修改排序参数并重新获取数据）
function handleHistorySort(sortBy: string) {
  if (historySort.sortBy === sortBy) {
    // 切换排序方向
    historySort.sortOrder = historySort.sortOrder === 'desc' ? 'asc' : 'desc'
  } else {
    // 设置新的排序字段
    historySort.sortBy = sortBy
    historySort.sortOrder = 'desc'
  }
  historyPagination.page = 1 // 重置到第一页
  fetchHistory()
}

// 获取告警状态文本
function getAlertStatusText(status: string) {
  const statusMap: Record<string, string> = {
    pending: '待处理',
    confirmed: '已确认',
    false_positive: '误报',
    resolved: '已解决',
  }
  return statusMap[status] || status
}

// 获取告警状态类型
function getAlertStatusType(status: string) {
  const typeMap: Record<string, any> = {
    pending: 'warning',
    confirmed: 'error',
    false_positive: 'default',
    resolved: 'success',
  }
  return typeMap[status] || 'default'
}

// 打开创建规则对话框
function openCreateRuleDialog() {
  editingRule.value = null
  resetRuleForm()
  showRuleFormDialog.value = true
}

// 打开编辑规则对话框
function openEditRuleDialog(rule: AlertRuleItem) {
  editingRule.value = rule
  ruleForm.name = rule.name
  ruleForm.rule_type = rule.rule_type
  ruleForm.camera_id = rule.camera_id || ''
  ruleForm.priority = rule.priority || 'medium'
  ruleForm.enabled = rule.enabled
  ruleForm.conditions = rule.conditions || {}
  ruleForm.notification_channels = rule.notification_channels || []
  ruleForm.recipients = rule.recipients || []

  // 更新文本字段
  ruleFormConditionsText.value = JSON.stringify(rule.conditions || {}, null, 2)
  ruleFormRecipientsText.value = (rule.recipients || []).join(', ')

  showRuleFormDialog.value = true
}

// 重置规则表单
function resetRuleForm() {
  ruleForm.name = ''
  ruleForm.rule_type = ''
  ruleForm.camera_id = ''
  ruleForm.priority = 'medium'
  ruleForm.enabled = true
  ruleForm.conditions = {}
  ruleForm.notification_channels = []
  ruleForm.recipients = []
  ruleFormConditionsText.value = '{}'
  ruleFormRecipientsText.value = ''
  ruleFormRef.value?.restoreValidation()
}

// 处理条件文本变化
function handleConditionsTextChange(value: string) {
  ruleFormConditionsText.value = value
  try {
    ruleForm.conditions = JSON.parse(value)
  } catch {
    // 无效JSON，保持原值
  }
}

// 处理接收人文本变化
function handleRecipientsTextChange(value: string) {
  ruleFormRecipientsText.value = value
  ruleForm.recipients = value
    .split(',')
    .map(r => r.trim())
    .filter(r => r.length > 0)
}

// 提交规则表单
async function submitRuleForm() {
  if (!ruleFormRef.value) return

  try {
    await ruleFormRef.value.validate()

    // 验证条件JSON
    try {
      ruleForm.conditions = JSON.parse(ruleFormConditionsText.value)
    } catch (e) {
      message.error('触发条件必须是有效的JSON格式')
      return
    }

    savingRule.value = true

    const ruleData = {
      name: ruleForm.name,
      description: ruleForm.rule_type, // 使用rule_type作为description
      severity: (ruleForm.priority as 'low' | 'medium' | 'high' | 'critical') || 'medium',
      enabled: ruleForm.enabled,
      conditions: ruleForm.conditions,
      action: {
        type: 'notification',
        channels: ruleForm.notification_channels || [],
        recipients: ruleForm.recipients || []
      }
    }

    if (editingRule.value) {
      // 更新规则
      await updateAlertRule(editingRule.value.id, ruleData)
      message.success('规则更新成功')
    } else {
      // 创建规则
      await createAlertRule(ruleData)
      message.success('规则创建成功')
    }

    showRuleFormDialog.value = false
    resetRuleForm()
    await fetchRules()
  } catch (e: any) {
    if (e.errors) {
      // 表单验证错误
      return
    }
    message.error(e?.message || '保存规则失败')
    console.error('保存规则失败:', e)
  } finally {
    savingRule.value = false
  }
}

onMounted(() => {
  fetchHistory()
  fetchRules()
  // 加载摄像头列表（用于表单中的摄像头选择）
  cameraStore.fetchCameras().catch(() => {
    // 忽略错误，摄像头列表是可选的
  })
})
</script>

<style scoped>
</style>

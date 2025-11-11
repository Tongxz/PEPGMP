<template>
  <div>
    <n-page-header title="告警中心" subtitle="历史告警与规则管理" />
    <n-space vertical size="large">
      <n-card title="历史告警" size="small">
        <n-space align="center" wrap>
          <n-input v-model:value="filters.cameraId" placeholder="摄像头ID(可选)" style="width: 200px" />
          <n-input v-model:value="filters.alertType" placeholder="告警类型(可选)" style="width: 200px" />
          <n-input-number v-model:value="filters.limit" :min="1" :max="500" placeholder="数量" />
          <n-button type="primary" :loading="loading.history" @click="fetchHistory">刷新</n-button>
        </n-space>
        <n-data-table
          :columns="historyColumns"
          :data="history.items"
          :loading="loading.history"
          :bordered="false"
          size="small"
          @update:sorter="handleHistorySorter"
        />
      </n-card>

      <n-card title="告警规则" size="small">
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
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NTag, NModal, NDescriptions, NDescriptionsItem, useMessage, useDialog, type DataTableColumns } from 'naive-ui'
import { alertsApi, type AlertHistoryItem, type AlertRuleItem } from '@/api/alerts'

const message = useMessage()
const dialog = useDialog()

const loading = reactive({ history: false, rules: false })

const filters = reactive({ limit: 100, cameraId: '', alertType: '' })
const history = reactive<{ items: AlertHistoryItem[] }>({ items: [] })

const ruleFilters = reactive<{ cameraId: string; enabled: boolean | null }>({ cameraId: '', enabled: null })
const rules = reactive<{ items: AlertRuleItem[] }>({ items: [] })

// 弹窗状态
const showAlertDetail = ref(false)
const showRuleDetail = ref(false)
const showDeleteConfirm = ref(false)
const selectedAlert = ref<AlertHistoryItem | null>(null)
const selectedRule = ref<AlertRuleItem | null>(null)
const ruleToDelete = ref<number | null>(null)

const historyColumns: DataTableColumns<AlertHistoryItem> = [
  {
    title: '时间',
    key: 'timestamp',
    width: 180,
    sorter: (row1, row2) => new Date(row1.timestamp).getTime() - new Date(row2.timestamp).getTime(),
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
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) => {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => viewAlertDetail(row),
        },
        { default: () => '详情' }
      )
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
            type: 'error',
            onClick: () => deleteRule(row.id),
          },
          { default: () => '删除' }
        ),
      ])
    },
  },
]

async function fetchHistory() {
  loading.history = true
  try {
    const res = await alertsApi.getHistory({
      limit: filters.limit,
      camera_id: filters.cameraId || undefined,
      alert_type: filters.alertType || undefined,
    })
    history.items = res.items
  } catch (e: any) {
    message.error(e?.message || '获取历史告警失败')
  } finally {
    loading.history = false
  }
}

async function fetchRules() {
  loading.rules = true
  try {
    const res = await alertsApi.listRules({
      camera_id: ruleFilters.cameraId || undefined,
      enabled: ruleFilters.enabled === null ? undefined : ruleFilters.enabled,
    })
    rules.items = res.items
  } catch (e: any) {
    message.error(e?.message || '获取规则失败')
  } finally {
    loading.rules = false
  }
}

// 查看告警详情
function viewAlertDetail(alert: AlertHistoryItem) {
  selectedAlert.value = alert
  showAlertDetail.value = true
}

// 查看规则详情
async function viewRuleDetail(rule: AlertRuleItem) {
  try {
    // 尝试获取完整规则详情
    const detail = await alertsApi.getRuleDetail(rule.id)
    selectedRule.value = detail
  } catch (e: any) {
    // 如果获取详情失败，使用列表中的规则数据
    selectedRule.value = rule
  }
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
    await alertsApi.deleteRule(ruleToDelete.value)
    message.success('规则删除成功')
    showDeleteConfirm.value = false
    ruleToDelete.value = null
    await fetchRules()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e?.message || '删除规则失败')
    console.error('删除规则失败:', e)
  }
}

// 处理历史记录排序
function handleHistorySorter(sorter: any) {
  console.log('排序:', sorter)
  // 可以在这里实现排序逻辑
}

onMounted(() => {
  fetchHistory()
  fetchRules()
})
</script>

<style scoped>
</style>

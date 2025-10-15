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
        <n-data-table :columns="historyColumns" :data="history.items" :loading="loading.history" :bordered="false" size="small" />
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
        <n-data-table :columns="rulesColumns" :data="rules.items" :loading="loading.rules" :bordered="false" size="small" />
      </n-card>
    </n-space>
  </div>

</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import { alertsApi, type AlertHistoryItem, type AlertRuleItem } from '@/api/alerts'

const message = useMessage()

const loading = reactive({ history: false, rules: false })

const filters = reactive({ limit: 100, cameraId: '', alertType: '' })
const history = reactive<{ items: AlertHistoryItem[] }>({ items: [] })

const ruleFilters = reactive<{ cameraId: string; enabled: boolean | null }>({ cameraId: '', enabled: null })
const rules = reactive<{ items: AlertRuleItem[] }>({ items: [] })

const historyColumns = [
  { title: '时间', key: 'timestamp', width: 180 },
  { title: '摄像头', key: 'camera_id', width: 120 },
  { title: '类型', key: 'alert_type', width: 160 },
  { title: '消息', key: 'message' },
]

const rulesColumns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name', width: 180 },
  { title: '摄像头', key: 'camera_id', width: 120 },
  { title: '类型', key: 'rule_type', width: 160 },
  { title: '启用', key: 'enabled', width: 80 },
  { title: '优先级', key: 'priority', width: 100 },
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

onMounted(() => {
  fetchHistory()
  fetchRules()
})
</script>

<style scoped>
</style>

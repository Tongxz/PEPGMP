<template>
  <n-card
    title="模型注册中心"
    :segmented="{ content: true, footer: 'soft' }"
    size="small"
  >
    <template #header-extra>
      <n-space wrap>
        <n-select
          v-model:value="filters.modelType"
          :options="modelTypeOptions"
          placeholder="全部类型"
          size="small"
          style="width: 140px"
          clearable
          @update:value="handleFilterChange"
        />
        <n-select
          v-model:value="filters.status"
          :options="statusOptions"
          placeholder="全部状态"
          size="small"
          style="width: 140px"
          clearable
          @update:value="handleFilterChange"
        />
        <n-button size="small" @click="refreshModels" :loading="loading">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
          刷新
        </n-button>
      </n-space>
    </template>

    <n-spin :show="loading">
      <n-empty v-if="models.length === 0" description="暂无模型记录">
        <template #extra>
          <n-button size="small" @click="refreshModels">刷新</n-button>
        </template>
      </n-empty>

      <div v-else>
        <n-list>
          <n-list-item v-for="model in models" :key="model.id">
            <n-card size="small" hoverable>
              <template #header>
                <n-space justify="space-between" align="center">
                  <div class="model-header">
                    <span class="model-name">{{ model.name }}</span>
                    <n-tag size="small" type="info">v{{ model.version }}</n-tag>
                    <n-tag size="small" :type="getStatusTagType(model.status)">
                      {{ getStatusLabel(model.status) }}
                    </n-tag>
                  </div>
                  <n-space>
                    <n-tooltip placement="top">
                      <template #trigger>
                        <n-button size="tiny" @click="openDetail(model)">详情</n-button>
                      </template>
                      查看训练指标、数据集和工件信息
                    </n-tooltip>
                    <n-popselect
                      :options="statusOptions"
                      trigger="click"
                      @update:value="value => handleStatusUpdate(model, value)"
                    >
                      <n-button size="tiny" secondary>
                        更新状态
                      </n-button>
                    </n-popselect>
                    <n-button size="tiny" type="error" @click="confirmDelete(model)">
                      删除
                    </n-button>
                  </n-space>
                </n-space>
              </template>

              <div class="model-body">
                <n-descriptions :column="2" size="small">
                  <n-descriptions-item label="模型类型">
                    {{ formatModelType(model.model_type) }}
                  </n-descriptions-item>
                  <n-descriptions-item label="数据集">
                    <span v-if="model.dataset_id">
                      {{ model.dataset_id }}
                    </span>
                    <span v-else>—</span>
                  </n-descriptions-item>
                  <n-descriptions-item label="创建时间">
                    {{ formatTime(model.created_at) }}
                  </n-descriptions-item>
                  <n-descriptions-item label="更新时间">
                    {{ formatTime(model.updated_at) }}
                  </n-descriptions-item>
                </n-descriptions>

                <n-divider dashed />

                <div class="metrics-overview" v-if="model.metrics && hasMetrics(model.metrics)">
                  <n-text depth="3" style="font-size: 12px;">核心指标</n-text>
                  <n-grid :cols="3" :x-gap="12" :y-gap="8" style="margin-top: 8px;">
                    <n-gi v-for="metric in primaryMetrics(model.metrics || {})" :key="metric.key">
                      <n-statistic :label="metric.label" :value="metric.value" />
                    </n-gi>
                  </n-grid>
                </div>

                <div v-else class="metrics-placeholder">
                  <n-text depth="3" style="font-size: 12px;">暂未提供指标信息</n-text>
                </div>
              </div>
            </n-card>
          </n-list-item>
        </n-list>
      </div>
    </n-spin>

    <template #footer>
      <n-text depth="3" style="font-size: 12px;">
        训练完成后模型会自动注册。可在详情中查看训练报告与工件路径。
      </n-text>
    </template>

    <n-modal
      v-model:show="detailVisible"
      preset="dialog"
      title="模型详情"
      style="width: 820px;"
      :show-icon="false"
    >
      <div v-if="detailModel" class="model-detail-content">
        <n-card title="基本信息" size="small" style="margin-bottom: 16px;">
          <n-descriptions :column="2" size="small">
            <n-descriptions-item label="模型名称">
              {{ detailModel.name }}
            </n-descriptions-item>
            <n-descriptions-item label="模型类型">
              {{ formatModelType(detailModel.model_type) }}
            </n-descriptions-item>
            <n-descriptions-item label="版本">
              v{{ detailModel.version }}
            </n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-select
                v-model:value="detailStatus"
                :options="statusOptions"
                size="small"
                style="width: 140px;"
              />
            </n-descriptions-item>
            <n-descriptions-item label="数据集ID">
              {{ detailModel.dataset_id || '—' }}
            </n-descriptions-item>
            <n-descriptions-item label="样本来源">
              {{ detailModel.dataset_path || '—' }}
            </n-descriptions-item>
            <n-descriptions-item label="创建时间">
              {{ formatTime(detailModel.created_at) }}
            </n-descriptions-item>
            <n-descriptions-item label="更新时间">
              {{ formatTime(detailModel.updated_at) }}
            </n-descriptions-item>
          </n-descriptions>
          <n-divider />
          <div class="path-row">
            <n-text depth="3" style="font-size: 12px;">模型文件</n-text>
            <n-input
              :value="detailModel.model_path"
              size="small"
              readonly
              class="path-input"
            />
            <n-button size="tiny" @click="copyPath(detailModel.model_path)">复制</n-button>
          </div>
          <div class="path-row" v-if="detailModel.report_path">
            <n-text depth="3" style="font-size: 12px;">训练报告</n-text>
            <n-input
              :value="detailModel.report_path"
              size="small"
              readonly
              class="path-input"
            />
            <n-button
              size="tiny"
              @click="detailModel.report_path && copyPath(detailModel.report_path)"
            >
              复制
            </n-button>
          </div>
          <n-divider v-if="detailModel.description" />
          <n-text v-if="detailModel.description" depth="3" style="font-size: 12px;">
            描述
          </n-text>
          <n-p v-if="detailModel.description" style="margin-top: 8px;">
            {{ detailModel.description }}
          </n-p>
        </n-card>

        <n-card v-if="detailMetrics.length > 0" title="训练指标" size="small" style="margin-bottom: 16px;">
          <n-grid :cols="3" :x-gap="16" :y-gap="16">
            <n-gi v-for="item in detailMetrics" :key="item.key">
              <n-statistic :label="item.label" :value="item.value" />
            </n-gi>
          </n-grid>
        </n-card>

        <n-card v-if="detailArtifacts.length > 0" title="工件信息" size="small" style="margin-bottom: 16px;">
          <n-descriptions :column="1" size="small">
            <n-descriptions-item v-for="artifact in detailArtifacts" :key="artifact.key" :label="artifact.label">
              <n-space>
                <n-text>{{ artifact.value }}</n-text>
                <n-button size="tiny" tertiary @click="copyPath(String(artifact.value))">复制</n-button>
              </n-space>
            </n-descriptions-item>
          </n-descriptions>
        </n-card>

        <n-card v-if="detailModel.training_params" title="训练参数" size="small">
          <n-code :code="JSON.stringify(detailModel.training_params, null, 2)" language="json" />
        </n-card>
      </div>
      <template #action>
        <n-space justify="end">
          <n-button @click="detailVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingStatus" @click="persistDetailStatus">
            保存
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NCard,
  NCode,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NEmpty,
  NGi,
  NGrid,
  NIcon,
  NInput,
  NList,
  NListItem,
  NModal,
  NP,
  NPopselect,
  NSelect,
  NSpace,
  NSpin,
  NStatistic,
  NTag,
  NText,
  NTooltip,
  useDialog,
  useMessage,
} from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import type { ModelInfo } from '@/api/mlops'
import { deleteModel, listModels, updateModelStatus } from '@/api/mlops'

const loading = ref(false)
const savingStatus = ref(false)
const models = ref<ModelInfo[]>([])

const filters = reactive({
  modelType: null as string | null,
  status: null as string | null,
})

const detailVisible = ref(false)
const detailModel = ref<ModelInfo | null>(null)
const detailStatus = ref<string | null>(null)

const message = useMessage()
const dialog = useDialog()

const statusOptions = [
  { label: '可用', value: 'active' },
  { label: '测试中', value: 'testing' },
  { label: '归档', value: 'archived' },
  { label: '禁用', value: 'disabled' },
]

const modelTypeOptions = computed(() => {
  const types = Array.from(
    new Set(models.value.map(model => model.model_type).filter(Boolean))
  )
  return types.map(type => ({ label: formatModelType(type), value: type }))
})

const detailMetrics = computed(() => {
  if (!detailModel.value?.metrics) return []
  return Object.entries(detailModel.value.metrics).map(([key, value]) => ({
    key,
    label: formatMetricKey(key),
    value: typeof value === 'number' ? Number(value.toFixed(4)) : value,
  }))
})

const detailArtifacts = computed(() => {
  if (!detailModel.value?.artifacts) return []
  return Object.entries(detailModel.value.artifacts).map(([key, value]) => ({
    key,
    label: formatArtifactKey(key),
    value,
  }))
})

function handleFilterChange() {
  refreshModels()
}

function primaryMetrics(metrics: Record<string, any>) {
  const keys = ['accuracy', 'map50', 'map50_95', 'precision', 'recall', 'f1']
  const entries: { key: string; label: string; value: number | string }[] = []
  keys.forEach(key => {
    if (metrics[key] != null) {
      const value = typeof metrics[key] === 'number' ? Number(metrics[key].toFixed(4)) : metrics[key]
      entries.push({ key, label: formatMetricKey(key), value })
    }
  })

  if (entries.length === 0) {
    const firstThree = Object.entries(metrics).slice(0, 3)
    return firstThree.map(([key, value]) => ({
      key,
      label: formatMetricKey(key),
      value: typeof value === 'number' ? Number(value.toFixed(4)) : value,
    }))
  }
  return entries
}

function hasMetrics(metrics: Record<string, any>) {
  return Object.keys(metrics).length > 0
}

function formatMetricKey(key: string) {
  const mapping: Record<string, string> = {
    accuracy: '准确率',
    precision: '精确率',
    recall: '召回率',
    f1: 'F1 值',
    map50: 'mAP@0.5',
    map50_95: 'mAP@0.5:0.95',
    loss: 'Loss',
  }
  return mapping[key] || key
}

function formatArtifactKey(key: string) {
  const mapping: Record<string, string> = {
    model: '模型文件',
    report: '训练报告',
    confusion_matrix: '混淆矩阵',
  }
  return mapping[key] || key
}

function formatModelType(type: string) {
  const mapping: Record<string, string> = {
    classification: '分类模型',
    detection: '检测模型',
    handwash: '洗手合规模型',
    multi_behavior: '多行为检测模型',
    yolov8: 'YOLOv8 模型',
  }
  return mapping[type] || type
}

function getStatusTagType(status: string) {
  const mapping: Record<string, 'success' | 'warning' | 'info' | 'error' | 'default'> = {
    active: 'success',
    testing: 'warning',
    archived: 'info',
    disabled: 'error',
  }
  return mapping[status] ?? 'default'
}

function getStatusLabel(status: string) {
  const mapping: Record<string, string> = {
    active: '可用',
    testing: '测试中',
    archived: '已归档',
    disabled: '已禁用',
  }
  return mapping[status] || status
}

function formatTime(value?: string | null) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

async function refreshModels() {
  loading.value = true
  try {
    models.value = await listModels({
      model_type: filters.modelType || undefined,
      status: filters.status || undefined,
    })
  } catch (error) {
    console.error('获取模型列表失败:', error)
    message.error('获取模型列表失败')
  } finally {
    loading.value = false
  }
}

function openDetail(model: ModelInfo) {
  detailModel.value = model
  detailStatus.value = model.status
  detailVisible.value = true
}

async function handleStatusUpdate(model: ModelInfo, status: string | null) {
  if (!status || status === model.status) return
  try {
    const updated = await updateModelStatus(model.id, status)
    updateModelInState(updated)
    message.success('模型状态已更新')
    if (detailModel.value?.id === updated.id) {
      detailModel.value = updated
      detailStatus.value = updated.status
    }
  } catch (error) {
    console.error('更新模型状态失败:', error)
    message.error('更新模型状态失败')
  }
}

function confirmDelete(model: ModelInfo) {
  dialog.warning({
    title: '删除模型',
    content: `确认删除模型「${model.name}」吗？该操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteModel(model.id)
        models.value = models.value.filter(item => item.id !== model.id)
        message.success('模型已删除')
        if (detailModel.value?.id === model.id) {
          detailVisible.value = false
        }
      } catch (error) {
        console.error('删除模型失败:', error)
        message.error('删除模型失败')
      }
    },
  })
}

function copyPath(path: string) {
  if (!navigator.clipboard) {
    message.warning('当前环境不支持复制到剪贴板')
    return
  }
  navigator.clipboard.writeText(path).then(
    () => message.success('路径已复制'),
    () => message.error('复制失败'),
  )
}

async function persistDetailStatus() {
  if (!detailModel.value || !detailStatus.value) {
    detailVisible.value = false
    return
  }
  if (detailStatus.value === detailModel.value.status) {
    detailVisible.value = false
    return
  }
  savingStatus.value = true
  try {
    const updated = await updateModelStatus(detailModel.value.id, detailStatus.value)
    updateModelInState(updated)
    detailModel.value = updated
    message.success('状态已保存')
    detailVisible.value = false
  } catch (error) {
    console.error('保存模型状态失败:', error)
    message.error('保存状态失败')
  } finally {
    savingStatus.value = false
  }
}

function updateModelInState(updated: ModelInfo) {
  const idx = models.value.findIndex(item => item.id === updated.id)
  if (idx >= 0) {
    models.value.splice(idx, 1, updated)
  } else {
    models.value.unshift(updated)
  }
}

defineExpose({
  refresh: refreshModels,
})

onMounted(() => {
  refreshModels()
})
</script>

<style scoped>
.model-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-weight: 600;
  font-size: 14px;
}

.model-body {
  margin-top: 8px;
}

.metrics-overview {
  margin-top: 8px;
}

.metrics-placeholder {
  margin-top: 8px;
  padding: 6px 8px;
  background-color: var(--n-color-target);
  border-radius: 4px;
}

.path-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.path-input {
  flex: 1;
}

.model-detail-content {
  max-height: 70vh;
  overflow-y: auto;
}
</style>

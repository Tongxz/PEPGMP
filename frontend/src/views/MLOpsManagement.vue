<template>
  <div class="mlops-management-page">
    <!-- 页面头部 -->
    <PageHeader
      title="MLOps管理"
      description="机器学习实验跟踪、模型版本管理与性能分析"
      icon="🤖"
    >
      <template #extra>
        <n-space>
          <n-button type="primary" @click="refreshData" :loading="loading">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新数据
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 主要内容区 -->
    <div class="mlops-content">
      <!-- 功能模块标签页 -->
      <n-tabs type="line" animated>
        <n-tab-pane name="experiments" tab="实验跟踪">
          <n-grid :cols="2" :x-gap="16" :y-gap="16">
            <!-- 实验跟踪 -->
            <n-gi>
              <DataCard title="MLflow实验跟踪" class="experiment-card">
            <n-empty v-if="experiments.length === 0" description="暂无实验数据">
              <template #extra>
                <n-button size="small" @click="refreshData">刷新</n-button>
              </template>
            </n-empty>
            <div v-else>
              <n-list>
                <n-list-item v-for="experiment in experiments" :key="experiment.run_id">
                  <n-card size="small">
                    <template #header>
                      <n-space justify="space-between">
                        <span>{{ experiment.run_name }}</span>
                        <n-tag :type="getStatusType(experiment.status)" size="small">
                          {{ experiment.status }}
                        </n-tag>
                      </n-space>
                    </template>
                    <div class="experiment-details">
                      <n-descriptions :column="2" size="small">
                        <n-descriptions-item label="开始时间">
                          {{ formatTime(experiment.start_time) }}
                        </n-descriptions-item>
                        <n-descriptions-item label="持续时间">
                          {{ formatDuration(experiment.end_time - experiment.start_time) }}
                        </n-descriptions-item>
                        <n-descriptions-item label="参数数量">
                          {{ Object.keys(experiment.params || {}).length }}
                        </n-descriptions-item>
                        <n-descriptions-item label="指标数量">
                          {{ Object.keys(experiment.metrics || {}).length }}
                        </n-descriptions-item>
                      </n-descriptions>
                    </div>
                  </n-card>
                </n-list-item>
              </n-list>
            </div>
          </DataCard>
        </n-gi>

        <!-- 模型版本管理 -->
        <n-gi>
          <DataCard title="DVC模型版本" class="model-card">
            <n-empty v-if="models.length === 0" description="暂无模型版本">
              <template #extra>
                <n-button size="small" @click="refreshData">刷新</n-button>
              </template>
            </n-empty>
            <div v-else>
              <n-list>
                <n-list-item v-for="model in models" :key="model.name">
                  <n-card size="small">
                    <template #header>
                      <n-space justify="space-between">
                        <span>{{ model.name }}</span>
                        <n-tag type="info" size="small">{{ model.version }}</n-tag>
                      </n-space>
                    </template>
                    <div class="model-details">
                      <n-descriptions :column="1" size="small">
                        <n-descriptions-item label="文件大小">
                          {{ formatFileSize(model.size) }}
                        </n-descriptions-item>
                        <n-descriptions-item label="最后修改">
                          {{ formatTime(model.modified_time) }}
                        </n-descriptions-item>
                        <n-descriptions-item label="路径">
                          <n-text code>{{ model.path }}</n-text>
                        </n-descriptions-item>
                      </n-descriptions>
                    </div>
                  </n-card>
                </n-list-item>
              </n-list>
            </div>
          </DataCard>
        </n-gi>

        <!-- 性能分析 -->
        <n-gi :span="2">
          <DataCard title="系统性能分析" class="performance-card">
            <n-grid :cols="4" :x-gap="16" :y-gap="16">
              <n-gi>
                <n-statistic label="平均处理时间" :value="avgProcessingTime" suffix="ms" />
              </n-gi>
              <n-gi>
                <n-statistic label="检测准确率" :value="detectionAccuracy" suffix="%" />
              </n-gi>
              <n-gi>
                <n-statistic label="系统稳定性" :value="systemStability" suffix="%" />
              </n-gi>
              <n-gi>
                <n-statistic label="资源利用率" :value="resourceUtilization" suffix="%" />
              </n-gi>
            </n-grid>

            <!-- 性能趋势图 -->
            <n-divider />
            <div class="performance-chart">
              <h4>性能趋势</h4>
              <n-empty description="性能图表功能开发中..." />
            </div>
          </DataCard>
        </n-gi>
      </n-grid>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NEmpty, NList, NListItem, NTag, NDescriptions, NDescriptionsItem, NGrid, NGi, NStatistic, NDivider, NText } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { PageHeader, DataCard } from '@/components/common'

interface Experiment {
  run_id: string
  run_name: string
  status: string
  start_time: number
  end_time: number
  params: Record<string, any>
  metrics: Record<string, any>
}

interface Model {
  name: string
  version: string
  path: string
  size: number
  modified_time: number
}

const loading = ref(false)
const experiments = ref<Experiment[]>([])
const models = ref<Model[]>([])

// 性能指标
const avgProcessingTime = ref(0)
const detectionAccuracy = ref(0)
const systemStability = ref(0)
const resourceUtilization = ref(0)

// 获取实验数据
async function fetchExperiments() {
  try {
    const response = await http.get('/mlops/experiments', {
      params: { limit: 10, offset: 0 }
    })
    experiments.value = response.data.items || []
  } catch (error: any) {
    console.error('获取实验数据失败:', error)
    message.error(error.message || '获取实验数据失败')
    experiments.value = []
  }
}

// 获取模型数据
async function fetchModels() {
  try {
    const response = await http.get('/mlops/models-versions')
    models.value = response.data.items || []
  } catch (error: any) {
    console.error('获取模型数据失败:', error)
    message.error(error.message || '获取模型数据失败')
    models.value = []
  }
}

// 获取性能数据
async function fetchPerformanceData() {
  try {
    const response = await http.get('/mlops/performance')
    const data = response.data
    avgProcessingTime.value = data.avg_processing_time || 0
    detectionAccuracy.value = data.detection_accuracy || 0
    systemStability.value = data.system_stability || 0
    resourceUtilization.value = data.resource_utilization || 0
  } catch (error: any) {
    console.error('获取性能数据失败:', error)
    message.error(error.message || '获取性能数据失败')
    avgProcessingTime.value = 0
    detectionAccuracy.value = 0
    systemStability.value = 0
    resourceUtilization.value = 0
  }
}

// 刷新数据
async function refreshData() {
  loading.value = true
  try {
    await Promise.all([
      fetchExperiments(),
      fetchModels(),
      fetchPerformanceData()
    ])
  } finally {
    loading.value = false
  }
}

// 获取状态类型
function getStatusType(status: string) {
  switch (status) {
    case 'FINISHED': return 'success'
    case 'RUNNING': return 'info'
    case 'FAILED': return 'error'
    default: return 'default'
  }
}

// 格式化时间
function formatTime(timestamp: number) {
  return new Date(timestamp).toLocaleString()
}

// 格式化持续时间
function formatDuration(duration: number) {
  const hours = Math.floor(duration / 3600000)
  const minutes = Math.floor((duration % 3600000) / 60000)
  return `${hours}h ${minutes}m`
}

// 格式化文件大小
function formatFileSize(bytes: number) {
  const sizes = ['B', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 B'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.mlops-management-page {
  padding: 16px;
}

.mlops-content {
  margin-top: 16px;
}

.experiment-card,
.model-card,
.performance-card {
  height: 100%;
}

.experiment-details,
.model-details {
  margin-top: 8px;
}

.performance-chart {
  margin-top: 16px;
}

.performance-chart h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
}
</style>

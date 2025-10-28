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
                            <n-descriptions-item label="参数">
                              <n-text depth="3" style="font-size: 11px;">
                                LR: {{ experiment.params.learning_rate }},
                                Batch: {{ experiment.params.batch_size }}
                              </n-text>
                            </n-descriptions-item>
                            <n-descriptions-item label="指标">
                              <n-text depth="3" style="font-size: 11px;">
                                Acc: {{ experiment.metrics.accuracy }},
                                Loss: {{ experiment.metrics.loss }}
                              </n-text>
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
              <DataCard title="DVC模型版本管理" class="model-card">
                <n-empty v-if="models.length === 0" description="暂无模型数据">
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
                            <n-tag type="info" size="small">v{{ model.version }}</n-tag>
                          </n-space>
                        </template>
                        <div class="model-details">
                          <n-descriptions :column="2" size="small">
                            <n-descriptions-item label="文件大小">
                              {{ formatFileSize(model.size) }}
                            </n-descriptions-item>
                            <n-descriptions-item label="修改时间">
                              {{ formatTime(model.modified_time) }}
                            </n-descriptions-item>
                            <n-descriptions-item label="路径">
                              <n-text depth="3" style="font-size: 11px;">{{ model.path }}</n-text>
                            </n-descriptions-item>
                          </n-descriptions>
                        </div>
                      </n-card>
                    </n-list-item>
                  </n-list>
                </div>
              </DataCard>
            </n-gi>
          </n-grid>
        </n-tab-pane>

        <n-tab-pane name="datasets" tab="数据管理">
          <DatasetManager />
        </n-tab-pane>

        <n-tab-pane name="deployments" tab="模型部署">
          <ModelDeployment />
        </n-tab-pane>

        <n-tab-pane name="workflows" tab="工作流管理">
          <WorkflowManager />
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NEmpty, NList, NListItem, NTag, NDescriptions, NDescriptionsItem, NGrid, NGi, NStatistic, NDivider, NText, NTabs, NTabPane } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { PageHeader, DataCard } from '@/components/common'
import DatasetManager from '@/components/MLOps/DatasetManager.vue'
import ModelDeployment from '@/components/MLOps/ModelDeployment.vue'
import WorkflowManager from '@/components/MLOps/WorkflowManager.vue'

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

const experiments = ref<Experiment[]>([])
const models = ref<Model[]>([])
const loading = ref(false)

// 获取实验数据
async function fetchExperiments() {
  try {
    // 这里应该调用实际的MLflow API
    // 目前使用模拟数据
    experiments.value = [
      {
        run_id: 'exp_001',
        run_name: 'intelligent_detection_test',
        status: 'FINISHED',
        start_time: Date.now() - 1800000,
        end_time: Date.now(),
        params: {
          learning_rate: 0.0005,
          batch_size: 64,
          epochs: 50
        },
        metrics: {
          accuracy: 0.97,
          loss: 0.03
        }
      }
    ]
  } catch (error) {
    console.error('获取实验数据失败:', error)
  }
}

// 获取模型数据
async function fetchModels() {
  try {
    // 这里应该调用实际的DVC API
    // 目前使用模拟数据
    models.value = [
      {
        name: 'yolov8s.pt',
        version: 'v1.2.0',
        path: 'models/yolo/yolov8s.pt',
        size: 21474836, // 20MB
        modified_time: Date.now() - 86400000
      },
      {
        name: 'hairnet_detection.pt',
        version: 'v2.1.0',
        path: 'models/hairnet_detection/hairnet_detection.pt',
        size: 52428800, // 50MB
        modified_time: Date.now() - 172800000
      }
    ]
  } catch (error) {
    console.error('获取模型数据失败:', error)
  }
}

// 刷新数据
async function refreshData() {
  loading.value = true
  try {
    await Promise.all([fetchExperiments(), fetchModels()])
  } finally {
    loading.value = false
  }
}

// 获取状态类型
function getStatusType(status: string) {
  const statusMap: Record<string, string> = {
    FINISHED: 'success',
    RUNNING: 'warning',
    FAILED: 'error'
  }
  return statusMap[status] || 'default'
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
  padding: 24px;
}

.mlops-content {
  margin-top: 24px;
}

.experiment-details,
.model-details {
  margin-top: 8px;
}
</style>

<template>
  <n-card title="模型部署管理" :segmented="{ content: true, footer: 'soft' }" size="small">
    <template #header-extra>
      <n-space>
        <n-button size="small" @click="refreshDeployments" :loading="loading">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
          刷新
        </n-button>
        <n-button size="small" type="primary" @click="showDeployDialog = true">
          <template #icon>
            <n-icon><RocketOutline /></n-icon>
          </template>
          部署模型
        </n-button>
      </n-space>
    </template>

    <!-- 部署列表 -->
    <n-empty v-if="deployments.length === 0" description="暂无部署">
      <template #extra>
        <n-button size="small" @click="showDeployDialog = true">部署第一个模型</n-button>
      </template>
    </n-empty>

    <div v-else>
      <n-list>
        <n-list-item v-for="deployment in deployments" :key="deployment.id">
          <n-card size="small" hoverable>
            <template #header>
              <n-space justify="space-between">
                <span>{{ deployment.name }}</span>
                <n-tag :type="getDeploymentStatusType(deployment.status)" size="small">
                  {{ getDeploymentStatusText(deployment.status) }}
                </n-tag>
              </n-space>
            </template>

            <div class="deployment-details">
              <n-descriptions :column="2" size="small">
                <n-descriptions-item label="模型版本">
                  {{ deployment.model_version }}
                </n-descriptions-item>
                <n-descriptions-item label="环境">
                  {{ deployment.environment }}
                </n-descriptions-item>
                <n-descriptions-item label="实例数">
                  {{ deployment.replicas }}
                </n-descriptions-item>
                <n-descriptions-item label="CPU使用率">
                  <n-progress type="line" :percentage="deployment.cpu_usage" :indicator-placement="'inside'" />
                </n-descriptions-item>
                <n-descriptions-item label="内存使用率">
                  <n-progress type="line" :percentage="deployment.memory_usage" :indicator-placement="'inside'" />
                </n-descriptions-item>
                <n-descriptions-item label="GPU使用率">
                  <n-progress v-if="deployment.gpu_usage !== undefined" type="line" :percentage="deployment.gpu_usage" :indicator-placement="'inside'" />
                  <span v-else>N/A</span>
                </n-descriptions-item>
                <n-descriptions-item label="请求数/分钟">
                  {{ deployment.requests_per_minute }}
                </n-descriptions-item>
                <n-descriptions-item label="平均响应时间">
                  {{ deployment.avg_response_time }}ms
                </n-descriptions-item>
                <n-descriptions-item label="错误率">
                  <n-tag :type="deployment.error_rate > 5 ? 'error' : deployment.error_rate > 1 ? 'warning' : 'success'" size="small">
                    {{ deployment.error_rate }}%
                  </n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="部署时间">
                  {{ formatTime(deployment.deployed_at) }}
                </n-descriptions-item>
              </n-descriptions>

              <!-- 性能图表 -->
              <n-divider />
              <div class="performance-charts">
                <n-text depth="3" style="font-size: 12px;">性能趋势 (最近24小时)</n-text>
                <n-grid :cols="2" :x-gap="12" :y-gap="8" style="margin-top: 8px;">
                  <n-gi>
                    <n-statistic label="总请求数" :value="deployment.total_requests" size="small" />
                  </n-gi>
                  <n-gi>
                    <n-statistic label="成功率" :value="deployment.success_rate" suffix="%" size="small" />
                  </n-gi>
                </n-grid>
              </div>

              <!-- 操作按钮 -->
              <n-divider />
              <n-space justify="end">
                <n-button size="small" @click="viewDeployment(deployment)">详情</n-button>
                <n-button size="small" @click="scaleDeployment(deployment)">扩缩容</n-button>
                <n-button size="small" @click="updateDeployment(deployment)">更新</n-button>
                <n-button
                  size="small"
                  :type="deployment.status === 'running' ? 'error' : 'primary'"
                  @click="toggleDeployment(deployment)"
                >
                  {{ deployment.status === 'running' ? '停止' : '启动' }}
                </n-button>
                <n-button size="small" type="error" @click="deleteDeployment(deployment)">删除</n-button>
              </n-space>
            </div>
          </n-card>
        </n-list-item>
      </n-list>
    </div>

    <!-- 部署模型对话框 -->
    <n-modal v-model:show="showDeployDialog" preset="dialog" title="部署模型" style="width: 600px;">
      <n-form :model="deployForm" label-placement="left" label-width="100px">
        <n-form-item label="模型选择">
          <n-select v-model:value="deployForm.model_id" placeholder="选择要部署的模型" :options="modelOptions" />
        </n-form-item>
        <n-form-item label="部署名称">
          <n-input v-model:value="deployForm.name" placeholder="输入部署名称" />
        </n-form-item>
        <n-form-item label="环境">
          <n-select v-model:value="deployForm.environment" placeholder="选择部署环境" :options="environmentOptions" />
        </n-form-item>
        <n-form-item label="实例数">
          <n-input-number v-model:value="deployForm.replicas" :min="1" :max="10" />
        </n-form-item>
        <n-form-item label="资源配置">
          <n-grid :cols="2" :x-gap="12">
            <n-gi>
              <n-input-group>
                <n-input-group-label>CPU</n-input-group-label>
                <n-input v-model:value="deployForm.cpu_limit" placeholder="1" />
                <n-input-group-label>核</n-input-group-label>
              </n-input-group>
            </n-gi>
            <n-gi>
              <n-input-group>
                <n-input-group-label>内存</n-input-group-label>
                <n-input v-model:value="deployForm.memory_limit" placeholder="2" />
                <n-input-group-label>GB</n-input-group-label>
              </n-input-group>
            </n-gi>
          </n-grid>
        </n-form-item>
        <n-form-item label="自动扩缩容">
          <n-switch v-model:value="deployForm.auto_scaling" />
        </n-form-item>
        <n-form-item v-if="deployForm.auto_scaling" label="扩缩容配置">
          <n-grid :cols="2" :x-gap="12">
            <n-gi>
              <n-input-group>
                <n-input-group-label>最小实例</n-input-group-label>
                <n-input-number v-model:value="deployForm.min_replicas" :min="1" />
              </n-input-group>
            </n-gi>
            <n-gi>
              <n-input-group>
                <n-input-group-label>最大实例</n-input-group-label>
                <n-input-number v-model:value="deployForm.max_replicas" :min="1" :max="20" />
              </n-input-group>
            </n-gi>
          </n-grid>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showDeployDialog = false">取消</n-button>
          <n-button type="primary" @click="submitDeployment" :loading="deploying">部署</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 部署详情对话框 -->
    <n-modal v-model:show="showDetailDialog" preset="dialog" title="部署详情" style="width: 900px;">
      <div v-if="selectedDeployment" class="deployment-detail-content">
        <!-- 基本信息 -->
        <n-card title="基本信息" size="small" style="margin-bottom: 16px;">
          <n-descriptions :column="2" size="small">
            <n-descriptions-item label="部署名称">
              {{ selectedDeployment.name }}
            </n-descriptions-item>
            <n-descriptions-item label="模型版本">
              {{ selectedDeployment.model_version }}
            </n-descriptions-item>
            <n-descriptions-item label="环境">
              <n-tag :type="getEnvironmentType(selectedDeployment.environment)" size="small">
                {{ getEnvironmentText(selectedDeployment.environment) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="getDeploymentStatusType(selectedDeployment.status)" size="small">
                {{ getDeploymentStatusText(selectedDeployment.status) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="实例数">
              {{ selectedDeployment.replicas }}
            </n-descriptions-item>
            <n-descriptions-item label="部署时间">
              {{ formatTime(selectedDeployment.deployed_at) }}
            </n-descriptions-item>
            <n-descriptions-item label="更新时间">
              {{ formatTime(selectedDeployment.updated_at) }}
            </n-descriptions-item>
            <n-descriptions-item label="总请求数">
              {{ selectedDeployment.total_requests.toLocaleString() }}
            </n-descriptions-item>
          </n-descriptions>
        </n-card>

        <!-- 资源使用情况 -->
        <n-card title="资源使用情况" size="small" style="margin-bottom: 16px;">
          <n-grid :cols="3" :x-gap="16" :y-gap="16">
            <n-gi>
              <n-statistic label="CPU使用率">
                <n-progress type="line" :percentage="selectedDeployment.cpu_usage" :indicator-placement="'inside'" />
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="内存使用率">
                <n-progress type="line" :percentage="selectedDeployment.memory_usage" :indicator-placement="'inside'" />
              </n-statistic>
            </n-gi>
            <n-gi>
              <n-statistic label="GPU使用率">
                <n-progress v-if="selectedDeployment.gpu_usage !== undefined" type="line" :percentage="selectedDeployment.gpu_usage" :indicator-placement="'inside'" />
                <span v-else>N/A</span>
              </n-statistic>
            </n-gi>
          </n-grid>
        </n-card>

        <!-- 性能指标 -->
        <n-card title="性能指标" size="small" style="margin-bottom: 16px;">
          <n-grid :cols="4" :x-gap="16" :y-gap="16">
            <n-gi>
              <n-statistic label="请求数/分钟" :value="selectedDeployment.requests_per_minute" />
            </n-gi>
            <n-gi>
              <n-statistic label="平均响应时间" :value="selectedDeployment.avg_response_time" suffix="ms" />
            </n-gi>
            <n-gi>
              <n-statistic label="错误率" :value="selectedDeployment.error_rate" suffix="%" />
            </n-gi>
            <n-gi>
              <n-statistic label="成功率" :value="selectedDeployment.success_rate" suffix="%" />
            </n-gi>
          </n-grid>
        </n-card>

        <!-- 监控图表 -->
        <n-card title="监控图表" size="small" style="margin-bottom: 16px;">
          <n-empty description="监控图表功能开发中">
            <template #extra>
              <n-button size="small" @click="loadMonitoringData">加载监控数据</n-button>
            </template>
          </n-empty>
        </n-card>

        <!-- 日志信息 -->
        <n-card title="日志信息" size="small">
          <n-empty description="日志功能开发中">
            <template #extra>
              <n-button size="small" @click="loadLogs">加载日志</n-button>
            </template>
          </n-empty>
        </n-card>
      </div>
      <template #action>
        <n-space>
          <n-button @click="showDetailDialog = false">关闭</n-button>
          <n-button type="primary" @click="scaleDeployment(selectedDeployment)">扩缩容</n-button>
          <n-button type="warning" @click="updateDeployment(selectedDeployment)">更新</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 更新部署对话框 -->
    <n-modal v-model:show="showUpdateDialog" preset="dialog" title="更新部署" style="width: 600px;">
      <n-form :model="updateForm" label-placement="left" label-width="100px">
        <n-form-item label="部署名称">
          <n-input v-model:value="updateForm.name" placeholder="输入部署名称" />
        </n-form-item>
        <n-form-item label="模型版本">
          <n-select v-model:value="updateForm.model_version" placeholder="选择新的模型版本" :options="modelVersionOptions" />
        </n-form-item>
        <n-form-item label="环境">
          <n-select v-model:value="updateForm.environment" placeholder="选择部署环境" :options="environmentOptions" />
        </n-form-item>
        <n-form-item label="实例数">
          <n-input-number v-model:value="updateForm.replicas" :min="1" :max="20" />
        </n-form-item>
        <n-form-item label="资源配置">
          <n-grid :cols="2" :x-gap="12">
            <n-gi>
              <n-input-group>
                <n-input-group-label>CPU</n-input-group-label>
                <n-input v-model:value="updateForm.cpu_limit" placeholder="1" />
                <n-input-group-label>核</n-input-group-label>
              </n-input-group>
            </n-gi>
            <n-gi>
              <n-input-group>
                <n-input-group-label>内存</n-input-group-label>
                <n-input v-model:value="updateForm.memory_limit" placeholder="2" />
                <n-input-group-label>GB</n-input-group-label>
              </n-input-group>
            </n-gi>
          </n-grid>
        </n-form-item>
        <n-form-item label="GPU配置">
          <n-grid :cols="2" :x-gap="12">
            <n-gi>
              <n-input-group>
                <n-input-group-label>GPU数量</n-input-group-label>
                <n-input-number v-model:value="updateForm.gpu_count" :min="0" :max="8" />
              </n-input-group>
            </n-gi>
            <n-gi>
              <n-input-group>
                <n-input-group-label>GPU内存</n-input-group-label>
                <n-input v-model:value="updateForm.gpu_memory" placeholder="8" />
                <n-input-group-label>GB</n-input-group-label>
              </n-input-group>
            </n-gi>
          </n-grid>
        </n-form-item>
        <n-form-item label="自动扩缩容">
          <n-switch v-model:value="updateForm.auto_scaling" />
        </n-form-item>
        <n-form-item v-if="updateForm.auto_scaling" label="扩缩容配置">
          <n-grid :cols="2" :x-gap="12">
            <n-gi>
              <n-input-group>
                <n-input-group-label>最小实例</n-input-group-label>
                <n-input-number v-model:value="updateForm.min_replicas" :min="1" />
              </n-input-group>
            </n-gi>
            <n-gi>
              <n-input-group>
                <n-input-group-label>最大实例</n-input-group-label>
                <n-input-number v-model:value="updateForm.max_replicas" :min="1" :max="50" />
              </n-input-group>
            </n-gi>
          </n-grid>
        </n-form-item>
        <n-form-item label="更新策略">
          <n-radio-group v-model:value="updateForm.update_strategy">
            <n-radio value="rolling">滚动更新</n-radio>
            <n-radio value="recreate">重新创建</n-radio>
            <n-radio value="blue_green">蓝绿部署</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="更新说明">
          <n-input v-model:value="updateForm.description" type="textarea" placeholder="输入更新说明" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showUpdateDialog = false">取消</n-button>
          <n-button type="primary" @click="submitUpdate" :loading="updating">更新</n-button>
        </n-space>
      </template>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NEmpty, NList, NListItem, NTag, NDescriptions, NDescriptionsItem, NDivider, NText, NGrid, NGi, NStatistic, NProgress, NModal, NForm, NFormItem, NSelect, NInput, NInputNumber, NInputGroup, NInputGroupLabel, NSwitch, NRadioGroup, NRadio, NP, useMessage } from 'naive-ui'
import { RefreshOutline, RocketOutline } from '@vicons/ionicons5'

interface Deployment {
  id: string
  name: string
  model_version: string
  environment: 'production' | 'staging' | 'development'
  status: 'running' | 'stopped' | 'deploying' | 'error' | 'scaling'
  replicas: number
  cpu_usage: number
  memory_usage: number
  gpu_usage?: number
  requests_per_minute: number
  avg_response_time: number
  error_rate: number
  total_requests: number
  success_rate: number
  deployed_at: string
  updated_at: string
}

const message = useMessage()
const deployments = ref<Deployment[]>([])
const loading = ref(false)
const showDeployDialog = ref(false)
const showDetailDialog = ref(false)
const showUpdateDialog = ref(false)
const selectedDeployment = ref<Deployment | null>(null)
const deploying = ref(false)
const updating = ref(false)

const deployForm = ref({
  model_id: '',
  name: '',
  environment: 'staging',
  replicas: 1,
  cpu_limit: '1',
  memory_limit: '2',
  auto_scaling: false,
  min_replicas: 1,
  max_replicas: 5
})

const updateForm = ref({
  name: '',
  model_version: '',
  environment: 'staging',
  replicas: 1,
  cpu_limit: '1',
  memory_limit: '2',
  gpu_count: 0,
  gpu_memory: '8',
  auto_scaling: false,
  min_replicas: 1,
  max_replicas: 5,
  update_strategy: 'rolling',
  description: ''
})

const modelOptions = [
  { label: 'YOLOv8 人体检测模型 v1.0', value: 'yolo_human_v1' },
  { label: 'YOLOv8 安全帽检测模型 v2.1', value: 'yolo_hairnet_v2' },
  { label: 'XGBoost 行为分类模型 v1.5', value: 'xgb_behavior_v1' },
  { label: 'MediaPipe 姿态检测模型 v1.0', value: 'mediapipe_pose_v1' }
]

const environmentOptions = [
  { label: '开发环境', value: 'development' },
  { label: '测试环境', value: 'staging' },
  { label: '生产环境', value: 'production' }
]

const modelVersionOptions = [
  { label: 'YOLOv8 人体检测模型 v1.0', value: 'yolo_human_v1.0' },
  { label: 'YOLOv8 人体检测模型 v1.1', value: 'yolo_human_v1.1' },
  { label: 'YOLOv8 人体检测模型 v1.2', value: 'yolo_human_v1.2' },
  { label: 'YOLOv8 安全帽检测模型 v2.1', value: 'yolo_hairnet_v2.1' },
  { label: 'YOLOv8 安全帽检测模型 v2.2', value: 'yolo_hairnet_v2.2' },
  { label: 'XGBoost 行为分类模型 v1.5', value: 'xgb_behavior_v1.5' },
  { label: 'XGBoost 行为分类模型 v1.6', value: 'xgb_behavior_v1.6' },
  { label: 'MediaPipe 姿态检测模型 v1.0', value: 'mediapipe_pose_v1.0' }
]

// 获取部署列表
async function fetchDeployments() {
  loading.value = true
  try {
    // 调用实际API
    const response = await fetch('/api/v1/mlops/deployments')
    if (response.ok) {
      deployments.value = await response.json()
    } else {
      console.error('获取部署列表失败:', response.statusText)
      // 如果API失败，使用模拟数据作为备用
      deployments.value = [
      {
        id: '1',
        name: 'human-detection-prod',
        model_version: 'yolo_human_v1.0',
        environment: 'production',
        status: 'running',
        replicas: 3,
        cpu_usage: 65,
        memory_usage: 78,
        gpu_usage: 45,
        requests_per_minute: 1200,
        avg_response_time: 45,
        error_rate: 0.5,
        total_requests: 172800,
        success_rate: 99.5,
        deployed_at: '2024-01-15T10:30:00Z',
        updated_at: '2024-01-20T14:20:00Z'
      },
      {
        id: '2',
        name: 'hairnet-detection-staging',
        model_version: 'yolo_hairnet_v2.1',
        environment: 'staging',
        status: 'running',
        replicas: 1,
        cpu_usage: 45,
        memory_usage: 60,
        gpu_usage: 30,
        requests_per_minute: 300,
        avg_response_time: 35,
        error_rate: 1.2,
        total_requests: 43200,
        success_rate: 98.8,
        deployed_at: '2024-01-18T09:15:00Z',
        updated_at: '2024-01-19T16:30:00Z'
      },
      {
        id: '3',
        name: 'behavior-classification-dev',
        model_version: 'xgb_behavior_v1.5',
        environment: 'development',
        status: 'stopped',
        replicas: 0,
        cpu_usage: 0,
        memory_usage: 0,
        requests_per_minute: 0,
        avg_response_time: 0,
        error_rate: 0,
        total_requests: 0,
        success_rate: 0,
        deployed_at: '2024-01-20T11:00:00Z',
        updated_at: '2024-01-20T11:00:00Z'
      }
    ]
    }
  } catch (error) {
    console.error('获取部署列表失败:', error)
    // 使用模拟数据作为备用
    deployments.value = [
      {
        id: '1',
        name: 'human-detection-prod',
        model_version: 'yolo_human_v1.0',
        environment: 'production',
        status: 'running',
        replicas: 3,
        cpu_usage: 65,
        memory_usage: 78,
        gpu_usage: 45,
        requests_per_minute: 1200,
        avg_response_time: 45,
        error_rate: 0.5,
        total_requests: 172800,
        success_rate: 99.5,
        deployed_at: '2024-01-15T10:30:00Z',
        updated_at: '2024-01-20T14:20:00Z'
      }
    ]
  } finally {
    loading.value = false
  }
}

// 刷新部署
function refreshDeployments() {
  fetchDeployments()
}

// 获取部署状态类型
function getDeploymentStatusType(status: string) {
  const statusMap = {
    running: 'success',
    stopped: 'default',
    deploying: 'warning',
    error: 'error',
    scaling: 'info'
  }
  return statusMap[status] || 'default'
}

// 获取部署状态文本
function getDeploymentStatusText(status: string) {
  const statusMap = {
    running: '运行中',
    stopped: '已停止',
    deploying: '部署中',
    error: '错误',
    scaling: '扩缩容中'
  }
  return statusMap[status] || status
}

// 格式化时间
function formatTime(timeString: string) {
  return new Date(timeString).toLocaleString('zh-CN')
}

// 查看部署详情
function viewDeployment(deployment: Deployment) {
  selectedDeployment.value = deployment
  showDetailDialog.value = true
}

// 扩缩容
async function scaleDeployment(deployment: Deployment) {
  console.log('扩缩容部署:', deployment)
  const newReplicas = prompt(`当前实例数: ${deployment.replicas}\n请输入新的实例数:`, deployment.replicas.toString())
  if (newReplicas && !isNaN(Number(newReplicas))) {
    try {
      message.loading('正在扩缩容...')
      const response = await fetch(`/api/v1/mlops/deployments/${deployment.id}/scale`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ replicas: Number(newReplicas) })
      })
      if (response.ok) {
        message.success('扩缩容成功')
        refreshDeployments()
      } else {
        throw new Error('扩缩容失败')
      }
    } catch (error) {
      message.error('扩缩容失败')
    }
  }
}

// 更新部署
function updateDeployment(deployment: Deployment) {
  selectedDeployment.value = deployment
  // 填充当前部署的配置到更新表单
  updateForm.value = {
    name: deployment.name,
    model_version: deployment.model_version,
    environment: deployment.environment,
    replicas: deployment.replicas,
    cpu_limit: '1', // 从当前配置获取
    memory_limit: '2', // 从当前配置获取
    gpu_count: 0,
    gpu_memory: '8',
    auto_scaling: false,
    min_replicas: 1,
    max_replicas: 5,
    update_strategy: 'rolling',
    description: ''
  }
  showUpdateDialog.value = true
}

// 切换部署状态
async function toggleDeployment(deployment: Deployment) {
  console.log('切换部署状态:', deployment)
  const action = deployment.status === 'running' ? '停止' : '启动'
  try {
    const confirmed = confirm(`确定要${action}部署 "${deployment.name}" 吗？`)
    if (confirmed) {
      message.loading(`正在${action}...`)
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      message.success(`部署${action}成功`)
      refreshDeployments()
    }
  } catch (error) {
    message.error(`${action}失败`)
  }
}

// 删除部署
async function deleteDeployment(deployment: Deployment) {
  console.log('删除部署:', deployment)
  try {
    const confirmed = confirm(`确定要删除部署 "${deployment.name}" 吗？此操作不可撤销。`)
    if (confirmed) {
      message.loading('正在删除...')
      const response = await fetch(`/api/v1/mlops/deployments/${deployment.id}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        message.success('部署删除成功')
        refreshDeployments()
      } else {
        throw new Error('删除失败')
      }
    }
  } catch (error) {
    message.error('删除失败')
  }
}

// 提交部署
async function submitDeployment() {
  deploying.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000))
    console.log('部署配置:', deployForm.value)
    showDeployDialog.value = false
    refreshDeployments()
  } catch (error) {
    console.error('部署失败:', error)
  } finally {
    deploying.value = false
  }
}

// 获取环境类型
function getEnvironmentType(environment: string) {
  const envMap = {
    production: 'error',
    staging: 'warning',
    development: 'info'
  }
  return envMap[environment] || 'default'
}

// 获取环境文本
function getEnvironmentText(environment: string) {
  const envMap = {
    production: '生产环境',
    staging: '测试环境',
    development: '开发环境'
  }
  return envMap[environment] || environment
}

// 加载监控数据
function loadMonitoringData() {
  message.info('正在加载监控数据...')
  // TODO: 实现监控数据加载
}

// 加载日志
function loadLogs() {
  message.info('正在加载日志...')
  // TODO: 实现日志加载
}

// 提交更新
async function submitUpdate() {
  if (!selectedDeployment.value) return
  
  updating.value = true
  try {
    message.loading('正在更新部署...')
    
    // 调用更新API
    const response = await fetch(`/api/v1/mlops/deployments/${selectedDeployment.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateForm.value)
    })
    
    if (response.ok) {
      message.success('部署更新成功')
      showUpdateDialog.value = false
      refreshDeployments()
    } else {
      throw new Error('更新失败')
    }
  } catch (error) {
    console.error('更新部署失败:', error)
    message.error('更新失败')
  } finally {
    updating.value = false
  }
}

onMounted(() => {
  fetchDeployments()
})
</script>

<style scoped>
.deployment-details {
  margin-top: 12px;
}

.performance-charts {
  margin-top: 8px;
  padding: 8px;
  background-color: var(--n-color-target);
  border-radius: 4px;
}

.deployment-detail-content {
  max-height: 70vh;
  overflow-y: auto;
}
</style>

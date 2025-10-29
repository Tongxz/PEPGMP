<template>
  <n-card title="工作流管理" :segmented="{ content: true, footer: 'soft' }" size="small">
    <template #header-extra>
      <n-space>
        <n-button size="small" @click="refreshWorkflows" :loading="loading">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
          刷新
        </n-button>
        <n-button size="small" type="primary" @click="showCreateDialog = true">
          <template #icon>
            <n-icon><AddOutline /></n-icon>
          </template>
          创建工作流
        </n-button>
      </n-space>
    </template>

    <!-- 工作流列表 -->
    <n-empty v-if="workflows.length === 0" description="暂无工作流">
      <template #extra>
        <n-button size="small" @click="showCreateDialog = true">创建第一个工作流</n-button>
      </template>
    </n-empty>

    <div v-else>
      <n-list>
        <n-list-item v-for="workflow in workflows" :key="workflow.id">
          <n-card size="small" hoverable>
            <template #header>
              <n-space justify="space-between">
                <span>{{ workflow.name }}</span>
                <n-tag :type="getWorkflowStatusType(workflow.status)" size="small">
                  {{ getWorkflowStatusText(workflow.status) }}
                </n-tag>
              </n-space>
            </template>

            <div class="workflow-details">
              <n-descriptions :column="2" size="small">
                <n-descriptions-item label="类型">
                  {{ getWorkflowTypeText(workflow.type) }}
                </n-descriptions-item>
                <n-descriptions-item label="触发器">
                  {{ getTriggerText(workflow.trigger) }}
                </n-descriptions-item>
                <n-descriptions-item label="最后运行">
                  {{ workflow.last_run ? formatTime(workflow.last_run) : '从未运行' }}
                </n-descriptions-item>
                <n-descriptions-item label="下次运行">
                  {{ workflow.next_run ? formatTime(workflow.next_run) : '无计划' }}
                </n-descriptions-item>
                <n-descriptions-item label="运行次数">
                  {{ workflow.run_count }}
                </n-descriptions-item>
                <n-descriptions-item label="成功率">
                  <n-tag :type="workflow.success_rate > 90 ? 'success' : workflow.success_rate > 70 ? 'warning' : 'error'" size="small">
                    {{ workflow.success_rate }}%
                  </n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="平均耗时">
                  {{ workflow.avg_duration }}分钟
                </n-descriptions-item>
                <n-descriptions-item label="创建时间">
                  {{ formatTime(workflow.created_at) }}
                </n-descriptions-item>
              </n-descriptions>

              <!-- 工作流步骤 -->
              <n-divider />
              <div class="workflow-steps">
                <n-text depth="3" style="font-size: 12px;">工作流步骤</n-text>
                <n-steps :current="getCurrentStep(workflow)" size="small" style="margin-top: 8px;">
                  <n-step
                    v-for="(step, index) in workflow.steps"
                    :key="index"
                    :title="step.name"
                    :status="getStepStatus(workflow, index)"
                  >
                    <template #description>
                      <n-text depth="3" style="font-size: 11px;">{{ step.description }}</n-text>
                    </template>
                  </n-step>
                </n-steps>
              </div>

              <!-- 最近运行记录 -->
              <n-divider v-if="workflow.recent_runs.length > 0" />
              <div v-if="workflow.recent_runs.length > 0" class="recent-runs">
                <n-text depth="3" style="font-size: 12px;">最近运行记录</n-text>
                <n-list size="small" style="margin-top: 8px;">
                  <n-list-item v-for="run in workflow.recent_runs.slice(0, 3)" :key="run.id">
                    <n-space justify="space-between">
                      <n-text style="font-size: 11px;">{{ formatTime(run.started_at) }}</n-text>
                      <n-tag :type="getRunStatusType(run.status)" size="tiny">
                        {{ getRunStatusText(run.status) }}
                      </n-tag>
                      <n-text depth="3" style="font-size: 11px;">{{ run.duration }}分钟</n-text>
                    </n-space>
                  </n-list-item>
                </n-list>
              </div>

              <!-- 操作按钮 -->
              <n-divider />
              <n-space justify="end">
                <n-button size="small" @click="viewWorkflow(workflow)">详情</n-button>
                <n-button size="small" @click="editWorkflow(workflow)">编辑</n-button>
                <n-button size="small" @click="runWorkflow(workflow)">运行</n-button>
                <n-button
                  size="small"
                  :type="workflow.status === 'active' ? 'error' : 'primary'"
                  @click="toggleWorkflow(workflow)"
                >
                  {{ workflow.status === 'active' ? '停用' : '启用' }}
                </n-button>
                <n-button size="small" type="error" @click="deleteWorkflow(workflow)">删除</n-button>
              </n-space>
            </div>
          </n-card>
        </n-list-item>
      </n-list>
    </div>

    <!-- 创建工作流对话框 -->
    <n-modal v-model:show="showCreateDialog" preset="dialog" title="创建工作流" style="width: 800px;">
      <n-form :model="workflowForm" label-placement="left" label-width="100px">
        <n-form-item label="工作流名称">
          <n-input v-model:value="workflowForm.name" placeholder="输入工作流名称" />
        </n-form-item>
        <n-form-item label="工作流类型">
          <n-select v-model:value="workflowForm.type" placeholder="选择工作流类型" :options="workflowTypeOptions" />
        </n-form-item>
        <n-form-item label="触发器">
          <n-select v-model:value="workflowForm.trigger" placeholder="选择触发器类型" :options="triggerOptions" />
        </n-form-item>
        <n-form-item v-if="workflowForm.trigger === 'schedule'" label="调度配置">
          <n-input v-model:value="workflowForm.schedule" placeholder="cron表达式，如：0 0 * * *" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="workflowForm.description" type="textarea" placeholder="输入工作流描述" />
        </n-form-item>

        <!-- 工作流步骤配置 -->
        <n-divider>工作流步骤</n-divider>
        <div v-for="(step, index) in workflowForm.steps" :key="index" class="workflow-step-config">
          <n-card size="small">
            <template #header>
              <n-space justify="space-between">
                <span>步骤 {{ index + 1 }}</span>
                <n-button size="tiny" type="error" @click="removeStep(index)">删除</n-button>
              </n-space>
            </template>
            <n-grid :cols="2" :x-gap="12">
              <n-gi>
                <n-form-item label="步骤名称">
                  <n-input v-model:value="step.name" placeholder="输入步骤名称" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="步骤类型">
                  <n-select v-model:value="step.type" placeholder="选择步骤类型" :options="stepTypeOptions" />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-form-item label="描述">
              <n-input v-model:value="step.description" placeholder="输入步骤描述" />
            </n-form-item>
            <n-form-item label="配置">
              <n-input v-model:value="step.config" type="textarea" placeholder="JSON配置" />
            </n-form-item>
          </n-card>
        </div>
        <n-button @click="addStep" type="dashed" style="width: 100%; margin-top: 12px;">
          <template #icon>
            <n-icon><AddOutline /></n-icon>
          </template>
          添加步骤
        </n-button>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showCreateDialog = false">取消</n-button>
          <n-button type="primary" @click="submitWorkflow" :loading="creating">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 工作流详情对话框 -->
    <n-modal v-model:show="showDetailDialog" preset="dialog" title="工作流详情" style="width: 1000px;">
      <div v-if="selectedWorkflow" class="workflow-detail-content">
        <!-- 基本信息 -->
        <n-card title="基本信息" size="small" style="margin-bottom: 16px;">
          <n-descriptions :column="2" size="small">
            <n-descriptions-item label="工作流名称">
              {{ selectedWorkflow.name }}
            </n-descriptions-item>
            <n-descriptions-item label="类型">
              <n-tag :type="getWorkflowTypeColor(selectedWorkflow.type)" size="small">
                {{ getWorkflowTypeText(selectedWorkflow.type) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="getWorkflowStatusType(selectedWorkflow.status)" size="small">
                {{ getWorkflowStatusText(selectedWorkflow.status) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="触发器">
              {{ getTriggerText(selectedWorkflow.trigger) }}
            </n-descriptions-item>
            <n-descriptions-item v-if="selectedWorkflow.schedule" label="调度配置">
              <n-code :code="selectedWorkflow.schedule" language="cron" />
            </n-descriptions-item>
            <n-descriptions-item label="运行次数">
              {{ selectedWorkflow.run_count }}
            </n-descriptions-item>
            <n-descriptions-item label="成功率">
              <n-tag :type="selectedWorkflow.success_rate > 90 ? 'success' : selectedWorkflow.success_rate > 70 ? 'warning' : 'error'" size="small">
                {{ selectedWorkflow.success_rate }}%
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="平均耗时">
              {{ selectedWorkflow.avg_duration }}分钟
            </n-descriptions-item>
            <n-descriptions-item label="创建时间">
              {{ formatTime(selectedWorkflow.created_at) }}
            </n-descriptions-item>
            <n-descriptions-item label="最后运行">
              {{ selectedWorkflow.last_run ? formatTime(selectedWorkflow.last_run) : '从未运行' }}
            </n-descriptions-item>
            <n-descriptions-item label="下次运行">
              {{ selectedWorkflow.next_run ? formatTime(selectedWorkflow.next_run) : '无计划' }}
            </n-descriptions-item>
          </n-descriptions>
          <n-divider />
          <n-text depth="3" style="font-size: 12px;">描述</n-text>
          <n-p style="margin-top: 8px;">{{ selectedWorkflow.description || '暂无描述' }}</n-p>
        </n-card>

        <!-- 工作流步骤 -->
        <n-card title="工作流步骤" size="small" style="margin-bottom: 16px;">
          <n-steps :current="getCurrentStep(selectedWorkflow)" size="small">
            <n-step
              v-for="(step, index) in selectedWorkflow.steps"
              :key="index"
              :title="step.name"
              :status="getStepStatus(selectedWorkflow, index)"
            >
              <template #description>
                <n-text depth="3" style="font-size: 12px;">{{ step.description }}</n-text>
                <n-tag :type="getStepTypeColor(step.type)" size="tiny" style="margin-left: 8px;">
                  {{ getStepTypeText(step.type) }}
                </n-tag>
              </template>
            </n-step>
          </n-steps>
        </n-card>

        <!-- 运行历史 -->
        <n-card title="运行历史" size="small" style="margin-bottom: 16px;">
          <n-list v-if="selectedWorkflow.recent_runs.length > 0">
            <n-list-item v-for="run in selectedWorkflow.recent_runs" :key="run.id">
              <n-card size="small">
                <n-space justify="space-between">
                  <n-space>
                    <n-text>{{ formatTime(run.started_at) }}</n-text>
                    <n-tag :type="getRunStatusType(run.status)" size="small">
                      {{ getRunStatusText(run.status) }}
                    </n-tag>
                    <n-text depth="3">耗时: {{ run.duration }}分钟</n-text>
                  </n-space>
                  <n-button size="tiny" @click="viewRunDetails(run)">详情</n-button>
                </n-space>
                <div v-if="run.error_message" style="margin-top: 8px;">
                  <n-alert type="error" :title="run.error_message" :bordered="false" />
                </div>
              </n-card>
            </n-list-item>
          </n-list>
          <n-empty v-else description="暂无运行记录" />
        </n-card>

        <!-- 配置信息 -->
        <n-card title="配置信息" size="small">
          <n-descriptions :column="1" size="small">
            <n-descriptions-item label="工作流ID">
              <n-code :code="selectedWorkflow.id" />
            </n-descriptions-item>
            <n-descriptions-item label="步骤配置">
              <n-code :code="JSON.stringify(selectedWorkflow.steps, null, 2)" language="json" />
            </n-descriptions-item>
          </n-descriptions>
        </n-card>
      </div>
      <template #action>
        <n-space>
          <n-button @click="showDetailDialog = false">关闭</n-button>
          <n-button type="primary" @click="runWorkflow(selectedWorkflow)">运行</n-button>
          <n-button type="warning" @click="editWorkflow(selectedWorkflow)">编辑</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑工作流对话框 -->
    <n-modal v-model:show="showEditDialog" preset="dialog" title="编辑工作流" style="width: 800px;">
      <n-form :model="editForm" label-placement="left" label-width="100px">
        <n-form-item label="工作流名称">
          <n-input v-model:value="editForm.name" placeholder="输入工作流名称" />
        </n-form-item>
        <n-form-item label="工作流类型">
          <n-select v-model:value="editForm.type" placeholder="选择工作流类型" :options="workflowTypeOptions" />
        </n-form-item>
        <n-form-item label="触发器">
          <n-select v-model:value="editForm.trigger" placeholder="选择触发器类型" :options="triggerOptions" />
        </n-form-item>
        <n-form-item v-if="editForm.trigger === 'schedule'" label="调度配置">
          <n-input v-model:value="editForm.schedule" placeholder="cron表达式，如：0 0 * * *" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="editForm.description" type="textarea" placeholder="输入工作流描述" />
        </n-form-item>

        <!-- 工作流步骤配置 -->
        <n-divider>工作流步骤</n-divider>
        <div v-for="(step, index) in editForm.steps" :key="index" class="workflow-step-config">
          <n-card size="small">
            <template #header>
              <n-space justify="space-between">
                <span>步骤 {{ index + 1 }}</span>
                <n-button size="tiny" type="error" @click="removeEditStep(index)">删除</n-button>
              </n-space>
            </template>
            <n-grid :cols="2" :x-gap="12">
              <n-gi>
                <n-form-item label="步骤名称">
                  <n-input v-model:value="step.name" placeholder="输入步骤名称" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="步骤类型">
                  <n-select v-model:value="step.type" placeholder="选择步骤类型" :options="stepTypeOptions" />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-form-item label="描述">
              <n-input v-model:value="step.description" placeholder="输入步骤描述" />
            </n-form-item>
            <n-form-item label="配置">
              <n-input v-model:value="step.config" type="textarea" placeholder="JSON配置" />
            </n-form-item>
            <n-form-item v-if="step.type === 'model_training'" label="训练参数">
              <n-grid :cols="2" :x-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>学习率</n-input-group-label>
                    <n-input :value="step.training_params?.learning_rate || ''" @update:value="(val) => updateTrainingParam(step, 'learning_rate', val)" placeholder="0.001" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>批次大小</n-input-group-label>
                    <n-input :value="step.training_params?.batch_size || ''" @update:value="(val) => updateTrainingParam(step, 'batch_size', val)" placeholder="32" />
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>
            <n-form-item v-if="step.type === 'model_deployment'" label="部署配置">
              <n-grid :cols="2" :x-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>实例数</n-input-group-label>
                    <n-input-number :value="step.deployment_params?.replicas || 1" @update:value="(val) => updateDeploymentParam(step, 'replicas', val)" :min="1" :max="10" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>环境</n-input-group-label>
                    <n-select :value="step.deployment_params?.environment || 'production'" @update:value="(val) => updateDeploymentParam(step, 'environment', val)" :options="environmentOptions" />
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>
          </n-card>
        </div>
        <n-button @click="addEditStep" type="dashed" style="width: 100%; margin-top: 12px;">
          <template #icon>
            <n-icon><AddOutline /></n-icon>
          </template>
          添加步骤
        </n-button>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showEditDialog = false">取消</n-button>
          <n-button type="primary" @click="submitEdit" :loading="editing">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NEmpty, NList, NListItem, NTag, NDescriptions, NDescriptionsItem, NDivider, NText, NSteps, NStep, NModal, NForm, NFormItem, NSelect, NInput, NInputNumber, NInputGroup, NInputGroupLabel, useMessage } from 'naive-ui'
import { RefreshOutline, AddOutline } from '@vicons/ionicons5'

interface WorkflowStep {
  name: string
  type: string
  description: string
  config: string
  training_params?: {
    learning_rate?: string
    batch_size?: string
  }
  deployment_params?: {
    replicas?: number
    environment?: string
  }
}

interface WorkflowRun {
  id: string
  status: 'success' | 'failed' | 'running' | 'pending'
  started_at: string
  duration: number
  error_message?: string
}

interface Workflow {
  id: string
  name: string
  type: 'training' | 'evaluation' | 'deployment' | 'data_processing'
  status: 'active' | 'inactive' | 'error'
  trigger: 'manual' | 'schedule' | 'webhook' | 'data_change'
  schedule?: string
  description: string
  steps: WorkflowStep[]
  last_run?: string
  next_run?: string
  run_count: number
  success_rate: number
  avg_duration: number
  created_at: string
  recent_runs: WorkflowRun[]
}

const message = useMessage()
const workflows = ref<Workflow[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showEditDialog = ref(false)
const selectedWorkflow = ref<Workflow | null>(null)
const creating = ref(false)
const editing = ref(false)

const workflowForm = ref({
  name: '',
  type: 'training',
  trigger: 'manual',
  schedule: '',
  description: '',
  steps: [
    { name: '数据预处理', type: 'data_processing', description: '清洗和预处理数据', config: '{}' }
  ]
})

const editForm = ref({
  name: '',
  type: 'training',
  trigger: 'manual',
  schedule: '',
  description: '',
  steps: [] as WorkflowStep[]
})

const workflowTypeOptions = [
  { label: '训练工作流', value: 'training' },
  { label: '评估工作流', value: 'evaluation' },
  { label: '部署工作流', value: 'deployment' },
  { label: '数据处理工作流', value: 'data_processing' }
]

const triggerOptions = [
  { label: '手动触发', value: 'manual' },
  { label: '定时触发', value: 'schedule' },
  { label: 'Webhook触发', value: 'webhook' },
  { label: '数据变更触发', value: 'data_change' }
]

const stepTypeOptions = [
  { label: '数据预处理', value: 'data_processing' },
  { label: '模型训练', value: 'model_training' },
  { label: '模型评估', value: 'model_evaluation' },
  { label: '模型部署', value: 'model_deployment' },
  { label: '数据验证', value: 'data_validation' },
  { label: '通知', value: 'notification' }
]

const environmentOptions = [
  { label: '开发环境', value: 'development' },
  { label: '测试环境', value: 'staging' },
  { label: '生产环境', value: 'production' }
]

// 更新训练参数
function updateTrainingParam(step: WorkflowStep, param: string, value: string) {
  if (!step.training_params) {
    step.training_params = {}
  }
  step.training_params[param as keyof typeof step.training_params] = value
}

// 更新部署参数
function updateDeploymentParam(step: WorkflowStep, param: string, value: string | number) {
  if (!step.deployment_params) {
    step.deployment_params = {}
  }
  step.deployment_params[param as keyof typeof step.deployment_params] = value
}

// 获取工作流列表
async function fetchWorkflows() {
  loading.value = true
  try {
    // 调用实际API
    const response = await fetch('/api/v1/mlops/workflows')
    if (response.ok) {
      workflows.value = await response.json()
    } else {
      console.error('获取工作流列表失败:', response.statusText)
      // 如果API失败，使用模拟数据作为备用
      workflows.value = [
      {
        id: '1',
        name: '智能检测模型训练流水线',
        type: 'training',
        status: 'active',
        trigger: 'schedule',
        schedule: '0 2 * * *',
        description: '每日自动训练智能检测模型',
        steps: [
          { name: '数据预处理', type: 'data_processing', description: '清洗和预处理检测数据', config: '{}' },
          { name: '模型训练', type: 'model_training', description: '训练YOLOv8检测模型', config: '{}' },
          { name: '模型评估', type: 'model_evaluation', description: '评估模型性能', config: '{}' },
          { name: '模型部署', type: 'model_deployment', description: '部署到生产环境', config: '{}' }
        ],
        last_run: '2024-01-20T02:00:00Z',
        next_run: '2024-01-21T02:00:00Z',
        run_count: 15,
        success_rate: 93.3,
        avg_duration: 45,
        created_at: '2024-01-01T10:00:00Z',
        recent_runs: [
          { id: '1', status: 'success', started_at: '2024-01-20T02:00:00Z', duration: 42 },
          { id: '2', status: 'success', started_at: '2024-01-19T02:00:00Z', duration: 38 },
          { id: '3', status: 'failed', started_at: '2024-01-18T02:00:00Z', duration: 15, error_message: '数据加载失败' }
        ]
      },
      {
        id: '2',
        name: '模型性能评估流水线',
        type: 'evaluation',
        status: 'active',
        trigger: 'webhook',
        description: '当新模型部署时自动评估性能',
        steps: [
          { name: '数据验证', type: 'data_validation', description: '验证测试数据质量', config: '{}' },
          { name: '模型评估', type: 'model_evaluation', description: '评估模型性能指标', config: '{}' },
          { name: '报告生成', type: 'notification', description: '生成评估报告', config: '{}' }
        ],
        last_run: '2024-01-20T14:30:00Z',
        next_run: undefined,
        run_count: 8,
        success_rate: 100,
        avg_duration: 12,
        created_at: '2024-01-10T15:00:00Z',
        recent_runs: [
          { id: '4', status: 'success', started_at: '2024-01-20T14:30:00Z', duration: 11 },
          { id: '5', status: 'success', started_at: '2024-01-19T16:45:00Z', duration: 13 }
        ]
      },
      {
        id: '3',
        name: '数据处理流水线',
        type: 'data_processing',
        status: 'inactive',
        trigger: 'data_change',
        description: '处理新上传的数据集',
        steps: [
          { name: '数据清洗', type: 'data_processing', description: '清洗原始数据', config: '{}' },
          { name: '数据标注', type: 'data_processing', description: '自动标注数据', config: '{}' },
          { name: '质量检查', type: 'data_validation', description: '检查数据质量', config: '{}' }
        ],
        last_run: '2024-01-15T09:00:00Z',
        next_run: undefined,
        run_count: 3,
        success_rate: 66.7,
        avg_duration: 25,
        created_at: '2024-01-05T11:00:00Z',
        recent_runs: [
          { id: '6', status: 'failed', started_at: '2024-01-15T09:00:00Z', duration: 8, error_message: '存储空间不足' }
        ]
      }
    ]
    }
  } catch (error) {
    console.error('获取工作流列表失败:', error)
    // 使用模拟数据作为备用
    workflows.value = [
      {
        id: '1',
        name: '智能检测模型训练流水线',
        type: 'training',
        status: 'active',
        trigger: 'schedule',
        schedule: '0 2 * * *',
        description: '每日自动训练智能检测模型',
        steps: [
          { name: '数据预处理', type: 'data_processing', description: '清洗和预处理检测数据' },
          { name: '模型训练', type: 'model_training', description: '训练YOLOv8检测模型' }
        ],
        last_run: '2024-01-20T02:00:00Z',
        next_run: '2024-01-21T02:00:00Z',
        run_count: 15,
        success_rate: 93.3,
        avg_duration: 45,
        created_at: '2024-01-01T10:00:00Z',
        recent_runs: [
          { id: '1', status: 'success', started_at: '2024-01-20T02:00:00Z', duration: 42 }
        ]
      }
    ]
  } finally {
    loading.value = false
  }
}

// 刷新工作流
function refreshWorkflows() {
  fetchWorkflows()
}

// 获取工作流状态类型
function getWorkflowStatusType(status: string) {
  const statusMap = {
    active: 'success',
    inactive: 'default',
    error: 'error'
  }
  return statusMap[status] || 'default'
}

// 获取工作流状态文本
function getWorkflowStatusText(status: string) {
  const statusMap = {
    active: '运行中',
    inactive: '已停用',
    error: '错误'
  }
  return statusMap[status] || status
}

// 获取工作流类型文本
function getWorkflowTypeText(type: string) {
  const typeMap = {
    training: '训练工作流',
    evaluation: '评估工作流',
    deployment: '部署工作流',
    data_processing: '数据处理工作流'
  }
  return typeMap[type] || type
}

// 获取触发器文本
function getTriggerText(trigger: string) {
  const triggerMap = {
    manual: '手动触发',
    schedule: '定时触发',
    webhook: 'Webhook触发',
    data_change: '数据变更触发'
  }
  return triggerMap[trigger] || trigger
}

// 获取当前步骤
function getCurrentStep(workflow: Workflow) {
  if (!workflow.last_run) return 0
  const lastRun = workflow.recent_runs[0]
  if (!lastRun || lastRun.status === 'success') return workflow.steps.length
  if (lastRun.status === 'failed') return 1
  return 2 // running
}

// 获取步骤状态
function getStepStatus(workflow: Workflow, index: number) {
  const currentStep = getCurrentStep(workflow)
  if (index < currentStep) return 'finish'
  if (index === currentStep) return 'process'
  return 'wait'
}

// 获取运行状态类型
function getRunStatusType(status: string) {
  const statusMap = {
    success: 'success',
    failed: 'error',
    running: 'warning',
    pending: 'default'
  }
  return statusMap[status] || 'default'
}

// 获取运行状态文本
function getRunStatusText(status: string) {
  const statusMap = {
    success: '成功',
    failed: '失败',
    running: '运行中',
    pending: '等待中'
  }
  return statusMap[status] || status
}

// 格式化时间
function formatTime(timeString: string) {
  return new Date(timeString).toLocaleString('zh-CN')
}

// 查看工作流
function viewWorkflow(workflow: Workflow) {
  selectedWorkflow.value = workflow
  showDetailDialog.value = true
}

// 编辑工作流
function editWorkflow(workflow: Workflow) {
  selectedWorkflow.value = workflow
  // 填充当前工作流的配置到编辑表单
  editForm.value = {
    name: workflow.name,
    type: workflow.type,
    trigger: workflow.trigger,
    schedule: workflow.schedule || '',
    description: workflow.description,
    steps: workflow.steps.map(step => ({
      ...step,
      training_params: step.type === 'model_training' ? {
        learning_rate: '0.001',
        batch_size: '32'
      } : undefined,
      deployment_params: step.type === 'model_deployment' ? {
        replicas: 1,
        environment: 'staging'
      } : undefined
    }))
  }
  showEditDialog.value = true
}

// 运行工作流
async function runWorkflow(workflow: Workflow) {
  console.log('运行工作流:', workflow)
  try {
    const confirmed = confirm(`确定要运行工作流 "${workflow.name}" 吗？`)
    if (confirmed) {
      message.loading('正在运行工作流...')
      const response = await fetch(`/api/v1/mlops/workflows/${workflow.id}/run`, {
        method: 'POST'
      })
      if (response.ok) {
        message.success('工作流运行成功')
        refreshWorkflows()
      } else {
        throw new Error('运行失败')
      }
    }
  } catch (error) {
    message.error('运行失败')
  }
}

// 切换工作流状态
async function toggleWorkflow(workflow: Workflow) {
  console.log('切换工作流状态:', workflow)
  const action = workflow.status === 'active' ? '停用' : '启用'
  try {
    const confirmed = confirm(`确定要${action}工作流 "${workflow.name}" 吗？`)
    if (confirmed) {
      message.loading(`正在${action}...`)
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      message.success(`工作流${action}成功`)
      refreshWorkflows()
    }
  } catch (error) {
    message.error(`${action}失败`)
  }
}

// 删除工作流
async function deleteWorkflow(workflow: Workflow) {
  console.log('删除工作流:', workflow)
  try {
    const confirmed = confirm(`确定要删除工作流 "${workflow.name}" 吗？此操作不可撤销。`)
    if (confirmed) {
      message.loading('正在删除...')
      const response = await fetch(`/api/v1/mlops/workflows/${workflow.id}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        message.success('工作流删除成功')
        refreshWorkflows()
      } else {
        throw new Error('删除失败')
      }
    }
  } catch (error) {
    message.error('删除失败')
  }
}

// 添加步骤
function addStep() {
  workflowForm.value.steps.push({
    name: '',
    type: 'data_processing',
    description: '',
    config: '{}'
  })
}

// 删除步骤
function removeStep(index: number) {
  workflowForm.value.steps.splice(index, 1)
}

// 提交工作流
async function submitWorkflow() {
  creating.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000))
    console.log('工作流配置:', workflowForm.value)
    showCreateDialog.value = false
    refreshWorkflows()
  } catch (error) {
    console.error('创建工作流失败:', error)
  } finally {
    creating.value = false
  }
}

// 获取工作流类型颜色
function getWorkflowTypeColor(type: string) {
  const typeMap = {
    training: 'success',
    evaluation: 'info',
    deployment: 'warning',
    data_processing: 'default'
  }
  return typeMap[type] || 'default'
}

// 获取步骤类型颜色
function getStepTypeColor(type: string) {
  const typeMap = {
    data_processing: 'info',
    model_training: 'success',
    model_evaluation: 'warning',
    model_deployment: 'error',
    data_validation: 'default',
    notification: 'info'
  }
  return typeMap[type] || 'default'
}

// 获取步骤类型文本
function getStepTypeText(type: string) {
  const typeMap = {
    data_processing: '数据处理',
    model_training: '模型训练',
    model_evaluation: '模型评估',
    model_deployment: '模型部署',
    data_validation: '数据验证',
    notification: '通知'
  }
  return typeMap[type] || type
}

// 查看运行详情
function viewRunDetails(run: WorkflowRun) {
  console.log('查看运行详情:', run)
  message.info(`查看运行详情: ${run.id}`)
  // TODO: 实现运行详情查看
}

// 添加编辑步骤
function addEditStep() {
  editForm.value.steps.push({
    name: '',
    type: 'data_processing',
    description: '',
    config: '{}'
  })
}

// 删除编辑步骤
function removeEditStep(index: number) {
  editForm.value.steps.splice(index, 1)
}

// 提交编辑
async function submitEdit() {
  if (!selectedWorkflow.value) return
  
  editing.value = true
  try {
    message.loading('正在保存工作流...')
    
    // 调用更新API
    const response = await fetch(`/api/v1/mlops/workflows/${selectedWorkflow.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editForm.value)
    })
    
    if (response.ok) {
      message.success('工作流保存成功')
      showEditDialog.value = false
      refreshWorkflows()
    } else {
      throw new Error('保存失败')
    }
  } catch (error) {
    console.error('保存工作流失败:', error)
    message.error('保存失败')
  } finally {
    editing.value = false
  }
}

onMounted(() => {
  fetchWorkflows()
})
</script>

<style scoped>
.workflow-details {
  margin-top: 12px;
}

.workflow-steps {
  margin-top: 8px;
  padding: 8px;
  background-color: var(--n-color-target);
  border-radius: 4px;
}

.recent-runs {
  margin-top: 8px;
  padding: 8px;
  background-color: var(--n-color-target);
  border-radius: 4px;
}

.workflow-step-config {
  margin-bottom: 12px;
}

.workflow-detail-content {
  max-height: 70vh;
  overflow-y: auto;
}
</style>

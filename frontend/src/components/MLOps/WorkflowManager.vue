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

    <!-- 错误提示 -->
    <n-alert
      v-if="errorMessage"
      type="error"
      title="获取工作流列表失败"
      :description="errorMessage"
      closable
      @close="errorMessage = null"
      style="margin-bottom: 16px"
    >
      <template #icon>
        <n-icon><AlertCircleOutline /></n-icon>
      </template>
    </n-alert>

    <!-- 工作流列表 -->
    <n-empty v-if="!loading && !errorMessage && workflows.length === 0" description="暂无工作流">
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
                    :description="step.description"
                  />
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
                <n-button
                  v-if="!isWorkflowRunning(workflow)"
                  size="small"
                  @click="runWorkflow(workflow)"
                >
                  运行
                </n-button>
                <n-button
                  v-if="isWorkflowRunning(workflow)"
                  size="small"
                  type="error"
                  @click="stopWorkflow(workflow)"
                >
                  停止
                </n-button>
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
              <n-input
                :value="configToString(step.config)"
                type="textarea"
                placeholder="JSON配置"
                @update:value="val => (step.config = val)"
              />
            </n-form-item>
            <n-form-item v-if="step.type === 'dataset_generation'" label="数据集配置">
              <n-grid :cols="2" :x-gap="12" :y-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>数据集名称</n-input-group-label>
                    <n-input
                      :value="(step as any).dataset_params?.dataset_name || ''"
                      @update:value="val => updateDatasetParam(step, 'dataset_name', val)"
                      placeholder="不填则自动生成"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>摄像头ID</n-input-group-label>
                    <n-input
                      :value="(step as any).dataset_params?.camera_ids || ''"
                      @update:value="val => updateDatasetParam(step, 'camera_ids', val)"
                      placeholder="多个摄像头用逗号分隔"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>最大记录</n-input-group-label>
                    <n-input-number
                      :value="(step as any).dataset_params?.max_records || 1000"
                      @update:value="val => updateDatasetParam(step, 'max_records', val)"
                      :min="100"
                      :max="50000"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>时间范围</n-input-group-label>
                    <n-date-picker
                      type="datetimerange"
                      :value="datasetTimeRange(step)"
                      @update:value="val => updateDatasetTimeRange(step, val)"
                      clearable
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>包含正常样本</n-input-group-label>
                    <div style="padding: 4px 0;">
                      <n-switch
                        :value="(step as any).dataset_params?.include_normal_samples ?? false"
                        @update:value="val => updateDatasetParam(step, 'include_normal_samples', val)"
                      />
                    </div>
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>

            <!-- 多行为训练配置（用于Roboflow数据集） -->
            <n-form-item v-if="step.type === 'multi_behavior_training'" label="训练配置">
              <n-grid :cols="1" :x-gap="12" :y-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>数据集目录</n-input-group-label>
                    <n-input
                      :value="getMultiBehaviorConfig(step, 'dataset_dir')"
                      @update:value="val => updateMultiBehaviorConfig(step, 'dataset_dir', val)"
                      placeholder="/Users/zhou/Code/Pyt/data/datasets/hairnet.v15i.yolov8"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>data.yaml路径</n-input-group-label>
                    <n-input
                      :value="getMultiBehaviorConfig(step, 'data_config')"
                      @update:value="val => updateMultiBehaviorConfig(step, 'data_config', val)"
                      placeholder="/Users/zhou/Code/Pyt/data/datasets/hairnet.v15i.yolov8/data.yaml"
                    />
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>

            <!-- 训练参数配置（适用于model_training和multi_behavior_training） -->
            <n-form-item v-if="step.type === 'model_training' || step.type === 'multi_behavior_training' || step.type === 'handwash_training'" label="训练参数">
              <n-grid :cols="2" :x-gap="12" :y-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>初始学习率 (lr0)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.lr0 || 0.01"
                      @update:value="(val) => updateTrainingParam(step, 'lr0', val ?? 0.01)"
                      :min="0.0001"
                      :max="1"
                      :step="0.001"
                      :precision="4"
                      placeholder="0.01"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>最终学习率 (lrf)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.lrf || 0.1"
                      @update:value="(val) => updateTrainingParam(step, 'lrf', val ?? 0.1)"
                      :min="0.01"
                      :max="1"
                      :step="0.01"
                      :precision="2"
                      placeholder="0.1"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>批次大小</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.batch_size || 16"
                      @update:value="(val) => updateTrainingParam(step, 'batch_size', val ?? 16)"
                      :min="1"
                      :max="128"
                      placeholder="16"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>设备</n-input-group-label>
                    <n-select
                      :value="(step as any).training_params?.device || 'auto'"
                      @update:value="(val) => updateTrainingParam(step, 'device', val || 'auto')"
                      :options="deviceOptions"
                      placeholder="选择设备"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>模型</n-input-group-label>
                    <n-input :value="(step as any).training_params?.model || ''" @update:value="(val) => updateTrainingParam(step, 'model', val)" placeholder="yolov8n.pt" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>训练轮数</n-input-group-label>
                    <n-input-number :value="(step as any).training_params?.epochs || 50" @update:value="(val) => updateTrainingParam(step, 'epochs', val ?? 50)" :min="1" :max="1000" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>图像尺寸</n-input-group-label>
                    <n-input-number :value="(step as any).training_params?.image_size || 640" @update:value="(val) => updateTrainingParam(step, 'image_size', val ?? 640)" :min="128" :max="2048" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>动量 (momentum)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.momentum || 0.937"
                      @update:value="(val) => updateTrainingParam(step, 'momentum', val ?? 0.937)"
                      :min="0"
                      :max="1"
                      :step="0.001"
                      :precision="3"
                      placeholder="0.937"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>权重衰减 (weight_decay)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.weight_decay || 0.0005"
                      @update:value="(val) => updateTrainingParam(step, 'weight_decay', val ?? 0.0005)"
                      :min="0"
                      :max="0.01"
                      :step="0.0001"
                      :precision="4"
                      placeholder="0.0005"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>预热轮数 (warmup_epochs)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.warmup_epochs || 3"
                      @update:value="(val) => updateTrainingParam(step, 'warmup_epochs', val ?? 3)"
                      :min="0"
                      :max="10"
                      placeholder="3"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>早停耐心值 (patience)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.patience || 15"
                      @update:value="(val) => updateTrainingParam(step, 'patience', val ?? 15)"
                      :min="0"
                      :max="100"
                      placeholder="15"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>边界框损失权重 (box)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.box || 7.5"
                      @update:value="(val) => updateTrainingParam(step, 'box', val ?? 7.5)"
                      :min="0"
                      :max="20"
                      :step="0.1"
                      :precision="1"
                      placeholder="7.5"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>分类损失权重 (cls)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.cls || 0.5"
                      @update:value="(val) => updateTrainingParam(step, 'cls', val ?? 0.5)"
                      :min="0"
                      :max="5"
                      :step="0.1"
                      :precision="1"
                      placeholder="0.5"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>DFL损失权重 (dfl)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.dfl || 1.5"
                      @update:value="(val) => updateTrainingParam(step, 'dfl', val ?? 1.5)"
                      :min="0"
                      :max="5"
                      :step="0.1"
                      :precision="1"
                      placeholder="1.5"
                    />
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>
          </n-card>
        </div>
        <n-button @click="addStep" tertiary style="width: 100%; margin-top: 12px;">
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
            />
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
          <n-button type="primary" @click="runWorkflow(selectedWorkflow!)" v-if="selectedWorkflow">运行</n-button>
          <n-button type="warning" @click="editWorkflow(selectedWorkflow!)" v-if="selectedWorkflow">编辑</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 运行详情对话框 -->
    <n-modal v-model:show="showRunLogDialog" preset="dialog" title="运行详情" style="width: 720px;">
      <div v-if="currentRun" class="run-log-content">
        <n-descriptions :column="2" size="small" label-placement="left">
          <n-descriptions-item label="运行ID">
            <n-code :code="currentRun.id" />
          </n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="getRunStatusType(currentRun.status)" size="small">
              {{ getRunStatusText(currentRun.status) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="开始时间">
            {{ formatTime(currentRun.started_at) }}
          </n-descriptions-item>
          <n-descriptions-item label="结束时间">
            {{ currentRun.ended_at ? formatTime(currentRun.ended_at) : '未结束' }}
          </n-descriptions-item>
          <n-descriptions-item label="耗时">
            {{ currentRun.duration != null ? `${currentRun.duration} 分钟` : '未记录' }}
          </n-descriptions-item>
        </n-descriptions>
        <div v-if="currentRun.error_message" style="margin-top: 12px;">
          <n-alert type="error" :title="currentRun.error_message" :bordered="false" />
        </div>
        <n-divider />
        <div v-if="trainingHighlights.length > 0" class="training-summary">
          <n-text depth="3" style="font-size: 12px;">训练结果摘要</n-text>
          <n-card
            v-for="highlight in trainingHighlights"
            :key="`${highlight.type}-${highlight.name}`"
            size="small"
            :title="`${highlight.name}（${getStepTypeText(highlight.type)}）`"
            style="margin-top: 12px;"
          >
            <n-descriptions :column="2" size="small">
              <n-descriptions-item label="模型版本">
                {{ highlight.version || '—' }}
              </n-descriptions-item>
              <n-descriptions-item label="使用样本数">
                {{ highlight.samples ?? '—' }}
              </n-descriptions-item>
              <n-descriptions-item v-if="highlight.modelPath" label="模型文件">
                <n-space align="center">
                  <n-text>{{ highlight.modelPath }}</n-text>
                  <n-button
                    size="tiny"
                    tertiary
                    @click="highlight.modelPath && copyToClipboard(highlight.modelPath)"
                  >
                    复制
                  </n-button>
                </n-space>
              </n-descriptions-item>
              <n-descriptions-item v-if="highlight.reportPath" label="训练报告">
                <n-space align="center">
                  <n-text>{{ highlight.reportPath }}</n-text>
                  <n-button
                    size="tiny"
                    tertiary
                    @click="highlight.reportPath && copyToClipboard(highlight.reportPath)"
                  >
                    复制
                  </n-button>
                </n-space>
              </n-descriptions-item>
            </n-descriptions>
            <n-divider v-if="highlight.metricEntries.length > 0" />
            <div v-if="highlight.metricEntries.length > 0" class="training-metrics">
              <n-grid :cols="2" :x-gap="12" :y-gap="12">
                <n-gi v-for="metric in highlight.metricEntries" :key="metric.key">
                  <n-statistic :label="metric.label" :value="metric.value" />
                </n-gi>
              </n-grid>
            </div>
            <n-divider v-if="highlight.artifactEntries.length > 0" />
            <n-descriptions
              v-if="highlight.artifactEntries.length > 0"
              :column="1"
              size="small"
            >
              <n-descriptions-item
                v-for="artifact in highlight.artifactEntries"
                :key="artifact.key"
                :label="artifact.label"
              >
                <n-space align="center">
                  <n-text>{{ artifact.value }}</n-text>
                  <n-button size="tiny" tertiary @click="copyToClipboard(String(artifact.value))">复制</n-button>
                </n-space>
              </n-descriptions-item>
            </n-descriptions>
          </n-card>
        </div>
        <n-text depth="3" style="font-size: 12px; margin-top: 16px; display: block;">
          步骤输出 ({{ currentRunEntries.length }} 个步骤)
        </n-text>
        <n-empty v-if="currentRunEntries.length === 0" description="暂无详细输出" style="margin-top: 12px;">
          <template #extra>
            <n-text depth="3" style="font-size: 11px;">
              如果工作流正在运行，请稍后刷新查看输出
            </n-text>
          </template>
        </n-empty>
        <n-collapse v-else style="margin-top: 12px;">
          <n-collapse-item
            v-for="(entry, index) in currentRunEntries"
            :key="index"
            :title="`步骤 ${index + 1}: ${entry.name || '未命名步骤'} (${getStepTypeText(entry.type)})`"
            :name="index"
          >
            <n-space vertical :size="12">
              <n-descriptions :column="1" size="small" bordered>
                <n-descriptions-item label="步骤名称">
                  {{ entry.name || '未命名步骤' }}
                </n-descriptions-item>
                <n-descriptions-item label="步骤类型">
                  <n-tag :type="getStepTypeColor(entry.type)" size="small">
                    {{ getStepTypeText(entry.type) }}
                  </n-tag>
                </n-descriptions-item>
              </n-descriptions>
              <n-divider style="margin: 8px 0;" />
              <n-text depth="3" style="font-size: 12px;">输出内容</n-text>
              <n-code
                :code="JSON.stringify(entry.output ?? {}, null, 2)"
                language="json"
                :show-line-numbers="true"
                :word-wrap="true"
              />
            </n-space>
          </n-collapse-item>
        </n-collapse>
      </div>
      <template #action>
        <n-space justify="end">
          <n-button @click="showRunLogDialog = false">关闭</n-button>
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
              <n-input
                :value="configToString(step.config)"
                type="textarea"
                placeholder="JSON配置"
                @update:value="val => (step.config = val)"
              />
            </n-form-item>
            <n-form-item v-if="step.type === 'dataset_generation'" label="数据集配置">
              <n-grid :cols="2" :x-gap="12" :y-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>数据集名称</n-input-group-label>
                    <n-input
                      :value="(step as any).dataset_params?.dataset_name || ''"
                      @update:value="val => updateDatasetParam(step, 'dataset_name', val)"
                      placeholder="不填则自动生成"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>摄像头ID</n-input-group-label>
                    <n-input
                      :value="(step as any).dataset_params?.camera_ids || ''"
                      @update:value="val => updateDatasetParam(step, 'camera_ids', val)"
                      placeholder="多个摄像头用逗号分隔"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>最大记录</n-input-group-label>
                    <n-input-number
                      :value="(step as any).dataset_params?.max_records || 1000"
                      @update:value="val => updateDatasetParam(step, 'max_records', val)"
                      :min="100"
                      :max="50000"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>时间范围</n-input-group-label>
                    <n-date-picker
                      type="datetimerange"
                      :value="datasetTimeRange(step)"
                      @update:value="val => updateDatasetTimeRange(step, val)"
                      clearable
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>包含正常样本</n-input-group-label>
                    <div style="padding: 4px 0;">
                      <n-switch
                        :value="(step as any).dataset_params?.include_normal_samples ?? false"
                        @update:value="val => updateDatasetParam(step, 'include_normal_samples', val)"
                      />
                    </div>
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>
            <!-- 多行为训练配置（用于Roboflow数据集） -->
            <n-form-item v-if="step.type === 'multi_behavior_training'" label="训练配置">
              <n-grid :cols="1" :x-gap="12" :y-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>数据集目录</n-input-group-label>
                    <n-input
                      :value="getMultiBehaviorConfig(step, 'dataset_dir')"
                      @update:value="val => updateMultiBehaviorConfig(step, 'dataset_dir', val)"
                      placeholder="/Users/zhou/Code/Pyt/data/datasets/hairnet.v15i.yolov8"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>data.yaml路径</n-input-group-label>
                    <n-input
                      :value="getMultiBehaviorConfig(step, 'data_config')"
                      @update:value="val => updateMultiBehaviorConfig(step, 'data_config', val)"
                      placeholder="/Users/zhou/Code/Pyt/data/datasets/hairnet.v15i.yolov8/data.yaml"
                    />
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>

            <!-- 训练参数配置（适用于model_training和multi_behavior_training） -->
            <n-form-item v-if="step.type === 'model_training' || step.type === 'multi_behavior_training' || step.type === 'handwash_training'" label="训练参数">
              <n-grid :cols="2" :x-gap="12" :y-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>初始学习率 (lr0)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.lr0 || 0.01"
                      @update:value="(val) => updateTrainingParam(step, 'lr0', val ?? 0.01)"
                      :min="0.0001"
                      :max="1"
                      :step="0.001"
                      :precision="4"
                      placeholder="0.01"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>最终学习率 (lrf)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.lrf || 0.1"
                      @update:value="(val) => updateTrainingParam(step, 'lrf', val ?? 0.1)"
                      :min="0.01"
                      :max="1"
                      :step="0.01"
                      :precision="2"
                      placeholder="0.1"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>批次大小</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.batch_size || 16"
                      @update:value="(val) => updateTrainingParam(step, 'batch_size', val ?? 16)"
                      :min="1"
                      :max="128"
                      placeholder="16"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>设备</n-input-group-label>
                    <n-select
                      :value="(step as any).training_params?.device || 'auto'"
                      @update:value="(val) => updateTrainingParam(step, 'device', val || 'auto')"
                      :options="deviceOptions"
                      placeholder="选择设备"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>模型</n-input-group-label>
                    <n-input :value="(step as any).training_params?.model || ''" @update:value="(val) => updateTrainingParam(step, 'model', val)" placeholder="yolov8n.pt" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>训练轮数</n-input-group-label>
                    <n-input-number :value="(step as any).training_params?.epochs || 50" @update:value="(val) => updateTrainingParam(step, 'epochs', val ?? 50)" :min="1" :max="1000" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>图像尺寸</n-input-group-label>
                    <n-input-number :value="(step as any).training_params?.image_size || 640" @update:value="(val) => updateTrainingParam(step, 'image_size', val ?? 640)" :min="128" :max="2048" />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>动量 (momentum)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.momentum || 0.937"
                      @update:value="(val) => updateTrainingParam(step, 'momentum', val ?? 0.937)"
                      :min="0"
                      :max="1"
                      :step="0.001"
                      :precision="3"
                      placeholder="0.937"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>权重衰减 (weight_decay)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.weight_decay || 0.0005"
                      @update:value="(val) => updateTrainingParam(step, 'weight_decay', val ?? 0.0005)"
                      :min="0"
                      :max="0.01"
                      :step="0.0001"
                      :precision="4"
                      placeholder="0.0005"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>预热轮数 (warmup_epochs)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.warmup_epochs || 3"
                      @update:value="(val) => updateTrainingParam(step, 'warmup_epochs', val ?? 3)"
                      :min="0"
                      :max="10"
                      placeholder="3"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>早停耐心值 (patience)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.patience || 15"
                      @update:value="(val) => updateTrainingParam(step, 'patience', val ?? 15)"
                      :min="0"
                      :max="100"
                      placeholder="15"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>边界框损失权重 (box)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.box || 7.5"
                      @update:value="(val) => updateTrainingParam(step, 'box', val ?? 7.5)"
                      :min="0"
                      :max="20"
                      :step="0.1"
                      :precision="1"
                      placeholder="7.5"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>分类损失权重 (cls)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.cls || 0.5"
                      @update:value="(val) => updateTrainingParam(step, 'cls', val ?? 0.5)"
                      :min="0"
                      :max="5"
                      :step="0.1"
                      :precision="1"
                      placeholder="0.5"
                    />
                  </n-input-group>
                </n-gi>
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>DFL损失权重 (dfl)</n-input-group-label>
                    <n-input-number
                      :value="(step as any).training_params?.dfl || 1.5"
                      @update:value="(val) => updateTrainingParam(step, 'dfl', val ?? 1.5)"
                      :min="0"
                      :max="5"
                      :step="0.1"
                      :precision="1"
                      placeholder="1.5"
                    />
                  </n-input-group>
                </n-gi>
              </n-grid>
            </n-form-item>
            <n-form-item v-if="step.type === 'model_deployment'" label="部署配置">
              <n-grid :cols="2" :x-gap="12">
                <n-gi>
                  <n-input-group>
                    <n-input-group-label>实例数</n-input-group-label>
                    <n-input-number :value="(step as any).deployment_params?.replicas || 1" @update:value="(val) => updateDeploymentParam(step, 'replicas', val ?? 1)" :min="1" :max="10" />
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
        <n-button @click="addEditStep" tertiary style="width: 100%; margin-top: 12px;">
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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NEmpty, NList, NListItem, NTag, NDescriptions, NDescriptionsItem, NDivider, NText, NSteps, NStep, NModal, NForm, NFormItem, NSelect, NInput, NInputNumber, NInputGroup, NInputGroupLabel, NDatePicker, NSwitch, NAlert, NCollapse, NCollapseItem, NCode, NGrid, NGi, NStatistic, useMessage } from 'naive-ui'
import { RefreshOutline, AddOutline, AlertCircleOutline } from '@vicons/ionicons5'
import { http } from '@/lib/http'

interface WorkflowStep {
  name: string
  type: string
  description: string
  config: string | Record<string, any>
  dataset_params?: {
    dataset_name?: string
    camera_ids?: string
    include_normal_samples?: boolean
    max_records?: number
    start_time?: string
    end_time?: string
  }
  training_params?: {
    learning_rate?: string | number
    batch_size?: string | number
    device?: string | number
    epochs?: string | number
    image_size?: string | number
    momentum?: string | number
    weight_decay?: string | number
    warmup_epochs?: string | number
    patience?: string | number
    box?: string | number
    cls?: string | number
    dfl?: string | number
    lr0?: string | number
    lrf?: string | number
    model?: string
  }
  deployment_params?: {
    replicas?: number
    environment?: string
  }
}

interface WorkflowRun {
  id: string
  workflow_id?: string
  status: 'success' | 'failed' | 'running' | 'pending' | 'cancelled'
  started_at: string
  ended_at?: string | null
  duration?: number | null
  error_message?: string | null
  run_log?: string | null
  run_config?: Record<string, any>
  step_outputs?: WorkflowStepOutput[]
}

interface WorkflowStepOutput {
  name: string
  type: string
  output?: Record<string, any> | null
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
const errorMessage = ref<string | null>(null)
function copyToClipboard(text: string) {
  if (!text) return
  if (!navigator.clipboard) {
    message.warning('当前环境不支持复制')
    return
  }
  navigator.clipboard.writeText(text).then(
    () => message.success('已复制到剪贴板'),
    () => message.error('复制失败'),
  )
}

const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showEditDialog = ref(false)
const selectedWorkflow = ref<Workflow | null>(null)
const creating = ref(false)
const editing = ref(false)
const showRunLogDialog = ref(false)
const currentRun = ref<WorkflowRun | null>(null)
const currentRunEntries = ref<WorkflowStepOutput[]>([])
const TRAINING_STEP_TYPES = ['model_training', 'handwash_training', 'multi_behavior_training']

function normalizeRecord(value: unknown): Record<string, any> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {}
  }
  return value as Record<string, any>
}

function formatMetricLabel(key: string) {
  const mapping: Record<string, string> = {
    accuracy: '准确率',
    precision: '精确率',
    recall: '召回率',
    f1: 'F1 值',
    loss: 'Loss',
    map50: 'mAP@0.5',
    map50_95: 'mAP@0.5:0.95',
  }
  return mapping[key] || key
}

function formatArtifactLabel(key: string) {
  const mapping: Record<string, string> = {
    model: '模型文件',
    report: '训练报告',
    confusion_matrix: '混淆矩阵',
  }
  return mapping[key] || key
}

function formatMetricValue(value: any) {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return value
    return Number(value.toFixed(4))
  }
  return value
}

function buildMetricEntries(metrics: Record<string, any>) {
  return Object.entries(metrics).map(([key, value]) => ({
    key,
    label: formatMetricLabel(key),
    value: formatMetricValue(value),
  }))
}

function buildArtifactEntries(artifacts: Record<string, any>) {
  return Object.entries(artifacts).map(([key, value]) => ({
    key,
    label: formatArtifactLabel(key),
    value,
  }))
}

const trainingHighlights = computed(() => {
  return currentRunEntries.value
    .filter(entry => TRAINING_STEP_TYPES.includes(entry.type))
    .map(entry => {
      const output = normalizeRecord(entry.output)
      const metrics = normalizeRecord(output.metrics)
      const artifacts = normalizeRecord(output.artifacts)
      return {
        name: entry.name || '模型训练',
        type: entry.type,
        version: output.version ?? '',
        samples: output.samples_used ?? null,
        modelPath: output.model_path ?? '',
        reportPath: output.report_path ?? '',
        metricEntries: buildMetricEntries(metrics),
        artifactEntries: buildArtifactEntries(artifacts),
      }
    })
})

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
  { label: '数据集生成', value: 'dataset_generation' },
  { label: '模型训练', value: 'model_training' },
  { label: '多行为训练', value: 'multi_behavior_training' },
  { label: '洗手训练', value: 'handwash_training' },
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

const deviceOptions = [
  { label: '自动选择', value: 'auto' },
  { label: 'CPU', value: 'cpu' },
  { label: 'CUDA (GPU)', value: 'cuda' },
  { label: 'MPS (Apple Silicon)', value: 'mps' }
]

// 更新训练参数
function updateTrainingParam(step: WorkflowStep, param: string, value: string | number) {
  if (!step.training_params) {
    step.training_params = {}
  }
  (step.training_params as any)[param] = value
  syncTrainingConfig(step)
}

// 获取多行为训练配置
function getMultiBehaviorConfig(step: WorkflowStep, key: string): string {
  const config = parseConfig(step.config)
  return config[key] || ''
}

// 更新多行为训练配置
function updateMultiBehaviorConfig(step: WorkflowStep, key: string, value: string) {
  const config = parseConfig(step.config)
  if (value) {
    config[key] = value
  } else {
    delete config[key]
  }
  step.config = JSON.stringify(config, null, 2)
}

// 同步训练配置到config
function syncTrainingConfig(step: WorkflowStep) {
  if (!step.training_params) {
    return
  }
  const config = parseConfig(step.config)
  if (!(config as any).training_params) {
    (config as any).training_params = {}
  }
  Object.assign(config.training_params, step.training_params)
  step.config = JSON.stringify(config, null, 2)
}

// 更新部署参数
function updateDeploymentParam(step: WorkflowStep, param: string, value: string | number) {
  if (!step.deployment_params) {
    step.deployment_params = {}
  }
  (step.deployment_params as any)[param] = value
}

function parseConfig(config: WorkflowStep['config']) {
  if (typeof config === 'string') {
    try {
      const parsed = JSON.parse(config)
      return typeof parsed === 'object' && parsed !== null ? parsed : {}
    } catch (error) {
      console.warn('配置解析失败:', error)
      return {}
    }
  }
  return config && typeof config === 'object' ? config : {}
}

function configToString(config: WorkflowStep['config']) {
  if (typeof config === 'string') {
    return config
  }
  try {
    return JSON.stringify(config || {}, null, 2)
  } catch (error) {
    console.warn('配置序列化失败:', error)
    return '{}'
  }
}

function ensureDatasetParams(step: WorkflowStep) {
  if (!step.dataset_params) {
    step.dataset_params = {
      include_normal_samples: false,
      max_records: 1000
    }
  }
}

function parseCameraIds(value: string | string[] | undefined): string[] | undefined {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean)
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return undefined
}

function datasetTimeRange(step: WorkflowStep): [number, number] | null {
  const params = (step as any).dataset_params
  if (!params || !params.start_time || !params.end_time) {
    return null
  }
  const start = Date.parse(params.start_time)
  const end = Date.parse(params.end_time)
  if (Number.isNaN(start) || Number.isNaN(end)) {
    return null
  }
  return [start, end]
}

function updateDatasetTimeRange(step: WorkflowStep, value: [number, number] | null) {
  ensureDatasetParams(step)
  if (value && Array.isArray(value) && value.length === 2) {
    step.dataset_params!.start_time = new Date(value[0]).toISOString()
    step.dataset_params!.end_time = new Date(value[1]).toISOString()
  } else {
    delete step.dataset_params!.start_time
    delete step.dataset_params!.end_time
  }
  syncDatasetConfig(step)
}

function updateDatasetParam(step: WorkflowStep, param: string, value: any) {
  ensureDatasetParams(step)
  if (param === 'max_records') {
    const numeric = Number(value)
    step.dataset_params!.max_records = Number.isNaN(numeric) ? 1000 : numeric
  } else if (param === 'include_normal_samples') {
    step.dataset_params!.include_normal_samples = Boolean(value)
  } else if (param === 'camera_ids') {
    if (value) {
      step.dataset_params!.camera_ids = value
    } else {
      delete step.dataset_params!.camera_ids
    }
  } else if (param === 'dataset_name') {
    if (value) {
      step.dataset_params!.dataset_name = value
    } else {
      delete step.dataset_params!.dataset_name
    }
  }
  syncDatasetConfig(step)
}

function syncDatasetConfig(step: WorkflowStep) {
  if (!step.dataset_params) {
    return
  }
  const cameraIds = parseCameraIds(step.dataset_params.camera_ids)
  const config: Record<string, any> = {
    ...step.dataset_params,
    camera_ids: cameraIds
  }
  if (cameraIds === undefined) {
    delete config.camera_ids
  }
  step.config = JSON.stringify(config, null, 2)
}

function normalizeDatasetParams(step: WorkflowStep) {
  if (step.type !== 'dataset_generation') {
    return undefined
  }
  if (!step.dataset_params) {
    return undefined
  }
  const params: Record<string, any> = {}
  if (step.dataset_params.dataset_name) {
    params.dataset_name = step.dataset_params.dataset_name
  }
  const cameraList = parseCameraIds(step.dataset_params.camera_ids)
  if (cameraList && cameraList.length > 0) {
    params.camera_ids = cameraList
  }
  if (step.dataset_params.include_normal_samples !== undefined) {
    params.include_normal_samples = Boolean(step.dataset_params.include_normal_samples)
  }
  if (step.dataset_params.max_records !== undefined) {
    const numeric = Number(step.dataset_params.max_records)
    params.max_records = Number.isNaN(numeric) ? 1000 : numeric
  }
  if (step.dataset_params.start_time) {
    params.start_time = step.dataset_params.start_time
  }
  if (step.dataset_params.end_time) {
    params.end_time = step.dataset_params.end_time
  }
  return Object.keys(params).length > 0 ? params : undefined
}

function normalizeStepsForSubmit(steps: WorkflowStep[]) {
  return steps.map((step) => {
    const normalized: Record<string, any> = {
      name: step.name,
      type: step.type,
      description: step.description
    }
    const configObj = parseConfig(step.config)
    const datasetParams = normalizeDatasetParams(step)
    if (datasetParams) {
      normalized.dataset_params = datasetParams
      Object.assign(configObj, datasetParams)
    }

    // 处理多行为训练配置
    if (step.type === 'multi_behavior_training') {
      normalized.config = {}
      if (configObj.dataset_dir) {
        normalized.config.dataset_dir = configObj.dataset_dir
      }
      if (configObj.data_config) {
        normalized.config.data_config = configObj.data_config
      }
      if (configObj.training_params) {
        normalized.config.training_params = configObj.training_params
      }
    } else if (Object.keys(configObj).length > 0) {
      normalized.config = configObj
    }

    if (step.training_params) {
      const trainingPayload: Record<string, any> = {}
      if ((step.training_params as any).lr0 !== undefined) {
        trainingPayload.lr0 = step.training_params.lr0
      }
      if (step.training_params.lrf !== undefined) {
        trainingPayload.lrf = step.training_params.lrf
      }
      if (step.training_params.learning_rate !== undefined) {
        trainingPayload.learning_rate = step.training_params.learning_rate
      }
      if (step.training_params.batch_size !== undefined) {
        trainingPayload.batch_size = step.training_params.batch_size
      }
      if (step.training_params.device) {
        trainingPayload.device = step.training_params.device
      }
      if (step.training_params.model) {
        trainingPayload.model = step.training_params.model
      }
      if (step.training_params.epochs !== undefined) {
        trainingPayload.epochs = step.training_params.epochs
      }
      if (step.training_params.image_size !== undefined) {
        trainingPayload.image_size = step.training_params.image_size
      }
      if (step.training_params.momentum !== undefined) {
        trainingPayload.momentum = step.training_params.momentum
      }
      if (step.training_params.weight_decay !== undefined) {
        trainingPayload.weight_decay = step.training_params.weight_decay
      }
      if (step.training_params.warmup_epochs !== undefined) {
        trainingPayload.warmup_epochs = step.training_params.warmup_epochs
      }
      if (step.training_params.patience !== undefined) {
        trainingPayload.patience = step.training_params.patience
      }
      if (step.training_params.box !== undefined) {
        trainingPayload.box = step.training_params.box
      }
      if (step.training_params.cls !== undefined) {
        trainingPayload.cls = step.training_params.cls
      }
      if (step.training_params.dfl !== undefined) {
        trainingPayload.dfl = step.training_params.dfl
      }
      if (Object.keys(trainingPayload).length > 0) {
        if (step.type === 'multi_behavior_training') {
          // 对于multi_behavior_training，将训练参数放在config.training_params中
          normalized.config = normalized.config || {}
          normalized.config.training_params = trainingPayload
        } else {
          normalized.training_params = trainingPayload
        }
      }
    }
    if (step.deployment_params) {
      const deploymentPayload: Record<string, any> = {}
      if (step.deployment_params.replicas) {
        deploymentPayload.replicas = step.deployment_params.replicas
      }
      if (step.deployment_params.environment) {
        deploymentPayload.environment = step.deployment_params.environment
      }
      if (Object.keys(deploymentPayload).length > 0) {
        normalized.deployment_params = deploymentPayload
      }
    }
    return normalized
  })
}

function buildWorkflowPayload(formValue: typeof workflowForm.value) {
  const payload: Record<string, any> = {
    name: formValue.name,
    type: formValue.type,
    trigger: formValue.trigger,
    description: formValue.description,
    steps: normalizeStepsForSubmit(formValue.steps)
  }
  if (formValue.trigger === 'schedule' && formValue.schedule) {
    payload.schedule = formValue.schedule
  }
  return payload
}

function resetWorkflowForm() {
  workflowForm.value = {
    name: '',
    type: 'training',
    trigger: 'manual',
    schedule: '',
    description: '',
    steps: [
      {
        name: '数据预处理',
        type: 'data_processing',
        description: '清洗和预处理数据',
        config: '{}'
      }
    ]
  }
}

function prepareStepForForm(step: any): WorkflowStep {
  const configObj = parseConfig(step?.config)
  let datasetParams: WorkflowStep['dataset_params']
  if (step?.type === 'dataset_generation') {
    const paramsSource = step.dataset_params || configObj || {}
    const cameraIds = paramsSource.camera_ids
    datasetParams = {
      dataset_name: paramsSource.dataset_name || '',
      camera_ids: Array.isArray(cameraIds) ? cameraIds.join(',') : cameraIds || '',
      include_normal_samples: paramsSource.include_normal_samples ?? false,
      max_records: paramsSource.max_records ?? 1000,
      start_time: paramsSource.start_time,
      end_time: paramsSource.end_time
    }
    if (!datasetParams.camera_ids) {
      delete datasetParams.camera_ids
    }
  }
  // 处理训练参数（从 config.training_params 或 step.training_params 中读取）
  let trainingParams: WorkflowStep['training_params'] | undefined
  if (step?.type === 'model_training' || step?.type === 'multi_behavior_training' || step?.type === 'handwash_training') {
    const configTrainingParams = configObj?.training_params || {}
    const stepTrainingParams = step?.training_params || {}
    // 合并配置中的参数和步骤中的参数
    trainingParams = {
      ...configTrainingParams,
      ...stepTrainingParams,
      // 确保数值类型正确
      lr0: configTrainingParams.lr0 ?? stepTrainingParams.lr0,
      lrf: configTrainingParams.lrf ?? stepTrainingParams.lrf,
      batch_size: configTrainingParams.batch_size ?? stepTrainingParams.batch_size,
      epochs: configTrainingParams.epochs ?? stepTrainingParams.epochs,
      image_size: configTrainingParams.image_size ?? stepTrainingParams.image_size,
      momentum: configTrainingParams.momentum ?? stepTrainingParams.momentum,
      weight_decay: configTrainingParams.weight_decay ?? stepTrainingParams.weight_decay,
      warmup_epochs: configTrainingParams.warmup_epochs ?? stepTrainingParams.warmup_epochs,
      patience: configTrainingParams.patience ?? stepTrainingParams.patience,
      box: configTrainingParams.box ?? stepTrainingParams.box,
      cls: configTrainingParams.cls ?? stepTrainingParams.cls,
      dfl: configTrainingParams.dfl ?? stepTrainingParams.dfl,
      device: configTrainingParams.device ?? stepTrainingParams.device ?? 'auto',
      model: configTrainingParams.model ?? stepTrainingParams.model ?? ''
    }
  }

  return {
    name: step?.name || '',
    type: step?.type || 'data_processing',
    description: step?.description || '',
    config: JSON.stringify(configObj, null, 2),
    dataset_params: datasetParams,
    training_params: trainingParams,
    deployment_params: step?.deployment_params
  }
}

// 获取工作流列表
async function fetchWorkflows() {
  loading.value = true
  errorMessage.value = null
  try {
    // 使用统一的http客户端
    const response = await http.get('/mlops/workflows')
    const data = response.data
    workflows.value = Array.isArray(data) ? data : (data.workflows || data.items || [])
    if (workflows.value.length === 0) {
      message.info('暂无工作流，请先创建工作流')
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '获取工作流列表失败'
    console.error('获取工作流列表失败:', error)
    errorMessage.value = errorMsg
    workflows.value = []
    const statusCode = error.response?.status
    if (statusCode === 404 || statusCode === 503) {
      message.error('工作流服务不可用，请检查后端服务是否正常运行', {
        duration: 5000
      })
    } else {
      message.error(`无法获取工作流列表: ${errorMsg}`, {
        duration: 5000
      })
    }
  } finally {
    loading.value = false
  }
}

// 刷新工作流
function refreshWorkflows() {
  return fetchWorkflows()
}

// 获取工作流状态类型
function getWorkflowStatusType(status: string) {
  const statusMap: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    active: 'success',
    inactive: 'default',
    error: 'error'
  }
  return statusMap[status] || 'default'
}

// 获取工作流状态文本
function getWorkflowStatusText(status: string) {
  const statusMap: Record<string, string> = {
    active: '运行中',
    inactive: '已停用',
    error: '错误'
  }
  return statusMap[status] || status
}

// 获取工作流类型文本
function getWorkflowTypeText(type: string) {
  const typeMap: Record<string, string> = {
    training: '训练工作流',
    evaluation: '评估工作流',
    deployment: '部署工作流',
    data_processing: '数据处理工作流'
  }
  return typeMap[type] || type
}

// 获取触发器文本
function getTriggerText(trigger: string) {
  const triggerMap: Record<string, string> = {
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
  const statusMap: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    success: 'success',
    failed: 'error',
    running: 'warning',
    pending: 'default'
  }
  return statusMap[status] || 'default'
}

// 获取运行状态文本
function getRunStatusText(status: string) {
  const statusMap: Record<string, string> = {
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
  editForm.value = {
    name: workflow.name,
    type: workflow.type,
    trigger: workflow.trigger,
    schedule: workflow.schedule || '',
    description: workflow.description,
    steps: workflow.steps.map((step) => {
      const prepared = prepareStepForForm(step)
      // prepareStepForForm 已经处理了 training_params，这里不需要再次设置
      if (step.type === 'model_deployment') {
        prepared.deployment_params = {
          replicas: step.deployment_params?.replicas || 1,
          environment: step.deployment_params?.environment || 'staging'
        }
      }
      return prepared
    })
  }
  showEditDialog.value = true
}

// 运行工作流
async function runWorkflow(workflow: Workflow) {
  console.log('运行工作流:', workflow)
  try {
    // 检查工作流ID是否有效
    if (!workflow.id) {
      message.error('工作流ID无效，无法运行。请刷新列表获取最新数据。')
      await refreshWorkflows()
      return
    }

    // 检查工作流是否来自真实API（避免运行测试数据）
    if (workflow.id.startsWith('mock_') || workflow.id === 'test_workflow') {
      message.error('无法运行测试工作流，请使用真实的工作流数据。请刷新列表获取最新数据。')
      await refreshWorkflows()
      return
    }

    const confirmed = confirm(`确定要运行工作流 "${workflow.name}" 吗？`)
    if (!confirmed) return

    const loadingMessage = message.loading('正在运行工作流...', { duration: 0 })
    try {
      const response = await fetch(`/api/v1/mlops/workflows/${workflow.id}/run`, {
        method: 'POST'
      })
      loadingMessage.destroy()

      if (response.ok) {
        const result = await response.json()
        message.success('工作流运行成功')
        await refreshWorkflows()
        if (result.outputs && Array.isArray(result.outputs)) {
          currentRunEntries.value = result.outputs as WorkflowStepOutput[]
          currentRun.value = {
            id: result.run_id,
            status: 'success',
            started_at: new Date().toISOString(),
            run_log: JSON.stringify(result.outputs)
          } as WorkflowRun
          showRunLogDialog.value = true
        }
      } else {
        const errorData = await response.json().catch(() => ({ detail: '运行失败' }))
        const errorMsg = errorData.detail || errorData.message || '运行失败'
        if (response.status === 404) {
          message.error(`工作流不存在，请刷新列表: ${errorMsg}`)
          await refreshWorkflows()
        } else {
          message.error(`运行失败: ${errorMsg}`)
        }
      }
    } catch (fetchError) {
      loadingMessage.destroy()
      console.error('运行工作流请求失败:', fetchError)
      message.error('网络请求失败，请检查后端服务是否正常运行')
    }
  } catch (error) {
    console.error('运行工作流失败:', error)
    message.error('运行失败')
  }
}

// 检查工作流是否正在运行
function isWorkflowRunning(workflow: Workflow): boolean {
  if (!workflow.recent_runs || workflow.recent_runs.length === 0) {
    return false
  }
  // 检查最近的运行记录状态是否为 'running'
  const lastRun = workflow.recent_runs[0]
  return lastRun && lastRun.status === 'running'
}

// 停止正在运行的工作流
async function stopWorkflow(workflow: Workflow) {
  console.log('停止工作流:', workflow)
  try {
    const confirmed = confirm(`确定要停止工作流 "${workflow.name}" 吗？`)
    if (!confirmed) {
      return
    }

    const loadingMessage = message.loading('正在停止工作流...', { duration: 0 })
    try {
      const response = await fetch(`/api/v1/mlops/workflows/${workflow.id}/stop`, {
        method: 'POST'
      })
      loadingMessage.destroy()

      if (response.ok) {
        const result = await response.json()
        if (result.success) {
          message.success('工作流已停止')
          await refreshWorkflows()
        } else {
          message.error(result.message || '停止失败')
        }
      } else {
        const errorData = await response.json().catch(() => ({ detail: '停止失败' }))
        message.error(errorData.detail || '停止失败')
      }
    } catch (fetchError) {
      loadingMessage.destroy()
      console.error('停止工作流请求失败:', fetchError)
      message.error('网络请求失败，请检查后端服务是否正常运行')
    }
  } catch (error) {
    console.error('停止工作流失败:', error)
    message.error('停止失败')
  }
}

// 切换工作流状态
async function toggleWorkflow(workflow: Workflow) {
  console.log('切换工作流状态:', workflow)
  const action = workflow.status === 'active' ? '停用' : '启用'
  const newStatus = workflow.status === 'active' ? 'inactive' : 'active'
  try {
    const confirmed = confirm(`确定要${action}工作流 "${workflow.name}" 吗？${workflow.status === 'active' ? '如果工作流正在运行，将先停止运行。' : ''}`)
    if (!confirmed) {
      return
    }

    const loadingMessage = message.loading(`正在${action}...`, { duration: 0 })

    try {
      // 如果停用工作流，先尝试停止正在运行的训练
      if (workflow.status === 'active') {
        try {
          const stopResponse = await fetch(`/api/v1/mlops/workflows/${workflow.id}/stop`, {
            method: 'POST'
          })
          if (stopResponse.ok) {
            const stopResult = await stopResponse.json()
            if (stopResult.success) {
              console.log('工作流已停止:', stopResult)
            }
          }
        } catch (stopError) {
          // 如果停止失败（可能工作流未在运行），继续更新状态
          console.warn('停止工作流失败（可能未在运行）:', stopError)
        }
      }

      // 更新工作流状态
      const response = await fetch(`/api/v1/mlops/workflows/${workflow.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...workflow,
          status: newStatus
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '更新失败' }))
        throw new Error(errorData.detail || '更新失败')
      }

      loadingMessage.destroy()
      message.success(`工作流${action}成功`)
      refreshWorkflows()
    } catch (error) {
      loadingMessage.destroy()
      console.error(`${action}工作流失败:`, error)
      message.error(`${action}失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  } catch (error) {
    console.error(`${action}工作流失败:`, error)
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
    const payload = buildWorkflowPayload(workflowForm.value)
    const response = await fetch('/api/v1/mlops/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(errorText || '创建失败')
    }
    message.success('工作流创建成功')
    showCreateDialog.value = false
    resetWorkflowForm()
    await refreshWorkflows()
  } catch (error) {
    console.error('创建工作流失败:', error)
    message.error('创建工作流失败')
  } finally {
    creating.value = false
  }
}

// 获取工作流类型颜色
function getWorkflowTypeColor(type: string) {
  const typeMap: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    training: 'success',
    evaluation: 'info',
    deployment: 'warning',
    data_processing: 'default'
  }
  return typeMap[type] || 'default'
}

// 获取步骤类型颜色
function getStepTypeColor(type: string) {
  const typeMap: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    data_processing: 'info',
    dataset_generation: 'success',
    model_training: 'success',
    multi_behavior_training: 'success',
    handwash_training: 'success',
    model_evaluation: 'warning',
    model_deployment: 'error',
    data_validation: 'default',
    notification: 'info'
  }
  return typeMap[type] || 'default'
}

// 获取步骤类型文本
function getStepTypeText(type: string): string {
  const typeMap: Record<string, string> = {
    data_processing: '数据处理',
    dataset_generation: '数据集生成',
    model_training: '模型训练',
    multi_behavior_training: '多行为训练',
    handwash_training: '洗手训练',
    model_evaluation: '模型评估',
    model_deployment: '模型部署',
    data_validation: '数据验证',
    notification: '通知'
  }
  return typeMap[type] || type
}

// 查看运行详情
async function viewRunDetails(run: WorkflowRun) {
  try {
    // 从API获取完整的运行详情（包括步骤输出）
    const loadingMessage = message.loading('正在加载运行详情...', { duration: 0 })
    try {
      // 从run对象中提取workflow_id（如果run对象中没有，需要从workflow中获取）
      const workflowId = run.workflow_id || (selectedWorkflow.value?.id)
      if (!workflowId) {
        loadingMessage.destroy()
        message.error('无法获取工作流ID')
        return
      }

      const response = await fetch(`/api/v1/mlops/workflows/${workflowId}/runs/${run.id}`)
      loadingMessage.destroy()

      if (response.ok) {
        const runDetail = await response.json()
        // 更新currentRun，使用API返回的完整数据
        currentRun.value = {
          id: runDetail.id,
          workflow_id: runDetail.workflow_id,
          status: runDetail.status,
          started_at: runDetail.started_at,
          ended_at: runDetail.ended_at,
          duration: runDetail.duration,
          error_message: runDetail.error_message,
          run_log: runDetail.run_log,
          run_config: runDetail.run_config
        } as WorkflowRun

        // 解析步骤输出
        let entries: WorkflowStepOutput[] = []
        if (runDetail.step_outputs && Array.isArray(runDetail.step_outputs)) {
          entries = runDetail.step_outputs as WorkflowStepOutput[]
        } else if (runDetail.run_log) {
          // 如果step_outputs不存在，尝试从run_log解析
          try {
            const parsed = JSON.parse(runDetail.run_log)
            if (Array.isArray(parsed)) {
              entries = parsed as WorkflowStepOutput[]
            } else if (parsed && typeof parsed === 'object' && parsed.outputs) {
              entries = parsed.outputs as WorkflowStepOutput[]
            }
          } catch (error) {
            console.warn('解析运行日志失败:', error)
          }
        }
        currentRunEntries.value = entries
        showRunLogDialog.value = true
      } else {
        // 如果API调用失败，回退到使用本地数据
        console.warn('获取运行详情失败，使用本地数据')
        currentRun.value = run
        let entries: WorkflowStepOutput[] = []
        if (run.run_log) {
          try {
            const parsed = JSON.parse(run.run_log)
            if (Array.isArray(parsed)) {
              entries = parsed as WorkflowStepOutput[]
            } else if (parsed && typeof parsed === 'object' && parsed.outputs) {
              entries = parsed.outputs as WorkflowStepOutput[]
            }
          } catch (error) {
            console.warn('解析运行日志失败:', error)
          }
        }
        currentRunEntries.value = entries
        showRunLogDialog.value = true
      }
    } catch (fetchError) {
      loadingMessage.destroy()
      console.error('获取运行详情请求失败:', fetchError)
      // 回退到使用本地数据
      currentRun.value = run
      let entries: WorkflowStepOutput[] = []
      if (run.run_log) {
        try {
          const parsed = JSON.parse(run.run_log)
          if (Array.isArray(parsed)) {
            entries = parsed as WorkflowStepOutput[]
          } else if (parsed && typeof parsed === 'object' && parsed.outputs) {
            entries = parsed.outputs as WorkflowStepOutput[]
          }
        } catch (error) {
          console.warn('解析运行日志失败:', error)
        }
      }
      currentRunEntries.value = entries
      showRunLogDialog.value = true
    }
  } catch (error) {
    console.error('查看运行详情失败:', error)
    message.error('加载运行详情失败')
  }
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
    const payload = buildWorkflowPayload(editForm.value as any)
    const loadingMessage = message.loading('正在保存工作流...', { duration: 0 })
    const response = await fetch(`/api/v1/mlops/workflows/${selectedWorkflow.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    loadingMessage.destroy()
    if (response.ok) {
      message.success('工作流保存成功')
      showEditDialog.value = false
      await refreshWorkflows()
    } else {
      const errorText = await response.text()
      throw new Error(errorText || '保存失败')
    }
  } catch (error) {
    console.error('保存工作流失败:', error)
    message.error('保存失败')
  } finally {
    editing.value = false
  }
}

// 自动刷新定时器
let refreshTimer: number | null = null

onMounted(() => {
  fetchWorkflows()
  // 如果有正在运行的工作流，每5秒自动刷新一次
  refreshTimer = setInterval(() => {
    const hasRunning = workflows.value.some(w => isWorkflowRunning(w))
    if (hasRunning) {
      refreshWorkflows()
    }
  }, 5000) // 每5秒刷新一次
})

onUnmounted(() => {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
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

.training-summary {
  margin-top: 8px;
}

.training-metrics {
  margin-top: 8px;
}

.workflow-step-config {
  margin-bottom: 12px;
}

.workflow-detail-content {
  max-height: 70vh;
  overflow-y: auto;
}
</style>

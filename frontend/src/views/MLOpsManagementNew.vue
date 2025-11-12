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
        <n-tab-pane name="model-registry" tab="模型管理">
          <ModelRegistry ref="modelRegistryRef" />
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
import { ref } from 'vue'
import { NButton, NSpace, NIcon, NTabs, NTabPane } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { PageHeader } from '@/components/common'
import DatasetManager from '@/components/MLOps/DatasetManager.vue'
import ModelDeployment from '@/components/MLOps/ModelDeployment.vue'
import WorkflowManager from '@/components/MLOps/WorkflowManager.vue'
import ModelRegistry from '@/components/MLOps/ModelRegistry.vue'

const loading = ref(false)
const modelRegistryRef = ref<InstanceType<typeof ModelRegistry> | null>(null)

async function refreshData() {
  loading.value = true
  try {
    await modelRegistryRef.value?.refresh()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mlops-management-page {
  padding: 24px;
}

.mlops-content {
  margin-top: 24px;
}

</style>

<template>
  <div class="home-page">
    <!-- 页面头部 -->
    <PageHeader
      title="智能监控系统"
      subtitle="欢迎使用 PYT 智能监控管理平台"
    >
      <template #actions>
        <n-space>
          <n-button type="primary" @click="onCheckHealth" :loading="systemStore.loading">
            <template #icon>
              <n-icon><HeartOutline /></n-icon>
            </template>
            健康检查
          </n-button>
          <n-button @click="onGetSystemInfo" :loading="systemStore.loading">
            <template #icon>
              <n-icon><InformationCircleOutline /></n-icon>
            </template>
            系统信息
          </n-button>
        </n-space>
      </template>
    </PageHeader>

    <!-- 主要内容区 -->
    <div class="home-content">
      <!-- 智能检测面板 -->
      <IntelligentDetectionPanel />

      <!-- 状态卡片区 -->
      <div class="status-cards">
        <DataCard
          title="系统健康状态"
          :loading="systemStore.loading"
          class="status-card"
        >
          <div class="status-content">
            <StatusIndicator
              v-if="systemStore.health"
              :status="'success'"
              :text="systemStore.health"
              size="large"
            />
            <StatusIndicator
              v-else-if="systemStore.error"
              :status="'error'"
              :text="systemStore.error"
              size="large"
            />
            <StatusIndicator
              v-else
              :status="'info'"
              text="点击检查系统健康状态"
              size="large"
            />
          </div>
        </DataCard>

        <DataCard
          title="系统信息"
          :loading="systemStore.loading"
          class="status-card"
        >
          <div class="status-content">
            <StatusIndicator
              v-if="systemStore.hasSystemInfo"
              :status="'success'"
              text="系统信息已获取"
              size="large"
            />
            <StatusIndicator
              v-else-if="systemStore.error"
              :status="'error'"
              :text="systemStore.error"
              size="large"
            />
            <StatusIndicator
              v-else
              :status="'info'"
              text="点击获取系统信息"
              size="large"
            />
          </div>
        </DataCard>
      </div>

      <!-- 系统信息详情 -->
      <n-card
        v-if="systemStore.systemInfo"
        title="系统详细信息"
        class="system-info-card"
        :bordered="false"
      >
        <template #header-extra>
          <n-tag type="success" size="small">
            <template #icon>
              <n-icon><CheckmarkCircleOutline /></n-icon>
            </template>
            已连接
          </n-tag>
        </template>

        <n-scrollbar style="max-height: 400px;">
          <pre class="system-info-content">{{ JSON.stringify(systemStore.systemInfo, null, 2) }}</pre>
        </n-scrollbar>
      </n-card>

      <!-- 快速操作区 -->
      <n-card title="快速操作" class="quick-actions-card" :bordered="false">
        <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen">
          <n-grid-item>
            <n-button
              block
              size="large"
              @click="$router.push('/camera-config')"
              class="action-button"
            >
              <template #icon>
                <n-icon><CameraOutline /></n-icon>
              </template>
              摄像头配置
            </n-button>
          </n-grid-item>
          <n-grid-item>
            <n-button
              block
              size="large"
              @click="$router.push('/region-config')"
              class="action-button"
            >
              <template #icon>
                <n-icon><LocationOutline /></n-icon>
              </template>
              区域配置
            </n-button>
          </n-grid-item>
          <n-grid-item>
            <n-button
              block
              size="large"
              @click="$router.push('/statistics')"
              class="action-button"
            >
              <template #icon>
                <n-icon><StatsChartOutline /></n-icon>
              </template>
              统计分析
            </n-button>
          </n-grid-item>
          <n-grid-item>
            <n-button
              block
              size="large"
              @click="$router.push('/system-info')"
              class="action-button"
            >
              <template #icon>
                <n-icon><SettingsOutline /></n-icon>
              </template>
              系统信息
            </n-button>
          </n-grid-item>
        </n-grid>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton, NTag, NCard, NSpace, NIcon, NGrid, NGridItem, NScrollbar } from 'naive-ui'
import {
  HeartOutline,
  InformationCircleOutline,
  CheckmarkCircleOutline,
  CameraOutline,
  LocationOutline,
  StatsChartOutline,
  SettingsOutline
} from '@vicons/ionicons5'
import { PageHeader, DataCard, StatusIndicator } from '@/components/common'
import IntelligentDetectionPanel from '@/components/IntelligentDetectionPanelSimple.vue'
import { useSystemStore } from '@/stores'

const systemStore = useSystemStore()

async function onCheckHealth() {
  try {
    await systemStore.checkHealth()
  } catch (e: any) {
    console.error('健康检查失败：', e.message)
  }
}

async function onGetSystemInfo() {
  try {
    await systemStore.fetchSystemInfo()
  } catch (e: any) {
    console.error('获取系统信息失败：', e.message)
  }
}
</script>

<style scoped>
.home-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-large);
}

.home-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-large);
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-large);
}

.status-card {
  min-height: 120px;
}

.status-content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
}

.system-info-card {
  flex: 1;
}

.system-info-content {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-small);
  line-height: 1.5;
  margin: 0;
  color: var(--text-color);
  background: var(--code-color);
  padding: var(--space-medium);
  border-radius: var(--border-radius-medium);
}

.quick-actions-card {
  margin-top: auto;
}

.action-button {
  height: 60px;
  font-size: var(--font-size-medium);
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .status-cards {
    grid-template-columns: 1fr;
  }

  .action-button {
    height: 50px;
    font-size: var(--font-size-small);
  }
}
</style>

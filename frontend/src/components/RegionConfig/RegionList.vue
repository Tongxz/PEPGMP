<template>
  <div class="region-list">
    <n-space vertical size="medium">
      <!-- 批量操作 -->
      <div class="batch-actions">
        <n-space>
          <n-dropdown
            :options="batchOptions"
            @select="onBatchAction"
            trigger="click"
          >
            <n-button>
              <template #icon>
                <n-icon><ListOutline /></n-icon>
              </template>
              批量操作
            </n-button>
          </n-dropdown>

          <n-button
            v-if="regions.length > 0"
            type="primary"
            @click="$emit('saveAll')"
            :loading="saving"
          >
            <template #icon>
              <n-icon><SaveOutline /></n-icon>
            </template>
            保存配置
          </n-button>
        </n-space>
      </div>

      <!-- 区域列表 -->
      <n-space vertical size="small">
        <n-card
          v-for="region in regions"
          :key="region.id"
          size="small"
          :bordered="false"
          class="region-card"
          :class="{ 'selected': region.id === selectedRegionId }"
          @click="$emit('selectRegion', region)"
        >
          <template #header>
            <n-space justify="space-between" align="center" style="width: 100%;">
              <n-space align="center">
                <n-icon><LocationOutline /></n-icon>
                <n-text strong>{{ region.name || `区域 ${region.id}` }}</n-text>
                <n-tag
                  v-if="!region.enabled"
                  type="warning"
                  size="small"
                >
                  已禁用
                </n-tag>
              </n-space>

              <n-space align="center" size="small">
                <n-dropdown
                  :options="getRegionActions(region)"
                  @select="(action) => onRegionAction($event, region)"
                  trigger="click"
                  @click.stop
                >
                  <n-button
                    size="small"
                    quaternary
                    circle
                    @click.stop
                  >
                    <template #icon>
                      <n-icon><EllipsisVerticalOutline /></n-icon>
                    </template>
                  </n-button>
                </n-dropdown>
              </n-space>
            </n-space>
          </template>

          <n-space vertical size="small">
            <n-text depth="3">
              类型：{{ getRegionTypeLabel(region.type) }}
            </n-text>
            <n-text v-if="region.description" depth="3">
              {{ region.description }}
            </n-text>
            <n-space size="small" justify="space-between" align="center">
              <n-space size="small">
                <n-tag size="small" type="info">
                  敏感度：{{ ((region.sensitivity ?? 0.8) * 100).toFixed(0) }}%
                </n-tag>
                <n-tag size="small" type="warning">
                  停留：{{ region.minDuration }}s
                </n-tag>
                <n-tag
                  v-if="region.alertEnabled"
                  size="small"
                  :type="getAlertLevelType(region.alertLevel)"
                >
                  {{ getAlertLevelLabel(region.alertLevel) }}
                </n-tag>
              </n-space>

              <!-- 编辑和删除按钮放在右下角，与n-tag水平对齐 -->
              <n-space size="small">
                <n-button
                  size="small"
                  type="primary"
                  quaternary
                  @click.stop="$emit('editRegion', region)"
                >
                  <template #icon>
                    <n-icon><CreateOutline /></n-icon>
                  </template>
                  编辑
                </n-button>

                <n-button
                  size="small"
                  type="error"
                  quaternary
                  @click.stop="handleDeleteRegion(region)"
                >
                  <template #icon>
                    <n-icon><TrashOutline /></n-icon>
                  </template>
                  删除
                </n-button>
              </n-space>
            </n-space>
          </n-space>
        </n-card>

        <!-- 空状态 -->
        <n-empty
          v-if="regions.length === 0"
          description="暂无配置的区域"
          size="medium"
        >
          <template #icon>
            <n-icon size="48" color="#d0d0d0">
              <LayersOutline />
            </n-icon>
          </template>
          <template #extra>
            <n-button
              type="primary"
              @click="$emit('startDrawing')"
              :disabled="!selectedCamera && !backgroundImage"
            >
              绘制第一个区域
            </n-button>
          </template>
        </n-empty>
      </n-space>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { h } from 'vue'

// Icons
import {
  ListOutline,
  SaveOutline,
  LocationOutline,
  EllipsisVerticalOutline,
  CreateOutline,
  TrashOutline,
  LayersOutline,
  CheckmarkCircleOutline,
  CloseOutline,
} from '@vicons/ionicons5'

// Props
interface Props {
  regions: any[]
  selectedRegionId?: string
  selectedCamera?: string
  backgroundImage?: any
  saving: boolean
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  selectRegion: [region: any]
  editRegion: [region: any]
  deleteRegion: [region: any]
  saveAll: []
  startDrawing: []
  batchAction: [action: string]
}>()

// Batch options
const batchOptions = [
  {
    label: '启用所有区域',
    key: 'enable',
    icon: () => h('n-icon', null, { default: () => h(CheckmarkCircleOutline) })
  },
  {
    label: '禁用所有区域',
    key: 'disable',
    icon: () => h('n-icon', null, { default: () => h(CloseOutline) })
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: '删除所有区域',
    key: 'delete',
    icon: () => h('n-icon', null, { default: () => h(TrashOutline) })
  }
]

// Methods
const getRegionActions = (region: any) => [
  {
    label: region.enabled ? '禁用' : '启用',
    key: region.enabled ? 'disable' : 'enable',
    icon: () => h('n-icon', null, {
      default: () => h(region.enabled ? CloseOutline : CheckmarkCircleOutline)
    })
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: '删除',
    key: 'delete',
    icon: () => h('n-icon', null, { default: () => h(TrashOutline) })
  }
]

const getRegionTypeLabel = (type: string) => {
  const typeMap: Record<string, string> = {
    entrance: '入口区域',
    handwash: '洗手区域',
    sanitize: '消毒区域',
    work_area: '工作区域',
    restricted: '限制区域',
    monitoring: '监控区域',
    custom: '自定义区域'
  }
  return typeMap[type] || type
}

const getAlertLevelLabel = (level: string) => {
  const levelMap: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '紧急'
  }
  return levelMap[level] || level
}

const getAlertLevelType = (level: string) => {
  const typeMap: Record<string, string> = {
    low: 'info',
    medium: 'warning',
    high: 'error',
    critical: 'error'
  }
  return typeMap[level] || 'warning'
}

const onRegionAction = (action: string, region: any) => {
  switch (action) {
    case 'enable':
      emit('batchAction', `enable_${region.id}`)
      break
    case 'disable':
      emit('batchAction', `disable_${region.id}`)
      break
    case 'delete':
      emit('deleteRegion', region)
      break
  }
}

const onBatchAction = (action: string) => {
  emit('batchAction', action)
}

const handleDeleteRegion = (region: any) => {
  emit('deleteRegion', region)
}
</script>

<style scoped>
.region-list {
  padding: 16px 12px;
}

.batch-actions {
  margin-bottom: 16px;
}

.region-card {
  cursor: pointer;
  transition: all 0.2s;
}

.region-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.region-card.selected {
  border: 2px solid #1890ff;
  background-color: #f0f8ff;
}
</style>

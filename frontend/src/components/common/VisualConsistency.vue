<template>
  <div class="visual-consistency-wrapper">
    <!-- 品牌标识区域 -->
    <div class="brand-identity" v-if="showBrandElements">
      <div class="brand-logo">
        <slot name="logo">
          <div class="default-logo">
            <n-icon size="32" :component="LogoIcon" />
            <span class="logo-text">{{ brandName }}</span>
          </div>
        </slot>
      </div>

      <div class="brand-tagline" v-if="tagline">
        {{ tagline }}
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="content-area" :class="contentClasses">
      <slot />
    </div>

    <!-- 状态指示器 -->
    <div class="status-indicators" v-if="showStatusIndicators">
      <div
        v-for="status in statusList"
        :key="status.key"
        class="status-item"
        :class="[`status-${status.type}`, { 'status-active': status.active }]"
      >
        <n-icon :component="status.icon" />
        <span class="status-text">{{ status.label }}</span>
        <div class="status-dot" :class="`dot-${status.type}`"></div>
      </div>
    </div>

    <!-- 操作按钮组 -->
    <div class="action-group" v-if="showActions">
      <slot name="actions">
        <n-button-group>
          <n-button
            v-for="action in actions"
            :key="action.key"
            :type="action.type || 'default'"
            :size="action.size || 'medium'"
            :disabled="action.disabled"
            :loading="action.loading"
            @click="handleAction(action)"
          >
            <template #icon v-if="action.icon">
              <n-icon :component="action.icon" />
            </template>
            {{ action.label }}
          </n-button>
        </n-button-group>
      </slot>
    </div>

    <!-- 数据展示卡片 -->
    <div class="data-cards" v-if="showDataCards">
      <div
        v-for="card in dataCards"
        :key="card.key"
        class="data-card"
        :class="[`card-${card.type}`, { 'card-highlighted': card.highlighted }]"
      >
        <div class="card-header">
          <n-icon :component="card.icon" class="card-icon" />
          <span class="card-title">{{ card.title }}</span>
        </div>
        <div class="card-content">
          <div class="card-value">{{ card.value }}</div>
          <div class="card-description">{{ card.description }}</div>
        </div>
        <div class="card-trend" v-if="card.trend">
          <n-icon
            :component="card.trend > 0 ? TrendUpIcon : TrendDownIcon"
            :class="card.trend > 0 ? 'trend-up' : 'trend-down'"
          />
          <span class="trend-value">{{ Math.abs(card.trend) }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon, NButton, NButtonGroup } from 'naive-ui'
import {
  LogoIcon,
  TrendUpIcon,
  TrendDownIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  InfoCircleIcon,
  XCircleIcon
} from '@/components/icons'

interface StatusItem {
  key: string
  type: 'success' | 'warning' | 'error' | 'info'
  label: string
  icon: any
  active?: boolean
}

interface ActionItem {
  key: string
  label: string
  type?: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'default'
  size?: 'tiny' | 'small' | 'medium' | 'large'
  icon?: any
  disabled?: boolean
  loading?: boolean
  handler?: () => void
}

interface DataCard {
  key: string
  type: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'default'
  title: string
  value: string | number
  description?: string
  icon: any
  trend?: number
  highlighted?: boolean
}

interface Props {
  // 品牌元素
  showBrandElements?: boolean
  brandName?: string
  tagline?: string

  // 内容样式
  contentVariant?: 'default' | 'card' | 'panel' | 'section'
  contentSpacing?: 'compact' | 'normal' | 'relaxed'

  // 状态指示器
  showStatusIndicators?: boolean
  statusList?: StatusItem[]

  // 操作按钮
  showActions?: boolean
  actions?: ActionItem[]

  // 数据卡片
  showDataCards?: boolean
  dataCards?: DataCard[]
}

const props = withDefaults(defineProps<Props>(), {
  showBrandElements: false,
  brandName: '系统名称',
  tagline: '',
  contentVariant: 'default',
  contentSpacing: 'normal',
  showStatusIndicators: false,
  statusList: () => [],
  showActions: false,
  actions: () => [],
  showDataCards: false,
  dataCards: () => []
})

const emit = defineEmits<{
  action: [action: ActionItem]
}>()

// 内容区域样式类
const contentClasses = computed(() => [
  `content-${props.contentVariant}`,
  `spacing-${props.contentSpacing}`
])

// 处理操作按钮点击
const handleAction = (action: ActionItem) => {
  if (action.handler) {
    action.handler()
  }
  emit('action', action)
}
</script>

<style scoped>
.visual-consistency-wrapper {
  --local-primary: var(--brand-primary);
  --local-secondary: var(--brand-secondary);
  --local-accent: var(--brand-accent);
  --local-spacing: var(--space-medium);

  display: flex;
  flex-direction: column;
  gap: var(--local-spacing);
  font-family: var(--font-family-primary);
}

/* 品牌标识 */
.brand-identity {
  display: flex;
  align-items: center;
  gap: var(--space-large);
  padding: var(--space-medium);
  border-bottom: 1px solid var(--border-secondary);
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: var(--space-small);
}

.default-logo {
  display: flex;
  align-items: center;
  gap: var(--space-small);
  color: var(--local-primary);
}

.logo-text {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.brand-tagline {
  font-size: var(--font-size-small);
  color: var(--text-secondary);
  font-style: italic;
}

/* 内容区域 */
.content-area {
  flex: 1;
  min-height: 0;
}

.content-default {
  padding: 0;
}

.content-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-large);
  box-shadow: var(--shadow-sm);
}

.content-panel {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--space-medium);
}

.content-section {
  border-left: 4px solid var(--local-primary);
  padding-left: var(--space-large);
}

.spacing-compact {
  --local-spacing: var(--space-small);
}

.spacing-normal {
  --local-spacing: var(--space-medium);
}

.spacing-relaxed {
  --local-spacing: var(--space-large);
}

/* 状态指示器 */
.status-indicators {
  display: flex;
  gap: var(--space-medium);
  padding: var(--space-medium);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-small);
  padding: var(--space-small) var(--space-medium);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  border: 1px solid var(--border-secondary);
  transition: all var(--duration-fast) var(--easing-smooth);
  position: relative;
}

.status-item.status-active {
  border-color: var(--local-primary);
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.status-success { color: var(--success-color); }
.status-warning { color: var(--warning-color); }
.status-error { color: var(--error-color); }
.status-info { color: var(--info-color); }

.status-text {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-medium);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  position: absolute;
  top: -2px;
  right: -2px;
}

.dot-success { background: var(--success-color); }
.dot-warning { background: var(--warning-color); }
.dot-error { background: var(--error-color); }
.dot-info { background: var(--info-color); }

/* 操作按钮组 */
.action-group {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-medium);
  border-top: 1px solid var(--border-secondary);
}

/* 数据卡片 */
.data-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-medium);
  padding: var(--space-medium);
}

.data-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-large);
  transition: all var(--duration-fast) var(--easing-smooth);
  position: relative;
  overflow: hidden;
}

.data-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.data-card.card-highlighted {
  border-color: var(--local-primary);
  box-shadow: var(--shadow-lg);
}

.data-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--border-primary);
  transition: background var(--duration-fast) var(--easing-smooth);
}

.card-primary::before { background: var(--brand-primary); }
.card-success::before { background: var(--success-color); }
.card-warning::before { background: var(--warning-color); }
.card-error::before { background: var(--error-color); }
.card-info::before { background: var(--info-color); }

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-small);
  margin-bottom: var(--space-medium);
}

.card-icon {
  font-size: var(--font-size-large);
  color: var(--text-secondary);
}

.card-title {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.card-content {
  margin-bottom: var(--space-medium);
}

.card-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-tiny);
}

.card-description {
  font-size: var(--font-size-small);
  color: var(--text-secondary);
  line-height: var(--line-height-relaxed);
}

.card-trend {
  display: flex;
  align-items: center;
  gap: var(--space-tiny);
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-medium);
}

.trend-up {
  color: var(--success-color);
}

.trend-down {
  color: var(--error-color);
}

.trend-value {
  color: inherit;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .brand-identity {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-small);
  }

  .status-indicators {
    flex-direction: column;
    gap: var(--space-small);
  }

  .data-cards {
    grid-template-columns: 1fr;
  }

  .action-group {
    justify-content: stretch;
  }

  .action-group :deep(.n-button-group) {
    width: 100%;
  }

  .action-group :deep(.n-button) {
    flex: 1;
  }
}

@media (max-width: 480px) {
  .visual-consistency-wrapper {
    --local-spacing: var(--space-small);
  }

  .content-card,
  .content-panel {
    padding: var(--space-medium);
  }

  .data-card {
    padding: var(--space-medium);
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .data-card,
  .status-item {
    border-width: 2px;
  }

  .status-dot {
    border: 2px solid var(--bg-primary);
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .data-card,
  .status-item {
    transition: none;
  }

  .data-card:hover {
    transform: none;
  }
}
</style>

<template>
  <n-card
    :class="['data-card', `data-card--${size}`, { 'data-card--hoverable': hoverable }]"
    :bordered="bordered"
    :segmented="segmented"
  >
    <!-- 卡片头部 -->
    <template #header>
      <div class="data-card-header">
        <div class="data-card-title">
          <n-icon v-if="icon" :size="iconSize" class="data-card-icon">
            <component :is="icon" />
          </n-icon>
          <span>{{ title }}</span>
        </div>
        <div v-if="$slots.extra" class="data-card-extra">
          <slot name="extra" />
        </div>
      </div>
    </template>

    <!-- 卡片内容 -->
    <div class="data-card-content">
      <!-- 主要数值 -->
      <div v-if="value !== undefined" class="data-card-value">
        <span :class="['value-number', `value-number--${valueType}`]">
          {{ formattedValue }}
        </span>
        <span v-if="unit" class="value-unit">{{ unit }}</span>
      </div>

      <!-- 变化趋势 -->
      <div v-if="trend !== undefined" class="data-card-trend">
        <n-icon
          :size="16"
          :class="['trend-icon', `trend-icon--${trendType}`]"
        >
          <svg v-if="trendType === 'up'" viewBox="0 0 24 24">
            <path fill="currentColor" d="M7 14l5-5 5 5z"/>
          </svg>
          <svg v-else-if="trendType === 'down'" viewBox="0 0 24 24">
            <path fill="currentColor" d="M7 10l5 5 5-5z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24">
            <path fill="currentColor" d="M8 12h8"/>
          </svg>
        </n-icon>
        <span :class="['trend-text', `trend-text--${trendType}`]">
          {{ Math.abs(trend) }}%
        </span>
        <span v-if="trendPeriod" class="trend-period">{{ trendPeriod }}</span>
      </div>

      <!-- 描述信息 -->
      <div v-if="description" class="data-card-description">
        {{ description }}
      </div>

      <!-- 自定义内容 -->
      <div v-if="$slots.default" class="data-card-custom">
        <slot />
      </div>
    </div>

    <!-- 卡片底部 -->
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NIcon } from 'naive-ui'

interface Props {
  title: string
  value?: number | string
  unit?: string
  trend?: number
  trendPeriod?: string
  description?: string
  icon?: any
  size?: 'small' | 'medium' | 'large'
  valueType?: 'default' | 'success' | 'warning' | 'error'
  bordered?: boolean
  segmented?: boolean
  hoverable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  valueType: 'default',
  bordered: true,
  segmented: false,
  hoverable: false
})

// 计算属性
const iconSize = computed(() => {
  const sizeMap = {
    small: 16,
    medium: 20,
    large: 24
  }
  return sizeMap[props.size]
})

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    // 格式化数字，添加千分位分隔符
    return props.value.toLocaleString()
  }
  return props.value
})

const trendType = computed(() => {
  if (props.trend === undefined) return 'flat'
  if (props.trend > 0) return 'up'
  if (props.trend < 0) return 'down'
  return 'flat'
})
</script>

<style scoped>
.data-card {
  transition: all 0.3s ease;
}

.data-card--hoverable:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.data-card--small {
  --card-padding: 16px;
}

.data-card--medium {
  --card-padding: 20px;
}

.data-card--large {
  --card-padding: 24px;
}

.data-card-header {
  display: flex;
  justify-content: space-between; /* 💡 优化：左右分散对齐 */
  align-items: center;
  flex-wrap: wrap; /* 💡 优化：允许换行，确保右侧内容在空间不足时能下移 */
  gap: 12px 0; /* 💡 优化：水平间距 12px，垂直间距 0（换行后上下有间距） */
}

.data-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  flex-shrink: 1; /* 💡 优化：允许收缩 */
  min-width: 0; /* 💡 优化：允许收缩到0 */
  overflow: hidden; /* 💡 优化：标题过长时截断 */
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-card-extra {
  flex-shrink: 0; /* 💡 优化：不收缩 */
  min-width: fit-content; /* 💡 优化：至少适应内容宽度 */
  flex: 0 0 auto; /* 💡 优化：不收缩，保持内容宽度 */
}

.data-card-icon {
  color: var(--n-primary-color);
}

.data-card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.data-card-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.value-number {
  font-size: 28px;
  font-weight: 600;
  line-height: 1;
}

.value-number--default {
  color: var(--n-text-color);
}

.value-number--success {
  color: var(--n-success-color);
}

.value-number--warning {
  color: var(--n-warning-color);
}

.value-number--error {
  color: var(--n-error-color);
}

.value-unit {
  font-size: 14px;
  color: var(--n-text-color-disabled);
  margin-left: 4px;
}

.data-card-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.trend-icon--up,
.trend-text--up {
  color: var(--n-success-color);
}

.trend-icon--down,
.trend-text--down {
  color: var(--n-error-color);
}

.trend-icon--flat,
.trend-text--flat {
  color: var(--n-text-color-disabled);
}

.trend-period {
  color: var(--n-text-color-disabled);
  margin-left: 4px;
}

.data-card-description {
  font-size: 12px;
  color: var(--n-text-color-disabled);
  line-height: 1.4;
}

.data-card-custom {
  margin-top: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .value-number {
    font-size: 24px;
  }

  .data-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>

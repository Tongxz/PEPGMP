<template>
  <div :class="['status-indicator', `status-indicator--${status}`, `status-indicator--${size}`]">
    <!-- 状态图标 -->
    <div class="status-icon">
      <n-icon :size="iconSize">
        <svg v-if="status === 'success'" viewBox="0 0 24 24">
          <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
        <svg v-else-if="status === 'warning'" viewBox="0 0 24 24">
          <path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
        </svg>
        <svg v-else-if="status === 'error'" viewBox="0 0 24 24">
          <path fill="currentColor" d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/>
        </svg>
        <svg v-else-if="status === 'loading'" viewBox="0 0 24 24">
          <path fill="currentColor" d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z">
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 12 12"
              to="360 12 12"
              dur="1s"
              repeatCount="indefinite"
            />
          </path>
        </svg>
        <svg v-else viewBox="0 0 24 24">
          <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h2v2h-2v-2zm0-8h2v6h-2V9z"/>
        </svg>
      </n-icon>
    </div>

    <!-- 状态文本 -->
    <div v-if="showText" class="status-text">
      <div class="status-label">{{ label || statusText }}</div>
      <div v-if="description" class="status-description">{{ description }}</div>
    </div>

    <!-- 脉冲动画（用于加载状态） -->
    <div v-if="status === 'loading'" class="status-pulse"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'

type StatusType = 'success' | 'warning' | 'error' | 'loading' | 'info'
type SizeType = 'small' | 'medium' | 'large'

interface Props {
  status: StatusType
  label?: string
  description?: string
  size?: SizeType
  showText?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  showText: true
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

const statusText = computed(() => {
  const textMap = {
    success: '正常',
    warning: '警告',
    error: '错误',
    loading: '加载中',
    info: '信息'
  }
  return textMap[props.status]
})
</script>

<style scoped>
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.status-indicator--small {
  gap: 6px;
}

.status-indicator--large {
  gap: 12px;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.status-indicator--success .status-icon {
  color: var(--n-success-color);
}

.status-indicator--warning .status-icon {
  color: var(--n-warning-color);
}

.status-indicator--error .status-icon {
  color: var(--n-error-color);
}

.status-indicator--loading .status-icon {
  color: var(--n-primary-color);
}

.status-indicator--info .status-icon {
  color: var(--n-info-color);
}

.status-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--n-text-color);
}

.status-indicator--small .status-label {
  font-size: 12px;
}

.status-indicator--large .status-label {
  font-size: 16px;
}

.status-description {
  font-size: 12px;
  color: var(--n-text-color-disabled);
  line-height: 1.4;
}

.status-indicator--small .status-description {
  font-size: 11px;
}

.status-indicator--large .status-description {
  font-size: 13px;
}

/* 脉冲动画 */
.status-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background-color: var(--n-primary-color);
  opacity: 0.3;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.2);
    opacity: 0.1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.4);
    opacity: 0;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .status-indicator {
    gap: 6px;
  }

  .status-label {
    font-size: 13px;
  }

  .status-description {
    font-size: 11px;
  }
}
</style>

<template>
  <button
    class="glow-button"
    :class="[variant, size, { loading: isLoading, disabled: isDisabled, block, icon: isIconOnly }]"
    :disabled="isDisabled || isLoading"
    @click="handleClick"
  >
    <!-- 涟漪效果 -->
    <span class="button-ripple" v-if="!isLoading"></span>

    <!-- 按钮内容 -->
    <span class="button-content">
      <!-- 图标插槽 -->
      <span class="button-icon" v-if="$slots.icon && !isLoading">
        <slot name="icon"></slot>
      </span>

      <!-- 加载图标 -->
      <span class="button-loading" v-if="isLoading">
        <svg class="loading-spinner" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" />
        </svg>
      </span>

      <!-- 文字内容 -->
      <span class="button-text" v-if="$slots.default && !isIconOnly">
        <slot></slot>
      </span>
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** 变体类型 */
  variant?: 'primary' | 'secondary' | 'tertiary' | 'success' | 'warning' | 'danger' | 'ghost'
  /** 按钮大小 */
  size?: 'small' | 'medium' | 'large'
  /** 是否加载中 */
  loading?: boolean
  /** 是否禁用 */
  disabled?: boolean
  /** 是否为块级按钮 */
  block?: boolean
  /** 是否仅显示图标 */
  iconOnly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'medium',
  loading: false,
  disabled: false,
  block: false,
  iconOnly: false
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const isLoading = computed(() => props.loading)
const isDisabled = computed(() => props.disabled)
const isIconOnly = computed(() => props.iconOnly)

const handleClick = (event: MouseEvent) => {
  if (!isLoading.value && !isDisabled.value) {
    emit('click', event)
  }
}
</script>

<style scoped lang="scss">
.glow-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-small);
  padding: var(--space-medium) var(--space-xl);
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: 2px solid;
  border-radius: var(--radius-medium);
  background: transparent;
  cursor: pointer;
  overflow: hidden;
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;

  &:focus-visible {
    outline: 2px solid var(--color-accent-500);
    outline-offset: 2px;
  }

  // 尺寸变体
  &.small {
    padding: var(--space-small) var(--space-medium);
    font-size: var(--font-size-small);

    &.icon {
      padding: var(--space-small);
      width: 32px;
      height: 32px;
    }
  }

  &.medium {
    padding: var(--space-medium) var(--space-xl);
    font-size: var(--font-size-base);

    &.icon {
      padding: var(--space-medium);
      width: 40px;
      height: 40px;
    }
  }

  &.large {
    padding: var(--space-large) var(--space-xxl);
    font-size: var(--font-size-large);

    &.icon {
      padding: var(--space-large);
      width: 48px;
      height: 48px;
    }
  }

  // 块级按钮
  &.block {
    width: 100%;
  }

  // 颜色变体
  &.primary {
    border-color: var(--color-accent-500);
    color: var(--color-accent-400);

    &:hover:not(:disabled) {
      background: var(--color-accent-500);
      color: white;
      box-shadow: var(--shadow-glow-cyan);
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      transform: translateY(0) scale(0.95);
    }
  }

  &.secondary {
    border-color: var(--color-primary-500);
    color: var(--color-primary-400);

    &:hover:not(:disabled) {
      background: var(--color-primary-500);
      color: white;
      box-shadow: var(--shadow-glow-blue);
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      transform: translateY(0) scale(0.95);
    }
  }

  &.tertiary {
    border-color: var(--color-warning-500);
    color: var(--color-warning-400);

    &:hover:not(:disabled) {
      background: var(--color-warning-500);
      color: white;
      box-shadow: var(--shadow-glow-orange);
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      transform: translateY(0) scale(0.95);
    }
  }

  &.success {
    border-color: var(--color-success-500);
    color: var(--color-success-500);

    &:hover:not(:disabled) {
      background: var(--color-success-500);
      color: white;
      box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      transform: translateY(0) scale(0.95);
    }
  }

  &.warning {
    border-color: var(--color-warning-500);
    color: var(--color-warning-500);

    &:hover:not(:disabled) {
      background: var(--color-warning-500);
      color: white;
      box-shadow: var(--shadow-glow-orange);
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      transform: translateY(0) scale(0.95);
    }
  }

  &.danger {
    border-color: var(--color-error-500);
    color: var(--color-error-500);

    &:hover:not(:disabled) {
      background: var(--color-error-500);
      color: white;
      box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      transform: translateY(0) scale(0.95);
    }
  }

  &.ghost {
    border-color: transparent;
    color: var(--color-text-secondary);

    &:hover:not(:disabled) {
      border-color: var(--color-border);
      background: rgba(255, 255, 255, 0.05);
      color: var(--color-text-primary);
    }

    &:active:not(:disabled) {
      transform: scale(0.95);
    }
  }

  // 禁用状态
  &.disabled,
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
  }

  // 加载状态
  &.loading {
    cursor: wait;
    pointer-events: none;
  }
}

// 按钮内容
.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-small);
  position: relative;
  z-index: 1;
}

.button-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2em;
}

.button-text {
  line-height: 1;
}

// 加载动画
.button-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;

  circle {
    stroke-dasharray: 50;
    stroke-dashoffset: 25;
    animation: dash 1.5s ease-in-out infinite;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}

// 涟漪效果
.button-ripple {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.glow-button:active:not(:disabled) .button-ripple {
  animation: ripple 0.6s ease-out;
}

@keyframes ripple {
  to {
    width: 300px;
    height: 300px;
    opacity: 0;
  }
}

// 响应式
@media (max-width: 768px) {
  .glow-button {
    font-size: var(--font-size-small);

    &.small {
      font-size: var(--font-size-tiny);
    }

    &.large {
      font-size: var(--font-size-base);
    }
  }
}
</style>

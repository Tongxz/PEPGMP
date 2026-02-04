<template>
  <div
    class="future-card"
    :class="[variant, { hoverable, bordered, loading: isLoading }]"
    :style="customStyle"
  >
    <!-- 发光效果层 -->
    <div class="card-glow" v-if="glow"></div>

    <!-- 装饰角 -->
    <template v-if="corners">
      <div class="card-corner top-left"></div>
      <div class="card-corner top-right"></div>
      <div class="card-corner bottom-left"></div>
      <div class="card-corner bottom-right"></div>
    </template>

    <!-- 卡片头部 -->
    <div class="card-header" v-if="$slots.header || title">
      <slot name="header">
        <div class="header-content">
          <div class="header-icon" v-if="$slots.icon">
            <slot name="icon"></slot>
          </div>
          <h3 class="header-title">{{ title }}</h3>
          <span class="header-badge mono-text" v-if="badge">{{ badge }}</span>
        </div>
      </slot>
      <div class="header-extra" v-if="$slots.extra">
        <slot name="extra"></slot>
      </div>
    </div>

    <!-- 卡片内容 -->
    <div class="card-body">
      <slot></slot>
    </div>

    <!-- 卡片底部 -->
    <div class="card-footer" v-if="$slots.footer">
      <slot name="footer"></slot>
    </div>

    <!-- 加载遮罩 -->
    <div class="card-loading" v-if="isLoading">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** 卡片标题 */
  title?: string
  /** 卡片徽章 */
  badge?: string
  /** 变体：cyan(青色) / blue(蓝色) / orange(橙色) / green(绿色) / red(红色) / default(默认) */
  variant?: 'cyan' | 'blue' | 'orange' | 'green' | 'red' | 'default'
  /** 是否显示发光效果 */
  glow?: boolean
  /** 是否显示装饰角 */
  corners?: boolean
  /** 是否可悬停 */
  hoverable?: boolean
  /** 是否显示边框 */
  bordered?: boolean
  /** 是否加载中 */
  loading?: boolean
  /** 自定义样式 */
  customStyle?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  glow: true,
  corners: false,
  hoverable: true,
  bordered: true,
  loading: false
})

const isLoading = computed(() => props.loading)
</script>

<style scoped lang="scss">
.future-card {
  position: relative;
  padding: var(--space-large);
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-large);
  backdrop-filter: blur(10px);
  transition: all var(--duration-normal) var(--ease-out);
  overflow: hidden;

  &.bordered {
    border-width: 1px;
  }

  &.hoverable:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-xl);

    .card-glow {
      opacity: 1;
    }

    .card-corner {
      opacity: 1;
    }

    &.cyan {
      border-color: var(--color-accent-500);
      box-shadow: var(--shadow-xl), var(--shadow-glow-cyan);
    }

    &.blue {
      border-color: var(--color-primary-500);
      box-shadow: var(--shadow-xl), var(--shadow-glow-blue);
    }

    &.orange {
      border-color: var(--color-warning-500);
      box-shadow: var(--shadow-xl), var(--shadow-glow-orange);
    }

    &.green {
      border-color: var(--color-success-500);
      box-shadow: var(--shadow-xl), 0 0 20px rgba(16, 185, 129, 0.3);
    }

    &.red {
      border-color: var(--color-error-500);
      box-shadow: var(--shadow-xl), 0 0 20px rgba(239, 68, 68, 0.3);
    }
  }

  &.loading {
    pointer-events: none;
    opacity: 0.6;
  }
}

// 发光效果层
.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    circle,
    rgba(6, 182, 212, 0.1) 0%,
    transparent 70%
  );
  opacity: 0;
  transition: opacity var(--duration-slow) var(--ease-out);
  pointer-events: none;
}

// 装饰角
.card-corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-accent-500);
  opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-out);
  pointer-events: none;

  &.top-left {
    top: 0;
    left: 0;
    border-right: none;
    border-bottom: none;
  }

  &.top-right {
    top: 0;
    right: 0;
    border-left: none;
    border-bottom: none;
  }

  &.bottom-left {
    bottom: 0;
    left: 0;
    border-right: none;
    border-top: none;
  }

  &.bottom-right {
    bottom: 0;
    right: 0;
    border-left: none;
    border-top: none;
  }
}

// 卡片头部
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-large);
  padding-bottom: var(--space-medium);
  border-bottom: 1px solid var(--color-border);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--space-medium);
  flex: 1;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.05em;
  margin: 0;
}

.header-badge {
  padding: var(--space-tiny) var(--space-small);
  font-size: var(--font-size-tiny);
  background: rgba(6, 182, 212, 0.2);
  border: 1px solid var(--color-accent-500);
  border-radius: var(--radius-small);
  color: var(--color-accent-400);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.header-extra {
  display: flex;
  align-items: center;
  gap: var(--space-small);
}

// 卡片内容
.card-body {
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

// 卡片底部
.card-footer {
  margin-top: var(--space-large);
  padding-top: var(--space-medium);
  border-top: 1px solid var(--color-border);
}

// 加载状态
.card-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(6, 182, 212, 0.2);
  border-top-color: var(--color-accent-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

// 响应式
@media (max-width: 768px) {
  .future-card {
    padding: var(--space-medium);
  }

  .header-title {
    font-size: var(--font-size-large);
  }
}
</style>

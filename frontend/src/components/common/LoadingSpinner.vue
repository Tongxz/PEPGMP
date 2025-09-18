<template>
  <div
    :class="[
      'loading-spinner',
      `loading-spinner--${size}`,
      `loading-spinner--${type}`,
      { 'loading-spinner--overlay': overlay }
    ]"
  >
    <div v-if="overlay" class="loading-spinner__backdrop" />

    <div class="loading-spinner__container">
      <!-- 旋转圆环 -->
      <div v-if="type === 'ring'" class="loading-spinner__ring">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>

      <!-- 脉冲点 -->
      <div v-else-if="type === 'pulse'" class="loading-spinner__pulse">
        <div></div>
        <div></div>
        <div></div>
      </div>

      <!-- 波浪 -->
      <div v-else-if="type === 'wave'" class="loading-spinner__wave">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>

      <!-- 默认旋转器 -->
      <div v-else class="loading-spinner__default">
        <svg viewBox="0 0 50 50">
          <circle
            cx="25"
            cy="25"
            r="20"
            fill="none"
            stroke="currentColor"
            stroke-width="4"
            stroke-linecap="round"
            stroke-dasharray="31.416"
            stroke-dashoffset="31.416"
          />
        </svg>
      </div>

      <!-- 加载文本 -->
      <div v-if="text" class="loading-spinner__text">
        {{ text }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface LoadingSpinnerProps {
  // 尺寸
  size?: 'small' | 'medium' | 'large'
  // 类型
  type?: 'default' | 'ring' | 'pulse' | 'wave'
  // 是否显示遮罩
  overlay?: boolean
  // 加载文本
  text?: string
}

withDefaults(defineProps<LoadingSpinnerProps>(), {
  size: 'medium',
  type: 'default',
  overlay: false
})
</script>

<style scoped>
.loading-spinner {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner--overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-loading);
}

.loading-spinner__backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-overlay);
  backdrop-filter: blur(2px);
}

.loading-spinner__container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  z-index: 1;
}

/* 默认旋转器 */
.loading-spinner__default {
  animation: spin 1s linear infinite;
}

.loading-spinner__default svg {
  width: 100%;
  height: 100%;
}

.loading-spinner__default circle {
  animation: dash 1.5s ease-in-out infinite;
}

/* 旋转圆环 */
.loading-spinner__ring {
  position: relative;
}

.loading-spinner__ring div {
  position: absolute;
  border: 2px solid var(--color-primary);
  border-radius: 50%;
  border-color: var(--color-primary) transparent transparent transparent;
  animation: ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
}

.loading-spinner__ring div:nth-child(1) { animation-delay: -0.45s; }
.loading-spinner__ring div:nth-child(2) { animation-delay: -0.3s; }
.loading-spinner__ring div:nth-child(3) { animation-delay: -0.15s; }

/* 脉冲点 */
.loading-spinner__pulse {
  display: flex;
  gap: 4px;
}

.loading-spinner__pulse div {
  background: var(--color-primary);
  border-radius: 50%;
  animation: pulse 1.4s ease-in-out infinite both;
}

.loading-spinner__pulse div:nth-child(1) { animation-delay: -0.32s; }
.loading-spinner__pulse div:nth-child(2) { animation-delay: -0.16s; }

/* 波浪 */
.loading-spinner__wave {
  display: flex;
  gap: 2px;
  align-items: flex-end;
}

.loading-spinner__wave div {
  background: var(--color-primary);
  animation: wave 1.2s ease-in-out infinite;
}

.loading-spinner__wave div:nth-child(1) { animation-delay: -1.2s; }
.loading-spinner__wave div:nth-child(2) { animation-delay: -1.1s; }
.loading-spinner__wave div:nth-child(3) { animation-delay: -1.0s; }
.loading-spinner__wave div:nth-child(4) { animation-delay: -0.9s; }
.loading-spinner__wave div:nth-child(5) { animation-delay: -0.8s; }

/* 加载文本 */
.loading-spinner__text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
  white-space: nowrap;
}

/* 尺寸变体 */
.loading-spinner--small .loading-spinner__default {
  width: 20px;
  height: 20px;
}

.loading-spinner--small .loading-spinner__ring {
  width: 20px;
  height: 20px;
}

.loading-spinner--small .loading-spinner__ring div {
  width: 16px;
  height: 16px;
  margin: 2px;
}

.loading-spinner--small .loading-spinner__pulse div {
  width: 4px;
  height: 4px;
}

.loading-spinner--small .loading-spinner__wave div {
  width: 2px;
  height: 12px;
}

.loading-spinner--medium .loading-spinner__default {
  width: 32px;
  height: 32px;
}

.loading-spinner--medium .loading-spinner__ring {
  width: 32px;
  height: 32px;
}

.loading-spinner--medium .loading-spinner__ring div {
  width: 26px;
  height: 26px;
  margin: 3px;
}

.loading-spinner--medium .loading-spinner__pulse div {
  width: 6px;
  height: 6px;
}

.loading-spinner--medium .loading-spinner__wave div {
  width: 3px;
  height: 18px;
}

.loading-spinner--large .loading-spinner__default {
  width: 48px;
  height: 48px;
}

.loading-spinner--large .loading-spinner__ring {
  width: 48px;
  height: 48px;
}

.loading-spinner--large .loading-spinner__ring div {
  width: 40px;
  height: 40px;
  margin: 4px;
}

.loading-spinner--large .loading-spinner__pulse div {
  width: 8px;
  height: 8px;
}

.loading-spinner--large .loading-spinner__wave div {
  width: 4px;
  height: 24px;
}

/* 动画定义 */
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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

@keyframes ring {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 1;
  }
  40% {
    transform: scale(1);
    opacity: 0.5;
  }
}

@keyframes wave {
  0%, 40%, 100% {
    transform: scaleY(0.4);
  }
  20% {
    transform: scaleY(1);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .loading-spinner--overlay .loading-spinner__container {
    padding: var(--spacing-lg);
  }

  .loading-spinner__text {
    font-size: var(--font-size-xs);
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .loading-spinner__default,
  .loading-spinner__ring div,
  .loading-spinner__pulse div,
  .loading-spinner__wave div {
    animation-duration: 2s;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .loading-spinner__default circle,
  .loading-spinner__ring div,
  .loading-spinner__pulse div,
  .loading-spinner__wave div {
    border-color: currentColor;
    background: currentColor;
  }
}
</style>

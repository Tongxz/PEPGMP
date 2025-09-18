<template>
  <div class="error-boundary">
    <slot v-if="!hasError" />

    <div v-else class="error-boundary__content">
      <div class="error-boundary__icon">
        <n-icon size="48" color="var(--color-error)">
          <ExclamationTriangleIcon />
        </n-icon>
      </div>

      <div class="error-boundary__message">
        <h3 class="error-boundary__title">
          {{ title || '出现了一些问题' }}
        </h3>

        <p class="error-boundary__description">
          {{ description || '页面遇到了意外错误，请尝试刷新页面或联系技术支持。' }}
        </p>

        <div v-if="showDetails && errorDetails" class="error-boundary__details">
          <n-collapse>
            <n-collapse-item title="错误详情" name="details">
              <pre class="error-boundary__stack">{{ errorDetails }}</pre>
            </n-collapse-item>
          </n-collapse>
        </div>
      </div>

      <div class="error-boundary__actions">
        <n-space>
          <n-button type="primary" @click="handleRetry">
            <template #icon>
              <n-icon><RefreshIcon /></n-icon>
            </template>
            重试
          </n-button>

          <n-button @click="handleReload">
            <template #icon>
              <n-icon><ReloadIcon /></n-icon>
            </template>
            刷新页面
          </n-button>

          <n-button v-if="showReport" @click="handleReport">
            <template #icon>
              <n-icon><BugIcon /></n-icon>
            </template>
            报告问题
          </n-button>
        </n-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, nextTick } from 'vue'
import { NIcon, NButton, NSpace, NCollapse, NCollapseItem } from 'naive-ui'
import {
  WarningOutline as ExclamationTriangleIcon,
  RefreshOutline as RefreshIcon,
  RefreshOutline as ReloadIcon,
  BugOutline as BugIcon
} from '@vicons/ionicons5'

export interface ErrorBoundaryProps {
  // 错误标题
  title?: string
  // 错误描述
  description?: string
  // 是否显示错误详情
  showDetails?: boolean
  // 是否显示报告按钮
  showReport?: boolean
  // 重试回调
  onRetry?: () => void | Promise<void>
  // 报告回调
  onReport?: (error: Error) => void | Promise<void>
}

const props = withDefaults(defineProps<ErrorBoundaryProps>(), {
  showDetails: false,
  showReport: false
})

const emit = defineEmits<{
  error: [error: Error]
  retry: []
  report: [error: Error]
}>()

const hasError = ref(false)
const errorDetails = ref<string>('')
const currentError = ref<Error | null>(null)

// 捕获子组件错误
onErrorCaptured((error: Error, instance, info) => {
  console.error('ErrorBoundary caught error:', error)
  console.error('Component instance:', instance)
  console.error('Error info:', info)

  hasError.value = true
  currentError.value = error
  errorDetails.value = `${error.message}\n\n${error.stack || ''}\n\nComponent Info: ${info}`

  emit('error', error)

  // 阻止错误继续向上传播
  return false
})

// 重试处理
const handleRetry = async () => {
  try {
    if (props.onRetry) {
      await props.onRetry()
    }

    // 重置错误状态
    hasError.value = false
    errorDetails.value = ''
    currentError.value = null

    emit('retry')

    // 等待下一个tick确保组件重新渲染
    await nextTick()
  } catch (error) {
    console.error('Retry failed:', error)
    // 如果重试失败，保持错误状态
  }
}

// 刷新页面
const handleReload = () => {
  window.location.reload()
}

// 报告问题
const handleReport = async () => {
  if (currentError.value) {
    try {
      if (props.onReport) {
        await props.onReport(currentError.value)
      }

      emit('report', currentError.value)
    } catch (error) {
      console.error('Report failed:', error)
    }
  }
}

// 手动触发错误（用于测试）
const triggerError = (error: Error) => {
  hasError.value = true
  currentError.value = error
  errorDetails.value = `${error.message}\n\n${error.stack || ''}`
  emit('error', error)
}

// 重置错误状态
const reset = () => {
  hasError.value = false
  errorDetails.value = ''
  currentError.value = null
}

// 暴露方法给父组件
defineExpose({
  triggerError,
  reset,
  hasError: readonly(hasError)
})
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.error-boundary__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  text-align: center;
  min-height: 300px;
  gap: var(--spacing-lg);
}

.error-boundary__icon {
  opacity: 0.8;
}

.error-boundary__message {
  max-width: 500px;
}

.error-boundary__title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-md) 0;
}

.error-boundary__description {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  margin: 0;
}

.error-boundary__details {
  width: 100%;
  max-width: 600px;
  margin-top: var(--spacing-lg);
  text-align: left;
}

.error-boundary__stack {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: var(--color-fill-quaternary);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.error-boundary__actions {
  margin-top: var(--spacing-lg);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .error-boundary__content {
    padding: var(--spacing-lg);
    min-height: 250px;
  }

  .error-boundary__title {
    font-size: var(--font-size-lg);
  }

  .error-boundary__description {
    font-size: var(--font-size-sm);
  }

  .error-boundary__actions :deep(.n-space) {
    flex-direction: column;
    width: 100%;
  }

  .error-boundary__actions :deep(.n-button) {
    width: 100%;
  }
}

/* 暗色主题适配 */
@media (prefers-color-scheme: dark) {
  .error-boundary__stack {
    background: var(--color-fill-secondary);
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .error-boundary__title {
    color: var(--color-text-primary);
  }

  .error-boundary__description {
    color: var(--color-text-primary);
  }

  .error-boundary__stack {
    border: 1px solid var(--color-border);
  }
}

/* 打印样式 */
@media print {
  .error-boundary__actions {
    display: none;
  }

  .error-boundary__details {
    page-break-inside: avoid;
  }
}
</style>

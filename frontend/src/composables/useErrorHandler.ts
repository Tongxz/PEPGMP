import { createDiscreteApi } from 'naive-ui'
import { h, reactive, readonly, ref } from 'vue'

// 创建离散的 Naive UI API 实例，用于在非组件上下文中使用
const { message, notification, dialog, loadingBar } = createDiscreteApi(
  ['message', 'notification', 'dialog', 'loadingBar']
)

// 错误类型定义
export interface ErrorHandlerOptions {
  showMessage?: boolean
  showNotification?: boolean
  showDialog?: boolean
  logError?: boolean
  customMessage?: string
  customTitle?: string
  duration?: number
  type?: 'error' | 'warning' | 'info'
  actions?: Array<{
    label: string
    type?: 'primary' | 'info' | 'success' | 'warning' | 'error'
    onClick: () => void
  }>
}

// 错误状态管理
const errorState = reactive({
  lastError: null as Error | null,
  errorCount: 0,
  isHandling: false
})

// 错误处理主函数
export function useErrorHandler() {
  const isHandlingError = ref(false)

  /**
   * 处理单个错误
   */
  const handleError = async (error: unknown, options: ErrorHandlerOptions = {}) => {
    if (isHandlingError.value) return // 防止重复处理

    isHandlingError.value = true

    try {
      // 默认选项
      const defaultOptions: Required<ErrorHandlerOptions> = {
        showMessage: true,
        showNotification: false,
        showDialog: false,
        logError: true,
        customMessage: '',
        customTitle: '',
        duration: 5000,
        type: 'error',
        actions: []
      }

      const opts = { ...defaultOptions, ...options }

      // 解析错误信息
      const errorInfo = parseError(error, opts.customMessage)

      // 记录错误
      if (opts.logError) {
        console.error('[ErrorHandler]', errorInfo)
        errorState.lastError = error instanceof Error ? error : new Error(String(error))
        errorState.errorCount++
      }

      // 显示错误信息
      if (opts.showDialog) {
        await showErrorDialog(errorInfo, opts)
      } else if (opts.showNotification) {
        showErrorNotification(errorInfo, opts)
      } else if (opts.showMessage) {
        showErrorMessage(errorInfo, opts)
      }

    } catch (handlerError) {
      // 处理错误处理器本身的错误
      console.error('[ErrorHandler] Error in error handler:', handlerError)
      message.error('错误处理失败')
    } finally {
      isHandlingError.value = false
    }
  }

  /**
   * 处理异步操作的错误
   */
  const handleAsyncError = <T>(
    asyncFn: () => Promise<T>,
    options: ErrorHandlerOptions = {}
  ): Promise<T | null> => {
    return asyncFn().catch(error => {
      handleError(error, options)
      return null
    })
  }

  /**
   * 处理多个错误
   */
  const handleMultipleErrors = (
    errors: unknown[],
    options: ErrorHandlerOptions = {}
  ) => {
    const errorMessages = errors.map(error => parseError(error).message)
    const combinedMessage = `发生 ${errors.length} 个错误:\n${errorMessages.join('\n')}`

    handleError(new Error(combinedMessage), {
      ...options,
      customMessage: combinedMessage
    })
  }

  /**
   * 创建错误边界处理函数
   */
  const createErrorBoundary = (fallbackMessage?: string) => {
    return (error: unknown) => {
      handleError(error, {
        showMessage: true,
        customMessage: fallbackMessage,
        logError: true
      })
    }
  }

  /**
   * 重置错误状态
   */
  const resetErrorState = () => {
    errorState.lastError = null
    errorState.errorCount = 0
    errorState.isHandling = false
  }

  return {
    handleError,
    handleAsyncError,
    handleMultipleErrors,
    createErrorBoundary,
    resetErrorState,
    isHandlingError: readonly(isHandlingError),
    errorState: readonly(errorState)
  }
}

// 辅助函数
function parseError(error: unknown, customMessage?: string): { message: string; title: string; details?: string } {
  if (customMessage) {
    return {
      message: customMessage,
      title: '操作失败',
      details: error instanceof Error ? error.message : String(error)
    }
  }

  if (error instanceof Error) {
    // 网络错误
    if (error.name === 'NetworkError' || error.message.includes('fetch')) {
      return {
        message: '网络连接失败，请检查网络连接',
        title: '网络错误',
        details: error.message
      }
    }

    // API错误
    if (error.message.includes('HTTP') || error.message.includes('status')) {
      return {
        message: '请求失败，请稍后重试',
        title: '请求错误',
        details: error.message
      }
    }

    // 权限错误
    if (error.message.includes('权限') || error.message.includes('unauthorized')) {
      return {
        message: '没有权限执行此操作',
        title: '权限不足',
        details: error.message
      }
    }

    // 通用错误
    return {
      message: error.message,
      title: '操作失败',
      details: error.stack
    }
  }

  // 字符串错误
  if (typeof error === 'string') {
    return {
      message: error,
      title: '操作失败'
    }
  }

  // 其他类型的错误
  return {
    message: '发生未知错误，请稍后重试',
    title: '未知错误',
    details: String(error)
  }
}

function showErrorMessage(errorInfo: ReturnType<typeof parseError>, options: ErrorHandlerOptions) {
  const { message: errorMessage, title } = errorInfo

  switch (options.type) {
    case 'warning':
      message.warning(errorMessage, {
        duration: options.duration,
        keepAliveOnHover: true
      })
      break
    case 'info':
      message.info(errorMessage, {
        duration: options.duration,
        keepAliveOnHover: true
      })
      break
    default:
      message.error(errorMessage, {
        duration: options.duration,
        keepAliveOnHover: true
      })
  }
}

function showErrorNotification(errorInfo: ReturnType<typeof parseError>, options: ErrorHandlerOptions) {
  const { message: errorMessage, title, details } = errorInfo

  notification[options.type || 'error']({
    title,
    content: errorMessage,
    description: details,
    duration: options.duration,
    keepAliveOnHover: true,
    action: options.actions?.length ? () => {
      return options.actions!.map(action =>
        h('n-button', {
          size: 'small',
          type: action.type || 'default',
          onClick: action.onClick
        }, action.label)
      )
    } : undefined
  })
}

async function showErrorDialog(errorInfo: ReturnType<typeof parseError>, options: ErrorHandlerOptions) {
  const { message: errorMessage, title, details } = errorInfo

  await dialog.error({
    title,
    content: errorMessage,
    description: details,
    positiveText: '确定',
    onPositiveClick: () => {
      options.actions?.forEach(action => action.onClick())
    }
  })
}

// 工具函数 - 防抖错误处理
export function createDebouncedErrorHandler(delay: number = 1000) {
  let timeoutId: NodeJS.Timeout | null = null

  return function debouncedHandleError(error: unknown, options?: ErrorHandlerOptions) {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }

    timeoutId = setTimeout(() => {
      const { handleError } = useErrorHandler()
      handleError(error, options)
      timeoutId = null
    }, delay)
  }
}

// 工具函数 - 错误重试
export function createRetryableErrorHandler(
  maxRetries: number = 3,
  retryDelay: number = 1000
) {
  return async function retryableHandler<T>(
    fn: () => Promise<T>,
    errorOptions?: ErrorHandlerOptions
  ): Promise<T | null> {
    const { handleError } = useErrorHandler()

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await fn()
      } catch (error) {
        if (attempt === maxRetries) {
          handleError(error, errorOptions)
          return null
        }

        // 等待重试
        await new Promise(resolve => setTimeout(resolve, retryDelay * attempt))
      }
    }

    return null
  }
}

// 全局错误处理器
export const globalErrorHandler = {
  // Vue 错误处理
  vueErrorHandler: (error: unknown, instance: any, info: string) => {
    const { handleError } = useErrorHandler()
    handleError(error, {
      customMessage: `Vue 组件错误: ${info}`,
      logError: true
    })
  },

  // 未捕获的 Promise 错误
  unhandledRejectionHandler: (event: PromiseRejectionEvent) => {
    const { handleError } = useErrorHandler()
    handleError(event.reason, {
      customMessage: '未处理的 Promise 拒绝',
      logError: true
    })
    event.preventDefault()
  },

  // 全局未捕获错误
  uncaughtErrorHandler: (event: ErrorEvent) => {
    const { handleError } = useErrorHandler()
    handleError(event.error || event.message, {
      customMessage: '未捕获的全局错误',
      logError: true
    })
  }
}

// 注册全局错误处理器
export function setupGlobalErrorHandling() {
  // Vue 错误处理
  // 这需要在 main.ts 中设置: app.config.errorHandler = globalErrorHandler.vueErrorHandler

  // 浏览器事件监听器
  if (typeof window !== 'undefined') {
    window.addEventListener('unhandledrejection', globalErrorHandler.unhandledRejectionHandler)
    window.addEventListener('error', globalErrorHandler.uncaughtErrorHandler)
  }
}

// 清理全局错误处理器
export function cleanupGlobalErrorHandling() {
  if (typeof window !== 'undefined') {
    window.removeEventListener('unhandledrejection', globalErrorHandler.unhandledRejectionHandler)
    window.removeEventListener('error', globalErrorHandler.uncaughtErrorHandler)
  }
}

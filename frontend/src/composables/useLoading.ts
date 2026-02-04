import { createDiscreteApi } from 'naive-ui'
import { computed, reactive, readonly, ref } from 'vue'

// 创建离散的 Naive UI API 实例
const { loadingBar } = createDiscreteApi(['loadingBar'])

// 加载状态类型定义
export interface LoadingState {
  isLoading: boolean
  message?: string
  progress?: number
  startTime?: number
  endTime?: number
}

export interface LoadingOptions {
  message?: string
  showLoadingBar?: boolean
  timeout?: number
  onTimeout?: () => void
}

// 全局加载状态管理
const globalLoadingState = reactive({
  activeLoadings: new Map<string, LoadingState>(),
  totalLoadingCount: 0
})

// 加载状态 composable
export function useLoading() {
  const localLoadingState = ref<LoadingState>({
    isLoading: false
  })

  /**
   * 开始加载状态
   */
  const startLoading = (key: string = 'default', options: LoadingOptions = {}) => {
    const { message, showLoadingBar = true, timeout, onTimeout } = options

    const loadingState: LoadingState = {
      isLoading: true,
      message,
      progress: 0,
      startTime: Date.now()
    }

    // 本地状态
    localLoadingState.value = loadingState

    // 全局状态
    globalLoadingState.activeLoadings.set(key, loadingState)
    globalLoadingState.totalLoadingCount++

    // 显示加载条
    if (showLoadingBar) {
      loadingBar.start()
    }

    // 设置超时
    if (timeout && timeout > 0) {
      const timeoutId = setTimeout(() => {
        finishLoading(key)
        if (onTimeout) {
          onTimeout()
        }
      }, timeout)

        // 存储超时ID用于清理
        ; (loadingState as any).timeoutId = timeoutId
    }

    return key
  }

  /**
   * 结束加载状态
   */
  const finishLoading = (key: string = 'default') => {
    const loadingState = globalLoadingState.activeLoadings.get(key)
    if (!loadingState) return

    // 更新状态
    loadingState.isLoading = false
    loadingState.endTime = Date.now()

    // 清理超时
    if ((loadingState as any).timeoutId) {
      clearTimeout((loadingState as any).timeoutId)
    }

    // 移除全局状态
    globalLoadingState.activeLoadings.delete(key)
    globalLoadingState.totalLoadingCount = Math.max(0, globalLoadingState.totalLoadingCount - 1)

    // 更新本地状态
    if (localLoadingState.value.startTime === loadingState.startTime) {
      localLoadingState.value = { isLoading: false }
    }

    // 隐藏加载条
    if (globalLoadingState.totalLoadingCount === 0) {
      loadingBar.finish()
    }
  }

  /**
   * 更新加载进度
   */
  const updateProgress = (key: string = 'default', progress: number) => {
    const loadingState = globalLoadingState.activeLoadings.get(key)
    if (loadingState) {
      loadingState.progress = Math.min(100, Math.max(0, progress))
    }
  }

  /**
   * 更新加载消息
   */
  const updateMessage = (key: string = 'default', message: string) => {
    const loadingState = globalLoadingState.activeLoadings.get(key)
    if (loadingState) {
      loadingState.message = message
    }
  }

  /**
   * 包装异步函数，自动处理加载状态
   */
  const withLoading = async <T>(
    asyncFn: () => Promise<T>,
    key: string = 'default',
    options: LoadingOptions = {}
  ): Promise<T> => {
    const loadingKey = startLoading(key, options)

    try {
      const result = await asyncFn()
      return result
    } finally {
      finishLoading(loadingKey)
    }
  }

  /**
   * 创建防抖加载状态
   */
  const createDebouncedLoading = (delay: number = 300) => {
    let timeoutId: NodeJS.Timeout | null = null
    let currentKey: string | null = null

    return {
      start: (key: string = 'debounced', options: LoadingOptions = {}) => {
        if (timeoutId) {
          clearTimeout(timeoutId)
        }

        timeoutId = setTimeout(() => {
          currentKey = startLoading(key, options)
        }, delay)
      },

      finish: (key?: string) => {
        if (timeoutId) {
          clearTimeout(timeoutId)
          timeoutId = null
        }

        if (currentKey || key) {
          finishLoading(currentKey || key!)
          currentKey = null
        }
      }
    }
  }

  /**
   * 创建多步骤加载状态
   */
  const createMultiStepLoading = (steps: Array<{ key: string; message: string; weight?: number }>) => {
    const totalWeight = steps.reduce((sum, step) => sum + (step.weight || 1), 0)
    let currentProgress = 0

    const stepLoadings = steps.map(step => ({
      ...step,
      weight: step.weight || 1,
      completed: false
    }))

    return {
      start: () => {
        startLoading('multi-step', {
          message: steps[0].message,
          showLoadingBar: true
        })
      },

      completeStep: (stepIndex: number) => {
        if (stepIndex >= stepLoadings.length) return

        const step = stepLoadings[stepIndex]
        if (step.completed) return

        step.completed = true
        currentProgress += (step.weight / totalWeight) * 100

        updateProgress('multi-step', currentProgress)

        // 更新消息到下一个步骤
        const nextStepIndex = stepIndex + 1
        if (nextStepIndex < steps.length) {
          updateMessage('multi-step', steps[nextStepIndex].message)
        }
      },

      finish: () => {
        finishLoading('multi-step')
        currentProgress = 0
        stepLoadings.forEach(step => step.completed = false)
      }
    }
  }

  // 计算属性
  const isLoading = computed(() => localLoadingState.value.isLoading)
  const loadingMessage = computed(() => localLoadingState.value.message)
  const loadingProgress = computed(() => localLoadingState.value.progress || 0)

  const globalIsLoading = computed(() => globalLoadingState.totalLoadingCount > 0)
  const globalActiveLoadings = computed(() => Array.from(globalLoadingState.activeLoadings.entries()))

  return {
    // 本地加载状态
    isLoading: readonly(isLoading),
    loadingMessage: readonly(loadingMessage),
    loadingProgress: readonly(loadingProgress),

    // 全局加载状态
    globalIsLoading: readonly(globalIsLoading),
    globalActiveLoadings: readonly(globalActiveLoadings),

    // 方法
    startLoading,
    finishLoading,
    updateProgress,
    updateMessage,
    withLoading,
    createDebouncedLoading,
    createMultiStepLoading
  }
}

// 全局加载状态 composable
export function useGlobalLoading() {
  return {
    globalIsLoading: computed(() => globalLoadingState.totalLoadingCount > 0),
    globalActiveLoadings: computed(() => Array.from(globalLoadingState.activeLoadings.entries())),
    totalLoadingCount: computed(() => globalLoadingState.totalLoadingCount)
  }
}

// 快捷方法 - 为常见操作创建加载状态
export function createApiLoading() {
  const { withLoading } = useLoading()

  return {
    withApiCall: <T>(apiCall: () => Promise<T>, message: string = '加载中...') =>
      withLoading(apiCall, 'api', { message, showLoadingBar: true }),

    withSave: <T>(saveCall: () => Promise<T>) =>
      withLoading(saveCall, 'save', { message: '保存中...', showLoadingBar: true }),

    withDelete: <T>(deleteCall: () => Promise<T>) =>
      withLoading(deleteCall, 'delete', { message: '删除中...', showLoadingBar: true }),

    withUpload: <T>(uploadCall: () => Promise<T>) =>
      withLoading(uploadCall, 'upload', { message: '上传中...', showLoadingBar: true }),

    withDownload: <T>(downloadCall: () => Promise<T>) =>
      withLoading(downloadCall, 'download', { message: '下载中...', showLoadingBar: true })
  }
}

// 加载状态组件的辅助函数
export function useLoadingState(initialLoading: boolean = false) {
  const isLoading = ref(initialLoading)
  const loadingMessage = ref<string>()
  const loadingProgress = ref<number>()

  const setLoading = (loading: boolean, message?: string, progress?: number) => {
    isLoading.value = loading
    loadingMessage.value = message
    loadingProgress.value = progress
  }

  const startLoading = (message?: string) => {
    setLoading(true, message, 0)
  }

  const finishLoading = () => {
    setLoading(false)
  }

  const updateProgress = (progress: number) => {
    loadingProgress.value = progress
  }

  return {
    isLoading: readonly(isLoading),
    loadingMessage: readonly(loadingMessage),
    loadingProgress: readonly(loadingProgress),
    setLoading,
    startLoading,
    finishLoading,
    updateProgress
  }
}

import { ref, computed, reactive, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, useDialog, useNotification } from 'naive-ui'

// 操作步骤定义
export interface FlowStep {
  id: string
  title: string
  description?: string
  component?: string
  validation?: () => boolean | Promise<boolean>
  onEnter?: () => void | Promise<void>
  onExit?: () => void | Promise<void>
  canSkip?: boolean
  isOptional?: boolean
}

// 用户操作类型
export type UserAction =
  | 'navigate'
  | 'submit'
  | 'cancel'
  | 'confirm'
  | 'retry'
  | 'skip'
  | 'back'
  | 'next'
  | 'save'
  | 'delete'
  | 'edit'
  | 'view'
  | 'refresh'

// 操作上下文
export interface ActionContext {
  action: UserAction
  source: string
  target?: string
  data?: any
  timestamp: number
  userId?: string
}

// 用户偏好设置
export interface UserPreferences {
  confirmBeforeDelete: boolean
  autoSave: boolean
  showTooltips: boolean
  animationEnabled: boolean
  compactMode: boolean
  keyboardShortcuts: boolean
}

export function useUserFlow() {
  const router = useRouter()
  const route = useRoute()
  const message = useMessage()
  const dialog = useDialog()
  const notification = useNotification()

  // 当前流程状态
  const currentFlow = ref<string | null>(null)
  const currentStep = ref<number>(0)
  const flowSteps = ref<FlowStep[]>([])
  const flowData = reactive<Record<string, any>>({})

  // 用户偏好
  const userPreferences = reactive<UserPreferences>({
    confirmBeforeDelete: true,
    autoSave: true,
    showTooltips: true,
    animationEnabled: true,
    compactMode: false,
    keyboardShortcuts: true
  })

  // 操作历史
  const actionHistory = ref<ActionContext[]>([])
  const maxHistorySize = 100

  // 加载状态
  const isLoading = ref(false)
  const loadingText = ref('')

  // 错误状态
  const hasError = ref(false)
  const errorMessage = ref('')

  // 计算属性
  const isFirstStep = computed(() => currentStep.value === 0)
  const isLastStep = computed(() => currentStep.value === flowSteps.value.length - 1)
  const canGoNext = computed(() => !isLastStep.value)
  const canGoBack = computed(() => !isFirstStep.value)
  const currentStepData = computed(() => flowSteps.value[currentStep.value])
  const progressPercentage = computed(() =>
    flowSteps.value.length > 0 ? ((currentStep.value + 1) / flowSteps.value.length) * 100 : 0
  )

  // 记录用户操作
  const recordAction = (action: UserAction, source: string, target?: string, data?: any) => {
    const actionContext: ActionContext = {
      action,
      source,
      target,
      data,
      timestamp: Date.now(),
      userId: 'current-user' // 实际项目中应该从认证系统获取
    }

    actionHistory.value.unshift(actionContext)

    // 限制历史记录大小
    if (actionHistory.value.length > maxHistorySize) {
      actionHistory.value = actionHistory.value.slice(0, maxHistorySize)
    }

    // 发送分析数据（可选）
    console.log('User Action:', actionContext)
  }

  // 启动流程
  const startFlow = async (flowId: string, steps: FlowStep[], initialData?: any) => {
    try {
      currentFlow.value = flowId
      flowSteps.value = steps
      currentStep.value = 0

      // 清空之前的数据
      Object.keys(flowData).forEach(key => delete flowData[key])

      // 设置初始数据
      if (initialData) {
        Object.assign(flowData, initialData)
      }

      recordAction('navigate', 'flow-start', flowId, { steps: steps.length })

      // 执行第一步的进入逻辑
      const firstStep = steps[0]
      if (firstStep?.onEnter) {
        await firstStep.onEnter()
      }

      return true
    } catch (error) {
      console.error('Failed to start flow:', error)
      handleError('启动流程失败', error)
      return false
    }
  }

  // 下一步
  const nextStep = async () => {
    if (!canGoNext.value) return false

    const current = currentStepData.value

    try {
      // 验证当前步骤
      if (current?.validation) {
        const isValid = await current.validation()
        if (!isValid) {
          message.warning('请完成当前步骤的必填项')
          return false
        }
      }

      // 执行当前步骤的退出逻辑
      if (current?.onExit) {
        await current.onExit()
      }

      // 移动到下一步
      currentStep.value++

      // 执行下一步的进入逻辑
      const next = currentStepData.value
      if (next?.onEnter) {
        await next.onEnter()
      }

      recordAction('next', 'step-navigation', next.id, {
        from: current.id,
        to: next.id
      })

      return true
    } catch (error) {
      console.error('Failed to go to next step:', error)
      handleError('进入下一步失败', error)
      return false
    }
  }

  // 上一步
  const prevStep = async () => {
    if (!canGoBack.value) return false

    const current = currentStepData.value

    try {
      // 执行当前步骤的退出逻辑
      if (current?.onExit) {
        await current.onExit()
      }

      // 移动到上一步
      currentStep.value--

      // 执行上一步的进入逻辑
      const prev = currentStepData.value
      if (prev?.onEnter) {
        await prev.onEnter()
      }

      recordAction('back', 'step-navigation', prev.id, {
        from: current.id,
        to: prev.id
      })

      return true
    } catch (error) {
      console.error('Failed to go to previous step:', error)
      handleError('返回上一步失败', error)
      return false
    }
  }

  // 跳转到指定步骤
  const goToStep = async (stepIndex: number) => {
    if (stepIndex < 0 || stepIndex >= flowSteps.value.length) return false

    const current = currentStepData.value
    const target = flowSteps.value[stepIndex]

    try {
      // 执行当前步骤的退出逻辑
      if (current?.onExit) {
        await current.onExit()
      }

      currentStep.value = stepIndex

      // 执行目标步骤的进入逻辑
      if (target?.onEnter) {
        await target.onEnter()
      }

      recordAction('navigate', 'step-jump', target.id, {
        from: current.id,
        to: target.id,
        index: stepIndex
      })

      return true
    } catch (error) {
      console.error('Failed to go to step:', error)
      handleError('跳转步骤失败', error)
      return false
    }
  }

  // 完成流程
  const completeFlow = async () => {
    const current = currentStepData.value

    try {
      // 验证最后一步
      if (current?.validation) {
        const isValid = await current.validation()
        if (!isValid) {
          message.warning('请完成所有必填项')
          return false
        }
      }

      // 执行退出逻辑
      if (current?.onExit) {
        await current.onExit()
      }

      recordAction('submit', 'flow-complete', currentFlow.value!, flowData)

      // 清理状态
      currentFlow.value = null
      currentStep.value = 0
      flowSteps.value = []
      Object.keys(flowData).forEach(key => delete flowData[key])

      message.success('操作完成')
      return true
    } catch (error) {
      console.error('Failed to complete flow:', error)
      handleError('完成流程失败', error)
      return false
    }
  }

  // 取消流程
  const cancelFlow = async () => {
    if (!currentFlow.value) return true

    const shouldCancel = userPreferences.confirmBeforeDelete
      ? await confirmAction('确定要取消当前操作吗？未保存的更改将丢失。')
      : true

    if (shouldCancel) {
      recordAction('cancel', 'flow-cancel', currentFlow.value)

      currentFlow.value = null
      currentStep.value = 0
      flowSteps.value = []
      Object.keys(flowData).forEach(key => delete flowData[key])

      message.info('操作已取消')
      return true
    }

    return false
  }

  // 确认操作
  const confirmAction = (message: string, title = '确认操作'): Promise<boolean> => {
    return new Promise((resolve) => {
      dialog.warning({
        title,
        content: message,
        positiveText: '确认',
        negativeText: '取消',
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
        onClose: () => resolve(false)
      })
    })
  }

  // 智能导航
  const smartNavigate = async (path: string, options?: {
    replace?: boolean
    query?: Record<string, any>
  }) => {
    try {
      recordAction('navigate', 'smart-navigation', path, options)

      const routeLocation = { path, query: options?.query }

      if (options?.replace) {
        await router.replace(routeLocation)
      } else {
        await router.push(routeLocation)
      }

      return true
    } catch (error) {
      console.error('Navigation failed:', error)
      handleError('页面跳转失败', error)
      return false
    }
  }

  // 批量操作
  const batchOperation = async <T>(
    items: T[],
    operation: (item: T, index: number) => Promise<any>,
    options?: {
      batchSize?: number
      showProgress?: boolean
      continueOnError?: boolean
    }
  ) => {
    const { batchSize = 10, showProgress = true, continueOnError = false } = options || {}
    const results: any[] = []
    const errors: any[] = []

    try {
      isLoading.value = true

      for (let i = 0; i < items.length; i += batchSize) {
        const batch = items.slice(i, i + batchSize)

        if (showProgress) {
          loadingText.value = `处理中... ${i + 1}-${Math.min(i + batchSize, items.length)}/${items.length}`
        }

        const batchPromises = batch.map((item, index) =>
          operation(item, i + index).catch(error => {
            if (!continueOnError) throw error
            errors.push({ item, index: i + index, error })
            return null
          })
        )

        const batchResults = await Promise.all(batchPromises)
        results.push(...batchResults)

        // 给UI一些时间更新
        await nextTick()
      }

      recordAction('submit', 'batch-operation', 'completed', {
        total: items.length,
        success: results.filter(r => r !== null).length,
        errors: errors.length
      })

      if (errors.length > 0 && !continueOnError) {
        throw new Error(`批量操作失败: ${errors.length} 个错误`)
      }

      return { results, errors }
    } finally {
      isLoading.value = false
      loadingText.value = ''
    }
  }

  // 错误处理
  const handleError = (userMessage: string, error: any) => {
    hasError.value = true
    errorMessage.value = userMessage

    console.error(userMessage, error)

    notification.error({
      title: '操作失败',
      content: userMessage,
      duration: 5000
    })

    recordAction('retry', 'error-handling', userMessage, { error: error.message })
  }

  // 清除错误
  const clearError = () => {
    hasError.value = false
    errorMessage.value = ''
  }

  // 保存用户偏好
  const savePreferences = () => {
    try {
      localStorage.setItem('userPreferences', JSON.stringify(userPreferences))
      message.success('偏好设置已保存')
    } catch (error) {
      console.error('Failed to save preferences:', error)
      message.error('保存偏好设置失败')
    }
  }

  // 加载用户偏好
  const loadPreferences = () => {
    try {
      const saved = localStorage.getItem('userPreferences')
      if (saved) {
        Object.assign(userPreferences, JSON.parse(saved))
      }
    } catch (error) {
      console.error('Failed to load preferences:', error)
    }
  }

  // 初始化
  loadPreferences()

  return {
    // 流程状态
    currentFlow,
    currentStep,
    flowSteps,
    flowData,

    // 计算属性
    isFirstStep,
    isLastStep,
    canGoNext,
    canGoBack,
    currentStepData,
    progressPercentage,

    // 加载和错误状态
    isLoading,
    loadingText,
    hasError,
    errorMessage,

    // 用户偏好
    userPreferences,

    // 操作历史
    actionHistory,

    // 流程控制
    startFlow,
    nextStep,
    prevStep,
    goToStep,
    completeFlow,
    cancelFlow,

    // 工具方法
    recordAction,
    confirmAction,
    smartNavigate,
    batchOperation,
    handleError,
    clearError,
    savePreferences,
    loadPreferences
  }
}

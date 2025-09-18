/**
 * UI状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 加载状态类型
export interface LoadingState {
  global: boolean
  [key: string]: boolean
}

// 通知类型
export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
  persistent?: boolean
  actions?: Array<{
    label: string
    action: () => void
    type?: 'primary' | 'secondary'
  }>
}

// 模态框状态
export interface ModalState {
  visible: boolean
  component?: string
  props?: Record<string, any>
  options?: {
    closable?: boolean
    maskClosable?: boolean
    width?: string | number
    height?: string | number
  }
}

// 侧边栏状态
export interface SidebarState {
  collapsed: boolean
  width: number
  collapsedWidth: number
}

// 面包屑项
export interface BreadcrumbItem {
  label: string
  path?: string
  icon?: string
}

export const useUIStore = defineStore('ui', () => {
  // 加载状态
  const loading = ref<LoadingState>({
    global: false
  })

  // 通知列表
  const notifications = ref<Notification[]>([])

  // 模态框状态
  const modal = ref<ModalState>({
    visible: false
  })

  // 侧边栏状态
  const sidebar = ref<SidebarState>({
    collapsed: false,
    width: 240,
    collapsedWidth: 64
  })

  // 面包屑
  const breadcrumbs = ref<BreadcrumbItem[]>([])

  // 页面标题
  const pageTitle = ref<string>('')

  // 全屏状态
  const isFullscreen = ref<boolean>(false)

  // 计算属性
  const hasNotifications = computed(() => notifications.value.length > 0)
  const isLoading = computed(() => Object.values(loading.value).some(Boolean))
  const currentSidebarWidth = computed(() =>
    sidebar.value.collapsed ? sidebar.value.collapsedWidth : sidebar.value.width
  )

  // 加载状态管理
  const setLoading = (key: string, value: boolean) => {
    loading.value[key] = value
  }

  const setGlobalLoading = (value: boolean) => {
    loading.value.global = value
  }

  const clearLoading = () => {
    Object.keys(loading.value).forEach(key => {
      loading.value[key] = false
    })
  }

  // 通知管理
  const addNotification = (notification: Omit<Notification, 'id'>) => {
    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const newNotification: Notification = {
      id,
      duration: 4000,
      ...notification
    }

    notifications.value.push(newNotification)

    // 自动移除通知
    if (!newNotification.persistent && newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, newNotification.duration)
    }

    return id
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearNotifications = () => {
    notifications.value = []
  }

  // 便捷通知方法
  const showSuccess = (title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'success',
      title,
      message,
      ...options
    })
  }

  const showError = (title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'error',
      title,
      message,
      persistent: true,
      ...options
    })
  }

  const showWarning = (title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'warning',
      title,
      message,
      ...options
    })
  }

  const showInfo = (title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'info',
      title,
      message,
      ...options
    })
  }

  // 模态框管理
  const showModal = (component: string, props?: Record<string, any>, options?: ModalState['options']) => {
    modal.value = {
      visible: true,
      component,
      props,
      options: {
        closable: true,
        maskClosable: true,
        ...options
      }
    }
  }

  const hideModal = () => {
    modal.value = {
      visible: false,
      component: undefined,
      props: undefined,
      options: undefined
    }
  }

  // 侧边栏管理
  const toggleSidebar = () => {
    sidebar.value.collapsed = !sidebar.value.collapsed
  }

  const setSidebarCollapsed = (collapsed: boolean) => {
    sidebar.value.collapsed = collapsed
  }

  const setSidebarWidth = (width: number) => {
    sidebar.value.width = width
  }

  // 面包屑管理
  const setBreadcrumbs = (items: BreadcrumbItem[]) => {
    breadcrumbs.value = items
  }

  const addBreadcrumb = (item: BreadcrumbItem) => {
    breadcrumbs.value.push(item)
  }

  const clearBreadcrumbs = () => {
    breadcrumbs.value = []
  }

  // 页面标题管理
  const setPageTitle = (title: string) => {
    pageTitle.value = title
    // 同时更新浏览器标题
    if (typeof document !== 'undefined') {
      document.title = title ? `${title} - 洗手检测系统` : '洗手检测系统'
    }
  }

  // 全屏管理
  const toggleFullscreen = async () => {
    if (typeof document === 'undefined') return

    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen()
        isFullscreen.value = true
      } else {
        await document.exitFullscreen()
        isFullscreen.value = false
      }
    } catch (error) {
      console.warn('Fullscreen operation failed:', error)
    }
  }

  const exitFullscreen = async () => {
    if (typeof document === 'undefined') return

    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
        isFullscreen.value = false
      }
    } catch (error) {
      console.warn('Exit fullscreen failed:', error)
    }
  }

  // 监听全屏状态变化
  if (typeof document !== 'undefined') {
    document.addEventListener('fullscreenchange', () => {
      isFullscreen.value = !!document.fullscreenElement
    })
  }

  // 重置所有状态
  const resetUI = () => {
    clearLoading()
    clearNotifications()
    hideModal()
    clearBreadcrumbs()
    setPageTitle('')
    setSidebarCollapsed(false)
  }

  return {
    // 状态
    loading,
    notifications,
    modal,
    sidebar,
    breadcrumbs,
    pageTitle,
    isFullscreen,

    // 计算属性
    hasNotifications,
    isLoading,
    currentSidebarWidth,

    // 加载状态方法
    setLoading,
    setGlobalLoading,
    clearLoading,

    // 通知方法
    addNotification,
    removeNotification,
    clearNotifications,
    showSuccess,
    showError,
    showWarning,
    showInfo,

    // 模态框方法
    showModal,
    hideModal,

    // 侧边栏方法
    toggleSidebar,
    setSidebarCollapsed,
    setSidebarWidth,

    // 面包屑方法
    setBreadcrumbs,
    addBreadcrumb,
    clearBreadcrumbs,

    // 页面标题方法
    setPageTitle,

    // 全屏方法
    toggleFullscreen,
    exitFullscreen,

    // 重置方法
    resetUI
  }
})

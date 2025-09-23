import { createPinia } from 'pinia'

// 创建 Pinia 实例
export const pinia = createPinia()

// 导出所有 store
export { useSystemStore } from './system'
export { useCameraStore } from './camera'
export { useRegionStore } from './region'
export { useStatisticsStore } from './statistics'
export { useUIStore } from './ui'

// 导出类型
export type {
  LoadingState,
  Notification,
  ModalState,
  SidebarState,
  BreadcrumbItem
} from './ui'

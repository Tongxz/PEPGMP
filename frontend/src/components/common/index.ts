/**
 * 通用组件导出
 */

// 页面头部组件
export { default as PageHeader } from './PageHeader.vue'

// 数据卡片组件
export { default as DataCard } from './DataCard.vue'

// 状态指示器组件
export { default as StatusIndicator } from './StatusIndicator.vue'

// 加载动画组件
export { default as LoadingSpinner } from './LoadingSpinner.vue'

// 错误边界组件
export { default as ErrorBoundary } from './ErrorBoundary.vue'

// 类型定义
export type StatusType = 'success' | 'warning' | 'error' | 'info' | 'loading'
export type SizeType = 'small' | 'medium' | 'large'

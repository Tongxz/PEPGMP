/**
 * 插件统一导出
 */
export { performancePlugin, recordApiPerformance, generatePerformanceReport, withApiPerformance } from './performance'

// 插件类型定义
export interface PluginOptions {
  performance?: {
    enabled?: boolean
    routeTracking?: boolean
    componentTracking?: boolean
    apiTracking?: boolean
    reportInterval?: number
    reportUrl?: string
    consoleOutput?: boolean
  }
}

// 默认插件配置
export const defaultPluginOptions: PluginOptions = {
  performance: {
    enabled: true,
    routeTracking: true,
    componentTracking: true,
    apiTracking: true,
    reportInterval: 30000,
    consoleOutput: import.meta.env.DEV
  }
}

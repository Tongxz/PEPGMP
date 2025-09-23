// API 模块统一导出
export * from './system'
export * from './camera'
export * from './statistics'
export * from './region'

// 重新导出类型
export type { Camera } from './camera'
export type { StatisticsSummary, EventData, DailyStatistics } from './statistics'
export type { Region } from './region'
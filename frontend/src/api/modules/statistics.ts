/**
 * 统计分析 API
 * 适配后端实际接口
 */

import request from '../index'

// ===== 后端实际返回的数据结构 =====

export interface RealtimeStatisticsResponse {
    timestamp: string
    system_status: string
    detection_stats: {
        total_detections_today: number
        handwashing_detections: number
        disinfection_detections: number
        hairnet_detections: number
        violation_count: number
    }
    region_stats: {
        active_regions: number
        monitored_areas: any[]
    }
    performance_metrics: {
        average_processing_time: number
        detection_accuracy: number
        system_uptime: string
    }
    alerts: {
        active_alerts: number
        recent_violations: any[]
    }
}

export interface DetectionRealtimeResponse {
    processing_efficiency: number
    avg_fps: number
    processed_frames: number
    skipped_frames: number
    scene_distribution: {
        static: number
        dynamic: number
        critical: number
    }
    performance: {
        cpu_usage: number
        memory_usage: number
        gpu_usage: number
    }
    connection_status: {
        connected: boolean
        active_cameras: number
    }
    timestamp: string
}

export interface DailyStatistics {
    date: string
    total_events: number
    counts_by_type: Record<string, number>
}

// ===== 前端使用的数据结构 =====

export interface SystemStatus {
    status: 'online' | 'warning' | 'offline'
    onlineCameras: number
    totalCameras: number
    realtimeFps: number
    activeAlerts: number
}

export interface DetectionTrend {
    date: string
    detections: number
    violations: number
}

export interface ViolationType {
    type: string
    count: number
    percentage: number
}

// ===== API 方法 =====

/**
 * 获取实时统计数据（原始）
 */
export const getRealtimeStatistics = (): Promise<RealtimeStatisticsResponse> => {
    return request.get('/api/v1/statistics/realtime')
}

/**
 * 获取检测实时统计（原始）
 */
export const getDetectionRealtimeStatistics = (): Promise<DetectionRealtimeResponse> => {
    return request.get('/api/v1/statistics/detection-realtime')
}

/**
 * 获取每日统计数据
 */
export const getDailyStatistics = (params: {
    days?: number
    camera_id?: string
}): Promise<DailyStatistics[]> => {
    return request.get('/api/v1/statistics/daily', { params })
}

/**
 * 获取统计摘要
 */
export const getStatisticsSummary = (params: {
    minutes?: number
    limit?: number
    camera_id?: string
}): Promise<{
    window_minutes: number
    total_events: number
    counts_by_type: Record<string, number>
    samples: any[]
}> => {
    return request.get('/api/v1/statistics/summary', { params })
}

/**
 * 获取事件历史
 */
export const getStatisticsHistory = (params: {
    minutes?: number
    limit?: number
    camera_id?: string
}): Promise<any[]> => {
    return request.get('/api/v1/statistics/history', { params })
}

// ===== 组合方法（前端使用） =====

/**
 * 获取系统状态（组合多个接口）
 * 用于首页状态栏
 */
export const getSystemStatus = async (): Promise<SystemStatus> => {
    try {
        const [realtimeStats, detectionStats] = await Promise.all([
            getRealtimeStatistics(),
            getDetectionRealtimeStatistics()
        ])

        return {
            status: realtimeStats.system_status === 'active' ? 'online' : 'offline',
            onlineCameras: detectionStats.connection_status.active_cameras,
            totalCameras: detectionStats.connection_status.active_cameras, // 暂时相同
            realtimeFps: Math.round(detectionStats.avg_fps),
            activeAlerts: realtimeStats.alerts.active_alerts
        }
    } catch (error) {
        console.error('获取系统状态失败:', error)
        throw error
    }
}

/**
 * 获取检测趋势（7天）
 */
export const getDetectionTrend = async (days: number = 7): Promise<DetectionTrend[]> => {
    try {
        const dailyStats = await getDailyStatistics({ days })

        return dailyStats.map(day => {
            // 计算总违规数（所有类型的违规数之和）
            const violations = Object.values(day.counts_by_type).reduce((sum, count) => sum + count, 0)

            return {
                date: day.date,
                detections: day.total_events,
                violations
            }
        })
    } catch (error) {
        console.error('获取检测趋势失败:', error)
        throw error
    }
}

/**
 * 获取违规类型分布
 * 注意：此接口后端暂未实现，使用 daily 数据聚合
 */
export const getViolationTypes = async (days: number = 7): Promise<ViolationType[]> => {
    try {
        const dailyStats = await getDailyStatistics({ days })

        // 聚合所有天的违规类型
        const typeMap: Record<string, number> = {}
        let totalViolations = 0

        dailyStats.forEach(day => {
            Object.entries(day.counts_by_type).forEach(([type, count]) => {
                typeMap[type] = (typeMap[type] || 0) + count
                totalViolations += count
            })
        })

        // 转换为数组并计算百分比
        return Object.entries(typeMap).map(([type, count]) => ({
            type,
            count,
            percentage: totalViolations > 0 ? Number(((count / totalViolations) * 100).toFixed(1)) : 0
        })).sort((a, b) => b.count - a.count) // 按数量降序
    } catch (error) {
        console.error('获取违规类型分布失败:', error)
        throw error
    }
}

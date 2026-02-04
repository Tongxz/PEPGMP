/**
 * 系统状态 API
 * 适配后端实际接口
 */

import request from '../index'
import { getSystemStatus as getSystemStatusFromStats } from './statistics'

// ===== 后端实际返回的数据结构 =====

export interface SystemInfoResponse {
    timestamp: string
    system: {
        platform: string
        platform_release: string
        platform_version: string
        architecture: string
        hostname: string
        processor: string
    }
    cpu: {
        physical_cores: number
        total_cores: number
        max_frequency: number
        current_frequency: number
        cpu_usage_percent: number
    }
    memory: {
        total: number
        available: number
        used: number
        percent: number
    }
    disk: {
        total: number
        used: number
        free: number
        percent: number
    }
    psutil_available: boolean
}

// ===== 前端使用的数据结构 =====

export interface SystemStatus {
    status: 'online' | 'warning' | 'offline'
    online_cameras: number
    total_cameras: number
    realtime_fps: number
    active_alerts: number
    cpu_usage?: number
    memory_usage?: number
    disk_usage?: number
    uptime?: number
}

export interface SystemHealth {
    healthy: boolean
    services: {
        database: boolean
        redis: boolean
        detection: boolean
    }
    message?: string
}

// ===== API 方法 =====

/**
 * 获取系统信息（原始）
 */
export const getSystemInfo = (): Promise<SystemInfoResponse> => {
    return request.get('/api/v1/system/info')
}

/**
 * 获取系统状态（组合多个接口）
 */
export const getSystemStatus = async (): Promise<SystemStatus> => {
    try {
        // 从统计接口获取系统状态
        const statusFromStats = await getSystemStatusFromStats()

        // 尝试获取系统信息（CPU、内存等）
        let systemInfo: SystemInfoResponse | null = null
        try {
            systemInfo = await getSystemInfo()
        } catch (error) {
            console.warn('获取系统信息失败，使用默认值')
        }

        return {
            ...statusFromStats,
            cpu_usage: systemInfo?.cpu?.cpu_usage_percent,
            memory_usage: systemInfo?.memory?.percent,
            disk_usage: systemInfo?.disk?.percent,
            uptime: undefined // 暂无此数据
        }
    } catch (error) {
        console.error('获取系统状态失败:', error)
        throw error
    }
}

/**
 * 获取系统健康状态
 * 注意：此接口后端返回503错误，暂不可用
 */
export const getSystemHealth = async (): Promise<SystemHealth> => {
    // 简化版：根据系统状态判断健康状态
    try {
        const status = await getSystemStatus()
        return {
            healthy: status.status === 'online',
            services: {
                database: true,
                redis: true,
                detection: status.status === 'online'
            }
        }
    } catch (error) {
        return {
            healthy: false,
            services: {
                database: false,
                redis: false,
                detection: false
            },
            message: '系统健康检查失败'
        }
    }
}

/**
 * Ping 测试
 */
export const ping = (): Promise<{ message: string; timestamp: string }> => {
    return request.get('/api/ping')
}

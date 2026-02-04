/**
 * 实时监控 API
 * 适配后端实际接口
 */

import { getCameras, type Camera } from './cameras'
import { getDetectionRealtimeStatistics, getRealtimeStatistics } from './statistics'

// ===== 前端使用的数据结构 =====

export interface MonitoringCamera {
    camera_id: string
    camera_name: string
    location: string
    status: 'online' | 'offline'
    fps: number
    resolution: string
    stream_url: string
    thumbnail?: string
    last_detection_time?: string
    detection_count_today: number
    violation_count_today: number
}

export interface MonitoringStatistics {
    online_cameras: number
    total_cameras: number
    realtime_detections: number
    avg_fps: number
    active_alerts: number
}

export interface StreamConfig {
    camera_id: string
    enable_detection: boolean
    save_frames: boolean
    detection_interval: number
}

// ===== API 方法（组合现有接口） =====

/**
 * 获取监控统计数据（组合多个接口）
 */
export const getMonitoringStatistics = async (): Promise<MonitoringStatistics> => {
    try {
        const [realtimeStats, detectionStats, camerasData] = await Promise.all([
            getRealtimeStatistics(),
            getDetectionRealtimeStatistics(),
            getCameras()
        ])

        return {
            online_cameras: camerasData.online,
            total_cameras: camerasData.total,
            realtime_detections: realtimeStats.detection_stats.total_detections_today,
            avg_fps: Math.round(detectionStats.avg_fps),
            active_alerts: realtimeStats.alerts.active_alerts
        }
    } catch (error) {
        console.error('获取监控统计失败:', error)
        throw error
    }
}

/**
 * 获取所有监控摄像头（使用摄像头列表接口）
 */
export const getMonitoringCameras = async (params?: {
    status?: 'online' | 'offline'
}): Promise<MonitoringCamera[]> => {
    try {
        const { cameras } = await getCameras(params)

        // 转换为监控摄像头格式
        return cameras.map((camera: Camera) => ({
            camera_id: camera.id,
            camera_name: camera.name,
            location: camera.location,
            status: camera.status,
            fps: camera.fps,
            resolution: camera.resolution,
            stream_url: camera.rtsp_url,
            thumbnail: camera.thumbnail,
            last_detection_time: undefined,
            detection_count_today: 0, // 暂无此数据
            violation_count_today: 0  // 暂无此数据
        }))
    } catch (error) {
        console.error('获取监控摄像头失败:', error)
        throw error
    }
}

/**
 * 获取摄像头视频流URL
 * 注意：此接口后端可能未实现
 */
export const getCameraStreamUrl = async (cameraId: string): Promise<{ stream_url: string }> => {
    // 从摄像头列表中获取
    const { cameras } = await getCameras()
    const camera = cameras.find(c => c.id === cameraId)

    if (!camera) {
        throw new Error('摄像头不存在')
    }

    return {
        stream_url: camera.rtsp_url
    }
}

/**
 * 更新视频流配置
 * 注意：此接口后端暂未实现
 */
export const updateStreamConfig = (
    cameraId: string,
    config: StreamConfig
): Promise<{ message: string }> => {
    throw new Error('更新视频流配置功能即将上线，敬请期待')
    // return request.post(`/api/v1/video-stream/${cameraId}/config`, config)
}

/**
 * 刷新摄像头列表
 * 注意：此接口后端暂未实现
 */
export const refreshCameras = (): Promise<{ message: string }> => {
    throw new Error('刷新摄像头列表功能即将上线，敬请期待')
    // return request.post('/api/v1/monitoring/refresh')
}

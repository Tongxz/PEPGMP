/**
 * 摄像头管理 API
 * 适配后端实际接口
 */

import request from '../index'

// ===== 后端实际返回的数据结构 =====

export interface CameraResponse {
    id: string
    name: string
    location: string
    status: string // 'active' | 'inactive'
    camera_type: string
    resolution: [number, number]
    fps: number | null
    region_id: string | null
    metadata: {
        source: string
        log_interval: number
        regions_file: string
    }
    created_at: string
    updated_at: string
    source: string
    log_interval: number
    regions_file: string
    active: boolean
    enabled: boolean
}

export interface CamerasListResponse {
    cameras: CameraResponse[]
}

// ===== 前端使用的数据结构 =====

export interface Camera {
    id: string
    name: string
    location: string
    ip: string
    rtsp_url: string
    resolution: string
    fps: number
    status: 'online' | 'offline'
    thumbnail?: string
    created_at?: string
    updated_at?: string
}

export interface CameraCreateRequest {
    name: string
    location: string
    ip: string
    rtsp_url: string
    resolution?: string
    fps?: number
}

export interface CameraUpdateRequest {
    name?: string
    location?: string
    ip?: string
    rtsp_url?: string
    resolution?: string
    fps?: number
    status?: 'online' | 'offline'
}

export interface CameraListResponse {
    cameras: Camera[]
    total: number
    online: number
    offline: number
    avg_fps: number
}

// ===== API 方法 =====

/**
 * 获取所有摄像头列表（原始）
 */
export const getCamerasRaw = (): Promise<CamerasListResponse> => {
    return request.get('/api/v1/cameras')
}

/**
 * 获取所有摄像头列表（转换为前端格式）
 */
export const getCameras = async (params?: {
    status?: 'online' | 'offline'
    search?: string
}): Promise<CameraListResponse> => {
    try {
        const response = await getCamerasRaw()

        // 转换为前端格式
        let cameras = response.cameras.map(convertCameraToFrontend)

        // 前端筛选
        if (params?.status) {
            cameras = cameras.filter(c => c.status === params.status)
        }

        if (params?.search) {
            const searchLower = params.search.toLowerCase()
            cameras = cameras.filter(c =>
                c.name.toLowerCase().includes(searchLower) ||
                c.location.toLowerCase().includes(searchLower)
            )
        }

        // 计算统计
        const online = cameras.filter(c => c.status === 'online').length
        const offline = cameras.length - online
        const avgFps = cameras.reduce((sum, c) => sum + c.fps, 0) / cameras.length || 0

        return {
            cameras,
            total: cameras.length,
            online,
            offline,
            avg_fps: Math.round(avgFps)
        }
    } catch (error) {
        console.error('获取摄像头列表失败:', error)
        throw error
    }
}

/**
 * 转换后端摄像头数据为前端格式
 */
function convertCameraToFrontend(camera: CameraResponse): Camera {
    return {
        id: camera.id,
        name: camera.name,
        location: camera.location || 'unknown',
        ip: extractIpFromSource(camera.source),
        rtsp_url: camera.source,
        resolution: `${camera.resolution[0]}x${camera.resolution[1]}`,
        fps: camera.fps || 0,
        status: camera.status === 'active' && camera.enabled ? 'online' : 'offline',
        created_at: camera.created_at,
        updated_at: camera.updated_at
    }
}

/**
 * 从 source 中提取 IP 地址
 */
function extractIpFromSource(source: string): string {
    // 尝试从 rtsp://192.168.1.100:554/stream 提取 IP
    const match = source.match(/rtsp:\/\/([0-9.]+)/)
    return match ? match[1] : 'N/A'
}

// ===== CRUD 操作 =====

/**
 * 获取单个摄像头详情
 */
export const getCamera = async (cameraId: string): Promise<Camera> => {
    // 从列表中查找
    const { cameras } = await getCameras()
    const camera = cameras.find(c => c.id === cameraId)
    if (!camera) {
        throw new Error('摄像头不存在')
    }
    return camera
}

/**
 * 创建摄像头
 */
export const createCamera = async (data: CameraCreateRequest): Promise<CameraResponse> => {
    try {
        // resolution需要转换为数组格式 [width, height]
        const resolution = data.resolution || '1920x1080'
        const parts = resolution.split('x')
        const resolutionArray = parts.length === 2
            ? [parseInt(parts[0]), parseInt(parts[1])]
            : [1920, 1080]

        const response = await request.post('/api/v1/cameras', {
            name: data.name,
            location: data.location,
            source: data.rtsp_url,
            resolution: resolutionArray,
            fps: data.fps || 30,
            camera_type: 'rtsp',
            enabled: true
        })
        return response.data
    } catch (error: any) {
        console.error('创建摄像头失败:', error)
        throw new Error(error.response?.data?.detail || '创建摄像头失败')
    }
}

/**
 * 更新摄像头
 */
export const updateCamera = async (cameraId: string, data: CameraUpdateRequest): Promise<CameraResponse> => {
    try {
        const updateData: any = {}

        if (data.name) updateData.name = data.name
        if (data.location) updateData.location = data.location
        if (data.rtsp_url) updateData.source = data.rtsp_url

        // resolution需要转换为数组格式 [width, height]
        if (data.resolution) {
            const parts = data.resolution.split('x')
            if (parts.length === 2) {
                updateData.resolution = [parseInt(parts[0]), parseInt(parts[1])]
            }
        }

        if (data.fps) updateData.fps = data.fps
        if (data.status) updateData.enabled = data.status === 'online'

        const response = await request.put(`/api/v1/cameras/${cameraId}`, updateData)
        return response.data
    } catch (error: any) {
        console.error('更新摄像头失败:', error)
        throw new Error(error.response?.data?.detail || '更新摄像头失败')
    }
}

/**
 * 删除摄像头
 */
export const deleteCamera = async (cameraId: string): Promise<{ message: string }> => {
    try {
        const response = await request.delete(`/api/v1/cameras/${cameraId}`)
        return response.data || { message: '删除成功' }
    } catch (error: any) {
        console.error('删除摄像头失败:', error)
        throw new Error(error.response?.data?.detail || '删除摄像头失败')
    }
}

// ===== 摄像头控制操作 =====

/**
 * 启动摄像头
 */
export const startCamera = async (cameraId: string): Promise<{ message: string }> => {
    try {
        const response = await request.post(`/api/v1/cameras/${cameraId}/start`)
        return response.data || { message: '启动成功' }
    } catch (error: any) {
        console.error('启动摄像头失败:', error)
        throw new Error(error.response?.data?.detail || '启动摄像头失败')
    }
}

/**
 * 停止摄像头
 */
export const stopCamera = async (cameraId: string): Promise<{ message: string }> => {
    try {
        const response = await request.post(`/api/v1/cameras/${cameraId}/stop`)
        return response.data || { message: '停止成功' }
    } catch (error: any) {
        console.error('停止摄像头失败:', error)
        throw new Error(error.response?.data?.detail || '停止摄像头失败')
    }
}

/**
 * 重启摄像头
 */
export const restartCamera = async (cameraId: string): Promise<{ message: string }> => {
    try {
        const response = await request.post(`/api/v1/cameras/${cameraId}/restart`)
        return response.data || { message: '重启成功' }
    } catch (error: any) {
        console.error('重启摄像头失败:', error)
        throw new Error(error.response?.data?.detail || '重启摄像头失败')
    }
}

/**
 * 获取摄像头状态
 */
export const getCameraStatus = async (cameraId: string): Promise<any> => {
    try {
        const response = await request.get(`/api/v1/cameras/${cameraId}/status`)
        return response.data
    } catch (error: any) {
        console.error('获取摄像头状态失败:', error)
        throw new Error(error.response?.data?.detail || '获取摄像头状态失败')
    }
}

/**
 * 获取摄像头日志
 */
export const getCameraLogs = async (cameraId: string, limit: number = 100): Promise<any> => {
    try {
        const response = await request.get(`/api/v1/cameras/${cameraId}/logs`, {
            params: { limit }
        })
        return response.data
    } catch (error: any) {
        console.error('获取摄像头日志失败:', error)
        throw new Error(error.response?.data?.detail || '获取摄像头日志失败')
    }
}

/**
 * 测试摄像头连接
 * 注意：此接口后端暂未实现，需要新增
 */
export const testCamera = async (cameraId: string): Promise<{ success: boolean; message: string; latency?: number }> => {
    // TODO: 等待后端实现此接口
    throw new Error('测试摄像头功能需要后端新增接口：POST /api/v1/cameras/{id}/test')
    // return request.post(`/api/v1/cameras/${cameraId}/test`)
}

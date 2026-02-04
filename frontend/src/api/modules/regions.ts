/**
 * 区域管理 API
 *
 * 提供区域的CRUD操作和导入导出功能
 */

import request from '../index'

/**
 * 区域数据接口
 */
export interface Region {
    id: string
    name: string
    camera_id: string
    camera_name?: string
    points: Array<[number, number]>  // 多边形顶点坐标 [[x1,y1], [x2,y2], ...]
    type: string  // 区域类型：restricted, monitoring, etc.
    color?: string  // 区域颜色（用于前端显示）
    enabled: boolean
    created_at?: string
    updated_at?: string
    description?: string
}

/**
 * 区域创建请求
 */
export interface RegionCreateRequest {
    name: string
    camera_id: string
    points: Array<[number, number]>
    type: string
    color?: string
    enabled?: boolean
    description?: string
}

/**
 * 区域更新请求
 */
export interface RegionUpdateRequest {
    name?: string
    camera_id?: string
    points?: Array<[number, number]>
    type?: string
    color?: string
    enabled?: boolean
    description?: string
}

/**
 * 区域查询参数
 */
export interface RegionQueryParams {
    camera_id?: string
    type?: string
    enabled?: boolean
}

/**
 * 获取区域列表
 *
 * @param params 查询参数
 * @returns 区域列表
 */
export const getRegions = (params?: RegionQueryParams): Promise<Region[]> => {
    return request.get('/api/v1/management/regions', { params })
}

/**
 * 获取单个区域详情
 *
 * @param regionId 区域ID
 * @returns 区域详情
 */
export const getRegion = (regionId: string): Promise<Region> => {
    return request.get(`/api/v1/management/regions/${regionId}`)
}

/**
 * 创建区域
 *
 * @param data 区域数据
 * @returns 创建的区域
 */
export const createRegion = (data: RegionCreateRequest): Promise<Region> => {
    return request.post('/api/v1/management/regions', data)
}

/**
 * 更新区域
 *
 * @param regionId 区域ID
 * @param data 更新数据
 * @returns 更新后的区域
 */
export const updateRegion = (regionId: string, data: RegionUpdateRequest): Promise<Region> => {
    return request.put(`/api/v1/management/regions/${regionId}`, data)
}

/**
 * 删除区域
 *
 * @param regionId 区域ID
 */
export const deleteRegion = (regionId: string): Promise<void> => {
    return request.delete(`/api/v1/management/regions/${regionId}`)
}

/**
 * 批量删除区域
 *
 * @param regionIds 区域ID列表
 */
export const batchDeleteRegions = (regionIds: string[]): Promise<void> => {
    return request.post('/api/v1/management/regions/batch-delete', { ids: regionIds })
}

/**
 * 启用/禁用区域
 *
 * @param regionId 区域ID
 * @param enabled 是否启用
 * @returns 更新后的区域
 */
export const toggleRegionEnabled = (regionId: string, enabled: boolean): Promise<Region> => {
    return request.put(`/api/v1/management/regions/${regionId}`, { enabled })
}

/**
 * 导入区域配置
 *
 * @param file 配置文件
 * @returns 导入结果
 */
export const importRegions = (file: File): Promise<{ success: number; failed: number }> => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/api/v1/management/regions/import', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

/**
 * 导出区域配置
 *
 * @param params 查询参数
 * @returns 配置文件Blob
 */
export const exportRegions = (params?: RegionQueryParams): Promise<Blob> => {
    return request.get('/api/v1/management/regions/export', {
        params,
        responseType: 'blob'
    })
}

/**
 * 获取区域类型列表
 *
 * @returns 区域类型列表
 */
export const getRegionTypes = (): Promise<Array<{ label: string; value: string; color: string }>> => {
    // 前端定义的区域类型
    return Promise.resolve([
        { label: '禁入区域', value: 'restricted', color: '#FF6B6B' },
        { label: '监控区域', value: 'monitoring', color: '#1E9FFF' },
        { label: '警戒区域', value: 'warning', color: '#FF9F43' },
        { label: '安全区域', value: 'safe', color: '#2BC9C9' }
    ])
}

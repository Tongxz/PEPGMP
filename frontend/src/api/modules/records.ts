/**
 * 检测记录 API
 * 适配后端实际接口
 */

import request from '../index'

// ===== 后端实际返回的数据结构 =====

export interface ViolationsResponse {
    violations: any[] // 后端返回的违规记录数组
    total: number
    limit: number
    offset: number
}

// ===== 前端使用的数据结构 =====

export interface DetectionRecord {
    id: string
    camera_id: string
    camera_name?: string
    timestamp: string
    frame_id: number
    detected_objects: number
    violations: ViolationDetail[]
    has_violation: boolean
    status: 'pending' | 'processing' | 'resolved' | 'false_positive'
    image_url?: string
    confidence: number
    processing_time: number
}

export interface ViolationDetail {
    type: string
    description: string
    confidence: number
    bbox?: number[]
}

export interface RecordListResponse {
    records: DetectionRecord[]
    total: number
    page: number
    page_size: number
    total_violations: number
    pending_count: number
    resolved_count: number
}

export interface RecordQueryParams {
    camera_id?: string
    start_time?: string
    end_time?: string
    violation_type?: string
    status?: 'pending' | 'processing' | 'resolved' | 'false_positive'
    page?: number
    page_size?: number
}

export interface RecordUpdateRequest {
    status: 'pending' | 'processing' | 'resolved' | 'false_positive'
    notes?: string
}

/**
 * 获取检测记录列表（原始）
 */
export const getRecordsRaw = (params?: RecordQueryParams): Promise<ViolationsResponse> => {
    const { page, page_size, ...rest } = params || {}

    // 转换分页参数
    const limit = page_size || 20
    const offset = ((page || 1) - 1) * limit

    return request.get('/api/v1/records/violations', {
        params: {
            ...rest,
            limit,
            offset
        }
    })
}

/**
 * 获取检测记录列表（转换为前端格式）
 */
export const getRecords = async (params?: RecordQueryParams): Promise<RecordListResponse> => {
    try {
        const response = await getRecordsRaw(params)

        // 防御性检查：确保violations是数组
        const violations = Array.isArray(response.violations) ? response.violations : []

        // 转换为前端格式
        const records = violations.map((v: any, index: number) => ({
            id: v.id || `violation-${index}`,
            camera_id: v.camera_id || 'unknown',
            camera_name: v.camera_name || '未知摄像头',
            timestamp: v.timestamp || new Date().toISOString(),
            frame_id: v.frame_id || 0,
            detected_objects: v.detected_objects || 0,
            violations: Array.isArray(v.violations) ? v.violations : [],
            has_violation: true,
            status: v.status || 'pending',
            image_url: v.image_url,
            confidence: v.confidence || 0,
            processing_time: v.processing_time || 0
        }))

        // 计算统计（简化版，实际应该从后端获取）
        const pending_count = records.filter((r: DetectionRecord) => r.status === 'pending').length
        const resolved_count = records.filter((r: DetectionRecord) => r.status === 'resolved').length

        return {
            records,
            total: response.total || 0,
            page: params?.page || 1,
            page_size: params?.page_size || 20,
            total_violations: response.total || 0,
            pending_count,
            resolved_count
        }
    } catch (error) {
        console.error('获取检测记录失败:', error)
        throw error
    }
}

/**
 * 获取单条记录详情
 */
export const getRecord = (recordId: string): Promise<DetectionRecord> => {
    return request.get(`/api/v1/records/violations/${recordId}`)
}

/**
 * 更新记录状态
 */
export const updateRecordStatus = async (
    recordId: string,
    data: RecordUpdateRequest
): Promise<DetectionRecord> => {
    try {
        const response = await request.put(`/api/v1/records/violations/${recordId}/status`, {
            status: data.status,
            note: data.notes
        })
        return response.data
    } catch (error: any) {
        console.error('更新记录状态失败:', error)
        throw new Error(error.response?.data?.detail || '更新记录状态失败')
    }
}

/**
 * 批量更新记录状态
 */
export const batchUpdateRecordStatus = async (
    recordIds: string[],
    status: 'pending' | 'processing' | 'resolved' | 'false_positive',
    notes?: string
): Promise<{ updated: number }> => {
    try {
        // 逐个更新（如果后端没有批量接口）
        const promises = recordIds.map(id =>
            updateRecordStatus(id, { status, notes })
        )
        await Promise.all(promises)
        return { updated: recordIds.length }
    } catch (error: any) {
        console.error('批量更新记录状态失败:', error)
        throw new Error(error.message || '批量更新记录状态失败')
    }
}

/**
 * 获取最近违规事件（用于首页）
 */
export const getRecentViolations = (limit: number = 5): Promise<DetectionRecord[]> => {
    return request.get('/api/v1/records/violations', {
        params: {
            limit,
            status: 'pending'
        }
    }).then((res: RecordListResponse) => res.records)
}

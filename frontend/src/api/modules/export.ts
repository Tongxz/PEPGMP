/**
 * 导出功能 API
 * 支持导出违规记录、统计数据等
 */

import request from '../index'

export interface ExportParams {
    start_date?: string
    end_date?: string
    camera_id?: string
    status?: string
    violation_type?: string
    format?: 'csv' | 'xlsx' | 'json'
}

/**
 * 下载文件辅助函数
 */
const downloadFile = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
}

/**
 * 导出违规记录
 */
export const exportViolations = async (params?: ExportParams): Promise<void> => {
    try {
        const format = params?.format || 'csv'
        const response = await request.get('/export/violations', {
            params: {
                ...params,
                format
            },
            responseType: 'blob'
        })

        const filename = `violations_${Date.now()}.${format}`
        downloadFile(response.data, filename)
    } catch (error: any) {
        console.error('导出违规记录失败:', error)
        throw new Error(error.response?.data?.detail || '导出违规记录失败')
    }
}

/**
 * 导出统计数据
 */
export const exportStatistics = async (params?: ExportParams): Promise<void> => {
    try {
        const format = params?.format || 'csv'
        const response = await request.get('/export/statistics', {
            params: {
                ...params,
                format
            },
            responseType: 'blob'
        })

        const filename = `statistics_${Date.now()}.${format}`
        downloadFile(response.data, filename)
    } catch (error: any) {
        console.error('导出统计数据失败:', error)
        throw new Error(error.response?.data?.detail || '导出统计数据失败')
    }
}

/**
 * 导出检测记录
 */
export const exportDetectionRecords = async (params?: ExportParams): Promise<void> => {
    try {
        const format = params?.format || 'csv'
        const response = await request.get('/export/detection-records', {
            params: {
                ...params,
                format
            },
            responseType: 'blob'
        })

        const filename = `detection_records_${Date.now()}.${format}`
        downloadFile(response.data, filename)
    } catch (error: any) {
        console.error('导出检测记录失败:', error)
        throw new Error(error.response?.data?.detail || '导出检测记录失败')
    }
}

/**
 * 导出摄像头列表
 */
export const exportCameras = async (format: 'csv' | 'xlsx' | 'json' = 'csv'): Promise<void> => {
    try {
        const response = await request.get('/export/cameras', {
            params: { format },
            responseType: 'blob'
        })

        const filename = `cameras_${Date.now()}.${format}`
        downloadFile(response.data, filename)
    } catch (error: any) {
        console.error('导出摄像头列表失败:', error)
        throw new Error(error.response?.data?.detail || '导出摄像头列表失败')
    }
}

/**
 * 导出告警记录
 */
export const exportAlerts = async (params?: ExportParams): Promise<void> => {
    try {
        const format = params?.format || 'csv'
        const response = await request.get('/export/alerts', {
            params: {
                ...params,
                format
            },
            responseType: 'blob'
        })

        const filename = `alerts_${Date.now()}.${format}`
        downloadFile(response.data, filename)
    } catch (error: any) {
        console.error('导出告警记录失败:', error)
        throw new Error(error.response?.data?.detail || '导出告警记录失败')
    }
}

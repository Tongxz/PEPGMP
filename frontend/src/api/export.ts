import { http } from '@/lib/http'

export interface ExportParams {
  camera_id?: string
  start_time?: string
  end_time?: string
  format?: 'csv' | 'excel'
  limit?: number
  status?: string
  violation_type?: string
  days?: number
}

/**
 * 导出API客户端
 */
export const exportApi = {
  /**
   * 导出检测记录
   * @param params 导出参数
   */
  async exportDetectionRecords(params: ExportParams): Promise<Blob> {
    const queryParams = new URLSearchParams()
    if (params.camera_id) queryParams.append('camera_id', params.camera_id)
    if (params.start_time) queryParams.append('start_time', params.start_time)
    if (params.end_time) queryParams.append('end_time', params.end_time)
    if (params.format) queryParams.append('format', params.format)
    if (params.limit) queryParams.append('limit', params.limit.toString())

    // 导出请求使用更长的超时时间（120秒）
    const response = await http.get(`/export/detection-records?${queryParams.toString()}`, {
      responseType: 'blob',
      timeout: 120000, // 120秒
    })
    return response.data
  },

  /**
   * 导出违规记录
   * @param params 导出参数
   */
  async exportViolations(params: ExportParams): Promise<Blob> {
    const queryParams = new URLSearchParams()
    if (params.camera_id) queryParams.append('camera_id', params.camera_id)
    if (params.status) queryParams.append('status', params.status)
    if (params.violation_type) queryParams.append('violation_type', params.violation_type)
    if (params.format) queryParams.append('format', params.format)
    if (params.limit) queryParams.append('limit', params.limit.toString())

    // 导出请求使用更长的超时时间（120秒）
    const response = await http.get(`/export/violations?${queryParams.toString()}`, {
      responseType: 'blob',
      timeout: 120000, // 120秒
    })
    return response.data
  },

  /**
   * 导出统计数据
   * @param params 导出参数
   */
  async exportStatistics(params: ExportParams): Promise<Blob> {
    const queryParams = new URLSearchParams()
    if (params.camera_id) queryParams.append('camera_id', params.camera_id)
    if (params.start_time) queryParams.append('start_time', params.start_time)
    if (params.end_time) queryParams.append('end_time', params.end_time)
    if (params.format) queryParams.append('format', params.format)
    if (params.days) queryParams.append('days', params.days.toString())

    // 导出请求使用更长的超时时间（120秒）
    const response = await http.get(`/export/statistics?${queryParams.toString()}`, {
      responseType: 'blob',
      timeout: 120000, // 120秒
    })
    return response.data
  }
}

/**
 * 下载Blob文件
 * @param blob Blob对象
 * @param filename 文件名
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

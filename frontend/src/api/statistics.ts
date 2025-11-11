import { http } from '@/lib/http'

// 统计数据类型
export interface StatisticsSummary {
  window_minutes: number
  total_events: number
  counts_by_type: Record<string, number>
  samples: any[]
}

export interface EventData {
  id: string
  timestamp: string
  type: string
  camera_id: string
  confidence: number
  metadata?: Record<string, any>
}

export interface DailyStatistics {
  date: string
  total_events: number
  counts_by_type: Record<string, number>
}

export interface RealtimeStatistics {
  active_cameras: number
  total_detections: number
  violations_count: number
  compliance_rate: number
  detection_accuracy: number
  recent_events: EventData[]
  [key: string]: any
}

export interface HistoryEvent {
  id: string
  timestamp: string
  camera_id: string
  camera_name?: string
  event_type: string
  confidence?: number
  metadata?: Record<string, any>
}

// 统计API接口
export const statisticsApi = {
  /**
   * 获取统计摘要
   * @param cameraId 可选的摄像头ID
   */
  async getSummary(cameraId?: string): Promise<StatisticsSummary> {
    const params = new URLSearchParams()
    if (cameraId) params.append('camera_id', cameraId)

    const response = await http.get(`/statistics/summary?${params}`)
    return response.data
  },

  /**
   * 获取每日统计数据
   * @param days 天数，默认7天
   * @param cameraId 可选的摄像头ID
   */
  async getDailyStats(days: number = 7, cameraId?: string): Promise<DailyStatistics[]> {
    const params = new URLSearchParams()
    params.append('days', days.toString())
    if (cameraId) params.append('camera_id', cameraId)

    const response = await http.get(`/statistics/daily?${params}`)
    return response.data
  },

  /**
   * 获取事件列表
   * @param params 查询参数
   */
  async getEvents(params: {
    start_time?: string
    end_time?: string
    event_type?: string
    camera_id?: string
    limit?: number
  } = {}): Promise<EventData[]> {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value) queryParams.append(key, value.toString())
    })

    const response = await http.get(`/statistics/events?${queryParams}`)
    return response.data.events || []
  },

  /**
   * 根据时间范围获取事件
   * @param timeRange 时间范围 ('1h', '24h', '7d')
   * @param cameraId 可选的摄像头ID
   */
  async getEventsByTimeRange(timeRange: string, cameraId?: string): Promise<EventData[]> {
    const now = new Date()
    let start: Date

    switch (timeRange) {
      case '1h':
        start = new Date(now.getTime() - 60 * 60 * 1000)
        break
      case '24h':
        start = new Date(now.getTime() - 24 * 60 * 60 * 1000)
        break
      case '7d':
        start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      default:
        start = new Date(now.getTime() - 24 * 60 * 60 * 1000)
    }

    return await this.getEvents({
      start_time: start.toISOString(),
      end_time: now.toISOString(),
      camera_id: cameraId
    })
  },

  /**
   * 根据事件类型获取事件
   * @param eventType 事件类型
   * @param cameraId 可选的摄像头ID
   */
  async getEventsByType(eventType: string, cameraId?: string): Promise<EventData[]> {
    return await this.getEvents({
      event_type: eventType,
      camera_id: cameraId
    })
  },

  /**
   * 根据摄像头获取事件
   * @param cameraId 摄像头ID
   */
  async getEventsByCamera(cameraId: string): Promise<EventData[]> {
    return await this.getEvents({
      camera_id: cameraId
    })
  },

  /**
   * 获取事件统计图表数据
   * @param params 查询参数
   */
  async getChartData(params: {
    start_time?: string
    end_time?: string
    camera_id?: string
    group_by?: 'hour' | 'day' | 'week'
  } = {}) {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value) queryParams.append(key, value.toString())
    })

    const response = await http.get(`/statistics/chart?${queryParams}`)
    return response.data
  },

  /**
   * 导出统计数据
   * @param params 导出参数
   */
  async exportData(params: {
    start_time?: string
    end_time?: string
    camera_id?: string
    format?: 'csv' | 'excel'
  } = {}) {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value) queryParams.append(key, value.toString())
    })

    const response = await http.get(`/statistics/export?${queryParams}`, {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * 获取实时统计数据
   */
  async getRealtimeStats(): Promise<RealtimeStatistics> {
    const response = await http.get('/statistics/realtime')
    return response.data
  },

  /**
   * 获取近期事件历史
   * @param minutes 要查询的最近分钟数，默认60分钟
   * @param limit 返回事件的最大数量，默认100
   * @param cameraId 可选的摄像头ID过滤
   */
  async getHistory(
    minutes: number = 60,
    limit: number = 100,
    cameraId?: string
  ): Promise<HistoryEvent[]> {
    const params = new URLSearchParams()
    params.append('minutes', minutes.toString())
    params.append('limit', limit.toString())
    if (cameraId) params.append('camera_id', cameraId)

    const response = await http.get(`/statistics/history?${params}`)
    return response.data || []
  }
}

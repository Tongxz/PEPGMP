import { statisticsApi, type EventData, type HistoryEvent, type RealtimeStatistics, type StatisticsSummary } from '@/api/statistics'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useStatisticsStore = defineStore('statistics', () => {
  // 状态
  const summary = ref<StatisticsSummary | null>(null)
  const events = ref<EventData[]>([])
  const dailyStats = ref<any[]>([])
  const realtimeStats = ref<RealtimeStatistics | null>(null)
  const historyEvents = ref<HistoryEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 筛选条件
  const selectedTimeRange = ref('24h')
  const selectedCameraId = ref<string>('')
  const selectedEventTypes = ref<string[]>([])

  // 计算属性
  const hasData = computed(() => summary.value !== null)
  const totalEvents = computed(() => summary.value?.total_events || 0)
  const eventTypes = computed(() => {
    if (!summary.value?.counts_by_type) return []
    return Object.keys(summary.value.counts_by_type)
  })
  const eventsByType = computed(() => summary.value?.counts_by_type || {})
  const filteredEvents = computed(() => {
    if (selectedEventTypes.value.length === 0) {
      return events.value
    }
    return events.value.filter(event => selectedEventTypes.value.includes(event.type))
  })

  // 操作
  async function fetchSummary(cameraId?: string) {
    loading.value = true
    error.value = null
    try {
      summary.value = await statisticsApi.getSummary(cameraId)
      return summary.value
    } catch (e: any) {
      error.value = e.message || '获取统计摘要失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchDailyStats(days: number = 7, cameraId?: string) {
    loading.value = true
    error.value = null
    try {
      dailyStats.value = await statisticsApi.getDailyStats(days, cameraId)
    } catch (e: any) {
      error.value = e.message || '获取每日统计失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchEvents(params: {
    start_time?: string
    end_time?: string
    event_type?: string
    camera_id?: string
    limit?: number
  } = {}) {
    loading.value = true
    error.value = null
    try {
      events.value = await statisticsApi.getEvents(params)
      return events.value
    } catch (e: any) {
      error.value = e.message || '获取事件列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchEventsByTimeRange(timeRange: string, cameraId?: string) {
    return await statisticsApi.getEventsByTimeRange(timeRange, cameraId)
  }

  async function fetchEventsByType(eventType: string, cameraId?: string) {
    return await statisticsApi.getEventsByType(eventType, cameraId)
  }

  async function fetchEventsByCamera(cameraId: string) {
    return await statisticsApi.getEventsByCamera(cameraId)
  }

  async function fetchRealtimeStats() {
    loading.value = true
    error.value = null
    try {
      realtimeStats.value = await statisticsApi.getRealtimeStats()
      return realtimeStats.value
    } catch (e: any) {
      error.value = e.message || '获取实时统计失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory(minutes: number = 60, limit: number = 100, cameraId?: string) {
    loading.value = true
    error.value = null
    try {
      historyEvents.value = await statisticsApi.getHistory(minutes, limit, cameraId)
      return historyEvents.value
    } catch (e: any) {
      error.value = e.message || '获取历史记录失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function setSelectedEventTypes(types: string[]) {
    selectedEventTypes.value = types
  }

  function addSelectedEventType(type: string) {
    if (!selectedEventTypes.value.includes(type)) {
      selectedEventTypes.value.push(type)
    }
  }

  function removeSelectedEventType(type: string) {
    selectedEventTypes.value = selectedEventTypes.value.filter(t => t !== type)
  }

  function clearSelectedEventTypes() {
    selectedEventTypes.value = []
  }

  function getEventById(id: string): EventData | undefined {
    return events.value.find(event => event.id === id)
  }

  function getEventsByTimeRange(start: Date, end: Date): EventData[] {
    return events.value.filter(event => {
      const eventTime = new Date(event.timestamp)
      return eventTime >= start && eventTime <= end
    })
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    summary.value = null
    events.value = []
    dailyStats.value = []
    realtimeStats.value = null
    historyEvents.value = []
    loading.value = false
    error.value = null
    selectedTimeRange.value = '24h'
    selectedCameraId.value = ''
    selectedEventTypes.value = []
  }

  return {
    // 状态
    summary,
    events,
    dailyStats,
    realtimeStats,
    historyEvents,
    loading,
    error,
    // 筛选条件
    selectedTimeRange,
    selectedCameraId,
    selectedEventTypes,
    // 计算属性
    hasData,
    totalEvents,
    eventTypes,
    eventsByType,
    filteredEvents,
    // 方法
    fetchSummary,
    fetchDailyStats,
    fetchEvents,
    fetchEventsByTimeRange,
    fetchEventsByType,
    fetchEventsByCamera,
    fetchRealtimeStats,
    fetchHistory,
    setSelectedEventTypes,
    addSelectedEventType,
    removeSelectedEventType,
    clearSelectedEventTypes,
    getEventById,
    getEventsByTimeRange,
    clearError,
    reset
  }
})

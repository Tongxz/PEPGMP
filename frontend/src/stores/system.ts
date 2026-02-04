import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSystemInfo as getSystemInfoAPI, getSystemHealth } from '@/api/modules/system'

export const useSystemStore = defineStore('system', () => {
  // 状态
  const health = ref<string>('')
  const systemInfo = ref<any>(null)
  const loading = ref(false)
  const error = ref<string>('')

  // 计算属性
  const isHealthy = computed(() => health.value === 'OK' || health.value.includes('healthy'))
  const hasSystemInfo = computed(() => systemInfo.value !== null)

  // 将后端返回的数据结构映射为页面期望的结构
  function mapSystemInfoResponse(raw: any) {
    if (!raw || typeof raw !== 'object') return null
    const arch = Array.isArray(raw.system?.architecture) ? raw.system?.architecture?.[0] : raw.system?.architecture
    return {
      status: 'running',
      os: raw.system?.system ?? null,
      version: raw.system?.version ?? null,
      architecture: arch ?? null,
      hostname: raw.system?.hostname ?? null,
      // 时间与网络信息后端暂未提供，保留占位，页面会显示 N/A
      boot_time: raw.boot_time ?? null,
      uptime: raw.uptime ?? null,
      timezone: raw.timezone ?? null,
      ip_address: raw.ip_address ?? null,
      mac_address: raw.mac_address ?? null,
      network_status: raw.network_status ?? null,
      cpu: {
        model: raw.system?.processor ?? null,
        cores: raw.cpu?.count ?? null,
        frequency: raw.cpu?.current_frequency ?? null,
        usage: raw.cpu?.usage_percent ?? null,
      },
      memory: {
        total: raw.memory?.total ?? null,
        used: raw.memory?.used ?? null,
        available: raw.memory?.available ?? null,
      },
      disk: {
        total: raw.disk?.total ?? null,
        used: raw.disk?.used ?? null,
        free: raw.disk?.free ?? null,
      },
      timestamp: raw.timestamp ?? null,
      psutil_available: raw.psutil_available ?? undefined,
    }
  }

  // 操作
  async function checkHealth() {
    loading.value = true
    error.value = ''
    try {
      const data = await getSystemHealth()
      health.value = data.healthy ? 'OK' : 'UNHEALTHY'
      return data
    } catch (e: any) {
      error.value = e.message || '健康检查失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchSystemInfo() {
    loading.value = true
    error.value = ''
    try {
      const data = await getSystemInfoAPI()
      systemInfo.value = mapSystemInfoResponse(data)
      return systemInfo.value
    } catch (e: any) {
      error.value = e.message || '获取系统信息失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = ''
  }

  function reset() {
    health.value = ''
    systemInfo.value = null
    error.value = ''
    loading.value = false
  }

  return {
    // 状态
    health,
    systemInfo,
    loading,
    error,
    // 计算属性
    isHealthy,
    hasSystemInfo,
    // 操作
    checkHealth,
    fetchSystemInfo,
    clearError,
    reset
  }
})

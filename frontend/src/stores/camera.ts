import { cameraApi, type Camera, type RuntimeStatus } from '@/api/camera'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useCameraStore = defineStore('camera', () => {
  // 状态
  const cameras = ref<Camera[]>([])
  const runtimeStatus = ref<Record<string, RuntimeStatus>>({})
  const loading = ref(false)
  const error = ref<string>('')
  const selectedCamera = ref<Camera | null>(null)

  // 计算属性 - 带运行状态的摄像头列表
  const camerasWithStatus = computed(() => {
    return cameras.value.map(cam => ({
      ...cam,
      runtime_status: runtimeStatus.value[cam.id] || {
        running: false,
        pid: 0
      }
    }))
  })

  const enabledCameras = computed(() => cameras.value.filter(cam => cam.enabled))
  const disabledCameras = computed(() => cameras.value.filter(cam => !cam.enabled))
  const cameraCount = computed(() => cameras.value.length)

  // 操作
  async function fetchCameras() {
    loading.value = true
    error.value = ''
    try {
      cameras.value = await cameraApi.getCameras()
      return cameras.value
    } catch (e: any) {
      error.value = e.message || '获取摄像头列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createCamera(cameraData: Omit<Camera, 'enabled'>) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.createCamera(cameraData)
      await fetchCameras() // 重新获取列表
    } catch (e: any) {
      error.value = e.message || '创建摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateCamera(id: string, cameraData: Partial<Camera>) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.updateCamera(id, cameraData)
      await fetchCameras() // 重新获取列表
    } catch (e: any) {
      error.value = e.message || '更新摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.deleteCamera(id)
      cameras.value = cameras.value.filter(cam => cam.id !== id)
      if (selectedCamera.value?.id === id) {
        selectedCamera.value = null
      }
    } catch (e: any) {
      error.value = e.message || '删除摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function selectCamera(camera: Camera | null) {
    selectedCamera.value = camera
  }

  function getCameraById(id: string): Camera | undefined {
    return cameras.value.find(cam => cam.id === id)
  }

  function clearError() {
    error.value = ''
  }

  // 刷新运行状态
  async function refreshRuntimeStatus() {
    try {
      const statuses = await cameraApi.batchGetStatus()
      runtimeStatus.value = statuses
    } catch (e: any) {
      console.error('刷新运行状态失败:', e)
    }
  }

  async function startCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      // 1. 发送启动命令
      await cameraApi.startCamera(id)

      // 2. 等待1秒让进程启动
      await new Promise(resolve => setTimeout(resolve, 1000))

      // 3. 刷新运行状态
      await refreshRuntimeStatus()

      // 4. 验证进程是否真正启动
      const status = runtimeStatus.value[id]
      if (status?.running) {
        return { success: true, message: `摄像头已启动 (PID: ${status.pid})` }
      } else {
        throw new Error('进程未能成功启动，请查看日志')
      }
    } catch (e: any) {
      error.value = e.message || '启动摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function stopCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.stopCamera(id)
      // 立即刷新运行状态
      await refreshRuntimeStatus()
    } catch (e: any) {
      error.value = e.message || '停止摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function refreshAllStatus() {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.refreshAllStatus()
      await fetchCameras() // 重新获取列表以更新状态
    } catch (e: any) {
      error.value = e.message || '刷新摄像头状态失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function activateCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.activateCamera(id)
      await fetchCameras() // 重新获取列表以更新状态
    } catch (e: any) {
      error.value = e.message || '激活摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deactivateCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.deactivateCamera(id)
      await fetchCameras() // 重新获取列表以更新状态
    } catch (e: any) {
      error.value = e.message || '停用摄像头失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function toggleAutoStart(id: string, autoStart: boolean) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.toggleAutoStart(id, autoStart)
      await fetchCameras() // 重新获取列表以更新状态
    } catch (e: any) {
      error.value = e.message || '切换自动启动失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function reset() {
    cameras.value = []
    selectedCamera.value = null
    error.value = ''
    loading.value = false
  }

  return {
    // 状态
    cameras,
    runtimeStatus,
    loading,
    error,
    selectedCamera,
    // 计算属性
    camerasWithStatus,
    enabledCameras,
    disabledCameras,
    cameraCount,
    // 操作
    fetchCameras,
    refreshRuntimeStatus,
    createCamera,
    updateCamera,
    deleteCamera,
    startCamera,
    stopCamera,
    refreshAllStatus,
    activateCamera,
    deactivateCamera,
    toggleAutoStart,
    selectCamera,
    getCameraById,
    clearError,
    reset
  }
})

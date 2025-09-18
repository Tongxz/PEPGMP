import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cameraApi, type Camera } from '@/api/camera'

export const useCameraStore = defineStore('camera', () => {
  // 状态
  const cameras = ref<Camera[]>([])
  const loading = ref(false)
  const error = ref<string>('')
  const selectedCamera = ref<Camera | null>(null)

  // 计算属性
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

  async function startCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      await cameraApi.startCamera(id)
      await fetchCameras() // 重新获取列表以更新状态
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
      await fetchCameras() // 重新获取列表以更新状态
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

  function reset() {
    cameras.value = []
    selectedCamera.value = null
    error.value = ''
    loading.value = false
  }

  return {
    // 状态
    cameras,
    loading,
    error,
    selectedCamera,
    // 计算属性
    enabledCameras,
    disabledCameras,
    cameraCount,
    // 操作
    fetchCameras,
    createCamera,
    updateCamera,
    deleteCamera,
    startCamera,
    stopCamera,
    refreshAllStatus,
    selectCamera,
    getCameraById,
    clearError,
    reset
  }
})

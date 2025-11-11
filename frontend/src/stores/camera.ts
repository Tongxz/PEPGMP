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

  // WebSocket状态（由外部组件管理）
  const wsConnected = ref(false)
  const wsStatusData = ref<Record<string, any>>({})

  // 计算属性 - 带运行状态的摄像头列表
  const camerasWithStatus = computed(() => {
    return cameras.value.map(cam => {
      // 优先使用WebSocket实时数据，回退到轮询数据
      const wsData = wsStatusData.value[cam.id]
      const pollData = runtimeStatus.value[cam.id]

      return {
        ...cam,
        runtime_status: wsData || pollData || {
          running: false,
          pid: 0
        },
        // 添加WebSocket连接状态
        ws_connected: wsConnected.value
      }
    })
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

  // WebSocket状态管理方法
  function updateWebSocketStatus(connected: boolean) {
    wsConnected.value = connected
  }

  function updateWebSocketData(data: Record<string, any>) {
    wsStatusData.value = { ...wsStatusData.value, ...data }
  }

  // 刷新运行状态
  async function refreshRuntimeStatus() {
    try {
      const statuses = await cameraApi.batchGetStatus()

      // 调试：记录接收到的数据
      console.debug('接收到的状态数据:', {
        type: typeof statuses,
        isArray: Array.isArray(statuses),
        isObject: statuses && typeof statuses === 'object' && !Array.isArray(statuses),
        keys: statuses && typeof statuses === 'object' ? Object.keys(statuses) : [],
        data: statuses
      })

      // 合并状态而不是完全替换，避免覆盖已更新的状态
      // 检查是否为对象且不是数组
      if (statuses && typeof statuses === 'object' && !Array.isArray(statuses)) {
        let updatedCount = 0
        const keys = Object.keys(statuses)

        if (keys.length === 0) {
          console.warn('摄像头状态刷新返回空对象（没有摄像头状态）')
          return {}
        }

        keys.forEach(cameraId => {
          const status = statuses[cameraId]
          // 检查状态是否有效（支持两种格式：{ok, running, pid, log} 或 {running, pid, log}）
          if (status && typeof status === 'object' && !Array.isArray(status)) {
            // 如果状态有 ok 字段，检查是否成功
            if (status.ok === false) {
              console.debug(`摄像头 ${cameraId} 状态查询失败: ok=false`)
              return
            }

            // 只更新存在的状态，保留已有的状态
            const oldStatus = runtimeStatus.value[cameraId]
            runtimeStatus.value[cameraId] = {
              running: status.running || false,
              pid: status.pid || 0,
              log: status.log || ''
            }
            // 如果状态发生变化，记录日志（调试用）
            if (oldStatus?.running !== runtimeStatus.value[cameraId].running) {
              console.debug(`摄像头 ${cameraId} 状态更新: ${oldStatus?.running ? '运行中' : '已停止'} -> ${runtimeStatus.value[cameraId].running ? '运行中' : '已停止'}`)
            }
            updatedCount++
          } else {
            console.warn(`摄像头 ${cameraId} 状态格式无效:`, status)
          }
        })

        // 无论是否更新了状态，只要有返回数据就返回（即使所有摄像头都是停止状态）
        // 这样调用方可以知道刷新是成功的，只是没有运行中的摄像头
        console.debug(`摄像头状态刷新完成: 更新了 ${updatedCount} 个摄像头状态，共 ${keys.length} 个摄像头`)
        return statuses
      } else {
        // 如果返回的不是对象（可能是数组或其他类型）
        console.warn('摄像头状态刷新返回的数据格式不正确:', {
          type: typeof statuses,
          isArray: Array.isArray(statuses),
          data: statuses
        })
        return {}
      }
    } catch (e: any) {
      console.error('刷新运行状态失败:', e)
      // 返回空对象，表示刷新失败
      return {}
    }
  }

  async function startCamera(id: string) {
    loading.value = true
    error.value = ''
    try {
      // 1. 发送启动命令
      const startResponse = await cameraApi.startCamera(id)
      const startData = startResponse?.data || startResponse

      // 检查启动API的响应，如果返回了running=true，说明启动成功
      if (startData?.ok && startData?.running) {
        // 启动成功，立即更新状态（确保状态不会被刷新覆盖）
        runtimeStatus.value[id] = {
          running: true,
          pid: startData.pid || 0,
          log: startData.log || ''
        }
        // 等待一小段时间确保状态已保存，避免立即被自动刷新覆盖
        await new Promise(resolve => setTimeout(resolve, 300))
        return {
          success: true,
          message: `摄像头已启动 (PID: ${startData.pid})`
        }
      }

      // 2. 如果启动API没有立即返回running=true，等待进程启动
      await new Promise(resolve => setTimeout(resolve, 1500))

      // 3. 查询单个摄像头状态（更快更准确）
      try {
        const statusResponse = await cameraApi.getCameraStatus(id)
        const statusData = statusResponse?.data || statusResponse
        if (statusData?.ok && statusData?.running) {
          // 状态查询成功，更新状态
          runtimeStatus.value[id] = {
            running: true,
            pid: statusData.pid || 0,
            log: statusData.log || ''
          }
          // 等待一小段时间确保状态已保存
          await new Promise(resolve => setTimeout(resolve, 300))
          return {
            success: true,
            message: `摄像头已启动 (PID: ${statusData.pid})`
          }
        }
      } catch (statusError: any) {
        console.warn('获取摄像头状态失败，尝试刷新所有状态:', statusError)
        // 回退到批量查询，但要注意可能返回空数据
        try {
          await refreshRuntimeStatus()
          // 检查批量查询后的状态
          const status = runtimeStatus.value[id]
          if (status?.running) {
            return { success: true, message: `摄像头已启动 (PID: ${status.pid})` }
          }
        } catch (refreshError: any) {
          console.warn('刷新运行状态失败:', refreshError)
        }
      }

      // 4. 验证进程是否真正启动
      const status = runtimeStatus.value[id]
      if (status?.running) {
        return { success: true, message: `摄像头已启动 (PID: ${status.pid})` }
      } else {
        // 如果状态中没有，再次查询一次（可能是进程刚启动，状态检查还没更新）
        try {
          await new Promise(resolve => setTimeout(resolve, 500))
          const finalStatusResponse = await cameraApi.getCameraStatus(id)
          const finalStatusData = finalStatusResponse?.data || finalStatusResponse
          if (finalStatusData?.ok && finalStatusData?.running) {
            runtimeStatus.value[id] = {
              running: true,
              pid: finalStatusData.pid || 0,
              log: finalStatusData.log || ''
            }
            return {
              success: true,
              message: `摄像头已启动 (PID: ${finalStatusData.pid})`
            }
          }
        } catch (e) {
          // 忽略最后的查询错误
        }
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
      // 1. 调用停止API
      await cameraApi.stopCamera(id)

      // 2. 等待一段时间让进程完全停止（后端最多等待5秒）
      await new Promise(resolve => setTimeout(resolve, 1000))

      // 3. 轮询检查状态，确认进程已停止（最多尝试5次，每次间隔1秒）
      let retryCount = 0
      const maxRetries = 5
      let isStopped = false

      while (retryCount < maxRetries && !isStopped) {
        await refreshRuntimeStatus()

        // 检查该摄像头的状态
        const status = runtimeStatus.value[id]
        if (!status || !status.running) {
          isStopped = true
          break
        }

        // 如果还在运行，等待后重试
        retryCount++
        if (retryCount < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
      }

      // 4. 最后再刷新一次状态，确保UI更新
      await refreshRuntimeStatus()

      // 如果经过多次尝试后进程仍在运行，给出警告但不抛出错误
      // 因为进程可能正在停止过程中，后端会在超时后强制kill
      const finalStatus = runtimeStatus.value[id]
      if (finalStatus?.running) {
        console.warn(`摄像头 ${id} 停止中，可能需要更长时间`)
      }
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
    // WebSocket状态管理
    updateWebSocketStatus,
    updateWebSocketData,
    reset
  }
})

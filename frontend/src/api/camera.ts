import { http } from '@/lib/http'

// 摄像头数据类型
export interface Camera {
  id: string
  name: string
  source: string
  resolution?: string
  fps?: number
  enabled?: boolean      // 兼容旧字段
  active?: boolean       // 是否激活（允许使用）
  auto_start?: boolean   // 是否自动启动
  regions_file?: string
  profile?: string
  device?: string
  imgsz?: string | number
}

// 摄像头API接口
export const cameraApi = {
  /**
   * 获取摄像头列表
   */
  async getCameras() {
    const response = await http.get<{ cameras: Camera[] }>('/cameras')
    return response.data.cameras || []
  },

  /**
   * 创建摄像头
   * @param cameraData 摄像头数据
   */
  async createCamera(cameraData: Omit<Camera, 'enabled'>) {
    return await http.post('/cameras', cameraData)
  },

  /**
   * 更新摄像头
   * @param id 摄像头ID
   * @param cameraData 更新的摄像头数据
   */
  async updateCamera(id: string, cameraData: Partial<Camera>) {
    return await http.put(`/cameras/${encodeURIComponent(id)}`, cameraData)
  },

  /**
   * 删除摄像头
   * @param id 摄像头ID
   */
  async deleteCamera(id: string) {
    return await http.delete(`/cameras/${encodeURIComponent(id)}`)
  },

  /**
   * 获取单个摄像头信息
   * @param id 摄像头ID
   */
  async getCameraById(id: string) {
    const response = await http.get(`/cameras/${encodeURIComponent(id)}`)
    return response.data
  },

  /**
   * 启用/禁用摄像头
   * @param id 摄像头ID
   * @param enabled 是否启用
   */
  async toggleCamera(id: string, enabled: boolean) {
    return await http.put(`/cameras/${encodeURIComponent(id)}`, { enabled })
  },

  /**
   * 启动摄像头
   * @param id 摄像头ID
   */
  async startCamera(id: string) {
    return await http.post(`/cameras/${encodeURIComponent(id)}/start`)
  },

  /**
   * 停止摄像头
   * @param id 摄像头ID
   */
  async stopCamera(id: string) {
    return await http.post(`/cameras/${encodeURIComponent(id)}/stop`)
  },

  /**
   * 刷新所有摄像头状态
   */
  async refreshAllStatus() {
    return await http.post('/cameras/refresh')
  },

  /**
   * 获取摄像头详细统计信息
   * @param id 摄像头ID
   */
  async getCameraStats(id: string) {
    const response = await http.get(`/cameras/${encodeURIComponent(id)}/stats`)
    return response.data
  },

  /**
   * 获取摄像头日志
   * @param id 摄像头ID
   * @param lines 返回的日志行数（默认100）
   */
  async getCameraLogs(id: string, lines: number = 100) {
    const response = await http.get(`/cameras/${encodeURIComponent(id)}/logs`, {
      params: { lines }
    })
    return response.data
  },

  /**
   * 获取摄像头状态
   * @param id 摄像头ID
   */
  async getCameraStatus(id: string) {
    const response = await http.get(`/cameras/${encodeURIComponent(id)}/status`)
    return response.data
  },

  /**
   * 激活摄像头
   * @param id 摄像头ID
   */
  async activateCamera(id: string) {
    return await http.post(`/cameras/${encodeURIComponent(id)}/activate`)
  },

  /**
   * 停用摄像头（会先停止运行中的进程）
   * @param id 摄像头ID
   */
  async deactivateCamera(id: string) {
    return await http.post(`/cameras/${encodeURIComponent(id)}/deactivate`)
  },

  /**
   * 切换自动启动设置
   * @param id 摄像头ID
   * @param autoStart 是否自动启动
   */
  async toggleAutoStart(id: string, autoStart: boolean) {
    return await http.put(`/cameras/${encodeURIComponent(id)}/auto-start?auto_start=${autoStart}`)
  }
}

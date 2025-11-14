import { http } from '@/lib/http'

/**
 * 视频流配置接口
 */
export interface VideoStreamConfig {
  camera_id: string
  stream_interval: number
  log_interval: number
  frame_by_frame: boolean
}

/**
 * 视频流配置请求
 */
export interface VideoStreamConfigRequest {
  stream_interval?: number
  log_interval?: number
  frame_by_frame?: boolean
}

/**
 * 视频流配置响应
 */
export interface VideoStreamConfigResponse {
  camera_id: string
  stream_interval: number
  log_interval: number
  frame_by_frame: boolean
  message: string
}

/**
 * 视频流API接口
 */
export const videoStreamApi = {
  /**
   * 获取视频流配置
   * @param cameraId 摄像头ID
   */
  async getConfig(cameraId: string): Promise<VideoStreamConfig> {
    const response = await http.get<VideoStreamConfig>(`/video-stream/config/${cameraId}`)
    return response.data
  },

  /**
   * 更新视频流配置
   * @param cameraId 摄像头ID
   * @param config 配置数据
   */
  async updateConfig(
    cameraId: string,
    config: VideoStreamConfigRequest
  ): Promise<VideoStreamConfigResponse> {
    const response = await http.post<VideoStreamConfigResponse>(
      `/video-stream/config/${cameraId}`,
      config
    )
    return response.data
  },

  /**
   * 获取视频流统计
   */
  async getStats() {
    const response = await http.get('/video-stream/stats')
    return response.data
  },

  /**
   * 获取摄像头视频流状态
   * @param cameraId 摄像头ID
   */
  async getStatus(cameraId: string) {
    const response = await http.get(`/video-stream/status/${cameraId}`)
    return response.data
  },
}

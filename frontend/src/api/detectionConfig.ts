/**
 * 检测配置API
 */

import { http } from '@/lib/http'

export interface HumanDetectionConfig {
  confidence_threshold: number
  iou_threshold: number
  min_box_area: number
  min_width: number
  min_height: number
  max_detections: number
}

export interface HairnetDetectionConfig {
  confidence_threshold: number
  total_score_threshold: number
}

export interface BehaviorRecognitionConfig {
  confidence_threshold: number
  handwashing_stability_frames: number
  sanitizing_stability_frames: number
}

export interface DetectionConfig {
  human_detection: HumanDetectionConfig
  hairnet_detection: HairnetDetectionConfig
  behavior_recognition: BehaviorRecognitionConfig
  message?: string
}

export interface DetectionConfigRequest {
  human_detection?: Partial<HumanDetectionConfig>
  hairnet_detection?: Partial<HairnetDetectionConfig>
  behavior_recognition?: Partial<BehaviorRecognitionConfig>
}

export interface DetectionConfigResponse {
  ok: boolean
  message: string
  updated_fields: string[]
  apply_immediately: boolean
  note: string
}

export const detectionConfigApi = {
  /**
   * 获取检测配置
   */
  async getConfig(): Promise<DetectionConfig> {
    const response = await http.get<DetectionConfig>('/api/v1/detection-config')
    return response.data
  },

  /**
   * 更新检测配置
   */
  async updateConfig(
    config: DetectionConfigRequest,
    applyImmediately: boolean = false
  ): Promise<DetectionConfigResponse> {
    const response = await http.put<DetectionConfigResponse>(
      `/api/v1/detection-config?apply_immediately=${applyImmediately}`,
      config
    )
    return response.data
  },
}

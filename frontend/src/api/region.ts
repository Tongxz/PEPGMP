import { http } from '@/lib/http'

// 区域数据类型
export interface Region {
  id: string
  name: string
  type: 'entrance' | 'handwash' | 'sanitize' | 'work_area' | 'restricted' | 'monitoring'
  description?: string
  rules: {
    requireHairnet: boolean
    limitOccupancy: boolean
    timeRestriction: boolean
  }
  maxOccupancy?: number
  points: Array<{ x: number; y: number }>
  enabled: boolean
}

// 后端返回的区域结构（宽松类型）
interface BackendRegionAny {
  id?: string
  name?: string
  type?: string
  points?: Array<{ x: number; y: number }> | Array<[number, number]>
  enabled?: boolean
  // 标准管理接口字段
  region_id?: string
  region_type?: string
  polygon?: Array<{ x: number; y: number }> | Array<[number, number]>
  is_active?: boolean
  rules?: Record<string, any>
  description?: string
}

function toPointArray(src: any): Array<{ x: number; y: number }> {
  if (!Array.isArray(src)) return []
  // 处理形如 [[x,y], [x,y]]
  if (src.length > 0 && Array.isArray(src[0]) && src[0].length === 2) {
    return (src as Array<[number, number]>).map(([x, y]) => ({ x, y }))
  }
  // 处理已是 {x,y}
  if (src.length > 0 && typeof src[0] === 'object' && 'x' in src[0] && 'y' in src[0]) {
    return (src as Array<{ x: number; y: number }>).map(p => ({ x: p.x, y: p.y }))
  }
  return []
}

function normalizeRegion(item: BackendRegionAny): Region {
  const id = item.region_id || item.id || `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  const type = (item.region_type || item.type || 'custom') as Region['type']
  const points = toPointArray(item.polygon ?? item.points ?? [])
  const enabled = (item.is_active ?? item.enabled ?? true) as boolean
  // 简单规则映射（后端可能返回更丰富的rules，这里做兼容降级）
  const rules = {
    requireHairnet: Boolean(item.rules?.requireHairnet) || false,
    limitOccupancy: Boolean(item.rules?.limitOccupancy) || false,
    timeRestriction: Boolean(item.rules?.timeRestriction) || false
  }
  return {
    id: String(id),
    name: item.name || '',
    type,
    description: item.description || '',
    rules,
    points,
    enabled
  }
}

function toBackendRegionPayload(regionData: Partial<Region>): any {
  const payload: { [key: string]: any } = {}

  // 生成 region_id（如果没有提供 id）
  if (regionData.id) {
    payload.region_id = regionData.id
  } else {
    payload.region_id = `region_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }

  if (regionData.name) payload.name = regionData.name
  if (regionData.type) payload.region_type = regionData.type
  if (regionData.points) payload.polygon = regionData.points.map(p => [p.x, p.y])
  if (regionData.enabled !== undefined) payload.is_active = regionData.enabled
  if (regionData.rules) payload.rules = regionData.rules
  if (regionData.description) payload.description = regionData.description
  return payload
}

// 区域API接口
export const regionApi = {
  /**
   * 获取区域列表
   * @param cameraId 可选的摄像头ID过滤
   */
  async getRegions(cameraId?: string): Promise<Region[]> {
    const params = new URLSearchParams()
    if (cameraId) params.append('camera_id', cameraId)

    const response = await http.get(`management/regions?${params}`)
    const data = response.data as any

    // 兼容两种返回：数组 或 { regions: [...] }
    const list: BackendRegionAny[] = Array.isArray(data)
      ? data
      : Array.isArray(data?.regions)
        ? data.regions
        : []

    return list.map(normalizeRegion)
  },

  /**
   * 创建区域
   * @param regionData 区域数据
   */
  async createRegion(regionData: Omit<Region, 'id'>): Promise<Region> {
    const payload = toBackendRegionPayload(regionData)
    const response = await http.post('management/regions', payload)
    return normalizeRegion(response.data)
  },

  /**
   * 更新区域
   * @param id 区域ID
   * @param regionData 更新的区域数据
   */
  async updateRegion(id: string, regionData: Partial<Region>): Promise<Region> {
    const payload = toBackendRegionPayload(regionData)
    const response = await http.put(`management/regions/${encodeURIComponent(id)}`, payload)
    return normalizeRegion(response.data)
  },

  /**
   * 删除区域
   * @param id 区域ID
   */
  async deleteRegion(id: string): Promise<void> {
    await http.delete(`management/regions/${encodeURIComponent(id)}`)
  },

  /**
   * 获取单个区域信息
   * @param id 区域ID
   */
  async getRegionById(id: string): Promise<Region> {
    const response = await http.get(`management/regions/${encodeURIComponent(id)}`)
    return response.data
  },

  /**
   * 批量保存区域配置
   * @param regions 区域列表
   */
  async saveRegions(regions: Region[]): Promise<void> {
    await http.post('management/regions/batch', { regions })
  },

  /**
   * 清空所有区域
   */
  async clearRegions(): Promise<void> {
    await http.delete('management/regions')
  },

  /**
   * 启用/禁用区域
   * @param id 区域ID
   * @param enabled 是否启用
   */
  async toggleRegion(id: string, enabled: boolean): Promise<Region> {
    const response = await http.put(`management/regions/${encodeURIComponent(id)}`, { enabled })
    return response.data
  },

  /**
   * 获取区域统计信息
   * @param id 区域ID
   */
  async getRegionStats(id: string): Promise<any> {
    const response = await http.get(`management/regions/${encodeURIComponent(id)}/stats`)
    return response.data
  },

  /**
   * 验证区域配置
   * @param regionData 区域数据
   */
  async validateRegion(regionData: Partial<Region>): Promise<{ valid: boolean; errors?: string[] }> {
    const response = await http.post('management/regions/validate', regionData)
    return response.data
  },

  /**
   * 导入区域配置
   * @param file 配置文件
   */
  async importRegions(file: File): Promise<Region[]> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await http.post('management/regions/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    const data = response.data as any
    const list: BackendRegionAny[] = Array.isArray(data?.regions) ? data.regions : []
    return list.map(normalizeRegion)
  },

  /**
   * 导出区域配置
   * @param format 导出格式 ('json' | 'yaml')
   */
  async exportRegions(format: 'json' | 'yaml' = 'json'): Promise<Blob> {
    const response = await http.get(`management/regions/export?format=${format}`, {
      responseType: 'blob'
    })
    return response.data
  }
}

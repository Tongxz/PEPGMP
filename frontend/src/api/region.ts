import { http } from '@/lib/http'

// 区域数据类型
export interface Region {
  id: string
  name: string
  type: 'entrance' | 'handwash' | 'sanitize' | 'work_area' | 'restricted' | 'monitoring' | 'custom'
  description?: string
  rules: {
    requireHairnet: boolean
    limitOccupancy: boolean
    timeRestriction: boolean
  }
  maxOccupancy?: number
  points: Array<{ x: number; y: number }>
  enabled: boolean
  // UI 扩展字段（前端配置用，不一定由后端提供）
  sensitivity?: number
  minDuration?: number
  alertEnabled?: boolean
  alertLevel?: 'low' | 'medium' | 'high' | 'critical'
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

// 后端API响应类型（与BackendRegionAny相同，用于HTTP响应类型标注）
type RegionResponse = BackendRegionAny

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
  // UI 扩展字段默认值（若后端未提供则使用前端默认）
  const sensitivity = typeof item.rules?.sensitivity === 'number' ? item.rules.sensitivity : 0.8
  const minDuration = typeof item.rules?.minDuration === 'number' ? item.rules.minDuration : 5
  const alertEnabled = typeof item.rules?.alertEnabled === 'boolean' ? item.rules.alertEnabled : false
  const alertLevel = (item.rules?.alertLevel as Region['alertLevel']) ?? 'medium'

  return {
    id: String(id),
    name: item.name || '',
    type,
    description: item.description || '',
    rules,
    points,
    enabled,
    sensitivity,
    minDuration,
    alertEnabled,
    alertLevel
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
  // 注意：UI 扩展字段（sensitivity、minDuration、alertEnabled、alertLevel）不直接提交到后端，
  // 若后端支持可在此进行映射
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

    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.get<RegionResponse[]>(`/api/v1/management/regions?camera_id=${cameraId}`);
    const data = response.data as any
    // 兼容两种返回：数组 或 { regions: [...] }
    const list: BackendRegionAny[] = Array.isArray(data)
      ? data
      : Array.isArray(data?.regions)
        ? data.regions
        : []
    return list.map(normalizeRegion)
  },

  async createRegion(regionData: Omit<Region, 'id'>): Promise<Region> {
    const payload = toBackendRegionPayload(regionData)
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.post<RegionResponse>(`/api/v1/management/regions`, toBackendRegionPayload(regionData)); return normalizeRegion(response.data);
  },

  async updateRegion(id: string, regionData: Partial<Region>): Promise<Region> {
    const payload = toBackendRegionPayload(regionData)
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.put<RegionResponse>(`/api/v1/management/regions/${id}`, toBackendRegionPayload(regionData)); return normalizeRegion(response.data);
  },

  async deleteRegion(id: string): Promise<void> {
    // 与后端路由前缀 /api/v1/management 对齐
    await http.delete(`/api/v1/management/regions/${encodeURIComponent(id)}`);
  },

  async getRegionById(id: string): Promise<Region> {
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.get(`api/v1/management/regions/${encodeURIComponent(id)}`)
    return normalizeRegion(response.data)
  },

  async saveRegions(regions: Region[]): Promise<void> {
    // 与后端路由前缀 /api/v1/management 对齐
    await http.post('api/v1/management/regions/batch', { regions })
  },

  async clearRegions(): Promise<void> {
    // 与后端路由前缀 /api/v1/management 对齐
    await http.delete('api/v1/management/regions')
  },

  async toggleRegion(id: string, enabled: boolean): Promise<Region> {
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.put(`api/v1/management/regions/${encodeURIComponent(id)}`, { enabled })
    return normalizeRegion(response.data)
  },

  async getRegionStats(id: string): Promise<any> {
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.get(`api/v1/management/regions/${encodeURIComponent(id)}/stats`)
    return response.data
  },

  async validateRegion(regionData: Partial<Region>): Promise<{ valid: boolean; errors?: string[] }> {
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.post('api/v1/management/regions/validate', regionData)
    return response.data
  },

  async importRegions(file: File): Promise<Region[]> {
    const formData = new FormData()
    formData.append('file', file)

    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.post('api/v1/management/regions/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    const data = response.data as any
    const list: BackendRegionAny[] = Array.isArray(data?.regions) ? data.regions : []
    return list.map(normalizeRegion)
  },

  async exportRegions(format: 'json' | 'yaml' = 'json'): Promise<Blob> {
    // 与后端路由前缀 /api/v1/management 对齐
    const response = await http.get(`api/v1/management/regions/export?format=${format}`, {
      responseType: 'blob'
    })
    return response.data
  }
}

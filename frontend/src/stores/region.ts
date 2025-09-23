import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { regionApi, type Region } from '@/api/region'

export const useRegionStore = defineStore('region', () => {
  // 状态
  const regions = ref<Region[]>([])
  const loading = ref(false)
  const error = ref<string>('')
  const selectedRegion = ref<Region | null>(null)
  const isDrawing = ref(false)
  const currentDrawingPoints = ref<Array<{ x: number; y: number }>>([])

  // 画布相关状态
  const canvasSize = ref({ width: 800, height: 450 })
  const backgroundImage = ref<HTMLImageElement | null>(null)

  // 计算属性
  const enabledRegions = computed(() => regions.value.filter(region => region.enabled))
  const regionsByType = computed(() => {
    const grouped: Record<string, Region[]> = {}
    regions.value.forEach(region => {
      if (!grouped[region.type]) {
        grouped[region.type] = []
      }
      grouped[region.type].push(region)
    })
    return grouped
  })
  const regionCount = computed(() => regions.value.length)

  // 操作
  async function fetchRegions(cameraId?: string) {
    loading.value = true
    error.value = ''
    try {
      regions.value = await regionApi.getRegions(cameraId)
    } catch (e: any) {
      error.value = e.message || '获取区域列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveRegion(regionData: Omit<Region, 'id' | 'enabled'>) {
    loading.value = true
    error.value = ''
    try {
      const newRegion: Region = {
        ...regionData,
        id: `region_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        enabled: true
      }
      regions.value.push(newRegion)
      return newRegion
    } catch (e: any) {
      error.value = e.message || '保存区域失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateRegion(id: string, regionData: Partial<Region>) {
    loading.value = true
    error.value = ''
    try {
      const updatedRegion = await regionApi.updateRegion(id, regionData)
      const index = regions.value.findIndex(region => region.id === id)
      if (index !== -1) {
        regions.value[index] = updatedRegion
      }
    } catch (e: any) {
      error.value = e.message || '更新区域失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createRegion(regionData: Omit<Region, 'id'>): Promise<Region> {
    loading.value = true
    error.value = ''
    try {
      const created = await regionApi.createRegion(regionData)
      regions.value.push(created)
      return created
    } catch (e: any) {
      error.value = e.message || '创建区域失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteRegion(id: string) {
    loading.value = true
    error.value = ''
    try {
      await regionApi.deleteRegion(id)
      regions.value = regions.value.filter(region => region.id !== id)
      if (selectedRegion.value?.id === id) {
        selectedRegion.value = null
      }
    } catch (e: any) {
      error.value = e.message || '删除区域失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function clearRegions() {
    loading.value = true
    error.value = ''
    try {
      await regionApi.clearRegions()
      regions.value = []
      selectedRegion.value = null
    } catch (e: any) {
      error.value = e.message || '清空区域失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveRegions(regionsToSave: Region[]) {
    loading.value = true
    error.value = ''
    try {
      await regionApi.saveRegions(regionsToSave)
      regions.value = [...regionsToSave]
    } catch (e: any) {
      error.value = e.message || '保存区域失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function selectRegion(region: Region | null) {
    selectedRegion.value = region
  }

  function startDrawing() {
    isDrawing.value = true
    currentDrawingPoints.value = []
  }

  function addDrawingPoint(point: { x: number; y: number }) {
    if (isDrawing.value) {
      currentDrawingPoints.value.push(point)
    }
  }

  async function finishDrawing(): Promise<Region> {
    if (currentDrawingPoints.value.length < 3) {
      cancelDrawing()
      throw new Error('需要至少3个点来创建多边形区域。')
    }
    isDrawing.value = false
    const points = [...currentDrawingPoints.value]
    currentDrawingPoints.value = []

    try {
      const newRegionData: Omit<Region, 'id'> = {
        name: `新区域 ${regions.value.length + 1}`,
        type: 'work_area',
        description: '新创建的多边形区域',
        rules: {
          requireHairnet: false,
          limitOccupancy: false,
          timeRestriction: false
        },
        points: points,
        enabled: true
      }

      const newRegion = await createRegion(newRegionData)
      selectRegion(newRegion)
      return newRegion
    } catch (e) {
      console.error('创建区域失败:', e)
      throw e
    }
  }

  function cancelDrawing() {
    isDrawing.value = false
    currentDrawingPoints.value = []
  }

  function setCanvasSize(width: number, height: number) {
    canvasSize.value = { width, height }
  }

  function setBackgroundImage(image: HTMLImageElement | null) {
    backgroundImage.value = image
  }

  function getRegionById(id: string): Region | undefined {
    return regions.value.find(region => region.id === id)
  }

  function clearError() {
    error.value = ''
  }

  function reset() {
    regions.value = []
    loading.value = false
    error.value = ''
    selectedRegion.value = null
    isDrawing.value = false
    currentDrawingPoints.value = []
  }

  return {
    // 状态
    regions,
    loading,
    error,
    selectedRegion,
    isDrawing,
    currentDrawingPoints,
    canvasSize,
    backgroundImage,
    // 计算属性
    enabledRegions,
    regionsByType,
    regionCount,
    // 方法
    fetchRegions,
    createRegion,
    saveRegion,
    updateRegion,
    deleteRegion,
    clearRegions,
    saveRegions,
    selectRegion,
    startDrawing,
    addDrawingPoint,
    finishDrawing,
    cancelDrawing,
    setCanvasSize,
    setBackgroundImage,
    getRegionById,
    clearError,
    reset
  }
})

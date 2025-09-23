/**
 * 区域配置管理器
 * 基于原始设计的RegionConfigManager重新实现
 */

export interface Point {
  x: number
  y: number
}

export interface RegionConfig {
  id: string
  name: string
  type: string
  points: Point[]
  color: string
  enabled: boolean
  rules?: Record<string, any>
}

export interface CanvasConfig {
  width: number
  height: number
  scale: number
  offsetX: number
  offsetY: number
}

export class RegionConfigManager {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private regions: Map<string, RegionConfig> = new Map()
  private selectedRegion: string | null = null
  private isDrawing = false
  private currentPoints: Point[] = []
  private draggedVertex: { regionId: string; vertexIndex: number } | null = null
  private canvasConfig: CanvasConfig
  private backgroundImage: HTMLImageElement | null = null

  // 区域颜色配置（基于原始设计）
  private readonly colors = {
    entrance: '#52C41A',    // 成功绿
    work_area: '#3A7AFE',   // 品牌蓝
    restricted: '#FF4D4F',  // 危险红
    monitoring: '#FAAD14',  // 警告橙
    handwash: '#1890FF',    // 洗手区蓝色
    sanitize: '#722ED1',    // 消毒区紫色
    custom: '#722ED1'       // 强调紫
  }

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')!
    this.canvasConfig = {
      width: canvas.width,
      height: canvas.height,
      scale: 1,
      offsetX: 0,
      offsetY: 0
    }
    this.initEventListeners()
  }

  /**
   * 坐标转换函数（基于原始设计）
   * 将鼠标事件坐标转换为画布坐标
   */
  getCanvasCoordinates(event: MouseEvent): Point {
    const rect = this.canvas.getBoundingClientRect()
    const mouseX = event.clientX - rect.left
    const mouseY = event.clientY - rect.top

    const scaleX = this.canvas.width / rect.width
    const scaleY = this.canvas.height / rect.height
    const x = Math.round(mouseX * scaleX)
    const y = Math.round(mouseY * scaleY)

    return { x, y }
  }

  /**
   * 将画布坐标转换为实际坐标
   */
  canvasToActualCoordinates(point: Point): Point {
    return {
      x: (point.x - this.canvasConfig.offsetX) / this.canvasConfig.scale,
      y: (point.y - this.canvasConfig.offsetY) / this.canvasConfig.scale
    }
  }

  /**
   * 将实际坐标转换为画布坐标
   */
  actualToCanvasCoordinates(point: Point): Point {
    return {
      x: point.x * this.canvasConfig.scale + this.canvasConfig.offsetX,
      y: point.y * this.canvasConfig.scale + this.canvasConfig.offsetY
    }
  }

  /**
   * 初始化事件监听器
   */
  private initEventListeners() {
    this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this))
    this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this))
    this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this))
    this.canvas.addEventListener('dblclick', this.onDoubleClick.bind(this))
    this.canvas.addEventListener('contextmenu', this.onContextMenu.bind(this))
  }

  /**
   * 鼠标按下事件处理
   */
  private onMouseDown(event: MouseEvent) {
    const point = this.getCanvasCoordinates(event)

    // 检查是否点击了顶点（用于拖拽编辑）
    const vertex = this.getVertexAtPoint(point)
    if (vertex) {
      this.draggedVertex = vertex
      return
    }

    // 检查是否点击了区域（用于选择）
    const clickedRegion = this.getRegionAtPoint(point)
    if (clickedRegion) {
      this.selectRegion(clickedRegion.id)
      this.render()
      return
    }

    // 如果在绘制模式，添加点
    if (this.isDrawing) {
      this.currentPoints.push(point)
      this.render()
    }
  }

  /**
   * 鼠标移动事件处理
   */
  private onMouseMove(event: MouseEvent) {
    const point = this.getCanvasCoordinates(event)

    // 处理顶点拖拽
    if (this.draggedVertex) {
      const region = this.regions.get(this.draggedVertex.regionId)
      if (region) {
        region.points[this.draggedVertex.vertexIndex] = point
        this.render()
      }
      return
    }

    // 绘制模式下显示临时线条
    if (this.isDrawing && this.currentPoints.length > 0) {
      this.render()
      this.drawTemporaryLine(point)
    }
  }

  /**
   * 鼠标释放事件处理
   */
  private onMouseUp(event: MouseEvent) {
    if (this.draggedVertex) {
      // 完成顶点拖拽，触发保存事件
      this.onRegionChanged(this.draggedVertex.regionId)
      this.draggedVertex = null
    }
  }

  /**
   * 双击事件处理（完成绘制）
   */
  private onDoubleClick(event: MouseEvent) {
    if (this.isDrawing && this.currentPoints.length >= 3) {
      this.finishDrawing()
    }
  }

  /**
   * 右键菜单事件处理
   */
  private onContextMenu(event: MouseEvent) {
    event.preventDefault()
    // 可以在这里添加右键菜单功能
  }

  /**
   * 开始绘制新区域
   */
  startDrawing(regionType: string = 'custom') {
    this.isDrawing = true
    this.currentPoints = []
    this.selectedRegion = null
    this.canvas.style.cursor = 'crosshair'
  }

  /**
   * 完成绘制
   */
  finishDrawing() {
    if (this.currentPoints.length < 3) {
      return
    }

    const regionId = this.generateRegionId()
    const region: RegionConfig = {
      id: regionId,
      name: `区域 ${this.regions.size + 1}`,
      type: 'custom',
      points: [...this.currentPoints],
      color: this.colors.custom,
      enabled: true
    }

    this.regions.set(regionId, region)
    this.isDrawing = false
    this.currentPoints = []
    this.canvas.style.cursor = 'default'
    this.selectRegion(regionId)
    this.render()

    // 触发区域创建事件
    this.onRegionCreated(region)
  }

  /**
   * 取消绘制
   */
  cancelDrawing() {
    this.isDrawing = false
    this.currentPoints = []
    this.canvas.style.cursor = 'default'
    this.render()
  }

  /**
   * 选择区域
   */
  selectRegion(regionId: string | null) {
    this.selectedRegion = regionId
    this.render()
  }

  /**
   * 删除区域
   */
  deleteRegion(regionId: string) {
    this.regions.delete(regionId)
    if (this.selectedRegion === regionId) {
      this.selectedRegion = null
    }
    this.render()
    this.onRegionDeleted(regionId)
  }

  /**
   * 更新区域配置
   */
  updateRegion(regionId: string, config: Partial<RegionConfig>) {
    const region = this.regions.get(regionId)
    if (region) {
      Object.assign(region, config)
      if (config.type && this.colors[config.type as keyof typeof this.colors]) {
        region.color = this.colors[config.type as keyof typeof this.colors]
      }
      this.render()
      this.onRegionChanged(regionId)
    }
  }

  /**
   * 设置背景图片
   */
  setBackgroundImage(image: HTMLImageElement) {
    this.backgroundImage = image
    this.fitImageToCanvas()
    this.render()
  }

  /**
   * 适配图片到画布
   */
  private fitImageToCanvas() {
    if (!this.backgroundImage) return

    const canvasRatio = this.canvas.width / this.canvas.height
    const imageRatio = this.backgroundImage.width / this.backgroundImage.height

    if (imageRatio > canvasRatio) {
      // 图片更宽，以宽度为准
      this.canvasConfig.scale = this.canvas.width / this.backgroundImage.width
      this.canvasConfig.offsetX = 0
      this.canvasConfig.offsetY = (this.canvas.height - this.backgroundImage.height * this.canvasConfig.scale) / 2
    } else {
      // 图片更高，以高度为准
      this.canvasConfig.scale = this.canvas.height / this.backgroundImage.height
      this.canvasConfig.offsetX = (this.canvas.width - this.backgroundImage.width * this.canvasConfig.scale) / 2
      this.canvasConfig.offsetY = 0
    }
  }

  /**
   * 渲染画布
   */
  render() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)

    // 绘制背景图片
    if (this.backgroundImage) {
      this.ctx.drawImage(
        this.backgroundImage,
        this.canvasConfig.offsetX,
        this.canvasConfig.offsetY,
        this.backgroundImage.width * this.canvasConfig.scale,
        this.backgroundImage.height * this.canvasConfig.scale
      )
    }

    // 绘制所有区域
    this.regions.forEach(region => {
      this.drawRegion(region, region.id === this.selectedRegion)
    })

    // 绘制当前绘制的点
    if (this.isDrawing) {
      this.drawCurrentPoints()
    }
  }

  /**
   * 绘制区域
   */
  private drawRegion(region: RegionConfig, isSelected: boolean) {
    if (region.points.length < 2) return

    this.ctx.save()

    // 绘制区域填充
    this.ctx.beginPath()
    this.ctx.moveTo(region.points[0].x, region.points[0].y)
    for (let i = 1; i < region.points.length; i++) {
      this.ctx.lineTo(region.points[i].x, region.points[i].y)
    }
    this.ctx.closePath()

    this.ctx.fillStyle = region.color + '30' // 30% 透明度
    this.ctx.fill()

    // 绘制区域边框
    this.ctx.strokeStyle = region.color
    this.ctx.lineWidth = isSelected ? 3 : 2
    this.ctx.stroke()

    // 绘制顶点
    if (isSelected) {
      region.points.forEach((point, index) => {
        this.ctx.beginPath()
        this.ctx.arc(point.x, point.y, 6, 0, 2 * Math.PI)
        this.ctx.fillStyle = '#ffffff'
        this.ctx.fill()
        this.ctx.strokeStyle = region.color
        this.ctx.lineWidth = 2
        this.ctx.stroke()
      })
    }

    this.ctx.restore()
  }

  /**
   * 绘制当前绘制的点
   */
  private drawCurrentPoints() {
    if (this.currentPoints.length === 0) return

    this.ctx.save()

    // 绘制已有的线段
    if (this.currentPoints.length > 1) {
      this.ctx.beginPath()
      this.ctx.moveTo(this.currentPoints[0].x, this.currentPoints[0].y)
      for (let i = 1; i < this.currentPoints.length; i++) {
        this.ctx.lineTo(this.currentPoints[i].x, this.currentPoints[i].y)
      }
      this.ctx.strokeStyle = '#1890ff'
      this.ctx.lineWidth = 2
      this.ctx.stroke()
    }

    // 绘制点
    this.currentPoints.forEach(point => {
      this.ctx.beginPath()
      this.ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI)
      this.ctx.fillStyle = '#1890ff'
      this.ctx.fill()
    })

    this.ctx.restore()
  }

  /**
   * 绘制临时线条
   */
  private drawTemporaryLine(currentPoint: Point) {
    if (this.currentPoints.length === 0) return

    this.ctx.save()
    this.ctx.beginPath()
    const lastPoint = this.currentPoints[this.currentPoints.length - 1]
    this.ctx.moveTo(lastPoint.x, lastPoint.y)
    this.ctx.lineTo(currentPoint.x, currentPoint.y)
    this.ctx.strokeStyle = '#1890ff'
    this.ctx.lineWidth = 1
    this.ctx.setLineDash([5, 5])
    this.ctx.stroke()
    this.ctx.restore()
  }

  /**
   * 获取指定点处的顶点
   */
  private getVertexAtPoint(point: Point): { regionId: string; vertexIndex: number } | null {
    for (const [regionId, region] of this.regions) {
      for (let i = 0; i < region.points.length; i++) {
        const vertex = region.points[i]
        const distance = Math.sqrt(Math.pow(point.x - vertex.x, 2) + Math.pow(point.y - vertex.y, 2))
        if (distance <= 8) { // 8像素的点击容差
          return { regionId, vertexIndex: i }
        }
      }
    }
    return null
  }

  /**
   * 获取指定点处的区域
   */
  private getRegionAtPoint(point: Point): RegionConfig | null {
    for (const region of this.regions.values()) {
      if (this.isPointInRegion(point, region.points)) {
        return region
      }
    }
    return null
  }

  /**
   * 判断点是否在多边形内
   */
  private isPointInRegion(point: Point, polygon: Point[]): boolean {
    let inside = false
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      if (((polygon[i].y > point.y) !== (polygon[j].y > point.y)) &&
          (point.x < (polygon[j].x - polygon[i].x) * (point.y - polygon[i].y) / (polygon[j].y - polygon[i].y) + polygon[i].x)) {
        inside = !inside
      }
    }
    return inside
  }

  /**
   * 生成区域ID
   */
  private generateRegionId(): string {
    return 'region_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
  }

  /**
   * 获取所有区域
   */
  getRegions(): RegionConfig[] {
    return Array.from(this.regions.values())
  }

  /**
   * 获取选中的区域
   */
  getSelectedRegion(): RegionConfig | null {
    return this.selectedRegion ? this.regions.get(this.selectedRegion) || null : null
  }

  /**
   * 清空所有区域
   */
  clearRegions() {
    this.regions.clear()
    this.selectedRegion = null
    this.render()
  }

  /**
   * 导出配置
   */
  exportConfig() {
    return {
      regions: this.getRegions(),
      canvasConfig: this.canvasConfig,
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 导入配置
   */
  importConfig(config: any) {
    this.regions.clear()
    if (config.regions) {
      config.regions.forEach((region: RegionConfig) => {
        this.regions.set(region.id, region)
      })
    }
    if (config.canvasConfig) {
      this.canvasConfig = { ...this.canvasConfig, ...config.canvasConfig }
    }
    this.render()
  }

  // 事件回调（可以被外部重写）
  onRegionCreated(region: RegionConfig) {
    console.log('Region created:', region)
  }

  onRegionChanged(regionId: string) {
    console.log('Region changed:', regionId)
  }

  onRegionDeleted(regionId: string) {
    console.log('Region deleted:', regionId)
  }
}

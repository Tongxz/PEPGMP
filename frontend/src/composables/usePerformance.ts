import { ref, onMounted, onUnmounted, nextTick } from 'vue'

export interface PerformanceMetrics {
  // 页面加载性能
  loadTime: number
  domContentLoaded: number
  firstPaint: number
  firstContentfulPaint: number
  largestContentfulPaint: number

  // 运行时性能
  memoryUsage: number
  frameRate: number

  // 网络性能
  networkLatency: number
  resourceLoadTime: number

  // 用户体验指标
  timeToInteractive: number
  cumulativeLayoutShift: number
}

export interface ResourceInfo {
  name: string
  type: string
  size: number
  loadTime: number
  cached: boolean
}

export function usePerformance() {
  const metrics = ref<Partial<PerformanceMetrics>>({})
  const resources = ref<ResourceInfo[]>([])
  const isMonitoring = ref(false)
  const frameRateHistory = ref<number[]>([])

  let frameRateTimer: number | null = null
  let performanceObserver: PerformanceObserver | null = null
  let lastFrameTime = 0
  let frameCount = 0

  // 获取页面加载性能指标
  const getLoadPerformance = (): Partial<PerformanceMetrics> => {
    if (!window.performance) return {}

    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
    const paint = performance.getEntriesByType('paint')

    const loadMetrics: Partial<PerformanceMetrics> = {}

    if (navigation) {
      loadMetrics.loadTime = navigation.loadEventEnd - navigation.fetchStart
      loadMetrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.fetchStart
      loadMetrics.timeToInteractive = navigation.domInteractive - navigation.fetchStart
    }

    paint.forEach((entry) => {
      if (entry.name === 'first-paint') {
        loadMetrics.firstPaint = entry.startTime
      } else if (entry.name === 'first-contentful-paint') {
        loadMetrics.firstContentfulPaint = entry.startTime
      }
    })

    return loadMetrics
  }

  // 获取内存使用情况
  const getMemoryUsage = (): number => {
    if ('memory' in performance) {
      const memory = (performance as any).memory
      return memory.usedJSHeapSize / 1024 / 1024 // MB
    }
    return 0
  }

  // 监控帧率
  const startFrameRateMonitoring = () => {
    let lastTime = performance.now()
    let frameCount = 0

    const measureFrameRate = (currentTime: number) => {
      frameCount++

      if (currentTime - lastTime >= 1000) {
        const fps = Math.round((frameCount * 1000) / (currentTime - lastTime))
        frameRateHistory.value.push(fps)

        // 保持最近30秒的数据
        if (frameRateHistory.value.length > 30) {
          frameRateHistory.value.shift()
        }

        metrics.value.frameRate = fps
        frameCount = 0
        lastTime = currentTime
      }

      if (isMonitoring.value) {
        requestAnimationFrame(measureFrameRate)
      }
    }

    requestAnimationFrame(measureFrameRate)
  }

  // 获取资源加载信息
  const getResourceInfo = (): ResourceInfo[] => {
    if (!window.performance) return []

    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[]

    return resources.map(resource => ({
      name: resource.name.split('/').pop() || resource.name,
      type: getResourceType(resource.name),
      size: resource.transferSize || 0,
      loadTime: resource.responseEnd - resource.requestStart,
      cached: resource.transferSize === 0 && resource.decodedBodySize > 0
    }))
  }

  // 获取资源类型
  const getResourceType = (url: string): string => {
    const extension = url.split('.').pop()?.toLowerCase()

    const typeMap: { [key: string]: string } = {
      js: 'JavaScript',
      css: 'CSS',
      png: 'Image',
      jpg: 'Image',
      jpeg: 'Image',
      gif: 'Image',
      svg: 'Image',
      webp: 'Image',
      woff: 'Font',
      woff2: 'Font',
      ttf: 'Font',
      json: 'JSON',
      xml: 'XML'
    }

    return typeMap[extension || ''] || 'Other'
  }

  // 测量网络延迟
  const measureNetworkLatency = async (): Promise<number> => {
    const start = performance.now()

    try {
      await fetch('/api/ping', {
        method: 'GET',
        cache: 'no-cache'
      })
      return performance.now() - start
    } catch {
      return -1
    }
  }

  // 监控 LCP (Largest Contentful Paint)
  const observeLCP = () => {
    if (!window.PerformanceObserver) return

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lastEntry = entries[entries.length - 1]
      metrics.value.largestContentfulPaint = lastEntry.startTime
    })

    observer.observe({ entryTypes: ['largest-contentful-paint'] })
    return observer
  }

  // 监控 CLS (Cumulative Layout Shift)
  const observeCLS = () => {
    if (!window.PerformanceObserver) return

    let clsValue = 0
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!(entry as any).hadRecentInput) {
          clsValue += (entry as any).value
          metrics.value.cumulativeLayoutShift = clsValue
        }
      }
    })

    observer.observe({ entryTypes: ['layout-shift'] })
    return observer
  }

  // 开始性能监控
  const startMonitoring = async () => {
    if (isMonitoring.value) return

    isMonitoring.value = true

    // 获取初始指标
    metrics.value = {
      ...metrics.value,
      ...getLoadPerformance(),
      memoryUsage: getMemoryUsage()
    }

    // 获取资源信息
    resources.value = getResourceInfo()

    // 测量网络延迟
    try {
      metrics.value.networkLatency = await measureNetworkLatency()
    } catch {
      metrics.value.networkLatency = -1
    }

    // 开始帧率监控
    startFrameRateMonitoring()

    // 开始性能观察
    const lcpObserver = observeLCP()
    const clsObserver = observeCLS()
    performanceObserver = lcpObserver || clsObserver || null
  }

  // 停止性能监控
  const stopMonitoring = () => {
    isMonitoring.value = false

    if (frameRateTimer) {
      cancelAnimationFrame(frameRateTimer)
      frameRateTimer = null
    }

    if (performanceObserver) {
      performanceObserver.disconnect()
      performanceObserver = null
    }
  }

  // 获取性能评分
  const getPerformanceScore = (): number => {
    const weights = {
      loadTime: 0.3,
      firstContentfulPaint: 0.2,
      largestContentfulPaint: 0.2,
      frameRate: 0.15,
      cumulativeLayoutShift: 0.15
    }

    let score = 100
    const m = metrics.value

    // 加载时间评分 (目标: <2s)
    if (m.loadTime) {
      const loadScore = Math.max(0, 100 - (m.loadTime / 2000) * 100)
      score -= (100 - loadScore) * weights.loadTime
    }

    // FCP评分 (目标: <1.8s)
    if (m.firstContentfulPaint) {
      const fcpScore = Math.max(0, 100 - (m.firstContentfulPaint / 1800) * 100)
      score -= (100 - fcpScore) * weights.firstContentfulPaint
    }

    // LCP评分 (目标: <2.5s)
    if (m.largestContentfulPaint) {
      const lcpScore = Math.max(0, 100 - (m.largestContentfulPaint / 2500) * 100)
      score -= (100 - lcpScore) * weights.largestContentfulPaint
    }

    // 帧率评分 (目标: 60fps)
    if (m.frameRate) {
      const fpsScore = Math.min(100, (m.frameRate / 60) * 100)
      score -= (100 - fpsScore) * weights.frameRate
    }

    // CLS评分 (目标: <0.1)
    if (m.cumulativeLayoutShift !== undefined) {
      const clsScore = Math.max(0, 100 - (m.cumulativeLayoutShift / 0.1) * 100)
      score -= (100 - clsScore) * weights.cumulativeLayoutShift
    }

    return Math.max(0, Math.round(score))
  }

  // 获取性能建议
  const getPerformanceSuggestions = (): string[] => {
    const suggestions: string[] = []
    const m = metrics.value

    if (m.loadTime && m.loadTime > 3000) {
      suggestions.push('页面加载时间过长，考虑优化资源大小或使用CDN')
    }

    if (m.firstContentfulPaint && m.firstContentfulPaint > 2000) {
      suggestions.push('首次内容绘制时间较长，考虑优化关键渲染路径')
    }

    if (m.frameRate && m.frameRate < 30) {
      suggestions.push('帧率较低，检查是否有性能密集型操作')
    }

    if (m.memoryUsage && m.memoryUsage > 100) {
      suggestions.push('内存使用量较高，检查是否有内存泄漏')
    }

    if (m.cumulativeLayoutShift && m.cumulativeLayoutShift > 0.1) {
      suggestions.push('布局偏移较大，确保图片和广告有明确的尺寸')
    }

    // 检查资源优化建议
    const largeResources = resources.value.filter(r => r.size > 1024 * 1024) // >1MB
    if (largeResources.length > 0) {
      suggestions.push(`发现${largeResources.length}个大型资源，考虑压缩或延迟加载`)
    }

    const uncachedResources = resources.value.filter(r => !r.cached && r.type !== 'Other')
    if (uncachedResources.length > 5) {
      suggestions.push('多个资源未被缓存，考虑设置适当的缓存策略')
    }

    return suggestions
  }

  // 导出性能报告
  const exportReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      metrics: metrics.value,
      resources: resources.value,
      frameRateHistory: frameRateHistory.value,
      score: getPerformanceScore(),
      suggestions: getPerformanceSuggestions(),
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    }

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json'
    })

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `performance-report-${Date.now()}.json`
    a.click()

    URL.revokeObjectURL(url)
  }

  // 性能优化工具
  const optimizationTools = {
    // 预加载关键资源
    preloadResource: (url: string, type: 'script' | 'style' | 'image' | 'font') => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.href = url
      link.as = type
      if (type === 'font') {
        link.crossOrigin = 'anonymous'
      }
      document.head.appendChild(link)
    },

    // 延迟加载图片
    lazyLoadImages: () => {
      if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              const img = entry.target as HTMLImageElement
              if (img.dataset.src) {
                img.src = img.dataset.src
                img.removeAttribute('data-src')
                imageObserver.unobserve(img)
              }
            }
          })
        })

        document.querySelectorAll('img[data-src]').forEach(img => {
          imageObserver.observe(img)
        })
      }
    },

    // 防抖函数
    debounce: <T extends (...args: any[]) => any>(
      func: T,
      wait: number
    ): ((...args: Parameters<T>) => void) => {
      let timeout: number
      return (...args: Parameters<T>) => {
        clearTimeout(timeout)
        timeout = window.setTimeout(() => func.apply(null, args), wait)
      }
    },

    // 节流函数
    throttle: <T extends (...args: any[]) => any>(
      func: T,
      limit: number
    ): ((...args: Parameters<T>) => void) => {
      let inThrottle: boolean
      return (...args: Parameters<T>) => {
        if (!inThrottle) {
          func.apply(null, args)
          inThrottle = true
          setTimeout(() => inThrottle = false, limit)
        }
      }
    }
  }

  // 生命周期
  onMounted(() => {
    // 页面加载完成后开始监控
    nextTick(() => {
      setTimeout(startMonitoring, 1000)
    })
  })

  onUnmounted(() => {
    stopMonitoring()
  })

  return {
    // 状态
    metrics,
    resources,
    isMonitoring,
    frameRateHistory,

    // 方法
    startMonitoring,
    stopMonitoring,
    getPerformanceScore,
    getPerformanceSuggestions,
    exportReport,
    measureNetworkLatency,

    // 工具
    optimizationTools
  }
}
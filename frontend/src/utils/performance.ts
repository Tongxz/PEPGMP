/**
 * 性能优化工具函数
 */

// 防抖函数
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate = false
): (...args: Parameters<T>) => void {
  let timeout: number | null = null

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      if (!immediate) func(...args)
    }

    const callNow = immediate && !timeout

    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(later, wait)

    if (callNow) func(...args)
  }
}

// 节流函数
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

// 延迟执行
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// 请求动画帧节流
export function rafThrottle<T extends (...args: any[]) => any>(
  func: T
): (...args: Parameters<T>) => void {
  let rafId: number | null = null

  return function executedFunction(...args: Parameters<T>) {
    if (rafId) return

    rafId = requestAnimationFrame(() => {
      func(...args)
      rafId = null
    })
  }
}

// 空闲时执行
export function runWhenIdle<T extends (...args: any[]) => any>(
  func: T,
  timeout = 5000
): (...args: Parameters<T>) => void {
  return function executedFunction(...args: Parameters<T>) {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(
        () => func(...args),
        { timeout }
      )
    } else {
      // 降级到 setTimeout
      setTimeout(() => func(...args), 0)
    }
  }
}

// 批量执行
export class BatchProcessor<T> {
  private batch: T[] = []
  private processor: (items: T[]) => void
  private delay: number
  private timeoutId: number | null = null

  constructor(processor: (items: T[]) => void, delay = 100) {
    this.processor = processor
    this.delay = delay
  }

  add(item: T): void {
    this.batch.push(item)
    this.scheduleBatch()
  }

  private scheduleBatch(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId)
    }

    this.timeoutId = setTimeout(() => {
      if (this.batch.length > 0) {
        this.processor([...this.batch])
        this.batch = []
      }
      this.timeoutId = null
    }, this.delay)
  }

  flush(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId)
      this.timeoutId = null
    }

    if (this.batch.length > 0) {
      this.processor([...this.batch])
      this.batch = []
    }
  }
}

// 内存缓存
export class MemoryCache<K, V> {
  private cache = new Map<K, { value: V; expiry: number }>()
  private maxSize: number
  private defaultTTL: number

  constructor(maxSize = 100, defaultTTL = 5 * 60 * 1000) {
    this.maxSize = maxSize
    this.defaultTTL = defaultTTL
  }

  set(key: K, value: V, ttl = this.defaultTTL): void {
    // 如果缓存已满，删除最旧的项
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      if (firstKey !== undefined) {
        this.cache.delete(firstKey)
      }
    }

    const expiry = Date.now() + ttl
    this.cache.set(key, { value, expiry })
  }

  get(key: K): V | undefined {
    const item = this.cache.get(key)

    if (!item) return undefined

    if (Date.now() > item.expiry) {
      this.cache.delete(key)
      return undefined
    }

    return item.value
  }

  has(key: K): boolean {
    return this.get(key) !== undefined
  }

  delete(key: K): boolean {
    return this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
  }

  size(): number {
    // 清理过期项
    const now = Date.now()
    for (const [key, item] of this.cache.entries()) {
      if (now > item.expiry) {
        this.cache.delete(key)
      }
    }
    return this.cache.size
  }
}

// 图片懒加载
export function createImageLoader(): {
  loadImage: (src: string) => Promise<HTMLImageElement>
  preloadImages: (srcs: string[]) => Promise<HTMLImageElement[]>
} {
  const cache = new Set<string>()

  const loadImage = (src: string): Promise<HTMLImageElement> => {
    return new Promise((resolve, reject) => {
      if (cache.has(src)) {
        const img = new Image()
        img.src = src
        resolve(img)
        return
      }

      const img = new Image()
      img.onload = () => {
        cache.add(src)
        resolve(img)
      }
      img.onerror = reject
      img.src = src
    })
  }

  const preloadImages = (srcs: string[]): Promise<HTMLImageElement[]> => {
    return Promise.all(srcs.map(loadImage))
  }

  return { loadImage, preloadImages }
}

// 虚拟滚动辅助函数
export function calculateVirtualScrollItems(
  containerHeight: number,
  itemHeight: number,
  scrollTop: number,
  totalItems: number,
  overscan = 5
): {
  startIndex: number
  endIndex: number
  visibleItems: number
  offsetY: number
} {
  const visibleItems = Math.ceil(containerHeight / itemHeight)
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan)
  const endIndex = Math.min(totalItems - 1, startIndex + visibleItems + overscan * 2)
  const offsetY = startIndex * itemHeight

  return {
    startIndex,
    endIndex,
    visibleItems,
    offsetY
  }
}

// 性能监控
export class PerformanceMonitor {
  private marks = new Map<string, number>()
  private measures = new Map<string, number>()

  mark(name: string): void {
    this.marks.set(name, performance.now())
  }

  measure(name: string, startMark: string, endMark?: string): number {
    const startTime = this.marks.get(startMark)
    if (!startTime) {
      // 静默处理缺失的标记，避免控制台警告
      return 0
    }

    const endTime = endMark ? this.marks.get(endMark) : performance.now()
    if (endMark && !endTime) {
      // 静默处理缺失的结束标记
      return 0
    }

    const duration = (endTime || performance.now()) - startTime
    this.measures.set(name, duration)

    return duration
  }

  getMeasure(name: string): number | undefined {
    return this.measures.get(name)
  }

  clear(): void {
    this.marks.clear()
    this.measures.clear()
  }

  report(): Record<string, number> {
    return Object.fromEntries(this.measures)
  }
}

// 资源预加载
export function preloadResource(href: string, as: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const link = document.createElement('link')
    link.rel = 'preload'
    link.href = href
    link.as = as
    link.onload = () => resolve()
    link.onerror = reject
    document.head.appendChild(link)
  })
}

// 代码分割辅助
export function createAsyncComponent<T>(
  loader: () => Promise<T>,
  options: {
    delay?: number
    timeout?: number
    errorComponent?: any
    loadingComponent?: any
  } = {}
) {
  const {
    delay = 200,
    timeout = 10000,
    errorComponent,
    loadingComponent
  } = options

  return {
    loader,
    delay,
    timeout,
    errorComponent,
    loadingComponent
  }
}

// Web Worker 辅助
export function createWorker(workerFunction: Function): Worker {
  const blob = new Blob([`(${workerFunction.toString()})()`], {
    type: 'application/javascript'
  })
  return new Worker(URL.createObjectURL(blob))
}

// 内存使用监控
export function getMemoryUsage(): {
  used: number
  total: number
  percentage: number
} | null {
  if ('memory' in performance) {
    const memory = (performance as any).memory
    return {
      used: memory.usedJSHeapSize,
      total: memory.totalJSHeapSize,
      percentage: (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
    }
  }
  return null
}

// 导出全局性能监控实例
export const performanceMonitor = new PerformanceMonitor()

// 导出全局图片加载器
export const imageLoader = createImageLoader()

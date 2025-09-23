/**
 * 性能监控插件
 */
import type { App } from 'vue'
import { performanceMonitor, debounce } from '@/utils/performance'

// 性能监控配置
interface PerformanceConfig {
  // 是否启用性能监控
  enabled?: boolean
  // 是否启用路由性能监控
  routeTracking?: boolean
  // 是否启用组件性能监控
  componentTracking?: boolean
  // 是否启用API性能监控
  apiTracking?: boolean
  // 性能数据上报间隔（毫秒）
  reportInterval?: number
  // 性能数据上报URL
  reportUrl?: string
  // 是否在控制台输出性能数据
  consoleOutput?: boolean
}

// 默认配置
const defaultConfig: PerformanceConfig = {
  enabled: true,
  routeTracking: true,
  componentTracking: true,
  apiTracking: true,
  reportInterval: 30000, // 30秒
  consoleOutput: import.meta.env.DEV
}

// 性能数据收集器
class PerformanceCollector {
  private config: PerformanceConfig
  private routeMetrics: Map<string, number[]> = new Map()
  private componentMetrics: Map<string, number[]> = new Map()
  private apiMetrics: Map<string, number[]> = new Map()
  private reportTimer: number | null = null

  constructor(config: PerformanceConfig) {
    this.config = { ...defaultConfig, ...config }
    this.startReporting()
  }

  // 记录路由性能
  recordRoute(routeName: string, duration: number) {
    if (!this.config.routeTracking) return

    if (!this.routeMetrics.has(routeName)) {
      this.routeMetrics.set(routeName, [])
    }

    const metrics = this.routeMetrics.get(routeName)!
    metrics.push(duration)

    // 保持最近100条记录
    if (metrics.length > 100) {
      metrics.shift()
    }
  }

  // 记录组件性能
  recordComponent(componentName: string, duration: number) {
    if (!this.config.componentTracking) return

    if (!this.componentMetrics.has(componentName)) {
      this.componentMetrics.set(componentName, [])
    }

    const metrics = this.componentMetrics.get(componentName)!
    metrics.push(duration)

    // 保持最近100条记录
    if (metrics.length > 100) {
      metrics.shift()
    }
  }

  // 记录API性能
  recordApi(apiPath: string, duration: number) {
    if (!this.config.apiTracking) return

    if (!this.apiMetrics.has(apiPath)) {
      this.apiMetrics.set(apiPath, [])
    }

    const metrics = this.apiMetrics.get(apiPath)!
    metrics.push(duration)

    // 保持最近100条记录
    if (metrics.length > 100) {
      metrics.shift()
    }
  }

  // 计算统计数据
  private calculateStats(metrics: number[]) {
    if (metrics.length === 0) return null

    const sorted = [...metrics].sort((a, b) => a - b)
    const sum = metrics.reduce((a, b) => a + b, 0)

    return {
      count: metrics.length,
      avg: sum / metrics.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      p50: sorted[Math.floor(sorted.length * 0.5)],
      p90: sorted[Math.floor(sorted.length * 0.9)],
      p95: sorted[Math.floor(sorted.length * 0.95)]
    }
  }

  // 生成性能报告
  generateReport() {
    const report = {
      timestamp: Date.now(),
      routes: {} as Record<string, any>,
      components: {} as Record<string, any>,
      apis: {} as Record<string, any>,
      memory: null as any,
      navigation: null as any
    }

    // 路由性能统计
    for (const [route, metrics] of this.routeMetrics.entries()) {
      const stats = this.calculateStats(metrics)
      if (stats) {
        report.routes[route] = stats
      }
    }

    // 组件性能统计
    for (const [component, metrics] of this.componentMetrics.entries()) {
      const stats = this.calculateStats(metrics)
      if (stats) {
        report.components[component] = stats
      }
    }

    // API性能统计
    for (const [api, metrics] of this.apiMetrics.entries()) {
      const stats = this.calculateStats(metrics)
      if (stats) {
        report.apis[api] = stats
      }
    }

    // 内存使用情况
    if ('memory' in performance) {
      const memory = (performance as any).memory
      report.memory = {
        used: memory.usedJSHeapSize,
        total: memory.totalJSHeapSize,
        limit: memory.jsHeapSizeLimit,
        percentage: (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
      }
    }

    // 导航性能
    if ('getEntriesByType' in performance) {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      if (navigation) {
        report.navigation = {
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
          loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
          firstPaint: 0,
          firstContentfulPaint: 0
        }

        // 获取绘制性能
        const paintEntries = performance.getEntriesByType('paint')
        for (const entry of paintEntries) {
          if (entry.name === 'first-paint') {
            report.navigation.firstPaint = entry.startTime
          } else if (entry.name === 'first-contentful-paint') {
            report.navigation.firstContentfulPaint = entry.startTime
          }
        }
      }
    }

    return report
  }

  // 开始定期上报
  private startReporting() {
    if (!this.config.enabled || !this.config.reportInterval) return

    const report = debounce(() => {
      const data = this.generateReport()

      if (this.config.consoleOutput) {
        console.group('🚀 Performance Report')
        console.table(data.routes)
        console.table(data.components)
        console.table(data.apis)
        if (data.memory) {
          console.log('Memory Usage:', data.memory)
        }
        if (data.navigation) {
          console.log('Navigation Timing:', data.navigation)
        }
        console.groupEnd()
      }

      // 上报到服务器
      if (this.config.reportUrl) {
        fetch(this.config.reportUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        }).catch(error => {
          console.warn('Performance report failed:', error)
        })
      }
    }, 1000)

    this.reportTimer = window.setInterval(report, this.config.reportInterval)
  }

  // 停止上报
  destroy() {
    if (this.reportTimer) {
      clearInterval(this.reportTimer)
      this.reportTimer = null
    }
  }
}

// 全局性能收集器实例
let collector: PerformanceCollector | null = null

// Vue性能监控指令
const performanceDirective = {
  mounted(el: HTMLElement, binding: any) {
    const componentName = binding.arg || el.tagName.toLowerCase()
    const startTime = performance.now()

    // 监听组件挂载完成
    requestAnimationFrame(() => {
      const duration = performance.now() - startTime
      collector?.recordComponent(componentName, duration)
    })
  }
}

// 性能监控插件
export const performancePlugin = {
  install(app: App, options: PerformanceConfig = {}) {
    const config = { ...defaultConfig, ...options }

    if (!config.enabled) return

    // 创建性能收集器
    collector = new PerformanceCollector(config)

    // 注册全局指令
    app.directive('perf', performanceDirective)

    // 提供全局方法
    app.config.globalProperties.$perf = {
      recordRoute: (name: string, duration: number) => collector?.recordRoute(name, duration),
      recordComponent: (name: string, duration: number) => collector?.recordComponent(name, duration),
      recordApi: (path: string, duration: number) => collector?.recordApi(path, duration),
      generateReport: () => collector?.generateReport(),
      mark: (name: string) => performanceMonitor.mark(name),
      measure: (name: string, start: string, end?: string) => performanceMonitor.measure(name, start, end)
    }

    // 监听路由变化（如果使用Vue Router）
    if (config.routeTracking) {
      app.mixin({
        beforeRouteEnter(to, from, next) {
          // 确保路由名称存在再创建标记
          if (to.name) {
            performanceMonitor.mark(`route-${String(to.name)}-start`)
          }
          next()
        },
        mounted() {
          if (this.$route && this.$route.name) {
            const routeName = String(this.$route.name)
            const duration = performanceMonitor.measure(
              `route-${routeName}`,
              `route-${routeName}-start`
            )
            // 只有在成功测量到时间时才记录
            if (duration > 0) {
              collector?.recordRoute(routeName, duration)
            }
          }
        }
      })
    }

    // 监听组件性能（如果启用）
    if (config.componentTracking) {
      app.mixin({
        beforeCreate() {
          if (this.$options.name) {
            performanceMonitor.mark(`component-${this.$options.name}-start`)
          }
        },
        mounted() {
          if (this.$options.name) {
            const duration = performanceMonitor.measure(
              `component-${this.$options.name}`,
              `component-${this.$options.name}-start`
            )
            collector?.recordComponent(this.$options.name, duration)
          }
        }
      })
    }

    // 应用销毁时清理
    app.config.globalProperties.$onBeforeUnmount?.(() => {
      collector?.destroy()
    })
  }
}

// 导出工具函数
export const recordApiPerformance = (path: string, duration: number) => {
  collector?.recordApi(path, duration)
}

export const generatePerformanceReport = () => {
  return collector?.generateReport()
}

// 创建API性能监控装饰器
export function withApiPerformance<T extends (...args: any[]) => Promise<any>>(
  apiFunction: T,
  apiPath: string
): T {
  return (async (...args: any[]) => {
    const startTime = performance.now()
    try {
      const result = await apiFunction(...args)
      const duration = performance.now() - startTime
      recordApiPerformance(apiPath, duration)
      return result
    } catch (error) {
      const duration = performance.now() - startTime
      recordApiPerformance(`${apiPath}:error`, duration)
      throw error
    }
  }) as T
}

// 默认导出
export default performancePlugin

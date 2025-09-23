/**
 * 异步数据管理组合式函数
 */
import { ref, computed, watch, onUnmounted, readonly, type Ref } from 'vue'
import { MemoryCache } from '@/utils/performance'

export interface AsyncDataOptions<T> {
  // 默认值
  default?: T
  // 缓存键
  key?: string
  // 缓存时间（毫秒）
  cacheTTL?: number
  // 是否立即执行
  immediate?: boolean
  // 重试次数
  retries?: number
  // 重试延迟（毫秒）
  retryDelay?: number
  // 依赖项，当依赖变化时重新获取数据
  dependencies?: Ref<any>[]
  // 错误处理函数
  onError?: (error: Error) => void
  // 成功回调
  onSuccess?: (data: T) => void
}

export interface AsyncDataState<T> {
  data: Ref<T | null>
  pending: Ref<boolean>
  error: Ref<Error | null>
  refresh: () => Promise<void>
  execute: () => Promise<void>
  clear: () => void
}

// 全局缓存实例
const globalCache = new MemoryCache<string, any>(50, 5 * 60 * 1000)

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  options: AsyncDataOptions<T> = {}
): AsyncDataState<T> {
  const {
    default: defaultValue,
    key,
    cacheTTL = 5 * 60 * 1000, // 5分钟默认缓存
    immediate = true,
    retries = 3,
    retryDelay = 1000,
    dependencies = [],
    onError,
    onSuccess
  } = options

  // 状态管理
  const data = ref<T | null>(defaultValue || null)
  const pending = ref(false)
  const error = ref<Error | null>(null)
  const retryCount = ref(0)

  // 从缓存获取数据
  const getCachedData = (): T | null => {
    if (!key) return null
    return globalCache.get(key) || null
  }

  // 设置缓存数据
  const setCachedData = (value: T): void => {
    if (key) {
      globalCache.set(key, value, cacheTTL)
    }
  }

  // 执行数据获取
  const execute = async (): Promise<void> => {
    // 检查缓存
    if (key) {
      const cached = getCachedData()
      if (cached !== null) {
        data.value = cached
        return
      }
    }

    pending.value = true
    error.value = null

    try {
      const result = await fetcher()
      data.value = result

      // 设置缓存
      setCachedData(result)

      // 重置重试计数
      retryCount.value = 0

      // 成功回调
      if (onSuccess) {
        onSuccess(result)
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err))

      // 重试逻辑
      if (retryCount.value < retries) {
        retryCount.value++
        setTimeout(() => {
          execute()
        }, retryDelay * retryCount.value)
        return
      }

      error.value = errorObj

      // 错误回调
      if (onError) {
        onError(errorObj)
      } else {
        console.error('AsyncData Error:', errorObj)
      }
    } finally {
      pending.value = false
    }
  }

  // 刷新数据（忽略缓存）
  const refresh = async (): Promise<void> => {
    if (key) {
      globalCache.delete(key)
    }
    await execute()
  }

  // 清除数据
  const clear = (): void => {
    data.value = defaultValue || null
    error.value = null
    pending.value = false
    retryCount.value = 0

    if (key) {
      globalCache.delete(key)
    }
  }

  // 监听依赖变化
  if (dependencies.length > 0) {
    watch(dependencies, () => {
      refresh()
    }, { deep: true })
  }

  // 立即执行
  if (immediate) {
    execute()
  }

  // 组件卸载时清理
  onUnmounted(() => {
    // 可以在这里添加清理逻辑
  })

  return {
    data,
    pending,
    error,
    refresh,
    execute,
    clear
  }
}

// 分页数据管理
export interface PaginatedDataOptions<T> extends Omit<AsyncDataOptions<T[]>, 'default'> {
  pageSize?: number
  initialPage?: number
}

export interface PaginatedResult<T> {
  data: T[]
  total: number
  hasMore: boolean
}

export function usePaginatedData<T>(
  fetcher: (page: number, pageSize: number) => Promise<PaginatedResult<T>>,
  options: PaginatedDataOptions<T> = {}
) {
  const {
    pageSize = 20,
    initialPage = 1,
    ...asyncOptions
  } = options

  const currentPage = ref(initialPage)
  const total = ref(0)
  const hasMore = ref(true)
  const allData = ref<T[]>([])

  const paginatedFetcher = async () => {
    const result = await fetcher(currentPage.value, pageSize)

    if (currentPage.value === 1) {
      allData.value = result.data
    } else {
      allData.value.push(...result.data)
    }

    total.value = result.total
    hasMore.value = result.hasMore

    return result.data
  }

  const asyncState = useAsyncData(paginatedFetcher, {
    ...asyncOptions,
    key: asyncOptions.key ? `${asyncOptions.key}_page_${currentPage.value}` : undefined
  })

  const loadMore = async (): Promise<void> => {
    if (!hasMore.value || asyncState.pending.value) return

    currentPage.value++
    await asyncState.execute()
  }

  const reset = (): void => {
    currentPage.value = initialPage
    allData.value = []
    total.value = 0
    hasMore.value = true
    asyncState.clear()
  }

  const refresh = async (): Promise<void> => {
    currentPage.value = initialPage
    allData.value = []
    await asyncState.refresh()
  }

  return {
    data: computed(() => allData.value),
    currentPage: readonly(currentPage),
    total: readonly(total),
    hasMore: readonly(hasMore),
    pending: asyncState.pending,
    error: asyncState.error,
    loadMore,
    reset,
    refresh
  }
}

// 无限滚动数据管理
export function useInfiniteScroll<T>(
  fetcher: (page: number, pageSize: number) => Promise<{
    data: T[]
    hasMore: boolean
  }>,
  options: PaginatedDataOptions<T> & {
    threshold?: number
    rootMargin?: string
  } = {}
) {
  const { threshold = 0.1, rootMargin = '0px', ...paginatedOptions } = options

  const paginatedData = usePaginatedData(
    async (page, pageSize) => {
      const result = await fetcher(page, pageSize)
      return {
        ...result,
        total: 0 // 无限滚动不需要总数
      }
    },
    paginatedOptions
  )

  const loadMoreElement = ref<HTMLElement>()

  const observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry.isIntersecting && paginatedData.hasMore.value && !paginatedData.pending.value) {
        paginatedData.loadMore()
      }
    },
    {
      threshold,
      rootMargin
    }
  )

  watch(loadMoreElement, (el) => {
    if (el) {
      observer.observe(el)
    }
  })

  onUnmounted(() => {
    observer.disconnect()
  })

  return {
    ...paginatedData,
    loadMoreElement
  }
}

// 简单的批量数据获取
export function useBatchData<T extends Record<string, any>>(
  fetchers: Record<keyof T, () => Promise<any>>,
  options: Omit<AsyncDataOptions<any>, 'key'> = {}
) {
  const states: Record<string, AsyncDataState<any>> = {}

  // 为每个fetcher创建AsyncData状态
  Object.keys(fetchers).forEach(name => {
    states[name] = useAsyncData(fetchers[name], {
      ...options,
      immediate: false
    })
  })

  // 计算整体状态
  const pending = computed(() => {
    return Object.values(states).some(state => state.pending.value)
  })

  const allSettled = computed(() => {
    return Object.values(states).every(state =>
      !state.pending.value && (state.data.value !== null || state.error.value !== null)
    )
  })

  // 批量刷新
  const refresh = async (): Promise<void> => {
    await Promise.all(
      Object.values(states).map(state => state.refresh())
    )
  }

  // 批量执行
  const executeAll = async (): Promise<void> => {
    await Promise.all(
      Object.values(states).map(state => state.execute())
    )
  }

  // 立即执行所有fetcher
  if (options.immediate !== false) {
    executeAll()
  }

  return {
    states,
    pending,
    allSettled,
    refresh,
    executeAll
  }
}

import { ref, computed, onMounted, onUnmounted } from 'vue'

// 断点定义（与 CSS 变量保持一致）
export const breakpoints = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600
} as const

export type BreakpointKey = keyof typeof breakpoints
export type BreakpointValue = typeof breakpoints[BreakpointKey]

// 全局屏幕宽度状态
const screenWidth = ref(0)

export function useBreakpoints() {
  // 更新屏幕宽度
  const updateScreenWidth = () => {
    if (typeof window !== 'undefined') {
      screenWidth.value = window.innerWidth
    }
  }

  // 当前断点
  const currentBreakpoint = computed<BreakpointKey>(() => {
    const width = screenWidth.value

    if (width >= breakpoints.xxl) return 'xxl'
    if (width >= breakpoints.xl) return 'xl'
    if (width >= breakpoints.lg) return 'lg'
    if (width >= breakpoints.md) return 'md'
    if (width >= breakpoints.sm) return 'sm'
    return 'xs'
  })

  // 检查是否大于等于指定断点
  const isGreaterOrEqual = (breakpoint: BreakpointKey) => {
    return computed(() => screenWidth.value >= breakpoints[breakpoint])
  }

  // 检查是否小于指定断点
  const isLess = (breakpoint: BreakpointKey) => {
    return computed(() => screenWidth.value < breakpoints[breakpoint])
  }

  // 检查是否在指定断点范围内
  const isBetween = (min: BreakpointKey, max: BreakpointKey) => {
    return computed(() => {
      const width = screenWidth.value
      return width >= breakpoints[min] && width < breakpoints[max]
    })
  }

  // 常用断点检查
  const isMobile = computed(() => screenWidth.value < breakpoints.md)
  const isTablet = computed(() => screenWidth.value >= breakpoints.md && screenWidth.value < breakpoints.lg)
  const isDesktop = computed(() => screenWidth.value >= breakpoints.lg)
  const isLargeScreen = computed(() => screenWidth.value >= breakpoints.xl)

  // 响应式网格列数
  const gridCols = computed(() => {
    const width = screenWidth.value

    if (width >= breakpoints.xxl) return 24
    if (width >= breakpoints.xl) return 20
    if (width >= breakpoints.lg) return 16
    if (width >= breakpoints.md) return 12
    if (width >= breakpoints.sm) return 8
    return 4
  })

  // 响应式间距
  const spacing = computed(() => {
    const width = screenWidth.value

    if (width >= breakpoints.xl) return 'large'
    if (width >= breakpoints.md) return 'medium'
    return 'small'
  })

  // 响应式字体大小
  const fontSize = computed(() => {
    const width = screenWidth.value

    if (width >= breakpoints.xl) return 'large'
    if (width >= breakpoints.md) return 'medium'
    return 'small'
  })

  // 获取响应式值
  // 响应式工具函数
  const getResponsiveValue = <T>(values: Partial<Record<BreakpointKey, T>>, defaultValue: T): T => {
    const bp = currentBreakpoint.value
    return values[bp] ?? values.lg ?? values.md ?? values.sm ?? values.xs ?? defaultValue
  }

  // 响应式列数
  const getResponsiveColumns = (config: Partial<Record<BreakpointKey, number>>) => {
    return computed(() => getResponsiveValue(config, 1))
  }

  // 响应式间距
  const getResponsiveSpacing = () => {
    return computed(() => {
      const spacingMap: Record<BreakpointKey, string> = {
        xs: 'var(--space-tiny)',
        sm: 'var(--space-small)',
        md: 'var(--space-medium)',
        lg: 'var(--space-large)',
        xl: 'var(--space-xl)',
        xxl: 'var(--space-xxl)'
      }
      return spacingMap[currentBreakpoint.value]
    })
  }

  // 响应式字体大小
  const getResponsiveFontSize = (base: 'tiny' | 'small' | 'medium' | 'large' | 'xl' = 'medium') => {
    return computed(() => {
      const sizeMap = {
        tiny: {
          xs: 'var(--font-size-tiny)',
          sm: 'var(--font-size-tiny)',
          md: 'var(--font-size-small)',
          lg: 'var(--font-size-small)',
          xl: 'var(--font-size-medium)',
          xxl: 'var(--font-size-medium)'
        },
        small: {
          xs: 'var(--font-size-tiny)',
          sm: 'var(--font-size-small)',
          md: 'var(--font-size-small)',
          lg: 'var(--font-size-medium)',
          xl: 'var(--font-size-medium)',
          xxl: 'var(--font-size-large)'
        },
        medium: {
          xs: 'var(--font-size-small)',
          sm: 'var(--font-size-small)',
          md: 'var(--font-size-medium)',
          lg: 'var(--font-size-medium)',
          xl: 'var(--font-size-large)',
          xxl: 'var(--font-size-large)'
        },
        large: {
          xs: 'var(--font-size-small)',
          sm: 'var(--font-size-medium)',
          md: 'var(--font-size-large)',
          lg: 'var(--font-size-large)',
          xl: 'var(--font-size-xl)',
          xxl: 'var(--font-size-xl)'
        },
        xl: {
          xs: 'var(--font-size-medium)',
          sm: 'var(--font-size-large)',
          md: 'var(--font-size-xl)',
          lg: 'var(--font-size-xl)',
          xl: 'var(--font-size-xxl)',
          xxl: 'var(--font-size-xxl)'
        }
      }

      return sizeMap[base][currentBreakpoint.value]
    })
  }

  // 媒体查询匹配
  const useMediaQuery = (query: string) => {
    const matches = ref(false)

    const updateMatch = () => {
      if (typeof window !== 'undefined') {
        matches.value = window.matchMedia(query).matches
      }
    }

    onMounted(() => {
      updateMatch()
      if (typeof window !== 'undefined') {
        const mediaQuery = window.matchMedia(query)
        mediaQuery.addEventListener('change', updateMatch)

        onUnmounted(() => {
          mediaQuery.removeEventListener('change', updateMatch)
        })
      }
    })

    return matches
  }

  // 设备特性检测
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)')
  const prefersHighContrast = useMediaQuery('(prefers-contrast: high)')
  const isTouchDevice = useMediaQuery('(hover: none) and (pointer: coarse)')
  const isHighDPI = useMediaQuery('(-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi)')

  // 方向检测
  const isLandscape = useMediaQuery('(orientation: landscape)')
  const isPortrait = useMediaQuery('(orientation: portrait)')

  // 容器查询支持检测
  const supportsContainerQueries = useMediaQuery('(container-type: inline-size)')

  // 强制颜色模式检测
  const forcedColors = useMediaQuery('(forced-colors: active)')

  // 媒体查询匹配
  const matchMedia = (query: string) => {
    const mediaQuery = ref<MediaQueryList | null>(null)
    const matches = ref(false)

    const updateMatches = () => {
      if (mediaQuery.value) {
        matches.value = mediaQuery.value.matches
      }
    }

    onMounted(() => {
      if (typeof window !== 'undefined' && window.matchMedia) {
        mediaQuery.value = window.matchMedia(query)
        updateMatches()
        mediaQuery.value.addEventListener('change', updateMatches)
      }
    })

    onUnmounted(() => {
      if (mediaQuery.value) {
        mediaQuery.value.removeEventListener('change', updateMatches)
      }
    })

    return { matches }
  }

  // 初始化
  onMounted(() => {
    updateScreenWidth()

    if (typeof window !== 'undefined') {
      window.addEventListener('resize', updateScreenWidth)
    }
  })

  onUnmounted(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', updateScreenWidth)
    }
  })

  return {
    // 状态
    screenWidth: computed(() => screenWidth.value),
    currentBreakpoint,

    // 断点检查
    isGreaterOrEqual,
    isLess,
    isBetween,

    // 常用检查
    isMobile,
    isTablet,
    isDesktop,
    isLargeScreen,

    // 响应式值
    gridCols,
    spacing,
    fontSize,

    // 响应式工具
    getResponsiveValue,
    getResponsiveColumns,
    getResponsiveSpacing,
    getResponsiveFontSize,

    // 媒体查询
    useMediaQuery,

    // 设备特性
    prefersReducedMotion,
    prefersDarkMode,
    prefersHighContrast,
    isTouchDevice,
    isHighDPI,

    // 方向
    isLandscape,
    isPortrait,

    // 现代特性
    supportsContainerQueries,
    forcedColors,

    // 工具
    breakpoints
  }
}

// 导出全局屏幕宽度状态
export { screenWidth }

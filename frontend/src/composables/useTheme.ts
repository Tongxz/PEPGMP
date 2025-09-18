import { ref, computed, watch, onMounted, readonly } from 'vue'
import { useOsTheme } from 'naive-ui'

export type ThemeMode = 'light' | 'dark' | 'auto'

const THEME_STORAGE_KEY = 'app-theme'

// 全局主题状态
const themeMode = ref<ThemeMode>('auto')
const isDark = ref(false)

export function useTheme() {
  const osTheme = useOsTheme()

  // 计算当前是否为暗色主题
  const currentTheme = computed(() => {
    if (themeMode.value === 'auto') {
      return osTheme.value === 'dark' ? 'dark' : 'light'
    }
    return themeMode.value
  })

  // 更新暗色主题状态
  const updateDarkMode = () => {
    isDark.value = currentTheme.value === 'dark'

    // 更新 HTML 属性
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', currentTheme.value)

      // 更新 Naive UI 主题
      if (isDark.value) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
  }

  // 设置主题模式
  const setThemeMode = (mode: ThemeMode) => {
    themeMode.value = mode

    // 保存到本地存储
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(THEME_STORAGE_KEY, mode)
    }

    updateDarkMode()
  }

  // 切换主题
  const toggleTheme = () => {
    if (themeMode.value === 'light') {
      setThemeMode('dark')
    } else if (themeMode.value === 'dark') {
      setThemeMode('auto')
    } else {
      setThemeMode('light')
    }
  }

  // 获取主题图标
  const getThemeIcon = () => {
    switch (themeMode.value) {
      case 'light':
        return 'sunny-outline'
      case 'dark':
        return 'moon-outline'
      case 'auto':
        return 'contrast-outline'
      default:
        return 'contrast-outline'
    }
  }

  // 获取主题标签
  const getThemeLabel = () => {
    switch (themeMode.value) {
      case 'light':
        return '浅色模式'
      case 'dark':
        return '深色模式'
      case 'auto':
        return '跟随系统'
      default:
        return '跟随系统'
    }
  }

  // 初始化主题
  const initTheme = () => {
    // 从本地存储读取主题设置
    if (typeof localStorage !== 'undefined') {
      const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode
      if (savedTheme && ['light', 'dark', 'auto'].includes(savedTheme)) {
        themeMode.value = savedTheme
      }
    }

    updateDarkMode()
  }

  // 监听系统主题变化
  watch(osTheme, () => {
    if (themeMode.value === 'auto') {
      updateDarkMode()
    }
  })

  // 监听主题模式变化
  watch(themeMode, updateDarkMode)

  // 组件挂载时初始化
  onMounted(() => {
    initTheme()
  })

  return {
    themeMode: readonly(themeMode),
    isDark: readonly(isDark),
    currentTheme,
    setThemeMode,
    toggleTheme,
    getThemeIcon,
    getThemeLabel,
    initTheme
  }
}

// 导出全局主题状态供其他组件使用
export { themeMode, isDark }

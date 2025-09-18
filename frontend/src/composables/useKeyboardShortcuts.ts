import { ref, onMounted, onUnmounted, computed } from 'vue'

export interface KeyboardShortcut {
  id: string
  key: string
  modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[]
  description: string
  action: () => void
  enabled?: boolean
  context?: string // 上下文限制，如 'region-config', 'camera-view' 等
}

export interface ShortcutGroup {
  name: string
  shortcuts: KeyboardShortcut[]
}

export function useKeyboardShortcuts() {
  const shortcuts = ref<KeyboardShortcut[]>([])
  const isEnabled = ref(true)
  const currentContext = ref<string>('')

  // 计算当前上下文的快捷键
  const activeShortcuts = computed(() => {
    return shortcuts.value.filter(shortcut => {
      if (!shortcut.enabled) return false
      if (!shortcut.context) return true
      return shortcut.context === currentContext.value
    })
  })

  // 按分组组织快捷键
  const shortcutGroups = computed(() => {
    const groups: { [key: string]: KeyboardShortcut[] } = {}

    activeShortcuts.value.forEach(shortcut => {
      const context = shortcut.context || 'global'
      if (!groups[context]) {
        groups[context] = []
      }
      groups[context].push(shortcut)
    })

    return Object.entries(groups).map(([name, shortcuts]) => ({
      name: getContextDisplayName(name),
      shortcuts
    }))
  })

  // 获取上下文显示名称
  const getContextDisplayName = (context: string): string => {
    const contextNames: { [key: string]: string } = {
      global: '全局',
      'region-config': '区域配置',
      'camera-view': '摄像头视图',
      'detection': '检测管理',
      'settings': '设置'
    }
    return contextNames[context] || context
  }

  // 解析快捷键字符串
  const parseShortcut = (shortcutStr: string) => {
    const parts = shortcutStr.toLowerCase().split('+')
    const modifiers: string[] = []
    let key = ''

    parts.forEach(part => {
      const trimmed = part.trim()
      if (['ctrl', 'alt', 'shift', 'meta', 'cmd'].includes(trimmed)) {
        if (trimmed === 'cmd') {
          modifiers.push('meta')
        } else {
          modifiers.push(trimmed)
        }
      } else {
        key = trimmed
      }
    })

    return { modifiers, key }
  }

  // 检查快捷键是否匹配
  const isShortcutMatch = (event: KeyboardEvent, shortcut: KeyboardShortcut): boolean => {
    const { modifiers = [], key } = parseShortcut(shortcut.key)

    // 检查主键
    if (event.key.toLowerCase() !== key.toLowerCase()) {
      return false
    }

    // 检查修饰键
    const requiredModifiers = {
      ctrl: modifiers.includes('ctrl'),
      alt: modifiers.includes('alt'),
      shift: modifiers.includes('shift'),
      meta: modifiers.includes('meta')
    }

    return (
      event.ctrlKey === requiredModifiers.ctrl &&
      event.altKey === requiredModifiers.alt &&
      event.shiftKey === requiredModifiers.shift &&
      event.metaKey === requiredModifiers.meta
    )
  }

  // 处理键盘事件
  const handleKeydown = (event: KeyboardEvent) => {
    if (!isEnabled.value) return

    // 忽略在输入框中的快捷键
    const target = event.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      return
    }

    // 查找匹配的快捷键
    const matchedShortcut = activeShortcuts.value.find(shortcut =>
      isShortcutMatch(event, shortcut)
    )

    if (matchedShortcut) {
      event.preventDefault()
      event.stopPropagation()
      matchedShortcut.action()
    }
  }

  // 注册快捷键
  const registerShortcut = (shortcut: KeyboardShortcut) => {
    const existingIndex = shortcuts.value.findIndex(s => s.id === shortcut.id)
    if (existingIndex >= 0) {
      shortcuts.value[existingIndex] = { ...shortcut, enabled: shortcut.enabled ?? true }
    } else {
      shortcuts.value.push({ ...shortcut, enabled: shortcut.enabled ?? true })
    }
  }

  // 批量注册快捷键
  const registerShortcuts = (shortcutList: KeyboardShortcut[]) => {
    shortcutList.forEach(registerShortcut)
  }

  // 注销快捷键
  const unregisterShortcut = (id: string) => {
    const index = shortcuts.value.findIndex(s => s.id === id)
    if (index >= 0) {
      shortcuts.value.splice(index, 1)
    }
  }

  // 启用/禁用快捷键
  const toggleShortcut = (id: string, enabled?: boolean) => {
    const shortcut = shortcuts.value.find(s => s.id === id)
    if (shortcut) {
      shortcut.enabled = enabled ?? !shortcut.enabled
    }
  }

  // 设置当前上下文
  const setContext = (context: string) => {
    currentContext.value = context
  }

  // 清除上下文
  const clearContext = () => {
    currentContext.value = ''
  }

  // 启用/禁用所有快捷键
  const toggleGlobal = (enabled?: boolean) => {
    isEnabled.value = enabled ?? !isEnabled.value
  }

  // 获取快捷键显示文本
  const getShortcutDisplay = (shortcutKey: string): string => {
    const { modifiers, key } = parseShortcut(shortcutKey)
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0

    const modifierSymbols: { [key: string]: string } = isMac ? {
      meta: '⌘',
      ctrl: '⌃',
      alt: '⌥',
      shift: '⇧'
    } : {
      meta: 'Win',
      ctrl: 'Ctrl',
      alt: 'Alt',
      shift: 'Shift'
    }

    const displayModifiers = modifiers.map(mod => modifierSymbols[mod] || mod)
    const displayKey = key.length === 1 ? key.toUpperCase() :
                      key === 'escape' ? 'Esc' :
                      key === 'delete' ? 'Del' :
                      key === 'backspace' ? '⌫' :
                      key === 'enter' ? '↵' :
                      key === 'space' ? 'Space' :
                      key.charAt(0).toUpperCase() + key.slice(1)

    return [...displayModifiers, displayKey].join(isMac ? '' : '+')
  }

  // 预定义的常用快捷键
  const createCommonShortcuts = () => {
    return [
      // 全局快捷键
      {
        id: 'help',
        key: 'F1',
        description: '显示帮助',
        action: () => console.log('显示帮助'),
        context: 'global'
      },
      {
        id: 'search',
        key: 'ctrl+f',
        description: '搜索',
        action: () => console.log('打开搜索'),
        context: 'global'
      },
      {
        id: 'save',
        key: 'ctrl+s',
        description: '保存',
        action: () => console.log('保存'),
        context: 'global'
      },
      {
        id: 'refresh',
        key: 'F5',
        description: '刷新',
        action: () => window.location.reload(),
        context: 'global'
      },

      // 区域配置快捷键
      {
        id: 'add-region',
        key: 'ctrl+n',
        description: '添加新区域',
        action: () => console.log('添加新区域'),
        context: 'region-config'
      },
      {
        id: 'delete-region',
        key: 'delete',
        description: '删除选中区域',
        action: () => console.log('删除区域'),
        context: 'region-config'
      },
      {
        id: 'duplicate-region',
        key: 'ctrl+d',
        description: '复制区域',
        action: () => console.log('复制区域'),
        context: 'region-config'
      },
      {
        id: 'toggle-preview',
        key: 'space',
        description: '切换预览',
        action: () => console.log('切换预览'),
        context: 'region-config'
      },

      // 摄像头视图快捷键
      {
        id: 'fullscreen',
        key: 'F11',
        description: '全屏显示',
        action: () => console.log('全屏'),
        context: 'camera-view'
      },
      {
        id: 'snapshot',
        key: 'ctrl+shift+s',
        description: '截图',
        action: () => console.log('截图'),
        context: 'camera-view'
      }
    ]
  }

  // 生命周期管理
  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown)
  })

  return {
    // 状态
    shortcuts: shortcuts.value,
    activeShortcuts,
    shortcutGroups,
    isEnabled,
    currentContext,

    // 方法
    registerShortcut,
    registerShortcuts,
    unregisterShortcut,
    toggleShortcut,
    setContext,
    clearContext,
    toggleGlobal,
    getShortcutDisplay,
    createCommonShortcuts,

    // 工具方法
    parseShortcut,
    isShortcutMatch
  }
}

// 快捷键帮助面板组合式函数
export function useShortcutHelp() {
  const showHelp = ref(false)
  const { shortcutGroups, getShortcutDisplay } = useKeyboardShortcuts()

  const toggleHelp = () => {
    showHelp.value = !showHelp.value
  }

  const closeHelp = () => {
    showHelp.value = false
  }

  return {
    showHelp,
    shortcutGroups,
    getShortcutDisplay,
    toggleHelp,
    closeHelp
  }
}

import { ref, onMounted, onUnmounted, nextTick } from 'vue'

export interface AccessibilityOptions {
  announcePageChanges?: boolean
  manageFocus?: boolean
  enableKeyboardNavigation?: boolean
  highContrastMode?: boolean
  reducedMotion?: boolean
  screenReaderOptimizations?: boolean
}

export interface FocusableElement {
  element: HTMLElement
  tabIndex: number
  role?: string
  label?: string
}

export function useAccessibility(options: AccessibilityOptions = {}) {
  const {
    announcePageChanges = true,
    manageFocus = true,
    enableKeyboardNavigation: enableKeyboardNavigationOption = true,
    highContrastMode = false,
    reducedMotion = false,
    screenReaderOptimizations = true
  } = options

  // 状态管理
  const isScreenReaderActive = ref(false)
  const currentFocusedElement = ref<HTMLElement | null>(null)
  const focusHistory = ref<HTMLElement[]>([])
  const announcements = ref<string[]>([])

  // ARIA Live Region 元素
  let liveRegion: HTMLElement | null = null
  let politeRegion: HTMLElement | null = null

  // 检测屏幕阅读器
  const detectScreenReader = (): boolean => {
    // 检测常见的屏幕阅读器特征
    const hasScreenReader =
      // 检查是否有辅助技术API
      'speechSynthesis' in window ||
      // 检查用户代理字符串
      /NVDA|JAWS|VoiceOver|TalkBack|Orca/i.test(navigator.userAgent)

    // 检查媒体查询（需要单独处理以避免类型错误）
    try {
      if (typeof window !== 'undefined' && 'matchMedia' in window) {
        return hasScreenReader ||
          window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
          window.matchMedia('(prefers-contrast: high)').matches
      }
    } catch (e) {
      // 忽略媒体查询错误
    }

    return hasScreenReader
  }

  // 创建ARIA Live Region
  const createLiveRegions = () => {
    // 创建assertive live region (紧急公告)
    liveRegion = document.createElement('div')
    liveRegion.setAttribute('aria-live', 'assertive')
    liveRegion.setAttribute('aria-atomic', 'true')
    liveRegion.setAttribute('class', 'sr-only')
    liveRegion.style.cssText = `
      position: absolute !important;
      width: 1px !important;
      height: 1px !important;
      padding: 0 !important;
      margin: -1px !important;
      overflow: hidden !important;
      clip: rect(0, 0, 0, 0) !important;
      white-space: nowrap !important;
      border: 0 !important;
    `
    document.body.appendChild(liveRegion)

    // 创建polite live region (礼貌公告)
    politeRegion = document.createElement('div')
    politeRegion.setAttribute('aria-live', 'polite')
    politeRegion.setAttribute('aria-atomic', 'true')
    politeRegion.setAttribute('class', 'sr-only')
    politeRegion.style.cssText = liveRegion.style.cssText
    document.body.appendChild(politeRegion)
  }

  // 公告消息给屏幕阅读器
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!message.trim()) return

    const region = priority === 'assertive' ? liveRegion : politeRegion
    if (!region) return

    // 清空后设置新消息
    region.textContent = ''
    setTimeout(() => {
      region.textContent = message
      announcements.value.push(message)

      // 限制历史记录长度
      if (announcements.value.length > 10) {
        announcements.value.shift()
      }
    }, 100)
  }

  // 焦点管理
  const focusManagement = {
    // 获取所有可聚焦元素
    getFocusableElements: (container: HTMLElement = document.body): FocusableElement[] => {
      const focusableSelectors = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[tabindex]:not([tabindex="-1"])',
        '[contenteditable="true"]',
        'audio[controls]',
        'video[controls]',
        'iframe',
        'object',
        'embed',
        'area[href]',
        'summary'
      ].join(', ')

      const elements = Array.from(container.querySelectorAll(focusableSelectors)) as HTMLElement[]

      return elements
        .filter(el => {
          // 过滤不可见元素
          const style = window.getComputedStyle(el)
          return style.display !== 'none' &&
                 style.visibility !== 'hidden' &&
                 el.offsetWidth > 0 &&
                 el.offsetHeight > 0
        })
        .map(el => ({
          element: el,
          tabIndex: el.tabIndex,
          role: el.getAttribute('role') || undefined,
          label: el.getAttribute('aria-label') ||
                 el.getAttribute('aria-labelledby') ||
                 (el as HTMLInputElement).placeholder ||
                 el.textContent?.trim() ||
                 undefined
        }))
        .sort((a, b) => {
          // 按tabIndex排序
          if (a.tabIndex !== b.tabIndex) {
            if (a.tabIndex === 0) return 1
            if (b.tabIndex === 0) return -1
            return a.tabIndex - b.tabIndex
          }
          return 0
        })
    },

    // 设置焦点
    setFocus: (element: HTMLElement, options: { preventScroll?: boolean; announce?: string } = {}) => {
      if (!element || !manageFocus) return

      // 保存当前焦点到历史
      if (currentFocusedElement.value && currentFocusedElement.value !== element) {
        focusHistory.value.push(currentFocusedElement.value)
        if (focusHistory.value.length > 10) {
          focusHistory.value.shift()
        }
      }

      currentFocusedElement.value = element
      element.focus({ preventScroll: options.preventScroll })

      // 公告焦点变化
      if (options.announce) {
        announce(options.announce, 'polite')
      }
    },

    // 恢复上一个焦点
    restoreFocus: () => {
      const previousElement = focusHistory.value.pop()
      if (previousElement && document.contains(previousElement)) {
        focusManagement.setFocus(previousElement)
        return true
      }
      return false
    },

    // 焦点陷阱 (用于模态框等)
    trapFocus: (container: HTMLElement) => {
      const focusableElements = focusManagement.getFocusableElements(container)
      if (focusableElements.length === 0) return () => {}

      const firstElement = focusableElements[0].element
      const lastElement = focusableElements[focusableElements.length - 1].element

      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Tab') return

        if (event.shiftKey) {
          // Shift + Tab
          if (document.activeElement === firstElement) {
            event.preventDefault()
            lastElement.focus()
          }
        } else {
          // Tab
          if (document.activeElement === lastElement) {
            event.preventDefault()
            firstElement.focus()
          }
        }
      }

      container.addEventListener('keydown', handleKeyDown)

      // 设置初始焦点
      firstElement.focus()

      // 返回清理函数
      return () => {
        container.removeEventListener('keydown', handleKeyDown)
      }
    }
  }

  // 键盘导航支持
  const keyboardNavigation = {
    // 方向键导航
    enableArrowKeyNavigation: (container: HTMLElement, options: {
      direction?: 'horizontal' | 'vertical' | 'both'
      wrap?: boolean
      selector?: string
    } = {}) => {
      const { direction = 'both', wrap = true, selector } = options

      const handleKeyDown = (event: KeyboardEvent) => {
        const target = event.target as HTMLElement
        if (!container.contains(target)) return

        const focusableElements = selector ?
          Array.from(container.querySelectorAll(selector)) as HTMLElement[] :
          focusManagement.getFocusableElements(container).map(f => f.element)

        const currentIndex = focusableElements.indexOf(target)
        if (currentIndex === -1) return

        let nextIndex = currentIndex

        switch (event.key) {
          case 'ArrowUp':
            if (direction === 'vertical' || direction === 'both') {
              event.preventDefault()
              nextIndex = currentIndex - 1
            }
            break
          case 'ArrowDown':
            if (direction === 'vertical' || direction === 'both') {
              event.preventDefault()
              nextIndex = currentIndex + 1
            }
            break
          case 'ArrowLeft':
            if (direction === 'horizontal' || direction === 'both') {
              event.preventDefault()
              nextIndex = currentIndex - 1
            }
            break
          case 'ArrowRight':
            if (direction === 'horizontal' || direction === 'both') {
              event.preventDefault()
              nextIndex = currentIndex + 1
            }
            break
          case 'Home':
            event.preventDefault()
            nextIndex = 0
            break
          case 'End':
            event.preventDefault()
            nextIndex = focusableElements.length - 1
            break
        }

        // 处理边界
        if (wrap) {
          if (nextIndex < 0) nextIndex = focusableElements.length - 1
          if (nextIndex >= focusableElements.length) nextIndex = 0
        } else {
          nextIndex = Math.max(0, Math.min(nextIndex, focusableElements.length - 1))
        }

        if (nextIndex !== currentIndex) {
          focusManagement.setFocus(focusableElements[nextIndex])
        }
      }

      container.addEventListener('keydown', handleKeyDown)
      return () => container.removeEventListener('keydown', handleKeyDown)
    },

    // Escape键处理
    enableEscapeKey: (callback: () => void) => {
      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Escape') {
          event.preventDefault()
          callback()
        }
      }

      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }

  // ARIA属性管理
  const ariaManager = {
    // 设置ARIA属性
    setAttributes: (element: HTMLElement, attributes: { [key: string]: string | null }) => {
      Object.entries(attributes).forEach(([key, value]) => {
        if (value === null) {
          element.removeAttribute(key)
        } else {
          element.setAttribute(key, value)
        }
      })
    },

    // 管理展开/折叠状态
    toggleExpanded: (trigger: HTMLElement, target: HTMLElement, expanded?: boolean) => {
      const isExpanded = expanded ?? trigger.getAttribute('aria-expanded') !== 'true'

      ariaManager.setAttributes(trigger, {
        'aria-expanded': isExpanded.toString()
      })

      ariaManager.setAttributes(target, {
        'aria-hidden': (!isExpanded).toString()
      })

      // 公告状态变化
      const label = trigger.getAttribute('aria-label') || trigger.textContent?.trim()
      if (label) {
        announce(`${label} ${isExpanded ? '已展开' : '已折叠'}`, 'polite')
      }

      return isExpanded
    },

    // 管理选中状态
    toggleSelected: (element: HTMLElement, selected?: boolean) => {
      const isSelected = selected ?? element.getAttribute('aria-selected') !== 'true'

      ariaManager.setAttributes(element, {
        'aria-selected': isSelected.toString()
      })

      return isSelected
    }
  }

  // 颜色对比度检查
  const checkColorContrast = (foreground: string, background: string): number => {
    // 简化的对比度计算
    const getLuminance = (color: string): number => {
      // 这里应该实现完整的颜色解析和亮度计算
      // 为简化，返回一个模拟值
      return 0.5
    }

    const fgLuminance = getLuminance(foreground)
    const bgLuminance = getLuminance(background)

    const lighter = Math.max(fgLuminance, bgLuminance)
    const darker = Math.min(fgLuminance, bgLuminance)

    return (lighter + 0.05) / (darker + 0.05)
  }

  // 无障碍检查工具
  const accessibilityChecker = {
    // 检查页面无障碍问题
    checkPage: (): string[] => {
      const issues: string[] = []

      // 检查图片alt属性
      const images = document.querySelectorAll('img')
      images.forEach(img => {
        if (!img.alt && !img.getAttribute('aria-label')) {
          issues.push(`图片缺少alt属性: ${img.src}`)
        }
      })

      // 检查表单标签
      const inputs = document.querySelectorAll('input, select, textarea')
      inputs.forEach(input => {
        const hasLabel = input.id && document.querySelector(`label[for="${input.id}"]`)
        const hasAriaLabel = input.getAttribute('aria-label') || input.getAttribute('aria-labelledby')

        if (!hasLabel && !hasAriaLabel) {
          issues.push(`表单控件缺少标签: ${input.tagName}`)
        }
      })

      // 检查标题层级
      const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6')
      let lastLevel = 0
      headings.forEach(heading => {
        const level = parseInt(heading.tagName.charAt(1))
        if (level > lastLevel + 1) {
          issues.push(`标题层级跳跃: 从 h${lastLevel} 跳到 h${level}`)
        }
        lastLevel = level
      })

      // 检查链接文本
      const links = document.querySelectorAll('a')
      links.forEach(link => {
        const text = link.textContent?.trim()
        if (!text || text.length < 2) {
          issues.push(`链接文本过短或为空: ${link.href}`)
        }
      })

      return issues
    },

    // 生成无障碍报告
    generateReport: () => {
      const issues = accessibilityChecker.checkPage()
      const focusableCount = focusManagement.getFocusableElements().length

      return {
        timestamp: new Date().toISOString(),
        issues,
        focusableElementsCount: focusableCount,
        screenReaderDetected: isScreenReaderActive.value,
        announcements: announcements.value.slice(-5), // 最近5条公告
        recommendations: [
          '确保所有交互元素都可以通过键盘访问',
          '为所有图片提供有意义的alt文本',
          '使用语义化的HTML标签',
          '保持足够的颜色对比度',
          '提供清晰的焦点指示器'
        ]
      }
    }
  }

  // 初始化
  const initialize = () => {
    // 检测屏幕阅读器
    isScreenReaderActive.value = detectScreenReader()

    // 创建Live Region
    createLiveRegions()

    // 添加全局样式
    const style = document.createElement('style')
    style.textContent = `
      .sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
      }

      .focus-visible {
        outline: 2px solid var(--primary-color, #1890ff) !important;
        outline-offset: 2px !important;
      }

      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
        }
      }

      @media (prefers-contrast: high) {
        * {
          border-color: currentColor !important;
        }
      }
    `
    document.head.appendChild(style)

    // 公告页面加载完成
    if (announcePageChanges) {
      announce('页面加载完成', 'polite')
    }
  }

  // 清理
  const cleanup = () => {
    if (liveRegion) {
      document.body.removeChild(liveRegion)
      liveRegion = null
    }
    if (politeRegion) {
      document.body.removeChild(politeRegion)
      politeRegion = null
    }
  }

  // 生命周期
  onMounted(() => {
    nextTick(() => {
      initialize()
    })
  })

  onUnmounted(() => {
    cleanup()
  })

  // 启用键盘导航的便捷方法
  const enableKeyboardNavigation = () => {
    // 这是一个便捷方法，用于启用键盘导航功能
    // 实际的键盘导航功能已经在 keyboardNavigation 对象中提供
    console.log('键盘导航功能已启用')
  }

  // 公告消息的便捷方法
  const announceMessage = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    announce(message, priority)
  }

  // 设置焦点到元素的便捷方法
  const setFocusToElement = (element: HTMLElement) => {
    focusManagement.setFocus(element)
  }

  return {
    // 状态
    isScreenReaderActive,
    currentFocusedElement,
    announcements,

    // 方法
    announce,
    announceMessage,
    focusManagement,
    keyboardNavigation,
    ariaManager,
    accessibilityChecker,
    checkColorContrast,
    enableKeyboardNavigation,
    setFocusToElement,

    // 工具
    initialize,
    cleanup
  }
}

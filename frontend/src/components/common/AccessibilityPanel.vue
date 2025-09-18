<template>
  <div class="accessibility-panel" :class="{ 'panel-open': isOpen }">
    <!-- 触发按钮 -->
    <button
      class="accessibility-trigger"
      @click="togglePanel"
      :aria-expanded="isOpen"
      aria-controls="accessibility-controls"
      aria-label="无障碍访问设置"
      title="无障碍访问设置"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 7.5V9M15 10.5V19L13.5 17.5V14.5L10.5 17.5V22H9V16.5L12 13.5V10.5L8 12V14H6.5V10.5L12 8.5C12.5 8.5 13 8.5 13.5 9L15 10.5Z"/>
      </svg>
    </button>

    <!-- 控制面板 -->
    <div
      v-show="isOpen"
      id="accessibility-controls"
      class="accessibility-controls"
      role="dialog"
      aria-labelledby="accessibility-title"
      aria-modal="false"
    >
      <div class="panel-header">
        <h3 id="accessibility-title" class="panel-title">无障碍访问设置</h3>
        <button
          class="close-button"
          @click="closePanel"
          aria-label="关闭无障碍设置面板"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 6.586L13.657 1l1.414 1.414L9.414 8l5.657 5.586-1.414 1.414L8 9.414 2.343 15 1 13.657 6.586 8 1 2.343 2.343 1 8 6.586z"/>
          </svg>
        </button>
      </div>

      <div class="panel-content">
        <!-- 视觉辅助 -->
        <section class="control-section">
          <h4 class="section-title">视觉辅助</h4>

          <div class="control-item">
            <label class="control-label">
              <input
                type="checkbox"
                v-model="settings.highContrast"
                @change="toggleHighContrast"
                class="control-checkbox"
              />
              <span class="checkbox-indicator"></span>
              高对比度模式
            </label>
            <p class="control-description">增强文本和背景的对比度，提高可读性</p>
          </div>

          <div class="control-item">
            <label class="control-label">
              <input
                type="checkbox"
                v-model="settings.reducedMotion"
                @change="toggleReducedMotion"
                class="control-checkbox"
              />
              <span class="checkbox-indicator"></span>
              减少动画效果
            </label>
            <p class="control-description">减少或禁用动画和过渡效果</p>
          </div>

          <div class="control-item">
            <label class="control-label" for="font-size-slider">
              字体大小: {{ settings.fontSize }}%
            </label>
            <input
              id="font-size-slider"
              type="range"
              min="75"
              max="150"
              step="5"
              v-model="settings.fontSize"
              @input="updateFontSize"
              class="control-slider"
              aria-describedby="font-size-desc"
            />
            <p id="font-size-desc" class="control-description">调整页面字体大小</p>
          </div>
        </section>

        <!-- 导航辅助 -->
        <section class="control-section">
          <h4 class="section-title">导航辅助</h4>

          <div class="control-item">
            <label class="control-label">
              <input
                type="checkbox"
                v-model="settings.keyboardNavigation"
                @change="toggleKeyboardNavigation"
                class="control-checkbox"
              />
              <span class="checkbox-indicator"></span>
              键盘导航增强
            </label>
            <p class="control-description">启用增强的键盘导航功能</p>
          </div>

          <div class="control-item">
            <label class="control-label">
              <input
                type="checkbox"
                v-model="settings.focusIndicator"
                @change="toggleFocusIndicator"
                class="control-checkbox"
              />
              <span class="checkbox-indicator"></span>
              焦点指示器增强
            </label>
            <p class="control-description">显示更明显的焦点指示器</p>
          </div>

          <div class="control-item">
            <button
              class="action-button"
              @click="showKeyboardShortcuts"
              aria-describedby="shortcuts-desc"
            >
              查看键盘快捷键
            </button>
            <p id="shortcuts-desc" class="control-description">显示可用的键盘快捷键列表</p>
          </div>
        </section>

        <!-- 屏幕阅读器 -->
        <section class="control-section">
          <h4 class="section-title">屏幕阅读器</h4>

          <div class="control-item">
            <div class="status-indicator">
              <span class="status-dot" :class="{ active: isScreenReaderActive }"></span>
              <span class="status-text">
                {{ isScreenReaderActive ? '已检测到屏幕阅读器' : '未检测到屏幕阅读器' }}
              </span>
            </div>
          </div>

          <div class="control-item">
            <label class="control-label">
              <input
                type="checkbox"
                v-model="settings.announcements"
                @change="toggleAnnouncements"
                class="control-checkbox"
              />
              <span class="checkbox-indicator"></span>
              页面变化公告
            </label>
            <p class="control-description">自动公告页面内容变化</p>
          </div>

          <div class="control-item">
            <button
              class="action-button"
              @click="testAnnouncement"
              aria-describedby="test-desc"
            >
              测试语音公告
            </button>
            <p id="test-desc" class="control-description">播放测试公告以验证屏幕阅读器</p>
          </div>
        </section>

        <!-- 无障碍检查 -->
        <section class="control-section">
          <h4 class="section-title">无障碍检查</h4>

          <div class="control-item">
            <button
              class="action-button primary"
              @click="runAccessibilityCheck"
              :disabled="isChecking"
              aria-describedby="check-desc"
            >
              {{ isChecking ? '检查中...' : '运行无障碍检查' }}
            </button>
            <p id="check-desc" class="control-description">检查当前页面的无障碍问题</p>
          </div>

          <div v-if="checkResults" class="check-results">
            <div class="results-summary">
              <span class="results-count">发现 {{ checkResults.issues.length }} 个问题</span>
              <span class="results-time">{{ formatTime(checkResults.timestamp) }}</span>
            </div>

            <div v-if="checkResults.issues.length > 0" class="issues-list">
              <h5 class="issues-title">发现的问题:</h5>
              <ul class="issues-items">
                <li v-for="(issue, index) in checkResults.issues" :key="index" class="issue-item">
                  {{ issue }}
                </li>
              </ul>
            </div>

            <div class="recommendations">
              <h5 class="recommendations-title">建议:</h5>
              <ul class="recommendations-items">
                <li v-for="(rec, index) in checkResults.recommendations" :key="index" class="recommendation-item">
                  {{ rec }}
                </li>
              </ul>
            </div>
          </div>
        </section>

        <!-- 重置按钮 -->
        <div class="panel-footer">
          <button
            class="reset-button"
            @click="resetSettings"
            aria-describedby="reset-desc"
          >
            重置所有设置
          </button>
          <p id="reset-desc" class="control-description">将所有无障碍设置恢复为默认值</p>
        </div>
      </div>
    </div>

    <!-- 遮罩层 -->
    <div
      v-show="isOpen"
      class="panel-overlay"
      @click="closePanel"
      aria-hidden="true"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAccessibility } from '@/composables/useAccessibility'

// 组件状态
const isOpen = ref(false)
const isChecking = ref(false)
const checkResults = ref<any>(null)

// 无障碍设置
const settings = reactive({
  highContrast: false,
  reducedMotion: false,
  fontSize: 100,
  keyboardNavigation: true,
  focusIndicator: true,
  announcements: true
})

// 使用无障碍composable
const {
  isScreenReaderActive,
  announce,
  focusManagement,
  keyboardNavigation,
  accessibilityChecker
} = useAccessibility()

// 焦点陷阱清理函数
let focusTrapCleanup: (() => void) | null = null

// 计算属性
const panelElement = computed(() => document.querySelector('.accessibility-controls') as HTMLElement)

// 方法
const togglePanel = () => {
  isOpen.value = !isOpen.value

  if (isOpen.value) {
    nextTick(() => {
      // 设置焦点陷阱
      const panel = panelElement.value
      if (panel) {
        focusTrapCleanup = focusManagement.trapFocus(panel)
      }
      announce('无障碍设置面板已打开', 'polite')
    })
  } else {
    closePanel()
  }
}

const closePanel = () => {
  isOpen.value = false

  // 清理焦点陷阱
  if (focusTrapCleanup) {
    focusTrapCleanup()
    focusTrapCleanup = null
  }

  // 恢复焦点到触发按钮
  const trigger = document.querySelector('.accessibility-trigger') as HTMLElement
  if (trigger) {
    focusManagement.setFocus(trigger)
  }

  announce('无障碍设置面板已关闭', 'polite')
}

// 设置切换方法
const toggleHighContrast = () => {
  document.documentElement.classList.toggle('high-contrast', settings.highContrast)
  announce(`高对比度模式已${settings.highContrast ? '启用' : '禁用'}`, 'polite')
}

const toggleReducedMotion = () => {
  document.documentElement.classList.toggle('reduced-motion', settings.reducedMotion)
  announce(`动画效果已${settings.reducedMotion ? '减少' : '恢复'}`, 'polite')
}

const updateFontSize = () => {
  document.documentElement.style.fontSize = `${settings.fontSize}%`
  announce(`字体大小已调整为 ${settings.fontSize}%`, 'polite')
}

const toggleKeyboardNavigation = () => {
  // 这里可以启用/禁用键盘导航功能
  announce(`键盘导航已${settings.keyboardNavigation ? '启用' : '禁用'}`, 'polite')
}

const toggleFocusIndicator = () => {
  document.documentElement.classList.toggle('enhanced-focus', settings.focusIndicator)
  announce(`焦点指示器已${settings.focusIndicator ? '增强' : '恢复默认'}`, 'polite')
}

const toggleAnnouncements = () => {
  announce(`页面变化公告已${settings.announcements ? '启用' : '禁用'}`, 'polite')
}

// 功能方法
const showKeyboardShortcuts = () => {
  // 这里可以显示键盘快捷键帮助
  announce('键盘快捷键帮助已打开', 'polite')
}

const testAnnouncement = () => {
  announce('这是一条测试公告，用于验证屏幕阅读器功能', 'assertive')
}

const runAccessibilityCheck = async () => {
  isChecking.value = true
  announce('开始运行无障碍检查', 'polite')

  try {
    // 模拟异步检查
    await new Promise(resolve => setTimeout(resolve, 1000))
    checkResults.value = accessibilityChecker.generateReport()

    const issueCount = checkResults.value.issues.length
    announce(`无障碍检查完成，发现 ${issueCount} 个问题`, 'assertive')
  } catch (error) {
    announce('无障碍检查失败，请稍后重试', 'assertive')
  } finally {
    isChecking.value = false
  }
}

const resetSettings = () => {
  settings.highContrast = false
  settings.reducedMotion = false
  settings.fontSize = 100
  settings.keyboardNavigation = true
  settings.focusIndicator = true
  settings.announcements = true

  // 重置DOM状态
  document.documentElement.classList.remove('high-contrast', 'reduced-motion', 'enhanced-focus')
  document.documentElement.style.fontSize = ''

  checkResults.value = null
  announce('所有无障碍设置已重置为默认值', 'polite')
}

// 工具方法
const formatTime = (timestamp: string): string => {
  return new Date(timestamp).toLocaleTimeString()
}

// 键盘事件处理
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && isOpen.value) {
    closePanel()
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)

  // 从localStorage恢复设置
  const savedSettings = localStorage.getItem('accessibility-settings')
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings)
      Object.assign(settings, parsed)

      // 应用保存的设置
      if (settings.highContrast) toggleHighContrast()
      if (settings.reducedMotion) toggleReducedMotion()
      if (settings.fontSize !== 100) updateFontSize()
      if (settings.focusIndicator) toggleFocusIndicator()
    } catch (e) {
      console.warn('Failed to restore accessibility settings:', e)
    }
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)

  // 保存设置到localStorage
  localStorage.setItem('accessibility-settings', JSON.stringify(settings))

  // 清理焦点陷阱
  if (focusTrapCleanup) {
    focusTrapCleanup()
  }
})
</script>

<style scoped>
.accessibility-panel {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
}

.accessibility-trigger {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--primary-color, #1890ff);
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.accessibility-trigger:hover {
  background: var(--primary-color-hover, #40a9ff);
  transform: scale(1.05);
}

.accessibility-trigger:focus {
  outline: 2px solid var(--primary-color, #1890ff);
  outline-offset: 2px;
}

.accessibility-controls {
  position: absolute;
  top: 60px;
  right: 0;
  width: 360px;
  max-height: 80vh;
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.close-button {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8c8c8c;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: #f5f5f5;
  color: #262626;
}

.panel-content {
  max-height: calc(80vh - 64px);
  overflow-y: auto;
  padding: 20px;
}

.control-section {
  margin-bottom: 24px;
}

.control-section:last-child {
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}

.control-item {
  margin-bottom: 16px;
}

.control-item:last-child {
  margin-bottom: 0;
}

.control-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: #262626;
  margin-bottom: 4px;
}

.control-checkbox {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.checkbox-indicator {
  width: 16px;
  height: 16px;
  border: 2px solid #d9d9d9;
  border-radius: 3px;
  margin-right: 8px;
  position: relative;
  transition: all 0.2s ease;
}

.control-checkbox:checked + .checkbox-indicator {
  background: var(--primary-color, #1890ff);
  border-color: var(--primary-color, #1890ff);
}

.control-checkbox:checked + .checkbox-indicator::after {
  content: '';
  position: absolute;
  left: 2px;
  top: -1px;
  width: 4px;
  height: 8px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.control-checkbox:focus + .checkbox-indicator {
  outline: 2px solid var(--primary-color, #1890ff);
  outline-offset: 2px;
}

.control-slider {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #f5f5f5;
  outline: none;
  margin: 8px 0;
  cursor: pointer;
}

.control-slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary-color, #1890ff);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.control-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary-color, #1890ff);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.control-description {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.4;
}

.action-button {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  color: #262626;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.action-button:hover {
  border-color: var(--primary-color, #1890ff);
  color: var(--primary-color, #1890ff);
}

.action-button:focus {
  outline: 2px solid var(--primary-color, #1890ff);
  outline-offset: 2px;
}

.action-button.primary {
  background: var(--primary-color, #1890ff);
  color: white;
  border-color: var(--primary-color, #1890ff);
}

.action-button.primary:hover {
  background: var(--primary-color-hover, #40a9ff);
  border-color: var(--primary-color-hover, #40a9ff);
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-indicator {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d9d9d9;
  margin-right: 8px;
  transition: background 0.2s ease;
}

.status-dot.active {
  background: #52c41a;
}

.status-text {
  font-size: 14px;
  color: #262626;
}

.check-results {
  margin-top: 16px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 4px;
}

.results-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
}

.results-count {
  font-weight: 600;
  color: #262626;
}

.results-time {
  font-size: 12px;
  color: #8c8c8c;
}

.issues-list,
.recommendations {
  margin-top: 12px;
}

.issues-title,
.recommendations-title {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: #262626;
}

.issues-items,
.recommendations-items {
  margin: 0;
  padding-left: 16px;
}

.issue-item,
.recommendation-item {
  font-size: 12px;
  color: #595959;
  line-height: 1.4;
  margin-bottom: 4px;
}

.panel-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.reset-button {
  width: 100%;
  padding: 10px;
  border: 1px solid #ff4d4f;
  border-radius: 4px;
  background: white;
  color: #ff4d4f;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.reset-button:hover {
  background: #ff4d4f;
  color: white;
}

.reset-button:focus {
  outline: 2px solid #ff4d4f;
  outline-offset: 2px;
}

.panel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.1);
  z-index: -1;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .accessibility-panel {
    top: 10px;
    right: 10px;
  }

  .accessibility-controls {
    width: calc(100vw - 20px);
    max-width: 360px;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .accessibility-controls {
    border: 2px solid currentColor;
  }

  .control-checkbox:checked + .checkbox-indicator {
    border-width: 3px;
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .accessibility-trigger,
  .checkbox-indicator,
  .action-button,
  .status-dot {
    transition: none;
  }

  .accessibility-controls {
    animation: none;
  }
}

/* 焦点可见性增强 */
.accessibility-panel :focus-visible {
  outline: 2px solid var(--primary-color, #1890ff) !important;
  outline-offset: 2px !important;
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .accessibility-trigger {
    width: 56px;
    height: 56px;
  }

  .action-button,
  .reset-button {
    min-height: 44px;
  }

  .control-label {
    min-height: 44px;
    align-items: center;
  }
}
</style>

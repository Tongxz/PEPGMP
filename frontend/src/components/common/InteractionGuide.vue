<template>
  <div class="interaction-guide">
    <!-- 引导遮罩 -->
    <div
      v-if="showGuide && currentStep"
      class="guide-overlay"
      @click="handleOverlayClick"
    >
      <!-- 高亮区域 -->
      <div
        class="highlight-area"
        :style="highlightStyle"
      ></div>

      <!-- 引导提示框 -->
      <div
        class="guide-tooltip"
        :style="tooltipStyle"
        :class="tooltipClass"
      >
        <div class="tooltip-header">
          <h4 class="tooltip-title">{{ currentStep.title }}</h4>
          <n-button
            text
            size="small"
            @click="closeGuide"
            class="close-btn"
          >
            <template #icon>
              <n-icon><CloseOutlined /></n-icon>
            </template>
          </n-button>
        </div>

        <div class="tooltip-content">
          <p>{{ currentStep.content }}</p>

          <!-- 操作提示 -->
          <div v-if="currentStep.action" class="action-hint">
            <n-icon class="action-icon">
              <component :is="getActionIcon(currentStep.action.type)" />
            </n-icon>
            <span>{{ currentStep.action.text }}</span>
          </div>

          <!-- 键盘快捷键提示 -->
          <div v-if="currentStep.shortcut" class="shortcut-hint">
            <span class="shortcut-label">快捷键：</span>
            <kbd class="shortcut-key">{{ currentStep.shortcut }}</kbd>
          </div>
        </div>

        <div class="tooltip-footer">
          <div class="step-indicator">
            <span class="step-current">{{ currentStepIndex + 1 }}</span>
            <span class="step-separator">/</span>
            <span class="step-total">{{ steps.length }}</span>
          </div>

          <div class="guide-actions">
            <n-button
              v-if="currentStepIndex > 0"
              size="small"
              @click="previousStep"
            >
              上一步
            </n-button>

            <n-button
              v-if="currentStepIndex < steps.length - 1"
              type="primary"
              size="small"
              @click="nextStep"
            >
              下一步
            </n-button>

            <n-button
              v-else
              type="primary"
              size="small"
              @click="finishGuide"
            >
              完成
            </n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 引导触发按钮 -->
    <n-button
      v-if="!showGuide && showTrigger"
      class="guide-trigger"
      circle
      type="primary"
      size="large"
      @click="startGuide"
    >
      <template #icon>
        <n-icon><QuestionCircleOutlined /></n-icon>
      </template>
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import {
  CloseOutline as CloseOutlined,
  HelpCircleOutline as QuestionCircleOutlined,
  FingerPrintOutline as ClickOutlined,
  MoveOutline as DragOutlined,
  KeypadOutline as KeyboardOutlined,
  EyeOutline as EyeOutlined
} from '@vicons/ionicons5'

interface GuideStep {
  id: string
  title: string
  content: string
  target: string // CSS选择器
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center'
  action?: {
    type: 'click' | 'drag' | 'input' | 'hover'
    text: string
  }
  shortcut?: string
  offset?: { x: number; y: number }
}

interface Props {
  steps: GuideStep[]
  autoStart?: boolean
  showTrigger?: boolean
  maskClosable?: boolean
  storageKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  autoStart: false,
  showTrigger: true,
  maskClosable: true,
  storageKey: 'interaction-guide'
})

const emit = defineEmits<{
  start: []
  finish: []
  stepChange: [step: GuideStep, index: number]
  close: []
}>()

// 响应式数据
const showGuide = ref(false)
const currentStepIndex = ref(0)
const targetElement = ref<HTMLElement | null>(null)

// 计算属性
const currentStep = computed(() => props.steps[currentStepIndex.value])

const highlightStyle = computed(() => {
  if (!targetElement.value) return {}

  const rect = targetElement.value.getBoundingClientRect()
  const padding = 8

  return {
    left: `${rect.left - padding}px`,
    top: `${rect.top - padding}px`,
    width: `${rect.width + padding * 2}px`,
    height: `${rect.height + padding * 2}px`
  }
})

const tooltipStyle = computed(() => {
  if (!targetElement.value) return {}

  const rect = targetElement.value.getBoundingClientRect()
  const position = currentStep.value?.position || 'bottom'
  const offset = currentStep.value?.offset || { x: 0, y: 0 }

  let left = 0
  let top = 0

  switch (position) {
    case 'top':
      left = rect.left + rect.width / 2 + offset.x
      top = rect.top - 20 + offset.y
      break
    case 'bottom':
      left = rect.left + rect.width / 2 + offset.x
      top = rect.bottom + 20 + offset.y
      break
    case 'left':
      left = rect.left - 20 + offset.x
      top = rect.top + rect.height / 2 + offset.y
      break
    case 'right':
      left = rect.right + 20 + offset.x
      top = rect.top + rect.height / 2 + offset.y
      break
    case 'center':
      left = window.innerWidth / 2 + offset.x
      top = window.innerHeight / 2 + offset.y
      break
  }

  return {
    left: `${left}px`,
    top: `${top}px`,
    transform: position === 'center' ? 'translate(-50%, -50%)' :
               position === 'top' || position === 'bottom' ? 'translateX(-50%)' :
               'translateY(-50%)'
  }
})

const tooltipClass = computed(() => {
  const position = currentStep.value?.position || 'bottom'
  return [`tooltip-${position}`]
})

// 方法
const getActionIcon = (type: string) => {
  const iconMap = {
    click: ClickOutlined,
    drag: DragOutlined,
    input: KeyboardOutlined,
    hover: EyeOutlined
  }
  return iconMap[type as keyof typeof iconMap] || ClickOutlined
}

const findTargetElement = (selector: string): HTMLElement | null => {
  return document.querySelector(selector) as HTMLElement
}

const updateTargetElement = async () => {
  if (!currentStep.value) return

  await nextTick()
  targetElement.value = findTargetElement(currentStep.value.target)

  if (targetElement.value) {
    // 滚动到目标元素
    targetElement.value.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
      inline: 'center'
    })
  }
}

const startGuide = () => {
  if (props.steps.length === 0) return

  showGuide.value = true
  currentStepIndex.value = 0
  updateTargetElement()
  emit('start')
}

const nextStep = () => {
  if (currentStepIndex.value < props.steps.length - 1) {
    currentStepIndex.value++
    updateTargetElement()
    emit('stepChange', currentStep.value, currentStepIndex.value)
  }
}

const previousStep = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
    updateTargetElement()
    emit('stepChange', currentStep.value, currentStepIndex.value)
  }
}

const finishGuide = () => {
  showGuide.value = false

  // 保存完成状态
  if (props.storageKey) {
    localStorage.setItem(props.storageKey, 'completed')
  }

  emit('finish')
}

const closeGuide = () => {
  showGuide.value = false
  emit('close')
}

const handleOverlayClick = (event: MouseEvent) => {
  if (props.maskClosable && event.target === event.currentTarget) {
    closeGuide()
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (!showGuide.value) return

  switch (event.key) {
    case 'Escape':
      closeGuide()
      break
    case 'ArrowRight':
    case 'ArrowDown':
      event.preventDefault()
      nextStep()
      break
    case 'ArrowLeft':
    case 'ArrowUp':
      event.preventDefault()
      previousStep()
      break
  }
}

// 监听器
watch(currentStepIndex, () => {
  updateTargetElement()
})

// 生命周期
onMounted(() => {
  // 检查是否需要自动启动
  if (props.autoStart) {
    const completed = props.storageKey ?
      localStorage.getItem(props.storageKey) === 'completed' : false

    if (!completed) {
      setTimeout(startGuide, 1000) // 延迟启动，确保页面加载完成
    }
  }

  // 添加键盘事件监听
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// 暴露方法给父组件
defineExpose({
  startGuide,
  nextStep,
  previousStep,
  finishGuide,
  closeGuide
})
</script>

<style scoped>
.interaction-guide {
  position: relative;
}

.guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.highlight-area {
  position: absolute;
  background: transparent;
  border: 2px solid var(--primary-color);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 4px var(--primary-color-suppl),
    0 0 20px rgba(24, 144, 255, 0.3);
  animation: highlight-pulse 2s infinite;
  pointer-events: none;
}

@keyframes highlight-pulse {
  0%, 100% {
    box-shadow:
      0 0 0 4px var(--primary-color-suppl),
      0 0 20px rgba(24, 144, 255, 0.3);
  }
  50% {
    box-shadow:
      0 0 0 8px var(--primary-color-suppl),
      0 0 30px rgba(24, 144, 255, 0.5);
  }
}

.guide-tooltip {
  position: absolute;
  background: var(--card-color);
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow-large);
  padding: var(--space-medium);
  max-width: 320px;
  min-width: 280px;
  z-index: 10000;
  border: 1px solid var(--border-color);
}

.guide-tooltip::before {
  content: '';
  position: absolute;
  width: 0;
  height: 0;
  border: 8px solid transparent;
}

.tooltip-top::before {
  bottom: -16px;
  left: 50%;
  transform: translateX(-50%);
  border-top-color: var(--card-color);
}

.tooltip-bottom::before {
  top: -16px;
  left: 50%;
  transform: translateX(-50%);
  border-bottom-color: var(--card-color);
}

.tooltip-left::before {
  right: -16px;
  top: 50%;
  transform: translateY(-50%);
  border-left-color: var(--card-color);
}

.tooltip-right::before {
  left: -16px;
  top: 50%;
  transform: translateY(-50%);
  border-right-color: var(--card-color);
}

.tooltip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-small);
}

.tooltip-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-1);
}

.close-btn {
  color: var(--text-color-3);
}

.tooltip-content {
  margin-bottom: var(--space-medium);
}

.tooltip-content p {
  margin: 0 0 var(--space-small) 0;
  color: var(--text-color-2);
  line-height: 1.5;
}

.action-hint {
  display: flex;
  align-items: center;
  gap: var(--space-small);
  padding: var(--space-small);
  background: var(--info-color-suppl);
  border-radius: var(--border-radius-small);
  color: var(--info-color);
  font-size: 14px;
  margin-top: var(--space-small);
}

.action-icon {
  font-size: 16px;
}

.shortcut-hint {
  display: flex;
  align-items: center;
  gap: var(--space-small);
  margin-top: var(--space-small);
  font-size: 14px;
  color: var(--text-color-3);
}

.shortcut-key {
  padding: 2px 6px;
  background: var(--code-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
}

.tooltip-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.step-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-color-3);
  font-size: 14px;
}

.step-current {
  color: var(--primary-color);
  font-weight: 600;
}

.guide-actions {
  display: flex;
  gap: var(--space-small);
}

.guide-trigger {
  position: fixed;
  bottom: var(--space-large);
  right: var(--space-large);
  z-index: 1000;
  box-shadow: var(--box-shadow-large);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .guide-tooltip {
    max-width: calc(100vw - 40px);
    min-width: auto;
  }

  .tooltip-footer {
    flex-direction: column;
    gap: var(--space-small);
    align-items: stretch;
  }

  .guide-actions {
    justify-content: center;
  }

  .guide-trigger {
    bottom: var(--space-medium);
    right: var(--space-medium);
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .highlight-area {
    border-width: 3px;
  }

  .guide-tooltip {
    border-width: 2px;
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .highlight-area {
    animation: none;
  }
}
</style>

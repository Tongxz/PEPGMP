<template>
  <div class="test-panel">
    <!-- 测试触发按钮 -->
    <button
      @click="togglePanel"
      class="test-trigger"
      :class="{ active: isVisible }"
      aria-label="打开测试面板"
      title="测试面板"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
      </svg>
    </button>

    <!-- 测试面板 -->
    <div v-if="isVisible" class="test-overlay" @click="closePanel">
      <div class="test-content" @click.stop>
        <div class="test-header">
          <h3>测试面板</h3>
          <button @click="closePanel" class="close-btn" aria-label="关闭测试面板">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <div class="test-body">
          <!-- 测试控制区 -->
          <div class="test-controls">
            <button
              @click="runAllTests"
              :disabled="isRunning"
              class="test-btn primary"
            >
              {{ isRunning ? '测试中...' : '运行全部测试' }}
            </button>

            <button
              @click="runPerformanceTest"
              :disabled="isRunning"
              class="test-btn"
            >
              性能测试
            </button>

            <button
              @click="runAccessibilityTest"
              :disabled="isRunning"
              class="test-btn"
            >
              无障碍测试
            </button>

            <button
              @click="runInteractionTest"
              :disabled="isRunning"
              class="test-btn"
            >
              交互测试
            </button>

            <button
              @click="runResponsiveTest"
              :disabled="isRunning"
              class="test-btn"
            >
              响应式测试
            </button>
          </div>

          <!-- 测试结果区 -->
          <div class="test-results">
            <div v-if="testResults.length === 0" class="no-results">
              点击上方按钮开始测试
            </div>

            <div v-else class="results-list">
              <div
                v-for="(result, index) in testResults"
                :key="index"
                class="result-item"
                :class="{ passed: result.passed, failed: !result.passed }"
              >
                <div class="result-header">
                  <span class="result-icon">
                    {{ result.passed ? '✅' : '❌' }}
                  </span>
                  <span class="result-title">{{ result.title }}</span>
                  <span class="result-time">{{ result.timestamp }}</span>
                </div>

                <div class="result-message">{{ result.message }}</div>

                <div v-if="result.details" class="result-details">
                  <button
                    @click="toggleDetails(index)"
                    class="details-toggle"
                  >
                    {{ result.showDetails ? '隐藏详情' : '显示详情' }}
                  </button>

                  <div v-if="result.showDetails" class="details-content">
                    <pre>{{ JSON.stringify(result.details, null, 2) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 测试报告区 -->
          <div v-if="testReport" class="test-report">
            <h4>测试报告</h4>
            <div class="report-content">
              <pre>{{ testReport }}</pre>
            </div>

            <div class="report-actions">
              <button @click="copyReport" class="test-btn">
                复制报告
              </button>
              <button @click="downloadReport" class="test-btn">
                下载报告
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { TestSuite, type TestResult } from '@/utils/testHelpers'

// 组件状态
const isVisible = ref(false)
const isRunning = ref(false)
const testResults = ref<Array<TestResult & {
  title: string
  timestamp: string
  showDetails?: boolean
}>>([])
const testReport = ref('')

// 测试工具
const testSuite = new TestSuite()

// 面板控制
const togglePanel = () => {
  isVisible.value = !isVisible.value
}

const closePanel = () => {
  isVisible.value = false
}

// 测试方法
const addTestResult = (title: string, result: TestResult) => {
  testResults.value.push({
    ...result,
    title,
    timestamp: new Date().toLocaleTimeString(),
    showDetails: false
  })
}

const runPerformanceTest = async () => {
  if (isRunning.value) return

  isRunning.value = true
  try {
    const container = document.querySelector('.region-config') as HTMLElement
    if (!container) {
      addTestResult('性能测试', {
        passed: false,
        message: '未找到测试容器'
      })
      return
    }

    const result = await testSuite['performanceUtils'].testComponentPerformance(
      'RegionConfig',
      async () => {
        await nextTick()
      }
    )

    addTestResult('性能测试', result)
  } catch (error) {
    addTestResult('性能测试', {
      passed: false,
      message: `测试失败: ${error}`
    })
  } finally {
    isRunning.value = false
  }
}

const runAccessibilityTest = async () => {
  if (isRunning.value) return

  isRunning.value = true
  try {
    const container = document.querySelector('.region-config') as HTMLElement
    if (!container) {
      addTestResult('无障碍测试', {
        passed: false,
        message: '未找到测试容器'
      })
      return
    }

    const result = await testSuite['accessibilityUtils'].runFullAccessibilityTest(container)
    addTestResult('无障碍测试', result)
  } catch (error) {
    addTestResult('无障碍测试', {
      passed: false,
      message: `测试失败: ${error}`
    })
  } finally {
    isRunning.value = false
  }
}

const runInteractionTest = async () => {
  if (isRunning.value) return

  isRunning.value = true
  try {
    const container = document.querySelector('.region-config') as HTMLElement
    if (!container) {
      addTestResult('交互测试', {
        passed: false,
        message: '未找到测试容器'
      })
      return
    }

    const result = await testSuite['interactionUtils'].testKeyboardNavigation(container)
    addTestResult('交互测试', result)
  } catch (error) {
    addTestResult('交互测试', {
      passed: false,
      message: `测试失败: ${error}`
    })
  } finally {
    isRunning.value = false
  }
}

const runResponsiveTest = async () => {
  if (isRunning.value) return

  isRunning.value = true
  try {
    const container = document.querySelector('.region-config') as HTMLElement
    if (!container) {
      addTestResult('响应式测试', {
        passed: false,
        message: '未找到测试容器'
      })
      return
    }

    const results = await testSuite['responsiveUtils'].testBreakpoints(container, [
      { name: '移动端', width: 375, height: 667 },
      { name: '平板', width: 768, height: 1024 },
      { name: '桌面端', width: 1200, height: 800 }
    ])

    results.forEach((result, index) => {
      addTestResult(`响应式测试 ${index + 1}`, result)
    })
  } catch (error) {
    addTestResult('响应式测试', {
      passed: false,
      message: `测试失败: ${error}`
    })
  } finally {
    isRunning.value = false
  }
}

const runAllTests = async () => {
  if (isRunning.value) return

  testResults.value = []
  testReport.value = ''

  isRunning.value = true
  try {
    const container = document.querySelector('.region-config') as HTMLElement
    if (!container) {
      addTestResult('全部测试', {
        passed: false,
        message: '未找到测试容器'
      })
      return
    }

    const results = await testSuite.runAllTests(container)

    // 添加各项测试结果
    addTestResult('性能测试', results.performance)
    addTestResult('无障碍测试', results.accessibility)
    addTestResult('交互测试', results.interaction)

    results.responsive.forEach((result, index) => {
      addTestResult(`响应式测试 ${index + 1}`, result)
    })

    // 生成测试报告
    testReport.value = testSuite.generateTestReport(results)
  } catch (error) {
    addTestResult('全部测试', {
      passed: false,
      message: `测试失败: ${error}`
    })
  } finally {
    isRunning.value = false
  }
}

// 工具方法
const toggleDetails = (index: number) => {
  testResults.value[index].showDetails = !testResults.value[index].showDetails
}

const copyReport = async () => {
  try {
    await navigator.clipboard.writeText(testReport.value)
    alert('报告已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
  }
}

const downloadReport = () => {
  const blob = new Blob([testReport.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `test-report-${new Date().toISOString().slice(0, 19)}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 生命周期
onMounted(() => {
  // 监听键盘快捷键
  const handleKeydown = (event: KeyboardEvent) => {
    if (event.ctrlKey && event.shiftKey && event.key === 'T') {
      event.preventDefault()
      togglePanel()
    }
  }

  document.addEventListener('keydown', handleKeydown)

  // 清理
  return () => {
    document.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped>
.test-panel {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
}

.test-trigger {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #007bff;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);
  transition: all 0.3s ease;
}

.test-trigger:hover {
  background: #0056b3;
  transform: scale(1.1);
}

.test-trigger.active {
  background: #28a745;
}

.test-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
}

.test-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.test-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.test-header h3 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  color: #666;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #333;
}

.test-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.test-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.test-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.test-btn:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #007bff;
}

.test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.test-btn.primary {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.test-btn.primary:hover:not(:disabled) {
  background: #0056b3;
}

.test-results {
  margin-bottom: 20px;
}

.no-results {
  text-align: center;
  color: #666;
  padding: 40px;
  background: #f8f9fa;
  border-radius: 4px;
}

.results-list {
  space-y: 12px;
}

.result-item {
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
}

.result-item.passed {
  border-color: #28a745;
  background: #f8fff9;
}

.result-item.failed {
  border-color: #dc3545;
  background: #fff8f8;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.result-icon {
  font-size: 16px;
}

.result-title {
  font-weight: 600;
  flex: 1;
}

.result-time {
  font-size: 12px;
  color: #666;
}

.result-message {
  color: #333;
  margin-bottom: 8px;
}

.details-toggle {
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  font-size: 12px;
  text-decoration: underline;
}

.details-content {
  margin-top: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 12px;
}

.details-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.test-report {
  border-top: 1px solid #e9ecef;
  padding-top: 20px;
}

.test-report h4 {
  margin: 0 0 12px 0;
  color: #333;
}

.report-content {
  background: #f8f9fa;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.report-content pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.report-actions {
  display: flex;
  gap: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .test-content {
    width: 95%;
    max-height: 95vh;
  }

  .test-controls {
    flex-direction: column;
  }

  .test-btn {
    width: 100%;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .test-trigger {
    border: 2px solid white;
  }

  .test-content {
    border: 2px solid #333;
  }

  .result-item {
    border-width: 2px;
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .test-trigger {
    transition: none;
  }

  .test-btn {
    transition: none;
  }
}
</style>

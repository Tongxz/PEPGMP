import { createApp } from 'vue'
import App from './App.vue'
import { globalErrorHandler, setupGlobalErrorHandling } from './composables/useErrorHandler'
import { performancePlugin } from './plugins'
import router from './router'
import { pinia } from './stores'

// 导入 Naive UI
import naive from 'naive-ui'

// 导入全局样式
import './styles/design-tokens.css'
import './styles/global.css'
import './styles/variables.css'

// 🆕 导入新设计系统 - Future Industrialism
import './styles/design-system.scss'

// 创建应用实例
const app = createApp(App)

// 设置全局错误处理器
app.config.errorHandler = globalErrorHandler.vueErrorHandler

// 使用插件
app.use(pinia)
app.use(router)
app.use(naive)

// 使用性能监控插件
app.use(performancePlugin, {
  enabled: true,
  routeTracking: true,
  componentTracking: true,
  apiTracking: true,
  reportInterval: 30000,
  consoleOutput: import.meta.env.DEV
})

// 设置全局错误处理
setupGlobalErrorHandling()

// 挂载应用
app.mount('#app')

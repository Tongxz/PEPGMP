import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import { performancePlugin } from './plugins'

// 导入 Naive UI
import naive from 'naive-ui'

// 导入全局样式
import './styles/design-tokens.css'
import './styles/variables.css'
import './styles/global.css'

// 创建应用实例
const app = createApp(App)

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

// 挂载应用
app.mount('#app')

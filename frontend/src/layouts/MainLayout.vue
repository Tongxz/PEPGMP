<template>
  <n-config-provider :theme="isDark ? darkTheme : null" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-notification-provider>
        <n-dialog-provider>
          <n-loading-bar-provider>
            <div class="layout-container">
              <!-- 侧边栏 -->
              <n-layout has-sider>
                <n-layout-sider
                  bordered
                  collapse-mode="width"
                  :collapsed-width="64"
                  :width="240"
                  :collapsed="collapsed"
                  show-trigger
                  @collapse="collapsed = true"
                  @expand="collapsed = false"
                  class="layout-sider"
                  :class="{ 'mobile-sider': isMobile }"
                >
                  <div class="logo-container">
                    <div class="logo">
                      <n-icon size="32" color="var(--primary-color)">
                        <svg viewBox="0 0 24 24">
                          <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                      </n-icon>
                      <span v-if="!collapsed" class="logo-text">智能监控</span>
                    </div>
                  </div>

                  <div class="menu-container">
                    <n-menu
                      :collapsed="collapsed"
                      :collapsed-width="64"
                      :collapsed-icon-size="22"
                      :options="menuOptions"
                      :value="activeKey"
                      @update:value="handleMenuSelect"
                      key="main-menu"
                    />
                  </div>

                  <!-- 底部操作区 -->
                  <div class="sider-footer">
                    <n-tooltip placement="right" :disabled="!collapsed">
                      <template #trigger>
                        <n-button
                          quaternary
                          circle
                          size="large"
                          @click="toggleTheme"
                          class="theme-toggle"
                        >
                          <n-icon size="20">
                            <svg v-if="isDark" viewBox="0 0 24 24">
                              <path fill="currentColor" d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/>
                            </svg>
                            <svg v-else viewBox="0 0 24 24">
                              <path fill="currentColor" d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
                            </svg>
                          </n-icon>
                        </n-button>
                      </template>
                      {{ isDark ? '切换到亮色主题' : '切换到暗色主题' }}
                    </n-tooltip>
                  </div>
                </n-layout-sider>

                <!-- 主内容区 -->
                <n-layout class="main-content">
                  <!-- 顶部导航栏 -->
                  <n-layout-header bordered class="layout-header">
                    <div class="header-content">
                      <div class="header-left">
                        <n-breadcrumb>
                          <n-breadcrumb-item
                            v-for="item in breadcrumbs"
                            :key="item.path"
                            :clickable="!!item.path"
                            @click="item.path && $router.push(item.path)"
                          >
                            {{ item.label }}
                          </n-breadcrumb-item>
                        </n-breadcrumb>
                      </div>

                      <div class="header-right">
                        <!-- 系统状态 -->
                        <n-tag :type="systemStatus.type" size="small" class="system-status">
                          {{ systemStatus.text }}
                        </n-tag>

                        <!-- 通知 -->
                        <n-badge :value="notificationCount" :max="99">
                          <n-button quaternary circle size="medium">
                            <n-icon size="18">
                              <svg viewBox="0 0 24 24">
                                <path fill="currentColor" d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
                              </svg>
                            </n-icon>
                          </n-button>
                        </n-badge>

                        <!-- 全屏切换 -->
                        <n-tooltip placement="bottom">
                          <template #trigger>
                            <n-button
                              quaternary
                              circle
                              size="medium"
                              @click="toggleFullscreen"
                            >
                              <n-icon size="18">
                                <svg viewBox="0 0 24 24">
                                  <path fill="currentColor" d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                                </svg>
                              </n-icon>
                            </n-button>
                          </template>
                          {{ isFullscreen ? '退出全屏' : '全屏显示' }}
                        </n-tooltip>
                      </div>
                    </div>
                  </n-layout-header>

                  <!-- 页面内容 -->
                  <n-layout-content class="layout-content" :native-scrollbar="false">
                    <div class="content-wrapper" :class="{ 'mobile-content': isMobile }">
                      <router-view v-slot="{ Component, route }">
                        <transition
                          :name="transitionName"
                          mode="out-in"
                          @before-enter="onBeforeEnter"
                          @after-enter="onAfterEnter"
                        >
                          <component :is="Component" :key="route.path" />
                        </transition>
                      </router-view>
                    </div>
                  </n-layout-content>

                  <!-- 底部信息栏 -->
                  <n-layout-footer bordered class="layout-footer" v-if="!isMobile">
                    <div class="footer-content">
                      <span class="copyright">© 2024 智能监控系统</span>
                      <div class="footer-info">
                        <span>版本: v1.0.0</span>
                        <n-divider vertical />
                        <span>在线用户: {{ onlineUsers }}</span>
                        <n-divider vertical />
                        <span>系统时间: {{ currentTime }}</span>
                      </div>
                    </div>
                  </n-layout-footer>
                </n-layout>
              </n-layout>
            </div>
          </n-loading-bar-provider>
        </n-dialog-provider>
      </n-notification-provider>
    </n-message-provider>

    <!-- 移动端遮罩 -->
    <div
      v-if="isMobile && !collapsed"
      class="mobile-overlay"
      @click="collapsed = true"
    />
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  darkTheme,
  NIcon,
  type MenuOption
} from 'naive-ui'
import {
  CameraOutline,
  HomeOutline,
  SettingsOutline,
  StatsChartOutline,
  InformationCircleOutline,
  NotificationsOutline,
  SunnyOutline,
  MoonOutline,
  ContrastOutline,
  ExpandOutline,
  ContractOutline,
  DocumentTextOutline
} from '@vicons/ionicons5'
import { StatusIndicator } from '@/components/common'
import { useTheme } from '@/composables/useTheme'
import { useBreakpoints } from '@/composables/useBreakpoints'

const router = useRouter()
const route = useRoute()

// 主题管理
const { isDark, toggleTheme, getThemeLabel, getThemeIcon } = useTheme()

// 响应式断点
    const { isMobile } = useBreakpoints()

// 布局状态
const collapsed = ref(false)
const activeKey = ref('')
const notificationCount = ref(3)
const systemStatus = ref<{ type: 'success' | 'warning' | 'error' | 'info' | 'default'; text: string }>({ type: 'success', text: '系统正常' })
const systemLoading = ref(false)
const onlineUsers = ref(1)
const currentTime = ref('')
const isFullscreen = ref(false)
const transitionName = ref('slide-right')

// 主题配置
const themeOverrides = {
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad6a',
    primaryColorPressed: '#0c7a43',
    primaryColorSuppl: '#36ad6a'
  }
}

// 菜单配置
const menuOptions = computed<MenuOption[]>(() => {
  const options = [
    {
      label: '首页',
      key: '/',
      icon: () => h(NIcon, null, { default: () => h(HomeOutline) })
    },
    {
      label: '相机配置',
      key: 'camera-config',
      icon: () => h(NIcon, null, { default: () => h(CameraOutline) })
    },
    {
      label: '区域配置',
      key: 'region-config',
      icon: () => h(NIcon, null, { default: () => h(SettingsOutline) })
    },
    {
      label: '统计分析',
      key: 'statistics',
      icon: () => h(NIcon, null, { default: () => h(StatsChartOutline) })
    },
    {
      label: '历史记录',
      key: 'detection-records',
      icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) })
    },
    {
      label: '系统信息',
      key: 'system-info',
      icon: () => h(NIcon, null, { default: () => h(InformationCircleOutline) })
    }
  ]
  return options
})

// 面包屑导航
const breadcrumbs = computed(() => {
  const pathMap: Record<string, string> = {
    '/': '首页',
    '/camera-config': '相机配置',
    '/region-config': '区域配置',
    '/statistics': '统计分析',
    '/detection-records': '历史记录',
    '/system-info': '系统信息'
  }

  const currentPath = route.path
  const items = [{ label: '首页', path: '/' }]

  if (currentPath !== '/') {
    items.push({ label: pathMap[currentPath] || '未知页面', path: currentPath })
  }

  return items
})

// 主题图标组件
const themeIcon = computed(() => {
  const iconName = getThemeIcon()
  switch (iconName) {
    case 'sunny-outline':
      return SunnyOutline
    case 'moon-outline':
      return MoonOutline
    case 'contrast-outline':
    default:
      return ContrastOutline
  }
})

// 菜单图标渲染
const renderMenuIcon = (option: MenuOption) => {
  return option.icon?.()
}

// 菜单标签渲染
const renderMenuLabel = (option: MenuOption) => {
  return option.label as string
}

// 菜单选择处理
const handleMenuSelect = (key: string) => {
  activeKey.value = key
  const path = key === '/' ? '/' : `/${key}`
  router.push(path)

  // 移动端收起侧边栏
  if (isMobile.value) {
    collapsed.value = true
  }
}

// 全屏切换
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 页面过渡动画
const onBeforeEnter = () => {
  // 可以在这里添加进入前的逻辑
}

const onAfterEnter = () => {
  // 可以在这里添加进入后的逻辑
}

// 更新当前时间
const updateCurrentTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// 更新活跃菜单键
    const updateActiveKey = () => {
      const currentPath = route.path

      if (currentPath === '/') {
        activeKey.value = '/'
      } else {
        const pathSegments = currentPath.split('/').filter(Boolean)
        activeKey.value = pathSegments[0] || '/'
      }
    }

// 响应式处理
const handleResize = () => {
  if (isMobile.value) {
    collapsed.value = true
  }
}

onMounted(() => {
  updateActiveKey()
  updateCurrentTime()

  // 定时更新时间
  const timeInterval = setInterval(updateCurrentTime, 1000)

  // 监听全屏变化
  document.addEventListener('fullscreenchange', handleFullscreenChange)

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)

  // 初始化响应式状态
  handleResize()

  onUnmounted(() => {
    clearInterval(timeInterval)
    document.removeEventListener('fullscreenchange', handleFullscreenChange)
    window.removeEventListener('resize', handleResize)
  })
})

// 监听路由变化
watch(route, () => {
  updateActiveKey()
}, { immediate: true })
</script>

<style scoped>
.layout-container {
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏样式 */
.layout-sider {
  background: var(--card-color);
  border-right: 1px solid var(--border-color);
  transition: all var(--duration-medium) var(--cubic-bezier-ease-in-out);
}

.mobile-sider {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 1000;
  box-shadow: var(--box-shadow-2);
}

.logo-container {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--n-border-color);
  padding: var(--space-large) var(--space-medium);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  font-size: 16px;
  color: var(--text-color);
}

.logo-text {
  color: var(--n-text-color);
  transition: opacity var(--duration-medium) var(--cubic-bezier-ease-in-out);
}

.sider-footer {
  position: absolute;
  bottom: var(--space-medium);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 0 var(--space-medium);
}

.theme-toggle {
  transition: all var(--duration-fast) var(--cubic-bezier-ease-in-out);
}

.theme-toggle:hover {
  background-color: var(--primary-color);
  color: white;
}

/* 主内容区样式 */
.main-content {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* 头部样式 */
.layout-header {
  background: var(--card-color);
  border-bottom: 1px solid var(--border-color);
  padding: 0;
  height: var(--header-height);
  flex-shrink: 0;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 var(--space-large);
}

.header-left {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-medium);
}

.system-status {
  margin-right: var(--space-small);
}

/* 内容区样式 */
.layout-content {
  flex: 1;
  overflow: hidden;
  background: var(--body-color);
}

.content-wrapper {
  height: 100%;
  padding: var(--space-large);
  overflow-y: auto;
  overflow-x: hidden;
}

.mobile-content {
  padding: var(--space-medium);
}

/* 底部样式 */
.layout-footer {
  background: var(--card-color);
  border-top: 1px solid var(--border-color);
  padding: var(--space-small) var(--space-large);
  flex-shrink: 0;
  height: var(--footer-height);
}

.footer-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--n-text-color-disabled);
  height: 100%;
}

.copyright {
  font-weight: 500;
}

.footer-info {
  display: flex;
  align-items: center;
  gap: var(--space-small);
}

/* 移动端遮罩 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  backdrop-filter: blur(4px);
}

/* 页面过渡动画 */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all var(--duration-medium) var(--cubic-bezier-ease-in-out);
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-right-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all var(--duration-medium) var(--cubic-bezier-ease-in-out);
}

.slide-left-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.slide-left-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-medium) var(--cubic-bezier-ease-in-out);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式设计 - 增强版 */
@media (max-width: 480px) {
  .layout-sider {
    width: 280px !important;
  }

  .header-content {
    padding: 0 var(--space-small);
  }

  .header-right {
    gap: var(--space-tiny);
  }

  .system-status,
  .breadcrumb {
    display: none;
  }

  .content-wrapper {
    padding: var(--space-small);
  }

  .logo-text {
    display: none;
  }

  .footer-info {
    display: none;
  }

  .copyright {
    font-size: var(--font-size-tiny);
    text-align: center;
    width: 100%;
  }
}

@media (max-width: 576px) {
  .layout-sider {
    width: 260px !important;
  }

  .header-content {
    padding: 0 var(--space-small);
  }

  .header-right {
    gap: var(--space-small);
  }

  .system-status {
    display: none;
  }

  .content-wrapper {
    padding: var(--space-medium);
  }

  .breadcrumb .n-breadcrumb-item:not(:last-child) {
    display: none;
  }
}

@media (max-width: 768px) {
  .layout-sider {
    width: 240px !important;
  }

  .header-content {
    padding: 0 var(--space-medium);
  }

  .footer-info {
    display: none;
  }

  .copyright {
    font-size: var(--font-size-tiny);
  }

  .logo-text {
    display: none;
  }

  .content-wrapper {
    padding: var(--space-medium);
  }

  /* 移动端菜单项样式调整 */
  .n-menu .n-menu-item {
    padding: var(--space-medium) var(--space-large) !important;
  }

  .n-menu .n-menu-item-content {
    font-size: var(--font-size-medium);
  }
}

@media (max-width: 992px) {
  .header-right .n-button {
    padding: var(--space-small);
  }

  .system-status .status-text {
    display: none;
  }
}

@media (max-width: 1200px) {
  .content-wrapper {
    padding: var(--space-large) var(--space-medium);
  }

  .footer-info span:nth-child(n+3) {
    display: none;
  }
}

/* 横屏模式适配 */
@media (max-height: 600px) and (orientation: landscape) {
  .layout-header {
    height: 48px;
  }

  .layout-footer {
    display: none;
  }

  .content-wrapper {
    padding: var(--space-medium);
  }

  .logo {
    height: 32px;
  }
}

/* 超大屏幕适配 */
@media (min-width: 1600px) {
  .layout-sider {
    width: 280px;
  }

  .content-wrapper {
    padding: var(--space-xl);
    max-width: 1400px;
    margin: 0 auto;
  }

  .header-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 var(--space-xl);
  }

  .footer-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 var(--space-xl);
  }
}

/* 平板竖屏模式 */
@media (min-width: 768px) and (max-width: 1024px) and (orientation: portrait) {
  .layout-sider {
    width: 200px;
  }

  .content-wrapper {
    padding: var(--space-large) var(--space-medium);
  }

  .n-menu .n-menu-item-content {
    font-size: var(--font-size-small);
  }
}

/* 平板横屏模式 */
@media (min-width: 768px) and (max-width: 1024px) and (orientation: landscape) {
  .layout-sider {
    width: 220px;
  }

  .layout-header {
    height: 56px;
  }

  .content-wrapper {
    padding: var(--space-medium);
  }
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .n-button {
    min-height: 44px;
    min-width: 44px;
  }

  .n-menu .n-menu-item {
    min-height: 48px;
  }

  .theme-toggle,
  .collapse-trigger {
    padding: var(--space-medium);
  }
}

/* 高分辨率屏幕优化 */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .logo,
  .n-icon {
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .layout-sider,
  .layout-header,
  .layout-footer {
    border-color: currentColor;
    border-width: 2px;
  }

  .n-button {
    border: 1px solid currentColor;
  }

  .system-status {
    border: 1px solid currentColor;
    border-radius: var(--border-radius-small);
  }
}

/* 减少动画的用户偏好 */
@media (prefers-reduced-motion: reduce) {
  .layout-sider,
  .logo-text,
  .theme-toggle,
  .slide-right-enter-active,
  .slide-right-leave-active,
  .slide-left-enter-active,
  .slide-left-leave-active,
  .fade-enter-active,
  .fade-leave-active,
  .n-button,
  .n-menu-item {
    transition: none !important;
    animation: none !important;
  }
}

/* 暗色模式偏好 */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    color-scheme: dark;
  }
}

/* 打印样式 */
@media print {
  .layout-sider,
  .layout-header,
  .layout-footer,
  .mobile-overlay,
  .n-button,
  .theme-toggle {
    display: none !important;
  }

  .main-content {
    height: auto !important;
    background: white !important;
  }

  .content-wrapper {
    padding: 0 !important;
    overflow: visible !important;
    background: white !important;
    color: black !important;
  }

  * {
    box-shadow: none !important;
    text-shadow: none !important;
  }
}

/* 容器查询支持 */
@supports (container-type: inline-size) {
  .content-wrapper {
    container-type: inline-size;
  }

  @container (max-width: 600px) {
    .content-wrapper > * {
      font-size: var(--font-size-small);
    }
  }

  @container (max-width: 400px) {
    .content-wrapper > * {
      font-size: var(--font-size-tiny);
    }
  }
}

/* 焦点可见性增强 */
@media (prefers-reduced-motion: no-preference) {
  .n-button:focus-visible,
  .n-menu-item:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
    transition: outline-offset var(--duration-fast) ease;
  }
}

/* 强制颜色模式支持 */
@media (forced-colors: active) {
  .layout-sider,
  .layout-header,
  .layout-footer {
    forced-color-adjust: none;
    border: 1px solid ButtonBorder;
  }

  .n-button {
    forced-color-adjust: none;
    border: 1px solid ButtonBorder;
    background: ButtonFace;
    color: ButtonText;
  }

  .n-button:hover {
    background: Highlight;
    color: HighlightText;
  }
}
</style>

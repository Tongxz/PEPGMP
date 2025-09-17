<script setup lang="ts">
const apiBase = import.meta.env.VITE_API_BASE || '/api'
</script>

<template>
  <n-config-provider>
    <n-message-provider>
      <n-notification-provider>
        <header class="nav">
          <nav>
            <RouterLink to="/">首页</RouterLink>
            <RouterLink to="/camera-config">摄像头配置</RouterLink>
            <RouterLink to="/region-config">区域配置</RouterLink>
            <RouterLink to="/statistics">统计</RouterLink>
            <RouterLink to="/system-info">系统信息</RouterLink>
          </nav>
        </header>
        <main>
          <h1>PYT 前端（Vue 3 + Vite 初始化）</h1>
          <p>API 基址：{{ apiBase }}</p>
          <router-view />
        </main>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.nav {
  padding: 12px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.nav a {
  margin-right: 12px;
  color: #2563eb;
  text-decoration: none;
}

.nav a:hover {
  text-decoration: underline;
}

main {
  padding: 24px;
}
</style>

# 实时监控页面调试指南

## 问题描述
点击"实时监控"菜单后，页面显示空白，没有任何组件。

## 可能的原因

1. **组件导入错误**
   - `VideoStreamCard` 组件路径不正确
   - `PageHeader` 组件导入失败

2. **样式问题**
   - 容器高度为0
   - 元素被隐藏

3. **数据加载问题**
   - 摄像头列表为空
   - `displayedCameras` 为空数组

4. **路由配置问题**
   - 路由未正确注册
   - 组件路径错误

## 调试步骤

### 1. 检查浏览器控制台
打开浏览器开发者工具（F12），查看：
- Console 标签页是否有错误信息
- Network 标签页是否有404错误

### 2. 检查组件文件是否存在
```bash
ls -la frontend/src/components/VideoStreamCard.vue
ls -la frontend/src/views/RealtimeMonitor.vue
```

### 3. 检查路由配置
确认 `frontend/src/router/index.ts` 中已添加路由：
```typescript
{
  path: 'realtime-monitor',
  name: 'realtime-monitor',
  component: () => import('../views/RealtimeMonitor.vue'),
}
```

### 4. 检查菜单配置
确认 `frontend/src/layouts/MainLayout.vue` 中已添加菜单项。

### 5. 临时测试
在 `RealtimeMonitor.vue` 中添加简单的测试内容：
```vue
<template>
  <div>
    <h1>实时监控测试</h1>
    <p>页面已加载</p>
  </div>
</template>
```

如果这个简单版本能显示，说明路由和菜单配置正常，问题在组件本身。

## 已修复的问题

1. ✅ 修复了重复的 `watch` 语句
2. ✅ 修复了重复的 `useMessage` 导入
3. ✅ 优化了容器样式（使用 `min-height` 而不是 `height: 100%`）
4. ✅ 改进了空状态显示逻辑

## 下一步

如果问题仍然存在，请提供：
1. 浏览器控制台的错误信息
2. Network 标签页的404错误（如果有）
3. 页面源代码中是否有任何内容

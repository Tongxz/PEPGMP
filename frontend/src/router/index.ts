import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/Home.vue'),
  },
  {
    path: '/camera-config',
    name: 'camera-config',
    component: () => import('../views/CameraConfig.vue'),
  },
  {
    path: '/region-config',
    name: 'region-config',
    component: () => import('../views/RegionConfig.vue'),
  },
  {
    path: '/statistics',
    name: 'statistics',
    component: () => import('../views/Statistics.vue'),
  },
  {
    path: '/system-info',
    name: 'system-info',
    component: () => import('../views/SystemInfo.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router

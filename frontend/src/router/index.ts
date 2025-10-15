import type { RouteRecordRaw } from 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('../views/Home.vue')
      },
      {
        path: 'camera-config',
        name: 'camera-config',
        component: () => import('../views/CameraConfig.vue'),
      },
      {
        path: 'region-config',
        name: 'region-config',
        component: () => import('../views/RegionConfig.vue'),
      },
      {
        path: 'statistics',
        name: 'statistics',
        component: () => import('../views/Statistics.vue'),
      },
      {
        path: 'detection-records',
        name: 'detection-records',
        component: () => import('../views/DetectionRecords.vue'),
      },
      {
        path: 'system-info',
        name: 'system-info',
        component: () => import('../views/SystemInfo.vue'),
      },
      {
        path: 'alerts',
        name: 'alerts',
        component: () => import('../views/Alerts.vue'),
      },
    ]
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router

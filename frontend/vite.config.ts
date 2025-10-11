import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: process.env.BASE_URL || '/',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    open: '/',
    proxy: {
      // 开发环境建议 VITE_API_BASE=/api/v1，所有 API 写相对路径，前缀走 /api
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      input: 'index.html',
      output: {
        // 代码分割策略 - 优化大型chunk
        manualChunks: (id) => {
          // Vue 核心库
          if (id.includes('vue') && !id.includes('naive-ui')) {
            return 'vue-vendor'
          }

          // Naive UI 核心组件 - 进一步细分chunk
          if (id.includes('naive-ui')) {
            // 基础组件
            if (id.includes('button') || id.includes('input') || id.includes('form')) {
              return 'ui-basic'
            }
            // 布局组件
            if (id.includes('card') || id.includes('space') || id.includes('grid') ||
              id.includes('layout') || id.includes('divider')) {
              return 'ui-layout'
            }
            // 数据展示组件
            if (id.includes('table') || id.includes('list') || id.includes('tree') ||
              id.includes('pagination') || id.includes('scrollbar')) {
              return 'ui-data'
            }
            // 反馈组件
            if (id.includes('message') || id.includes('notification') || id.includes('modal') ||
              id.includes('drawer') || id.includes('popover') || id.includes('tooltip')) {
              return 'ui-feedback'
            }
            // 导航组件
            if (id.includes('tabs') || id.includes('menu') || id.includes('breadcrumb') ||
              id.includes('steps') || id.includes('anchor')) {
              return 'ui-navigation'
            }
            // 选择器组件
            if (id.includes('select') || id.includes('cascader') || id.includes('transfer') ||
              id.includes('tree-select') || id.includes('auto-complete')) {
              return 'ui-selector'
            }
            // 日期时间组件
            if (id.includes('date') || id.includes('time') || id.includes('calendar')) {
              return 'ui-datetime'
            }
            // 上传和进度组件
            if (id.includes('upload') || id.includes('progress') || id.includes('spin')) {
              return 'ui-progress'
            }
            // 其他UI组件
            return 'ui-misc'
          }

          // 工具库
          if (id.includes('axios')) {
            return 'utils-vendor'
          }

          // Pinia 状态管理
          if (id.includes('pinia')) {
            return 'state-vendor'
          }

          // 第三方库
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        },
        // 文件命名策略
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.') || []
          let extType = info[info.length - 1]

          // 图片资源
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name || '')) {
            extType = 'images'
          }
          // 字体资源
          else if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name || '')) {
            extType = 'fonts'
          }
          // CSS 资源
          else if (/\.css$/i.test(assetInfo.name || '')) {
            extType = 'css'
          }

          return `assets/${extType}/[name]-[hash].[ext]`
        },
      },
    },
    outDir: 'dist',
    sourcemap: false,
    // 构建优化
    chunkSizeWarningLimit: 800, // 提高警告阈值到800KB
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    // 资源内联阈值
    assetsInlineLimit: 4096,
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 构建目标
    target: 'es2015',
    // 报告压缩详情
    reportCompressedSize: true,
  },
  // 依赖预构建优化
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'naive-ui',
      'axios',
    ],
    exclude: [],
  },
  // CSS 预处理器选项
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`,
      },
    },
    // CSS 模块化
    modules: {
      localsConvention: 'camelCase',
    },
  },
})

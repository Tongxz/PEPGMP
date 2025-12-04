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
    open: true,
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
        // 代码分割策略 - 简化策略，避免循环依赖
        // 将所有第三方库放在一个 vendor chunk 中，避免循环依赖问题
        manualChunks: (id) => {
          // 只处理 node_modules 中的依赖
          if (!id.includes('node_modules')) {
            return
          }

          // 所有第三方库都放在 vendor chunk 中
          // 这样可以避免循环依赖，因为所有依赖都在同一个 chunk 中
          return 'vendor'
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
    // 构建目标（提高版本以支持更好的模块初始化）
    target: 'es2020',
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

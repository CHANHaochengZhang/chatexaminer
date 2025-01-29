import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3001,
    hmr: {
      overlay: true,  // 显示错误提示
      clientPort: 3001,  // WebSocket client port
      host: 'localhost',
    },
    watch: {
      usePolling: true,  // 使用轮询监听文件变化
      interval: 100,  // 轮询间隔
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      }
    }
  }
})

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// 环境变量配置
const useRemote = process.env.VITE_USE_REMOTE === 'true'
const isLocalContainer = process.env.VITE_LOCAL_CONTAINER === 'true'

// 开发环境代理目标
const apiTarget = useRemote 
  ? 'http://127.0.0.1:8022'
  : 'http://127.0.0.1:8022'

const wsTarget = useRemote
  ? 'ws://127.0.0.1:8022'
  : 'ws://127.0.0.1:8022'

console.log(`[Vite Config] Environment: ${process.env.NODE_ENV || 'development'}`)
console.log(`[Vite Config] Use Remote: ${useRemote}`)
console.log(`[Vite Config] Local Container: ${isLocalContainer}`)
console.log(`[Vite Config] API Target: ${apiTarget}`)
console.log(`[Vite Config] WebSocket Target: ${wsTarget}`)
console.log(`[Vite Config] Note: Proxy only works in development mode`)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    allowedHosts: ['localhost', 'indoorpositioning-demo.seeed.cc', '192.168.200.24'],
    proxy: {
      // 代理配置只在开发环境有效
      // 生产环境中，这些代理不会工作，请求由 API 配置处理
      
      // API 代理 - 开发环境下将 /api 代理到后端服务器
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        secure: false, // 允许自签名证书
        configure: (proxy, options) => {
          console.log(`[Vite Proxy] Proxying /api to ${options.target}`)
        }
      },
      // 静态图片代理
      '/uploads': {
        target: apiTarget,
        changeOrigin: true,
        secure: false, // 允许自签名证书
        configure: (proxy, options) => {
          console.log(`[Vite Proxy] Proxying /uploads to ${options.target}`)
        }
      },
      
      // WebSocket 代理 - 开发环境下将 /ws 代理到后端服务器
      '/ws': {
        target: wsTarget,
        ws: true,
        changeOrigin: true,
        secure: false,
        configure: (proxy, options) => {
          console.log(`[Vite Proxy] Proxying /ws to ${options.target}`)
        }
      }
    }
  }
})

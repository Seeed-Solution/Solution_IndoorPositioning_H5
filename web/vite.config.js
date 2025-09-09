import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// 修正环境变量判断逻辑
const useRemote = process.env.VITE_USE_REMOTE === 'true'

// 开发环境：默认使用本地代理，可通过环境变量切换到直接访问远程服务器
const apiTarget = useRemote 
  ? 'http://127.0.0.1:8022'
  : 'http://127.0.0.1:8022'

const wsTarget = useRemote
  ? 'ws://127.0.0.1:8022'
  : 'ws://127.0.0.1:8022'

console.log(`[Vite Config] Environment: ${process.env.NODE_ENV || 'development'}`)
console.log(`[Vite Config] Use Remote: ${useRemote}`)
console.log(`[Vite Config] API Target: ${apiTarget}`)
console.log(`[Vite Config] WebSocket Target: ${wsTarget}`)

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
      // 只在本地开发模式下使用代理
      // 生产环境或远程开发模式下，由前端代码直接请求完整URL
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        secure: false, // 允许自签名证书
        configure: (proxy, options) => {
          // 开发环境下的代理配置
          console.log(`[Vite Proxy] Proxying /api to ${options.target}`)
        }
      },
      // WebSocket代理配置
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

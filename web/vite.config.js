import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const isRemoteDev = process.env.VITE_USE_REMOTE === 'false'

// 开发环境：默认使用本地服务器，可通过环境变量切换到远程
const apiTarget = isRemoteDev 
  ? 'http://indoorpositioning-demo.seeed.cc/config-master:8022'
  : 'http://localhost:8022'

const wsTarget = isRemoteDev
  ? 'wss://indoorpositioning-demo.seeed.cc:8022'
  : 'ws://localhost:8022'

console.log(`[Vite Config] Environment: ${process.env.NODE_ENV || 'development'}`)
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
    port: 5173, // Optional: define your frontend port if different from default
    allowedHosts: ['localhost', 'indoorpositioning-demo.seeed.cc', '192.168.200.24'],
    proxy: {
      // Proxy API requests to your FastAPI backend
      '/api': {
        target: apiTarget,
        changeOrigin: true, // Recommended for most cases
        // secure: false, // Uncomment if your backend is HTTPS with self-signed cert
        // rewrite: (path) => path.replace(/^\/api/, '') // Uncomment if your backend API routes don't include /api
      },
      // Proxy WebSocket requests
      '/ws': {
        target: wsTarget,
        ws: true,
        changeOrigin: true,
      }
    }
  }
})

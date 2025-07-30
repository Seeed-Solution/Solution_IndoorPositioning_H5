import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

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
        target: 'http://indoorpositioning-demo.seeed.cc/config-master:8022', // Your FastAPI backend address and port
        changeOrigin: true, // Recommended for most cases
        // secure: false, // Uncomment if your backend is HTTPS with self-signed cert
        // rewrite: (path) => path.replace(/^\/api/, '') // Uncomment if your backend API routes don't include /api
      },
      // Proxy WebSocket requests
      '/ws': {
        target: 'wss://indoorpositioning-demo.seeed.cc:8022', // Your FastAPI backend WebSocket address and port
        ws: true,
        changeOrigin: true,
      }
    }
  }
})

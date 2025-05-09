import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173, // Optional: define your frontend port if different from default
    proxy: {
      // Proxy API requests to your FastAPI backend
      '/api': {
        target: 'http://127.0.0.1:8022', // Your FastAPI backend address and port
        changeOrigin: true, // Recommended for most cases
        // secure: false, // Uncomment if your backend is HTTPS with self-signed cert
        // rewrite: (path) => path.replace(/^\/api/, '') // Uncomment if your backend API routes don't include /api
      },
      // Proxy WebSocket requests
      '/ws': {
        target: 'ws://127.0.0.1:8022', // Your FastAPI backend WebSocket address and port
        ws: true,
        changeOrigin: true,
      }
    }
  }
})

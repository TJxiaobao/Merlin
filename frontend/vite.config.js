/**
 * Vite Configuration for Merlin Frontend
 * Author: TJxiaobao
 * License: MIT
 */

import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 1108,
    strictPort: false,
    open: true,
    proxy: {
      '/upload': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/download': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      // ⭐️ Socket.IO 代理（虽然我们直接连接，但保留以防万一）
      '/socket.io': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true  // 启用 WebSocket 代理
      }
    }
  },
  
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true
  }
})


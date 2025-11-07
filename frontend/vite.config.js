/**
 * Vite Configuration for Merlin Frontend
 * Author: TJxiaobao
 * License: MIT
 */

import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5173,
    strictPort: false,
    open: true,
    proxy: {
      '/upload': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/execute': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/download': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true
  }
})


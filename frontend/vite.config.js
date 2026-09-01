import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

// 读取根目录 config.json
const configPath = path.resolve(__dirname, '../config.json')
let config = { backend: { host: '127.0.0.1', port: 8000 }, frontend: { port: 1145 } }
if (fs.existsSync(configPath)) {
  try {
    const content = fs.readFileSync(configPath, 'utf-8')
    config = JSON.parse(content)
  } catch (e) {
    console.warn('读取 config.json 失败，使用默认配置', e)
  }
}

const backendHost = config.backend?.host || '127.0.0.1'
const backendPort = config.backend?.port || 8000
const frontendPort = config.frontend?.port || 1145

export default defineConfig({
  plugins: [vue()],
  // ===== 新增：路径别名配置 =====
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')  // @ 指向 src 目录
    }
  },
  base: './',
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true
      },
      '/ws': {
        target: `ws://${backendHost}:${backendPort}`,
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  },
  define: {
    __BACKEND_HOST__: JSON.stringify(backendHost),
    __BACKEND_PORT__: JSON.stringify(backendPort),
  }
})
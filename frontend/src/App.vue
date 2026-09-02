<template>
  <div id="app" style="display:flex;flex-direction:column;height:100vh;overflow:hidden;">
    <header style="background:#001529;padding:8px 24px;display:flex;align-items:center;gap:20px;flex-shrink:0;flex-wrap:wrap;">
      <h1 style="color:white;font-size:18px;margin:0;">Molecular Lab Suite, MLS V26.9</h1>
      <nav style="display:flex;gap:12px;flex-wrap:wrap;">
        <router-link to="/" style="color:#aaa;text-decoration:none;font-size:14px;">首页</router-link>
        <router-link to="/gjf-modify" style="color:#aaa;text-decoration:none;font-size:14px;">修改GJF</router-link>
        <router-link to="/log-to-gjf" style="color:#aaa;text-decoration:none;font-size:14px;">LOG→GJF</router-link>
        <router-link to="/scan-extract" style="color:#aaa;text-decoration:none;font-size:14px;">提取扫描</router-link>
        <router-link to="/orbital" style="color:#aaa;text-decoration:none;font-size:14px;">轨道能量</router-link>
        <router-link to="/td" style="color:#aaa;text-decoration:none;font-size:14px;">TD信息</router-link>
        <router-link to="/soc" style="color:#aaa;text-decoration:none;font-size:14px;">SOC数据</router-link>
        <router-link to="/reorg" style="color:#aaa;text-decoration:none;font-size:14px;">重组能</router-link>
        <router-link to="/reorg-extract" style="color:#aaa;text-decoration:none;font-size:14px;">重组能提取</router-link>
      </nav>
      <div style="flex:1;"></div>
      <div style="display:flex;gap:8px;align-items:center;">
        <button class="btn btn-primary" style="height:28px;padding:0 12px;font-size:12px;" @click="showConnection = true">
          <span v-if="!remoteStore.connected">连接服务器</span>
          <span v-else>{{ remoteStore.displayName }}</span>
        </button>
        <button class="btn btn-success" style="height:28px;padding:0 12px;font-size:12px;" @click="toggleTerminal" :disabled="!remoteStore.connected">
          终端
        </button>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main style="flex:1;overflow:hidden;padding:20px;min-height:0;">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>

    <!-- 底部终端面板 -->
    <div v-if="showTerminal" class="terminal-panel" :style="{ height: terminalHeight + 'px' }">
      <div class="terminal-panel-header">
        <span class="terminal-panel-title">终端 - {{ remoteStore.displayName }}</span>
        <button class="terminal-panel-close" @click="showTerminal = false">✕</button>
      </div>
      <div ref="terminalContainer" class="terminal-panel-body"></div>
    </div>

    <!-- 连接对话框 -->
    <ConnectionDialog v-model:visible="showConnection" @connected="onConnected" />
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { Terminal } from 'xterm'
import 'xterm/css/xterm.css'
import ConnectionDialog from '@/components/ConnectionDialog.vue'

export default {
  name: 'App',
  components: { ConnectionDialog },
  setup() {
    const remoteStore = useRemoteStore()
    return { remoteStore }
  },
  data() {
    return {
      showConnection: false,
      showTerminal: false,
      terminalHeight: 280,
      terminal: null,
      ws: null,
      resizeObserver: null,
    }
  },
  watch: {
    showTerminal(val) {
      if (val) {
        this.$nextTick(() => {
          this.initTerminal()
        })
      } else {
        this.cleanupTerminal()
      }
    }
  },
  beforeUnmount() {
    this.cleanupTerminal()
  },
  methods: {
    onConnected() {
      // 连接成功后自动打开终端
      this.showTerminal = true
    },
    toggleTerminal() {
      if (this.remoteStore.connected) {
        this.showTerminal = !this.showTerminal
      }
    },
    cleanupTerminal() {
      if (this.ws) {
        try { this.ws.close() } catch(e) {}
        this.ws = null
      }
      if (this.resizeObserver) {
        try { this.resizeObserver.disconnect() } catch(e) {}
        this.resizeObserver = null
      }
      if (this.terminal) {
        try { this.terminal.dispose() } catch(e) {}
        this.terminal = null
      }
    },
    initTerminal() {
      const container = this.$refs.terminalContainer
      if (!container) return
      if (this.terminal) return

      this.terminal = new Terminal({
        cursorBlink: true,
        theme: {
          background: '#1e1e1e',
          foreground: '#d4d4d4',
          cursor: '#ffffff',
        },
        fontSize: 13,
        fontFamily: 'Consolas, monospace',
        convertEol: true,
        scrollback: 1000,
      })
      this.terminal.open(container)

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/terminal`
      this.ws = new WebSocket(wsUrl)
      this.ws.onopen = () => {
        this.ws.send(JSON.stringify({
          session_id: this.remoteStore.sessionId,
          initial_path: '/'
        }))
      }
      this.ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'output') {
          this.terminal.write(data.data)
        } else if (data.type === 'ready') {
          console.log('[Terminal] ready')
        }
      }
      this.ws.onerror = (e) => {
        console.error('[Terminal] WebSocket error:', e)
        this.terminal.write('\x1b[31mWebSocket error\x1b[0m\r\n')
      }
      this.terminal.onData((data) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ action: 'input', data }))
        }
      })

      this.resizeObserver = new ResizeObserver(() => {
        if (this.terminal && container) {
          const rect = container.getBoundingClientRect()
          const cols = Math.floor(rect.width / 9) || 80
          const rows = Math.floor(rect.height / 18) || 24
          this.terminal.resize(cols, rows)
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ action: 'resize', cols, rows }))
          }
        }
      })
      this.resizeObserver.observe(container)

      // 发送初始回车
      setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ action: 'input', data: '\r' }))
        }
      }, 500)
    }
  }
}
</script>

<style>
/* ===== 全局重置 ===== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Segoe UI', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
  background: #f5f5f5;
  height: 100vh;
  overflow: hidden;
}
.router-link-active {
  color: white !important;
  font-weight: bold;
}

/* ===== 控件系统（供所有组件复用） ===== */

/* --- 基础输入控件 --- */
.control {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 0 8px;
  font-size: 13px;
  box-sizing: border-box;
  background: white;
  color: #333;
  outline: none;
  transition: border-color 0.2s;
}
.control:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}
.control:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

/* --- 高度等级 --- */
.h-sm { height: 24px; }
.h-md { height: 28px; }
.h-lg { height: 32px; }

/* --- 宽度等级 --- */
.w-xs { width: 50px; }
.w-sm { width: 70px; }
.w-md { width: 100px; }
.w-lg { width: 140px; }
.w-xl { width: 200px; }
.w-2xl { width: 260px; }
.w-3xl { width: 360px; }
.w-full { width: 100%; }

/* --- 只读预览框 --- */
.preview {
  background: #f5f5f5;
  color: #666;
  cursor: default;
}

/* --- 标签 --- */
.label {
  font-weight: 600;
  font-size: 13px;
  color: #333;
  white-space: nowrap;
}

/* --- 按钮 --- */
.btn {
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  box-sizing: border-box;
  transition: background 0.2s, opacity 0.2s;
  padding: 0 14px;
  height: 28px;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-primary {
  background: #1890ff;
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}
.btn-success {
  background: #52c41a;
  color: white;
}
.btn-success:hover:not(:disabled) {
  background: #73d13d;
}
.btn-warning {
  background: #faad14;
  color: white;
}
.btn-warning:hover:not(:disabled) {
  background: #ffc53d;
}
.btn-danger {
  background: #ff4d4f;
  color: white;
}
.btn-danger:hover:not(:disabled) {
  background: #ff7875;
}

/* --- 选择框 --- */
select.control {
  appearance: auto;
  padding-right: 24px;
}

/* --- 文本框 --- */
textarea.control {
  padding: 8px;
  resize: vertical;
  font-family: monospace;
  line-height: 1.5;
}

/* --- Flex 工具类 --- */
.flex { display: flex; }
.flex-col { display: flex; flex-direction: column; }
.flex-center { display: flex; align-items: center; }
.flex-1 { flex: 1; }
.flex-shrink-0 { flex-shrink: 0; }
.min-h-0 { min-height: 0; }
.h-full { height: 100%; }

/* --- 间距工具类 --- */
.mr-1 { margin-right: 4px; }
.mr-2 { margin-right: 8px; }
.mr-3 { margin-right: 12px; }
.ml-1 { margin-left: 4px; }
.ml-2 { margin-left: 8px; }
.ml-3 { margin-left: 12px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }

/* ===== 底部终端面板 ===== */
.terminal-panel {
  flex-shrink: 0;
  background: #1e1e1e;
  border-top: 1px solid #444;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.25s ease-out;
}
@keyframes slideUp {
  from { height: 0; opacity: 0; }
  to { height: 280px; opacity: 1; }
}
.terminal-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #2d2d2d;
  padding: 4px 12px;
  flex-shrink: 0;
}
.terminal-panel-title {
  color: #ccc;
  font-size: 13px;
  font-weight: 500;
}
.terminal-panel-close {
  background: transparent;
  border: none;
  color: #ccc;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}
.terminal-panel-close:hover {
  color: #fff;
  background: #e81123;
  border-radius: 4px;
}
.terminal-panel-body {
  flex: 1;
  overflow: hidden;
}
.terminal-panel-body .xterm {
  height: 100% !important;
}
.terminal-panel-body .xterm-viewport {
  width: 100% !important;
}
</style>
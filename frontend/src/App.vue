<template>
  <div id="app" class="mls-shell">
    <!-- PyCharm 风格顶栏：中性工具条 + 弱边框 -->
    <header class="mls-topbar">
      <div class="mls-brand">
        <span class="mls-brand-mark">MLS</span>
        <span class="mls-brand-name">Molecular Lab Suite&nbsp;V26.9</span>
      </div>
      <nav class="mls-nav">
        <router-link to="/gjf-modify">修改GJF</router-link>
        <router-link to="/log-to-gjf">LOG→GJF</router-link>
        <router-link to="/scan-extract">提取扫描</router-link>
        <router-link to="/orbital">轨道能量</router-link>
        <router-link to="/td">TD信息</router-link>
        <router-link to="/soc">SOC数据</router-link>
        <router-link to="/reorg">重组能</router-link>
      </nav>
      <div style="flex:1;"></div>
      <div class="mls-topbar-actions">
        <button class="btn btn-primary" style="height:26px;padding:0 12px;font-size:12px;" @click="showConnection = true">
          <span v-if="!remoteStore.connected">连接服务器</span>
          <span v-else>{{ remoteStore.displayName }}</span>
        </button>
        <button class="btn btn-success" style="height:26px;padding:0 12px;font-size:12px;" @click="toggleTerminal" :disabled="!remoteStore.connected">
          终端
        </button>
        <button class="btn btn-default" style="height:26px;padding:0 12px;font-size:12px;" @click="toggleFtp" :disabled="!remoteStore.connected">
          FTP
        </button>
        <button
          class="btn btn-default mls-theme-toggle"
          :title="theme === 'dark' ? '切换到明亮模式' : '切换到暗色模式'"
          @click="toggleThemeMode"
        >
          {{ theme === 'dark' ? '☀' : '☾' }}
        </button>
      </div>
    </header>

    <!-- 主内容区域：keep-alive 保留各页解析结果；离开页面时页面自身的 ws 任务会被停用钩子停止 -->
    <main class="mls-main">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>

    <!-- 底部面板：终端居左、FTP 居右，可共存；单独打开时占满宽度 -->
    <div
      v-if="showTerminal || showFtp"
      class="mls-bottom"
      :style="{ height: terminalHeight + 'px' }"
    >
      <div v-if="showTerminal" class="terminal-panel" style="flex:1;min-width:0;width:auto;height:100%;">
        <div class="terminal-panel-header">
          <span class="terminal-panel-title">终端 - {{ remoteStore.displayName }}</span>
          <button class="terminal-panel-close" @click="showTerminal = false" title="关闭终端">×</button>
        </div>
        <div ref="terminalContainer" class="terminal-panel-body"></div>
      </div>
      <FtpPanel v-if="showFtp" style="flex:1;min-width:0;width:auto;height:100%;" @close="showFtp = false" />
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
import FtpPanel from '@/components/FtpPanel.vue'
import { currentTheme, toggleTheme } from '@/theme/theme'

export default {
  name: 'App',
  components: { ConnectionDialog, FtpPanel },
  setup() {
    const remoteStore = useRemoteStore()
    return { remoteStore }
  },
  data() {
    return {
      showConnection: false,
      showTerminal: false,
      showFtp: false,
      terminalHeight: 280,
      terminal: null,
      ws: null,
      resizeObserver: null,
      theme: currentTheme(),
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
    toggleThemeMode() {
      this.theme = toggleTheme()
    },
    toggleTerminal() {
      if (this.remoteStore.connected) {
        this.showTerminal = !this.showTerminal
      }
    },
    toggleFtp() {
      if (this.remoteStore.connected) {
        this.showFtp = !this.showFtp
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
        let data
        try {
          data = JSON.parse(e.data)
        } catch (err) {
          return
        }
        if (data.type === 'output') {
          this.terminal.write(data.data)
        } else if (data.type === 'ready') {
          console.log('[Terminal] ready')
        } else if (data.type === 'error') {
          // 后端错误也要在终端里可见（避免“只有空光标”的假象）
          console.error('[Terminal] error:', data.message)
          this.terminal.write(`\x1b[31m\r\n[终端错误] ${data.message || ''}\x1b[0m\r\n`)
        }
      }
      this.ws.onerror = () => {
        this.terminal.write('\x1b[31m\r\n[终端] WebSocket 连接错误（后端是否已启动？）\x1b[0m\r\n')
      }
      this.ws.onclose = (e) => {
        if (e && !e.wasClean) {
          this.terminal.write('\x1b[33m\r\n[终端] 连接已断开\x1b[0m\r\n')
        }
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
/* ===== 应用外壳（顶栏/主区）— 只放与框架相关样式，控件系统见 assets/style.css ===== */
.mls-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--c-app);
}
.mls-topbar {
  background: var(--c-bar);
  border-bottom: 1px solid var(--c-border);
  padding: 4px 14px;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
  flex-wrap: wrap;
  min-height: 40px;
  user-select: none;
}
.mls-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mls-brand-mark {
  background: var(--c-accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: var(--r-sm);
  padding: 2px 6px;
}
.mls-brand-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  white-space: nowrap;
}
.mls-nav {
  display: flex;
  gap: 2px;
  flex-wrap: wrap;
  align-items: center;
}
.mls-nav a {
  color: var(--c-text-2);
  text-decoration: none;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: var(--r-sm);
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.mls-nav a:hover {
  background: var(--c-hover);
  color: var(--c-text);
}
.mls-nav a.router-link-active {
  color: var(--c-accent);
  background: var(--c-accent-soft);
  font-weight: 600;
}
.mls-topbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.mls-theme-toggle {
  width: 26px;
  padding: 0;
  font-size: 14px;
  line-height: 1;
}
.mls-main {
  flex: 1;
  overflow: auto;
  padding: 16px 20px 20px 20px;
  min-height: 0;
  background: var(--c-main);
}
.mls-bottom {
  display: flex;
  flex-direction: row;
  flex-shrink: 0;
  border-top: 1px solid var(--c-border);
  background: var(--c-app);
  overflow: hidden;
}
.mls-bottom > * {
  min-width: 0;
  min-height: 0;
  height: 100%;
}
</style>
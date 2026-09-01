<template>
  <div ref="terminalContainer" style="width:100%;height:100%;background:#1e1e1e;border-radius:4px;overflow:hidden;"></div>
</template>

<script>
import { Terminal } from 'xterm'
import 'xterm/css/xterm.css'

export default {
  name: 'XTermTerminal',
  props: {
    sessionId: {
      type: String,
      required: true
    },
    initialPath: {
      type: String,
      default: '/'
    }
  },
  data() {
    return {
      terminal: null,
      ws: null,
      resizeObserver: null,
    }
  },
  mounted() {
    this.initTerminal()
  },
  beforeUnmount() {
    this.cleanup()
  },
  methods: {
    cleanup() {
      if (this.ws) {
        try { this.ws.close() } catch (e) {}
        this.ws = null
      }
      if (this.resizeObserver) {
        try { this.resizeObserver.disconnect() } catch (e) {}
        this.resizeObserver = null
      }
      if (this.terminal) {
        try { this.terminal.dispose() } catch (e) {}
        this.terminal = null
      }
    },
    initTerminal() {
      const container = this.$refs.terminalContainer
      if (!container) return

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

      // 连接 WebSocket
      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/terminal`
      this.ws = new WebSocket(wsUrl)
      this.ws.onopen = () => {
        console.log('[XTerm] WebSocket opened')
        this.ws.send(JSON.stringify({
          session_id: this.sessionId,
          initial_path: this.initialPath
        }))
      }

      this.ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'output') {
          if (this.terminal) {
            this.terminal.write(data.data)
          }
        } else if (data.type === 'ready') {
          console.log('[XTerm] Ready received')
        } else if (data.type === 'error') {
          console.error('[XTerm] Error:', data.message)
          if (this.terminal) {
            this.terminal.write(`\x1b[31m${data.message}\x1b[0m\r\n`)
          }
        }
      }

      this.ws.onerror = (e) => {
        console.error('[XTerm] WebSocket error:', e)
        if (this.terminal) {
          this.terminal.write('\x1b[31mWebSocket error\x1b[0m\r\n')
        }
      }

      // 用户输入
      this.terminal.onData((data) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ action: 'input', data }))
        }
      })

      // 调整大小
      this.resizeObserver = new ResizeObserver(() => {
        if (this.terminal && container) {
          const rect = container.getBoundingClientRect()
          const cols = Math.floor(rect.width / 9) || 80
          const rows = Math.floor(rect.height / 18) || 24
          this.terminal.resize(cols, rows)
          // 通知后端
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
              action: 'resize',
              cols: cols,
              rows: rows
            }))
          }
        }
      })
      this.resizeObserver.observe(container)
    }
  }
}
</script>

<style scoped>
:deep(.xterm) {
  height: 100% !important;
}
:deep(.xterm-viewport) {
  width: 100% !important;
}
</style>
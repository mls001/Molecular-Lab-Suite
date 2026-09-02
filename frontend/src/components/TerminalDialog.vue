<template>
  <div
    v-if="visible"
    class="terminal-float"
    ref="terminalWindow"
    :style="windowStyle"
  >
    <!-- 标题栏 -->
    <div class="terminal-header" @mousedown="startDrag">
      <span class="terminal-title">终端 - {{ store.displayName }}</span>
      <button @click="close" class="terminal-close-btn">✕</button>
    </div>
    <!-- 终端容器 -->
    <div ref="terminalContainer" class="terminal-body"></div>
    <!-- 右下角拖拽手柄 -->
    <div class="resize-handle" @mousedown="startResize"></div>
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { Terminal } from 'xterm'
import 'xterm/css/xterm.css'

export default {
  props: { visible: Boolean },
  emits: ['update:visible'],
  data() {
    return {
      terminal: null,
      ws: null,
      resizeObserver: null,
      store: null,
      // 窗口位置和尺寸
      windowX: 100,
      windowY: 100,
      windowWidth: 800,
      windowHeight: 500,
      dragging: false,
      dragOffsetX: 0,
      dragOffsetY: 0,
      resizing: false,
      resizeStartX: 0,
      resizeStartY: 0,
      resizeStartWidth: 0,
      resizeStartHeight: 0,
    }
  },
  computed: {
    windowStyle() {
      return {
        left: this.windowX + 'px',
        top: this.windowY + 'px',
        width: this.windowWidth + 'px',
        height: this.windowHeight + 'px',
      }
    }
  },
  watch: {
    visible(val) {
      if (val) {
        this.store = useRemoteStore()
        // 居中显示
        this.windowX = Math.max(0, (window.innerWidth - this.windowWidth) / 2)
        this.windowY = Math.max(0, (window.innerHeight - this.windowHeight) / 2)
        this.$nextTick(() => {
          this.initTerminal()
        })
      } else {
        this.cleanup()
      }
    }
  },
  methods: {
    // ---- 窗口拖拽 ----
    startDrag(e) {
      if (e.target.tagName === 'BUTTON') return
      this.dragging = true
      const rect = this.$refs.terminalWindow.getBoundingClientRect()
      this.dragOffsetX = e.clientX - rect.left
      this.dragOffsetY = e.clientY - rect.top
      document.addEventListener('mousemove', this.onDrag)
      document.addEventListener('mouseup', this.stopDrag)
    },
    onDrag(e) {
      if (!this.dragging) return
      this.windowX = e.clientX - this.dragOffsetX
      this.windowY = e.clientY - this.dragOffsetY
      this.windowX = Math.max(0, this.windowX)
      this.windowY = Math.max(0, this.windowY)
    },
    stopDrag() {
      this.dragging = false
      document.removeEventListener('mousemove', this.onDrag)
      document.removeEventListener('mouseup', this.stopDrag)
    },

    // ---- 窗口缩放 ----
    startResize(e) {
      e.preventDefault()
      this.resizing = true
      this.resizeStartX = e.clientX
      this.resizeStartY = e.clientY
      this.resizeStartWidth = this.windowWidth
      this.resizeStartHeight = this.windowHeight
      document.addEventListener('mousemove', this.onResize)
      document.addEventListener('mouseup', this.stopResize)
    },
    onResize(e) {
      if (!this.resizing) return
      const deltaX = e.clientX - this.resizeStartX
      const deltaY = e.clientY - this.resizeStartY
      // 最小尺寸限制
      this.windowWidth = Math.max(400, this.resizeStartWidth + deltaX)
      this.windowHeight = Math.max(200, this.resizeStartHeight + deltaY)
      // 注意：ResizeObserver 会自动调整终端大小，无需手动调用
    },
    stopResize() {
      this.resizing = false
      document.removeEventListener('mousemove', this.onResize)
      document.removeEventListener('mouseup', this.stopResize)
    },

    // ---- 终端管理 ----
    cleanup() {
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
      if (!this.store || !this.store.connected) {
        alert('未连接服务器，请先连接。')
        this.close()
        return
      }
      const container = this.$refs.terminalContainer
      if (!container) return

      this.terminal = new Terminal({
        cursorBlink: true,
        theme: { background: '#1e1e1e', foreground: '#d4d4d4', cursor: '#ffffff' },
        fontSize: 13,
        fontFamily: 'Consolas, monospace',
        convertEol: true,
        scrollback: 1000,
      })
      this.terminal.open(container)

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/terminal`
      this.ws = new WebSocket(wsUrl)
      this.ws.onopen = () => {
        this.ws.send(JSON.stringify({ session_id: this.store.sessionId, initial_path: '/' }))
      }
      this.ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'output') {
          this.terminal.write(data.data)
        } else if (data.type === 'ready') {
          console.log('[TerminalDialog] ready')
        }
      }
      this.ws.onerror = (e) => {
        console.error('[TerminalDialog] WebSocket error:', e)
        this.terminal.write('\x1b[31mWebSocket error\x1b[0m\r\n')
      }
      this.terminal.onData((data) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ action: 'input', data }))
        }
      })
      // Resize 监听
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
    },
    close() {
      this.$emit('update:visible', false)
    }
  }
}
</script>

<style scoped>
.terminal-float {
  position: fixed;
  background: #1e1e1e;
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  z-index: 9999;
  border: 1px solid #444;
  user-select: none;
  min-width: 400px;
  min-height: 200px;
}
.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #2d2d2d;
  padding: 6px 12px;
  border-radius: 8px 8px 0 0;
  flex-shrink: 0;
  cursor: move;
}
.terminal-title {
  color: #ccc;
  font-size: 13px;
  font-weight: 500;
}
.terminal-close-btn {
  background: transparent;
  border: none;
  color: #ccc;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}
.terminal-close-btn:hover {
  color: #fff;
  background: #e81123;
  border-radius: 4px;
}
.terminal-body {
  flex: 1;
  overflow: hidden;
  border-radius: 0 0 8px 8px;
}
.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, #666 50%);
  border-radius: 0 0 8px 0;
  z-index: 10;
}
.resize-handle:hover {
  background: linear-gradient(135deg, transparent 50%, #888 50%);
}
</style>
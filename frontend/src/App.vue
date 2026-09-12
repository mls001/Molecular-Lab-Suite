<template>
  <div id="app" class="mls-shell">
    <!-- 顶栏两行：上行=功能页面（左对齐），下行=外部程序/日志/终端/FTP 等（右对齐） -->
    <header class="mls-topbar">
      <div class="mls-topbar-row">
        <div class="mls-brand">
          <span class="mls-brand-mark">MLS</span>
          <span class="mls-brand-name">Molecular Lab Suite&nbsp;V26.9</span>
        </div>
        <nav class="mls-nav">
          <router-link to="/molecule">{{ $t('分子结构') }}</router-link>
          <router-link to="/input-gen">{{ $t('生成输入') }}</router-link>
          <router-link to="/gjf-modify">{{ $t('修改GJF') }}</router-link>
          <router-link to="/scan-extract">{{ $t('提取扫描') }}</router-link>
          <router-link to="/orbital">{{ $t('轨道能量') }}</router-link>
          <router-link to="/nto">{{ $t('NTO分析') }}</router-link>
          <router-link to="/hole-electron">{{ $t('电子空穴') }}</router-link>
          <router-link to="/td">{{ $t('TD信息') }}</router-link>
          <router-link to="/soc">{{ $t('SOC数据') }}</router-link>
          <router-link to="/reorg">{{ $t('重组能') }}</router-link>
        </nav>
      </div>
      <div class="mls-topbar-row mls-topbar-row-actions">
        <div class="mls-topbar-actions">
        <button class="btn btn-primary" style="height:26px;padding:0 12px;font-size:12px;" @click="showConnection = true">
          <span v-if="!remoteStore.connected">{{ $t('连接服务器') }}</span>
          <span v-else>{{ remoteStore.displayName }}</span>
        </button>
        <button class="btn btn-success" style="height:26px;padding:0 12px;font-size:12px;" @click="toggleTerminal" :disabled="!remoteStore.connected">
          {{ $t('终端') }}
        </button>
        <button class="btn btn-default" style="height:26px;padding:0 12px;font-size:12px;" @click="toggleFtp" :disabled="!remoteStore.connected">
          FTP
        </button>
        <!-- 外部程序（Multiwfn / VMD）工作目录：为后续联用分析、绘图做准备 -->
        <button
          class="btn"
          :class="toolsStore.configured ? 'btn-primary' : 'btn-default'"
          style="height:26px;padding:0 12px;font-size:12px;"
          :title="toolsStore.configured ? ($t('外部程序') + '：' + toolsStore.summary) : $t('添加 Multiwfn / VMD 工作目录')"
          @click="showTools = true"
        >
          {{ $t('外部程序') }}
        </button>
        <!-- 日志面板开关（右上角）：关闭后仍可用此按钮重新打开 -->
        <button
          class="btn"
          :class="logPanel.visible ? 'btn-primary' : 'btn-default'"
          style="height:26px;padding:0 12px;font-size:12px;"
          :title="$t('日志')"
          @click="logPanel.toggle()"
        >
          {{ $t('日志') }}
        </button>
        <button
          class="btn btn-default mls-theme-toggle"
          :title="theme === 'dark' ? $t('切换到明亮模式') : $t('切换到暗色模式')"
          @click="toggleThemeMode"
        >
          {{ theme === 'dark' ? '☀' : '☾' }}
        </button>
        <button class="btn btn-default mls-lang-toggle" :title="$t('切换语言')" @click="onToggleLang">
          {{ uiLang === 'en' ? 'EN' : '中文' }}
        </button>
        </div>
      </div>
    </header>

    <!-- 主内容区域：keep-alive 保留各页解析结果；离开页面时页面自身的 ws 任务会被停用钩子停止 -->
    <main class="mls-main">
      <!-- 按路径给 key：NTO 与电子空穴共用同一个视图组件，不加 key 会被 keep-alive 当成同一页复用 -->
      <router-view v-slot="{ Component, route }">
        <keep-alive>
          <component :is="Component" :key="route.path" />
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
          <span class="terminal-panel-title">{{ $t('终端') }} - {{ remoteStore.displayName }}</span>
          <button class="terminal-panel-close" @click="showTerminal = false" :title="$t('关闭终端')">×</button>
        </div>
        <div ref="terminalContainer" class="terminal-panel-body"></div>
      </div>
      <FtpPanel v-if="showFtp" style="flex:1;min-width:0;width:auto;height:100%;" @close="showFtp = false" />
    </div>

    <!-- 连接对话框 -->
    <ConnectionDialog v-model:visible="showConnection" @connected="onConnected" />

    <!-- 外部程序（Multiwfn / VMD）工作目录 -->
    <ExternalToolsModal v-model:visible="showTools" />

    <!-- Multiwfn 引用说明（调用外部 Multiwfn 功能前整屏弹出） -->
    <MultiwfnCitationModal />

    <!-- 应用内 本地路径选择器（全局单例）：pickDirectory/pickFile 均通过它返回路径 -->
    <LocalPathPicker />

    <!-- 最下方的全局进度条：Multiwfn/VMD 处理与 FTP 传输都在这里显示 -->
    <ProgressBar />
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { Terminal } from 'xterm'
import 'xterm/css/xterm.css'
import ConnectionDialog from '@/components/ConnectionDialog.vue'
import FtpPanel from '@/components/FtpPanel.vue'
import LocalPathPicker from '@/components/LocalPathPicker.vue'
import ExternalToolsModal from '@/components/ExternalToolsModal.vue'
import MultiwfnCitationModal from '@/components/MultiwfnCitationModal.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import { currentTheme, toggleTheme } from '@/theme/theme'
import { useLogPanelStore } from '@/stores/logPanel'
import { useExternalToolsStore } from '@/stores/externalTools'
import { t as $tr } from '@/i18n'


export default {
  name: 'App',
  components: { ConnectionDialog, FtpPanel, LocalPathPicker, ExternalToolsModal, MultiwfnCitationModal, ProgressBar },
  setup() {
    const remoteStore = useRemoteStore()
    const logPanel = useLogPanelStore()
    const toolsStore = useExternalToolsStore()
    return { remoteStore, logPanel, toolsStore }
  },
  data() {
    return {
      showConnection: false,
      showTools: false,
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
    window.removeEventListener('mls-open-external-tools', this.openTools)
    this.cleanupTerminal()
  },
  mounted() {
    window.addEventListener('mls-open-external-tools', this.openTools)
    // 启动时解析一次 Multiwfn / VMD 位置（配置的目录优先，其次系统 PATH）
    this.toolsStore.detect()
  },
  methods: {
    openTools() {
      this.showTools = true
    },
    onConnected() {
      // 连接成功后自动打开终端
      this.showTerminal = true
    },
    toggleThemeMode() {
      this.theme = toggleTheme()
    },
    onToggleLang() {
      this.$toggleLang()
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
          this.terminal.write(`\x1b[31m\r\n[${$tr('终端错误')}] ${data.message || ''}\x1b[0m\r\n`)
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
/* 顶栏 = 两条硬边工具条：上行功能页（左对齐）、下行操作按钮（右对齐） */
.mls-topbar {
  background: var(--c-bar);
  border-bottom: 1px solid var(--c-border-strong);
  box-shadow: inset 0 1px 0 var(--bevel-light);
  padding: 3px 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex-shrink: 0;
  user-select: none;
}
.mls-topbar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 26px;
  width: 100%;
}
.mls-topbar-row-actions { justify-content: flex-end; }
.mls-brand {
  display: flex;
  align-items: center;
  gap: 6px;
}
.mls-brand-mark {
  background: linear-gradient(180deg, var(--c-titlebar-b), var(--c-titlebar-a));
  color: var(--c-titlebar-text);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border: 1px solid var(--c-border-strong);
  box-shadow: inset 1px 1px 0 var(--bevel-light);
  border-radius: 0;
  padding: 1px 5px;
}
.mls-brand-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--c-text);
  white-space: nowrap;
}
/* 导航 = 98 风格立体标签页：未选中浮起，选中呈"按下"效果 */
.mls-nav {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
  align-items: center;
}
.mls-nav a {
  color: var(--c-text);
  text-decoration: none;
  font-size: 12px;
  padding: 3px 10px;
  border: 1px solid var(--c-border-strong);
  border-radius: 0;
  background: var(--c-btn-face);
  box-shadow: inset 1px 1px 0 var(--bevel-light), inset -1px -1px 0 var(--bevel-dark);
  white-space: nowrap;
}
.mls-nav a:hover {
  background: var(--c-hover);
}
.mls-nav a.router-link-active {
  background: var(--c-main);
  font-weight: 700;
  color: var(--c-accent);
  box-shadow: inset 1px 1px 0 var(--bevel-dark), inset -1px -1px 0 var(--bevel-light);
  padding-top: 4px;
}
.mls-topbar-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}
.mls-theme-toggle,
.mls-lang-toggle {
  min-width: 30px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 1;
}
.mls-main {
  flex: 1;
  overflow: auto;
  padding: 8px 10px 10px 10px;
  min-height: 0;
  background: var(--c-main);
}
.mls-bottom {
  display: flex;
  flex-direction: row;
  flex-shrink: 0;
  border-top: 1px solid var(--c-border-strong);
  background: var(--c-app);
  overflow: hidden;
}
.mls-bottom > * {
  min-width: 0;
  min-height: 0;
  height: 100%;
}
</style>
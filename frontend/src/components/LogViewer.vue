<template>
  <div v-if="panel.visible" class="log-panel">
    <div class="log-panel-head">
      <span>{{ $t('日志') }}</span>
      <button class="log-panel-close" :title="$t('关闭日志')" @click="panel.set(false)">×</button>
    </div>
    <div class="log-viewer" ref="logContainer">
      <div v-for="(line, i) in lines" :key="i" :style="{color: line.color || '#d4d4d4'}">
        {{ line.text }}
      </div>
      <div v-if="!lines.length" style="color:#666;">{{ $t('就绪') }}</div>
    </div>
  </div>
</template>

<script>
import { useLogPanelStore } from '@/stores/logPanel'

export default {
  name: 'LogViewer',
  props: {
    lines: {
      type: Array,
      default: () => []
    }
  },
  setup() {
    const panel = useLogPanelStore()
    return { panel }
  },
  watch: {
    lines: {
      handler() {
        this.scrollToBottom()
      },
      deep: true,
      immediate: true
    }
  },
  updated() {
    // 防止组件更新后未触发 watch（比如 push 但引用不变）
    this.scrollToBottom()
  },
  methods: {
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.logContainer
        if (container) {
          // 使用 setTimeout 确保 DOM 渲染完成
          setTimeout(() => {
            container.scrollTop = container.scrollHeight
          }, 20)
        }
      })
    }
  }
}
</script>

<style scoped>
/* 日志面板：深色底 + 硬朗直角边框；标题行右侧的 × 用于关闭（顶栏按钮可再次打开） */
.log-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #3a3f45;
  box-shadow: inset 1px 1px 0 #0b0d0f;
  background: #16181b;
}
.log-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 4px 0 8px;
  height: 18px;
  background: #2b3036;
  border-bottom: 1px solid #3a3f45;
  color: #b9c0c8;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  user-select: none;
}
.log-panel-close {
  background: transparent;
  border: 1px solid transparent;
  color: #b9c0c8;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  padding: 0 5px;
  border-radius: 0;
}
.log-panel-close:hover {
  background: #e81123;
  border-color: #7a0a13;
  color: #fff;
}
.log-viewer {
  height: 54px;
  overflow-y: auto;
  padding: 3px 8px;
  color: #d4d4d4;
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.45;
}
.log-viewer::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}
.log-viewer::-webkit-scrollbar-track {
  background: #1d2024;
}
.log-viewer::-webkit-scrollbar-thumb {
  background: #4a5057;
  border: 1px solid #23272b;
  box-shadow: inset 1px 1px 0 #6b737c, inset -1px -1px 0 #14171a;
  border-radius: 0;
}
</style>

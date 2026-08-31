<template>
  <div class="log-viewer" ref="logContainer">
    <div v-for="(line, i) in lines" :key="i" :style="{color: line.color || '#d4d4d4'}">
      {{ line.text }}
    </div>
    <div v-if="!lines.length" style="color:#666;">就绪</div>
  </div>
</template>

<script>
export default {
  name: 'LogViewer',
  props: {
    lines: {
      type: Array,
      default: () => []
    }
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
.log-viewer {
  flex-shrink: 0;
  height: 50px;
  background: #1e1e1e;
  border-radius: 6px;
  padding: 4px 12px;
  overflow-y: auto;
  color: #d4d4d4;
  font-family: monospace;
  font-size: 12px;
}
.log-viewer::-webkit-scrollbar {
  width: 6px;
}
.log-viewer::-webkit-scrollbar-track {
  background: #2a2a2a;
  border-radius: 3px;
}
.log-viewer::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}
</style>
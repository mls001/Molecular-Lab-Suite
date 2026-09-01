<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:bold;">📂 选择远程路径</span>
        <button class="btn btn-danger h-lg" @click="close">✕</button>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <input class="control h-lg" style="flex:1;" v-model="currentPath" placeholder="路径" />
        <button class="btn btn-primary h-lg" @click="refresh">🔄 刷新</button>
        <button class="btn btn-warning h-lg" @click="goParent">📤 上级</button>
      </div>
      <div style="flex:1;overflow-y:auto;border:1px solid #e8e8e8;border-radius:4px;padding:4px;min-height:200px;max-height:400px;">
        <div
          v-for="entry in entries"
          :key="entry.name"
          class="browser-item"
          @click="selectItem(entry)"
          @dblclick="enterDir(entry)"
          style="padding:4px 8px;cursor:pointer;display:flex;align-items:center;gap:8px;border-bottom:1px solid #f5f5f5;"
          :style="{ background: selectedItem && selectedItem.name === entry.name ? '#e6f7ff' : 'transparent' }"
        >
          <span v-if="entry.is_dir">📁</span>
          <span v-else>📄</span>
          <span style="flex:1;">{{ entry.name }}</span>
          <span style="font-size:12px;color:#999;">{{ entry.is_dir ? '' : formatSize(entry.size) }}</span>
        </div>
        <div v-if="!entries.length" style="padding:20px;text-align:center;color:#999;">目录为空或无法读取</div>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px;justify-content:flex-end;">
        <button class="btn btn-primary h-lg" @click="confirm" :disabled="!selectedItem">✅ 选择</button>
        <button class="btn btn-default h-lg" @click="close">取消</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RemoteFileBrowser',
  props: {
    visible: {
      type: Boolean,
      required: true
    },
    sessionId: {
      type: String,
      required: true
    },
    initialPath: {
      type: String,
      default: '/'
    },
    target: {
      type: String,
      default: ''
    }
  },
  emits: ['update:visible', 'select'],
  data() {
    return {
      currentPath: this.initialPath || '/',
      entries: [],
      selectedItem: null
    }
  },
  watch: {
    initialPath(newVal) {
      this.currentPath = newVal || '/'
    },
    visible(newVal) {
      if (newVal) {
        this.currentPath = this.initialPath || '/'
        this.selectedItem = null
        this.refresh()
      }
    }
  },
  methods: {
    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / 1048576).toFixed(1) + ' MB'
    },
    async refresh() {
      if (!this.sessionId) {
        console.warn('缺少 sessionId')
        return
      }
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/remote/ls`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            path: this.currentPath
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.entries = data.entries || []
          this.currentPath = data.current_path || this.currentPath
        } else {
          console.error('读取目录失败:', data.detail)
        }
      } catch (e) {
        console.error('读取目录失败:', e.message)
      }
    },
    goParent() {
      const parts = this.currentPath.split('/').filter(p => p)
      if (parts.length > 0) {
        parts.pop()
        this.currentPath = '/' + parts.join('/')
        if (this.currentPath === '') this.currentPath = '/'
        this.refresh()
      }
    },
    selectItem(entry) {
      this.selectedItem = entry
    },
    enterDir(entry) {
      if (entry.is_dir) {
        this.currentPath = this.currentPath.endsWith('/') ? this.currentPath + entry.name : this.currentPath + '/' + entry.name
        this.selectedItem = null
        this.refresh()
      }
    },
    confirm() {
      if (!this.selectedItem) return
      const fullPath = this.currentPath.endsWith('/') ? this.currentPath + this.selectedItem.name : this.currentPath + '/' + this.selectedItem.name
      this.$emit('select', {
        target: this.target,
        path: fullPath,
        is_dir: this.selectedItem.is_dir,
        name: this.selectedItem.name
      })
      this.close()
    },
    close() {
      this.$emit('update:visible', false)
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.modal-content {
  background: white;
  border-radius: 8px;
  padding: 20px;
  width: 600px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.browser-item:hover {
  background: #f0f0f0 !important;
}
</style>
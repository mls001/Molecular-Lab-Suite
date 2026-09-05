<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-content" style="width:600px;max-height:70vh;background:var(--c-elev);border-radius:8px;padding:16px;display:flex;flex-direction:column;color:var(--c-text);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:bold;">选择远程路径</span>
        <button class="btn btn-danger h-lg" @click="close">X</button>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <input class="control h-lg" style="flex:1;" v-model="currentPath" placeholder="路径" />
        <button class="btn btn-primary h-lg" @click="refresh">刷新</button>
        <button class="btn btn-warning h-lg" @click="goParent">上级</button>
        <button class="btn btn-success h-lg" @click="showMk = !showMk">新建文件夹</button>
      </div>
      <div v-if="showMk" class="flex" style="gap:8px;margin-bottom:8px;">
        <input class="control h-lg" style="flex:1;" v-model="mkName" placeholder="输入新文件夹名（将创建于当前路径下）" @keydown.enter="createFolder" />
        <button class="btn btn-primary h-lg" @click="createFolder" :disabled="creating">创建</button>
        <button class="btn btn-default h-lg" @click="showMk = false; mkName = ''">取消</button>
      </div>
      <div style="flex:1;overflow-y:auto;border:1px solid var(--c-border);border-radius:4px;padding:4px;">
        <div
          v-for="entry in entries"
          :key="entry.name"
          class="browser-item"
          @click="selectItem(entry)"
          @dblclick="onDoubleClick(entry)"
          style="padding:4px 8px;cursor:pointer;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--c-border-soft);"
          :style="{ background: selectedItem && selectedItem.name === entry.name ? 'var(--c-accent-soft)' : 'transparent' }"
        >
          <span v-if="entry.is_dir"></span>
          <span v-else></span>
          <span style="flex:1;">{{ entry.name }}</span>
          <span style="font-size:12px;color:var(--c-text-3);">{{ entry.is_dir ? '' : formatSize(entry.size) }}</span>
        </div>
        <div v-if="!entries.length" style="padding:20px;text-align:center;color:var(--c-text-3);">目录为空或无法读取</div>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px;justify-content:flex-end;">
        <button class="btn btn-primary h-lg" @click="confirm" :disabled="!canConfirm">选择</button>
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
      selectedItem: null,
      backendUrl: '', // 新增：动态后端地址
      showMk: false,
      mkName: '',
      creating: false
    }
  },
  computed: {
    canConfirm() {
      return this.selectedItem !== null || (this.currentPath && this.currentPath !== '/')
    }
  },
  async mounted() {
    // 获取后端地址（与上一个组件保持一致）
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        this.backendUrl = await window.electronAPI.getBackendUrl()
      } catch (e) {
        console.error('获取后端地址失败:', e)
        this.backendUrl = 'http://127.0.0.1:8002' // 降级
      }
    } else {
      // 开发环境 fallback
      this.backendUrl = 'http://127.0.0.1:8002'
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
      if (!this.sessionId) return
      try {
        const response = await fetch(`${this.backendUrl}/api/remote/ls`, {
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
        this.selectedItem = null
        this.refresh()
      }
    },
    selectItem(entry) {
      this.selectedItem = entry
    },
    async createFolder() {
      const name = (this.mkName || '').trim()
      if (!name || name.indexOf('/') >= 0 || name.indexOf('\\') >= 0) {
        alert('请输入合法的文件夹名（不含 / 或 \\）')
        return
      }
      const path = (this.currentPath.endsWith('/') ? this.currentPath : this.currentPath + '/') + name
      this.creating = true
      try {
        const r = await fetch(`${this.backendUrl}/api/remote/mkdir`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, path })
        })
        const d = await r.json().catch(() => ({}))
        if (r.ok) {
          this.currentPath = path
          this.mkName = ''
          this.showMk = false
          this.selectedItem = null
          this.refresh()
        } else {
          alert('创建失败：' + (d.detail || `HTTP ${r.status}`))
        }
      } catch (e) {
        alert('创建失败：' + (e.message || e))
      } finally {
        this.creating = false
      }
    },
    onDoubleClick(entry) {
      if (entry.is_dir) {
        // 双击目录：进入
        this.currentPath = this.currentPath.endsWith('/') ? this.currentPath + entry.name : this.currentPath + '/' + entry.name
        this.selectedItem = null
        this.refresh()
      } else {
        // 双击文件：直接确认选择
        this.selectedItem = entry
        this.confirm()
      }
    },
    confirm() {
      let resultPath
      let isDir = false
      let name = ''

      if (this.selectedItem) {
        const fullPath = this.currentPath.endsWith('/') ? this.currentPath + this.selectedItem.name : this.currentPath + '/' + this.selectedItem.name
        resultPath = fullPath
        isDir = this.selectedItem.is_dir
        name = this.selectedItem.name
      } else {
        resultPath = this.currentPath
        isDir = true
        name = this.currentPath.split('/').filter(p => p).pop() || this.currentPath
      }

      this.$emit('select', {
        target: this.target,
        path: resultPath,
        is_dir: isDir,
        name: name
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
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.modal-content {
  background: var(--c-elev);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 20px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.browser-item {
  color: var(--c-text);
}
.browser-item:hover {
  background: var(--c-hover) !important;
}
</style>
<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-content" @mousedown.stop @click.stop style="width:520px;background:var(--c-elev);border-radius:8px;padding:20px;box-shadow:0 4px 20px rgba(0,0,0,0.35);color:var(--c-text);">
      <h3 style="margin-top:0;">连接服务器</h3>

      <!-- 预设管理 -->
      <div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;">
        <select class="control h-lg" style="flex:1;min-width:120px;" v-model="selectedPreset" @change="onPresetChange">
          <option value="">-- 加载预设 --</option>
          <option v-for="name in connectionPresetNames" :key="name" :value="name">{{ name.replace(/^conn_/, '') }}</option>
        </select>
        <input class="control h-lg" style="width:120px;" v-model="newPresetName" placeholder="预设名称" />
        <button class="btn btn-primary h-lg" @click="savePreset">保存</button>
        <button class="btn btn-danger h-lg" @click="deletePreset" :disabled="!selectedPreset">删除</button>
      </div>

      <!-- 连接参数 -->
      <div style="display:grid;grid-template-columns:70px 1fr;gap:8px;margin-bottom:12px;">
        <label>主机</label>
        <input v-model="localHost" class="control h-lg" placeholder="IP地址" />
        <label>端口</label>
        <input v-model="localPort" class="control h-lg" placeholder="22" />
        <label>用户名</label>
        <input v-model="localUsername" class="control h-lg" placeholder="用户名" />
        <label>密码</label>
        <input v-model="localPassword" class="control h-lg" type="password" placeholder="密码" />
      </div>

      <!-- 按钮 -->
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;">
        <button class="btn btn-primary" @click="doConnect" :disabled="connecting">
          {{ connecting ? (remoteStore.backendRetrying ? '连接中(等待后端启动)…' : '连接中…') : '连接' }}
        </button>
        <button class="btn btn-default" @click="close" :disabled="connecting">取消</button>
      </div>

      <!-- 后端未就绪 / 自动重试提示 -->
      <div v-if="connecting && remoteStore.backendRetrying" style="color:#d46b08;margin-top:8px;font-size:13px;">
         {{ remoteStore.error }}
      </div>

      <div v-if="errorMessage" style="color:#ff4d4f;margin-top:8px;">{{ errorMessage }}</div>
    </div>
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'

export default {
  props: { visible: Boolean },
  emits: ['update:visible', 'connected'],
  setup() {
    const remoteStore = useRemoteStore()
    return { remoteStore }
  },
  data() {
    return {
      localHost: '',
      localPort: 22,
      localUsername: '',
      localPassword: '',
      connecting: false,
      errorMessage: '',
      selectedPreset: '',
      newPresetName: '',
      presetNames: [],
      backendUrl: '' // 新增：动态获取的后端地址
    }
  },
  computed: {
    connectionPresetNames() {
      return this.presetNames.filter(name => name.startsWith('conn_'))
    }
  },
  async mounted() {
    // 获取后端地址（通过 preload 暴露的方法）
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        this.backendUrl = await window.electronAPI.getBackendUrl()
      } catch (e) {
        console.error('获取后端地址失败:', e)
        this.backendUrl = 'http://127.0.0.1:8002' // 降级
      }
    } else {
      // 开发环境 fallback（直接访问 localhost）
      this.backendUrl = 'http://127.0.0.1:8002'
    }
  },
  watch: {
    visible(val) {
      if (val) {
        const store = useRemoteStore()
        this.localHost = store.host || ''
        this.localPort = store.port || 22
        this.localUsername = store.username || ''
        this.localPassword = ''
        this.errorMessage = ''
        this.selectedPreset = ''
        this.newPresetName = ''
        this.loadPresetList()
      }
    }
  },
  methods: {
    async loadPresetList() {
      try {
        const response = await fetch(`${this.backendUrl}/api/preset/list`)
        const data = await response.json()
        this.presetNames = data.names || []
      } catch (e) {
        console.error('加载预设列表失败:', e)
      }
    },

    async savePreset() {
      const name = this.newPresetName.trim()
      if (!name) {
        this.errorMessage = '请输入预设名称'
        return
      }
      if (!this.localHost || !this.localUsername) {
        this.errorMessage = '请填写主机和用户名'
        return
      }
      const fullName = `conn_${name}`
      try {
        const response = await fetch(`${this.backendUrl}/api/preset/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: fullName,
            host: this.localHost,
            port: this.localPort,
            username: this.localUsername,
            password: this.localPassword,
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.errorMessage = ''
          this.newPresetName = ''
          await this.loadPresetList()
          this.selectedPreset = fullName
          this.$emit('connected')
        } else {
          this.errorMessage = data.detail || '保存失败'
        }
      } catch (e) {
        this.errorMessage = `保存失败: ${e.message}`
      }
    },

    async onPresetChange() {
      if (!this.selectedPreset) return
      try {
        const response = await fetch(`${this.backendUrl}/api/preset/load?name=${encodeURIComponent(this.selectedPreset)}`)
        const data = await response.json()
        if (response.ok) {
          this.localHost = data.host || ''
          this.localPort = data.port || 22
          this.localUsername = data.username || ''
          this.localPassword = data.password || ''
          this.errorMessage = ''
        } else {
          this.errorMessage = data.detail || '加载失败'
        }
      } catch (e) {
        this.errorMessage = `加载失败: ${e.message}`
      }
    },

    async deletePreset() {
      if (!this.selectedPreset) return
      if (!confirm(`确定删除预设 "${this.selectedPreset.replace(/^conn_/, '')}" 吗？`)) return
      try {
        const response = await fetch(`${this.backendUrl}/api/preset/delete?name=${encodeURIComponent(this.selectedPreset)}`, {
          method: 'DELETE'
        })
        const data = await response.json()
        if (response.ok) {
          this.selectedPreset = ''
          await this.loadPresetList()
        } else {
          this.errorMessage = data.detail || '删除失败'
        }
      } catch (e) {
        this.errorMessage = `删除失败: ${e.message}`
      }
    },

    async doConnect() {
      if (!this.localHost || !this.localUsername) {
        this.errorMessage = '请填写主机和用户名'
        return
      }
      this.connecting = true
      this.errorMessage = ''
      const store = useRemoteStore()
      const result = await store.connect(this.localHost, this.localPort, this.localUsername, this.localPassword)
      if (result.success) {
        this.$emit('connected')
        this.close()
      } else {
        this.errorMessage = result.message
      }
      this.connecting = false
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
  max-width: 90vw;
  max-height: 80vh;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  color: var(--c-text);
}
.modal-content label {
  color: var(--c-text-2);
}
</style>
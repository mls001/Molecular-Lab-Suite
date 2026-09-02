import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useRemoteStore = defineStore('remote', () => {
  const sessionId = ref('')
  const connected = ref(false)
  const host = ref('')
  const port = ref(22)
  const username = ref('')
  const connecting = ref(false)
  const error = ref('')
  const backendUrl = ref('') // 新增：动态后端地址

  const displayName = computed(() => {
    if (!connected.value) return '未连接'
    return `${username.value}@${host.value}:${port.value}`
  })

  // 获取后端地址
  async function getBackendUrl() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        backendUrl.value = await window.electronAPI.getBackendUrl()
        return backendUrl.value
      } catch (e) {
        console.error('获取后端地址失败:', e)
        backendUrl.value = 'http://127.0.0.1:8000'
        return backendUrl.value
      }
    }
    backendUrl.value = 'http://127.0.0.1:8000'
    return backendUrl.value
  }

  // 加载配置
  function loadConfig() {
    if (window.electronAPI && window.electronAPI.storeGet) {
      const saved = window.electronAPI.storeGet('remote')
      if (saved) {
        host.value = saved.host || ''
        port.value = saved.port || 22
        username.value = saved.username || ''
        // 不自动连接，只填充表单
      }
    }
  }

  // 保存配置
  function saveConfig() {
    if (window.electronAPI && window.electronAPI.storeSet) {
      window.electronAPI.storeSet('remote', {
        host: host.value,
        port: port.value,
        username: username.value,
        // 不保存 password（安全考虑）
      })
    }
  }

  async function connect(hostVal, portVal, usernameVal, passwordVal) {
    if (connecting.value) return
    connecting.value = true
    error.value = ''

    // 确保后端地址已获取
    if (!backendUrl.value) {
      await getBackendUrl()
    }

    try {
      const response = await fetch(`${backendUrl.value}/api/remote/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host: hostVal, port: portVal, username: usernameVal, password: passwordVal, auth_method: 'password' })
      })
      const data = await response.json()
      if (response.ok) {
        sessionId.value = data.session_id
        connected.value = true
        host.value = hostVal
        port.value = portVal
        username.value = usernameVal
        saveConfig()   // 保存配置
        return { success: true, message: '连接成功' }
      } else {
        error.value = data.detail
        return { success: false, message: data.detail }
      }
    } catch (e) {
      error.value = e.message
      return { success: false, message: e.message }
    } finally {
      connecting.value = false
    }
  }

  async function disconnect() {
    if (!sessionId.value) return

    // 确保后端地址已获取
    if (!backendUrl.value) {
      await getBackendUrl()
    }

    try {
      await fetch(`${backendUrl.value}/api/remote/disconnect?session_id=${sessionId.value}`, {
        method: 'DELETE'
      })
    } catch (e) {
      console.error('[RemoteStore] disconnect error:', e)
    } finally {
      sessionId.value = ''
      connected.value = false
      // 不清除 host/port/username，保留配置
    }
  }

  // 初始化：加载配置 + 获取后端地址
  loadConfig()
  getBackendUrl() // 异步获取后端地址

  return {
    sessionId,
    connected,
    host,
    port,
    username,
    connecting,
    error,
    displayName,
    connect,
    disconnect,
    loadConfig,
    saveConfig
  }
})
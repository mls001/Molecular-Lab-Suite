import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useRemoteStore = defineStore('remote', () => {
  const sessionId = ref('')
  const connected = ref(false)
  const host = ref('')
  const port = ref(22)
  const username = ref('')
  const password = ref('') // 仅在内存中存储
  const connecting = ref(false)
  const error = ref('')
  // 后端服务连通性状态（用于提示“后端启动中/未就绪”）
  const backendReady = ref(true)
  const backendRetrying = ref(false)
  const backendUrl = ref('http://127.0.0.1:8002')

  const displayName = computed(() => {
    // 连接成功后仅显示用户名（界面要求，不暴露主机/IP）
    if (!connected.value) return '未连接'
    return username.value || '已连接'
  })

  // 获取后端地址
  async function getBackendUrl() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        const url = await window.electronAPI.getBackendUrl()
        backendUrl.value = url
        return url
      } catch (e) {
        console.error('获取后端地址失败:', e)
        backendUrl.value = 'http://127.0.0.1:8002'
        return backendUrl.value
      }
    }
    backendUrl.value = 'http://127.0.0.1:8002'
    return backendUrl.value
  }

  // 加载配置（非敏感数据）
  async function loadConfig() {
    if (window.electronAPI && window.electronAPI.storeGet) {
      const saved = await window.electronAPI.storeGet('remote')
      if (saved) {
        host.value = saved.host || ''
        port.value = saved.port || 22
        username.value = saved.username || ''
      }
    }

    // 从 keytar 加载密码（如果存在）
    if (window.electronAPI && window.electronAPI.keytar) {
      try {
        const result = await window.electronAPI.keytar.getPassword()
        if (result.success && result.password) {
          password.value = result.password
          console.log('[RemoteStore] 从系统密钥链加载密码成功')
        }
      } catch (e) {
        console.warn('[RemoteStore] 从系统密钥链加载密码失败:', e)
      }
    }
  }

  // 保存配置（非敏感数据）
  function saveConfig() {
    if (window.electronAPI && window.electronAPI.storeSet) {
      const saved = window.electronAPI.storeSet('remote', {
        host: host.value,
        port: port.value,
        username: username.value,
        // 密码不保存到 store，通过 keytar 单独保存
      })
      if (saved && typeof saved.catch === 'function') {
        saved.catch((e) => console.warn('[RemoteStore] 保存配置失败:', e))
      }
    }
  }

  // 保存密码到系统密钥链
  async function savePassword(passwordVal) {
    if (window.electronAPI && window.electronAPI.keytar) {
      try {
        if (passwordVal) {
          await window.electronAPI.keytar.setPassword(passwordVal)
          console.log('[RemoteStore] 密码已保存到系统密钥链')
        } else {
          await window.electronAPI.keytar.deletePassword()
          console.log('[RemoteStore] 密码已从系统密钥链删除')
        }
        return true
      } catch (e) {
        console.error('[RemoteStore] 保存密码失败:', e)
        return false
      }
    }
    return false
  }

  // 删除密码
  async function deletePassword() {
    if (window.electronAPI && window.electronAPI.keytar) {
      try {
        await window.electronAPI.keytar.deletePassword()
        password.value = ''
        console.log('[RemoteStore] 密码已从系统密钥链删除')
        return true
      } catch (e) {
        console.error('[RemoteStore] 删除密码失败:', e)
        return false
      }
    }
    return false
  }

  // 判断是否为网络层错误（后端未启动/未就绪时 fetch 抛 TypeError）
  function isNetworkError(e) {
    if (!e) return false
    if (e.name === 'AbortError') return true
    const msg = (e && e.message) || ''
    return e instanceof TypeError || /fetch|network|ECONN|Failed to fetch/i.test(msg)
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

  async function connect(hostVal, portVal, usernameVal, passwordVal) {
    if (connecting.value) return
    connecting.value = true
    error.value = ''
    backendRetrying.value = false

    if (!backendUrl.value || backendUrl.value === 'http://127.0.0.1:8002') {
      await getBackendUrl()
    }
    const url = backendUrl.value

    // 后端冷启动（导入 pandas/rdkit 等）可能需数十秒：网络层失败时自动等待重试
    const MAX_ATTEMPTS = 12 // 每次失败后等待 5s，最多约 60s
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        const response = await fetch(`${url}/api/remote/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host: hostVal,
            port: portVal,
            username: usernameVal,
            password: passwordVal,
            auth_method: 'password'
          })
        })
        const data = await response.json().catch(() => ({}))
        if (response.ok) {
          sessionId.value = data.session_id
          connected.value = true
          host.value = hostVal
          port.value = portVal
          username.value = usernameVal
          password.value = passwordVal
          backendReady.value = true
          backendRetrying.value = false

          // 保存配置（非敏感数据）
          saveConfig()
          // 保存密码到系统密钥链
          await savePassword(passwordVal)

          connecting.value = false
          return { success: true, message: '连接成功' }
        }
        // 后端可达但连接失败（如认证失败、超时）→ 直接返回真实原因
        backendReady.value = true
        backendRetrying.value = false
        error.value = data.detail || '连接失败'
        connecting.value = false
        return { success: false, message: data.detail || '连接失败' }
      } catch (e) {
        if (!isNetworkError(e)) {
          backendReady.value = true
          backendRetrying.value = false
          error.value = e.message || '连接失败'
          connecting.value = false
          return { success: false, message: e.message || '连接失败' }
        }
        // 网络层失败：等待后端健康后重试
        backendReady.value = false
        if (attempt < MAX_ATTEMPTS) {
          backendRetrying.value = true
          error.value = `后端服务尚未就绪，正在等待并自动重试 (${attempt}/${MAX_ATTEMPTS - 1})…`
          await sleep(5000)
          continue
        }
      }
    }

    backendReady.value = false
    backendRetrying.value = false
    const msg = '无法连接后端服务：多次重试仍失败。请确认应用后端已成功启动（首次启动可能需要等待 30~60 秒），或重新打开应用后再试。'
    error.value = msg
    connecting.value = false
    return { success: false, message: msg }
  }

  async function disconnect() {
    if (!sessionId.value) return

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
    }
  }

  function setBackendUrl(url) {
    backendUrl.value = url
  }

  // 初始化
  loadConfig()

  return {
    sessionId,
    connected,
    host,
    port,
    username,
    password,
    connecting,
    error,
    backendReady,
    backendRetrying,
    backendUrl,
    displayName,
    connect,
    disconnect,
    loadConfig,
    saveConfig,
    savePassword,
    deletePassword,
    getBackendUrl,
    setBackendUrl,
  }
})
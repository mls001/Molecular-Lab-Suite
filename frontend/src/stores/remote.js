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

  const displayName = computed(() => {
    if (!connected.value) return '未连接'
    return `${username.value}@${host.value}:${port.value}`
  })

  async function connect(hostVal, portVal, usernameVal, passwordVal) {
    if (connecting.value) return
    connecting.value = true
    error.value = ''
    try {
      const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/remote/connect`, {
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
    try {
      await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/remote/disconnect?session_id=${sessionId.value}`, {
        method: 'DELETE'
      })
    } catch (e) {
      console.error('[RemoteStore] disconnect error:', e)
    } finally {
      sessionId.value = ''
      connected.value = false
      host.value = ''
      port.value = 22
      username.value = ''
    }
  }

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
    disconnect
  }
})
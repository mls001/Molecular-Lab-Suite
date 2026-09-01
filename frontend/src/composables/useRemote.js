import { ref } from 'vue'

export function useRemote() {
  const sessionId = ref('')
  const connected = ref(false)
  const connecting = ref(false)
  const error = ref('')

  const connect = async ({ host, port, username, password }) => {
    if (connecting.value) return
    connecting.value = true
    error.value = ''
    try {
      const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/remote/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host, port, username, password, auth_method: 'password' })
      })
      const data = await response.json()
      if (response.ok) {
        sessionId.value = data.session_id
        connected.value = true
        console.log('[useRemote] Session saved:', sessionId.value)
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

  const disconnect = async () => {
    if (!sessionId.value) return
    try {
      await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/remote/disconnect?session_id=${sessionId.value}`, {
        method: 'DELETE'
      })
    } catch (e) {
      console.error('[useRemote] Disconnect error:', e)
    } finally {
      sessionId.value = ''
      connected.value = false
      console.log('[useRemote] Session cleared')
    }
  }

  const listDirectory = async (path) => {
    if (!sessionId.value) throw new Error('未连接')
    const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/remote/ls`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, path })
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail)
    return data
  }

  return {
    sessionId,
    connected,
    connecting,
    error,
    connect,
    disconnect,
    listDirectory
  }
}
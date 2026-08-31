class WebSocketClient {
  constructor(url) {
    this.url = url
    this.ws = null
    this.callbacks = {}
    this.reconnectTimer = null
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return
    this.ws = new WebSocket(this.url)
    this.ws.onopen = () => {
      console.log('WebSocket 已连接')
      this.emit('connected')
    }
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.emit('message', data)
      } catch (e) {
        console.error('解析消息失败:', e)
      }
    }
    this.ws.onclose = () => {
      console.log('WebSocket 已断开')
      this.emit('disconnected')
      // 尝试重连
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
      this.reconnectTimer = setTimeout(() => {
        this.connect()
      }, 3000)
    }
    this.ws.onerror = (err) => {
      console.error('WebSocket 错误:', err)
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket 未连接，无法发送消息')
    }
  }

  on(event, callback) {
    if (!this.callbacks[event]) this.callbacks[event] = []
    this.callbacks[event].push(callback)
  }

  emit(event, data) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(cb => cb(data))
    }
  }

  close() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export default WebSocketClient
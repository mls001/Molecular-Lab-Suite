// 后端地址 + 带重试的请求：后端是单独的 68 MB 可执行文件，启动要几秒，
// 界面首屏如果在它起来之前发请求就会 "Failed to fetch"。这里统一重试到后端就绪。
let cachedBase = ''

export async function backendBase() {
  if (cachedBase) return cachedBase
  if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
    try {
      const u = await window.electronAPI.getBackendUrl()
      if (u) { cachedBase = u; return cachedBase }
    } catch (e) { /* 主进程还没准备好就退回编译期地址 */ }
  }
  cachedBase = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
  return cachedBase
}

/** 网络错误（后端还没起来）/ 502 / 503 都算“可以再等等” */
export function isRetryable(err, status) {
  if (status === 502 || status === 503 || status === 504) return true
  if (!err) return false
  const m = String(err.message || err)
  return /Failed to fetch|NetworkError|ERR_CONNECTION|fetch failed|ECONNREFUSED/i.test(m)
}

/**
 * 带重试的 fetch（默认：最多 ~15 秒，每 500ms 一次，逐次退避）
 * @returns {Promise<Response>} 最后一次的响应；全部失败则抛出最后一个错误
 */
export async function fetchWithRetry(url, options = {}, { tries = 30, delay = 500, maxDelay = 1500, onWait } = {}) {
  let lastErr = null
  let wait = delay
  for (let i = 0; i < tries; i++) {
    try {
      const resp = await fetch(url, options)
      if (!isRetryable(null, resp.status)) return resp
      lastErr = new Error(`HTTP ${resp.status}`)
    } catch (e) {
      if (!isRetryable(e)) throw e
      lastErr = e
    }
    if (i === tries - 1) break
    if (onWait) { try { onWait(i + 1) } catch (e) { /* ignore */ } }
    await new Promise((r) => setTimeout(r, wait))
    wait = Math.min(maxDelay, Math.round(wait * 1.4))
  }
  throw lastErr || new Error('后端未就绪')
}

/** 等到后端 /api/health 可用（可选，用于需要“确保后端在”的场景） */
export async function waitForBackend(opts) {
  const base = await backendBase()
  const resp = await fetchWithRetry(`${base}/api/health`, {}, opts)
  return resp.ok
}

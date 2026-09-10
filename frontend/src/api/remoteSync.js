// 远程解析公共工具：把远程目录中的目标扩展名文件同步到后端本地缓存，返回缓存目录
const BACKEND_BASE = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`

function posixJoin(p, n) {
  return `${String(p).replace(/\/+$/, '')}/${n}`
}

// 从后端返回的缓存文件路径推导缓存目录（兼容 / 与 \ 两种分隔符）
function dirOf(cachePath) {
  const cp = cachePath || ''
  const idx = Math.max(cp.lastIndexOf('/'), cp.lastIndexOf('\\'))
  return idx >= 0 ? cp.substring(0, idx) : ''
}

/**
 * 将远程目录 remoteFolder 中的 <ext> 文件(如 .log)同步到缓存
 * @returns {Promise<{cacheDir:string, count:number}>}
 */
export async function syncRemoteFolder(sessionId, remoteFolder, ext = '.log') {
  if (!sessionId) throw new Error('未连接服务器')
  const lsResp = await fetch(`${BACKEND_BASE}/api/remote/ls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, path: remoteFolder })
  })
  const lsData = await lsResp.json()
  if (!lsResp.ok) throw new Error(lsData.detail || '无法读取远程目录')

  const wanted = (lsData.entries || [])
    .filter((x) => !x.is_dir && String(x.name).toLowerCase().endsWith(ext.toLowerCase()))
    .map((x) => x.name)
  if (!wanted.length) throw new Error(`远程目录中没有 ${ext} 文件`)

  const paths = wanted.map((n) => posixJoin(remoteFolder, n))
  const dlResp = await fetch(`${BACKEND_BASE}/api/remote/batch-download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, paths })
  })
  const dlData = await dlResp.json()
  if (!dlResp.ok) throw new Error(dlData.detail || '文件同步失败')
  const okPaths = (dlData.results || []).filter((r) => r.status === 'success')
  if (!okPaths.length) throw new Error('文件同步失败，请检查远程目录权限')

  const cacheDir = dirOf(okPaths[0].cache_path)
  if (!cacheDir) throw new Error('无法确定本地缓存目录')
  return { cacheDir, count: okPaths.length }
}

export { BACKEND_BASE }

// 远程解析公共工具：把远程目录中的目标文件同步到后端本地缓存，返回缓存路径
const BACKEND_BASE = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`

// Multiwfn 能直接读的波函数文件（与后端 WAVEFN_EXTS 对应，按优先级排序）
const WAVEFN_EXTS = ['fch', 'fchk', 'wfx', 'molden', 'wfn', 'mwfn', '47', 'gbw']

function posixJoin(p, n) {
  return `${String(p).replace(/\/+$/, '')}/${n}`
}

function extOf(name) {
  const i = String(name).lastIndexOf('.')
  return i > 0 ? String(name).slice(i + 1).toLowerCase() : ''
}

function stemOf(name) {
  const i = String(name).lastIndexOf('.')
  return i > 0 ? String(name).slice(0, i) : String(name)
}

// 从后端返回的缓存文件路径推导缓存目录（兼容 / 与 \ 两种分隔符）
function dirOf(cachePath) {
  const cp = cachePath || ''
  const idx = Math.max(cp.lastIndexOf('/'), cp.lastIndexOf('\\'))
  return idx >= 0 ? cp.substring(0, idx) : ''
}

/** 列远程目录 */
export async function remoteLs(sessionId, path) {
  if (!sessionId) throw new Error('未连接服务器')
  const resp = await fetch(`${BACKEND_BASE}/api/remote/ls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, path })
  })
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.detail || '无法读取远程目录')
  return data.entries || []
}

/** 批量下载远程文件到本地缓存，返回 results（含 cache_path / status） */
export async function downloadRemote(sessionId, paths) {
  if (!sessionId) throw new Error('未连接服务器')
  const resp = await fetch(`${BACKEND_BASE}/api/remote/batch-download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, paths })
  })
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.detail || '文件同步失败')
  return data.results || []
}

/**
 * 将远程目录 remoteFolder 中的 <ext> 文件(如 .log)同步到缓存
 * @returns {Promise<{cacheDir:string, count:number}>}
 */
export async function syncRemoteFolder(sessionId, remoteFolder, ext = '.log') {
  const entries = await remoteLs(sessionId, remoteFolder)
  const wanted = entries
    .filter((x) => !x.is_dir && String(x.name).toLowerCase().endsWith(ext.toLowerCase()))
    .map((x) => x.name)
  if (!wanted.length) throw new Error(`远程目录中没有 ${ext} 文件`)

  const results = await downloadRemote(sessionId, wanted.map((n) => posixJoin(remoteFolder, n)))
  const okPaths = results.filter((r) => r.status === 'success')
  if (!okPaths.length) throw new Error('文件同步失败，请检查远程目录权限')

  const cacheDir = dirOf(okPaths[0].cache_path)
  if (!cacheDir) throw new Error('无法确定本地缓存目录')
  return { cacheDir, count: okPaths.length }
}

/**
 * 找远程目录里与 stem 同名的波函数文件（.fchk/.wfn/.wfx/.molden/.47/.gbw）
 * @returns {Promise<string[]>} 文件名（按优先级排序）
 */
export async function findRemoteWavefn(sessionId, remoteFolder, stem) {
  const entries = await remoteLs(sessionId, remoteFolder)
  const want = String(stem).toLowerCase()
  return entries
    .filter((x) => !x.is_dir)
    .map((x) => x.name)
    .filter((n) => stemOf(n).toLowerCase() === want && WAVEFN_EXTS.includes(extOf(n)))
    .sort((a, b) => WAVEFN_EXTS.indexOf(extOf(a)) - WAVEFN_EXTS.indexOf(extOf(b)))
}

export { BACKEND_BASE, WAVEFN_EXTS, posixJoin, stemOf, extOf }

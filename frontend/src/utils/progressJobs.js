// 多文件并行任务的进度显示规则（纯函数，方便单测）
//
// 同一个界面里可以同时跑多个文件的任务（渲染 A 的同时切到 B 再渲染 B），
// 每个任务用 key = '<文件路径>|<类型>' 标识；进度条只显示"当前正在看的文件"的任务。

/** 任务 key：文件路径 + 类型（render / analyze / cub / restore …） */
export function jobKey(path, kind) {
  return `${path || ''}|${kind || ''}`
}

/**
 * 当前该显示哪个任务：
 *   - active 非空：只挑这个文件自己的任务（多个就挑最新更新的那个，按 seq）
 *   - active 为空：用不区分的任务（key = ''，其他页面的老用法）
 * 找不到就返回 null
 */
export function pickJob(jobs, active) {
  const all = jobs || {}
  const keys = Object.keys(all).filter((k) => (active ? k.startsWith(active + '|') : k === ''))
  let best = null
  keys.forEach((k) => {
    const j = all[k]
    if (!j) return
    if (!best || (j.seq || 0) > (best.seq || 0)) best = j
  })
  return best || null
}

/** 当前文件之外还有几个任务在跑（用来提示"还有 N 个文件正在后台处理…"） */
export function otherJobCount(jobs, active) {
  return Object.keys(jobs || {}).filter((k) => !(active ? k.startsWith(active + '|') : k === '')).length
}

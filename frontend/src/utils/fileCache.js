// 每个文件各自的界面状态缓存（键 = 文件完整路径）
// 规则：取不到就返回空，绝不沿用上一个文件的值 —— 否则会把 A 的波函数/勾选/图带到 B 上
export function cacheGet(cache, path) {
  if (!cache || !path) return null
  return cache[path] || null
}

/** 切到某个文件时该用的波函数文件：该文件自己缓存过的，没有就返回空串（让组件按新文件重新查找） */
export function cachedWavefn(cache, path) {
  const c = cacheGet(cache, path)
  return (c && c.wavefnPath) || ''
}

/** 通用字段读取：取不到就用默认值 */
export function cachedList(cache, path, field) {
  const c = cacheGet(cache, path)
  const v = c ? c[field] : null
  return Array.isArray(v) ? v : []
}

export function cachedMap(cache, path, field) {
  const c = cacheGet(cache, path)
  const v = c ? c[field] : null
  return v && typeof v === 'object' ? v : {}
}

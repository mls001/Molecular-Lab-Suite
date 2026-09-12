// 外部程序（Multiwfn / VMD / tachyon）可执行文件位置解析：
// 先看用户配置的目录，找不到再去系统 PATH（环境变量）里找 —— 由后端统一判断。
import { BACKEND_BASE } from './remoteSync'

/**
 * @returns {Promise<{ok:boolean, path:string, dir:string, kind:string, error?:string}>}
 */
export async function resolveProgram(kind, dir = '') {
  const qs = new URLSearchParams({ kind, dir: dir || '' }).toString()
  try {
    const resp = await fetch(`${BACKEND_BASE}/api/ext/program?${qs}`)
    const data = await resp.json()
    return {
      ok: resp.ok && !!data.ok,
      path: data.path || '',
      dir: data.dir || '',
      kind: data.kind || kind,
      error: resp.ok ? '' : (data.detail || '检测失败')
    }
  } catch (e) {
    return { ok: false, path: '', dir, kind, error: e.message }
  }
}

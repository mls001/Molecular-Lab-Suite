// 3Dmol 统一加载入口：只使用打包进来的版本，保证离线/内网机器也能用
// （以前这里是「打包版失败就退回 CDN」，对方没网时 3D 视图会直接空白）
let loading = null

export async function load3Dmol() {
  if (window.$3Dmol && typeof window.$3Dmol.createViewer === 'function') return window.$3Dmol
  if (!loading) {
    loading = (async () => {
      try {
        const mod = await import('3dmol/build/3Dmol.es6.js')
        const lib = mod && (mod.default || mod)
        if (lib && typeof lib.createViewer === 'function') {
          window.$3Dmol = lib
          return lib
        }
        console.warn('[3Dmol] 打包版本里没有 createViewer')
      } catch (e) {
        console.warn('[3Dmol] 打包版本加载失败:', e && e.message)
      }
      return null
    })()
  }
  return loading
}

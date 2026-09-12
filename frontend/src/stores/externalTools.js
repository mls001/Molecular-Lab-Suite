// 外部程序工作目录（Multiwfn / VMD）：为「与 Multiwfn / VMD 联用分析绘图」准备。
// 目录存在 localStorage；可执行文件的实际路径（含系统 PATH 里找到的）每次启动重新解析。
import { defineStore } from 'pinia'
import { resolveProgram } from '@/api/externalTools'

const KEY = 'mls.externalTools'

function read() {
  try {
    const raw = localStorage.getItem(KEY)
    const d = raw ? JSON.parse(raw) : {}
    return { multiwfnDir: d.multiwfnDir || '', vmdDir: d.vmdDir || '' }
  } catch (e) {
    return { multiwfnDir: '', vmdDir: '' }
  }
}

export const useExternalToolsStore = defineStore('externalTools', {
  state: () => ({ ...read(), multiwfnPath: '', vmdPath: '', pathChecked: false }),
  getters: {
    // 目录配了、或系统 PATH 里能找到，就算可用
    multiwfnReady: (s) => !!(s.multiwfnDir || s.multiwfnPath),
    vmdReady: (s) => !!(s.vmdDir || s.vmdPath),
    configured() { return !!(this.multiwfnReady || this.vmdReady) },
    summary() {
      const m = this.multiwfnPath || this.multiwfnDir
      const v = this.vmdPath || this.vmdDir
      return [m && `Multiwfn: ${m}`, v && `VMD: ${v}`].filter(Boolean).join('  ·  ')
    }
  },
  actions: {
    save(payload = {}) {
      if (payload.multiwfnDir !== undefined) this.multiwfnDir = payload.multiwfnDir || ''
      if (payload.vmdDir !== undefined) this.vmdDir = payload.vmdDir || ''
      try {
        localStorage.setItem(KEY, JSON.stringify({ multiwfnDir: this.multiwfnDir, vmdDir: this.vmdDir }))
      } catch (e) { /* ignore */ }
      window.dispatchEvent(new CustomEvent('mls-external-tools-change'))
    },
    // 解析 Multiwfn / VMD 可执行文件位置（目录优先，其次系统 PATH）
    async detect() {
      const [m, v] = await Promise.all([
        resolveProgram('multiwfn', this.multiwfnDir),
        resolveProgram('vmd', this.vmdDir)
      ])
      this.multiwfnPath = m.ok ? m.path : ''
      this.vmdPath = v.ok ? v.path : ''
      this.pathChecked = true
      return this
    }
  }
})

// 使用外部 Multiwfn 功能前必须让用户确认引用说明：
// 每次调用 Multiwfn 之前 require() 一次；用户勾了「我将时刻牢记，不再提示」之后就永久放行。
import { defineStore } from 'pinia'
import { BACKEND_BASE } from '@/api/remoteSync'

const KEY = 'mls.multiwfnCitation.ack'

// 等待确认的 resolve 队列（放在模块作用域，避免进响应式 state）
let waiters = []

export const useMultiwfnCitationStore = defineStore('multiwfnCitation', {
  state: () => ({
    ack: (() => { try { return localStorage.getItem(KEY) === '1' } catch (e) { return false } })(),
    visible: false,
    loading: false,
    payload: null,
    kind: ''
  }),
  getters: {
    mustCite: (s) => (s.payload && s.payload.must_cite) || [],
    extraCite: (s) => (s.payload && s.payload.extra_cite) || [],
    body: (s) => (s.payload && s.payload.body) || '',
    links: (s) => (s.payload && s.payload.links) || [],
    pdf: (s) => (s.payload && s.payload.pdf) || ''
  },
  actions: {
    async load(kind = '') {
      if (this.payload && this.kind === kind) return this.payload
      this.loading = true
      try {
        const qs = new URLSearchParams({ kind: kind || '' }).toString()
        const resp = await fetch(`${BACKEND_BASE}/api/ext/citation?${qs}`)
        const data = await resp.json()
        if (resp.ok) { this.payload = data; this.kind = kind }
      } catch (e) { /* 拿不到就只显示最关键的引用信息 */ }
      this.loading = false
      return this.payload
    },
    /** 调用 Multiwfn 之前等用户确认；已勾选「不再提示」则立即返回 true */
    async require(kind = '') {
      if (this.ack) return true
      await this.load(kind)
      this.visible = true
      return await new Promise((resolve) => { waiters.push(resolve) })
    },
    confirm(remember) {
      if (remember) {
        this.ack = true
        try { localStorage.setItem(KEY, '1') } catch (e) { /* ignore */ }
      }
      this.visible = false
      const list = waiters
      waiters = []
      list.forEach((r) => r(true))
    },
    /** 重新允许提示（设置页里用） */
    reset() {
      this.ack = false
      try { localStorage.removeItem(KEY) } catch (e) { /* ignore */ }
    }
  }
})

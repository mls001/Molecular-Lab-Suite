import { defineStore } from 'pinia'

const KEY = 'mls.logPanelVisible'

// 日志面板显隐（全局）：顶栏按钮与日志面板自带的关闭按钮都作用于它
export const useLogPanelStore = defineStore('logPanel', {
  state: () => ({
    visible: localStorage.getItem(KEY) !== '0'
  }),
  actions: {
    set(v) {
      this.visible = !!v
      try { localStorage.setItem(KEY, this.visible ? '1' : '0') } catch (e) { /* ignore */ }
    },
    toggle() {
      this.set(!this.visible)
    }
  }
})

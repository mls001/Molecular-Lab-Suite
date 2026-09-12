// 全局进度：Multiwfn / VMD 处理、FTP 上传下载都往这里写，界面最下方统一显示
import { defineStore } from 'pinia'

export const useProgressStore = defineStore('progress', {
  state: () => ({
    visible: false,
    text: '',
    percent: -1          // <0 表示不确定进度（转圈/流动条）
  }),
  actions: {
    start(text = '') {
      this.visible = true
      this.text = text
      this.percent = -1
    },
    set(percent, text) {
      this.visible = true
      if (typeof percent === 'number' && percent >= 0) {
        this.percent = Math.max(0, Math.min(100, Math.round(percent)))
      }
      if (text !== undefined) this.text = text
    },
    /** 第 done 个 / 共 total 个 */
    step(done, total, text) {
      this.visible = true
      this.percent = total > 0 ? Math.max(0, Math.min(100, Math.round((done / total) * 100))) : -1
      if (text !== undefined) this.text = text
    },
    finish(text = '', delay = 1200) {
      if (text) this.text = text
      this.percent = 100
      window.setTimeout(() => {
        if (this.percent === 100) this.hide()
      }, delay)
    },
    hide() {
      this.visible = false
      this.percent = -1
      this.text = ''
    }
  }
})

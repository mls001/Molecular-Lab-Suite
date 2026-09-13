// 全局进度：Multiwfn / VMD 处理、FTP 上传下载都往这里写，界面最下方统一显示
//
// 同一个界面里可以同时跑多个文件的任务（例如一边渲染分子 A、一边切到 B 渲染）：
//   - 每个任务有自己的 key：'<文件路径>|<类型>'（页面用 setActive(文件路径) 告诉进度条
//     "我现在在看哪个文件"）
//   - 进度条只显示当前文件自己的任务；别的文件还在跑就提示"还有 N 个文件正在后台处理…"
//   - 不传 key 的老调用（其他页面）行为不变：它们就是"当前显示"的任务
import { defineStore } from 'pinia'
import { t as $tr } from '@/i18n'
import { pickJob, otherJobCount } from '@/utils/progressJobs'

export const useProgressStore = defineStore('progress', {
  state: () => ({
    visible: false,
    text: '',
    percent: -1,          // <0 表示不确定进度（转圈/流动条）
    active: '',           // 当前界面对应的文件（空 = 没有"按文件区分"的界面）
    jobs: {},             // key -> { text, percent, seq }
    seq: 0
  }),
  actions: {
    /** 界面切到某个文件：之后进度条只显示这个文件的任务 */
    setActive(key) {
      this.active = key || ''
      this._refresh()
    },
    start(text = '', key = '') {
      this._put(key, { text, percent: -1 })
    },
    set(percent, text, key = '') {
      const j = this.jobs[key] || {}
      if (typeof percent === 'number' && percent >= 0) {
        j.percent = Math.max(0, Math.min(100, Math.round(percent)))
      }
      if (text !== undefined) j.text = text
      this._put(key, j)
    },
    /** 第 done 个 / 共 total 个 */
    step(done, total, text, key = '') {
      const j = this.jobs[key] || {}
      j.percent = total > 0 ? Math.max(0, Math.min(100, Math.round((done / total) * 100))) : -1
      if (text !== undefined) j.text = text
      this._put(key, j)
    },
    finish(text = '', key = '', delay = 1200) {
      const j = this.jobs[key] || {}
      if (text) j.text = text
      j.percent = 100
      this._put(key, j)
      window.setTimeout(() => {
        const cur = this.jobs[key]
        if (cur && cur.percent === 100) this.hide(key)
      }, delay)
    },
    /** 只结束这一个任务（同一个文件的其他任务照旧显示） */
    hide(key = '') {
      if (this.jobs[key]) {
        delete this.jobs[key]
        this._refresh()
      }
    },
    _put(key, job) {
      this.seq += 1
      this.jobs[key] = { text: '', percent: -1, ...job, seq: this.seq }
      this._refresh()
    },
    _refresh() {
      const job = pickJob(this.jobs, this.active)
      if (job) {
        this.visible = true
        this.text = job.text || ''
        this.percent = job.percent
        return
      }
      const n = otherJobCount(this.jobs, this.active)
      if (n > 0) {
        // 当前文件没有任务，但别的文件还在跑：说清楚是"后台"，不要让人以为卡住了
        this.visible = true
        this.percent = -1
        this.text = $tr('还有 {0} 个文件正在后台处理…', { 0: n })
        return
      }
      this.visible = false
      this.percent = -1
      this.text = ''
    }
  }
})

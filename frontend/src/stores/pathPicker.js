import { defineStore } from 'pinia'

// 应用内路径选择器的全局状态。
// 之所以做成 store + 全局弹窗，是为了让 pickDirectory()/pickFile() 保持「等一个路径」的
// Promise 语义，所有既有调用点（6 个页面）无需改动即可换成「能看见全部文件」的选择器。
export const usePathPickerStore = defineStore('pathPicker', {
  state: () => ({
    visible: false,
    mode: 'dir',          // 'dir' = 选择文件夹，'file' = 选择文件
    title: '',
    initialPath: '',
    extensions: [],       // 期望的扩展名（仅用于高亮/过滤，默认仍显示全部文件）
    resolver: null
  }),
  actions: {
    open({ title = '选择路径', initialPath = '', mode = 'dir', extensions = [] } = {}) {
      this.cancel()                              // 避免上一个未完成的 Promise 悬挂
      this.title = title
      this.initialPath = initialPath
      this.mode = mode
      this.extensions = extensions
      this.visible = true
      return new Promise((resolve) => { this.resolver = resolve })
    },
    finish(path) {
      this.visible = false
      const resolve = this.resolver
      this.resolver = null
      if (resolve) resolve(path || null)
    },
    cancel() {
      if (this.resolver) {
        const resolve = this.resolver
        this.resolver = null
        resolve(null)
      }
      this.visible = false
    }
  }
})

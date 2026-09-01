export default {
  data() {
    return {
      savedScrollTop: 0,
      scrollContainerRef: 'tableContainer',
      _restorePending: false
    }
  },
  activated() {
    this._restorePending = true
    this.restoreScroll()
  },
  deactivated() {
    this.saveScroll()
    this._restorePending = false
  },
  methods: {
    saveScroll() {
      const container = this.$refs[this.scrollContainerRef]
      if (container) {
        this.savedScrollTop = container.scrollTop
        console.log('[scrollCache] 保存滚动位置:', this.savedScrollTop)
      } else {
        console.warn('[scrollCache] 保存时容器不存在', this.scrollContainerRef)
      }
    },
    triggerRestore() {
      console.log('[scrollCache] triggerRestore 被调用')
      this.restoreScroll()
    },
    restoreScroll() {
      console.log('[scrollCache] restoreScroll 执行')
      const container = this.$refs[this.scrollContainerRef]
      if (!container) {
        console.warn('[scrollCache] 容器不存在，延迟重试')
        setTimeout(() => this.restoreScroll(), 200)
        return
      }
      console.log('[scrollCache] 容器存在，scrollTop:', container.scrollTop, 'savedScrollTop:', this.savedScrollTop)
      if (this.savedScrollTop === undefined || this.savedScrollTop === 0) {
        console.log('[scrollCache] 没有需要恢复的滚动位置')
        return
      }
      if (Math.abs(container.scrollTop - this.savedScrollTop) < 2) {
        console.log('[scrollCache] 滚动位置已匹配')
        return
      }
      this.$nextTick(() => {
        container.scrollTop = this.savedScrollTop
        console.log('[scrollCache] ✅ 尝试恢复滚动位置:', this.savedScrollTop)
        // 检查恢复效果
        setTimeout(() => {
          console.log('[scrollCache] 恢复后实际 scrollTop:', container.scrollTop)
        }, 50)
      })
    }
  }
}
<template>
  <!-- 全局进度条：软件最下方常驻的大长条，说明文字写在长条内部 -->
  <div class="mls-progress">
    <div class="mls-progress-track">
      <span class="mls-progress-fill" :style="{ width: store.percent >= 0 ? store.percent + '%' : '0%' }"></span>
      <span v-if="busy && store.percent < 0" class="mls-progress-flow"></span>
      <span class="mls-progress-label">{{ label }}</span>
    </div>
  </div>
</template>

<script>
import { useProgressStore } from '@/stores/progress'

export default {
  name: 'ProgressBar',
  computed: {
    store() { return useProgressStore() },
    busy() { return this.store.visible },
    label() {
      const t = this.store.text
      if (!this.busy) return this.$t('就绪')
      if (this.store.percent >= 0) return `${t}  ${this.store.percent}%`.trim()
      return t || this.$t('处理中…')
    }
  }
}
</script>

<style scoped>
.mls-progress {
  flex-shrink: 0;
  padding: 3px 8px 4px 8px;
  /* 与面板/窗格顶部的深色标题栏同一套配色：上一条深色栏、下一条深色栏，视觉对称 */
  background: linear-gradient(90deg, var(--c-titlebar-a), var(--c-titlebar-b));
  border-top: 1px solid var(--c-border-strong);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.mls-progress-track {
  position: relative;
  width: 100%;
  height: 18px;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.22);
  overflow: hidden;
}
.mls-progress-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: var(--c-accent);
  transition: width 0.2s linear;
}
.mls-progress-flow {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 28%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  animation: mls-flow 1.1s linear infinite;
}
@keyframes mls-flow {
  from { transform: translateX(-110%); }
  to { transform: translateX(380%); }
}
.mls-progress-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11.5px;
  line-height: 1;
  color: var(--c-titlebar-text);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 6px;
  pointer-events: none;
}
</style>

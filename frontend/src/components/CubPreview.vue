<template>
  <!-- 轨道 cube 等值面预览（3Dmol 体数据渲染，离线可用） -->
  <div class="cub-view" :style="{ background: '#ffffff' }">
    <div ref="gl" class="cub-canvas"></div>
    <div v-if="!ready" class="cub-overlay">{{ $t('正在加载预览…') }}</div>
    <div v-if="label" class="cub-label">{{ label }}</div>
  </div>
</template>

<script>
import { load3Dmol } from '@/utils/threeDmol'

export default {
  name: 'CubPreview',
  props: {
    cubText: { type: String, default: '' },
    label: { type: String, default: '' },
    isovalue: { type: Number, default: 0.02 },
    height: { type: Number, default: 150 }
  },
  data() {
    return { ready: false, viewer: null }
  },
  watch: {
    cubText() { this.render() }
  },
  async mounted() {
    if (typeof ResizeObserver !== 'undefined') {
      this._ro = new ResizeObserver(() => { if (this.viewer) this.viewer.resize() })
      this._ro.observe(this.$el)
    }
    await this.render()
  },
  beforeUnmount() {
    if (this._ro) { this._ro.disconnect(); this._ro = null }
    if (this.viewer) { try { this.viewer.clear() } catch (e) { /* ignore */ } }
    this.viewer = null
  },
  methods: {
    async render() {
      if (!this.cubText) return
      try {
        const $3Dmol = await load3Dmol()
        const el = this.$refs.gl
        if (!$3Dmol || !el) return
        if (!this.viewer) {
          this.viewer = $3Dmol.createViewer(el, { backgroundColor: 'white', antialias: true })
        }
        this.viewer.removeAllModels()
        this.viewer.removeAllSurfaces()
        this.viewer.addModel(this.cubText, 'cube')
        this.viewer.setStyle({}, { stick: { radius: 0.09, colorscheme: 'Jmol' } })
        const iso = Math.abs(this.isovalue) || 0.02
        this.viewer.addVolumetricData(this.cubText, 'cube', { isoval: iso, color: 'blue', opacity: 0.85 })
        this.viewer.addVolumetricData(this.cubText, 'cube', { isoval: -iso, color: 'red', opacity: 0.85 })
        this.viewer.zoomTo()
        this.viewer.render()
        this.ready = true
      } catch (e) {
        console.warn('[CubPreview] 预览失败:', e && e.message)
        this.ready = false
      }
    }
  }
}
</script>

<style scoped>
.cub-view {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 90px;
  overflow: hidden;
  border: 1px solid var(--c-border-soft);
}
.cub-canvas { position: absolute; inset: 0; }
.cub-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--c-text-3);
}
.cub-label {
  position: absolute;
  left: 4px;
  top: 2px;
  font-size: 11px;
  color: var(--c-text-2);
  background: rgba(255, 255, 255, 0.75);
  padding: 0 3px;
  pointer-events: none;
}
</style>

<template>
  <!-- 3D 模型查看器（3Dmol）；2D 结构式由 MolCanvas2D 负责，这里只画 3D -->
  <div class="mol-viewer" :style="{ background: bgColor }">
    <div ref="gl" class="mol-canvas"
         @pointerdown="onCanvasDown"
         @click="onCanvasClick"></div>
    <div v-if="!ready" class="mol-overlay">{{ $t('正在加载 3D 视图…') }}</div>
  </div>
</template>

<script>
// 3D 用打包进来的 3Dmol（离线可用，不回退外网 CDN）
import { load3Dmol } from '@/utils/threeDmol'

import { CPK3D } from '@/utils/molDraw'

    // 显示方式（对标 MolView 的 Representation）
const REPR = {
  ballstick: { stick: { radius: 0.14, colorscheme: 'Jmol' }, sphere: { scale: 0.26, colorscheme: 'Jmol' } },
  stick: { stick: { radius: 0.15, colorscheme: 'Jmol' }, sphere: { scale: 0.12, colorscheme: 'Jmol' } },
  spacefill: { sphere: { scale: 1.0, colorscheme: 'Jmol' } },
  wireframe: { line: { linewidth: 1.5, colorscheme: 'Jmol' }, sphere: { scale: 0.14, colorscheme: 'Jmol' } },
  line: { line: { linewidth: 2, colorscheme: 'Jmol' } }
}
const BGS = { white: '#ffffff', gray: '#808080', black: '#000000' }
// 选中高亮：原子琥珀、键橙色（与 2D 画布一致）
const HILITE = { atom: '#ffb300', bond: '#ff7a00' }

export default {
  name: 'MolViewer',
  props: {
    molblock: { type: String, default: '' },
    selected: { type: Number, default: null },   // 选中的原子序号
    selectedBondAtoms: { type: Array, default: null },   // 选中的键（两个原子序号）→ 高亮
    showIndices: { type: Boolean, default: false },
    representation: { type: String, default: 'ballstick' },
    background: { type: String, default: '#c9ced5' },   // 'white'|'gray'|'black' 或 #rrggbb（跟随主题）
    charges: { type: Array, default: () => [] }, // [{index, charge}] → 着色 + 标注
    elementColors: { type: Boolean, default: true },    // 3D 用 CPK 元素着色（与 2D 一致）
    overlay: { type: Object, default: () => ({ lines: [], labels: [] }) }  // 测量用的线与标签
  },
  emits: ['select', 'background-click'],
  data() {
    return { ready: false, viewer: null }
  },
  computed: {
    bgColor() {
      const b = this.background
      if (BGS[b]) return BGS[b]
      return (typeof b === 'string' && b.charAt(0) === '#') ? b : '#c9ced5'
    },
    isDarkBg() {
      const hex = this.bgColor.replace('#', '')
      if (hex.length < 6) return false
      const r = parseInt(hex.slice(0, 2), 16)
      const g = parseInt(hex.slice(2, 4), 16)
      const b = parseInt(hex.slice(4, 6), 16)
      return (0.299 * r + 0.587 * g + 0.114 * b) < 140
    },
    labelColor() { return this.isDarkBg ? '#f0f0f0' : '#1b1b1b' },
    labelBg() { return this.isDarkBg ? '#000000' : '#ffffff' }
  },
  watch: {
    molblock() { this.render3d() },
    mode(val) { if (val === '3d') this.$nextTick(() => this.render3d()) },
    selected() { if (this.viewer) this.applyStyles() },
    selectedBondAtoms() { if (this.viewer) this.applyStyles() },
    showIndices() { if (this.viewer) this.applyStyles() },
    representation() { if (this.viewer) this.applyStyles() },
    charges() { if (this.viewer) this.applyStyles() },
    overlay: {
      handler() { if (this.viewer) this.applyStyles() },
      deep: true
    },
    background() {
      if (!this.viewer) return
      try {
        this.viewer.setBackgroundColor(this.bgColor)
        this.applyStyles()
      } catch (e) { /* ignore */ }
    }
  },
  async mounted() {
    await this.$nextTick()
    await this.render3d()
    if (typeof ResizeObserver !== 'undefined') {
      this._ro = new ResizeObserver(() => { if (this.viewer) this.viewer.resize() })
      this._ro.observe(this.$el)
    }
  },
  beforeUnmount() {
    if (this._ro) { this._ro.disconnect(); this._ro = null }
    if (this.viewer) { try { this.viewer.clear() } catch (e) { /* ignore */ } }
    this.viewer = null
  },
  methods: {
    async render3d() {
      if (!this.molblock) return
      try {
        const $3Dmol = await load3Dmol()
        if (!$3Dmol) return
        const el = this.$refs.gl
        if (!el) return
        if (!this.viewer) {
          this.viewer = $3Dmol.createViewer(el, { backgroundColor: this.bgColor, antialias: true })
        }
        this.viewer.removeAllModels()
        this.viewer.removeAllShapes()
        this.viewer.addModel(this.molblock, 'sdf')
        this.applyStyles()
        // 点击选原子（3Dmol 的 index 与 RDKit 原子序号一致）
        this.viewer.setClickable({}, true, (atom) => {
          if (atom && typeof atom.index === 'number') {
            this._hitAtom = true
            this.$emit('select', atom.index)
          }
        })
        this.viewer.zoomTo()
        this.viewer.render()
        this.ready = true
      } catch (e) {
        console.warn('[MolViewer] 3D 渲染失败:', e && e.message)
        this.ready = false
      }
    },
    styleFor() {
      return REPR[this.representation] || REPR.ballstick
    },
    applyStyles() {
      if (!this.viewer) return
      try {
        // setStyle（不是 addStyle）：整体替换该原子的样式，避免残留 colorscheme 覆盖 color
        this.viewer.setStyle({}, this.styleFor())
        this.applyElementColors()
        this.applyChargeColors()
        this.applyLabels()
        this.applyOverlay()
        this.viewer.render()
      } catch (e) { /* ignore */ }
    },
    // 把显示方式里的每个子样式加上颜色（保留 radius/scale 等几何参数）
    // 注意：必须去掉 colorscheme，否则 3Dmol 会用 colorscheme 覆盖 color，颜色不生效
    colored(style, color) {
      const out = {}
      for (const k of Object.keys(style)) {
        const s = Object.assign({}, style[k])
        delete s.colorscheme
        s.color = color
        out[k] = s
      }
      return out
    },
    applyElementColors() {
      if (!this.viewer || !this.elementColors) return
      try {
        const model = this.viewer.getModel()
        const atoms = (model && typeof model.selectedAtoms === 'function') ? model.selectedAtoms({}) : []
        const rep = this.styleFor()
        for (const a of atoms) {
          const sym = a.elem || a.element || ''
          const col = CPK3D[sym]
          if (!col) continue
          this.viewer.setStyle({ index: a.index }, this.colored(rep, col))
        }
      } catch (e) {
        console.warn('[MolViewer] 元素着色失败:', e && e.message)
      }
    },
    // 原子电荷：红=负、蓝=正（对标 MolView 的 Charge 着色）
    applyChargeColors() {
      if (!this.viewer || !this.charges || !this.charges.length) return
      const rep = this.styleFor()
      for (const c of this.charges) {
        const color = c.charge > 0.02 ? '#3a6fd8' : (c.charge < -0.02 ? '#d24545' : '#c9c9c9')
        try {
          this.viewer.setStyle({ index: c.index }, this.colored(rep, color))
        } catch (e) { /* ignore */ }
      }
    },
    // 原子序号 + 电荷数值标签（一起画，避免互相清除）
    applyLabels() {
      if (!this.viewer) return
      try {
        this.viewer.removeAllLabels()
      } catch (e) { /* ignore */ }
      const wantIndex = !!this.showIndices
      const wantCharge = !!(this.charges && this.charges.length)
      if (!wantIndex && !wantCharge) return
      try {
        const model = this.viewer.getModel()
        const atoms = (model && typeof model.selectedAtoms === 'function')
          ? model.selectedAtoms({}) : []
        const qmap = {}
        for (const c of (this.charges || [])) qmap[c.index] = c.charge
        for (const a of atoms) {
          const idx = (a.index !== undefined && a.index !== null) ? a.index : a.serial
          const parts = []
          if (wantIndex) parts.push(String(idx))
          if (wantCharge && qmap[idx] !== undefined) parts.push(Number(qmap[idx]).toFixed(2))
          if (!parts.length) continue
          let color = this.labelColor
          if (wantCharge && qmap[idx] !== undefined) {
            color = qmap[idx] > 0.02 ? '#2f5fd0' : (qmap[idx] < -0.02 ? '#c03535' : color)
          }
          this.viewer.addLabel(parts.join(' '), {
            position: { x: a.x, y: a.y, z: a.z },
            fontSize: 11,
            fontColor: color,
            backgroundColor: this.labelBg,
            backgroundOpacity: 0.6,
            showBackground: true,
            inFront: true
          })
        }
      } catch (e) {
        console.warn('[MolViewer] 标注失败:', e && e.message)
      }
    },
    // 测量：虚线 + 数值标签
    applyOverlay() {
      if (!this.viewer) return
      const ov = this.overlay || {}
      try {
        this.viewer.removeAllShapes()            // 只清叠加图形，不动模型
      } catch (e) { /* ignore */ }
      try {
        // 选中高亮：只画线框「外框」（wireframe），不动原子本身的元素颜色
        for (const hl of (ov.highlights || [])) {
          if (hl.kind === 'sphere') {
            this.viewer.addSphere({
              center: { x: hl.x, y: hl.y, z: hl.z },
              radius: hl.radius || 0.6, color: hl.color, wireframe: true, opacity: 1.0
            })
          } else {
            this.viewer.addCylinder({
              start: { x: hl.x, y: hl.y, z: hl.z },
              end: { x: hl.x2, y: hl.y2, z: hl.z2 },
              radius: hl.radius || 0.22, color: hl.color, wireframe: true, opacity: 1.0
            })
          }
        }
        for (const ln of (ov.lines || [])) {
          this.viewer.addLine({
            dashed: true,
            start: { x: ln.x1, y: ln.y1, z: ln.z1 },
            end: { x: ln.x2, y: ln.y2, z: ln.z2 },
            color: '#ffb300',
            linewidth: 2
          })
        }
        for (const lb of (ov.labels || [])) {
          this.viewer.addLabel(lb.text, {
            position: { x: lb.x, y: lb.y, z: lb.z },
            fontSize: 12,
            fontColor: '#111111',
            backgroundColor: '#ffe680',
            backgroundOpacity: 0.9,
            showBackground: true,
            inFront: true
          })
        }
        for (const ar of (ov.arrows || [])) {
          this.viewer.addArrow({
            start: { x: ar.x1, y: ar.y1, z: ar.z1 },
            end: { x: ar.x2, y: ar.y2, z: ar.z2 },
            radius: 0.06,
            radiusRatio: 2.2,
            mid: 0.75,
            color: '#d24545'
          })
        }
      } catch (e) {
        console.warn('[MolViewer] 测量叠加层绘制失败:', e && e.message)
      }
    },
    resetView() {
      if (!this.viewer) return
      this.viewer.zoomTo()
      this.viewer.render()
    },
    // 空白处点击（没点到原子）= 取消所有选中；旋转/缩放拖动不算点击
    onCanvasDown(e) {
      this._hitAtom = false
      this._downAt = { x: e.clientX, y: e.clientY }
    },
    onCanvasClick(e) {
      const d = this._downAt
      this._downAt = null
      if (d && Math.hypot(e.clientX - d.x, e.clientY - d.y) > 4) return
      setTimeout(() => {
        const hit = this._hitAtom
        this._hitAtom = false
        if (!hit) this.$emit('background-click')
      }, 60)
    },
    spin(on) {
      if (!this.viewer) return
      if (on) this.viewer.spin('y')
      else this.viewer.spin(false)
    },
    // 导出 3D 模型图片（PNG data URI）
    pngURI() {
      if (!this.viewer) return ''
      try {
        this.viewer.render()
        return this.viewer.pngURI()
      } catch (e) {
        console.warn('[MolViewer] 导出 PNG 失败:', e && e.message)
        return ''
      }
    }
  }
}
</script>

<style scoped>
.mol-viewer {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.mol-canvas {
  position: absolute;
  inset: 0;
}
.mol-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-3);
  font-size: 12px;
  pointer-events: none;
}
</style>

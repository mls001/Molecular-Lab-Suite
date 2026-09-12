<template>
  <!-- 2D 结构式画布（渲染对标 MolView/ChemDraw：骨架式、元素着色、Kekulé 双键、无顶点圆点） -->
  <div class="mol2d" ref="wrap">
    <svg
      ref="svg"
      :width="size.w"
      :height="size.h"
      :style="{ cursor: cursorStyle, background: bg }"
      @pointerdown="onBackgroundDown"
      @pointermove="onHover"
      @pointerleave="onLeave"
      @wheel.prevent="onWheel"
      @dblclick="onDblClick"
    >
      <rect x="0" y="0" :width="size.w" :height="size.h" :fill="bg" />

      <!-- 化学键 -->
      <g stroke-linecap="round">
        <template v-for="(b, i) in renderBonds" :key="'b' + i">
          <line
            v-for="(seg, j) in b.segs"
            :key="'s' + j"
            :x1="seg.x1" :y1="seg.y1" :x2="seg.x2" :y2="seg.y2"
            :stroke="b.color"
            :stroke-width="b.width"
            stroke-linecap="round"
          />
          <!-- 命中区域（不可见，便于点键） -->
          <line
            :x1="b.x1" :y1="b.y1" :x2="b.x2" :y2="b.y2"
            stroke="rgba(0,0,0,0)" stroke-width="12"
            style="pointer-events:stroke;"
            @pointerdown.stop="onBondDown($event, b.bondIndex)"
            @dblclick.stop
          />
        </template>
      </g>

      <!-- 拉键预览 -->
      <line
        v-if="tempBond"
        :x1="tempBond.x1" :y1="tempBond.y1" :x2="tempBond.x2" :y2="tempBond.y2"
        stroke="#8a97a5" stroke-width="2" stroke-dasharray="5 4" stroke-linecap="round"
      />
      <circle v-if="ghost" :cx="ghost.X" :cy="ghost.Y" r="3.5" fill="#8a97a5" />

      <!-- 原子：只有带标签的原子画文字（骨架式），透明圆用于命中/高亮 -->
      <g>
        <template v-for="a in drawAtoms" :key="'a' + a.index">
          <circle
            :cx="a.X" :cy="a.Y" :r="a.hit"
            fill="none" :stroke="a.ringColor" :stroke-width="a.ringWidth"
            style="pointer-events:all;"
            @pointerdown.stop="onAtomDown($event, a.index)"
            @dblclick.stop="onAtomDblClick($event, a.index)"
          />
          <!-- 不合法原子：红色虚线警示圈 -->
          <circle
            v-if="a.warn"
            :cx="a.X" :cy="a.Y" :r="a.hit + 3"
            fill="none" stroke="#e53935" stroke-width="1.8" stroke-dasharray="4 3"
            style="pointer-events:none;"
          />
          <text
            v-if="a.label"
            :x="a.X" :y="a.Y"
            text-anchor="middle" dominant-baseline="central"
            :font-size="a.fs" :font-weight="a.weight" :fill="a.color"
            font-family="Arial, Helvetica, 'Microsoft YaHei', sans-serif"
            :style="{ pointerEvents: 'all', cursor: 'inherit', userSelect: 'none' }"
            @pointerdown.stop="onAtomDown($event, a.index)"
            @dblclick.stop
          >{{ a.label }}<tspan v-if="a.sub" :font-size="a.fs * 0.68" dy="2.5">{{ a.sub }}</tspan><tspan v-if="a.charge" :font-size="a.fs * 0.68" dy="-2.5">{{ a.charge }}</tspan></text>
          <text
            v-if="a.showIdx"
            :x="a.idxX" :y="a.idxY"
            :font-size="Math.max(9, a.fs * 0.55)" :fill="subText"
            font-family="Arial, sans-serif" style="pointer-events:none;user-select:none;"
          >{{ a.index }}</text>
        </template>
      </g>

      <text
        v-if="!atoms.length"
        :x="size.w / 2" :y="size.h / 2"
        text-anchor="middle" font-size="12" :fill="subText"
        font-family="Arial, sans-serif" style="pointer-events:none;"
      >{{ $t('单击画布放置原子 · 从原子拖动绘制化学键') }}</text>

      <!-- 框选：矩形 / 曲线（套索） -->
      <rect
        v-if="marquee"
        :x="Math.min(marquee.x1, marquee.x2)" :y="Math.min(marquee.y1, marquee.y2)"
        :width="Math.abs(marquee.x2 - marquee.x1)" :height="Math.abs(marquee.y2 - marquee.y1)"
        fill="rgba(55,81,109,0.12)" stroke="#37516d" stroke-width="1" stroke-dasharray="4 3"
        style="pointer-events:none;"
      />
      <polygon
        v-if="lassoPath"
        :points="lassoPath"
        fill="rgba(55,81,109,0.12)" stroke="#37516d" stroke-width="1" stroke-dasharray="4 3"
        style="pointer-events:none;"
      />
    </svg>

    <div class="mol2d-hint">{{ hint }}</div>
  </div>
</template>

<script>
// 骨架式 2D 绘制画布（对标 MolView sketcher）。
// 渲染：碳顶点不画点、杂原子按元素着色、芳香键按后端给的 Kekulé 序画成交替单双键、
//       环内双键的第二条线画在环内侧（flip 由后端按环中心算好）。
// 交互：只产生「意图」事件，真正的结构修改交给父组件调后端（RDKit 把关价键/芳香性）。
import { CPK, atomText, bondSegments, fontSizeFor, bondGapFor, bondColorFor, isDarkColor, fitToBox, moleculeSvg } from '@/utils/molDraw'

const DEFAULTS = { select: 'default', bond: 'crosshair', ring: 'copy', erase: 'not-allowed', charge: 'pointer' }

export default {
  name: 'MolCanvas2D',
  props: {
    atoms: { type: Array, default: () => [] },
    bonds: { type: Array, default: () => [] },
    selected: { type: Number, default: null },
    selectedBond: { type: Number, default: null },
    showIndices: { type: Boolean, default: false },
    showExplicitCH: { type: Boolean, default: false },   // 非骨架式：碳也标出 C / CH3
    element: { type: String, default: 'C' },
    bondOrder: { type: Number, default: 1 },
    chargeDelta: { type: Number, default: 1 },
    tool: { type: String, default: 'bond' },             // select | bond | ring | charge | erase
    selectMode: { type: String, default: 'rect' },        // rect | lasso（选择工具下的框选方式）
    selectedAtoms: { type: Array, default: () => [] },    // 多选（框选/曲线选）
    autoExtend: { type: Boolean, default: true },         // 键工具下单击原子 = 自动接键
    armRing: { type: Object, default: null },
    background: { type: String, default: '#ffffff' },     // 画布底色（跟随明暗主题）
    warnAtom: { type: Number, default: null },            // 结构不合法时标红的原子
    hint: { type: String, default: '' },
    readonly: { type: Boolean, default: false }
  },
  emits: ['select-atom', 'select-atoms', 'select-bond', 'add-atom', 'add-atom-chain', 'add-bond', 'add-bond-atom',
          'cycle-bond', 'place-ring', 'move-atom', 'delete-atom', 'delete-bond', 'charge-atom',
          'extend-atom', 'hover-atom'],
  data() {
    return {
      view: { cx: 0, cy: 0, scale: 42 },
      size: { w: 600, h: 400 },
      press: null,
      tempTo: null,
      panning: null,
      hover: null,
      marquee: null,          // 矩形框选 {x1,y1,x2,y2}（像素）
      lassoPts: null,         // 曲线框选点列（像素）
      fitted: false
    }
  },
  computed: {
    bg() { return this.background || '#ffffff' },
    dark() { return isDarkColor(this.bg) },
    bondColor() { return bondColorFor(this.dark) },
    subText() { return this.dark ? '#9aa3ad' : '#7d868f' },
    cursorStyle() {
      if (this.panning) return 'grabbing'
      if (this.hover !== null && this.tool === 'select') return 'move'
      return DEFAULTS[this.tool] || 'crosshair'
    },
    atomMap() {
      const m = {}
      for (const a of this.atoms) m[a.index] = a
      return m
    },
    bondPx() { return this.view.scale * 1.4 },                    // 标准键长（像素）
    fontSize() { return fontSizeFor(this.bondPx) },
    bondGap() { return bondGapFor(this.bondPx) },
    drawAtoms() {
      const out = []
      const fs = this.fontSize
      for (const a of this.atoms) {
        const p = this.dragPos(a)
        const { X, Y } = this.toPx(p)
        const hit = this.labelOf(a) ? fs * 0.95 : 7
        out.push(Object.assign({
          index: a.index, X, Y, hit, fs,
          showIdx: this.showIndices,
          warn: this.warnAtom === a.index,
          idxX: X + hit * 0.75, idxY: Y - hit * 0.6,
          selected: this.selected === a.index || (this.selectedAtoms || []).includes(a.index),
          hover: this.hover === a.index,
          ringColor: (this.selected === a.index || (this.selectedAtoms || []).includes(a.index)) ? '#f0a500'
            : (this.hover === a.index ? (this.dark ? '#6b7684' : '#c9d3de') : 'none'),
          ringWidth: (this.selected === a.index || (this.selectedAtoms || []).includes(a.index)) ? 2 : 1.5
        }, this.labelParts(a)))
      }
      return out
    },
    renderBonds() {
      const out = []
      this.bonds.forEach((b, i) => {
        const A = this.atomMap[b.a]
        const B = this.atomMap[b.b]
        if (!A || !B) return
        const pa = this.toPx(this.dragPos(A))
        const pb = this.toPx(this.dragPos(B))
        out.push({
          bondIndex: i,
          x1: pa.X, y1: pa.Y, x2: pb.X, y2: pb.Y,
          segs: this.bondSegments(pa, pb, b),
          color: this.selectedBond === i ? '#f0a500' : this.bondColor,
          width: this.selectedBond === i ? 3 : 2
        })
      })
      return out
    },
    tempBond() {      if (!this.press || !this.press.moved || !this.tempTo) return null
      if (this.press.kind === 'move') return null
      if (this.press.kind === 'atom') {
        const a = this.atomMap[this.press.index]
        if (!a) return null
        const p = this.toPx(a)
        return { x1: p.X, y1: p.Y, x2: this.tempTo.X, y2: this.tempTo.Y }
      }
      const p = this.toPx({ x: this.press.molX, y: this.press.molY })
      return { x1: p.X, y1: p.Y, x2: this.tempTo.X, y2: this.tempTo.Y }
    },
    ghost() {
      if (!this.press || !this.press.moved || this.press.kind !== 'blank' || !this.tempTo) return null
      const m = this.snapFrom(this.press.molX, this.press.molY, this.toMolRaw(this.tempTo))
      return this.toPx(m)
    },
    lassoPath() {
      if (!this.lassoPts || this.lassoPts.length < 2) return ''
      return this.lassoPts.map(p => `${p.X.toFixed(1)},${p.Y.toFixed(1)}`).join(' ')
    }
  },
  watch: {
    atoms: {
      handler() { if (!this.fitted && this.atoms.length) this.$nextTick(() => this.fit()) },
      deep: false
    }
  },
  mounted() {
    this.measure()
    if (typeof ResizeObserver !== 'undefined') {
      this._ro = new ResizeObserver(() => this.measure())
      this._ro.observe(this.$refs.wrap)
    }
    if (this.atoms.length) this.fit()
  },
  beforeUnmount() {
    if (this._ro) { this._ro.disconnect(); this._ro = null }
    this.detach()
  },
  methods: {
    // ===== 坐标换算 =====
    measure() {
      const el = this.$refs.wrap
      if (!el) return
      const r = el.getBoundingClientRect()
      this.size = { w: Math.max(120, Math.round(r.width)), h: Math.max(120, Math.round(r.height)) }
    },
    toPx(p) {
      return {
        X: (p.x - this.view.cx) * this.view.scale + this.size.w / 2,
        Y: -(p.y - this.view.cy) * this.view.scale + this.size.h / 2
      }
    },
    toMolRaw(pt) {
      return {
        x: (pt.X - this.size.w / 2) / this.view.scale + this.view.cx,
        y: -(pt.Y - this.size.h / 2) / this.view.scale + this.view.cy
      }
    },
    toMol(e) {
      const r = this.$refs.svg.getBoundingClientRect()
      return this.toMolRaw({ X: e.clientX - r.left, Y: e.clientY - r.top })
    },
    eventPos(e) {
      const r = this.$refs.svg.getBoundingClientRect()
      return { X: e.clientX - r.left, Y: e.clientY - r.top }
    },
    dragPos(a) {
      if (this.press && this.press.kind === 'move' && this.press.moved && this.press.index === a.index) {
        return { x: this.press.x, y: this.press.y }
      }
      return a
    },
    // ===== 视图 =====
    fit() {
      this.fitted = true
      this.measure()
      if (!this.atoms.length) {
        this.view = { cx: 0, cy: 0, scale: 42 }
        return
      }
      const xs = this.atoms.map(a => a.x)
      const ys = this.atoms.map(a => a.y)
      const minX = Math.min(...xs), maxX = Math.max(...xs)
      const minY = Math.min(...ys), maxY = Math.max(...ys)
      const pad = 70
      const w = Math.max(maxX - minX, 1.5)
      const h = Math.max(maxY - minY, 1.5)
      const scale = Math.min((this.size.w - pad) / w, (this.size.h - pad) / h)
      this.view = {
        cx: (minX + maxX) / 2, cy: (minY + maxY) / 2,
        scale: Math.max(14, Math.min(scale, 46))
      }
    },
    refit() { this.fitted = false; this.fit() },
    // 导出结构式图片：用共用渲染函数重新出一张「白底深色键」的图（便于论文/打印），
    // 与画布共用同一套画法，不做 DOM 序列化
    toSvg() {
      if (!this.atoms.length) return ''
      const w = Math.max(240, this.size.w)
      const h = Math.max(180, this.size.h)
      const fit = fitToBox(this.atoms, w, h, 70)
      const text = moleculeSvg(this.atoms, this.bonds, {
        width: w, height: h, toPx: fit.toPx,
        fontSize: fit.fontSize, bondGap: fit.bondGap,
        showExplicitCH: this.showExplicitCH, showIndices: this.showIndices,
        background: '#ffffff', dark: false
      })
      return '<?xml version="1.0" encoding="UTF-8"?>\n' + text
    },
    zoomBy(f, about) {
      const target = about || { X: this.size.w / 2, Y: this.size.h / 2 }
      const before = this.toMolRaw(target)
      this.view.scale = Math.min(160, Math.max(8, this.view.scale * f))
      const after = this.toMolRaw(target)
      this.view.cx += before.x - after.x
      this.view.cy += before.y - after.y
    },
    onWheel(e) { this.zoomBy(e.deltaY < 0 ? 1.12 : 0.89, this.eventPos(e)) },

    // ===== 原子标签（骨架式：C 不标；非骨架式：全部标出）=====
    labelParts(a) {
      const t = atomText(a, { showExplicitCH: this.showExplicitCH, dark: this.dark })
      return {
        label: t.label, sub: t.sub, charge: t.charge, color: t.color,
        fs: this.fontSize, weight: 500
      }
    },
    labelOf(a) { return atomText(a, { showExplicitCH: this.showExplicitCH, dark: this.dark }).label },
    // ===== 化学键 =====
    bondSegments(pa, pb, b) {
      return bondSegments(b, pa, pb, {
        gapA: this.labelOf(this.atomMap[b.a]) ? this.fontSize * 0.62 + 2 : 0,
        gapB: this.labelOf(this.atomMap[b.b]) ? this.fontSize * 0.62 + 2 : 0,
        bondGap: this.bondGap,
        bondPx: this.bondPx
      })
    },
    // ===== 交互 =====
    attach() {
      window.addEventListener('pointermove', this.onPointerMove)
      window.addEventListener('pointerup', this.onPointerUp)
    },
    detach() {
      window.removeEventListener('pointermove', this.onPointerMove)
      window.removeEventListener('pointerup', this.onPointerUp)
    },
    nearestAtom(pt, tol) {
      let best = null, bestD = tol
      for (const a of this.atoms) {
        const q = this.toPx(this.dragPos(a))
        const d = Math.hypot(q.X - pt.X, q.Y - pt.Y)
        if (d < bestD) { bestD = d; best = a.index }
      }
      return best
    },
    onHover(e) {
      if (this.press || this.panning) return
      const idx = this.nearestAtom(this.eventPos(e), 12)
      if (idx !== this.hover) {
        this.hover = idx
        this.$emit('hover-atom', idx)          // 供「悬停原子 + 按字母改元素」使用
      }
    },
    onLeave() {
      if (this.hover !== null) {
        this.hover = null
        this.$emit('hover-atom', null)
      }
    },
    // 射线法：判断点是否在曲线（套索）多边形内
    pointInPolygon(p, poly) {
      let inside = false
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const xi = poly[i].X, yi = poly[i].Y
        const xj = poly[j].X, yj = poly[j].Y
        if (((yi > p.Y) !== (yj > p.Y)) && (p.X < (xj - xi) * (p.Y - yi) / ((yj - yi) || 1e-9) + xi)) {
          inside = !inside
        }
      }
      return inside
    },
    // 从 (x0,y0) 朝指针方向按 1.4 Å + 30° 网格吸附
    snapFrom(x0, y0, m) {
      const dx = m.x - x0, dy = m.y - y0
      if (Math.hypot(dx, dy) < 1e-6) return { x: x0 + 1.4, y: y0 }
      let ang = Math.atan2(dy, dx)
      const step = Math.PI / 6
      const snapped = Math.round(ang / step) * step
      if (Math.abs(((ang - snapped + Math.PI) % (2 * Math.PI)) - Math.PI) < 0.18) ang = snapped
      return { x: x0 + Math.cos(ang) * 1.4, y: y0 + Math.sin(ang) * 1.4 }
    },
    onAtomDown(e, index) {
      if (this.readonly || e.button !== 0) return
      const pt = this.eventPos(e)
      const a = this.atomMap[index]
      if (!a) return
      if (this.tool === 'erase') { this.$emit('delete-atom', index); return }
      if (this.tool === 'charge') {
        this.$emit('charge-atom', { index, delta: this.chargeDelta })
        return
      }
      if (this.tool === 'ring') {
        const m = this.toMolRaw(pt)
        this.$emit('place-ring', { x: m.x, y: m.y, attach: index })
        return
      }
      const kind = this.tool === 'select' ? 'move' : 'atom'
      this.press = { kind, index, X: pt.X, Y: pt.Y, moved: false, x: a.x, y: a.y }
      this.attach()
    },
    onAtomDblClick(e, index) {
      e.stopPropagation()
      this.$emit('select-atom', index)
    },
    onBondDown(e, bondIndex) {
      if (this.readonly || e.button !== 0) return
      const b = this.bonds[bondIndex]
      if (!b) return
      if (this.tool === 'erase') { this.$emit('delete-bond', { a: b.a, b: b.b }); return }
      if (this.tool === 'ring') return
      this.$emit('select-bond', bondIndex)
      if (this.tool === 'select') return
      // 键工具：单击已有键 = 键级循环（单 → 双 → 三 → 单）
      const cur = b.display_order || Math.round(b.order) || 1
      this.$emit('cycle-bond', { a: b.a, b: b.b, order: cur >= 3 ? 1 : cur + 1 })
    },
    onBackgroundDown(e) {
      if (this.readonly) return
      const pt = this.eventPos(e)
      // 「选择」工具在空白处按下：拖出矩形/曲线框选（不移动则只取消选中）
      if (e.button === 0 && this.tool === 'select') {
        this.$emit('select-atom', null)
        this.$emit('select-bond', null)
        if (this.selectMode === 'lasso') this.lassoPts = [{ X: pt.X, Y: pt.Y }]
        else this.marquee = { x1: pt.X, y1: pt.Y, x2: pt.X, y2: pt.Y }
        this.attach()
        return
      }
      // 中键/Alt：平移画布
      if (e.button === 1 || e.altKey) {
        this.panning = { X: pt.X, Y: pt.Y, cx: this.view.cx, cy: this.view.cy, moved: false }
        this.attach()
        return
      }
      if (e.button !== 0) return
      const m = this.toMolRaw(pt)
      if (this.tool === 'ring') {
        this.$emit('place-ring', { x: m.x, y: m.y, attach: null })
        return
      }
      this.$emit('select-atom', null)
      this.$emit('select-bond', null)
      if (this.tool === 'erase' || this.tool === 'charge') return
      this.press = { kind: 'blank', X: pt.X, Y: pt.Y, molX: m.x, molY: m.y, moved: false }
      this.attach()
    },
    onDblClick(e) {
      if (e.target && e.target.tagName === 'svg') this.refit()
    },
    onPointerMove(e) {
      const pt = this.eventPos(e)
      if (this.panning) {
        if (Math.hypot(pt.X - this.panning.X, pt.Y - this.panning.Y) > 3) this.panning.moved = true
        this.view.cx = this.panning.cx - (pt.X - this.panning.X) / this.view.scale
        this.view.cy = this.panning.cy + (pt.Y - this.panning.Y) / this.view.scale
        return
      }
      if (this.marquee) {
        this.marquee.x2 = pt.X
        this.marquee.y2 = pt.Y
        return
      }
      if (this.lassoPts) {
        const last = this.lassoPts[this.lassoPts.length - 1]
        if (!last || Math.hypot(pt.X - last.X, pt.Y - last.Y) > 3) this.lassoPts.push({ X: pt.X, Y: pt.Y })
        return
      }
      if (!this.press) return
      if (!this.press.moved && Math.hypot(pt.X - this.press.X, pt.Y - this.press.Y) > 4) {
        this.press.moved = true
      }
      this.tempTo = { X: pt.X, Y: pt.Y }
      if (this.press.kind === 'move' && this.press.moved) {
        const m = this.toMolRaw(pt)
        this.press.x = m.x
        this.press.y = m.y
      }
    },
    onPointerUp(e) {
      const pt = this.eventPos(e)
      if (this.panning) { this.panning = null; this.detach(); return }
      // 框选结束：算出落在矩形/曲线内的原子
      if (this.marquee) {
        const m = this.marquee
        this.marquee = null
        this.detach()
        const box = { x1: Math.min(m.x1, m.x2), y1: Math.min(m.y1, m.y2), x2: Math.max(m.x1, m.x2), y2: Math.max(m.y1, m.y2) }
        if (box.x2 - box.x1 < 4 && box.y2 - box.y1 < 4) { this.$emit('select-atoms', []); return }
        const inside = this.atoms.filter((a) => {
          const p = this.toPx(a)
          return p.X >= box.x1 && p.X <= box.x2 && p.Y >= box.y1 && p.Y <= box.y2
        }).map(a => a.index)
        this.$emit('select-atoms', inside)
        return
      }
      if (this.lassoPts) {
        const pts = this.lassoPts
        this.lassoPts = null
        this.detach()
        if (pts.length < 3) { this.$emit('select-atoms', []); return }
        const inside = this.atoms.filter(a => this.pointInPolygon(this.toPx(a), pts)).map(a => a.index)
        this.$emit('select-atoms', inside)
        return
      }
      const press = this.press
      this.press = null
      this.tempTo = null
      this.detach()
      if (!press) return
      const snap = this.nearestAtom(pt, 16)

      // 原子：单击选中（键工具下单击 = 自动接一个键）/ 选择工具拖动移动 / 键工具拖动拉键
      if (press.kind === 'atom' || press.kind === 'move') {
        if (!press.moved) {
          if (press.kind === 'atom' && this.autoExtend) {
            this.$emit('extend-atom', { index: press.index })
            return
          }
          this.$emit('select-atom', press.index)
          return
        }
        if (press.kind === 'move') {
          this.$emit('move-atom', {
            index: press.index,
            x: Math.round(press.x * 1000) / 1000,
            y: Math.round(press.y * 1000) / 1000
          })
          return
        }
        if (snap !== null && snap !== press.index) {
          this.$emit('add-bond', { a: press.index, b: snap, order: this.bondOrder })
          return
        }
        const a0 = this.atomMap[press.index]
        const m = this.toMolRaw(pt)
        if (!a0) return
        if (Math.hypot(m.x - a0.x, m.y - a0.y) < 0.35) return
        const p = this.snapFrom(a0.x, a0.y, m)
        this.$emit('add-bond-atom', { from: press.index, x: p.x, y: p.y, order: this.bondOrder })
        return
      }

      // 空白：单击放原子；拖动画一条新键
      if (!press.moved) {
        this.$emit('add-atom', { x: press.molX, y: press.molY })
        return
      }
      const p = this.snapFrom(press.molX, press.molY, this.toMolRaw(pt))
      this.$emit('add-atom-chain', { x1: press.molX, y1: press.molY, x2: p.x, y2: p.y, order: this.bondOrder })
    }
  }
}
</script>

<style scoped>
.mol2d {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.mol2d svg { display: block; touch-action: none; }
.mol2d-hint {
  position: absolute;
  left: 8px; bottom: 5px;
  font-size: 11px;
  color: var(--c-text-3);
  pointer-events: none;
}
</style>

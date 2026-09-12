<template>
  <!-- SOC 提取：左=文件 / 中=SOC矩阵 / 右=阈值·能级选择与能级图 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- 左：本地 .out 文件 -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>{{ $t('文件列表') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ files.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!files.length" class="ide-empty">{{ $t('暂无文件') }}<br>{{ $t('请先在右栏选择文件夹') }}</div>
          <div
            v-for="(f, idx) in files"
            :key="idx"
            class="ide-list-item"
            :class="{ active: selectedFile === f }"
            @click="parseFile(f)"
          >
            {{ f }}
          </div>
        </div>
      </aside>

      <!-- 中：SOC 矩阵 -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>{{ $t('SOC 矩阵（|Hso| cm⁻¹）') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ matrixInfo }}</span>
        </div>
        <!-- 阈值设置行 -->
        <div class="flex-center" style="gap:10px;padding:5px 12px;border-bottom:1px solid var(--c-border-soft);flex-shrink:0;background:var(--c-bar);flex-wrap:wrap;">
          <span class="label" style="font-weight:600;">{{ $t('阈值设置') }}</span>
          <span style="font-size:12px;color:var(--c-text-2);">|Hso| ≥</span>
          <input v-model.number="warnThr" type="number" min="0" step="0.1" class="control" style="width:70px;height:24px;" />
          <span class="badge badge-yellow">{{ $t('需关注(黄)') }}</span>
          <span style="font-size:12px;color:var(--c-text-2);">&gt;</span>
          <input v-model.number="critThr" type="number" min="0" step="0.1" class="control" style="width:70px;height:24px;" />
          <span class="badge badge-red">{{ $t('重点关注(红)') }}</span>
          <span style="font-size:12px;color:var(--c-text-3);">{{ $t('单位 cm⁻¹') }}</span>
        </div>
        <div class="flex-1 min-h-0" style="overflow:auto;padding:8px;">
          <table v-if="tRows.length" style="border-collapse:collapse;font-size:12px;">
            <thead style="position:sticky;top:0;background:var(--c-panel);z-index:5;">
              <tr>
                <th style="padding:4px 8px;border:1px solid var(--c-border);min-width:56px;">T \ S</th>
                <th v-for="s in sCols" :key="s" style="padding:4px 8px;border:1px solid var(--c-border);min-width:64px;">{{ s === 0 ? $t('S0(基态)') : 'S' + s }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tRows" :key="t">
                <td style="padding:4px 8px;border:1px solid var(--c-border);font-weight:600;background:var(--c-panel);">T{{ t }}</td>
                <td
                  v-for="s in sCols" :key="s"
                  :style="cellStyle(t, s)"
                  @click="addPair(t, s)"
                  :title="`T${t} – S${s === 0 ? '0' : s}`"
                >
                  <div style="text-align:center;font-weight:600;">{{ fmtSoc(t, s) }}</div>
                  <div style="text-align:center;font-size:10px;color:var(--c-on-accent);">ΔE {{ fmtGap(t, s) }} eV</div>
                </td>
              </tr>
            </tbody>
          </table>
          <EmptyNotice
            v-else-if="parsedOnce"
            :text="$t('该文件内不含 SOC 数据')"
            :hint="noticeHint"
          />
          <div v-else class="ide-empty" style="padding:60px;">{{ $t('请选择右侧文件解析') }}</div>
        </div>
      </section>

      <!-- 右：设置 + 能级图 -->
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>{{ $t('设置与能级图') }}</span></div>
        <div class="ide-pane-body">
          <div class="ide-group">
            <div class="flex-center" style="gap:6px;justify-content:space-between;">
              <span class="label" style="font-weight:400;">{{ $t('数据来源') }}</span>
              <div class="flex-center" style="gap:6px;">
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'local' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'local'">{{ $t('本地') }}</button>
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'remote' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'remote'" :disabled="!connected">{{ $t('远程') }}</button>
              </div>
            </div>
            <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;">
              {{ parseMode === 'remote' ? (remoteFolder || $t('未选择远程目录（含 .out）')) : (folder || $t('未选择本地文件夹')) }}
            </div>
            <button class="btn" @click="chooseDir">{{ parseMode === 'remote' ? $t('选择远程目录') : $t('选择文件夹') }}</button>
            <button class="btn btn-primary" @click="doParse" :disabled="parsing || !(parseMode === 'remote' ? remoteFolder : folder)">
              {{ parsing ? $t('解析中...') : $t('解析 / 重新解析') }}
            </button>
            <div v-if="tRows.length" class="flex" style="gap:6px;">
              <button class="btn" style="flex:1;" @click="exportCSV">{{ $t('导出 CSV') }}</button>
              <button class="btn" style="flex:1;" @click="exportExcel">{{ $t('导出 Excel') }}</button>
            </div>
          </div>

          <div class="ide-group">
            <div class="flex-center" style="justify-content:space-between;">
              <span class="label">{{ $t('自定义能级图层') }}</span>
              <button class="btn" style="height:22px;font-size:12px;padding:0 8px;" @click="addLayer">{{ $t('＋ 添加图层') }}</button>
            </div>
            <!-- 表头：序号 | S | → | T -->
            <div class="soc-grid" style="grid-template-columns:20px 1fr 18px 1fr;">
              <span></span>
              <span style="font-weight:600;color:var(--c-lumo);">{{ $t('S(单线态)') }}</span>
              <span></span>
              <span style="font-weight:600;color:var(--c-homo);">{{ $t('T(三线态)') }}</span>
            </div>
            <div v-for="(ly, idx) in layers" :key="idx" class="flex-col" style="gap:2px;padding:3px 0;border-bottom:1px dashed var(--c-border-soft);">
              <!-- 当前取值：S几 → T几 -->
              <div class="flex-center" style="justify-content:space-between;gap:6px;">
                <span style="font-size:12px;">
                  <span style="color:var(--c-lumo);font-weight:600;">{{ ly.a }}</span>
                  <span style="color:var(--c-text-3);margin:0 4px;">→</span>
                  <span style="color:var(--c-homo);font-weight:600;">{{ ly.b }}</span>
                </span>
                <button class="btn" style="height:20px;font-size:11px;padding:0 6px;" @click="removeLayer(idx)">{{ $t('删除') }}</button>
              </div>
              <div class="soc-grid" style="grid-template-columns:20px 1fr 18px 1fr;">
                <span style="color:var(--c-text-3);font-size:11px;">{{ idx + 1 }}.</span>
                <select class="control" style="width:100%;height:24px;font-size:12px;" v-model="ly.a">
                  <option v-for="opt in sOptions" :key="'a' + idx + opt.code" :value="opt.code">{{ opt.label }}</option>
                </select>
                <span></span>
                <select class="control" style="width:100%;height:24px;font-size:12px;" v-model="ly.b">
                  <option v-for="opt in tOptions" :key="'b' + idx + opt.code" :value="opt.code">{{ opt.label }}</option>
                </select>
              </div>
            </div>
            <div v-if="!layers.length" style="color:var(--c-text-3);font-size:12px;">{{ $t('（无图层，点“＋ 添加图层”开始）') }}</div>
            <button class="btn" style="height:24px;font-size:12px;" @click="clearLayers">{{ $t('清空全部') }}</button>
          </div>

          <div class="ide-group">
            <canvas
              ref="socCanvas"
              class="soc-canvas"
              @click="openBig"
              :title="$t('点击放大')"
              style="width:100%;background:#ffffff;border:1px solid var(--c-border-strong);cursor:pointer;"
            ></canvas>
            <div style="font-size:11px;color:var(--c-text-3);">{{ $t('红=S　蓝=T') }}</div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 远程文件浏览器 -->
    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="sessionId"
      :initial-path="browserInitialPath"
      :target="browserTarget"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />

    <LogViewer :lines="logLines" />

    <ImagePreviewModal
      v-model:visible="previewVisible"
      :src="previewSrc"
      :title="previewTitle"
      :filename="previewName"
      :initial-dir="folder"
    />
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'
import RemoteFileBrowser from '../components/RemoteFileBrowser.vue'
import { pickDirectory } from '@/api/dialog'
import { syncRemoteFolder } from '@/api/remoteSync'
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import { t as $tr } from '@/i18n'
import { PALETTE, drawAxes, drawLevel, drawEnergyLabel, font, crisp } from '@/utils/naturePlot'
import EmptyNotice from '@/components/EmptyNotice.vue'
import ImagePreviewModal from '@/components/ImagePreviewModal.vue'

const BACKEND = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`


export default {
  name: 'SocView',
  components: { LogViewer, RemoteFileBrowser, EmptyNotice, ImagePreviewModal },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, connected, sessionId, username }
  },
  data() {
    return {
      folder: '',
      previewVisible: false,
      previewSrc: '',
      previewTitle: '',
      previewName: 'soc-levels.png',
      parseMode: 'local',
      remoteFolder: '',
      browserVisible: false,
      browserInitialPath: '/',
      browserTarget: '',
      files: [],
      selectedFile: '',
      singlet: {},
      triplet: {},
      soc: {},
      maxT: 0,
      maxS: 0,
      parsing: false,
      parsedOnce: false,     // 已解析过 → 无数据显示"该文件内不含 SOC 数据"
      noticeHint: '',        // 解析失败原因
      warnThr: 0.2,
      critThr: 0.5,
      layers: [],
      logLines: [],
      logKey: 0,
      bigUrl: ''
    }
  },
  computed: {
    tRows() { return this.maxT ? Array.from({ length: this.maxT }, (_, i) => i + 1) : [] },
    sCols() { return this.maxS >= 0 ? Array.from({ length: this.maxS + 1 }, (_, i) => i) : [] },
    matrixInfo() {
      if (!this.maxT) return ''
      return `${this.maxT} T × ${this.maxS + 1} S`
    },
    // 可选能级（不显示能量，下拉更紧凑）
    levelOptions() {
      const out = []
      for (let s = 0; s <= this.maxS; s++) {
        out.push({ code: 'S' + s, label: 'S' + s })
      }
      for (let t = 1; t <= this.maxT; t++) {
        out.push({ code: 'T' + t, label: 'T' + t })
      }
      return out
    },
    // 左侧只放 S，右侧只放 T
    sOptions() {
      return this.levelOptions.filter(o => o.code.charAt(0) === 'S')
    },
    tOptions() {
      return this.levelOptions.filter(o => o.code.charAt(0) === 'T')
    }
  },
  watch: {
    layers: {
      deep: true,
      handler() { this.drawLevels() }
    }
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 120) this.logLines.shift()
    },
    async chooseDir() {
      if (this.parseMode === 'remote') {
        if (!this.connected) { this.addLog($tr('请先连接服务器'), '#ffa500'); return }
        this.browserTarget = 'socDir'
        this.browserInitialPath = `/home/${this.username}` || '/'
        this.browserVisible = true
        return
      }
      let p
      try { p = await pickDirectory($tr('选择包含 ORCA SOC .out 的文件夹')) } catch (e) { this.addLog(e.message, '#ff6b6b'); return }
      if (p) {
        await this.loadFolder(p)
        // 选好目录后自动解析第一个文件（与远程模式一致，无需再手动点解析）
        if (this.files.length) this.parseFile(this.files[0])
      }
    },
    async loadFolder(p) {
      this.folder = p
      this.selectedFile = ''
      this.singlet = {}; this.triplet = {}; this.soc = {}; this.maxT = 0; this.maxS = 0
      this.files = []
      this.addLog($tr('本地目录: {0}', { 0: p }), '#87d2ff')
      try {
        const r = await fetch(`${BACKEND}/api/local/ls`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: p }) })
        const d = await r.json()
        if (r.ok) this.files = (d.entries || []).filter(e => !e.is_dir && /\.out$/i.test(e.name)).map(e => e.name)
        else this.addLog(d.detail || $tr('读取目录失败'), '#ff6b6b')
      } catch (e) { this.addLog($tr('读取目录失败: ') + e.message, '#ff6b6b') }
    },
    async doParse() {
      if (this.parseMode === 'local') {
        if (!this.folder) { this.addLog($tr('请先选择本地文件夹'), '#ffa500'); return }
        this.parseFile(this.selectedFile || this.files[0])
        return
      }
      // 远程：同步 .out 到缓存后解析
      if (!this.remoteFolder) { this.addLog($tr('请先选择远程目录'), '#ffa500'); return }
      if (!this.connected) { this.addLog($tr('请先连接服务器'), '#ffa500'); return }
      if (this.parsing) return
      this.parsing = true
      this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      try {
        const { cacheDir, count } = await syncRemoteFolder(this.sessionId, this.remoteFolder, '.out')
        this.addLog($tr('已同步 {0} 个 .out → {1}', { 0: count, 1: cacheDir }), '#87d2ff')
        await this.loadFolder(cacheDir)
        this.parsing = false // 释放同步守卫，让 parseFile 接管
        if (!this.files.length) {
          this.addLog($tr('缓存中没有可解析的 .out 文件'), '#ffa500')
        } else {
          await this.parseFile(this.files[0])
        }
      } catch (e) {
        this.addLog($tr('远程解析失败: ') + e.message, '#ff6b6b')
      } finally {
        this.parsing = false
      }
    },
    onBrowserSelect({ target, path, is_dir }) {
      if (target === 'socDir') {
        this.remoteFolder = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
        this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      }
    },
    async parseFile(name) {
      if (!name) {
        this.addLog($tr('请先在左侧选择文件'), '#ffa500')
        return
      }
      if (this.parsing) return
      const path = `${this.folder.replace(/[\\/]+$/, '')}\\${name}`
      this.selectedFile = name
      this.parsing = true
      this.addLog($tr('解析: {0}', { 0: name }), '#87d2ff')
      try {
        const r = await fetch(`${BACKEND}/api/soc/parse`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path }) })
        const d = await r.json()
        if (!r.ok) throw new Error(d.detail || $tr('解析失败'))
        this.parsedOnce = true
        this.noticeHint = ''
        this.singlet = d.singlet || {}
        this.triplet = d.triplet || {}
        this.soc = d.soc || {}
        this.maxT = d.max_t || 0
        this.maxS = d.max_s || 0
        // 默认图层：S1 → T2（左 S 右 T）
        this.layers = [{ a: 'S1', b: 'T2' }]
        this.addLog($tr('解析完成：{0} T × {1} S', { 0: this.maxT, 1: this.maxS + 1 }), '#7cfc00')
        this.drawLevels()
      } catch (e) {
        this.parsedOnce = true
        this.noticeHint = e.message || ''
        this.singlet = {}; this.triplet = {}; this.soc = {}; this.maxT = 0; this.maxS = 0
        this.addLog($tr('解析失败: ') + e.message, '#ff6b6b')
      } finally {
        this.parsing = false
      }
    },
    // 添加一层（左 S，右 T）
    addLayer() {
      const sOpts = this.sOptions
      const tOpts = this.tOptions
      const a = sOpts.find(o => o.code === 'S1') || sOpts[0]
      const b = tOpts.find(o => o.code === 'T1') || tOpts[0]
      this.layers = [...this.layers, { a: a ? a.code : 'S0', b: b ? b.code : 'T1' }]
    },
    removeLayer(idx) {
      this.layers = this.layers.filter((_, i) => i !== idx)
    },
    clearLayers() {
      this.layers = []
      this.drawLevels()
    },
    // 点击矩阵单元格：加入或移除 T–S 层（左 S，右 T）
    addCellPair(t, s) {
      const a = 'S' + s
      const b = 'T' + t
      const idx = this.layers.findIndex(ly => ly.a === a && ly.b === b)
      if (idx >= 0) this.layers = this.layers.filter((_, i) => i !== idx)
      else this.layers = [...this.layers, { a, b }]
    },
    energyOf(kind, i) { return kind === 'T' ? (this.triplet[i] || 0) : (this.singlet[i] || 0) },
    codeInfo(code) {
      const kind = String(code || 'S0').charAt(0).toUpperCase()
      const id = Number(String(code).slice(1))
      return { kind: kind === 'T' ? 'T' : 'S', id: isNaN(id) ? 0 : id }
    },
    socVal(t, s) { return Number(this.soc[`${t}_${s}`] || 0) },
    fmtSoc(t, s) { return this.socVal(t, s) ? this.socVal(t, s).toFixed(3) : '—' },
    gapVal(t, s) {
      const et = Number(this.triplet[t]); const es = Number(this.singlet[s])
      if (isNaN(et)) return null
      if (s === 0 || isNaN(es)) return Math.abs(et)
      return Math.abs(et - es)
    },
    fmtGap(t, s) {
      const g = this.gapVal(t, s)
      return g === null ? '—' : g.toFixed(3)
    },
    cellStyle(t, s) {
      const base = { border: '1px solid var(--c-border-soft)', minWidth: '76px', cursor: 'pointer', textAlign: 'center' }
      const v = this.socVal(t, s)
      if (v > this.critThr) return { ...base, background: 'rgba(200,60,50,0.32)' }
      if (v >= this.warnThr) return { ...base, background: 'rgba(214,158,46,0.30)' }
      return base
    },
    //energyOf(kind, i) { return kind === 'T' ? (this.triplet[i] || 0) : (this.singlet[i] || 0) },
    drawLevels() {
      const cv = this.$refs.socCanvas
      if (!cv) return
      // 9:16 竖屏；内部分辨率固定 900×1600（放大绘制，点击弹大图清晰）
      const W = Math.max(160, cv.clientWidth || 220)
      const H = Math.round(W * 16 / 9)
      cv.style.height = H + 'px'
      cv.width = 900
      cv.height = 1600
      const ctx = cv.getContext('2d')
      ctx.setTransform(900 / W, 0, 0, 1600 / H, 0, 0)
      ctx.clearRect(0, 0, W, H)
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H)
      this.drawScene(ctx, W, H)
    },
    drawScene(ctx, W, H) {
      // 合并绘制：所有 S-T 图层叠在同一张图上，左=S，右=T，含能量坐标轴（Nature 风格）
      const colorS = PALETTE.singlet
      const colorT = PALETTE.triplet
      const sf = Math.max(0.6, W / 260)
      const eOf = (code) => { const ci = this.codeInfo(code); return this.energyOf(ci.kind, ci.id) }

      // 收集涉及能级
      const used = []
      const seen = {}
      const pairs = this.layers.filter(function (ly) {
        const ciA = this.codeInfo(ly.a)
        const ciB = this.codeInfo(ly.b)
        return ciA.id >= 0 && ciB.id >= 0
      }, this)
      pairs.forEach(ly => {
        [ly.a, ly.b].forEach(code => {
          if (!seen[code]) { seen[code] = true; used.push(code) }
        })
      })
      if (!used.length) return

      const es = used.map(eOf)
      const eMin = Math.max(0, Math.min.apply(null, es) - 0.35)
      const eMax = Math.max.apply(null, es) + 0.35
      const L = Math.max(50 * sf, W * 0.16)
      const R = W - 14 * sf
      const T = 22 * sf
      const B = H - 42 * sf
      const yOf = drawAxes(ctx, { L, T, R, B, min: eMin, max: eMax, sf, title: 'Energy (eV)' })

      const cxS = L + (R - L) * 0.24
      const cxT = L + (R - L) * 0.76
      const seg = Math.min(26 * sf, (R - L) * 0.11)

      // S-T 连线：只保留虚线（不标数值，层与层的关系在上方图层列表里）
      pairs.forEach((ly) => {
        const ciA = this.codeInfo(ly.a)
        const ciB = this.codeInfo(ly.b)
        const yS = yOf(this.energyOf('S', ciA.id))
        const yT = yOf(this.energyOf('T', ciB.id))
        ctx.save()
        ctx.strokeStyle = PALETTE.connector
        ctx.lineWidth = Math.max(0.9, 1.1 * sf)
        ctx.setLineDash([3.5 * sf, 3 * sf])
        ctx.beginPath()
        ctx.moveTo(cxS + seg + 3 * sf, crisp(yS))
        ctx.lineTo(cxT - seg - 3 * sf, crisp(yT))
        ctx.stroke()
        ctx.restore()
      })

      // 能级线 + 标签（每种能级画一次）
      used.forEach(code => {
        const ci = this.codeInfo(code)
        const y = yOf(eOf(code))
        const cx = ci.kind === 'T' ? cxT : cxS
        const color = ci.kind === 'T' ? colorT : colorS
        drawLevel(ctx, { cx, y, half: seg, color, sf, width: 2.2 })
        const label = code + '  ' + eOf(code).toFixed(3)
        if (ci.kind === 'T') {
          drawEnergyLabel(ctx, { x: cxT - seg - 6 * sf, y, text: label, color, align: 'right', sf })
        } else {
          drawEnergyLabel(ctx, { x: cxS + seg + 6 * sf, y, text: label, color, align: 'left', sf })
        }
      })

      // <S|Hso|T> 按顺序标注，集中在下轴下方居中
      const annos = []
      pairs.forEach(ly => {
        const ciA = this.codeInfo(ly.a)
        const ciB = this.codeInfo(ly.b)
        const v = this.socVal(ciB.id, ciA.id)
        if (v) annos.push(`⟨S${ciA.id}|Hso|T${ciB.id}⟩ ${v.toFixed(2)} cm⁻¹`)
      })
      if (annos.length) {
        ctx.save()
        ctx.fillStyle = PALETTE.text
        ctx.font = font(10.5 * sf, '500')
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        const lineH = 13 * sf
        const room = Math.max(1, Math.floor((H - B - 6 * sf) / lineH))
        const shown = annos.slice(0, room)
        const extra = annos.length - shown.length
        shown.forEach((txt, i) => {
          const suffix = (i === shown.length - 1 && extra > 0) ? `   +${extra}` : ''
          ctx.fillText(txt + suffix, (cxS + cxT) / 2, B + 7 * sf + i * lineH)
        })
        ctx.restore()
      }
    },

    openBig() {
      const cv = this.$refs.socCanvas
      if (!cv) return
      const copy = document.createElement('canvas')
      copy.width = cv.width; copy.height = cv.height
      copy.getContext('2d').drawImage(cv, 0, 0)
      this.previewSrc = copy.toDataURL('image/png')
      this.previewTitle = this.$t('SOC能级图')
      this.previewName = 'soc-levels.png'
      this.previewVisible = true
    },
    async exportExcel() {
      if (!this.maxT) return
      try {
        const XLSX = await import('xlsx')
        const wb = XLSX.utils.book_new()
        // 矩阵
        const rows = this.tRows.map(t => {
          const o = { 'T\\S': 'T' + t }
          this.sCols.forEach(s => { o[s === 0 ? 'S0(基态)' : 'S' + s] = this.socVal(t, s) || '' })
          return o
        })
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), $tr('SOC矩阵_cm-1'))
        // 能级
        const lv = []
        this.sCols.slice(1).forEach(s => lv.push({ 类型: 'Singlet', 标签: 'S' + s, '能量(eV)': this.energyOf('S', s) }))
        this.tRows.forEach(t => lv.push({ 类型: 'Triplet', 标签: 'T' + t, '能量(eV)': this.energyOf('T', t) }))
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(lv), $tr('能级'))
        // 耦合
        const cp = []
        this.tRows.forEach(t => this.sCols.forEach(s => {
          const v = this.socVal(t, s)
          if (v) cp.push({ T: 'T' + t, S: s === 0 ? 'S0' : 'S' + s, '|Hso|(cm⁻¹)': v, '|ΔE|(eV)': this.gapVal(t, s) == null ? '' : this.gapVal(t, s).toFixed(4) })
        }))
        if (cp.length) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(cp), $tr('耦合'))
        XLSX.writeFile(wb, 'soc_data.xlsx')
        this.addLog($tr('SOC 数据已导出 (soc_data.xlsx)'), '#7cfc00')
      } catch (e) { this.addLog($tr('导出失败: ') + e.message, '#ffa500') }
    },
    exportCSV() {
      if (!this.maxT) return
      const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
      const header = ['T\\S', ...this.sCols.map(s => s === 0 ? 'S0(基态)' : 'S' + s)]
      const lines = [header.join(',')]
      this.tRows.forEach(t => {
        lines.push(['T' + t, ...this.sCols.map(s => this.socVal(t, s) ? this.socVal(t, s).toFixed(4) : '')].map(esc).join(','))
      })
      // 附带 |ΔE| 表（第二块）
      lines.push('')
      lines.push(['|ΔE| eV', ...this.sCols.map(s => s === 0 ? 'S0(基态)' : 'S' + s)].join(','))
      this.tRows.forEach(t => {
        lines.push(['T' + t, ...this.sCols.map(s => this.gapVal(t, s) == null ? '' : this.gapVal(t, s).toFixed(4))].join(','))
      })
      const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'soc_matrix.csv'
      a.click()
      URL.revokeObjectURL(a.href)
      this.addLog('SOC 数据已导出 (soc_matrix.csv)', '#7cfc00')
    }
  }
}
</script>

<style scoped>
.badge { font-size:11px; padding:0 6px; border-radius:3px; border:1px solid; }
.badge-yellow { color:#8a6d1a; border-color:#c9a83a; background:rgba(214,158,46,0.18); }
.badge-red { color:#a3332b; border-color:#c9a83a; background:rgba(200,60,50,0.16); }
.chip { font-size:12px; display:inline-flex; align-items:center; gap:3px; padding:1px 5px; border:1px solid var(--c-border); border-radius:9px; cursor:pointer; }
.chip-x { background:transparent; border:none; cursor:pointer; color:var(--c-text-3); font-size:12px; padding:0 2px; }
.chip-x:hover { color:#c22; }
.soc-grid { display:grid; align-items:center; gap:4px; margin:2px 0; }
</style>

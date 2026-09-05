<template>
  <!-- SOC 提取：左=文件 / 中=SOC矩阵 / 右=阈值·能级选择与能级图 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- 左：本地 .out 文件 -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>文件列表</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ files.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!files.length" class="ide-empty">暂无文件<br>请先在右栏选择文件夹</div>
          <div
            v-for="(f, idx) in files"
            :key="idx"
            class="ide-list-item"
            :class="{ active: selectedFile === f }"
            @click="selectedFile = f"
          >
            {{ f }}
          </div>
        </div>
      </aside>

      <!-- 中：SOC 矩阵 -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>SOC 矩阵（|Hso| cm⁻¹）</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ matrixInfo }}</span>
        </div>
        <!-- 阈值设置行 -->
        <div class="flex-center" style="gap:10px;padding:5px 12px;border-bottom:1px solid var(--c-border-soft);flex-shrink:0;background:var(--c-bar);flex-wrap:wrap;">
          <span class="label" style="font-weight:600;">阈值设置</span>
          <span style="font-size:12px;color:var(--c-text-2);">|Hso| ≥</span>
          <input v-model.number="warnThr" type="number" min="0" step="0.1" class="control" style="width:70px;height:24px;" />
          <span class="badge badge-yellow">需关注(黄)</span>
          <span style="font-size:12px;color:var(--c-text-2);">&gt;</span>
          <input v-model.number="critThr" type="number" min="0" step="0.1" class="control" style="width:70px;height:24px;" />
          <span class="badge badge-red">重点关注(红)</span>
          <span style="font-size:12px;color:var(--c-text-3);">单位 cm⁻¹（耦合强到弱：S0 列含基态）</span>
        </div>
        <div class="flex-1 min-h-0" style="overflow:auto;padding:8px;">
          <table v-if="tRows.length" style="border-collapse:collapse;font-size:12px;">
            <thead style="position:sticky;top:0;background:var(--c-panel);z-index:5;">
              <tr>
                <th style="padding:4px 8px;border:1px solid var(--c-border);min-width:56px;">T \ S</th>
                <th v-for="s in sCols" :key="s" style="padding:4px 8px;border:1px solid var(--c-border);min-width:64px;">{{ s === 0 ? 'S0(基态)' : 'S' + s }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tRows" :key="t">
                <td style="padding:4px 8px;border:1px solid var(--c-border);font-weight:600;background:var(--c-panel);">T{{ t }}</td>
                <td
                  v-for="s in sCols" :key="s"
                  :style="cellStyle(t, s)"
                  @click="addPair(t, s)"
                  :title="`点击加入能级对：T${t}–S${s === 0 ? '0(基态)' : s}`"
                >
                  <div style="text-align:center;font-weight:600;">{{ fmtSoc(t, s) }}</div>
                  <div style="text-align:center;font-size:10px;color:var(--c-text-3);">ΔE {{ fmtGap(t, s) }} eV</div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="ide-empty" style="padding:60px;">请选择右侧文件解析</div>
        </div>
      </section>

      <!-- 右：设置 + 能级图 -->
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>设置与能级图</span></div>
        <div class="ide-pane-body">
          <div class="ide-group">
            <div class="flex-center" style="gap:6px;justify-content:space-between;">
              <span class="label" style="font-weight:400;">数据来源</span>
              <div class="flex-center" style="gap:6px;">
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'local' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'local'">本地</button>
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'remote' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'remote'" :disabled="!connected">远程</button>
              </div>
            </div>
            <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;">
              {{ parseMode === 'remote' ? (remoteFolder || '未选择远程目录（含 .out）') : (folder || '未选择本地文件夹') }}
            </div>
            <button class="btn" @click="chooseDir">选择{{ parseMode === 'remote' ? '远程目录' : '文件夹' }}</button>
            <button class="btn btn-primary" @click="doParse" :disabled="parsing || !(parseMode === 'remote' ? remoteFolder : folder)">
              {{ parsing ? '解析中...' : '解析 / 重新解析' }}
            </button>
            <div v-if="tRows.length" class="flex" style="gap:6px;">
              <button class="btn" style="flex:1;" @click="exportCSV">导出 CSV</button>
              <button class="btn" style="flex:1;background:#722ed1;color:#fff;border-color:#722ed1;" @click="exportExcel">导出 Excel</button>
            </div>
          </div>

          <div class="ide-group">
            <div class="flex-center" style="justify-content:space-between;">
              <span class="label">自定义能级图层</span>
              <button class="btn" style="height:22px;font-size:12px;padding:0 8px;" @click="addLayer">＋ 添加图层</button>
            </div>
            <div style="font-size:11px;color:var(--c-text-3);">每层选一个 S(左) 与一个 T(右)，点击矩阵单元格可快速加入；按顺序叠画在一张图上</div>
            <!-- 表头：序号 | S | → | T -->
            <div class="soc-grid" style="grid-template-columns:20px 1fr 18px 1fr;">
              <span></span>
              <span style="font-weight:600;color:var(--c-lumo);">S(单线态)</span>
              <span></span>
              <span style="font-weight:600;color:var(--c-homo);">T(三线态)</span>
            </div>
            <div v-for="(ly, idx) in layers" :key="idx" class="flex-col" style="gap:2px;padding:3px 0;border-bottom:1px dashed var(--c-border-soft);">
              <!-- 当前取值：S几 → T几 -->
              <div class="flex-center" style="justify-content:space-between;gap:6px;">
                <span style="font-size:12px;">
                  <span style="color:var(--c-lumo);font-weight:600;">{{ ly.a }}</span>
                  <span style="color:var(--c-text-3);margin:0 4px;">→</span>
                  <span style="color:var(--c-homo);font-weight:600;">{{ ly.b }}</span>
                </span>
                <button class="btn" style="height:20px;font-size:11px;padding:0 6px;" @click="removeLayer(idx)">删除</button>
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
            <div v-if="!layers.length" style="color:var(--c-text-3);font-size:12px;">（无图层，点“＋ 添加图层”开始）</div>
            <button class="btn" style="height:24px;font-size:12px;" @click="clearLayers">清空全部</button>
          </div>

          <div class="ide-group">
            <canvas
              ref="socCanvas"
              class="soc-canvas"
              @click="openBig"
              title="点击放大"
              style="width:100%;background:#ffffff;border:1px solid var(--c-border);border-radius:4px;cursor:pointer;"
            ></canvas>
            <div style="font-size:11px;color:var(--c-text-3);">红=单线态(S) 蓝=三线态(T)；每层一栏，按上顺序排列</div>
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
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'
import RemoteFileBrowser from '../components/RemoteFileBrowser.vue'
import { pickDirectory } from '@/api/dialog'
import { syncRemoteFolder } from '@/api/remoteSync'
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'

const BACKEND = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`

export default {
  name: 'SocView',
  components: { LogViewer, RemoteFileBrowser },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, connected, sessionId, username }
  },
  data() {
    return {
      folder: '',
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
        if (!this.connected) { this.addLog('请先连接服务器', '#ffa500'); return }
        this.browserTarget = 'socDir'
        this.browserInitialPath = `/home/${this.username}` || '/'
        this.browserVisible = true
        return
      }
      let p
      try { p = await pickDirectory('选择包含 ORCA SOC .out 的文件夹') } catch (e) { this.addLog(e.message, '#ff6b6b'); return }
      if (p) this.loadFolder(p)
    },
    async loadFolder(p) {
      this.folder = p
      this.selectedFile = ''
      this.singlet = {}; this.triplet = {}; this.soc = {}; this.maxT = 0; this.maxS = 0
      this.files = []
      this.addLog(`本地目录: ${p}`, '#87d2ff')
      try {
        const r = await fetch(`${BACKEND}/api/local/ls`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: p }) })
        const d = await r.json()
        if (r.ok) this.files = (d.entries || []).filter(e => !e.is_dir && /\.out$/i.test(e.name)).map(e => e.name)
        else this.addLog(d.detail || '读取目录失败', '#ff6b6b')
      } catch (e) { this.addLog('读取目录失败: ' + e.message, '#ff6b6b') }
    },
    async doParse() {
      if (this.parseMode === 'local') {
        if (!this.folder) { this.addLog('请先选择本地文件夹', '#ffa500'); return }
        this.parseFile(this.selectedFile || this.files[0])
        return
      }
      // 远程：同步 .out 到缓存后解析
      if (!this.remoteFolder) { this.addLog('请先选择远程目录', '#ffa500'); return }
      if (!this.connected) { this.addLog('请先连接服务器', '#ffa500'); return }
      if (this.parsing) return
      this.parsing = true
      this.addLog(`远程目录: ${this.remoteFolder}`, '#87d2ff')
      try {
        const { cacheDir, count } = await syncRemoteFolder(this.sessionId, this.remoteFolder, '.out')
        this.addLog(`已同步 ${count} 个 .out → ${cacheDir}`, '#87d2ff')
        await this.loadFolder(cacheDir)
        this.parsing = false // 释放同步守卫，让 parseFile 接管
        if (!this.files.length) {
          this.addLog('缓存中没有可解析的 .out 文件', '#ffa500')
        } else {
          await this.parseFile(this.files[0])
        }
      } catch (e) {
        this.addLog('远程解析失败: ' + e.message, '#ff6b6b')
      } finally {
        this.parsing = false
      }
    },
    onBrowserSelect({ target, path, is_dir }) {
      if (target === 'socDir') {
        this.remoteFolder = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
        this.addLog(`远程目录: ${this.remoteFolder}`, '#87d2ff')
      }
    },
    async parseFile(name) {
      if (!name) {
        this.addLog('请先在左侧选择文件', '#ffa500')
        return
      }
      if (this.parsing) return
      const path = `${this.folder.replace(/[\\/]+$/, '')}\\${name}`
      this.selectedFile = name
      this.parsing = true
      this.addLog(`解析: ${name}`, '#87d2ff')
      try {
        const r = await fetch(`${BACKEND}/api/soc/parse`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path }) })
        const d = await r.json()
        if (!r.ok) throw new Error(d.detail || '解析失败')
        this.singlet = d.singlet || {}
        this.triplet = d.triplet || {}
        this.soc = d.soc || {}
        this.maxT = d.max_t || 0
        this.maxS = d.max_s || 0
        // 默认图层：S1 → T2（左 S 右 T）
        this.layers = [{ a: 'S1', b: 'T2' }]
        this.addLog(`解析完成：${this.maxT} T × ${this.maxS + 1} S`, '#7cfc00')
        this.drawLevels()
      } catch (e) {
        this.addLog('解析失败: ' + e.message, '#ff6b6b')
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
    energyOf(kind, i) { return kind === 'T' ? (this.triplet[i] || 0) : (this.singlet[i] || 0) },
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
      // 合并绘制：所有 S-T 图层叠在同一张图上，左=红S，右=蓝T，含能量坐标轴
      const colorS = '#b3483c'
      const colorT = '#2f6fae'
      const sf = Math.max(0.6, W / 260)
      const plotL = 58 * sf
      const plotR = W - 10
      const plotT = 18
      const plotB = H - 24
      const plotW = plotR - plotL
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
      const yOf = (e) => plotB - ((e - eMin) / (eMax - eMin)) * (plotB - plotT)

      // 画轴：黑框 + 左纵轴刻度
      ctx.strokeStyle = '#111111'
      ctx.lineWidth = Math.max(1, sf * 0.8)
      ctx.strokeRect(plotL, plotT, plotW, plotB - plotT)
      ctx.fillStyle = '#111111'
      ctx.font = Math.round(10 * sf) + 'px Segoe UI, sans-serif'
      ctx.textAlign = 'right'
      ctx.textBaseline = 'middle'
      const range = eMax - eMin
      const rawStep = range / 6
      const mag = Math.pow(10, Math.floor(Math.log10(rawStep)))
      const norm = rawStep / mag
      const step = (norm >= 5 ? 5 : norm >= 2 ? 2 : 1) * mag
      for (let v = Math.ceil(eMin / step) * step; v <= eMax + 1e-9; v += step) {
        const y = yOf(v)
        if (y < plotT - 2 || y > plotB + 2) continue
        ctx.beginPath()
        ctx.moveTo(plotL - 4 * sf, y)
        ctx.lineTo(plotL, y)
        ctx.stroke()
        ctx.fillText(v.toFixed(2), plotL - 6 * sf, y)
      }

      ctx.fillStyle = '#111111'
      ctx.font = Math.round(10 * sf) + 'px Segoe UI, sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText('E (eV)', plotL + 4 * sf, plotT - 6 * sf)

      const cxS = plotL + plotW * 0.20
      const cxT = plotL + plotW * 0.80
      const seg = Math.min(26 * sf, plotW * 0.10)

      // 能级线 + 标签（每种能级画一次）
      used.forEach(code => {
        const ci = this.codeInfo(code)
        const y = yOf(eOf(code))
        const cx = ci.kind === 'T' ? cxT : cxS
        ctx.strokeStyle = ci.kind === 'T' ? colorT : colorS
        ctx.lineWidth = Math.max(1.6, 3 * sf)
        ctx.beginPath()
        ctx.moveTo(cx - seg, y)
        ctx.lineTo(cx + seg, y)
        ctx.stroke()
        ctx.font = '600 ' + Math.round(12 * sf) + 'px Segoe UI, sans-serif'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = ci.kind === 'T' ? colorT : colorS
        if (ci.kind === 'T') {
          ctx.textAlign = 'right'
          ctx.fillText(code + '  ' + eOf(code).toFixed(3) + ' eV', cxT - seg - 8 * sf, y)
        } else {
          ctx.textAlign = 'left'
          ctx.fillText(code + '  ' + eOf(code).toFixed(3) + ' eV', cxS + seg + 8 * sf, y)
        }
      })

      // S-T 连线
      pairs.forEach(ly => {
        const ciA = this.codeInfo(ly.a)
        const ciB = this.codeInfo(ly.b)
        const yS = yOf(this.energyOf('S', ciA.id))
        const yT = yOf(this.energyOf('T', ciB.id))
        ctx.strokeStyle = '#999999'
        ctx.lineWidth = Math.max(0.8, sf)
        ctx.setLineDash([4, 3])
        ctx.beginPath()
        ctx.moveTo(cxS + seg + 6 * sf, yS)
        ctx.lineTo(cxT - seg - 6 * sf, yT)
        ctx.stroke()
        ctx.setLineDash([])
      })
      // <S|Hso|T> 按顺序标注，集中在下轴上方居中
      const annos = []
      pairs.forEach(ly => {
        const ciA = this.codeInfo(ly.a)
        const ciB = this.codeInfo(ly.b)
        const v = this.socVal(ciB.id, ciA.id)
        if (v) annos.push('<S' + ciA.id + '|Hso|T' + ciB.id + '> ' + v.toFixed(2))
      })
      if (annos.length) {
        ctx.fillStyle = '#111111'
        ctx.font = 'bold ' + Math.round(11 * sf) + 'px Segoe UI, sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        const maxLine = Math.max(1, Math.floor((plotB - plotT - 12) / (15 * sf)))
        const shown = annos.slice(0, maxLine)
        const extra = annos.length - shown.length
        for (let li = 0; li < shown.length; li++) {
          ctx.fillText(shown[li] + (li === shown.length - 1 && extra > 0 ? ' ... +' + extra : ''), (cxS + cxT) / 2, plotB - 12 - li * (15 * sf))
        }
      }
    },

    openBig() {
      const cv = this.$refs.socCanvas
      if (!cv) return
      const win = window.open('', '_blank', 'width=900,height=1200')
      if (win) {
        const copy = document.createElement('canvas')
        copy.width = cv.width; copy.height = cv.height
        copy.getContext('2d').drawImage(cv, 0, 0)
        win.document.write('<html><head><title>SOC能级图</title></head><body style="margin:0;background:#fff;"><img style="width:100%;" src="' + copy.toDataURL('image/png') + '" /></body></html>')
        win.document.close()
      }
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
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), 'SOC矩阵_cm-1')
        // 能级
        const lv = []
        this.sCols.slice(1).forEach(s => lv.push({ 类型: 'Singlet', 标签: 'S' + s, '能量(eV)': this.energyOf('S', s) }))
        this.tRows.forEach(t => lv.push({ 类型: 'Triplet', 标签: 'T' + t, '能量(eV)': this.energyOf('T', t) }))
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(lv), '能级')
        // 耦合
        const cp = []
        this.tRows.forEach(t => this.sCols.forEach(s => {
          const v = this.socVal(t, s)
          if (v) cp.push({ T: 'T' + t, S: s === 0 ? 'S0' : 'S' + s, '|Hso|(cm⁻¹)': v, '|ΔE|(eV)': this.gapVal(t, s) == null ? '' : this.gapVal(t, s).toFixed(4) })
        }))
        if (cp.length) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(cp), '耦合')
        XLSX.writeFile(wb, 'soc_data.xlsx')
        this.addLog('SOC 数据已导出 (soc_data.xlsx)', '#7cfc00')
      } catch (e) { this.addLog('导出失败: ' + e.message, '#ffa500') }
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
.chip-x { background:transparent; border:none; cursor:pointer; color:#999; font-size:12px; padding:0 2px; }
.chip-x:hover { color:#c22; }
.soc-grid { display:grid; align-items:center; gap:4px; margin:2px 0; }
</style>

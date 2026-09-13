<template>
  <!-- 三栏：左=激发态输出文件 / 中=分析结果 / 右=参数与运行 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- ===== 左：文件列表 ===== -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>{{ $t('文件列表') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ files.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!files.length" class="ide-empty">
            {{ $t('暂无文件') }}<br>{{ $t('请先在右侧选择文件夹') }}
          </div>
          <div
            v-for="(f, idx) in files"
            :key="idx"
            class="ide-list-item"
            :class="{ active: selectedIndex === idx }"
            @click="selectFile(idx)"
          >
            {{ f.name }}
            <!-- 该文件正在分析 / 绘制（可以同时跑多个文件，切走也不影响） -->
            <span v-if="fileBusy(f, idx)" class="ana-busy">{{ fileBusy(f, idx) }}</span>
          </div>
        </div>
      </aside>

      <!-- ===== 中：分析结果 ===== -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>{{ mode === 'nto' ? $t('自然跃迁轨道（NTO）分析') : $t('空穴-电子分析') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">
            {{ sourceFile ? sourceFile.name : '—' }}
          </span>
        </div>
        <div class="ide-pane-body" style="overflow:auto;">
          <div v-if="restoring" class="ana-block" style="color:var(--c-accent);font-weight:600;">
            {{ $t('正在恢复先前解析的内容……') }}
          </div>
          <EmptyNotice v-if="!results.length && !running && !restoring" :text="$t('还没有分析结果')"
                       :hint="$t('左侧选择一个含激发态信息的输出文件，勾选激发态后点「开始分析」')" />

          <div v-for="it in results" :key="it.state" class="ana-block">
            <div class="ana-head">
              <span class="ana-title" :class="it.spin === 'T' ? 'spin-t' : 'spin-s'">{{ stateLabel(it) }}</span>
              <span v-if="it.error" class="ana-err">{{ it.error }}</span>
            </div>

            <!-- 定量指标 -->
            <table v-if="it.metrics && it.metrics.length" class="ana-table">
              <tbody>
                <tr v-for="m in it.metrics" :key="m.key">
                  <td class="ana-k">{{ metricLabel(m) }}</td>
                  <td class="ana-v">
                    <template v-if="m.vec">{{ m.vec.map(v => v.toFixed(3)).join(', ') }} {{ m.unit }}</template>
                    <template v-else>{{ fmt(m.value) }} {{ m.unit }}</template>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- NTO 本征值 -->
            <template v-if="it.parsed">
              <div class="ana-sub">
                {{ $t('激发能') }} {{ fmt(it.parsed.energy) }} eV · {{ $t('多重度') }} {{ it.parsed.mult }} ·
                {{ $t('组态数') }} {{ it.parsed.pairs }} · {{ $t('占据轨道') }} {{ it.parsed.nocc }}
              </div>
              <table v-if="(it.parsed.eigenvalues || []).length" class="ana-table">
                <thead>
                  <tr>
                    <th class="ana-k">{{ $t('NTO 对') }}</th>
                    <th class="ana-v">{{ $t('本征值（贡献）') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(e, i) in it.parsed.eigenvalues" :key="i" :class="{ 'ana-top': i === 0 }">
                    <td class="ana-k">{{ $t('第 {n} 对', { n: i + 1 }) }}</td>
                    <td class="ana-v">{{ (e * 100).toFixed(2) }} %</td>
                  </tr>
                </tbody>
              </table>
              <div class="ana-sub">
                {{ $t('本征值之和') }} {{ fmt(it.parsed.eigen_sum) }} ·
                {{ $t('归一化偏差') }} {{ fmt(it.parsed.deviation) }}
                <span v-if="it.nto_file"> · {{ $t('NTO 文件') }}: {{ baseName(it.nto_file) }}</span>
              </div>
            </template>

            <!-- 成对的图形：NTO 一左一右（占据/空），空穴-电子则是 Hole / Electron -->
            <div v-for="row in pairRows(it)" :key="row.key" class="pair-row">
              <div class="pair-cell">
                <div class="pair-head">{{ row.leftLabel }}</div>
                <div class="pair-body">
                  <img v-if="row.left && imageData[row.left.cub]" :src="imageData[row.left.cub]"
                       class="pair-img" loading="lazy" decoding="async" @click="openPreview(row.left)" />
                  <CubPreview v-else-if="row.left && cubTexts[row.left.cub]"
                              :cub-text="cubTexts[row.left.cub]" :isovalue="activeIso" />
                  <div v-else class="orb-pending">{{ row.leftLabel }}</div>
                </div>
              </div>
              <div class="pair-cell">
                <div class="pair-head">{{ row.rightLabel }}</div>
                <div class="pair-body">
                  <img v-if="row.right && imageData[row.right.cub]" :src="imageData[row.right.cub]"
                       class="pair-img" loading="lazy" decoding="async" @click="openPreview(row.right)" />
                  <CubPreview v-else-if="row.right && cubTexts[row.right.cub]"
                              :cub-text="cubTexts[row.right.cub]" :isovalue="activeIso" />
                  <div v-else class="orb-pending">{{ row.rightLabel || '—' }}</div>
                </div>
              </div>
            </div>

            <!-- 叠加图 / 单独图（适应窗口宽度显示） -->
            <div v-for="p in overlayFor(it)" :key="p.name" class="wide-fig">
              <div class="pair-head">{{ p.title }}</div>
              <img v-if="p.src" :src="p.src" class="wide-img" loading="lazy" decoding="async" @click="openImage(p)" />
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 右：参数 ===== -->
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>{{ $t('分析设置') }}</span></div>
        <div class="ide-pane-body">
          <div class="ide-group">
            <div class="flex-center" style="gap:6px;justify-content:space-between;">
              <span class="label" style="font-weight:400;">{{ $t('数据来源') }}</span>
              <div class="flex-center" style="gap:6px;">
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;"
                        :class="parseMode === 'local' ? 'btn-primary' : 'btn-default'"
                        @click="parseMode = 'local'">{{ $t('本地') }}</button>
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;"
                        :class="parseMode === 'remote' ? 'btn-primary' : 'btn-default'"
                        @click="parseMode = 'remote'" :disabled="!connected">{{ $t('远程') }}</button>
              </div>
            </div>
            <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;">
              {{ parseMode === 'remote' ? (remoteFolder || $t('未选择远程目录')) : (folder || $t('未选择本地文件夹')) }}
            </div>
            <button class="btn" @click="chooseSource">
              {{ parseMode === 'remote' ? $t('选择远程目录') : $t('选择文件夹') }}
            </button>
          </div>

          <!-- 激发态 -->
          <div class="ide-group" v-if="states.length">
            <div class="flex-center" style="justify-content:space-between;">
              <span class="label">{{ $t('激发态（{n}）', { n: states.length }) }}</span>
              <span class="flex-center" style="gap:6px;">
                <button class="btn" style="height:20px;padding:0 8px;font-size:11px;" @click="pickStates('all')">{{ $t('全选') }}</button>
                <button class="btn" style="height:20px;padding:0 8px;font-size:11px;" @click="pickStates('none')">{{ $t('清空') }}</button>
              </span>
            </div>
            <div class="state-list">
              <label v-for="(s, si) in states" :key="si" class="state-row">
                <input type="checkbox" :value="s.order || s.state" v-model="chosenStates" />
                <span class="state-idx" :class="s.spin === 'T' ? 'spin-t' : 'spin-s'">{{ spinLabel(s) }}{{ s.spin_index || s.state }}</span>
                <span class="state-e">{{ fmt(s.energy) }} eV</span>
                <span class="state-f">f={{ (s.f || 0).toFixed(3) }}</span>
              </label>
            </div>
            <div v-if="dupStates" class="rp-hint" style="color:var(--c-warning);">
              {{ $t('该文件里单重态与三重态各自编号（ORCA 的 SOC 输出就是这样）：这里 S 与 T 分开标号，分析按文件顺序序号提交') }}
            </div>
          </div>
          <div v-else-if="statesHint" class="ide-group">
            <div class="rp-hint" style="color:var(--c-warning);">{{ statesHint }}</div>
          </div>

          <WavefnSource
            ref="wf"
            v-model="wavefnPath"
            :source-path="sourcePath"
            :remote-cache="fromRemoteCache"
            :session-id="sessionId"
            :remote-folder="remoteFolder"
            :extra-dir="outDirResolved"
            @blocked="wfBlocked = $event"
            @force-try="run(true)"
            @log="onLog"
          />

          <div class="ide-group">
            <div class="rp-row">
              <span class="label">{{ $t('目标目录') }}</span>
              <span class="flex-center" style="gap:4px;">
                <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="chooseOutDir">{{ $t('选择…') }}</button>
                <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="outDir = ''">{{ $t('默认') }}</button>
              </span>
            </div>
            <div class="rp-hint" style="word-break:break-all;">{{ outDirResolved || $t('未选择') }}</div>
            <div class="rp-row">
              <span class="label">{{ $t('网格质量') }}</span>
              <select class="control rp-num" style="font-size:11px;" v-model.number="grid">
                <option :value="1">{{ $t('低（快）') }}</option>
                <option :value="2">{{ $t('中') }}</option>
                <option :value="3">{{ $t('高（慢）') }}</option>
              </select>
            </div>
            <div class="rp-row">
              <span class="label">{{ $t('等值面') }}</span>
              <input class="control rp-num" type="number" step="0.0005" min="0.0001" v-model.number="activeIso" />
            </div>

            <!-- NTO 专有 -->
            <template v-if="mode === 'nto'">
              <div class="rp-row">
                <span class="label">{{ $t('导出 NTO 对') }}</span>
                <select class="control rp-num" style="font-size:11px;" v-model.number="pairs">
                  <option :value="0">{{ $t('不导出轨道') }}</option>
                  <option :value="1">{{ $t('第 1 对') }}</option>
                  <option :value="2">{{ $t('前 2 对') }}</option>
                  <option :value="3">{{ $t('前 3 对') }}</option>
                </select>
              </div>
              <div class="rp-row">
                <span class="label">{{ $t('NTO 文件格式') }}</span>
                <select class="control rp-num" style="font-size:11px;" v-model="exportFormat">
                  <option value="mwfn">.mwfn</option>
                  <option value="fch">.fch</option>
                  <option value="molden">.molden</option>
                </select>
              </div>
            </template>

            <!-- 空穴-电子专有 -->
            <template v-else>
              <div class="label" style="margin-top:2px;">{{ $t('导出图形数据') }}</div>
              <label v-for="k in exportOptions" :key="k.id" class="rp-check">
                <input type="checkbox" :value="k.id" v-model="exports" /> {{ $t(k.label) }}
              </label>
            </template>

            <div class="rp-row">
              <span class="label">{{ $t('渲染风格') }}</span>
              <select class="control rp-num" style="font-size:11px;" v-model="style">
                <option value="art_noshadow">{{ $t('艺术级（无阴影）') }}</option>
                <option value="art">{{ $t('艺术级（阴影着色）') }}</option>
                <option value="standard">{{ $t('标准') }}</option>
              </select>
            </div>
          </div>

          <div class="ide-group">
            <button class="btn btn-primary" @click="run()"
                    :disabled="running || !sourcePath || !chosenStates.length || wfBlocked">
              {{ running ? $t('分析中…') : (mode === 'nto' ? $t('开始 NTO 分析') : $t('开始空穴-电子分析')) }}
            </button>
            <button v-if="allCubes.length" class="btn" @click="mode === 'nto' ? renderCubes() : renderHeFigures()" :disabled="rendering">
              {{ rendering ? $t('渲染中…') : $t('绘制（VMD）') }}
            </button>
          </div>

          <!-- 只在缺程序时提示（正常时不必占地方显示路径） -->
          <div v-if="missingTools" class="ide-group">
            <div class="rp-hint" style="color:var(--c-warning);">
              {{ $t('没检测到 {0}：可在右上角「外部程序」里指定目录，或把程序所在目录加入系统环境变量 PATH', { 0: missingTools }) }}
            </div>
          </div>
        </div>
      </aside>
    </div>

    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="sessionId"
      :initial-path="browserInitialPath"
      target="excitedFolder"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />
    <LogViewer :lines="logLines" />

    <!-- 页面下方：绘图方法参考 -->
    <DocLinks :links="docLinks" />

    <ImagePreviewModal v-model:visible="previewVisible" :src="previewSrc"
                       :title="mode === 'nto' ? $t('NTO 轨道图') : $t('空穴与电子图')"
                       filename="analysis.png" :initial-dir="outDirResolved" />
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'
import RemoteFileBrowser from '../components/RemoteFileBrowser.vue'
import EmptyNotice from '@/components/EmptyNotice.vue'
import CubPreview from '@/components/CubPreview.vue'
import ImagePreviewModal from '@/components/ImagePreviewModal.vue'
import WavefnSource from '@/components/WavefnSource.vue'
import DocLinks from '@/components/DocLinks.vue'
import { useExternalToolsStore } from '@/stores/externalTools'
import { useMultiwfnCitationStore } from '@/stores/multiwfnCitation'
import { useProgressStore } from '@/stores/progress'
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import { pairRows, spinLabel, stateLabel, ntoNote, heNote } from '@/utils/analysisPairs'
import { cacheGet, cachedWavefn } from '@/utils/fileCache'
import { pickDirectory } from '@/api/dialog'
import { syncRemoteFolder } from '@/api/remoteSync'
import scrollCache from '@/mixins/scrollCache'
import { t as $tr } from '@/i18n'

const LOG_EXTS = ['.log', '.out']

// 空穴-电子分析的指标名（后端给的是 key，这里映射成可翻译的中文标签）
const METRIC_LABELS = {
  energy: '激发能',
  hole_integral: '空穴积分',
  electron_integral: '电子积分',
  Sr: 'Sr 指数（空穴-电子重叠）',
  Sm: 'Sm 指数（空穴-电子重叠）',
  D: 'D 指数（空穴-电子质心距离）',
  delta_sigma: 'Δσ 指数（分布广度之差）',
  H: 'H 指数（平均延展程度）',
  t: 't 指数（分离程度）',
  RMSD_hole: '空穴分布广度 |σ_hole|',
  RMSD_ele: '电子分布广度 |σ_ele|',
  HDI: '空穴离域指数 HDI',
  EDI: '电子离域指数 EDI',
  ghost: 'ghost-hunter 指数',
  dipole_change: '激发前后偶极变化 |Δμ|',
  centroid_hole: '空穴质心',
  centroid_ele: '电子质心'
}

export default {
  name: 'ExcitedAnalysisView',
  components: { LogViewer, RemoteFileBrowser, EmptyNotice, CubPreview, ImagePreviewModal, WavefnSource, DocLinks },
  mixins: [scrollCache],
  props: {
    mode: { type: String, default: 'nto' }        // nto | he
  },
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
      fromRemoteCache: false,
      browserVisible: false,
      browserInitialPath: '/',
      files: [],
      selectedIndex: -1,
      states: [],
      statesHint: '',
      chosenStates: [],
      restoring: false,
      wavefnPath: '',
      wfBlocked: false,
      outDir: '',
      grid: 2,
      iso: 0.02,                // NTO 等值面
      heIso: 0.0005,            // 空穴-电子分析的密度等值面（默认比 NTO 小）
      heCfg: {},                // mls-plots.json 里的 hole_electron（材质/透明模式/等值面默认值）
      _heCfgApplied: false,
      _styleApplied: false,
      pairs: 1,
      exportFormat: 'mwfn',
      exports: ['hole', 'electron'],   // 默认只勾空穴分布 + 电子分布
      style: 'art_noshadow',    // 渲染风格（默认无阴影，可在 mls-plots.json 里改）
      results: [],
      cubTexts: {},
      imageData: {},
      imageFull: {},            // cube 路径 → 原图路径（界面上显示缩略图，点开大图时才读原图）
      overlayImages: [],
      _busy: {},                // 文件路径 → { analyze, render }：每个文件各自的任务状态（可同时跑多个）
      previewVisible: false,
      previewSrc: '',
      _previewKey: '',
      thumbW: 900,              // 界面缩略图最大宽度（原图只在点开大图时才读）
      logLines: [],
      backendUrl: '',
      _fileCache: {},           // 每个输出文件的激发态/结果/图（切回来还在）
    }
  },
  computed: {
    toolsStore() { return useExternalToolsStore() },
    /** 缺失的外部程序（正常时为空串 → 不显示任何提示） */
    missingTools() {
      const miss = []
      if (!this.toolsStore.multiwfnReady) miss.push('Multiwfn')
      if (!this.toolsStore.vmdReady) miss.push('VMD')
      return miss.join(' / ')
    },
    exportOptions() {
      return [
        { id: 'hole', label: '空穴分布' },
        { id: 'electron', label: '电子分布' },
        { id: 'Sr', label: '空穴-电子重叠 Sr' },
        { id: 'CDD', label: '密度差 CDD' },
        { id: 'CholeCele', label: 'Chole / Cele（平滑化）' },
        { id: 'transition', label: '跃迁密度' }
      ]
    },
    sourceFile() { return this.files[this.selectedIndex] || null },
    /** 产物归档用的分子名（取输出文件名，例如 DFMP-PI） */
    moleculeStem() { return (this.sourceFile ? this.sourceFile.name : 'molecule').replace(/\.[^.]+$/, '') },
    sourcePath() { return this.pathOf(this.selectedIndex) },
    /** 当前文件自己的任务状态：别的文件在跑不影响这里的按钮与文字 */
    busyHere() { return this._busy[this.sourcePath] || {} },
    running() { return !!this.busyHere.analyze },
    rendering() { return !!this.busyHere.render },
    outDirResolved() { return this.outDir || this.folder || '' },
    allCubes() {
      const out = []
      this.results.forEach((it) => (it.cubes || []).forEach((c) => out.push({ ...c, state: it.state })))
      return out
    },
    remotePreview() { return this.overlayImages },
    /** 当前模式该用的等值面：NTO 用 iso，电子空穴用 heIso（默认 0.0005） */
    activeIso() {
      return this.mode === 'he' ? this.heIso : this.iso
    },
    /** 空穴-电子叠加参数：等值面用界面上的值，材质/透明模式来自根目录 mls-plots.json */
    hePlot() {
      const c = this.heCfg || {}
      return {
        iso: this.heIso,
        material: c.material || 'Translucent',
        trans_mode: c.trans_mode || 'trans_vmd'
      }
    },
    // ORCA 的 SOC 输出里 S 与 T 各自从 1 编号 → 序号会重复，界面要提醒
    dupStates() {
      const seen = {}
      let dup = false
      this.states.forEach((s) => {
        if (seen[s.state]) dup = true
        seen[s.state] = true
      })
      return dup
    },
    docLinks() {
      return this.mode === 'nto'
        ? [{ label: '使用 Multiwfn 做自然跃迁轨道(NTO)分析（sobereva.com/377）', url: 'http://sobereva.com/377' },
           { label: 'Multiwfn 支持的电子激发分析方法一览（sobereva.com/437）', url: 'http://sobereva.com/437' }]
        : [{ label: '使用 Multiwfn 做空穴-电子分析全面考察电子激发特征（sobereva.com/434）', url: 'http://sobereva.com/434' },
           { label: '图解电子激发的分类（sobereva.com/284）', url: 'http://sobereva.com/284' }]
    }
  },
  activated() {
    this.toolsStore.detect()
    this.loadPlotConfig()
    useProgressStore().setActive(this.sourcePath)   // 回到本页：进度条只显示当前文件的任务
  },
  deactivated() { useProgressStore().setActive('') },
  watch: {
    // 两个页面共用这一个组件：万一路由切换时复用了实例，也要把结果清空（互不串台）
    mode() {
      this.results = []
      this.cubTexts = {}
      this.imageData = {}
      this.imageFull = {}
      this.overlayImages = []
    }
  },
  methods: {
    // 单重态固定 S；三重态或未知都按实际标（Multiwfn/ORCA 输出里读出来的）
    spinLabel(o) { return spinLabel(o) },
    /** S1 / T2 这样的独立标号（S 与 T 各自从 1 数） */
    stateLabel(o) { return stateLabel(o, this.states) },
    /** 该激发态的振子强度（按文件顺序号找） */
    fOf(state) {
      const s = this.states.find((x) => (x.order || x.state) === state)
      return s && s.f != null ? Number(s.f) : null
    },
    /** 图片右下角标注：Hole/Electron + NTO 对序号 + 贡献值 + 该态的振子强度 */
    ntoNote(item, cube) { return ntoNote(item, cube, this.states) },
    /** 图片右下角标注：该态的 Sr 与 D 指数 */
    heNote(item) { return heNote(item, this.states) },
    /** 把 cube 按物理含义成对摆放：NTO=占据/空，空穴-电子=Hole/Electron、Chole/Cele */
    pairRows(it) { return pairRows(this.mode, it, this.$t) },
    /** 该激发态的叠加图（一次 VMD 渲染出来的整图，按状态标号对应） */
    overlayFor(it) {
      const label = this.stateLabel(it)
      return this.overlayImages
        .filter((p) => p.name && p.name.indexOf(`-${label}-`) >= 0)
        .map((p) => ({ ...p, title: `${this.moleculeStem} ${label} — Hole + Electron（${this.$t('空穴 + 电子叠加图')}）` }))
    },
    onLog({ text, color }) { this.addLog(text, color) },
    /** 读根目录 mls-plots.json 里的空穴-电子参数与默认渲染风格（只覆盖默认值，用户改过的不动） */
    async loadPlotConfig() {
      const { ok, data } = await this.api('/api/ext/defaults', 'GET')
      if (!ok || !data) return
      const he = data.hole_electron || (data.config || {}).hole_electron || null
      if (he) {
        this.heCfg = he
        if (!this._heCfgApplied) {
          const v = Number(he.iso)
          if (isFinite(v) && v > 0) this.heIso = v
          this._heCfgApplied = true
        }
      }
      if (data.style && !this._styleApplied) {
        this.style = data.style
        this._styleApplied = true
      }
    },
    fmt(v) {
      if (v === undefined || v === null || Number.isNaN(v)) return '—'
      return Math.abs(v) >= 1000 ? String(v) : Number(v).toFixed(4).replace(/0+$/, '').replace(/\.$/, '')
    },
    baseName(p) { return String(p || '').split(/[\\/]/).pop() },
    /** 第 idx 个文件的完整路径 */
    pathOf(idx) {
      const f = this.files[idx]
      if (!f || !this.folder) return ''
      const sep = this.folder.includes('\\') ? '\\' : '/'
      return `${this.folder.replace(/[\\/]+$/, '')}${sep}${f.name}`
    },
    /** 左侧列表里标出该文件正在做什么（允许多个文件同时跑） */
    fileBusy(f, idx) {
      const b = this._busy[this.pathOf(idx)]
      if (!b) return ''
      const parts = []
      if (b.analyze) parts.push(this.$t('分析中…'))
      if (b.render) parts.push(this.$t('渲染中…'))
      return parts.join(' / ')
    },
    /** 记下/清除某个文件的任务状态（每个文件各记各的） */
    setBusy(path, kind, val) {
      if (!path) return
      const cur = { ...(this._busy[path] || {}) }
      cur[kind] = !!val
      this._busy = { ...this._busy, [path]: cur }
    },
    metricLabel(m) {
      const zh = METRIC_LABELS[m.key]
      return zh ? this.$t(zh) : m.label
    },
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      if (this.logLines.length > 300) this.logLines.shift()
    },
    async ensureBackend() {
      if (this.backendUrl) return this.backendUrl
      if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
        try { this.backendUrl = await window.electronAPI.getBackendUrl() } catch (e) { /* ignore */ }
      }
      if (!this.backendUrl) this.backendUrl = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
      return this.backendUrl
    },
    async api(path, method = 'GET', body = null, params = null) {
      const base = await this.ensureBackend()
      const qs = params ? '?' + new URLSearchParams(params).toString() : ''
      const resp = await fetch(`${base}${path}${qs}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined
      })
      const text = await resp.text()
      let data = {}
      if (text) { try { data = JSON.parse(text) } catch (e) { data = { detail: text.slice(0, 300) } } }
      return { ok: resp.ok, data }
    },

    // ===== 选文件 =====
    async chooseSource() {
      if (this.parseMode === 'remote') {
        if (!this.connected) { this.addLog($tr('请先连接服务器'), '#ffa500'); return }
        this.browserInitialPath = `/home/${this.username}` || '/'
        this.browserVisible = true
        return
      }
      try {
        const p = await pickDirectory(this.$t('选择含激发态输出的文件夹'), this.folder)
        if (!p) return
        this.folder = p
        this.fromRemoteCache = false
        await this.loadFiles()
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    async onBrowserSelect({ path, is_dir }) {
      if (!path) return
      this.remoteFolder = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
      this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      try {
        const { cacheDir, count } = await syncRemoteFolder(this.sessionId, this.remoteFolder, '.log')
        this.addLog($tr('已同步 {0} 个 .log → {1}', { 0: count, 1: cacheDir }), '#87d2ff')
        this.folder = cacheDir
        this.fromRemoteCache = true
        await this.loadFiles()
      } catch (e) {
        this.addLog($tr('远程解析失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    async loadFiles() {
      const { ok, data } = await this.api('/api/local/ls', 'POST', { path: this.folder })
      if (!ok) { this.addLog($tr('读取目录失败: {0}', { 0: data.detail }), '#ff6b6b'); return }
      this.files = (data.entries || [])
        .filter((e) => !e.is_dir && LOG_EXTS.some((x) => e.name.toLowerCase().endsWith(x)))
        .map((e) => ({ name: e.name, size: e.size }))
      this.selectedIndex = -1
      this.states = []
      this.chosenStates = []
      this.results = []
      useProgressStore().setActive('')
      this.addLog($tr('找到 {0} 个激发态输出文件', { 0: this.files.length }), '#87d2ff')
    },
    async selectFile(idx) {
      // 每个文件的激发态、分析结果与图各自缓存：切回来还能看到之前的结果（分析很耗时）
      this.restoring = true
      const gp = useProgressStore()
      this.cacheCurrent()
      this.selectedIndex = idx
      const myIdx = idx
      const gpKey = this.sourcePath + '|restore'
      gp.setActive(this.sourcePath)          // 进度条从此只显示这个文件自己的任务
      gp.start($tr('正在恢复先前解析的内容……'), gpKey)
      this.results = []
      this.cubTexts = {}
      this.imageData = {}
      this.imageFull = {}
      this.overlayImages = []
      this.states = []
      this.statesHint = ''
      this.chosenStates = []
      // 波函数选择必须跟着文件换：缓存里有就用该文件自己的，没有就清空让组件重新自动查找
      const cached = cacheGet(this._fileCache, this.sourcePath)
      this.wavefnPath = cachedWavefn(this._fileCache, this.sourcePath)
      // 等这一轮渲染把新的 source-path / v-model 传给 WavefnSource 之后再让它预检
      await this.$nextTick()
      await this.$refs.wf.reload()
      if (cached && cached.results && cached.results.length) {
        this.restoreCache(cached)
        this.addLog($tr('恢复 {0} 之前的分析结果', { 0: cached.states.length }), '#87d2ff')
      }
      const { ok, data } = await this.api('/api/analysis/states', 'GET', null,
        { path: this.sourcePath, wavefn: this.wavefnPath || '' })
      if (this.selectedIndex === myIdx) this.restoring = false
      gp.hide(gpKey)                          // 只结束"恢复"这一个任务（别的文件/别的任务照旧显示）
      if (this.selectedIndex !== myIdx) return   // 期间用户又切走了，结果留给那次切换处理
      if (!ok) { this.addLog($tr('读取激发态失败: {0}', { 0: data.detail }), '#ff6b6b'); return }
      if (!this.states.length) this.states = data.states || []
      this.statesHint = data.hint || ''
      this.addLog($tr('激发态: {0} 个（{1}）', { 0: this.states.length, 1: data.kind || '—' }), '#87d2ff')
    },
    /** 缓存当前文件的激发态/勾选/结果/图/波函数选择 */
    cacheCurrent() {
      const key = this.sourcePath
      if (!key) return
      this._fileCache[key] = {
        states: this.states,
        statesHint: this.statesHint,
        chosenStates: [...this.chosenStates],
        results: this.results,
        cubTexts: this.cubTexts,
        imageData: this.imageData,
        imageFull: this.imageFull,
        overlayImages: this.overlayImages,
        wavefnPath: this.wavefnPath
      }
    },
    restoreCache(c) {
      this.states = c.states || []
      this.statesHint = c.statesHint || ''
      this.chosenStates = [...(c.chosenStates || [])]
      this.results = c.results || []
      this.cubTexts = c.cubTexts || {}
      this.imageData = c.imageData || {}
      this.imageFull = c.imageFull || {}
      this.overlayImages = c.overlayImages || []
    },
    pickStates(what) {
      this.chosenStates = what === 'all' ? this.states.map((s) => s.order || s.state) : []
    },
    async chooseOutDir() {
      try {
        const p = await pickDirectory(this.$t('选择分析结果输出目录'), this.outDirResolved)
        if (p) this.outDir = p
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 运行分析 =====
    async run(force = false) {
      if (!this.sourcePath) { this.addLog($tr('请先选择激发态输出文件'), '#ffa500'); return }
      if (!this.chosenStates.length) { this.addLog($tr('请先勾选要分析的激发态'), '#ffa500'); return }
      if (!this.toolsStore.multiwfnReady) {
        this.addLog($tr('没检测到 Multiwfn：请先在右上角「外部程序」里指定目录'), '#ffa500')
        return
      }
      if (!force && this.wfBlocked) {
        const local = await this.$refs.wf.ensureRemote()
        if (local) this.wavefnPath = local
      }
      // 使用 Multiwfn 前必须先确认引用说明（可勾选不再提示）
      const citation = useMultiwfnCitationStore()
      await citation.require(this.mode === 'he' ? 'hole-electron' : 'nto')

      this.setBusy(this.sourcePath, 'analyze', true)
      const url = this.mode === 'nto' ? '/api/analysis/nto' : '/api/analysis/hole-electron'
      const payload = {
        source: this.sourcePath,
        wavefn: this.wavefnPath,
        out_dir: this.outDirResolved,
        folder_name: this.moleculeStem,
        states: this.chosenStates.map(Number).sort((a, b) => a - b),
        grid: this.grid,
        multiwfn_dir: this.toolsStore.multiwfnDir
      }
      if (this.mode === 'nto') {
        payload.pairs = this.pairs
        payload.export_format = this.exportFormat
      } else {
        payload.exports = this.exports
      }
      // 逐态调用：既能显示最下方的进度条，也能边算边看到结果
      const gp = useProgressStore()
      const states = payload.states
      // 解析很耗时，期间用户可能切到别的文件：结果一律按开始时的文件（runKey）归属，
      // 只有 runKey 还是当前文件才直接显示，否则写进那个文件自己的缓存，绝不串到别的分子上
      const runKey = this.sourcePath
      const gpKey = runKey + '|analyze'
      const labels = states.map((s) => this.stateLabel({ state: s, order: s }))
      const acc = []
      let outDir = ''
      for (let i = 0; i < states.length; i++) {
        gp.step(i, states.length, $tr('Multiwfn 分析 {0}（{1}/{2}）', {
          0: labels[i], 1: i + 1, 2: states.length
        }), gpKey)
        this.addLog($tr('调用 Multiwfn 分析 {0}（{1}/{2}）…', { 0: labels[i], 1: i + 1, 2: states.length }), '#87d2ff')
        const one = { ...payload, states: [states[i]] }
        const { ok, data } = await this.api(url, 'POST', one)
        if (!ok) {
          this.addLog($tr('分析失败: {0}', { 0: data.detail }), '#ff6b6b')
          continue
        }
        acc.push(...(data.items || []))
        this.setRunResults(runKey, acc)
        outDir = data.out_dir || outDir
        if (data.log) String(data.log).split('\n').forEach((l) => this.addLog(l, '#9aa3ad'))
        if (data.hint) this.addLog(data.hint, '#ff6b6b')
      }
      this.setBusy(runKey, 'analyze', false)
      const cubes = []
      acc.forEach((it) => (it.cubes || []).forEach((c) => cubes.push({ ...c, state: it.state })))
      this.addLog($tr('分析完成：{0} 个激发态，{1} 个 cube → {2}', { 0: acc.length, 1: cubes.length, 2: outDir }),
        '#7cfc00')
      let k = 0
      const pick = cubes.slice(0, 8)
      const texts = {}
      for (const c of pick) {
        const r = await this.api('/api/ext/read-cub', 'POST', { path: c.cub })
        if (r.ok) texts[c.cub] = r.data.text
        k++
        gp.step(k, pick.length || 1, $tr('读取 cube {0}/{1}', { 0: k, 1: pick.length }), gpKey)
      }
      this.setRunCubTexts(runKey, texts)
      gp.finish($tr('分析完成：{0} 个激发态', { 0: acc.length }), gpKey)
      // 始终停在同一个文件才写回当前状态；已经切走了就别覆盖别人（结果早已存进 runKey 的缓存）
      if (!runKey || runKey === this.sourcePath) this.cacheCurrent()
    },
    /** 分析结果写回：还停在这个文件就直接显示，已经切走了就存进那个文件自己的缓存 */
    setRunResults(runKey, items) {
      if (!runKey || runKey === this.sourcePath) { this.results = items.slice(); return }
      const c = cacheGet(this._fileCache, runKey) || {}
      c.results = items.slice()
      this._fileCache[runKey] = c
    },
    /** cube 文本同理：按解析开始时的文件归属 */
    setRunCubTexts(runKey, texts) {
      if (!runKey || runKey === this.sourcePath) { this.cubTexts = { ...this.cubTexts, ...texts }; return }
      const c = cacheGet(this._fileCache, runKey) || {}
      c.cubTexts = { ...(c.cubTexts || {}), ...texts }
      this._fileCache[runKey] = c
    },

    // ===== 渲染 =====
    async renderCubes() {
      if (!this.toolsStore.vmdReady) {
        this.addLog($tr('没检测到 VMD：请先在右上角「外部程序」里指定目录'), '#ffa500')
        return
      }
      // 渲染期间可能切文件：cube 列表与归属文件先固定下来，结果按 cacheKey 写回
      const cacheKey = this.sourcePath
      const gpKey = cacheKey + '|render'
      const gp = useProgressStore()
      this.setBusy(cacheKey, 'render', true)
      gp.start($tr('VMD 渲染 {0} 张图…', { 0: this.allCubes.length }), gpKey)
      const cubes = this.allCubes.slice()
      const results = this.results.slice()
      const states = this.states.slice()
      this.addLog($tr('调用 VMD 渲染 {0} 张图…', { 0: cubes.length }), '#87d2ff')
      const { ok, data } = await this.api('/api/ext/render', 'POST', {
        out_dir: this.outDirResolved,
        folder_name: this.moleculeStem + '-NTOs',
        items: cubes.map((c, i) => ({
          orbital: i,
          cub: c.cub,
          note: this.mode === 'nto' ? ntoNote(c, c, states)
                                    : heNote(results.find((r) => r.state === c.state) || { state: c.state }, states)
        })),
        vmd_dir: this.toolsStore.vmdDir,
        iso: this.iso,
        style: this.style
      })
      this.setBusy(cacheKey, 'render', false)
      if (!ok) {
        gp.hide(gpKey)
        this.addLog($tr('VMD 渲染失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      if (data.log) String(data.log).split('\n').forEach((l) => this.addLog(l, '#9aa3ad'))
      const done = (data.items || []).filter((i) => i.ok)
      const collected = {}
      const full = {}
      let n = 0
      for (const it of done) {
        const c = cubes[it.orbital]
        if (!c) continue
        const r = await this.api('/api/ext/read-image', 'POST', { path: it.image, max_w: this.thumbW })
        if (r.ok) {
          collected[c.cub] = `data:${r.data.mime};base64,${r.data.base64}`
          full[c.cub] = it.image
        }
        n++
        gp.step(n, done.length || 1, $tr('读取渲染图 {0}/{1}', { 0: n, 1: done.length }), gpKey)
      }
      this.applyRenderResult(cacheKey, collected, [], full)
      gp.finish($tr('已渲染 {0} 张图', { 0: done.length }), gpKey)
      this.addLog($tr('已渲染 {0} 张图 → {1}', { 0: done.length, 1: data.out_dir }), '#7cfc00')
    },
    /** 空穴-电子分析：一次把「单图 + 叠加图」都画出来（只有 Chole/Cele 等值面透明，其余不透明） */
    async renderHeFigures() {
      if (!this.toolsStore.vmdReady) {
        this.addLog($tr('没检测到 VMD：请先在右上角「外部程序」里指定目录'), '#ffa500')
        return
      }
      const cacheKey = this.sourcePath
      const gpKey = cacheKey + '|render'
      const gp = useProgressStore()
      // 渲染很慢，期间可能切文件：结果、分子名、输出目录先固定下来，图按 cacheKey 写回
      const resultsSnap = this.results.slice()
      const statesSnap = this.states.slice()
      const stem = this.moleculeStem
      const outDir = this.outDirResolved
      const he = this.hePlot
      this.setBusy(cacheKey, 'render', true)
      gp.start($tr('VMD 渲染 {0} 张图…', { 0: resultsSnap.length }), gpKey)
      const collected = {}          // cube 路径 → dataURL（最后按 cacheKey 归属写回，切文件也不会串）
      const full = {}               // cube 路径 → 原图路径
      const overlays = []
      // 只有平滑化的 Chole / Cele（以及它们的叠加图）用半透明等值面：质心球要能看见；
      // 其余图（hole/electron/Sr/CDD/跃迁密度/Hole+Electron）保持不透明，层次更清楚
      const transOf = (tag) => tag === 'Chole' || tag === 'Cele' || tag === 'Chole+Cele'
      const figOf = (label, cub1, cub2, spheres, tag, text) => ({
        label, cub1, cub2, spheres, note: text,
        transparent: transOf(tag),
        material: transOf(tag) ? he.material : 'Glossy'
      })
      const kinds = [
        ['hole', 'hole'], ['electron', 'electron'],
        ['Chole', 'Chole'], ['Cele', 'Cele'],
        ['Sr', 'Sr'], ['CDD', 'CDD'], ['transition', 'transition']
      ]
      let made = 0
      for (let i = 0; i < resultsSnap.length; i++) {
        const it = resultsSnap[i]
        const by = {}
        ;(it.cubes || []).forEach((c) => { by[c.kind] = c.cub })
        const m = {}
        ;(it.metrics || []).forEach((r) => { m[r.key] = r })
        const ch = (m.centroid_hole || {}).vec
        const ce = (m.centroid_ele || {}).vec
        const figs = []
        const lab = stateLabel(it, statesSnap)
        const note = heNote(it, statesSnap)
        kinds.forEach(([kind, tag]) => {
          if (!by[kind]) return
          // 电荷中心只标在 Chole / Cele 上（hole/electron 单图不加）
          const spheres = []
          if (ch && kind === 'Chole') spheres.push([...ch, 'purple'])
          if (ce && kind === 'Cele') spheres.push([...ce, 'orange'])
          figs.push(figOf(`${stem}-${lab}-${tag}`, by[kind], '', spheres, tag, `${note}  ${tag}`))
        })
        // 叠加图：Hole+Electron（不透明）+ Chole+Cele（透明，标两个电荷中心）
        if (by.hole && by.electron) {
          figs.push(figOf(`${stem}-${lab}-Hole+Electron`, by.hole, by.electron, [],
                          'Hole+Electron', `${note}  Hole+Electron`))
        }
        if (by.Chole && by.Cele) {
          const spheres = []
          if (ch) spheres.push([...ch, 'purple'])
          if (ce) spheres.push([...ce, 'orange'])
          figs.push(figOf(`${stem}-${lab}-Chole+Cele`, by.Chole, by.Cele, spheres,
                          'Chole+Cele', `${note}  Chole+Cele`))
        }
        if (figs.length) {
          gp.step(i, resultsSnap.length,
                  $tr('VMD 渲染 {0}（{1}/{2}）', { 0: lab, 1: i + 1, 2: resultsSnap.length }), gpKey)
          const { ok, data } = await this.api('/api/analysis/overlay', 'POST', {
            out_dir: outDir, folder_name: stem + '-HoleElectron',
            pairs: figs, iso: he.iso, style: this.style,
            material: he.material, trans_mode: he.trans_mode,   // 每张图自己带 透明/材质
            vmd_dir: this.toolsStore.vmdDir
          })
          if (!ok) { this.addLog($tr('渲染失败: {0}', { 0: data.detail }), '#ff6b6b'); continue }
          if (data.log) String(data.log).split('\n').forEach((l) => this.addLog(l, '#9aa3ad'))
          for (const r2 of (data.items || []).filter((x) => x.ok)) {
            const tag = String(r2.label || '').split('-').pop()
            const cub = by[tag]
            const rr = await this.api('/api/ext/read-image', 'POST', { path: r2.image, max_w: this.thumbW })
            const src = rr && rr.ok ? `data:${rr.data.mime};base64,${rr.data.base64}` : ''
            if (cub && src) {
              collected[cub] = src
              full[cub] = r2.image                      // 原图路径：点开大图时才读
            }
            // 叠加图单独列出（没有对应的单个 cube）
            if ((tag === 'Chole+Cele' || tag === 'Hole+Electron') && src) {
              overlays.push({ name: r2.name, path: r2.image, src })
            }
            made++
          }
        }
      }
      this.setBusy(cacheKey, 'render', false)
      gp.finish($tr('已渲染 {0} 张图', { 0: made }), gpKey)
      this.addLog($tr('已渲染 {0} 张图 → {1}', { 0: made, 1: outDir }), '#7cfc00')
      this.applyRenderResult(cacheKey, collected, overlays, full)
    },
    /** 渲染结果写回：按开始绘制时的文件归属写（中途切文件也不会把图串到别的分子上） */
    applyRenderResult(cacheKey, collected, overlays, full = {}) {
      if (cacheKey && cacheKey !== this.sourcePath) {
        const c = cacheGet(this._fileCache, cacheKey) || {}
        c.imageData = { ...(c.imageData || {}), ...collected }
        c.imageFull = { ...(c.imageFull || {}), ...full }
        c.overlayImages = (c.overlayImages || [])
          .filter((p) => !overlays.some((o) => o.name === p.name))
          .concat(overlays)
        this._fileCache[cacheKey] = c
        this.addLog($tr('绘制完成（结果已存到该文件自己的缓存里）'), '#7cfc00')
        return
      }
      Object.assign(this.imageData, collected)
      Object.assign(this.imageFull, full)
      const merged = this.overlayImages.filter((p) => !overlays.some((o) => o.name === p.name)).concat(overlays)
      this.overlayImages = merged
      this.cacheCurrent()
    },
    /** 点开大图：先用界面上的缩略图立即显示，再把原图读进来替换（原图只在需要时才传） */
    async openFull(key, fullPath, thumbSrc) {
      if (!thumbSrc && !fullPath) return
      this.previewSrc = thumbSrc || ''
      this._previewKey = key
      this.previewVisible = true
      if (!fullPath) return
      const r = await this.api('/api/ext/read-image', 'POST', { path: fullPath })
      if (r.ok && this.previewVisible && this._previewKey === key) {
        this.previewSrc = `data:${r.data.mime};base64,${r.data.base64}`
      }
    },
    openPreview(c) {
      this.openFull(c.cub, this.imageFull[c.cub] || '', this.imageData[c.cub])
    },
    openImage(p) {
      this.openFull(p.name || p.path, p.path || '', p.src)
    }
  }
}
</script>

<style scoped>
.ana-block {
  border: 1px solid var(--c-border-soft);
  background: var(--c-panel);
  margin-bottom: 10px;
  padding: 8px 10px;
}
.ana-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px; }
.ana-title { font-size: 14px; font-weight: 700; color: var(--c-accent); }
/* S 态红、T 态蓝 */
.spin-s { color: #cf3b34 !important; }
.spin-t { color: #2b6fd4 !important; }
.ana-err { font-size: 12px; color: var(--c-danger); }
/* 左侧列表里"该文件正在分析/绘制"的小标记（允许多个文件同时跑） */
.ana-busy {
  margin-left: 6px; padding: 0 4px; font-size: 11px;
  color: var(--c-accent); border: 1px solid var(--c-border-soft);
}
.ana-sub { font-size: 12px; color: var(--c-text-2); margin: 4px 0; word-break: break-all; }
.ana-table { width: 100%; border-collapse: collapse; font-size: 12.5px; margin: 4px 0; }
.ana-table th { text-align: left; border-bottom: 1px solid var(--c-border); padding: 3px 6px; }
.ana-k { color: var(--c-text-2); padding: 3px 6px; }
.ana-v { text-align: right; padding: 3px 6px; font-family: Consolas, monospace; }
.ana-top .ana-k, .ana-top .ana-v { font-weight: 700; color: var(--c-accent); }
.state-list { max-height: 190px; overflow: auto; border: 1px solid var(--c-border-soft); }
.state-row {
  display: flex; align-items: center; gap: 6px;
  padding: 2px 6px; font-size: 12px; cursor: pointer;
}
.state-row:hover { background: var(--c-hover); }
.state-idx { width: 34px; font-weight: 600; }
.state-e { width: 84px; font-family: Consolas, monospace; }
.state-f { color: var(--c-text-3); }

/* 成对图形：一左一右，各自带标题栏，图片按窗口宽度自适应 */
.pair-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 6px 0;
}
.pair-cell { display: flex; flex-direction: column; min-width: 0; }
.pair-head {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  background: var(--c-panel);
  border: 1px solid var(--c-border-soft);
  border-bottom: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pair-body {
  position: relative;
  height: 260px;
  border: 1px solid var(--c-border-soft);
  background: #fff;
  overflow: hidden;
}
.pair-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: zoom-in;
  display: block;
}
.wide-fig { margin: 6px 0; }
.wide-img {
  width: 100%;
  max-height: 62vh;
  object-fit: contain;
  border: 1px solid var(--c-border-soft);
  background: #fff;
  cursor: zoom-in;
  display: block;
}
</style>

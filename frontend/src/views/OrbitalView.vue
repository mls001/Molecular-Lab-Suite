<template>
  <!-- PyCharm 风格三栏：左=文件列表 / 中=轨道能级表 / 右=解析设置与能隙计算 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- ===== 左：文件列表 ===== -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>{{ $t('文件列表') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ allData.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!allData.length" class="ide-empty">{{ $t('暂无文件') }}<br>{{ $t('请先在右侧选择文件夹并解析') }}</div>
          <div
            v-for="(item, idx) in allData"
            :key="idx"
            class="ide-list-item"
            :class="{ active: selectedIndex === idx }"
            @click="selectFile(idx)"
          >
            {{ item.filename }}
            <!-- 该文件正在生成 cube / 绘制（可同时跑多个文件，切走也不影响） -->
            <span v-if="fileBusy(idx)" class="orb-busy">{{ fileBusy(idx) }}</span>
          </div>
        </div>
      </aside>

      <!-- ===== 中：轨道能级表 ===== -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>{{ $t('轨道能级') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">
            {{ allData.length && allData[selectedIndex] ? allData[selectedIndex].filename : '—' }}
          </span>
        </div>
        <div class="flex-col flex-1 min-h-0" style="overflow:hidden;padding:8px 12px 0;">
          <div style="flex-shrink:0;padding:0 0 6px 0;">
            <div v-if="restoring" style="font-size:13px;color:var(--c-accent);font-weight:600;">{{ $t('正在恢复先前解析的内容……') }}</div>
            <div v-else-if="currentTableData.length" style="font-size:13px;color:var(--c-text-2);">{{ $t('共 {n} 条轨道', { n: currentTableData.length }) }}</div>
          </div>
          <div ref="tableContainer" style="flex:1;overflow:auto;padding:0 0 12px 0;">
            <table v-if="currentTableData.length" style="width:100%;border-collapse:collapse;font-size:13px;">
              <thead style="position:sticky;top:0;background:var(--c-panel);z-index:10;">
                <tr>
                  <th style="padding:6px 6px;border-bottom:1px solid var(--c-border);text-align:center;width:26px;">
                    <input type="checkbox" :checked="allChecked" @change="toggleAllOrbitals($event.target.checked)" />
                  </th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:left;">{{ $t('自旋') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:left;">{{ $t('类型') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('轨道序号') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('能量 (Ha)') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('能量 (eV)') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('标记') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, rIdx) in currentTableData"
                  :key="rIdx"
                  :class="{ 'row-homo': row.isHOMO, 'row-lumo': row.isLUMO }"
                  :style="row.isHOMO ? 'background:var(--c-homo-row);' : row.isLUMO ? 'background:var(--c-lumo-row);' : ''"
                >
                  <td style="padding:5px 6px;border-bottom:1px solid var(--c-hover);text-align:center;">
                    <input type="checkbox" :value="Number(row.index)" v-model="selectedOrbitals" />
                  </td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);">{{ row.spin }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);">{{ row.type }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;">{{ row.index }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;">{{ row.energy_ha }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;">{{ row.energy_ev }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;font-weight:bold;">
                    <span v-if="row.isHOMO" style="color:var(--c-homo);">HOMO</span>
                    <span v-else-if="row.isLUMO" style="color:var(--c-lumo);">LUMO</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <EmptyNotice
              v-else-if="parsedOnce"
              :text="$t('该文件内不含轨道能量信息')"
              :hint="noticeHint"
            />
            <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--c-text-3);font-size:14px;">
              {{ $t('请选择文件夹并等待解析完成') }}
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 右：解析设置 + 能隙计算 ===== -->
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>{{ $t('解析设置') }}</span></div>
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
              {{ parseMode === 'remote' ? (remoteFolder || $t('未选择远程目录（含 .log）')) : (folder || $t('未选择本地文件夹')) }}
            </div>
            <button class="btn" @click="chooseParseSource">{{ parseMode === 'remote' ? $t('选择远程目录') : $t('选择文件夹') }}</button>
            <button class="btn btn-primary" @click="runParse" :disabled="running || !(parseMode === 'remote' ? remoteFolder : folder)">
              {{ running ? $t('解析中...') : $t('解析 / 重新解析') }}
            </button>
            <div class="flex" style="gap:6px;">
              <button v-if="allData.length" class="btn" style="flex:1;" @click="exportCSV">{{ $t('导出 CSV') }}</button>
              <button v-if="allData.length" class="btn" style="flex:1;" @click="exportExcel">{{ $t('导出 Excel') }}</button>
            </div>
          </div>
          <div class="ide-group">
            <span class="label">{{ $t('能隙计算') }}</span>
            <div class="flex-center" style="gap:6px;">
              <span style="font-size:12px;">A</span>
              <input v-model.number="gapIndexA" type="number" min="1" class="control" style="flex:1;min-width:0;height:28px;" :placeholder="$t('轨道 A 序号')" />
              <span style="font-size:12px;">B</span>
              <input v-model.number="gapIndexB" type="number" min="1" class="control" style="flex:1;min-width:0;height:28px;" :placeholder="$t('轨道 B 序号')" />
            </div>
            <button class="btn" @click="calcGap" :disabled="!currentTableData.length">{{ $t('计算能隙') }}</button>
            <div v-if="gapResult" style="font-weight:700;font-size:13px;color:var(--c-accent);">{{ gapResult }}</div>
            <div v-if="gapError" style="color:var(--c-danger);font-size:13px;">{{ gapError }}</div>
          </div>

          <!-- 轨道图：Multiwfn 生成 cub → VMD 渲染 -->
          <div class="ide-group">
            <span class="label">{{ $t('轨道图') }}</span>
            <!-- 只在缺程序时提示（正常时不必占地方显示路径） -->
            <div v-if="missingTools" class="rp-hint" style="color:var(--c-warning);">
              {{ $t('没检测到 {0}：可在右上角「外部程序」里指定目录，或把程序所在目录加入系统环境变量 PATH', { 0: missingTools }) }}
            </div>
            <!-- 波函数来源：与 NTO / 空穴-电子页共用同一个组件 -->
            <WavefnSource
              ref="wf"
              v-model="wavefnPath"
              :source-path="sourceLogPath"
              :remote-cache="fromRemoteCache"
              :session-id="sessionId"
              :remote-folder="remoteFolder"
              :extra-dir="cubDirResolved"
              @blocked="wfBlocked = $event"
              @force-try="makeCubs(true)"
              @log="onWfLog"
            />
            <div class="rp-row">
              <span class="label">{{ $t('目标目录') }}</span>
              <span class="flex-center" style="gap:4px;">
                <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="chooseCubDir">{{ $t('选择…') }}</button>
                <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="cubDir = defaultCubDir">{{ $t('默认') }}</button>
              </span>
            </div>
            <div class="rp-hint">{{ cubDir || defaultCubDir || $t('未选择') }}</div>
            <div class="rp-row">
              <span class="label">{{ $t('网格质量') }}</span>
              <select class="control rp-num" style="font-size:11px;" v-model.number="cubGrid">
                <option :value="1">{{ $t('低（快）') }}</option>
                <option :value="2">{{ $t('中') }}</option>
                <option :value="3">{{ $t('高（慢）') }}</option>
              </select>
            </div>
            <div class="rp-row">
              <span class="label">{{ $t('等值面') }}</span>
              <input class="control rp-num" type="number" step="0.005" min="0.001" v-model.number="isoValue" />
            </div>
            <div class="rp-row">
              <span class="label">{{ $t('渲染风格') }}</span>
              <select class="control rp-num" style="font-size:11px;" v-model="renderStyle">
                <option value="art_noshadow">{{ $t('艺术级（无阴影）') }}</option>
                <option value="art">{{ $t('艺术级（阴影着色）') }}</option>
                <option value="standard">{{ $t('标准') }}</option>
              </select>
            </div>
            <div class="flex" style="gap:6px;">
              <button class="btn btn-primary" style="flex:1;" @click="makeCubs()"
                      :disabled="orbBusy || !selectedOrbitals.length || !sourceLogPath || wfBlocked">
                {{ cubBusy ? $t('生成中…') : $t('生成 cub（{n}）', { n: selectedOrbitals.length }) }}
              </button>
              <button class="btn btn-success" style="flex:1;" @click="renderCubs"
                      :disabled="orbBusy || !cubItems.length">
                {{ vmdBusy ? $t('渲染中…') : $t('绘制（VMD）') }}
              </button>
            </div>
            <div v-if="!sourceLogPath" class="rp-hint" style="color:var(--c-warning);">{{ $t('请先在左侧选择已解析的 LOG 文件') }}</div>
            <div v-if="cubItems.length" class="rp-hint">{{ $t('已生成 {0} 个 cube', { 0: cubItems.length }) }}</div>
            <label class="rp-check">
              <input type="checkbox" v-model="showScripts" /> {{ $t('编辑脚本模板') }}
            </label>
            <template v-if="showScripts">
              <div class="flex-col" style="gap:3px;">
                <span class="label">Multiwfn</span>
                <textarea class="control" style="width:100%;height:62px;font-size:11px;padding:4px;" v-model="cubScriptText" :placeholder="$t('留空用默认：200/3/{orb}/{grid}/1（末尾自动补 0、q 正常退出）')"></textarea>
              </div>
              <div class="flex-col" style="gap:3px;">
                <span class="label">VMD</span>
                <textarea class="control" style="width:100%;height:62px;font-size:11px;padding:4px;" v-model="vmdScriptText" :placeholder="$t('留空用默认：mol new {cub} / Isosurface {iso} / render Tachyon {scene}')"></textarea>
              </div>
              <button class="btn" style="height:22px;font-size:11px;" @click="cubScriptText = ''; vmdScriptText = ''">{{ $t('恢复默认脚本') }}</button>
            </template>
          </div>

          <!-- 轨道预览（渲染好的 VMD 图优先，其次 3Dmol 实时等值面） -->
          <div v-if="previews.length" class="ide-group">
            <span class="label">{{ $t('轨道预览') }}</span>
            <div class="orb-grid">
              <div v-for="p in previews" :key="p.orbital" class="orb-cell" @click="openPreview(p)">
                <img v-if="p.imageData" :src="p.imageData" class="orb-img" loading="lazy" decoding="async" />
                <CubPreview v-else-if="p.cubText" :cub-text="p.cubText" :label="p.label" :isovalue="isoValue" />
                <div v-else class="orb-pending">{{ p.label }}<br />{{ $t('等待 cube…') }}</div>
              </div>
            </div>
            <div v-if="cubItems.length > previews.length" class="rp-hint">
              {{ $t('只预览前 {0} 个轨道', { 0: previews.length }) }}
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 远程文件浏览器（远程模式选目录） -->
    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="sessionId"
      :initial-path="browserInitialPath"
      :target="browserTarget"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />

    <LogViewer :lines="logLines" />

    <!-- 页面下方：绘图方法参考 -->
    <DocLinks :links="docLinks" />

    <!-- 轨道图放大预览 -->
    <ImagePreviewModal
      v-model:visible="previewVisible"
      :src="previewSrc"
      :title="$t('轨道图')"
      filename="orbital.png"
      :initial-dir="cubDirResolved"
    />
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
import { cachedList, cachedMap, cachedWavefn, cacheGet } from '@/utils/fileCache'
import scrollCache from '@/mixins/scrollCache'
import { pickDirectory } from '@/api/dialog'
import { syncRemoteFolder } from '@/api/remoteSync'
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import { t as $tr } from '@/i18n'


export default {
  name: 'OrbitalView',
  components: { LogViewer, RemoteFileBrowser, EmptyNotice, CubPreview, ImagePreviewModal, WavefnSource, DocLinks },
  mixins: [scrollCache],
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
      running: false,
      logLines: [],
      logKey: 0,
      ws: null,
      allData: [],
      selectedIndex: 0,
      currentTableData: [],
      rowRefs: [],
      gapIndexA: null,
      gapIndexB: null,
      gapResult: '',
      gapError: '',
      parsedOnce: false,        // 是否已经跑过一次解析（用于区分"未解析"与"该文件不含轨道信息"）
      noticeHint: '',           // 解析失败原因（显示在提示下方的小字）
      // ===== 轨道图（Multiwfn + VMD） =====
      selectedOrbitals: [],
      cubDir: '',
      cubGrid: 3,
      isoValue: 0.02,
      wavefnPath: '',           // 波函数文件（.fchk/.wfn/.wfx/.molden…），空 = 用 LOG / 自动检测
      wfBlocked: false,         // 由 WavefnSource 组件上报：LOG 读不出波函数且没指定别的文件
      restoring: false,         // 切换文件、恢复该文件先前解析内容的过程中
      fromRemoteCache: false,   // 当前解析结果来自远程缓存（不是本地目录）
      cubItems: [],
      imageItems: [],
      _busy: {},                // 文件路径 → { cub, vmd }：各文件自己的生成/绘制状态（可同时跑）
      cubScript: null,
      vmdScript: null,
      showScripts: false,
      cubScriptText: '',
      vmdScriptText: '',
      renderStyle: 'art_noshadow',  // 渲染风格：art_noshadow（艺术级无阴影，默认）/ art / standard
      _styleApplied: false,     // 是否已经按 mls-plots.json 里的默认风格设置过
      backendUrl: '',
      previewVisible: false,
      previewSrc: '',
      _previewKey: '',
      thumbW: 900,              // 界面缩略图最大宽度（原图只在点开大图时才读）
      cubTexts: {},             // 轨道序号 → cube 文本（供等值面预览）
      imageData: {},            // 轨道序号 → 渲染图片 dataURL
      _pageActive: true,
      _scrollToken: 0,
      _scrollRaf: null,
      _fileCache: {},           // 每个文件的勾选与产物（切回来还在）
    }
  },
  watch: {
    selectedIndex(val) {
      this.buildCurrentTable(val)
      this.autoScrollToHOMO()
      this.gapResult = ''
      this.gapError = ''
    },
    sourceLogPath(val) {
      // 换 LOG：波函数选择必须跟着换（该文件缓存过的就用它自己的，否则清空让组件按新文件重新查找）
      this.wavefnPath = cachedWavefn(this._fileCache, val)
    }
  },
  beforeUnmount() {
    this._pageActive = false
    if (this.ws) {
      try { this.ws.close() } catch (e) { /* ignore */ }
      this.ws = null
    }
  },
  deactivated() {
    // 离开页面（keep-alive 停用）时立即停止解析任务，避免后台消息更新已隐藏/销毁的组件
    this._pageActive = false
    if (this.ws) {
      try { this.ws.close() } catch (e) { /* ignore */ }
      this.ws = null
    }
    this.running = false
    useProgressStore().setActive('')
  },
  activated() {
    this._pageActive = true
    // 回到本页时重新解析 Multiwfn / VMD 位置（用户可能刚改过目录或环境变量）
    this.toolsStore.detect()
    this.loadPlotConfig()
    useProgressStore().setActive(this.sourceLogPath)   // 进度条只显示当前文件自己的任务
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
    docLinks() {
      return [
        { label: '使用 Multiwfn+VMD 快速绘制高质量分子轨道等值面图（sobereva.com/447）', url: 'http://sobereva.com/447' },
        { label: '用 Multiwfn 结合 VMD 绘制艺术级轨道等值面图（sobereva.com/449）', url: 'http://sobereva.com/449' }
      ]
    },
    allChecked() {
      return this.currentTableData.length > 0 && this.selectedOrbitals.length === this.currentTableData.length
    },
    // 当前解析出的 LOG 绝对路径（本地模式）
    sourceLogPath() {
      const item = this.allData[this.selectedIndex]
      if (!item || !this.folder) return ''
      const sep = this.folder.includes('\\') ? '\\' : '/'
      return `${this.folder.replace(/[\\/]+$/, '')}${sep}${item.filename}`
    },
    sourceLogName() {
      const item = this.allData[this.selectedIndex]
      return item ? item.filename : ''
    },
    defaultCubDir() { return this.folder || '' },
    cubDirResolved() { return this.cubDir || this.defaultCubDir },
    // 产物目录用的分子名（取 LOG 文件名，例如 DFMP-PI）；实际目录再加 -Orbitals 后缀
    moleculeStem() { return (this.sourceLogName || 'molecule').replace(/\.[^.]+$/, '') },
    // 每个文件各自的任务状态：切到别的文件时按钮与文字只反映那个文件自己（可以同时跑多个文件）
    busyHere() { return this._busy[this.sourceLogPath] || {} },
    cubBusy() { return !!this.busyHere.cub },
    vmdBusy() { return !!this.busyHere.vmd },
    orbBusy() { return this.cubBusy || this.vmdBusy },
    // 预览列表：优先显示已渲染图片，其次实时等值面预览
    previews() {
      const limit = 6
      const list = []
      for (const it of this.cubItems.slice(0, limit)) {
        list.push({
          orbital: it.orbital,
          label: `#${it.orbital}`,
          cub: it.cub,
          image: (this.imageItems.find(x => x.orbital === it.orbital && x.ok) || {}).image || '',
          imageData: this.imageData[it.orbital] || '',
          cubText: this.cubTexts[it.orbital] || ''
        })
      }
      return list
    }
  },
  methods: {
    // ===== 轨道图：Multiwfn 生成 cub / VMD 渲染 =====
    async ensureBackend() {
      if (this.backendUrl) return this.backendUrl
      if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
        try { this.backendUrl = await window.electronAPI.getBackendUrl() } catch (e) { /* ignore */ }
      }
      if (!this.backendUrl) this.backendUrl = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
      return this.backendUrl
    },
    async extPost(path, body) {
      const base = await this.ensureBackend()
      const resp = await fetch(`${base}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      })
      const text = await resp.text()
      let data = {}
      if (text) {
        try { data = JSON.parse(text) } catch (e) { data = { detail: text.slice(0, 300) } }
      }
      return { ok: resp.ok, data }
    },
    async extGet(path, params = {}) {
      const base = await this.ensureBackend()
      const qs = new URLSearchParams(params).toString()
      const resp = await fetch(`${base}${path}${qs ? '?' + qs : ''}`)
      const text = await resp.text()
      let data = {}
      if (text) {
        try { data = JSON.parse(text) } catch (e) { data = { detail: text.slice(0, 300) } }
      }
      return { ok: resp.ok, data }
    },
    baseName(p) {
      return String(p || '').split(/[\\/]/).pop()
    },
    // 预检交给 WavefnSource 组件（轨道图 / NTO / 空穴-电子三页共用），这里只接收日志
    onWfLog({ text, color }) {
      this.addLog(text, color)
    },
    /** 记下/清除某个文件的任务状态（每个文件各记各的，切走不影响） */
    setBusy(path, kind, val) {
      if (!path) return
      const cur = { ...(this._busy[path] || {}) }
      cur[kind] = !!val
      this._busy = { ...this._busy, [path]: cur }
    },
    /** 读根目录 mls-plots.json 里的默认渲染风格（只覆盖默认值，用户选过的不动） */
    async loadPlotConfig() {
      const { ok, data } = await this.extGet('/api/ext/defaults')
      if (!ok || !data || !data.style) return
      if (!this._styleApplied) {
        this.renderStyle = data.style
        this._styleApplied = true
      }
    },
    /** 左侧列表里标出该文件正在做什么 */
    fileBusy(idx) {
      const item = this.allData[idx]
      if (!item || !this.folder) return ''
      const sep = this.folder.includes('\\') ? '\\' : '/'
      const p = `${this.folder.replace(/[\\/]+$/, '')}${sep}${item.filename}`
      const b = this._busy[p]
      if (!b) return ''
      const parts = []
      if (b.cub) parts.push(this.$t('生成中…'))
      if (b.vmd) parts.push(this.$t('渲染中…'))
      return parts.join(' / ')
    },
    // 脚本模板文本 → 行数组（留空则用后端默认）
    scriptLines(text) {
      const lines = String(text || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean)
      return lines.length ? lines : null
    },
    toggleAllOrbitals(checked) {
      this.selectedOrbitals = checked ? this.currentTableData.map(r => Number(r.index)) : []
    },
    async chooseCubDir() {
      try {
        const p = await pickDirectory(this.$t('选择 cub / 图片输出目录'), this.cubDirResolved)
        if (p) this.cubDir = p
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    async makeCubs(force = false) {
      if (!this.sourceLogPath) { this.addLog($tr('请先在左侧选择已解析的 LOG 文件'), '#ffa500'); return }
      if (!this.toolsStore.multiwfnReady) { this.addLog($tr('没检测到 Multiwfn：请先在右上角「外部程序」里指定目录'), '#ffa500'); return }
      if (!this.selectedOrbitals.length) { this.addLog($tr('请先勾选要生成的轨道'), '#ffa500'); return }
      // 远程模式：先按需把同名的 .fchk 等波函数文件下载到本地缓存（由 WavefnSource 负责）
      if (!force && this.wfBlocked) {
        const local = await this.$refs.wf.ensureRemote()
        if (local) this.wavefnPath = local
      }
      // 使用 Multiwfn 前先确认引用说明（可勾选不再提示）
      await useMultiwfnCitationStore().require('orbitals')
      const cubKey = this.sourceLogPath       // 记下开始生成时的文件，中途切文件也不会串
      const gpKey = cubKey + '|cub'
      this.setBusy(cubKey, 'cub', true)
      const gp = useProgressStore()
      gp.start($tr('Multiwfn 生成 {0} 个轨道 cube…', { 0: this.selectedOrbitals.length }), gpKey)
      this.addLog($tr('调用 Multiwfn 生成 {0} 个轨道 cube…', { 0: this.selectedOrbitals.length }), '#87d2ff')
      const { ok, data } = await this.extPost('/api/ext/cub', {
        source: this.sourceLogPath,
        wavefn: this.wavefnPath,
        force: !!force,
        out_dir: this.cubDirResolved,
        folder_name: this.moleculeStem,
        orbitals: this.selectedOrbitals.map(Number).sort((a, b) => a - b),
        grid: this.cubGrid,
        multiwfn_dir: this.toolsStore.multiwfnDir,
        template: this.scriptLines(this.cubScriptText)
      })
      this.setBusy(cubKey, 'cub', false)
      if (!ok) {
        gp.hide(gpKey)
        this.addLog($tr('生成 cube 失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      const items = (data.items || []).filter(i => i.ok)
      const bad = (data.items || []).filter(i => !i.ok)
      this.addLog($tr('已生成 {0} 个 cube → {1}', { 0: items.length, 1: data.out_dir }), '#7cfc00')
      if (bad.length) this.addLog($tr('{0} 个轨道未生成成功（看日志）', { 0: bad.length }), '#ffa500')
      if (data.log) data.log.split('\n').forEach(l => this.addLog(l, '#9aa3ad'))
      if (data.hint) this.addLog(data.hint, '#ff6b6b')
      // 读取 cube 文本供等值面预览
      let doneN = 0
      const todo = items.slice(0, 6)
      const texts = {}
      for (const it of todo) {
        const r = await this.extPost('/api/ext/read-cub', { path: it.cub })
        if (r.ok) texts[it.orbital] = r.data.text
        doneN++
        gp.step(doneN, todo.length || 1, $tr('读取 cube {0}/{1}', { 0: doneN, 1: todo.length }), gpKey)
      }
      gp.finish($tr('已生成 {0} 个 cube', { 0: items.length }), gpKey)
      // 写回：还停在这个文件就直接显示，已经切走了就存进那个文件自己的缓存
      if (!cubKey || cubKey === this.sourceLogPath) {
        this.cubItems = items
        this.imageItems = []
        this.cubTexts = { ...this.cubTexts, ...texts }
      } else {
        const c = cacheGet(this._fileCache, cubKey) || {}
        c.cubItems = items
        c.imageItems = []
        c.cubTexts = { ...(c.cubTexts || {}), ...texts }
        this._fileCache[cubKey] = c
        this.addLog($tr('生成完成（结果已存到该文件自己的缓存里）'), '#7cfc00')
      }
    },
    /** 图片右下角标注：分子名 + 轨道号 + HOMO/LUMO 标记 + 能量 */
    orbNote(orb) {
      const row = this.currentTableData.find(r => Number(r.index) === Number(orb))
      let tag = ''
      if (row) {
        if (row.isHOMO) tag = 'HOMO'
        else if (row.isLUMO) tag = 'LUMO'
      }
      const parts = [this.moleculeStem, `orb${orb}`]
      if (tag) parts.push(tag)
      if (row && row.energy_ev != null && row.energy_ev !== '') parts.push(`${row.energy_ev} eV`)
      return parts.join('  ')
    },
    async renderCubs() {
      if (!this.cubItems.length) return
      if (!this.toolsStore.vmdReady) { this.addLog($tr('没检测到 VMD：请先在右上角「外部程序」里指定目录'), '#ffa500'); return }
      const cacheKey = this.sourceLogPath       // 记下开始绘制时的文件，中途切文件也不会串
      const gpKey = cacheKey + '|vmd'
      this.setBusy(cacheKey, 'vmd', true)
      const gp = useProgressStore()
      gp.start($tr('VMD 渲染 {0} 张轨道图…', { 0: this.cubItems.length }), gpKey)
      this.addLog($tr('调用 VMD 渲染 {0} 个轨道图…', { 0: this.cubItems.length }), '#87d2ff')
      const { ok, data } = await this.extPost('/api/ext/render', {
        out_dir: this.cubDirResolved,
        folder_name: this.moleculeStem + '-Orbitals',
        items: this.cubItems.map(i => ({ orbital: i.orbital, cub: i.cub, note: this.orbNote(i.orbital) })),
        vmd_dir: this.toolsStore.vmdDir,
        iso: this.isoValue,
        style: this.renderStyle,
        script: this.scriptLines(this.vmdScriptText)
      })
      this.setBusy(cacheKey, 'vmd', false)
      if (!ok) {
        gp.hide(gpKey)
        this.addLog($tr('VMD 渲染失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      const items = data.items || []
      const done = items.filter(i => i.ok)
      this.addLog($tr('已渲染 {0} 张轨道图 → {1}', { 0: done.length, 1: data.out_dir }), '#7cfc00')
      if (data.log) data.log.split('\n').forEach(l => this.addLog(l, '#9aa3ad'))
      // 通过后端取回图片（避免 file:// 在同源策略下加载失败）；界面用缩略图，点开大图时再读原图
      const collected = {}
      let n = 0
      for (const it of done) {
        const r = await this.extPost('/api/ext/read-image', { path: it.image, max_w: this.thumbW })
        if (r.ok) collected[it.orbital] = `data:${r.data.mime};base64,${r.data.base64}`
        n++
        gp.step(n, done.length || 1, $tr('读取渲染图 {0}/{1}', { 0: n, 1: done.length }), gpKey)
      }
      if (cacheKey && cacheKey !== this.sourceLogPath) {
        // 绘制期间用户切走了：把结果存进那个文件自己的缓存
        const c = cacheGet(this._fileCache, cacheKey) || {}
        c.imageData = { ...(c.imageData || {}), ...collected }
        c.imageItems = items
        this._fileCache[cacheKey] = c
        this.addLog($tr('绘制完成（结果已存到该文件自己的缓存里）'), '#7cfc00')
      } else {
        this.imageItems = items
        Object.assign(this.imageData, collected)
        this.cacheCurrent()
      }
      gp.finish($tr('已渲染 {0} 张轨道图', { 0: done.length }), gpKey)
    },
    /** 点开大图：先用缩略图立即显示，再把原图读进来替换 */
    async openPreview(p) {
      if (!p.imageData) return
      const key = String(p.orbital)
      this.previewSrc = p.imageData
      this._previewKey = key
      this.previewVisible = true
      const it = (this.imageItems || []).find((x) => x.orbital === p.orbital && x.image)
      if (!it) return
      const r = await this.extPost('/api/ext/read-image', { path: it.image })
      if (r.ok && this.previewVisible && this._previewKey === key) {
        this.previewSrc = `data:${r.data.mime};base64,${r.data.base64}`
      }
    },
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 200) this.logLines.shift()
    },

    async chooseParseSource() {
      if (this.parseMode === 'remote') {
        if (!this.connected) {
          this.addLog($tr('请先连接服务器'), '#ffa500')
          return
        }
        this.browserTarget = 'logFolder'
        this.browserInitialPath = `/home/${this.username}` || '/'
        this.browserVisible = true
        return
      }
      // 本地：选择文件夹（不自动解析，避免与下方“解析”按钮重复）
      let path
      try {
        path = await pickDirectory($tr('选择包含 Gaussian .log 文件的文件夹'))
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return
      this.folder = path
      this.addLog($tr('本地目录: {0}', { 0: path }), '#87d2ff')
    },

    async runParse() {
      if (this.running) return
      if (this.parseMode === 'local') {
        if (!this.folder) {
          this.addLog($tr('请先选择本地文件夹'), '#ffa500')
          return
        }
        this.fromRemoteCache = false
        this.startParse()
        return
      }
      // 远程：同步 .log 到缓存后解析
      if (!this.remoteFolder) {
        this.addLog($tr('请先选择远程目录'), '#ffa500')
        return
      }
      if (!this.connected) {
        this.addLog($tr('请先连接服务器'), '#ffa500')
        return
      }
      this.running = true
      this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      try {
        const { cacheDir, count } = await syncRemoteFolder(this.sessionId, this.remoteFolder, '.log')
        this.addLog($tr('已同步 {0} 个 .log → {1}', { 0: count, 1: cacheDir }), '#87d2ff')
        if (!this._pageActive) {
          this.running = false
          return
        }
        this.folder = cacheDir
        this.fromRemoteCache = true      // 数据来自远程缓存：cub 需要时再下载同名波函数文件
        this.running = false
        this.startParse()
      } catch (e) {
        this.addLog($tr('远程解析失败: {0}', { 0: e.message }), '#ff6b6b')
        this.running = false
      }
    },

    onBrowserSelect({ target, path, is_dir }) {
      if (target === 'logFolder') {
        this.remoteFolder = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
        this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      }
    },

    async selectFolder() {
      let path
      try {
        path = await pickDirectory($tr('选择包含 .log 文件的文件夹'))
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.folder = path
      this.addLog($tr(' 选择目录: {0}', { 0: path }), '#87d2ff')
      this.allData = []
      this.currentTableData = []
      this.selectedIndex = 0
      this.gapResult = ''
      this.gapError = ''
      this.startParse()
    },

    startParse() {
      if (this.running || !this.folder) return
      this.running = true
      this.logLines.splice(0)
      this.logKey++
      this.allData = []
      this.currentTableData = []
      this.selectedIndex = 0
      this.gapResult = ''
      this.gapError = ''
      this.addLog($tr('开始解析轨道能量...'), '#00ff00')

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/orbital`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog('', '#87d2ff')
        this.ws.send(JSON.stringify({ action: 'parse_orbital', folder: this.folder }))
      }

      this.ws.onmessage = (e) => {
        if (!this._pageActive || !this.ws) return
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog($tr(' {0} 解析成功 [{1}/{2}]', { 0: data.filename, 1: data.index, 2: data.total }), '#7cfc00')
            } else {
              this.noticeHint = data.message || ''
              this.addLog($tr(' {0} 解析失败: {1}', { 0: data.filename, 1: data.message }), '#ff6b6b')
            }
            break
          case 'result':
            this.parsedOnce = true
            this.allData = data.data
            if (this.allData.length) {
              this.selectedIndex = 0
              this.buildCurrentTable(0)
              this.autoScrollToHOMO(12)
              this.addLog($tr('共解析 {0} 个文件', { 0: this.allData.length }), '#87d2ff')
              this.$nextTick(() => {
                this.triggerRestore()
              })
            }
            break
          case 'done':
            this.addLog(`${data.message}`, '#00ff00')
            this.running = false
            this.ws.close()
            break
          case 'error':
            this.addLog(` ${data.message}`, '#ff6b6b')
            this.running = false
            this.ws.close()
            break
          default:
            this.addLog(JSON.stringify(data))
        }
      }

      this.ws.onerror = () => {
        this.addLog($tr(' WebSocket 错误'), '#ff6b6b')
        this.running = false
      }
      this.ws.onclose = () => {
        this.running = false
      }
    },

    async selectFile(idx) {
      if (idx === this.selectedIndex) return
      // 切文件：先亮「正在恢复先前解析的内容」，把该文件自己的勾选/产物/波函数恢复回来
      this.restoring = true
      const gp = useProgressStore()
      this.cacheCurrent()
      this.selectedIndex = idx
      const myIdx = idx
      const gpKey = this.sourceLogPath + '|restore'
      gp.setActive(this.sourceLogPath)      // 进度条从此只显示这个文件自己的任务
      gp.start($tr('正在恢复先前解析的内容……'), gpKey)
      this.restoreCache()
      await this.$nextTick()
      try {
        await this.$refs.wf.reload()      // 波函数按这个文件重新预检
      } catch (e) { /* 预检失败不挡切换 */ }
      if (this.selectedIndex === myIdx) this.restoring = false
      gp.hide(gpKey)                        // 只结束"恢复"这一个任务（别的文件/别的任务照旧）
    },
    /** 把当前文件的状态存进缓存（键用完整路径，避免不同目录同名文件撞车） */
    cacheCurrent() {
      const key = this.sourceLogPath
      if (!key) return
      this._fileCache[key] = {
        selectedOrbitals: [...this.selectedOrbitals],
        cubItems: this.cubItems,
        imageItems: this.imageItems,
        cubTexts: this.cubTexts,
        imageData: this.imageData,
        wavefnPath: this.wavefnPath
      }
    },
    /** 切回某文件时恢复它自己的状态；没有缓存就清空（波函数会按新文件重新自动查找） */
    restoreCache() {
      const key = this.sourceLogPath
      this.selectedOrbitals = cachedList(this._fileCache, key, 'selectedOrbitals')
      this.cubItems = cachedList(this._fileCache, key, 'cubItems')
      this.imageItems = cachedList(this._fileCache, key, 'imageItems')
      this.cubTexts = cachedMap(this._fileCache, key, 'cubTexts')
      this.imageData = cachedMap(this._fileCache, key, 'imageData')
      this.wavefnPath = cachedWavefn(this._fileCache, key)
    },

    buildCurrentTable(idx) {
      if (!this.allData.length || idx >= this.allData.length) {
        this.currentTableData = []
        return
      }
      const fileData = this.allData[idx]
      const rows = []
      const filename = fileData.filename
      fileData.alpha_occ.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Alpha',
          type: 'Occ',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: idxNum === fileData.homo_alpha,
          isLUMO: false
        })
      })
      fileData.alpha_virt.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Alpha',
          type: 'Vir',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: false,
          isLUMO: idxNum === fileData.lumo_alpha
        })
      })
      fileData.beta_occ.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Beta',
          type: 'Occ',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: idxNum === fileData.homo_beta,
          isLUMO: false
        })
      })
      fileData.beta_virt.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Beta',
          type: 'Vir',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: false,
          isLUMO: idxNum === fileData.lumo_beta
        })
      })
      this.currentTableData = rows
      this.rowRefs = []
    },

    // 表格刚渲染时容器可能尚未测量完成，采用重试方式确保滚动到 HOMO/LUMO 行
    autoScrollToHOMO(attempts = 8) {
      const token = ++this._scrollToken
      this.$nextTick(() => {
        const step = () => {
          if (attempts <= 0 || !this._pageActive || token !== this._scrollToken) return
          attempts--
          this.scrollToHOMO_LUMO()
          setTimeout(step, 120)
        }
        step()
      })
    },

    scrollToHOMO_LUMO() {
      const container = this.$refs.tableContainer
      if (!container) return
      // 通过标记类定位 HOMO/LUMO 行（不依赖具体背景色，主题可自由换色）
      const target = container.querySelector('.row-homo, .row-lumo') ||
        container.querySelector('tbody tr')
      if (target) this.fastScrollIntoCenter(container, target)
    },

    // 自绘滚动：scrollIntoView 的 smooth 时长不可控（行长时很慢），
    // 这里固定 140ms + easeOutCubic，滚动距离大时也不会拖沓
    fastScrollIntoCenter(container, el, duration = 140) {
      const cRect = container.getBoundingClientRect()
      const eRect = el.getBoundingClientRect()
      const max = Math.max(0, container.scrollHeight - container.clientHeight)
      const target = container.scrollTop + (eRect.top - cRect.top)
        - (container.clientHeight - eRect.height) / 2
      const to = Math.max(0, Math.min(max, target))
      const from = container.scrollTop
      if (Math.abs(to - from) < 1) return
      if (this._scrollRaf) cancelAnimationFrame(this._scrollRaf)
      const start = performance.now()
      const tick = (now) => {
        const p = Math.min(1, (now - start) / duration)
        const eased = 1 - Math.pow(1 - p, 3)
        container.scrollTop = from + (to - from) * eased
        if (p < 1) this._scrollRaf = requestAnimationFrame(tick)
        else this._scrollRaf = null
      }
      this._scrollRaf = requestAnimationFrame(tick)
    },

    calcGap() {
      this.gapResult = ''
      this.gapError = ''
      if (!this.currentTableData.length) {
        this.gapError = $tr('请先解析轨道数据')
        return
      }
      const a = this.gapIndexA
      const b = this.gapIndexB
      if (a === null || b === null || isNaN(a) || isNaN(b) || a < 1 || b < 1) {
        this.gapError = $tr('请输入有效的轨道序号（正整数）')
        return
      }
      if (a === b) {
        this.gapError = $tr('请选择两个不同的轨道序号')
        return
      }
      const findEnergy = (index) => {
        const row = this.currentTableData.find(r => r.index === index)
        return row ? parseFloat(row.energy_ha) : null
      }
      const engA = findEnergy(a)
      const engB = findEnergy(b)
      if (engA === null) {
        this.gapError = $tr('未找到轨道序号 {0}', { 0: a })
        return
      }
      if (engB === null) {
        this.gapError = $tr('未找到轨道序号 {0}', { 0: b })
        return
      }
      const deltaHa = Math.abs(engA - engB)
      const deltaEv = deltaHa * 27.211386
      this.gapResult = `ΔE = ${deltaEv.toFixed(4)} eV (${deltaHa.toFixed(6)} Ha)`
    },

    exportCSV() {
      if (!this.allData.length) return
      const headers = [$tr('文件'), $tr('自旋'), $tr('类型'), $tr('轨道序号'), $tr('能量(Ha)'), $tr('能量(eV)'), 'HOMO/LUMO']
      const rows = []
      this.allData.forEach(fileData => {
        const filename = fileData.filename
        const allTracks = [
          ...fileData.alpha_occ.map(([idx, eng]) => ({ file: filename, spin: 'Alpha', type: 'Occ', index: idx, eng, isHOMO: idx === fileData.homo_alpha, isLUMO: false })),
          ...fileData.alpha_virt.map(([idx, eng]) => ({ file: filename, spin: 'Alpha', type: 'Vir', index: idx, eng, isHOMO: false, isLUMO: idx === fileData.lumo_alpha })),
          ...fileData.beta_occ.map(([idx, eng]) => ({ file: filename, spin: 'Beta', type: 'Occ', index: idx, eng, isHOMO: idx === fileData.homo_beta, isLUMO: false })),
          ...fileData.beta_virt.map(([idx, eng]) => ({ file: filename, spin: 'Beta', type: 'Vir', index: idx, eng, isHOMO: false, isLUMO: idx === fileData.lumo_beta }))
        ]
        allTracks.forEach(t => {
          rows.push([
            t.file, t.spin, t.type, t.index,
            t.eng.toFixed(6),
            (t.eng * 27.211386).toFixed(4),
            t.isHOMO ? 'HOMO' : t.isLUMO ? 'LUMO' : ''
          ])
        })
      })
      const content = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
      const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = 'orbital_energies.csv'
      link.click()
    },

    async exportExcel() {
      if (!this.allData.length) return
      try {
        const XLSX = await import('xlsx')
        const wb = XLSX.utils.book_new()
        this.allData.forEach((fileData) => {
          const filename = fileData.filename
          const allTracks = [
            ...fileData.alpha_occ.map(([idxNum, eng]) => ({ spin: 'Alpha', type: 'Occ', index: idxNum, eng, homo: idxNum === fileData.homo_alpha, lumo: false })),
            ...fileData.alpha_virt.map(([idxNum, eng]) => ({ spin: 'Alpha', type: 'Vir', index: idxNum, eng, homo: false, lumo: idxNum === fileData.lumo_alpha })),
            ...fileData.beta_occ.map(([idxNum, eng]) => ({ spin: 'Beta', type: 'Occ', index: idxNum, eng, homo: idxNum === fileData.homo_beta, lumo: false })),
            ...fileData.beta_virt.map(([idxNum, eng]) => ({ spin: 'Beta', type: 'Vir', index: idxNum, eng, homo: false, lumo: idxNum === fileData.lumo_beta }))
          ]
          const rows = allTracks.map(t => ({
            '自旋': t.spin,
            '类型': t.type,
            '轨道序号': t.index,
            '能量(Ha)': t.eng.toFixed(6),
            '能量(eV)': (t.eng * 27.211386).toFixed(4),
            'HOMO/LUMO': t.homo ? 'HOMO' : t.lumo ? 'LUMO' : ''
          }))
          let sheetName = filename.replace(/\.log$/i, '').replace(/[\[\]:*?/\\]/g, '_')
          if (sheetName.length > 31) sheetName = sheetName.substring(0, 31)
          const existingSheets = wb.SheetNames
          let finalName = sheetName
          let counter = 1
          while (existingSheets.includes(finalName)) {
            finalName = `${sheetName}_${counter++}`
            if (finalName.length > 31) finalName = finalName.substring(0, 31)
          }
          const ws = XLSX.utils.json_to_sheet(rows)
          XLSX.utils.book_append_sheet(wb, ws, finalName)
        })
        XLSX.writeFile(wb, 'orbital_energies.xlsx')
        this.addLog($tr('Excel 导出成功（多个 sheet）'), '#7cfc00')
      } catch (e) {
        this.addLog($tr('导出 Excel 需要 xlsx 库，请安装: npm install xlsx'), '#ffa500')
        console.error(e)
      }
    }
  }
}
</script>
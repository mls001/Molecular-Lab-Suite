<template>
  <div class="flex-col h-full" style="gap:6px;overflow:hidden;">
    <div class="flex flex-1 min-h-0" style="gap:6px;">

      <!-- ===== 左：分子文件 ===== -->
      <aside class="flex-col mls-panel" style="width:240px;flex-shrink:0;min-height:0;">
        <div class="mls-panel-head">
          <span>{{ $t('分子文件') }}</span>
          <button class="btn" style="height:20px;padding:0 8px;font-size:11px;" @click="refreshList">{{ $t('刷新') }}</button>
        </div>
        <div class="mls-subhead" :title="folder">{{ folder || $t('未选择目录') }}</div>
        <div class="flex" style="gap:4px;padding:4px 6px;border-bottom:1px solid var(--c-border-soft);">
          <button class="btn" style="flex:1;height:22px;font-size:11px;" @click="chooseFolder">{{ $t('选择文件夹…') }}</button>
          <button class="btn" style="flex:1;height:22px;font-size:11px;" @click="useMolsDir">{{ $t('Mols 目录') }}</button>
        </div>
        <div v-if="fromStore" style="padding:3px 8px;font-size:11px;color:var(--c-accent);border-bottom:1px solid var(--c-border-soft);">
          {{ $t('已载入分子结构页的分子') }}：{{ molName }}
        </div>
        <div style="flex:1;overflow-y:auto;padding:2px 0;min-height:0;">
          <div v-if="!files.length" class="ide-empty">{{ $t('目录里没有分子文件') }}</div>
          <div
            v-for="f in files"
            :key="f.path"
            class="flex-center"
            style="gap:6px;padding:3px 8px;cursor:pointer;font-size:12px;"
            :style="{ background: activeName === f.name ? 'var(--c-hl-a)' : 'transparent' }"
            @click="openFile(f)"
            @mouseenter="ev => { if (activeName !== f.name) ev.currentTarget.style.background = 'var(--c-hover)' }"
            @mouseleave="ev => { if (activeName !== f.name) ev.currentTarget.style.background = 'transparent' }"
          >
            <span style="flex-shrink:0;font-size:10px;font-weight:700;color:var(--c-text-3);">{{ f.ext.replace('.', '').toUpperCase() }}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ f.name }}</span>
          </div>
        </div>
      </aside>

      <!-- ===== 中：生成的输入文件 ===== -->
      <section class="flex-col mls-panel" style="flex:1;min-width:0;min-height:0;">
        <div class="mls-toolbar" style="justify-content:space-between;">
          <div class="flex-center" style="gap:8px;min-width:0;flex:1;">
            <span style="font-weight:700;font-size:12px;">{{ outFilename || $t('（未生成）') }}</span>
            <span v-if="molName" style="font-size:11px;color:var(--c-text-3);">
              {{ molName }} · {{ nAtoms }} {{ $t('原子') }}
            </span>
          </div>
          <div class="flex-center" style="gap:4px;flex-shrink:0;">
            <button class="btn" style="height:22px;padding:0 10px;font-size:11px;" @click="generate" :disabled="busy || !hasMolecule">{{ $t('重新生成') }}</button>
            <button class="btn" style="height:22px;padding:0 10px;font-size:11px;" @click="copyContent" :disabled="!content">{{ $t('复制') }}</button>
            <button class="btn btn-primary" style="height:22px;padding:0 10px;font-size:11px;" @click="saveInput" :disabled="busy || !content">{{ $t('保存为文件') }}</button>
          </div>
        </div>

        <EmptyNotice
          v-if="!hasMolecule"
          :text="$t('请先在左侧选择一个分子文件')"
          :hint="$t('支持 .mls/.mol/.sdf/.xyz/.pdb/.smi/.gjf/.inp/.log/.out；也可以先在「分子结构」页编辑后点「生成输入文件」')"
        />
        <textarea
          v-else
          v-model="content"
          readonly
          class="control"
          style="flex:1;width:100%;border:none;padding:8px;font-family:var(--font-mono);font-size:12px;line-height:1.5;resize:none;background:var(--c-editor);color:var(--c-code);box-shadow:none;"
          spellcheck="false"
        ></textarea>

        <div class="mls-subhead">
          <span v-if="outFolder">{{ $t('输出目录') }}: {{ outFolder }}</span>
          <span v-else>{{ $t('保存前请选择输出目录') }}</span>
        </div>
      </section>

      <!-- ===== 右：参数 ===== -->
      <aside class="flex-col mls-panel" style="width:290px;flex-shrink:0;overflow-y:auto;padding:8px 10px;gap:8px;min-height:0;">

        <div class="rp-sec">
          <span class="label">{{ $t('目标程序') }}</span>
          <div class="flex" style="gap:6px;">
            <button class="btn" :class="target === 'gaussian' ? 'btn-primary' : 'btn-default'" style="flex:1;height:24px;font-size:11px;" @click="setTarget('gaussian')">Gaussian</button>
            <button class="btn" :class="target === 'orca' ? 'btn-primary' : 'btn-default'" style="flex:1;height:24px;font-size:11px;" @click="setTarget('orca')">ORCA</button>
          </div>
        </div>

        <!-- 计算资源（预设 / 内存 / 核心数）：与「修改GJF」「提取扫描」完全一致 -->
        <div class="rp-sec">
          <div class="rp-row">
            <span class="label">{{ $t('预设') }}</span>
            <select class="control rp-num" style="font-size:11px;" v-model="selectedPreset" @change="applyPreset">
              <option v-for="name in resourceNames" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div class="rp-row">
            <span class="label">{{ $t('内存') }}</span>
            <input class="control rp-num" v-model="mem" :placeholder="'%mem'" @change="generate" />
          </div>
          <div class="rp-row">
            <span class="label">{{ $t('核心数') }}</span>
            <input class="control rp-num" v-model="nproc" @change="generate" />
          </div>
        </div>

        <!-- 计算模式 -->
        <div class="rp-sec">
          <template v-if="target === 'gaussian'">
            <div class="flex-col" style="gap:4px;">
              <span class="label">{{ $t('计算模式') }}</span>
              <input class="control rp-full" v-model="calc" list="molCalcPresets" @change="generate" />
              <datalist id="molCalcPresets">
                <option v-for="m in gaussianModes" :key="m" :value="m" />
              </datalist>
            </div>
          </template>
          <template v-else>
            <div class="flex-col" style="gap:4px;">
              <span class="label">{{ $t('ORCA 预设') }}</span>
              <select class="control rp-full" style="font-size:11px;" v-model="preset" @change="generate">
                <option v-for="p in orcaPresets" :key="p.id" :value="p.id">{{ $t(p.label) }}</option>
              </select>
            </div>
            <div class="rp-row">
              <span class="label">{{ $t('激发态数 nroots') }}</span>
              <input class="control rp-num" v-model.number="nstates" type="number" min="1" @change="generate" />
            </div>
            <div class="rp-row">
              <span class="label">%maxcore</span>
              <input class="control rp-num" v-model.number="maxcore" type="number" min="100" @change="generate" />
            </div>
          </template>
        </div>

        <!-- 方法与公共参数 -->
        <div class="rp-sec">
          <div class="flex-col" style="gap:4px;">
            <span class="label">{{ $t('泛函 / 基组') }}</span>
            <input class="control rp-full" v-model="functional" list="molFuncPresets" @change="generate" />
            <input class="control rp-full" v-model="basis" list="molBasisPresets" @change="generate" />
            <datalist id="molFuncPresets">
              <option v-for="f in funcPresets" :key="f" :value="f" />
            </datalist>
            <datalist id="molBasisPresets">
              <option v-for="b in basisPresets" :key="b" :value="b" />
            </datalist>
          </div>
          <div class="flex-col" style="gap:4px;">
            <span class="label">{{ $t('电荷 / 自旋') }}</span>
            <div class="flex" style="gap:6px;">
              <input class="control" style="flex:1;min-width:0;height:24px;" v-model.number="charge" type="number" @change="generate" />
              <input class="control" style="flex:1;min-width:0;height:24px;" v-model.number="mult" type="number" min="1" @change="generate" />
            </div>
          </div>
        </div>

        <!-- 额外设置 -->
        <div class="rp-sec">
          <div class="rp-row">
            <span class="label">{{ $t('标题') }}</span>
            <input class="control rp-num" v-model="title" @change="generate" />
          </div>
          <div class="flex-col" style="gap:3px;">
            <span class="label">{{ $t('额外关键词') }}</span>
            <input class="control rp-full" v-model="extraKeywords" @change="generate" />
          </div>
          <div v-if="target === 'orca'" class="flex-col" style="gap:3px;">
            <span class="label">{{ $t('额外 %block') }}</span>
            <textarea class="control" style="width:100%;height:52px;font-size:11px;padding:4px;" v-model="extraBlocks" @change="generate"></textarea>
          </div>
        </div>

        <!-- 保存 -->
        <div class="rp-sec">
          <span class="label">{{ $t('输出文件') }}</span>
          <input class="control rp-full" v-model="outFilename" :placeholder="$t('文件名')" />
          <div class="rp-row">
            <span class="rp-hint" style="flex:1;">{{ outFolder || $t('未选择') }}</span>
            <button class="btn" style="height:24px;font-size:11px;flex-shrink:0;" @click="chooseOutFolder">{{ $t('选择…') }}</button>
          </div>
          <button class="btn btn-primary h-lg" @click="saveInput" :disabled="busy || !content || !outFolder">{{ $t('保存为文件') }}</button>
        </div>
      </aside>
    </div>

    <LogViewer :lines="logLines" />
  </div>
</template>

<script>
import LogViewer from '@/components/LogViewer.vue'
import EmptyNotice from '@/components/EmptyNotice.vue'
import { pickDirectory } from '@/api/dialog'
import { resourceOf, RESOURCE_PRESET_NAMES, DEFAULT_RESOURCE_PRESET } from '@/utils/mlsPresets'
import { useMoleculeStore } from '@/stores/molecule'
import { t as $tr } from '@/i18n'

export default {
  name: 'InputGenView',
  components: { LogViewer, EmptyNotice },
  data() {
    return {
      backendUrl: '',
      molsDir: '',
      folder: '',
      files: [],
      activeName: '',
      // 分子
      molblock: '',
      molName: '',
      nAtoms: 0,
      fromStore: false,
      // 参数
      target: 'gaussian',
      functional: 'm062x',
      basis: '6-31g(d,p)',
      calc: '#p opt',
      preset: 'soc_tddft',
      nstates: 10,
      mem: '12GB',
      nproc: '12',
      maxcore: 2500,
      selectedPreset: DEFAULT_RESOURCE_PRESET,
      resourceNames: RESOURCE_PRESET_NAMES,
      charge: 0,
      mult: 1,
      title: '',
      extraKeywords: '',
      extraBlocks: '',
      // 预设列表
      gaussianModes: [],
      orcaPresets: [],
      gaussianFuncPresets: [],
      gaussianBasisPresets: [],
      orcaFuncPresets: [],
      orcaBasisPresets: [],
      // 输出
      content: '',
      outFilename: '',
      outFolder: '',
      busy: false,
      _storeRev: -1,        // 已经载入过的「分子结构」页分子版本
      _ready: false,        // 预设读完没有（activated 钩子据此判断能不能直接刷新）
      logLines: []
    }
  },
  computed: {
    hasMolecule() { return !!this.molblock },
    funcPresets() {
      return this.target === 'orca' ? this.orcaFuncPresets : this.gaussianFuncPresets
    },
    basisPresets() {
      return this.target === 'orca' ? this.orcaBasisPresets : this.gaussianBasisPresets
    }
  },
  async mounted() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try { this.backendUrl = await window.electronAPI.getBackendUrl() } catch (e) { /* fallthrough */ }
    }
    if (!this.backendUrl) this.backendUrl = 'http://127.0.0.1:8002'

    try {
      const r = await fetch(`${this.backendUrl}/api/mol/presets`)
      const d = await r.json()
      this.molsDir = d.mols_dir || ''
      this.folder = this.molsDir
      this.outFolder = this.molsDir
      this.gaussianModes = d.gaussian_modes || []
      this.orcaPresets = d.orca_presets || []
      this.gaussianFuncPresets = d.gaussian_func_presets || []
      this.gaussianBasisPresets = d.gaussian_basis_presets || []
      this.orcaFuncPresets = d.orca_func_presets || []
      this.orcaBasisPresets = d.orca_basis_presets || []
    } catch (e) {
      this.addLog($tr('读取预设失败: {0}', { 0: e.message }), '#ff6b6b')
    }

    this._ready = true
    await this.loadFromStore()
    await this.refreshList()
  },
  /** 本页被 keep-alive 缓存，再次进入不会走 mounted：这里补一次，保证能收到「分子结构」页送来的新分子 */
  activated() {
    if (!this._ready) return
    this.loadFromStore()
    this.refreshList()
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      if (this.logLines.length > 200) this.logLines.shift()
    },
    async postJson(url, body) {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      })
      const text = await resp.text()
      let data = {}
      if (text) {
        try { data = JSON.parse(text) } catch (e) {
          data = { detail: text.length > 400 ? text.slice(0, 400) + '…' : text }
        }
      }
      return { ok: resp.ok, status: resp.status, data }
    },

    /** 载入「分子结构」页送来的分子（未保存的也算）：版本没变就不重复载入 */
    async loadFromStore() {
      const store = useMoleculeStore()
      if (!store.molblock || store.rev === this._storeRev) return false
      this._storeRev = store.rev
      this.molblock = store.molblock
      this.molName = store.name || ''
      this.nAtoms = (store.atoms || []).length
      this.fromStore = true
      this.activeName = store.source || ''
      this.charge = store.charge || 0
      this.mult = store.mult || 1
      this.title = ''
      this.addLog($tr('已从「分子结构」页载入分子: {0}', { 0: this.molName }), '#87d2ff')
      await this.generate()
      return true
    },
    async refreshList() {
      if (!this.folder) return
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/list`, { folder: this.folder })
      if (!ok) {
        this.files = []
        this.addLog($tr('读取目录失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.files = data.files || []
      this.addLog($tr('找到 {0} 个分子文件', { 0: this.files.length }), '#87d2ff')
    },
    async chooseFolder() {
      let p
      try {
        p = await pickDirectory($tr('选择包含分子文件的文件夹'), this.folder)
      } catch (e) { this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b'); return }
      if (!p) return
      this.folder = p
      await this.refreshList()
    },
    async useMolsDir() {
      this.folder = this.molsDir
      await this.refreshList()
    },
    async chooseOutFolder() {
      let p
      try {
        p = await pickDirectory($tr('选择输入文件保存目录'), this.outFolder || this.folder)
      } catch (e) { this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b'); return }
      if (!p) return
      this.outFolder = p
    },
    // 计算资源预设（与「修改GJF」「提取扫描」共用同一份）
    applyPreset() {
      const p = resourceOf(this.selectedPreset)
      this.mem = p.mem
      this.nproc = p.nproc
      this.maxcore = p.maxcore
      this.generate()
      this.addLog($tr('应用预设: {0}', { 0: this.selectedPreset }), '#87d2ff')
    },
    setTarget(t) {
      this.target = t
      this.basis = t === 'orca' ? 'def2-SVP' : '6-31g(d,p)'
      this.functional = 'm062x'
      this.generate()
    },
    async openFile(file) {
      if (this.busy) return
      this.busy = true
      this.addLog($tr('打开: {0}', { 0: file.name }), '#87d2ff')
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/open`, { path: file.path })
      this.busy = false
      if (!ok) { this.addLog($tr('打开失败: {0}', { 0: data.detail }), '#ff6b6b'); return }
      this.activeName = file.name
      this.fromStore = false
      this.molblock = data.molblock || ''
      this.molName = data.name || file.name.replace(/\.[^.]+$/, '')
      this.nAtoms = data.n_atoms || 0
      this.charge = data.charge || 0
      this.mult = data.mult || 1
      this.title = ''
      this.addLog($tr('已载入 {0}：{1} 个原子', { 0: file.name, 1: this.nAtoms }), '#7cfc00')
      await this.generate()
    },
    async generate() {
      if (!this.molblock || this.busy) return
      this.busy = true
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/to-input`, {
        molblock: this.molblock,
        target: this.target,
        charge: this.charge,
        mult: this.mult,
        functional: this.functional,
        basis: this.basis,
        calc: this.calc,
        preset: this.preset,
        nstates: this.nstates,
        mem: this.mem,
        nproc: this.nproc,
        maxcore: this.maxcore,
        title: this.title,
        extra_keywords: this.extraKeywords,
        extra_blocks: this.extraBlocks,
        filename: this.molName
      })
      this.busy = false
      if (!ok) { this.addLog($tr('生成失败: {0}', { 0: data.detail }), '#ff6b6b'); return }
      this.content = data.content || ''
      this.outFilename = data.filename || ''
      this.addLog($tr('已生成 {0}（{1} 个原子）', { 0: data.filename, 1: data.n_atoms }), '#7cfc00')
    },
    async copyContent() {
      try {
        await navigator.clipboard.writeText(this.content)
        this.addLog($tr('已复制到剪贴板'), '#7cfc00')
      } catch (e) {
        this.addLog($tr('复制失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    async saveInput() {
      if (!this.content) return
      if (!this.outFolder) { this.addLog($tr('请先选择输出目录'), '#ffa500'); return }
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/save-input`, {
        folder: this.outFolder,
        filename: this.outFilename || (this.molName + (this.target === 'orca' ? '.inp' : '.gjf')),
        content: this.content
      })
      if (!ok) { this.addLog($tr('保存失败: {0}', { 0: data.detail }), '#ff6b6b'); return }
      this.addLog($tr('已保存输入文件: {0}', { 0: data.path }), '#7cfc00')
    }
  }
}
</script>

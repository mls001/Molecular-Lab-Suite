<template>
  <div class="flex-col h-full" style="gap:6px;overflow:hidden;">

    <div class="flex flex-1 min-h-0" style="gap:6px;">

      <!-- ===== 左：扫描步骤列表 ===== -->
      <aside class="flex-col mls-panel" style="width:240px;flex-shrink:0;min-height:0;">
        <div class="mls-panel-head">
          <span>{{ $t('步骤列表') }}</span>
          <label class="flex-center" style="gap:4px;font-size:11px;color:var(--c-titlebar-text);cursor:pointer;">
            <input type="checkbox" v-model="selectAll" @change="toggleAll" /> {{ $t('全选') }}
          </label>
        </div>
        <div v-if="steps.length" class="mls-subhead">
          {{ $t('共 {n} 个扫描点', { n: steps.length }) }} · {{ sourceLabel }}
        </div>
        <div style="flex:1;overflow-y:auto;padding:2px 0;min-height:0;">
          <div v-if="!steps.length" class="ide-empty">{{ $t('暂无扫描步骤') }}</div>
          <div
            v-for="s in steps"
            :key="s.id"
            class="flex-center"
            style="gap:6px;padding:3px 8px;cursor:pointer;font-size:12px;"
            :style="{ background: selectedStepId === s.id ? 'var(--c-hl-a)' : 'transparent' }"
            @click="selectStep(s.id)"
            @mouseenter="ev => { if (selectedStepId !== s.id) ev.currentTarget.style.background = 'var(--c-hover)' }"
            @mouseleave="ev => { if (selectedStepId !== s.id) ev.currentTarget.style.background = 'transparent' }"
          >
            <input type="checkbox" :value="s.id" v-model="checkedSteps" @click.stop />
            <span style="flex:1;">ScanPoint {{ s.id }}</span>
            <span style="font-size:11px;color:var(--c-text-3);">{{ s.natoms }}</span>
          </div>
        </div>
      </aside>

      <!-- ===== 中：GJF 预览 ===== -->
      <section class="flex-col mls-panel" style="flex:1;min-width:0;min-height:0;">
        <div class="mls-toolbar" style="justify-content:space-between;">
          <div class="flex" style="gap:10px;align-items:center;min-width:0;flex:1;">
            <span style="font-weight:700;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
              {{ logName ? logName + '.log' : $t('未选择文件') }}
            </span>
            <span v-if="mode === 'remote'" style="color:var(--c-accent);font-size:12px;">{{ $t('(远程)') }}</span>
            <span v-if="selectedStepId" style="font-size:12px;color:var(--c-text-2);">
              {{ $t('预览') }}: ScanPoint {{ selectedStepId }}
            </span>
          </div>
          <button class="btn btn-primary" style="height:24px;" @click="schedulePreview(0)" :disabled="!hasSource || !selectedStepId">
            {{ $t('刷新预览') }}
          </button>
        </div>
        <EmptyNotice
          v-if="parsedOnce && !steps.length"
          :text="$t('该文件内不含扫描构象信息')"
          :hint="noticeHint"
        />
        <textarea
          v-else
          v-model="stepContent"
          readonly
          class="control"
          style="flex:1;width:100%;border:none;padding:8px;font-family:var(--font-mono);font-size:12px;line-height:1.45;resize:none;background:var(--c-editor);color:var(--c-code);box-shadow:none;"
          spellcheck="false"
        ></textarea>
      </section>

      <!-- ===== 右：参数与操作 ===== -->
      <aside class="flex-col mls-panel" style="width:290px;flex-shrink:0;overflow-y:auto;padding:8px 10px;gap:8px;min-height:0;">

        <div class="flex-center" style="justify-content:space-between;">
          <span class="label">{{ $t('工作模式') }}</span>
          <div class="flex-center" style="gap:6px;">
            <button class="btn" :class="mode === 'local' ? 'btn-primary' : 'btn-default'" style="height:22px;padding:0 10px;font-size:11px;" @click="switchMode('local')">{{ $t('本地') }}</button>
            <button class="btn" :class="mode === 'remote' ? 'btn-primary' : 'btn-default'" style="height:22px;padding:0 10px;font-size:11px;" @click="switchMode('remote')" :disabled="!connected">{{ $t('远程') }}</button>
          </div>
        </div>

        <!-- 输入 -->
        <div class="rp-sec">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ mode === 'remote' ? $t('远程目录') : $t('输入 LOG') }}</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="chooseInput">{{ $t('选择…') }}</button>
          </div>
          <div class="rp-hint">{{ inputDisplay || $t('未选择') }}</div>
          <select
            v-if="mode === 'remote' && remoteLogFiles.length"
            class="control rp-full"
            style="font-size:11px;"
            v-model="remoteLogName"
            @change="selectRemoteLog(remoteLogName)"
          >
            <option v-for="f in remoteLogFiles" :key="f" :value="f">{{ f }}</option>
          </select>
        </div>

        <!-- 输出 -->
        <div class="rp-sec">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ $t('输出目录') }}</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="chooseOutput">{{ $t('选择…') }}</button>
          </div>
          <div class="rp-hint">{{ outputDisplay || $t('未选择') }}</div>
        </div>

        <!-- 计算资源（预设 / 内存 / 核心数） -->
        <div class="rp-sec">
          <div class="rp-row">
            <span class="label">{{ $t('预设') }}</span>
            <select class="control rp-num" style="font-size:11px;" v-model="selectedPreset" @change="applyPreset">
              <option v-for="name in resourceNames" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <label class="rp-check">
            <input type="checkbox" v-model="addResources" @change="schedulePreview(0)" /> {{ $t('添加 %mem / %nprocshared 行') }}
          </label>
          <div class="rp-row">
            <span class="label">{{ $t('内存') }}</span>
            <input class="control rp-num" v-model="mem" :disabled="!addResources" :placeholder="'%mem'" />
          </div>
          <div class="rp-row">
            <span class="label">{{ $t('核心数') }}</span>
            <input class="control rp-num" v-model="nproc" :disabled="!addResources" :placeholder="'%nprocshared'" />
          </div>
        </div>

        <!-- 关键词行 -->
        <div class="rp-sec">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ $t('关键词行') }}</span>
            <label class="rp-check">
              <input type="checkbox" v-model="useLogRoute" @change="schedulePreview(0)" /> {{ $t('取用 LOG') }}
            </label>
          </div>
          <input class="control rp-full" v-model="route" :disabled="useLogRoute" />
        </div>

        <!-- 电荷 / 自旋 -->
        <div class="rp-sec">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ $t('电荷 / 自旋') }}</span>
            <label class="rp-check">
              <input type="checkbox" v-model="useLogChargeMult" @change="schedulePreview(0)" /> {{ $t('取用 LOG') }}
            </label>
          </div>
          <div class="flex" style="gap:6px;">
            <input class="control" style="flex:1;min-width:0;height:24px;" v-model="charge" :disabled="useLogChargeMult" />
            <input class="control" style="flex:1;min-width:0;height:24px;" v-model="mult" :disabled="useLogChargeMult" />
          </div>
        </div>

        <!-- 文件命名 -->
        <div class="rp-sec">
          <div class="rp-row">
            <span class="label">{{ $t('前缀') }}</span>
            <input class="control rp-num" v-model="prefix" @input="schedulePreview()" />
          </div>
        </div>

        <!-- 操作 -->
        <div class="rp-sec" style="gap:6px;">
          <button class="btn btn-primary h-lg" :disabled="running || !hasSource || !hasOutput || !checkedSteps.length"
                  @click="runExtract(checkedSteps)">
            {{ running ? $t('处理中...') : $t('提取选中（{n}）', { n: checkedSteps.length }) }}
          </button>
          <button class="btn btn-success h-lg" :disabled="running || !hasSource || !hasOutput || !steps.length"
                  @click="runExtract(null)">
            {{ running ? $t('处理中...') : $t('提取全部（{n}）', { n: steps.length }) }}
          </button>
        </div>
      </aside>
    </div>

    <LogViewer :lines="logLines" />

    <!-- 远程目录选择 -->
    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="sessionId"
      :initial-path="browserInitialPath"
      :target="browserTarget"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />
  </div>
</template>

<script>
import LogViewer from '@/components/LogViewer.vue'
import RemoteFileBrowser from '@/components/RemoteFileBrowser.vue'
import EmptyNotice from '@/components/EmptyNotice.vue'
import { pickDirectory, pickFile } from '@/api/dialog'
import { resourceOf, RESOURCE_PRESET_NAMES, DEFAULT_RESOURCE_PRESET } from '@/utils/mlsPresets'
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import { t as $tr } from '@/i18n'

const posixJoin = (dir, name) => `${(dir || '/').replace(/\/+$/, '')}/${name}`.replace(/\/{2,}/g, '/')

export default {
  name: 'ScanExtractView',
  components: { LogViewer, RemoteFileBrowser, EmptyNotice },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, connected, sessionId, username }
  },
  data() {
    return {
      backendUrl: '',
      mode: 'local',
      // 本地
      localLogPath: '',
      localOutputFolder: '',
      // 远程
      remoteFolder: '',
      remoteLogFiles: [],
      remoteLogName: '',
      remoteLogContent: '',
      remoteOutFolder: '',
      browserVisible: false,
      browserInitialPath: '/',
      browserTarget: '',
      // 公共
      logName: '',
      steps: [],
      source: '',
      selectedStepId: null,
      stepContent: '',
      checkedSteps: [],
      selectAll: false,
      prefix: '',
      route: '',
      charge: '0',
      mult: '1',
      useLogRoute: true,
      useLogChargeMult: true,
      mem: '20GB',
      nproc: '8',
      selectedPreset: DEFAULT_RESOURCE_PRESET,
      resourceNames: RESOURCE_PRESET_NAMES,
      addResources: true,
      running: false,
      parsedOnce: false,     // 已解析过 → 中间窗口显示"该文件内不含扫描构象信息"
      noticeHint: '',        // 解析失败原因
      logLines: [],
      _previewTimer: null
    }
  },
  computed: {
    sourceLabel() {
      if (this.source === 'ModRedundant') return $tr('扫描步')
      if (this.source === 'orientation') return $tr('坐标段')
      return ''
    },
    hasSource() {
      return this.mode === 'remote' ? !!this.remoteLogContent : !!this.localLogPath
    },
    inputDisplay() {
      return this.mode === 'remote'
        ? (this.remoteFolder ? this.remoteFolder + (this.remoteLogName ? ' / ' + this.remoteLogName : '') : '')
        : this.localLogPath
    },
    outputDisplay() {
      return this.mode === 'remote' ? this.remoteOutFolder : this.localOutputFolder
    },
    hasOutput() {
      return !!this.outputDisplay
    }
  },
  async mounted() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        this.backendUrl = await window.electronAPI.getBackendUrl()
      } catch (e) {
        this.backendUrl = 'http://127.0.0.1:8002'
      }
    } else {
      this.backendUrl = 'http://127.0.0.1:8002'
    }
  },
  beforeUnmount() {
    if (this._previewTimer) clearTimeout(this._previewTimer)
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      if (this.logLines.length > 200) this.logLines.shift()
    },
    // 计算资源预设（与「生成输入」「修改GJF」共用同一份）
    applyPreset() {
      const p = resourceOf(this.selectedPreset)
      this.mem = p.mem
      this.nproc = p.nproc
      this.addResources = true
      this.schedulePreview(0)
      this.addLog($tr('应用预设: {0}', { 0: this.selectedPreset }), '#87d2ff')
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
        try {
          data = JSON.parse(text)
        } catch (e) {
          data = { detail: text.length > 500 ? text.slice(0, 500) + '…' : text }
        }
      }
      return { ok: resp.ok, status: resp.status, data }
    },

    // 本地用 path，远程用 content（日志已下载到缓存）
    params(stepIds) {
      const body = {
        prefix: this.prefix,
        mem: this.mem,
        nproc: this.nproc,
        add_resources: this.addResources,
        route: this.useLogRoute ? null : this.route,
        charge: this.useLogChargeMult ? null : (parseInt(this.charge, 10) || 0),
        mult: this.useLogChargeMult ? null : (parseInt(this.mult, 10) || 1)
      }
      if (this.mode === 'remote') body.content = this.remoteLogContent
      else body.path = this.localLogPath
      if (stepIds) body.step_ids = stepIds
      return body
    },

    switchMode(m) {
      if (m === 'remote' && !this.connected) {
        this.addLog($tr('请先通过工具栏连接服务器'), '#ffa500')
        return
      }
      if (this.mode === m) return
      this.mode = m
      this.steps = []
      this.checkedSteps = []
      this.selectedStepId = null
      this.stepContent = ''
      this.logName = ''
      this.addLog(m === 'remote' ? $tr('已切换到远程模式，请选择远程目录') : $tr('已切换到本地模式，请选择 LOG 文件'), '#87d2ff')
    },

    // ===== 选择输入 =====
    async chooseInput() {
      if (this.mode === 'remote') {
        this.browserTarget = 'scanDir'
        this.browserInitialPath = this.remoteFolder || `/home/${this.username}`
        this.browserVisible = true
        return
      }
      let p
      try {
        p = await pickFile($tr('选择 Gaussian 扫描 log'), ['log', 'out'])
      } catch (e) {
        this.addLog($tr('选择文件失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!p) return
      this.localLogPath = p
      this.logName = (p.split(/[\\/]/).pop() || '').replace(/\.(log|out)$/i, '')
      if (!this.localOutputFolder) {
        const dir = p.replace(/[\\/][^\\/]*$/, '')
        if (dir && dir !== p) this.localOutputFolder = dir
      }
      this.addLog($tr('已选择 LOG: {0}', { 0: p }), '#87d2ff')
      await this.parseScan()
    },

    // ===== 选择输出 =====
    async chooseOutput() {
      if (this.mode === 'remote') {
        this.browserTarget = 'scanOut'
        this.browserInitialPath = this.remoteOutFolder || this.remoteFolder || `/home/${this.username}`
        this.browserVisible = true
        return
      }
      let p
      try {
        p = await pickDirectory($tr('选择输出文件夹（保存 .gjf）'), this.localOutputFolder || '')
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!p) return
      this.localOutputFolder = p
      this.addLog($tr('输出目录: {0}', { 0: p }), '#87d2ff')
    },

    onBrowserSelect({ target, path, is_dir }) {
      const dir = is_dir ? path : path.replace(/\/[^/]*$/, '') || '/'
      if (target === 'scanDir') {
        this.remoteFolder = dir
        this.addLog($tr('远程目录: {0}', { 0: dir }), '#87d2ff')
        this.loadRemoteLogs()
      } else if (target === 'scanOut') {
        this.remoteOutFolder = dir
        this.addLog($tr('输出目录: {0}', { 0: dir }), '#87d2ff')
      }
    },

    async loadRemoteLogs() {
      this.remoteLogFiles = []
      this.remoteLogName = ''
      this.remoteLogContent = ''
      this.steps = []
      this.stepContent = ''
      if (!this.remoteFolder || !this.sessionId) return
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/remote/ls`,
        { session_id: this.sessionId, path: this.remoteFolder })
      if (!ok) {
        this.addLog($tr('读取远程目录失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.remoteLogFiles = (data.entries || [])
        .filter(e => !e.is_dir && /\.(log|out)$/i.test(e.name))
        .map(e => e.name)
      if (!this.remoteLogFiles.length) {
        this.addLog($tr('远程目录中没有 .log / .out 文件'), '#ffa500')
        return
      }
      this.addLog($tr('找到 {0} 个远程 log', { 0: this.remoteLogFiles.length }), '#87d2ff')
      await this.selectRemoteLog(this.remoteLogFiles[0])
    },

    async selectRemoteLog(name) {
      if (!name) return
      this.remoteLogName = name
      this.logName = name.replace(/\.(log|out)$/i, '')
      const remotePath = posixJoin(this.remoteFolder, name)
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/remote/download`,
        { session_id: this.sessionId, path: remotePath })
      if (!ok) {
        this.addLog($tr('下载 {0} 失败: {1}', { 0: name, 1: data.detail }), '#ff6b6b')
        return
      }
      this.remoteLogContent = data.content || ''
      this.addLog($tr('已下载到缓存: {0}', { 0: name }), '#87d2ff')
      await this.parseScan()
    },

    // ===== 解析 =====
    async parseScan() {
      if (!this.hasSource) {
        this.addLog($tr('请先选择扫描 log'), '#ffa500')
        return
      }
      this.steps = []
      this.checkedSteps = []
      this.selectedStepId = null
      this.stepContent = ''
      this.addLog($tr('开始解析扫描构象...'), '#87d2ff')
      const body = this.mode === 'remote' ? { content: this.remoteLogContent } : { path: this.localLogPath }
      const { ok, status, data } = await this.postJson(`${this.backendUrl}/api/scan/parse`, body)
      this.parsedOnce = true
      if (!ok) {
        this.noticeHint = data.detail || ''
        this.addLog($tr('解析失败({0}): {1}', { 0: status, 1: data.detail }), '#ff6b6b')
        return
      }
      this.noticeHint = ''
      this.steps = data.steps || []
      this.source = data.source || ''
      this.route = data.route || ''
      this.charge = String(data.charge ?? 0)
      this.mult = String(data.mult ?? 1)
      this.addLog($tr('找到 {0} 个扫描点（来源：{1}）', { 0: this.steps.length, 1: this.sourceLabel }), '#7cfc00')
      this.addLog($tr('关键词行: {0}', { 0: this.route }), '#87d2ff')
      if (this.steps.length) this.selectStep(this.steps[0].id)
    },

    selectStep(id) {
      this.selectedStepId = id
      this.previewStep(id)
    },

    async previewStep(id) {
      if (!this.hasSource || !id) return
      const { ok, status, data } = await this.postJson(`${this.backendUrl}/api/scan/preview`,
        { ...this.params([id]) })
      if (!ok) {
        this.stepContent = ''
        this.addLog($tr('生成预览失败({0}): {1}', { 0: status, 1: data.detail }), '#ff6b6b')
        return
      }
      this.stepContent = data.content || ''
    },

    schedulePreview(delay = 350) {
      if (!this.selectedStepId) return
      if (this._previewTimer) clearTimeout(this._previewTimer)
      this._previewTimer = setTimeout(() => this.previewStep(this.selectedStepId), delay)
    },

    toggleAll() {
      this.checkedSteps = this.selectAll ? this.steps.map(s => s.id) : []
    },

    // ===== 提取 =====
    async runExtract(stepIds) {
      if (this.running) return
      if (!this.hasSource) {
        this.addLog($tr('请先选择扫描 log'), '#ffa500')
        return
      }
      if (!this.hasOutput) {
        this.addLog($tr('请先选择输出目录'), '#ffa500')
        return
      }
      this.running = true
      this.logLines = []
      const count = stepIds ? stepIds.length : this.steps.length
      this.addLog($tr('开始提取 {0} 个构象 → {1}', { 0: count, 1: this.outputDisplay }), '#00ff00')

      if (this.mode === 'local') {
        const { ok, status, data } = await this.postJson(`${this.backendUrl}/api/scan/extract`,
          { ...this.params(stepIds), output_folder: this.localOutputFolder })
        if (!ok) {
          this.addLog($tr('提取失败({0}): {1}', { 0: status, 1: data.detail }), '#ff6b6b')
          this.running = false
          return
        }
        ;(data.results || []).forEach(item => {
          if (item.status === 'success') this.addLog($tr('已生成: {0}', { 0: item.output }), '#7cfc00')
          else this.addLog($tr('{0} 失败: {1}', { 0: item.filename, 1: item.message }), '#ff6b6b')
        })
        this.addLog($tr('提取完成，成功 {0}/{1}', { 0: data.success, 1: data.count }), '#00ff00')
        this.running = false
        return
      }

      // 远程：本地生成内容 → 逐帧上传
      const { ok, status, data } = await this.postJson(`${this.backendUrl}/api/scan/build`, this.params(stepIds))
      if (!ok) {
        this.addLog($tr('提取失败({0}): {1}', { 0: status, 1: data.detail }), '#ff6b6b')
        this.running = false
        return
      }
      let success = 0
      const files = data.files || []
      for (let i = 0; i < files.length; i++) {
        const f = files[i]
        const remotePath = posixJoin(this.remoteOutFolder, f.filename)
        const up = await this.postJson(`${this.backendUrl}/api/remote/upload`,
          { session_id: this.sessionId, path: remotePath, content: f.content })
        if (up.ok) {
          success++
          this.addLog($tr('已上传: {0}', { 0: remotePath }), '#7cfc00')
        } else {
          this.addLog($tr('上传失败: {0} - {1}', { 0: f.filename, 1: up.data.detail }), '#ff6b6b')
        }
      }
      this.addLog($tr('提取完成，成功 {0}/{1}', { 0: success, 1: files.length }), '#00ff00')
      this.running = false
    }
  }
}
</script>

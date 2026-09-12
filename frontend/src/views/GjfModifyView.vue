<template>
  <!-- 三栏：左=文件列表 / 中=编辑窗口 / 右=参数调节；下方日志与终端保持不动 -->
  <div class="flex-col h-full" style="gap:6px;overflow:hidden;">

    <div class="flex flex-1 min-h-0" style="gap:6px;">

      <!-- ===== 左侧：文件列表（显示目录内全部文件，便于确认目录是否正确） ===== -->
      <aside class="flex-col mls-panel" style="width:240px;flex-shrink:0;min-height:0;">
        <div class="mls-panel-head">
          <span>{{ workMode === 'log' ? $t('LOG 文件') : $t('GJF 文件') }}</span>
          <div class="flex-center" style="gap:6px;">
            <label class="flex-center" style="gap:4px;font-size:11px;color:var(--c-titlebar-text);cursor:pointer;">
              <input type="checkbox" v-model="selectAll" @change="toggleAll" /> {{ $t('全选') }}
            </label>
            <button class="btn" style="height:20px;padding:0 8px;font-size:11px;" @click="refreshList" :disabled="!inputFolder">{{ $t('刷新') }}</button>
          </div>
        </div>
        <div v-if="inputFolder" class="mls-subhead">
          {{ $t('共 {n} 项 · 可用 {m} 个', { n: allEntries.length, m: listFiles.length }) }}{{ workMode === 'log' ? ' .log/.out' : ' .gjf/.mls' }}
        </div>
        <div style="flex:1;overflow-y:auto;padding:4px 0;min-height:0;">
          <div v-if="!inputFolder" style="color:var(--c-text-3);text-align:center;padding:18px;font-size:13px;">
            {{ $t('请先在右侧选择输入目录') }}
          </div>
          <template v-else>
            <div v-if="!allEntries.length" style="color:var(--c-text-3);text-align:center;padding:18px;font-size:13px;">
              {{ $t('目录为空或无法读取') }}
            </div>
            <div
              v-for="entry in displayEntries"
              :key="(entry.is_dir ? 'D_' : 'F_') + entry.name"
              @click="onEntryClick(entry)"
              @dblclick="onEntryDblClick(entry)"
              :title="entry.is_dir ? $t('双击进入该目录') : (entryMatches(entry) ? $t('双击可重命名') : $t('非当前模式需要的文件，仅用于确认目录内容'))"
              :style="{
                padding: '4px 10px',
                cursor: 'pointer',
                background: activeFile === entry.name ? 'var(--c-hl-a)' : 'transparent',
                borderLeft: activeFile === entry.name ? '3px solid var(--c-accent)' : '3px solid transparent',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: entry.is_dir ? 'var(--c-text)' : (entryMatches(entry) ? 'var(--c-text)' : 'var(--c-text-3)')
              }"
              @mouseenter="e=>e.target.style.background=(activeFile===entry.name) ? 'var(--c-hl-a)' : 'var(--c-hover)'"
              @mouseleave="e=>{ if(activeFile!==entry.name) e.target.style.background='transparent' }"
            >
              <input
                v-if="entryMatches(entry)"
                type="checkbox"
                v-model="checkedFiles"
                :value="entry.name"
                @click.stop
              />
              <span v-else style="width:13px;flex-shrink:0;"></span>
              <span style="flex-shrink:0;font-size:11px;color:var(--c-text-3);">{{ entry.is_dir ? $t('[目录]') : $t('[文件]') }}</span>
              <span v-if="isEditingName(entry.name)" style="flex:1;">
                <input
                  v-model="editingName"
                  @blur="finishRename"
                  @keydown.enter="finishRename"
                  @keydown.esc="cancelRename"
                  @click.stop
                  class="control"
                  style="width:100%;height:24px;font-size:12px;border-color:var(--c-accent);"
                  ref="renameInput"
                />
              </span>
              <span v-else style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ entry.name }}</span>
              <span
                v-if="!entry.is_dir && isMlsName(entry.name)"
                style="flex-shrink:0;font-size:10px;font-weight:700;color:var(--c-accent);"
              >MLS</span>
            </div>
          </template>
        </div>
      </aside>

      <!-- ===== 中间：编辑窗口 ===== -->
      <section class="flex-col mls-panel" style="flex:1;min-width:0;min-height:0;">
        <div class="mls-toolbar" style="justify-content:space-between;">
          <!-- 模式切换：同一页面在「修改 GJF」与「LOG → GJF」之间切换 -->
          <div class="flex-center" style="gap:3px;flex-shrink:0;">
            <button
              class="btn"
              :class="workMode === 'gjf' ? 'btn-primary' : 'btn-default'"
              style="height:22px;padding:0 12px;font-size:12px;"
              @click="switchWorkMode('gjf')"
            >{{ $t('GJF 模式') }}</button>
            <button
              class="btn"
              :class="workMode === 'log' ? 'btn-primary' : 'btn-default'"
              style="height:22px;padding:0 12px;font-size:12px;"
              @click="switchWorkMode('log')"
            >{{ $t('LOG 模式') }}</button>
          </div>
          <div class="flex" style="gap:10px;align-items:center;min-width:0;flex:1;margin-left:6px;">
            <span style="font-weight:700;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ activeFile ? activeFile : $t('未选择文件') }}</span>
            <span v-if="mode === 'remote'" style="color:var(--c-accent);font-size:12px;">{{ $t('(远程)') }}</span>
            <span v-if="workMode === 'log'" style="color:var(--c-text-3);font-size:12px;">{{ $t('LOG → GJF 预览') }}</span>
          </div>
          <div class="flex" style="gap:6px;align-items:center;flex-shrink:0;">
            <button class="btn btn-success" style="height:24px;" @click="saveCurrent" :disabled="!activeFile || saving || (workMode === 'log' && !logPreview)">
              {{ saving ? $t('保存中...') : (workMode === 'log' ? $t('保存为 GJF') : $t('保存')) }}
            </button>
            <button class="btn" style="height:24px;" @click="refreshList" :disabled="!activeFile">
              {{ $t('刷新列表') }}
            </button>
          </div>
        </div>

        <!-- 最终参数预览行：与中间窗口同宽，置于编辑区上方 -->
        <div class="flex-center" style="gap:8px;padding:4px 8px;flex-shrink:0;border-bottom:1px solid var(--c-border);background:var(--c-panel);flex-wrap:wrap;">
          <template v-if="workMode === 'log'">
            <span class="label" style="white-space:nowrap;">{{ $t('LOG 信息') }}</span>
            <span style="font-size:12px;color:var(--c-text-2);white-space:nowrap;">
              <template v-if="logInfo">
                {{ $t('{n} 原子 · {src} 共 {f} 段，取第 {i} 段', { n: logInfo.natoms, src: logInfo.source, f: logInfo.frames, i: logInfo.frame_index }) }} ·
                <span :style="{ color: logInfo.normal_termination ? 'var(--c-ok)' : 'var(--c-warn)' }">
                  {{ logInfo.normal_termination ? $t('正常结束') : (logInfo.error_termination ? $t('异常结束') : $t('未见结束标记')) }}
                </span>
                <span v-if="logInfo.title" style="color:var(--c-text-3);"> · {{ $t('LOG 内标题') }}: {{ logInfo.title }}</span>
              </template>
              <template v-else>{{ $t('选择左侧 LOG 文件后自动解析末帧结构') }}</template>
            </span>
            <label class="flex-center" style="gap:4px;font-size:12px;color:var(--c-text-2);cursor:pointer;white-space:nowrap;">
              <input type="checkbox" v-model="useLogChargeMult" @change="onLogParamsToggle" /> {{ $t('电荷/自旋取用 LOG') }}
            </label>
            <label class="flex-center" style="gap:4px;font-size:12px;color:var(--c-text-2);cursor:pointer;white-space:nowrap;">
              <input type="checkbox" v-model="useLogKeyword" @change="onLogParamsToggle" /> {{ $t('关键词取用 LOG') }}
            </label>
          </template>
          <span class="label" style="white-space:nowrap;">{{ workMode === 'log' ? $t('生成关键词') : $t('最终参数预览') }}</span>
          <input class="control preview" style="flex:1;min-width:180px;height:24px;" :value="workMode === 'log' ? effectiveKeyword : fullKeyword" readonly />
          <span class="label" style="white-space:nowrap;">{{ $t('电荷') }}</span>
          <input class="control" style="width:52px;height:24px;" v-model="charge" :disabled="workMode === 'log' && useLogChargeMult" />
          <span class="label" style="white-space:nowrap;">{{ $t('自旋') }}</span>
          <input class="control" style="width:52px;height:24px;" v-model="mult" :disabled="workMode === 'log' && useLogChargeMult" />
        </div>

        <EmptyNotice
          v-if="workMode === 'log' && logNotice && !logPreview"
          :text="$t('该 LOG 文件内不含可提取的结构信息')"
          :hint="logNotice"
        />
        <textarea
          v-else
          v-model="editorText"
          :disabled="!activeFile"
          class="control"
          style="flex:1;width:100%;border:none;padding:8px;font-family:var(--font-mono);font-size:12px;line-height:1.45;resize:none;background:var(--c-editor);color:var(--c-code);box-shadow:none;"
          spellcheck="false"
        ></textarea>
      </section>

      <!-- ===== 右侧：参数调节 ===== -->
      <aside class="flex-col mls-panel" style="width:290px;flex-shrink:0;overflow-y:auto;padding:8px 10px;gap:8px;min-height:0;">
        <div class="flex-center" style="justify-content:space-between;">
          <span class="label">{{ $t('工作模式') }}</span>
          <div class="flex-center" style="gap:6px;">
            <button class="btn" :class="mode === 'local' ? 'btn-primary' : 'btn-default'" style="height:24px;padding:0 10px;font-size:12px;" @click="switchMode('local')">{{ $t('本地') }}</button>
            <button class="btn" :class="mode === 'remote' ? 'btn-primary' : 'btn-default'" style="height:24px;padding:0 10px;font-size:12px;" @click="switchMode('remote')" :disabled="!remoteConnected">{{ $t('远程') }}</button>
          </div>
        </div>
        <div v-if="mode === 'remote'" style="font-size:12px;color:var(--c-text-2);">
          {{ remoteConnected ? ($t('已连接') + ' ' + remoteStore.displayName) : $t('未连接') }}
        </div>

        <!-- 目录 -->
        <div class="rp-sec">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ workMode === 'log' ? $t('LOG 目录') : $t('输入目录') }}</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="mode==='local' ? selectInputFolder() : openRemoteBrowser('input')" :disabled="mode==='remote' && !remoteConnected">{{ $t('选择…') }}</button>
          </div>
          <div class="rp-hint">{{ inputFolder || $t('未选择') }}</div>
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ workMode === 'log' ? $t('GJF 输出目录') : $t('输出目录') }}</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="mode==='local' ? selectOutputFolder() : openRemoteBrowser('output')" :disabled="mode==='remote' && !remoteConnected">{{ $t('选择…') }}</button>
          </div>
          <div class="rp-hint">{{ outputFolder || (workMode === 'log' ? $t('未选择（默认与 LOG 目录相同）') : $t('未选择')) }}</div>
        </div>

        <!-- 计算资源（预设 / 内存 / 核心数） -->
        <div class="rp-sec">
          <div class="rp-row">
            <span class="label">{{ $t('预设') }}</span>
            <select class="control rp-num" style="font-size:11px;" v-model="selectedPreset" @change="applyPreset">
              <option v-for="name in resourceNames" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div class="rp-row">
            <span class="label">{{ $t('内存') }}</span>
            <input class="control rp-num" v-model="mem" :placeholder="$t('如 20GB')" />
          </div>
          <div class="rp-row">
            <span class="label">{{ $t('核心数') }}</span>
            <input class="control rp-num" v-model="nproc" :placeholder="$t('如 8')" />
          </div>
        </div>

        <!-- 计算参数 -->
        <div class="rp-sec">
          <div class="flex-col" style="gap:4px;">
            <span class="label">{{ $t('计算模式') }}</span>
            <input class="control rp-full" v-model="calcMode" list="calcModePresets" />
            <datalist id="calcModePresets">
              <option v-for="preset in calcModePresets" :key="preset" :value="preset" />
            </datalist>
          </div>
          <div class="flex-col" style="gap:4px;">
            <span class="label">{{ $t('泛函 / 基组') }}</span>
            <div class="flex" style="gap:6px;">
              <input class="control" style="flex:1;min-width:0;height:24px;" v-model="functional" list="functionalPresets" :placeholder="$t('如 b3lyp')" />
              <input class="control" style="flex:1;min-width:0;height:24px;" v-model="basis" list="basisPresets" :placeholder="$t('如 6-31g(d,p)')" />
            </div>
            <datalist id="functionalPresets">
              <option v-for="preset in functionalPresets" :key="preset" :value="preset" />
            </datalist>
            <datalist id="basisPresets">
              <option v-for="preset in basisPresets" :key="preset" :value="preset" />
            </datalist>
          </div>
          <div class="rp-row">
            <span class="label">{{ $t('前缀') }}</span>
            <input class="control rp-num" v-model="prefix" :placeholder="$t('如 opt_')" />
          </div>
        </div>

        <!-- LOG 模式专属：从 LOG 回填参数 -->
        <div v-if="workMode === 'log'" class="rp-sec">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ $t('LOG 检出关键词') }}</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="applyLogToParams" :disabled="!logInfo || !logInfo.route_first">{{ $t('填入参数栏') }}</button>
          </div>
          <div class="rp-hint">{{ (logInfo && logInfo.route_first) || $t('未检出关键词行') }}</div>
          <div class="rp-row">
            <span class="label">{{ $t('输出文件名') }}</span>
            <span class="rp-hint" style="text-align:right;">{{ logOutputName || '—' }}</span>
          </div>
        </div>

        <!-- 操作 -->
        <div class="rp-sec" style="gap:8px;padding-top:10px;">
          <template v-if="workMode === 'log'">
            <button class="btn btn-primary h-lg" @click="convertCurrentLog" :disabled="!logFile || !logPreview || running">
              {{ running ? $t('处理中...') : $t('转换当前 LOG → GJF') }}
            </button>
            <button class="btn btn-success h-lg" @click="batchConvertLogs" :disabled="running || !inputFolder || !checkedFiles.length">
              {{ running ? $t('处理中...') : $t('批量转换（{n}）', { n: checkedFiles.length }) }}
            </button>
            <button class="btn h-lg" @click="switchToGjfAfterConvert" :disabled="!logPreview">
              {{ $t('转到 GJF 模式继续修改') }}
            </button>
          </template>
          <template v-else>
            <button class="btn btn-primary h-lg" @click="applyParamsAndSave" :disabled="!currentFile">{{ $t('保存并应用参数至当前文件') }}</button>
            <button class="btn btn-success h-lg" @click="startBatchModify" :disabled="running || !inputFolder || !outputFolder || !checkedFiles.length">
              {{ running ? $t('处理中...') : $t('批量修改（{n}）', { n: checkedFiles.length }) }}
            </button>
          </template>
        </div>
      </aside>
    </div>

    <!-- 日志区域（保持在底部、终端之上，与其他页面一致） -->
    <LogViewer :lines="logLines" />

    <!-- 远程文件浏览器组件 -->
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
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import LogViewer from '@/components/LogViewer.vue'
import EmptyNotice from '@/components/EmptyNotice.vue'
import RemoteFileBrowser from '@/components/RemoteFileBrowser.vue'
import { pickDirectory } from '@/api/dialog'
import { resourceOf, RESOURCE_PRESET_NAMES, DEFAULT_RESOURCE_PRESET } from '@/utils/mlsPresets'
import { t as $tr } from '@/i18n'
const posixpath = {
  join: (...segments) => segments.filter(s => s && s !== '').join('/').replace(/\/+/g, '/')
};


export default {
  name: 'GjfModifyView',
  components: { LogViewer, RemoteFileBrowser, EmptyNotice },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected: remoteConnected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, remoteConnected, sessionId, username }
  },
  data() {
    return {
      mode: 'local',
      // 页面工作模式：'gjf' = 修改 GJF，'log' = LOG → GJF（同一页面切换）
      workMode: 'gjf',
      // 本地/远程目录分开记忆，避免切换模式时相互污染
      localInputFolder: '',
      localOutputFolder: '',
      remoteInputFolder: '',
      remoteOutputFolder: '',
      prefix: '',
      fileList: [],
      selectedIndex: -1,
      currentFile: null,
      currentContent: '',
      allEntries: [],          // 输入目录下的全部条目（含非目标扩展名的文件与子目录）
      // ===== LOG 模式专用状态 =====
      logFileList: [],
      logIndex: -1,
      logFile: null,
      logPreview: '',
      logInfo: null,
      logGenName: '',
      logNotice: '',           // LOG 解析失败原因（显示在中间窗口）
      _logText: '',
      _logTextFile: '',
      _logInfoFile: '',
      _logPreviewTimer: null,
      useLogChargeMult: true,
      useLogKeyword: true,     // 默认沿用 LOG 里原任务的关键词，避免误用右侧默认泛函
      mem: '20GB',
      nproc: '8',
      calcMode: '#p opt',
      functional: 'b3lyp',
      basis: '6-31g(d,p)',
      charge: '0',
      mult: '1',
      selectedPreset: DEFAULT_RESOURCE_PRESET,
      resourceNames: RESOURCE_PRESET_NAMES,
      calcModePresets: [
        '#p opt',
        '#p opt freq',
        '#p td=(50-50,nstates=10)',
        '#p td opt',
        '#p td opt freq'
      ],
      functionalPresets: ['b3lyp', 'wb97xd', 'm062x', 'cam-b3lyp', 'pbe1pbe'],
      basisPresets: [
        '6-31g(d,p)', '6-31g(d)', '6-311g(d,p)',
        '6-311+g(d,p)', 'def2svp', 'def2tzvp', 'def2tzvpp'
      ],
      running: false,
      saving: false,
      ws: null,
      logLines: [],
      logKey: 0,
      checkedFiles: [],
      selectAll: false,
      editingIndex: -1,
      editingName: '',
      browserVisible: false,
      browserInitialPath: '/',
      browserTarget: '',
      _remoteCacheFiles: [],
      backendUrl: ''
    }
  },
  computed: {
    // 当前工作模式对应的左侧文件列表
    listFiles() {
      return this.workMode === 'gjf' ? this.fileList : this.logFileList
    },
    // 当前工作模式对应的选中下标
    activeIndex: {
      get() {
        return this.workMode === 'gjf' ? this.selectedIndex : this.logIndex
      },
      set(v) {
        if (this.workMode === 'gjf') this.selectedIndex = v
        else this.logIndex = v
      }
    },
    // 当前工作模式对应的选中文件名
    activeFile() {
      return this.workMode === 'gjf' ? this.currentFile : this.logFile
    },
    // 中间编辑区内容：GJF 模式为文件内容，LOG 模式为生成的 GJF 预览
    editorText: {
      get() {
        return this.workMode === 'gjf' ? this.currentContent : this.logPreview
      },
      set(v) {
        if (this.workMode === 'gjf') this.currentContent = v
        else this.logPreview = v
      }
    },
    // 左侧列表显示：目录 → 匹配文件 → 其它文件（全部列出，便于确认目录是否正确）
    displayEntries() {
      const rank = (e) => (e.is_dir ? 0 : (this.entryMatches(e) ? 1 : 2))
      return [...this.allEntries].sort((a, b) => {
        const ra = rank(a), rb = rank(b)
        if (ra !== rb) return ra - rb
        return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
      })
    },
    logOutputName() {
      if (!this.logFile) return ''
      const stem = this.logFile.replace(/\.(log|out)$/i, '')
      return `${this.prefix}${stem}.gjf`
    },
    // LOG 模式下实际写入 GJF 的关键词行
    effectiveKeyword() {
      if (this.workMode === 'log' && this.useLogKeyword && this.logInfo && this.logInfo.route_first) {
        return this.logInfo.route_first
      }
      return this.fullKeyword
    },
    // 目录路径代理：按当前模式读写各自的记忆字段（本地/远程互不串用）
    inputFolder: {
      get() {
        return this.mode === 'local' ? this.localInputFolder : this.remoteInputFolder
      },
      set(v) {
        if (this.mode === 'local') this.localInputFolder = v
        else this.remoteInputFolder = v
      }
    },
    outputFolder: {
      get() {
        return this.mode === 'local' ? this.localOutputFolder : this.remoteOutputFolder
      },
      set(v) {
        if (this.mode === 'local') this.localOutputFolder = v
        else this.remoteOutputFolder = v
      }
    },
    fullKeyword() {
      const mode = this.calcMode.trim()
      const func = this.functional.trim()
      const bas = this.basis.trim()
      let funcBasis = ''
      if (func && bas) funcBasis = `${func}/${bas}`
      else if (func) funcBasis = func
      else if (bas) funcBasis = bas
      if (!mode && !funcBasis) return ''
      if (!mode) return funcBasis
      if (!funcBasis) return mode
      return `${mode} ${funcBasis}`
    }
  },
  async mounted() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        this.backendUrl = await window.electronAPI.getBackendUrl()
      } catch (e) {
        console.error($tr('获取后端地址失败:'), e)
        this.backendUrl = 'http://127.0.0.1:8002'
      }
    } else {
      this.backendUrl = 'http://127.0.0.1:8002'
    }
  },
  watch: {
    inputFolder(newVal, oldVal) {
      if (newVal && newVal !== oldVal) {
        if (this.mode === 'remote') {
          this.clearCacheIfRemote()
        }
        this.reloadActiveList()
      } else if (!newVal) {
        this.clearCacheIfRemote()
        this.resetLists()
      }
    },
    mode(newVal, oldVal) {
      if (oldVal === 'remote' && newVal !== 'remote') {
        this.clearCacheIfRemote()
      }
      this.resetLists()
      if (this.inputFolder) {
        this.reloadActiveList()
      }
    },
    workMode() {
      this.resetLists()
      if (this.inputFolder) {
        this.reloadActiveList()
      }
    },
    checkedFiles(val) {
      this.selectAll = val.length === this.listFiles.length && this.listFiles.length > 0
    },
    // LOG 模式下参数变化后自动重算预览
    fullKeyword() { this.scheduleLogPreview() },
    mem() { this.scheduleLogPreview() },
    nproc() { this.scheduleLogPreview() },
    charge() { this.scheduleLogPreview() },
    mult() { this.scheduleLogPreview() }
  },
  beforeUnmount() {
    if (this.ws) this.ws.close()
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 200) this.logLines.shift()
    },
    toggleAll() {
      this.checkedFiles = this.selectAll ? [...this.listFiles] : []
    },

    // ===== 目录内全部文件列表（确认目录用） =====
    // GJF 模式同时接受 .mls（分子坐标文件，读入后直接按当前参数生成 GJF 内容）
    entryMatches(entry) {
      if (!entry || entry.is_dir) return false
      const n = (entry.name || '').toLowerCase()
      return this.workMode === 'log' ? /\.(log|out)$/.test(n) : /\.(gjf|mls)$/.test(n)
    },
    isMlsName(name) {
      return /\.mls$/i.test(name || '')
    },
    entryFullPath(name) {
      if (this.mode === 'remote') return posixpath.join(this.inputFolder, name)
      return `${(this.inputFolder || '').replace(/[\\/]+$/, '')}\\${name}`
    },
    isEditingName(name) {
      return this.editingIndex >= 0 && this.listFiles[this.editingIndex] === name
    },
    startRenameByFile(name) {
      const idx = this.listFiles.indexOf(name)
      if (idx >= 0) this.startRename(idx)
    },
    onEntryClick(entry) {
      if (entry.is_dir) return                       // 目录：双击进入
      if (this.entryMatches(entry)) {
        if (this.workMode === 'gjf' && this.isMlsName(entry.name)) {
          this.openMlsAsGjf(entry.name)
          return
        }
        const idx = this.listFiles.indexOf(entry.name)
        if (idx >= 0) this.selectFile(idx)
        return
      }
      this.addLog($tr('{0} 不是 {1} 文件，仅用于确认目录内容', { 0: entry.name, 1: this.workMode === 'log' ? '.log / .out' : '.gjf / .mls' }), '#ffa500')
    },
    onEntryDblClick(entry) {
      if (entry.is_dir) {
        const target = this.entryFullPath(entry.name)
        this.addLog($tr('进入子目录: {0}', { 0: target }), '#87d2ff')
        this.inputFolder = target
        return
      }
      if (this.entryMatches(entry)) this.startRenameByFile(entry.name)
    },
    // 拉取目录下全部条目（本地 /api/local/ls、远程 /api/remote/ls）
    async refreshAllEntries() {
      if (!this.inputFolder) {
        this.allEntries = []
        return
      }
      try {
        let result
        if (this.mode === 'local') {
          result = await this.postJson(`${this.backendUrl}/api/local/ls`, { path: this.inputFolder })
        } else {
          if (!this.remoteConnected) { this.allEntries = []; return }
          result = await this.postJson(`${this.backendUrl}/api/remote/ls`, {
            session_id: this.sessionId,
            path: this.inputFolder
          })
        }
        this.allEntries = result.ok ? (result.data.entries || []) : []
      } catch (e) {
        this.allEntries = []
      }
    },

    // ===== 工作模式切换（GJF / LOG）与列表重置 =====
    switchWorkMode(m) {
      if (this.workMode === m) return
      this.workMode = m
      this.addLog(m === 'log'
        ? $tr('已切换到 LOG 模式：选择 .log/.out 文件即可提取末帧坐标生成 GJF')
        : $tr('已切换到 GJF 模式：可对生成的 GJF 继续调参 / 批量修改'), '#87d2ff')
    },
    resetLists() {
      this.fileList = []
      this.selectedIndex = -1
      this.currentFile = null
      this.currentContent = ''
      this.allEntries = []
      this.logFileList = []
      this.logIndex = -1
      this.logFile = null
      this.logPreview = ''
      this.logInfo = null
      this.logGenName = ''
      this._logText = ''
      this._logTextFile = ''
      this._logInfoFile = ''
      this.checkedFiles = []
      this.selectAll = false
    },
    reloadActiveList() {
      if (this.workMode === 'log') {
        if (this.mode === 'local') this.loadLogListLocal()
        else this.loadLogListRemote()
      } else {
        if (this.mode === 'local') this.loadFileListLocal()
        else this.loadFileListRemote()
      }
    },

    // ===== 自动清除远程缓存 =====
    async clearCacheIfRemote() {
      if (this.mode === 'remote' && this.remoteConnected && this.sessionId) {
        try {
          await fetch(`${this.backendUrl}/api/remote/cache?session_id=${this.sessionId}`, {
            method: 'DELETE'
          })
        } catch (e) {
          console.warn($tr('清除缓存失败:'), e)
        }
      }
    },

    // ===== 刷新列表（清除缓存 + 重新加载） =====
    async refreshList() {
      if (!this.inputFolder) {
        this.addLog($tr('请先选择输入文件夹'), '#ffa500')
        return
      }
      if (this.mode === 'remote' && this.remoteConnected) {
        try {
          const resp = await fetch(`${this.backendUrl}/api/remote/cache?session_id=${this.sessionId}`, {
            method: 'DELETE'
          })
          if (resp.ok) {
            this.addLog($tr('缓存已自动清除'), '#7cfc00')
          } else {
            const data = await resp.json()
            this.addLog($tr('清除缓存失败: {0}', { 0: data.detail || $tr('未知错误') }), '#ff6b6b')
          }
        } catch (e) {
          this.addLog($tr('清除缓存失败: {0}', { 0: e.message }), '#ff6b6b')
        }
      }
      if (this.mode === 'local') {
        if (this.workMode === 'log') await this.loadLogListLocal()
        else await this.loadFileListLocal()
      } else {
        if (this.workMode === 'log') await this.loadLogListRemote()
        else await this.loadFileListRemote()
      }
      this.addLog($tr('文件列表已刷新'), '#87d2ff')
    },

    // ===== 模式切换（本地/远程） =====
    switchMode(mode) {
      if (mode === 'remote' && !this.remoteConnected) {
        this.addLog($tr('请先通过工具栏连接服务器'), '#ffa500')
        return
      }
      if (this.mode !== mode && this.mode === 'remote') {
        this.clearCacheIfRemote()
      }
      this.mode = mode
      this.resetLists()
      if (this.inputFolder) {
        this.reloadActiveList()
      }
    },

    // ===== 选择文件夹（本地） =====
    selectInputFolder() {
      this.selectLocalFolder('inputFolder', $tr('选择包含 .gjf 的文件夹'))
    },
    selectOutputFolder() {
      this.selectLocalFolder('outputFolder', $tr('选择输出文件夹'))
    },
    async selectLocalFolder(variable, title) {
      const initial = this[variable] || this.inputFolder || this.outputFolder || ''
      let path
      try {
        path = await pickDirectory(title, initial)
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      const changed = this[variable] !== path
      this[variable] = path
      this.addLog($tr('选择目录：{0} → {1}', { 0: title, 1: path }), '#87d2ff')
      if (variable === 'inputFolder') {
        this.checkedFiles = []
        this.selectAll = false
        // 路径变化时由 watcher 触发加载；路径没变（重复选择同一目录）时这里手动刷新
        if (!changed) this.reloadActiveList()
      }
    },

    // ===== 远程目录浏览器 =====
    openRemoteBrowser(target) {
      if (!this.remoteConnected) {
        this.addLog($tr('请先通过工具栏连接服务器'), '#ffa500')
        return
      }
      let initialPath = '/'
      if (target === 'input' && this.inputFolder) initialPath = this.inputFolder
      else if (target === 'output' && this.outputFolder) initialPath = this.outputFolder
      else initialPath = `/home/${this.username}`
      this.browserInitialPath = initialPath
      this.browserTarget = target
      this.browserVisible = true
    },
    onBrowserSelect({ target, path, is_dir, name }) {
      if (target === 'input') {
        if (is_dir) {
          this.inputFolder = path
          if (this.mode === 'remote') {
            this.clearCacheIfRemote()
            this.loadFileListRemote()
          }
        } else {
          this.addLog($tr('请选择目录而非文件'), '#ffa500')
        }
      } else if (target === 'output') {
        if (is_dir) {
          this.outputFolder = path
        } else {
          this.addLog($tr('请选择目录而非文件'), '#ffa500')
        }
      }
      this.addLog($tr('已选择: {0}', { 0: path }), '#87d2ff')
    },

    // ===== 加载文件列表 =====
    async loadFileListLocal() {
      if (!this.inputFolder) return
      try {
        const normalizedPath = this.inputFolder.replace(/\\/g, '/')
        const url = `${this.backendUrl}/api/gjf/list?path=${encodeURIComponent(normalizedPath)}`
        const response = await fetch(url)
        const data = await response.json()
        if (response.ok) {
          this.fileList = data.files || []
          this.checkedFiles = this.checkedFiles.filter(f => this.fileList.includes(f))
          if (this.fileList.length) {
            this.selectedIndex = 0
            this.loadFileContentLocal(this.fileList[0])
          } else {
            this.selectedIndex = -1
            this.currentFile = null
            this.currentContent = ''
          }
          this.addLog($tr('找到 {0} 个 .gjf 文件 (本地)', { 0: this.fileList.length }), '#87d2ff')
          await this.refreshAllEntries()
        } else {
          this.addLog($tr('加载文件列表失败: {0}', { 0: data.detail }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('加载文件列表失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    async loadFileListRemote() {
      if (!this.inputFolder || !this.remoteConnected) return
      try {
        const listResp = await fetch(`${this.backendUrl}/api/remote/ls`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            path: this.inputFolder
          })
        })
        const listData = await listResp.json()
        if (!listResp.ok) {
          this.addLog($tr('获取远程文件列表失败: {0}', { 0: listData.detail }), '#ff6b6b')
          return
        }
        const allEntries = listData.entries || []
        this.allEntries = allEntries
        const gjfFiles = allEntries.filter(e => !e.is_dir && e.name.endsWith('.gjf')).map(e => e.name)
        this.fileList = gjfFiles
        this.checkedFiles = this.checkedFiles.filter(f => this.fileList.includes(f))
        if (!this.fileList.length) {
          this.addLog($tr('远程目录中没有 .gjf 文件'), '#ffa500')
          this.selectedIndex = -1
          this.currentFile = null
          this.currentContent = ''
          return
        }

        this.addLog($tr('正在下载 {0} 个远程文件到本地缓存...', { 0: this.fileList.length }), '#87d2ff')
        const remotePaths = this.fileList.map(f => posixpath.join(this.inputFolder, f))
        const downloadResp = await fetch(`${this.backendUrl}/api/remote/batch-download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            paths: remotePaths
          })
        })
        const downloadData = await downloadResp.json()
        if (!downloadResp.ok) {
          this.addLog($tr('批量下载失败: {0}', { 0: downloadData.detail }), '#ff6b6b')
          return
        }
        const results = downloadData.results || []
        const successCount = results.filter(r => r.status === 'success').length
        this.addLog($tr('成功下载 {0}/{1} 个文件到缓存', { 0: successCount, 1: this.fileList.length }), '#87d2ff')
        if (successCount === 0) {
          this.addLog($tr('下载失败，请检查网络或权限'), '#ff6b6b')
          return
        }

        this.selectedIndex = 0
        this.loadFileContentRemote(this.fileList[0])
      } catch (e) {
        this.addLog($tr('加载远程文件列表失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 刷新列表并保持当前选中文件（保存/应用后调用，让用户看到磁盘上的最新内容） =====
    async refreshListKeepSelection() {
      const target = this.currentFile
      await this.refreshList()
      if (target) {
        const idx = this.fileList.indexOf(target)
        if (idx >= 0) this.selectFile(idx)
      }
    },

    // ===== 选中文件 =====
    selectFile(idx) {
      if (idx < 0 || idx >= this.listFiles.length) return
      if (this.workMode === 'log') {
        this.selectLogFile(idx)
        return
      }
      this.selectedIndex = idx
      if (this.mode === 'remote') {
        this.loadFileContentRemote(this.fileList[idx])
      } else {
        this.loadFileContentLocal(this.fileList[idx])
      }
    },

    // ===== 加载文件内容（本地） =====
    async loadFileContentLocal(filename) {
      if (!this.inputFolder) return
      const fullPath = `${this.inputFolder}\\${filename}`
      try {
        const response = await fetch(`${this.backendUrl}/api/gjf/read`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: fullPath })
        })
        const data = await response.json()
        if (response.ok) {
          this.currentFile = filename
          this.currentContent = data.content
        } else {
          this.addLog($tr('读取文件失败: {0}', { 0: data.detail }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('读取文件失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 读取 .mls（分子坐标）并按当前参数生成 GJF 内容 =====
    // .mls 仅含坐标，没有 route 信息，因此用右侧当前参数（mem/nproc/泛函/基组/电荷/自旋）现场生成
    async openMlsAsGjf(filename) {
      if (!this.inputFolder) return
      if (this.mode === 'remote') {
        this.addLog($tr('远程目录暂不支持直接读取 .mls，请先下载到本地：{0}', { 0: filename }), '#ffa500')
        return
      }
      const fullPath = `${this.inputFolder}\\${filename}`
      const stem = filename.replace(/\.mls$/i, '')
      try {
        const response = await fetch(`${this.backendUrl}/api/mol/to-input`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: fullPath,
            target: 'gaussian',
            functional: this.functional,
            basis: this.basis,
            calc: this.calcMode,
            mem: this.mem,
            nproc: this.nproc,
            charge: parseInt(this.charge || '0', 10) || 0,
            mult: parseInt(this.mult || '1', 10) || 1,
            filename: stem
          })
        })
        const data = await response.json()
        if (!response.ok) {
          this.addLog($tr('读取 .mls 失败: {0}', { 0: data.detail }), '#ff6b6b')
          return
        }
        this.selectedIndex = -1
        this.currentFile = data.filename
        this.currentContent = data.content
        this.addLog($tr('已从 {0} 生成 {1}（{2} 个原子，保存后写入磁盘）', { 0: filename, 1: data.filename, 2: data.n_atoms }), '#7cfc00')
      } catch (e) {
        this.addLog($tr('读取 .mls 失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 加载文件内容（远程-从缓存读取） =====
    async loadFileContentRemote(filename) {
      if (!this.sessionId) return
      try {
        const response = await fetch(`${this.backendUrl}/api/remote/cache/read`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            path: filename
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.currentFile = filename
          this.currentContent = data.content
        } else {
          this.addLog($tr('缓存读取失败，尝试重新下载: {0}', { 0: filename }), '#ffa500')
          await this.downloadSingleFile(filename)
        }
      } catch (e) {
        this.addLog($tr('读取缓存文件失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 单独下载文件（备用） =====
    async downloadSingleFile(filename) {
      const remotePath = posixpath.join(this.inputFolder, filename)
      try {
        const response = await fetch(`${this.backendUrl}/api/remote/download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            path: remotePath
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.currentFile = filename
          this.currentContent = data.content
          this.addLog($tr('重新下载成功: {0}', { 0: filename }), '#7cfc00')
        } else {
          this.addLog($tr('下载失败: {0}', { 0: data.detail }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('下载失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 保存入口（按工作模式分派） =====
    async saveCurrent() {
      if (this.workMode === 'log') {
        await this.saveLogAsGjf()
        return
      }
      await this.saveCurrentFile()
    },

    // ===== 保存文件 =====
    async saveCurrentFile() {
      if (!this.currentFile) return
      if (this.mode === 'remote') {
        await this.saveFileRemote()
      } else {
        await this.saveFileLocal()
      }
    },

    async saveFileLocal() {
      const fullPath = `${this.inputFolder}\\${this.currentFile}`
      this.saving = true
      let ok = false
      try {
        const response = await fetch(`${this.backendUrl}/api/gjf/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: fullPath, content: this.currentContent })
        })
        const data = await response.json()
        if (response.ok) {
          ok = true
          this.addLog($tr('保存成功: {0} (本地)', { 0: this.currentFile }), '#7cfc00')
        } else {
          this.addLog($tr('保存失败: {0}', { 0: data.detail }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('保存失败: {0}', { 0: e.message }), '#ff6b6b')
      }
      this.saving = false
      return ok
    },

    async saveFileRemote() {
      this.saving = true
      let ok = false
      try {
        const outputRemotePath = posixpath.join(this.inputFolder, this.currentFile)
        const uploadResp = await fetch(`${this.backendUrl}/api/remote/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            path: outputRemotePath,
            content: this.currentContent
          })
        })
        const uploadData = await uploadResp.json()
        if (uploadResp.ok) {
          ok = true
          this.addLog($tr('上传成功: {0} (远程)', { 0: this.currentFile }), '#7cfc00')
        } else {
          this.addLog($tr('上传失败: {0}', { 0: uploadData.detail }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('保存失败: {0}', { 0: e.message }), '#ff6b6b')
      }
      this.saving = false
      return ok
    },

    // ===== 重命名 =====
    startRename(idx) {
      this.editingIndex = idx
      this.editingName = this.listFiles[idx]
      this.$nextTick(() => {
        const input = this.$refs.renameInput
        if (input) { input.focus(); input.select() }
      })
    },
    async finishRename() {
      const idx = this.editingIndex
      if (idx === -1) return
      const oldName = this.listFiles[idx]
      const newName = this.editingName.trim()
      if (!newName || newName === oldName) {
        this.cancelRename(); return
      }
      if (this.listFiles.some((f, i) => i !== idx && f === newName)) {
        this.addLog($tr('文件名 "{0}" 已存在', { 0: newName }), '#ff6b6b')
        this.cancelRename(); return
      }
      if (this.mode === 'remote') {
        await this.renameFileRemote(oldName, newName, idx)
      } else {
        await this.renameFileLocal(oldName, newName, idx)
      }
      this.cancelRename()
    },
    async renameFileLocal(oldName, newName, idx) {
      try {
        const response = await fetch(`${this.backendUrl}/api/gjf/rename`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            folder: this.inputFolder,
            old_name: oldName,
            new_name: newName
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.listFiles[idx] = newName
          if (this.currentFile === oldName) this.currentFile = newName
          if (this.logFile === oldName) this.logFile = newName
          const checkedIdx = this.checkedFiles.indexOf(oldName)
          if (checkedIdx !== -1) this.checkedFiles[checkedIdx] = newName
          this.addLog($tr('重命名成功: {0} -> {1} (本地)', { 0: oldName, 1: newName }), '#7cfc00')
          if (this.workMode === 'gjf' && this.currentFile === newName) this.loadFileContentLocal(newName)
        } else {
          this.addLog($tr('重命名失败: {0}', { 0: data.detail }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('重命名失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    async renameFileRemote(oldName, newName, idx) {
      const oldPath = posixpath.join(this.inputFolder, oldName)
      const newPath = posixpath.join(this.inputFolder, newName)
      try {
        const renameResp = await fetch(`${this.backendUrl}/api/remote/rename`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            old_path: oldPath,
            new_path: newPath
          })
        })
        const renameData = await renameResp.json()
        if (!renameResp.ok) throw new Error(renameData.detail || $tr('远程重命名失败'))
        await fetch(`${this.backendUrl}/api/remote/cache/write`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            path: newName,
            content: this.currentContent
          })
        })
        this.fileList[idx] = newName
        if (this.currentFile === oldName) this.currentFile = newName
        if (this.logFile === oldName) this.logFile = newName
        const checkedIdx = this.checkedFiles.indexOf(oldName)
        if (checkedIdx !== -1) this.checkedFiles[checkedIdx] = newName
        this.addLog($tr('重命名成功: {0} -> {1} (远程)', { 0: oldName, 1: newName }), '#7cfc00')
        if (this.workMode === 'gjf' && this.currentFile === newName) this.loadFileContentRemote(newName)
      } catch (e) {
        this.addLog($tr('重命名失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    cancelRename() {
      this.editingIndex = -1
      this.editingName = ''
    },

    // ===== 预设应用 =====
    applyPreset() {
      const preset = resourceOf(this.selectedPreset)
      this.mem = preset.mem
      this.nproc = preset.nproc
      this.addLog($tr('应用预设: {0}', { 0: this.selectedPreset }), '#87d2ff')
    },

    // 统一的 GET + 容错 JSON 解析
    async getJson(url) {
      const resp = await fetch(url)
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

    // 统一的 POST + 容错 JSON 解析：后端返回非 JSON（如纯文本 500）时也不会抛
    // "Unexpected token ... is not valid JSON"，而是把原文当 detail 交给日志/提示显示
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

    // ==================================================================
    //  LOG → GJF（与「修改 GJF」同页，仅切换工作模式）
    // ==================================================================

    // 共用参数（LOG 模式生成 GJF 时使用）
    logParams() {
      return {
        prefix: this.prefix,
        mem: this.mem,
        nproc: this.nproc,
        keyword: this.fullKeyword,
        charge: this.charge,
        mult: this.mult,
        use_log_charge_mult: this.useLogChargeMult,
        use_log_keyword: this.useLogKeyword
      }
    },

    // 列出本地 LOG / OUT 文件
    async loadLogListLocal() {
      if (!this.inputFolder) return
      try {
        const normalizedPath = this.inputFolder.replace(/\\/g, '/')
        const url = `${this.backendUrl}/api/gjf/log-list?path=${encodeURIComponent(normalizedPath)}`
        const { ok, status, data } = await this.getJson(url)
        if (!ok) {
          this.addLog($tr('加载 LOG 列表失败({0}): {1}', { 0: status, 1: data.detail }), '#ff6b6b')
          return
        }
        this.logFileList = data.files || []
        this.checkedFiles = this.checkedFiles.filter(f => this.logFileList.includes(f))
        this.addLog($tr('找到 {0} 个 LOG 文件 (本地)', { 0: this.logFileList.length }), '#87d2ff')
        await this.refreshAllEntries()
        if (this.logFileList.length) {
          this.selectLogFile(0)
        } else {
          this.logIndex = -1
          this.logFile = null
          this.logPreview = ''
          this.logInfo = null
        }
      } catch (e) {
        this.addLog($tr('加载 LOG 列表失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // 列出远程 LOG / OUT 文件（复用远程 ls + 批量下载到缓存）
    async loadLogListRemote() {
      if (!this.inputFolder || !this.remoteConnected) return
      try {
        const listResp = await fetch(`${this.backendUrl}/api/remote/ls`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, path: this.inputFolder })
        })
        const listData = await listResp.json()
        if (!listResp.ok) {
          this.addLog($tr('获取远程 LOG 列表失败: {0}', { 0: listData.detail }), '#ff6b6b')
          return
        }
        const entries = listData.entries || []
        this.allEntries = entries
        this.logFileList = entries
          .filter(e => !e.is_dir && /\.(log|out)$/i.test(e.name))
          .map(e => e.name)
        this.checkedFiles = this.checkedFiles.filter(f => this.logFileList.includes(f))
        if (!this.logFileList.length) {
          this.addLog($tr('远程目录中没有 .log / .out 文件'), '#ffa500')
          this.logIndex = -1
          this.logFile = null
          this.logPreview = ''
          this.logInfo = null
          return
        }
        this.addLog($tr('找到 {0} 个 LOG 文件，正在下载到本地缓存...', { 0: this.logFileList.length }), '#87d2ff')
        const remotePaths = this.logFileList.map(f => posixpath.join(this.inputFolder, f))
        const downloadResp = await fetch(`${this.backendUrl}/api/remote/batch-download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, paths: remotePaths })
        })
        const downloadData = await downloadResp.json()
        if (!downloadResp.ok) {
          this.addLog($tr('批量下载失败: {0}', { 0: downloadData.detail }), '#ff6b6b')
          return
        }
        const results = downloadData.results || []
        this.addLog($tr('成功下载 {0}/{1} 个 LOG 到缓存', { 0: results.filter(r => r.status === 'success').length, 1: this.logFileList.length }), '#87d2ff')
        this.selectLogFile(0)
      } catch (e) {
        this.addLog($tr('加载远程 LOG 列表失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    selectLogFile(idx) {
      if (idx < 0 || idx >= this.logFileList.length) return
      this.logIndex = idx
      this.logFile = this.logFileList[idx]
      this._logText = ''
      this._logTextFile = ''
      this._logInfoFile = ''
      this.logGenName = ''
      this.buildLogPreview(true)
    },

    // 读取远程文件内容（同时写入后端缓存）
    async fetchRemoteContent(filename) {
      try {
        const remotePath = posixpath.join(this.inputFolder, filename)
        const { ok, data } = await this.postJson(`${this.backendUrl}/api/remote/download`, {
          session_id: this.sessionId,
          path: remotePath
        })
        if (!ok) {
          this.addLog($tr('下载 {0} 失败: {1}', { 0: filename, 1: data.detail }), '#ff6b6b')
          return null
        }
        return data.content
      } catch (e) {
        this.addLog($tr('下载 {0} 失败: {1}', { 0: filename, 1: e.message }), '#ff6b6b')
        return null
      }
    },

    // 解析当前 LOG（取末帧坐标）并生成 GJF 预览
    async buildLogPreview(forceReparse = false) {
      if (!this.logFile) return
      const needParse = forceReparse || !this.logInfo || this._logInfoFile !== this.logFile
      try {
        if (needParse) {
          let parseBody
          if (this.mode === 'local') {
            parseBody = { path: `${this.inputFolder}\\${this.logFile}` }
          } else {
            if (!this._logText || this._logTextFile !== this.logFile) {
              const content = await this.fetchRemoteContent(this.logFile)
              if (content === null) return
              this._logText = content
              this._logTextFile = this.logFile
            }
            parseBody = { content: this._logText }
          }
          const parseResp = await this.postJson(`${this.backendUrl}/api/gjf/log-parse`, parseBody)
          if (!parseResp.ok) {
            this.logInfo = null
            this.logPreview = ''
            this.logNotice = parseResp.data.detail || ''
            this.addLog($tr('{0} 解析失败({1}): {2}', { 0: this.logFile, 1: parseResp.status, 2: parseResp.data.detail }), '#ff6b6b')
            return
          }
          this.logNotice = ''
          const info = parseResp.data
          this.logInfo = info
          this._logInfoFile = this.logFile
          this.syncChargeMultFromLog()
        }

        const payload = { ...this.logParams(), filename: this.logFile }
        if (this.mode === 'local') payload.path = `${this.inputFolder}\\${this.logFile}`
        else payload.content = this._logText
        const genResp = await this.postJson(`${this.backendUrl}/api/gjf/log-to-gjf`, payload)
        if (!genResp.ok) {
          this.logPreview = ''
          this.addLog($tr('生成 GJF 失败({0}): {1}', { 0: genResp.status, 1: genResp.data.detail }), '#ff6b6b')
          return
        }
        const generated = genResp.data
        this.logPreview = generated.content
        this.logGenName = generated.filename
        if (needParse) {
          this.addLog($tr('已解析 {0}：{1} 原子，{2} 取第 {3}/{4} 段 → {5}', { 0: this.logFile, 1: this.logInfo.natoms, 2: this.logInfo.source, 3: this.logInfo.frame_index, 4: this.logInfo.frames, 5: generated.filename }), '#7cfc00')
          if (generated.log_title) {
            this.addLog($tr('（标题行使用文件名；LOG 内原标题为「{0}」）', { 0: generated.log_title }), '#87d2ff')
          }
        }
      } catch (e) {
        this.addLog($tr('LOG 处理失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // 电荷/自旋取用 LOG 检出值
    syncChargeMultFromLog() {
      if (!this.useLogChargeMult || !this.logInfo) return
      if (this.logInfo.charge !== null && this.logInfo.charge !== undefined) this.charge = String(this.logInfo.charge)
      if (this.logInfo.mult !== null && this.logInfo.mult !== undefined) this.mult = String(this.logInfo.mult)
    },

    // 勾选项变化后重新同步并刷新预览
    async onLogParamsToggle() {
      if (this.workMode !== 'log' || !this.logFile) return
      this.syncChargeMultFromLog()
      await this.buildLogPreview(false)
    },

    // 参数变动后延迟重算预览，避免每次按键都请求后端
    scheduleLogPreview() {
      if (this.workMode !== 'log' || !this.logFile || !this.logInfo) return
      clearTimeout(this._logPreviewTimer)
      this._logPreviewTimer = setTimeout(() => {
        this.buildLogPreview(false)
      }, 350)
    },

    // 把 LOG 中检出的关键词行回填到参数栏
    async applyLogToParams() {
      const parts = this.logInfo && this.logInfo.route_parts
      if (!parts || !parts.route) {
        this.addLog($tr('该 LOG 未检出关键词行'), '#ffa500')
        return
      }
      if (parts.mode) this.calcMode = parts.mode
      if (parts.functional) this.functional = parts.functional
      if (parts.basis) this.basis = parts.basis
      this.useLogKeyword = false
      this.addLog($tr('已填入 LOG 关键词：{0} {1}/{2}', { 0: parts.mode, 1: parts.functional, 2: parts.basis }), '#87d2ff')
      await this.buildLogPreview(false)
    },

    // 当前 LOG 转换结果保存为 .gjf
    async saveLogAsGjf() {
      if (!this.logFile || !this.logPreview) return false
      const outDir = this.outputFolder || this.inputFolder
      if (!outDir) {
        this.addLog($tr('请先选择 GJF 输出目录'), '#ffa500')
        return false
      }
      const filename = this.logGenName || this.logOutputName
      this.saving = true
      let ok = false
      try {
        if (this.mode === 'local') {
          const resp = await this.postJson(`${this.backendUrl}/api/gjf/save`, {
            path: `${outDir}\\${filename}`,
            content: this.logPreview
          })
          if (resp.ok) {
            ok = true
            this.addLog($tr('已生成: {0}\\{1}', { 0: outDir, 1: filename }), '#7cfc00')
          } else {
            this.addLog($tr('保存失败({0}): {1}', { 0: resp.status, 1: resp.data.detail }), '#ff6b6b')
          }
        } else {
          const remotePath = posixpath.join(outDir.replace(/\\/g, '/'), filename)
          const resp = await this.postJson(`${this.backendUrl}/api/remote/upload`, {
            session_id: this.sessionId,
            path: remotePath,
            content: this.logPreview
          })
          if (resp.ok) {
            ok = true
            this.addLog($tr('已上传: {0}', { 0: remotePath }), '#7cfc00')
          } else {
            this.addLog($tr('上传失败({0}): {1}', { 0: resp.status, 1: resp.data.detail }), '#ff6b6b')
          }
        }
      } catch (e) {
        this.addLog($tr('保存失败: {0}', { 0: e.message }), '#ff6b6b')
      }
      this.saving = false
      return ok
    },

    async convertCurrentLog() {
      const ok = await this.saveLogAsGjf()
      if (ok) {
        this.addLog($tr('转换完成；可点击「转到 GJF 模式继续修改」继续调参或批量修改'), '#00ff00')
      }
    },

    // 批量 LOG → GJF
    async batchConvertLogs() {
      if (this.running) return
      if (!this.inputFolder) {
        this.addLog($tr('请先选择 LOG 目录'), '#ffa500')
        return
      }
      if (!this.checkedFiles.length) {
        this.addLog($tr('请至少勾选一个 LOG 文件'), '#ffa500')
        return
      }
      const outDir = this.outputFolder || this.inputFolder
      const keyword = this.fullKeyword
      if (!keyword && !this.useLogKeyword) {
        this.addLog($tr('请填写计算模式、泛函和基组，或勾选「关键词取用 LOG」'), '#ffa500')
        return
      }

      this.running = true
      this.logLines = []
      this.addLog($tr('开始批量转换 {0} 个 LOG → GJF ...', { 0: this.checkedFiles.length }), '#00ff00')

      if (this.mode === 'local') {
        try {
          const resp = await this.postJson(`${this.backendUrl}/api/gjf/log-batch`, {
            input_folder: this.inputFolder,
            output_folder: outDir,
            files: this.checkedFiles,
            prefix: this.prefix,
            mem: this.mem,
            nproc: this.nproc,
            keyword: keyword,
            charge: this.charge,
            mult: this.mult,
            use_log_charge_mult: this.useLogChargeMult,
            use_log_keyword: this.useLogKeyword
          })
          const data = resp.data
          if (!resp.ok) {
            this.addLog($tr('批量转换失败({0}): {1}', { 0: resp.status, 1: data.detail }), '#ff6b6b')
          } else {
            (data.results || []).forEach(item => {
              if (item.status === 'success') {
                this.addLog($tr('{0} → {1}（{2} 原子，电荷 {3}，自旋 {4}）', { 0: item.filename, 1: item.output, 2: item.natoms, 3: item.charge, 4: item.mult }), '#7cfc00')
              } else {
                this.addLog($tr('{0} 失败: {1}', { 0: item.filename, 1: item.message }), '#ff6b6b')
              }
            })
            this.addLog($tr('批量转换完成，成功 {0}/{1}', { 0: data.success, 1: data.total }), '#00ff00')
          }
        } catch (e) {
          this.addLog($tr('批量转换失败: {0}', { 0: e.message }), '#ff6b6b')
        }
      } else {
        let successCount = 0
        for (const name of this.checkedFiles) {
          try {
            const content = await this.fetchRemoteContent(name)
            if (content === null) continue
            const genResp = await this.postJson(`${this.backendUrl}/api/gjf/log-to-gjf`, {
              ...this.logParams(), filename: name, content
            })
            if (!genResp.ok) throw new Error(genResp.data.detail || $tr('转换失败'))
            const generated = genResp.data
            const remotePath = posixpath.join(outDir.replace(/\\/g, '/'), generated.filename)
            const upResp = await this.postJson(`${this.backendUrl}/api/remote/upload`, {
              session_id: this.sessionId, path: remotePath, content: generated.content
            })
            if (!upResp.ok) throw new Error(upResp.data.detail || $tr('上传失败'))
            successCount++
            this.addLog(`${name} → ${remotePath}`, '#7cfc00')
          } catch (e) {
            this.addLog($tr('{0} 失败: {1}', { 0: name, 1: e.message }), '#ff6b6b')
          }
        }
        this.addLog($tr('批量转换完成，成功 {0}/{1} (远程)', { 0: successCount, 1: this.checkedFiles.length }), '#00ff00')
      }
      this.running = false
    },

    // 转换后切到 GJF 模式并定位到新生成的文件，实现 log→gjf→修改 连贯操作
    async switchToGjfAfterConvert() {
      const outDir = this.outputFolder || this.inputFolder
      this.workMode = 'gjf'
      if (outDir) this.inputFolder = outDir
      await this.$nextTick()
      const target = this.logGenName || this.logOutputName
      this.addLog($tr('已切换到 GJF 模式，可继续调参或批量修改'), '#87d2ff')
      if (!target) return
      for (let i = 0; i < 20; i++) {
        await new Promise(resolve => setTimeout(resolve, 150))
        const idx = this.fileList.indexOf(target)
        if (idx >= 0) {
          this.selectFile(idx)
          return
        }
      }
    },

    // ===== 应用参数并保存（单文件） =====
    async applyParamsAndSave() {
      if (!this.currentFile) {
        this.addLog($tr('请先选择文件'), '#ffa500')
        return
      }
      const keyword = this.fullKeyword
      if (!keyword) {
        this.addLog($tr('请填写计算模式、泛函和基组'), '#ffa500')
        return
      }
      this.addLog($tr('应用参数并保存...'), '#87d2ff')
      let newContent = ''
      try {
        const chkName = this.currentFile ? `${this.prefix}${this.currentFile.replace('.gjf', '.chk')}` : undefined
        const applyResp = await fetch(`${this.backendUrl}/api/gjf/apply-params`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: this.currentContent,
            mem: this.mem,
            nproc: this.nproc,
            keyword: keyword,
            charge: this.charge,
            mult: this.mult,
            chk_name: chkName
          })
        })
        const applyData = await applyResp.json()
        if (!applyResp.ok) throw new Error(applyData.detail || $tr('应用参数失败'))
        newContent = applyData.content
      } catch (e) {
        this.addLog($tr('应用参数失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      this.currentContent = newContent
      let saved = false
      if (this.mode === 'remote') {
        saved = await this.saveFileRemote()
      } else {
        saved = await this.saveFileLocal()
      }
      if (saved) {
        // 保存成功后刷新一次列表（保持当前文件选中），让编辑区展示更新后的磁盘内容
        await this.refreshListKeepSelection()
        this.addLog($tr('已刷新文件列表'), '#87d2ff')
      }
    },

    // ===== 批量修改 =====
    async startBatchModify() {
      if (this.running) return
      if (!this.inputFolder || !this.outputFolder) {
        this.addLog($tr('请选择输入和输出文件夹'), '#ffa500')
        return
      }
      if (!this.checkedFiles.length) {
        this.addLog($tr('请至少勾选一个文件'), '#ffa500')
        return
      }
      const keyword = this.fullKeyword
      if (!keyword) {
        this.addLog($tr('请填写计算模式、泛函和基组'), '#ffa500')
        return
      }

      this.running = true
      this.logLines = []
      this.addLog($tr('开始批量修改 {0} 个文件...', { 0: this.checkedFiles.length }), '#00ff00')

      if (this.mode === 'remote') {
        await this.batchModifyRemote(keyword)
      } else {
        await this.batchModifyLocal(keyword)
      }
      this.running = false

      // 批量修改完成后自动刷新：输入与输出同目录时直接回读最新内容展示
      const norm = (p) => (p || '').replace(/\\/g, '/').replace(/\/+$/, '')
      if (this.inputFolder && norm(this.inputFolder) === norm(this.outputFolder)) {
        await this.refreshListKeepSelection()
        this.addLog($tr('批量修改完成，已刷新文件列表'), '#87d2ff')
      } else {
        this.addLog($tr('批量修改完成，输出目录与输入目录不同，结果位于输出目录中'), '#87d2ff')
      }
    },

    async batchModifyLocal(keyword) {
      try {
        const response = await fetch(`${this.backendUrl}/api/gjf/batch-modify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            input_folder: this.inputFolder,
            output_folder: this.outputFolder,
            files: this.checkedFiles,
            prefix: this.prefix,
            mem: this.mem,
            nproc: this.nproc,
            keyword: keyword,
            charge: this.charge,
            mult: this.mult
          })
        })
        const data = await response.json()
        if (response.ok) {
          const results = data.results || []
          results.forEach(item => {
            if (item.status === 'success') {
              this.addLog($tr('{0} -> {1} (本地)', { 0: item.filename, 1: item.output }), '#7cfc00')
            } else {
              this.addLog($tr('{0} 失败: {1} (本地)', { 0: item.filename, 1: item.message }), '#ff6b6b')
            }
          })
          this.addLog($tr('批量修改完成，共处理 {0} 个文件', { 0: results.length }), '#00ff00')
        } else {
          this.addLog($tr('批量修改失败: {0}', { 0: data.detail || $tr('未知错误') }), '#ff6b6b')
        }
      } catch (e) {
        this.addLog($tr('批量修改失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },

    // ===== 远程批量修改（已修复 chk 文件名） =====
    async batchModifyRemote(keyword) {
      const total = this.checkedFiles.length
      let successCount = 0

      for (let i = 0; i < total; i++) {
        const filename = this.checkedFiles[i]
        try {
          // 1. 读取缓存内容
          let content
          const readResp = await fetch(`${this.backendUrl}/api/remote/cache/read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: this.sessionId, path: filename })
          })
          if (readResp.ok) {
            const readData = await readResp.json()
            content = readData.content
          } else {
            const remotePath = posixpath.join(this.inputFolder, filename)
            const downloadResp = await fetch(`${this.backendUrl}/api/remote/download`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ session_id: this.sessionId, path: remotePath })
            })
            const downloadData = await downloadResp.json()
            if (!downloadResp.ok) throw new Error(downloadData.detail || $tr('下载失败'))
            content = downloadData.content
          }

          // 2. 应用参数修改（传递 chk_name）
          const chkName = `${this.prefix}${filename.replace('.gjf', '.chk')}`
          const applyResp = await fetch(`${this.backendUrl}/api/gjf/apply-params`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              content: content,
              mem: this.mem,
              nproc: this.nproc,
              keyword: keyword,
              charge: this.charge,
              mult: this.mult,
              chk_name: chkName
            })
          })
          const applyData = await applyResp.json()
          if (!applyResp.ok) throw new Error(applyData.detail || $tr('应用参数失败'))

          // 3. 上传修改后的内容
          const outputFilename = `${this.prefix}${filename}`
          const outputRemotePath = posixpath.join(this.outputFolder, outputFilename)
          const uploadResp = await fetch(`${this.backendUrl}/api/remote/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: this.sessionId,
              path: outputRemotePath,
              content: applyData.content
            })
          })
          const uploadData = await uploadResp.json()
          if (uploadResp.ok) {
            this.addLog($tr('上传成功: {0} (远程)', { 0: outputFilename }), '#7cfc00')
            successCount++
          } else {
            this.addLog($tr('上传失败: {0} - {1}', { 0: outputFilename, 1: uploadData.detail }), '#ff6b6b')
          }
        } catch (e) {
          this.addLog($tr('处理 {0} 失败: {1}', { 0: filename, 1: e.message }), '#ff6b6b')
        }
      }
      this.addLog($tr('批量修改完成，成功 {0}/{1} 个文件 (远程)', { 0: successCount, 1: total }), '#00ff00')
    }
  }
}
</script>
<template>
  <!-- PyCharm 风格三栏：左=文件列表 / 中=编辑窗口 / 右=参数调节；下方日志与终端保持不动 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">

    <div class="flex flex-1 min-h-0" style="gap:10px;">

      <!-- ===== 左侧：文件列表 ===== -->
      <aside class="flex-col" style="width:250px;flex-shrink:0;background:var(--c-panel);border:1px solid var(--c-border);border-radius:var(--r-lg);overflow:hidden;min-height:0;">
        <div class="flex-center" style="justify-content:space-between;padding:6px 10px;border-bottom:1px solid var(--c-border);flex-shrink:0;background:var(--c-bar);">
          <span style="font-weight:600;font-size:13px;">文件列表</span>
          <div class="flex-center" style="gap:6px;">
            <label class="flex-center" style="gap:4px;font-size:12px;color:var(--c-text-2);cursor:pointer;">
              <input type="checkbox" v-model="selectAll" @change="toggleAll" /> 全选
            </label>
            <button class="btn" style="height:22px;padding:0 8px;font-size:12px;" @click="refreshList" :disabled="!inputFolder">刷新</button>
          </div>
        </div>
        <div style="flex:1;overflow-y:auto;padding:4px 0;min-height:0;">
          <div v-if="!fileList.length" style="color:var(--c-text-3);text-align:center;padding:18px;font-size:13px;">
            暂无 .gjf 文件<br><span style="font-size:12px;">请先在右侧选择输入目录</span>
          </div>
          <div
            v-for="(file, idx) in fileList"
            :key="idx"
            @click="selectFile(idx)"
            @dblclick="startRename(idx)"
            :style="{
              padding: '4px 10px',
              cursor: 'pointer',
              background: selectedIndex === idx ? 'var(--c-hl-a)' : 'transparent',
              borderLeft: selectedIndex === idx ? '3px solid var(--c-accent)' : '3px solid transparent',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--c-text)'
            }"
            @mouseenter="e=>e.target.style.background=selectedIndex===idx ? 'var(--c-hl-a)' : 'var(--c-hover)'"
            @mouseleave="e=>{ if(selectedIndex!==idx) e.target.style.background='transparent' }"
          >
            <input type="checkbox" v-model="checkedFiles" :value="file" @click.stop />
            <span v-if="editingIndex === idx" style="flex:1;">
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
            <span v-else style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ file }}</span>
          </div>
        </div>
      </aside>

      <!-- ===== 中间：编辑窗口 ===== -->
      <section class="flex-col" style="flex:1;min-width:0;min-height:0;border:1px solid var(--c-border);border-radius:var(--r-lg);overflow:hidden;background:var(--c-main);">
        <div class="flex" style="justify-content:space-between;align-items:center;gap:8px;padding:6px 12px;border-bottom:1px solid var(--c-border);flex-shrink:0;background:var(--c-bar);">
          <div class="flex" style="gap:10px;align-items:center;min-width:0;flex-wrap:wrap;">
            <span style="font-weight:600;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ currentFile ? currentFile : '未选择文件' }}</span>
            <span v-if="mode === 'remote'" style="color:var(--c-accent);font-size:12px;">(远程)</span>
          </div>
          <div class="flex" style="gap:8px;align-items:center;flex-shrink:0;">
            <button class="btn btn-success" style="height:26px;" @click="saveCurrentFile" :disabled="!currentFile || saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="btn" style="height:26px;" @click="refreshList" :disabled="!currentFile">
              刷新列表
            </button>
          </div>
        </div>

        <!-- 最终参数预览行：与中间窗口同宽，置于编辑区上方 -->
        <div class="flex-center" style="gap:8px;padding:6px 12px;flex-shrink:0;border-bottom:1px solid var(--c-border-soft);background:var(--c-panel);flex-wrap:wrap;">
          <span class="label" style="white-space:nowrap;">最终参数预览</span>
          <input class="control preview" style="flex:1;min-width:180px;height:28px;" :value="fullKeyword" readonly />
          <span class="label" style="white-space:nowrap;">电荷</span>
          <input class="control" style="width:56px;height:28px;" v-model="charge" />
          <span class="label" style="white-space:nowrap;">自旋</span>
          <input class="control" style="width:56px;height:28px;" v-model="mult" />
        </div>

        <textarea
          v-model="currentContent"
          :disabled="!currentFile"
          class="control"
          style="flex:1;width:100%;border:none;border-radius:0;padding:10px;font-family:var(--font-mono);font-size:13px;line-height:1.5;resize:none;background:var(--c-editor);color:var(--c-code);"
          spellcheck="false"
        ></textarea>
      </section>

      <!-- ===== 右侧：参数调节 ===== -->
      <aside class="flex-col" style="width:300px;flex-shrink:0;background:var(--c-main);border:1px solid var(--c-border);border-radius:var(--r-lg);overflow-y:auto;padding:10px 12px;gap:10px;min-height:0;">
        <div class="flex-center" style="justify-content:space-between;">
          <span class="label">工作模式</span>
          <div class="flex-center" style="gap:6px;">
            <button class="btn" :class="mode === 'local' ? 'btn-primary' : 'btn-default'" style="height:24px;padding:0 10px;font-size:12px;" @click="switchMode('local')">本地</button>
            <button class="btn" :class="mode === 'remote' ? 'btn-primary' : 'btn-default'" style="height:24px;padding:0 10px;font-size:12px;" @click="switchMode('remote')" :disabled="!remoteConnected">远程</button>
          </div>
        </div>
        <div v-if="mode === 'remote'" style="font-size:12px;color:var(--c-text-2);">
          {{ remoteConnected ? `已连接 ${remoteStore.displayName}` : '未连接（请先通过顶部工具栏连接服务器）' }}
        </div>

        <!-- 目录 -->
        <div class="flex-col" style="gap:4px;border-top:1px solid var(--c-border-soft);padding-top:10px;">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">输入目录</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="mode==='local' ? selectInputFolder() : openRemoteBrowser('input')" :disabled="mode==='remote' && !remoteConnected">选择…</button>
          </div>
          <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;min-height:16px;">{{ inputFolder || '未选择' }}</div>
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">输出目录</span>
            <button class="btn" style="height:24px;padding:0 10px;font-size:12px;" @click="mode==='local' ? selectOutputFolder() : openRemoteBrowser('output')" :disabled="mode==='remote' && !remoteConnected">选择…</button>
          </div>
          <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;min-height:16px;">{{ outputFolder || '未选择' }}</div>
        </div>

        <!-- 参数 -->
        <div class="flex-col" style="gap:6px;border-top:1px solid var(--c-border-soft);padding-top:10px;">
          <div class="flex-center" style="gap:8px;justify-content:space-between;">
            <span class="label">前缀</span>
            <input class="control" style="width:150px;height:28px;" v-model="prefix" placeholder="如 opt_" />
          </div>
          <div class="flex-center" style="gap:8px;justify-content:space-between;">
            <span class="label">预设</span>
            <select class="control" style="width:150px;height:28px;" v-model="selectedPreset" @change="applyPreset">
              <option v-for="(conf, name) in presetResources" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div class="flex-center" style="gap:8px;justify-content:space-between;">
            <span class="label">内存</span>
            <input class="control" style="width:150px;height:28px;" v-model="mem" placeholder="如 20GB" />
          </div>
          <div class="flex-center" style="gap:8px;justify-content:space-between;">
            <span class="label">核心数</span>
            <input class="control" style="width:150px;height:28px;" v-model="nproc" placeholder="如 8" />
          </div>
          <div class="flex-col" style="gap:4px;">
            <span class="label">计算模式</span>
            <input class="control" style="width:100%;height:28px;" v-model="calcMode" list="calcModePresets" />
            <datalist id="calcModePresets">
              <option v-for="preset in calcModePresets" :key="preset" :value="preset" />
            </datalist>
          </div>
          <div class="flex-col" style="gap:4px;">
            <span class="label">泛函 / 基组</span>
            <div class="flex" style="gap:6px;">
              <input class="control" style="flex:1;min-width:0;height:28px;" v-model="functional" list="functionalPresets" placeholder="如 b3lyp" />
              <input class="control" style="flex:1;min-width:0;height:28px;" v-model="basis" list="basisPresets" placeholder="如 6-31g(d,p)" />
            </div>
            <datalist id="functionalPresets">
              <option v-for="preset in functionalPresets" :key="preset" :value="preset" />
            </datalist>
            <datalist id="basisPresets">
              <option v-for="preset in basisPresets" :key="preset" :value="preset" />
            </datalist>
          </div>
        </div>

        <!-- 操作 -->
        <div class="flex-col" style="gap:8px;border-top:1px solid var(--c-border-soft);padding-top:10px;">
          <button class="btn btn-primary h-lg" @click="applyParamsAndSave" :disabled="!currentFile">保存并应用参数至当前文件</button>
          <button class="btn btn-success h-lg" @click="startBatchModify" :disabled="running || !inputFolder || !outputFolder || !checkedFiles.length">
            {{ running ? '处理中...' : `批量修改（${checkedFiles.length}）` }}
          </button>
          <div style="font-size:12px;color:var(--c-text-3);line-height:1.5;">
            在左侧勾选文件后可批量修改；修改结果实时写入输入目录（输入=输出时自动刷新展示）。
          </div>
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
import RemoteFileBrowser from '@/components/RemoteFileBrowser.vue'
import { pickDirectory } from '@/api/dialog'
const posixpath = {
  join: (...segments) => segments.filter(s => s && s !== '').join('/').replace(/\/+/g, '/')
};
export default {
  name: 'GjfModifyView',
  components: { LogViewer, RemoteFileBrowser },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected: remoteConnected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, remoteConnected, sessionId, username }
  },
  data() {
    return {
      mode: 'local',
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
      mem: '20GB',
      nproc: '8',
      calcMode: '#p opt',
      functional: 'b3lyp',
      basis: '6-31g(d,p)',
      charge: '0',
      mult: '1',
      selectedPreset: 'students/zstoffice',
      presetResources: {
        'hachimi单并行': { nproc: '10', mem: '40GB' },
        'hachimi四并行': { nproc: '4', mem: '10GB' },
        'Tomori八队列': { nproc: '12', mem: '12GB' },
        'students/zstoffice': { nproc: '8', mem: '20GB' },
        'zst106': { nproc: '24', mem: '180GB' }
      },
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
        console.error('获取后端地址失败:', e)
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
        if (this.mode === 'local') this.loadFileListLocal()
        else this.loadFileListRemote()
      } else if (!newVal) {
        this.clearCacheIfRemote()
        this.fileList = []
        this.selectedIndex = -1
        this.currentFile = null
        this.currentContent = ''
        this.checkedFiles = []
        this.selectAll = false
      }
    },
    mode(newVal, oldVal) {
      if (oldVal === 'remote' && newVal !== 'remote') {
        this.clearCacheIfRemote()
      }
      this.fileList = []
      this.selectedIndex = -1
      this.currentFile = null
      this.currentContent = ''
      this.checkedFiles = []
      this.selectAll = false
      if (this.inputFolder) {
        if (newVal === 'local') this.loadFileListLocal()
        else this.loadFileListRemote()
      }
    },
    checkedFiles(val) {
      this.selectAll = val.length === this.fileList.length && this.fileList.length > 0
    }
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
      this.checkedFiles = this.selectAll ? [...this.fileList] : []
    },

    // ===== 自动清除远程缓存 =====
    async clearCacheIfRemote() {
      if (this.mode === 'remote' && this.remoteConnected && this.sessionId) {
        try {
          await fetch(`${this.backendUrl}/api/remote/cache?session_id=${this.sessionId}`, {
            method: 'DELETE'
          })
        } catch (e) {
          console.warn('清除缓存失败:', e)
        }
      }
    },

    // ===== 刷新列表（清除缓存 + 重新加载） =====
    async refreshList() {
      if (!this.inputFolder) {
        this.addLog('请先选择输入文件夹', '#ffa500')
        return
      }
      if (this.mode === 'remote' && this.remoteConnected) {
        try {
          const resp = await fetch(`${this.backendUrl}/api/remote/cache?session_id=${this.sessionId}`, {
            method: 'DELETE'
          })
          if (resp.ok) {
            this.addLog('缓存已自动清除', '#7cfc00')
          } else {
            const data = await resp.json()
            this.addLog(`清除缓存失败: ${data.detail || '未知错误'}`, '#ff6b6b')
          }
        } catch (e) {
          this.addLog(`清除缓存失败: ${e.message}`, '#ff6b6b')
        }
      }
      if (this.mode === 'local') {
        await this.loadFileListLocal()
      } else {
        await this.loadFileListRemote()
      }
      this.addLog('文件列表已刷新', '#87d2ff')
    },

    // ===== 模式切换 =====
    switchMode(mode) {
      if (mode === 'remote' && !this.remoteConnected) {
        this.addLog('请先通过工具栏连接服务器', '#ffa500')
        return
      }
      if (this.mode !== mode && this.mode === 'remote') {
        this.clearCacheIfRemote()
      }
      this.mode = mode
      this.fileList = []
      this.selectedIndex = -1
      this.currentFile = null
      this.currentContent = ''
      this.checkedFiles = []
      this.selectAll = false
      if (this.inputFolder) {
        if (mode === 'local') this.loadFileListLocal()
        else this.loadFileListRemote()
      }
    },

    // ===== 选择文件夹（本地） =====
    selectInputFolder() {
      this.selectLocalFolder('inputFolder', '选择包含 .gjf 的文件夹')
    },
    selectOutputFolder() {
      this.selectLocalFolder('outputFolder', '选择输出文件夹')
    },
    async selectLocalFolder(variable, title) {
      let path
      try {
        path = await pickDirectory(title)
      } catch (e) {
        this.addLog(`选择目录失败: ${e.message}`, '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this[variable] = path
      this.addLog(`选择目录: ${title}: ${path}`, '#87d2ff')
      if (variable === 'inputFolder') {
        this.checkedFiles = []
        this.selectAll = false
        if (this.mode === 'local') this.loadFileListLocal()
        else this.loadFileListRemote()
      }
    },

    // ===== 远程目录浏览器 =====
    openRemoteBrowser(target) {
      if (!this.remoteConnected) {
        this.addLog('请先通过工具栏连接服务器', '#ffa500')
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
          this.addLog('请选择目录而非文件', '#ffa500')
        }
      } else if (target === 'output') {
        if (is_dir) {
          this.outputFolder = path
        } else {
          this.addLog('请选择目录而非文件', '#ffa500')
        }
      }
      this.addLog(`已选择: ${path}`, '#87d2ff')
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
          this.addLog(`找到 ${this.fileList.length} 个 .gjf 文件 (本地)`, '#87d2ff')
        } else {
          this.addLog(`加载文件列表失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`加载文件列表失败: ${e.message}`, '#ff6b6b')
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
          this.addLog(`获取远程文件列表失败: ${listData.detail}`, '#ff6b6b')
          return
        }
        const allEntries = listData.entries || []
        const gjfFiles = allEntries.filter(e => !e.is_dir && e.name.endsWith('.gjf')).map(e => e.name)
        this.fileList = gjfFiles
        this.checkedFiles = this.checkedFiles.filter(f => this.fileList.includes(f))
        if (!this.fileList.length) {
          this.addLog('远程目录中没有 .gjf 文件', '#ffa500')
          this.selectedIndex = -1
          this.currentFile = null
          this.currentContent = ''
          return
        }

        this.addLog(`正在下载 ${this.fileList.length} 个远程文件到本地缓存...`, '#87d2ff')
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
          this.addLog(`批量下载失败: ${downloadData.detail}`, '#ff6b6b')
          return
        }
        const results = downloadData.results || []
        const successCount = results.filter(r => r.status === 'success').length
        this.addLog(`成功下载 ${successCount}/${this.fileList.length} 个文件到缓存`, '#87d2ff')
        if (successCount === 0) {
          this.addLog('下载失败，请检查网络或权限', '#ff6b6b')
          return
        }

        this.selectedIndex = 0
        this.loadFileContentRemote(this.fileList[0])
      } catch (e) {
        this.addLog(`加载远程文件列表失败: ${e.message}`, '#ff6b6b')
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
      if (idx < 0 || idx >= this.fileList.length) return
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
          this.addLog(`读取文件失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`读取文件失败: ${e.message}`, '#ff6b6b')
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
          this.addLog(`缓存读取失败，尝试重新下载: ${filename}`, '#ffa500')
          await this.downloadSingleFile(filename)
        }
      } catch (e) {
        this.addLog(`读取缓存文件失败: ${e.message}`, '#ff6b6b')
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
          this.addLog(`重新下载成功: ${filename}`, '#7cfc00')
        } else {
          this.addLog(`下载失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`下载失败: ${e.message}`, '#ff6b6b')
      }
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
          this.addLog(`保存成功: ${this.currentFile} (本地)`, '#7cfc00')
        } else {
          this.addLog(`保存失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`保存失败: ${e.message}`, '#ff6b6b')
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
          this.addLog(`上传成功: ${this.currentFile} (远程)`, '#7cfc00')
        } else {
          this.addLog(`上传失败: ${uploadData.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`保存失败: ${e.message}`, '#ff6b6b')
      }
      this.saving = false
      return ok
    },

    // ===== 重命名 =====
    startRename(idx) {
      this.editingIndex = idx
      this.editingName = this.fileList[idx]
      this.$nextTick(() => {
        const input = this.$refs.renameInput
        if (input) { input.focus(); input.select() }
      })
    },
    async finishRename() {
      const idx = this.editingIndex
      if (idx === -1) return
      const oldName = this.fileList[idx]
      const newName = this.editingName.trim()
      if (!newName || newName === oldName) {
        this.cancelRename(); return
      }
      if (this.fileList.some((f, i) => i !== idx && f === newName)) {
        this.addLog(`文件名 "${newName}" 已存在`, '#ff6b6b')
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
          this.fileList[idx] = newName
          if (this.currentFile === oldName) this.currentFile = newName
          const checkedIdx = this.checkedFiles.indexOf(oldName)
          if (checkedIdx !== -1) this.checkedFiles[checkedIdx] = newName
          this.addLog(`重命名成功: ${oldName} -> ${newName} (本地)`, '#7cfc00')
          if (this.currentFile === newName) this.loadFileContentLocal(newName)
        } else {
          this.addLog(`重命名失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`重命名失败: ${e.message}`, '#ff6b6b')
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
        if (!renameResp.ok) throw new Error(renameData.detail || '远程重命名失败')
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
        const checkedIdx = this.checkedFiles.indexOf(oldName)
        if (checkedIdx !== -1) this.checkedFiles[checkedIdx] = newName
        this.addLog(`重命名成功: ${oldName} -> ${newName} (远程)`, '#7cfc00')
        if (this.currentFile === newName) this.loadFileContentRemote(newName)
      } catch (e) {
        this.addLog(`重命名失败: ${e.message}`, '#ff6b6b')
      }
    },
    cancelRename() {
      this.editingIndex = -1
      this.editingName = ''
    },

    // ===== 预设应用 =====
    applyPreset() {
      const preset = this.presetResources[this.selectedPreset]
      if (preset) {
        this.mem = preset.mem
        this.nproc = preset.nproc
        this.addLog(`应用预设: ${this.selectedPreset}`, '#87d2ff')
      }
    },

    // ===== 应用参数并保存（单文件） =====
    async applyParamsAndSave() {
      if (!this.currentFile) {
        this.addLog('请先选择文件', '#ffa500')
        return
      }
      const keyword = this.fullKeyword
      if (!keyword) {
        this.addLog('请填写计算模式、泛函和基组', '#ffa500')
        return
      }
      this.addLog('应用参数并保存...', '#87d2ff')
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
        if (!applyResp.ok) throw new Error(applyData.detail || '应用参数失败')
        newContent = applyData.content
      } catch (e) {
        this.addLog(`应用参数失败: ${e.message}`, '#ff6b6b')
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
        this.addLog('已刷新文件列表', '#87d2ff')
      }
    },

    // ===== 批量修改 =====
    async startBatchModify() {
      if (this.running) return
      if (!this.inputFolder || !this.outputFolder) {
        this.addLog('请选择输入和输出文件夹', '#ffa500')
        return
      }
      if (!this.checkedFiles.length) {
        this.addLog('请至少勾选一个文件', '#ffa500')
        return
      }
      const keyword = this.fullKeyword
      if (!keyword) {
        this.addLog('请填写计算模式、泛函和基组', '#ffa500')
        return
      }

      this.running = true
      this.logLines = []
      this.addLog(`开始批量修改 ${this.checkedFiles.length} 个文件...`, '#00ff00')

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
        this.addLog('批量修改完成，已刷新文件列表', '#87d2ff')
      } else {
        this.addLog('批量修改完成，输出目录与输入目录不同，结果位于输出目录中', '#87d2ff')
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
              this.addLog(`${item.filename} -> ${item.output} (本地)`, '#7cfc00')
            } else {
              this.addLog(`${item.filename} 失败: ${item.message} (本地)`, '#ff6b6b')
            }
          })
          this.addLog(`批量修改完成，共处理 ${results.length} 个文件`, '#00ff00')
        } else {
          this.addLog(`批量修改失败: ${data.detail || '未知错误'}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`批量修改失败: ${e.message}`, '#ff6b6b')
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
            if (!downloadResp.ok) throw new Error(downloadData.detail || '下载失败')
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
          if (!applyResp.ok) throw new Error(applyData.detail || '应用参数失败')

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
            this.addLog(`上传成功: ${outputFilename} (远程)`, '#7cfc00')
            successCount++
          } else {
            this.addLog(`上传失败: ${outputFilename} - ${uploadData.detail}`, '#ff6b6b')
          }
        } catch (e) {
          this.addLog(`处理 ${filename} 失败: ${e.message}`, '#ff6b6b')
        }
      }
      this.addLog(`批量修改完成，成功 ${successCount}/${total} 个文件 (远程)`, '#00ff00')
    }
  }
}
</script>
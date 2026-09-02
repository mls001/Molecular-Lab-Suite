<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">批量修改 GJF 参数</h2>
    <p style="color:#666;margin:0;font-size:14px;">选择文件夹，批量修改或单独预览/编辑 .gjf 文件</p>

    <!-- 控制栏（含模式切换） -->
    <div class="flex-center flex-shrink-0" style="gap:12px;flex-wrap:wrap;background:#f9f9f9;padding:6px 14px;border-radius:6px;">
      <!-- 模式切换 -->
      <div style="display:flex;align-items:center;gap:6px;">
        <span class="label">模式</span>
        <button class="btn" :class="mode === 'local' ? 'btn-primary' : 'btn-default'" @click="switchMode('local')" style="height:28px;padding:0 12px;font-size:12px;">本地</button>
        <button class="btn" :class="mode === 'remote' ? 'btn-primary' : 'btn-default'" @click="switchMode('remote')" style="height:28px;padding:0 12px;font-size:12px;" :disabled="!remoteConnected">远程</button>
        <span v-if="mode === 'remote' && remoteConnected" style="color:#52c41a;font-size:12px;">已连接 {{ remoteStore.displayName }}</span>
        <span v-else-if="mode === 'remote' && !remoteConnected" style="color:#ff4d4f;font-size:12px;">未连接</span>
      </div>

      <button class="btn btn-primary h-lg" @click="selectInputFolder" v-if="mode === 'local'">选择输入文件夹</button>
      <button class="btn btn-primary h-lg" @click="openRemoteBrowser('input')" v-else :disabled="!remoteConnected">远程输入目录</button>

      <span v-if="inputFolder" style="color:#1890ff;font-size:13px;">{{ inputFolder }}</span>
      <span v-else style="color:#999;font-size:13px;">未选择</span>

      <button class="btn btn-success h-lg" @click="selectOutputFolder" v-if="mode === 'local'">选择输出文件夹</button>
      <button class="btn btn-success h-lg" @click="openRemoteBrowser('output')" v-else :disabled="!remoteConnected">远程输出目录</button>
      <span v-if="outputFolder" style="color:#52c41a;font-size:13px;">{{ outputFolder }}</span>
      <span v-else style="color:#999;font-size:13px;">未选择</span>

      <button class="btn btn-warning h-lg" @click="startBatchModify" :disabled="running || !inputFolder || !outputFolder">
        {{ running ? '处理中...' : '批量修改' }}
      </button>
      <label class="flex-center" style="font-size:13px;color:#666;gap:4px;height:32px;">
        <input type="checkbox" v-model="selectAll" @change="toggleAll" />
        全选
      </label>
    </div>

    <!-- 参数预设 -->
    <div class="flex-center flex-shrink-0" style="gap:8px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">前缀</span>
      <input class="control h-lg w-sm" v-model="prefix" />

      <span class="label">预设</span>
      <select class="control h-lg" style="width:140px;" v-model="selectedPreset" @change="applyPreset">
        <option v-for="(conf, name) in presetResources" :key="name" :value="name">{{ name }}</option>
      </select>

      <span class="label">内存</span>
      <input class="control h-lg w-sm" v-model="mem" />

      <span class="label">核心数</span>
      <input class="control h-lg w-sm" v-model="nproc" />

      <span class="label">计算模式</span>
      <input class="control h-lg" style="width:180px;" v-model="calcMode" list="calcModePresets" />
      <datalist id="calcModePresets">
        <option v-for="preset in calcModePresets" :key="preset" :value="preset" />
      </datalist>

      <span class="label">泛函</span>
      <input class="control h-lg w-md" v-model="functional" list="functionalPresets" placeholder="如 b3lyp" />
      <datalist id="functionalPresets">
        <option v-for="preset in functionalPresets" :key="preset" :value="preset" />
      </datalist>

      <span class="label" style="font-weight:400;">/</span>

      <span class="label">基组</span>
      <input class="control h-lg w-lg" v-model="basis" list="basisPresets" placeholder="如 6-31g(d,p)" />
      <datalist id="basisPresets">
        <option v-for="preset in basisPresets" :key="preset" :value="preset" />
      </datalist>

      <span class="label">预览</span>
      <input class="control h-lg preview" style="width:340px;" :value="fullKeyword" readonly />

      <span class="label">电荷</span>
      <input class="control h-lg w-xs" v-model="charge" />

      <span class="label">自旋</span>
      <input class="control h-lg w-xs" v-model="mult" />

      <button class="btn btn-primary h-lg" @click="applyParamsAndSave">保存并应用</button>
    </div>

    <!-- 主区域 -->
    <div class="flex flex-1 min-h-0" style="gap:16px;border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
      <!-- 左侧文件列表 -->
      <div style="width:220px;background:#fafafa;border-right:1px solid #e8e8e8;overflow-y:auto;padding:8px 0;flex-shrink:0;">
        <div v-if="!fileList.length" style="color:#999;text-align:center;padding:20px;font-size:13px;">
          暂无 .gjf 文件
        </div>
        <div
          v-for="(file, idx) in fileList"
          :key="idx"
          @click="selectFile(idx)"
          @dblclick="startRename(idx)"
          :style="{
            padding: '4px 8px',
            cursor: 'pointer',
            background: selectedIndex === idx ? '#e6f7ff' : 'transparent',
            borderLeft: selectedIndex === idx ? '3px solid #1890ff' : '3px solid transparent',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }"
          @mouseenter="e=>e.target.style.background='#f0f0f0'"
          @mouseleave="e=>{if(selectedIndex!==idx) e.target.style.background='transparent'}"
        >
          <input type="checkbox" v-model="checkedFiles" :value="file" @click.stop />
          <span v-if="editingIndex === idx" style="flex:1;">
            <input
              v-model="editingName"
              @blur="finishRename"
              @keydown.enter="finishRename"
              @keydown.esc="cancelRename"
              @click.stop
              class="control h-lg"
              style="width:100%;border-color:#1890ff;"
              ref="renameInput"
            />
          </span>
          <span v-else style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {{ file }}
          </span>
        </div>
      </div>

      <!-- 右侧编辑器 -->
      <div class="flex-col flex-1 min-h-0" style="padding:12px;">
        <div class="flex" style="justify-content:space-between;align-items:center;margin-bottom:8px;flex-shrink:0;">
          <span style="font-size:13px;color:#888;">
            {{ currentFile ? currentFile : '未选择文件' }}
            <span v-if="mode === 'remote'" style="color:#1890ff;font-size:12px;margin-left:8px;">(远程)</span>
          </span>
          <div class="flex" style="gap:8px;">
            <button class="btn btn-success h-lg" @click="saveCurrentFile" :disabled="!currentFile || saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="btn btn-warning h-lg" @click="refreshList" :disabled="!currentFile">
              刷新列表
            </button>
          </div>
        </div>
        <textarea
          v-model="currentContent"
          :disabled="!currentFile"
          class="control"
          style="flex:1;width:100%;padding:8px;font-family:monospace;font-size:13px;resize:none;background:white;"
          spellcheck="false"
        ></textarea>
      </div>
    </div>

    <!-- 日志区域 -->
    <LogViewer :lines="logLines" :key="logKey" />

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
      inputFolder: '',
      outputFolder: '',
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
      const path = await window.electronAPI.selectDirectory({ title })
      if (path) {
        this[variable] = path
        this.addLog(`选择目录: ${title}: ${path}`, '#87d2ff')
        if (variable === 'inputFolder') {
          this.checkedFiles = []
          this.selectAll = false
          if (this.mode === 'local') this.loadFileListLocal()
          else this.loadFileListRemote()
        }
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
      try {
        const response = await fetch(`${this.backendUrl}/api/gjf/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: fullPath, content: this.currentContent })
        })
        const data = await response.json()
        if (response.ok) {
          this.addLog(`保存成功: ${this.currentFile} (本地)`, '#7cfc00')
        } else {
          this.addLog(`保存失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`保存失败: ${e.message}`, '#ff6b6b')
      }
      this.saving = false
    },

    async saveFileRemote() {
      this.saving = true
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
          this.addLog(`上传成功: ${this.currentFile} (远程)`, '#7cfc00')
        } else {
          this.addLog(`上传失败: ${uploadData.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`保存失败: ${e.message}`, '#ff6b6b')
      }
      this.saving = false
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
      if (this.mode === 'remote') {
        await this.saveFileRemote()
      } else {
        await this.saveFileLocal()
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
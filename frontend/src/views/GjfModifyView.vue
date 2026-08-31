<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">批量修改 GJF 参数</h2>
    <p style="color:#666;margin:0;font-size:14px;">选择文件夹，批量修改或单独预览/编辑 .gjf 文件</p>

    <!-- 控制栏 -->
    <div class="flex-center flex-shrink-0" style="gap:16px;flex-wrap:wrap;">
      <button class="btn btn-primary h-lg" @click="selectInputFolder">📂 输入文件夹</button>
      <span v-if="inputFolder" style="color:#1890ff;font-size:13px;">{{ inputFolder }}</span>
      <span v-else style="color:#999;font-size:13px;">未选择</span>

      <button class="btn btn-success h-lg" @click="selectOutputFolder">📁 输出文件夹</button>
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
    <div class="flex-center flex-shrink-0" style="gap:10px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">前缀</span>
      <input class="control h-lg w-sm" v-model="prefix" />

      <span class="label">预设</span>
      <select class="control h-lg w-xl" style="width:140px;" v-model="selectedPreset" @change="applyPreset">
        <option v-for="(conf, name) in presetResources" :key="name" :value="name">{{ name }}</option>
      </select>

      <span class="label">%mem</span>
      <input class="control h-lg w-sm" v-model="mem" />

      <span class="label">%nproc</span>
      <input class="control h-lg w-sm" v-model="nproc" />

      <!-- 计算模式 -->
      <span class="label">计算模式</span>
      <CustomSelect
        v-model="calcMode"
        :options="calcModePresets"
        placeholder="选择或输入"
        width="220px"
      />

      <!-- 泛函 -->
      <span class="label">泛函</span>
      <CustomSelect
        v-model="functional"
        :options="functionalPresets"
        placeholder="如 b3lyp"
        width="160px"
      />

      <span class="label" style="font-weight:400;padding:0 2px;">/</span>

      <!-- 基组 -->
      <span class="label">基组</span>
      <CustomSelect
        v-model="basis"
        :options="basisPresets"
        placeholder="如 6-31g(d,p)"
        width="160px"
      />

      <!-- 完整关键词预览 -->
      <span class="label">--预览-→</span>
      <input class="control h-lg w-3xl preview" style="width:340px;" :value="fullKeyword" readonly />

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
          </span>
          <div class="flex" style="gap:8px;">
            <button class="btn btn-success h-lg" @click="saveCurrentFile" :disabled="!currentFile || saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="btn btn-warning h-lg" @click="reloadCurrentFile" :disabled="!currentFile">
              🔄 重新加载
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
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'
import CustomSelect from '../components/CustomSelect.vue'

export default {
  name: 'GjfModifyView',
  components: { LogViewer, CustomSelect },
  data() {
    return {
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
      selectedPreset: 'students',
      presetResources: {
        'hachimi单并行': { nproc: '10', mem: '40GB' },
        'hachimi四并行': { nproc: '4', mem: '10GB' },
        'Tomori八队列': { nproc: '12', mem: '12GB' },
        'students': { nproc: '8', mem: '20GB' },
        'zstoffice': { nproc: '8', mem: '20GB' },
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
    }
  },
  computed: {
    fullKeyword() {
      const mode = this.calcMode.trim()
      const func = this.functional.trim()
      const bas = this.basis.trim()
      let funcBasis = ''
      if (func && bas) {
        funcBasis = `${func}/${bas}`
      } else if (func) {
        funcBasis = func
      } else if (bas) {
        funcBasis = bas
      }
      if (!mode && !funcBasis) return ''
      if (!mode) return funcBasis
      if (!funcBasis) return mode
      return `${mode} ${funcBasis}`
    }
  },
  watch: {
    inputFolder(newVal) {
      if (newVal) this.loadFileList()
      else {
        this.fileList = []
        this.selectedIndex = -1
        this.currentFile = null
        this.currentContent = ''
        this.checkedFiles = []
        this.selectAll = false
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
    async selectFolder(variable, title) {
      const path = await window.electronAPI.selectDirectory({ title })
      if (path) {
        this[variable] = path
        this.addLog(`📂 ${title}: ${path}`, '#87d2ff')
        if (variable === 'inputFolder') {
          this.checkedFiles = []
          this.selectAll = false
          this.loadFileList()
        }
      }
    },
    selectInputFolder() {
      this.selectFolder('inputFolder', '选择包含 .gjf 的文件夹')
    },
    selectOutputFolder() {
      this.selectFolder('outputFolder', '选择输出文件夹')
    },

    async loadFileList() {
      if (!this.inputFolder) return
      try {
        const normalizedPath = this.inputFolder.replace(/\\/g, '/')
        const url = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/list?path=${encodeURIComponent(normalizedPath)}`
        const response = await fetch(url)
        const data = await response.json()
        if (response.ok) {
          this.fileList = data.files || []
          this.checkedFiles = this.checkedFiles.filter(f => this.fileList.includes(f))
          if (this.fileList.length) {
            this.selectedIndex = 0
            this.loadFileContent(this.fileList[0])
          } else {
            this.selectedIndex = -1
            this.currentFile = null
            this.currentContent = ''
          }
          this.addLog(`找到 ${this.fileList.length} 个 .gjf 文件`, '#87d2ff')
        } else {
          this.addLog(`❌ 加载文件列表失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`❌ 加载文件列表失败: ${e.message}`, '#ff6b6b')
      }
    },

    selectFile(idx) {
      if (idx < 0 || idx >= this.fileList.length) return
      this.selectedIndex = idx
      this.loadFileContent(this.fileList[idx])
    },

    async loadFileContent(filename) {
      if (!this.inputFolder) return
      const fullPath = `${this.inputFolder}\\${filename}`
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/read`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: fullPath })
        })
        const data = await response.json()
        if (response.ok) {
          this.currentFile = filename
          this.currentContent = data.content
        } else {
          this.addLog(`❌ 读取文件失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`❌ 读取文件失败: ${e.message}`, '#ff6b6b')
      }
    },

    reloadCurrentFile() {
      if (this.currentFile) {
        this.loadFileContent(this.currentFile)
        this.addLog(`🔄 重新加载 ${this.currentFile}`, '#87d2ff')
      }
    },

    async saveCurrentFile() {
      if (!this.currentFile) return
      const fullPath = `${this.inputFolder}\\${this.currentFile}`
      this.saving = true
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: fullPath, content: this.currentContent })
        })
        const data = await response.json()
        if (response.ok) {
          this.addLog(`保存成功: ${this.currentFile}`, '#7cfc00')
        } else {
          this.addLog(`❌ 保存失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`❌ 保存失败: ${e.message}`, '#ff6b6b')
      }
      this.saving = false
    },

    startRename(idx) {
      this.editingIndex = idx
      this.editingName = this.fileList[idx]
      this.$nextTick(() => {
        const input = this.$refs.renameInput
        if (input) {
          input.focus()
          input.select()
        }
      })
    },

    async finishRename() {
      const idx = this.editingIndex
      if (idx === -1) return
      const oldName = this.fileList[idx]
      const newName = this.editingName.trim()
      if (!newName || newName === oldName) {
        this.cancelRename()
        return
      }
      if (this.fileList.some((f, i) => i !== idx && f === newName)) {
        this.addLog(`❌ 文件名 "${newName}" 已存在`, '#ff6b6b')
        this.cancelRename()
        return
      }
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/rename`, {
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
          this.addLog(`重命名成功: ${oldName} → ${newName}`, '#7cfc00')
          if (this.currentFile === newName) this.loadFileContent(newName)
        } else {
          this.addLog(`❌ 重命名失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`❌ 重命名失败: ${e.message}`, '#ff6b6b')
      }
      this.cancelRename()
    },

    cancelRename() {
      this.editingIndex = -1
      this.editingName = ''
    },

    applyPreset() {
      const preset = this.presetResources[this.selectedPreset]
      if (preset) {
        this.mem = preset.mem
        this.nproc = preset.nproc
        this.addLog(`⚙️ 应用预设: ${this.selectedPreset}`, '#87d2ff')
      }
    },

    async applyParamsAndSave() {
      if (!this.currentFile) {
        this.addLog('⚠️ 请先选择文件', '#ffa500')
        return
      }
      const keyword = this.fullKeyword
      if (!keyword) {
        this.addLog('⚠️ 请填写计算模式、泛函和基组', '#ffa500')
        return
      }
      this.addLog('⏳ 应用参数并保存...', '#87d2ff')
      try {
        const applyResp = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/apply-params`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: this.currentContent,
            mem: this.mem,
            nproc: this.nproc,
            keyword: keyword,
            charge: this.charge,
            mult: this.mult
          })
        })
        const applyData = await applyResp.json()
        if (!applyResp.ok) throw new Error(applyData.detail || '应用参数失败')

        const fullPath = `${this.inputFolder}\\${this.currentFile}`
        const saveResp = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: fullPath, content: applyData.content })
        })
        const saveData = await saveResp.json()
        if (!saveResp.ok) throw new Error(saveData.detail || '保存失败')

        this.currentContent = applyData.content
        this.addLog(`参数已应用并保存到 ${this.currentFile}`, '#7cfc00')
      } catch (e) {
        this.addLog(`❌ 操作失败: ${e.message}`, '#ff6b6b')
      }
    },

    async startBatchModify() {
      if (this.running) return
      if (!this.inputFolder || !this.outputFolder) {
        this.addLog('⚠️ 请选择输入和输出文件夹', '#ffa500')
        return
      }
      if (!this.checkedFiles.length) {
        this.addLog('⚠️ 请至少勾选一个文件', '#ffa500')
        return
      }
      const keyword = this.fullKeyword
      if (!keyword) {
        this.addLog('⚠️ 请填写计算模式、泛函和基组', '#ffa500')
        return
      }

      this.running = true
      this.logLines.splice(0)
      this.logKey++
      this.addLog(`开始批量修改 ${this.checkedFiles.length} 个文件...`, '#00ff00')

      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/gjf/batch-modify`, {
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
              this.addLog(` ${item.filename} → ${item.output}`, '#7cfc00')
            } else {
              this.addLog(`❌ ${item.filename} 失败: ${item.message}`, '#ff6b6b')
            }
          })
          this.addLog(`批量修改完成，共处理 ${results.length} 个文件`, '#00ff00')
        } else {
          this.addLog(`❌ 批量修改失败: ${data.detail || '未知错误'}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`❌ 批量修改失败: ${e.message}`, '#ff6b6b')
      }
      this.running = false
    }
  }
}
</script>
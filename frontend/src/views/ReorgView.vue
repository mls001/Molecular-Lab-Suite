<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">重组能计算</h2>
    <p style="color:#666;margin:0;font-size:14px;">通过 SSH 连接远程服务器，提交 nomap.sh 任务（请先通过工具栏连接服务器）</p>

    <!-- ===== 预设管理 ===== -->
    <div class="flex-center flex-shrink-0" style="gap:8px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">预设</span>
      <select class="control h-lg" style="width:140px;" v-model="selectedPreset" @change="onPresetChange">
        <option value="">-- 选择预设 --</option>
        <option v-for="name in presetNames" :key="name" :value="name">{{ name }}</option>
      </select>
      <input class="control h-lg" style="width:120px;" v-model="newPresetName" placeholder="预设名称" />
      <button class="btn btn-primary h-lg" @click="savePreset">保存</button>
      <button class="btn btn-danger h-lg" @click="deletePreset" :disabled="!selectedPreset">删除</button>
    </div>

    <!-- ===== 任务参数 ===== -->
    <div class="flex-center flex-shrink-0" style="gap:10px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">工作目录</span>
      <input class="control h-lg" style="width:200px;" v-model="workdir" placeholder="/path/to/workdir" />
      <button class="btn btn-default h-lg" @click="openBrowser('workdir')">...</button>

      <span class="label">文件参数</span>
      <input class="control h-lg" style="width:150px;" v-model="fileArg" placeholder=".gjf 文件名或任务名" />
      <button class="btn btn-default h-lg" @click="openBrowser('fileArg')">...</button>

      <span class="label">g</span>
      <input class="control h-lg w-sm" v-model="g" placeholder="b3lyp" />
      <span class="label">o</span>
      <input class="control h-lg w-sm" v-model="o" placeholder="b3lyp/G" />
      <span class="label">gb</span>
      <input class="control h-lg w-sm" v-model="gb" placeholder="6-31G(d,p)" />
      <span class="label">ob</span>
      <input class="control h-lg w-sm" v-model="ob" placeholder="可选" />

      <span class="label">root</span>
      <input class="control h-lg w-xs" v-model="root" placeholder="1" />
      <span class="label">sm</span>
      <input class="control h-lg w-xs" v-model="sm" placeholder="1" />
      <span class="label">c</span>
      <input class="control h-lg w-xs" v-model="c" placeholder="0" />

      <button class="btn btn-success h-lg" @click="submitJob" :disabled="running || !connected">提交任务</button>
    </div>

    <!-- ===== 高级选项 ===== -->
    <div class="flex-center flex-shrink-0" style="gap:12px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;border-top:1px solid #e8e8e8;">
      <span style="font-weight:600;font-size:13px;color:#333;">高级选项</span>

      <label style="font-size:13px;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" v-model="useState1" />
        使用外部 state1 .fchk
      </label>
      <div v-if="useState1" class="flex-center" style="gap:4px;">
        <input class="control h-lg" style="width:200px;" v-model="state1Path" placeholder="远程路径" />
        <button class="btn btn-default h-lg" @click="openBrowser('state1Path')">...</button>
      </div>

      <label style="font-size:13px;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" v-model="useState2" />
        使用外部 state2 .fchk
      </label>
      <div v-if="useState2" class="flex-center" style="gap:4px;">
        <input class="control h-lg" style="width:200px;" v-model="state2Path" placeholder="远程路径" />
        <button class="btn btn-default h-lg" @click="openBrowser('state2Path')">...</button>
      </div>

      <label style="font-size:13px;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" v-model="enableIC" />
        启用 IC 计算
      </label>
    </div>

    <!-- ===== 远程浏览器组件 ===== -->
    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="sessionId"
      :initial-path="browserInitialPath"
      :target="browserTarget"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />

    <!-- ===== 日志区域 ===== -->
    <LogViewer :lines="logLines" :key="logKey" />
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import RemoteFileBrowser from '@/components/RemoteFileBrowser.vue'
import LogViewer from '@/components/LogViewer.vue'

export default {
  name: 'ReorgView',
  components: { RemoteFileBrowser, LogViewer },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, connected, sessionId, username }
  },
  data() {
    return {
      // 任务参数
      workdir: '',
      fileArg: '',
      g: 'b3lyp',
      o: 'b3lyp/G',
      gb: '6-31G(d,p)',
      ob: '',
      root: '1',
      sm: '1',
      c: '0',

      // 高级选项
      useState1: false,
      state1Path: '',
      useState2: false,
      state2Path: '',
      enableIC: false,

      // 预设管理
      selectedPreset: '',
      newPresetName: '',
      presetNames: [],

      // 远程浏览器
      browserVisible: false,
      browserInitialPath: '/',
      browserTarget: '',

      // 任务状态
      running: false,
      logLines: [],
      logKey: 0,
      ws: null,
    }
  },
  mounted() {
    this.loadPresetList()
  },
  beforeUnmount() {
    if (this.ws) this.ws.close()
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 500) this.logLines.shift()
    },

    // ===== 预设管理 =====
    async loadPresetList() {
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/preset/list`)
        const data = await response.json()
        this.presetNames = data.names || []
      } catch (e) {
        console.error('加载预设列表失败:', e)
      }
    },

    async savePreset() {
      if (!this.newPresetName.trim()) {
        this.addLog('请输入预设名称', '#ffa500')
        return
      }
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/preset/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.newPresetName.trim(),
            workdir: this.workdir,
            fileArg: this.fileArg,
            g: this.g,
            o: this.o,
            gb: this.gb,
            ob: this.ob,
            root: this.root,
            sm: this.sm,
            c: this.c,
            useState1: this.useState1,
            state1Path: this.state1Path,
            useState2: this.useState2,
            state2Path: this.state2Path,
            enableIC: this.enableIC,
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.addLog(`预设 "${this.newPresetName}" 保存成功`, '#7cfc00')
          this.newPresetName = ''
          this.loadPresetList()
        } else {
          this.addLog(`保存失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`保存失败: ${e.message}`, '#ff6b6b')
      }
    },

    async onPresetChange() {
      if (!this.selectedPreset) return
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/preset/load?name=${encodeURIComponent(this.selectedPreset)}`)
        const data = await response.json()
        if (response.ok) {
          this.workdir = data.workdir || ''
          this.fileArg = data.fileArg || ''
          this.g = data.g || 'b3lyp'
          this.o = data.o || 'b3lyp/G'
          this.gb = data.gb || '6-31G(d,p)'
          this.ob = data.ob || ''
          this.root = data.root || '1'
          this.sm = data.sm || '1'
          this.c = data.c || '0'
          this.useState1 = data.useState1 || false
          this.state1Path = data.state1Path || ''
          this.useState2 = data.useState2 || false
          this.state2Path = data.state2Path || ''
          this.enableIC = data.enableIC || false
          this.addLog(`已加载预设 "${this.selectedPreset}"`, '#7cfc00')
        } else {
          this.addLog(`加载失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`加载失败: ${e.message}`, '#ff6b6b')
      }
    },

    async deletePreset() {
      if (!this.selectedPreset) {
        this.addLog('请选择一个预设', '#ffa500')
        return
      }
      if (!confirm(`确定删除预设 "${this.selectedPreset}" 吗？`)) return
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/preset/delete?name=${encodeURIComponent(this.selectedPreset)}`, {
          method: 'DELETE'
        })
        const data = await response.json()
        if (response.ok) {
          this.addLog(`已删除预设 "${this.selectedPreset}"`, '#7cfc00')
          this.selectedPreset = ''
          this.loadPresetList()
        } else {
          this.addLog(`删除失败: ${data.detail}`, '#ff6b6b')
        }
      } catch (e) {
        this.addLog(`删除失败: ${e.message}`, '#ff6b6b')
      }
    },

    // ===== 远程浏览器 =====
    openBrowser(target) {
      if (!this.connected) {
        this.addLog('请先通过工具栏连接服务器', '#ffa500')
        return
      }
      let initialPath = '/'
      if (target === 'workdir') initialPath = this.workdir || `/home/${this.username}`
      else if (target === 'fileArg') initialPath = this.workdir || `/home/${this.username}`
      else if (target === 'state1Path') initialPath = this.state1Path || `/home/${this.username}`
      else if (target === 'state2Path') initialPath = this.state2Path || `/home/${this.username}`
      this.browserInitialPath = initialPath
      this.browserTarget = target
      this.browserVisible = true
    },

    onBrowserSelect({ target, path, is_dir, name }) {
      if (target === 'workdir') {
        if (is_dir) {
          this.workdir = path
        } else {
          this.workdir = path.substring(0, path.lastIndexOf('/'))
        }
      } else if (target === 'fileArg') {
        this.fileArg = name
      } else if (target === 'state1Path') {
        this.state1Path = path
      } else if (target === 'state2Path') {
        this.state2Path = path
      }
      this.addLog(`已选择: ${path}`, '#87d2ff')
    },

    // ===== 提交任务 =====
    submitJob() {
      if (this.running) return
      if (!this.connected) {
        this.addLog('请先通过工具栏连接服务器', '#ffa500')
        return
      }
      if (!this.workdir || !this.fileArg) {
        this.addLog('请填写工作目录和文件参数', '#ffa500')
        return
      }
      if (this.useState1 && !this.state1Path.trim()) {
        this.addLog('请填写 state1 .fchk 路径', '#ffa500')
        return
      }
      if (this.useState2 && !this.state2Path.trim()) {
        this.addLog('请填写 state2 .fchk 路径', '#ffa500')
        return
      }

      this.running = true
      this.logLines = []
      this.addLog('开始提交任务...', '#00ff00')

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/reorg`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog('WebSocket 已连接', '#87d2ff')
        const params = {
          session_id: this.sessionId,
          workdir: this.workdir,
          file_arg: this.fileArg,
          g: this.g,
          o: this.o,
          gb: this.gb,
          ob: this.ob,
          root: this.root,
          sm: this.sm,
          c: this.c,
        }
        if (this.useState1) params.state1 = this.state1Path.trim()
        if (this.useState2) params.state2 = this.state2Path.trim()
        if (!this.enableIC) params.ic = 'off'

        this.ws.send(JSON.stringify({
          action: 'run_reorg',
          params: params
        }))
      }

      this.ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'info':
            this.addLog(`[INFO] ${data.message}`, '#87d2ff')
            break
          case 'log':
            this.addLog(`[${data.tag}] ${data.message}`, data.tag === 'STDERR' ? '#ff6b6b' : '#d4d4d4')
            break
          case 'done':
            this.addLog(`[DONE] ${data.message}`, '#00ff00')
            this.running = false
            this.ws.close()
            break
          case 'error':
            this.addLog(`[ERROR] ${data.message}`, '#ff6b6b')
            this.running = false
            this.ws.close()
            break
          default:
            this.addLog(JSON.stringify(data))
        }
      }

      this.ws.onerror = () => {
        this.addLog('WebSocket 错误', '#ff6b6b')
        this.running = false
      }
      this.ws.onclose = () => {
        this.running = false
      }
    }
  }
}
</script>
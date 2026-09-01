<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">重组能计算</h2>
    <p style="color:#666;margin:0;font-size:14px;">通过 SSH 连接远程服务器，提交 nomap.sh 任务</p>

    <!-- 预设管理 -->
    <div class="flex-center flex-shrink-0" style="gap:8px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">预设</span>
      <select class="control h-lg" style="width:140px;" v-model="selectedPreset" @change="onPresetChange">
        <option value="">-- 选择预设 --</option>
        <option v-for="name in presetNames" :key="name" :value="name">{{ name }}</option>
      </select>
      <input class="control h-lg" style="width:120px;" v-model="newPresetName" placeholder="预设名称" />
      <button class="btn btn-primary h-lg" @click="savePreset" :disabled="!remote.connected.value">保存</button>
      <button class="btn btn-danger h-lg" @click="deletePreset" :disabled="!selectedPreset">删除</button>
    </div>

    <!-- 服务器连接区域（连接后锁定输入框） -->
    <div class="flex-center flex-shrink-0" style="gap:10px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">主机</span>
      <input class="control h-lg" style="width:120px;" v-model="host" placeholder="IP 地址" :disabled="remote.connected.value" />
      <span class="label">端口</span>
      <input class="control h-lg w-sm" v-model="port" placeholder="22" :disabled="remote.connected.value" />
      <span class="label">用户名</span>
      <input class="control h-lg" style="width:100px;" v-model="username" placeholder="用户名" :disabled="remote.connected.value" />
      <span class="label">密码</span>
      <input class="control h-lg" style="width:120px;" v-model="password" type="password" placeholder="密码" :disabled="remote.connected.value" />
      <button class="btn btn-primary h-lg" @click="handleConnect" :disabled="remote.connecting.value || remote.connected.value">
        {{ remote.connecting.value ? '连接中...' : '连接' }}
      </button>
      <button v-if="remote.connected.value" class="btn btn-danger h-lg" @click="handleDisconnect" :disabled="remote.connecting.value">
        断开
      </button>
      <span v-if="remote.connected.value" style="color:#52c41a;font-size:13px;">已连接</span>
      <span v-else style="color:#999;font-size:13px;">未连接</span>
    </div>

    <!-- 任务参数 -->
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

      <button class="btn btn-success h-lg" @click="submitJob" :disabled="running || !remote.connected.value">提交任务</button>
    </div>

    <!-- 高级选项 -->
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

    <!-- 终端区域 -->
    <div class="flex-1 min-h-0" style="border:1px solid #e8e8e8;border-radius:6px;overflow:hidden;background:#1e1e1e;">
      <XTermTerminal
        v-if="remote.connected.value && remote.sessionId.value"
        :session-id="remote.sessionId.value"
        :initial-path="workdir || `/home/${username}`"
      />
      <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;font-size:14px;background:#1e1e1e;">
        未连接服务器，请先填写连接信息并点击“连接”
      </div>
    </div>

    <!-- 远程浏览器组件 -->
    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="remote.sessionId.value"
      :initial-path="browserInitialPath"
      :target="browserTarget"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />

    <!-- 日志区域 -->
    <LogViewer :lines="logLines" :key="logKey" />
  </div>
</template>

<script>
import { useRemote } from '@/composables/useRemote'
import RemoteFileBrowser from '@/components/RemoteFileBrowser.vue'
import LogViewer from '@/components/LogViewer.vue'
import XTermTerminal from '@/components/XTermTerminal.vue'

export default {
  name: 'ReorgView',
  components: { RemoteFileBrowser, LogViewer, XTermTerminal },
  setup() {
    const remote = useRemote()
    return { remote }
  },
  data() {
    return {
      host: '',
      port: 22,
      username: '',
      password: '',
      selectedPreset: '',
      newPresetName: '',
      presetNames: [],
      workdir: '',
      fileArg: '',
      g: 'b3lyp',
      o: 'b3lyp/G',
      gb: '6-31G(d,p)',
      ob: '',
      root: '1',
      sm: '1',
      c: '0',
      useState1: false,
      state1Path: '',
      useState2: false,
      state2Path: '',
      enableIC: false,
      browserVisible: false,
      browserInitialPath: '/',
      browserTarget: '',
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
    if (this.remote.connected.value) {
      this.remote.disconnect()
    }
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 500) this.logLines.shift()
    },

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
      if (!this.host || !this.username) {
        this.addLog('请填写主机和用户名', '#ffa500')
        return
      }
      try {
        const response = await fetch(`http://${__BACKEND_HOST__}:${__BACKEND_PORT__}/api/preset/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.newPresetName.trim(),
            host: this.host,
            port: this.port,
            username: this.username,
            password: this.password
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
          this.host = data.host || ''
          this.port = data.port || 22
          this.username = data.username || ''
          this.password = data.password || ''
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

    async handleConnect() {
      if (this.remote.connecting.value) return
      if (this.remote.connected.value) {
        await this.remote.disconnect()
      }
      if (!this.host || !this.username) {
        this.addLog('请填写主机和用户名', '#ffa500')
        return
      }
      const result = await this.remote.connect({
        host: this.host,
        port: this.port,
        username: this.username,
        password: this.password
      })
      this.addLog(result.message, result.success ? '#7cfc00' : '#ff6b6b')
      if (result.success) {
        this.browserInitialPath = `/home/${this.username}`
      }
    },

    async handleDisconnect() {
      if (!this.remote.connected.value) return
      await this.remote.disconnect()
      this.addLog('已断开连接', '#ff6b6b')
    },

    openBrowser(target) {
      if (!this.remote.connected.value) {
        this.addLog('请先连接服务器', '#ffa500')
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

    submitJob() {
      if (this.running) return
      if (!this.remote.connected.value) {
        this.addLog('请先连接服务器', '#ffa500')
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
          session_id: this.remote.sessionId.value,
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
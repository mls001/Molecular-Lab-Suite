<template>
  <!-- 重组能（计算 + 解析合并单页）：左=解析文件列表 / 中=谱图 / 右=上计算参数 · 下解析目录 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- ===== 左：解析文件列表 ===== -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>解析文件列表</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ allData.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!allData.length" class="ide-empty">暂无解析文件<br>请先在右下选择目录并解析</div>
          <div
            v-for="(item, idx) in allData"
            :key="idx"
            class="ide-list-item"
            :class="{ active: selectedIndex === idx }"
            @click="selectFile(idx)"
          >
            {{ item.filename }}
          </div>
        </div>
      </aside>

      <!-- ===== 中：重组能谱图 ===== -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>重组能谱</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">
            {{ currentData ? currentData.filename : '—' }}
          </span>
        </div>
        <!-- 谱图上方：读取/计算总重组能一览 -->
        <div
          v-if="currentData"
          class="flex-center"
          style="gap:18px;flex-shrink:0;padding:5px 12px;border-bottom:1px solid var(--c-border-soft);font-size:12px;color:var(--c-text-2);flex-wrap:wrap;background:var(--c-bar);"
        >
          <span>总重组能：<b style="color:var(--c-accent);">{{ Number(currentData.reorg_total).toFixed(4) }} eV</b></span>
          <span>计算总重组能：<b style="color:var(--c-accent);">{{ computedTotalReorg.toFixed(4) }} eV</b></span>
          <span>模式数：{{ (currentData.frequencies || []).length }}</span>
        </div>
        <div class="flex-1 min-h-0" style="position:relative;padding:6px;">
          <!-- ECharts 独立占满容器；Vue 不管理其内部，避免外部 canvas 干扰 Vue 插入锚点 -->
          <div ref="chartContainer" style="position:absolute;top:6px;left:6px;right:6px;bottom:6px;border-radius:4px;border:1px solid var(--c-hover);"></div>
          <div v-if="!chartData.length" style="position:absolute;top:6px;left:6px;right:6px;bottom:6px;display:flex;align-items:center;justify-content:center;color:var(--c-text-3);font-size:14px;pointer-events:none;">
            等待数据
          </div>
        </div>
      </section>

      <!-- ===== 右：上=计算参数 / 下=解析目录 ===== -->
      <aside class="ide-pane ide-col ide-right" style="width:330px;">
        <div class="ide-pane-head"><span>重组能</span></div>
        <div class="ide-pane-body">

          <!-- 上栏：远程计算参数 -->
          <div class="ide-group">
            <span class="label">计算重组能（远程任务）</span>
            <span class="label" style="font-weight:400;font-size:12px;color:var(--c-text-3);">
              连接状态：<span :style="{ color: connected ? 'var(--c-green)' : 'var(--c-danger)' }">{{ connected ? remoteStore.displayName : '未连接' }}</span>
            </span>
            <div style="font-size:12px;color:var(--c-text-3);">提交 nomap 任务（g/o/gb/ob 等参数）</div>
            <div class="flex-col" style="gap:5px;">
              <div class="flex-center" style="gap:6px;">
                <span class="label" style="font-weight:400;width:66px;">工作目录</span>
                <input class="control" style="flex:1;min-width:0;height:28px;" v-model="workdir" placeholder="/path/to/workdir" />
                <button class="btn" style="width:32px;height:28px;padding:0;" @click="openBrowser('workdir')">…</button>
              </div>
              <div class="flex-center" style="gap:6px;">
                <span class="label" style="font-weight:400;width:66px;">文件参数</span>
                <input class="control" style="flex:1;min-width:0;height:28px;" v-model="fileArg" placeholder=".gjf 文件名或任务名" />
                <button class="btn" style="width:32px;height:28px;padding:0;" @click="openBrowser('fileArg')">…</button>
              </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">g（基态泛函）</span><input class="control" style="width:100%;height:28px;" v-model="g" placeholder="b3lyp" /></div>
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">o（激发态泛函）</span><input class="control" style="width:100%;height:28px;" v-model="o" placeholder="b3lyp/G" /></div>
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">gb（基组）</span><input class="control" style="width:100%;height:28px;" v-model="gb" placeholder="6-31G(d,p)" /></div>
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">ob（激发态基组）</span><input class="control" style="width:100%;height:28px;" v-model="ob" placeholder="可选" /></div>
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">root</span><input class="control" style="width:100%;height:28px;" v-model="root" placeholder="1" /></div>
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">sm</span><input class="control" style="width:100%;height:28px;" v-model="sm" placeholder="1" /></div>
              <div class="flex-col" style="gap:2px;"><span style="font-size:11px;color:var(--c-text-3);">c</span><input class="control" style="width:100%;height:28px;" v-model="c" placeholder="0" /></div>
              <div class="flex-col" style="gap:2px;">
                <span style="font-size:11px;color:var(--c-text-3);">coord（建议默认INTERNAL）</span>
                <select class="control" style="width:100%;height:28px;" v-model="coord">
                  <option value="CARTESIAN">CARTESIAN</option>
                  <option value="INTERNAL">INTERNAL</option>
                </select>
              </div>
            </div>
            <div style="border-top:1px dashed var(--c-border-soft);padding-top:6px;">
              <label style="font-size:12px;display:flex;align-items:center;gap:5px;margin-bottom:4px;">
                <input type="checkbox" v-model="useState1" /> 外部 state1 .fchk
              </label>
              <div v-if="useState1" class="flex" style="gap:6px;margin-bottom:4px;">
                <input class="control" style="flex:1;min-width:0;height:26px;" v-model="state1Path" placeholder="远程路径" />
                <button class="btn" style="width:32px;height:26px;padding:0;" @click="openBrowser('state1Path')">…</button>
              </div>
              <label style="font-size:12px;display:flex;align-items:center;gap:5px;margin-bottom:4px;">
                <input type="checkbox" v-model="useState2" /> 外部 state2 .fchk
              </label>
              <div v-if="useState2" class="flex" style="gap:6px;margin-bottom:4px;">
                <input class="control" style="flex:1;min-width:0;height:26px;" v-model="state2Path" placeholder="远程路径" />
                <button class="btn" style="width:32px;height:26px;padding:0;" @click="openBrowser('state2Path')">…</button>
              </div>
              <label style="font-size:12px;display:flex;align-items:center;gap:5px;">
                <input type="checkbox" v-model="enableIC" /> 启用 IC 计算
              </label>
            </div>
            <button class="btn btn-success" style="height:30px;" @click="submitJob" :disabled="running || !connected">
              {{ jobRunning ? '任务进行中...' : '提交任务' }}
            </button>
          </div>

          <!-- 下栏：解析目录 -->
          <div class="ide-group">
            <span class="label">重组能解析（目录选择）</span>
            <div class="flex-center" style="gap:6px;">
              <span class="label" style="font-weight:400;">模式</span>
              <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'local' ? 'btn-primary' : 'btn-default'" @click="setParseMode('local')">本地</button>
              <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'remote' ? 'btn-primary' : 'btn-default'" @click="setParseMode('remote')" :disabled="!connected">远程</button>
            </div>
            <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;min-height:30px;line-height:1.5;">
              <template v-if="parseMode === 'local'">{{ parseFolder || '未选择本地文件夹（含 .out 与 HuangRhys 文件）' }}</template>
              <template v-else>{{ parseFolder || '未选择远程目录' }}</template>
            </div>
            <div class="flex" style="gap:6px;">
              <button class="btn" style="flex:1;height:28px;" @click="chooseParseFolder">选择目录</button>
              <button class="btn btn-primary" style="flex:1;height:28px;" @click="runParse" :disabled="running || !parseFolder">
                {{ parseRunning ? '解析中...' : '解析' }}
              </button>
            </div>
            <button v-if="allData.length" class="btn" style="height:26px;" @click="exportExcel">导出 Excel（所有解析结果）</button>
            <div style="font-size:12px;color:var(--c-text-3);line-height:1.6;">
              远程模式下将把目录中的 .out 与 HuangRhys 文件同步到本地缓存后解析；解析结果展示在左侧列表与中间谱图。
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 远程浏览器组件（用于远程目录/路径选择） -->
    <RemoteFileBrowser
      :visible="browserVisible"
      :session-id="sessionId"
      :initial-path="browserInitialPath"
      :target="browserTarget"
      @update:visible="browserVisible = $event"
      @select="onBrowserSelect"
    />

    <!-- 日志区域（保持在底部、终端之上） -->
    <LogViewer :lines="logLines" />
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'
import LogViewer from '../components/LogViewer.vue'
import RemoteFileBrowser from '../components/RemoteFileBrowser.vue'
import * as echarts from 'echarts'
import { pickDirectory } from '@/api/dialog'
import { cssVar } from '@/theme/theme'

const BACKEND_BASE = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`

export default {
  name: 'ReorgView',
  components: { LogViewer, RemoteFileBrowser },
  setup() {
    const remoteStore = useRemoteStore()
    const { connected, sessionId, username } = storeToRefs(remoteStore)
    return { remoteStore, connected, sessionId, username }
  },
  data() {
    return {
      // ---- 远程计算参数 ----
      workdir: '',
      fileArg: '',
      g: 'b3lyp',
      o: 'b3lyp/G',
      gb: '6-31G(d,p)',
      ob: '',
      root: '1',
      sm: '1',
      c: '0',
      coord: 'INTERNAL',
      useState1: false,
      state1Path: '',
      useState2: false,
      state2Path: '',
      enableIC: false,

      // ---- 解析 ----
      parseMode: 'local',
      parseFolder: '',
      allData: [],
      selectedIndex: 0,
      chartInstance: null,
      _resizeObserver: null,
      _lastChartData: null,

      // ---- 远程浏览器 ----
      browserVisible: false,
      browserInitialPath: '/',
      browserTarget: '',

      // ---- 状态 ----
      running: false,
      logLines: [],
      logKey: 0,
      ws: null,
      _pageActive: true,
    }
  },
  computed: {
    currentData() {
      if (this.allData.length && this.selectedIndex < this.allData.length) {
        return this.allData[this.selectedIndex]
      }
      return null
    },
    computedTotalReorg() {
      if (!this.currentData) return 0
      return (this.currentData.reorg_contrib || []).reduce((a, b) => a + b, 0)
    },
    chartData() {
      if (!this.currentData) return []
      const sorted = this.currentData.frequencies.map((freq, idx) => ({
        freq: freq,
        reorg: this.currentData.reorg_contrib[idx] || 0
      })).sort((a, b) => a.freq - b.freq)
      return sorted
    },
    jobRunning() {
      return this.running && !!this.ws && this._jobWs === true
    },
    parseRunning() {
      return this.running && !!this.ws && this._jobWs === false
    }
  },
  mounted() {
    this.initChart()
    window.addEventListener('mls-theme-change', this.rerenderChart)
  },
  beforeUnmount() {
    this._pageActive = false
    if (this.ws) {
      try { this.ws.close() } catch (e) { /* ignore */ }
      this.ws = null
    }
    window.removeEventListener('mls-theme-change', this.rerenderChart)
    if (this._resizeObserver) {
      this._resizeObserver.disconnect()
      this._resizeObserver = null
    }
    if (this.chartInstance) {
      this.chartInstance.dispose()
      this.chartInstance = null
    }
  },
  deactivated() {
    // 离开页面（keep-alive 停用）时停止远程任务/解析，避免后台消息更新已隐藏的组件
    this._pageActive = false
    if (this.ws) {
      try { this.ws.close() } catch (e) { /* ignore */ }
      this.ws = null
    }
    this.running = false
  },
  activated() {
    this._pageActive = true
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 300) this.logLines.shift()
    },

    // ==================== 谱图 ====================
    initChart() {
      const container = this.$refs.chartContainer
      if (!container) return
      if (this.chartInstance) {
        this.chartInstance.dispose()
        this.chartInstance = null
      }
      this.chartInstance = echarts.init(container)
      this._resizeObserver = new ResizeObserver(() => {
        if (this.chartInstance) this.chartInstance.resize()
      })
      this._resizeObserver.observe(container)
      this.updateChart([])
    },

    updateChart(data) {
      this._lastChartData = data || []
      if (!this.chartInstance) {
        this.initChart()
        if (!this.chartInstance) return
      }
      const C = {
        text: cssVar('--c-text'),
        sub: cssVar('--c-text-2'),
        grid: cssVar('--c-border'),
        line: cssVar('--c-accent'),
        area: cssVar('--c-accent-soft')
      }
      if (!data || data.length === 0) {
        this.chartInstance.setOption({
          title: { text: '重组能谱', left: 'center', top: 8, textStyle: { fontSize: 14, fontWeight: 'normal', color: C.text } },
          xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: C.grid } }, axisLabel: { color: C.sub } },
          yAxis: { type: 'value', min: 0, name: '重组能 (eV)', nameTextStyle: { color: C.sub }, axisLabel: { color: C.sub } },
          series: [{ type: 'line', data: [] }]
        }, true)
        return
      }
      const freqValues = data.map(d => d.freq.toFixed(1))
      const reorgValues = data.map(d => d.reorg)
      const maxReorg = Math.max(...reorgValues, 0.001)
      const option = {
        title: { text: '重组能谱', left: 'center', top: 8, textStyle: { fontSize: 14, fontWeight: 'normal', color: C.text } },
        tooltip: {
          trigger: 'axis',
          backgroundColor: cssVar('--c-elev'),
          borderColor: cssVar('--c-border'),
          textStyle: { color: C.text },
          formatter: function (params) {
            const p = params[0]
            return `频率: ${p.name} cm⁻¹<br>重组能: ${p.value.toFixed(6)} eV`
          }
        },
        grid: { left: 60, right: 20, top: 50, bottom: 40 },
        xAxis: {
          name: '频率 (cm⁻¹)', nameLocation: 'center', nameGap: 25, type: 'category', data: freqValues,
          nameTextStyle: { color: C.sub }, axisLine: { lineStyle: { color: C.grid } },
          axisLabel: { color: C.sub, fontSize: 10, interval: Math.max(0, Math.floor(freqValues.length / 30)) }
        },
        yAxis: {
          name: '重组能 (eV)', nameLocation: 'center', nameGap: 35, type: 'value', min: 0, max: maxReorg * 1.1,
          nameTextStyle: { color: C.sub }, splitLine: { lineStyle: { color: C.grid } },
          axisLabel: { color: C.sub, fontSize: 10, formatter: function (value) { return value.toExponential(2) } }
        },
        series: [{
          type: 'line', data: reorgValues, smooth: false, symbol: 'none',
          lineStyle: { color: C.line, width: 1.5 }, areaStyle: { color: C.area }
        }]
      }
      this.chartInstance.setOption(option, true)
      this.chartInstance.resize()
    },

    rerenderChart() {
      this.$nextTick(() => {
        this.updateChart(this._lastChartData)
      })
    },

    selectFile(idx) {
      if (idx >= 0 && idx < this.allData.length) {
        this.selectedIndex = idx
        this.$nextTick(() => {
          this.updateChart(this.chartData)
        })
      }
    },

    // ==================== 远程浏览器 ====================
    openBrowser(target) {
      if (!this.connected) {
        this.addLog('请先连接服务器', '#ffa500')
        return
      }
      let initialPath = '/'
      if (target === 'workdir') initialPath = this.workdir || `/home/${this.username}`
      else if (target === 'fileArg') initialPath = this.workdir || `/home/${this.username}`
      else if (target === 'state1Path') initialPath = this.state1Path || `/home/${this.username}`
      else if (target === 'state2Path') initialPath = this.state2Path || `/home/${this.username}`
      else if (target === 'parseRemote') initialPath = (this.parseMode === 'remote' && this.parseFolder) || `/home/${this.username}`
      this.browserInitialPath = initialPath
      this.browserTarget = target
      this.browserVisible = true
    },

    onBrowserSelect({ target, path, is_dir, name }) {
      if (target === 'workdir') {
        this.workdir = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
      } else if (target === 'fileArg') {
        this.fileArg = name
      } else if (target === 'state1Path') {
        this.state1Path = path
      } else if (target === 'state2Path') {
        this.state2Path = path
      } else if (target === 'parseRemote') {
        if (is_dir) this.parseFolder = path
        else this.parseFolder = path.substring(0, path.lastIndexOf('/'))
      }
      this.addLog(`已选择: ${path}`, '#87d2ff')
    },

    // 切换解析模式时清空旧的目录选择与解析结果，避免本地/远程路径串用
    setParseMode(mode) {
      if (this.parseMode === mode) return
      this.parseMode = mode
      this.parseFolder = ''
      this.allData = []
      this.selectedIndex = 0
      this.updateChart([])
      this.addLog(mode === 'remote' ? '已切换到远程解析模式，请选择远程目录' : '已切换到本地解析模式，请选择本地文件夹', '#87d2ff')
    },

    // ==================== 远程计算任务 ====================
    submitJob() {
      if (this.running) return
      if (!this.connected) {
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
      this._jobWs = true
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
          g: this.g, o: this.o, gb: this.gb, ob: this.ob,
          root: this.root, sm: this.sm, c: this.c, coord: this.coord,
        }
        if (this.useState1) params.state1 = this.state1Path.trim()
        if (this.useState2) params.state2 = this.state2Path.trim()
        if (!this.enableIC) params.ic = 'off'
        this.ws.send(JSON.stringify({ action: 'run_reorg', params: params }))
      }
      this.ws.onmessage = (e) => {
        if (!this._pageActive || !this.ws) return
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'info': this.addLog(`[INFO] ${data.message}`, '#87d2ff'); break
          case 'log': this.addLog(`[${data.tag}] ${data.message}`, data.tag === 'STDERR' ? '#ff6b6b' : '#d4d4d4'); break
          case 'done':
            this.addLog(`[DONE] ${data.message}`, '#00ff00')
            this.finishWs()
            break
          case 'error':
            this.addLog(`[错误] ${data.message}`, '#ff6b6b')
            this.finishWs()
            break
          default: this.addLog(JSON.stringify(data))
        }
      }
      this.ws.onerror = () => {
        this.addLog('[错误] WebSocket 连接失败', '#ff6b6b')
        this.finishWs()
      }
      this.ws.onclose = () => { this.finishWs() }
    },

    // ==================== 解析（本地 / 远程） ====================
    async chooseParseFolder() {
      if (this.parseMode === 'remote') {
        if (!this.connected) {
          this.addLog('请先连接服务器', '#ffa500')
          return
        }
        this.openBrowser('parseRemote')
        return
      }
      // 本地模式：直接选目录后自动解析
      let path
      try {
        path = await pickDirectory('选择包含 .out 与 HuangRhys 文件的文件夹')
      } catch (e) {
        this.addLog(`选择目录失败: ${e.message}`, '#ff6b6b')
        return
      }
      if (!path) return
      this.parseFolder = path
      this.runParse()
    },

    async runParse() {
      if (this.running || !this.parseFolder) return
      if (this.parseMode === 'remote') {
        await this.runRemoteParse()
        return
      }
      this.startExtractWs(this.parseFolder)
    },

    // 远程解析：只缓存目标文件（.out 与对应的 HuangRhys 文件），避免把目录整体（可能很大）下载到本地
    async runRemoteParse() {
      if (!this._pageActive) return
      try {
        this.running = true
        this.addLog(`读取远程目录: ${this.parseFolder}`, '#87d2ff')
        const lsResp = await fetch(`${BACKEND_BASE}/api/remote/ls`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, path: this.parseFolder })
        })
        const lsData = await lsResp.json()
        if (!lsResp.ok) throw new Error(lsData.detail || '无法读取远程目录')
        const files = (lsData.entries || []).filter(x => !x.is_dir)
        // 目标文件：*.out 或名字含 huang(黄里斯) 的文件
        const need = files.filter(f => /\.out$/i.test(f.name) || /huang/i.test(f.name))
        if (!need.length) {
          this.addLog('远程目录中未找到 .out 或 HuangRhys 目标文件', '#ffa500')
          this.running = false
          return
        }
        const posix = (p, n) => `${p.replace(/\/+$/, '')}/${n}`
        const paths = need.map(f => posix(this.parseFolder, f.name))
        this.addLog(`同步 ${paths.length} 个目标文件（.out + HuangRhys）到本地缓存...`, '#87d2ff')
        const dlResp = await fetch(`${BACKEND_BASE}/api/remote/batch-download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, paths })
        })
        const dlData = await dlResp.json()
        if (!dlResp.ok) throw new Error(dlData.detail || '下载失败')
        const okPaths = (dlData.results || []).filter(r => r.status === 'success')
        if (!okPaths.length) {
          this.addLog('目标文件同步失败，请检查远程目录权限', '#ff6b6b')
          this.running = false
          return
        }
        // 缓存路径可能同时含 / 与 \（后端为 Windows），取最后一个分隔符前的目录作为解析目录
        const cp = okPaths[0].cache_path || ''
        const idx = Math.max(cp.lastIndexOf('/'), cp.lastIndexOf('\\'))
        const cacheDir = idx >= 0 ? cp.substring(0, idx) : ''
        if (!cacheDir) {
          this.addLog('无法从下载结果确定缓存目录', '#ff6b6b')
          this.running = false
          return
        }
        this.addLog(`已同步 ${okPaths.length} 个目标文件 → 缓存目录: ${cacheDir}`, '#87d2ff')
        this.running = false
        if (!this._pageActive) return // 用户已离开页面则不继续解析
        this.startExtractWs(cacheDir)
      } catch (e) {
        this.addLog(`远程解析失败: ${e.message}`, '#ff6b6b')
        this.running = false
      }
    },

    startExtractWs(folder) {
      this.running = true
      this._jobWs = false
      this.allData = []
      this.selectedIndex = 0
      this.updateChart([])
      this.logLines = []
      this.addLog('开始解析重组能数据...', '#00ff00')
      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/reorg-extract`
      this.ws = new WebSocket(wsUrl)
      this.ws.onopen = () => {
        this.addLog('WebSocket 已连接', '#87d2ff')
        this.ws.send(JSON.stringify({ action: 'extract_reorg', folder }))
      }
      this.ws.onmessage = (e) => {
        if (!this._pageActive || !this.ws) return
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog(`${data.filename} 解析成功 [${data.index}/${data.total}]`, '#7cfc00')
            } else {
              this.addLog(`${data.filename} 解析失败: ${data.message}`, '#ff6b6b')
            }
            break
          case 'result':
            this.allData = data.data || []
            if (this.allData.length) {
              this.selectedIndex = 0
              this.addLog(`共解析 ${this.allData.length} 个文件`, '#87d2ff')
              const valid = this.allData.filter(d => (d.frequencies || []).length > 0).length
              if (!valid) {
                this.addLog('[提示] 没有文件解析出有效数据：请确认目录同时包含 FCclasses 的 .out 与对应的 HuangRhys 文件', '#ffa500')
              }
              this.$nextTick(() => {
                this.updateChart(this.chartData)
              })
            } else {
              this.addLog('未解析出任何文件数据', '#ffa500')
            }
            break
          case 'done':
            this.addLog(`${data.message}`, '#00ff00')
            this.finishWs()
            break
          case 'error':
            this.addLog(`[错误] ${data.message}`, '#ff6b6b')
            this.finishWs()
            break
          default:
            this.addLog(JSON.stringify(data))
        }
      }
      this.ws.onerror = () => {
        this.addLog('[错误] WebSocket 连接失败', '#ff6b6b')
        this.finishWs()
      }
      this.ws.onclose = () => { this.finishWs() }
    },

    finishWs() {
      this.running = false
      this._jobWs = undefined
      if (this.ws) {
        try { this.ws.close() } catch (e) { /* ignore */ }
        this.ws = null
      }
    },

    // ==================== 导出 ====================
    async exportExcel() {
      if (!this.allData.length) return
      try {
        const XLSX = await import('xlsx')
        const wb = XLSX.utils.book_new()
        this.allData.forEach(fileData => {
          const rows = fileData.frequencies.map((freq, idx) => ({
            '频率 (cm⁻¹)': freq,
            '黄里斯因子': fileData.huang_rhys[idx] !== undefined ? fileData.huang_rhys[idx] : 0,
            '分解重组能 (eV)': fileData.reorg_contrib[idx] !== undefined ? fileData.reorg_contrib[idx] : 0
          }))
          const computed = (fileData.reorg_contrib || []).reduce((a, b) => a + b, 0)
          rows.push({ '频率 (cm⁻¹)': '原始总重组能', '黄里斯因子': '', '分解重组能 (eV)': fileData.reorg_total })
          rows.push({ '频率 (cm⁻¹)': '计算总重组能', '黄里斯因子': '', '分解重组能 (eV)': computed })
          let sheetName = String(fileData.filename || '').replace(/\.out$/i, '').replace(/[\[\]:*?/\\]/g, '_')
          if (sheetName.length > 31) sheetName = sheetName.substring(0, 31)
          const existing = wb.SheetNames
          let finalName = sheetName
          let counter = 1
          while (existing.includes(finalName)) {
            finalName = `${sheetName}_${counter++}`
            if (finalName.length > 31) finalName = finalName.substring(0, 31)
          }
          XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), finalName)
        })
        XLSX.writeFile(wb, 'reorganization_energy.xlsx')
        this.addLog('Excel 导出成功', '#7cfc00')
      } catch (e) {
        this.addLog('导出 Excel 失败', '#ffa500')
        console.error(e)
      }
    }
  }
}
</script>

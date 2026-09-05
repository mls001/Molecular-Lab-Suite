<template>
  <!-- PyCharm 风格三栏：左=文件列表 / 中=激发态信息 / 右=解析设置 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- ===== 左：文件列表 ===== -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>文件列表</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ allData.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!allData.length" class="ide-empty">暂无文件<br>请先在右侧选择文件夹并解析</div>
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

      <!-- ===== 中：激发态信息 ===== -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>TD 激发态</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">
            {{ allData.length && allData[selectedIndex] ? allData[selectedIndex].filename : '—' }}
          </span>
        </div>
        <div class="flex-col flex-1 min-h-0" style="overflow:hidden;padding:8px 12px 0;">
          <div style="flex-shrink-0;font-size:13px;color:var(--c-text-2);margin-bottom:6px;">
            <span v-if="currentStates.length">共 {{ currentStates.length }} 个激发态</span>
          </div>
          <div ref="tableContainer" style="flex:1;overflow:auto;padding:0 0 12px 0;">
            <table v-if="currentStates.length" style="width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;">
              <colgroup>
                <col style="width:8%;" />
                <col style="width:10%;" />
                <col style="width:14%;" />
                <col style="width:14%;" />
                <col style="width:14%;" />
                <col style="width:40%;" />
              </colgroup>
              <thead style="position:sticky;top:0;background:var(--c-panel);z-index:10;">
                <tr>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">序号</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">多重度</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">能量 (eV)</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">波长 (nm)</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">振子强度</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:left;">主要跃迁</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(state, idx) in displayStates" :key="idx">
                  <td style="padding:5px 8px;border-bottom:1px solid var(--c-hover);text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">
                    <span
                      v-if="state.tagKind === 'S'"
                      style="display:inline-block;padding:1px 7px;border-radius:9px;font-weight:600;background:var(--c-lumo-row);color:var(--c-lumo);"
                    >{{ state.tag }}</span>
                    <span
                      v-else-if="state.tagKind === 'T'"
                      style="display:inline-block;padding:1px 7px;border-radius:9px;font-weight:600;background:var(--c-homo-row);color:var(--c-homo);"
                    >{{ state.tag }}</span>
                    <span v-else>{{ state.tag }}</span>
                  </td>
                  <td style="padding:5px 8px;border-bottom:1px solid var(--c-hover);text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;"
                    :style="state.tagKind === 'S' ? 'color:var(--c-lumo);' : state.tagKind === 'T' ? 'color:var(--c-homo);' : ''">{{ state.mult_type }}</td>
                  <td style="padding:5px 8px;border-bottom:1px solid var(--c-hover);text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">{{ state.energy_eV.toFixed(4) }}</td>
                  <td style="padding:5px 8px;border-bottom:1px solid var(--c-hover);text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">{{ state.wavelength_nm.toFixed(2) }}</td>
                  <td style="padding:5px 8px;border-bottom:1px solid var(--c-hover);text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">{{ state.osc_strength.toFixed(6) }}</td>
                  <td style="padding:5px 8px;border-bottom:1px solid var(--c-hover);height:2.6em;vertical-align:middle;text-align:left;">
                    <div style="height:100%;overflow-y:auto;word-break:break-word;line-height:1.3em;">
                      <span v-for="(t, i) in getMajorTransitions(state)" :key="i">
                        {{ t }}<span v-if="i < getMajorTransitions(state).length - 1">; </span>
                      </span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--c-text-3);font-size:14px;">
              请选择文件夹并解析
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 右：解析设置 ===== -->
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>解析设置</span></div>
        <div class="ide-pane-body">
          <div class="ide-group">
            <div class="flex-center" style="gap:6px;justify-content:space-between;">
              <span class="label" style="font-weight:400;">数据来源</span>
              <div class="flex-center" style="gap:6px;">
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'local' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'local'">本地</button>
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'remote' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'remote'" :disabled="!connected">远程</button>
              </div>
            </div>
            <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;">
              {{ parseMode === 'remote' ? (remoteFolder || '未选择远程目录（含 .log）') : (folder || '未选择本地文件夹') }}
            </div>
            <button class="btn" @click="chooseParseSource">选择{{ parseMode === 'remote' ? '远程目录' : '文件夹' }}</button>
            <button class="btn btn-primary" @click="runParse" :disabled="running || !(parseMode === 'remote' ? remoteFolder : folder)">
              {{ running ? '解析中...' : '解析 / 重新解析' }}
            </button>
            <div class="flex" style="gap:6px;">
              <button v-if="allData.length" class="btn" style="flex:1;" @click="exportCSV">导出 CSV</button>
              <button v-if="allData.length" class="btn" style="flex:1;background:#722ed1;color:#fff;border-color:#722ed1;" @click="exportExcel">导出 Excel</button>
            </div>
          </div>
          <div v-if="displayStates.length" class="ide-group">
            <span class="label">激发态能级图</span>
            <canvas
              ref="levelCanvas"
              class="level-canvas"
              @click="openLevelPopup"
              title="点击放大查看"
              style="width:100%;background:#ffffff;border:1px solid var(--c-border);border-radius:4px;cursor:pointer;"
            ></canvas>
            <div style="font-size:11px;color:var(--c-text-3);line-height:1.6;">蓝线 = 三线态 (T)，红线 = 单线态 (S)，能量单位为 eV。点击图像可在新窗口查看大图。</div>
          </div>
          <div class="ide-group" style="color:var(--c-text-3);font-size:12px;line-height:1.6;">
            <span>提示：TD 激发态信息提取自 Gaussian log 的最后一段 “Excited State” 输出，包括激发能、波长、振子强度与主要轨道跃迁。</span>
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

    <!-- 日志区域 -->
    <LogViewer :lines="logLines" />
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'
import RemoteFileBrowser from '../components/RemoteFileBrowser.vue'
import scrollCache from '@/mixins/scrollCache'
import { pickDirectory } from '@/api/dialog'
import { syncRemoteFolder } from '@/api/remoteSync'
import { useRemoteStore } from '@/stores/remote'
import { storeToRefs } from 'pinia'

export default {
  name: 'TdView',
  components: { LogViewer, RemoteFileBrowser },
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
      levelBigUrl: '',
      _pageActive: true,
    }
  },
  computed: {
    currentStates() {
      if (this.allData.length && this.selectedIndex < this.allData.length) {
        return this.allData[this.selectedIndex].states || []
      }
      return []
    },
    // 为每个态标注 S# / T#（singlet / triplet），便于区分与检索
    displayStates() {
      const counters = { S: 0, T: 0, X: 0 }
      return (this.currentStates || []).map((state) => {
        const typeStr = String(state.mult_type || '')
        let kind = 'X'
        if (/singlet/i.test(typeStr)) kind = 'S'
        else if (/triplet/i.test(typeStr)) kind = 'T'
        counters[kind] += 1
        return {
          ...state,
          tag: kind === 'X' ? String(state.state_num) : `${kind}${counters[kind]}`,
          tagKind: kind
        }
      })
    }
  },
  watch: {
    displayStates() {
      // 解析结果/切换文件后自动重绘能级图
      this.$nextTick(() => this.renderLevels())
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
    // 离开页面时停止后台解析，避免消息更新已隐藏/销毁的组件引发空引用
    this._pageActive = false
    if (this.ws) {
      try { this.ws.close() } catch (e) { /* ignore */ }
      this.ws = null
    }
    this.running = false
  },
  activated() {
    this._pageActive = true
    this.$nextTick(() => this.renderLevels())
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 200) this.logLines.shift()
    },

    getMajorTransitions(state, threshold = 5) {
      const items = state.transitions
        .filter(t => t.percent > threshold)
        .sort((a, b) => b.percent - a.percent)
        .map(t => `${t.from}→${t.to} (${t.percent.toFixed(1)}%)`)
      return items.length ? items : ['无显著贡献']
    },

    // ===== 激发态能级图（单线态红、三线态蓝；点击弹窗放大查看大图） =====
    renderLevels() {
      const cv = this.$refs.levelCanvas
      if (!cv) return
      const states = this.displayStates || []
      const dpr = window.devicePixelRatio || 1
      // 竖向 9:16 比例：高度随宽度自适应
      const cssW = Math.max(200, cv.clientWidth || 240)
      const cssH = Math.round(cssW * 16 / 9)
      cv.style.height = cssH + 'px'
      cv.width = Math.round(cssW * dpr)
      cv.height = Math.round(cssH * dpr)
      const ctx = cv.getContext('2d')
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      this.drawLevelDiagram(ctx, cssW, cssH, states)
      // 生成用于弹窗的高分辨率竖向大图（同样 9:16）
      const big = document.createElement('canvas')
      big.width = 900
      big.height = 1600
      this.drawLevelDiagram(big.getContext('2d'), 900, 1600, states)
      this.levelBigUrl = states.length ? big.toDataURL('image/png') : ''
    },

        drawLevelDiagram(ctx, W, H, states) {
      ctx.clearRect(0, 0, W, H)
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, W, H)
      if (!states.length) return

      const COLOR_SINGLET = '#b3483c' // singlet: red (low saturation)
      const COLOR_TRIPLET = '#2f6fae' // triplet: blue (low saturation)
      const COLOR_OTHER = '#5a5a5a'
      const s = Math.sqrt(W / 272)

      const items = states
        .map(function (st) { return { tag: st.tag, kind: st.tagKind, e: Number(st.energy_eV) || 0 } })
        .filter(function (x) { return isFinite(x.e) })
        .sort(function (a, b) { return a.e - b.e })
      if (!items.length) return

      const eMin = Math.max(0, items[0].e - 0.4)
      const eMax = items[items.length - 1].e + 0.4
      const pad = (eMax - eMin) * 0.08
      const vMin = Math.max(0, eMin - pad)
      const vMax = eMax + pad

      // tall portrait plot; split area: left half center = singlet, right half center = triplet
      const plotL = Math.max(46, W * 0.11)
      const plotR = W - 6
      const plotT = 14
      const plotB = H - 14
      const plotW = plotR - plotL

      const yOf = function (e) { return plotB - ((e - vMin) / (vMax - vMin)) * (plotB - plotT) }

      const niceStep = function (range, n) {
        const raw = range / n
        const mag = Math.pow(10, Math.floor(Math.log10(raw)))
        const norm = raw / mag
        const step = norm >= 5 ? 5 : norm >= 2 ? 2 : 1
        return step * mag
      }
      const step = Math.max(0.01, niceStep(vMax - vMin, 8))
      const first = Math.ceil(vMin / step) * step

      ctx.strokeStyle = '#111111'
      ctx.lineWidth = Math.max(1, s * 0.8)
      ctx.strokeRect(plotL, plotT, plotW, plotB - plotT)
      ctx.fillStyle = '#111111'
      ctx.font = Math.round(10 * s) + 'px Segoe UI, sans-serif'
      ctx.textAlign = 'right'
      ctx.textBaseline = 'middle'
      for (let v = first; v <= vMax + 1e-9; v += step) {
        const y = yOf(Math.min(v, vMax))
        if (y < plotT - 2 || y > plotB + 2) continue
        ctx.beginPath()
        ctx.moveTo(plotL - 4 * s, y)
        ctx.lineTo(plotL, y)
        ctx.stroke()
        ctx.fillText(v.toFixed(2), plotL - 7 * s, y)
      }

      const segHalf = Math.min(40, plotW * 0.17)
      const singX = plotL + plotW * 0.24
      const tripX = plotL + plotW * 0.76
      const midX = plotL + plotW * 0.5

      const lineH = Math.max(1.6, 3 * s)
      const textH = Math.round(15 * s)
      const fs = Math.round(12 * s)
      const boxes = []
      items.forEach(function (item) {
        const y = yOf(item.e)
        const isS = item.kind === 'S'
        const isT = item.kind === 'T'
        const color = isT ? COLOR_TRIPLET : isS ? COLOR_SINGLET : COLOR_OTHER

        let cx = midX
        if (isS) cx = singX
        else if (isT) cx = tripX

        ctx.strokeStyle = color
        ctx.lineWidth = lineH
        ctx.beginPath()
        ctx.moveTo(cx - segHalf, y)
        ctx.lineTo(cx + segHalf, y)
        ctx.stroke()

        const label = item.tag + ' ' + item.e.toFixed(2)
        ctx.font = '600 ' + fs + 'px Segoe UI, sans-serif'
        const labelW = ctx.measureText(label).width
        // 2D 包围盒避让：优先在线段右侧贴线 → 左侧 → 逐步小幅上下让位，保证不互相遮挡
        const anchors = [
          { sx: 1, x0: cx + segHalf + 6 * s },
          { sx: -1, x0: cx - segHalf - 6 * s }
        ]
        let placedAny = false
        for (let ai = 0; ai < anchors.length && !placedAny; ai++) {
          const anc = anchors[ai]
          const x0 = anc.sx > 0 ? anc.x0 : anc.x0 - labelW
          for (let off = 0; off <= 14 && !placedAny; off++) {
            for (let dir = 0; dir < 2 && !placedAny; dir++) {
              const dy = off === 0 ? 0 : (dir === 0 ? -off * textH : off * textH)
              const yy = y + dy
              const top = yy - textH / 2
              const bot = yy + textH / 2
              let collide = false
              for (let bi = 0; bi < boxes.length; bi++) {
                const b = boxes[bi]
                if (!(bot < b.top || top > b.bot || x0 > b.x1 || (x0 + labelW) < b.x0)) {
                  collide = true
                  break
                }
              }
              if (!collide) {
                boxes.push({ x0: x0, x1: x0 + labelW, top: top, bot: bot })
                ctx.fillStyle = color
                ctx.textAlign = anc.sx > 0 ? 'left' : 'right'
                ctx.textBaseline = 'middle'
                ctx.fillText(label, anc.x0, yy)
                placedAny = true
              }
            }
          }
        }
        if (!placedAny) {
          ctx.fillStyle = color
          ctx.textAlign = 'left'
          ctx.textBaseline = 'middle'
          ctx.fillText(label, cx + segHalf + 6 * s, y)
        }
      })
    },

    openLevelPopup() {
      if (!this.levelBigUrl) return
      const win = window.open('', '_blank', 'width=1100,height=1900')
      if (win) {
        win.document.write(
          '<html><head><title>激发态能级图</title></head>' +
          '<body style="margin:0;background:#ffffff;">' +
          `<img src="${this.levelBigUrl}" style="width:100%;height:auto;" />` +
          '</body></html>'
        )
        win.document.close()
      } else {
        alert('无法打开新窗口，请允许弹出窗口后再试')
      }
    },

    async chooseParseSource() {
      if (this.parseMode === 'remote') {
        if (!this.connected) {
          this.addLog('请先连接服务器', '#ffa500')
          return
        }
        this.browserTarget = 'logFolder'
        this.browserInitialPath = `/home/${this.username}` || '/'
        this.browserVisible = true
        return
      }
      let path
      try {
        path = await pickDirectory('选择包含 Gaussian .log 文件的文件夹')
      } catch (e) {
        this.addLog(`选择目录失败: ${e.message}`, '#ff6b6b')
        return
      }
      if (!path) return
      this.folder = path
      this.addLog(`本地目录: ${path}`, '#87d2ff')
    },

    async runParse() {
      if (this.running) return
      if (this.parseMode === 'local') {
        if (!this.folder) {
          this.addLog('请先选择本地文件夹', '#ffa500')
          return
        }
        this.startParse()
        return
      }
      if (!this.remoteFolder) {
        this.addLog('请先选择远程目录', '#ffa500')
        return
      }
      if (!this.connected) {
        this.addLog('请先连接服务器', '#ffa500')
        return
      }
      this.running = true
      this.addLog(`远程目录: ${this.remoteFolder}`, '#87d2ff')
      try {
        const { cacheDir, count } = await syncRemoteFolder(this.sessionId, this.remoteFolder, '.log')
        this.addLog(`已同步 ${count} 个 .log → ${cacheDir}`, '#87d2ff')
        if (!this._pageActive) {
          this.running = false
          return
        }
        this.folder = cacheDir
        this.running = false
        this.startParse()
      } catch (e) {
        this.addLog(`远程解析失败: ${e.message}`, '#ff6b6b')
        this.running = false
      }
    },

    onBrowserSelect({ target, path, is_dir }) {
      if (target === 'logFolder') {
        this.remoteFolder = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
        this.addLog(`远程目录: ${this.remoteFolder}`, '#87d2ff')
      }
    },

    async selectFolder() {
      let path
      try {
        path = await pickDirectory('选择包含 .log 文件的文件夹')
      } catch (e) {
        this.addLog(`选择目录失败: ${e.message}`, '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.folder = path
      this.addLog(` 选择目录: ${path}`, '#87d2ff')
      this.allData = []
      this.selectedIndex = 0
      this.startParse()
    },

    startParse() {
      if (this.running || !this.folder) return
      this.running = true
      this.logLines.splice(0)
      this.logKey++
      this.allData = []
      this.selectedIndex = 0
      this.addLog('开始解析 TD 信息...', '#00ff00')

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/td`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog('WebSocket 已连接', '#87d2ff')
        this.ws.send(JSON.stringify({ action: 'parse_td', folder: this.folder }))
      }

      this.ws.onmessage = (e) => {
        if (!this._pageActive || !this.ws) return
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog(`${data.filename} 解析成功 [${data.index}/${data.total}]`, '#7cfc00')
            } else {
              this.addLog(` ${data.filename} 解析失败: ${data.message}`, '#ff6b6b')
            }
            break
          case 'result':
            this.allData = data.data
            if (this.allData.length) {
              this.selectedIndex = 0
              this.addLog(`共解析 ${this.allData.length} 个文件`, '#87d2ff')
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
        this.addLog(' WebSocket 错误', '#ff6b6b')
        this.running = false
      }
      this.ws.onclose = () => {
        this.running = false
      }
    },

    selectFile(idx) {
      if (idx >= 0 && idx < this.allData.length) {
        this.selectedIndex = idx
      }
    },

    exportCSV() {
      if (!this.allData.length) return
      const headers = ['文件', '激发态序号', '多重度', '能量(eV)', '波长(nm)', '振子强度', '主要跃迁']
      const rows = []
      this.allData.forEach(fileData => {
        const filename = fileData.filename
        fileData.states.forEach(state => {
          const major = this.getMajorTransitions(state).join('; ')
          rows.push([
            filename,
            state.state_num,
            state.mult_type,
            state.energy_eV.toFixed(4),
            state.wavelength_nm.toFixed(2),
            state.osc_strength.toFixed(6),
            major
          ])
        })
      })
      const content = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
      const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = 'td_data.csv'
      link.click()
    },

    async exportExcel() {
      if (!this.allData.length) return
      try {
        const XLSX = await import('xlsx')
        const wb = XLSX.utils.book_new()
        this.allData.forEach(fileData => {
          const filename = fileData.filename
          const rows = fileData.states.map(state => ({
            '激发态序号': state.state_num,
            '多重度': state.mult_type,
            '能量(eV)': state.energy_eV.toFixed(4),
            '波长(nm)': state.wavelength_nm.toFixed(2),
            '振子强度': state.osc_strength.toFixed(6),
            '主要跃迁': this.getMajorTransitions(state).join('; ')
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
        XLSX.writeFile(wb, 'td_data.xlsx')
        this.addLog('Excel 导出成功', '#7cfc00')
      } catch (e) {
        this.addLog('导出 Excel 需要 xlsx 库，请安装: npm install xlsx', '#ffa500')
        console.error(e)
      }
    }
  }
}
</script>
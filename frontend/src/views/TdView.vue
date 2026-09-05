<template>
  <!-- PyCharm 风格三栏：左=文件列表 / 中=激发态信息 / 右=解析设置 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <!-- ===== 左：文件列表 ===== -->
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head">
          <span>{{ $t('文件列表') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">{{ allData.length }} 个</span>
        </div>
        <div class="ide-pane-body" style="padding:6px 0;">
          <div v-if="!allData.length" class="ide-empty">{{ $t('暂无文件') }}<br>{{ $t('请先在右侧选择文件夹并解析') }}</div>
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
          <span>{{ $t('TD 激发态') }}</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">
            {{ allData.length && allData[selectedIndex] ? allData[selectedIndex].filename : '—' }}
          </span>
        </div>
        <div class="flex-col flex-1 min-h-0" style="overflow:hidden;padding:8px 12px 0;">
          <div style="flex-shrink-0;font-size:13px;color:var(--c-text-2);margin-bottom:6px;">
            <span v-if="currentStates.length">{{ $t('共 {n} 个激发态', { n: currentStates.length }) }}</span>
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
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('序号') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('多重度') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('能量 (eV)') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('波长 (nm)') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">{{ $t('振子强度') }}</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:left;">{{ $t('主要跃迁') }}</th>
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
            <EmptyNotice
              v-else-if="parsedOnce"
              :text="$t('该文件内不含 TD 激发态信息')"
              :hint="noticeHint"
            />
            <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--c-text-3);font-size:14px;">
              {{ $t('请选择文件夹并解析') }}
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 右：解析设置 ===== -->
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>{{ $t('解析设置') }}</span></div>
        <div class="ide-pane-body">
          <div class="ide-group">
            <div class="flex-center" style="gap:6px;justify-content:space-between;">
              <span class="label" style="font-weight:400;">{{ $t('数据来源') }}</span>
              <div class="flex-center" style="gap:6px;">
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'local' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'local'">{{ $t('本地') }}</button>
                <button class="btn" style="height:24px;font-size:12px;padding:0 10px;" :class="parseMode === 'remote' ? 'btn-primary' : 'btn-default'" @click="parseMode = 'remote'" :disabled="!connected">{{ $t('远程') }}</button>
              </div>
            </div>
            <div style="font-size:12px;color:var(--c-text-2);word-break:break-all;">
              {{ parseMode === 'remote' ? (remoteFolder || $t('未选择远程目录（含 .log）')) : (folder || $t('未选择本地文件夹')) }}
            </div>
            <button class="btn" @click="chooseParseSource">{{ parseMode === 'remote' ? $t('选择远程目录') : $t('选择文件夹') }}</button>
            <button class="btn btn-primary" @click="runParse" :disabled="running || !(parseMode === 'remote' ? remoteFolder : folder)">
              {{ running ? $t('解析中...') : $t('解析 / 重新解析') }}
            </button>
            <div class="flex" style="gap:6px;">
              <button v-if="allData.length" class="btn" style="flex:1;" @click="exportCSV">{{ $t('导出 CSV') }}</button>
              <button v-if="allData.length" class="btn" style="flex:1;" @click="exportExcel">{{ $t('导出 Excel') }}</button>
            </div>
          </div>
          <div v-if="displayStates.length" class="ide-group">
            <span class="label">{{ $t('激发态能级图') }}</span>
            <canvas
              ref="levelCanvas"
              class="level-canvas"
              @click="openLevelPopup"
              :title="$t('点击放大查看')"
              style="width:100%;background:#ffffff;border:1px solid var(--c-border-strong);cursor:pointer;"
            ></canvas>
          </div>

          <!-- 自选能级图层：不添加即绘制全部激发态 -->
          <div v-if="displayStates.length" class="ide-group">
            <div class="flex-center" style="justify-content:space-between;">
              <span class="label">{{ $t('自定义能级图层') }}</span>
              <button class="btn" style="height:22px;font-size:11px;padding:0 8px;" @click="addLayer">{{ $t('＋ 添加图层') }}</button>
            </div>
            <div class="soc-grid" style="grid-template-columns:1fr 14px 1fr 18px;">
              <span style="font-weight:700;color:var(--c-lumo);">{{ $t('S(单线态)') }}</span>
              <span></span>
              <span style="font-weight:700;color:var(--c-homo);">{{ $t('T(三线态)') }}</span>
              <span></span>
            </div>
            <div v-for="(ly, idx) in tdLayers" :key="idx" class="flex-center" style="gap:3px;">
              <select v-model="ly.s" class="control" style="flex:1;min-width:0;height:22px;font-size:11px;" @change="renderLevels">
                <option v-for="o in sOptions" :key="o" :value="o">{{ o }}</option>
              </select>
              <span style="color:var(--c-text-3);font-size:11px;">→</span>
              <select v-model="ly.t" class="control" style="flex:1;min-width:0;height:22px;font-size:11px;" @change="renderLevels">
                <option v-for="o in tOptions" :key="o" :value="o">{{ o }}</option>
              </select>
              <button class="chip-x" @click="removeLayer(idx)">×</button>
            </div>
            <div v-if="!tdLayers.length" style="font-size:11px;color:var(--c-text-3);">{{ $t('（无图层，点“＋ 添加图层”开始）') }}</div>
            <button v-if="tdLayers.length" class="btn" style="height:22px;font-size:11px;" @click="clearLayers">{{ $t('清空全部') }}</button>
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
import { t as $tr } from '@/i18n'
import EmptyNotice from '@/components/EmptyNotice.vue'
import { PALETTE, drawAxes, drawLevel, drawEnergyLabel, font, crisp } from '@/utils/naturePlot'


export default {
  name: 'TdView',
  components: { LogViewer, RemoteFileBrowser, EmptyNotice },
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
      parsedOnce: false,     // 已跑过一次解析 → 空数据显示"该文件内不含…"
      noticeHint: '',        // 解析失败原因
      logLines: [],
      logKey: 0,
      ws: null,
      allData: [],
      selectedIndex: 0,
      levelBigUrl: '',
      tdLayers: [],        // [{ s: 'S1', t: 'T2' }]，为空 = 绘制全部激发态
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
    },
    stateByTag() {
      const map = {}
      this.displayStates.forEach(st => { map[st.tag] = st })
      return map
    },
    sOptions() {
      return this.displayStates.filter(st => st.tagKind === 'S').map(st => st.tag)
    },
    tOptions() {
      return this.displayStates.filter(st => st.tagKind === 'T').map(st => st.tag)
    },
    // 有图层 → 只画被引用的能级；无图层 → 画全部
    plottedStates() {
      if (!this.tdLayers.length) return this.displayStates
      const seen = {}
      const out = []
      this.tdLayers.forEach(ly => {
        ;[ly.s, ly.t].forEach(tag => {
          if (tag && !seen[tag] && this.stateByTag[tag]) {
            seen[tag] = true
            out.push(this.stateByTag[tag])
          }
        })
      })
      return out.length ? out : this.displayStates
    }
  },
  watch: {
    displayStates() {
      // 换文件/重新解析后：清掉在新数据里不存在的图层，并重绘图
      const valid = (tag) => !!this.stateByTag[tag]
      this.tdLayers = this.tdLayers.filter(ly => valid(ly.s) && valid(ly.t))
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
      return items.length ? items : [$tr('无显著贡献')]
    },

    // ===== 激发态能级图（S 红 / T 蓝；Nature 风格：发丝轴 + 浅网格 + 克制配色）=====
    renderLevels() {
      const cv = this.$refs.levelCanvas
      if (!cv) return
      const states = this.plottedStates || []
      const dpr = window.devicePixelRatio || 1
      const cssW = Math.max(200, cv.clientWidth || 240)
      const cssH = Math.round(cssW * 16 / 9)
      cv.style.height = cssH + 'px'
      cv.width = Math.round(cssW * dpr)
      cv.height = Math.round(cssH * dpr)
      const ctx = cv.getContext('2d')
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      this.drawLevelDiagram(ctx, cssW, cssH, states)
      // 高分辨率竖向大图（点击弹窗查看）
      const big = document.createElement('canvas')
      big.width = 1200
      big.height = 2100
      this.drawLevelDiagram(big.getContext('2d'), 1200, 2100, states)
      this.levelBigUrl = states.length ? big.toDataURL('image/png') : ''
    },

    drawLevelDiagram(ctx, W, H, states) {
      ctx.clearRect(0, 0, W, H)
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, W, H)
      const items = (states || [])
        .map(st => ({ tag: st.tag, kind: st.tagKind, e: Number(st.energy_eV) || 0 }))
        .filter(x => isFinite(x.e))
        .sort((a, b) => a.e - b.e)
      if (!items.length) return

      const sf = Math.sqrt(W / 272)
      const es = items.map(i => i.e)
      const eMin = Math.max(0, Math.min.apply(null, es) - 0.4)
      const eMax = Math.max.apply(null, es) + 0.4
      const L = Math.max(50 * sf, W * 0.15)
      const R = W - 16 * sf
      const T = 22 * sf
      const B = H - 22 * sf
      const yOf = drawAxes(ctx, { L, T, R, B, min: eMin, max: eMax, sf, title: 'Energy (eV)' })

      const cxS = L + (R - L) * 0.30
      const cxT = L + (R - L) * 0.72
      const half = Math.min(30 * sf, (R - L) * 0.13)
      const lineH = Math.max(1.8, 2.4 * sf)
      const fs = 11 * sf
      const textH = 15 * sf
      const boxes = []

      items.forEach(item => {
        const y = yOf(item.e)
        const isT = item.kind === 'T'
        const color = isT ? PALETTE.triplet : item.kind === 'S' ? PALETTE.singlet : PALETTE.other
        const cx = isT ? cxT : item.kind === 'S' ? cxS : (cxS + cxT) / 2

        drawLevel(ctx, { cx, y, half, color, sf, width: lineH })

        const label = `${item.tag}  ${item.e.toFixed(2)}`
        ctx.font = font(fs, '500')
        const labelW = ctx.measureText(label).width
        const anchors = [
          { sx: 1, x0: cx + half + 5 * sf },
          { sx: -1, x0: cx - half - 5 * sf }
        ]
        let placedAny = false
        for (let ai = 0; ai < anchors.length && !placedAny; ai++) {
          const anc = anchors[ai]
          const x0 = anc.sx > 0 ? anc.x0 : anc.x0 - labelW
          for (let off = 0; off <= 16 && !placedAny; off++) {
            for (let dir = 0; dir < 2 && !placedAny; dir++) {
              const dy = off === 0 ? 0 : (dir === 0 ? -off * textH : off * textH)
              const yy = y + dy
              const top = yy - textH / 2
              const bot = yy + textH / 2
              let collide = false
              for (let bi = 0; bi < boxes.length; bi++) {
                const b = boxes[bi]
                if (!(bot < b.top || top > b.bot || x0 > b.x1 || (x0 + labelW) < b.x0)) { collide = true; break }
              }
              if (!collide) {
                boxes.push({ x0, x1: x0 + labelW, top, bot })
                drawEnergyLabel(ctx, { x: anc.x0, y: yy, text: label, color, align: anc.sx > 0 ? 'left' : 'right', sf })
                placedAny = true
              }
            }
          }
        }
        if (!placedAny) {
          drawEnergyLabel(ctx, { x: cx + half + 5 * sf, y, text: label, color, align: 'left', sf })
        }
      })
    },

    // ===== 自选能级图层 =====
    addLayer() {
      const sList = this.sOptions
      const tList = this.tOptions
      if (!sList.length || !tList.length) return
      const usedS = new Set(this.tdLayers.map(l => l.s))
      const usedT = new Set(this.tdLayers.map(l => l.t))
      const s = sList.find(x => !usedS.has(x)) || sList[0]
      const t = tList.find(x => !usedT.has(x)) || tList[0]
      this.tdLayers.push({ s, t })
      this.renderLevels()
    },
    removeLayer(idx) {
      this.tdLayers.splice(idx, 1)
      this.renderLevels()
    },
    clearLayers() {
      this.tdLayers = []
      this.renderLevels()
    },

    openLevelPopup() {
      if (!this.levelBigUrl) return
      const win = window.open('', '_blank', 'width=1100,height=1900')
      if (win) {
        win.document.write(
          $tr('<html><head><title>激发态能级图</title></head>') +
          '<body style="margin:0;background:#ffffff;">' +
          `<img src="${this.levelBigUrl}" style="width:100%;height:auto;" />` +
          '</body></html>'
        )
        win.document.close()
      } else {
        alert($tr('无法打开新窗口，请允许弹出窗口后再试'))
      }
    },

    async chooseParseSource() {
      if (this.parseMode === 'remote') {
        if (!this.connected) {
          this.addLog($tr('请先连接服务器'), '#ffa500')
          return
        }
        this.browserTarget = 'logFolder'
        this.browserInitialPath = `/home/${this.username}` || '/'
        this.browserVisible = true
        return
      }
      let path
      try {
        path = await pickDirectory($tr('选择包含 Gaussian .log 文件的文件夹'))
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return
      this.folder = path
      this.addLog($tr('本地目录: {0}', { 0: path }), '#87d2ff')
    },

    async runParse() {
      if (this.running) return
      if (this.parseMode === 'local') {
        if (!this.folder) {
          this.addLog($tr('请先选择本地文件夹'), '#ffa500')
          return
        }
        this.startParse()
        return
      }
      if (!this.remoteFolder) {
        this.addLog($tr('请先选择远程目录'), '#ffa500')
        return
      }
      if (!this.connected) {
        this.addLog($tr('请先连接服务器'), '#ffa500')
        return
      }
      this.running = true
      this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      try {
        const { cacheDir, count } = await syncRemoteFolder(this.sessionId, this.remoteFolder, '.log')
        this.addLog($tr('已同步 {0} 个 .log → {1}', { 0: count, 1: cacheDir }), '#87d2ff')
        if (!this._pageActive) {
          this.running = false
          return
        }
        this.folder = cacheDir
        this.running = false
        this.startParse()
      } catch (e) {
        this.addLog($tr('远程解析失败: {0}', { 0: e.message }), '#ff6b6b')
        this.running = false
      }
    },

    onBrowserSelect({ target, path, is_dir }) {
      if (target === 'logFolder') {
        this.remoteFolder = is_dir ? path : path.substring(0, path.lastIndexOf('/'))
        this.addLog($tr('远程目录: {0}', { 0: this.remoteFolder }), '#87d2ff')
      }
    },

    async selectFolder() {
      let path
      try {
        path = await pickDirectory($tr('选择包含 .log 文件的文件夹'))
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.folder = path
      this.addLog($tr(' 选择目录: {0}', { 0: path }), '#87d2ff')
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
      this.addLog($tr('开始解析 TD 信息...'), '#00ff00')

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/td`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog($tr('WebSocket 已连接'), '#87d2ff')
        this.ws.send(JSON.stringify({ action: 'parse_td', folder: this.folder }))
      }

      this.ws.onmessage = (e) => {
        if (!this._pageActive || !this.ws) return
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog($tr('{0} 解析成功 [{1}/{2}]', { 0: data.filename, 1: data.index, 2: data.total }), '#7cfc00')
            } else {
              this.noticeHint = data.message || ''
              this.addLog($tr(' {0} 解析失败: {1}', { 0: data.filename, 1: data.message }), '#ff6b6b')
            }
            break
          case 'result':
            this.parsedOnce = true
            this.allData = data.data
            if (this.allData.length) {
              this.selectedIndex = 0
              this.addLog($tr('共解析 {0} 个文件', { 0: this.allData.length }), '#87d2ff')
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
        this.addLog($tr(' WebSocket 错误'), '#ff6b6b')
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
      const headers = [$tr('文件'), $tr('激发态序号'), $tr('多重度'), $tr('能量(eV)'), $tr('波长(nm)'), $tr('振子强度'), $tr('主要跃迁')]
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
        this.addLog($tr('Excel 导出成功'), '#7cfc00')
      } catch (e) {
        this.addLog($tr('导出 Excel 需要 xlsx 库，请安装: npm install xlsx'), '#ffa500')
        console.error(e)
      }
    }
  }
}
</script>
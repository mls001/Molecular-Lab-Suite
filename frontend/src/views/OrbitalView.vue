<template>
  <!-- PyCharm 风格三栏：左=文件列表 / 中=轨道能级表 / 右=解析设置与能隙计算 -->
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

      <!-- ===== 中：轨道能级表 ===== -->
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head">
          <span>轨道能级</span>
          <span style="font-weight:400;font-size:12px;color:var(--c-text-3);">
            {{ allData.length && allData[selectedIndex] ? allData[selectedIndex].filename : '—' }}
          </span>
        </div>
        <div class="flex-col flex-1 min-h-0" style="overflow:hidden;padding:8px 12px 0;">
          <div style="flex-shrink:0;padding:0 0 6px 0;">
            <div v-if="currentTableData.length" style="font-size:13px;color:var(--c-text-2);">共 {{ currentTableData.length }} 条轨道</div>
          </div>
          <div ref="tableContainer" style="flex:1;overflow:auto;padding:0 0 12px 0;">
            <table v-if="currentTableData.length" style="width:100%;border-collapse:collapse;font-size:13px;">
              <thead style="position:sticky;top:0;background:var(--c-panel);z-index:10;">
                <tr>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:left;">自旋</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:left;">类型</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">轨道序号</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">能量 (Ha)</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">能量 (eV)</th>
                  <th style="padding:6px 10px;border-bottom:1px solid var(--c-border);text-align:center;">标记</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, rIdx) in currentTableData"
                  :key="rIdx"
                  :class="{ 'row-homo': row.isHOMO, 'row-lumo': row.isLUMO }"
                  :style="row.isHOMO ? 'background:var(--c-homo-row);' : row.isLUMO ? 'background:var(--c-lumo-row);' : ''"
                >
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);">{{ row.spin }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);">{{ row.type }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;">{{ row.index }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;">{{ row.energy_ha }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;">{{ row.energy_ev }}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--c-hover);text-align:center;font-weight:bold;">
                    <span v-if="row.isHOMO" style="color:var(--c-homo);">HOMO</span>
                    <span v-else-if="row.isLUMO" style="color:var(--c-lumo);">LUMO</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--c-text-3);font-size:14px;">
              请选择文件夹并等待解析完成
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 右：解析设置 + 能隙计算 ===== -->
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
          <div class="ide-group">
            <span class="label">能隙计算</span>
            <div class="flex-center" style="gap:6px;">
              <span style="font-size:12px;">A</span>
              <input v-model.number="gapIndexA" type="number" min="1" class="control" style="flex:1;min-width:0;height:28px;" placeholder="轨道 A 序号" />
              <span style="font-size:12px;">B</span>
              <input v-model.number="gapIndexB" type="number" min="1" class="control" style="flex:1;min-width:0;height:28px;" placeholder="轨道 B 序号" />
            </div>
            <button class="btn" @click="calcGap" :disabled="!currentTableData.length">计算能隙</button>
            <div v-if="gapResult" style="font-weight:600;font-size:14px;color:#1890ff;">{{ gapResult }}</div>
            <div v-if="gapError" style="color:var(--c-danger);font-size:13px;">{{ gapError }}</div>
          </div>
          <div class="ide-group" style="color:var(--c-text-3);font-size:12px;line-height:1.6;">
            <span>提示：解析完成会自动滚动到 HOMO / LUMO 行；HOMO/LUMO 已用颜色标记，可通过能隙计算估算带隙。</span>
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
  name: 'OrbitalView',
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
      currentTableData: [],
      rowRefs: [],
      gapIndexA: null,
      gapIndexB: null,
      gapResult: '',
      gapError: '',
      _pageActive: true,
      _scrollToken: 0,
    }
  },
  watch: {
    selectedIndex(val) {
      this.buildCurrentTable(val)
      this.autoScrollToHOMO()
      this.gapResult = ''
      this.gapError = ''
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
    // 离开页面（keep-alive 停用）时立即停止解析任务，避免后台消息更新已隐藏/销毁的组件
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
      if (this.logLines.length > 200) this.logLines.shift()
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
      // 本地：选择文件夹（不自动解析，避免与下方“解析”按钮重复）
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
      // 远程：同步 .log 到缓存后解析
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
      this.currentTableData = []
      this.selectedIndex = 0
      this.gapResult = ''
      this.gapError = ''
      this.startParse()
    },

    startParse() {
      if (this.running || !this.folder) return
      this.running = true
      this.logLines.splice(0)
      this.logKey++
      this.allData = []
      this.currentTableData = []
      this.selectedIndex = 0
      this.gapResult = ''
      this.gapError = ''
      this.addLog('开始解析轨道能量...', '#00ff00')

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/orbital`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog('', '#87d2ff')
        this.ws.send(JSON.stringify({ action: 'parse_orbital', folder: this.folder }))
      }

      this.ws.onmessage = (e) => {
        if (!this._pageActive || !this.ws) return
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog(` ${data.filename} 解析成功 [${data.index}/${data.total}]`, '#7cfc00')
            } else {
              this.addLog(` ${data.filename} 解析失败: ${data.message}`, '#ff6b6b')
            }
            break
          case 'result':
            this.allData = data.data
            if (this.allData.length) {
              this.selectedIndex = 0
              this.buildCurrentTable(0)
              this.autoScrollToHOMO(12)
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

    buildCurrentTable(idx) {
      if (!this.allData.length || idx >= this.allData.length) {
        this.currentTableData = []
        return
      }
      const fileData = this.allData[idx]
      const rows = []
      const filename = fileData.filename
      fileData.alpha_occ.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Alpha',
          type: 'Occ',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: idxNum === fileData.homo_alpha,
          isLUMO: false
        })
      })
      fileData.alpha_virt.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Alpha',
          type: 'Vir',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: false,
          isLUMO: idxNum === fileData.lumo_alpha
        })
      })
      fileData.beta_occ.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Beta',
          type: 'Occ',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: idxNum === fileData.homo_beta,
          isLUMO: false
        })
      })
      fileData.beta_virt.forEach(([idxNum, eng]) => {
        rows.push({
          file: filename,
          spin: 'Beta',
          type: 'Vir',
          index: idxNum,
          energy_ha: eng.toFixed(6),
          energy_ev: (eng * 27.211386).toFixed(4),
          isHOMO: false,
          isLUMO: idxNum === fileData.lumo_beta
        })
      })
      this.currentTableData = rows
      this.rowRefs = []
    },

    // 表格刚渲染时容器可能尚未测量完成，采用重试方式确保滚动到 HOMO/LUMO 行
    autoScrollToHOMO(attempts = 12) {
      const token = ++this._scrollToken
      this.$nextTick(() => {
        const step = () => {
          if (attempts <= 0 || !this._pageActive || token !== this._scrollToken) return
          attempts--
          this.scrollToHOMO_LUMO()
          setTimeout(step, 200)
        }
        step()
      })
    },

    scrollToHOMO_LUMO() {
      const container = this.$refs.tableContainer
      if (!container) return
      // 通过标记类定位 HOMO/LUMO 行（不依赖具体背景色，主题可自由换色）
      const target = container.querySelector('.row-homo, .row-lumo')
      if (target) {
        target.scrollIntoView({ block: 'center', behavior: 'smooth' })
        return
      }
      const rows = container.querySelectorAll('tr')
      if (rows.length) rows[0].scrollIntoView({ block: 'center', behavior: 'smooth' })
    },

    calcGap() {
      this.gapResult = ''
      this.gapError = ''
      if (!this.currentTableData.length) {
        this.gapError = '请先解析轨道数据'
        return
      }
      const a = this.gapIndexA
      const b = this.gapIndexB
      if (a === null || b === null || isNaN(a) || isNaN(b) || a < 1 || b < 1) {
        this.gapError = '请输入有效的轨道序号（正整数）'
        return
      }
      if (a === b) {
        this.gapError = '请选择两个不同的轨道序号'
        return
      }
      const findEnergy = (index) => {
        const row = this.currentTableData.find(r => r.index === index)
        return row ? parseFloat(row.energy_ha) : null
      }
      const engA = findEnergy(a)
      const engB = findEnergy(b)
      if (engA === null) {
        this.gapError = `未找到轨道序号 ${a}`
        return
      }
      if (engB === null) {
        this.gapError = `未找到轨道序号 ${b}`
        return
      }
      const deltaHa = Math.abs(engA - engB)
      const deltaEv = deltaHa * 27.211386
      this.gapResult = `ΔE = ${deltaEv.toFixed(4)} eV (${deltaHa.toFixed(6)} Ha)`
    },

    exportCSV() {
      if (!this.allData.length) return
      const headers = ['文件', '自旋', '类型', '轨道序号', '能量(Ha)', '能量(eV)', 'HOMO/LUMO']
      const rows = []
      this.allData.forEach(fileData => {
        const filename = fileData.filename
        const allTracks = [
          ...fileData.alpha_occ.map(([idx, eng]) => ({ file: filename, spin: 'Alpha', type: 'Occ', index: idx, eng, isHOMO: idx === fileData.homo_alpha, isLUMO: false })),
          ...fileData.alpha_virt.map(([idx, eng]) => ({ file: filename, spin: 'Alpha', type: 'Vir', index: idx, eng, isHOMO: false, isLUMO: idx === fileData.lumo_alpha })),
          ...fileData.beta_occ.map(([idx, eng]) => ({ file: filename, spin: 'Beta', type: 'Occ', index: idx, eng, isHOMO: idx === fileData.homo_beta, isLUMO: false })),
          ...fileData.beta_virt.map(([idx, eng]) => ({ file: filename, spin: 'Beta', type: 'Vir', index: idx, eng, isHOMO: false, isLUMO: idx === fileData.lumo_beta }))
        ]
        allTracks.forEach(t => {
          rows.push([
            t.file, t.spin, t.type, t.index,
            t.eng.toFixed(6),
            (t.eng * 27.211386).toFixed(4),
            t.isHOMO ? 'HOMO' : t.isLUMO ? 'LUMO' : ''
          ])
        })
      })
      const content = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
      const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = 'orbital_energies.csv'
      link.click()
    },

    async exportExcel() {
      if (!this.allData.length) return
      try {
        const XLSX = await import('xlsx')
        const wb = XLSX.utils.book_new()
        this.allData.forEach((fileData) => {
          const filename = fileData.filename
          const allTracks = [
            ...fileData.alpha_occ.map(([idxNum, eng]) => ({ spin: 'Alpha', type: 'Occ', index: idxNum, eng, homo: idxNum === fileData.homo_alpha, lumo: false })),
            ...fileData.alpha_virt.map(([idxNum, eng]) => ({ spin: 'Alpha', type: 'Vir', index: idxNum, eng, homo: false, lumo: idxNum === fileData.lumo_alpha })),
            ...fileData.beta_occ.map(([idxNum, eng]) => ({ spin: 'Beta', type: 'Occ', index: idxNum, eng, homo: idxNum === fileData.homo_beta, lumo: false })),
            ...fileData.beta_virt.map(([idxNum, eng]) => ({ spin: 'Beta', type: 'Vir', index: idxNum, eng, homo: false, lumo: idxNum === fileData.lumo_beta }))
          ]
          const rows = allTracks.map(t => ({
            '自旋': t.spin,
            '类型': t.type,
            '轨道序号': t.index,
            '能量(Ha)': t.eng.toFixed(6),
            '能量(eV)': (t.eng * 27.211386).toFixed(4),
            'HOMO/LUMO': t.homo ? 'HOMO' : t.lumo ? 'LUMO' : ''
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
        XLSX.writeFile(wb, 'orbital_energies.xlsx')
        this.addLog('Excel 导出成功（多个 sheet）', '#7cfc00')
      } catch (e) {
        this.addLog('导出 Excel 需要 xlsx 库，请安装: npm install xlsx', '#ffa500')
        console.error(e)
      }
    }
  }
}
</script>
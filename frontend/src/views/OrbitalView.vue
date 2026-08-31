<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">⚡ 轨道能量解析</h2>
    <p style="color:#666;margin:0;font-size:14px;">选择包含 Gaussian .log 文件的文件夹，自动解析并展示轨道能量</p>

    <!-- 控制栏 -->
    <div class="flex-center flex-shrink-0" style="gap:16px;flex-wrap:wrap;">
      <button class="btn btn-primary" style="height:32px;" @click="selectFolder">📂 选择文件夹</button>
      <span v-if="folder" style="color:#1890ff;font-size:13px;">{{ folder }}</span>
      <span v-else style="color:#999;font-size:13px;">未选择</span>
      <button class="btn btn-success" style="height:32px;" @click="startParse" :disabled="running || !folder">
        {{ running ? '解析中...' : '🔄 重新解析' }}
      </button>
      <button v-if="allData.length" class="btn btn-warning" style="height:32px;" @click="exportCSV">📥 导出 CSV</button>
      <button v-if="allData.length" class="btn" style="height:32px;background:#722ed1;color:white;" @click="exportExcel">📊 导出 Excel</button>
    </div>

    <!-- 能隙计算 -->
    <div class="flex-center flex-shrink-0" style="gap:10px;background:#f9f9f9;padding:6px 14px;border-radius:6px;flex-wrap:wrap;">
      <span class="label">🔬 能隙计算</span>
      <span style="font-size:13px;">轨道 A</span>
      <input v-model.number="gapIndexA" type="number" min="1" class="control" style="height:32px; width:96px;" placeholder="序号" />
      <span style="font-size:13px;">轨道 B</span>
      <input v-model.number="gapIndexB" type="number" min="1" class="control" style="height:32px; width:96px;" placeholder="序号" />
      <button class="btn btn-primary" style="height:32px;" @click="calcGap">计算</button>
      <span v-if="gapResult" style="font-weight:bold;font-size:14px;color:#1890ff;">{{ gapResult }}</span>
      <span v-if="gapError" style="color:#ff4d4f;font-size:13px;">{{ gapError }}</span>
    </div>

    <!-- 主区域 -->
    <div class="flex flex-1 min-h-0" style="gap:16px;border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
      <!-- 左侧列表 -->
      <div style="width:200px;background:#fafafa;border-right:1px solid #e8e8e8;overflow-y:auto;padding:8px 0;flex-shrink:0;">
        <div v-if="!allData.length" style="color:#999;text-align:center;padding:20px;font-size:13px;">暂无文件</div>
        <div
          v-for="(item, idx) in allData"
          :key="idx"
          @click="selectFile(idx)"
          :style="{
            padding: '6px 16px',
            cursor: 'pointer',
            background: selectedIndex === idx ? '#e6f7ff' : 'transparent',
            borderLeft: selectedIndex === idx ? '3px solid #1890ff' : '3px solid transparent',
            fontSize: '13px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }"
          @mouseenter="e=>e.target.style.background='#f0f0f0'"
          @mouseleave="e=>{if(selectedIndex!==idx) e.target.style.background='transparent'}"
        >
          {{ item.filename }}
        </div>
      </div>

      <!-- 右侧表格 -->
      <div class="flex-col flex-1 min-h-0" style="overflow:hidden;padding:10px 12px 0;">
        <div style="flex-shrink:0;padding:0 0 8px 0;">
          <div v-if="currentTableData.length" style="font-size:13px;color:#888;">共 {{ currentTableData.length }} 条轨道</div>
        </div>
        <div ref="tableContainer" style="flex:1;overflow:auto;padding:0 0 12px 0;">
          <table v-if="currentTableData.length" style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead style="position:sticky;top:0;background:#fafafa;z-index:10;">
              <tr>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:left;">自旋</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:left;">类型</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">轨道序号</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">能量 (Ha)</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">能量 (eV)</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">标记</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, rIdx) in currentTableData"
                :key="rIdx"
                :style="row.isHOMO ? 'background:#e6f7ff;' : row.isLUMO ? 'background:#fff7e6;' : ''"
              >
                <td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;">{{ row.spin }}</td>
                <td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;">{{ row.type }}</td>
                <td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;text-align:center;">{{ row.index }}</td>
                <td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;text-align:center;">{{ row.energy_ha }}</td>
                <td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;text-align:center;">{{ row.energy_ev }}</td>
                <td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:bold;">
                  <span v-if="row.isHOMO" style="color:#1890ff;">HOMO</span>
                  <span v-else-if="row.isLUMO" style="color:#faad14;">LUMO</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;font-size:14px;">
            请选择文件夹并等待解析完成
          </div>
        </div>
      </div>
    </div>

    <LogViewer :lines="logLines" :key="logKey" />
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'

export default {
  name: 'OrbitalView',
  components: { LogViewer },
  data() {
    return {
      folder: '',
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
    }
  },
  watch: {
    selectedIndex(val) {
      this.buildCurrentTable(val)
      this.$nextTick(() => {
        this.scrollToHOMO_LUMO()
      })
      this.gapResult = ''
      this.gapError = ''
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

    async selectFolder() {
      const path = await window.electronAPI.selectDirectory({ title: '选择包含 .log 文件的文件夹' })
      if (path) {
        this.folder = path
        this.addLog(`📂 选择目录: ${path}`, '#87d2ff')
        this.allData = []
        this.currentTableData = []
        this.selectedIndex = 0
        this.gapResult = ''
        this.gapError = ''
        this.startParse()
      }
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
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog(` ${data.filename} 解析成功 [${data.index}/${data.total}]`, '#7cfc00')
            } else {
              this.addLog(`❌ ${data.filename} 解析失败: ${data.message}`, '#ff6b6b')
            }
            break
          case 'result':
            this.allData = data.data
            if (this.allData.length) {
              this.selectedIndex = 0
              this.buildCurrentTable(0)
              this.$nextTick(() => {
                setTimeout(() => {
                  this.scrollToHOMO_LUMO()
                }, 100)
              })
              this.addLog(`共解析 ${this.allData.length} 个文件`, '#87d2ff')
            }
            break
          case 'done':
            this.addLog(`🎉 ${data.message}`, '#00ff00')
            this.running = false
            this.ws.close()
            break
          case 'error':
            this.addLog(`❌ ${data.message}`, '#ff6b6b')
            this.running = false
            this.ws.close()
            break
          default:
            this.addLog(JSON.stringify(data))
        }
      }

      this.ws.onerror = () => {
        this.addLog('❌ WebSocket 错误', '#ff6b6b')
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

    scrollToHOMO_LUMO() {
      const container = this.$refs.tableContainer
      if (!container) return
      const rows = container.querySelectorAll('tr')
      for (const row of rows) {
        const style = getComputedStyle(row)
        if (style.backgroundColor === 'rgb(230, 247, 255)' || style.backgroundColor === 'rgb(255, 247, 230)') {
          row.scrollIntoView({ block: 'center', behavior: 'smooth' })
          return
        }
      }
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
<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">TD 信息提取</h2>
    <p style="color:#666;margin:0;font-size:14px;">选择包含 Gaussian .log 文件的文件夹，提取 TD 激发态信息</p>

    <!-- 控制栏 -->
    <div class="flex-center flex-shrink-0" style="gap:16px;flex-wrap:wrap;">
      <button class="btn btn-primary h-lg" @click="selectFolder">📂 选择文件夹</button>
      <span v-if="folder" style="color:#1890ff;font-size:13px;">{{ folder }}</span>
      <span v-else style="color:#999;font-size:13px;">未选择</span>
      <button class="btn btn-success h-lg" @click="startParse" :disabled="running || !folder">
        {{ running ? '解析中...' : '解析' }}
      </button>
      <button v-if="allData.length" class="btn btn-warning h-lg" @click="exportCSV">导出 CSV</button>
      <button v-if="allData.length" class="btn" style="background:#722ed1;color:white;height:32px;" @click="exportExcel">导出 Excel</button>
    </div>

    <!-- 主区域 -->
    <div class="flex flex-1 min-h-0" style="gap:16px;border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
      <!-- 左侧文件列表 -->
      <div style="width:200px;background:#fafafa;border-right:1px solid #e8e8e8;overflow-y:auto;padding:8px 0;flex-shrink:0;">
        <div v-if="!allData.length" style="color:#999;text-align:center;padding:20px;font-size:13px;">
          暂无文件
        </div>
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
      <div class="flex-col flex-1 min-h-0" style="padding:10px 12px 0;">
        <div style="flex-shrink:0;font-size:13px;color:#888;margin-bottom:6px;">
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
            <thead style="position:sticky;top:0;background:#fafafa;z-index:10;">
              <tr>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">序号</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">多重度</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">能量 (eV)</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">波长 (nm)</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:center;">振子强度</th>
                <th style="padding:6px 10px;border-bottom:1px solid #e8e8e8;text-align:left;">主要跃迁</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(state, idx) in currentStates" :key="idx">
                <!-- 固定高度的列 -->
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">
                  {{ state.state_num }}
                </td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">
                  {{ state.mult_type }}
                </td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">
                  {{ state.energy_eV.toFixed(4) }}
                </td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">
                  {{ state.wavelength_nm.toFixed(2) }}
                </td>
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;text-align:center;height:2.6em;line-height:1.3em;overflow:hidden;vertical-align:middle;">
                  {{ state.osc_strength.toFixed(6) }}
                </td>
                <!-- 主要跃迁列：内部 div 滚动 -->
                <td style="padding:5px 8px;border-bottom:1px solid #f0f0f0;height:2.6em;vertical-align:middle;text-align:left;">
                  <div style="height:100%;overflow-y:auto;word-break:break-word;line-height:1.3em;">
                    <span v-for="(t, i) in getMajorTransitions(state)" :key="i">
                      {{ t }}
                      <span v-if="i < getMajorTransitions(state).length - 1">; </span>
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;font-size:14px;">
            请选择文件夹并解析
          </div>
        </div>
      </div>
    </div>

    <!-- 日志区域 -->
    <LogViewer :lines="logLines" :key="logKey" />
  </div>
</template>

<script>
import LogViewer from '../components/LogViewer.vue'
import scrollCache from '@/mixins/scrollCache'

export default {
  name: 'TdView',
  components: { LogViewer },
  mixins: [scrollCache],
  data() {
    return {
      folder: '',
      running: false,
      logLines: [],
      logKey: 0,
      ws: null,
      allData: [],
      selectedIndex: 0,
    }
  },
  computed: {
    currentStates() {
      if (this.allData.length && this.selectedIndex < this.allData.length) {
        return this.allData[this.selectedIndex].states || []
      }
      return []
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

    getMajorTransitions(state, threshold = 5) {
      const items = state.transitions
        .filter(t => t.percent > threshold)
        .sort((a, b) => b.percent - a.percent)
        .map(t => `${t.from}→${t.to} (${t.percent.toFixed(1)}%)`)
      return items.length ? items : ['无显著贡献']
    },

    async selectFolder() {
      const path = await window.electronAPI.selectDirectory({ title: '选择包含 .log 文件的文件夹' })
      if (path) {
        this.folder = path
        this.addLog(`📂 选择目录: ${path}`, '#87d2ff')
        this.allData = []
        this.selectedIndex = 0
        this.startParse()
      }
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
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'progress':
            if (data.status === 'success') {
              this.addLog(`${data.filename} 解析成功 [${data.index}/${data.total}]`, '#7cfc00')
            } else {
              this.addLog(`❌ ${data.filename} 解析失败: ${data.message}`, '#ff6b6b')
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
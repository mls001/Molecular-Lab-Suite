<template>
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <h2 style="margin:0;">重组能提取</h2>
    <p style="color:#666;margin:0;font-size:14px;">选择包含 FCclasses .out 输出文件和 HuangRhys.dat/.txt 的文件夹</p>

    <!-- 控制栏 -->
    <div class="flex-center flex-shrink-0" style="gap:16px;flex-wrap:wrap;">
      <button class="btn btn-primary h-lg" @click="selectFolder">📂 选择文件夹</button>
      <span v-if="folder" style="color:#1890ff;font-size:13px;">{{ folder }}</span>
      <span v-else style="color:#999;font-size:13px;">未选择</span>
      <button class="btn btn-success h-lg" @click="startParse" :disabled="running || !folder">
        {{ running ? '解析中...' : '解析' }}
      </button>
      <button v-if="allData.length" class="btn btn-warning h-lg" @click="exportExcel">导出 Excel</button>
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

      <!-- 右侧：表格 + 图表 -->
      <div class="flex-col flex-1 min-h-0" style="padding:10px 12px 0;gap:8px;">
        <!-- 总重组能信息 -->
        <div v-if="currentData" style="flex-shrink:0;font-size:13px;color:#1890ff;font-weight:bold;display:flex;gap:20px;flex-wrap:wrap;">
          <span>原始总重组能: {{ currentData.reorg_total.toFixed(4) }} eV</span>
          <span>计算总重组能: {{ computedTotalReorg.toFixed(4) }} eV</span>
          <span>模式数: {{ currentData.frequencies.length }}</span>
        </div>

        <!-- 表格 + 图表 -->
        <div class="flex flex-1 min-h-0" style="gap:12px;">
          <!-- 左侧表格 -->
          <div class="flex-col" style="flex:1;min-width:0;overflow:hidden;">
            <div style="flex-shrink:0;font-size:12px;color:#888;margin-bottom:4px;">
              频率 (cm⁻¹) | 黄里斯因子 | 分解重组能 (eV)
            </div>
            <div ref="tableContainer" style="flex:1;overflow:auto;border:1px solid #f0f0f0;border-radius:4px;">
              <table v-if="currentData && currentData.frequencies.length" style="width:100%;border-collapse:collapse;font-size:12px;">
                <thead style="position:sticky;top:0;background:#fafafa;z-index:10;">
                  <tr>
                    <th style="padding:4px 8px;border-bottom:1px solid #e8e8e8;text-align:center;width:33%;">频率 (cm⁻¹)</th>
                    <th style="padding:4px 8px;border-bottom:1px solid #e8e8e8;text-align:center;width:33%;">黄里斯因子</th>
                    <th style="padding:4px 8px;border-bottom:1px solid #e8e8e8;text-align:center;width:34%;">重组能 (eV)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(freq, idx) in currentData.frequencies" :key="idx">
                    <td style="padding:3px 8px;border-bottom:1px solid #f5f5f5;text-align:center;">{{ freq.toFixed(2) }}</td>
                    <td style="padding:3px 8px;border-bottom:1px solid #f5f5f5;text-align:center;">
                      {{ currentData.huang_rhys[idx] !== undefined ? currentData.huang_rhys[idx].toFixed(6) : '0.000000' }}
                    </td>
                    <td style="padding:3px 8px;border-bottom:1px solid #f5f5f5;text-align:center;">
                      {{ currentData.reorg_contrib[idx] !== undefined ? currentData.reorg_contrib[idx].toFixed(6) : '0.000000' }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;font-size:14px;">
                请选择文件并解析
              </div>
            </div>
          </div>

          <!-- 右侧图表（始终保留实例） -->
          <div ref="chartContainer" style="flex:1.5;min-width:0;height:100%;background:white;border-radius:4px;border:1px solid #f0f0f0;position:relative;">
            <!-- 覆盖层：当无数据时显示提示 -->
            <div v-if="!chartData.length" style="position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#999;font-size:14px;pointer-events:none;z-index:1;">
              等待数据
            </div>
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
import * as echarts from 'echarts'

export default {
  name: 'ReorgExtractView',
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
      chartInstance: null,
      _resizeObserver: null,
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
    }
  },
  mounted() {
    this.initChart()
  },
  beforeUnmount() {
    if (this.ws) this.ws.close()
    if (this._resizeObserver) {
      this._resizeObserver.disconnect()
      this._resizeObserver = null
    }
    if (this.chartInstance) {
      this.chartInstance.dispose()
      this.chartInstance = null
    }
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      this.logKey++
      if (this.logLines.length > 200) this.logLines.shift()
    },

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
      // 初始空图表
      this.updateChart([])
    },

    updateChart(data) {
      if (!this.chartInstance) {
        this.initChart()
        if (!this.chartInstance) return
      }
      if (!data || data.length === 0) {
        // 清空图表但保留坐标系
        this.chartInstance.setOption({
          title: {
            text: '重组能谱',
            left: 'center',
            top: 8,
            textStyle: { fontSize: 14, fontWeight: 'normal' }
          },
          xAxis: { type: 'category', data: [] },
          yAxis: { type: 'value', min: 0, name: '重组能 (eV)' },
          series: [{ type: 'line', data: [] }]
        }, true)
        return
      }

      const freqValues = data.map(d => d.freq.toFixed(1))
      const reorgValues = data.map(d => d.reorg)
      const maxReorg = Math.max(...reorgValues, 0.001)

      const option = {
        title: {
          text: '重组能谱',
          left: 'center',
          top: 8,
          textStyle: { fontSize: 14, fontWeight: 'normal' }
        },
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            const p = params[0]
            return `频率: ${p.name} cm⁻¹<br>重组能: ${p.value.toFixed(6)} eV`
          }
        },
        grid: {
          left: 60,
          right: 20,
          top: 50,
          bottom: 40
        },
        xAxis: {
          name: '频率 (cm⁻¹)',
          nameLocation: 'center',
          nameGap: 25,
          type: 'category',
          data: freqValues,
          axisLabel: {
            fontSize: 10,
            interval: Math.max(0, Math.floor(freqValues.length / 30))
          }
        },
        yAxis: {
          name: '重组能 (eV)',
          nameLocation: 'center',
          nameGap: 35,
          type: 'value',
          min: 0,
          max: maxReorg * 1.1,
          axisLabel: {
            fontSize: 10,
            formatter: function(value) {
              return value.toExponential(2)
            }
          }
        },
        series: [{
          type: 'line',
          data: reorgValues,
          smooth: false,
          symbol: 'none',
          lineStyle: {
            color: '#1890ff',
            width: 1.5
          },
          areaStyle: {
            color: 'rgba(24, 144, 255, 0.15)'
          }
        }]
      }
      this.chartInstance.setOption(option, true)
      this.chartInstance.resize()
    },

    async selectFolder() {
      const path = await window.electronAPI.selectDirectory({ title: '选择包含 .out 和 HuangRhys 文件的文件夹' })
      if (path) {
        this.folder = path
        this.addLog(`📂 选择目录: ${path}`, '#87d2ff')
        this.allData = []
        this.selectedIndex = 0
        // 清空图表
        this.updateChart([])
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
      this.updateChart([]) // 清空图表
      this.addLog('开始解析重组能数据...', '#00ff00')

      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/reorg-extract`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog('WebSocket 已连接', '#87d2ff')
        this.ws.send(JSON.stringify({ action: 'extract_reorg', folder: this.folder }))
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
              // 更新图表
              this.$nextTick(() => {
                this.updateChart(this.chartData)
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
        // 更新图表
        this.$nextTick(() => {
          this.updateChart(this.chartData)
        })
      }
    },

async exportExcel() {
  if (!this.allData.length) return
  try {
    const XLSX = await import('xlsx')
    const wb = XLSX.utils.book_new()
    this.allData.forEach(fileData => {
      const filename = fileData.filename
      // 构建数据行：数值列直接存储为数字（不转字符串）
      const rows = fileData.frequencies.map((freq, idx) => ({
        '频率 (cm⁻¹)': freq,   // 数值
        '黄里斯因子': fileData.huang_rhys[idx] !== undefined ? fileData.huang_rhys[idx] : 0,
        '分解重组能 (eV)': fileData.reorg_contrib[idx] !== undefined ? fileData.reorg_contrib[idx] : 0
      }))
      // 添加总重组能行（数值列保留数字）
      const computed = fileData.reorg_contrib.reduce((a, b) => a + b, 0)
      rows.push({
        '频率 (cm⁻¹)': '原始总重组能',   // 文本
        '黄里斯因子': '',                // 空文本
        '分解重组能 (eV)': fileData.reorg_total  // 数值
      })
      rows.push({
        '频率 (cm⁻¹)': '计算总重组能',   // 文本
        '黄里斯因子': '',                // 空文本
        '分解重组能 (eV)': computed       // 数值
      })

      let sheetName = filename.replace(/\.out$/i, '').replace(/[\[\]:*?/\\]/g, '_')
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
    XLSX.writeFile(wb, 'reorganization_energy.xlsx')
    this.addLog('Excel 导出成功', '#7cfc00')
  } catch (e) {
    this.addLog('导出 Excel 需要 xlsx 库，请安装: npm install xlsx', '#ffa500')
    console.error(e)
  }
}
  }
}
</script>
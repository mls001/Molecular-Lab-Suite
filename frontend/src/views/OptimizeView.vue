<template>
  <div style="display:flex;flex-direction:column;gap:16px;padding:20px;">
    <h2>🧬 分子力场优化 → GJF</h2>

    <!-- 文件夹选择 -->
    <div style="display:flex;gap:20px;flex-wrap:wrap;">
      <div>
        <button @click="selectInputFolder" style="padding:6px 16px;background:#1890ff;color:white;border:none;border-radius:4px;cursor:pointer;">
           输入文件夹
        </button>
        <span v-if="inputFolder" style="margin-left:12px;color:#1890ff;">{{ inputFolder }}</span>
        <span v-else style="margin-left:12px;color:var(--c-text-3);">未选择</span>
      </div>
      <div>
        <button @click="selectOutputFolder" style="padding:6px 16px;background:#52c41a;color:white;border:none;border-radius:4px;cursor:pointer;">
           输出文件夹
        </button>
        <span v-if="outputFolder" style="margin-left:12px;color:#52c41a;">{{ outputFolder }}</span>
        <span v-else style="margin-left:12px;color:var(--c-text-3);">未选择</span>
      </div>
    </div>

    <!-- 参数 -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
      <div><label>前缀：</label><input v-model="prefix" style="width:100%;padding:4px;border:1px solid var(--c-border);border-radius:4px;" /></div>
      <div><label>力场：</label>
        <select v-model="ff" style="width:100%;padding:4px;border:1px solid var(--c-border);border-radius:4px;">
          <option>MMFF94</option>
          <option>UFF</option>
        </select>
      </div>
      <div><label>最大迭代：</label><input v-model="maxiter" type="number" style="width:100%;padding:4px;border:1px solid var(--c-border);border-radius:4px;" /></div>
      <div><label>电荷/自旋：</label><input v-model="chargeMult" placeholder="0 1" style="width:100%;padding:4px;border:1px solid var(--c-border);border-radius:4px;" /></div>
    </div>

    <div style="display:flex;gap:16px;align-items:center;">
      <label><input type="checkbox" v-model="embed" /> 自动生成3D</label>
      <label><input type="checkbox" v-model="addH" /> 添加氢</label>
      <button @click="startOptimize" :disabled="running || !inputFolder || !outputFolder" style="background:#1890ff;color:white;border:none;padding:8px 24px;border-radius:6px;cursor:pointer;">
        {{ running ? '运行中...' : ' 运行优化' }}
      </button>
    </div>

    <!-- 3D + 日志 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;height:500px;">
      <div ref="mol3dContainer" style="background:var(--c-editor);border-radius:8px;border:1px solid var(--c-border);position:relative;overflow:hidden;">
        <div v-if="!mol3dLoaded" style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--c-text-3);">等待分子加载...</div>
      </div>
      <div style="background:#1e1e1e;border-radius:8px;padding:12px;overflow-y:auto;color:#d4d4d4;font-family:monospace;font-size:13px;">
        <div v-for="(line, i) in logLines" :key="i" :style="{color: line.color || '#d4d4d4'}">{{ line.text }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { pickDirectory } from '@/api/dialog'
import { cssVar } from '@/theme/theme'
export default {
  name: 'OptimizeView',
  data() {
    return {
      inputFolder: '',
      outputFolder: '',
      prefix: 'opt_',
      ff: 'MMFF94',
      maxiter: 500,
      chargeMult: '0 1',
      embed: true,
      addH: true,
      running: false,
      logLines: [],
      ws: null,
      mol3dLoaded: false,
      viewer: null,
    }
  },
  mounted() {
    // 加载 3Dmol.js
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/3dmol@2.0.0/build/3Dmol.min.js'
    script.onload = () => {
      this.initMol3D()
    }
    document.head.appendChild(script)
  },
  beforeUnmount() {
    if (this.ws) this.ws.close()
  },
  methods: {
    // ----- 日志 -----
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      if (this.logLines.length > 200) this.logLines.shift()
    },

    // ----- 选择文件夹（调用 Electron API）-----
    async selectInputFolder() {
      let path
      try {
        path = await pickDirectory('选择输入文件夹（含 .mol）')
      } catch (e) {
        this.addLog(`选择目录失败: ${e.message}`, '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.inputFolder = path
      this.addLog(` 输入目录: ${path}`, '#87d2ff')
    },
    async selectOutputFolder() {
      let path
      try {
        path = await pickDirectory('选择输出文件夹（保存 .gjf）')
      } catch (e) {
        this.addLog(`选择目录失败: ${e.message}`, '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.outputFolder = path
      this.addLog(` 输出目录: ${path}`, '#87d2ff')
    },

    // ----- 3D 初始化 -----
    initMol3D() {
      if (!this.$refs.mol3dContainer) return
      try {
        this.viewer = new window.$3Dmol.createViewer(this.$refs.mol3dContainer, {
          backgroundColor: cssVar('--c-editor'),
        })
        this.viewer.setStyle({}, { stick: {} })
        this.viewer.zoomTo()
        this.viewer.render()
        this.mol3dLoaded = true
        this.addLog(' 3D 预览已初始化', '#7cfc00')
      } catch (e) {
        this.addLog('️ 3Dmol 加载失败', '#ffa500')
      }
    },

    // ----- 更新 3D 结构 -----
    updateMol3D(coords, filename, step) {
      if (!this.viewer) return
      // 构建 XYZ 字符串（使用原子符号占位，实际可根据分子确定）
      const symbols = ['C', 'C', 'C', 'C', 'C', 'C', 'H', 'H', 'H', 'H', 'H', 'H']
      let xyz = `${coords.length}\n${filename} step ${step}\n`
      coords.forEach((pos, i) => {
        const sym = symbols[i % symbols.length]
        xyz += `${sym} ${pos[0]} ${pos[1]} ${pos[2]}\n`
      })
      this.viewer.removeAllModels()
      this.viewer.addModel(xyz, 'xyz')
      this.viewer.setStyle({}, { stick: { color: 'gray' }, sphere: { radius: 0.3, color: 'gray' } })
      this.viewer.zoomTo()
      this.viewer.render()
    },

    // ----- 启动优化 -----
    startOptimize() {
      if (this.running) return
      if (!this.inputFolder || !this.outputFolder) {
        this.addLog('️ 请先选择输入和输出文件夹', '#ffa500')
        return
      }
      this.running = true
      this.logLines = []
      this.addLog(' 开始优化...', '#00ff00')

      // 使用注入的全局常量构建 WebSocket URL
      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/optimize`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog(' WebSocket 已连接', '#87d2ff')
        const params = {
          input_folder: this.inputFolder,
          output_folder: this.outputFolder,
          prefix: this.prefix,
          ff: this.ff,
          maxiter: this.maxiter,
          embed: this.embed,
          add_h: this.addH,
          charge: this.chargeMult.split(' ')[0] || '0',
          mult: this.chargeMult.split(' ')[1] || '1',
          keyword: '#p opt b3lyp/6-31g(d,p)',
          mem: '20GB',
          nproc: '8'
        }
        this.ws.send(JSON.stringify({ action: 'optimize', params }))
      }

      this.ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        switch (data.type) {
          case 'structure':
            if (this.viewer && data.coords) {
              this.updateMol3D(data.coords, data.filename, data.step)
            }
            this.addLog(` ${data.filename} 步 ${data.step}`, '#87d2ff')
            break
          case 'info':
            this.addLog(` ${data.message}`, '#7cfc00')
            break
          case 'error':
            this.addLog(` ${data.message}`, '#ff6b6b')
            break
          case 'file_generated':
            this.addLog(` 生成: ${data.output_path}`, '#ffd700')
            break
          case 'done':
            this.addLog(` ${data.message}`, '#00ff00')
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
    }
  }
}
</script>
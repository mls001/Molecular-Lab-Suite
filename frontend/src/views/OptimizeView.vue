<template>
  <div style="display:flex;flex-direction:column;gap:12px;padding:10px;">
    <h2 style="font-size:15px;">{{ $t('分子力场优化 → GJF') }}</h2>

    <!-- 文件夹选择 -->
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
      <div class="flex-center">
        <button class="btn btn-primary" @click="selectInputFolder">
           {{ $t('输入文件夹') }}
        </button>
        <span v-if="inputFolder" style="margin-left:10px;color:var(--c-accent);font-size:12px;">{{ inputFolder }}</span>
        <span v-else style="margin-left:10px;color:var(--c-text-3);font-size:12px;">{{ $t('未选择') }}</span>
      </div>
      <div class="flex-center">
        <button class="btn" @click="selectOutputFolder">
           {{ $t('输出文件夹') }}
        </button>
        <span v-if="outputFolder" style="margin-left:10px;color:var(--c-green);font-size:12px;">{{ outputFolder }}</span>
        <span v-else style="margin-left:10px;color:var(--c-text-3);font-size:12px;">{{ $t('未选择') }}</span>
      </div>
    </div>

    <!-- 参数 -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;max-width:760px;">
      <div><label class="label">{{ $t('前缀：') }}</label><input v-model="prefix" class="control" style="width:100%;height:24px;" /></div>
      <div><label class="label">{{ $t('力场：') }}</label>
        <select v-model="ff" class="control" style="width:100%;height:24px;">
          <option>MMFF94</option>
          <option>UFF</option>
        </select>
      </div>
      <div><label class="label">{{ $t('最大迭代：') }}</label><input v-model="maxiter" type="number" class="control" style="width:100%;height:24px;" /></div>
      <div><label class="label">{{ $t('电荷/自旋：') }}</label><input v-model="chargeMult" placeholder="0 1" class="control" style="width:100%;height:24px;" /></div>
    </div>

    <div style="display:flex;gap:14px;align-items:center;">
      <label class="flex-center" style="gap:4px;font-size:12px;"><input type="checkbox" v-model="embed" /> {{ $t('自动生成3D') }}</label>
      <label class="flex-center" style="gap:4px;font-size:12px;"><input type="checkbox" v-model="addH" /> {{ $t('添加氢') }}</label>
      <button class="btn btn-primary" @click="startOptimize" :disabled="running || !inputFolder || !outputFolder">
        {{ running ? $t('运行中...') : $t(' 运行优化') }}
      </button>
    </div>

    <!-- 3D + 日志 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;height:460px;">
      <div ref="mol3dContainer" class="mls-panel" style="position:relative;overflow:hidden;">
        <div v-if="!mol3dLoaded" style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--c-text-3);">{{ $t('等待分子加载...') }}</div>
      </div>
      <div style="background:#16181b;border:1px solid #3a3f45;padding:8px;overflow-y:auto;color:#d4d4d4;font-family:var(--font-mono);font-size:11.5px;">
        <div v-for="(line, i) in logLines" :key="i" :style="{color: line.color || '#d4d4d4'}">{{ line.text }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { pickDirectory } from '@/api/dialog'
import { load3Dmol } from '@/utils/threeDmol'
import { cssVar } from '@/theme/theme'
import { t as $tr } from '@/i18n'


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
    // 3Dmol 用打包进来的版本（离线可用，不加载外部 CDN）
    load3Dmol().then((lib) => {
      if (lib) this.initMol3D()
      else this.addLog($tr('3D 视图加载失败（打包版 3Dmol 不可用）'), '#ff6b6b')
    })
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
        path = await pickDirectory($tr('选择输入文件夹（含 .mol）'))
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.inputFolder = path
      this.addLog($tr(' 输入目录: {0}', { 0: path }), '#87d2ff')
    },
    async selectOutputFolder() {
      let path
      try {
        path = await pickDirectory($tr('选择输出文件夹（保存 .gjf）'))
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!path) return // 用户取消
      this.outputFolder = path
      this.addLog($tr(' 输出目录: {0}', { 0: path }), '#87d2ff')
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
        this.addLog($tr(' 3D 预览已初始化'), '#7cfc00')
      } catch (e) {
        this.addLog($tr('️ 3Dmol 加载失败'), '#ffa500')
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
        this.addLog($tr('️ 请先选择输入和输出文件夹'), '#ffa500')
        return
      }
      this.running = true
      this.logLines = []
      this.addLog($tr(' 开始优化...'), '#00ff00')

      // 使用注入的全局常量构建 WebSocket URL
      const wsUrl = `ws://${__BACKEND_HOST__}:${__BACKEND_PORT__}/ws/optimize`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.addLog($tr(' WebSocket 已连接'), '#87d2ff')
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
            this.addLog($tr(' {0} 步 {1}', { 0: data.filename, 1: data.step }), '#87d2ff')
            break
          case 'info':
            this.addLog(` ${data.message}`, '#7cfc00')
            break
          case 'error':
            this.addLog(` ${data.message}`, '#ff6b6b')
            break
          case 'file_generated':
            this.addLog($tr(' 生成: {0}', { 0: data.output_path }), '#ffd700')
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
        this.addLog($tr(' WebSocket 错误'), '#ff6b6b')
        this.running = false
      }

      this.ws.onclose = () => {
        this.running = false
      }
    }
  }
}
</script>
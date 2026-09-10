<template>
  <div v-if="picker.visible" class="modal-overlay" @click.self="cancel">
    <div
      class="modal-content flex-col"
      style="width:760px;max-width:92vw;height:72vh;background:var(--c-elev);padding:12px;color:var(--c-text);"
    >
      <!-- 标题 -->
      <div class="flex-center" style="justify-content:space-between;margin-bottom:8px;">
        <span style="font-weight:700;">{{ picker.title }}</span>
        <span style="font-size:12px;color:var(--c-text-3);">
          {{ picker.mode === 'dir' ? $t('选择文件夹') : $t('选择文件') }}
        </span>
      </div>

      <!-- 常用位置 / 盘符 -->
      <div class="flex-center" style="gap:6px;flex-wrap:wrap;margin-bottom:6px;">
        <button
          v-for="p in places"
          :key="p.path"
          class="btn btn-default"
          style="height:22px;padding:0 9px;font-size:11px;"
          @click="goto(p.path)"
        >{{ p.label }}</button>
        <span style="flex:1;"></span>
        <button v-if="hasNative" class="btn btn-default" style="height:22px;padding:0 9px;font-size:11px;" @click="nativePick">
          {{ $t('系统对话框…') }}
        </button>
      </div>

      <!-- 路径栏 -->
      <div class="flex-center" style="gap:6px;margin-bottom:6px;">
        <input class="control" style="flex:1;height:26px;" v-model="pathInput" @keydown.enter="goto(pathInput)" :placeholder="$t('可直接粘贴路径后回车')" />
        <button class="btn btn-default" style="height:26px;" @click="goUp" :disabled="!canGoUp">{{ $t('上级') }}</button>
        <button class="btn btn-primary" style="height:26px;" @click="reload" :disabled="loading">{{ $t('刷新') }}</button>
      </div>

      <!-- 过滤 -->
      <div class="flex-center" style="gap:10px;margin-bottom:6px;">
        <input class="control" style="flex:1;height:24px;font-size:12px;" v-model="filterText" :placeholder="$t('按名称过滤')" />
        <label v-if="matchExtensions.length" class="flex-center" style="gap:4px;font-size:12px;color:var(--c-text-2);cursor:pointer;white-space:nowrap;">
          <input type="checkbox" v-model="onlyMatching" /> {{ $t('只看') }} {{ matchExtensions.join(' / ') }}
        </label>
      </div>

      <!-- 列表 -->
      <div style="flex:1;min-height:0;overflow-y:auto;border:1px solid var(--c-border-strong);padding:2px;background:var(--c-main);">
        <div
          v-if="error"
          style="padding:14px;color:var(--c-danger);font-size:12px;white-space:pre-wrap;"
        >{{ error }}</div>
        <template v-else>
          <div
            v-for="e in shownEntries"
            :key="e.name"
            class="flex-center"
            style="gap:8px;padding:3px 8px;cursor:pointer;font-size:12px;"
            :style="{ background: selected === e.name ? 'var(--c-hl-a)' : 'transparent' }"
            @click="onClick(e)"
            @dblclick="onDblClick(e)"
            @mouseenter="ev => { if (selected !== e.name) ev.currentTarget.style.background = 'var(--c-hover)' }"
            @mouseleave="ev => { if (selected !== e.name) ev.currentTarget.style.background = 'transparent' }"
          >
            <span style="width:52px;flex-shrink:0;font-size:11px;color:var(--c-text-3);">{{ e.is_dir ? $t('[目录]') : $t('[文件]') }}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :style="{ color: e.is_dir ? 'var(--c-text)' : (e.match ? 'var(--c-code)' : 'var(--c-text-2)'), fontWeight: e.match ? 700 : 400 }">{{ e.name }}</span>
            <span v-if="!e.is_dir" style="font-size:11px;color:var(--c-text-3);flex-shrink:0;">{{ fmtSize(e.size) }}</span>
          </div>
          <div v-if="!shownEntries.length && !loading" style="padding:16px;text-align:center;color:var(--c-text-3);font-size:12px;">
            {{ filterText || onlyMatching ? $t('没有匹配项') : $t('（空目录）') }}
          </div>
          <div v-if="loading" style="padding:16px;text-align:center;color:var(--c-text-3);font-size:12px;">{{ $t('读取中…') }}</div>
        </template>
      </div>

      <!-- 底部 -->
      <div class="flex-center" style="gap:8px;margin-top:10px;">
        <span style="font-size:12px;color:var(--c-text-2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          {{ $t('当前') }}: {{ currentPath }}
          <template v-if="picker.mode === 'dir'">　{{ $t('选中') }}: {{ selectedDir || $t('（未选中，将使用当前目录）') }}</template>
          <template v-else>　{{ $t('选中文件') }}: {{ selectedFile || $t('（未选中）') }}</template>
        </span>
        <button class="btn btn-default h-lg" @click="cancel">{{ $t('取消') }}</button>
        <button class="btn btn-primary h-lg" @click="confirm" :disabled="!canConfirm">
          {{ picker.mode === 'dir' ? $t('使用此文件夹') : $t('选择此文件') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { usePathPickerStore } from '@/stores/pathPicker'
import { t as $tr } from '@/i18n'

const BACKEND = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
const LAST_DIR_KEY = 'mls.lastDir'

const isWinPath = (p) => /^[A-Za-z]:[\\/]/.test(p || '')
const joinPath = (dir, name) => {
  if (!dir) return name
  const sep = dir.includes('\\') || isWinPath(dir) ? '\\' : '/'
  return dir.replace(/[\\/]+$/, '') + sep + name
}
const parentPath = (p) => {
  const n = (p || '').replace(/[\\/]+$/, '')
  if (!n) return ''
  if (/^[A-Za-z]:$/.test(n)) return ''            // 盘符根：用上方盘符按钮切换
  const i = Math.max(n.lastIndexOf('\\'), n.lastIndexOf('/'))
  if (i < 0) return ''
  if (i === 0) return '/'
  const head = n.substring(0, i)
  if (/^[A-Za-z]:$/.test(head)) return head + '\\'
  return head
}
const fmtSize = (n) => {
  if (!n && n !== 0) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}


export default {
  name: 'LocalPathPicker',
  setup() {
    const picker = usePathPickerStore()
    return { picker }
  },
  data() {
    return {
      currentPath: '',
      pathInput: '',
      entries: [],
      selected: '',            // 条目名（目录或文件）
      filterText: '',
      onlyMatching: false,
      loading: false,
      error: '',
      places: [],
      lastDir: ''
    }
  },
  computed: {
    matchExtensions() {
      const exts = (this.picker.extensions || []).filter(e => e && e !== '*')
      return exts.map(e => (e.startsWith('.') ? e : `.${e}`))
    },
    shownEntries() {
      let list = this.entries
      if (this.onlyMatching && this.matchExtensions.length) {
        list = list.filter(e => e.is_dir || e.match)
      }
      const q = this.filterText.trim().toLowerCase()
      if (q) list = list.filter(e => e.name.toLowerCase().includes(q))
      return list
    },
    selectedEntry() {
      return this.entries.find(e => e.name === this.selected) || null
    },
    selectedDir() {
      const e = this.selectedEntry
      return e && e.is_dir ? joinPath(this.currentPath, e.name) : ''
    },
    selectedFile() {
      const e = this.selectedEntry
      return e && !e.is_dir ? joinPath(this.currentPath, e.name) : ''
    },
    canConfirm() {
      if (this.picker.mode === 'file') return !!this.selectedFile
      return !!this.currentPath
    },
    // 注意：parentPath 是模块级函数，模板里访问不到，必须用 computed 暴露
    canGoUp() {
      return !!parentPath(this.currentPath)
    },
    hasNative() {
      const api = window.electronAPI
      return !!(api && (typeof api.selectDirectory === 'function' || typeof api.selectFile === 'function'))
    }
  },
  watch: {
    'picker.visible'(vis) {
      if (vis) this.start()
      else this.detachKeys()
    }
  },
  mounted() {
    this.loadPlaces()
  },
  beforeUnmount() {
    this.detachKeys()
  },
  methods: {
    fmtSize,
    // ===== 生命周期 =====
    async start() {
      if (!this.places.length) await this.loadPlaces()
      const candidate = this.picker.initialPath || localStorage.getItem(LAST_DIR_KEY) || ''
      this.pathInput = candidate
      this.selected = ''
      this.filterText = ''
      this.onlyMatching = false
      this.attachKeys()
      await this.goto(candidate)
    },
    attachKeys() {
      window.addEventListener('keydown', this.onKey)
    },
    detachKeys() {
      window.removeEventListener('keydown', this.onKey)
    },
    onKey(e) {
      if (!this.picker.visible) return
      if (e.key === 'Escape') { e.preventDefault(); this.cancel() }
      else if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); this.confirm() }
    },
    // ===== 数据加载 =====
    async loadPlaces() {
      try {
        const r = await fetch(`${BACKEND}/api/local/places`)
        const d = await r.json()
        this.places = [...(d.drives || []), ...(d.places || [])]
        this.lastDir = d.home || ''
      } catch (e) {
        this.places = []
      }
    },
    async goto(path) {
      const target = (path || '').trim()
      if (!target) {
        // 没有可用起始路径时退到主目录/第一个盘符
        if (this.lastDir) return await this.goto(this.lastDir)
        if (this.places.length) return await this.goto(this.places[0].path)
        return
      }
      this.loading = true
      this.error = ''
      try {
        const r = await fetch(`${BACKEND}/api/local/ls`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: target })
        })
        const d = await r.json().catch(() => ({}))
        if (!r.ok) {
          this.error = $tr('无法读取目录：{0}\n路径：{1}', { 0: d.detail || ('HTTP ' + r.status), 1: target })
          this.entries = []
          return
        }
        this.currentPath = d.path || target
        this.pathInput = this.currentPath
        const exts = this.matchExtensions.map(x => x.toLowerCase())
        this.entries = (d.entries || []).map(e => {
          const lower = e.name.toLowerCase()
          const match = !exts.length ? true : exts.some(x => lower.endsWith(x))
          return { ...e, match }
        })
        this.selected = ''
        localStorage.setItem(LAST_DIR_KEY, this.currentPath)
      } catch (e) {
        this.error = $tr('无法读取目录：{0}\n路径：{1}', { 0: e.message, 1: target })
        this.entries = []
      } finally {
        this.loading = false
      }
    },
    reload() {
      return this.goto(this.currentPath || this.pathInput)
    },
    goUp() {
      const parent = parentPath(this.currentPath)
      if (parent) return this.goto(parent)
    },
    // ===== 交互 =====
    onClick(entry) {
      this.selected = entry.name
    },
    onDblClick(entry) {
      if (entry.is_dir) {
        this.goto(joinPath(this.currentPath, entry.name))
      } else if (this.picker.mode === 'file') {
        this.selected = entry.name
        this.confirm()
      }
      // 目录模式下双击文件：保持当前目录（提示用户可用当前目录）
    },
    confirm() {
      let result = null
      if (this.picker.mode === 'file') {
        result = this.selectedFile
        if (!result) return
      } else {
        result = this.selectedDir || this.currentPath
        if (!result) return
      }
      localStorage.setItem(LAST_DIR_KEY, this.picker.mode === 'dir' ? result : this.currentPath)
      this.picker.finish(result)
    },
    cancel() {
      this.picker.cancel()
    },
    async nativePick() {
      const api = window.electronAPI
      try {
        let path = null
        if (this.picker.mode === 'file' && typeof api.selectFile === 'function') {
          path = await api.selectFile({
            title: this.picker.title,
            defaultPath: this.currentPath || undefined,
            filters: this.matchExtensions.length
              ? [{ name: $tr('匹配文件'), extensions: this.matchExtensions.map(x => x.replace('.', '')) },
                 { name: $tr('全部文件'), extensions: ['*'] }]
              : [{ name: $tr('全部文件'), extensions: ['*'] }]
          })
        } else if (typeof api.selectDirectory === 'function') {
          path = await api.selectDirectory({ title: this.picker.title, defaultPath: this.currentPath || undefined })
        }
        if (path) {
          localStorage.setItem(LAST_DIR_KEY, this.picker.mode === 'dir' ? path : this.currentPath)
          this.picker.finish(path)
        }
      } catch (e) {
        this.error = $tr('系统对话框失败：{0}', { 0: e.message })
      }
    }
  }
}
</script>

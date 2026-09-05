<template>
  <!-- 远程路径选择：与「本地路径选择器」保持同一套外观与交互（弹窗 / 快捷位置 / 路径栏 / 列表 / 底部） -->
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div
      class="modal-content flex-col"
      style="width:760px;max-width:92vw;height:72vh;background:var(--c-elev);padding:12px;color:var(--c-text);"
    >
      <!-- 标题 -->
      <div class="flex-center" style="justify-content:space-between;margin-bottom:8px;">
        <span style="font-weight:700;">{{ $t('选择远程路径') }}</span>
        <span style="font-size:12px;color:var(--c-text-3);">
          {{ sessionId ? ($t('远程') + (username ? ' · ' + username : '')) : $t('未连接') }}
        </span>
      </div>

      <!-- 快捷位置 -->
      <div class="flex-center" style="gap:6px;flex-wrap:wrap;margin-bottom:6px;">
        <button
          v-for="p in quickPlaces"
          :key="p.path"
          class="btn btn-default"
          style="height:22px;padding:0 9px;font-size:11px;"
          @click="goto(p.path)"
        >{{ p.label }}</button>
        <span style="flex:1;"></span>
        <button class="btn btn-default" style="height:22px;padding:0 9px;font-size:11px;" @click="showMk = !showMk">
          {{ $t('新建文件夹') }}
        </button>
      </div>

      <!-- 路径栏 -->
      <div class="flex-center" style="gap:6px;margin-bottom:6px;">
        <input class="control" style="flex:1;height:26px;" v-model="currentPath" :placeholder="$t('路径')" @keydown.enter="refresh" />
        <button class="btn btn-default" style="height:26px;" @click="goParent" :disabled="currentPath === '/'">{{ $t('上级') }}</button>
        <button class="btn btn-primary" style="height:26px;" @click="refresh" :disabled="loading">{{ $t('刷新') }}</button>
      </div>

      <!-- 新建文件夹 -->
      <div v-if="showMk" class="flex-center" style="gap:6px;margin-bottom:6px;">
        <input
          class="control"
          style="flex:1;height:26px;"
          v-model="mkName"
          :placeholder="$t('新文件夹名称')"
          @keydown.enter="createFolder"
        />
        <button class="btn btn-primary" style="height:26px;" @click="createFolder" :disabled="creating">
          {{ creating ? $t('创建中…') : $t('创建') }}
        </button>
        <button class="btn btn-default" style="height:26px;" @click="showMk = false; mkName = ''">{{ $t('取消') }}</button>
      </div>

      <!-- 过滤 -->
      <div class="flex-center" style="gap:8px;margin-bottom:6px;">
        <input class="control" style="flex:1;height:24px;font-size:12px;" v-model="filterText" :placeholder="$t('按名称过滤')" />
      </div>

      <!-- 列表 -->
      <div style="flex:1;min-height:0;overflow-y:auto;border:1px solid var(--c-border-strong);background:var(--c-main);padding:2px;">
        <div v-if="error" style="padding:14px;color:var(--c-danger);font-size:12px;white-space:pre-wrap;">{{ error }}</div>
        <template v-else>
          <div
            v-for="e in shownEntries"
            :key="(e.is_dir ? 'D_' : 'F_') + e.name"
            class="flex-center"
            style="gap:8px;padding:3px 8px;cursor:pointer;font-size:12px;"
            :style="{ background: selectedName === e.name ? 'var(--c-hl-a)' : 'transparent' }"
            @click="selectItem(e)"
            @dblclick="onDoubleClick(e)"
            @mouseenter="ev => { if (selectedName !== e.name) ev.currentTarget.style.background = 'var(--c-hover)' }"
            @mouseleave="ev => { if (selectedName !== e.name) ev.currentTarget.style.background = 'transparent' }"
          >
            <span style="width:52px;flex-shrink:0;font-size:11px;color:var(--c-text-3);">{{ e.is_dir ? $t('[目录]') : $t('[文件]') }}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ e.name }}</span>
            <span v-if="!e.is_dir" style="font-size:11px;color:var(--c-text-3);flex-shrink:0;">{{ formatSize(e.size) }}</span>
          </div>
          <div v-if="!shownEntries.length && !loading" style="padding:16px;text-align:center;color:var(--c-text-3);font-size:12px;">
            {{ filterText ? $t('没有匹配项（可清空过滤框查看全部）') : $t('目录为空或无法读取') }}
          </div>
          <div v-if="loading" style="padding:16px;text-align:center;color:var(--c-text-3);font-size:12px;">{{ $t('读取中…') }}</div>
        </template>
      </div>

      <!-- 底部 -->
      <div class="flex-center" style="gap:8px;margin-top:8px;">
        <span style="font-size:12px;color:var(--c-text-2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          {{ $t('当前') }}: {{ currentPath }}　{{ $t('选中') }}: {{ selectedPath || $t('（未选中，将使用当前目录）') }}
        </span>
        <button class="btn btn-default h-lg" @click="close">{{ $t('取消') }}</button>
        <button class="btn btn-primary h-lg" @click="confirm" :disabled="!canConfirm">{{ $t('选择') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { t as $tr } from '@/i18n'

const posixJoin = (dir, name) => `${(dir || '/').replace(/\/+$/, '')}/${name}`.replace(/\/{2,}/g, '/')


export default {
  name: 'RemoteFileBrowser',
  props: {
    visible: { type: Boolean, required: true },
    sessionId: { type: String, required: true },
    initialPath: { type: String, default: '/' },
    target: { type: String, default: '' }
  },
  emits: ['update:visible', 'select'],
  setup() {
    const remoteStore = useRemoteStore()
    return { remoteStore }
  },
  data() {
    return {
      currentPath: this.initialPath || '/',
      entries: [],
      selectedName: '',
      filterText: '',
      backendUrl: '',
      showMk: false,
      mkName: '',
      creating: false,
      loading: false,
      error: ''
    }
  },
  computed: {
    username() {
      return this.remoteStore.username || ''
    },
    quickPlaces() {
      const places = [{ label: '/', path: '/' }]
      if (this.username) places.push({ label: '~', path: `/home/${this.username}` })
      places.push({ label: '/home', path: '/home' }, { label: '/tmp', path: '/tmp' }, { label: '/scratch', path: '/scratch' })
      return places
    },
    shownEntries() {
      const q = this.filterText.trim().toLowerCase()
      const list = q ? this.entries.filter(e => e.name.toLowerCase().includes(q)) : this.entries
      return list
    },
    selectedPath() {
      return this.selectedName ? posixJoin(this.currentPath, this.selectedName) : ''
    },
    canConfirm() {
      return !!this.selectedName || (!!this.currentPath && this.currentPath !== '/')
    }
  },
  async mounted() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try {
        this.backendUrl = await window.electronAPI.getBackendUrl()
      } catch (e) {
        this.backendUrl = 'http://127.0.0.1:8002'
      }
    } else {
      this.backendUrl = 'http://127.0.0.1:8002'
    }
  },
  watch: {
    initialPath(newVal) {
      this.currentPath = newVal || '/'
    },
    visible(newVal) {
      if (newVal) {
        this.currentPath = this.initialPath || '/'
        this.selectedName = ''
        this.filterText = ''
        this.showMk = false
        this.mkName = ''
        this.error = ''
        this.refresh()
      }
    }
  },
  methods: {
    formatSize(bytes) {
      if (!bytes && bytes !== 0) return ''
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / 1048576).toFixed(1) + ' MB'
    },
    async goto(path) {
      this.currentPath = path || '/'
      await this.refresh()
    },
    async refresh() {
      if (!this.sessionId) {
        this.error = this.$t($tr('未连接'))
        return
      }
      this.loading = true
      this.error = ''
      try {
        const response = await fetch(`${this.backendUrl}/api/remote/ls`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, path: this.currentPath || '/' })
        })
        const text = await response.text()
        let data = {}
        try {
          data = text ? JSON.parse(text) : {}
        } catch (e) {
          data = { detail: text }
        }
        if (response.ok) {
          this.entries = data.entries || []
          this.currentPath = data.current_path || this.currentPath
          this.selectedName = ''
        } else {
          this.entries = []
          this.error = `${this.$t('目录为空或无法读取')}：${data.detail || ('HTTP ' + response.status)}`
        }
      } catch (e) {
        this.entries = []
        this.error = $tr('读取目录失败: {0}', { 0: e.message })
      } finally {
        this.loading = false
      }
    },
    goParent() {
      const parts = (this.currentPath || '/').split('/').filter(p => p)
      if (parts.length) {
        parts.pop()
        this.currentPath = '/' + parts.join('/')
        if (this.currentPath === '') this.currentPath = '/'
        this.selectedName = ''
        this.refresh()
      }
    },
    selectItem(entry) {
      this.selectedName = entry.name
    },
    async createFolder() {
      const name = (this.mkName || '').trim()
      if (!name || name.indexOf('/') >= 0 || name.indexOf('\\') >= 0) {
        this.error = this.$t($tr('请输入合法的文件夹名（不含路径分隔符）'))
        return
      }
      const path = posixJoin(this.currentPath, name)
      this.creating = true
      try {
        const r = await fetch(`${this.backendUrl}/api/remote/mkdir`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId, path })
        })
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`)
        this.mkName = ''
        this.showMk = false
        this.error = ''
        await this.refresh()          // 停留在当前目录并刷新，新建的文件夹即可见
      } catch (e) {
        this.error = `${this.$t('创建失败')}：` + (e.message || e)
      } finally {
        this.creating = false
      }
    },
    onDoubleClick(entry) {
      if (entry.is_dir) {
        this.currentPath = posixJoin(this.currentPath, entry.name)
        this.selectedName = ''
        this.refresh()
      } else {
        this.selectedName = entry.name
        this.confirm()
      }
    },
    confirm() {
      const entry = this.entries.find(e => e.name === this.selectedName) || null
      let resultPath = this.currentPath
      let isDir = true
      let name = (this.currentPath || '/').split('/').filter(p => p).pop() || '/'
      if (entry) {
        resultPath = posixJoin(this.currentPath, entry.name)
        isDir = !!entry.is_dir
        name = entry.name
      }
      this.$emit('select', { target: this.target, path: resultPath, is_dir: isDir, name })
      this.close()
    },
    close() {
      this.$emit('update:visible', false)
    }
  }
}
</script>

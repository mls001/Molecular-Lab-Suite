<template>
  <div class="flex-col" style="height:100%;background:#1e1e1e;color:#cfcfcf;font-size:12px;min-height:0;">
    <!-- 标题 -->
    <div class="flex-center" style="justify-content:space-between;background:#2d2d2d;padding:3px 10px;flex-shrink:0;">
      <span style="font-weight:500;font-size:12px;color:#ccc;">FTP - {{ remoteStore.displayName }}</span>
      <button class="ftp-close" @click="$emit('close')" :title="$t('关闭FTP')">×</button>
    </div>

    <div class="flex flex-1 min-h-0" style="padding:4px;gap:6px;">
      <!-- 本地 -->
      <div class="flex-col" style="flex:1;min-width:0;border:1px solid #3a3a3a;border-radius:4px;overflow:hidden;">
        <div class="flex-center" style="gap:4px;padding:4px;background:#2d2d2d;flex-shrink:0;">
          <span style="color:#8a8a8a;">{{ $t('本地') }}</span>
          <input v-model="localPath" class="ftp-input" @keydown.enter="loadLocal" />
          <button class="ftp-btn" @click="loadLocal">{{ $t('刷新') }}</button>
        </div>
        <div class="flex-1" style="overflow-y:auto;padding:2px;" ref="localList" @wheel.prevent="onWheel($event, 'local')">
          <div class="ftp-row" @click="enterLocalParent">{{ $t('..（上级）') }}</div>
          <div
            v-for="e in localEntries"
            :key="e.name"
            class="ftp-row"
            :class="{ selected: localSel.has(e.name) }"
            @click="toggleLocal(e)"
            @dblclick="enterLocalDir(e)"
          >
            <input type="checkbox" :checked="localSel.has(e.name)" @click.stop @change="toggleLocal(e)" />
            <span>{{ e.is_dir ? $t('[目录]') : '' }} {{ e.name }}</span>
            <span v-if="!e.is_dir" style="margin-left:auto;color:#777;">{{ fmtSize(e.size) }}</span>
          </div>
          <div v-if="!localEntries.length" style="color:#666;padding:8px;text-align:center;">{{ $t('（空目录）') }}</div>
        </div>
      </div>

      <!-- 远程 -->
      <div class="flex-col" style="flex:1;min-width:0;border:1px solid #3a3a3a;border-radius:4px;overflow:hidden;">
        <div class="flex-center" style="gap:4px;padding:4px;background:#2d2d2d;flex-shrink:0;">
          <span style="color:#8a8a8a;">{{ $t('远程') }}</span>
          <input v-model="remotePath" class="ftp-input" @keydown.enter="loadRemote" />
          <button class="ftp-btn" @click="loadRemote">{{ $t('刷新') }}</button>
          <button class="ftp-btn" @click="showMk = !showMk">{{ $t('新建文件夹') }}</button>
        </div>
        <div v-if="showMk" class="flex-center" style="gap:4px;padding:4px;background:#262626;flex-shrink:0;">
          <input v-model="mkName" class="ftp-input" :placeholder="$t('新文件夹名称')" @keydown.enter="createRemoteFolder" />
          <button class="ftp-btn main" @click="createRemoteFolder" :disabled="creatingMk">{{ creatingMk ? $t('创建中…') : $t('创建') }}</button>
          <button class="ftp-btn" @click="showMk = false; mkName = ''">{{ $t('取消') }}</button>
        </div>
        <div class="flex-1" style="overflow-y:auto;padding:2px;" ref="remoteList" @wheel.prevent="onWheel($event, 'remote')">
          <div class="ftp-row" @click="enterRemoteParent">{{ $t('..（上级）') }}</div>
          <div
            v-for="e in remoteEntries"
            :key="e.name"
            class="ftp-row"
            :class="{ selected: remoteSel.has(e.name) }"
            @click="toggleRemote(e)"
            @dblclick="enterRemoteDir(e)"
          >
            <input
              type="checkbox"
              :checked="remoteSel.has(e.name)"
              :disabled="isBlocked(e.name)"
              @click.stop
              @change="toggleRemote(e)"
            />
            <span>{{ e.is_dir ? $t('[目录]') : '' }} {{ e.name }}</span>
            <span v-if="isBlocked(e.name)" style="margin-left:auto;color:#b3483c;font-size:11px;">{{ $t('禁止下载') }}</span>
            <span v-else-if="!e.is_dir" style="margin-left:auto;color:#777;">{{ fmtSize(e.size) }}</span>
          </div>
          <div v-if="!remoteEntries.length" style="color:#666;padding:8px;text-align:center;">{{ $t('（空目录）') }}</div>
        </div>
      </div>
    </div>

    <!-- 传输操作 + 进度 -->
    <div style="padding:4px 8px;background:#262626;flex-shrink:0;">
      <div class="flex-center" style="gap:6px;">
        <button class="ftp-btn main" @click="uploadSelected" :disabled="busy || !localSel.size || !remotePath || !remoteStore.connected" style="color:#7ecb7e;">{{ $t('上传 → 远程') }}</button>
        <button class="ftp-btn main" @click="downloadSelected" :disabled="busy || !remoteSel.size || !localPath" style="color:#7fb0dd;">{{ $t('下载 → 本地') }}</button>
        <button class="ftp-btn" @click="clearSel">{{ $t('清空选择') }}</button>
        <span style="margin-left:auto;color:#8a8a8a;">{{ localSel.size }} 本地 / {{ remoteSel.size }} 远程</span>
      </div>
      <div v-if="busy" style="margin-top:4px;">
        <div style="height:6px;background:#3a3a3a;border-radius:3px;overflow:hidden;">
          <div :style="{ width: progress + '%', height: '100%', background: '#4f8cc9' }"></div>
        </div>
        <div style="font-size:11px;color:#9aa;margin-top:2px;">{{ progressText }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { useRemoteStore } from '@/stores/remote'
import { useProgressStore } from '@/stores/progress'
import { t as $tr } from '@/i18n'

const BACKEND = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
const winParent = (p) => { const n = p.replace(/[\\/]+$/, ''); const i = Math.max(n.lastIndexOf('\\'), n.lastIndexOf('/')); return i > 0 ? n.substring(0, i) : (n.includes('\\') ? n.substring(0, 2) : '/') }
const posixJoin = (p, n) => `${p.replace(/\/+$/, '')}/${n}`
const winJoin = (p, n) => `${p.replace(/[\\/]+$/, '')}\\${n}`


export default {
  name: 'FtpPanel',
  emits: ['close'],
  setup() {
    const remoteStore = useRemoteStore()
    return { remoteStore }
  },
  data() {
    return {
      localPath: '',
      remotePath: '',
      localEntries: [],
      remoteEntries: [],
      localSel: new Set(),
      remoteSel: new Set(),
      busy: false,
      progress: 0,
      progressText: '',
      showMk: false,
      mkName: '',
      creatingMk: false
    }
  },
  mounted() {
    this.applyDefaults()
  },
  watch: {
    'remoteStore.username'(val) {
      if (val && (!this.remotePath || this.remotePath === '/')) {
        this.remotePath = `/home/${val}`
        this.loadRemote()
      }
    }
  },
  methods: {
    posixJoin,
    winJoin,
    async applyDefaults() {
      let desktop = null, home = null, platform = 'win32'
      try {
        if (window.electronAPI && window.electronAPI.getDefaultPaths) {
          const d = await window.electronAPI.getDefaultPaths()
          desktop = d.desktop; home = d.home; platform = d.platform
        }
      } catch (e) { /* ignore */ }
      if (platform === 'win32') this.localPath = desktop || 'C:\\'
      else this.localPath = (home || '/') + (this.remoteStore.username ? '/' + this.remoteStore.username : '')
      this.loadLocal()
      const u = this.remoteStore.username
      this.remotePath = u ? `/home/${u}` : '/'
      this.loadRemote()
    },
    fmtSize(b) {
      if (b < 1024) return b + ' B'
      if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
      return (b / 1048576).toFixed(1) + ' MB'
    },
    async loadLocal() {
      try {
        const r = await fetch(`${BACKEND}/api/local/ls`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: this.localPath || 'C:\\' }) })
        const d = await r.json()
        if (r.ok) this.localEntries = d.entries || []
        else this.localEntries = []
      } catch (e) { this.localEntries = [] }
    },
    async loadRemote() {
      if (!this.remoteStore.sessionId) { this.remoteEntries = []; return }
      try {
        const r = await fetch(`${BACKEND}/api/remote/ls`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: this.remoteStore.sessionId, path: this.remotePath || '/' }) })
        const d = await r.json()
        if (r.ok) this.remoteEntries = d.entries || []
      } catch (e) { this.remoteEntries = [] }
    },
    // 在当前远程目录下新建文件夹（后端 /api/remote/mkdir 已修复绝对路径拼接问题）
    async createRemoteFolder() {
      const name = (this.mkName || '').trim()
      if (!name || /[\\/]/.test(name)) {
        alert($tr('请输入合法的文件夹名（不含路径分隔符）'))
        return
      }
      if (!this.remoteStore.connected || !this.remoteStore.sessionId) {
        alert($tr('请先连接服务器'))
        return
      }
      const base = (this.remotePath || '/').replace(/\/+$/, '')
      const path = `${base}/${name}`
      this.creatingMk = true
      try {
        const r = await fetch(`${BACKEND}/api/remote/mkdir`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.remoteStore.sessionId, path })
        })
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`)
        this.showMk = false
        this.mkName = ''
        this.remotePath = base || '/'
        await this.loadRemote()          // 停留在原目录并刷新，新建的文件夹即可见
      } catch (e) {
        alert($tr('新建文件夹失败：') + (e.message || e))
      } finally {
        this.creatingMk = false
      }
    },
    enterLocalParent() { this.localPath = winParent(this.localPath); this.loadLocal() },
    enterRemoteParent() { const p = this.remotePath.replace(/\/+$/, ''); const i = p.lastIndexOf('/'); this.remotePath = i > 0 ? p.substring(0, i) : '/'; this.loadRemote() },
    enterLocalDir(e) { if (e.is_dir) { this.localPath = winJoin(this.localPath, e.name); this.loadLocal() } },
    enterRemoteDir(e) { if (e.is_dir) { this.remotePath = posixJoin(this.remotePath, e.name); this.loadRemote() } },
    isBlocked(name) { return /\.chk$/i.test(name) },
    onWheel(e, side) {
      const el = side === 'local' ? this.$refs.localList : this.$refs.remoteList
      if (!el) return
      const mult = e.deltaMode === 1 ? 16 : 1
      el.scrollTop += e.deltaY * mult * 0.45
    },
    toggleLocal(e) {
      if (this.localSel.has(e.name)) this.localSel.delete(e.name)
      else this.localSel.add(e.name)
      this.localSel = new Set(this.localSel)
    },
    toggleRemote(e) {
      if (this.isBlocked(e.name)) return
      if (this.remoteSel.has(e.name)) this.remoteSel.delete(e.name)
      else this.remoteSel.add(e.name)
      this.remoteSel = new Set(this.remoteSel)
    },
    clearSel() { this.localSel = new Set(); this.remoteSel = new Set() },
    async uploadSelected() {
      const names = [...this.localSel]
      if (!names.length) return
      const dir = this.localPath
      const rd = this.remotePath
      this.busy = true; this.progress = 0
      const gp = useProgressStore()
      gp.start($tr('上传 {0} 个文件…', { 0: names.length }))
      let done = 0, ok = 0
      let lastErr = ''
      for (const name of names) {
        const ent = this.localEntries.find(x => x.name === name)
        const lp = `${dir.replace(/[\\/]+$/, '')}\\${name}`
        this.progressText = $tr('上传中 {0}（{1}/{2}）', { 0: name, 1: done + 1, 2: names.length })
        gp.step(done, names.length, this.progressText)
        try {
          let r
          if (ent && ent.is_dir) {
            // 整目录上传：远程目标为 当前目录/文件夹名（保留文件夹本身）
            r = await fetch(`${BACKEND}/api/ftp/push-dir`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: this.remoteStore.sessionId, local_dir: lp, remote_dir: posixJoin(rd, name) }) })
          } else {
            r = await fetch(`${BACKEND}/api/ftp/push`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: this.remoteStore.sessionId, local_path: lp, remote_dir: rd }) })
          }
          const d = await r.json().catch(() => ({}))
          if (r.ok) ok++
          else lastErr = d.detail || `HTTP ${r.status}`
        } catch (e) { lastErr = e.message || $tr('网络错误') }
        done++; this.progress = Math.round((done / names.length) * 100)
        gp.step(done, names.length, this.progressText)
      }
      this.progressText = lastErr && ok < names.length ? $tr('上传：成功 {0}/{1}（{2}）', { 0: ok, 1: names.length, 2: lastErr }) : $tr('上传完成：成功 {0}/{1}', { 0: ok, 1: names.length })
      gp.finish(this.progressText)
      this.busy = false
      this.clearSel(); this.loadLocal(); this.loadRemote()
      setTimeout(() => { this.progress = 0; this.progressText = '' }, 2500)
    },
    async downloadSelected() {
      const names = [...this.remoteSel].filter(n => !this.isBlocked(n))
      if (!names.length) {
        this.progressText = $tr('所选均被禁止下载（.chk）')
        setTimeout(() => { this.progressText = '' }, 2500)
        return
      }
      const rd = this.remotePath
      const dir = this.localPath
      this.busy = true; this.progress = 0
      const gp = useProgressStore()
      gp.start($tr('下载 {0} 个文件…', { 0: names.length }))
      let done = 0, ok = 0
      let lastErr = ''
      for (const name of names) {
        const ent = this.remoteEntries.find(x => x.name === name)
        const p = posixJoin(rd, name)
        this.progressText = $tr('下载中 {0}（{1}/{2}）', { 0: name, 1: done + 1, 2: names.length })
        gp.step(done, names.length, this.progressText)
        try {
          let r
          if (ent && ent.is_dir) {
            r = await fetch(`${BACKEND}/api/ftp/pull-dir`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: this.remoteStore.sessionId, remote_dir: p, local_dir: dir }) })
          } else {
            r = await fetch(`${BACKEND}/api/ftp/pull`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: this.remoteStore.sessionId, remote_path: p, local_dir: dir }) })
          }
          const d = await r.json().catch(() => ({}))
          if (r.ok) ok++
          else lastErr = d.detail || `HTTP ${r.status}`
        } catch (e) { lastErr = e.message || $tr('网络错误') }
        done++; this.progress = Math.round((done / names.length) * 100)
        gp.step(done, names.length, this.progressText)
      }
      this.progressText = lastErr && ok < names.length ? $tr('下载：成功 {0}/{1}（{2}）', { 0: ok, 1: names.length, 2: lastErr }) : $tr('下载完成：成功 {0}/{1}', { 0: ok, 1: names.length })
      gp.finish(this.progressText)
      this.busy = false
      this.clearSel(); this.loadLocal(); this.loadRemote()
      setTimeout(() => { this.progress = 0; this.progressText = '' }, 2500)
    }
  }
}
</script>

<style scoped>
/* FTP 面板：深色底 + 硬朗立体边（与终端/日志一致的直角风格） */
.ftp-btn {
  background: #3a3f45;
  border: 1px solid #23272b;
  color: #d3d7dc;
  border-radius: 0;
  font-size: 11.5px;
  height: 22px;
  padding: 0 8px;
  cursor: pointer;
  box-shadow: inset 1px 1px 0 #545a61, inset -1px -1px 0 #16181b;
}
.ftp-btn:disabled { opacity:.45; cursor:not-allowed; }
.ftp-btn:active:not(:disabled) { box-shadow: inset 1px 1px 0 #16181b, inset -1px -1px 0 #545a61; padding-top:1px; }
.ftp-btn.main { background:#454b52; color:#e6eaee; font-weight:700; }
.ftp-input {
  flex:1; min-width:0; background:#16181b; border:1px solid #23272b; color:#d3d7dc;
  border-radius:0; height:22px; padding:0 6px; font-size:11.5px; outline:none;
  box-shadow: inset 1px 1px 0 #0b0d0f;
}
.ftp-row { display:flex; align-items:center; gap:6px; padding:2px 6px; cursor:pointer; border-radius:0; white-space:nowrap; font-size:11.5px; }
.ftp-row:hover { background:#41464c; }
.ftp-row.selected { background:#2c4f8a; color:#fff; }
.ftp-close { background:transparent; border:1px solid transparent; color:#ccc; cursor:pointer; font-size:14px; padding:0 5px; border-radius:0; }
.ftp-close:hover { background:#e81123; border-color:#7a0a13; color:#fff; }
</style>

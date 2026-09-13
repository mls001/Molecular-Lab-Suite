<template>
  <div class="wf-src">
    <div class="rp-row">
      <span class="label">{{ $t('波函数来源') }}</span>
      <span class="flex-center" style="gap:4px;">
        <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="choose">{{ $t('选择…') }}</button>
        <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="auto">{{ $t('自动') }}</button>
      </span>
    </div>
    <div class="rp-hint" style="word-break:break-all;">{{ label }}</div>
    <template v-if="blocked">
      <div class="rp-hint" style="color:var(--c-danger);">{{ info.hint }}</div>
      <div v-if="info.chk" class="rp-hint">{{ $t('发现同名 .chk：{0}', { 0: baseName(info.chk) }) }}</div>
      <!-- 名字对不上但同目录/附近确实有波函数文件时，列出来给用户点选（不自动替换，避免用错分子） -->
      <div v-if="others.length" class="rp-hint">{{ $t('附近的其它波函数文件（点一下就用它）：') }}</div>
      <div v-for="c in others" :key="c" class="wf-pick" @click="useFile(c)">{{ baseName(c) }}</div>
      <div class="flex" style="gap:6px;">
        <button v-if="info.formchk" class="btn" style="flex:1;height:22px;font-size:11px;"
                @click="runFormchk" :disabled="busy">
          {{ busy ? $t('转换中…') : $t('用 formchk 转 .fchk') }}
        </button>
        <button class="btn" style="flex:1;height:22px;font-size:11px;" @click="$emit('force-try')">{{ $t('仍然尝试') }}</button>
      </div>
    </template>
  </div>
</template>

<script>
import { pickFile } from '@/api/dialog'
import { findRemoteWavefn, downloadRemote, posixJoin, stemOf } from '@/api/remoteSync'

// 波函数来源（.fch/.fchk/.wfn/.wfx/.molden…）的统一处理：
// 预检 LOG 能否直接给 Multiwfn 读 → 自动找同名波函数文件 → 远程按需下载 → formchk 转换。
// 三个用到 Multiwfn 的页面（轨道图 / NTO / 空穴-电子）共用这一份逻辑。
export default {
  name: 'WavefnSource',
  props: {
    sourcePath: { type: String, default: '' },      // 当前 LOG/输出文件绝对路径
    remoteCache: { type: Boolean, default: false },  // 数据来自远程缓存（需要时去远程取 .fchk）
    sessionId: { type: String, default: '' },
    remoteFolder: { type: String, default: '' },
    extraDir: { type: String, default: '' },         // 额外的搜索目录（目标目录），同名 .fchk 常放在别处
    modelValue: { type: String, default: '' }        // v-model: 选定的波函数文件
  },
  emits: ['update:modelValue', 'blocked', 'force-try', 'log'],
  data() {
    return { info: null, busy: false, triedRemote: false }
  },
  computed: {
    blocked() { return !!(this.info && this.info.ok === false && !this.modelValue) },
    // 候选里排除了自动选中的那个（同名），剩下的按名字给用户点选
    others() {
      const c = (this.info && this.info.companions) || []
      return c.filter((p) => p !== this.info.picked).slice(0, 6)
    },
    label() {
      const p = this.modelValue || this.sourcePath
      return p ? this.baseName(p) : this.$t('未选择')
    }
  },
  watch: {
    // flush:'post' —— 必须等父级这一轮渲染把新的 source-path / v-model 都传下来后再预检；
    // 否则会拿着上一个文件的波函数路径去预检（切文件时波函数不跟着换的根因）
    sourcePath: {
      flush: 'post',
      handler() {
        this.triedRemote = false
        this.info = null
        this.reload()
      }
    },
    blocked(val) { this.$emit('blocked', val) }
  },
  methods: {
    say(text, color = '#87d2ff') { this.$emit('log', { text, color }) },
    baseName(p) { return String(p || '').split(/[\\/]/).pop() },
    async extGet(path, params = {}) {
      const base = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
      const qs = new URLSearchParams(params).toString()
      const resp = await fetch(`${base}${path}${qs ? '?' + qs : ''}`)
      const text = await resp.text()
      let data = {}
      if (text) { try { data = JSON.parse(text) } catch (e) { data = { detail: text.slice(0, 300) } } }
      return { ok: resp.ok, data }
    },
    /** 预检指定文件（不给就用当前 sourcePath）；同名波函数文件会在同目录/目标目录/附近子目录里找 */
    async reload(target = '') {
      const path = target || this.modelValue || this.sourcePath
      if (!path) { this.info = null; return null }
      const { ok, data } = await this.extGet('/api/ext/wavefn', { path, dir: this.extraDir || '' })
      if (!ok) { this.info = null; return null }
      this.info = data
      if (!target && !this.modelValue && data.picked) {
        this.$emit('update:modelValue', data.picked)
        this.say(this.$t('已自动使用波函数文件: {0}', { 0: data.picked }))
      }
      return this.info
    },
    async choose() {
      try {
        const p = await pickFile(this.$t('选择波函数 / LOG 文件'),
          ['fch', 'fchk', 'wfn', 'wfx', 'molden', '47', 'mwfn', 'gbw', 'log', 'out'],
          this.sourcePath || '')
        if (!p) return
        this.$emit('update:modelValue', p)
        await this.reload(p)
        this.say(this.$t('波函数来源: {0}', { 0: p }))
      } catch (e) {
        this.$emit('log', { text: this.$t('选择文件失败: {0}', { 0: e.message }), color: '#ff6b6b' })
      }
    },
    async auto() {
      this.$emit('update:modelValue', '')
      this.triedRemote = false
      this.info = null
      await this.reload()
    },
    /** 点选候选文件（名字与 LOG 不一致的那些，需要用户明确指定） */
    async useFile(p) {
      this.$emit('update:modelValue', p)
      await this.reload(p)
      this.say(this.$t('波函数来源: {0}', { 0: p }))
    },
    /** 远程模式：LOG 读不出波函数时，把远程同名波函数文件下载到本地缓存 */
    async ensureRemote() {
      if (!this.remoteCache || !this.remoteFolder || !this.sessionId) return ''
      if (this.triedRemote || this.modelValue) return ''
      const name = this.baseName(this.sourcePath)
      if (!name) return ''
      let names = []
      try {
        names = await findRemoteWavefn(this.sessionId, this.remoteFolder, stemOf(name))
      } catch (e) {
        this.$emit('log', { text: this.$t('读取远程目录失败: {0}', { 0: e.message }), color: '#ff6b6b' })
        return ''
      }
      this.triedRemote = true
      if (!names.length) {
        this.$emit('log', { text: this.$t('远程目录里没有 {0} 的同名波函数文件（.fchk/.wfn/.wfx/.gbw 等）',
          { 0: stemOf(name) }), color: '#ffa500' })
        return ''
      }
      this.say(this.$t('远程找到同名波函数文件：{0}，正在下载…', { 0: names.join('、') }))
      try {
        const results = await downloadRemote(this.sessionId, names.map((n) => posixJoin(this.remoteFolder, n)))
        const good = results.find((r) => r.status === 'success' && r.cache_path)
        if (!good) {
          this.$emit('log', { text: this.$t('远程波函数文件下载失败'), color: '#ff6b6b' })
          return ''
        }
        this.say(this.$t('已下载到缓存: {0}', { 0: good.cache_path }), '#7cfc00')
        this.$emit('update:modelValue', good.cache_path)
        await this.reload(good.cache_path)
        return good.cache_path
      } catch (e) {
        this.$emit('log', { text: this.$t('远程波函数文件下载失败: {0}', { 0: e.message }), color: '#ff6b6b' })
        return ''
      }
    },
    /** 用 Gaussian 的 formchk 把同名 .chk 转成 .fchk */
    async runFormchk() {
      if (!this.info || !this.info.chk) return
      this.busy = true
      this.say(this.$t('调用 formchk 转换 {0}…', { 0: this.baseName(this.info.chk) }))
      const base = `http://${__BACKEND_HOST__}:${__BACKEND_PORT__}`
      let data = {}
      let ok = false
      try {
        const resp = await fetch(`${base}/api/ext/formchk`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chk: this.info.chk, formchk_exe: this.info.formchk || '' })
        })
        data = await resp.json()
        ok = resp.ok
      } catch (e) {
        data = { detail: e.message }
      }
      this.busy = false
      if (data && data.log) String(data.log).split('\n').forEach((l) => this.$emit('log', { text: l, color: '#9aa3ad' }))
      if (!ok || !data.ok) {
        this.$emit('log', { text: this.$t('formchk 转换失败: {0}', { 0: data.detail || data.error || '' }), color: '#ff6b6b' })
        return
      }
      this.say(this.$t('已生成 {0}', { 0: data.fchk }), '#7cfc00')
      this.$emit('update:modelValue', data.fchk)
      await this.reload(data.fchk)
    }
  }
}
</script>

<style scoped>
.wf-pick {
  font-size: 11px;
  padding: 1px 4px;
  color: var(--c-accent);
  cursor: pointer;
  word-break: break-all;
}
.wf-pick:hover { background: var(--c-hover); text-decoration: underline; }
</style>

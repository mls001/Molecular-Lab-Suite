<template>
  <div v-if="visible" class="xt-mask" @click.self="$emit('update:visible', false)">
    <div class="xt-win">
      <div class="mls-panel-head">
        <span>{{ $t('外部程序目录') }}</span>
        <button class="log-panel-close" :title="$t('关闭')" @click="$emit('update:visible', false)">×</button>
      </div>

      <div class="xt-body">
        <div v-for="k in kinds" :key="k.id" class="rp-sec">
          <div class="rp-row">
            <span class="label">{{ k.label }}</span>
            <span class="flex-center" style="gap:4px;">
              <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="choose(k.id)">{{ $t('选择目录…') }}</button>
              <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="check(k.id)">{{ $t('检测') }}</button>
              <button class="btn" style="height:22px;padding:0 8px;font-size:11px;" @click="clear(k.id)">{{ $t('清除') }}</button>
              <button v-if="k.id === 'multiwfn'" class="btn" style="height:22px;padding:0 8px;font-size:11px;"
                      @click="showCitation">{{ $t('引用说明') }}</button>
            </span>
          </div>
          <input class="control rp-full" v-model="dirs[k.id]" :placeholder="k.placeholder" @change="persist" />
          <div class="rp-hint" :style="{ color: status[k.id] && status[k.id].ok ? 'var(--c-green)' : 'var(--c-text-2)' }">
            {{ statusText(k.id) }}
          </div>
          <div v-if="resolvedPath(k.id)" class="rp-hint" style="color:var(--c-green);word-break:break-all;">
            {{ $t('实际使用：{0}', { 0: resolvedPath(k.id) }) }}
          </div>
          <div v-else class="rp-hint" style="color:var(--c-warning);">
            {{ $t('没检测到 {0}：请填上面的目录，或把程序所在目录加入系统环境变量 PATH', { 0: k.label }) }}
          </div>
        </div>
        <div class="rp-hint" style="margin-top:6px;">{{ $t('配置后可在后续版本里直接用 Multiwfn / VMD 做分析与绘图') }}</div>
      </div>

      <div class="xt-foot">
        <button class="btn btn-primary" style="height:26px;padding:0 14px;font-size:12px;" @click="done">{{ $t('完成') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import { pickDirectory } from '@/api/dialog'
import { useExternalToolsStore } from '@/stores/externalTools'
import { useMultiwfnCitationStore } from '@/stores/multiwfnCitation'
import { t as $tr } from '@/i18n'

export default {
  name: 'ExternalToolsModal',
  props: {
    visible: { type: Boolean, default: false }
  },
  emits: ['update:visible'],
  data() {
    return {
      kinds: [
        { id: 'multiwfn', label: 'Multiwfn', placeholder: this.$t('Multiwfn 所在目录（含 Multiwfn.exe）') },
        { id: 'vmd', label: 'VMD', placeholder: this.$t('VMD 安装目录（含 vmd.exe）') }
      ],
      dirs: { multiwfn: '', vmd: '' },
      status: {},
      backendUrl: ''
    }
  },
  async mounted() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try { this.backendUrl = await window.electronAPI.getBackendUrl() } catch (e) { /* ignore */ }
    }
    if (!this.backendUrl) this.backendUrl = 'http://127.0.0.1:8002'
    const store = useExternalToolsStore()
    this.dirs = { multiwfn: store.multiwfnDir, vmd: store.vmdDir }
    await store.detect()
    for (const k of this.kinds) if (this.dirs[k.id]) this.check(k.id)
  },
  methods: {
    persist() {
      const store = useExternalToolsStore()
      store.save({ multiwfnDir: this.dirs.multiwfn, vmdDir: this.dirs.vmd })
      store.detect()
    },
    resolvedPath(kind) {
      const s = useExternalToolsStore()
      return kind === 'vmd' ? s.vmdPath : s.multiwfnPath
    },
    // 再显示一次 Multiwfn 引用说明（勾过「不再提示」后也能找回来）
    async showCitation() {
      const store = useMultiwfnCitationStore()
      store.reset()
      store.payload = null
      await store.load('multiwfn')
      store.visible = true
    },
    async choose(kind) {
      let p
      try {
        p = await pickDirectory(this.$t('选择 {0} 目录', { 0: kind === 'vmd' ? 'VMD' : 'Multiwfn' }), this.dirs[kind])
      } catch (e) {
        this.status[kind] = { ok: false, text: e.message }
        return
      }
      if (!p) return
      this.dirs[kind] = p
      this.persist()
      this.check(kind)
    },
    clear(kind) {
      this.dirs[kind] = ''
      this.status[kind] = null
      this.persist()
    },
    async check(kind) {
      const dir = (this.dirs[kind] || '').trim()
      if (!dir) {
        this.status[kind] = { ok: false, text: $tr('未设置目录') }
        return
      }
      try {
        const resp = await fetch(`${this.backendUrl}/api/tools/check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dir, kind })
        })
        const data = await resp.json()
        if (!resp.ok) {
          this.status[kind] = { ok: false, text: data.detail || $tr('检测失败') }
          return
        }
        this.status[kind] = data.ok
          ? { ok: true, text: $tr('已找到：{0}', { 0: data.found.map(f => f.name).join('、') }), found: data.found }
          : { ok: false, text: $tr('该目录里没找到 {0} 的可执行文件', { 0: kind === 'vmd' ? 'VMD' : 'Multiwfn' }) }
        useExternalToolsStore().detect()
      } catch (e) {
        this.status[kind] = { ok: false, text: e.message }
      }
    },
    statusText(kind) {
      const s = this.status[kind]
      if (!s) return this.dirs[kind] ? this.$t('未检测') : ''
      return s.text
    },
    done() {
      this.persist()
      this.$emit('update:visible', false)
    }
  }
}
</script>

<style scoped>
.xt-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 400;
}
.xt-win {
  width: 460px;
  max-width: 92vw;
  background: var(--c-main);
  border: 1px solid var(--c-border-strong);
  box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
}
.xt-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.xt-foot {
  display: flex;
  justify-content: flex-end;
  padding: 8px 12px;
  border-top: 1px solid var(--c-border-soft);
}
</style>

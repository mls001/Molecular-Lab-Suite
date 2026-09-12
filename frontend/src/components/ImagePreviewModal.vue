<template>
  <!-- 图内预览弹窗：替代 window.open（Electron 里会被拦截），可直接保存 PNG -->
  <div v-if="visible" class="ip-mask" @click.self="$emit('update:visible', false)">
    <div class="ip-win">
      <div class="mls-panel-head">
        <span>{{ title || $t('图片预览') }}</span>
        <button class="log-panel-close" :title="$t('关闭')" @click="$emit('update:visible', false)">×</button>
      </div>
      <div class="ip-body">
        <img v-if="src" :src="src" class="ip-img" :style="{ maxWidth: zoom + '%' }" />
        <div v-else class="ide-empty">{{ $t('没有可显示的图片') }}</div>
      </div>
      <div class="ip-foot">
        <span class="rp-hint" style="flex:1;">{{ hint }}</span>
        <button class="btn" style="height:26px;padding:0 10px;font-size:12px;" @click="zoom = Math.max(30, zoom - 20)">－</button>
        <button class="btn" style="height:26px;padding:0 10px;font-size:12px;" @click="zoom = Math.min(300, zoom + 20)">＋</button>
        <button class="btn btn-primary" style="height:26px;padding:0 12px;font-size:12px;" @click="save" :disabled="!src || saving">
          {{ saving ? $t('保存中…') : $t('保存 PNG') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { pickDirectory } from '@/api/dialog'
import { t as $tr } from '@/i18n'

export default {
  name: 'ImagePreviewModal',
  props: {
    visible: { type: Boolean, default: false },
    src: { type: String, default: '' },
    title: { type: String, default: '' },
    filename: { type: String, default: 'figure.png' },
    initialDir: { type: String, default: '' }
  },
  emits: ['update:visible'],
  data() {
    return { zoom: 100, saving: false, backendUrl: '', hint: '' }
  },
  async mounted() {
    if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
      try { this.backendUrl = await window.electronAPI.getBackendUrl() } catch (e) { /* ignore */ }
    }
    if (!this.backendUrl) this.backendUrl = 'http://127.0.0.1:8002'
  },
  methods: {
    async save() {
      if (!this.src) return
      let dir
      try {
        dir = await pickDirectory($tr('选择图片保存目录'), this.initialDir || '')
      } catch (e) {
        this.hint = e.message
        return
      }
      if (!dir) return
      this.saving = true
      try {
        const resp = await fetch(`${this.backendUrl}/api/mol/save-file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder: dir, filename: this.filename, content_base64: this.src })
        })
        const data = await resp.json()
        this.hint = resp.ok ? $tr('已保存 {0}', { 0: data.path }) : (data.detail || $tr('保存失败'))
      } catch (e) {
        this.hint = e.message
      }
      this.saving = false
    }
  }
}
</script>

<style scoped>
.ip-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
}
.ip-win {
  width: min(1100px, 92vw);
  height: min(85vh, 1200px);
  display: flex;
  flex-direction: column;
  background: var(--c-main);
  border: 1px solid var(--c-border-strong);
  box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.45);
}
.ip-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #ffffff;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 8px;
}
.ip-img { display: block; height: auto; }
.ip-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-top: 1px solid var(--c-border-soft);
}
</style>

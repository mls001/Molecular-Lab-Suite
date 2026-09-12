<template>
  <div v-if="visible" class="cite-mask">
    <div class="cite-win">
      <div class="cite-head">
        <span class="cite-title">{{ $t('使用 Multiwfn 必须在文章正文中引用其原文') }}</span>
      </div>

      <div class="cite-body">
        <div class="cite-must">
          <div class="cite-must-title">{{ $t('必须引用的 Multiwfn 原文（缺一不可）') }}</div>
          <div v-for="(m, i) in mustCite" :key="'m' + i" class="cite-ref">{{ m }}</div>
          <template v-if="extraCite.length">
            <div class="cite-must-title" style="margin-top:6px;">{{ $t('本功能还要求引用') }}</div>
            <div v-for="(m, i) in extraCite" :key="'e' + i" class="cite-ref">{{ m }}</div>
          </template>
        </div>

        <pre class="cite-text">{{ body }}</pre>

        <div v-if="pdf" class="cite-links">
          <span class="cite-hint">{{ $t('完整引用说明见程序包中的文档：') }}</span>
          <span class="cite-path">{{ pdf }}</span>
        </div>
        <div class="cite-links">
          <a v-for="(l, i) in links" :key="'l' + i" :href="l.url" target="_blank" class="cite-link">{{ l.label }}</a>
        </div>
      </div>

      <div class="cite-foot">
        <label class="cite-check">
          <input type="checkbox" v-model="remember" />
          <span>{{ $t('我将时刻牢记，不再提示') }}</span>
        </label>
        <button class="btn btn-primary cite-ok" @click="ok">{{ $t('我已阅读并接受，继续使用 Multiwfn') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import { useMultiwfnCitationStore } from '@/stores/multiwfnCitation'

export default {
  name: 'MultiwfnCitationModal',
  data() {
    return { remember: false }
  },
  computed: {
    store() { return useMultiwfnCitationStore() },
    visible() { return this.store.visible },
    mustCite() { return this.store.mustCite },
    extraCite() { return this.store.extraCite },
    body() { return this.store.body },
    links() { return this.store.links },
    pdf() { return this.store.pdf }
  },
  methods: {
    ok() {
      this.store.confirm(this.remember)
    }
  }
}
</script>

<style scoped>
.cite-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 900;
}
.cite-win {
  width: 92vw;
  height: 92vh;
  background: var(--c-main);
  border: 1px solid var(--c-border-strong);
  box-shadow: 3px 3px 16px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}
.cite-head {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--c-border-strong);
  background: var(--c-panel);
}
.cite-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-danger);
}
.cite-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.cite-must {
  border: 1px solid var(--c-danger);
  background: var(--c-panel);
  padding: 8px 10px;
}
.cite-must-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--c-danger);
  margin-bottom: 4px;
}
.cite-ref {
  font-family: Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.6;
  word-break: break-all;
}
.cite-text {
  margin: 0;
  font-family: Consolas, 'Microsoft YaHei', monospace;
  font-size: 12.5px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--c-text);
}
.cite-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  font-size: 12px;
}
.cite-link { color: var(--c-accent); text-decoration: underline; }
.cite-hint { color: var(--c-text-2); }
.cite-path { font-family: Consolas, monospace; word-break: break-all; }
.cite-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-top: 1px solid var(--c-border-strong);
  background: var(--c-panel);
}
.cite-check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.cite-ok { height: 30px; padding: 0 18px; font-size: 13px; }
</style>

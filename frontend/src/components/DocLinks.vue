<template>
  <!-- 页面下方的绘图方法参考链接（点击由系统浏览器打开） -->
  <div v-if="links.length" class="doc-links">
    <span class="doc-title">{{ $t('绘图方法参考（Sobereva 博客）') }}</span>
    <a v-for="(l, i) in links" :key="i" :href="l.url" target="_blank" class="doc-link">{{ l.label }}</a>
  </div>
</template>

<script>
export default {
  name: 'DocLinks',
  props: {
    links: { type: Array, default: () => [] }     // [{ label, url }]
  }
}
</script>

<style scoped>
.doc-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 4px 8px 0 8px;
  font-size: 12px;
  flex-shrink: 0;
}
.doc-title { color: var(--c-text-3); }
.doc-link { color: var(--c-accent); text-decoration: underline; }
.doc-link:hover { color: var(--c-accent-hover, var(--c-accent)); }
</style>

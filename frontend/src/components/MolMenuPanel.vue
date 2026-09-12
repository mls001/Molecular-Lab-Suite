<template>
  <!-- 统一的浮层菜单面板（fixed 定位 + 统一样式），各处菜单共用，避免重复样式/定位逻辑 -->
  <div class="mv-menu-panel" :style="{ left: left + 'px', top: top + 'px', minWidth: minWidth + 'px' }"
       @click.stop>
    <slot />
  </div>
</template>

<script>
export default {
  name: 'MolMenuPanel',
  props: {
    left: { type: Number, default: 40 },
    top: { type: Number, default: 60 },
    minWidth: { type: Number, default: 200 }
  }
}
</script>

<style scoped>
.mv-menu-panel {
  position: fixed;
  z-index: 200;
  max-height: 70vh;
  overflow-y: auto;
  background: var(--c-elev);
  border: 1px solid var(--c-border-strong);
  box-shadow: 2px 2px 6px rgba(0, 0, 0, 0.35);
  padding: 2px 0;
}
</style>

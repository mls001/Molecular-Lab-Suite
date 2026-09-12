<template>
  <!-- 统一图标集（MolView 风格线性图标）；所有工具栏共用，避免重复内联 SVG -->
  <svg :width="size" :height="size" viewBox="0 0 16 16" :class="{ 'mol-icon-filled': !!def.fill }"
       fill="none" stroke="currentColor" :stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
    <path v-for="(d, i) in def.d" :key="i" :d="d" :fill="def.fill ? 'currentColor' : 'none'"
          :stroke="def.fill ? 'none' : 'currentColor'" />
  </svg>
</template>

<script>
// 每个图标 = 一组 16×16 的 path；fill:true 表示实心（如选择箭头）
const ICONS = {
  select: { fill: true, d: ['M3 1.5 L3 12.5 L6.2 9.6 L8.4 14.2 L10.4 13.2 L8.3 8.7 L12.8 8.3 Z'] },
  bond1: { d: ['M3.2 12.8 L12.8 3.2'] },
  bond2: { d: ['M2.6 12.4 L12.4 2.6', 'M4.4 14.2 L14.2 4.4'] },
  bond3: { d: ['M2.2 11.6 L11.6 2.2', 'M3.4 13.4 L13.4 3.4', 'M4.6 15.2 L15.2 4.6'] },
  ring6: { d: ['M8 1.6 L13.6 4.8 L13.6 11.2 L8 14.4 L2.4 11.2 L2.4 4.8 Z'] },
  ring5: { d: ['M8 1.6 L14.2 6.2 L11.8 13.6 L4.2 13.6 L1.8 6.2 Z'] },
  ring3: { d: ['M8 2 L14.4 13.4 L1.6 13.4 Z'] },
  chain: { d: ['M1.6 12.4 L6 4.4 L10.4 12.4 L14.4 5.2'] },
  erase: { d: ['M3 11.4 L8.6 5.8 L12.6 9.8 L7 15.4', 'M2 15.4 L15 15.4'] },
  chargePlus: { d: ['M8 3.2 L8 12.8', 'M3.2 8 L12.8 8'] },
  chargeMinus: { d: ['M3.2 8 L12.8 8'] },
  undo: { d: ['M3 8.4 A5 5 0 1 1 8 13.4', 'M1 6 L3 8.6', 'M5.4 6 L3 8.6'] },
  redo: { d: ['M13 8.4 A5 5 0 1 0 8 13.4', 'M15 6 L13 8.6', 'M10.6 6 L13 8.6'] },
  trash: { d: ['M2.4 4.2 L13.6 4.2', 'M6 4.2 L6 2.4 L10 2.4 L10 4.2', 'M3.6 4.2 L4.6 14 L11.4 14 L12.4 4.2'] },
  clean: { d: ['M2 14 L9.5 6.5', 'M11.6 2 L12.5 3.9 L14.4 4.8 L12.5 5.7 L11.6 7.6 L10.7 5.7 L8.8 4.8 L10.7 3.9 Z'] },
  zoomIn: { d: ['M7 2.4 A4.6 4.6 0 1 0 7 11.6 A4.6 4.6 0 1 0 7 2.4', 'M10.6 10.6 L14.4 14.4', 'M4.6 7 L9.4 7', 'M7 4.6 L7 9.4'] },
  zoomOut: { d: ['M7 2.4 A4.6 4.6 0 1 0 7 11.6 A4.6 4.6 0 1 0 7 2.4', 'M10.6 10.6 L14.4 14.4', 'M4.6 7 L9.4 7'] },
  fit: { d: ['M2 6 L2 2 L6 2', 'M10 2 L14 2 L14 6', 'M14 10 L14 14 L10 14', 'M6 14 L2 14 L2 10'] },
  download: { d: ['M8 2 L8 10.4', 'M4.6 7.2 L8 10.8 L11.4 7.2', 'M2.4 13.6 L13.6 13.6'] }
}

export default {
  name: 'MolIcon',
  props: {
    name: { type: String, required: true },
    size: { type: [Number, String], default: 15 }
  },
  computed: {
    def() { return ICONS[this.name] || { d: [] } }
  }
}
</script>

<style scoped>
.mol-icon-filled { stroke: none; }
</style>

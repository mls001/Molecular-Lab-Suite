<template>
  <!-- 中间主窗口的空数据提示：文件里没有当前页面需要的信息时显示 -->
  <div class="empty-notice">
    <div class="empty-notice-main">{{ text }}</div>
    <div v-if="hint" class="empty-notice-hint">{{ hint }}</div>
  </div>
</template>

<script>
export default {
  name: 'EmptyNotice',
  props: {
    text: { type: String, required: true },
    hint: { type: String, default: '' }
  }
}
</script>

<style scoped>
.empty-notice {
  height: 100%;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  text-align: center;
  user-select: none;
}
.empty-notice-main {
  font-size: 14px;
  font-weight: 700;
  color: var(--c-text-2);
}
.empty-notice-hint {
  font-size: 12px;
  color: var(--c-text-3);
  max-width: 640px;
  line-height: 1.6;
  word-break: break-word;
}
</style>

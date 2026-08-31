<template>
  <div id="app" style="display:flex;flex-direction:column;height:100vh;overflow:hidden;">
    <header style="background:#001529;padding:12px 24px;display:flex;align-items:center;gap:20px;flex-shrink:0;">
      <h1 style="color:white;font-size:20px;margin:0;">Molecular Lab Suite, MLS V26.9</h1>
      <nav style="display:flex;gap:12px;flex-wrap:wrap;">
        <router-link to="/" style="color:#aaa;text-decoration:none;font-size:14px;">首页</router-link>
        <!-- <router-link to="/optimize" style="color:#aaa;text-decoration:none;font-size:14px;">分子优化</router-link> -->
        <router-link to="/gjf-modify" style="color:#aaa;text-decoration:none;font-size:14px;">修改GJF</router-link>
        <router-link to="/log-to-gjf" style="color:#aaa;text-decoration:none;font-size:14px;">LOG→GJF</router-link>
        <router-link to="/scan-extract" style="color:#aaa;text-decoration:none;font-size:14px;">提取扫描</router-link>
        <router-link to="/orbital" style="color:#aaa;text-decoration:none;font-size:14px;">轨道能量</router-link>
        <router-link to="/td" style="color:#aaa;text-decoration:none;font-size:14px;">TD信息</router-link>
        <router-link to="/soc" style="color:#aaa;text-decoration:none;font-size:14px;">SOC数据</router-link>
        <router-link to="/reorg" style="color:#aaa;text-decoration:none;font-size:14px;">重组能</router-link>
      </nav>
    </header>
    <main style="flex:1;overflow:hidden;padding:20px;">
      <router-view />
    </main>
  </div>
</template>

<script>
export default { name: 'App' }
</script>

<style>
/* ===== 全局重置 ===== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Segoe UI', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
  background: #f5f5f5;
  height: 100vh;
  overflow: hidden;
}
.router-link-active {
  color: white !important;
  font-weight: bold;
}

/* ===== 控件系统（供所有组件复用） ===== */

/* --- 基础输入控件 --- */
.control {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 0 8px;
  font-size: 13px;
  box-sizing: border-box;
  background: white;
  color: #333;
  outline: none;
  transition: border-color 0.2s;
}
.control:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}
.control:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

/* --- 高度等级 --- */
.h-sm { height: 24px; }
.h-md { height: 28px; }
.h-lg { height: 32px; }

/* --- 宽度等级 --- */
.w-xs { width: 50px; }
.w-sm { width: 70px; }
.w-md { width: 100px; }
.w-lg { width: 140px; }
.w-xl { width: 200px; }
.w-2xl { width: 260px; }
.w-3xl { width: 360px; }
.w-full { width: 100%; }

/* --- 只读预览框 --- */
.preview {
  background: #f5f5f5;
  color: #666;
  cursor: default;
}

/* --- 标签 --- */
.label {
  font-weight: 600;
  font-size: 13px;
  color: #333;
  white-space: nowrap;
}

/* --- 按钮 --- */
.btn {
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  box-sizing: border-box;
  transition: background 0.2s, opacity 0.2s;
  padding: 0 14px;
  height: 28px; /* 默认高度，可被 h-* 覆盖 */
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-primary {
  background: #1890ff;
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}
.btn-success {
  background: #52c41a;
  color: white;
}
.btn-success:hover:not(:disabled) {
  background: #73d13d;
}
.btn-warning {
  background: #faad14;
  color: white;
}
.btn-warning:hover:not(:disabled) {
  background: #ffc53d;
}
.btn-danger {
  background: #ff4d4f;
  color: white;
}
.btn-danger:hover:not(:disabled) {
  background: #ff7875;
}

/* --- 选择框 --- */
select.control {
  appearance: auto;
  padding-right: 24px;
}

/* --- 文本框 --- */
textarea.control {
  padding: 8px;
  resize: vertical;
  font-family: monospace;
  line-height: 1.5;
}

/* --- Flex 工具类 --- */
.flex { display: flex; }
.flex-col { display: flex; flex-direction: column; }
.flex-center { display: flex; align-items: center; }
.flex-1 { flex: 1; }
.flex-shrink-0 { flex-shrink: 0; }
.min-h-0 { min-height: 0; }
.h-full { height: 100%; }

/* --- 间距工具类 --- */
.mr-1 { margin-right: 4px; }
.mr-2 { margin-right: 8px; }
.mr-3 { margin-right: 12px; }
.ml-1 { margin-left: 4px; }
.ml-2 { margin-left: 8px; }
.ml-3 { margin-left: 12px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
</style>
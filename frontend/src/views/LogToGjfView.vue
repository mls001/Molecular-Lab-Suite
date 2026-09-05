<template>
  <!-- LOG → GJF（开发中）：三栏 IDE 布局占位 -->
  <div class="flex-col h-full" style="gap:8px;overflow:hidden;">
    <div class="ide">
      <aside class="ide-pane ide-col ide-left">
        <div class="ide-pane-head"><span>文件列表</span></div>
        <div class="ide-pane-body"><div class="ide-empty">暂无文件</div></div>
      </aside>
      <section class="ide-pane ide-col ide-center">
        <div class="ide-pane-head"><span>LOG → GJF</span></div>
        <div class="ide-pane-body" style="display:flex;align-items:center;justify-content:center;">
          <div style="text-align:center;color:var(--c-text-3);">
            <div style="font-size:36px;"></div>
            <div style="margin-top:10px;font-size:15px;">LOG → GJF（开发中）</div>
            <div style="font-size:12px;margin-top:6px;color:var(--c-text-3);">从 Gaussian LOG 提取末帧坐标，生成可提交的 GJF</div>
          </div>
        </div>
      </section>
      <aside class="ide-pane ide-col ide-right">
        <div class="ide-pane-head"><span>参数</span></div>
        <div class="ide-pane-body">
          <div class="ide-group" style="color:var(--c-text-3);font-size:12px;line-height:1.7;">功能建设中，敬请期待。</div>
        </div>
      </aside>
    </div>
  </div>
</template>
<script>export default { name: 'LogToGjfView' }</script>

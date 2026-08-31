<template>
  <div style="text-align:center;padding:60px 20px;">
    <h1 style="font-size:32px;">Molecular Lab Suite, MLS V26.9</h1>
    <p style="color:#666;font-size:16px;margin-top:16px;">
      欢迎使用分子实验室工具包<br>
      请从上方导航栏选择功能
    </p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;max-width:900px;margin:32px auto;">
      <div v-for="item in cards" :key="item.path" @click="$router.push(item.path)" style="background:white;padding:24px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);cursor:pointer;transition:0.3s;"
           @mouseenter="e=>e.target.style.boxShadow='0 4px 16px rgba(0,0,0,0.15)'"
           @mouseleave="e=>e.target.style.boxShadow='0 2px 8px rgba(0,0,0,0.08)'">
        <div style="font-size:28px;">{{ item.icon }}</div>
        <div style="font-weight:600;margin-top:8px;">{{ item.name }}</div>
        <div style="font-size:13px;color:#888;">{{ item.desc }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      cards: [
        // { name: '分子力场优化', desc: 'MMFF94/UFF → GJF', icon: '', path: '/optimize' },
        { name: '修改GJF参数', desc: '批量修改Gaussian输入', icon: '', path: '/gjf-modify' },
        { name: 'LOG→GJF', desc: '从LOG提取坐标', icon: '', path: '/log-to-gjf' },
        { name: '提取扫描构象', desc: 'ModRedundant扫描', icon: '', path: '/scan-extract' },
        { name: '轨道能量', desc: '批量提取HOMO/LUMO', icon: '', path: '/orbital' },
        { name: 'TD信息', desc: '激发态解析', icon: '', path: '/td' },
        { name: 'SOC数据', desc: 'ORCA SOC矩阵', icon: '', path: '/soc' },
        { name: '重组能计算', desc: '远程提交任务', icon: '', path: '/reorg' },
      ]
    }
  }
}
</script>
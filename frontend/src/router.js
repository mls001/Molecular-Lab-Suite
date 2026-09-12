import { createRouter, createWebHistory } from 'vue-router'
import MoleculeView from './views/MoleculeView.vue'
import InputGenView from './views/InputGenView.vue'
import GjfModifyView from './views/GjfModifyView.vue'
import ScanExtractView from './views/ScanExtractView.vue'
import OrbitalView from './views/OrbitalView.vue'
import TdView from './views/TdView.vue'
import SocView from './views/SocView.vue'
import ReorgView from './views/ReorgView.vue'
import ExcitedAnalysisView from './views/ExcitedAnalysisView.vue'

const routes = [
  // 首页：分子结构（编辑器）
  { path: '/', redirect: '/molecule' },
  { path: '/molecule', component: MoleculeView },
  // 生成输入文件（Gaussian / ORCA）
  { path: '/input-gen', component: InputGenView },
  { path: '/gjf-modify', component: GjfModifyView },
  // LOG → GJF 已并入「修改GJF」页面（页内 GJF/LOG 模式切换），旧路径重定向
  { path: '/log-to-gjf', redirect: '/gjf-modify' },
  { path: '/scan-extract', component: ScanExtractView },
  { path: '/orbital', component: OrbitalView },
  // 电子激发分析：NTO / 空穴-电子（同一视图，两类功能）
  { path: '/nto', component: ExcitedAnalysisView, props: { mode: 'nto' } },
  { path: '/hole-electron', component: ExcitedAnalysisView, props: { mode: 'he' } },
  { path: '/td', component: TdView },
  { path: '/soc', component: SocView },
  // 重组能（计算 + 解析 合并单页）
  { path: '/reorg', component: ReorgView },
  // 兜底：未知路径回到默认页
  { path: '/:pathMatch(.*)*', redirect: '/molecule' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

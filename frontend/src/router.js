import { createRouter, createWebHistory } from 'vue-router'
import GjfModifyView from './views/GjfModifyView.vue'
import ScanExtractView from './views/ScanExtractView.vue'
import OrbitalView from './views/OrbitalView.vue'
import TdView from './views/TdView.vue'
import SocView from './views/SocView.vue'
import ReorgView from './views/ReorgView.vue'

const routes = [
  // 首页已取消：默认进入 修改GJF
  { path: '/', redirect: '/gjf-modify' },
  { path: '/gjf-modify', component: GjfModifyView },
  // LOG → GJF 已并入「修改GJF」页面（页内 GJF/LOG 模式切换），旧路径重定向
  { path: '/log-to-gjf', redirect: '/gjf-modify' },
  { path: '/scan-extract', component: ScanExtractView },
  { path: '/orbital', component: OrbitalView },
  { path: '/td', component: TdView },
  { path: '/soc', component: SocView },
  // 重组能（计算 + 解析 合并单页）
  { path: '/reorg', component: ReorgView },
  // 兜底：未知路径回到默认页
  { path: '/:pathMatch(.*)*', redirect: '/gjf-modify' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

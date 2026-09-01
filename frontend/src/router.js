import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import OptimizeView from './views/OptimizeView.vue'
import GjfModifyView from './views/GjfModifyView.vue'
import LogToGjfView from './views/LogToGjfView.vue'
import ScanExtractView from './views/ScanExtractView.vue'
import OrbitalView from './views/OrbitalView.vue'
import TdView from './views/TdView.vue'
import SocView from './views/SocView.vue'
import ReorgView from './views/ReorgView.vue'
import ReorgExtractView from './views/ReorgExtractView.vue'

const routes = [
  { path: '/', component: Home },
  //{ path: '/optimize', component: OptimizeView },
  { path: '/gjf-modify', component: GjfModifyView },
  { path: '/log-to-gjf', component: LogToGjfView },
  { path: '/scan-extract', component: ScanExtractView },
  { path: '/orbital', component: OrbitalView },
  { path: '/td', component: TdView },
  { path: '/soc', component: SocView },
  { path: '/reorg', component: ReorgView },
  { path: '/reorg-extract', component: ReorgExtractView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
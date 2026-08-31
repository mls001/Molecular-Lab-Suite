import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './assets/style.css'
import LogViewer from './components/LogViewer.vue'

const app = createApp(App)
app.use(router)
app.use(Antd)
app.mount('#app')
app.component('LogViewer', LogViewer)  // 全局注册
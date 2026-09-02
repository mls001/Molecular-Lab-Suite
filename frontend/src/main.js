import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './assets/style.css'
import LogViewer from './components/LogViewer.vue'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd)
app.component('LogViewer', LogViewer)

app.mount('#app')
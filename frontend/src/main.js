import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './assets/style.css'
import LogViewer from './components/LogViewer.vue'
import { initTheme } from './theme/theme'

// 尽早应用已保存的主题，避免首帧闪烁
initTheme()

const app = createApp(App)

// 全局错误捕获：记录组件与钩子上下文，便于定位渲染期异常
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue 错误]', info || '', err)
  const name = (instance && instance.$options && instance.$options.name) || (instance && instance.constructor && instance.constructor.name) || '未知组件'
  console.error('[Vue 错误] 组件:', name)
}

app.use(createPinia())
app.use(router)
app.use(Antd)
app.component('LogViewer', LogViewer)

app.mount('#app')
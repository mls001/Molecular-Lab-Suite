// 轻量 i18n：以「中文原文」作为 key，zh 模式直接返回原文，en 模式查 zh-en.json。
// 这样既有页面可以逐步接入（$t('保存')），也不会因为漏翻而出现空白。
import { ref } from 'vue'
import zhEn from './zh-en.json'

const STORAGE_KEY = 'mls.lang'
export const LANGS = [
  { id: 'zh', label: '中文' },
  { id: 'en', label: 'EN' }
]

// 默认英文（"全英"）；用户手动切换后按 localStorage 记忆
export const lang = ref(localStorage.getItem(STORAGE_KEY) === 'zh' ? 'zh' : 'en')

export function setLang(id) {
  lang.value = id === 'en' ? 'en' : 'zh'
  try {
    localStorage.setItem(STORAGE_KEY, lang.value)
  } catch (e) { /* ignore */ }
  document.documentElement.setAttribute('lang', lang.value === 'en' ? 'en' : 'zh-CN')
}

export function toggleLang() {
  setLang(lang.value === 'en' ? 'zh' : 'en')
  return lang.value
}

// 带占位符的文案：t('已连接 {name}', { name: 'zst106' })；也支持 {0}/{1} 形式
export function t(key, params) {
  let text = key
  if (lang.value === 'en') text = zhEn[key] || key
  if (params) {
    text = text.replace(/\{(\w+)\}/g, (m, k) => (Object.prototype.hasOwnProperty.call(params, k) ? params[k] : m))
  }
  return text
}

export function applyHtmlLang() {
  document.documentElement.setAttribute('lang', lang.value === 'en' ? 'en' : 'zh-CN')
}

export function installI18n(app) {
  app.config.globalProperties.$t = t
  app.config.globalProperties.$toggleLang = toggleLang
  app.mixin({
    computed: {
      // 模板里可用 uiLang === 'en' 做少量语言相关分支
      uiLang() {
        return lang.value
      }
    }
  })
  applyHtmlLang()
}

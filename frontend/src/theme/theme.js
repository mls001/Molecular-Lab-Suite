// 主题管理（亮/暗，仿 PyCharm）。模块化：任何组件 import 本模块即可读写主题。
const THEME_KEY = 'mls-theme'
const THEMES = ['light', 'dark']

export function currentTheme() {
  const saved = localStorage.getItem(THEME_KEY)
  return THEMES.includes(saved) ? saved : 'dark'
}

export function isDarkTheme() {
  return currentTheme() === 'dark'
}

// 应用主题到 <html data-theme="…"> 并持久化；同时广播事件供图表等按需重绘
export function applyTheme(theme) {
  const t = THEMES.includes(theme) ? theme : 'dark'
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem(THEME_KEY, t)
  window.dispatchEvent(new CustomEvent('mls-theme-change', { detail: t }))
  return t
}

export function toggleTheme() {
  return applyTheme(currentTheme() === 'dark' ? 'light' : 'dark')
}

// 启动时尽早调用（main.js 顶部），避免首帧闪烁
export function initTheme() {
  const t = currentTheme()
  document.documentElement.setAttribute('data-theme', t)
  return t
}

// 读取当前主题下的 CSS 变量值（供 ECharts 等非 CSS 场景使用）
export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

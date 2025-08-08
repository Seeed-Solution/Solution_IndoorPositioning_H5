import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import zh from './locales/zh.json'

const messages = {
  en,
  zh
}

// 获取浏览器语言或从localStorage获取保存的语言
function getDefaultLocale() {
  const savedLocale = localStorage.getItem('app-locale')
  if (savedLocale && Object.keys(messages).includes(savedLocale)) {
    return savedLocale
  }
  
  // 默认使用英文
  return 'en'
}

const i18n = createI18n({
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  messages,
  legacy: false // 使用 Composition API 模式
})

export default i18n
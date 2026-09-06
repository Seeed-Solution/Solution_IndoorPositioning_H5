import { createApp } from 'vue'
import './styles/sc-tokens.css'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import notificationService from './services/notificationService.js'

const app = createApp(App)
app.use(router)
app.use(i18n)

// 初始化通知服务的i18n实例
notificationService.setI18n(i18n)

app.mount('#app')

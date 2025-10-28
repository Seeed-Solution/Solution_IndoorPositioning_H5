<template>
  <div class="login-container">
    <div class="language-switcher-top">
      <LanguageSwitcher />
    </div>
    <div class="login-card">
      <div class="login-header">
        <h1>{{ $t('login.title', '室内定位') }}</h1>
        <p class="login-subtitle">{{ $t('login.subtitle', '请输入您的用户名和密码') }}</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">{{ $t('login.username', '用户名') }}</label>
          <input
            id="username"
            type="text"
            v-model="loginForm.username"
            :placeholder="$t('login.usernamePlaceholder', '请输入用户名')"
            required
            :disabled="loading"
          />
        </div>
        
        <div class="form-group">
          <label for="password">{{ $t('login.password', '密码') }}</label>
          <input
            id="password"
            type="password"
            v-model="loginForm.password"
            :placeholder="$t('login.passwordPlaceholder', '请输入密码')"
            required
            :disabled="loading"
          />
        </div>
        
        <div v-if="errorMessage" class="status-display error">
          <i class="fas fa-exclamation-circle"></i>
          {{ errorMessage }}
        </div>
        
        <button type="submit" class="button-primary login-button" :disabled="loading">
          <i v-if="loading" class="fas fa-spinner fa-spin"></i>
          <i v-else class="fas fa-sign-in-alt"></i>
          {{ loading ? $t('login.logging', '登录中...') : $t('login.loginButton', '登录') }}
        </button>
      </form>
      
      <div class="guest-login-section">
        <div class="divider">
          <span>{{ $t('login.or', '或') }}</span>
        </div>
        <button 
          type="button" 
          class="button-secondary guest-login-button" 
          :disabled="loading"
          @click="handleGuestLogin"
        >
          <i v-if="loading" class="fas fa-spinner fa-spin"></i>
          <i v-else class="fas fa-user-friends"></i>
          {{ loading ? $t('login.logging', '登录中...') : $t('login.guestLogin', '访客登录') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import httpClient from '../utils/httpClient.js'
import { API_ENDPOINTS } from '../config/api.js'
import { authService } from '../services/authService.js'

const router = useRouter()
const { t } = useI18n()

const loading = ref(false)
const errorMessage = ref('')

const loginForm = reactive({
  username: '',
  password: ''
})

// MD5加密函数
function md5(str) {
  function md5cycle(x, k) {
    let a = x[0], b = x[1], c = x[2], d = x[3]
    
    a = ff(a, b, c, d, k[0], 7, -680876936)
    d = ff(d, a, b, c, k[1], 12, -389564586)
    c = ff(c, d, a, b, k[2], 17, 606105819)
    b = ff(b, c, d, a, k[3], 22, -1044525330)
    a = ff(a, b, c, d, k[4], 7, -176418897)
    d = ff(d, a, b, c, k[5], 12, 1200080426)
    c = ff(c, d, a, b, k[6], 17, -1473231341)
    b = ff(b, c, d, a, k[7], 22, -45705983)
    a = ff(a, b, c, d, k[8], 7, 1770035416)
    d = ff(d, a, b, c, k[9], 12, -1958414417)
    c = ff(c, d, a, b, k[10], 17, -42063)
    b = ff(b, c, d, a, k[11], 22, -1990404162)
    a = ff(a, b, c, d, k[12], 7, 1804603682)
    d = ff(d, a, b, c, k[13], 12, -40341101)
    c = ff(c, d, a, b, k[14], 17, -1502002290)
    b = ff(b, c, d, a, k[15], 22, 1236535329)
    
    a = gg(a, b, c, d, k[1], 5, -165796510)
    d = gg(d, a, b, c, k[6], 9, -1069501632)
    c = gg(c, d, a, b, k[11], 14, 643717713)
    b = gg(b, c, d, a, k[0], 20, -373897302)
    a = gg(a, b, c, d, k[5], 5, -701558691)
    d = gg(d, a, b, c, k[10], 9, 38016083)
    c = gg(c, d, a, b, k[15], 14, -660478335)
    b = gg(b, c, d, a, k[4], 20, -405537848)
    a = gg(a, b, c, d, k[9], 5, 568446438)
    d = gg(d, a, b, c, k[14], 9, -1019803690)
    c = gg(c, d, a, b, k[3], 14, -187363961)
    b = gg(b, c, d, a, k[8], 20, 1163531501)
    a = gg(a, b, c, d, k[13], 5, -1444681467)
    d = gg(d, a, b, c, k[2], 9, -51403784)
    c = gg(c, d, a, b, k[7], 14, 1735328473)
    b = gg(b, c, d, a, k[12], 20, -1926607734)
    
    a = hh(a, b, c, d, k[5], 4, -378558)
    d = hh(d, a, b, c, k[8], 11, -2022574463)
    c = hh(c, d, a, b, k[11], 16, 1839030562)
    b = hh(b, c, d, a, k[14], 23, -35309556)
    a = hh(a, b, c, d, k[1], 4, -1530992060)
    d = hh(d, a, b, c, k[4], 11, 1272893353)
    c = hh(c, d, a, b, k[7], 16, -155497632)
    b = hh(b, c, d, a, k[10], 23, -1094730640)
    a = hh(a, b, c, d, k[13], 4, 681279174)
    d = hh(d, a, b, c, k[0], 11, -358537222)
    c = hh(c, d, a, b, k[3], 16, -722521979)
    b = hh(b, c, d, a, k[6], 23, 76029189)
    a = hh(a, b, c, d, k[9], 4, -640364487)
    d = hh(d, a, b, c, k[12], 11, -421815835)
    c = hh(c, d, a, b, k[15], 16, 530742520)
    b = hh(b, c, d, a, k[2], 23, -995338651)
    
    a = ii(a, b, c, d, k[0], 6, -198630844)
    d = ii(d, a, b, c, k[7], 10, 1126891415)
    c = ii(c, d, a, b, k[14], 15, -1416354905)
    b = ii(b, c, d, a, k[5], 21, -57434055)
    a = ii(a, b, c, d, k[12], 6, 1700485571)
    d = ii(d, a, b, c, k[3], 10, -1894986606)
    c = ii(c, d, a, b, k[10], 15, -1051523)
    b = ii(b, c, d, a, k[1], 21, -2054922799)
    a = ii(a, b, c, d, k[8], 6, 1873313359)
    d = ii(d, a, b, c, k[15], 10, -30611744)
    c = ii(c, d, a, b, k[6], 15, -1560198380)
    b = ii(b, c, d, a, k[13], 21, 1309151649)
    a = ii(a, b, c, d, k[4], 6, -145523070)
    d = ii(d, a, b, c, k[11], 10, -1120210379)
    c = ii(c, d, a, b, k[2], 15, 718787259)
    b = ii(b, c, d, a, k[9], 21, -343485551)
    
    x[0] = add32(a, x[0])
    x[1] = add32(b, x[1])
    x[2] = add32(c, x[2])
    x[3] = add32(d, x[3])
  }
  
  function cmn(q, a, b, x, s, t) {
    a = add32(add32(a, q), add32(x, t))
    return add32((a << s) | (a >>> (32 - s)), b)
  }
  
  function ff(a, b, c, d, x, s, t) {
    return cmn((b & c) | ((~b) & d), a, b, x, s, t)
  }
  
  function gg(a, b, c, d, x, s, t) {
    return cmn((b & d) | (c & (~d)), a, b, x, s, t)
  }
  
  function hh(a, b, c, d, x, s, t) {
    return cmn(b ^ c ^ d, a, b, x, s, t)
  }
  
  function ii(a, b, c, d, x, s, t) {
    return cmn(c ^ (b | (~d)), a, b, x, s, t)
  }
  
  function md51(s) {
    const n = s.length
    const state = [1732584193, -271733879, -1732584194, 271733878]
    let i
    for (i = 64; i <= s.length; i += 64) {
      md5cycle(state, md5blk(s.substring(i - 64, i)))
    }
    s = s.substring(i - 64)
    const tail = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for (i = 0; i < s.length; i++) tail[i >> 2] |= s.charCodeAt(i) << ((i % 4) << 3)
    tail[i >> 2] |= 0x80 << ((i % 4) << 3)
    if (i > 55) {
      md5cycle(state, tail)
      for (i = 0; i < 16; i++) tail[i] = 0
    }
    tail[14] = n * 8
    md5cycle(state, tail)
    return state
  }
  
  function md5blk(s) {
    const md5blks = []
    for (let i = 0; i < 64; i += 4) {
      md5blks[i >> 2] = s.charCodeAt(i) + (s.charCodeAt(i + 1) << 8) + (s.charCodeAt(i + 2) << 16) + (s.charCodeAt(i + 3) << 24)
    }
    return md5blks
  }
  
  const hex_chr = '0123456789abcdef'.split('')
  
  function rhex(n) {
    let s = ''
    for (let j = 0; j <= 3; j++) s += hex_chr[(n >> (j * 8 + 4)) & 0x0f] + hex_chr[(n >> (j * 8)) & 0x0f]
    return s
  }
  
  function hex(x) {
    for (let i = 0; i < x.length; i++) x[i] = rhex(x[i])
    return x.join('')
  }
  
  function add32(a, b) {
    return (a + b) & 0xffffffff
  }
  
  return hex(md51(str))
}

const handleLogin = async () => {
  errorMessage.value = ''
  
  if (!loginForm.username || !loginForm.password) {
    errorMessage.value = t('login.emptyFields', '请填写用户名和密码')
    return
  }
  
  loading.value = true
  
  try {
    // 计算密码的MD5摘要
    const passwordMd5 = md5(loginForm.password)
    
    const response = await httpClient.post(API_ENDPOINTS.LOGIN, {
      username: loginForm.username,
      password: passwordMd5
    })
    
    if (response.status === 200) {
      // 处理登录响应中的token
      authService.handleLoginResponse(response)
      // 登录成功，跳转到原始页面或首页
      const redirectPath = router.currentRoute.value.query.redirect || '/'
      router.push(redirectPath)
    }
  } catch (error) {
    if (error.response?.status === 401) {
      errorMessage.value = t('login.invalidCredentials', '用户名或密码错误')
    } else {
      errorMessage.value = t('login.loginError', '登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

const handleGuestLogin = async () => {
  errorMessage.value = ''
  loading.value = true
  
  try {
    // 访客登录固定参数
    const guestUsername = 'guest'
    const guestPassword = 'ca2d140c362dfd56acab2fdbd56ff5a5'
    
    const response = await httpClient.post(API_ENDPOINTS.LOGIN, {
      username: guestUsername,
      password: guestPassword
    })
    
    if (response.status === 200) {
      // 处理登录响应中的token
      authService.handleLoginResponse(response)
      // 登录成功，跳转到原始页面或首页
      const redirectPath = router.currentRoute.value.query.redirect || '/'
      router.push(redirectPath)
    }
  } catch (error) {
    if (error.response?.status === 401) {
      errorMessage.value = t('login.guestNotAllowed', '访客登录功能暂不可用')
    } else {
      errorMessage.value = t('login.loginError', '登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

// 检查是否已登录
onMounted(() => {
  // 可以在这里检查是否已有有效的会话
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--background-color);
  padding: 1rem;
  position: relative;
}

.language-switcher-top {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  z-index: 10;
}

.login-card {
  background-color: var(--card-background);
  border-radius: var(--border-radius);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 2rem;
  width: 100%;
  max-width: 400px;
  border: 1px solid var(--border-color);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  font-size: 1.8rem;
  color: var(--text-color);
  margin: 0 0 0.5rem 0;
  font-weight: 600;
}

.login-subtitle {
  color: var(--secondary-color);
  font-size: 0.95rem;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--text-color);
  font-size: 0.9rem;
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.95rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  width: 100%;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(115, 199, 77, 0.1);
}

.form-group input:disabled {
  background-color: var(--light-color);
  cursor: not-allowed;
  opacity: 0.7;
}

.login-button {
  width: 100%;
  padding: 0.8rem;
  font-size: 1rem;
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.login-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}


.status-display.error {
  margin: 0;
  padding: 0.7rem;
  font-size: 0.9rem;
}

.guest-login-section {
  margin-top: 1.5rem;
  text-align: center;
}

.divider {
  position: relative;
  margin-bottom: 1rem;
  text-align: center;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background-color: var(--border-color);
  z-index: 1;
}

.divider span {
  background-color: var(--card-background);
  padding: 0 1rem;
  color: var(--secondary-color);
  font-size: 0.9rem;
  position: relative;
  z-index: 2;
}

.guest-login-button {
  width: 100%;
  padding: 0.8rem;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background-color: var(--light-color);
  color: var(--text-color);
  border: 1px solid var(--border-color);
}

.guest-login-button:hover {
  background-color: var(--hover-light-color);
  border-color: var(--secondary-color);
}

.guest-login-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .login-container {
    padding: 0.5rem;
  }
  
  .login-card {
    padding: 1.5rem;
  }
  
  .login-header h1 {
    font-size: 1.5rem;
  }
}
</style>
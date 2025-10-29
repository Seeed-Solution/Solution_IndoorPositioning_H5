<template>
  <div id="app-shell">
    <nav v-if="!isLoginPage && !isFullscreenMode" class="main-nav">
      <div class="nav-links">
        <!-- <router-link to="/" class="nav-link">Live Map</router-link> REMOVE THIS -->
        <router-link to="/config-tracker" class="nav-link">{{ $t('nav.mapTracker') }}</router-link>
<!--        <router-link to="/config-local" class="nav-link">{{ $t('nav.localMode') }}</router-link>-->
        <router-link to="/map-overview" class="nav-link">{{ $t('nav.mapDashboard') }}</router-link>
        <!-- <router-link to="/map-dashboard?fullscreen=true" class="nav-link">{{ $t('nav.mapDashboard') }}</router-link> OLD ROUTE - COMMENTED FOR FUTURE USE -->
        <router-link to="/config" class="nav-link">{{ $t('nav.mapBeaconConfig') }}</router-link>
      </div>
      <div class="nav-right">
        <LanguageSwitcher />
        <button @click="handleLogout" class="logout-button" :title="$t('common.logout', '登出')">
          <i class="fas fa-sign-out-alt"></i>
          <span class="logout-text">{{ $t('common.logout', '登出') }}</span>
        </button>
      </div>
    </nav>
    <div class="main-content" :class="{ 'fullscreen-content': isFullscreenMode }">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import { authService } from './services/authService.js'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isLoginPage = computed(() => route.path === '/login')

// 检测全屏模式的状态
const isFullscreenMode = ref(false)

// 检测全屏模式的函数
const checkFullscreenMode = () => {
  // 检查 DOM 中是否存在全屏模式的标识
  const fullscreenOverlay = document.querySelector('.fullscreen-overlay')
  isFullscreenMode.value = !!fullscreenOverlay
}

// 使用 MutationObserver 监听 DOM 变化
let observer
onMounted(() => {
  // 初始检查
  checkFullscreenMode()
  
  // 创建 observer 监听 DOM 变化
  observer = new MutationObserver(() => {
    checkFullscreenMode()
  })
  
  // 开始观察 document.body 的子元素变化
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class']
  })
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})

const handleLogout = async () => {
  try {
    const success = await authService.logout()
    if (success) {
      // 登出成功，跳转到登录页面
      router.push('/login')
    } else {
      console.error('Logout failed')
      // 即使后端登出失败，也跳转到登录页面
      router.push('/login')
    }
  } catch (error) {
    console.error('Logout error:', error)
    // 出错时也跳转到登录页面
    router.push('/login')
  }
}
</script>

<style scoped>
#app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* background-color: var(--background-color); /* Optionally set body bg here if not taking full page */
}

.main-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background-color: var(--card-background); /* Changed from --dark-color to white */
  padding: 0.75rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08); /* Adjusted shadow for white bg */
  border-bottom: 1px solid var(--border-color); /* Added a light border like SenseCraft */
}

.main-content {
  /* 为固定导航栏留出空间 */
  margin-top: 70px; /* 导航栏高度 + 一些余量 */
}

.main-content.fullscreen-content {
  /* 全屏模式下不需要顶部边距 */
  margin-top: 0;
}

.nav-links {
  display: flex;
  justify-content: center;
  flex: 1;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-link {
  color: var(--secondary-color); /* Medium gray for inactive links */
  text-decoration: none;
  padding: 0.85rem 1.3rem; /* Adjusted padding for larger font */
  margin: 0 0.5rem;
  border-radius: var(--border-radius);
  transition: color 0.2s ease, border-bottom-color 0.2s ease;
  font-weight: 600; /* Bolder font weight */
  font-size: 1.05rem; /* Further increased font size */
  border-bottom: 3px solid transparent; /* Increased border thickness slightly */
}

.nav-link:hover {
  color: var(--primary-color); /* Green on hover */
}

.nav-link.router-link-exact-active {
  color: var(--primary-color); /* Green text for active tab */
  border-bottom-color: var(--primary-color); /* Green underline for active tab */
  /* font-weight: 700; */ /* Active link is already 600, ensure it stands out or keep same */
}

/* 统一的导航右侧控件样式 */
.nav-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--secondary-color);
  padding: 0.4rem 0.8rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
  height: 36px;
  box-sizing: border-box;
}

.logout-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--secondary-color);
  padding: 0.4rem 0.8rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
  height: 36px;
  box-sizing: border-box;
  line-height: 1;
}

.logout-button i {
  display: flex;
  align-items: center;
  line-height: 1;
}

.logout-button:hover {
  border-color: var(--danger-color);
  color: var(--danger-color);
  background-color: rgba(245, 108, 108, 0.05);
}

.logout-text {
  font-size: 0.85rem;
  font-weight: 500;
  line-height: 1;
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .logout-text {
    display: none;
  }
  
  .logout-button {
    padding: 0.4rem 0.6rem;
  }
}

/* The <router-view /> itself doesn't need styling unless it's wrapped */
/* Content inside router-view should have its own padding via .page-container or similar */
</style>

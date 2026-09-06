<template>
  <div id="app-shell">
    <template v-if="isLoginPage || isFullscreenMode || isDisplayMode">
      <div class="main-content fullscreen-content">
        <router-view />
      </div>
    </template>
    <AppShell
      v-else
      :menu-items="menuItems"
      :breadcrumb="breadcrumb"
      :page-title="pageTitle"
      :current-username="currentUsername"
      :flush="isMapPage"
      @logout="handleLogout"
    >
      <router-view />
    </AppShell>
    <Toast />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppShell from './components/AppShell.vue'
import Toast from './components/Toast.vue'
import { authService } from './services/authService.js'
import { getCurrentUsername } from './services/userStore.js'
import { isDisplayRoute } from './utils/mapUrlState.js'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isLoginPage = computed(() => route.path === '/login')
// 展示模式不套 AppShell: 侧栏与顶栏都要让位给铺满视口的地图（spec §9.2）
const isDisplayMode = computed(() => isDisplayRoute({ path: route.path, query: route.query }))

// 侧栏菜单（结构对齐 kit AppShell 的 menuItems）
// 业务入口收敛成 Map + Config 两项; 室内/室外在 /map 内部用图层控件切换。
const menuItems = computed(() => [
  { key: 'map', to: '/map', icon: 'fa-map-location-dot', label: t('nav.map', 'Map') },
  { key: 'config', to: '/config', icon: 'fa-sliders-h', label: t('nav.mapBeaconConfig') },
])

const currentMenuItem = computed(() => menuItems.value.find((item) => route.path.startsWith(item.to)))
const pageTitle = computed(() => currentMenuItem.value?.label ?? '')
const breadcrumb = computed(() =>
  currentMenuItem.value ? [{ title: t('app.title', 'Indoor Positioning') }, { title: currentMenuItem.value.label }] : []
)

// 地图页内容区自带布局与全屏控件，外壳不加 padding
const MAP_ROUTES = ['/map', '/legacy/map-overview', '/legacy/outdoor-map']
const isMapPage = computed(() => MAP_ROUTES.includes(route.path))

// 当前用户名（从全局状态获取）
const currentUsername = ref(getCurrentUsername())

// 更新用户名的函数
const updateUsername = () => {
  currentUsername.value = getCurrentUsername()
}

// 监听路由变化，当路由变化时更新用户名（checkAuth 会在路由守卫中调用）
watch(() => route.path, (newPath, oldPath) => {
  // 延迟更新，确保路由守卫中的 checkAuth 已经执行完成
  setTimeout(() => {
    updateUsername()
  }, 100)
})

// 组件挂载时也更新一次
onMounted(() => {
  updateUsername()
})

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
    // logout 中已经清空了全局用户名，这里同步更新显示
    currentUsername.value = getCurrentUsername()
    if (success) {
      router.push('/login')
    } else {
      console.log("Logout failed")
      // 即使后端登出失败，也跳转到登录页面
      router.push('/login')
    }
  } catch (error) {
    console.error('Logout error:', error)
    // 出错时也清空并跳转到登录页面
    currentUsername.value = getCurrentUsername()
    router.push('/login')
  }
}
</script>

<style scoped>
#app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* 登录页与全屏地图不套外壳，内容自己铺满 */
.main-content.fullscreen-content {
  margin-top: 0;
  flex: 1 1 auto;
  min-width: 0;
}
</style>

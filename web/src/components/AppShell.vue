<template>
  <div class="sc-shell">
    <div
      v-if="isMobile && mobileMenuOpen"
      class="sc-sider-scrim"
      @click="mobileMenuOpen = false"
    ></div>
    <aside
      class="sc-sider"
      :class="{ 'is-collapsed': collapsed, 'is-offcanvas': isMobile, 'is-open': mobileMenuOpen }"
    >
      <div class="sc-sider__logo">
        <i class="fas fa-map-marker-alt sc-sider__logo-icon"></i>
        <span v-if="!collapsed" class="sc-sider__logo-title">{{ $t('app.title', 'Indoor Positioning') }}</span>
      </div>
      <nav class="sc-menu">
        <router-link
          v-for="item in menuItems"
          :key="item.key"
          :to="item.to"
          class="sc-menu__item"
          :title="item.label"
          @click="mobileMenuOpen = false"
        >
          <i :class="['fas', item.icon, 'sc-menu__icon']"></i>
          <span v-if="!collapsed" class="sc-menu__label">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <div class="sc-main" @transitionend="onMainTransitionEnd">
      <header class="sc-header">
        <button
          type="button"
          class="sc-header__toggle"
          aria-label="toggle-sider"
          @click="onToggleSider"
        >
          <i class="fas fa-bars"></i>
        </button>
        <span class="sc-header__title">{{ pageTitle }}</span>
        <div class="sc-header__extra">
          <div v-if="currentUsername" class="sc-user">
            <i class="fas fa-user"></i>
            <span class="sc-user__name">{{ currentUsername }}</span>
          </div>
          <LanguageSwitcher />
          <button type="button" class="sc-logout" :title="$t('common.logout', '登出')" @click="$emit('logout')">
            <i class="fas fa-sign-out-alt"></i>
            <span class="sc-logout__text">{{ $t('common.logout', '登出') }}</span>
          </button>
        </div>
      </header>

      <main class="sc-content" :class="{ 'is-flush': flush }">
        <nav v-if="breadcrumb.length" class="sc-breadcrumb" aria-label="breadcrumb">
          <template v-for="(crumb, idx) in breadcrumb" :key="crumb.title">
            <span v-if="idx > 0" class="sc-breadcrumb__sep">/</span>
            <router-link v-if="crumb.to" :to="crumb.to" class="sc-breadcrumb__link">{{ crumb.title }}</router-link>
            <span v-else class="sc-breadcrumb__current">{{ crumb.title }}</span>
          </template>
        </nav>
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import LanguageSwitcher from './LanguageSwitcher.vue'
import { LAYOUT_MOBILE, watchLayoutMode } from '@/utils/breakpoints.js'

defineProps({
  menuItems: { type: Array, default: () => [] },
  breadcrumb: { type: Array, default: () => [] },
  pageTitle: { type: String, default: '' },
  currentUsername: { type: String, default: '' },
  // 地图页内容区自带布局，不加内容 padding
  flush: { type: Boolean, default: false },
})

defineEmits(['logout'])

// 断点只在挂载时读一次是拿不到旋屏/拖窗口的，这里挂 change 监听并在卸载时摘掉。
const route = useRoute()
const isMobile = ref(false)
const collapsed = ref(false)
const mobileMenuOpen = ref(false)
let stopLayoutWatch = null

const onToggleSider = () => {
  if (isMobile.value) mobileMenuOpen.value = !mobileMenuOpen.value
  else collapsed.value = !collapsed.value
}

onMounted(() => {
  stopLayoutWatch = watchLayoutMode(
    typeof window !== 'undefined' ? window : null,
    (mode) => {
      const narrow = mode === LAYOUT_MOBILE
      isMobile.value = narrow
      // 窄屏侧栏是 off-canvas 覆盖层，宽度按展开算；关掉时整条滑出视口
      collapsed.value = false
      if (!narrow) mobileMenuOpen.value = false
    },
  )
})

onUnmounted(() => {
  if (stopLayoutWatch) {
    stopLayoutWatch()
    stopLayoutWatch = null
  }
})

// 导航之后收起 off-canvas，否则新页面一直被侧栏盖着
watch(() => route.fullPath, () => { mobileMenuOpen.value = false })

// 折叠/展开改的是内容区宽度，不是窗口尺寸，浏览器不会发 resize 事件。
// 地图（Leaflet 的 trackResize、MapPreview 的 canvas）都只监听 window resize，
// 不补这一下会留下灰块和点击偏移。等过渡结束再发，拿到的才是最终宽度。
const onMainTransitionEnd = (event) => {
  if (event.propertyName !== 'margin-left') return
  if (event.target !== event.currentTarget) return
  window.dispatchEvent(new Event('resize'))
}
</script>

<style scoped>
/* 尺寸与结构对齐 sensecraft-ui-kit 的 AppShell：
   侧栏 --sc-layout-sider-width(256) / 折叠 80，顶栏 --sc-layout-header-height(64)，
   内容区 padding --sc-layout-content-padding(24)。 */
.sc-shell {
  display: flex;
  min-height: 100vh;
  background: var(--sc-color-bg-layout);
}

.sc-sider {
  width: var(--sc-layout-sider-width);
  flex: 0 0 var(--sc-layout-sider-width);
  background: var(--sc-color-bg-container);
  border-right: 1px solid var(--sc-color-border);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: var(--sc-z-sticky);
  transition: width 0.2s ease, flex-basis 0.2s ease;
}

.sc-sider.is-collapsed {
  width: var(--sc-layout-sider-collapsed-width);
  flex-basis: var(--sc-layout-sider-collapsed-width);
}

.sc-sider__logo {
  height: var(--sc-layout-header-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  overflow: hidden;
  white-space: nowrap;
  border-bottom: 1px solid var(--sc-color-border);
}

.sc-sider__logo-icon {
  color: var(--sc-color-primary);
  font-size: 20px;
}

.sc-sider__logo-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--sc-color-text);
}

.sc-menu {
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 4px;
}

.sc-menu__item {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px;
  padding: 0 12px;
  margin: 0 8px;
  border-radius: var(--sc-radius-md);
  color: var(--sc-color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.sc-menu__item:hover {
  background: var(--sc-color-bg-layout);
  color: var(--sc-color-primary);
}

.sc-menu__item.router-link-active {
  background: var(--sc-status-normal-bg);
  color: var(--sc-color-primary-active);
}

.sc-menu__icon {
  width: 16px;
  text-align: center;
  flex: 0 0 16px;
}

.sc-main {
  flex: 1 1 auto;
  min-width: 0;
  margin-left: var(--sc-layout-sider-width);
  display: flex;
  flex-direction: column;
  transition: margin-left 0.2s ease;
}

.sc-sider.is-collapsed + .sc-main {
  margin-left: var(--sc-layout-sider-collapsed-width);
}

.sc-header {
  height: var(--sc-layout-header-height);
  flex: 0 0 var(--sc-layout-header-height);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  background: var(--sc-color-bg-container);
  border-bottom: 1px solid var(--sc-color-border);
  position: sticky;
  top: 0;
  z-index: var(--sc-z-sticky);
}

.sc-header__toggle {
  background: transparent;
  border: none;
  color: var(--sc-color-text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: var(--sc-radius-md);
  box-shadow: none;
}

.sc-header__toggle:hover {
  background: var(--sc-color-bg-layout);
  color: var(--sc-color-primary);
  box-shadow: none;
}

.sc-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--sc-color-text);
}

.sc-header__extra {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sc-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.8rem;
  color: var(--sc-color-text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
}

.sc-user i {
  color: var(--sc-color-primary);
}

.sc-logout {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: 1px solid var(--sc-color-border);
  color: var(--sc-color-text-secondary);
  padding: 0.4rem 0.8rem;
  border-radius: var(--sc-radius-md);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  height: 36px;
  box-sizing: border-box;
  line-height: 1;
  box-shadow: none;
}

.sc-logout:hover {
  border-color: var(--sc-color-error);
  color: var(--sc-color-error);
  background-color: var(--sc-status-danger-bg);
  box-shadow: none;
}

.sc-content {
  flex: 1 1 auto;
  min-width: 0;
  box-sizing: border-box;
  padding: var(--sc-layout-content-padding);
  /* 溢出兜底：真正的修复在各页的 min-width:0 / 换行，这里只是外壳保护 */
  overflow-x: auto;
}

.sc-content.is-flush {
  padding: 0;
}

.sc-content.is-flush .sc-breadcrumb {
  padding: 12px var(--sc-layout-content-padding) 0;
  margin-bottom: 0;
}

.sc-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--sc-color-text-tertiary);
}

.sc-breadcrumb__sep {
  color: var(--sc-color-text-tertiary);
}

.sc-breadcrumb__link {
  color: var(--sc-color-text-secondary);
  text-decoration: none;
}

.sc-breadcrumb__link:hover {
  color: var(--sc-color-primary);
}

.sc-breadcrumb__current {
  color: var(--sc-color-text);
  font-weight: 500;
}

.sc-sider-scrim {
  position: fixed;
  inset: 0;
  z-index: calc(var(--sc-z-sticky) - 1);
  background: rgba(0, 0, 0, 0.4);
}

@media (max-width: 767.98px) {
  .sc-user__name,
  .sc-logout__text {
    display: none;
  }

  /* <768: 侧栏整条滑出视口，内容区铺满，不再留 80px 让位 */
  .sc-sider.is-offcanvas {
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.12);
  }

  .sc-sider.is-offcanvas.is-open {
    transform: translateX(0);
  }

  .sc-main,
  .sc-sider + .sc-main,
  .sc-sider.is-collapsed + .sc-main {
    margin-left: 0;
  }
}
</style>

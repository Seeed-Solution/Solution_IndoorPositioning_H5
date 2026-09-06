<template>
  <div class="sc-shell">
    <aside class="sc-sider" :class="{ 'is-collapsed': collapsed }">
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
          @click="collapsed = !collapsed"
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
import { ref } from 'vue'
import LanguageSwitcher from './LanguageSwitcher.vue'

defineProps({
  menuItems: { type: Array, default: () => [] },
  breadcrumb: { type: Array, default: () => [] },
  pageTitle: { type: String, default: '' },
  currentUsername: { type: String, default: '' },
  // 地图页内容区自带布局，不加内容 padding
  flush: { type: Boolean, default: false },
})

defineEmits(['logout'])

// 窄屏默认折叠：侧栏是 fixed 定位，展开时会盖住内容区
const isNarrowScreen = () =>
  typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(max-width: 768px)').matches
    : false

const collapsed = ref(isNarrowScreen())

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
  padding: var(--sc-layout-content-padding);
  /* 宽内容（地图/表格）在内容区内部横向滚动，不让整页横向滚动 */
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

@media (max-width: 768px) {
  .sc-user__name,
  .sc-logout__text {
    display: none;
  }

  /* 窄屏展开时侧栏盖在内容上，内容区仍按折叠宽度让位，不再被挤掉一半 */
  .sc-sider:not(.is-collapsed) {
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.12);
  }

  .sc-main,
  .sc-sider:not(.is-collapsed) + .sc-main {
    margin-left: var(--sc-layout-sider-collapsed-width);
  }
}
</style>

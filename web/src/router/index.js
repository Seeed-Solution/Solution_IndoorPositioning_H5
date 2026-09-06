import { createRouter, createWebHistory } from 'vue-router';
import TrackerModeConfigView from '@/views/TrackerModeConfigView.vue'; // Import the new view
import MapOverview from '@/views/MapOverview.vue'; // Import the new map overview view
import LoginView from '@/views/LoginView.vue'; // Import the login view
import ConfigurationSuiteView from '@/views/ConfigurationSuiteView.vue'; // Import the main config view
import OutdoorMapOverview from '@/views/OutdoorMapOverview.vue'; // Outdoor (WGS84) map view
import MapWorkspaceView from '@/views/MapWorkspaceView.vue'; // 统一地图工作台 /map

import { authService } from '@/services/authService.js';
import { LEGACY_ROUTE_MAP, MAP_PATH, migrateLastVisitedPage } from '@/utils/mapUrlState.js';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    // 旧页面组件保留一个发布周期作为回退入口, 路径加 /legacy 前缀, 不出现在导航里。
    path: '/legacy/config-tracker',
    name: 'TrackerModeConfig',
    component: TrackerModeConfigView, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/legacy/map-overview',
    name: 'MapOverview',
    component: MapOverview, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/legacy/outdoor-map',
    name: 'OutdoorMapOverview',
    component: OutdoorMapOverview,
    meta: { requiresAuth: true }
  },
  {
    path: MAP_PATH,
    name: 'MapWorkspace',
    component: MapWorkspaceView,
    meta: { requiresAuth: true }
  },
  // 旧路由兼容: 开发环境（Vite）与 SPA 内部导航靠这里的 client redirect；
  // 生产环境由 nginx 的 return 301 先接住（nginx.conf），两条路都要留。
  ...Object.entries(LEGACY_ROUTE_MAP).map(([from, preset]) => ({
    path: from,
    redirect: () => ({ path: MAP_PATH, query: { ...preset } }),
  })),
  {
    path: '/config',
    name: 'Configuration',
    component: ConfigurationSuiteView,
    meta: { requiresAuth: true }
  },
];

const router = createRouter({
  history: createWebHistory("/web"),
  routes,
});

// 智能路由决策函数
const getDefaultRoute = async () => {
  try {
    // 这里可以添加自定义逻辑来决定默认页面
    
    // 示例逻辑1：根据用户角色或权限
    // const userInfo = await authService.getUserInfo()
    // if (userInfo.role === 'admin') {
    //   return '/config'
    // } else if (userInfo.role === 'viewer') {
    //   return '/map-overview'
    // }
    
    // 示例逻辑2：根据本地存储的用户偏好
    // 旧版本存的是 /map-overview 之类的裸 path, 原样恢复会把用户送回下线页面。
    const stored = localStorage.getItem('lastVisitedPage')
    const migrated = migrateLastVisitedPage(stored)
    if (migrated && migrated !== stored) {
      localStorage.setItem('lastVisitedPage', migrated)
    }
    if (migrated) {
      return migrated
    }
    
    // 示例逻辑3：根据时间段
    // const hour = new Date().getHours()
    // if (hour >= 9 && hour <= 17) { // 工作时间
    //   return '/config-tracker'
    // } else {
    //   return '/map-overview'
    // }
    
    // 示例逻辑4：根据设备配置状态
    // const hasConfiguredMaps = await checkIfMapsConfigured()
    // if (!hasConfiguredMaps) {
    //   return '/config'
    // }
    
    return MAP_PATH
  } catch (error) {
    console.error('Error determining default route:', error)
    return MAP_PATH
  }
}

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 检查路由是否需要认证
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth) {
    try {
      // 检查用户是否已登录
      const isAuthenticated = await authService.checkAuth()
      
      if (isAuthenticated) {
        // 如果访问的是根路径 "/"，使用智能路由决策
        if (to.path === '/' || to.path === '/web/') {
          const defaultRoute = await getDefaultRoute()
          if (defaultRoute !== '/') {
            next(defaultRoute)
            return
          }
        }
        
        // 记录用户访问的页面（用于下次登录时的智能跳转）
        // 存 fullPath: /map 的界面状态全在 query 里, 只存 path 会把它丢干净。
        if (to.path !== '/login') {
          localStorage.setItem('lastVisitedPage', to.fullPath)
        }
        
        next() // 已登录，允许访问
      } else {
        // 未登录，重定向到登录页面
        next({
          path: '/login',
          query: { redirect: to.fullPath } // 保存原始路径，登录成功后可以跳转回去
        })
      }
    } catch (error) {
      console.error('Authentication check failed:', error)
      // 认证检查失败，重定向到登录页面
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
    }
  } else {
    // 不需要认证的路由（如登录页面）
    // 如果访问的是登录页面，直接放行
    if (to.path === '/login') {
      next()
      return
    }
    // 如果访问的是根路径，跳转到默认页面
    if (to.path === '/' || to.path === '/web/') {
      const defaultPath = await getDefaultRoute()
      next(defaultPath)
      return
    }
    // 其他不需要认证的路由，直接放行
    next()
  }
});

export default router; 
import { createRouter, createWebHistory } from 'vue-router';
import TrackerModeConfigView from '@/views/TrackerModeConfigView.vue'; // Import the new view
import MapOverview from '@/views/MapOverview.vue'; // Import the new map overview view
import LoginView from '@/views/LoginView.vue'; // Import the login view
import ConfigurationSuiteView from '@/views/ConfigurationSuiteView.vue'; // Import the main config view
import OutdoorMapOverview from '@/views/OutdoorMapOverview.vue'; // Outdoor (WGS84) map view

import { authService } from '@/services/authService.js';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/config-tracker', // Define path for tracker mode
    name: 'TrackerModeConfig', // This is the specific path for Tracker Mode if not default
    component: TrackerModeConfigView, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/map-overview', // Define path for map overview
    name: 'MapOverview', // Name for the map overview route
    component: MapOverview, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/outdoor-map', // WGS84 / GNSS trackers on a Leaflet base map
    name: 'OutdoorMapOverview',
    component: OutdoorMapOverview,
    meta: { requiresAuth: true }
  },
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
    const lastVisitedPage = localStorage.getItem('lastVisitedPage')
    if (lastVisitedPage && lastVisitedPage !== '/login') {
      return lastVisitedPage
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
    
    // 默认返回 tracker 页面
    return '/config-tracker'
  } catch (error) {
    console.error('Error determining default route:', error)
    return '/config-tracker' // 出错时的默认页面
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
        if (to.path !== '/login') {
          localStorage.setItem('lastVisitedPage', to.path)
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
import { createRouter, createWebHistory } from 'vue-router';
// import LiveMapView from '@/views/LiveMapView.vue'; // To be removed
import MasterConfigView from '@/views/MasterConfigView.vue'; // New Master Config
import LocalModeConfigView from '@/views/LocalModeConfigView.vue'; // Renamed from PersonalModeConfigView
import TrackerModeConfigView from '@/views/TrackerModeConfigView.vue'; // Import the new view
import MapDashboardView from '@/views/MapDashboardView.vue'; // Import the map dashboard view
import MapOverview from '@/views/MapOverview.vue'; // Import the new map overview view
import LoginView from '@/views/LoginView.vue'; // Import the login view
// import HomeView from '@/views/HomeView.vue';
// import ConfigurationView from '@/views/ConfigurationView.vue'; // Old, to be removed or reworked
import ConfigurationSuiteView from '@/views/ConfigurationSuiteView.vue'; // Import the main config view
// import LiveDataView from '@/views/LiveDataView.vue';
// import DeviceTrackingView from '@/views/DeviceTrackingView.vue';
import { authService } from '@/services/authService.js';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  // {
  //   path: '/',
  //   name: 'LiveMap',
  //   component: LiveMapView, // Remove this route
  // },
  {
    path: '/', // Make TrackerMode the default landing page
    name: 'TrackerModeConfiguration', // Keep original name for consistency or change to TrackerModeDefault
    component: TrackerModeConfigView,
    meta: { requiresAuth: true }
  },
  {
    path: '/config-master',
    name: 'MasterConfiguration', // Changed from MasterConfigRedirect for clarity
    component: MasterConfigView, // Route for the new master config page
    meta: { requiresAuth: true }
  },
  {
    path: '/config-local', // Renamed path
    name: 'LocalModeConfiguration', // Renamed name
    component: LocalModeConfigView, // Route for the new personal mode config page
    meta: { requiresAuth: true }
  },
  {
    path: '/config-tracker', // Define path for tracker mode
    name: 'TrackerModeConfig', // This is the specific path for Tracker Mode if not default
    component: TrackerModeConfigView, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/map-dashboard', // Define path for map dashboard
    name: 'MapDashboard', // Name for the map dashboard route
    component: MapDashboardView, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/map-overview', // Define path for map overview
    name: 'MapOverview', // Name for the map overview route
    component: MapOverview, // Use the new component
    meta: { requiresAuth: true }
  },
  {
    path: '/config',
    name: 'Configuration',
    component: ConfigurationSuiteView,
    meta: { requiresAuth: true }
  },
  // {
  //   path: '/live-data',
  //   name: 'LiveData',
  //   component: LiveDataView,
  // },
  // {
  //   path: '/device-tracking',
  //   name: 'DeviceTracking',
  //   component: DeviceTrackingView,
  // },
  // {
  //   path: '/config', // Old path, decide if to keep, redirect, or remove
  //   name: 'Configuration',
  //   component: ConfigurationSuiteView, 
  // },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
        if (to.path === '/') {
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
    // 不需要认证的路由（如登录页面），直接放行
    next()
  }
});

export default router; 
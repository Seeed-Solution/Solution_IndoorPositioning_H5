/**
 * API配置管理
 * 统一管理开发环境和生产环境的API基础URL
 * 支持三种部署模式：
 * 1. development: 开发模式，使用 vite 代理
 * 2. production-remote: 远程生产模式，访问远程服务器
 * 3. production-local: 本地生产模式，web和后端在同一容器
 */

// 获取环境变量 - 兼容 Vite 和 Node.js 环境
const isDev = typeof import.meta !== 'undefined' && import.meta.env 
  ? import.meta.env.DEV 
  : process.env.NODE_ENV !== 'production'

const useRemote = typeof import.meta !== 'undefined' && import.meta.env
  ? import.meta.env.VITE_USE_REMOTE === 'true'
  : process.env.VITE_USE_REMOTE === 'true'

// 检测是否为本地容器部署模式
// 在容器内部署时，web和后端在同一个服务中，直接使用相对路径
const isLocalContainer = typeof import.meta !== 'undefined' && import.meta.env
  ? import.meta.env.VITE_LOCAL_CONTAINER === 'true'
  : process.env.VITE_LOCAL_CONTAINER === 'true'

// 定义API基础URL
const API_CONFIG = {
  // 开发环境配置
  development: {
    // 本地开发（默认）- 使用 vite 代理
    local: '/api',
    // 远程开发 - 直接访问远程服务器
    remote: 'http://127.0.0.1:8022/api'
  },
  // 生产环境配置
  production: {
    // 本地容器模式 - web和后端在同一个服务中
    local: `${window.location.protocol}//${window.location.hostname}:8022/api`,
    // 远程模式 - 访问远程服务器
    remote: 'https://indoorpositioning-demo.seeed.cc/api'
  }
}

// WebSocket配置
const WS_CONFIG = {
  development: {
    local: 'ws://127.0.0.1:8022',
    remote: 'ws://127.0.0.1:8022'
  },
  production: {
    // 本地容器模式 - 使用相对路径，协议会自动适配
    local: () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      return `${protocol}//${window.location.hostname}:8022`
    },
    // 远程模式 - 访问远程服务器
    remote: 'wss://indoorpositioning-demo.seeed.cc'
  }
}

/**
 * 获取API基础URL
 * @returns {string} API基础URL
 */
export function getApiBaseUrl() {
  // // 实时获取环境变量，支持动态切换
  // const currentIsDev = typeof import.meta !== 'undefined' && import.meta.env
  //   ? import.meta.env.DEV
  //   : process.env.NODE_ENV !== 'production'
  //
  // const currentUseRemote = typeof import.meta !== 'undefined' && import.meta.env
  //   ? import.meta.env.VITE_USE_REMOTE === 'true'
  //   : process.env.VITE_USE_REMOTE === 'true'
  //
  // const currentIsLocalContainer = typeof import.meta !== 'undefined' && import.meta.env
  //   ? import.meta.env.VITE_LOCAL_CONTAINER === 'true'
  //   : process.env.VITE_LOCAL_CONTAINER === 'true'
  //
  // if (currentIsDev) {
  //   // 开发环境：根据环境变量决定使用本地代理还是直接访问远程
  //   return currentUseRemote ? API_CONFIG.development.remote : API_CONFIG.development.local
  // } else {
  //   // 生产环境：根据部署模式选择配置
  //   if (currentIsLocalContainer) {
  //     // 本地容器模式：web和后端在同一个服务中，使用相对路径
  //     return API_CONFIG.production.local
  //   } else {
  //     // 远程模式：访问远程服务器
  //     return API_CONFIG.production.remote
  //   }
  // }
  return `${window.location.protocol}//${window.location.host}/api`;
}

/**
 * 获取WebSocket基础URL
 * @returns {string} WebSocket基础URL
 */
export function getWsBaseUrl() {
  // const currentIsDev = typeof import.meta !== 'undefined' && import.meta.env
  //   ? import.meta.env.DEV
  //   : process.env.NODE_ENV !== 'production'
  //
  // const currentUseRemote = typeof import.meta !== 'undefined' && import.meta.env
  //   ? import.meta.env.VITE_USE_REMOTE === 'true'
  //   : process.env.VITE_USE_REMOTE === 'true'
  //
  // const currentIsLocalContainer = typeof import.meta !== 'undefined' && import.meta.env
  //   ? import.meta.env.VITE_LOCAL_CONTAINER === 'true'
  //   : process.env.VITE_LOCAL_CONTAINER === 'true'
  //
  // if (currentIsDev) {
  //   return currentUseRemote ? WS_CONFIG.development.remote : WS_CONFIG.development.local
  // } else {
  //   // 生产环境：根据部署模式选择配置
  //   if (currentIsLocalContainer) {
  //     // 本地容器模式：动态构建WebSocket URL
  //     const wsConfig = WS_CONFIG.production.local
  //     return typeof wsConfig === 'function' ? wsConfig() : wsConfig
  //   } else {
  //     // 远程模式：访问远程服务器
  //     return WS_CONFIG.production.remote
  //   }
  // }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.hostname}:5173`
}

/**
 * 构建完整的API URL
 * @param {string} endpoint - API端点，如 '/configuration/web'
 * @returns {string} 完整的API URL
 */
export function buildApiUrl(endpoint) {
  const baseUrl = getApiBaseUrl()
  // 确保端点以 / 开头
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  // 如果baseUrl已经包含/api，则不重复添加
  if (baseUrl.endsWith('/api') && cleanEndpoint.startsWith('/')) {
    return `${baseUrl}${cleanEndpoint}`
  }
  return `${baseUrl}${cleanEndpoint}`
}

/**
 * 构建完整的WebSocket URL
 * @param {string} endpoint - WebSocket端点，如 '/realtime'
 * @returns {string} 完整的WebSocket URL
 */
export function buildWsUrl(endpoint) {
  const baseUrl = getWsBaseUrl()
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${baseUrl}${cleanEndpoint}`
}

/**
 * 构建图片的完整访问URL
 * 如果URL已经是完整URL（包含协议），则直接返回
 * 如果是相对路径，则使用当前页面的协议+域名拼接
 * @param {string} imageUrl - 图片URL（可能是相对路径或完整URL）
 * @returns {string} 完整的图片URL
 */
export function buildImageUrl(imageUrl) {
  if (!imageUrl) {
    return imageUrl;
  }
  
  // 如果已经是完整URL（包含协议），直接返回
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://') || 
      imageUrl.startsWith('blob:') || imageUrl.startsWith('data:')) {
    return imageUrl;
  }
  
  // 如果是相对路径，使用当前页面的协议+域名拼接
  return `${window.location.protocol}//${window.location.host}${imageUrl}`;
}

// 导出配置常量
export const API_ENDPOINTS = {
  // 认证相关
  AUTH_CHECK: '/auth/check',
  AUTH_LOGOUT: '/auth/logout',
  LOGIN: '/login',
  CHANGE_PASSWORD: '/change-password',
  
  // 配置相关
  CONFIG_WEB: '/configuration/web',
  CONFIG_DASHBOARD: '/configuration/dashboard',
  SERVER_RUNTIME_CONFIG: '/server-runtime-config',
  
  // MQTT相关
  MQTT_CONNECT: '/mqtt/connect',
  MQTT_DISCONNECT: '/mqtt/disconnect',
  
  // 设备相关
  TRACKERS: '/trackers',
  ALLOW_TRACKER_LIST: '/allow_tracker-list',
  PAAS_DEVICES: '/list_paas_device',
  DEVICES_BATCH_UPDATE_GROUP: '/devices/batch-update-group',
  
  // 分组相关
  GROUPS: '/groups',
  GROUP_BY_ID: (id) => `/groups/${id}`,
  
  // 系统相关
  SHUTDOWN: '/shutdown',
  SERVICE_CREDENTIALS: '/set-service-credentials',
  
  // 地图和数据相关
  MAP_EXAMPLE_FORMAT: '/map-example-format',
  DEFAULT_TEST_CONFIG: '/default-test-config',
  LIST_ALARM: '/list_alarm',
  
  // 事件/告警相关
  EVENTS: '/events',
  EVENT_BY_ID: (id) => `/events/${id}`
}

// 开发环境下打印配置信息
if (isDev) {
  console.log(`[API Config] Environment: ${isDev ? 'development' : 'production'}`)
  console.log(`[API Config] Use Remote: ${useRemote}`)
  console.log(`[API Config] Local Container: ${isLocalContainer}`)
  console.log(`[API Config] API Base URL: ${getApiBaseUrl()}`)
  console.log(`[API Config] WS Base URL: ${getWsBaseUrl()}`)
}
/**
 * API配置管理
 * 统一管理开发环境和生产环境的API基础URL
 */

// 获取环境变量 - 兼容 Vite 和 Node.js 环境
const isDev = typeof import.meta !== 'undefined' && import.meta.env 
  ? import.meta.env.DEV 
  : process.env.NODE_ENV !== 'production'

const useRemote = typeof import.meta !== 'undefined' && import.meta.env
  ? import.meta.env.VITE_USE_REMOTE === 'true'
  : process.env.VITE_USE_REMOTE === 'true'

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
    baseUrl: 'https://indoorpositioning-demo.seeed.cc/api'
  }
}

// WebSocket配置
const WS_CONFIG = {
  development: {
    local: '/ws',
    remote: 'ws://127.0.0.1:8022/ws'
  },
  production: {
    baseUrl: 'wss://indoorpositioning-demo.seeed.cc/ws'
  }
}

/**
 * 获取API基础URL
 * @returns {string} API基础URL
 */
export function getApiBaseUrl() {
  // 实时获取环境变量，支持动态切换
  const currentIsDev = typeof import.meta !== 'undefined' && import.meta.env 
    ? import.meta.env.DEV 
    : process.env.NODE_ENV !== 'production'
    
  const currentUseRemote = typeof import.meta !== 'undefined' && import.meta.env
    ? import.meta.env.VITE_USE_REMOTE === 'true'
    : process.env.VITE_USE_REMOTE === 'true'
    
  if (currentIsDev) {
    // 开发环境：根据环境变量决定使用本地代理还是直接访问远程
    return currentUseRemote ? API_CONFIG.development.remote : API_CONFIG.development.local
  } else {
    // 生产环境：使用生产环境配置
    return API_CONFIG.production.baseUrl
  }
}

/**
 * 获取WebSocket基础URL
 * @returns {string} WebSocket基础URL
 */
export function getWsBaseUrl() {
  const currentIsDev = typeof import.meta !== 'undefined' && import.meta.env 
    ? import.meta.env.DEV 
    : process.env.NODE_ENV !== 'production'
    
  const currentUseRemote = typeof import.meta !== 'undefined' && import.meta.env
    ? import.meta.env.VITE_USE_REMOTE === 'true'
    : process.env.VITE_USE_REMOTE === 'true'
    
  if (currentIsDev) {
    return currentUseRemote ? WS_CONFIG.development.remote : WS_CONFIG.development.local
  } else {
    return WS_CONFIG.production.baseUrl
  }
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
  
  // 系统相关
  SHUTDOWN: '/shutdown',
  SERVICE_CREDENTIALS: '/set-service-credentials',
  
  // 地图和数据相关
  MAP_EXAMPLE_FORMAT: '/map-example-format',
  DEFAULT_TEST_CONFIG: '/default-test-config',
  LIST_ALARM: '/list_alarm'
}

// 开发环境下打印配置信息
if (isDev) {
  console.log(`[API Config] Environment: ${isDev ? 'development' : 'production'}`)
  console.log(`[API Config] Use Remote: ${useRemote}`)
  console.log(`[API Config] API Base URL: ${getApiBaseUrl()}`)
  console.log(`[API Config] WS Base URL: ${getWsBaseUrl()}`)
}
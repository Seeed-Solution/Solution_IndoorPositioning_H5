/**
 * 统一的HTTP客户端
 * 基于axios创建配置好的HTTP客户端实例
 */

import axios from 'axios'
import { getApiBaseUrl } from '../config/api.js'
import notificationService from '../services/notificationService.js'

/**
 * 创建axios实例
 */
const httpClient = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  // 请求超时时间
  timeout: 30000,
})

/**
 * 请求拦截器
 */
httpClient.interceptors.request.use(
  (config) => {
    // 在请求发送之前做一些处理
    // 例如添加认证token、请求日志等
    return config
  },
  (error) => {
    console.error('Request interceptor error:', error)
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
httpClient.interceptors.response.use(
  (response) => {
    // 对响应数据做一些处理
    return response
  },
  (error) => {
    // 统一错误处理
    console.error('HTTP Client Error:', error)
    
    if (error.response) {
      // 服务器响应了错误状态码
      const status = error.response.status
      const detail = error.response.data?.detail || error.message
      
      // 使用通知服务显示用户友好的错误信息
      notificationService.httpError(status, detail)
      
      // 特殊处理401状态码 - 可能需要重定向到登录页
      if (status === 401) {
        console.warn('Unauthorized access, may need to redirect to login')
        // 这里可以添加重定向到登录页的逻辑
        // router.push('/login')
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应 - 网络错误
      console.error('Network error: No response received')
      notificationService.networkError()
    } else {
      // 设置请求时发生了错误
      console.error('Request setup error:', error.message)
      notificationService.error(error.message)
    }
    
    return Promise.reject(error)
  }
)

/**
 * 便捷的API请求方法
 */
export const apiRequest = {
  get: (url, config) => httpClient.get(url, config),
  post: (url, data, config) => httpClient.post(url, data, config),
  put: (url, data, config) => httpClient.put(url, data, config),
  patch: (url, data, config) => httpClient.patch(url, data, config),
  delete: (url, config) => httpClient.delete(url, config),
}

/**
 * 原始fetch包装器（用于需要使用fetch的场景）
 */
export async function fetchApi(endpoint, options = {}) {
  const baseUrl = getApiBaseUrl()
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }
  
  try {
    const response = await fetch(url, defaultOptions)
    return response
  } catch (error) {
    console.error('Fetch API Error:', error)
    throw error
  }
}

export default httpClient
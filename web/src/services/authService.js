import httpClient from '../utils/httpClient.js'
import { API_ENDPOINTS } from '../config/api.js'
import { saveTokenToLocalStorage, getTokenFromLocalStorage, removeTokenFromLocalStorage } from './localStorageService.js'

export const authService = {
  /**
   * 检查用户是否已登录
   */
  async checkAuth() {
    try {
      const response = await httpClient.get(API_ENDPOINTS.AUTH_CHECK)
      if (response.status === 200 && response.data?.data?.token) {
        saveTokenToLocalStorage(response.data.data.token)
      }
      return response.status === 200
    } catch (error) {
      return false
    }
  },

  /**
   * 用户登出
   */
  async logout() {
    try {
      const response = await httpClient.post(API_ENDPOINTS.AUTH_LOGOUT)
      if (response.status === 200) {
        removeTokenFromLocalStorage()
      }
      return response.status === 200
    } catch (error) {
      console.error('Logout error:', error)
      return false
    }
  },

  /**
   * 获取存储的token
   */
  getStoredToken() {
    return getTokenFromLocalStorage()
  },

  /**
   * 处理登录响应中的token
   */
  handleLoginResponse(response) {
    if (response.data?.data?.token) {
      saveTokenToLocalStorage(response.data.data.token)
      return true
    }
    return false
  }
}
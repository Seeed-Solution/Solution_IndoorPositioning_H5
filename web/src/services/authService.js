import httpClient from '../utils/httpClient.js'
import { API_ENDPOINTS } from '../config/api.js'

export const authService = {
  /**
   * 检查用户是否已登录
   */
  async checkAuth() {
    try {
      const response = await httpClient.get(API_ENDPOINTS.AUTH_CHECK)
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
      return response.status === 200
    } catch (error) {
      console.error('Logout error:', error)
      return false
    }
  }
}
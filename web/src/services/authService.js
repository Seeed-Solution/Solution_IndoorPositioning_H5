import httpClient from '../utils/httpClient.js'
import { API_ENDPOINTS } from '../config/api.js'
import { saveTokenToLocalStorage, getTokenFromLocalStorage, removeTokenFromLocalStorage } from './localStorageService.js'
import { setCurrentUsername, clearCurrentUsername } from './userStore.js'

export const authService = {
  /**
   * 检查用户是否已登录
   */
  async checkAuth() {
    try {
      const response = await httpClient.get(API_ENDPOINTS.AUTH_CHECK)
      if (response.status === 200) {
        // 保存 token（如果存在）
        if (response.data?.data?.token) {
          saveTokenToLocalStorage(response.data.data.token)
        }
        // 保存用户名（如果存在）
        // 接口返回格式: {"success":true,"message":"登录成功","username":"admin"}
        if (response.data?.username) {
          setCurrentUsername(response.data.username)
        } else {
          clearCurrentUsername()
        }
        return true
      } else {
        clearCurrentUsername()
        return false
      }
    } catch (error) {
      clearCurrentUsername()
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
        clearCurrentUsername()
      } else {
        clearCurrentUsername()
      }
      return response.status === 200
    } catch (error) {
      console.error('Logout error:', error)
      clearCurrentUsername()
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
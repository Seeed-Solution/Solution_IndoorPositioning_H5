/**
 * 全局通知服务
 * 提供统一的用户通知功能
 */

import { createApp } from 'vue'

// 通知类型常量
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info'
}

/**
 * 全局通知服务类
 */
class NotificationService {
  constructor() {
    this.i18nInstance = null
  }

  /**
   * 设置i18n实例，用于国际化
   * @param {Object} i18n - Vue i18n 实例
   */
  setI18n(i18n) {
    this.i18nInstance = i18n
  }

  /**
   * 获取翻译文本
   * @param {string} key - 翻译键
   * @param {string} fallback - 备用文本
   * @returns {string}
   */
  translate(key, fallback = '') {
    if (this.i18nInstance && this.i18nInstance.global) {
      return this.i18nInstance.global.t(key, fallback)
    }
    return fallback
  }

  /**
   * 显示成功通知
   * @param {string} message - 消息内容
   * @param {string} translationKey - 翻译键
   */
  success(message, translationKey = '') {
    const text = translationKey ? this.translate(translationKey, message) : message
    this.show(text, NOTIFICATION_TYPES.SUCCESS)
  }

  /**
   * 显示错误通知
   * @param {string} message - 消息内容
   * @param {string} translationKey - 翻译键
   */
  error(message, translationKey = '') {
    const text = translationKey ? this.translate(translationKey, message) : message
    this.show(text, NOTIFICATION_TYPES.ERROR)
  }

  /**
   * 显示警告通知
   * @param {string} message - 消息内容
   * @param {string} translationKey - 翻译键
   */
  warning(message, translationKey = '') {
    const text = translationKey ? this.translate(translationKey, message) : message
    this.show(text, NOTIFICATION_TYPES.WARNING)
  }

  /**
   * 显示信息通知
   * @param {string} message - 消息内容
   * @param {string} translationKey - 翻译键
   */
  info(message, translationKey = '') {
    const text = translationKey ? this.translate(translationKey, message) : message
    this.show(text, NOTIFICATION_TYPES.INFO)
  }

  /**
   * 显示HTTP错误通知
   * @param {number} statusCode - HTTP状态码
   * @param {string} defaultMessage - 默认消息
   */
  httpError(statusCode, defaultMessage = '') {
    let translationKey = 'errors.unknownError'
    let fallbackMessage = defaultMessage || '未知错误'

    switch (statusCode) {
      case 400:
        translationKey = 'errors.badRequest'
        fallbackMessage = '请求参数错误'
        break
      case 401:
        translationKey = 'errors.unauthorized'
        fallbackMessage = '未授权访问，请重新登录'
        break
      case 403:
        translationKey = 'errors.forbidden'
        fallbackMessage = '没有权限进行此操作'
        break
      case 404:
        translationKey = 'errors.notFound'
        fallbackMessage = '请求的资源未找到'
        break
      case 408:
        translationKey = 'errors.requestTimeout'
        fallbackMessage = '请求超时，请重试'
        break
      case 500:
      case 502:
      case 503:
      case 504:
        translationKey = 'errors.serverError'
        fallbackMessage = '服务器错误，请稍后重试'
        break
      default:
        if (statusCode >= 400 && statusCode < 500) {
          translationKey = 'errors.badRequest'
          fallbackMessage = '客户端请求错误'
        } else if (statusCode >= 500) {
          translationKey = 'errors.serverError'
          fallbackMessage = '服务器错误，请稍后重试'
        }
    }

    const message = this.translate(translationKey, fallbackMessage)
    this.error(message)
  }

  /**
   * 显示网络错误通知
   */
  networkError() {
    const message = this.translate('errors.networkError', '网络连接错误，请检查网络连接')
    this.error(message)
  }

  /**
   * 实际显示通知的方法
   * @param {string} message - 消息内容
   * @param {string} type - 通知类型
   * @param {number} duration - 显示时长（毫秒），0 表示不自动关闭
   */
  show(message, type = NOTIFICATION_TYPES.INFO, duration = 4000) {
    // 使用 Toast 组件显示通知
    if (window.toastService) {
      window.toastService.show(message, type, duration)
    } else {
      // 如果 Toast 服务未初始化，降级使用 alert
      const typeIcons = {
        [NOTIFICATION_TYPES.SUCCESS]: '✅',
        [NOTIFICATION_TYPES.ERROR]: '❌',
        [NOTIFICATION_TYPES.WARNING]: '⚠️',
        [NOTIFICATION_TYPES.INFO]: 'ℹ️'
      }
      const icon = typeIcons[type] || typeIcons[NOTIFICATION_TYPES.INFO]
      alert(`${icon} ${message}`)
    }

    // 也在控制台记录，便于调试
    const consoleMethod = type === NOTIFICATION_TYPES.ERROR ? 'error' : 
                         type === NOTIFICATION_TYPES.WARNING ? 'warn' : 'info'
    console[consoleMethod](`[${type.toUpperCase()}] ${message}`)
  }
}

// 创建全局单例实例
export const notificationService = new NotificationService()

// 默认导出
export default notificationService
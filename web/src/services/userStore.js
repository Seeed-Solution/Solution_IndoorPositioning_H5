// 当前登录用户名的本地存储。基线分支上 App.vue 与 authService.js 都 import
// 这个模块, 但文件从未入库, 导致 `npm run build` 直接失败。这里按两处调用点的
// 签名补齐最小实现。
const STORAGE_KEY = 'currentUsername';

export function getCurrentUsername() {
  try {
    return localStorage.getItem(STORAGE_KEY) || '';
  } catch (err) {
    console.warn('[userStore] read failed:', err);
    return '';
  }
}

export function setCurrentUsername(username) {
  try {
    if (username) {
      localStorage.setItem(STORAGE_KEY, username);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch (err) {
    console.warn('[userStore] write failed:', err);
  }
}

export function clearCurrentUsername() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.warn('[userStore] clear failed:', err);
  }
}

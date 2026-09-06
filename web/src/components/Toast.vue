<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast"
      tag="div"
      class="toast-container"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
        @click="removeToast(toast.id)"
      >
        <div class="toast-icon">
          <i :class="getIconClass(toast.type)"></i>
        </div>
        <div class="toast-content">
          <div class="toast-message" v-html="formatMessage(toast.message)"></div>
        </div>
        <button
          class="toast-close"
          @click.stop="removeToast(toast.id)"
          :aria-label="$t('common.close', '关闭')"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const toasts = ref([])
let toastIdCounter = 0

const getIconClass = (type) => {
  const icons = {
    success: 'fas fa-check-circle',
    error: 'fas fa-exclamation-circle',
    warning: 'fas fa-exclamation-triangle',
    info: 'fas fa-info-circle'
  }
  return icons[type] || icons.info
}

const formatMessage = (message) => {
  // 将换行符转换为 <br> 标签
  if (typeof message === 'string') {
    return message.replace(/\n/g, '<br>')
  }
  return message
}

const removeToast = (id) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

const showToast = (message, type = 'info', duration = 4000) => {
  const id = ++toastIdCounter
  const toast = {
    id,
    message,
    type,
    duration
  }
  
  toasts.value.push(toast)
  
  // 自动移除
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }
  
  return id
}

// 暴露方法给全局使用
onMounted(() => {
  window.toastService = {
    show: showToast,
    success: (message, duration) => showToast(message, 'success', duration),
    error: (message, duration) => showToast(message, 'error', duration),
    warning: (message, duration) => showToast(message, 'warning', duration),
    info: (message, duration) => showToast(message, 'info', duration)
  }
})

onUnmounted(() => {
  if (window.toastService) {
    delete window.toastService
  }
})

// 暴露给父组件
defineExpose({
  show: showToast,
  success: (message, duration) => showToast(message, 'success', duration),
  error: (message, duration) => showToast(message, 'error', duration),
  warning: (message, duration) => showToast(message, 'warning', duration),
  info: (message, duration) => showToast(message, 'info', duration)
})
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: var(--border-radius, 8px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background-color: var(--card-background, #ffffff);
  border-left: 4px solid;
  pointer-events: auto;
  cursor: pointer;
  transition: all 0.3s ease;
  animation: slideInRight 0.3s ease;
}

.toast:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  transform: translateX(-4px);
}

.toast-success {
  border-left-color: var(--primary-color, var(--sc-color-primary));
  background-color: #f0f9ed;
}

.toast-error {
  border-left-color: var(--danger-color, var(--sc-color-error));
  background-color: #fef0f0;
}

.toast-warning {
  border-left-color: var(--sc-color-warning);
  background-color: #fdf6ec;
}

.toast-info {
  border-left-color: #409eff;
  background-color: #ecf5ff;
}

.toast-icon {
  flex-shrink: 0;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.toast-success .toast-icon {
  color: var(--primary-color, var(--sc-color-primary));
}

.toast-error .toast-icon {
  color: var(--danger-color, var(--sc-color-error));
}

.toast-warning .toast-icon {
  color: var(--sc-color-warning);
}

.toast-info .toast-icon {
  color: #409eff;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-message {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-color, var(--sc-color-text));
  word-wrap: break-word;
}

.toast-close {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--secondary-color, #999999);
  transition: color 0.2s ease;
  border-radius: 4px;
}

.toast-close:hover {
  color: var(--text-color, var(--sc-color-text));
  background-color: rgba(0, 0, 0, 0.05);
}

/* 动画效果 */
.toast-enter-active {
  animation: slideInRight 0.3s ease;
}

.toast-leave-active {
  animation: slideOutRight 0.3s ease;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOutRight {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .toast-container {
    top: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }
  
  .toast {
    padding: 12px;
  }
  
  .toast-message {
    font-size: 13px;
  }
}
</style>


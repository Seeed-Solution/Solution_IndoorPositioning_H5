<template>
  <div v-if="show" class="modal-overlay" @click="handleBackdropClick">
    <div class="edit-tracker-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">{{ $t('tracker.editTrackerModal.title') }}</h3>
        <button class="btn-close" @click="closeModal" :title="$t('tracker.editTrackerModal.close')">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">{{ $t('tracker.editTrackerModal.deviceName') }}</label>
          <input 
            v-model="formData.deviceName"
            type="text" 
            class="form-input"
            :class="{ 'error': errors.deviceName }"
            :placeholder="$t('tracker.editTrackerModal.deviceNamePlaceholder')"
            maxlength="20"
            @input="clearError('deviceName')"
          />
          <div v-if="errors.deviceName" class="error-message">
            {{ errors.deviceName }}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">{{ $t('tracker.editTrackerModal.deviceEui') }}</label>
          <input 
            :value="formData.deviceEui"
            type="text" 
            class="form-input readonly"
            readonly
            :placeholder="$t('tracker.editTrackerModal.deviceEuiPlaceholder')"
          />
        </div>

        <div class="form-group">
          <label class="form-label">{{ $t('tracker.editTrackerModal.deviceGroup') }}</label>
          <div class="select-wrapper">
            <select 
              v-model="formData.deviceGroup"
              class="form-select"
              :class="{ 'error': errors.deviceGroup }"
              @change="clearError('deviceGroup')"
            >
              <option value="">{{ $t('tracker.editTrackerModal.selectGroup') }}</option>
              <option v-for="group in availableGroups" :key="group.id" :value="group.id">
                {{ group.group_name }}
              </option>
            </select>
            <i class="fas fa-chevron-down select-icon"></i>
          </div>
          <div v-if="errors.deviceGroup" class="error-message">
            {{ errors.deviceGroup }}
          </div>
        </div>

        <div class="form-group star-group">
          <div class="star-label-container">
            <label class="form-label">{{ $t('tracker.editTrackerModal.star') }}</label>
            <div class="star-toggle-container">
              <input 
                v-model="formData.starred"
                type="checkbox" 
                id="starToggle"
                class="star-toggle-input"
              />
              <label for="starToggle" class="star-toggle-label">
                <div class="star-toggle-slider">
                  <div class="star-toggle-knob"></div>
                </div>
              </label>
            </div>
          </div>
        </div>

        <!-- Error message area -->
        <div v-if="generalError" class="general-error-message">
          {{ generalError }}
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          class="btn btn-cancel" 
          @click="closeModal"
          :disabled="isLoading"
        >
          {{ $t('tracker.editTrackerModal.cancel') }}
        </button>
        <button 
          class="btn btn-save"
          @click="saveTracker"
          :disabled="isLoading || !isFormValid"
        >
          <span v-if="isLoading">
            <i class="fas fa-spinner fa-spin"></i> {{ $t('tracker.editTrackerModal.saving') }}
          </span>
          <span v-else>{{ $t('tracker.editTrackerModal.save') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  tracker: {
    type: Object,
    default: () => ({})
  },
  availableGroups: {
    type: Array,
    default: () => []
  },
  externalError: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'save'])

// 表单数据
const formData = ref({
  deviceName: '',
  deviceEui: '',
  deviceGroup: '',
  starred: false
})

// 错误状态
const errors = ref({
  deviceName: '',
  deviceGroup: ''
})

const generalError = ref('')
const isLoading = ref(false)

// 计算属性
const isFormValid = computed(() => {
  return formData.value.deviceName.trim() && 
         formData.value.deviceGroup !== '' &&
         !Object.values(errors.value).some(error => error)
})

// 监听传入的tracker数据变化
watch(() => props.tracker, (newTracker) => {
  if (newTracker && Object.keys(newTracker).length > 0) {
    initializeForm(newTracker)
  }
}, { immediate: true, deep: true })

// 监听模态框显示状态
watch(() => props.show, (newShow) => {
  if (newShow && props.tracker) {
    initializeForm(props.tracker)
    clearAllErrors()
  }
})

// 监听外部错误
watch(() => props.externalError, (newError) => {
  if (newError) {
    generalError.value = newError
    isLoading.value = false
  }
})

// 初始化表单数据
const initializeForm = (tracker) => {
  formData.value = {
    deviceName: tracker.device_name || tracker.name || '',
    deviceEui: tracker.trackerId || '',
    deviceGroup: tracker.group_id || tracker.group_id === 0 ? tracker.group_id : '',
    starred: tracker.starred || tracker.is_favorite || false
  }
}

// 清除特定字段错误
const clearError = (field) => {
  errors.value[field] = ''
  generalError.value = ''
}

// 清除所有错误
const clearAllErrors = () => {
  errors.value = {
    deviceName: '',
    deviceGroup: ''
  }
  generalError.value = ''
}

// 验证表单
const validateForm = () => {
  clearAllErrors()
  let isValid = true

  // 验证设备名称
  if (!formData.value.deviceName.trim()) {
    errors.value.deviceName = t('tracker.editTrackerModal.deviceNameRequired')
    isValid = false
  } else if (formData.value.deviceName.trim().length > 20) {
    errors.value.deviceName = t('tracker.editTrackerModal.deviceNameTooLong')
    isValid = false
  }

  // 验证设备分组
  if (formData.value.deviceGroup === '') {
    errors.value.deviceGroup = t('tracker.editTrackerModal.selectDeviceGroup')
    isValid = false
  }

  return isValid
}

// 关闭模态框
const closeModal = () => {
  if (!isLoading.value) {
    emit('close')
  }
}

// 处理背景点击
const handleBackdropClick = () => {
  closeModal()
}

// 保存设备信息
const saveTracker = async () => {
  if (!validateForm()) {
    return
  }

  try {
    isLoading.value = true
    generalError.value = ''
    
    // 准备保存的数据 - 符合DeviceUpdateRequest格式
    const saveData = {
      dev_eui: formData.value.deviceEui,
      device_name: formData.value.deviceName.trim(),
      group_id: formData.value.deviceGroup,
      is_favorite: formData.value.starred
    }

    // 发射保存事件到父组件
    emit('save', saveData)
    
  } catch (error) {
    console.error('[EditTrackerModal] Error saving tracker:', error)
    generalError.value = error.message || t('tracker.editTrackerModal.saveFailed')
  } finally {
    isLoading.value = false
  }
}

// 组件挂载时初始化
onMounted(() => {
  if (props.show && props.tracker) {
    initializeForm(props.tracker)
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.edit-tracker-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--sc-color-border);
  background: var(--sc-color-bg-layout);
}

.modal-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--sc-color-text);
}

.btn-close {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: var(--sc-color-text-secondary);
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  font-size: 1rem;
}

.btn-close:hover {
  background: var(--sc-color-border);
  color: var(--sc-color-text);
}

.modal-body {
  padding: 2rem;
  flex: 1;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--sc-color-text);
  margin-bottom: 0.5rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid var(--sc-color-border);
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s;
  box-sizing: border-box;
  background: white;
}

.form-input:focus {
  outline: none;
  border-color: var(--sc-color-info);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.form-input.readonly {
  background-color: var(--sc-color-bg-layout);
  color: var(--sc-color-text-secondary);
  cursor: not-allowed;
}

.form-input.error {
  border-color: var(--sc-color-error);
}

.form-input.error:focus {
  border-color: var(--sc-color-error);
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.select-wrapper {
  position: relative;
}

.form-select {
  width: 100%;
  padding: 0.75rem 2.5rem 0.75rem 1rem;
  border: 2px solid var(--sc-color-border);
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s;
  box-sizing: border-box;
  background: white;
  appearance: none;
  cursor: pointer;
}

.form-select:focus {
  outline: none;
  border-color: var(--sc-color-info);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.form-select.error {
  border-color: var(--sc-color-error);
}

.form-select.error:focus {
  border-color: var(--sc-color-error);
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.select-icon {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--sc-color-text-secondary);
  pointer-events: none;
  font-size: 0.8rem;
}

.star-group {
  margin-bottom: 2rem;
}

.star-label-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.star-toggle-container {
  position: relative;
}

.star-toggle-input {
  display: none;
}

.star-toggle-label {
  cursor: pointer;
  display: block;
}

.star-toggle-slider {
  width: 52px;
  height: 28px;
  background-color: var(--sc-color-border);
  border-radius: 14px;
  position: relative;
  transition: background-color 0.3s;
}

.star-toggle-input:checked + .star-toggle-label .star-toggle-slider {
  background-color: var(--sc-color-info);
}

.star-toggle-knob {
  width: 24px;
  height: 24px;
  background-color: white;
  border-radius: 12px;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.3s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.star-toggle-input:checked + .star-toggle-label .star-toggle-knob {
  transform: translateX(24px);
}

.error-message {
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background-color: var(--sc-status-danger-bg);
  border: 1px solid var(--sc-status-danger-bg);
  border-radius: 6px;
  color: var(--sc-status-danger-fg);
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-message::before {
  content: "\f071";
  font-family: "Font Awesome 5 Free";
  font-weight: 900;
  color: var(--sc-color-error);
  flex-shrink: 0;
}

.general-error-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background-color: var(--sc-status-danger-bg);
  border: 1px solid var(--sc-status-danger-bg);
  border-radius: 8px;
  color: var(--sc-status-danger-fg);
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.general-error-message::before {
  content: "\f071";
  font-family: "Font Awesome 5 Free";
  font-weight: 900;
  color: var(--sc-color-error);
  flex-shrink: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-top: 1px solid var(--sc-color-border);
  background: var(--sc-color-bg-layout);
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-cancel {
  background: var(--sc-color-text-secondary);
  color: white;
}

.btn-cancel:hover:not(:disabled) {
  background: #545b62;
}

.btn-save {
  background: var(--sc-color-info);
  color: white;
}

.btn-save:hover:not(:disabled) {
  background: var(--sc-color-info);
}

.btn:disabled {
  background: var(--sc-color-text-tertiary);
  cursor: not-allowed;
  opacity: 0.7;
}

.fa-spinner {
  font-size: 0.9rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .edit-tracker-modal {
    width: 95%;
    margin: 1rem;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem 1.5rem;
  }
  
  .modal-title {
    font-size: 1.1rem;
  }
  
  .form-input,
  .form-select {
    padding: 0.625rem 0.875rem;
  }
  
  .form-select {
    padding-right: 2.25rem;
  }
  
  .modal-footer {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .btn {
    width: 100%;
  }
}
</style>
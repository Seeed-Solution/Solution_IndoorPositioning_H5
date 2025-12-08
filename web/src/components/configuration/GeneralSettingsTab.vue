<template>
  <div class="general-settings-tab">
    <h3><i class="fas fa-cog"></i> {{ t('config.generalSettings.title') }}</h3>
    
    <!-- 只读模式 - 只显示设置值 -->
    <div v-if="readOnly" class="settings-display">
      <div class="setting-item">
        <label>{{ t('config.generalSettings.signalPropagationFactor') }}</label>
        <span class="setting-value">{{ editableSettings.signalPropagationFactor }}</span>
        <p class="info">{{ t('config.generalSettings.signalPropagationFactorInfo') }}</p>
      </div>
    </div>
    
    <!-- 编辑模式 - 显示表单和按钮 -->
    <form v-else @submit.prevent="saveSettings">
      <div class="setting-item">
        <label for="signalFactor">{{ t('config.generalSettings.signalPropagationFactor') }}</label>
        <input type="number" id="signalFactor" v-model.number="editableSettings.signalPropagationFactor" step="0.01" min="1" max="6" required />
        <p class="info">{{ t('config.generalSettings.signalPropagationFactorInfo') }}</p>
      </div>
      <!-- More general settings can be added here -->
      <div class="form-actions">
        <button type="submit" class="action-btn primary-btn">
          <i class="fas fa-check"></i> {{ t('config.generalSettings.applySettings') }}
        </button>
        <button type="button" @click="resetToOriginals" class="action-btn secondary-btn">
          <i class="fas fa-undo"></i> {{ t('config.generalSettings.resetSettings') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { notificationService } from '@/services/notificationService.js';

const { t } = useI18n();

const props = defineProps({
  initialSettings: {
    type: Object,
    default: () => ({ signalPropagationFactor: 2.5 }) // Default structure
  },
  readOnly: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['settings-updated']);

// Local reactive copy for editing
const editableSettings = ref({ signalPropagationFactor: 2.5 });

// Function to load settings from props into the local editable state
const loadSettings = (settingsFromProp) => {
  if (settingsFromProp && typeof settingsFromProp.signalPropagationFactor === 'number') {
    editableSettings.value = JSON.parse(JSON.stringify(settingsFromProp));
  } else {
    // Fallback to a default if prop is malformed or null
    editableSettings.value = { signalPropagationFactor: 2.5 };
  }
  console.log("GeneralSettingsTab: Settings loaded/updated", editableSettings.value);
};

// Watch for prop changes to update local state
watch(() => props.initialSettings, (newVal) => {
  loadSettings(newVal);
}, { deep: true, immediate: true }); // Immediate to load on component mount

onMounted(() => {
  // Covered by the immediate watcher
  // loadSettings(props.initialSettings);
});

const saveSettings = () => {
  if (editableSettings.value.signalPropagationFactor === null || 
      editableSettings.value.signalPropagationFactor < 1 || 
      editableSettings.value.signalPropagationFactor > 6) {
    notificationService.error(t('config.generalSettings.validationError'));
    return;
  }
  // Emit the updated settings object (a deep copy)
  emit('settings-updated', JSON.parse(JSON.stringify(editableSettings.value)));
  notificationService.success(t('config.generalSettings.settingsUpdated'));
};

const resetToOriginals = () => {
    // Reload from the prop, effectively resetting any local changes
    loadSettings(props.initialSettings);
    notificationService.success(t('config.generalSettings.settingsReset'));
}

// Expose method to parent component
defineExpose({ loadSettings });

</script>

<style scoped>
.general-settings-tab {
  padding: 1rem;
}

.general-settings-tab h3 {
  margin-bottom: 1.5rem;
  color: var(--primary-color-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.settings-display {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid #e9ecef;
}

.setting-item {
  margin-bottom: 1.5rem;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.general-settings-tab label {
  font-weight: 600;
  display: block;
  margin-bottom: 0.5rem;
  color: var(--secondary-color);
}

.setting-value {
  display: inline-block;
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--primary-color-dark);
  background: white;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  border: 1px solid #dee2e6;
  min-width: 60px;
}

.general-settings-tab input[type="number"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  width: 120px;
  box-sizing: border-box;
  font-size: 1rem;
}

.general-settings-tab input[type="number"]:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 2rem;
}

/* 按钮样式 */
.action-btn {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.primary-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

.primary-btn:hover {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.secondary-btn {
  background: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.secondary-btn:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.info {
  font-size: 0.85em;
  color: #6c757d;
  margin-top: 0.5rem;
  line-height: 1.4;
}
</style> 
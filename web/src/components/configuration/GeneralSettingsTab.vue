<template>
  <div class="general-settings-tab">
    <h3>General Settings</h3>
    <form @submit.prevent="saveSettings">
      <div>
        <label for="signalFactor">Signal Propagation Factor (n):</label>
        <input type="number" id="signalFactor" v-model.number="editableSettings.signalPropagationFactor" step="0.01" min="1" max="6" required />
        <p class="info">This value affects RSSI to distance conversion. Common range: Free space approx. 2.0, indoor environments may range from 1.8 to 4.0.</p>
      </div>
      <!-- More general settings can be added here -->
      <div class="form-actions">
        <button type="submit" class="button-primary">Apply & Update Settings</button>
        <button type="button" @click="resetToOriginals" class="button-light-blue">Reset to Initially Loaded Values</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';

const props = defineProps({
  initialSettings: {
    type: Object,
    default: () => ({ signalPropagationFactor: 2.5 }) // Default structure
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
    alert("Signal Propagation Factor must be between 1.0 and 6.0.");
    return;
  }
  // Emit the updated settings object (a deep copy)
  emit('settings-updated', JSON.parse(JSON.stringify(editableSettings.value)));
  alert('Settings have been updated and the main configuration has been notified. Actual saving to the server is handled in the main configuration.');
};

const resetToOriginals = () => {
    // Reload from the prop, effectively resetting any local changes
    loadSettings(props.initialSettings);
    alert("Settings have been reset to their initially loaded values.");
}

// Expose method to parent component
defineExpose({ loadSettings });

</script>

<style scoped>
.general-settings-tab div:not(.form-actions) {
  margin-bottom: 1rem;
}
.general-settings-tab label {
  font-weight: bold;
  display: block;
  margin-bottom: 0.3rem;
}
.general-settings-tab input[type="number"] {
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  width: 120px;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.info {
  font-size: 0.85em;
  color: #555;
  margin-top: 0.5rem;
}
</style> 
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
      <button type="submit">Apply & Update Settings</button>
    </form>
    <button @click="resetToOriginals">Reset to Initially Loaded Values</button>
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
.general-settings-tab div {
  margin-bottom: 10px;
}
.general-settings-tab label {
  margin-right: 10px;
  font-weight: bold;
}
.general-settings-tab input[type="number"] {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: 100px;
}
.general-settings-tab button {
  margin-top:10px;
  margin-right: 10px;
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  background-color: #007bff;
  color: white;
  cursor: pointer;
}
.general-settings-tab button[type="submit"] {
  background-color: #28a745; /* Green for save/apply */
}

.general-settings-tab button:hover {
  opacity: 0.9;
}
.info {
  font-size: 0.85em;
  color: #555;
  margin-top: 3px;
}
</style> 
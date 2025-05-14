<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { loadServerConfiguration, saveServerConfiguration } from '@/services/configApiService.js';

const props = defineProps({
  liveMqttStatus: {
    type: String,
    default: 'unknown',
  }
});

const emit = defineEmits(['settings-applied']);

const formState = ref({
  mqtt: {
    brokerHost: '',
    brokerPort: 1883,
    username: '',
    password: '',
    applicationID: '',
    topicPattern: '',
    clientID: '',
    enabled: true,
  },
  server: {
    port: 8022,
  },
  kalman: {
    processVariance: 1.0,
    measurementVariance: 10.0,
  },
});

const initialPasswordPlaceholder = '********';
const passwordField = ref('');
const isPasswordVisible = ref(false);

const loadingStatus = ref('idle');
const loadingError = ref('');
const saveStatus = ref('idle');
const saveError = ref('');

const mqttStatusMessage = computed(() => {
  let statusText = 'MQTT status is currently unknown.';
  let statusClass = 'info';
  let iconClass = 'fas fa-question-circle';

  if (!formState.value.mqtt.enabled) {
    statusText = 'MQTT client is Disabled in these settings. Save to apply.';
    statusClass = 'info';
    iconClass = 'fas fa-toggle-off';
  } else if (!formState.value.mqtt.brokerHost) {
    statusText = 'MQTT broker host not configured. MQTT will not connect.';
    statusClass = 'warn';
    iconClass = 'fas fa-exclamation-triangle';
  } else {
    switch (props.liveMqttStatus) {
      case 'connected':
        statusText = 'Live MQTT Status: Connected.';
        statusClass = 'success';
        iconClass = 'fas fa-check-circle';
        break;
      case 'connecting':
        statusText = 'Live MQTT Status: Connecting...';
        statusClass = 'info';
        iconClass = 'fas fa-spinner fa-spin';
        break;
      case 'disconnected':
        statusText = 'Live MQTT Status: Disconnected. Check settings or click "Apply Settings" to attempt reconnect.';
        statusClass = 'warn';
        iconClass = 'fas fa-plug';
        break;
      case 'disabled': 
        statusText = 'Live MQTT Status: Disabled by server.';
        statusClass = 'info';
        iconClass = 'fas fa-toggle-off';
        break;
      case 'misconfigured': 
        statusText = 'Live MQTT Status: Misconfigured on server.';
        statusClass = 'warn';
        iconClass = 'fas fa-exclamation-triangle';
        break;
      case 'error':
        statusText = 'Live MQTT Status: Connection Error.';
        statusClass = 'error';
        iconClass = 'fas fa-times-circle';
        break;
      default:
        statusText = 'Live MQTT Status: Unknown. MQTT is configured as enabled; click "Apply Settings" to ensure connection.';
        statusClass = 'info';
        iconClass = 'fas fa-question-circle';
        break;
    }
  }
  return { text: statusText, class: statusClass, icon: iconClass };
});

const fetchFullServerConfig = async () => {
  loadingStatus.value = 'loading';
  loadingError.value = '';
  try {
    const config = await loadServerConfiguration();
    console.log("[ServerSettings] Raw response from loadServerConfiguration:", JSON.stringify(config, null, 2));
    if (config && config.mqtt && config.server && config.kalman) {
      formState.value = {
        mqtt: { ...formState.value.mqtt, ...config.mqtt },
        server: { ...formState.value.server, ...config.server },
        kalman: { ...formState.value.kalman, ...config.kalman },
      };
      passwordField.value = config.mqtt.password ? initialPasswordPlaceholder : '';
      formState.value.mqtt.password = '';
      isPasswordVisible.value = false;
      loadingStatus.value = 'loaded';
    } else {
      console.error("[ServerSettings] API response for server config is missing expected structure.", config);
      loadingStatus.value = 'error';
      loadingError.value = 'Invalid data structure received from server.';
    }
  } catch (error) {
    console.error("Failed to fetch server config:", error);
    loadingStatus.value = 'error';
    loadingError.value = error.message || 'Unknown error';
  }
};

const applyAndSaveChanges = async () => {
  saveStatus.value = 'saving';
  saveError.value = '';

  const payload = JSON.parse(JSON.stringify(formState.value));
  if (passwordField.value && passwordField.value !== initialPasswordPlaceholder) {
    payload.mqtt.password = passwordField.value;
  } else {
    delete payload.mqtt.password; 
  }

  try {
    await saveServerConfiguration(payload);
    saveStatus.value = 'success';
    await fetchFullServerConfig(); 
    isPasswordVisible.value = false;
    emit('settings-applied');
  } catch (error) {
    console.error("Failed to save server config:", error);
    saveStatus.value = 'error';
    saveError.value = error.message || 'Unknown error';
  }
};

const passwordInputType = computed(() => isPasswordVisible.value ? 'text' : 'password');

const togglePasswordVisibility = () => {
  isPasswordVisible.value = !isPasswordVisible.value;
};

onMounted(() => {
  fetchFullServerConfig();
});

watch(() => props.liveMqttStatus, (newStatus) => {
  console.log("[ServerSettings] Live MQTT status prop changed to:", newStatus);
});

</script>

<template>
  <div class="server-settings-config-section settings-panel">
    <p :class="['status-display', mqttStatusMessage.class, 'mqtt-status-banner']">
        <i :class="mqttStatusMessage.icon"></i> {{ mqttStatusMessage.text }}
    </p>

    <div v-if="loadingStatus === 'loading'" class="status info"><i class="fas fa-spinner fa-spin"></i> Loading settings...</div>
    <div v-if="loadingStatus === 'error'" class="status error"><i class="fas fa-exclamation-triangle"></i> Failed to load settings: {{ loadingError }}</div>
    
    <form @submit.prevent="applyAndSaveChanges" v-if="loadingStatus === 'loaded'" class="settings-form">
      <div class="form-columns-container">
        <div class="form-column">
          <h4><i class="fas fa-network-wired"></i> MQTT Configuration Details <span v-if="!formState.mqtt.enabled">(Disabled)</span></h4>
          <div class="form-group horizontal">
            <label for="mqttBrokerHost">Broker Host:</label>
            <input type="text" id="mqttBrokerHost" v-model="formState.mqtt.brokerHost" :disabled="!formState.mqtt.enabled" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttBrokerPort">Broker Port:</label>
            <input type="number" id="mqttBrokerPort" v-model.number="formState.mqtt.brokerPort" :disabled="!formState.mqtt.enabled" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttUsername">Username:</label>
            <input type="text" id="mqttUsername" v-model="formState.mqtt.username" :disabled="!formState.mqtt.enabled" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttPassword">Password:</label>
            <div class="password-input-wrapper">
                <input :type="passwordInputType" id="mqttPassword" v-model="passwordField" :placeholder="initialPasswordPlaceholder" :disabled="!formState.mqtt.enabled" />
                <button type="button" @click="togglePasswordVisibility" class="button-icon-only" :disabled="!formState.mqtt.enabled">
                    <i :class="isPasswordVisible ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                </button>
            </div>
          </div>
          <div class="form-group horizontal">
            <label for="mqttApplicationID">Application ID (OrgID):</label>
            <input type="text" id="mqttApplicationID" v-model="formState.mqtt.applicationID" :disabled="!formState.mqtt.enabled" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttTopicPattern">Topic Pattern:</label>
            <input type="text" id="mqttTopicPattern" v-model="formState.mqtt.topicPattern" :disabled="!formState.mqtt.enabled" placeholder="e.g., /device_sensor_data/{ApplicationID}/+/+/+/+" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttClientID">Client ID (Optional):</label>
            <input type="text" id="mqttClientID" v-model="formState.mqtt.clientID" :disabled="!formState.mqtt.enabled" placeholder="Autogenerated if empty" />
          </div>
        </div>

        <div class="form-column">
          <h4><i class="fas fa-server"></i> Web Server Configuration</h4>
          <div class="form-group horizontal">
            <label for="serverPort">Server Port:</label>
            <input type="number" id="serverPort" v-model.number="formState.server.port" />
          </div>

          <h4><i class="fas fa-filter"></i> Kalman Filter Parameters</h4>
          <div class="form-group horizontal">
            <label for="kalmanProcessVariance">Process Variance (Q):</label>
            <input type="number" step="any" id="kalmanProcessVariance" v-model.number="formState.kalman.processVariance" />
          </div>
          <div class="form-group horizontal">
            <label for="kalmanMeasurementVariance">Measurement Variance (R):</label>
            <input type="number" step="any" id="kalmanMeasurementVariance" v-model.number="formState.kalman.measurementVariance" />
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="button-primary" :disabled="saveStatus === 'saving'">
          <i v-if="saveStatus === 'saving'" class="fas fa-spinner fa-spin"></i>
          {{ saveStatus === 'saving' ? 'Applying...' : 'Apply Settings & Reconnect MQTT' }}
        </button>
        <div v-if="saveStatus === 'success'" class="status success"><i class="fas fa-check-circle"></i> Settings applied successfully. MQTT will attempt to (re)connect if enabled.</div>
        <div v-if="saveStatus === 'error'" class="status error"><i class="fas fa-exclamation-triangle"></i> Failed to apply settings: {{ saveError }}</div>
      </div>
    </form>
  </div>
</template>

<style scoped>
.settings-panel {
  background-color: #fff;
  padding: 25px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
}

.settings-panel h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
  font-size: 1.4em;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.settings-panel h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #555;
  font-size: 1.15em;
}

.settings-form .form-columns-container {
  display: flex;
  flex-wrap: wrap;
  gap: 30px;
}

.form-column {
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-column .section-spacing {
  margin-top: 25px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 15px;
  align-items: baseline;
}

.form-group label {
  font-weight: 600;
  color: #444;
  font-size: 0.95em;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="password"] {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  box-sizing: border-box;
  font-size: 0.95em;
  transition: border-color 0.2s ease-in-out;
}

.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group input[type="password"]:focus {
  border-color: #007bff;
  outline: none;
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
  transform: scale(1.1);
  accent-color: #007bff;
}

.form-group input[type="checkbox"] + label, 
label[for*="mqttEnabled"] {
  display: inline-flex;
  align-items: center;
  font-weight: normal;
}

.form-group small {
  font-size: 0.8em;
  color: #777;
  margin-top: 2px;
}

.form-actions {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 15px;
}

.button.primary {
  background-color: #007bff;
  color: white;
  padding: 10px 18px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.button.primary:hover {
  background-color: #0056b3;
}

.button.primary:disabled {
  background-color: #a0c7e4;
  cursor: not-allowed;
}

.status {
  padding: 10px 15px;
  border-radius: 5px;
  margin-bottom: 15px;
  font-size: 0.95em;
  display: flex;
  align-items: center;
  gap: 8px;
}
.status.small {
  padding: 6px 10px;
  font-size: 0.85em;
  margin-bottom: 0;
}

.status.info {
  background-color: #e7f3fe;
  border: 1px solid #d0eaff;
  color: #0c5460;
}

.status.success {
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.status.warn {
  background-color: #fff3cd;
  border: 1px solid #ffeeba;
  color: #856404;
}

.status.error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.mqtt-status-banner {
    padding: 0.75rem 1rem;
    border-radius: var(--border-radius);
    margin-bottom: 1rem;
    text-align: center;
    font-weight: 500;
}
.mqtt-status-banner.success { background-color: var(--success-bg-color); border: 1px solid var(--success-border-color); color: var(--success-text-color); }
.mqtt-status-banner.warn { background-color: var(--warning-bg-color); border: 1px solid var(--warning-border-color); color: var(--warning-text-color); }
.mqtt-status-banner.error { background-color: var(--error-bg-color); border: 1px solid var(--error-border-color); color: var(--error-text-color); }
.mqtt-status-banner.info { background-color: var(--info-bg-color); border: 1px solid var(--info-border-color); color: var(--info-text-color); }

.form-group.horizontal,
.form-group-grid .form-group {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.form-group.horizontal label,
.form-group-grid .form-group label {
  flex-basis: 150px;
  flex-shrink: 0;
  margin-bottom: 0;
  text-align: right;
  padding-right: 10px;
}

.form-group.horizontal input[type="text"],
.form-group.horizontal input[type="number"],
.form-group.horizontal input[type="password"],
.form-group-grid .form-group input[type="text"],
.form-group-grid .form-group input[type="number"] {
  flex-grow: 1;
  width: auto;
}

.form-group.checkbox-group {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.form-group.checkbox-group label {
  flex-basis: 200px;
  text-align: left;
  margin-bottom: 0;
}
.form-group.checkbox-group input[type="checkbox"] {
 margin: 0;
 order: 1;
}
.form-group.checkbox-group label {
    order: 0;
}

.form-group.horizontal label {
  align-self: center;
}

.modal-overlay {
  /* Add any necessary styles for the modal overlay */
}

.password-note {
  font-size: 0.8em;
  color: #777;
  margin-top: 2px;
  padding-left: 160px;
  display: block;
  margin-bottom: 10px;
}

.password-input-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
}

.password-input-wrapper input[type="password"],
.password-input-wrapper input[type="text"] {
  flex-grow: 1;
  border-right: none;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.toggle-password-visibility {
  padding: 0.5em 0.75em;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-left: none; 
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: calc(2.25em + 2px);
  border-top-right-radius: var(--border-radius, 4px);
  border-bottom-right-radius: var(--border-radius, 4px);
  color: #333;
}

.toggle-password-visibility:hover {
  background-color: #e0e0e0;
}

.toggle-password-visibility:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.password-note {
  grid-column: 2 / -1;
  font-size: 0.8em;
  color: #666;
  margin-top: -0.5em;
  margin-bottom: 0.5em;
  display: block;
}

.form-group.horizontal label {
  align-self: center;
}

.button-icon-only {
    padding: 0.5rem;
    height: 100%;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    border-left: none;
    background-color: #f0f0f0;
}

.button-icon-only:hover {
    background-color: #e0e0e0;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="checkbox"] {
  padding: 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.95em;
  box-sizing: border-box;
}

.form-group input[type="checkbox"] {
    width: auto;
    margin-right: 0.5rem;
}

.form-group-checkbox {
    align-items: center;
    padding: 0.5rem 0;
}

.form-group-checkbox label {
    text-align: left;
    flex-basis: auto;
    font-weight: normal;
}

.form-actions {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color-light);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.form-actions button {
  min-width: 200px;
}

</style> 
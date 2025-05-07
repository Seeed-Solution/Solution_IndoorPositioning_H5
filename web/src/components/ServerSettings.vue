<script setup>
import { ref, onMounted, computed, defineProps, watch } from 'vue';
import axios from 'axios';

const props = defineProps({
  liveMqttStatus: {
    type: String,
    default: 'unknown',
  }
});

const formState = ref({
  mqtt: {
    brokerHost: '',
    brokerPort: 1883,
    username: '',
    password: '', // Will be handled carefully: display ********, only send if changed
    applicationID: '',
    topicPattern: '',
    clientID: '',
    enabled: true,
  },
  server: {
    port: 8000,
  },
  kalman: {
    processVariance: 1.0,
    measurementVariance: 10.0,
  },
});

const initialPasswordPlaceholder = '********'; // Placeholder for password if loaded
const passwordField = ref(''); // Separate ref for password input to detect changes
const isPasswordVisible = ref(false); // For password visibility toggle

const loadingStatus = ref('idle'); // idle, loading, loaded, error
const loadingError = ref('');
const saveStatus = ref('idle'); // idle, saving, success, error
const saveError = ref('');

// This ref will hold the status fetched via API, to combine with WebSocket updates
const initialApiMqttStatus = ref('unknown');

const mqttStatusMessage = computed(() => {
  let statusText = 'MQTT status is currently unknown.';
  let statusClass = 'info';
  let iconClass = 'fas fa-question-circle'; // Default icon

  // Prioritize live status from WebSocket if it's not 'unknown'
  const currentStatus = props.liveMqttStatus !== 'unknown' ? props.liveMqttStatus : initialApiMqttStatus.value;

  if (!formState.value.mqtt.enabled) {
    statusText = 'MQTT client is disabled in settings.';
    statusClass = 'info';
    iconClass = 'fas fa-toggle-off';
  } else if (!formState.value.mqtt.brokerHost) {
    statusText = 'MQTT broker host not configured.';
    statusClass = 'warn';
    iconClass = 'fas fa-exclamation-triangle';
  } else {
    // Use the determined currentStatus (from WS or API)
    switch (currentStatus) {
      case 'connected':
        statusText = 'MQTT: Connected to broker.';
        statusClass = 'success';
        iconClass = 'fas fa-check-circle';
        break;
      case 'connecting':
        statusText = 'MQTT: Connecting...';
        statusClass = 'info';
        iconClass = 'fas fa-spinner fa-spin';
        break;
      case 'disconnected':
        statusText = 'MQTT: Disconnected.';
        statusClass = 'warn';
        iconClass = 'fas fa-plug';
        break;
      case 'disabled': // Set by backend if MQTT explicitly disabled during setup
        statusText = 'MQTT: Disabled by server configuration.';
        statusClass = 'info';
        iconClass = 'fas fa-toggle-off';
        break;
      case 'misconfigured': // Set by backend if essential parts missing
        statusText = 'MQTT: Misconfigured (e.g., missing broker host).';
        statusClass = 'warn';
        iconClass = 'fas fa-exclamation-triangle';
        break;
      case 'error':
        statusText = 'MQTT: Connection error or setup failure.';
        statusClass = 'error';
        iconClass = 'fas fa-times-circle';
        break;
      default: // 'unknown' or any other case
        statusText = 'MQTT: Status unavailable. Configured to connect.';
        statusClass = 'info';
        iconClass = 'fas fa-question-circle';
        break;
    }
  }
  return { text: statusText, class: statusClass, icon: iconClass };
});

const fetchInitialMqttStatus = async () => {
    try {
        const response = await axios.get('/api/mqtt-status', {
             headers: { 'Cache-Control': 'no-cache' } // Ensure fresh status
        });
        if (response.data && response.data.status) {
            initialApiMqttStatus.value = response.data.status;
            console.log("[ServerSettings] Initial MQTT status from API:", initialApiMqttStatus.value);
        }
    } catch (error) {
        console.error("[ServerSettings] Failed to fetch initial MQTT status:", error);
        initialApiMqttStatus.value = 'error_fetching'; // Indicate API fetch error
    }
};

const fetchServerRuntimeConfig = async () => {
  loadingStatus.value = 'loading';
  loadingError.value = '';
  try {
    const response = await axios.get('/api/server-runtime-config', {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache', // For HTTP/1.0 proxies/clients.
        'Expires': '0', // Proxies.
      }
    });
    console.log("[ServerSettings] Raw response from /api/server-runtime-config:", JSON.stringify(response.data, null, 2));
    if (response.data && response.data.mqtt && response.data.server && response.data.kalman) {
      formState.value = {
        mqtt: { 
            ...formState.value.mqtt, 
            ...response.data.mqtt 
        },
        server: { 
            ...formState.value.server,
            ...response.data.server 
        },
        kalman: { 
            ...formState.value.kalman,
            ...response.data.kalman 
        },
      };
      
      // Directly use the password from the server response for passwordField.
      // If it's null or undefined, default to an empty string.
      passwordField.value = response.data.mqtt.password || '';
      
      // The main formState.mqtt.password is not directly used by UI input, clear it.
      formState.value.mqtt.password = ''; 
      isPasswordVisible.value = false; // Ensure password is not visible on load/fetch
      
      loadingStatus.value = 'loaded';
      console.log("[ServerSettings] Populated formState:", JSON.stringify(formState.value, null, 2));
    } else {
        console.error("[ServerSettings] API response for server runtime config is missing expected structure.", response.data);
        loadingStatus.value = 'error';
        loadingError.value = 'Invalid data structure received from server.';
    }
    // Now also fetch initial MQTT status after fetching the main config
    await fetchInitialMqttStatus();
  } catch (error) {
    console.error("Failed to fetch server runtime config:", error);
    loadingStatus.value = 'error';
    loadingError.value = error.response?.data?.detail || error.message || 'Unknown error';
  }
};

const saveServerRuntimeConfig = async () => {
  saveStatus.value = 'saving';
  saveError.value = '';

  const passwordValueBeforeSave = passwordField.value; // Capture current input value

  // Construct payload, including password only if it has been changed from placeholder or filled
  const payload = JSON.parse(JSON.stringify(formState.value)); // Deep copy
  if (passwordField.value && passwordField.value !== initialPasswordPlaceholder) {
    payload.mqtt.password = passwordField.value;
  } else {
    // If password field is placeholder or empty, don't send password field at all
    // This tells backend not to update it if it's not provided in payload
    // Pydantic `Optional` fields if not present in payload are not updated by default.
    delete payload.mqtt.password; 
  }

  try {
    await axios.post('/api/server-runtime-config', payload);
    saveStatus.value = 'success';
    
    // Fetch the latest config for all fields. This will set passwordField to '********' or ''
    await fetchServerRuntimeConfig(); 

    // If user had entered a new password (not placeholder, not empty), restore that value to the field.
    // Otherwise, the '********' or '' set by fetchServerRuntimeConfig is correct.
    if (passwordValueBeforeSave !== initialPasswordPlaceholder && passwordValueBeforeSave !== '') {
      passwordField.value = passwordValueBeforeSave;
    }
    
    isPasswordVisible.value = false; // Ensure password is not visible after save

  } catch (error) {
    console.error("Failed to save server runtime config:", error);
    saveStatus.value = 'error';
    saveError.value = error.response?.data?.detail || error.message || 'Unknown error';
  }
};

const passwordInputType = computed(() => isPasswordVisible.value ? 'text' : 'password');

const togglePasswordVisibility = () => {
  isPasswordVisible.value = !isPasswordVisible.value;
};

onMounted(() => {
  fetchServerRuntimeConfig();
});

// Optional: Watch the liveMqttStatus prop for direct updates if needed for other logic
// watch(() => props.liveMqttStatus, (newStatus) => {
//   console.log("[ServerSettings] Live MQTT status prop changed to:", newStatus);
// });

</script>

<template>
  <div class="server-settings-config-section settings-panel">
    <h3><i class="fas fa-cogs"></i> Server Runtime Configuration</h3>
    <div v-if="loadingStatus === 'loading'" class="status info"><i class="fas fa-spinner fa-spin"></i> Loading settings...</div>
    <div v-if="loadingStatus === 'error'" class="status error"><i class="fas fa-exclamation-triangle"></i> Failed to load settings: {{ loadingError }}</div>
    
    <form @submit.prevent="saveServerRuntimeConfig" v-if="loadingStatus === 'loaded'" class="settings-form">
      <div class="form-columns-container">
        <!-- Column 1: MQTT Configuration -->
        <div class="form-column">
          <h4><i class="fas fa-network-wired"></i> MQTT Configuration</h4>
          
          <!-- Applying horizontal layout to MQTT fields -->
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
              <input :type="passwordInputType" id="mqttPassword" v-model="passwordField" placeholder="" :disabled="!formState.mqtt.enabled" />
              <button type="button" @click="togglePasswordVisibility" class="toggle-password-visibility" :disabled="!formState.mqtt.enabled">
                <i :class="['fas', isPasswordVisible ? 'fa-eye-slash' : 'fa-eye']"></i>
              </button>
            </div>
          </div>
          
          <div class="form-group horizontal">
            <label for="mqttApplicationID">Application ID (OrgID):</label>
            <input type="text" id="mqttApplicationID" v-model="formState.mqtt.applicationID" :disabled="!formState.mqtt.enabled" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttTopicPattern">Topic Pattern:</label>
            <input type="text" id="mqttTopicPattern" v-model="formState.mqtt.topicPattern" :disabled="!formState.mqtt.enabled" />
          </div>
          <div class="form-group horizontal">
            <label for="mqttClientID">Client ID (Optional):</label>
            <input type="text" id="mqttClientID" v-model="formState.mqtt.clientID" :disabled="!formState.mqtt.enabled" />
          </div>
        </div>

        <!-- Column 2: Web Server & Kalman -->
        <div class="form-column">
          <h4><i class="fas fa-server"></i> Web Server Configuration</h4>
          <div class="form-group horizontal">
            <label for="serverPort">Server Port:</label>
            <input type="number" id="serverPort" v-model.number="formState.server.port" />
          </div>

          <h4 class="section-spacing"><i class="fas fa-filter"></i> Kalman Filter Parameters</h4>
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
        <button type="submit" class="button primary" :disabled="saveStatus === 'saving'">
          <i :class="saveStatus === 'saving' ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i> 
          {{ saveStatus === 'saving' ? 'Saving...' : 'Save Configuration' }}
        </button>
        <div v-if="saveStatus === 'success'" class="status success small"><i class="fas fa-check-circle"></i> Settings saved successfully.</div>
        <div v-if="saveStatus === 'error'" class="status error small"><i class="fas fa-exclamation-triangle"></i> Failed to save: {{ saveError }}</div>
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
  flex-wrap: wrap; /* Allow wrapping on smaller screens */
  gap: 30px; /* Space between columns */
}

.form-column {
  flex: 1; /* Each column takes equal space */
  min-width: 300px; /* Minimum width before wrapping */
  display: flex;
  flex-direction: column;
  gap: 15px; /* Space between form groups within a column */
}

.form-column .section-spacing {
  margin-top: 25px; /* Add space before a new h4 within the same column */
}

.form-group {
  display: flex;
  flex-direction: column; /* Stack label and input vertically */
  gap: 6px; /* Space between label and input */
}

.form-group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); /* Responsive grid for grouped items */
  gap: 15px; /* Space between grid items */
  /* Align items in the grid group to the baseline for better visual consistency if labels are different heights */
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
/* Adjust checkbox label alignment if needed */
.form-group input[type="checkbox"] + label, 
label[for*="mqttEnabled"] { /* Target specifically if structure is input then label */
  display: inline-flex; /* Align checkbox and label text */
  align-items: center;
  font-weight: normal; /* Labels for checkboxes usually normal weight */
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

.mqtt-status-indicator {
  margin-bottom: 20px; /* Specific margin for this status */
}

/* Ensure checkbox is next to label, not above */
div.form-group > label[for="mqttEnabled"] {
    order: 1; /* Puts label after checkbox if input is first */
    font-weight: 600; /* Keep consistent label weight */
}
div.form-group > input#mqttEnabled {
    order: 0; /* Puts checkbox before label */
    width: auto; /* Override full width for checkbox */
    margin-right: 8px; /* Space between checkbox and its label */
}
/* Re-target for checkbox with label directly after for better alignment */
.form-group.checkbox-group {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.form-group.checkbox-group label {
  /* font-weight: 600; */ /* Default form-group label style will apply */
  /* flex-basis: auto; */ /* Override fixed basis for checkbox label if needed, or set specific */
  flex-basis: 200px; /* Example: give it more space if needed */
  text-align: left; /* Override right-align for checkbox label */
  margin-bottom: 0;
}
.form-group.checkbox-group input[type="checkbox"] {
 margin: 0; /* Reset margin if handled by gap */
 order: 1; /* Ensure checkbox comes after label if preferred */
}
.form-group.checkbox-group label {
    order: 0;
}

/* Styles for horizontal form groups */
.form-group.horizontal,
.form-group-grid .form-group { /* Apply to direct children of grid too if they are simple groups */
  flex-direction: row;
  align-items: center; /* Vertically align label and input */
  gap: 10px; /* Space between label and input */
}

.form-group.horizontal label,
.form-group-grid .form-group label {
  flex-basis: 150px; /* Give label a fixed basis */
  flex-shrink: 0; /* Prevent label from shrinking */
  margin-bottom: 0; /* Remove bottom margin as it's now horizontal */
  text-align: right; /* Optional: align label text to the right */
  padding-right: 10px; /* Add some padding for spacing from input */
}

.form-group.horizontal input[type="text"],
.form-group.horizontal input[type="number"],
.form-group.horizontal input[type="password"],
.form-group-grid .form-group input[type="text"],
.form-group-grid .form-group input[type="number"] {
  flex-grow: 1; /* Allow input to take remaining space */
  width: auto; /* Override width: 100% if previously set */
}

/* Ensure checkbox group still behaves as intended */
.form-group.checkbox-group {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.form-group.checkbox-group label {
  /* font-weight: 600; */ /* Default form-group label style will apply */
  /* flex-basis: auto; */ /* Override fixed basis for checkbox label if needed, or set specific */
  flex-basis: 200px; /* Example: give it more space if needed */
  text-align: left; /* Override right-align for checkbox label */
  margin-bottom: 0;
}
.form-group.checkbox-group input[type="checkbox"] {
 margin: 0; /* Reset margin if handled by gap */
 order: 1; /* Ensure checkbox comes after label if preferred */
}
.form-group.checkbox-group label {
    order: 0;
}

/* Ensure checkbox is next to label, not above - old specific rules might conflict or be redundant */
/* Remove or comment out older specific mqttEnabled styling if it conflicts with new horizontal/checkbox-group approach */
/*
div.form-group > label[for="mqttEnabled"] {
    order: 1; 
    font-weight: 600; 
}
div.form-group > input#mqttEnabled {
    order: 0; 
    width: auto; 
    margin-right: 8px; 
}
*/

/* Specific styling for password note if needed */
.password-note {
  font-size: 0.8em;
  color: #777;
  margin-top: 2px;
  /* Adjust margin if it's outside a .form-group.horizontal or if that group needs specific padding */
  padding-left: 160px; /* Align with inputs if labels are 150px + 10px gap/padding */
  display: block; /* Ensure it takes its own line if needed */
  margin-bottom: 10px; /* Space before next form group */
}

.password-input-wrapper {
  display: flex;
  align-items: center;
  width: 100%; /* Ensure it takes the available width in the form group */
}

.password-input-wrapper input[type="password"],
.password-input-wrapper input[type="text"] {
  flex-grow: 1;
  border-right: none; /* Optional: if you want button to look attached */
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
  height: calc(2.25em + 2px); /* Match typical input height */
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
  grid-column: 2 / -1; /* Span across the input area if in grid */
  font-size: 0.8em;
  color: #666;
  margin-top: -0.5em; /* Adjust spacing if needed */
  margin-bottom: 0.5em;
  display: block;
}

/* Adjust label alignment if password-input-wrapper causes misalignment */
.form-group.horizontal label {
  align-self: center; /* Vertically center label with the input group */
}

.modal-overlay {
  /* Add any necessary styles for the modal overlay */
}

</style> 
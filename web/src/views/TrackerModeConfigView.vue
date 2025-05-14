<template>
  <div class="tracker-mode-config-view page-container">
    <h1 class="page-title">Tracker Mode Configuration</h1>
    <p class="info-banner status-display info" v-if="statusMessage">{{ statusMessage }}</p>

    <div class="config-management card">
      <div class="card-header"><h2>Master Configuration Management</h2></div>
      <div class="card-content">
        <!-- <input type="file" @change="handleImportMasterConfigFile" accept=".json" ref="importMasterFileRef" style="display: none;" /> -->
        <!-- <button @click="triggerImportMasterFile" class="button-primary">Import Configuration & Update Server (JSON)</button> -->
        
        <label for="jsonImportTracker">Paste Master Configuration JSON here:</label>
        <textarea id="jsonImportTracker" v-model="jsonInputForImport" rows="8" 
                  :placeholder="jsonPlaceholderText"></textarea>
        <button @click="handleImportMasterConfigJson" class="button-primary">Import & Update Server (from Textarea)</button>

        <p v-if="!currentFullConfig.map && !statusMessage.includes('Processing')" class="status-display warning">Please import a master configuration file first.</p>
        <p v-if="currentFullConfig.map" class="status-display success">
          Current master configuration loaded: {{ currentFullConfig.map.name || 'Unnamed Map' }}.
          (Beacons: {{ currentFullConfig.beacons.length }}, Map Entities: {{ currentFullConfig.map.entities?.length || 0 }})
        </p>
        <button @click="clearTrackerConfig" v-if="currentFullConfig.map" class="button-danger button-small">Clear This Tracker Configuration</button>
      </div>
    </div>

    <!-- Server Settings and Status Section -->
    <div class="server-status-and-settings card">
        <div class="card-header"> 
            <h2>Server Status & Runtime Configuration</h2>
        </div>
        <div class="card-content">
            <div class="status-indicators-and-controls">
                 <p class="info-banner info">
                    WebSocket Status: <span :class="wsStatus === 'connected' ? 'status-connected' : 'status-disconnected'">{{ wsStatus }}</span>
                    <span v-if="wsStatus === 'connected'"> | MQTT Status (Live): <span :class="['mqtt-status-indicator-inline', mqttStatusDisplay.class]"><i :class="mqttStatusDisplay.icon"></i> {{ mqttStatusDisplay.text }}</span></span>
                </p>
                <div class="mqtt-controls">
                    <button 
                        @click="connectMqtt"
                        :disabled="isConnectingMqtt || (liveMqttStatusForServerSettings === 'connected' && currentServerConfig?.mqtt?.enabled)"
                        class="button-success">
                        <i v-if="isConnectingMqtt" class="fas fa-spinner fa-spin"></i>
                        {{ (liveMqttStatusForServerSettings === 'connected' && currentServerConfig?.mqtt?.enabled) ? 'MQTT Enabled & Connected' : 'Enable & Connect MQTT' }}
                    </button>
                    <button 
                        @click="disconnectMqtt"
                        :disabled="isDisconnectingMqtt || liveMqttStatusForServerSettings === 'disabled' || liveMqttStatusForServerSettings === 'disconnected' || (currentServerConfig && !currentServerConfig.mqtt?.enabled)" 
                        class="button-danger">
                        <i v-if="isDisconnectingMqtt" class="fas fa-spinner fa-spin"></i>
                        {{ (currentServerConfig && !currentServerConfig.mqtt?.enabled) ? 'MQTT Is Disabled' : 'Disable MQTT' }}
                    </button>
                    <button @click="toggleServerSettingsPanel" class="button-primary">
                        <i class="fas fa-cog"></i> 
                        {{ isServerSettingsPanelVisible ? 'Hide Settings' : 'Show Settings' }}
                    </button>
                </div>
            </div>
            <div class="form-group tracker-id-filter-group">
              <label for="trackerIdFilter">Tracker ID Filter (e.g., tracker-*, specificID):</label>
              <input type="text" id="trackerIdFilter" v-model="trackerSettings.filterPattern" @input="saveTrackerSettingsDebounced" placeholder="Leave empty to show all" />
            </div>
            <hr class="section-divider" v-if="isServerSettingsPanelVisible">
            <ServerSettings 
                v-if="isServerSettingsPanelVisible"
                :live-mqtt-status="liveMqttStatusForServerSettings" 
                @settings-applied="handleServerSettingsApplied" 
            />
        </div>
    </div>
    
    <div v-if="currentFullConfig.map" class="map-display-tracker card">
      <div class="card-header"><h2>Map Preview (Live Trackers: {{ filteredTrackerList.length }})</h2></div>
      <div class="card-content content-columns">
        <div class="map-view-wrapper">
          <MapView 
            v-if="currentFullConfig.map" 
            :config="currentFullConfig" 
            :trackers="filteredTrackerList" 
          />
        </div>
        <aside class="tracker-list-aside">
          <h4>Trackers ({{ filteredTrackerList.length }})</h4>
          <ul v-if="filteredTrackerList.length > 0">
            <li v-for="tracker in filteredTrackerList" :key="tracker.trackerId" class="tracker-item">
              <strong>{{ tracker.trackerId }}</strong>
              <span v-if="tracker.position" class="tracker-pos">
                X: {{ tracker.position.x.toFixed(2) }}, Y: {{ tracker.position.y.toFixed(2) }}
                <span v-if="tracker.position.accuracy">, Acc: {{ tracker.position.accuracy.toFixed(2) }}m</span>
              </span>
              <span v-else class="tracker-pos-na">No position data</span>
              <div v-if="tracker.timestamp" class="tracker-meta">
                 Last seen: {{ new Date(tracker.timestamp).toLocaleTimeString() }}
              </div>
            </li>
          </ul>
          <p v-else>No trackers matching filter, or no trackers received yet.</p>
        </aside>
      </div>
    </div>
     <p v-if="!currentFullConfig.map && wsStatus !== 'disconnected'" class="info-banner warning">
        WebSocket connected, but no map configuration loaded. Please import a master configuration to see trackers on a map.
    </p>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import MapView from '@/components/MapView.vue';
import ServerSettings from '@/components/ServerSettings.vue'; // Import ServerSettings
import { loadConfigFromLocalStorage, saveConfigToLocalStorage, clearConfigFromLocalStorage } from '@/services/localStorageService.js';
import { saveWebConfiguration, loadServerConfiguration, saveServerConfiguration } from '@/services/configApiService.js'; // Added for saving to server

const CONFIG_STORAGE_KEY = 'trackerModeConfig'; 
const TRACKER_SETTINGS_STORAGE_KEY = 'trackerModeUISettings';

// const importMasterFileRef = ref(null); // Removed
const jsonInputForImport = ref(''); // Added for textarea
const statusMessage = ref('');

const jsonPlaceholderText = `Paste your full configuration JSON here (map, beacons, settings). Example structure:
{
  "map": { "name": "My Map", "image": "data:image/png;base64,...", "width": 1000, "height": 800, "origin": {"x":0,"y":0}, "ppm": 10, "entities":[] },
  "beacons": [ { "uuid": "...", "major":1, "minor":1, "x":10,"y":20,"txPower":-59, "name":"B1" } ],
  "settings": { "signalPropagationFactor": 2.5 }
}`;

const initialMasterConfig = () => ({
  map: null,
  beacons: [],
  settings: { signalPropagationFactor: 2.5 },
});
const currentFullConfig = ref(initialMasterConfig()); 

const trackerSettings = ref({
  filterPattern: ''
});

const trackers = ref({}); 
const ws = ref(null);
const wsStatus = ref('disconnected');
const liveMqttStatusForServerSettings = ref('unknown'); // For ServerSettings prop
let saveSettingsTimeout = null;

const currentServerConfig = ref(null); // For storing full server config (mqtt.enabled, etc.)
const isServerSettingsPanelVisible = ref(false);
const isConnectingMqtt = ref(false);
const isDisconnectingMqtt = ref(false);

const trackerList = computed(() => {
    return Object.values(trackers.value).sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

const filteredTrackerList = computed(() => {
  if (!trackerSettings.value.filterPattern) {
    return trackerList.value;
  }
  try {
    const regex = new RegExp(trackerSettings.value.filterPattern, 'i');
    return trackerList.value.filter(tracker => regex.test(tracker.trackerId));
  } catch (e) {
    console.warn("Invalid regex in tracker filter:", e);
    return trackerList.value; 
  }
});

const mqttStatusDisplay = computed(() => {
  let statusText = 'MQTT: Unknown';
  let statusClass = 'info';
  let iconClass = 'fas fa-question-circle';

  // Check if currentServerConfig and its mqtt property exist before accessing enabled
  const mqttConfig = currentServerConfig.value?.mqtt;
  const mqttEnabledInConfig = mqttConfig?.enabled;

  if (mqttEnabledInConfig === false) { // Explicitly configured as disabled
    statusText = 'Disabled in Config'; 
    statusClass = 'info'; 
    iconClass = 'fas fa-toggle-off';
  } else if (mqttConfig && !mqttConfig.brokerHost && mqttEnabledInConfig) { // Configured as enabled but no host
    statusText = 'Enabled, No Broker Host';
    statusClass = 'warn';
    iconClass = 'fas fa-exclamation-triangle';
  } else if (mqttEnabledInConfig) { // Configured as enabled, use live status
      switch (liveMqttStatusForServerSettings.value) {
        case 'connected': statusText = 'Connected'; statusClass = 'success'; iconClass = 'fas fa-check-circle'; break;
        case 'connecting': statusText = 'Connecting...'; statusClass = 'info'; iconClass = 'fas fa-spinner fa-spin'; break;
        case 'disconnected': statusText = 'Disconnected'; statusClass = 'warn'; iconClass = 'fas fa-plug'; break;
        case 'disabled': statusText = 'Disabled by Server'; statusClass = 'info'; iconClass = 'fas fa-toggle-off'; break; // This state means server override
        case 'misconfigured': statusText = 'Misconfigured on Server'; statusClass = 'warn'; iconClass = 'fas fa-exclamation-triangle'; break;
        case 'error': statusText = 'Connection Error'; statusClass = 'error'; iconClass = 'fas fa-times-circle'; break;
        default: 
          statusText = `Live: ${liveMqttStatusForServerSettings.value}`;
          if (liveMqttStatusForServerSettings.value === 'unknown' && mqttConfig?.brokerHost) {
            statusText = "Enabled, Status Unknown";
          }
          break; 
      }
  } else if (liveMqttStatusForServerSettings.value !== 'unknown') {
    // If config not loaded yet, but we have a live status, show that primarily
     switch (liveMqttStatusForServerSettings.value) {
        case 'connected': statusText = 'Connected'; statusClass = 'success'; iconClass = 'fas fa-check-circle'; break;
        case 'connecting': statusText = 'Connecting...'; statusClass = 'info'; iconClass = 'fas fa-spinner fa-spin'; break;
        case 'disconnected': statusText = 'Disconnected'; statusClass = 'warn'; iconClass = 'fas fa-plug'; break;
        case 'disabled': statusText = 'Disabled by Server'; statusClass = 'info'; iconClass = 'fas fa-toggle-off'; break;
        case 'misconfigured': statusText = 'Misconfigured on Server'; statusClass = 'warn'; iconClass = 'fas fa-exclamation-triangle'; break;
        case 'error': statusText = 'Connection Error'; statusClass = 'error'; iconClass = 'fas fa-times-circle'; break;
        default: statusText = `Live: ${liveMqttStatusForServerSettings.value}`; break;
      }
  }
  // else, it remains 'MQTT: Unknown' from initialization

  return { text: statusText, class: statusClass, icon: iconClass };
});

const connectWebSocket = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`; 
    ws.value = new WebSocket(wsUrl);
    wsStatus.value = 'connecting';

    ws.value.onopen = () => { 
        wsStatus.value = 'connected'; 
        fetchFullServerConfig(); // Fetch server config once WebSocket is connected
    };
    ws.value.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            if (message.type === 'initial_state') {
                trackers.value = message.data || {};
            } else if (message.type === 'tracker_update') {
                const updatedTrackerId = Object.keys(message.data)[0];
                if (updatedTrackerId) {
                     trackers.value = { ...trackers.value, [updatedTrackerId]: message.data[updatedTrackerId] };
                }
            } else if (message.type === 'mqtt_status_update') { 
                if (message.data && typeof message.data.status === 'string') {
                    liveMqttStatusForServerSettings.value = message.data.status;
                    // If MQTT becomes disabled via WebSocket, ensure our currentServerConfig reflects this if it was enabled
                    if (message.data.status === 'disabled' && currentServerConfig.value && currentServerConfig.value.mqtt.enabled) {
                        // fetchFullServerConfig(); // Option: refetch to get the definitive state including enabled flag
                        // Or, assume if server says disabled, it means enabled flag is now false or effectively false
                         if(currentServerConfig.value) currentServerConfig.value.mqtt.enabled = false;
                    }
                }
            }
        } catch (error) { console.error('TrackerModeConfigView: WebSocket message parse error:', error); }
    };
    ws.value.onerror = (error) => { wsStatus.value = 'error'; console.error('TrackerModeConfigView: WebSocket error:', error); };
    ws.value.onclose = () => { wsStatus.value = 'disconnected'; };
};

const showStatus = (msg, type = 'info') => { // Added type parameter, defaulting to info
    statusMessage.value = `${type.toUpperCase()}: ${msg}`; 
    // Determine class based on type for better visual feedback if needed here
    setTimeout(() => { statusMessage.value = '' }, 7000); 
};
// const triggerImportMasterFile = () => { importMasterFileRef.value.click(); }; // Removed

// Replaces handleImportMasterConfigFile
const handleImportMasterConfigJson = async () => {
  if (!jsonInputForImport.value.trim()) {
    showStatus('JSON input is empty. Please paste configuration data.', 'error');
    return;
  }
  statusMessage.value = 'Processing configuration from textarea...';
  try {
    const jsonData = JSON.parse(jsonInputForImport.value);
    if (jsonData && jsonData.map && Array.isArray(jsonData.beacons) && jsonData.settings) {
      showStatus('Configuration parsed. Attempting to save to server...');
      try {
        const serverResponse = await saveWebConfiguration(jsonData);
        showStatus(serverResponse.message || 'Configuration successfully saved to server!', 'success');

        currentFullConfig.value = { 
          map: jsonData.map, 
          beacons: jsonData.beacons, 
          settings: { ...initialMasterConfig().settings, ...jsonData.settings } 
        };
        saveConfigToLocalStorage(CONFIG_STORAGE_KEY, currentFullConfig.value);
        jsonInputForImport.value = ''; // Clear textarea
      } catch (serverError) {
        console.error("Error saving configuration to server:", serverError);
        showStatus(`Failed to save configuration to server: ${serverError.response?.data?.detail || serverError.message || 'Unknown server error'}. Local configuration not updated.`, 'error');
      }
    } else { 
      showStatus('Invalid JSON structure. Ensure it has map, beacons, and settings properties.', 'error'); 
    }
  } catch (parseError) { 
    showStatus(`Failed to parse JSON: ${parseError.message}`, 'error'); 
  }
};

const loadMasterConfig = () => {
  const loaded = loadConfigFromLocalStorage(CONFIG_STORAGE_KEY);
  if (loaded && loaded.map) { currentFullConfig.value = loaded; showStatus('Tracker mode master configuration loaded.'); }
  else { showStatus('No Tracker mode master configuration found. Please import one.'); currentFullConfig.value = initialMasterConfig(); }
};

const loadTrackerSettings = () => {
  const loaded = loadConfigFromLocalStorage(TRACKER_SETTINGS_STORAGE_KEY);
  if (loaded) trackerSettings.value = { ...trackerSettings.value, ...loaded };
};

const saveTrackerSettings = () => { saveConfigToLocalStorage(TRACKER_SETTINGS_STORAGE_KEY, trackerSettings.value); };
const saveTrackerSettingsDebounced = () => { clearTimeout(saveSettingsTimeout); saveSettingsTimeout = setTimeout(saveTrackerSettings, 500); };

const clearTrackerConfig = () => {
  if (confirm('Clear Tracker Mode master configuration?')) {
    clearConfigFromLocalStorage(CONFIG_STORAGE_KEY);
    currentFullConfig.value = initialMasterConfig();
    showStatus('Tracker Mode master configuration cleared.');
  }
};

const fetchFullServerConfig = async () => {
  try {
    statusMessage.value = "Loading server runtime configuration...";
    const config = await loadServerConfiguration();
    currentServerConfig.value = config;
    statusMessage.value = "Server runtime configuration loaded.";
    // Update liveMqttStatusForServerSettings based on fetched config if needed, though WebSocket is primary
    if (config && config.mqtt && !config.mqtt.enabled && liveMqttStatusForServerSettings.value !== 'disabled') {
        // liveMqttStatusForServerSettings.value = 'disabled'; // Or let WebSocket update this
    }
  } catch (error) {
    console.error("Failed to fetch full server config:", error);
    statusMessage.value = `Error loading server runtime config: ${error.message}`;
    currentServerConfig.value = null; // Ensure it's null on error
  }
};

const connectMqtt = async () => {
  if (!currentServerConfig.value) {
    showStatus('Server configuration not loaded. Cannot enable MQTT.', 'error');
    await fetchFullServerConfig(); // Attempt to load it
    if (!currentServerConfig.value) return;
  }
  isConnectingMqtt.value = true;
  showStatus('Attempting to enable and connect MQTT...', 'info');
  try {
    const configToSave = JSON.parse(JSON.stringify(currentServerConfig.value));
    configToSave.mqtt.enabled = true;
    await saveServerConfiguration(configToSave);
    currentServerConfig.value = configToSave; // Update local state
    showStatus('MQTT enabled. Server will attempt to connect. Monitor status via WebSocket.', 'success');
    // Live status will update via WebSocket
  } catch (error) {
    showStatus(`Error enabling MQTT: ${error.message}`, 'error');
  } finally {
    isConnectingMqtt.value = false;
  }
};

const disconnectMqtt = async () => {
  if (!currentServerConfig.value) {
    showStatus('Server configuration not loaded. Cannot disable MQTT.', 'error');
    await fetchFullServerConfig(); // Attempt to load it
    if (!currentServerConfig.value) return;
  }
  isDisconnectingMqtt.value = true;
  showStatus('Attempting to disable MQTT...', 'info');
  try {
    const configToSave = JSON.parse(JSON.stringify(currentServerConfig.value));
    configToSave.mqtt.enabled = false;
    await saveServerConfiguration(configToSave);
    currentServerConfig.value = configToSave; // Update local state
    showStatus('MQTT disabled. Server will disconnect if connected.', 'success');
    // Live status will update via WebSocket, likely to 'disabled' or 'disconnected'
  } catch (error) {
    showStatus(`Error disabling MQTT: ${error.message}`, 'error');
  } finally {
    isDisconnectingMqtt.value = false;
  }
};

const toggleServerSettingsPanel = () => {
  isServerSettingsPanelVisible.value = !isServerSettingsPanelVisible.value;
  if (isServerSettingsPanelVisible.value && !currentServerConfig.value) {
      fetchFullServerConfig(); // Load if panel is opened and config not yet loaded
  }
};

const handleServerSettingsApplied = () => {
    showStatus('Server runtime settings applied. Fetching latest to ensure consistency.', 'info');
    fetchFullServerConfig(); // Refetch to update currentServerConfig after ServerSettings saves
    // MQTT status will update via WebSocket based on new settings saved by ServerSettings.vue
};

watch(trackerSettings, saveTrackerSettingsDebounced, { deep: true });

onMounted(() => { 
    loadMasterConfig(); 
    loadTrackerSettings(); 
    connectWebSocket(); 
    // fetchFullServerConfig(); // Moved to on WebSocket open for better timing
});
onUnmounted(() => { if (ws.value) { ws.value.onclose = null; ws.value.close(); } clearTimeout(saveSettingsTimeout); });

</script>

<style scoped>
.page-container { padding: 1.5rem; width: 100%; max-width: 1200px; margin: 0 auto; box-sizing: border-box; }
.page-title { font-size: 1.8rem; color: var(--primary-color-dark); margin-bottom: 1rem; border-bottom: 2px solid var(--primary-color); padding-bottom: 0.5rem; }
.config-management, .tracker-specific-settings, .map-display-tracker { margin-bottom: 1.5rem; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-header h2 { margin: 0; font-size: 1.2rem; color: var(--text-color-dark); }
.card-content { padding: 1rem; }
.card-content button { margin-right: 0.5rem; margin-bottom: 0.5rem; }
.info-banner { padding: 0.75rem 1rem; border-radius: var(--border-radius); margin-bottom: 1rem; }
.info-banner.status-display.info { background-color: var(--info-bg-color, #e6f7ff); border: 1px solid var(--info-border-color, #91d5ff); color: var(--info-text-color, #005280); }
.info-banner.warning { background-color: var(--warning-bg-color, #fffbe6); border: 1px solid var(--warning-border-color, #ffe58f); color: var(--warning-text-color, #8a6d3b); }
.status-display.success { background-color: var(--success-bg-color, #f6ffed); border: 1px solid var(--success-border-color, #b7eb8f); color: var(--success-text-color, #389e0d); padding: 0.5em; margin-top: 0.5em; }
.status-display.warning { background-color: var(--warning-bg-color, #fffbe6); border: 1px solid var(--warning-border-color, #ffe58f); color: var(--warning-text-color, #8a6d3b); padding: 0.5em; margin-top: 0.5em; }

.content-columns {
  display: flex;
  gap: 1rem;
}
.map-view-wrapper {
  flex-grow: 1;
  min-height: 400px; /* Ensure map has space */
}
.tracker-list-aside {
  width: 300px; /* Fixed width for tracker list */
  flex-shrink: 0;
  max-height: 500px; /* Or adjust as needed */
  overflow-y: auto;
  padding: 0.5rem;
  border: 1px solid var(--border-color, #eee);
  border-radius: var(--border-radius);
  background-color: var(--light-bg-color, #f9f9f9);
}
.tracker-list-aside h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-color, #ddd);
  font-size: 1rem;
}
.tracker-list-aside ul { list-style-type: none; padding: 0; margin: 0;}
.tracker-item { padding: 0.5rem 0.2rem; border-bottom: 1px solid #eee; font-size: 0.9em;}
.tracker-item:last-child { border-bottom: none; }
.tracker-pos { font-size: 0.85em; color: #333; display: block; margin-top: 2px;}
.tracker-pos-na { font-size: 0.85em; color: #888; font-style: italic; display: block; margin-top: 2px;}
.tracker-meta { font-size: 0.8em; color: #555; margin-top: 1px;}

.map-placeholder { text-align: center; padding: 2rem; color: #666;}
.status-connected { color: var(--success-text-color, green); font-weight: bold;}
.status-disconnected { color: var(--error-text-color, red); font-weight: bold;}
.mqtt-status-indicator-inline.success { color: var(--success-text-color, green); }
.mqtt-status-indicator-inline.warn { color: var(--warning-text-color, orange); }
.mqtt-status-indicator-inline.error { color: var(--error-text-color, red); }
.mqtt-status-indicator-inline.info { color: var(--info-text-color, blue); }

.form-group { margin-bottom: 1rem;}
.form-group label { display: block; margin-bottom: 0.3rem; font-weight: 500;}
.form-group input[type="text"] { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: var(--border-radius); box-sizing: border-box;}

.status-indicators-and-controls {
    display: flex;
    flex-direction: column; /* Stack status and controls vertically */
    gap: 1rem;
    margin-bottom: 1rem;
}

.mqtt-controls {
    display: flex;
    gap: 0.5rem; /* Space between buttons */
    align-items: center;
    flex-wrap: wrap; /* Allow buttons to wrap on smaller screens */
}

.mqtt-controls button {
    padding: 0.6rem 1rem; /* Adjusted padding for consistency */
    display: inline-flex; /* For icon alignment */
    align-items: center;
    gap: 0.5rem; /* Space between icon and text */
}

.tracker-id-filter-group {
    margin-top: 1rem; /* Add some space above the tracker ID filter if MQTT controls are present */
}

.section-divider {
    margin-top: 1rem;
    margin-bottom: 1rem;
    border: 0;
    border-top: 1px solid var(--border-color-light);
}

</style>

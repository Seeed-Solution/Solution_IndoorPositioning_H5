<template>
  <div class="tracker-mode-config-view page-content-wrapper">
    <h1 class="page-title">Tracker Mode Configuration</h1>
    <p class="info-banner status-display info" v-if="statusMessage">{{ statusMessage }}</p>

    <div class="config-management card">
      <div class="card-header">
        <h2>Master Configuration Management</h2>
        <button @click="toggleMasterConfigSection" class="button-secondary button-small">
          <i :class="isMasterConfigSectionVisible ? 'fas fa-chevron-up' : 'fas fa-chevron-down'"></i>
          {{ isMasterConfigSectionVisible ? 'Hide' : 'Show' }}
        </button>
      </div>
      <div v-if="isMasterConfigSectionVisible" class="card-content">
        <!-- <input type="file" @change="handleImportMasterConfigFile" accept=".json" ref="importMasterFileRef" style="display: none;" /> -->
        <!-- <button @click="triggerImportMasterFile" class="button-primary">Import Configuration & Update Server (JSON)</button> -->
        
        <label for="jsonImportTracker">Paste Master Configuration JSON here:</label>
        <textarea id="jsonImportTracker" v-model="jsonInputForImport" rows="8" 
                  :placeholder="jsonPlaceholderText"></textarea>
        
        <div class="action-buttons-group">
          <button @click="handleImportMasterConfigJson" class="button-primary">Import & Update Server (from Textarea)</button>
          <button @click="clearTrackerConfig" v-if="currentFullConfig.map" class="button-danger button-small">Clear This Tracker Configuration</button>
        </div>

        <p v-if="!currentFullConfig.map && !statusMessage.includes('Processing')" class="status-display warning">Please import a master configuration file first.</p>
        <p v-if="currentFullConfig.map" class="status-display success">
          Current master configuration loaded: {{ currentFullConfig.map.name || 'Unnamed Map' }}.
          (Beacons: {{ currentFullConfig.beacons.length }}, Map Entities: {{ currentFullConfig.map.entities?.length || 0 }})
        </p>
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
                        @click="toggleMqttConnection"
                        :disabled="isMqttToggleInProgress || wsStatus !== 'connected' || !currentFullConfig.map || !currentServerConfig || !currentServerConfig.mqtt" 
                        :class="{
                            'button-success': (!currentServerConfig?.mqtt?.enabled || (currentServerConfig?.mqtt?.enabled && (liveMqttStatusForServerSettings === 'disconnected' || liveMqttStatusForServerSettings === 'error' || liveMqttStatusForServerSettings === 'misconfigured'))) && currentFullConfig.map,
                            'button-danger': currentServerConfig?.mqtt?.enabled && liveMqttStatusForServerSettings === 'connected' && currentFullConfig.map,
                            'button-default': !currentFullConfig.map || !currentServerConfig || !currentServerConfig.mqtt, // Fallback if config not loaded
                        }"
                        :title="!currentFullConfig.map ? 'Please import a master configuration first to enable MQTT' : (currentServerConfig?.mqtt?.enabled && liveMqttStatusForServerSettings === 'connected' ? 'Disconnect from MQTT' : 'Connect to MQTT')"
                        >
                        <i v-if="isMqttToggleInProgress" class="fas fa-spinner fa-spin"></i>
                        {{ mqttToggleButtonText }}
                    </button>
                    <button @click="toggleServerSettingsPanel" class="button-light-blue" :disabled="wsStatus !== 'connected'">
                        <i class="fas fa-cog"></i> 
                        {{ isServerSettingsPanelVisible ? 'Hide Settings' : 'Show Settings' }}
                    </button>
                </div>
            </div>
            <ServerSettings 
                v-if="isServerSettingsPanelVisible"
                :live-mqtt-status="liveMqttStatusForServerSettings" 
                :initial-settings="currentServerConfig" 
                @settings-applied="handleServerSettingsApplied" 
            />
        </div>
    </div>
    
    <div v-if="currentFullConfig.map" class="map-display-tracker card">
      <div class="card-header"><h2>Map Preview (Live Trackers: {{ trackerList.length }})</h2></div>
      <div class="card-content">
        <div class="content-columns">
          <div class="map-view-wrapper">
            <MapView 
              v-if="currentFullConfig.map" 
              :config="currentFullConfig" 
              :trackers="trackerList" 
            />
          </div>
          <aside class="tracker-list-aside">
            <h4>Trackers ({{ trackerList.length }})</h4>
            <ul v-if="trackerList.length > 0">
              <li v-for="tracker in trackerList" :key="tracker.trackerId" class="tracker-item">
                <strong>{{ tracker.trackerId }}</strong>
                
                <!-- Position Data -->
                <div v-if="tracker.position && typeof tracker.position.x === 'number' && typeof tracker.position.y === 'number'" class="tracker-pos">
                  X: {{ tracker.position.x.toFixed(2) }}, Y: {{ tracker.position.y.toFixed(2) }}
                  <span v-if="tracker.position.accuracy && typeof tracker.position.accuracy === 'number'">, Acc: {{ tracker.position.accuracy.toFixed(2) }}m</span>
                </div>
                <div v-else class="tracker-pos-na">
                  No position data
                </div>

                <!-- Meta Data -->
                <div class="tracker-meta-group">
                  <div v-if="tracker.timestamp" class="tracker-meta-item">
                     Last seen: {{ new Date(tracker.timestamp).toLocaleTimeString() }}
                  </div>
                  <div v-if="tracker.last_detected_beacons && tracker.last_detected_beacons.length > 0" class="tracker-meta-item">
                    Strongest RSSI: {{ Math.max(...tracker.last_detected_beacons.map(b => b.rssi)) }} dBm
                    (Detected {{ tracker.last_detected_beacons.length }} beacon(s))
                  </div>
                  <div v-else-if="tracker.last_detected_beacons" class="tracker-meta-item"> <!-- Added else-if for clarity if last_detected_beacons is an empty array -->
                    No beacons detected in last update.
                  </div>
                </div>
              </li>
            </ul>
            <p v-else>No trackers received yet.</p>
          </aside>
        </div>
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
import { loadWebConfiguration, saveWebConfiguration, loadServerConfiguration, saveServerConfiguration, requestMqttAction } from '@/services/configApiService.js'; // Added loadWebConfiguration and requestMqttAction previously

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

// const trackerSettings = ref({ // REMOVED as filter is gone
// filterPattern: ''
// });

const trackers = ref({}); 
const ws = ref(null);
const wsStatus = ref('disconnected');
const liveMqttStatusForServerSettings = ref('unknown'); // For ServerSettings prop
let saveSettingsTimeout = null;

const currentServerConfig = ref(null); // For storing full server config (mqtt.enabled, etc.)
const isServerSettingsPanelVisible = ref(false);
const isMqttToggleInProgress = ref(false); // Used for the single toggle button
const isMasterConfigSectionVisible = ref(true); // Initialize as true

const trackerList = computed(() => {
    return Object.values(trackers.value).sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

const isMqttEffectivelyEnabled = computed(() => {
  // MQTT is effectively enabled if the config says so AND it's not in a live 'disabled' state from the server
  return currentServerConfig.value?.mqtt?.enabled && liveMqttStatusForServerSettings.value !== 'disabled';
});

const mqttToggleButtonText = computed(() => {
  if (isMqttToggleInProgress.value) return 'Processing...';
  if (!currentServerConfig.value?.mqtt) return 'MQTT Status Loading...';

  const intendedToBeEnabled = currentServerConfig.value.mqtt.enabled;
  const liveStatus = liveMqttStatusForServerSettings.value;

  if (intendedToBeEnabled) {
    if (liveStatus === 'connected') {
      return 'Disable MQTT';
    } else if (liveStatus === 'connecting') {
      return 'Processing...'; // Or 'Cancel Connecting'
    } else { // 'disconnected', 'error', 'misconfigured', 'disabled' (server override), 'unknown' (but config says enabled)
      return 'Connect MQTT'; 
    }
  } else { // Not intended to be enabled (mqtt.enabled is false)
    return 'Enable MQTT';
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
        // Fetch initial configurations once WebSocket is connected
        initializeMasterConfig(); // Load master config (server first, then local)
        fetchFullServerConfig();     // Then fetch live server state (runtime MQTT settings etc)
    };
    ws.value.onmessage = (event) => {
        console.log('[WebSocket] RAW onmessage event received. Data:', event.data); // Log raw event data
        try {
            const message = JSON.parse(event.data);
            console.log('[WebSocket] PARSED message object:', message); // Log parsed message

            if (message.type === 'initial_state') {
                console.log('[WebSocket] Processing initial_state. Current isMqttEffectivelyEnabled:', isMqttEffectivelyEnabled.value, 'Data:', message.data);
                if (isMqttEffectivelyEnabled.value) {
                    trackers.value = message.data || {};
                } else {
                    trackers.value = {};
                }
            } else if (message.type === 'tracker_update') {
                console.log('[WebSocket] Processing tracker_update. Data:', message.data);
                if (isMqttEffectivelyEnabled.value) { // Or isMqttConnected.value if more direct
                    const updatedTrackerId = Object.keys(message.data)[0];
                    if (updatedTrackerId && message.data[updatedTrackerId]) {
                        const newTrackerData = message.data[updatedTrackerId];
                        console.log(`[WebSocket] Updating tracker ${updatedTrackerId} with (raw incoming):`, newTrackerData);
                        
                        // Create a new object with deep copies of nested structures
                        const trackerInstanceData = {
                            trackerId: newTrackerData.trackerId,
                            position: newTrackerData.position ? { 
                                x: newTrackerData.position.x, 
                                y: newTrackerData.position.y, 
                                accuracy: newTrackerData.position.accuracy // Will be undefined if not present, that's fine
                            } : null,
                            timestamp: newTrackerData.timestamp,
                            last_detected_beacons: newTrackerData.last_detected_beacons 
                                ? newTrackerData.last_detected_beacons.map(b => ({ ...b })) 
                                : [],
                            position_history: newTrackerData.position_history 
                                ? newTrackerData.position_history.map(hEntry => Array.isArray(hEntry) ? [...hEntry] : hEntry) 
                                : []
                            // Ensure all fields expected by the template are initialized here
                        };

                        if (!trackers.value[updatedTrackerId]) {
                            // If tracker is new, add it by creating new trackers object to ensure root reactivity
                            trackers.value = { ...trackers.value, [updatedTrackerId]: trackerInstanceData };
                        } else {
                            // If tracker exists, replace its instance to trigger update
                            trackers.value[updatedTrackerId] = trackerInstanceData;
                        }
                        
                        // Force Vue to process updates and then log the state.
                        nextTick(() => {
                            if (trackers.value[updatedTrackerId]) {
                                console.log(`[Vue Reactive State AFTER nextTick] Tracker ${updatedTrackerId} .position is now:`, trackers.value[updatedTrackerId].position);
                                console.log(`[Vue Reactive State AFTER nextTick] Tracker ${updatedTrackerId} .timestamp is now:`, trackers.value[updatedTrackerId].timestamp);
                            } else {
                                console.warn(`[Vue Reactive State AFTER nextTick] Tracker ${updatedTrackerId} missing after update.`);
                            }
                        });
                    }
                }
            } else if (message.type === 'mqtt_status_update') { 
                console.log('[WebSocket] Processing mqtt_status_update. Data:', message.data);
                if (message.data && typeof message.data.status === 'string') {
                    liveMqttStatusForServerSettings.value = message.data.status;
                    // If MQTT becomes disabled via WebSocket, ensure our currentServerConfig reflects this if it was enabled
                    if (message.data.status === 'disabled' && currentServerConfig.value && currentServerConfig.value.mqtt.enabled) {
                        // fetchFullServerConfig(); // Option: refetch to get the definitive state including enabled flag
                        // Or, assume if server says disabled, it means enabled flag is now false or effectively false
                         if(currentServerConfig.value) currentServerConfig.value.mqtt.enabled = false;
                    }
                }
            } else {
                console.log('[WebSocket] Received unhandled message type:', message.type, 'Data:', message.data);
            }
        } catch (error) {
            console.error('[WebSocket] FATAL: Error parsing WebSocket message or in handler. Raw data:', event.data, 'Error:', error);
        }
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
        isMasterConfigSectionVisible.value = false; // Collapse after successful import
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

// Function to load master config from server, with localStorage fallback
async function initializeMasterConfig() {
  showStatus('Loading master configuration...', 'info');
  try {
    const serverMasterConfig = await loadWebConfiguration(); // from configApiService
    if (serverMasterConfig && serverMasterConfig.map && Array.isArray(serverMasterConfig.beacons)) {
      currentFullConfig.value = { 
        map: serverMasterConfig.map, 
        beacons: serverMasterConfig.beacons, 
        settings: { ...initialMasterConfig().settings, ...serverMasterConfig.settings } 
      };
      saveConfigToLocalStorage(CONFIG_STORAGE_KEY, currentFullConfig.value);
      showStatus('Master configuration loaded from server.', 'success');
      isMasterConfigSectionVisible.value = false; // Collapse if loaded from server
      return; // Successfully loaded from server
    } else {
      // No valid config from server, or server returned empty/default
      showStatus('No master configuration found on server. Checking local storage...', 'info');
      loadMasterConfigFromStorage(); // Fallback to local storage
    }
  } catch (error) {
    console.error('Error loading master configuration from server:', error);
    showStatus(`Failed to load master config from server: ${error.message || 'Unknown error'}. Trying local storage.`, 'error');
    loadMasterConfigFromStorage(); // Fallback on error
    // isMasterConfigSectionVisible remains true if server load fails, to allow user input
  }
}

const loadMasterConfigFromStorage = () => {
  const loaded = loadConfigFromLocalStorage(CONFIG_STORAGE_KEY);
  if (loaded && loaded.map) { 
    currentFullConfig.value = loaded; 
    showStatus('Tracker mode master configuration loaded from local storage.'); 
    isMasterConfigSectionVisible.value = false; // Collapse if loaded from local storage
  }
  else { 
    // showStatus('No Tracker mode master configuration found in local storage. Please import one.'); // Can be noisy if server load is primary
    currentFullConfig.value = initialMasterConfig(); 
    isMasterConfigSectionVisible.value = true; // Expand if no config found anywhere
  }
};

const clearTrackerConfig = () => {
  if (confirm('Clear Tracker Mode master configuration?')) {
    clearConfigFromLocalStorage(CONFIG_STORAGE_KEY);
    currentFullConfig.value = initialMasterConfig();
    showStatus('Tracker Mode master configuration cleared.');
    isMasterConfigSectionVisible.value = true; // Expand after clearing
  }
};

const fetchFullServerConfig = async () => {
  if (wsStatus.value !== 'connected') {
    // console.warn("[TrackerMode] Skipping fetchFullServerConfig as WebSocket is not connected.");
    return;
  }
  // statusMessage.value = 'Fetching current server configuration...'; // Can be too noisy
  try {
    const config = await loadServerConfiguration();
    if (config) {
      currentServerConfig.value = config;
      // DO NOT set liveMqttStatusForServerSettings here. It should ONLY be updated by WebSocket.
      // liveMqttStatusForServerSettings.value = config.mqtt?.status || 'unknown'; // <--- REMOVE THIS LINE
      // statusMessage.value = 'Server configuration loaded.'; // Can be too noisy
    } else {
      // statusMessage.value = 'Could not fetch server configuration.';
      console.warn('[TrackerMode] Failed to load server configuration or server returned empty.');
    }
  } catch (error) {
    // statusMessage.value = `Error fetching server configuration: ${error.message}`;
    console.error('[TrackerMode] Error fetching server configuration:', error);
  }
  // setTimeout(() => { if (statusMessage.value.includes('Fetching') || statusMessage.value.includes('loaded') || statusMessage.value.includes('Could not fetch')) statusMessage.value = ''; }, 3000);
};

const toggleMqttConnection = async () => {
  // The button's :disabled attribute already checks for !currentFullConfig.map
  // if (!currentFullConfig.map) { 
  //   showStatus('Master configuration not loaded. Please import a configuration before connecting to MQTT.', 'error');
  //   return;
  // }

  // Guard for server config, operation in progress, or WebSocket disconnected still relevant
  if (!currentServerConfig.value || !currentServerConfig.value.mqtt || isMqttToggleInProgress.value || wsStatus.value !== 'connected') {
    showStatus('Cannot toggle MQTT: Server config not loaded, operation in progress, or WebSocket disconnected. Or master config missing.', 'error');
    return;
  }
  isMqttToggleInProgress.value = true;
  
  let action;
  const intendedToBeEnabled = currentServerConfig.value.mqtt.enabled;
  const liveStatus = liveMqttStatusForServerSettings.value;

  if (intendedToBeEnabled) {
    if (liveStatus === 'connected') {
      action = 'disable'; // Currently connected, so action is to disable
    } else {
      action = 'enable';  
    }
  } else {
    action = 'enable';    // Configured to be off, so action is to enable
  }

  try {
    const serverResponseJson = await requestMqttAction(action); // Assume this is the parsed JSON response on HTTP success

    let msgToShow = serverResponseJson?.message || `MQTT ${action} action acknowledged. Status will update.`;
    let msgType = 'success'; // Default to success for 200 OK responses with a message

    if (action === 'enable') {
      if (liveStatus === 'connected' && serverResponseJson?.current_status === 'connected') {
        // If trying to connect when client already thought it was connected, and server confirms.
        msgToShow = 'MQTT is already connected.';
        msgType = 'info';
      } else if (serverResponseJson?.current_status === 'connected') {
        // If an 'enable' action resulted in 'connected' status (or confirmed it was already connected)
        // Use server message if available, otherwise a generic success message.
        msgToShow = serverResponseJson?.message || 'MQTT connection successful.';
        // msgType remains 'success'
      } else if (serverResponseJson?.message) {
        // General case for 'enable' action if not definitively connected by this response, use server message.
        msgToShow = serverResponseJson.message; 
      }
    } else if (action === 'disable') {
      // For 'disable' action, use server message or a generic acknowledgement.
      msgToShow = serverResponseJson?.message || `MQTT disconnection request acknowledged.`;
    }
    
    showStatus(msgToShow, msgType);

    // Optimistically update local server config state's 'enabled' flag
    if (currentServerConfig.value.mqtt) {
      currentServerConfig.value.mqtt.enabled = (action === 'enable');
    }

    // Explicitly update live status if server's API response confirms the state post-action
    if (action === 'enable' && serverResponseJson?.current_status === 'connected') {
      liveMqttStatusForServerSettings.value = 'connected';
    } else if (action === 'disable' && serverResponseJson?.current_status === 'disconnected') {
      liveMqttStatusForServerSettings.value = 'disconnected';
    }
    // For other statuses like 'connecting', 'error', 'misconfigured' from serverResponseJson.current_status,
    // we can also update liveMqttStatusForServerSettings.value if it provides more immediate feedback
    // than waiting for a potential WebSocket message, especially if the WebSocket message might be delayed or not sent
    // if the state didn't fundamentally change from the server Paho client's perspective.
    else if (serverResponseJson?.current_status && 
             ['connecting', 'error', 'misconfigured', 'disabled'].includes(serverResponseJson.current_status)) {
      liveMqttStatusForServerSettings.value = serverResponseJson.current_status;
    }

    // Server will send mqtt_status_update via WebSocket for general updates.
    // Re-fetch to get the latest full server config (NOT for live MQTT status, but for other settings like broker details if they changed)
    await fetchFullServerConfig(); 
  } catch (error) {
    const errorMessage = error.response?.data?.detail || // FastAPI HTTPException detail
                         error.message ||                 // General error message
                         'Unknown error';
    showStatus(`Error during MQTT ${action} request: ${errorMessage}`, 'error');
    console.error(`Error MQTT ${action}:`, error);
  } finally {
    isMqttToggleInProgress.value = false;
  }
};

const toggleServerSettingsPanel = () => {
  isServerSettingsPanelVisible.value = !isServerSettingsPanelVisible.value;
  if (isServerSettingsPanelVisible.value && !currentServerConfig.value) {
      fetchFullServerConfig(); // Load if panel is opened and config not yet loaded
  }
};

const handleServerSettingsApplied = async (settingsToApply) => {
  statusMessage.value = 'Applying server settings...';
  try {
    const result = await saveServerConfiguration(settingsToApply);
    if (result && result.success) {
      statusMessage.value = result.message || 'Server settings applied successfully! Status will update via WebSocket.';
      // Update local currentServerConfig with what was applied, then wait for WebSocket for live status
      currentServerConfig.value = JSON.parse(JSON.stringify(settingsToApply));
      // Optionally, hide panel after successful save
      // isServerSettingsPanelVisible.value = false; 
    } else {
      statusMessage.value = result.message || 'Failed to apply server settings.';
    }
  } catch (error) {
    statusMessage.value = `Error applying settings: ${error.message}`;
  }
  setTimeout(() => { statusMessage.value = ''; }, 7000);
};

const toggleMasterConfigSection = () => {
  isMasterConfigSectionVisible.value = !isMasterConfigSectionVisible.value;
};

onMounted(() => { 
    // loadMasterConfigFromStorage(); // Now handled by initializeMasterConfig via ws.onopen
    // loadTrackerSettings(); // Filter and its settings are removed
    connectWebSocket(); 
});
onUnmounted(() => { if (ws.value) { ws.value.onclose = null; ws.value.close(); } /* clearTimeout(saveSettingsTimeout); // saveSettingsTimeout no longer exists */ });

</script>

<style scoped>
/* Remove scoped .page-container or .page-content-wrapper if present */

/* .page-title style is now global in style.css */
/*
.page-title {
  font-size: 1.6rem; 
  color: var(--text-color); 
  margin-bottom: 1.5rem; 
  padding-bottom: 0; 
  font-weight: 600; 
}
*/

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
.tracker-pos { font-size: 0.85em; color: #333; display: block; margin-top: 2px; margin-bottom: 4px;}
.tracker-pos-na { font-size: 0.85em; color: #888; font-style: italic; display: block; margin-top: 2px; margin-bottom: 4px;}

.tracker-meta-group { 
  font-size: 0.8em; 
  color: #555; 
  margin-top: 3px; 
}
.tracker-meta-item { 
  display: block; /* Ensure each meta item is on a new line if not already */
  margin-bottom: 2px; 
}
.tracker-meta-item:last-child {
  margin-bottom: 0;
}

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

/* New style for the button group */
.action-buttons-group {
  display: flex;
  align-items: center; /* Align items vertically if they have different heights */
  gap: 0.5rem; /* Space between buttons */
  margin-bottom: 0.75rem; /* Space below the button group */
}
/* Ensure buttons within the group don't have excessive bottom margin from global styles if not needed */
.action-buttons-group button {
  margin-bottom: 0; 
}

</style>

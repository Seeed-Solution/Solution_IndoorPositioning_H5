<template>
  <div class="tracker-mode-config-view page-content-wrapper">
    <h1 class="page-title">Tracker Mode Configuration</h1>
    <p class="info-banner status-display info" v-if="statusMessage">{{ statusMessage }}</p>

    <div class="config-management card"> 
      <div class="card-header">
        <h2>Master Configuration Status</h2>
      </div>
      <div class="card-content">
        <p v-if="!currentFullConfig.map && !statusMessage.includes('Processing') && wsStatus === 'connected'" class="status-text warning-text">Waiting for server configuration...</p>
        <p v-if="!currentFullConfig.map && wsStatus === 'disconnected'" class="status-text error-text">Disconnected from server. Cannot load configuration.</p>
        <p v-if="currentFullConfig.map" class="status-text">
          Current master configuration loaded: {{ currentFullConfig.map.name || 'Unnamed Map' }}.
          (Beacons: {{ currentFullConfig.beacons.length }}, Map Entities: {{ currentFullConfig.map.entities?.length || 0 }})
        </p>
      </div>
    </div>

    <div class="server-status-and-settings card">
        <div class="card-header"> 
            <h2>Server Status</h2>
        </div>
        <div class="card-content">
            <p class="status-text">
              WebSocket Status: <span :class="wsStatus === 'connected' ? 'status-connected' : 'status-disconnected'">{{ wsStatus }}</span>
              <span v-if="wsStatus === 'connected'"> | MQTT Status (Live): <span :class="['mqtt-status-indicator-inline', mqttStatusDisplay.class]"><i :class="mqttStatusDisplay.icon"></i> {{ mqttStatusDisplay.text }}</span></span>
            </p>
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
                  <div v-else-if="tracker.last_detected_beacons" class="tracker-meta-item">
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
import { loadConfigFromLocalStorage, saveConfigToLocalStorage, clearConfigFromLocalStorage } from '@/services/localStorageService.js';
import { loadWebConfiguration, saveWebConfiguration, loadServerConfiguration, saveServerConfiguration } from '@/services/configApiService.js';

const CONFIG_STORAGE_KEY = 'trackerModeConfig'; 
const TRACKER_SETTINGS_STORAGE_KEY = 'trackerModeUISettings';

const statusMessage = ref('');

const initialMasterConfig = () => ({
  map: null,
  beacons: [],
  settings: { signalPropagationFactor: 2.5 },
});
const currentFullConfig = ref(initialMasterConfig()); 

const trackers = ref({}); 
const ws = ref(null);
const wsStatus = ref('disconnected');
const liveMqttStatusForServerSettings = ref('unknown');
let saveSettingsTimeout = null;

const currentServerConfig = ref(null);
const isMasterConfigSectionVisible = ref(true);

const trackerList = computed(() => {
    return Object.values(trackers.value).sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

const mqttStatusDisplay = computed(() => {
  let statusText = 'MQTT: Unknown';
  let statusClass = 'info';
  let iconClass = 'fas fa-question-circle';

  const mqttConfig = currentServerConfig.value?.mqtt;
  const mqttEnabledInConfig = mqttConfig?.enabled;

  if (wsStatus.value !== 'connected') {
    statusText = 'Unavailable (WebSocket Disconnected)';
    statusClass = 'error';
    iconClass = 'fas fa-wifi-slash';
  } else if (!mqttConfig) {
    statusText = 'Status Loading...';
    statusClass = 'info';
    iconClass = 'fas fa-hourglass-start';
  } else if (mqttEnabledInConfig === false) {
    statusText = 'Disabled by Server Configuration'; 
    statusClass = 'info'; 
    iconClass = 'fas fa-toggle-off';
  } else {
      switch (liveMqttStatusForServerSettings.value) {
        case 'connected': statusText = 'Connected'; statusClass = 'success'; iconClass = 'fas fa-check-circle'; break;
        case 'connecting': statusText = 'Connecting...'; statusClass = 'info'; iconClass = 'fas fa-spinner fa-spin'; break;
        case 'disconnected': statusText = 'Disconnected'; statusClass = 'warn'; iconClass = 'fas fa-plug'; break;
        case 'misconfigured': statusText = 'Misconfigured on Server'; statusClass = 'warn'; iconClass = 'fas fa-exclamation-triangle'; break;
        case 'error': statusText = 'Connection Error'; statusClass = 'error'; iconClass = 'fas fa-times-circle'; break;
        default:
          if (liveMqttStatusForServerSettings.value === 'unknown') {
            statusText = "Awaiting Status...";
            iconClass = 'fas fa-hourglass-half';
            statusClass = 'info';
          } else {
            statusText = `Live Status: ${liveMqttStatusForServerSettings.value}`;
            iconClass = 'fas fa-exclamation-circle';
            statusClass = 'warn';
          }
          break;
      }
  }
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
        initializeMasterConfig();
        fetchFullServerConfig();    
    };
    ws.value.onmessage = (event) => {
        console.log('[WebSocket] RAW onmessage event received. Data:', event.data);
        try {
            const message = JSON.parse(event.data);
            console.log('[WebSocket] PARSED message object:', message);

            if (message.type === 'initial_state') {
                console.log('[WebSocket] Processing initial_state. Current isMqttEffectivelyEnabled:', isMqttEffectivelyEnabled.value, 'Data:', message.data);
                if (isMqttEffectivelyEnabled.value) {
                    trackers.value = message.data || {};
                } else {
                    trackers.value = {};
                }
            } else if (message.type === 'tracker_update') {
                console.log('[WebSocket] Processing tracker_update. Data:', message.data);
                if (isMqttEffectivelyEnabled.value) {
                    const updatedTrackerId = Object.keys(message.data)[0];
                    if (updatedTrackerId && message.data[updatedTrackerId]) {
                        const newTrackerData = message.data[updatedTrackerId];
                        console.log(`[WebSocket] Updating tracker ${updatedTrackerId} with (raw incoming):`, newTrackerData);
                        
                        const trackerInstanceData = {
                            trackerId: newTrackerData.trackerId,
                            position: newTrackerData.position ? { 
                                x: newTrackerData.position.x, 
                                y: newTrackerData.position.y, 
                                accuracy: newTrackerData.position.accuracy
                            } : null,
                            timestamp: newTrackerData.timestamp,
                            last_detected_beacons: newTrackerData.last_detected_beacons 
                                ? newTrackerData.last_detected_beacons.map(b => ({ ...b })) 
                                : [],
                            position_history: newTrackerData.position_history 
                                ? newTrackerData.position_history.map(hEntry => Array.isArray(hEntry) ? [...hEntry] : hEntry) 
                                : []
                        };

                        if (!trackers.value[updatedTrackerId]) {
                            trackers.value = { ...trackers.value, [updatedTrackerId]: trackerInstanceData };
                        } else {
                            trackers.value[updatedTrackerId] = trackerInstanceData;
                        }
                        
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
                    if (message.data.status === 'disabled' && currentServerConfig.value && currentServerConfig.value.mqtt.enabled) {
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

const showStatus = (msg, type = 'info') => {
    statusMessage.value = `${type.toUpperCase()}: ${msg}`; 
    setTimeout(() => { statusMessage.value = '' }, 7000); 
};

const initializeMasterConfig = async () => {
  showStatus('Loading master configuration...', 'info');
  try {
    const config = await loadWebConfiguration();
    if (config && config.map) {
      currentFullConfig.value = config;
      showStatus('Master configuration loaded from server.', 'success');
      isMasterConfigSectionVisible.value = false;
      return;
    } else {
      showStatus('No master configuration found on server. Checking local storage...', 'info');
      loadMasterConfigFromStorage();
    }
  } catch (error) {
    console.error('Error loading master configuration from server:', error);
    showStatus(`Failed to load master config from server: ${error.message || 'Unknown error'}. Trying local storage.`, 'error');
    loadMasterConfigFromStorage();
  }
};

const loadMasterConfigFromStorage = () => {
  const loaded = loadConfigFromLocalStorage(CONFIG_STORAGE_KEY);
  if (loaded && loaded.map) { 
    currentFullConfig.value = loaded; 
    showStatus('Tracker mode master configuration loaded from local storage.'); 
    isMasterConfigSectionVisible.value = false;
  }
  else { 
    currentFullConfig.value = initialMasterConfig(); 
    isMasterConfigSectionVisible.value = true;
  }
};

const fetchFullServerConfig = async () => {
  if (wsStatus.value !== 'connected') {
    return;
  }
  try {
    const config = await loadServerConfiguration();
    if (config) {
      currentServerConfig.value = config;
      if (config.mqtt && typeof config.mqtt.live_mqtt_status !== 'undefined') {
        liveMqttStatusForServerSettings.value = config.mqtt.live_mqtt_status;
      } else if (config.mqtt && config.mqtt.enabled) {
        liveMqttStatusForServerSettings.value = 'unknown';
      }
    } else {
      console.warn('[TrackerMode] Failed to load server configuration or server returned empty.');
      currentServerConfig.value = null;
      liveMqttStatusForServerSettings.value = 'unknown';
    }
  } catch (error) {
    console.error('[TrackerMode] Error fetching server configuration:', error);
    currentServerConfig.value = null;
    liveMqttStatusForServerSettings.value = 'unknown';
  }
};

const isMqttEffectivelyEnabled = computed(() => {
  return currentServerConfig.value?.mqtt?.enabled && liveMqttStatusForServerSettings.value !== 'disabled';
});

onMounted(() => {
    connectWebSocket();
});
onUnmounted(() => { if (ws.value) { ws.value.onclose = null; ws.value.close(); } });

</script>

<style scoped>
/* .page-content-wrapper removed to use global */

.page-title {
  /* color: #333; */ /* Use global */
  /* margin-bottom: 20px; */ /* Use global */
  text-align: center; /* Specific to this view */
}

/* .info-banner styles removed to rely on global .status-display */

.config-management {
  margin-bottom: 20px;
}

.server-status-and-settings {
  margin-bottom: 20px;
}

.status-text {
  /* padding: 0; */ /* Handled by card-content parent */
  /* padding-left: 10px; */ /* Handled by card-content parent */
  margin-bottom: 5px;
  /* border-radius: 0; */ /* Not needed for plain text */
  /* background-color: transparent; */ /* Default */
  /* border: none; */ /* Default for <p> */
  color: #333; /* Or var(--text-color) if #333 is not from a variable */
  text-align: left;
}

.status-text.warning-text {
  color: #8a6d3b;
}
.status-text.error-text {
  color: #a94442;
}

.status-connected { color: green; font-weight: bold; }
.status-disconnected { color: red; font-weight: bold; }

.map-display-tracker {
  margin-bottom: 1.5rem;
}

.content-columns {
  display: flex;
  gap: 20px;
}

.map-view-wrapper {
  flex-grow: 1;
  min-height: 400px;
}

.tracker-list-aside {
  width: 300px;
  flex-shrink: 0;
  background-color: #f9f9f9;
  padding: 0.75rem; /* Standardized padding */
  border-radius: 4px; /* Matches global --border-radius if var(--border-radius) is 4px, else use var */
  /* Consider var(--border-radius) for consistency if it's not 4px */
  border: 1px solid #eee; /* Consider var(--border-color) for consistency */
  max-height: 500px;
  overflow-y: auto;
}

.tracker-list-aside h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 5px;
}

.tracker-list-aside ul {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.tracker-item {
  padding: 8px;
  border-bottom: 1px solid #eee;
  font-size: 0.9em;
}
.tracker-item:last-child {
  border-bottom: none;
}
.tracker-item strong {
  color: #0056b3; 
  display: block;
  margin-bottom: 3px;
}
.tracker-pos {
  color: #333;
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-pos-na {
  color: #777;
  font-style: italic;
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-meta-group {
  font-size: 0.85em;
  color: #555;
}
.tracker-meta-item {
  margin-top: 2px;
}

.fas {
  margin-right: 5px;
}

.mqtt-controls {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}

.mqtt-status-indicator-inline {
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 0.9em;
}
.mqtt-status-indicator-inline.success { background-color: #28a745; color: white; }
.mqtt-status-indicator-inline.warn { background-color: #ffc107; color: #333; }
.mqtt-status-indicator-inline.error { background-color: #dc3545; color: white; }
.mqtt-status-indicator-inline.info { background-color: #17a2b8; color: white; }
</style>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import axios from 'axios';
import MapView from './components/MapView.vue';
import ServerSettings from './components/ServerSettings.vue';

// Config related refs
const showPasteConfigArea = ref(false);
const pastedConfigJson = ref('');
const uploadStatus = ref('idle'); // idle, uploading, success, error
const uploadError = ref('');
const showConfigTemplate = ref(false); // For toggling template visibility

// Server Settings UI toggle
const showServerSettings = ref(false);
const liveMqttStatus = ref('unknown'); // Added for MQTT live status
const mqttControlLoading = ref(false); // For Connect/Disconnect button
const mqttControlError = ref(''); // Error messages from connect/disconnect attempts

// State refs
const configStatus = ref('idle'); // idle, loading, loaded, error
const currentConfig = ref(null); // This will hold MiniprogramConfig data
const trackers = ref({});
const wsStatus = ref('disconnected');
const ws = ref(null);

const trackerList = computed(() => {
    return Object.values(trackers.value).sort((a, b) => a.trackerId.localeCompare(b.trackerId));
});

const submitPastedConfig = async () => {
  if (!pastedConfigJson.value.trim()) {
    uploadError.value = 'Textarea is empty. Paste your JSON config.';
    uploadStatus.value = 'error';
    return;
  }

  uploadStatus.value = 'uploading';
  uploadError.value = '';
  let parsedConfig;

  try {
    parsedConfig = JSON.parse(pastedConfigJson.value);
  } catch (error) {
    console.error('JSON Parse error:', error);
    uploadStatus.value = 'error';
    uploadError.value = 'Invalid JSON format: ' + error.message;
    return;
  }

  try {
    // Using the new endpoint /api/config/upload which expects a JSON body
    const response = await axios.post('/api/config/upload', parsedConfig, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    console.log('Submit pasted config response:', response.data);
    uploadStatus.value = 'success';
    // Backend will broadcast config_update via WebSocket which should trigger UI update.
    // Or, we can call fetchConfig() here too for immediate feedback.
    fetchConfig(); 
    showPasteConfigArea.value = false; // Hide textarea on success
    pastedConfigJson.value = ''; // Clear textarea
  } catch (error) {
    console.error('Submit pasted config error:', error);
    uploadStatus.value = 'error';
    uploadError.value = error.response?.data?.detail || error.message || 'Unknown error submitting config';
    configStatus.value = 'error';
    currentConfig.value = null;
  }
};

const fetchConfig = async () => {
    configStatus.value = 'loading';
    try {
        // This endpoint now returns MiniprogramConfig
        const response = await axios.get('/api/config'); 
        if (response.data) {
            currentConfig.value = response.data;
            configStatus.value = 'loaded';
            console.log("Miniprogram Config loaded:", currentConfig.value);
        } else {
             configStatus.value = 'idle';
             currentConfig.value = null;
        }
    } catch (error) {
        console.error("Failed to fetch miniprogram config:", error);
        configStatus.value = 'error';
        currentConfig.value = null;
    }
};

// WebSocket connection logic (connectWebSocket, onmessage handlers, etc.)
// remains largely the same, but ensure 'config_update' handler works with MiniprogramConfig
const connectWebSocket = () => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    ws.value = new WebSocket(wsUrl);
    wsStatus.value = 'connecting';

    ws.value.onopen = () => {
        wsStatus.value = 'connected';
        console.log('WebSocket connected');
    };

    ws.value.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            if (message.type === 'initial_state') {
                // Assuming initial_state provides data in the new TrackerState format
                const initialTrackers = {};
                Object.keys(message.data).forEach(trackerId => {
                    initialTrackers[trackerId] = message.data[trackerId];
                });
                trackers.value = initialTrackers;
                console.log('Received initial tracker state:', trackers.value);
            } else if (message.type === 'tracker_update') {
                // Data is expected to be { trackerId: { tracker_data } }
                // So we can directly merge it in.
                const updatedTrackerId = Object.keys(message.data)[0];
                if (updatedTrackerId) {
                     trackers.value = {
                        ...trackers.value,
                        [updatedTrackerId]: message.data[updatedTrackerId]
                     };
                }
            } else if (message.type === 'config_update') {
                // This will be the MiniprogramConfig
                currentConfig.value = message.data;
                configStatus.value = 'loaded';
                console.log('Received miniprogram config update via WebSocket:', currentConfig.value);
            } else if (message.type === 'mqtt_status_update') { // New handler
                if (message.data && typeof message.data.status === 'string') {
                    liveMqttStatus.value = message.data.status;
                    console.log('MQTT Status Update via WS:', liveMqttStatus.value);
                }
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    };

    ws.value.onerror = (error) => {
        wsStatus.value = 'error';
        console.error('WebSocket error:', error);
    };

    ws.value.onclose = (event) => {
        wsStatus.value = 'disconnected';
        console.log('WebSocket disconnected:', event.reason || `Code ${event.code}`);
    };
};

const mqttStatusDisplay = computed(() => {
  let statusText = 'MQTT: Unknown';
  let statusClass = 'info';
  let iconClass = 'fas fa-question-circle';
  let isConnected = false;

  // Similar logic to what was in ServerSettings
  switch (liveMqttStatus.value) {
    case 'connected':
      statusText = 'MQTT: Connected';
      statusClass = 'success';
      iconClass = 'fas fa-check-circle';
      isConnected = true;
      break;
    case 'connecting':
      statusText = 'MQTT: Connecting...';
      statusClass = 'info';
      iconClass = 'fas fa-spinner fa-spin';
      break;
    case 'disconnected':
      statusText = 'MQTT: Disconnected';
      statusClass = 'warn';
      iconClass = 'fas fa-plug';
      break;
    case 'disabled':
      statusText = 'MQTT: Disabled by server config or no auto-start.';
      statusClass = 'info';
      iconClass = 'fas fa-toggle-off';
      break;
    case 'misconfigured':
      statusText = 'MQTT: Misconfigured (e.g., missing broker host).';
      statusClass = 'warn';
      iconClass = 'fas fa-exclamation-triangle';
      break;
    case 'error':
      statusText = 'MQTT: Connection Error';
      statusClass = 'error';
      iconClass = 'fas fa-times-circle';
      break;
    default:
      statusText = `MQTT: ${liveMqttStatus.value}`;
      statusClass = 'info';
      break;
  }
  return { text: statusText, class: statusClass, icon: iconClass, connected: isConnected };
});

const connectMqtt = async () => {
  mqttControlLoading.value = true;
  mqttControlError.value = '';
  try {
    const response = await axios.post('/api/mqtt/connect');
    // liveMqttStatus should update via WebSocket from backend status broadcast
    console.log("MQTT Connect API call successful:", response.data.message);
    // Optionally show a temporary success message for the action itself
  } catch (error) {
    console.error("Failed to connect MQTT:", error);
    mqttControlError.value = error.response?.data?.detail || error.message || 'Failed to initiate MQTT connection.';
    // liveMqttStatus will eventually reflect error if connection truly fails
  } finally {
    mqttControlLoading.value = false;
  }
};

const disconnectMqtt = async () => {
  mqttControlLoading.value = true;
  mqttControlError.value = '';
  try {
    const response = await axios.post('/api/mqtt/disconnect');
    // liveMqttStatus should update via WebSocket
    console.log("MQTT Disconnect API call successful:", response.data.message);
  } catch (error) {
    console.error("Failed to disconnect MQTT:", error);
    mqttControlError.value = error.response?.data?.detail || error.message || 'Failed to initiate MQTT disconnection.';
  } finally {
    mqttControlLoading.value = false;
  }
};

const exampleMiniprogramConfig = JSON.stringify({
  map: {
    name: "Sample Map",
    width: 20.0,
    height: 15.0,
    originX: 0.0,
    originY: 0.0,
    refPoint1DisplayX: 1.0,
    refPoint1DisplayY: 1.0,
    refPoint1ActualX: 0.0,
    refPoint1ActualY: 0.0,
    refPoint2DisplayX: 19.0,
    refPoint2DisplayY: 14.0,
    refPoint2ActualX: 18.0,
    refPoint2ActualY: 13.0,
    ppm: 100.0,
    backgroundImage: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", // Example: 1x1 transparent pixel
    entities: [
      {
        type: "polyline",
        points: [[1,1], [1,14], [18,14], [18,1], [1,1]],
        color: "#000000",
        lineWidth: 2,
        id: "wall1"
      }
    ]
  },
  beacons: [
    {
      deviceId: "MBeaco1",
      displayName: "Main Beacon 1",
      macAddress: "AA:BB:CC:DD:EE:01",
      x: 2.5,
      y: 3.0,
      txPower: -59
    },
    {
      deviceId: "MBeaco2",
      displayName: "Corner Beacon 2",
      macAddress: "AA:BB:CC:DD:EE:02",
      x: 17.0,
      y: 12.5,
      txPower: -62
    }
  ],
  settings: {
    signalPropagationFactor: 2.5
  }
}, null, 2);

const copyConfigTemplate = async () => {
  try {
    await navigator.clipboard.writeText(exampleMiniprogramConfig);
    alert('Config template copied to clipboard!'); // Simple feedback
  } catch (err) {
    console.error('Failed to copy template: ', err);
    alert('Failed to copy template. See console for details.');
  }
};

onMounted(() => {
  fetchConfig();
  connectWebSocket();
});

onUnmounted(() => {
    if (ws.value) {
        ws.value.close();
    }
});

</script>

<template>
  <div id="app-container">
    <header class="app-header">
      <div class="header-content-wrapper">
        <h1><i class="fas fa-broadcast-tower"></i> Beacon Positioning System</h1>
      </div>
    </header>

    <main class="main-content">
      <!-- MQTT Control Panel -->
      <div class="mqtt-control-panel data-panel">
        <div :class="['status', mqttStatusDisplay.class]">
          <i :class="mqttStatusDisplay.icon"></i> {{ mqttStatusDisplay.text }}
        </div>
        <button 
          @click="mqttStatusDisplay.connected ? disconnectMqtt() : connectMqtt()" 
          :disabled="mqttControlLoading" 
          :class="['button-secondary', mqttStatusDisplay.connected ? 'mqtt-disconnect-btn' : 'mqtt-connect-btn']"
        >
          <i :class="mqttControlLoading ? 'fas fa-spinner fa-spin' : (mqttStatusDisplay.connected ? 'fas fa-plug' : 'fas fa-link')"></i>
          {{ mqttControlLoading ? 'Processing...' : (mqttStatusDisplay.connected ? 'Disconnect MQTT' : 'Connect MQTT') }}
        </button>
        <button @click="showServerSettings = !showServerSettings" class="button-primary server-settings-toggle-btn">
          <i :class="showServerSettings ? 'fas fa-eye-slash' : 'fas fa-cog'"></i>
          {{ showServerSettings ? 'Hide Settings' : 'Show Settings' }}
        </button>
        <div v-if="mqttControlError" class="status error small">{{ mqttControlError }}</div>
      </div>

      <ServerSettings 
        v-if="showServerSettings" 
        class="settings-panel" 
        :live-mqtt-status="liveMqttStatus" 
      />

      <div class="miniprogram-config-panel config-panel" v-if="!showServerSettings">
        <div class="panel-header">
          <h2><i class="fas fa-map-signs"></i> Map & Beacon Configuration</h2>
          <button @click="showPasteConfigArea = !showPasteConfigArea" class="button-secondary">
            <i :class="showPasteConfigArea ? 'fas fa-times-circle' : 'fas fa-paste'"></i>
            {{ showPasteConfigArea ? 'Cancel Paste' : 'Load Config via Paste' }}
          </button>
        </div>

        <div v-if="configStatus === 'loaded' && currentConfig?.settings" class="status success">
          <i class="fas fa-check-circle"></i> Miniprogram Config loaded. Signal Factor (n): {{ currentConfig.settings.signalPropagationFactor }}
        </div>
        <div v-else-if="configStatus === 'loaded' && !currentConfig?.settings" class="status success">
          <i class="fas fa-check-circle"></i> Miniprogram Config loaded (structure might be partial or old).
        </div>
        <div v-else-if="configStatus === 'error'" class="status error">
          <i class="fas fa-exclamation-triangle"></i> Failed to load/submit Miniprogram config. Check console.
        </div>
        <div v-else-if="configStatus === 'loading'" class="status info">
          <i class="fas fa-spinner fa-spin"></i> Loading Miniprogram configuration...
        </div>
        <div v-else class="status">
          <i class="fas fa-info-circle"></i> No Miniprogram configuration loaded. Use button below.
        </div>

        <div v-if="showPasteConfigArea" class="paste-area">
          <textarea v-model="pastedConfigJson" placeholder="Paste Miniprogram JSON config here..."></textarea>
          <button @click="submitPastedConfig" :disabled="uploadStatus === 'uploading' || !pastedConfigJson.trim()" class="button-primary">
            <i class="fas fa-upload"></i> {{ uploadStatus === 'uploading' ? 'Submitting...' : 'Submit Pasted Config' }}
          </button>
        </div>
        <div v-if="uploadStatus === 'success' && !showPasteConfigArea" class="status success"><i class="fas fa-check-circle"></i> Miniprogram config submitted successfully!</div>
        <div v-if="uploadStatus === 'error'" class="status error"><i class="fas fa-exclamation-triangle"></i> Submission failed: {{ uploadError }}</div>
      
        <!-- View Template Section - only show if paste area is active -->
        <div v-if="showPasteConfigArea" class="template-controls-and-viewer">
            <div class="template-viewer-controls">
                <button @click="showConfigTemplate = !showConfigTemplate" class="button-link-styled">
                <i :class="showConfigTemplate ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                {{ showConfigTemplate ? 'Hide Template' : 'View Example Template' }}
                </button>
            </div>
            <div v-if="showConfigTemplate" class="config-template-viewer">
            <div class="template-actions">
                <button @click="copyConfigTemplate" class="button-secondary small-button">
                <i class="fas fa-copy"></i> Copy Template
                </button>
            </div>
            <pre><code>{{ exampleMiniprogramConfig }}</code></pre>
            </div>
        </div>
      </div>

      <div class="live-data-section">
        <div class="map-section data-panel">
          <h2><i class="fas fa-map-marked-alt"></i> Live Map</h2>
          <div class="status">WebSocket: <i :class="wsStatus === 'connected' ? 'fas fa-check-circle ws-connected' : (wsStatus === 'connecting' ? 'fas fa-spinner fa-spin' : 'fas fa-times-circle ws-disconnected')"></i> {{ wsStatus }}</div>
          <MapView :config="currentConfig" :trackers="trackerList" />
        </div>

        <div class="tracker-list-section data-panel">
          <h2><i class="fas fa-list-ul"></i> Trackers ({{ Object.keys(trackers).length }})</h2>
          <ul v-if="Object.keys(trackers).length > 0">
            <li v-for="tracker in trackerList" :key="tracker.trackerId">
                <strong><i class="fas fa-tag"></i> {{ tracker.trackerId }}</strong>:
                <i class="fas fa-map-marker-alt"></i> ({{ tracker.x?.toFixed(2) ?? 'N/A' }}, {{ tracker.y?.toFixed(2) ?? 'N/A' }}) 
                <span v-if="tracker.last_update_time"><i class="far fa-clock"></i> {{ new Date(tracker.last_update_time).toLocaleTimeString() }}</span>
                <span v-if="tracker.last_detected_beacons && tracker.last_detected_beacons.length > 0" class="beacon-details">
                    | <i class="fas fa-signal"></i> {{ tracker.last_detected_beacons.map(b => `${b.macAddress.slice(-5)}(${b.rssi})`).join(', ') }}
                </span>
            </li>
          </ul>
          <p v-else><i class="fas fa-search-location"></i> No trackers detected yet.</p>
        </div>
      </div>
    </main>
  </div>
</template>

<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css');

:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --error-color: #dc3545;
  --info-color: #17a2b8;
  --light-bg: #f8f9fa;
  --border-color: #dee2e6;
  --text-color: #212529;
  --text-muted: #6c757d;
  --warn-color: #ffc107; /* Added for warning status */
  --panel-bg: #ffffff;
  --panel-border-radius: 8px;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  margin: 0;
  background-color: #eef2f7; /* Slightly off-white for better contrast with white panels */
  color: var(--text-color);
  box-sizing: border-box;
}

*, *:before, *:after { /* Apply border-box to all elements */
  box-sizing: inherit;
}

#app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background-color: var(--primary-color);
  color: white;
  padding: 0 20px; /* Consistent horizontal padding with main-content */
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  /* Height will be determined by content + padding in header-content-wrapper */
}

.header-content-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px; 
  margin: 0 auto; 
  padding: 15px 0; /* Vertical padding for header content */
  width: 100%; 
}

.app-header h1 {
  margin: 0;
  font-size: 1.6em; /* Slightly reduced font size for better fit */
  display: flex;
  align-items: center;
}
.app-header h1 .fas {
  margin-right: 12px;
}

.main-content {
  flex-grow: 1;
  padding: 20px; /* Horizontal padding */
  display: flex;
  flex-direction: column; 
  gap: 20px;
  max-width: 1200px; /* Match header-content-wrapper for alignment */
  width: 100%; 
  margin: 20px auto; /* Add top/bottom margin for spacing from header/footer */
}

.config-panel, .settings-panel, .data-panel {
  background-color: white;
  border: 1px solid var(--border-color);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.config-panel h2, .settings-panel h3, .data-panel h2 {
  margin-top: 0;
  color: var(--primary-color);
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 15px;
  font-size: 1.4em;
}
.config-panel h2 .fas, .settings-panel h3 .fas, .data-panel h2 .fas {
  margin-right: 8px;
}

.button-primary, .button-secondary {
  padding: 10px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.95em;
  transition: background-color 0.2s ease;
  margin-right: 10px;
}

.button-primary {
  background-color: var(--primary-color);
  color: white;
}
.button-primary:hover {
  background-color: #0056b3;
}
.button-primary:disabled {
  background-color: #aaa;
  cursor: not-allowed;
}

.button-secondary {
  background-color: var(--secondary-color);
  color: white;
}
.button-secondary:hover {
  background-color: #545b62;
}

.top-controls button .fas {
    margin-right: 6px;
}

.status {
  margin-top: 10px;
  font-size: 0.9em;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}
.status .fas {
  margin-right: 8px;
  font-size: 1.1em;
}

.status.success {
  color: var(--success-color);
  background-color: #e9f7ef;
  border-left: 4px solid var(--success-color);
}
.status.error {
  color: var(--error-color);
  background-color: #fdecea;
  border-left: 4px solid var(--error-color);
}
.status.info {
    color: var(--info-color);
    background-color: #e8f7fa;
    border-left: 4px solid var(--info-color);
}

.ws-connected { color: var(--success-color); }
.ws-disconnected { color: var(--error-color); }

.config-section textarea, .paste-area textarea {
  width: 100%;
  min-height: 150px;
  margin-top: 10px;
  margin-bottom: 10px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 10px;
}

.paste-area {
  margin-top: 15px;
  border: 1px solid var(--border-color);
  padding: 15px;
  border-radius: 4px;
  background-color: var(--light-bg);
}

.live-data-section {
    display: grid;
    grid-template-columns: 2fr 1fr; /* Map takes more space */
    gap: 20px;
}

.tracker-list-section ul {
  list-style: none;
  padding: 0;
  max-height: 300px; /* Increased height */
  overflow-y: auto;
  border: 1px solid var(--border-color);
  margin-top: 10px;
  border-radius: 4px;
}
.tracker-list-section li {
  margin-bottom: 0;
  font-size: 0.9em;
  border-bottom: 1px solid #f0f0f0;
  padding: 8px 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 5px 10px; /* Gap for items in the line */
  align-items: center;
}
.tracker-list-section li:last-child {
    border-bottom: none;
}
.tracker-list-section li .fas, .tracker-list-section li .far {
    margin-right: 5px;
    color: var(--text-muted);
}
.beacon-details {
  font-size: 0.9em;
  color: #555;
  word-break: break-all; /* Prevent long beacon strings from breaking layout */
}

/* Ensure settings panel is also styled */
.settings-panel {
    /* Inherits .config-panel styles, can add specific ones if needed */
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .live-data-section {
    grid-template-columns: 1fr; /* Stack map and tracker list on smaller screens */
  }
  .app-header {
    flex-direction: column;
    gap: 10px;
  }
}

.mqtt-control-panel {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  /* background-color: var(--panel-bg); Already applied by data-panel */
  /* border-radius: var(--panel-border-radius); Already applied by data-panel */
  /* box-shadow: 0 2px 8px rgba(0,0,0,0.07); Already applied by data-panel */
}

.mqtt-control-panel .status {
  margin-bottom: 0; /* Remove default margin from status component */
  flex-grow: 1; /* Allow status text to take available space */
}

.mqtt-connect-btn {
  /* Specific styles if needed */
  background-color: var(--success-color) !important;
  color: white !important;
}
.mqtt-connect-btn:hover {
  background-color: #1e7e34 !important;
}

.mqtt-disconnect-btn {
  background-color: var(--warn-color) !important;
  color: #212529 !important; /* Darker text for warning yellow */
}
.mqtt-disconnect-btn:hover {
  background-color: #e0a800 !important;
}

/* General Panel Styling */
.config-panel,
.data-panel,
.settings-panel {
  background-color: var(--panel-bg);
  padding: 20px;
  border-radius: var(--panel-border-radius);
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}

.config-panel h2, .data-panel h2, .settings-panel h3 {
  margin-top: 0;
  color: var(--primary-color);
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 15px;
  font-size: 1.4em;
}
.config-panel h2 .fas, .data-panel h2 .fas, .settings-panel h3 .fas {
  margin-right: 8px;
}

.button-link-styled {
  background: none;
  border: none;
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: underline;
  padding: 5px;
  font-size: 0.9em;
}
.button-link-styled:hover {
  color: #0056b3;
}
.button-link-styled .fas {
    margin-right: 4px;
}

.small-button {
    padding: 5px 10px;
    font-size: 0.85em;
}

/* Styles for panel headers to align title and button */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px; /* Existing margin-bottom from h2 */
}

.panel-header h2 {
  margin-bottom: 0; /* Remove bottom margin as it's handled by panel-header */
}

.template-controls-and-viewer {
    margin-top: 15px; /* Add some space above this section when it appears */
}

/* Config Template Viewer Styles */
.template-viewer-controls {
    margin-bottom: 10px;
}

.config-template-viewer {
  margin-top: 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: #f8f9fa; /* Light background for the pre block */
}
.config-template-viewer .template-actions {
    padding: 8px 12px;
    background-color: #f1f3f5;
    border-bottom: 1px solid var(--border-color);
    text-align: right;
}

.config-template-viewer pre {
  padding: 15px;
  margin: 0;
  max-height: 300px; 
  overflow: auto;
  white-space: pre-wrap; 
  word-break: break-all; 
  font-size: 0.85em;
  background-color: #fff; 
  border-radius: 0 0 4px 4px;
  text-align: left; /* Ensure JSON is left-aligned */
}
.config-template-viewer code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
}

/* Styling for the moved server settings button */
.server-settings-toggle-btn {
  /* Add specific styling if needed, or rely on .button-primary */
  /* Example: margin-left: auto; to push to far right if other elements are not flex-grow */
  margin-left: 10px; /* Add some space from the connect/disconnect button */
}

</style>

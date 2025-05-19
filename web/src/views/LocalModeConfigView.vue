<template>
  <div class="local-mode-config-view page-content-wrapper">
    <h1 class="page-title">Local Device Positioning Configuration</h1>
    <p class="info-banner status-display info" v-if="statusMessage">{{ statusMessage }}</p>

    <div class="config-management card">
      <div class="card-header">
        <h2>Configuration Management</h2>
        <div class="header-buttons">
          <button @click="loadDefaultTestConfig" class="button-link load-default-btn" title="Load a predefined test configuration from the server">
            <i class="fas fa-cogs"></i> Load Default Test Config
          </button>
          <button @click="isJsonInputAreaVisible = !isJsonInputAreaVisible" class="button-link toggle-json-input-btn">
            <i :class="isJsonInputAreaVisible ? 'fas fa-chevron-up' : 'fas fa-chevron-down'"></i> 
            {{ isJsonInputAreaVisible ? 'Hide JSON Input' : 'Show JSON Input' }}
          </button>
        </div>
      </div>
      <div class="card-content">
        <div v-if="isJsonInputAreaVisible" class="json-input-collapsible-area">
            <label for="jsonImportLocal">Paste Master Configuration JSON here:</label>
            <div class="textarea-button-row">
                <textarea id="jsonImportLocal" v-model="jsonInputForImport" rows="8" 
                          :placeholder="jsonPlaceholderText"></textarea>
                <button @click="handleImportMasterConfigJson" class="button-primary import-json-btn">Import & Save<br>Configuration</button>
            </div>
        </div>

        <p v-if="!currentFullConfig.map && !isJsonInputAreaVisible" class="status-display warning">Please import a master configuration file first by showing and using the JSON input area above, or configure one on the "Map & Beacon Configuration" page and export it.</p>
        <p v-if="!currentFullConfig.map && isJsonInputAreaVisible" class="status-display info">Paste your JSON above and click 'Import & Save'.</p>
        
        <div class="loaded-config-actions" v-if="currentFullConfig.map">
          <p class="status-display success loaded-config-text">
            Current configuration loaded: {{ currentFullConfig.map.name || 'Unnamed Map' }}.
            (Beacons: {{ currentFullConfig.beacons.length }}, Map Entities: {{ currentFullConfig.map.entities?.length || 0 }})
          </p>
          <button @click="clearLocalConfig" class="button-danger button-small">Clear This Configuration from Local Storage</button>
        </div>
      </div>
    </div>

    <div v-if="currentFullConfig.map" class="local-positioning card">
      <div class="card-header"><h2>Local Positioning Control</h2></div>
      <div class="card-content">
        
        <div class="position-control-merged-display">
            <div class="position-text-merged-area">
                <div v-if="isLocalPositioningRunning && (!currentFullConfig.beacons || currentFullConfig.beacons.length < 1)" class="status-display warning" style="margin-bottom: 5px; padding: 5px; font-size: 0.9em;">
                    There are no beacons in the current configuration. Please ensure the imported configuration includes beacons, or add beacons via the Master Configuration page.
                </div>
                <div v-if="localDevicePositionDisplay" class="local-position-text">
                    <strong>Local Device Position:</strong> {{ localDevicePositionDisplay }}
                </div>
                <div v-if="!localDevicePositionDisplay && isLocalPositioningRunning && currentFullConfig.beacons && currentFullConfig.beacons.length > 0" class="local-position-text">
                    <i>Waiting for position data...</i>
                </div>
                 <div v-if="!localDevicePositionDisplay && !isLocalPositioningRunning && isWebSocketConnected" class="local-position-text">
                    <i>Service connected. Click 'Start Local Positioning' to begin.</i>
                </div>
                 <div v-if="!isWebSocketConnected" class="local-position-text">
                    <i>Service disconnected. Click 'Connect to Local Service' to attempt connection.</i>
                </div>
            </div>
            <button 
              @click="isWebSocketConnected ? toggleLocalPositioning() : connectWebSocket()"
              :disabled="isWebSocketConnected && (!currentFullConfig.beacons || currentFullConfig.beacons.length < 1)"
              class="button-local-positioning-control">
              {{ 
                !isWebSocketConnected 
                  ? 'Connect to Local Service' 
                  : (isLocalPositioningRunning ? 'Stop Local Positioning' : 'Start Local Positioning') 
              }}
            </button>
        </div>

         <p v-if="statusMessageLocalPositioning" :class="['status-display', localPositioningStatusType]">{{statusMessageLocalPositioning}}</p>
      </div>
    </div>

    <div v-if="currentFullConfig.map" class="map-display card">
      <div class="card-header"><h2>Map Preview (Local Device Position)</h2></div>
      <div class="card-content map-view-wrapper-local">
        <MapView 
          v-if="currentFullConfig.map" 
          :config="currentFullConfig" 
          :trackers="localDeviceAsTrackerArray" 
          :initial-show-trails="currentFullConfig.settings.showTrails"
          @trails-toggled="handleTrailsToggled"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import MapView from '@/components/MapView.vue'; // Changed from MapEditorTab
import { loadConfigFromLocalStorage, saveConfigToLocalStorage, clearConfigFromLocalStorage } from '@/services/localStorageService.js';
import { calculatePosition, calculateDistance, setSignalFactor } from '@/utils/positioning/positionCalculator.js';
import { loadServerConfiguration } from '@/services/configApiService.js'; // Example, might not be the right one

const CONFIG_STORAGE_KEY = 'localModeConfig';

const jsonInputForImport = ref('');
const initialLocalConfig = () => ({
  map: null,
  beacons: [],
  settings: { signalPropagationFactor: 2.5, positioningAlgorithm: 'trilateration', showTrails: false } 
});
const currentFullConfig = ref(initialLocalConfig()); 

// Initialize based on the initial state of currentFullConfig.map
const isJsonInputAreaVisible = ref(!currentFullConfig.value.map);

const jsonPlaceholderText = `Paste your full configuration JSON here (map, beacons, settings). Example structure:
{
  "map": { "name": "My Map", "image": "data:image/png;base64,...", "width": 1000, "height": 800, "origin": {"x":0,"y":0}, "ppm": 10, "entities":[] },
  "beacons": [ { "uuid": "...", "major":1, "minor":1, "x":10,"y":20,"txPower":-59, "name":"B1" } ],
  "settings": { "signalPropagationFactor": 2.5, "showTrails": false }
}`;

const statusMessage = ref('');
const statusMessageLocalPositioning = ref('Attempting to connect to local beacon service...');
const localPositioningStatusType = ref('info'); 

const isLocalPositioningRunning = ref(false);
const localDevicePosition = ref(null); // { x, y, accuracy, method }
const localDevicePositionHistory = ref([]); // For trails
const detectedBeaconsForPositioning = ref([]);

// WebSocket State (remains the same)
const socket = ref(null);
const serviceUrl = 'ws://localhost:8081';
const isWebSocketConnected = ref(false);
const retryCount = ref(0);
const maxRetries = 5;
const retryTimeout = 5000;
let connectTimeoutId = null;
let scanActiveOnServer = ref(false);

// Computed property to format localDevicePosition for MapView
const localDeviceAsTrackerArray = computed(() => {
  if (localDevicePosition.value) {
    return [{
      trackerId: 'localDevice',
      x: localDevicePosition.value.x,
      y: localDevicePosition.value.y,
      accuracy: localDevicePosition.value.accuracy,
      position_history: currentFullConfig.value.settings.showTrails ? localDevicePositionHistory.value.map(p => [p.x, p.y]) : []
    }];
  }
  return [];
});

watch(localDevicePosition, (newPos, oldPos) => {
  // Only add to history if the position has actually changed and trails are enabled
  if (newPos && currentFullConfig.value.settings.showTrails) {
    if (!oldPos || newPos.x !== oldPos.x || newPos.y !== oldPos.y) {
        localDevicePositionHistory.value.push({ x: newPos.x, y: newPos.y });
        if (localDevicePositionHistory.value.length > 100) { 
            localDevicePositionHistory.value.shift();
        }
    }
  } 
  // If trails are turned off, or position is lost, history is handled by localDeviceAsTrackerArray or cleared elsewhere
});

// Watch for showTrails setting change to clear history if trails are turned off
watch(() => currentFullConfig.value.settings.showTrails, (show) => {
    if (!show) {
        localDevicePositionHistory.value = [];
    }
});

watch(detectedBeaconsForPositioning, (newDetectedBeacons) => {
  if (isLocalPositioningRunning.value && newDetectedBeacons.length > 0 && currentFullConfig.value.beacons.length > 0) {
    setSignalFactor(currentFullConfig.value.settings.signalPropagationFactor);
    const beaconsForCalc = newDetectedBeacons.map(detected => {
      const configured = currentFullConfig.value.beacons.find(cfg => 
        cfg.uuid === detected.uuid && cfg.major === detected.major && cfg.minor === detected.minor
      );
      if (configured) {
        const distance = calculateDistance(detected.rssi, detected.txPower);
        if (distance !== null) {
          return { id: configured.deviceId || configured.uuid, x: configured.x, y: configured.y, txPower: configured.txPower, rssi: detected.rssi, distance: distance };
        }
      }
      return null;
    }).filter(b => b !== null);

    if (beaconsForCalc.length > 0) {
      const positionResult = calculatePosition(beaconsForCalc);
      if (positionResult) {
        localDevicePosition.value = { x: positionResult.x, y: positionResult.y, accuracy: null, method: positionResult.method };
      } 
    } 
  }
}, { deep: true });

// WebSocket methods (connectWebSocket, disconnectWebSocket, sendWebSocketMessage, handleServiceStatusUpdate) remain the same

const handleServiceStatusUpdate = (status) => {
  console.log('[LocalModeConfigView] Service Status Update:', status);
  statusMessageLocalPositioning.value = status.message;
  switch (status.type) {
    case 'connecting': localPositioningStatusType.value = 'info'; break;
    case 'connected': localPositioningStatusType.value = 'success'; break;
    case 'disconnected':
      localPositioningStatusType.value = 'warn';
      if (isLocalPositioningRunning.value || scanActiveOnServer.value) {
        isLocalPositioningRunning.value = false; scanActiveOnServer.value = false;
        statusMessageLocalPositioning.value = status.message + " Positioning stopped.";
      }
      break;
    case 'error':
      localPositioningStatusType.value = 'error';
      if (status.message.includes('Bluetooth adapter') || status.message.includes('Failed to start')){
        isLocalPositioningRunning.value = false; scanActiveOnServer.value = false;
      }
      break;
    case 'info': 
      localPositioningStatusType.value = 'info';
      if (status.message === 'Scanning started.') {
        scanActiveOnServer.value = true;
        statusMessageLocalPositioning.value = 'Local positioning active. Receiving beacon data...';
      } else if (status.message === 'Scanning stopped.') {
        scanActiveOnServer.value = false;
        if(isLocalPositioningRunning.value) isLocalPositioningRunning.value = false;
        statusMessageLocalPositioning.value = detectedBeaconsForPositioning.value.length === 0 ? 'Positioning stopped. No beacon data was received.' : `Positioning stopped. Last data had ${detectedBeaconsForPositioning.value.length} beacon(s).`;
      }
      break;
    default: localPositioningStatusType.value = 'info';
  }
};

const connectWebSocket = () => {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) return;
  handleServiceStatusUpdate({ type: 'connecting', message: `Attempting to connect to local beacon service at ${serviceUrl}... (Attempt ${retryCount.value + 1})` });
  socket.value = new WebSocket(serviceUrl);
  socket.value.onopen = () => {
    isWebSocketConnected.value = true; retryCount.value = 0; if (connectTimeoutId) clearTimeout(connectTimeoutId);
    handleServiceStatusUpdate({ type: 'connected', message: 'Successfully connected to local beacon service.' });
  };
  socket.value.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === 'beacon' && message.data) {
        const beaconData = message.data; const beaconKey = beaconData.id;
        let parsedUuid = 'N/A', parsedMajor = null, parsedMinor = null, parsedTxPower = -59;
        if (beaconData.iBeacon) {
            parsedUuid = beaconData.iBeacon.uuid || 'N/A';
            if (beaconData.iBeacon.major !== null) parsedMajor = parseInt(beaconData.iBeacon.major, 10);
            if (beaconData.iBeacon.minor !== null) parsedMinor = parseInt(beaconData.iBeacon.minor, 10);
            if (beaconData.iBeacon.txPowerCalibrated !== null) parsedTxPower = parseInt(beaconData.iBeacon.txPowerCalibrated, 10);
        }
        if (parsedUuid === 'N/A' || parsedMajor === null || parsedMinor === null) return;
        const existingBeaconIndex = detectedBeaconsForPositioning.value.findIndex(b => b.id === beaconKey);
        const beaconInfo = { id: beaconKey, rssi: parseInt(beaconData.rssi, 10), uuid: parsedUuid, major: parsedMajor, minor: parsedMinor, txPower: parsedTxPower };
        if (existingBeaconIndex > -1) detectedBeaconsForPositioning.value.splice(existingBeaconIndex, 1, beaconInfo);
        else detectedBeaconsForPositioning.value.push(beaconInfo);
      } else if (message.type === 'info') handleServiceStatusUpdate({ type: 'info', message: message.message });
      else if (message.type === 'error') handleServiceStatusUpdate({ type: 'error', message: `Server Error: ${message.message}` });
    } catch (error) { console.error('[LocalModeConfigView] Error processing WebSocket message:', error); handleServiceStatusUpdate({ type: 'error', message: 'Received malformed message from server.' }); }
  };
  socket.value.onerror = (error) => console.error('[LocalModeConfigView] WebSocket Error:', error);
  socket.value.onclose = (event) => {
    isWebSocketConnected.value = false; scanActiveOnServer.value = false;
    if (isLocalPositioningRunning.value) isLocalPositioningRunning.value = false;
    if (retryCount.value < maxRetries) {
      retryCount.value++;
      handleServiceStatusUpdate({ type: 'disconnected', message: `Disconnected. Retrying connection (${retryCount.value}/${maxRetries}) in ${retryTimeout / 1000}s...` });
      if (connectTimeoutId) clearTimeout(connectTimeoutId); connectTimeoutId = setTimeout(connectWebSocket, retryTimeout);
    } else handleServiceStatusUpdate({ type: 'error', message: `Failed to connect after ${maxRetries} retries. Please check the local service and refresh.` });
  };
};

const disconnectWebSocket = () => {
  if (connectTimeoutId) clearTimeout(connectTimeoutId); retryCount.value = maxRetries;
  if (socket.value) { socket.value.close(1000, 'Client initiated disconnect'); socket.value = null; }
  isWebSocketConnected.value = false; scanActiveOnServer.value = false;
  if (isLocalPositioningRunning.value) isLocalPositioningRunning.value = false;
};

const sendWebSocketMessage = (messageObject) => {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) socket.value.send(JSON.stringify(messageObject));
  else showStatus('Cannot send command: Local service not connected.', 'error', 'localPos');
};

// localDevicePositionDisplay computed prop remains the same
const localDevicePositionDisplay = computed(() => {
  if (!localDevicePosition.value) return 'Position not yet available.';
  let display = `X: ${localDevicePosition.value.x.toFixed(2)}, Y: ${localDevicePosition.value.y.toFixed(2)}`;
  if (localDevicePosition.value.accuracy !== undefined && localDevicePosition.value.accuracy !== null) {
    display += `, Accuracy: ${localDevicePosition.value.accuracy.toFixed(2)}m`;
  }
  if (localDevicePosition.value.method) {
    // Translate method to English
    let methodName = localDevicePosition.value.method;
    if (methodName === '三边测量') methodName = 'Trilateration';
    else if (methodName === '最小二乘法') methodName = 'Least Squares';
    else if (methodName === '加权质心') methodName = 'Weighted Centroid';
    display += `, Method: ${methodName}`;
  }
  return display;
});

// showStatus method remains the same
const showStatus = (msg, type = 'info', target = 'main') => {
  if (target === 'localPos') {
    statusMessageLocalPositioning.value = msg;
    localPositioningStatusType.value = type;
    setTimeout(() => { if(statusMessageLocalPositioning.value === msg) statusMessageLocalPositioning.value = ''; }, 5000);
  } else {
    statusMessage.value = msg;
    setTimeout(() => { if(statusMessage.value === msg) statusMessage.value = ''; }, 5000);
  }
};

// handleImportMasterConfigJson and loadConfig remain mostly the same, but no longer call initializeServicesWithConfig
const handleImportMasterConfigJson = () => {
  if (!jsonInputForImport.value.trim()) {
    showStatus('JSON input is empty. Please paste configuration data.', 'error');
    return;
  }
  try {
    const jsonData = JSON.parse(jsonInputForImport.value);
    if (jsonData && jsonData.map && Array.isArray(jsonData.beacons) && jsonData.settings) {
      currentFullConfig.value = { map: jsonData.map, beacons: jsonData.beacons, settings: { ...initialLocalConfig().settings, ...jsonData.settings } };
      saveConfigToLocalStorage(CONFIG_STORAGE_KEY, currentFullConfig.value);
      setSignalFactor(currentFullConfig.value.settings.signalPropagationFactor);
      showStatus('Master configuration successfully imported and saved to local storage.', 'success');
      // MapView will react to prop changes, no explicit loadConfiguration call needed on localMapRef
    } else {
      showStatus('Invalid JSON structure. Ensure it has map, beacons, and settings properties.', 'error');
    }
  } catch (error) {
    showStatus(`Failed to parse JSON: ${error.message}`, 'error');
  }
};

const loadConfig = () => {
  const loaded = loadConfigFromLocalStorage(CONFIG_STORAGE_KEY);
  if (loaded) {
    currentFullConfig.value = { map: loaded.map || null, beacons: loaded.beacons || [], settings: { ...initialLocalConfig().settings, ...(loaded.settings || {}) } };
    // isJsonInputAreaVisible.value = false; // Set by onMounted after this call
    setSignalFactor(currentFullConfig.value.settings.signalPropagationFactor); 
    showStatus('Local mode configuration loaded from local storage.');
    return true;
  }
  // isJsonInputAreaVisible.value = true; // Set by onMounted after this call
  showStatus('No local mode configuration found. Please import a master configuration.');
  return false;
};

// clearLocalConfig remains mostly the same
const clearLocalConfig = () => {
  if (confirm('Are you sure you want to clear the local mode configuration?')) {
    if(isLocalPositioningRunning.value) {
      sendWebSocketMessage({ command: 'stopScan' });
      isLocalPositioningRunning.value = false; scanActiveOnServer.value = false;
    }
    clearConfigFromLocalStorage(CONFIG_STORAGE_KEY);
    currentFullConfig.value = initialLocalConfig();
    localDevicePosition.value = null; detectedBeaconsForPositioning.value = []; localDevicePositionHistory.value = [];
    showStatus('Configuration cleared.');
  }
};

// toggleLocalPositioning remains mostly the same
const toggleLocalPositioning = async () => {
  if (!currentFullConfig.value || !currentFullConfig.value.beacons || currentFullConfig.value.beacons.length === 0) {
    showStatus('Cannot start: No beacons defined in the configuration.', 'error', 'localPos'); return;
  }
  if (!isWebSocketConnected.value) {
    showStatus('Cannot start: Local beacon service not connected.', 'error', 'localPos'); return;
  }
  if (isLocalPositioningRunning.value) {
    sendWebSocketMessage({ command: 'stopScan' });
    isLocalPositioningRunning.value = false; 
    localDevicePosition.value = null; detectedBeaconsForPositioning.value = []; 
    // Keep history for a bit if user quickly restarts, or clear: localDevicePositionHistory.value = [];
    showStatus('Stop command sent to local positioning service.', 'info', 'localPos');
  } else {
    if (currentFullConfig.value.settings.showTrails) { // Clear history only when starting a new session if trails are on
        localDevicePositionHistory.value = []; 
    }
    sendWebSocketMessage({ command: 'startScan', ignoredMacAddresses: [] });
    isLocalPositioningRunning.value = true;
    detectedBeaconsForPositioning.value = []; localDevicePosition.value = null; localDevicePositionHistory.value = []; // Clear history on new start
    showStatus('Start command sent. Waiting for beacon data...', 'info', 'localPos');
  }
};

// Removed handleLocalMapReady as MapView manages its own drawing based on props

onMounted(() => {
  if (loadConfig()) { 
    isJsonInputAreaVisible.value = false; // Collapse if config was successfully loaded
  } else {
    isJsonInputAreaVisible.value = true;  // Expand if no config was loaded
  }
  // setSignalFactor is called within loadConfig or based on initialLocalConfig if loadConfig fails.
  // If loadConfig calls currentFullConfig.value setter, signal factor is set there.
  // If loadConfig returns false, we might need to ensure factor is set from initial.
  // However, setSignalFactor is already in loadConfig and handled if it returns false by prior logic block in original onMounted.
  // Re-evaluating the setSignalFactor placement. It's in loadConfig() and in the else block of onMounted in original code.
  // Let's ensure factor is set correctly based on loaded/initial config.
  if (currentFullConfig.value && currentFullConfig.value.settings) {
      setSignalFactor(currentFullConfig.value.settings.signalPropagationFactor);
  } else {
      setSignalFactor(initialLocalConfig().settings.signalPropagationFactor); // Fallback
  }

  connectWebSocket();
});

onUnmounted(() => {
  if (scanActiveOnServer.value) sendWebSocketMessage({ command: 'stopScan' });
  disconnectWebSocket();
});

// Ensure saveConfigToStorage is defined if used in template, or integrate into existing save functions
const saveConfigToStorage = () => {
  saveConfigToLocalStorage(CONFIG_STORAGE_KEY, currentFullConfig.value);
  showStatus('Trail setting saved.', 'info');
};

const handleTrailsToggled = (newTrailState) => {
  if (currentFullConfig.value && currentFullConfig.value.settings) {
    currentFullConfig.value.settings.showTrails = newTrailState;
    saveConfigToStorage(); // Save when toggled via map
  }
};

const loadDefaultTestConfig = async () => {
  showStatus('Loading default test configuration from server...', 'info');
  try {
    // Make sure the server is running and this endpoint is available
    const response = await fetch('/api/default-test-config'); 
    if (!response.ok) {
      throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
    }
    const configText = await response.text(); // Assuming server sends plain text JSON
    jsonInputForImport.value = configText;
    isJsonInputAreaVisible.value = true; // Ensure the input area is visible
    showStatus('Default test configuration loaded into textarea. Click Import & Save to apply.', 'info');
    // Optionally, directly import it:
    // handleImportMasterConfigJson(); 
    // showStatus('Default test configuration loaded and imported.', 'success');
  } catch (error) {
    console.error('Failed to load default test configuration:', error);
    showStatus(`Failed to load default config: ${error.message}`, 'error');
  }
};

</script>

<style scoped>
/* Remove scoped .page-container or .page-content-wrapper if present */

/* .page-title style is now global in style.css */
/*
.page-title {
  font-size: 1.8rem;
  color: var(--primary-color-dark);
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
}
*/

.config-management,
.local-positioning,
.map-display {
  margin-bottom: 1.5rem;
}

/* .card-content padding is now global
.card-content {
  padding: 1rem;
}
*/
.card-content button {
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
}

.local-position-display {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #f0f2f5;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.95em;
}

.position-control-merged-display {
  display: flex;
  align-items: center; 
  background-color: #f0f2f5; 
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.75rem;
  margin-bottom: 10px; 
}

.button-local-positioning-control {
  margin-left: 15px;
  flex-shrink: 0;
}

.position-text-merged-area {
  flex-grow: 1; 
}

.local-position-text { /* Style for the actual position text */
  font-size: 0.95em;
}

.settings-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.settings-inline label {
  margin-bottom: 0;
}

.map-view-wrapper-local .card-content {
  /* Ensures MapView can expand. MapView.vue has display:block on canvas */
  /* May need specific height or aspect ratio control depending on MapView's internal sizing */
  min-height: 450px; /* Example: give it some minimum height */
  display: flex; /* To center MapView if it doesn't take full width */
  justify-content: center; /* Center MapView horizontally */
  align-items: center; /* Center MapView vertically */
  overflow: hidden; /* If MapView canvas tries to be too large */
}

.config-management .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 10px; /* Space between buttons in the header */
}

.load-default-btn,
.toggle-json-input-btn {
  font-size: 0.9em;
  padding: 5px 8px; 
}

.json-input-collapsible-area {
  margin-bottom: 15px; 
  border: 1px solid var(--border-color);
  padding: 1rem;
  border-radius: var(--border-radius);
  background-color: #fdfdfd;
}

.textarea-button-row {
  display: flex;
  align-items: flex-start; /* Align items to the top */
  gap: 10px;
}

.textarea-button-row textarea {
  flex-grow: 1;
  /* Ensure textarea does not shrink if button text is long */
  min-width: 0; 
}

.import-json-btn {
  flex-shrink: 0; /* Prevent button from shrinking */
  /* Allow button text to wrap if needed, adjust padding as necessary */
  white-space: normal;
  text-align: center;
  padding: 10px; /* Adjust padding for better appearance with wrapped text */
  line-height: 1.2;
}

.loaded-config-actions {
  display: flex;
  align-items: center; /* Vertically align items in the middle */
  justify-content: space-between; /* Puts space between the text and the button */
  padding: 0.75rem;
  background-color: #e6ffed; /* Light green background for success */
  border: 1px solid #b7ebc0; /* Green border - specific success state */
  border-radius: var(--border-radius); /* Use var for consistency */
  margin-top: 15px;
  margin-bottom: 15px;
}

.loaded-config-text { /* Style for the p tag containing the loaded config text */
  margin: 0; /* Remove default paragraph margins */
  flex-grow: 1; /* Allow text to take up available space */
  padding-right: 10px; /* Add some space to the right of the text, before the button */
  text-align: left; /* Ensure text is left-aligned */
}

.loaded-config-actions .button-danger {
  flex-shrink: 0; /* Prevent the button from shrinking */
}

.toggle-json-input-btn {
  margin-left: 10px; /* Add some space between the buttons in the header */
}

.load-default-btn {
  /* Styles for the load default button if any specific are needed */
}

.json-input-collapsible-area {
  margin-bottom: 15px; /* Add space below the JSON input area when visible */
}

.textarea-button-row {
  display: flex;
  align-items: flex-start; /* Align textarea top with button top */
  gap: 10px; /* Space between textarea and button */
  margin-bottom:10px; /* Space below this row */
}

.textarea-button-row textarea {
  flex-grow: 1; /* Textarea takes available space */
  /* min-height: 100px; Ensure a decent minimum height */
}

.textarea-button-row .import-json-btn {
  flex-shrink: 0; /* Prevent button from shrinking */
  white-space: normal; /* Allow button text to wrap */
  text-align: center;
  padding: 8px 12px; /* Adjust padding if needed */
  /* max-width: 150px; /* Optional: constrain button width */
}

/* General Card Styling - already moved to global, ensure it's not duplicated or conflicting if still here */
/* Specific styles for LocalModeConfigView */
.local-mode-config-view {
  padding-bottom: 20px; /* Add some padding at the bottom */
}

</style> 
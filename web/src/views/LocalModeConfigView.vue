<template>
  <div class="local-mode-config-view page-container">
    <h1 class="page-title">Local Device Positioning Configuration</h1>
    <p class="info-banner status-display info" v-if="statusMessage">{{ statusMessage }}</p>

    <div class="config-management card">
      <div class="card-header"><h2>Configuration Management</h2></div>
      <div class="card-content">
        <!-- <input type="file" @change="handleImportMasterConfigFile" accept=".json" ref="importMasterFileRef" style="display: none;" /> -->
        <!-- <button @click="triggerImportMasterFile" class="button-primary">Import Master Configuration (JSON)</button> -->
        
        <label for="jsonImportLocal">Paste Master Configuration JSON here:</label>
        <textarea id="jsonImportLocal" v-model="jsonInputForImport" rows="8" 
                  :placeholder="jsonPlaceholderText"></textarea>
        <button @click="handleImportMasterConfigJson" class="button-primary">Import & Save Configuration (from Textarea)</button>

        <p v-if="!currentFullConfig.map" class="status-display warning">Please import a master configuration file first.</p>
        <p v-else class="status-display success">
          Current configuration loaded: {{ currentFullConfig.map.name || 'Unnamed Map' }}.
          (Beacons: {{ currentFullConfig.beacons.length }}, Map Entities: {{ currentFullConfig.map.entities?.length || 0 }})
        </p>
        <button @click="clearLocalConfig" v-if="currentFullConfig.map" class="button-danger button-small">Clear This Configuration from Local Storage</button>
      </div>
    </div>

    <div v-if="currentFullConfig.map" class="local-positioning card">
      <div class="card-header"><h2>Local Positioning Control</h2></div>
      <div class="card-content">
        <button @click="toggleLocalPositioning" :disabled="!currentFullConfig.beacons || currentFullConfig.beacons.length < 1">
          {{ isLocalPositioningRunning ? 'Stop Local Positioning' : 'Start Local Positioning' }}
        </button>
        <div v-if="isLocalPositioningRunning && (!currentFullConfig.beacons || currentFullConfig.beacons.length < 1)" class="status-display warning">
          There are no beacons in the current configuration. Please ensure the imported configuration includes beacons, or add beacons via the Master Configuration page.
        </div>
        <div v-if="localDevicePositionDisplay" class="local-position-display">
          <strong>Local Device Position:</strong> {{ localDevicePositionDisplay }}
        </div>
         <p v-if="statusMessageLocalPositioning" :class="['status-display', localPositioningStatusType]">{{statusMessageLocalPositioning}}</p>
      </div>
    </div>

    <div v-if="currentFullConfig.map" class="map-display card">
      <div class="card-header"><h2>Map Preview (Local Device Position)</h2></div>
      <div class="card-content">
        <MapEditorTab 
          ref="localMapRef"
          :configured-beacons="currentFullConfig.beacons"
          :current-local-device-position="localDevicePosition"
          :initial-map-data="currentFullConfig.map" 
          :is-read-only="true" 
          @map-loaded="handleLocalMapReady" 
        />
        <!-- 
          Note: MapEditorTab is complex. For a purely display purpose, a simpler MapView component
          might be better if MapEditorTab's editing features are not needed or cause issues.
          For now, using MapEditorTab with is-read-only.
        -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import MapEditorTab from '@/components/configuration/MapEditorTab.vue'; // Reusing for display
import { loadConfigFromLocalStorage, saveConfigToLocalStorage, clearConfigFromLocalStorage } from '@/services/localStorageService.js';
import * as localPositioningService from '@/services/localPositioningService.js';

const CONFIG_STORAGE_KEY = 'localModeConfig';

// const importMasterFileRef = ref(null); // Removed
const jsonInputForImport = ref(''); // Added for textarea
const localMapRef = ref(null);

const jsonPlaceholderText = `Paste your full configuration JSON here (map, beacons, settings). Example structure:
{
  "map": { "name": "My Map", "image": "data:image/png;base64,...", "width": 1000, "height": 800, "origin": {"x":0,"y":0}, "ppm": 10, "entities":[] },
  "beacons": [ { "uuid": "...", "major":1, "minor":1, "x":10,"y":20,"txPower":-59, "name":"B1" } ],
  "settings": { "signalPropagationFactor": 2.5 }
}`;

const statusMessage = ref('');
const statusMessageLocalPositioning = ref('');
const localPositioningStatusType = ref('info'); // 'info', 'success', 'error'

const initialLocalConfig = () => ({ // Renamed from initialPersonalConfig
  map: null,
  beacons: [],
  settings: { signalPropagationFactor: 2.5 } // Default, will be overwritten by import
});
const currentFullConfig = ref(initialLocalConfig()); // Use renamed init function

const isLocalPositioningRunning = ref(false);
const localDevicePosition = ref(null); // { x, y, accuracy, method }

const localDevicePositionDisplay = computed(() => {
  if (!localDevicePosition.value) return 'Position not yet available.';
  let display = `X: ${localDevicePosition.value.x.toFixed(2)}, Y: ${localDevicePosition.value.y.toFixed(2)}`;
  if (localDevicePosition.value.accuracy !== undefined) {
    display += `, Accuracy: ${localDevicePosition.value.accuracy.toFixed(2)}m`;
  }
  if (localDevicePosition.value.method) {
    display += `, Method: ${localDevicePosition.value.method}`;
  }
  return display;
});

const showStatus = (msg, type = 'info', target = 'main') => {
  if (target === 'localPos') {
    statusMessageLocalPositioning.value = msg;
    localPositioningStatusType.value = type;
    setTimeout(() => { statusMessageLocalPositioning.value = '' }, 5000);
  } else {
    statusMessage.value = msg;
    setTimeout(() => { statusMessage.value = '' }, 5000);
  }
};

// const triggerImportMasterFile = () => { // Removed
//   importMasterFileRef.value.click();
// };

// Replaces handleImportMasterConfigFile
const handleImportMasterConfigJson = () => {
  if (!jsonInputForImport.value.trim()) {
    showStatus('JSON input is empty. Please paste configuration data.', 'error');
    return;
  }
  try {
    const jsonData = JSON.parse(jsonInputForImport.value);
    if (jsonData && jsonData.map && Array.isArray(jsonData.beacons) && jsonData.settings) {
      currentFullConfig.value = jsonData;
      saveConfigToLocalStorage(CONFIG_STORAGE_KEY, currentFullConfig.value);
      showStatus('Master configuration successfully imported from textarea and saved to local storage.', 'success');
      initializeServicesWithConfig();
      jsonInputForImport.value = ''; // Clear textarea after successful import
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
    currentFullConfig.value = loaded;
    showStatus('Local mode configuration loaded from local storage.'); // Updated text
    initializeServicesWithConfig();
    return true;
  }
  showStatus('No local mode configuration found in local storage. Please import a master configuration.'); // Updated text
  return false;
};

const clearLocalConfig = () => {
  if (confirm('Are you sure you want to clear the local mode configuration from local storage? This action cannot be undone.')) { // Updated text
    if(isLocalPositioningRunning.value) {
      localPositioningService.stopLocalPositioning();
      isLocalPositioningRunning.value = false;
    }
    clearConfigFromLocalStorage(CONFIG_STORAGE_KEY);
    currentFullConfig.value = initialLocalConfig(); // Use renamed init function
    localDevicePosition.value = null;
    showStatus('Configuration cleared from local storage.');
     nextTick(() => { 
        if (localMapRef.value && localMapRef.value.loadConfiguration) { // Use renamed ref
             localMapRef.value.loadConfiguration(currentFullConfig.value);
        } else if (localMapRef.value && localMapRef.value.redrawMap) { // Use renamed ref
            localMapRef.value.redrawMap(); 
        }
    });
  }
};

const initializeServicesWithConfig = () => {
  if (currentFullConfig.value && currentFullConfig.value.map) {
    // Initialize local positioning service with the current config
    // The callback updates the localDevicePosition ref, which is used by the map
    localPositioningService.initialize(currentFullConfig.value, (pos) => {
      localDevicePosition.value = pos;
    });

    // Tell MapEditorTab to load the new map data
    nextTick(() => {
        if (localMapRef.value && localMapRef.value.loadConfiguration) { // Use renamed ref
             localMapRef.value.loadConfiguration(currentFullConfig.value);
        } else if (localMapRef.value && localMapRef.value.redrawMap) { // Use renamed ref
            localMapRef.value.redrawMap(); 
        }
    });
  }
};

const toggleLocalPositioning = async () => {
  if (!currentFullConfig.value || !currentFullConfig.value.beacons || currentFullConfig.value.beacons.length === 0) {
    showStatus('Cannot start positioning: No beacons defined in the configuration.', 'error', 'localPos');
    return;
  }

  if (isLocalPositioningRunning.value) {
    try {
      await localPositioningService.stopLocalPositioning();
      isLocalPositioningRunning.value = false;
      localDevicePosition.value = null; // Clear position when stopping
      showStatus('Local positioning stopped.', 'info', 'localPos');
    } catch (e) {
      showStatus(`Error stopping positioning: ${e.message}`, 'error', 'localPos');
    }
  } else {
    try {
      // Ensure service is initialized with current config before starting
      localPositioningService.initialize(currentFullConfig.value, (pos) => {
         localDevicePosition.value = pos;
      });
      await localPositioningService.startLocalPositioning();
      isLocalPositioningRunning.value = true;
      showStatus('Local positioning started.', 'success', 'localPos');
    } catch (e) {
      isLocalPositioningRunning.value = false; // Ensure state is correct on error
      showStatus(`Error starting positioning: ${e.message}`, 'error', 'localPos');
      console.error("Error starting local positioning:", e);
    }
  }
};

const handleLocalMapReady = (mapData) => { // Renamed from handlePersonalMapReady
  console.log('LocalModeConfigView: Map component is ready or reloaded.', mapData); // Updated log text
};

onMounted(() => {
  loadConfig();
});

onUnmounted(() => {
  if (isLocalPositioningRunning.value) {
    localPositioningService.stopLocalPositioning();
  }
});

</script>

<style scoped>
.page-container {
  padding: 1.5rem;
  width: 100%;
  max-width: 1000px; 
  margin: 0 auto;
  box-sizing: border-box;
}

.page-title {
  font-size: 1.8rem;
  color: var(--primary-color-dark);
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
}

.config-management,
.local-positioning,
.map-display {
  margin-bottom: 1.5rem;
}

.card-content {
  padding: 1rem;
}
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

.status-display { /* Already global, but for context */
  margin-top: 0.5rem;
}

/* Make MapEditorTab take up available space within its container */
.map-display .card-content {
  min-height: 400px; /* Ensure map has space */
  display: flex; /* If MapEditorTab itself isn't taking full width */
}
.map-display .card-content > :deep(div) { /* Target the root div of MapEditorTab if necessary */
  flex-grow: 1;
}

</style> 
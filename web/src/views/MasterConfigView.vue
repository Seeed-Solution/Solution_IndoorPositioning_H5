<template>
  <div class="master-config-view page-container">
    <h1 class="page-title">Map & Beacon Configuration</h1>
    <p class="info-banner status-display info" v-if="configStatusMessage">{{ configStatusMessage }}</p>

    <div class="global-actions card">
      <div class="card-header"><h2>Configuration Actions</h2></div>
      <div class="card-content">
        <input type="file" @change="handleImportFullConfigurationFile" accept=".json" ref="importFileRef" style="display: none;" />
        <button @click="triggerImportFile" :disabled="isLoadingConfig" class="button-primary">Import Configuration from File</button>
        <button @click="exportFullConfiguration" :disabled="!currentConfiguration.map || isLoadingConfig">Export Configuration to Clipboard</button>
        <p class="info-banner info" style="margin-top:10px;">This section is for creating or modifying a complete map and beacon setup. Use 'Export' to copy the configuration, then import it into 'Personal Mode' or 'Tracker Mode'. Changes here are for the current session and are not automatically saved to the server or other modes.</p>
      </div>
    </div>

    <div class="tabs-navigation">
      <button @click="activeTab = 'beacons'" :class="{ active: activeTab === 'beacons' }">Beacon Management</button>
      <button @click="activeTab = 'map'" :class="{ active: activeTab === 'map' }">Map Editor</button>
      <button @click="activeTab = 'settings'" :class="{ active: activeTab === 'settings' }">General Settings</button>
    </div>

    <div class="tab-content card">
      <div class="card-content">
        <BeaconManagerTab 
          v-if="activeTab === 'beacons'" 
          ref="beaconManagerTabRef"
          :initial-beacons="currentConfiguration.beacons"
          @beacons-updated="handleBeaconsUpdated"
          @beacon-selected-for-placement="handleBeaconSelectedForPlacement"
        />
        <MapEditorTab 
          v-if="activeTab === 'map'" 
          ref="mapEditorTabRef"
          :initial-map-data="currentConfiguration.map" 
          :configured-beacons="currentConfiguration.beacons"
          :selected-beacon-for-placement="selectedBeaconForPlacement"
          :current-local-device-position="null" 
          :initial-settings="currentConfiguration.settings"
          @map-loaded="handleMapOrSettingsLoadedFromMapEditor"
          @config-updated="handleConfigUpdatedFromMapEditor"
          @request-beacon-selection="handleRequestBeaconSelection"
        />
        <GeneralSettingsTab 
          v-if="activeTab === 'settings'"
          ref="generalSettingsTabRef"
          :initial-settings="currentConfiguration.settings"
          @settings-updated="handleSettingsUpdated"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';
import BeaconManagerTab from '@/components/configuration/BeaconManagerTab.vue';
import MapEditorTab from '@/components/configuration/MapEditorTab.vue';
import GeneralSettingsTab from '@/components/configuration/GeneralSettingsTab.vue';
// Removed: loadWebConfiguration, saveWebConfiguration from configApiService

const activeTab = ref('beacons'); 

const beaconManagerTabRef = ref(null);
const mapEditorTabRef = ref(null);
const generalSettingsTabRef = ref(null);
const importFileRef = ref(null);

const isLoadingConfig = ref(false); // Kept for import operation
const configStatusMessage = ref('');

const initialConfiguration = () => ({
  map: null,
  beacons: [],
  settings: {
    signalPropagationFactor: 2.5,
    // Add other default settings as needed
  }
});

const currentConfiguration = ref(initialConfiguration());
const selectedBeaconForPlacement = ref(null);

// --- Event Handlers from Child Components ---
const handleBeaconsUpdated = (newBeacons) => {
  currentConfiguration.value.beacons = JSON.parse(JSON.stringify(newBeacons));
  // If map editor is active, it might need to know about beacon changes for display
  if (activeTab.value === 'map' && mapEditorTabRef.value?.updateBeaconsList) {
    mapEditorTabRef.value.updateBeaconsList(currentConfiguration.value.beacons);
  }
};

const handleBeaconSelectedForPlacement = (beacon) => {
  selectedBeaconForPlacement.value = beacon;
  activeTab.value = 'map'; 
  if (beacon) {
    configStatusMessage.value = `Beacon "${beacon.displayName}" selected. Click on the map in the 'Map Editor' tab to place it.`;
  }
};

// Unified handler for when MapEditorTab loads/updates map or settings data internally (e.g., image upload)
const handleMapOrSettingsLoadedFromMapEditor = (loadedData) => {
  // MapEditorTab now emits a full config object structure or specific parts
  let changed = false;
  if (loadedData.map) {
    currentConfiguration.value.map = JSON.parse(JSON.stringify(loadedData.map));
    changed = true;
  }
  // MapEditor can also adjust settings like map scale, which should be part of general settings
  if (loadedData.settings) { 
    currentConfiguration.value.settings = { ...currentConfiguration.value.settings, ...JSON.parse(JSON.stringify(loadedData.settings)) };
    changed = true;
  }

  if (changed) {
    configStatusMessage.value = 'Map or map-related settings updated from Map Editor.';
    nextTick(() => {
      if (generalSettingsTabRef.value?.loadSettings) { // Update general settings tab if settings changed
         generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
    });
  }
  
  // If MapEditorTab emits beacons (e.g. if it allows removing them from map), handle here too
  if (loadedData.beacons && Array.isArray(loadedData.beacons)) {
    currentConfiguration.value.beacons = JSON.parse(JSON.stringify(loadedData.beacons));
    if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
    }
  }
};


// Unified handler for detailed updates from MapEditor (like beacon coordinate changes)
const handleConfigUpdatedFromMapEditor = (updateDetail) => {
  if (updateDetail.type === 'beaconUpdateCoordinates') {
    const { beaconIdentifier, newCoordinates } = updateDetail;
    const beaconIndex = currentConfiguration.value.beacons.findIndex(b => 
      b.uuid === beaconIdentifier.uuid && 
      b.major === beaconIdentifier.major && 
      b.minor === beaconIdentifier.minor &&
      (b.macAddress || b.id || null) === (beaconIdentifier.macAddress || beaconIdentifier.id || null) // id for scanned, macAddress for manually added
    );
    if (beaconIndex !== -1) {
      currentConfiguration.value.beacons[beaconIndex].x = newCoordinates.x;
      currentConfiguration.value.beacons[beaconIndex].y = newCoordinates.y;
      selectedBeaconForPlacement.value = null; 
      configStatusMessage.value = `Beacon "${currentConfiguration.value.beacons[beaconIndex].displayName}" position updated on map.`;
       // Notify BeaconManagerTab to refresh if it displays coordinates
      if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
    }
  } else if (updateDetail.type === 'mapNameChanged') {
    if (currentConfiguration.value.map) {
      currentConfiguration.value.map.name = updateDetail.name;
      configStatusMessage.value = 'Map name updated.';
    }
  } else if (updateDetail.type === 'mapEntitiesUpdated') {
     if (currentConfiguration.value.map) {
      currentConfiguration.value.map.entities = JSON.parse(JSON.stringify(updateDetail.entities));
      configStatusMessage.value = 'Map entities updated.';
    }
  }
  // Add other specific updates from MapEditorTab if needed
};

const handleSettingsUpdated = (newSettings) => {
  currentConfiguration.value.settings = JSON.parse(JSON.stringify(newSettings));
  configStatusMessage.value = 'General settings updated.';
  // If map editor depends on any of these settings, notify it
  if (activeTab.value === 'map' && mapEditorTabRef.value?.updateSettings) {
     mapEditorTabRef.value.updateSettings(currentConfiguration.value.settings);
  }
};

const handleRequestBeaconSelection = () => {
  configStatusMessage.value = "Please select a beacon from the 'Beacon Management' tab first to place it on the map.";
  activeTab.value = 'beacons';
};

// --- Global Actions ---
const triggerImportFile = () => {
  selectedBeaconForPlacement.value = null;
  importFileRef.value.click(); 
};

const handleImportFullConfigurationFile = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  isLoadingConfig.value = true;
  configStatusMessage.value = 'Importing configuration file...';
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const jsonData = JSON.parse(e.target.result);
      processAndApplyFullConfig(jsonData, 'Configuration successfully imported from file.');
    } catch (error) {
      configStatusMessage.value = `Failed to import JSON file: ${error.message}`;
    } finally {
      isLoadingConfig.value = false;
      event.target.value = null; // Reset file input
      setTimeout(() => { configStatusMessage.value = '' }, 7000);
    }
  };
  reader.onerror = () => {
    configStatusMessage.value = 'Error reading file.';
    isLoadingConfig.value = false;
    event.target.value = null;
    setTimeout(() => { configStatusMessage.value = '' }, 7000);
  };
  reader.readAsText(file);
};

const exportFullConfiguration = () => {
  if (!currentConfiguration.value.map && currentConfiguration.value.beacons.length === 0) {
    configStatusMessage.value = 'No configuration data (map or beacons) to export.';
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
    return;
  }
  try {
    const jsonString = JSON.stringify(currentConfiguration.value, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      configStatusMessage.value = 'Configuration copied to clipboard.';
    }).catch(err => {
      configStatusMessage.value = 'Failed to copy to clipboard. See console for error. You may need to grant clipboard permissions.';
      console.error('Clipboard write error:', err);
    });
  } catch (e) {
    configStatusMessage.value = 'Export failed: JSON serialization error.';
    console.error('JSON serialization error:', e);
  }
  setTimeout(() => { configStatusMessage.value = '' }, 7000);
};

// --- Server-related functions are REMOVED ---
// fetchServerConfiguration removed
// saveConfigurationToServer removed

// Function to deeply apply imported/loaded configuration to currentConfiguration
// and ensure child components are updated.
const processAndApplyFullConfig = (configData, successMessage) => {
  if (configData && (configData.map || Array.isArray(configData.beacons) || configData.settings) ) {
    // Ensure all parts are at least initialized to prevent errors if some are missing from import
    const newConfig = {
        map: configData.map ? JSON.parse(JSON.stringify(configData.map)) : currentConfiguration.value.map || null,
        beacons: Array.isArray(configData.beacons) ? JSON.parse(JSON.stringify(configData.beacons)) : currentConfiguration.value.beacons || [],
        settings: configData.settings ? JSON.parse(JSON.stringify(configData.settings)) : currentConfiguration.value.settings || initialConfiguration().settings,
    };
    currentConfiguration.value = newConfig;
    selectedBeaconForPlacement.value = null; 

    configStatusMessage.value = successMessage;
    
    nextTick(() => {
      if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
      if (mapEditorTabRef.value?.loadConfiguration) { // This method should take the full config
        mapEditorTabRef.value.loadConfiguration(currentConfiguration.value); 
      }
      if (generalSettingsTabRef.value?.loadSettings) {
        generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
      // This attempt to force re-render tab might not be needed if children react to props properly.
      // const currentActiveTab = activeTab.value;
      // activeTab.value = ''; 
      // nextTick(() => { activeTab.value = currentActiveTab; });
    });

  } else {
    configStatusMessage.value = 'Imported data is not a valid configuration structure.';
    console.error("Invalid config structure on import:", configData);
  }
  // Clear message after a delay handled by callers or a general timeout if preferred
};


// Lifecycle Hooks
onMounted(() => {
  configStatusMessage.value = 'Welcome to Map & Beacon Configuration. Create a new setup or import an existing one from a file.';
  setTimeout(() => { configStatusMessage.value = '' }, 7000);
  // No automatic loading from server. Starts fresh or retains previous session state if any.
});

// Watchers are generally not needed here if props/events are handled correctly for child components.
// Child components receive initial data via props.
// Child components emit updates, parent updates currentConfiguration.
// Vue's reactivity should ensure props are updated in children.
// Explicit loadConfiguration/loadBeacons/loadSettings methods on child refs are used after a full import.

</script>

<style scoped>
.page-container {
  padding: 1.5rem;
  max-width: 1000px; 
  margin: 0 auto;
}

.page-title {
  font-size: 1.8rem;
  color: var(--primary-color-dark);
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
}

.global-actions, .tabs-navigation, .tab-content {
  margin-bottom: 1.5rem;
}
.card-header { /* Re-style if needed, or use global card styles */ }
.card-content { padding: 1rem; }
.card-content button:not(:last-child) { margin-right: 0.5rem; }
.info-banner { margin-top: 0.5rem; } /* Global info banner styles are in style.css */


.tabs-navigation {
  display: flex;
  border-bottom: 1px solid var(--border-color, #ccc);
}
.tabs-navigation button {
  padding: 0.75rem 1.5rem;
  border: none;
  background-color: transparent;
  cursor: pointer;
  font-size: 1rem;
  color: var(--text-color-light);
  border-bottom: 3px solid transparent; /* For active indicator */
  margin-bottom: -1px; /* Align with parent border */
}
.tabs-navigation button.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
  font-weight: bold;
}
.tabs-navigation button:hover:not(.active) {
  background-color: var(--hover-bg-color, #f5f5f5);
  color: var(--primary-color-dark);
}
</style>

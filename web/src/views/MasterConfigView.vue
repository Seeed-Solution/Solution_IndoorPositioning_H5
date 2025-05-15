<template>
  <div class="master-config-view page-content-wrapper">
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
      <button @click="activeTab = 'map'" :class="{ active: activeTab === 'map' }">Map Editor</button>
      <button @click="activeTab = 'beacons'" :class="{ active: activeTab === 'beacons' }">Beacon Management</button>
      <button @click="activeTab = 'settings'" :class="{ active: activeTab === 'settings' }">General Settings</button>
    </div>

    <div class="tab-content card">
      <div class="card-content">
        <keep-alive>
          <MapEditorTab 
            v-show="activeTab === 'map'" 
            ref="mapEditorTabRef"
            :initial-map-data="currentConfiguration.map" 
            :configured-beacons="currentConfiguration.beacons"
            :selected-beacon-for-placement="selectedBeaconForPlacement"
            :current-local-device-position="null" 
            :initial-settings="currentConfiguration.settings"
            @map-loaded="handleMapOrSettingsLoadedFromMapEditor"
            @config-updated="handleConfigUpdatedFromMapEditor"
            @request-beacon-selection="handleRequestBeaconSelection"
            @beacon-coordinates-updated="handleBeaconCoordinatesUpdatedFromMapEditor" 
            @placement-confirmed="handlePlacementConfirmedFromMapEditor"
          />
        </keep-alive>
        <keep-alive>
          <BeaconManagerTab 
            v-show="activeTab === 'beacons'" 
            ref="beaconManagerTabRef"
            :initial-beacons="currentConfiguration.beacons"
            :current-map-layout="currentConfiguration.map"
            @beacons-updated="handleBeaconsUpdated"
            @beacon-selected-for-placement="handleBeaconSelectedForPlacement"
          />
        </keep-alive>
        <keep-alive>
          <GeneralSettingsTab 
            v-show="activeTab === 'settings'"
            ref="generalSettingsTabRef"
            :initial-settings="currentConfiguration.settings"
            @settings-updated="handleSettingsUpdated"
          />
        </keep-alive>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue';
import BeaconManagerTab from '@/components/configuration/BeaconManagerTab.vue';
import MapEditorTab from '@/components/configuration/MapEditorTab.vue';
import GeneralSettingsTab from '@/components/configuration/GeneralSettingsTab.vue';
// Removed: loadWebConfiguration, saveWebConfiguration from configApiService

const SESSION_STORAGE_KEY = 'masterConfigData';

const activeTab = ref('map'); /* Default to Map Editor tab */

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

// Load initial config from session storage or use defaults
const loadConfigFromSessionStorage = () => {
  const storedConfig = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (storedConfig) {
    try {
      return JSON.parse(storedConfig);
    } catch (e) {
      console.error('Error parsing master config from session storage:', e);
      sessionStorage.removeItem(SESSION_STORAGE_KEY); // Clear invalid data
    }
  }
  return initialConfiguration();
};

const currentConfiguration = ref(loadConfigFromSessionStorage());
const selectedBeaconForPlacement = ref(null);

// Watch for changes in currentConfiguration.value.beacons specifically for debugging
watch(() => currentConfiguration.value.beacons, (newBeaconsList, oldBeaconsList) => {
  console.log('[MasterConfigView - Watcher for beacons list] Beacon list changed.');
  console.log('  New list length:', newBeaconsList ? newBeaconsList.length : 'N/A');
  console.log('  Old list length:', oldBeaconsList ? oldBeaconsList.length : 'N/A');
  console.log('  New list content:', JSON.parse(JSON.stringify(newBeaconsList)));
  // You can add a stack trace here if needed to see what triggered the change:
  // console.trace('Beacon list changed stack trace');
}, { deep: true });

// Watch for changes in currentConfiguration and save to session storage
watch(currentConfiguration, (newConfig) => {
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newConfig));
    console.log('[MasterConfigView] Configuration saved to session storage.');
  } catch (e) {
    console.error('Error saving master config to session storage:', e);
  }
}, { deep: true });

// --- Event Handlers from Child Components ---
const handleBeaconsUpdated = (newBeacons) => {
  console.log('[MasterConfigView - handleBeaconsUpdated] Received beacons-updated event.');
  console.log('  Data received (newBeacons):', JSON.parse(JSON.stringify(newBeacons)));
  console.log('  currentConfiguration.beacons BEFORE update:', JSON.parse(JSON.stringify(currentConfiguration.value.beacons)));
  
  currentConfiguration.value.beacons = JSON.parse(JSON.stringify(newBeacons));
  
  console.log('  currentConfiguration.beacons AFTER update:', JSON.parse(JSON.stringify(currentConfiguration.value.beacons)));
  console.log('  Length of currentConfiguration.beacons AFTER update:', currentConfiguration.value.beacons ? currentConfiguration.value.beacons.length : 'N/A');

  // If map editor is active, it might need to know about beacon changes for display
  if (activeTab.value === 'map' && mapEditorTabRef.value?.updateBeaconsList) {
    mapEditorTabRef.value.updateBeaconsList(currentConfiguration.value.beacons);
  }
};

const handleBeaconSelectedForPlacement = (beacon) => {
  selectedBeaconForPlacement.value = beacon;
  // Use nextTick to ensure DOM/state updates from a potential preceding beacons-updated event
  // are processed before switching tabs and MapEditorTab becomes active with the selected beacon.
  nextTick(() => {
    activeTab.value = 'map'; 
    if (beacon) {
      configStatusMessage.value = `Beacon "${beacon.displayName}" selected. Click on the map in the 'Map Editor' tab to place it.`;
      // Consider also logging here the state of currentConfiguration.value.beacons 
      // to see if it's populated as expected when selection occurs.
      console.log('[MasterConfigView - handleBeaconSelectedForPlacement (in nextTick)] Selected beacon for placement:', JSON.parse(JSON.stringify(beacon)));
      console.log('  Current beacons list at this point:', JSON.parse(JSON.stringify(currentConfiguration.value.beacons)));
    }
  });
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

const handleBeaconCoordinatesUpdatedFromMapEditor = (updatedBeacon) => {
  // --- DETAILED LOGGING START ---
  console.log("--- [MasterConfigView] Attempting to Update Beacon Coordinates --- ");
  console.log("[MasterConfigView] TARGET Beacon (from map click):", JSON.parse(JSON.stringify(updatedBeacon)));
  
  const beaconToUpdateUUID = updatedBeacon.uuid ? String(updatedBeacon.uuid).toUpperCase() : null;
  const beaconToUpdateMajor = updatedBeacon.major;
  const beaconToUpdateMinor = updatedBeacon.minor;

  // Check if this update is for the beacon currently being edited/added in the BeaconManagerTab modal
  if (selectedBeaconForPlacement.value && 
      selectedBeaconForPlacement.value.uuid === beaconToUpdateUUID &&
      selectedBeaconForPlacement.value.major === beaconToUpdateMajor &&
      selectedBeaconForPlacement.value.minor === beaconToUpdateMinor &&
      beaconManagerTabRef.value && 
      typeof beaconManagerTabRef.value.updateCoordinatesForBeaconInModal === 'function'
  ) {
    console.log("[MasterConfigView] Forwarding coordinate update to BeaconManagerTab modal.");
    beaconManagerTabRef.value.updateCoordinatesForBeaconInModal(
      beaconToUpdateUUID,
      beaconToUpdateMajor,
      beaconToUpdateMinor,
      updatedBeacon.x,
      updatedBeacon.y
    );
    // The modal is now updated. We don't clear selectedBeaconForPlacement here because the user might want to click again.
    // The 'Save' or 'Cancel' in the modal will handle clearing it or applying the changes.
    configStatusMessage.value = `Coordinates for ${updatedBeacon.displayName || 'selected beacon'} updated in the form. Save to confirm.`;
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
    return; // Exit early as the modal handled it
  }

  // If not handled by the modal, proceed with updating the main configuration list
  // This path is for beacons that are already configured and are being re-positioned directly,
  // or if the modal flow isn't active for some reason.
  console.log("[MasterConfigView] Beacon not being edited in modal, or modal communication failed. Attempting to update in main list.");
  const currentBeaconList = currentConfiguration.value.beacons;
  console.log("[MasterConfigView] SEARCH LIST (currentConfiguration.beacons at time of search):\n", JSON.parse(JSON.stringify(currentBeaconList)));

  if (!currentBeaconList || currentBeaconList.length === 0) {
    console.warn("[MasterConfigView] The SEARCH LIST (currentConfiguration.value.beacons) is EMPTY. Cannot find the target beacon.");
  }

  const beaconIndex = currentConfiguration.value.beacons.findIndex((b, index) => {
    console.log(`[MasterConfigView - findIndex] Comparing with beacon at index ${index} in list:`, JSON.parse(JSON.stringify(b)));
    const listBeaconUUID = b.uuid ? String(b.uuid).toUpperCase() : null;
    
    console.log(`  Target (from map click): UUID=${beaconToUpdateUUID}, Major=${beaconToUpdateMajor}, Minor=${beaconToUpdateMinor}`);
    console.log(`  List item (index ${index}):   UUID=${listBeaconUUID}, Major=${b.major}, Minor=${b.minor}`);

    const canCompareByFullIBProperties = 
      beaconToUpdateUUID && typeof beaconToUpdateMajor === 'number' && typeof beaconToUpdateMinor === 'number' &&
      listBeaconUUID && typeof b.major === 'number' && typeof b.minor === 'number';

    console.log(`  Can compare by full iBeacon properties? ${canCompareByFullIBProperties}`);

    if (canCompareByFullIBProperties) {
      const isMatch = listBeaconUUID === beaconToUpdateUUID &&
                      b.major === beaconToUpdateMajor &&
                      b.minor === beaconToUpdateMinor;
      console.log(`  Full iBeacon properties match result: ${isMatch}`);
      return isMatch;
    }
    
    console.log('  Comparison by full iBeacon properties skipped (incomplete data on one or both sides).');
    return false;
  });

  console.log(`[MasterConfigView] Result of findIndex on SEARCH LIST: ${beaconIndex}`);
  console.log("--- [MasterConfigView] Finished Attempt to Update Beacon Coordinates --- ");

  if (beaconIndex !== -1) {
    currentConfiguration.value.beacons[beaconIndex].x = updatedBeacon.x;
    currentConfiguration.value.beacons[beaconIndex].y = updatedBeacon.y;
    configStatusMessage.value = `Beacon "${currentConfiguration.value.beacons[beaconIndex].displayName}" position updated successfully.`;
    if (beaconManagerTabRef.value?.loadConfiguredBeacons) { // Refresh beacon manager list if needed
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
    }
  } else {
    console.warn(
        "[MasterConfigView] Beacon to update coordinates for NOT FOUND in the list (after modal check).",
        "Target Beacon (from map click):", JSON.parse(JSON.stringify(updatedBeacon)),
        "Searched List (currentConfiguration.beacons at time of search):", JSON.parse(JSON.stringify(currentConfiguration.value.beacons))
    );
    configStatusMessage.value = "错误：尝试更新位置的信标未在已配置列表中找到。如果您正在编辑一个新信标，请确保从信标表单中点击'从地图更新坐标'。";
  }
  selectedBeaconForPlacement.value = null; // Clear selection after attempt, regardless of outcome for this path
  setTimeout(() => { configStatusMessage.value = '' }, 7000);
};

const handlePlacementConfirmedFromMapEditor = () => {
  activeTab.value = 'beacons';
  configStatusMessage.value = "Beacon placed. Select another beacon or edit existing ones.";
  // selectedBeaconForPlacement is already cleared by handleBeaconCoordinatesUpdatedFromMapEditor
  // which is called by MapEditorTab before placement-confirmed or should be if the flow is correct.
  // For safety, ensure it's cleared:
  selectedBeaconForPlacement.value = null;
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
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
  // Configuration is loaded from session storage upon ref initialization
  // Update status message or perform other onMount tasks
  if (currentConfiguration.value.map || currentConfiguration.value.beacons.length > 0) {
    configStatusMessage.value = 'Previously unsaved configuration loaded from session. Use Export to save permanently.';
  } else {
    configStatusMessage.value = 'Welcome to Map & Beacon Configuration. Create a new setup or import an existing one from a file.';
  }
  setTimeout(() => { configStatusMessage.value = '' }, 7000);
});

// Watchers are generally not needed here if props/events are handled correctly for child components.
// Child components receive initial data via props.
// Child components emit updates, parent updates currentConfiguration.
// Vue's reactivity should ensure props are updated in children.
// Explicit loadConfiguration/loadBeacons/loadSettings methods on child refs are used after a full import.

</script>

<style scoped>
/* Remove the scoped style for page-content-wrapper to ensure global style is applied */
/* 
.page-content-wrapper { 
  padding: 1.5rem;
  max-width: 1000px; 
  margin: 0 auto; 
  width: 100%;
}
*/

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
  color: var(--secondary-color); /* Was var(--text-color-light), now secondary gray */
  border-bottom: 3px solid transparent; /* For active indicator */
  margin-bottom: -1px; /* Align with parent border */
  transition: color 0.2s ease, border-bottom-color 0.2s ease; /* Added transitions */
}
.tabs-navigation button.active {
  color: var(--primary-color); /* Green text for active */
  border-bottom-color: var(--primary-color); /* Green underline for active */
  font-weight: bold;
}
.tabs-navigation button:hover:not(.active) {
  /* background-color: var(--hover-bg-color, #f5f5f5); */ /* Removed hover background */
  color: var(--primary-color); /* Green text on hover for inactive tabs */
}
</style>

<template>
  <div class="configuration-suite page-container">
    <h1 class="page-title">设备与地图配置</h1>
    <p class="info-banner status-display info" v-if="configStatusMessage">{{ configStatusMessage }}</p>

    <div class="global-actions card">
      <div class="card-header"><h2>全局操作</h2></div>
      <div class="card-content">
        <input type="file" @change="handleImportFullConfigurationFile" accept=".json" ref="importFileRef" style="display: none;" />
        <button @click="triggerImportFile" :disabled="isLoadingConfig" class="button-primary">导入完整配置 (JSON)</button>
        <button @click="exportFullConfiguration" :disabled="!currentConfiguration.map || isLoadingConfig">导出完整配置</button>
        <button @click="fetchServerConfiguration" :disabled="isLoadingConfig || currentPositioningMode === 'local'" title="从服务器加载最新配置">加载服务器配置</button>
        <button @click="saveConfigurationToServer" :disabled="!currentConfiguration.map || isLoadingConfig || currentPositioningMode === 'local'" title="将当前配置保存到服务器">保存配置到服务器</button>
      </div>
    </div>

    <div class="tabs-navigation">
      <button @click="activeTab = 'beacons'" :class="{ active: activeTab === 'beacons' }">信标管理</button>
      <button @click="activeTab = 'map'" :class="{ active: activeTab === 'map' }">地图编辑</button>
      <button @click="activeTab = 'settings'" :class="{ active: activeTab === 'settings' }">通用设置</button>
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
          :configured-beacons="currentConfiguration.beacons"
          :selected-beacon-for-placement="selectedBeaconForPlacement"
          :current-local-device-position="localDevicePosition" 
          @map-loaded="handleMapLoaded"
          @config-updated="handleConfigUpdated"
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

    <div class="positioning-mode-switcher card">
      <div class="card-header"><h2>定位模式</h2></div>
      <div class="card-content">
        <select v-model="currentPositioningMode" @change="handleModeChange">
          <option value="external">追踪外部信标设备</option>
          <option value="local">追踪本机设备</option>
        </select>
        <p v-if="currentPositioningMode === 'local'" class="mode-info">
          本机追踪模式：浏览器将扫描已配置的固定信标，并进行本地定位计算。
        </p>
        <div v-if="currentPositioningMode === 'local'" class="local-positioning-controls">
          <button @click="toggleLocalPositioning" :disabled="!currentConfiguration.beacons || currentConfiguration.beacons.length < 1">
            {{ isLocalPositioningRunning ? '停止本机定位' : '开始本机定位' }}
          </button>
          <div v-if="localDevicePosition" class="local-position-display">
            本机位置: X: {{ localDevicePosition.x !== null ? localDevicePosition.x.toFixed(2) : 'N/A' }}, 
            Y: {{ localDevicePosition.y !== null ? localDevicePosition.y.toFixed(2) : 'N/A' }}
            <span v-if="localDevicePosition.accuracy !== undefined"> (精度: {{ localDevicePosition.accuracy.toFixed(2) }}m)</span>
            <span v-if="localDevicePosition.method"> (方法: {{ localDevicePosition.method }})</span>
          </div>
          <p v-if="isLocalPositioningRunning && (!currentConfiguration.beacons || currentConfiguration.beacons.length < 1)" class="status-display warning">
            请先在"信标管理"中配置至少一个固定信标才能开始本机定位。
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue';
import BeaconManagerTab from '@/components/configuration/BeaconManagerTab.vue';
import MapEditorTab from '@/components/configuration/MapEditorTab.vue';
import GeneralSettingsTab from '@/components/configuration/GeneralSettingsTab.vue';
import { loadWebConfiguration, saveWebConfiguration } from '@/services/configApiService.js';
import { loadConfigFromLocalStorage, saveConfigToLocalStorage } from '@/services/localStorageService.js';
import * as localPositioningService from '@/services/localPositioningService.js';

const activeTab = ref('beacons');
const currentPositioningMode = ref('external');

// Refs for child components
const beaconManagerTabRef = ref(null);
const mapEditorTabRef = ref(null);
const generalSettingsTabRef = ref(null);
const importFileRef = ref(null);

const isLoadingConfig = ref(false);
const configStatusMessage = ref(''); // For displaying loading/saving status or errors

const initialConfiguration = () => ({
  map: null, // { name, width, height, entities: [] }
  beacons: [], // [{ uuid, major, minor, x, y, txPower, displayName, macAddress }]
  settings: { // { signalPropagationFactor }
    signalPropagationFactor: 2.5, // Default value
  }
});

const currentConfiguration = ref(initialConfiguration());
const selectedBeaconForPlacement = ref(null); // { uuid, major, minor, ... }

const isLocalPositioningRunning = ref(false);
const localDevicePosition = ref(null); // Will store { x, y, accuracy, method, etc. }


// --- Event Handlers from Child Components ---

const handleBeaconsUpdated = (newBeacons) => {
  currentConfiguration.value.beacons = JSON.parse(JSON.stringify(newBeacons));
  console.log("ConfigurationSuiteView: Beacons updated", currentConfiguration.value.beacons);
};

const handleBeaconSelectedForPlacement = (beacon) => {
  selectedBeaconForPlacement.value = beacon;
  activeTab.value = 'map'; // Switch to map tab automatically
  if (beacon) {
    alert(`信标 "${beacon.displayName}" 已选定，请在地图上点击以放置。`);
  }
};

const handleMapLoaded = (loadedConfig) => { // This event comes from MapEditorTab when it loads a *full* config
  if (loadedConfig && loadedConfig.map && loadedConfig.beacons && loadedConfig.settings) {
    currentConfiguration.value.map = JSON.parse(JSON.stringify(loadedConfig.map));
    currentConfiguration.value.beacons = JSON.parse(JSON.stringify(loadedConfig.beacons));
    currentConfiguration.value.settings = JSON.parse(JSON.stringify(loadedConfig.settings));
    
    selectedBeaconForPlacement.value = null; // Reset placement selection

    // Ensure child components are updated with the new full configuration
    nextTick(() => {
      if (beaconManagerTabRef.value && beaconManagerTabRef.value.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
      // MapEditorTab's loadConfiguration would have been called by itself or via its own prop watcher for configuredBeacons
      // but we can also explicitly call it if needed, though its internal 'mapLoaded' already set its state.
      // If mapEditorTabRef.value?.loadConfiguration exists, it would be for external calls.
      // Its current 'mapLoaded' emitter implies it manages its own state upon successful file upload.
      // What we need is to ensure *its* `configuredBeacons` prop is updated if we load a full config here.

      if (mapEditorTabRef.value && mapEditorTabRef.value.loadConfiguration) { // If mapEditorTab has a method to take the whole config
         mapEditorTabRef.value.loadConfiguration(currentConfiguration.value); // Pass the whole thing
      } else if (mapEditorTabRef.value && mapEditorTabRef.value.redrawMap) { // Or at least tell it to redraw if map changed
         mapEditorTabRef.value.redrawMap();
      }


      if (generalSettingsTabRef.value && generalSettingsTabRef.value.loadSettings) {
        generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
    });
    console.log("ConfigurationSuiteView: Full configuration loaded/updated.", currentConfiguration.value);
  } else {
    console.error("ConfigurationSuiteView: mapLoaded event did not provide a valid full configuration.", loadedConfig);
  }
};

const handleConfigUpdated = (updateDetail) => { // Primarily for beacon coordinate updates from MapEditorTab
  if (updateDetail.type === 'beaconUpdateCoordinates') {
    const { beaconIdentifier, newCoordinates } = updateDetail;
    const beaconIndex = currentConfiguration.value.beacons.findIndex(b => 
      b.uuid === beaconIdentifier.uuid && 
      b.major === beaconIdentifier.major && 
      b.minor === beaconIdentifier.minor &&
      // Handle cases where macAddress might be null or undefined consistently
      (b.macAddress || null) === (beaconIdentifier.macAddress || null)
    );

    if (beaconIndex !== -1) {
      currentConfiguration.value.beacons[beaconIndex].x = newCoordinates.x;
      currentConfiguration.value.beacons[beaconIndex].y = newCoordinates.y;
      console.log(`ConfigurationSuiteView: Beacon ${currentConfiguration.value.beacons[beaconIndex].displayName} coordinates updated.`);
      // Deselect beacon after placement
      selectedBeaconForPlacement.value = null; 
      // The map tab should redraw automatically due to prop changes.
    } else {
      console.warn("ConfigurationSuiteView: Beacon to update coordinates for not found.", beaconIdentifier);
    }
  }
  // Potentially handle other 'configUpdated' types here
};

const handleSettingsUpdated = (newSettings) => {
  currentConfiguration.value.settings = JSON.parse(JSON.stringify(newSettings));
  console.log("ConfigurationSuiteView: Settings updated", currentConfiguration.value.settings);
};

const handleRequestBeaconSelection = () => {
  alert("请先从'信标管理'标签页选择一个信标，然后才能在地图上放置。");
  activeTab.value = 'beacons';
};

// --- Global Actions ---

const triggerImportFile = () => {
  selectedBeaconForPlacement.value = null; // Clear any pending placement
  importFileRef.value.click(); 
};

const handleImportFullConfigurationFile = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  isLoadingConfig.value = true;
  configStatusMessage.value = '正在导入配置文件...';

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const jsonData = JSON.parse(e.target.result);
      processAndApplyFullConfig(jsonData, '配置文件已成功从本地文件导入并应用。');
    } catch (error) {
      console.error("Configuration import error:", error);
      configStatusMessage.value = `导入JSON文件失败: ${error.message}`;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
    }
    isLoadingConfig.value = false;
  };
  reader.onerror = () => {
      configStatusMessage.value = '读取文件时发生错误。';
      isLoadingConfig.value = false;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
  };
  reader.readAsText(file);
  event.target.value = null; // Reset file input
};

const exportFullConfiguration = () => {
  if (!currentConfiguration.value.map) {
    alert('没有配置数据可导出。请先导入或创建配置。');
    return;
  }
  try {
    const jsonString = JSON.stringify(currentConfiguration.value, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      alert('完整配置已复制到剪贴板。');
    }).catch(err => {
      console.error('复制到剪贴板失败: ', err);
      alert('复制失败。请查看控制台，并可手动复制。' + jsonString);
    });
  } catch (e) {
    alert('导出配置失败: JSON序列化错误。');
    console.error('JSON序列化错误:', e);
  }
};

const fetchServerConfiguration = async () => {
  if (currentPositioningMode.value === 'local') {
    configStatusMessage.value = '处于本地模式，请从浏览器缓存加载或导入文件。';
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
    return;
  }
  isLoadingConfig.value = true;
  configStatusMessage.value = '正在从服务器加载配置...';
  try {
    const loadedConfig = await loadWebConfiguration();
    if (loadedConfig) {
        // The backend might return a default empty-ish config if web_config.json doesn't exist.
        // We should check if it actually contains a map to consider it "valid" for practical use.
        if (loadedConfig.map) { 
            processAndApplyFullConfig(loadedConfig, '配置已成功从服务器加载并应用。');
        } else {
            // If no map, it means it's likely a default/empty config from server
            // We can either apply this empty state or keep current local state.
            // Applying it makes the UI consistent with server state.
            processAndApplyFullConfig(loadedConfig, '服务器上没有找到保存的地图配置，已加载默认空配置。');
            // Alternatively, one might choose to inform the user and not overwrite a locally modified config
            // configStatusMessage.value = '服务器上没有地图配置。当前本地配置未更改。';
        }
    } else {
        // This case might occur if API returns null or undefined, though our service tries to make it an empty object.
        configStatusMessage.value = '从服务器加载配置失败：未收到有效数据。';
        // Consider loading initialConfiguration() as a fallback
        // applyFullConfiguration(initialConfiguration());
    }
  } catch (error) {
    console.error("Failed to fetch server configuration:", error);
    configStatusMessage.value = `加载服务器配置错误: ${error.message}`;
  }
  isLoadingConfig.value = false;
  setTimeout(() => { configStatusMessage.value = '' }, 7000);
};

const saveConfigurationToServer = async () => {
  if (currentPositioningMode.value === 'local') {
    configStatusMessage.value = '处于本地模式，配置已自动保存到浏览器缓存。如需同步到服务器，请先切换到外部模式。';
    setTimeout(() => { configStatusMessage.value = '' }, 7000);
    return;
  }
  if (!currentConfiguration.value.map) { // Also ensure there is something to save
    configStatusMessage.value = '没有地图配置，无法保存到服务器。请先创建或导入地图。';
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
    return;
  }
  isLoadingConfig.value = true;
  configStatusMessage.value = '正在保存配置到服务器...';
  try {
    const response = await saveWebConfiguration(currentConfiguration.value);
    configStatusMessage.value = response.message || '配置已成功保存到服务器！';
    console.log("Save response:", response);
  } catch (error) {
    console.error("Failed to save configuration to server:", error);
    configStatusMessage.value = `保存配置到服务器失败: ${error.message}`;
  }
  isLoadingConfig.value = false;
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
};


// --- Positioning Mode ---
const handleModeChange = async () => {
  console.log(`Positioning mode changed to: ${currentPositioningMode.value}`);
  isLoadingConfig.value = true;
  if (isLocalPositioningRunning.value) { // Stop local positioning if it's running before changing mode
    await localPositioningService.stopLocalPositioning();
    isLocalPositioningRunning.value = false;
    localDevicePosition.value = null;
  }

  if (currentPositioningMode.value === 'local') {
    configStatusMessage.value = '切换到本地模式，正在加载本地配置...';
    const localConfig = loadConfigFromLocalStorage();
    if (localConfig) {
      applyFullConfiguration(localConfig);
      configStatusMessage.value = '本地配置已加载。';
    } else {
      saveConfigToLocalStorage(currentConfiguration.value);
      configStatusMessage.value = '未找到本地配置，当前配置已保存为本地副本。';
    }
    // Initialize local positioning service with the current (possibly just loaded from local) config
    localPositioningService.initialize(currentConfiguration.value, updateLocalDevicePositionDisplay);
  } else { // Switching to 'external'
    configStatusMessage.value = '切换到外部模式，正在从服务器加载配置...';
    await fetchServerConfiguration(); 
  }
  isLoadingConfig.value = false;
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
  // TODO: Communicate mode change to backend or main application state if necessary
};

// Lifecycle Hooks
onMounted(async () => {
  // Default to 'external' and load from server initially.
  // User can then switch to 'local' if they wish.
  currentPositioningMode.value = 'external'; // Explicitly set default
  await fetchServerConfiguration(); // Load configuration from server when component mounts

  // If, for some reason, an app was previously in 'local' mode, this ensures it starts there.
  // However, standard flow is external first. This could be a setting itself.
  // For now, let's ensure that if a user *manually* sets it to local, it tries to load.
  // The handleModeChange logic will cover loading from localStorage when mode is set to local.
});

// Watchers to potentially help propagate changes if props aren't deep enough by default
// or if child components need explicit reload calls.

watch(() => currentConfiguration.value.beacons, (newBeacons) => {
    // This watcher helps if BeaconManagerTab needs to be explicitly told about external beacon changes
    // that didn't originate from itself.
    if (beaconManagerTabRef.value && beaconManagerTabRef.value.loadConfiguredBeacons) {
        // beaconManagerTabRef.value.loadConfiguredBeacons(newBeacons); // Already handled by initial-beacons prop?
    }
    // MapEditorTab receives beacons as a prop, so it should update.
}, { deep: true });


watch(() => currentConfiguration.value.settings, (newSettings) => {
    if (generalSettingsTabRef.value && generalSettingsTabRef.value.loadSettings) {
        // generalSettingsTabRef.value.loadSettings(newSettings); // Already handled by initial-settings prop?
    }
}, { deep: true });

// Watch for changes in currentConfiguration to save to localStorage when in local mode
watch(currentConfiguration, (newConfig) => {
  if (currentPositioningMode.value === 'local') {
    saveConfigToLocalStorage(newConfig);
    console.log("Auto-saved configuration to localStorage due to change in local mode.");
    // If local positioning is active, update its internal config too
    if (isLocalPositioningRunning.value) {
      localPositioningService.updateConfiguration(newConfig);
    }
  }
}, { deep: true });

// Unified function to apply a loaded configuration (from file import or server)
const applyFullConfiguration = (configData) => {
  if (configData && configData.map && Array.isArray(configData.beacons) && configData.settings) {
    currentConfiguration.value.map = JSON.parse(JSON.stringify(configData.map));
    currentConfiguration.value.beacons = JSON.parse(JSON.stringify(configData.beacons));
    currentConfiguration.value.settings = JSON.parse(JSON.stringify(configData.settings));
    
    selectedBeaconForPlacement.value = null;

    nextTick(() => {
      if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
      if (mapEditorTabRef.value?.loadConfiguration) {
        mapEditorTabRef.value.loadConfiguration(currentConfiguration.value); 
      }
      if (generalSettingsTabRef.value?.loadSettings) {
        generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
    });
    console.log("ConfigurationSuiteView: Full configuration applied.", currentConfiguration.value);
    return true;
  } else {
    console.error("ConfigurationSuiteView: Attempted to apply invalid full configuration structure.", configData);
    return false;
  }
};

// Renamed handleMapLoaded to reflect its primary use (processing config for application)
// This is called by file upload in MapEditorTab or by global file import, or by loading from server.
const processAndApplyFullConfig = (loadedConfig, sourceMessage = '配置已成功加载并应用。') => {
  if (applyFullConfiguration(loadedConfig)) {
    configStatusMessage.value = sourceMessage;
    // If in local mode, ensure this newly applied config is also saved to local storage
    if (currentPositioningMode.value === 'local') {
      saveConfigToLocalStorage(currentConfiguration.value);
      // Also update the local positioning service if it has been initialized for local mode
      localPositioningService.updateConfiguration(currentConfiguration.value);
    }
  } else {
    configStatusMessage.value = '错误：加载的配置数据格式无效。';
    // Optionally, reset to a known good state or initial state
    // currentConfiguration.value = initialConfiguration();
    // applyFullConfiguration(currentConfiguration.value); // to update children
  }
  // Clear message after a few seconds
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
};

</script>

<style scoped>
.page-container {
  padding: 1.5rem; /* Consistent padding with global .main-content-global if used */
  width: 100%;
  max-width: 1200px; /* Optional: constrain max width */
  margin: 0 auto; /* Center if max-width is used */
  box-sizing: border-box;
}

.page-title {
  font-size: 1.8rem; /* Larger page title */
  color: var(--primary-color-dark);
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
}

.info-banner {
  /* Uses global .status-display.info now */
  text-align: center;
}

.global-actions,
.tab-content,
.positioning-mode-switcher {
  /* Now uses global .card styling by having class="card" */
  /* Removed specific background, border, padding from here if handled by .card */
  margin-bottom: 1.5rem;
}

.card-content {
 padding: 1rem; /* Add padding inside cards if not directly on child elements */
}

.global-actions .card-content button {
  margin-right: 10px;
  margin-bottom: 5px; /* Spacing for buttons if they wrap */
  /* Button styling now comes from global button classes */
}

.tabs-navigation {
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.tabs-navigation button {
  padding: 0.6rem 1rem;
  margin-right: 0.5rem;
  border: 1px solid transparent; /* Cleaner look */
  border-bottom: none;
  background-color: transparent; /* Use theme colors */
  color: var(--primary-color);
  cursor: pointer;
  border-radius: var(--border-radius) var(--border-radius) 0 0; /* Rounded top corners */
  font-size: 1rem;
  font-weight: 500;
}

.tabs-navigation button.active {
  background-color: var(--primary-color);
  color: white;
  border-color: var(--primary-color-dark);
}
.tabs-navigation button:hover:not(.active) {
  background-color: #e7f3ff; /* Light hover for non-active tabs */
  color: var(--primary-color-dark);
}

/* Ensure .tab-content has some top margin if .tabs-navigation border is removed or styled differently */
/* .tab-content {
  margin-top: 0; 
}*/

.positioning-mode-switcher h2 { /* Handled by .card-header */
  margin-top: 0;
}

.mode-info {
  font-size: 0.9em;
  color: #333;
  margin-top: 0.5rem;
  margin-bottom: 1rem;
}

.local-positioning-controls button {
  margin-bottom: 0.5rem;
}

.local-position-display {
  margin-top: 0.5rem;
  font-size: 0.95em;
  padding: 0.5rem;
  background-color: #f0f2f5;
  border-radius: var(--border-radius);
}

.warning-text {
 /* Using global .status-display.warning */
}

select {
  /* Uses global select style from style.css */
  padding: 0.5rem;
  font-size: 0.95rem;
}

/* Override global button disabled style if needed for specific contexts, */
/* or rely on global button:disabled */
/* .global-actions button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
} */
</style> 
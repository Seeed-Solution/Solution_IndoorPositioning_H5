<template>
  <div class="tracker-mode-config-view page-content-wrapper">
    <h1 class="page-title">{{ $t('tracker.mapTracker') }}</h1>
    
    <!-- Tracker Statistics at Top -->
    <div v-if="wsStatus === 'connected'" class="tracker-stats-card card">
      <div class="card-header">
        <h2><i class="fas fa-chart-bar"></i> {{ $t('tracker.trackerStatistics') }}</h2>
      </div>
      <div class="card-content">
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-number">{{ trackerStats.total }}</div>
            <div class="stat-label">{{ $t('tracker.totalTrackers') }}</div>
          </div>
          <div class="stat-item success">
            <div class="stat-number">{{ trackerStats.online }}</div>
            <div class="stat-label">{{ $t('tracker.onlineTrackers') }}</div>
          </div>
          <div class="stat-item secondary">
            <div class="stat-number">{{ trackerStats.offline }}</div>
            <div class="stat-label">{{ $t('tracker.offlineTrackers') }}</div>
          </div>
          <div class="stat-item danger">
            <div class="stat-number">{{ trackerStats.sos }}</div>
            <div class="stat-label">{{ $t('tracker.sosAlerts') }}</div>
          </div>
        </div>
        <div v-if="Object.keys(trackerStats.byMap).length > 0" class="map-distribution">
          <h4>{{ $t('tracker.distributionByMap') }}:</h4>
          <div class="map-stats">
            <div v-for="(count, mapName) in trackerStats.byMap" :key="mapName" class="map-stat">
              <span class="map-name">{{ mapName }}</span>
              <span class="map-count">{{ count }} {{ count === 1 ? 'tracker' : 'trackers' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Map Viewer Section -->
    <div class="map-viewer-section card">
      <div class="card-header">
        <h2><i class="fas fa-map-marked-alt"></i> {{ $t('tracker.mapViewer') }}</h2>
        <div class="map-selector-wrapper">
          <div class="map-selector-dropdown">
            <button 
              @click="toggleMapDropdown" 
              class="map-dropdown-button"
              :disabled="availableMaps.length === 0"
            >
              <span v-if="selectedMapConfig">
                {{ selectedMapConfig.map.name || $t('tracker.unnamedMap') }}
                <small class="map-info">({{ getMapInfoText(selectedMapConfig) }})</small>
              </span>
              <span v-else>{{ $t('tracker.selectMapPlaceholder') }}</span>
              <i class="fas fa-chevron-down dropdown-icon" :class="{ 'rotated': showMapDropdown }"></i>
            </button>
            
            <div v-if="showMapDropdown" class="map-dropdown-menu">
              <div 
                v-for="mapConfig in availableMaps" 
                :key="mapConfig.map.name"
                @click="selectMap(mapConfig)"
                class="map-dropdown-item"
                :class="{ 'selected': selectedMapConfig && selectedMapConfig.map.name === mapConfig.map.name }"
              >
                <div class="map-item-info">
                  <strong>{{ mapConfig.map.name || $t('tracker.unnamedMap') }}</strong>
                  <small>{{ getMapInfoText(mapConfig) }}</small>
                </div>
              </div>
              <div v-if="availableMaps.length === 0" class="map-dropdown-item disabled">
                {{ $t('tracker.noMapsAvailable') }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="card-content map-content">
        <div v-if="selectedMapConfig">
          <div class="map-header">
            <h3>
              {{ selectedMapConfig.map.name || $t('tracker.unnamedMap') }}
              <span class="tracker-count">({{ filteredTrackerList.length }} {{ $t('tracker.activeTrackers') }})</span>
            </h3>
          </div>
          <MapPreview 
            :config="selectedMapConfig"
            :trackers="trackers"
            :initialShowTrails="showTrails"
            @trails-toggled="onTrailsToggled"
          />
        </div>
        <div v-else class="no-map-selected">
          <div class="empty-state">
            <i class="fas fa-map-marked-alt empty-state-icon"></i>
            <h3>{{ $t('tracker.noMapSelected') }}</h3>
            <p>{{ $t('tracker.selectMapToView') }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Status Messages -->
    <p v-if="statusMessage" class="status-message" :class="statusMessageType">{{ statusMessage }}</p>
    
    <!-- No Map Selected State -->
    <div v-if="!selectedMapConfig && wsStatus === 'connected'" class="empty-state-card">
      <div class="empty-state">
        <i class="fas fa-map-marked-alt empty-state-icon"></i>
        <h3>{{ $t('tracker.noMapSelected') }}</h3>
        <p>{{ $t('tracker.selectMapToView') }}</p>
      </div>
    </div>
    
    <!-- Disconnected State -->
    <div v-if="wsStatus === 'disconnected'" class="empty-state-card">
      <div class="empty-state">
        <i class="fas fa-wifi-slash empty-state-icon error"></i>
        <h3>{{ $t('tracker.connectionLost') }}</h3>
        <p>{{ $t('tracker.reconnecting') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import MapPreview from '@/components/MapPreview.vue';
import { loadConfigFromLocalStorage } from '@/services/localStorageService.js';
import { loadWebConfiguration, loadDashboardConfiguration, loadServerConfiguration, loadTrackers } from '@/services/configApiService.js';

const statusMessage = ref('');
const statusMessageType = ref('info');

// Available maps and selection
const availableMaps = ref([]);
const selectedMapConfig = ref(null);
const showMapDropdown = ref(false);
const showTrails = ref(false);

// WebSocket and tracker data
const trackers = ref({}); 
const allTrackers = ref([]); // All trackers from /api/trackers
const ws = ref(null);
const wsStatus = ref('disconnected');
const liveMqttStatusForServerSettings = ref('unknown');
const currentServerConfig = ref(null);

// Computed properties
const filteredTrackerList = computed(() => {
    const allTrackers = Object.values(trackers.value);
    if (!selectedMapConfig.value || !selectedMapConfig.value.map) {
        return [];
    }
    
    return allTrackers
        .filter(tracker => tracker.map === selectedMapConfig.value.map.name)
        .sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

// Tracker statistics
const trackerStats = computed(() => {
    const totalTrackers = allTrackers.value.length;
    const now = Date.now();
    const fifteenMinutesMs = 15 * 60 * 1000; // 15 minutes in milliseconds
    
    // Calculate online/offline based on last_update_time from /api/trackers
    const onlineTrackers = allTrackers.value.filter(tracker => {
        if (!tracker.last_update_time) return false;
        const lastUpdateTime = new Date(tracker.last_update_time).getTime();
        return (now - lastUpdateTime) <= fifteenMinutesMs;
    }).length;
    
    const offlineTrackers = totalTrackers - onlineTrackers;
    
    // Count trackers by map using live tracker data
    const liveTrackers = Object.values(trackers.value);
    const trackersByMap = {};
    liveTrackers.forEach(tracker => {
        if (tracker.map) {
            trackersByMap[tracker.map] = (trackersByMap[tracker.map] || 0) + 1;
        }
    });
    
    // Count SOS trackers from live data
    const sosTrackers = liveTrackers.filter(tracker => tracker.sos === 1).length;
    
    return {
        total: totalTrackers,
        online: onlineTrackers,
        offline: offlineTrackers,
        sos: sosTrackers,
        byMap: trackersByMap
    };
});

// Map selection methods
const toggleMapDropdown = () => {
    showMapDropdown.value = !showMapDropdown.value;
};

const selectMap = (mapConfig) => {
    selectedMapConfig.value = mapConfig;
    showMapDropdown.value = false;
    showStatus(`Selected map: ${mapConfig.map.name || 'Unnamed Map'}`, 'success');
};

const onTrailsToggled = (showTrailsValue) => {
    showTrails.value = showTrailsValue;
};

// Get formatted map info text
const getMapInfoText = (mapConfig) => {
    if (!mapConfig) return '';
    
    const beaconsCount = Array.isArray(mapConfig.beacons) ? mapConfig.beacons.length : 0;
    const entitiesCount = mapConfig.map?.entities?.length || 0;
    
    const parts = [];
    if (beaconsCount > 0) {
        parts.push(`${beaconsCount} ${beaconsCount === 1 ? 'beacon' : 'beacons'}`);
    }
    if (entitiesCount > 0) {
        parts.push(`${entitiesCount} ${entitiesCount === 1 ? 'entity' : 'entities'}`);
    }
    
    return parts.length > 0 ? parts.join(', ') : 'No data';
};

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
    if (!event.target.closest('.map-selector-dropdown')) {
        showMapDropdown.value = false;
    }
};

const connectWebSocket = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    ws.value = new WebSocket(wsUrl);
    wsStatus.value = 'connecting';
    showStatus('Connecting to server...', 'info');

    ws.value.onopen = () => { 
        wsStatus.value = 'connected'; 
        showStatus('Connected to server', 'success');
        loadAvailableMaps();
        loadAllTrackers();
        fetchFullServerConfig();    
    };
    
    ws.value.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);

            if (message.type === 'initial_state') {
                if (isMqttEffectivelyEnabled.value) {
                    trackers.value = message.data || {};
                } else {
                    trackers.value = {};
                }
            } else if (message.type === 'tracker_update') {
                if (isMqttEffectivelyEnabled.value) {
                    const updatedTrackerId = Object.keys(message.data)[0];
                    if (updatedTrackerId && message.data[updatedTrackerId]) {
                        const newTrackerData = message.data[updatedTrackerId];
                        
                        const trackerInstanceData = {
                            trackerId: newTrackerData.trackerId,
                            map: newTrackerData.map,
                            position: newTrackerData.position ? { 
                                x: newTrackerData.position.x, 
                                y: newTrackerData.position.y, 
                                accuracy: newTrackerData.position.accuracy
                            } : null,
                            timestamp: newTrackerData.timestamp,
                            sos: newTrackerData.sos || false,
                            sos_happen: newTrackerData.sos_happen,
                            last_detected_beacons: newTrackerData.last_detected_beacons 
                                ? newTrackerData.last_detected_beacons.map(b => ({ ...b })) 
                                : [],
                            position_history: newTrackerData.position_history 
                                ? newTrackerData.position_history.map(hEntry => Array.isArray(hEntry) ? [...hEntry] : hEntry) 
                                : []
                        };

                        trackers.value[updatedTrackerId] = trackerInstanceData;
                    }
                }
            } else if (message.type === 'mqtt_status_update') { 
                if (message.data && typeof message.data.status === 'string') {
                    liveMqttStatusForServerSettings.value = message.data.status;
                    if (message.data.status === 'disabled' && currentServerConfig.value?.mqtt?.enabled) {
                         currentServerConfig.value.mqtt.enabled = false;
                    }
                }
            }
        } catch (error) {
            console.error('[WebSocket] Error parsing message:', error);
        }
    };
    
    ws.value.onerror = (error) => { 
        wsStatus.value = 'error'; 
        showStatus('WebSocket connection error', 'error');
    };
    
    ws.value.onclose = () => { 
        wsStatus.value = 'disconnected'; 
        showStatus('Disconnected from server. Reconnecting...', 'error');
        setTimeout(connectWebSocket, 3000);
    };
};

const showStatus = (msg, type = 'info') => {
    statusMessage.value = msg;
    statusMessageType.value = type; 
    setTimeout(() => { statusMessage.value = ''; statusMessageType.value = 'info'; }, 5000); 
};

const loadAllTrackers = async () => {
  try {
    const trackersData = await loadTrackers();
    allTrackers.value = Array.isArray(trackersData) ? trackersData : [];
    console.log(`Loaded ${allTrackers.value.length} total trackers from server`);
  } catch (error) {
    console.error('Error loading all trackers:', error);
    allTrackers.value = [];
  }
};

const loadAvailableMaps = async () => {
  showStatus('Loading available maps...', 'info');
  try {
    // Load dashboard configuration which contains the maps array
    const dashboardConfig = await loadDashboardConfiguration();
    
    if (dashboardConfig && Array.isArray(dashboardConfig.maps)) {
      // Dashboard config contains a maps array
      availableMaps.value = dashboardConfig.maps;
      
      if (dashboardConfig.maps.length > 0) {
        showStatus(`Found ${dashboardConfig.maps.length} available map(s)`, 'success');
        // Auto-select the first map if none selected
        if (!selectedMapConfig.value) {
          selectedMapConfig.value = dashboardConfig.maps[0];
        }
      } else {
        showStatus('No maps found in dashboard configuration.', 'warning');
      }
    } else if (dashboardConfig && dashboardConfig.map) {
      // Fallback: single map in dashboard config
      availableMaps.value = [dashboardConfig];
      selectedMapConfig.value = dashboardConfig;
      showStatus('Found 1 available map', 'success');
    } else {
      // No maps found, try fallback sources
      showStatus('No maps found in dashboard. Checking fallback sources...', 'warning');
      
      const fallbackMaps = [];
      
      // Try web configuration as fallback
      try {
        const webConfig = await loadWebConfiguration();
        if (webConfig && webConfig.map) {
          fallbackMaps.push(webConfig);
        }
      } catch (error) {
        console.warn('Could not load web configuration:', error);
      }
      
      // Try local storage as fallback
      try {
        const localConfig = loadConfigFromLocalStorage('trackerModeConfig');
        if (localConfig && localConfig.map) {
          fallbackMaps.push(localConfig);
        }
      } catch (error) {
        console.warn('Could not load from local storage:', error);
      }
      
      availableMaps.value = fallbackMaps;
      
      if (fallbackMaps.length > 0) {
        showStatus(`Found ${fallbackMaps.length} fallback map(s)`, 'success');
        if (!selectedMapConfig.value) {
          selectedMapConfig.value = fallbackMaps[0];
        }
      } else {
        showStatus('No maps found. Please configure maps in the dashboard first.', 'warning');
      }
    }
  } catch (error) {
    console.error('Error loading available maps:', error);
    showStatus(`Failed to load maps: ${error.message}`, 'error');
    availableMaps.value = [];
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
    }
  } catch (error) {
    console.error('Error fetching server configuration:', error);
  }
};

const isMqttEffectivelyEnabled = computed(() => {
  return currentServerConfig.value?.mqtt?.enabled && liveMqttStatusForServerSettings.value !== 'disabled';
});

onMounted(() => {
    connectWebSocket();
    document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => { 
    if (ws.value) { 
        ws.value.onclose = null; 
        ws.value.close(); 
    }
    document.removeEventListener('click', handleClickOutside);
});

</script>

<style scoped>
/* Page Title */
.page-title {
  text-align: center;
  margin: 0 0 0.5rem 0;
  color: var(--text-color);
  font-size: 1.3rem;
  font-weight: 600;
}

/* Map Viewer Section */
.map-viewer-section {
  margin-bottom: 0.5rem;
}

.map-viewer-section .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 1rem;
}

.map-viewer-section .card-header h2 {
  margin: 0;
  flex: 1;
  font-size: 1rem;
}

/* Map Selector */
.map-selector-wrapper {
  min-width: 300px;
  flex-shrink: 0;
}

.map-selector-dropdown {
  position: relative;
  width: 100%;
}

.map-dropdown-button {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background-color: var(--card-background);
  color: var(--text-color);
  font-size: 0.95rem;
  text-align: left;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
  min-height: 48px;
}

.map-dropdown-button:hover:not(:disabled) {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(115, 199, 77, 0.1);
}

.map-dropdown-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.map-info {
  color: var(--secondary-color);
  margin-left: 0.5rem;
}

.dropdown-icon {
  transition: transform 0.2s ease;
  color: var(--secondary-color);
}

.dropdown-icon.rotated {
  transform: rotate(180deg);
}

.map-dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: var(--card-background);
  border: 2px solid var(--border-color);
  border-top: none;
  border-radius: 0 0 var(--border-radius) var(--border-radius);
  box-shadow: var(--box-shadow);
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
}

.map-dropdown-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid var(--border-color);
}

.map-dropdown-item:last-child {
  border-bottom: none;
}

.map-dropdown-item:hover:not(.disabled) {
  background-color: rgba(115, 199, 77, 0.05);
}

.map-dropdown-item.selected {
  background-color: rgba(115, 199, 77, 0.1);
  color: var(--primary-color);
  font-weight: 600;
}

.map-dropdown-item.disabled {
  color: var(--secondary-color);
  cursor: not-allowed;
  font-style: italic;
}

.map-item-info strong {
  display: block;
  margin-bottom: 0.25rem;
}

.map-item-info small {
  color: var(--secondary-color);
  font-size: 0.8rem;
}

/* Status Message */
.status-message {
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius);
  border-left: 4px solid;
  font-size: 0.9rem;
  margin: 0;
}

.status-message.info {
  background-color: var(--info-bg-color);
  border-left-color: var(--info-color);
  color: var(--info-color);
}

.status-message.success {
  background-color: rgba(115, 199, 77, 0.1);
  border-left-color: var(--success-color);
  color: var(--success-color);
}

.status-message.warning {
  background-color: rgba(230, 162, 60, 0.1);
  border-left-color: var(--warning-color);
  color: var(--warning-color);
}

.status-message.error {
  background-color: rgba(245, 108, 108, 0.1);
  border-left-color: var(--danger-color);
  color: var(--danger-color);
}

/* Tracker Statistics Card */
.tracker-stats-card {
  margin-bottom: 0.5rem;
}

.tracker-stats-card .card-header {
  padding: 0.5rem 1rem;
}

.tracker-stats-card .card-content {
  padding: 0.75rem 1rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.stat-item {
  text-align: center;
  padding: 0.5rem;
  background-color: rgba(95, 99, 104, 0.1);
  border-radius: var(--border-radius);
  border-left: 4px solid var(--secondary-color);
  transition: transform 0.2s ease;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 60px;
}

.stat-item:hover {
  transform: translateY(-1px);
}

.stat-item.success {
  background-color: rgba(115, 199, 77, 0.1);
  border-left-color: var(--success-color);
}

.stat-item.secondary {
  background-color: rgba(95, 99, 104, 0.1);
  border-left-color: var(--secondary-color);
}

.stat-item.danger {
  background-color: rgba(245, 108, 108, 0.1);
  border-left-color: var(--danger-color);
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-color);
  margin-bottom: 0.125rem;
  display: block;
  line-height: 1;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--secondary-color);
  font-weight: 500;
  line-height: 1;
}

.map-distribution {
  border-top: 1px solid var(--border-color);
  padding-top: 0.5rem;
}

.map-distribution h4 {
  margin: 0 0 0.25rem 0;
  color: var(--text-color);
  font-size: 0.75rem;
  font-weight: 600;
}

.map-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.map-stat {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.375rem;
  background-color: rgba(115, 199, 77, 0.05);
  border-radius: var(--border-radius);
  border: 1px solid rgba(115, 199, 77, 0.2);
  font-size: 0.65rem;
}

.map-name {
  font-weight: 600;
  color: var(--text-color);
  font-size: 0.65rem;
}

.map-count {
  font-size: 0.6rem;
  color: var(--secondary-color);
}

/* Map Content */
.map-header {
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-color);
}

.map-header h3 {
  margin: 0;
  color: var(--text-color);
  font-size: 0.9rem;
  font-weight: 600;
}

.tracker-count {
  color: var(--secondary-color);
  font-weight: normal;
  font-size: 0.75rem;
}

.map-content {
  padding: 0.5rem;
}

.no-map-selected {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Empty States */
.empty-state-card {
  margin-bottom: 1.5rem;
  padding: 3rem 2rem;
  text-align: center;
  background-color: var(--card-background);
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
}

.empty-state {
  color: var(--secondary-color);
}

.empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.6;
}

.empty-state-icon.error {
  color: var(--danger-color);
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  color: var(--text-color);
  font-size: 1.2rem;
}

.empty-state p {
  margin: 0;
  font-size: 0.95rem;
}

/* Responsive */
@media (max-width: 1024px) {
  .map-viewer-section .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .map-selector-wrapper {
    width: 100%;
    min-width: auto;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }
}

@media (max-width: 768px) {
  .page-title {
    font-size: 1.5rem;
  }
  
  .map-dropdown-button {
    font-size: 0.9rem;
    padding: 0.5rem 0.75rem;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }
  
  .stat-item {
    padding: 0.75rem;
    min-height: 70px;
  }
  
  .stat-number {
    font-size: 1.6rem;
  }
  
  .empty-state-card,
  .no-map-selected {
    padding: 2rem 1rem;
  }
  
  .empty-state-icon {
    font-size: 2rem;
  }
}
</style>
<template>
  <div class="map-dashboard-view page-content-wrapper">
    <h1 class="page-title">Map Dashboard</h1>
    <p class="info-banner status-display info" v-if="statusMessage">{{ statusMessage }}</p>

    <!-- 连接状态与统计信息 -->
    <div class="dashboard-overview card">
      <div class="card-content">
        <div class="overview-content">
          <!-- WebSocket Connection Status -->
          <div class="connection-status">
            <i :class="wsStatusIcon" class="connection-icon"></i>
            <div class="connection-info">
              <span class="connection-label">WebSocket:</span>
              <span :class="['connection-value', wsStatus === 'connected' ? 'status-connected' : 'status-disconnected']">
                {{ wsStatusText }}
              </span>
            </div>
          </div>

          <!-- Statistics -->
          <div class="stats-compact">
            <div class="stat-item-compact">
              <i class="fas fa-map stat-icon-compact"></i>
              <span class="stat-number-compact">{{ totalMaps }}</span>
              <span class="stat-label-compact">Maps</span>
            </div>
            <div class="stat-item-compact">
              <i class="fas fa-broadcast-tower stat-icon-compact"></i>
              <span class="stat-number-compact">{{ totalBeacons }}</span>
              <span class="stat-label-compact">Beacons</span>
            </div>
            <div class="stat-item-compact">
              <i class="fas fa-map-marker-alt stat-icon-compact"></i>
              <span class="stat-number-compact">{{ totalTrackers }}</span>
              <span class="stat-label-compact">Trackers</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 地图部分 -->
    <div class="maps-container" v-if="availableMaps.length > 0">
      <!-- 全屏按钮 -->
      <div class="maps-header">
        <h2>地图总览</h2>
        <button @click="enterFullscreen" class="btn-fullscreen">
          <i class="fas fa-expand"></i> 全屏显示
        </button>
      </div>
      <div class="maps-grid">
        <div v-for="(mapConfig, index) in availableMaps" :key="index" class="map-grid-item">
          <div class="map-dashboard-card">
            <!-- Map Header -->
            <div class="map-header">
              <h3 class="map-title">{{ mapConfig.map?.name || `Map ${index + 1}` }}</h3>
              <div class="map-stats">
                <span class="map-stat">
                  <i class="fas fa-broadcast-tower"></i>
                  {{ mapConfig.beacons?.length || 0 }}
                </span>
                <span class="map-stat">
                  <i class="fas fa-map-marker-alt"></i>
                  {{ Object.keys(getTrackersForMap(mapConfig)).length }}
                </span>
              </div>
            </div>
            
            <!-- Map Display -->
            <div class="map-display-area">
              <MapView 
                :config="mapConfig"
                :trackers="Object.values(getTrackersForMap(mapConfig))"
              />
            </div>
            
            <!-- Map Actions Footer -->
            <div class="map-actions-footer">
              <div class="map-info-summary">
                <span class="info-item">
                  <i class="fas fa-broadcast-tower"></i>
                  {{ mapConfig.beacons?.length || 0 }} Beacons
                </span>
                <span class="info-item">
                  <i class="fas fa-cube"></i>
                  {{ mapConfig.map?.entities?.length || 0 }} Entities
                </span>
                <span class="info-item" v-if="mapConfig.map?.dimensions">
                  <i class="fas fa-ruler-combined"></i>
                  {{ mapConfig.map.dimensions.width }}×{{ mapConfig.map.dimensions.height }}m
                </span>
              </div>
              <div class="map-actions">
                <button @click="viewMapDetails(mapConfig, index)" class="btn-sm btn-primary">Details</button>
                <button @click="configureMap(mapConfig, index)" class="btn-sm btn-secondary">Config</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Placeholder when no maps -->
    <div v-if="availableMaps.length === 0 && !statusMessage.includes('Loading')" class="no-maps-placeholder card">
      <div class="card-content">
        <div class="placeholder-content">
          <i class="fas fa-map fa-3x"></i>
          <h3>No Maps Available</h3>
          <p>Create your first map in the "Map & Beacon Configuration" section.</p>
          <button @click="goToConfiguration" class="btn-primary">Go to Configuration</button>
        </div>
      </div>
    </div>

    <!-- 全屏模式 -->
    <div v-if="isFullscreen" class="fullscreen-overlay">
      <div class="fullscreen-container">
        <!-- 右上角退出按钮 -->
        <button @click="exitFullscreen" class="btn-close-floating">
          <i class="fas fa-times"></i>
        </button>

        <!-- 全屏地图网格 -->
        <div class="fullscreen-maps-grid">
          <div v-for="(mapConfig, index) in availableMaps.slice(0, 4)" :key="index" class="fullscreen-map-item">
            <div class="fullscreen-map-card">
              <!-- Map Header -->
              <div class="fullscreen-map-header">
                <h4>{{ mapConfig.map?.name || `Map ${index + 1}` }}</h4>
                <div class="fullscreen-map-stats">
                  <span><i class="fas fa-broadcast-tower"></i> {{ mapConfig.beacons?.length || 0 }}</span>
                  <span><i class="fas fa-map-marker-alt"></i> {{ Object.keys(getTrackersForMap(mapConfig)).length }}</span>
                </div>
              </div>
              
              <!-- Map Display -->
              <div class="fullscreen-map-display">
                <MapView 
                  :config="mapConfig"
                  :trackers="Object.values(getTrackersForMap(mapConfig))"
                />
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
// import MapView from '@/components/MapView.vue';
import MapView from '@/components/MapPreview.vue'
import {
  loadDashboardConfiguration,
  loadServerConfiguration,
  loadWebConfiguration
} from '@/services/configApiService.js';
import { loadConfigFromLocalStorage } from '@/services/localStorageService.js';

const router = useRouter();

// Config storage key
const CONFIG_STORAGE_KEY = 'mapDashboardConfig';

// Reactive data
const statusMessage = ref('Loading dashboard...');
const availableMaps = ref([]);
const trackers = ref({});
const ws = ref(null);
const wsStatus = ref('disconnected');
const liveMqttStatus = ref('unknown');
const serverConfig = ref(null);

// Master configuration state (similar to TrackerMode)
const initialMasterConfig = () => ({
  maps: []
});
const currentFullConfig = ref(initialMasterConfig());

// 全屏模式状态
const isFullscreen = ref(false);
const currentPage = ref(0);
const mapsPerPage = 4;

// Computed properties
const totalMaps = computed(() => availableMaps.value.length);
const totalBeacons = computed(() => 
  availableMaps.value.reduce((total, mapConfig) => total + (mapConfig.beacons?.length || 0), 0)
);
const totalTrackers = computed(() => Object.keys(trackers.value).length);

// 分页计算
const totalPages = computed(() => Math.ceil(availableMaps.value.length / mapsPerPage));
const paginatedMaps = computed(() => {
  const start = currentPage.value * mapsPerPage;
  return availableMaps.value.slice(start, start + mapsPerPage);
});

const wsStatusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'Connected';
    case 'connecting': return 'Connecting...';
    case 'disconnected': return 'Disconnected';
    case 'error': return 'Connection Error';
    default: return 'Unknown';
  }
});

const wsStatusIcon = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'fas fa-wifi connection-icon-success';
    case 'connecting': return 'fas fa-spinner fa-spin connection-icon-info';
    case 'disconnected': return 'fas fa-wifi-slash connection-icon-error';
    case 'error': return 'fas fa-exclamation-triangle connection-icon-error';
    default: return 'fas fa-question-circle connection-icon-info';
  }
});

const isMqttEffectivelyEnabled = computed(() => {
  return serverConfig.value?.mqtt?.enabled && liveMqttStatus.value !== 'disabled';
});

const mqttStatusDisplay = computed(() => {
  let statusText = 'Unknown';
  let statusClass = 'info';
  let iconClass = 'fas fa-question-circle';

  const mqttConfig = serverConfig.value?.mqtt;
  const mqttEnabledInConfig = mqttConfig?.enabled;

  if (wsStatus.value !== 'connected') {
    statusText = 'Unavailable';
    statusClass = 'error';
    iconClass = 'fas fa-wifi-slash';
  } else if (!mqttConfig) {
    statusText = 'Loading...';
    statusClass = 'info';
    iconClass = 'fas fa-hourglass-start';
  } else if (mqttEnabledInConfig === false) {
    statusText = 'Disabled';
    statusClass = 'info';
    iconClass = 'fas fa-toggle-off';
  } else {
    switch (liveMqttStatus.value) {
      case 'connected': statusText = 'Connected'; statusClass = 'success'; iconClass = 'fas fa-check-circle'; break;
      case 'connecting': statusText = 'Connecting...'; statusClass = 'info'; iconClass = 'fas fa-spinner fa-spin'; break;
      case 'disconnected': statusText = 'Disconnected'; statusClass = 'warn'; iconClass = 'fas fa-plug'; break;
      case 'error': statusText = 'Error'; statusClass = 'error'; iconClass = 'fas fa-times-circle'; break;
      default: statusText = 'Unknown'; statusClass = 'info'; iconClass = 'fas fa-question-circle'; break;
    }
  }
  return { text: statusText, class: statusClass, icon: iconClass };
});

// Methods
const showStatus = (msg, type = 'info') => {
  statusMessage.value = `${type.toUpperCase()}: ${msg}`;
  setTimeout(() => { statusMessage.value = '' }, 7000);
};

const initializeMasterConfig = async () => {
  showStatus('Loading master configuration...', 'info');
  try {
    const config = await loadDashboardConfiguration();
    if (config && config.maps) {
      currentFullConfig.value = config.maps;
      availableMaps.value = config.maps;
      showStatus('Master configuration loaded from server.', 'success');
      return;
    } else {
      showStatus('No master configuration found on server. Checking local storage...', 'info');
      loadMasterConfigFromStorage();
    }
  } catch (error) {
    console.error('[MapDashboard] Error loading master configuration from server:', error);
    showStatus(`Failed to load master config from server: ${error.message || 'Unknown error'}. Trying local storage.`, 'error');
    loadMasterConfigFromStorage();
  }
};

const loadMasterConfigFromStorage = () => {
  const loaded = loadConfigFromLocalStorage(CONFIG_STORAGE_KEY);
  if (loaded && loaded.maps) {
    currentFullConfig.value = loaded.maps;
    availableMaps.value = loaded.maps;
    showStatus('Master configuration loaded from local storage.');
  } else {
    currentFullConfig.value = initialMasterConfig();
  }
};

const connectWebSocket = () => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) return;
  
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
  ws.value = new WebSocket(wsUrl);
  // ws.value = new WebSocket('ws://indoorpositioning-demo.seeed.cc:8022');
  wsStatus.value = 'connecting';

  ws.value.onopen = () => {
    wsStatus.value = 'connected';
    initializeMasterConfig();
    fetchFullServerConfig();
  };

  ws.value.onmessage = (event) => {
    console.log('[MapDashboard] RAW onmessage event received. Data:', event.data);
    try {
      const message = JSON.parse(event.data);
      console.log('[MapDashboard] PARSED message object:', message);
      
      if (message.type === 'initial_state') {
        console.log('[MapDashboard] Processing initial_state. Current isMqttEffectivelyEnabled:', isMqttEffectivelyEnabled.value, 'Data:', message.data);
        // Only update trackers if MQTT is effectively enabled
        if (isMqttEffectivelyEnabled.value) {
          trackers.value = message.data || {};
        } else {
          trackers.value = {};
        }
      } else if (message.type === 'tracker_update') {
        console.log('[MapDashboard] Processing tracker_update. Data:', message.data);
        if (isMqttEffectivelyEnabled.value) {
          const updatedTrackerId = Object.keys(message.data)[0];
          if (updatedTrackerId && message.data[updatedTrackerId]) {
            const newTrackerData = message.data[updatedTrackerId];
            console.log(`[MapDashboard] Updating tracker ${updatedTrackerId} with (raw incoming):`, newTrackerData);
            
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
                : [],
              map: newTrackerData.map
            };

            if (!trackers.value[updatedTrackerId]) {
              trackers.value = { ...trackers.value, [updatedTrackerId]: trackerInstanceData };
            } else {
              trackers.value[updatedTrackerId] = trackerInstanceData;
            }
          }
        }
      } else if (message.type === 'mqtt_status_update') {
        console.log('[MapDashboard] Processing mqtt_status_update. Data:', message.data);
        if (message.data && typeof message.data.status === 'string') {
          liveMqttStatus.value = message.data.status;
          if (message.data.status === 'disabled' && serverConfig.value && serverConfig.value.mqtt.enabled) {
            if (serverConfig.value) serverConfig.value.mqtt.enabled = false;
          }
        }
      } else {
        console.log('[MapDashboard] Received unhandled message type:', message.type, 'Data:', message.data);
      }
    } catch (error) {
      console.error('[MapDashboard] FATAL: Error parsing WebSocket message or in handler. Raw data:', event.data, 'Error:', error);
    }
  };

  ws.value.onerror = (error) => {
    wsStatus.value = 'error';
    console.error('[MapDashboard] WebSocket error:', error);
  };

  ws.value.onclose = () => {
    wsStatus.value = 'disconnected';
    console.log('[MapDashboard] WebSocket disconnected');
  };
};

const loadDashboardData = async () => {
  try {
    statusMessage.value = 'Loading maps and configurations...';
    
    // TODO: 这里需要实现加载所有可用地图的逻辑
    // 暂时使用示例数据，后续需要从服务器或存储中加载
    // fetchServerConfig is called separately in connectWebSocket onopen
    
    statusMessage.value = '';
  } catch (error) {
    console.error('[MapDashboard] Error loading dashboard data:', error);
    statusMessage.value = `Error loading dashboard: ${error.message}`;
  }
};

const fetchFullServerConfig = async () => {
  if (wsStatus.value !== 'connected') {
    return;
  }
  try {
    console.log('[MapDashboard] Fetching server configuration...');
    const config = await loadServerConfiguration();
    if (config) {
      serverConfig.value = config;
      console.log('[MapDashboard] Server configuration loaded:', config);
      if (config.mqtt && typeof config.mqtt.live_mqtt_status !== 'undefined') {
        liveMqttStatus.value = config.mqtt.live_mqtt_status;
      } else if (config.mqtt && config.mqtt.enabled) {
        liveMqttStatus.value = 'unknown';
      }
    } else {
      console.warn('[MapDashboard] Failed to load server configuration or server returned empty.');
      serverConfig.value = null;
      liveMqttStatus.value = 'unknown';
    }
  } catch (error) {
    console.error('[MapDashboard] Error fetching server configuration:', error);
    serverConfig.value = null;
    liveMqttStatus.value = 'unknown';
  }
};

const loadAvailableMaps = async () => {
  // TODO: 实现实际的地图加载逻辑
};

const getTrackersForMap = (mapConfig) => {
  // 根据地图名称筛选相关的tracker
  const mapName = mapConfig.map?.name;
  if (!mapName) {
    return {};
  }
  
  const filteredTrackers = {};
  Object.entries(trackers.value).forEach(([trackerId, tracker]) => {
    if (tracker.map === mapName) {
      filteredTrackers[trackerId] = tracker;
    }
  });
  
  return filteredTrackers;
};


const viewMapDetails = (mapConfig, index) => {
  // TODO: 实现查看地图详情的逻辑
  console.log('View map details:', mapConfig, index);
};

const configureMap = (mapConfig, index) => {
  // 跳转到配置页面
  router.push('/config-master');
};

const goToConfiguration = () => {
  router.push('/config-master');
};

// 全屏功能
const enterFullscreen = () => {
  isFullscreen.value = true;
  // 阻止body滚动
  document.body.style.overflow = 'hidden';
};

const exitFullscreen = () => {
  isFullscreen.value = false;
  // 恢复body滚动
  document.body.style.overflow = '';
};

// 分页控制
const goToPreviousPage = () => {
  if (currentPage.value > 0) {
    currentPage.value--;
  }
};

const goToNextPage = () => {
  if (currentPage.value < totalPages.value - 1) {
    currentPage.value++;
  }
};

// 键盘事件处理
const handleKeydown = (event) => {
  if (event.key === 'Escape' && isFullscreen.value) {
    exitFullscreen();
  }
};

// Lifecycle
onMounted(() => {
  console.log('[MapDashboard] Component mounted, connecting WebSocket...');
  connectWebSocket();
  
  // 添加键盘事件监听
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  console.log('[MapDashboard] Component unmounting, closing WebSocket...');
  if (ws.value) {
    ws.value.onclose = null;
    ws.value.close();
  }
  
  // 移除键盘事件监听
  window.removeEventListener('keydown', handleKeydown);
  
  // 确保恢复body滚动
  document.body.style.overflow = '';
});
</script>

<style scoped>
.map-dashboard-view {
  padding: 1rem;
}

.page-title {
  text-align: center;
  margin-bottom: 2rem;
}

.dashboard-overview {
  margin-bottom: 1.5rem;
}

.overview-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0;
  gap: 2rem;
  flex-wrap: wrap;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.connection-icon {
  font-size: 1.2rem;
}

.connection-icon-success {
  color: #28a745;
}

.connection-icon-info {
  color: #17a2b8;
}

.connection-icon-error {
  color: #dc3545;
}

.connection-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.connection-label {
  font-size: 0.9rem;
  color: #6c757d;
  font-weight: 500;
}

.connection-value {
  font-size: 0.95rem;
  font-weight: 600;
}

.stats-compact {
  display: flex;
  gap: 2rem;
  align-items: center;
}

.stat-item-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background-color: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  min-width: 80px;
}

.stat-icon-compact {
  color: #0056b3;
  font-size: 1rem;
  width: 16px;
  text-align: center;
}

.stat-number-compact {
  font-size: 1.2rem;
  font-weight: bold;
  color: #0056b3;
  min-width: 20px;
}

.stat-label-compact {
  font-size: 0.8rem;
  color: #6c757d;
  font-weight: 500;
}

/* Responsive layout for smaller screens */
@media (max-width: 768px) {
  .overview-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .stats-compact {
    gap: 1rem;
    flex-wrap: wrap;
  }
}

.status-connected {
  color: #28a745;
  font-weight: bold;
}

.status-disconnected {
  color: #dc3545;
  font-weight: bold;
}

.mqtt-status-indicator {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 500;
}

.mqtt-status-indicator.success {
  background-color: #28a745;
  color: white;
}

.mqtt-status-indicator.warn {
  background-color: #ffc107;
  color: #333;
}

.mqtt-status-indicator.error {
  background-color: #dc3545;
  color: white;
}

.mqtt-status-indicator.info {
  background-color: #17a2b8;
  color: white;
}

.maps-container {
  margin-bottom: 2rem;
}

.maps-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 0 1rem;
}

.maps-header h2 {
  margin: 0;
  color: #333;
}

.btn-fullscreen {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background-color: #0056b3;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-fullscreen:hover {
  background-color: #004494;
}

.maps-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.map-grid-item {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 500px; /* Taller height for full-width display */
}

.map-dashboard-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.map-dashboard-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.map-actions-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: #f8f9fa;
  border-top: 1px solid #dee2e6;
  margin-top: auto;
}

.map-info-summary {
  display: flex;
  gap: 1rem;
  flex: 1;
  align-items: center;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: #6c757d;
  white-space: nowrap;
}

.info-item i {
  font-size: 0.75rem;
  color: #0056b3;
}

.map-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.map-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  margin-right: 1rem;
}

.map-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.map-stat {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: #6c757d;
  font-weight: 500;
}

.map-stat i {
  font-size: 0.75rem;
  color: #0056b3;
}

.map-display-area {
  flex: 1;
  position: relative;
  background-color: #f8f9fa;
  height: 400px; /* Increased height for full-width display */
}

.btn-primary, .btn-secondary {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8rem;
}

.btn-primary {
  background-color: #0056b3;
  color: white;
}

.btn-primary:hover {
  background-color: #004494;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
}

.no-maps-placeholder {
  text-align: center;
}

.placeholder-content {
  padding: 3rem 2rem;
}

.placeholder-content i {
  color: #6c757d;
  margin-bottom: 1rem;
}

.placeholder-content h3 {
  color: #495057;
  margin-bottom: 1rem;
}

.placeholder-content p {
  color: #6c757d;
  margin-bottom: 2rem;
}

.fas {
  margin-right: 0.25rem;
}

/* 全屏模式样式 */
.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.95);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;
  box-sizing: border-box;
}

.fullscreen-container {
  position: relative;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  background-color: white;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 浮动关闭按钮 */
.btn-close-floating {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 10;
  width: 40px;
  height: 40px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.btn-close-floating:hover {
  background-color: rgba(0, 0, 0, 0.9);
  transform: scale(1.1);
}

.fullscreen-maps-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 1rem;
  padding: 1rem 1rem 0 1rem;
  overflow: hidden;
  box-sizing: border-box;
  min-height: 0;
}

.fullscreen-map-item {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  width: 100%;
  height: 100%;
}

.fullscreen-map-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-height: 0;
  min-width: 0;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
}

.fullscreen-map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.fullscreen-map-header h4 {
  margin: 0;
  color: #333;
  font-size: 1.1rem;
}

.fullscreen-map-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #6c757d;
}

.fullscreen-map-stats i {
  color: #0056b3;
  margin-right: 0.25rem;
}

.fullscreen-map-display {
  flex: 1;
  background-color: #f8f9fa;
  min-height: 0;
  min-width: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

.fullscreen-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #f8f9fa;
  border-top: 1px solid #dee2e6;
}

.pagination-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.pagination-info {
  color: #6c757d;
  font-size: 0.85rem;
  font-weight: 500;
}

.btn-page {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background-color: white;
  color: #0056b3;
  border: 1px solid #0056b3;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-page:hover:not(:disabled) {
  background-color: #0056b3;
  color: white;
}

.btn-page:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  border-color: #dee2e6;
  cursor: not-allowed;
}

.page-dots {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.page-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #dee2e6;
  cursor: pointer;
  transition: background-color 0.2s;
}

.page-dot:hover {
  background-color: #adb5bd;
}

.page-dot.active {
  background-color: #0056b3;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .fullscreen-overlay {
    padding: 0.5rem;
  }
  
  .fullscreen-maps-grid {
    padding: 0.75rem;
    gap: 0.75rem;
  }
}

@media (max-width: 768px) {
  .fullscreen-maps-grid {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(4, 1fr);
  }
  
  .fullscreen-pagination {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
  }
  
  .pagination-center {
    order: -1;
  }
  
  .btn-close-floating {
    top: 0.5rem;
    right: 0.5rem;
    width: 36px;
    height: 36px;
    font-size: 1rem;
  }
}
</style>
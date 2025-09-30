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

    <!-- Tracker List Section -->
    <TrackerList 
      :trackers="trackers"
      @edit-tracker="handleEditTracker"
      @add-tracker="handleAddTracker"
      @toggle-star="handleToggleStar"
      @show-alert="handleShowAlert"
    />

    <!-- Map Viewer Section - TEMPORARILY DISABLED -->
    <!-- 
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
          <div classbu="empty-state">
            <i class="fas fa-map-marked-alt empty-state-icon"></i>
            <h3>{{ $t('tracker.noMapSelected') }}</h3>
            <p>{{ $t('tracker.selectMapToView') }}</p>
          </div>
        </div>
      </div>
    </div>
    -->
    
    <!-- Status Messages -->
    <p v-if="statusMessage" class="status-message" :class="statusMessageType">{{ statusMessage }}</p>
    
    <!-- No Map Selected State - TEMPORARILY DISABLED -->
    <!-- 
    <div v-if="!selectedMapConfig && wsStatus === 'connected'" class="empty-state-card">
      <div class="empty-state">
        <i class="fas fa-map-marked-alt empty-state-icon"></i>
        <h3>{{ $t('tracker.noMapSelected') }}</h3>
        <p>{{ $t('tracker.selectMapToView') }}</p>
      </div>
    </div>
    -->
    
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
import TrackerList from '@/components/TrackerList.vue';
import { loadConfigFromLocalStorage } from '@/services/localStorageService.js';
import { loadWebConfiguration, loadDashboardConfiguration, loadServerConfiguration, loadTrackers } from '@/services/configApiService.js';
import { getWsBaseUrl, buildWsUrl } from '@/config/api.js';

const statusMessage = ref('');
const statusMessageType = ref('info');
// 用于触发统计数据刷新的响应式变量
const statsRefreshTrigger = ref(0);

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
    if (!selectedMapConfig.value || !selectedMapConfig.value.map) {
        return [];
    }
    
    const selectedMapName = selectedMapConfig.value.map.name;
    
    // 合并API数据和WebSocket数据，优先使用WebSocket数据
    const combinedTrackers = {};
    
    // 1. 先添加API数据中属于当前地图的tracker
    allTrackers.value.forEach(tracker => {
        if (tracker.map === selectedMapName && tracker.trackerId) {
            combinedTrackers[tracker.trackerId] = {
                trackerId: tracker.trackerId,
                map: tracker.map,
                position: null, // API数据通常没有实时position
                timestamp: tracker.last_update_time ? new Date(tracker.last_update_time).getTime() : null,
                sos: tracker.sos !== undefined ? tracker.sos : 2,
                last_detected_beacons: tracker.last_detected_beacons || [],
                isFromApi: true
            };
        }
    });
    
    // 2. WebSocket数据覆盖API数据
    Object.values(trackers.value).forEach(tracker => {
        if (tracker.map === selectedMapName && tracker.trackerId) {
            combinedTrackers[tracker.trackerId] = {
                ...tracker, // 使用完整的WebSocket数据
                isFromApi: false
            };
        }
    });
    
    return Object.values(combinedTrackers)
        .sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

// Tracker statistics - 初始API数据 + WebSocket实时更新
const trackerStats = computed(() => {
    // 包含刷新触发器以确保定时更新
    statsRefreshTrigger.value;
    
    const now = Date.now();
    const fifteenMinutesMs = 15 * 60 * 1000; // 15 minutes in milliseconds
    
    // 合并API数据和WebSocket数据
    const allTrackerData = {};
    
    // 1. 先从API数据初始化所有设备状态
    allTrackers.value.forEach(tracker => {
        if (tracker.trackerId) {
            allTrackerData[tracker.trackerId] = {
                trackerId: tracker.trackerId,
                timestamp: tracker.last_update_time ? new Date(tracker.last_update_time).getTime() : 0,
                sos: tracker.sos !== undefined ? tracker.sos : 2,
                map: tracker.map || 'unknown map',
                isFromApi: true
            };
        }
    });
    
    // 2. 用WebSocket实时数据覆盖/更新设备状态
    const liveTrackers = Object.values(trackers.value);
    liveTrackers.forEach(tracker => {
        if (tracker.trackerId) {
            // 如果已有API数据，则更新；如果没有，则新增
            if (allTrackerData[tracker.trackerId]) {
                // 更新现有设备的实时数据
                allTrackerData[tracker.trackerId].timestamp = tracker.timestamp || allTrackerData[tracker.trackerId].timestamp;
                allTrackerData[tracker.trackerId].sos = tracker.sos !== undefined ? tracker.sos : allTrackerData[tracker.trackerId].sos;
                allTrackerData[tracker.trackerId].map = tracker.map || allTrackerData[tracker.trackerId].map;
                allTrackerData[tracker.trackerId].isFromApi = false; // 标记为已被WebSocket更新
            } else {
                // 新增仅在WebSocket中出现的设备
                allTrackerData[tracker.trackerId] = {
                    trackerId: tracker.trackerId,
                    timestamp: tracker.timestamp || 0,
                    sos: tracker.sos !== undefined ? tracker.sos : 2,
                    map: tracker.map || 'unknown map',
                    isFromApi: false
                };
            }
        }
    });
    
    const allCombinedTrackers = Object.values(allTrackerData);
    const totalTrackers = allCombinedTrackers.length;
    
    // Calculate online/offline based on timestamp
    const onlineTrackers = allCombinedTrackers.filter(tracker => {
        if (!tracker.timestamp) return false;
        return (now - tracker.timestamp) <= fifteenMinutesMs;
    }).length;
    
    const offlineTrackers = totalTrackers - onlineTrackers;
    
    // Count trackers by map
    const trackersByMap = {};
    allCombinedTrackers.forEach(tracker => {
        if (tracker.map && tracker.map !== 'unknown map') {
            trackersByMap[tracker.map] = (trackersByMap[tracker.map] || 0) + 1;
        }
    });
    
    // Count SOS trackers
    const sosTrackers = allCombinedTrackers.filter(tracker => tracker.sos === 1).length;
    
    // 调试日志 - 显示统计信息
    if (allCombinedTrackers.length > 0) {
        const apiCount = allCombinedTrackers.filter(t => t.isFromApi).length;
        const wsCount = allCombinedTrackers.filter(t => !t.isFromApi).length;
        console.log('[TrackerStats] Combined data summary:', {
            total: totalTrackers,
            fromApi: apiCount,
            updatedByWS: wsCount,
            online: onlineTrackers,
            offline: offlineTrackers,
            sosAlerts: sosTrackers,
            maps: Object.keys(trackersByMap),
            trackersByMap
        });
    }
    
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

const selectMap = async (mapConfig) => {
    selectedMapConfig.value = mapConfig;
    showMapDropdown.value = false;
    showStatus(`Selected map: ${mapConfig.map.name || 'Unnamed Map'}`, 'success');
    
    // 切换地图时重新获取tracker数据以获取最新状态
    showStatus('Loading tracker data for selected map...', 'info');
    await loadAllTrackers();
    
    // 触发统计数据更新
    statsRefreshTrigger.value++;
    
    showStatus(`Map switched successfully: ${mapConfig.map.name || 'Unnamed Map'}`, 'success');
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
    
    // 使用配置化的WebSocket URL
    const wsUrl = buildWsUrl('/ws');
    console.log('[TrackerModeConfig] Connecting to WebSocket:', wsUrl);
    ws.value = new WebSocket(wsUrl);
    wsStatus.value = 'connecting';
    showStatus('Connecting to server...', 'info');

    ws.value.onopen = () => { 
        wsStatus.value = 'connected'; 
        showStatus('Connected to server', 'success');
        loadAvailableMaps();
        loadAllTrackers(); // 恢复API调用，获取初始设备状态
        fetchFullServerConfig();    
    };
    
    ws.value.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);

            if (message.type === 'initial_state') {
                trackers.value = message.data || {};
            } else if (message.type === 'tracker_update') {
                const updatedTrackerId = Object.keys(message.data)[0];
                    if (updatedTrackerId && message.data[updatedTrackerId]) {
                        const newTrackerData = message.data[updatedTrackerId];

                        console.log(`[DEBUG] WebSocket update for ${updatedTrackerId}: original sos=${newTrackerData.sos}, type=${typeof newTrackerData.sos}`);
                        // SOS值：0=恢复, 1=触发, 2=未知，确保正确处理0值
                        const finalSos = newTrackerData.sos !== undefined ? newTrackerData.sos : 2;
                        console.log(`[DEBUG] Final sos value: ${finalSos}, type=${typeof finalSos}`);

                        const trackerInstanceData = {
                            trackerId: newTrackerData.trackerId,
                            map: newTrackerData.map,
                            position: newTrackerData.position ? {
                                x: newTrackerData.position.x,
                                y: newTrackerData.position.y,
                                accuracy: newTrackerData.position.accuracy
                            } : null,
                            timestamp: newTrackerData.timestamp,
                            sos: finalSos,
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
            } else if (message.type === 'tracker_location_approximate') {
                console.log('[TrackerMode] Processing tracker_location_approximate. Data:', message.data);
                const updatedTrackerId = Object.keys(message.data)[0];
                if (updatedTrackerId && message.data[updatedTrackerId]) {
                    const newTrackerData = message.data[updatedTrackerId];
                    console.log(`[TrackerMode] Updating tracker ${updatedTrackerId} with approximate location:`, newTrackerData);
                    
                    const trackerInstanceData = {
                        trackerId: newTrackerData.trackerId,
                        map: newTrackerData.map,
                        position: null, // 区域定位没有精确position
                        radius: newTrackerData.radius,
                        timestamp: newTrackerData.timestamp,
                        sos: newTrackerData.sos !== undefined ? newTrackerData.sos : 2,
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
            } else if (message.type === 'tracker_sos') {
                console.log('[TrackerMode] Processing tracker_sos. Data:', message.data);
                const updatedTrackerId = Object.keys(message.data)[0];
                    if (updatedTrackerId && message.data[updatedTrackerId]) {
                        if (!trackers.value[updatedTrackerId]) {
                            console.log('[TrackerMode] Tracker not found for SOS update:', updatedTrackerId);
                            return;
                        }
                        const newTrackerEvent = message.data[updatedTrackerId];
                        trackers.value[updatedTrackerId].sos = newTrackerEvent.sos;
                        trackers.value[updatedTrackerId].sos_happen = newTrackerEvent.timestamp;
                        console.log(`[TrackerMode] Updated SOS status for ${updatedTrackerId}: sos=${newTrackerEvent.sos}, timestamp=${newTrackerEvent.timestamp}`);
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
    // Convert tracker states object to array format
    if (Array.isArray(trackersData)) {
      allTrackers.value = trackersData;
    } else if (trackersData && typeof trackersData === 'object') {
      // Convert object to array of tracker states
      allTrackers.value = Object.values(trackersData);
    } else {
      allTrackers.value = [];
    }
    console.log(`Loaded ${allTrackers.value.length} total trackers from server`);
  } catch (error) {
    console.error('Error loading all trackers:', error);
    allTrackers.value = [];
  }
};

const loadAvailableMaps = async () => {
  try {
    // Load dashboard configuration which contains the maps array
    const dashboardConfig = await loadDashboardConfiguration();
    
    if (dashboardConfig && Array.isArray(dashboardConfig.maps)) {
      // Dashboard config contains a maps array
      availableMaps.value = dashboardConfig.maps;
      
      if (dashboardConfig.maps.length > 0) {
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

// TrackerList事件处理方法
const handleEditTracker = (tracker) => {
  console.log('[TrackerModeConfig] Edit tracker:', tracker);
  
  // 实现编辑设备的逻辑
  showStatus(`编辑设备: ${tracker.name || tracker.trackerId}`, 'info');
  
  // TODO: 这里需要实现具体的编辑弹窗或页面跳转
  // 可能需要：
  // 1. 打开编辑模态框
  // 2. 加载设备详细信息
  // 3. 提供表单让用户编辑设备名称、分组、参数等
};

const handleAddTracker = () => {
  console.log('[TrackerModeConfig] Add new tracker');
  
  // 实现添加设备的逻辑
  showStatus('打开添加设备界面', 'info');
  
  // TODO: 这里需要实现具体的添加设备逻辑
  // 可能需要：
  // 1. 打开添加设备模态框
  // 2. 提供表单让用户输入设备信息（EUI、名称、分组等）
  // 3. 调用后端API注册新设备
  // 4. 更新设备列表
};

const handleToggleStar = async (tracker) => {
  console.log('[TrackerModeConfig] Toggle star for tracker:', tracker.trackerId, tracker.starred);
  
  try {
    // 实现收藏/取消收藏的逻辑
    const action = tracker.starred ? '取消收藏' : '收藏';
    showStatus(`${action}设备: ${tracker.name || tracker.trackerId}`, 'info');
    
    // TODO: 这里需要调用后端API保存收藏状态
    // 示例API调用：
    // const response = await fetch(`/api/trackers/${tracker.trackerId}/star`, {
    //   method: 'PUT',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ starred: tracker.starred })
    // });
    
    // if (!response.ok) {
    //   throw new Error('保存收藏状态失败');
    // }
    
    showStatus(`${action}成功`, 'success');
  } catch (error) {
    console.error('[TrackerModeConfig] Error toggling star:', error);
    showStatus(`${tracker.starred ? '取消收藏' : '收藏'}失败: ${error.message}`, 'error');
    // 回滚状态
    tracker.starred = !tracker.starred;
  }
};

const handleShowAlert = (tracker) => {
  console.log('[TrackerModeConfig] Show alert for tracker:', tracker);
  
  // 实现显示设备警报设置的逻辑
  showStatus(`打开设备警报设置: ${tracker.name || tracker.trackerId}`, 'info');
  
  // TODO: 这里需要实现具体的警报设置逻辑
  // 可能需要：
  // 1. 打开警报设置模态框
  // 2. 显示当前的警报配置（低电量警报、离线警报、区域警报等）
  // 3. 提供界面让用户配置警报参数
  // 4. 调用后端API保存警报设置
};

// 定时器引用
let statsUpdateInterval = null;

onMounted(() => {
    connectWebSocket();
    document.addEventListener('click', handleClickOutside);
    
    // 启动统计数据更新定时器，每30秒刷新一次在线/离线状态
    statsUpdateInterval = setInterval(() => {
        statsRefreshTrigger.value++;
    }, 30000); // 30秒
});

onUnmounted(() => { 
    if (ws.value) { 
        ws.value.onclose = null; 
        ws.value.close(); 
    }
    document.removeEventListener('click', handleClickOutside);
    
    // 清理定时器
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
    }
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
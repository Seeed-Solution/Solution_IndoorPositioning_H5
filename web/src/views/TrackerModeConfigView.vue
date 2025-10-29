<template>
  <div class="tracker-mode-config-view page-content-wrapper">
    <h1 class="page-title">{{ $t('tracker.mapTracker') }}</h1>
    
    <!-- Tracker Statistics at Top -->
    <div class="tracker-stats-card card">
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
              <span class="map-count">{{ count }} {{ count === 1 ? $t('tracker.tracker') : $t('tracker.trackers') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tracker List Section -->
    <TrackerList 
      :trackers="trackerListData"
      @edit-tracker="handleEditTracker"
      @add-tracker="handleAddTracker"
      @toggle-star="handleToggleStar"
      @show-alert="handleShowAlert"
      @refresh-data="handleRefreshData"
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
    
    <!-- Alarm History Modal -->
    <AlarmHistoryModal 
      :isVisible="showAlarmHistoryModal"
      :selectedTracker="selectedTrackerForAlarm"
      @close="handleCloseAlarmModal"
      @view-on-map="handleViewAlarmOnMap"
      @view-details="handleViewAlarmDetails"
    />
    
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
    
    <!-- Disconnected State - DISABLED for WebSocket removal -->
    <!-- 
    <div v-if="wsStatus === 'disconnected'" class="empty-state-card">
      <div class="empty-state">
        <i class="fas fa-wifi-slash empty-state-icon error"></i>
        <h3>{{ $t('tracker.connectionLost') }}</h3>
        <p>{{ $t('tracker.reconnecting') }}</p>
      </div>
    </div>
    -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import MapPreview from '@/components/MapPreview.vue';
import TrackerList from '@/components/TrackerList.vue';
import AlarmHistoryModal from '@/components/AlarmHistoryModal.vue';
import { loadConfigFromLocalStorage } from '@/services/localStorageService.js';
import { loadWebConfiguration, loadDashboardConfiguration, loadServerConfiguration, loadTrackers, loadLatestTrackerData } from '@/services/configApiService.js';
import { getWsBaseUrl, buildWsUrl } from '@/config/api.js';

const { t } = useI18n();

const statusMessage = ref('');
const statusMessageType = ref('info');
// 用于触发统计数据刷新的响应式变量
const statsRefreshTrigger = ref(0);

// Alarm History Modal state
const showAlarmHistoryModal = ref(false);
const selectedTrackerForAlarm = ref(null);

// Available maps and selection
const availableMaps = ref([]);
const selectedMapConfig = ref(null);
const showMapDropdown = ref(false);
const showTrails = ref(false);

// WebSocket and tracker data - DISABLED for Map Preview removal
// const trackers = ref({}); 
const allTrackers = ref([]); // All trackers from /api/trackers
// const ws = ref(null);
// const wsStatus = ref('disconnected');
// const liveMqttStatusForServerSettings = ref('unknown');
// const currentServerConfig = ref(null);

// Computed properties
const filteredTrackerList = computed(() => {
    if (!selectedMapConfig.value || !selectedMapConfig.value.map) {
        return [];
    }
    
    const selectedMapName = selectedMapConfig.value.map.name;
    
    // 只使用API数据 (WebSocket部分已禁用)
    const filteredTrackers = allTrackers.value
        .filter(tracker => tracker.map === selectedMapName && tracker.trackerId)
        .map(tracker => ({
            trackerId: tracker.trackerId,
            map: tracker.map,
            position: (tracker.x !== null && tracker.y !== null) ? {
                x: tracker.x,
                y: tracker.y,
                accuracy: 1.0
            } : null,
            timestamp: tracker.last_update_time || null,
            sos: tracker.sos !== undefined ? tracker.sos : 2,
            last_detected_beacons: tracker.last_detected_beacons || [],
            device_name: tracker.device_name,
            group_id: tracker.group_id,
            is_favorite: tracker.is_favorite || false,
            isFromApi: true
        }))
        .sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
    
    return filteredTrackers;
    
    /* DISABLED - WebSocket integration for Map Preview
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
    */
});

// Tracker statistics - 仅使用API数据 (WebSocket已禁用)
const trackerStats = computed(() => {
    // 包含刷新触发器以确保定时更新
    statsRefreshTrigger.value;
    
    // 只使用API数据
    const totalTrackers = allTrackers.value.length;
    
    // Calculate online/offline status - 完全依赖后端online字段
    // online=在线，offline/unknown=离线
    const onlineTrackers = allTrackers.value.filter(tracker => {
        return tracker.online === 'online';
    }).length;
    
    const offlineTrackers = totalTrackers - onlineTrackers;
    
    // Count trackers by map (包含unknown地图)
    const trackersByMap = {};
    allTrackers.value.forEach(tracker => {
        const mapName = tracker.map || t('common.unknown'); // 没有map字段时默认为unknown
        trackersByMap[mapName] = (trackersByMap[mapName] || 0) + 1;
    });
    
    // Count SOS trackers
    const sosTrackers = allTrackers.value.filter(tracker => tracker.sos === 1).length;
    
    // 调试日志 - 显示统计信息
    if (allTrackers.value.length > 0) {
        console.log('[TrackerStats] 📊 统计数据更新:', {
            '📱 总设备数': totalTrackers,
            '🟢 在线设备': onlineTrackers,
            '🔴 离线设备': offlineTrackers,
            '🚨 SOS告警': sosTrackers,
            '🗺️ 地图分布': trackersByMap,
            '📍 地图列表': Object.keys(trackersByMap)
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

// 根据group_id获取分组名称的辅助函数
const getGroupNameById = (groupId) => {
    if (groupId === 0 || groupId === null || groupId === undefined) {
        return t('tracker.defaultGroup');
    }
    // 从API数据中查找对应的分组名称
    // 注意：这需要有分组数据的支持，目前暂时返回默认格式
    return `Group ${groupId}`;
};

// 为TrackerList组件准备的数据格式 - 直接使用后端online字段
const trackerListData = computed(() => {
    const result = {};
    
    allTrackers.value.forEach(tracker => {
        if (tracker && tracker.trackerId) {
            result[tracker.trackerId] = {
                trackerId: tracker.trackerId,
                device_name: tracker.device_name, // 传递设备名
                timestamp: tracker.last_update_time,
                sos: tracker.sos,
                last_detected_beacons: tracker.last_detected_beacons || [],
                starred: tracker.is_favorite || false,
                group_id: tracker.group_id || 0, // 传递group_id，让TrackerList组件处理分组名映射
                online: tracker.online, // 直接传递后端的online字段：'online'/'offline'/'unknown'
                // 设备硬件信息
                battery: tracker.battery, // 电池电量
                // Last Position相关字段
                map: tracker.map || t('common.unknown'), // 所在地图
                type: tracker.type, // 定位类型：'calculation' 或 'approximate'
                x: tracker.x, // X坐标
                y: tracker.y, // Y坐标
                radius: tracker.radius, // 区域半径
                last_known_measurement_time: tracker.last_known_measurement_time, // 最后一次定位时间（毫秒时间戳）
                position: (tracker.x !== null && tracker.y !== null) ? {
                    x: tracker.x,
                    y: tracker.y,
                    accuracy: 1.0
                } : null
            };
        }
    });
    
    console.log('[TrackerModeConfig] TrackerList data prepared, total:', Object.keys(result).length);
    return result;
});

// Map selection methods
const toggleMapDropdown = () => {
    showMapDropdown.value = !showMapDropdown.value;
};

const selectMap = async (mapConfig) => {
    selectedMapConfig.value = mapConfig;
    showMapDropdown.value = false;
    showStatus(t('tracker.selectedMap', { mapName: mapConfig.map.name || t('tracker.unnamedMap') }), 'success');
    
    // 切换地图时重新获取tracker数据以获取最新状态
    showStatus(t('tracker.loadingTrackerData'), 'info');
    await refreshTrackerData();
    
    // 触发统计数据更新
    statsRefreshTrigger.value++;
    
    showStatus(t('tracker.mapSwitchedSuccessfully', { mapName: mapConfig.map.name || t('tracker.unnamedMap') }), 'success');
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
        parts.push(`${beaconsCount} ${beaconsCount === 1 ? t('tracker.beacon') : t('tracker.beacons')}`);
    }
    if (entitiesCount > 0) {
        parts.push(`${entitiesCount} ${entitiesCount === 1 ? t('tracker.entity') : t('tracker.entities')}`);
    }
    
    return parts.length > 0 ? parts.join(', ') : t('common.noData');
};

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
    if (!event.target.closest('.map-selector-dropdown')) {
        showMapDropdown.value = false;
    }
};

/* DISABLED - WebSocket connection for Map Preview
const connectWebSocket = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return;
    
    // 使用配置化的WebSocket URL
    const wsUrl = buildWsUrl('/ws');
    console.log('[TrackerModeConfig] Connecting to WebSocket:', wsUrl);
    ws.value = new WebSocket(wsUrl);
    wsStatus.value = 'connecting';
    showStatus(t('tracker.connectingToServer'), 'info');

    ws.value.onopen = () => { 
        wsStatus.value = 'connected'; 
        showStatus(t('tracker.connectedToServer'), 'success');
        loadAvailableMaps();
        refreshTrackerData(); // 使用新的数据刷新函数
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
        showStatus(t('tracker.websocketConnectionError'), 'error');
    };
    
    ws.value.onclose = () => { 
        wsStatus.value = 'disconnected'; 
        showStatus(t('tracker.disconnectedReconnecting'), 'error');
        setTimeout(connectWebSocket, 3000);
    };
};
*/

const showStatus = (msg, type = 'info') => {
    statusMessage.value = msg;
    statusMessageType.value = type; 
    setTimeout(() => { statusMessage.value = ''; statusMessageType.value = 'info'; }, 5000); 
};

// 数据格式转换函数：将后端格式转换为组件内部格式
const convertTrackerDataFormat = (backendData) => {
  const convertedTrackers = {};
  
  // 遍历后端返回的对象格式数据
  Object.entries(backendData).forEach(([trackerId, trackerInfo]) => {
    convertedTrackers[trackerId] = {
      trackerId: trackerInfo.trackerId,
      map: trackerInfo.map || t('common.unknown'),
      position: (trackerInfo.x !== null && trackerInfo.y !== null) ? {
        x: trackerInfo.x,
        y: trackerInfo.y,
        accuracy: 1.0 // 默认精度
      } : null,
      timestamp: trackerInfo.last_update_time || Date.now(), // 最近设备上报的时间
      sos: trackerInfo.sos !== undefined ? trackerInfo.sos : 2, // 0=恢复, 1=触发, 2=未知
      sos_happen: trackerInfo.sos_happen, // 设备上次触发sos告警的时间
      last_detected_beacons: trackerInfo.last_detected_beacons || [],
      position_history: trackerInfo.position_history || [],
      radius: trackerInfo.radius || 0.0,
      battery: trackerInfo.battery,
      online: trackerInfo.online || t('common.unknown'),
      device_name: trackerInfo.device_name,
      group_id: trackerInfo.group_id,
      is_favorite: trackerInfo.is_favorite || false,
      // 正确传递后端的last_known_measurement_time字段
      last_known_measurement_time: trackerInfo.last_known_measurement_time, // 设备上次定位成功的时间（毫秒时间戳）
      // 其他位置相关字段
      type: trackerInfo.type, // 定位类型：'calculation' 或 'approximate'
      x: trackerInfo.x,
      y: trackerInfo.y,
      // 标记数据来源
      isFromApi: true
    };
  });
  
  return convertedTrackers;
};

// 封装好的更新本地数据函数 - 每次调用都会获取最新数据并更新组件状态
const refreshTrackerData = async () => {
  try {
    console.log('[TrackerModeConfig] Refreshing tracker data from backend...');
    
    // 1. 获取最新的后端数据
    const latestBackendData = await loadLatestTrackerData();
    
    // 2. 转换数据格式
    const convertedData = convertTrackerDataFormat(latestBackendData);
    
    // 3. 更新到allTrackers（用于统计和基础数据）
    allTrackers.value = Object.values(convertedData);
    
    // 4. DISABLED - WebSocket trackers update for Map Preview
    // Object.entries(convertedData).forEach(([trackerId, trackerData]) => {
    //   // 只有在WebSocket中没有这个tracker的实时数据时，才用API数据
    //   if (!trackers.value[trackerId]) {
    //     trackers.value[trackerId] = trackerData;
    //   }
    // });
    
    // 5. 触发统计数据更新
    statsRefreshTrigger.value++;
    
    console.log(`[TrackerModeConfig] Successfully refreshed ${Object.keys(convertedData).length} trackers`);
    
    return convertedData;
  } catch (error) {
    console.error('[TrackerModeConfig] Error refreshing tracker data:', error);
    showStatus(t('tracker.refreshDataFailed', { error: error.message }), 'error');
    throw error;
  }
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
        showStatus(t('tracker.noMapsFoundInDashboard'), 'warning');
      }
    } else if (dashboardConfig && dashboardConfig.map) {
      // Fallback: single map in dashboard config
      availableMaps.value = [dashboardConfig];
      selectedMapConfig.value = dashboardConfig;
    } else {
      // No maps found, try fallback sources
      showStatus(t('tracker.noMapsCheckingFallback'), 'warning');
      
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
        showStatus(t('tracker.noMapsConfigureFirst'), 'warning');
      }
    }
  } catch (error) {
    console.error('Error loading available maps:', error);
    showStatus(t('tracker.loadMapsFailed', { error: error.message }), 'error');
    availableMaps.value = [];
  }
};

const fetchFullServerConfig = async () => {
  // DISABLED - WebSocket status check for Map Preview
  // if (wsStatus.value !== 'connected') {
  //   return;
  // }
  try {
    const config = await loadServerConfiguration();
    if (config) {
      currentServerConfig.value = config;
      if (config.mqtt && typeof config.mqtt.live_mqtt_status !== 'undefined') {
        liveMqttStatusForServerSettings.value = config.mqtt.live_mqtt_status;
      } else if (config.mqtt && config.mqtt.enabled) {
        liveMqttStatusForServerSettings.value = t('common.unknown');
      }
    }
  } catch (error) {
    console.error('Error fetching server configuration:', error);
  }
};

// DISABLED - MQTT status for Map Preview
// const isMqttEffectivelyEnabled = computed(() => {
//   return currentServerConfig.value?.mqtt?.enabled && liveMqttStatusForServerSettings.value !== 'disabled';
// });

// TrackerList事件处理方法
const handleEditTracker = async (tracker) => {
  console.log('[TrackerModeConfig] Edit tracker completed:', tracker);
  
  // 编辑完成后刷新数据以获取最新状态
  showStatus(t('tracker.deviceUpdateSuccessRefreshing', { deviceName: tracker.device_name || tracker.trackerId }), 'info');
  
  try {
    // 刷新tracker数据
    await refreshTrackerData();
    
    // 触发统计数据更新
    statsRefreshTrigger.value++;
    
    showStatus(t('tracker.deviceUpdateSuccess', { deviceName: tracker.device_name || tracker.trackerId }), 'success');
  } catch (error) {
    console.error('[TrackerModeConfig] Error refreshing data after edit:', error);
    showStatus(t('tracker.deviceUpdateSuccessButRefreshFailed', { error: error.message }), 'warning');
  }
};

const handleAddTracker = () => {
  console.log('[TrackerModeConfig] Add new tracker');
  
  // 实现添加设备的逻辑
  showStatus(t('tracker.openAddDeviceInterface'), 'info');
  
  // TODO: 这里需要实现具体的添加设备逻辑
  // 可能需要：
  // 1. 打开添加设备模态框
  // 2. 提供表单让用户输入设备信息（EUI、名称、分组等）
  // 3. 调用后端API注册新设备
  // 4. 更新设备列表
};

const handleToggleStar = async (tracker) => {
  console.log('[TrackerModeConfig] Star status changed for tracker:', tracker.trackerId, tracker.starred);
  
  try {
    // star状态已在TrackerList组件中通过API更新，这里只需要刷新数据
    const action = tracker.starred ? t('tracker.favorite') : t('tracker.unfavorite');
    showStatus(t('tracker.favoriteSuccessRefreshing', { action }), 'info');
    
    // 刷新tracker数据以获取最新状态
    await refreshTrackerData();
    
    // 触发统计数据更新
    statsRefreshTrigger.value++;
    
    showStatus(t('tracker.favoriteSuccess', { action }), 'success');
  } catch (error) {
    console.error('[TrackerModeConfig] Error refreshing data after toggle star:', error);
    showStatus(t('tracker.favoriteSuccessButRefreshFailed', { error: error.message }), 'warning');
  }
};

const handleShowAlert = (tracker) => {
  console.log('[TrackerModeConfig] Show alert for tracker:', tracker);
  
  // 打开告警历史弹窗
  selectedTrackerForAlarm.value = tracker;
  showAlarmHistoryModal.value = true;
  
  showStatus(t('tracker.loadingAlarmHistory', { deviceName: tracker.device_name || tracker.trackerId }), 'info');
};

const handleRefreshData = async () => {
  console.log('[TrackerModeConfig] Refresh data requested from TrackerList');
  
  try {
    showStatus(t('tracker.refreshingDeviceData'), 'info');
    
    // 刷新tracker数据
    await refreshTrackerData();
    
    // 触发统计数据更新
    statsRefreshTrigger.value++;
    
    showStatus(t('tracker.deviceDataRefreshSuccess'), 'success');
  } catch (error) {
    console.error('[TrackerModeConfig] Error refreshing data:', error);
    showStatus(t('tracker.dataRefreshFailed', { error: error.message }), 'error');
  }
};

// Alarm History Modal事件处理方法
const handleCloseAlarmModal = () => {
  showAlarmHistoryModal.value = false;
  selectedTrackerForAlarm.value = null;
};

const handleViewAlarmOnMap = (alarm) => {
  console.log('[TrackerModeConfig] View alarm on map:', alarm);
  
  // TODO: 实现在地图上显示告警位置的逻辑
  // 可能需要：
  // 1. 检查告警是否有位置信息
  // 2. 切换到对应的地图
  // 3. 高亮显示告警位置
  // 4. 关闭告警历史弹窗
  
  if (alarm.position && alarm.position.map) {
    showStatus(t('tracker.showingAlarmOnMap', { mapName: alarm.position.map }), 'info');
    
    // 关闭告警历史弹窗
    handleCloseAlarmModal();
    
    // TODO: 切换到对应地图并高亮告警位置
  } else {
    showStatus(t('tracker.alarmNoPosition'), 'warning');
  }
};

const handleViewAlarmDetails = (alarm) => {
  console.log('[TrackerModeConfig] View alarm details:', alarm);
  
  // TODO: 实现显示告警详情的逻辑
  // 可能需要：
  // 1. 打开告警详情弹窗
  // 2. 显示告警的完整信息（触发条件、处理过程、相关设备状态等）
  // 3. 提供告警处理操作（手动恢复、标记为已处理等）
  
  showStatus(t('tracker.loadingAlarmDetails', { alarmName: alarm.name }), 'info');
};

// 定时器引用
let statsUpdateInterval = null;
let dataRefreshInterval = null;

onMounted(() => {
    // connectWebSocket(); // DISABLED - for Map Preview
    document.addEventListener('click', handleClickOutside);
    
    // 启动统计数据更新定时器，每30秒刷新一次在线/离线状态
    statsUpdateInterval = setInterval(() => {
        statsRefreshTrigger.value++;
    }, 30000); // 30秒
    
    // 启动设备数据自动刷新定时器，每10秒刷新一次设备数据
    dataRefreshInterval = setInterval(async () => {
        try {
            console.log('[TrackerModeConfig] Auto-refreshing tracker data...');
            await refreshTrackerData();
            console.log('[TrackerModeConfig] Auto-refresh completed successfully');
        } catch (error) {
            console.error('[TrackerModeConfig] Auto-refresh failed:', error);
            // 自动刷新失败时不显示错误提示，避免干扰用户
        }
    }, 10000); // 10秒
    
    // 初始化时获取数据 (替代WebSocket连接时的初始化)
    loadAvailableMaps();
    refreshTrackerData();
});

onUnmounted(() => { 
    // DISABLED - WebSocket cleanup for Map Preview
    // if (ws.value) { 
    //     ws.value.onclose = null; 
    //     ws.value.close(); 
    // }
    document.removeEventListener('click', handleClickOutside);
    
    // 清理定时器
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
    }
    if (dataRefreshInterval) {
        clearInterval(dataRefreshInterval);
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
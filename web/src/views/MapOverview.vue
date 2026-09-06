<template>
  <div class="map-overview-container">

    <!-- 页面内容 -->
    <div class="page-content">
      <!-- 页面标题 -->
      <h1 class="page-title">{{ $t('mapOverview.title') }}</h1>

      <!-- 状态消息 -->
      <div v-if="statusMessage" class="status-message" :class="statusMessage.toLowerCase().includes('error') ? 'error' : statusMessage.toLowerCase().includes('success') ? 'success' : 'info'">
        {{ statusMessage }}
      </div>

      <!-- 连接状态和统计信息 -->
      <div class="status-bar">
        <!-- WebSocket 连接状态 -->
        <div class="connection-status">
          <i :class="wsStatusIcon" class="status-icon"></i>
          <span class="status-label">{{ $t('mapOverview.webSocketLabel') }}:</span>
          <span :class="['status-value', wsStatus === 'connected' ? 'connected' : 'disconnected']">
            {{ wsStatusText }}
          </span>
        </div>

        <!-- 统计信息 -->
        <div class="stats-section">
          <div class="stat-item">
            <i class="fas fa-map stat-icon"></i>
            <span class="stat-number">{{ totalMaps }}</span>
            <span class="stat-label">{{ $t('mapOverview.maps') }}</span>
          </div>
          <div class="stat-item">
            <i class="fas fa-broadcast-tower stat-icon"></i>
            <span class="stat-number">{{ totalBeacons }}</span>
            <span class="stat-label">{{ $t('mapOverview.beacons') }}</span>
          </div>
          <div class="stat-item">
            <i class="fas fa-map-marker-alt stat-icon"></i>
            <span class="stat-number">{{ totalTrackers }}</span>
            <span class="stat-label">{{ $t('mapOverview.trackers') }}</span>
          </div>
        </div>
      </div>

      <!-- 地图概览区域 -->
      <div class="map-overview-section">
        <div class="section-header">
          <div class="section-title">
            <i class="fas fa-map section-icon"></i>
            <span>{{ $t('mapOverview.mapOverviewTitle') }}</span>
          </div>
          <button class="fullscreen-btn" @click="toggleFullscreen">
            <i class="fas fa-expand"></i>
            {{ $t('mapOverview.fullscreen') }}
          </button>
        </div>

        <!-- 主要内容区域 -->
        <div class="main-content-area">
          <!-- 左侧：地图选择器和地图显示 -->
          <div class="map-section">
            <!-- 地图选择器 -->
            <div class="map-selector">
              <div class="map-viewer-header">
                <div class="map-viewer-title">
                  <i class="fas fa-eye map-viewer-icon"></i>
                  <span class="map-viewer-label">{{ $t('mapOverview.mapViewer') }}</span>
                </div>
                <div class="map-dropdown">
                  <select v-model="selectedMapIndex" class="map-select" @change="onMapChange">
                    <option v-for="(map, index) in availableMaps" :key="index" :value="index">
                      {{ map.map?.name || `Map ${index + 1}` }} ({{ map.beacons?.length || 0 }} beacons)
                    </option>
                    <option :value="OUTDOOR_MAP_INDEX">
                      {{ $t('outdoorMap.title') }} ({{ outdoorTrackerList.length }})
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 地图显示区域 -->
            <div class="map-display-container">
              <div v-if="isOutdoorView" class="map-display">
                <OutdoorMapView
                  :trackers="trackers"
                  :outdoor="outdoorConfig"
                  :maps="availableMaps"
                  @registration-saved="onRegistrationSaved"
                />
              </div>
              <div v-else-if="selectedMap" class="map-display">
                <MapPreview 
                  :config="selectedMap"
                  :trackers="getTrackersForMap(selectedMap)"
                  :initialShowTrails="false"
                />
              </div>
              <div v-else class="no-map-selected">
                <i class="fas fa-map-marked-alt no-map-icon"></i>
                <p>{{ $t('mapOverview.selectMapToView') }}</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- 全屏模式 -->
    <div v-if="isFullscreen" class="fullscreen-overlay">
      <div class="fullscreen-container">
        <!-- 右上角关闭按钮 -->
        <button @click="exitFullscreen" class="btn-close-floating" :title="$t('mapOverview.exitFullscreen')">
          <i class="fas fa-times"></i>
        </button>

        <!-- 全屏布局 -->
        <div class="fullscreen-content">
          <!-- 左侧地图列表 -->
          <div class="fullscreen-map-list">
            <div class="map-list-header">
              <i class="fas fa-map map-list-icon"></i>
              <span class="map-list-title">{{ $t('mapOverview.map') }}</span>
            </div>
            <div class="map-list-items">
              <div 
                v-for="(map, index) in availableMaps" 
                :key="index"
                class="map-list-item"
                :class="{ active: selectedMapIndex === index }"
                @click="selectMapInFullscreen(index)"
              >
                <div class="map-item-header">
                  <span class="map-item-name">{{ map.map?.name || `Map ${index + 1}` }}</span>
                  <div class="map-item-stats">
                    <span class="beacon-count">{{ map.beacons?.length || 0 }} {{ $t('mapOverview.beacons') }}</span>
                    <span class="tracker-count">{{ Object.keys(getTrackersForMap(map)).length }} {{ $t('mapOverview.onlineTrackers') }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 中间地图显示 -->
          <div class="fullscreen-map-area">
            <div class="fullscreen-map-header">
              <h2 class="current-map-title">{{ selectedMap?.map?.name || $t('mapOverview.noMapSelected') }}</h2>
              <div class="map-header-stats">
                <span class="header-stat">
                  <i class="fas fa-broadcast-tower"></i>
                  {{ selectedMap?.beacons?.length || 0 }}
                </span>
                <span class="header-stat">
                  <i class="fas fa-map-marker-alt"></i>
                  {{ Object.keys(getTrackersForMap(selectedMap || {})).length }}
                </span>
              </div>
            </div>
            <div class="fullscreen-map-display">
              <OutdoorMapView
                v-if="isOutdoorView"
                :trackers="trackers"
                :outdoor="outdoorConfig"
                :maps="availableMaps"
                @registration-saved="onRegistrationSaved"
              />
              <MapPreview 
                v-else-if="selectedMap"
                ref="fullscreenMapPreviewRef"
                :config="selectedMap"
                :trackers="getTrackersForMap(selectedMap)"
                :initialShowTrails="false"
              />
              <div v-else class="no-map-placeholder">
                <i class="fas fa-map-marked-alt"></i>
                <p>{{ $t('mapOverview.selectMapToView') }}</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { 
  loadDashboardConfiguration,
  loadTrackers
} from '@/services/configApiService.js'
import { loadConfigFromLocalStorage } from '@/services/localStorageService.js'
import { buildWsUrl } from '@/config/api.js'
import MapPreview from '@/components/MapPreview.vue'
import OutdoorMapView from '@/components/OutdoorMapView.vue'
import { isOutdoorTracker } from '@/utils/trail.js'

const router = useRouter()
const { t } = useI18n()

// Config storage key
const CONFIG_STORAGE_KEY = 'mapDashboardConfig'

// 响应式数据
const wsStatus = ref('disconnected') // connected, connecting, disconnected, error
const totalMaps = ref(0)
const totalBeacons = ref(0)
const totalTrackers = ref(0)
const selectedMapIndex = ref(0)
const showTrails = ref(false)
const isLoading = ref(false)
const statusMessage = ref('')

// 全屏模式状态
const isFullscreen = ref(false)
const fullscreenMapPreviewRef = ref(null)

// 地图配置数据
const availableMaps = ref([])
const currentFullConfig = ref([])

// tracker数据 - 通过API和WebSocket获取
const trackers = ref({})
const ws = ref(null)

// 计算属性
const OUTDOOR_MAP_INDEX = -1
const outdoorConfig = ref(null)

const isOutdoorView = computed(() => selectedMapIndex.value === OUTDOOR_MAP_INDEX)

const selectedMap = computed(() => {
  if (isOutdoorView.value) return null
  return availableMaps.value[selectedMapIndex.value] || null
})

// tracker.type === 'wGS84' 的走室外 Leaflet 视图, 其余留在室内 Canvas 视图
const outdoorTrackerList = computed(
  () => Object.values(trackers.value || {}).filter(isOutdoorTracker)
)

const filteredTrackers = computed(() => {
  if (!selectedMap.value) return []
  return Object.values(getTrackersForMap(selectedMap.value))
})

const wsStatusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return t('mapOverview.connectionStatus.connected')
    case 'connecting': return t('mapOverview.connectionStatus.connecting')
    case 'disconnected': return t('mapOverview.connectionStatus.disconnected')
    case 'error': return t('mapOverview.connectionStatus.error')
    default: return t('mapOverview.connectionStatus.unknown')
  }
})

const wsStatusIcon = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'fas fa-wifi status-connected'
    case 'connecting': return 'fas fa-spinner fa-spin status-connecting'
    case 'disconnected': return 'fas fa-wifi-slash status-disconnected'
    case 'error': return 'fas fa-exclamation-triangle status-error'
    default: return 'fas fa-question-circle status-unknown'
  }
})

// 方法
const showStatus = (msg, type = 'info') => {
  statusMessage.value = `${type.toUpperCase()}: ${msg}`
  setTimeout(() => { statusMessage.value = '' }, 7000)
}

const initializeMasterConfig = async () => {
  isLoading.value = true
  showStatus(t('mapOverview.status.loadingMasterConfig'), 'info')
  
  try {
    const config = await loadDashboardConfiguration()
    outdoorConfig.value = config?.outdoor || null
    if (config && config.maps) {
      currentFullConfig.value = config.maps
      availableMaps.value = config.maps
      
      // 更新统计信息
      totalMaps.value = config.maps.length
      totalBeacons.value = config.maps.reduce((total, mapConfig) => 
        total + (mapConfig.beacons?.length || 0), 0)
      
      showStatus(t('mapOverview.status.masterConfigLoadedFromServer'), 'success')
      // console.log('[MapOverview] Loaded maps:', config.maps)
    } else {
      showStatus(t('mapOverview.status.noMasterConfigOnServer'), 'info')
      loadMasterConfigFromStorage()
    }
  } catch (error) {
    console.error('[MapOverview] Error loading master configuration from server:', error)
    showStatus(t('mapOverview.status.masterConfigLoadFailed', { error: error.message || t('common.unknownError') }), 'error')
    loadMasterConfigFromStorage()
  } finally {
    isLoading.value = false
  }
}

const loadMasterConfigFromStorage = () => {
  const loaded = loadConfigFromLocalStorage(CONFIG_STORAGE_KEY)
  if (loaded && loaded.maps) {
    currentFullConfig.value = loaded.maps
    availableMaps.value = loaded.maps
    
    // 更新统计信息
    totalMaps.value = loaded.maps.length
    totalBeacons.value = loaded.maps.reduce((total, mapConfig) => 
      total + (mapConfig.beacons?.length || 0), 0)
    
    showStatus(t('mapOverview.status.masterConfigLoadedFromStorage'))
    console.log('[MapOverview] Loaded maps from storage:', loaded.maps)
  } else {
    availableMaps.value = []
    totalMaps.value = 0
    totalBeacons.value = 0
    showStatus(t('mapOverview.status.noConfigFound'), 'warn')
  }
}

// 配准保存后本地也留一份, 刷新前就能按配准渲染; 服务端已落盘, 刷新后由
// initializeMasterConfig 重新读回来。
const onRegistrationSaved = ({ mapName, registration }) => {
  const entry = availableMaps.value.find((m) => m.map?.name === mapName)
  if (entry && entry.map) entry.map.registration = { ...registration }
}

const getTrackersForMap = (mapConfig) => {
  // 根据地图名称筛选相关的tracker
  const mapName = mapConfig.map?.name;
  if (!mapName) {
    return {};
  }
  
  const filteredTrackers = {};
  Object.entries(trackers.value).forEach(([trackerId, tracker]) => {
    // 室外 tracker 由 OutdoorMapView 渲染, 不进室内地图
    if (tracker.map === mapName && !isOutdoorTracker(tracker)) {
      filteredTrackers[trackerId] = tracker;
    }
  });
  
  return filteredTrackers;
}

// 预加载 tracker 数据的函数
const preloadTrackers = async () => {
  try {
    // console.log('[MapOverview] Preloading trackers data from /api/trackers...')
    const trackersData = await loadTrackers()
    
    // 处理返回的数据格式
    if (trackersData) {
      if (Array.isArray(trackersData)) {
        // 如果是数组格式，转换为对象
        trackers.value = trackersData.reduce((acc, tracker) => {
          if (tracker.trackerId) {
            acc[tracker.trackerId] = tracker
          }
          return acc
        }, {})
      } else if (typeof trackersData === 'object') {
        // 如果是对象格式，直接使用
        trackers.value = trackersData
      } else {
        trackers.value = {}
      }
      
      // console.log(`[MapOverview] Successfully preloaded ${Object.keys(trackers.value).length} trackers`)
      // 更新tracker统计
      totalTrackers.value = Object.keys(trackers.value).length
    } else {
      trackers.value = {}
      console.log('[MapOverview] No tracker data received from API')
    }
  } catch (error) {
    console.error('[MapOverview] Error preloading trackers:', error)
    trackers.value = {}
  }
}

const connectWebSocket = () => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) return;
  
  // 使用配置化的WebSocket URL
  const wsUrl = buildWsUrl('/ws');
  console.log('[MapOverview] Connecting to WebSocket:', wsUrl);
  ws.value = new WebSocket(wsUrl);
  wsStatus.value = 'connecting';

  ws.value.onopen = () => {
    wsStatus.value = 'connected';
    console.log('[MapOverview] WebSocket connected');
  };

  ws.value.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === 'initial_state') {
        trackers.value = message.data || {};
        totalTrackers.value = Object.keys(trackers.value).length;
      } else if (message.type === 'tracker_update') {
        console.log('[MapOverview] Processing tracker_update. Data:', message.data);
        const updatedTrackerId = Object.keys(message.data)[0];
        if (updatedTrackerId && message.data[updatedTrackerId]) {
          const newTrackerData = message.data[updatedTrackerId];
          console.log(`[MapOverview] Updating tracker ${updatedTrackerId} with (raw incoming):`, newTrackerData);

          const trackerInstanceData = {
            trackerId: newTrackerData.trackerId,
            device_name: newTrackerData.device_name,
            x: newTrackerData.position?.x ?? null,
            y: newTrackerData.position?.y ?? null,
            lat: newTrackerData.lat ?? newTrackerData.position?.lat ?? null,
            lon: newTrackerData.lon ?? newTrackerData.position?.lon ?? null,
            alt: newTrackerData.alt ?? null,
            accuracy: newTrackerData.accuracy ?? null,
            fix_time: newTrackerData.fix_time ?? null,
            // position: newTrackerData.position ? {
            //   x: newTrackerData.position.x,
            //   y: newTrackerData.position.y,
            //   accuracy: newTrackerData.position.accuracy
            // } : null,
            timestamp: newTrackerData.timestamp,
            sos: newTrackerData.sos !== undefined ? newTrackerData.sos : 2,
            sos_happen: newTrackerData.sos_happen,
            last_detected_beacons: newTrackerData.last_detected_beacons
              ? newTrackerData.last_detected_beacons.map(b => ({ ...b }))
              : [],
            used_beacons: newTrackerData.last_detected_beacons,
            position_history: newTrackerData.position_history
              ? newTrackerData.position_history.map(hEntry => Array.isArray(hEntry) ? [...hEntry] : hEntry)
              : [],
            type: newTrackerData.type || "calculation",
            map: newTrackerData.map
          };

          if (!trackers.value[updatedTrackerId]) {
            trackers.value = { ...trackers.value, [updatedTrackerId]: trackerInstanceData };
          } else {
            trackers.value[updatedTrackerId] = trackerInstanceData;
          }

          // 更新tracker统计
          totalTrackers.value = Object.keys(trackers.value).length;
        }
      } else if (message.type === 'tracker_location_approximate') {
        const updatedTrackerId = Object.keys(message.data)[0];
        if (updatedTrackerId && message.data[updatedTrackerId]) {
          const newTrackerData = message.data[updatedTrackerId];

          const trackerInstanceData = {
            trackerId: newTrackerData.trackerId,
            device_name: newTrackerData.device_name,
            position: null, // 区域定位没有精确position
            radius: newTrackerData.radius,
            timestamp: newTrackerData.timestamp,
            sos: newTrackerData.sos !== undefined ? newTrackerData.sos : 2,
            sos_happen: newTrackerData.sos_happen,
            used_beacons: newTrackerData.last_detected_beacons
              ? newTrackerData.last_detected_beacons.map(b => ({ ...b }))
              : [],
            type: "approximate",
            map: newTrackerData.map
          };

          console.log(`[MapOverview] Processed beacon data:`, trackerInstanceData.last_detected_beacons);

          if (!trackers.value[updatedTrackerId]) {
            trackers.value = { ...trackers.value, [updatedTrackerId]: trackerInstanceData };
          } else {
            trackers.value[updatedTrackerId] = trackerInstanceData;
          }

          // 更新tracker统计
          totalTrackers.value = Object.keys(trackers.value).length;
        }
      } else if (message.type === 'tracker_sos') {
        console.log('[MapOverview] Processing tracker_sos. Data:', message.data);
        const updatedTrackerId = Object.keys(message.data)[0];
        if (updatedTrackerId && message.data[updatedTrackerId]) {
          if (!trackers.value[updatedTrackerId]) {
            console.log('[MapOverview] not found the tracker: ', updatedTrackerId);
            return;
          }
          const newTrackerEvent = message.data[updatedTrackerId];
          trackers.value[updatedTrackerId].sos = newTrackerEvent.sos;
          trackers.value[updatedTrackerId].sos_happen = newTrackerEvent.timestamp;
        }
      } else {
        console.log('[MapOverview] Received unhandled message type:', message.type, 'Data:', message.data);
      }
    } catch (error) {
      console.error('[MapOverview] FATAL: Error parsing WebSocket message or in handler. Raw data:', event.data, 'Error:', error);
    }
  };

  ws.value.onerror = (error) => {
    wsStatus.value = 'error';
    console.error('[MapOverview] WebSocket error:', error);
  };

  ws.value.onclose = () => {
    wsStatus.value = 'disconnected';
    console.log('[MapOverview] WebSocket disconnected');
  };
};

const onMapChange = () => {
  console.log('Map changed to:', selectedMap.value)
  // 这里后续会添加地图切换的逻辑
}

const toggleTrails = () => {
  showTrails.value = !showTrails.value
  console.log('Trails toggled:', showTrails.value)
  // 这里后续会添加轨迹显示/隐藏的逻辑
}

const toggleFullscreen = async () => {
  isFullscreen.value = true
  // 阻止body滚动
  document.body.style.overflow = 'hidden'
  
  // 等待 Vue 完成 DOM 更新
  await nextTick()
  
  // 等待 MapPreview 组件初始化完成（包括布局计算）
  if (fullscreenMapPreviewRef.value && typeof fullscreenMapPreviewRef.value.waitForReady === 'function') {
    await fullscreenMapPreviewRef.value.waitForReady()
  }
  
  console.log('Entered fullscreen mode')
}

const exitFullscreen = () => {
  isFullscreen.value = false
  // 恢复body滚动
  document.body.style.overflow = ''
  console.log('Exited fullscreen mode')
}

const selectMapInFullscreen = (index) => {
  selectedMapIndex.value = index
  console.log('Selected map in fullscreen:', availableMaps.value[index])
}

// 键盘事件处理
const handleKeydown = (event) => {
  if (event.key === 'Escape' && isFullscreen.value) {
    exitFullscreen()
  }
}

// 生命周期钩子
onMounted(async () => {
  console.log('MapOverview component mounted')
  
  // 初始化地图配置
  await initializeMasterConfig()
  
  // 预加载tracker数据
  await preloadTrackers()
  
  // 建立WebSocket连接
  connectWebSocket()
  
  // 添加键盘事件监听
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  console.log('MapOverview component unmounting, closing WebSocket...')
  if (ws.value) {
    ws.value.onclose = null
    ws.value.close()
  }
  
  // 移除键盘事件监听
  window.removeEventListener('keydown', handleKeydown)
  
  // 确保恢复body滚动
  document.body.style.overflow = ''
})
</script>

<style scoped>
.map-overview-container {
  /* 页面被 AppShell 包在 64px 顶栏下面，写 100vh 会永远多出一屏高，逼出纵向滚动条 */
  min-height: calc(100vh - var(--sc-layout-header-height));
  background-color: var(--sc-color-bg-layout);
  display: flex;
  flex-direction: column;
}

/* 页面内容 */
.page-content {
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
  padding: 2rem;
  max-width: 1400px;
  margin: 1rem auto;
  width: 100%;
  background: white;
  border-radius: 8px;
}

.page-title {
  text-align: center;
  font-size: 2rem;
  font-weight: 600;
  color: var(--sc-color-text);
  margin-bottom: 2rem;
}

/* 状态消息 */
.status-message {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  text-align: center;
}

.status-message.info {
  background-color: var(--sc-color-bg-layout);
  color: #1976d2;
  border: 1px solid #bbdefb;
}

.status-message.success {
  background-color: #e8f5e8;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.status-message.error {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

/* 状态栏 */
/* 溢出根因 1: 状态栏原来不换行, 内容一多就把父容器撑宽 */
.status-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  background: white;
  border-radius: 8px;
  padding: 1rem 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-icon {
  font-size: 1.2rem;
}

.status-icon.status-connected {
  color: var(--sc-color-success);
}

.status-icon.status-connecting {
  color: var(--sc-color-info);
}

.status-icon.status-disconnected {
  color: #f44336;
}

.status-icon.status-error {
  color: #ff9800;
}

.status-label {
  font-weight: 500;
  color: var(--sc-color-text-secondary);
}

.status-value {
  font-weight: 600;
}

.status-value.connected {
  color: var(--sc-color-success);
}

.status-value.disconnected {
  color: #f44336;
}

/* 溢出根因 2: 统计卡定宽横排 -> auto-fit grid, 窄屏自动折行 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  min-width: 0;
  flex: 1 1 240px;
}

.stat-item {
  min-width: 0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--sc-color-bg-layout);
  border-radius: 6px;
  border: 1px solid var(--sc-color-border);
}

.stat-icon {
  color: var(--sc-color-info);
  font-size: 1rem;
}

.stat-number {
  font-size: 1.25rem;
  font-weight: bold;
  color: var(--sc-color-info);
  min-width: 30px;
  text-align: center;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--sc-color-text-secondary);
  font-weight: 500;
}

/* 地图概览区域 */
.map-overview-section {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--sc-color-bg-layout);
  border-bottom: 1px solid var(--sc-color-border);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--sc-color-text);
}

.section-icon {
  color: var(--sc-color-info);
}

.fullscreen-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--sc-color-info);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background-color 0.3s;
}

.fullscreen-btn:hover {
  background: #1976D2;
}

/* 主要内容区域 */
.main-content-area {
  display: flex;
  min-width: 0;
  height: 600px;
}

/* 地图区域 */
.map-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 0; /* 允许 flex 子元素收缩，防止被内容撑开 */
}

.map-selector {
  padding: 1rem;
  background: var(--sc-color-bg-layout);
  border-bottom: 1px solid var(--sc-color-border);
}

.map-viewer-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.map-viewer-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.map-viewer-icon {
  color: var(--sc-color-text-secondary);
}

.map-viewer-label {
  font-weight: 500;
  color: var(--sc-color-text);
}

.map-dropdown {
  position: relative;
  min-width: 0;
  max-width: 100%;
}

/* 溢出根因 3: 下拉 min-width:250px 在窄屏直接顶出容器 */
.map-select {
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  padding: 0.75rem;
  border: 1px solid var(--sc-color-border);
  border-radius: 6px;
  background: white;
  font-size: 0.9rem;
  color: var(--sc-color-text);
  cursor: pointer;
}

.map-select:focus {
  outline: none;
  border-color: var(--sc-color-info);
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

/* 地图显示区域 */
.map-display-container {
  flex: 1;
  position: relative;
  min-height: 0; /* 允许 flex 子元素收缩，防止被内容撑开 */
}

.map-display {
  height: 100%;
  background: var(--sc-color-bg-layout);
}

.map-display :deep(.map-preview-container) {
  height: 100%;
}


.no-map-selected {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--sc-color-text-tertiary);
}

.no-map-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}


/* 响应式设计 */
@media (max-width: 1200px) {
  .main-content-area {
    height: auto;
  }
  
  .map-section {
    width: 100%;
    height: 600px;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: 1rem;
  }
  
  .status-bar {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .stats-section {
    justify-content: space-around;
    gap: 1rem;
  }
  
  .section-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
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
  overflow: hidden;
  box-sizing: border-box;
}

.fullscreen-container {
  position: relative;
  width: 100%;
  height: 100vh;
  background-color: var(--sc-color-bg-layout);
  display: grid;
  grid-template-rows: 1fr;
  overflow: hidden;
  box-sizing: border-box;
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

/* 全屏内容布局 */
.fullscreen-content {
  display: grid;
  grid-template-columns: 220px 1fr;
  height: 100vh;
  overflow: hidden;
}

/* 左侧地图列表 */
.fullscreen-map-list {
  width: 220px;
  background: white;
  border-right: 1px solid var(--sc-color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.map-list-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--sc-color-bg-layout);
  border-bottom: 1px solid var(--sc-color-border);
  font-weight: 600;
  color: var(--sc-color-text);
}

.map-list-icon {
  color: var(--sc-color-info);
  font-size: 1.1rem;
}

.map-list-title {
  font-size: 1rem;
}

.map-list-items {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.map-list-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.map-list-item:hover {
  background: var(--sc-color-bg-container);
}

.map-list-item.active {
  background: var(--sc-color-bg-layout);
  border-color: var(--sc-color-info);
}

.map-item-header {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.map-item-name {
  font-weight: 600;
  color: var(--sc-color-text);
  font-size: 0.9rem;
}

.map-item-stats {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.beacon-count,
.tracker-count {
  font-size: 0.75rem;
  color: var(--sc-color-text-secondary);
}

.beacon-count {
  color: #ff9800;
}

.tracker-count {
  color: var(--sc-color-success);
}

/* 中间地图区域 */
.fullscreen-map-area {
  display: grid;
  grid-template-rows: auto 1fr;
  background: white;
  overflow: hidden;
  height: 100vh;
}

.fullscreen-map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--sc-color-bg-layout);
  border-bottom: 1px solid var(--sc-color-border);
  flex-shrink: 0;
}

.current-map-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--sc-color-text);
}

.map-header-stats {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.header-stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 500;
  color: var(--sc-color-text-secondary);
}

.header-stat i {
  color: var(--sc-color-info);
  font-size: 1.1rem;
}

.fullscreen-map-display {
  height: calc(100vh - 73px);
  background: var(--sc-color-bg-layout);
  overflow: hidden;
  position: relative;
}

.fullscreen-map-display :deep(.map-preview-container) {
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fullscreen-map-display :deep(.content-columns) {
  height: 100%;
  max-height: 100%;
  overflow: hidden;
}

.fullscreen-map-display :deep(.map-view-wrapper) {
  height: 100%;
  overflow: hidden;
}

.fullscreen-map-display :deep(.map-container) {
  height: 100%;
  max-height: 100%;
  overflow: hidden;
}

.fullscreen-map-display :deep(canvas) {
  max-width: none !important;
  max-height: 100% !important;
  width: 100% !important;
  height: auto !important;
  object-fit: contain;
}

.no-map-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--sc-color-text-tertiary);
}

.no-map-placeholder i {
  font-size: 4rem;
  margin-bottom: 1rem;
}


/* 全屏模式响应式设计 */
@media (max-width: 1200px) {
  .fullscreen-map-list {
    width: 200px;
  }
}

@media (max-width: 768px) {
  .fullscreen-content {
    grid-template-columns: 1fr;
    grid-template-rows: 120px 1fr;
  }
  
  .fullscreen-map-list {
    width: 100%;
    height: 120px;
    border-right: none;
    border-bottom: 1px solid var(--sc-color-border);
  }
  
  .map-list-items {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    gap: 0.5rem;
    padding: 0.5rem;
  }
  
  .map-list-item {
    min-width: 150px;
    margin-bottom: 0;
  }
  
  .fullscreen-map-area {
    grid-row: 2;
  }
  
  .fullscreen-map-display {
    height: calc(100vh - 73px - 120px);
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
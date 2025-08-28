<!-- web/src/components/MapPreview.vue -->
<template>
  <div class="map-preview-container">
    <div class="content-columns">
      <div class="map-view-wrapper">
        <div class="map-container">
          <canvas ref="mapCanvas" :width="canvasWidth" :height="canvasHeight" style="border: 1px solid #ccc;"></canvas>
          <!-- 加载指示器 -->
          <div v-if="isLoadingTrackers" class="loading-overlay">
            <div class="loading-content">
              <i class="fas fa-spinner fa-spin"></i>
              <span>{{ t('tracker.loadingTrackers') || 'Loading trackers...' }}</span>
            </div>
          </div>
          <div v-if="config && config.map" class="map-info" style="display: none;">
            Map Dimensions: {{ config.map.width.toFixed(1) }}m x {{ config.map.height.toFixed(1) }}m
          </div>
          <div v-else class="map-info" style="display: none;">
            Load configuration to display map.
          </div>
        </div>
      </div>
      <aside class="tracker-list-aside">
        <!-- 告警记录视图 (完全替换tracker列表) -->
        <div v-if="showAlarmPanel" class="alarm-records-view">
          <div class="alarm-view-header">
            <button @click="closeAlarmPanel" class="back-btn" :title="t('common.back')">
              <i class="fas fa-arrow-left"></i>
            </button>
            <div class="header-title">
              <i class="fas fa-exclamation-triangle alarm-icon"></i>
              <div class="title-content">
                <h4>{{ t('tracker.alarmRecords') }}</h4>
                <span class="device-id">{{ selectedTracker?.trackerId }}</span>
              </div>
            </div>
          </div>
          
          <div class="alarm-view-body">
            <div v-if="isLoadingAlarms" class="loading-indicator">
              <i class="fas fa-spinner fa-spin"></i> {{ t('common.loading') }}
            </div>
            
            <div v-else-if="alarmRecords.length === 0" class="no-alarms">
              <i class="fas fa-shield-alt"></i>
              <p>{{ t('tracker.noAlarmRecords') }}</p>
            </div>
            
            <div v-else class="alarm-records-list">
              <div v-for="record in alarmRecords" :key="record.id" 
                   class="alarm-record-item" 
                   :class="{ 'sos-alarm': record.sos === 1, 'sos-recovery': record.sos === 0, 'clickable': hasBluetoothLocation(record) }"
                   @click="showAlarmLocationOnMap(record)">
                <div class="alarm-header">
                  <div class="alarm-type">
                    <i :class="record.sos === 1 ? 'fas fa-exclamation-circle' : record.sos === 0 ? 'fas fa-check-circle' : 'fas fa-info-circle'" 
                       :style="{ color: record.sos === 1 ? '#dc3545' : record.sos === 0 ? '#28a745' : '#17a2b8' }"></i>
                    <span>{{ record.sos === 1 ? t('tracker.sosAlert').replace('🚨 ', '') : record.sos === 0 ? t('tracker.sosRecovery') : t('tracker.statusChange') }}</span>
                  </div>
                </div>
                
                <div class="alarm-details">
                  <div class="alarm-time-detail">
                    <i class="fas fa-clock"></i>
                    <span>{{ formatDateTime(record.alarm_time) }}</span>
                  </div>
                  
                  <div v-if="record.loc && (record.loc.x !== undefined || record.loc.lon !== undefined)" class="alarm-location">
                    <i class="fas fa-map-marker-alt"></i>
                    <span v-if="record.pos_type === 'bluetooth' && record.loc.x !== undefined">
                      {{ t('tracker.location') }}: X={{ record.loc.x?.toFixed(2) }}, Y={{ record.loc.y?.toFixed(2) }} ({{ t('tracker.bluetoothPositioning') }})
                    </span>
                    <span v-else-if="record.pos_type === 'gps' && record.loc.lon !== undefined">
                      {{ t('tracker.location') }}: {{ t('tracker.longitude') }}={{ record.loc.lon?.toFixed(6) }}, {{ t('tracker.latitude') }}={{ record.loc.alt?.toFixed(6) }} ({{ t('tracker.gpsPositioning') }})
                    </span>
                    <span v-else>{{ t('tracker.locationNotAvailable') }}</span>
                  </div>
                  
                  <div v-if="record.map_name" class="alarm-map">
                    <i class="fas fa-map"></i>
                    <span>{{ t('tracker.map') }}: {{ record.map_name }}</span>
                  </div>
                  
                  <div class="alarm-pos-type">
                    <i class="fas fa-satellite"></i>
                    <span>{{ t('tracker.positioningType') }}: {{ record.pos_type === 'bluetooth' ? t('tracker.bluetoothPositioning') : record.pos_type === 'gps' ? t('tracker.gpsPositioning') : t('tracker.unknown') }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 分页控制 -->
            <div v-if="pagination.total_pages > 1" class="pagination-controls">
              <button @click="loadAlarmPage(pagination.page - 1)" :disabled="pagination.page <= 1" class="page-button">
                <i class="fas fa-chevron-left"></i> {{ t('tracker.previousPage') }}
              </button>
              <span class="page-info">{{ t('tracker.pageInfo', { page: pagination.page, total: pagination.total_pages }) }}</span>
              <button @click="loadAlarmPage(pagination.page + 1)" :disabled="pagination.page >= pagination.total_pages" class="page-button">
                {{ t('tracker.nextPage') }} <i class="fas fa-chevron-right"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Tracker 列表视图 (默认显示) -->
        <div v-else class="tracker-list-view">
          <div class="tracker-list-header">
            <h4>{{ t('tracker.trackers') }} ({{ trackerList.length }})</h4>
            <button @click="toggleTrails" class="button-secondary map-trail-toggle-btn">
              <i :class="['fas', localShowTrails ? 'fa-eye-slash' : 'fa-eye']"></i> {{ localShowTrails ? t('tracker.hideTrails') : t('tracker.showTrails') }}
            </button>
          </div>
          <ul v-if="trackerList.length > 0">
            <li v-for="tracker in trackerList" :key="tracker.trackerId" class="tracker-item" :class="{ 'tracker-sos': tracker.sos === 1 }" @click="showTrackerAlarmRecords(tracker)">
              <strong>{{ tracker.trackerId }}</strong>
              
              <!-- SOS Status -->
              <div v-if="tracker.sos === 1" class="tracker-sos-status">
                {{ t('tracker.sosAlert') }}
                <div v-if="tracker.sos_happen" class="tracker-sos-time">
                  {{ new Date(tracker.sos_happen).toLocaleString() }}
                </div>
              </div>
              
              <!-- Position Data -->
              <div v-if="tracker.position && typeof tracker.position.x === 'number' && typeof tracker.position.y === 'number'" class="tracker-pos">
                X: {{ tracker.position.x.toFixed(2) }}, Y: {{ tracker.position.y.toFixed(2) }}
                <span v-if="tracker.position.accuracy && typeof tracker.position.accuracy === 'number'">, {{ t('tracker.accuracy') }}: {{ tracker.position.accuracy.toFixed(2) }}m</span>
              </div>
              <div v-else class="tracker-pos-na">
                {{ t('tracker.noPositionData') }}
              </div>

              <!-- Meta Data -->
              <div class="tracker-meta-group">
                <div v-if="tracker.timestamp" class="tracker-meta-item">
                   {{ t('tracker.lastSeen') }}: {{ new Date(tracker.timestamp).toLocaleTimeString() }}
                </div>
                <div v-if="tracker.last_detected_beacons && tracker.last_detected_beacons.length > 0" class="tracker-meta-item">
                  {{ t('tracker.strongestRssi') }}: {{ Math.max(...tracker.last_detected_beacons.map(b => b.rssi)) }} dBm
                  ({{ t('tracker.detected') }} {{ tracker.last_detected_beacons.length }} {{ t('tracker.beacons') }})
                </div>
                <div v-else-if="tracker.last_detected_beacons" class="tracker-meta-item">
                  {{ t('tracker.noBeaconsDetected') }}
                </div>
              </div>
            </li>
          </ul>
          <p v-else>{{ t('tracker.noTrackers') }}</p>
        </div>
      </aside>
    </div>
    
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, defineEmits, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import { loadTrackers } from '@/services/configApiService.js';

const { t } = useI18n();

const props = defineProps({
  config: {
    type: Object,
    default: null
  },
  trackers: {
    type: Array,
    default: () => []
  },
  initialShowTrails: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['trails-toggled']);

const mapCanvas = ref(null);

// 本地 tracker 状态 - 用于预加载数据
const localTrackers = ref({});
const isLoadingTrackers = ref(false);

// 合并 props trackers 和本地预加载的 trackers
const mergedTrackers = computed(() => {
    // 优先使用 props.trackers (WebSocket 实时数据)，如果没有则使用预加载的数据
    let trackersToUse = {};
    
    if (props.trackers && Object.keys(props.trackers).length > 0) {
        // 如果 props.trackers 有数据，使用它（WebSocket 实时数据）
        if (Array.isArray(props.trackers)) {
            // 如果是数组格式，转换为对象
            trackersToUse = props.trackers.reduce((acc, tracker) => {
                if (tracker.trackerId) {
                    acc[tracker.trackerId] = tracker;
                }
                return acc;
            }, {});
        } else {
            trackersToUse = props.trackers;
        }
    } else if (Object.keys(localTrackers.value).length > 0) {
        // 如果 props.trackers 没有数据，使用预加载的数据
        trackersToUse = localTrackers.value;
    }
    
    return trackersToUse;
});

// 过滤出属于当前地图的 trackers（基于 map 字段）
const filteredTrackers = computed(() => {
    const allTrackers = Object.values(mergedTrackers.value || {});

    if (!props.config?.map?.name || allTrackers.length === 0) {
        return [];
    }
    
    const result = allTrackers.filter(tracker => {
        // 首先基于 map 字段过滤
        if (props.config.map.name === tracker.map) {
            console.log(`[FilteredTrackers] ${props.config.map.name} 存在 tracker: ${tracker.trackerId}`);
            return true;
        } else {
            console.log(`[FilteredTrackers] ${props.config.map.name} 跳过 tracker: ${tracker.trackerId} (map字段不匹配: tracker.map=${tracker.map})`);
            return false;
        }
    });
    
    console.log(`[FilteredTrackers] 过滤结果数量: ${result.length}`);
    return result;
});

// 再次过滤：基于 beacon 检测的 trackers
const trackerList = computed(() => {
    return filteredTrackers.value.sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

// 获取有效的告警位置数据（用于在地图上显示）
const alarmLocations = computed(() => {
    if (!showAlarmPanel.value || !alarmRecords.value.length) {
        return [];
    }
    
    return alarmRecords.value
        .filter(record => 
            record.pos_type === 'bluetooth' && 
            record.loc && 
            typeof record.loc.x === 'number' && 
            typeof record.loc.y === 'number'
        )
        .map(record => ({
            x: record.loc.x,
            y: record.loc.y,
            sos: record.sos,
            timestamp: record.alarm_time,
            id: record.id
        }));
});
const canvasWidth = ref(600); // Default canvas width  
const canvasHeight = ref(450); // Default canvas height
const localShowTrails = ref(props.initialShowTrails); // Initialize with prop

// 告警记录相关状态
const showAlarmPanel = ref(false);
const selectedTracker = ref(null);
const alarmRecords = ref([]);
const isLoadingAlarms = ref(false);
const pagination = ref({
  page: 1,
  page_size: 10,
  total: 0,
  total_pages: 0
});

// 闪烁动画状态
const blinkingLocation = ref(null);
const isBlinking = ref(false);

// Watch for prop changes to update localShowTrails
watch(() => props.initialShowTrails, (newValue) => {
  localShowTrails.value = newValue;
});

const updateCanvasSize = () => {
  const mapContainer = mapCanvas.value?.parentElement;
  if (mapContainer) {
    const containerWidth = mapContainer.clientWidth;
    const containerHeight = mapContainer.clientHeight;
    
    // 计算可用空间，减少预留空间（因为隐藏了map-info）
    const availableWidth = Math.max(containerWidth - 20, 400); // 减少边距，最小宽度 400px
    const availableHeight = Math.max(containerHeight - 50, 300); // 减少上下元素空间，最小高度 300px
    
    // 直接使用可用空间，不强制固定宽高比
    canvasWidth.value = Math.floor(availableWidth);
    canvasHeight.value = Math.floor(availableHeight);
    
    // console.log(`[DEBUG] Canvas size updated:`, {
    //   containerWidth,
    //   containerHeight,
    //   availableWidth,
    //   availableHeight,
    //   canvasWidth: canvasWidth.value,
    //   canvasHeight: canvasHeight.value
    // });
  }
};

const toggleTrails = () => {
  localShowTrails.value = !localShowTrails.value;
  emit('trails-toggled', localShowTrails.value);
};

// 显示设备告警记录
const showTrackerAlarmRecords = async (tracker) => {
  selectedTracker.value = tracker;
  showAlarmPanel.value = true;
  await loadAlarmRecords(tracker.trackerId, 1);
};

// 关闭告警记录面板
const closeAlarmPanel = () => {
  showAlarmPanel.value = false;
  selectedTracker.value = null;
  alarmRecords.value = [];
  pagination.value = {
    page: 1,
    page_size: 10,
    total: 0,
    total_pages: 0
  };
};

// 加载告警记录
const loadAlarmRecords = async (deviceEui, page = 1) => {
  if (!deviceEui) return;
  
  isLoadingAlarms.value = true;
  
  try {
    const response = await axios.get('/api/list_alarm', {
      params: {
        device_eui: deviceEui,
        page: page,
        page_size: pagination.value.page_size,
        map_name: props.config?.map?.name || undefined
      }
    });
    
    if (response.data.code === 200) {
      alarmRecords.value = response.data.data.records || [];
      pagination.value = {
        page: response.data.data.pagination.page,
        page_size: response.data.data.pagination.page_size,
        total: response.data.data.pagination.total,
        total_pages: response.data.data.pagination.total_pages
      };
    } else {
      console.error('加载告警记录失败:', response.data.message);
      alarmRecords.value = [];
    }
  } catch (error) {
    console.error('加载告警记录出错:', error);
    alarmRecords.value = [];
  } finally {
    isLoadingAlarms.value = false;
  }
};

// 加载指定页码的告警记录
const loadAlarmPage = (page) => {
  if (page >= 1 && page <= pagination.value.total_pages && selectedTracker.value) {
    loadAlarmRecords(selectedTracker.value.trackerId, page);
  }
};

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return t('tracker.unknownTime');
  
  try {
    const date = new Date(dateTimeStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (error) {
    return t('tracker.timeFormatError');
  }
};

// 检查记录是否有蓝牙定位信息
const hasBluetoothLocation = (record) => {
  return record.pos_type === 'bluetooth' && 
         record.loc && 
         typeof record.loc.x === 'number' && 
         typeof record.loc.y === 'number';
};

// 在地图上显示告警位置并闪烁
const showAlarmLocationOnMap = (record) => {
  if (!hasBluetoothLocation(record)) {
    return;
  }
  
  // 设置闪烁位置信息
  blinkingLocation.value = {
    x: record.loc.x,
    y: record.loc.y,
    sos: record.sos,
    id: record.id,
    timestamp: record.alarm_time
  };
  
  // 开始闪烁动画
  isBlinking.value = true;
  
  // 3秒后停止闪烁
  setTimeout(() => {
    isBlinking.value = false;
    blinkingLocation.value = null;
  }, 3000);
};

// 预加载 tracker 数据的函数
const preloadTrackers = async () => {
  if (isLoadingTrackers.value) return;
  
  isLoadingTrackers.value = true;
  try {
    console.log('[MapPreview] Preloading trackers data from /api/trackers...');
    const trackersData = await loadTrackers();
    
    // 处理返回的数据格式
    if (trackersData) {
      if (Array.isArray(trackersData)) {
        // 如果是数组格式，转换为对象
        localTrackers.value = trackersData.reduce((acc, tracker) => {
          if (tracker.trackerId) {
            acc[tracker.trackerId] = tracker;
          }
          return acc;
        }, {});
      } else if (typeof trackersData === 'object') {
        // 如果是对象格式，直接使用
        localTrackers.value = trackersData;
      } else {
        localTrackers.value = {};
      }
      
      console.log(`[MapPreview] Successfully preloaded ${Object.keys(localTrackers.value).length} trackers`);
    } else {
      localTrackers.value = {};
      console.log('[MapPreview] No tracker data received from API');
    }
  } catch (error) {
    console.error('[MapPreview] Error preloading trackers:', error);
    localTrackers.value = {};
  } finally {
    isLoadingTrackers.value = false;
  }
};

const isTrackerInCurrentMap = (tracker) => {
  console.log(`[Beacon检测] 检查 tracker: ${tracker.trackerId}`);
  
  if (!props.config || !props.config.beacons) {
    console.log(`[Beacon检测] props.config 或 beacons 为空`);
    return true; // 临时改为 true，先让所有通过第一层过滤的 tracker 都显示
  }
  
  if (!tracker.last_detected_beacons) {
    console.log(`[Beacon检测] tracker ${tracker.trackerId} 没有 last_detected_beacons 数据`);
    return true; // 临时改为 true，如果没有 beacon 数据就直接显示
  }
  
  const mapBeacons = props.config.beacons;
  const trackerBeacons = tracker.last_detected_beacons;
  
  const result = trackerBeacons.some(trackerBeacon => {
    return mapBeacons.some(mapBeacon => {
      const match = mapBeacon.macAddress.replace(":", "").toLowerCase() === trackerBeacon.macAddress.replace(":", "").toLowerCase();
      if (match) {
        console.log(`[Beacon检测] 匹配成功: ${mapBeacon.macAddress} === ${trackerBeacon.macAddress}`);
      }
      return match;
    });
  });
  
  console.log(`[Beacon检测] tracker ${tracker.trackerId} 检测结果: ${result}`);
  return result;
};

const drawMap = (ctx) => {
  if (!props.config || !props.config.map || !ctx) {
    console.warn("[MapView] Attempted to drawMap without valid config.map data.");
    if (ctx) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    }
    return;
  }

  const { width: mapWidthMeters, height: mapHeightMeters, entities } = props.config.map;
  const beacons = props.config.beacons || [];
  
  // Calculate actual bounds of map data
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  entities.forEach(entity => {
    if (entity.points) {
      entity.points.forEach(point => {
        minX = Math.min(minX, point[0]);
        maxX = Math.max(maxX, point[0]);
        minY = Math.min(minY, point[1]);
        maxY = Math.max(maxY, point[1]);
      });
    }
  });
  
  // console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Data bounds:`, {
  //   minX, maxX, minY, maxY,
  //   dataWidth: maxX - minX,
  //   dataHeight: maxY - minY
  // });

  // Ensure canvas internal drawing buffer matches these dimensions.
  ctx.canvas.width = canvasWidth.value;
  ctx.canvas.height = canvasHeight.value;

  // Calculate the dimensions for the 80% content area
  const contentAreaWidth = canvasWidth.value * 0.9;
  const contentAreaHeight = canvasHeight.value * 0.9;

  // Use actual data bounds for scaling
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  
  // Calculate scale to fit map into the content area, maintaining aspect ratio
  let currentScale;
  if (dataWidth <= 0 || dataHeight <= 0) {
    // Avoid division by zero or negative scales if map dimensions are invalid
    currentScale = 1;
  } else {
    const scaleX = contentAreaWidth / dataWidth;
    const scaleY = contentAreaHeight / dataHeight;
    currentScale = Math.min(scaleX, scaleY);
  }

  // Prevent scale from being zero or negative if map dimensions are very large or contentArea is small
  if (currentScale <= 0) {
      currentScale = 1; // Fallback to a minimal positive scale
  }

  // Calculate the actual pixel dimensions of the scaled map content
  const renderedMapWidth = dataWidth * currentScale;
  const renderedMapHeight = dataHeight * currentScale;

  // Calculate offsets to center the scaled map content within the canvas
  const offsetX = (canvasWidth.value - renderedMapWidth) / 2;
  const offsetY = (canvasHeight.value - renderedMapHeight) / 2;
  
  // console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Canvas and offset values:`, {
  //   canvasWidth: canvasWidth.value,
  //   canvasHeight: canvasHeight.value,
  //   mapWidthMeters,
  //   mapHeightMeters,
  //   currentScale,
  //   renderedMapWidth,
  //   renderedMapHeight,
  //   offsetX,
  //   offsetY,
  //   translateX: offsetX,
  //   translateY: canvasHeight.value - offsetY
  // });
  
  // console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Entity count:`, entities.length);
  // if (entities.length > 0) {
  //   console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - First entity:`, entities[0]);
  // }

  // Clear canvas
  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);

  // --- Draw Map Entities ---
  ctx.save();
  // Translate to the bottom-left corner of the centered content box, then flip Y
  ctx.translate(offsetX, canvasHeight.value - offsetY);
  ctx.scale(1, -1);

  entities.forEach((entity, index) => {
    if (entity.type === 'polyline' && entity.points && entity.points.length > 0) {
      // if (index === 0) {
      //   console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - First entity points:`, entity.points.slice(0, 3));
      //   console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Scaled points:`, entity.points.slice(0, 3).map(p => [p[0] * currentScale, p[1] * currentScale]));
      // }
      
      ctx.beginPath();
      ctx.strokeStyle = entity.color || '#333333';
      // ctx.lineWidth = (entity.lineWidth || 1) / currentScale; // If line width is in world units
      ctx.lineWidth = entity.lineWidth || 1; // Assuming line width is in pixels

      const startPoint = entity.points[0];
      ctx.moveTo((startPoint[0] - minX) * currentScale, (startPoint[1] - minY) * currentScale);

      for (let i = 1; i < entity.points.length; i++) {
        ctx.lineTo((entity.points[i][0] - minX) * currentScale, (entity.points[i][1] - minY) * currentScale);
      }

      if (entity.closed) {
        ctx.closePath();
      }
      ctx.stroke();
    }
    // Add drawing logic for other entity types if needed (e.g., circles, rectangles)
  });

   // --- Draw Beacons ---
   beacons.forEach(beacon => {
    const beaconX = (beacon.x - minX) * currentScale;
    const beaconY = (beacon.y - minY) * currentScale;
    ctx.beginPath();
    ctx.arc(beaconX, beaconY, 5, 0, 2 * Math.PI); // Draw beacon as a small circle (radius 5px)
    ctx.fillStyle = 'orange';
    ctx.fill();
    ctx.fillStyle = 'black';
    ctx.font = '10px Arial';
     // Draw text upright despite flipped context
    ctx.save();
    ctx.translate(beaconX, beaconY);
    ctx.scale(1, -1); // Flip text back
    ctx.fillText(beacon.displayName || `B(${beacon.major},${beacon.minor})`, 8, 4);
    ctx.restore();
  });

   // --- Draw Trackers ---
   filteredTrackers.value.forEach(tracker => {
       if (tracker.position && tracker.position.x !== null && tracker.position.y !== null) {
           const trackerX = (tracker.position.x - minX) * currentScale;
           const trackerY = (tracker.position.y - minY) * currentScale;

           // Draw tracker circle with transparency
           ctx.beginPath();
           ctx.arc(trackerX, trackerY, 8, 0, 2 * Math.PI); // Slightly larger circle
           
           // Change color based on SOS status
           console.log(`[DEBUG] Tracker ${tracker.trackerId}: sos=${tracker.sos}, type=${typeof tracker.sos}, sos===1=${tracker.sos === 1}`);
           if (tracker.sos === 1) {
             ctx.fillStyle = 'rgba(255, 0, 0, 0.8)'; // Red with 80% opacity for SOS
             ctx.strokeStyle = 'rgba(220, 0, 0, 1)'; // Darker red border for SOS
             console.log(`[DEBUG] Drawing ${tracker.trackerId} as SOS (RED)`);
           } else {
             ctx.fillStyle = 'rgba(0, 123, 255, 0.7)'; // Blue with 70% opacity (normal)
             ctx.strokeStyle = 'rgba(0, 123, 255, 0.9)'; // Darker blue border (normal)
             console.log(`[DEBUG] Drawing ${tracker.trackerId} as NORMAL (BLUE)`);
           }
           
           ctx.fill();

           // Add border for better visibility
           ctx.lineWidth = 2;
           ctx.stroke();

           // Draw text to the right of the circle
           ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'; // Dark text with slight transparency
           ctx.font = 'bold 11px Arial';
           ctx.textAlign = 'left';
           ctx.textBaseline = 'middle';

           // Draw text upright despite flipped context
           ctx.save();
           ctx.translate(trackerX + 12, trackerY); // Position text to the right of circle
           ctx.scale(1, -1); // Flip text back
           ctx.fillText(tracker.trackerId.substring(10), 0, 0); // Show more chars
           ctx.restore();

           console.log(`tracker(${tracker.trackerId}) 绘制成功`)
         return
       }
       console.log(`tracker(${tracker.trackerId}) 绘制失败, 无定位信息`)
   });

  // --- Draw Alarm Locations (if alarm panel is open) ---
  if (showAlarmPanel.value && alarmLocations.value.length > 0) {
    alarmLocations.value.forEach(alarmLocation => {
      const alarmX = (alarmLocation.x - minX) * currentScale;
      const alarmY = (alarmLocation.y - minY) * currentScale;
      
      // Draw alarm location marker
      ctx.beginPath();
      ctx.arc(alarmX, alarmY, 12, 0, 2 * Math.PI); // Larger circle for alarm locations
      
      // Different colors for alarm vs recovery
      if (alarmLocation.sos === 1) {
        // SOS Alarm: Bright red with pulsing effect
        ctx.fillStyle = 'rgba(255, 0, 0, 0.8)';
        ctx.strokeStyle = 'rgba(139, 0, 0, 1)'; // Dark red border
      } else if (alarmLocation.sos === 0) {
        // Recovery: Green
        ctx.fillStyle = 'rgba(40, 167, 69, 0.8)';
        ctx.strokeStyle = 'rgba(25, 135, 84, 1)'; // Dark green border
      } else {
        // Other status: Orange
        ctx.fillStyle = 'rgba(255, 193, 7, 0.8)';
        ctx.strokeStyle = 'rgba(255, 153, 0, 1)'; // Dark orange border
      }
      
      ctx.fill();
      
      // Add thicker border for better visibility
      ctx.lineWidth = 3;
      ctx.stroke();
      
      // Add inner white circle for contrast
      ctx.beginPath();
      ctx.arc(alarmX, alarmY, 6, 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.fill();
      
      // Add small icon indicator
      ctx.beginPath();
      ctx.arc(alarmX, alarmY, 3, 0, 2 * Math.PI);
      if (alarmLocation.sos === 1) {
        ctx.fillStyle = '#dc3545'; // Red for alarm
      } else if (alarmLocation.sos === 0) {
        ctx.fillStyle = '#28a745'; // Green for recovery
      } else {
        ctx.fillStyle = '#ffc107'; // Yellow for other
      }
      ctx.fill();
    });
  }

  // --- Draw Blinking Alarm Location (最上层显示) ---
  if (isBlinking.value && blinkingLocation.value) {
    const blinkX = (blinkingLocation.value.x - minX) * currentScale;
    const blinkY = (blinkingLocation.value.y - minY) * currentScale;
    
    // 计算闪烁效果 (每400ms闪烁一次)
    const now = Date.now();
    const blinkCycle = 400; // 400ms per blink
    const blinkPhase = (now % blinkCycle) / blinkCycle;
    const isVisible = blinkPhase < 0.5; // 50% 占空比
    
    if (isVisible) {
      // 绘制大的闪烁圆圈
      ctx.beginPath();
      ctx.arc(blinkX, blinkY, 20, 0, 2 * Math.PI);
      
      // 根据SOS状态选择颜色
      if (blinkingLocation.value.sos === 1) {
        // SOS 告警：亮红色
        ctx.fillStyle = 'rgba(255, 59, 48, 0.7)';
        ctx.strokeStyle = 'rgba(255, 59, 48, 1)';
      } else if (blinkingLocation.value.sos === 0) {
        // 恢复：亮绿色
        ctx.fillStyle = 'rgba(52, 199, 89, 0.7)';
        ctx.strokeStyle = 'rgba(52, 199, 89, 1)';
      } else {
        // 其他状态：亮橙色
        ctx.fillStyle = 'rgba(255, 149, 0, 0.7)';
        ctx.strokeStyle = 'rgba(255, 149, 0, 1)';
      }
      
      ctx.fill();
      ctx.lineWidth = 4;
      ctx.stroke();
      
      // 内部白色圆圈增强对比度
      ctx.beginPath();
      ctx.arc(blinkX, blinkY, 12, 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.fill();
      
      // 中心图标
      ctx.beginPath();
      ctx.arc(blinkX, blinkY, 6, 0, 2 * Math.PI);
      if (blinkingLocation.value.sos === 1) {
        ctx.fillStyle = '#ff3b30';
      } else if (blinkingLocation.value.sos === 0) {
        ctx.fillStyle = '#34c759';
      } else {
        ctx.fillStyle = '#ff9500';
      }
      ctx.fill();
      
      // 外部光环效果
      ctx.beginPath();
      ctx.arc(blinkX, blinkY, 25, 0, 2 * Math.PI);
      ctx.strokeStyle = (blinkingLocation.value.sos === 1) ? 'rgba(255, 59, 48, 0.3)' :
                       (blinkingLocation.value.sos === 0) ? 'rgba(52, 199, 89, 0.3)' :
                                                          'rgba(255, 149, 0, 0.3)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  // --- Draw Tracker Trails (if enabled) ---
  if (localShowTrails.value) {
    filteredTrackers.value.forEach(tracker => {
      if (tracker.position_history && tracker.position_history.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(0, 0, 255, 0.3)'; // Light blue, semi-transparent
        ctx.lineWidth = 2; // Thinner than current tracker dot

        // Move to the oldest point in the history for this tracker
        const firstPoint = tracker.position_history[0];
        ctx.moveTo((firstPoint[0] - minX) * currentScale, (firstPoint[1] - minY) * currentScale);

        // Draw lines to subsequent points
        for (let i = 1; i < tracker.position_history.length; i++) {
          const point = tracker.position_history[i];
          ctx.lineTo((point[0] - minX) * currentScale, (point[1] - minY) * currentScale);
        }
        ctx.stroke();
      }
    });
  }

  ctx.restore(); // Restore original context state
};

let resizeHandler;

onMounted(async () => {
  // 预加载 tracker 数据
  await preloadTrackers();
  
  updateCanvasSize();
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) {
    drawMap(ctx);
  }
  
  // 监听窗口大小变化
  resizeHandler = () => {
    updateCanvasSize();
    const ctx = mapCanvas.value?.getContext('2d');
    if (ctx) {
      drawMap(ctx);
    }
  };
  window.addEventListener('resize', resizeHandler);
});

onUnmounted(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
  }
  
  // 清理动画帧
  if (animationFrame) {
    cancelAnimationFrame(animationFrame);
  }
});

// Watch for changes in config, trackers, trail visibility, or alarm panel and redraw
watch([() => props.config, () => props.trackers, mergedTrackers, localShowTrails, showAlarmPanel, alarmRecords, isBlinking], () => {
   const ctx = mapCanvas.value?.getContext('2d');
   if (ctx) {
       drawMap(ctx);
   }
}, { deep: true });

// 创建动画循环来持续重绘闪烁效果
let animationFrame;
const startBlinkingAnimation = () => {
  if (isBlinking.value) {
    const ctx = mapCanvas.value?.getContext('2d');
    if (ctx) {
      drawMap(ctx);
    }
    animationFrame = requestAnimationFrame(startBlinkingAnimation);
  }
};

// 监听闪烁状态变化
watch(isBlinking, (newValue) => {
  if (newValue) {
    startBlinkingAnimation();
  } else if (animationFrame) {
    cancelAnimationFrame(animationFrame);
  }
});

// 暴露方法给父组件使用
defineExpose({
  isTrackerInCurrentMap
});

</script>

<style scoped>
.map-preview-container {
  width: 100%;
}

.content-columns {
  display: flex;
  gap: 10px;
}

.map-view-wrapper {
  flex-grow: 1;
  min-height: 450px;
  display: flex;
  flex-direction: column;
}

/* Tracker 列表视图样式 */
.tracker-list-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tracker-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.map-container {
  position: relative;
  width: 100%;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.tracker-list-aside {
  width: 300px;
  flex-shrink: 0;
  background-color: #f9f9f9;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #eee;
  max-height: 500px;
  overflow-y: auto;
}

.tracker-list-aside h4 {
  margin: 0;
  color: #333;
}

.tracker-list-aside ul {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.tracker-item {
  padding: 8px;
  border-bottom: 1px solid #eee;
  font-size: 0.9em;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.tracker-item:hover {
  background-color: rgba(0, 123, 255, 0.05);
}

.tracker-item.tracker-sos {
  background-color: rgba(255, 0, 0, 0.1);
  border-left: 4px solid #ff0000;
}
.tracker-item:last-child {
  border-bottom: none;
}
.tracker-item strong {
  color: #0056b3; 
  display: block;
  margin-bottom: 3px;
}
.tracker-pos {
  color: #333;
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-pos-na {
  color: #777;
  font-style: italic;
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-meta-group {
  font-size: 0.85em;
  color: #555;
}
.tracker-meta-item {
  margin-top: 2px;
}

.tracker-sos-status {
  color: #ff0000;
  font-weight: bold;
  font-size: 0.9em;
  margin-bottom: 4px;
  padding: 2px 4px;
  background-color: rgba(255, 0, 0, 0.1);
  border-radius: 3px;
}

.tracker-sos-time {
  font-size: 0.8em;
  font-weight: normal;
  color: #666;
  margin-top: 2px;
}


.map-trail-toggle-btn {
  padding: 4px 8px;
  font-size: 0.75em;
  background-color: #fff;
  border: 1px solid #ccc;
  color: #333;
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}
.map-trail-toggle-btn:hover {
  background-color: #f0f0f0;
}

.map-info {
    position: absolute;
    top: 5px;
    left: 5px;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 5px 8px;
    border-radius: 3px;
    font-size: 0.85em;
    color: #666;
    border: 1px solid rgba(0, 0, 0, 0.1);
}
canvas {
    display: block; /* Prevents extra space below canvas */
    max-width: 100%;
    height: auto;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid #e3e6ea;
}

.loading-content i {
  font-size: 1.5rem;
  color: #667eea;
}

.loading-content span {
  color: #495057;
  font-size: 0.9rem;
}

/* 告警记录视图样式 (完全替换tracker列表) */
.alarm-records-view {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 1px solid #e3e6ea;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.alarm-view-header {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;
  gap: 1rem;
  position: relative;
  color: white;
}

.back-btn {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.alarm-icon {
  font-size: 1.5rem;
  color: #ffd700;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.title-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.title-content h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.device-id {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.8);
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
}

.alarm-view-body {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: white;
}

.loading-indicator {
  text-align: center;
  padding: 3rem 2rem;
  color: #6c757d;
}

.loading-indicator i {
  font-size: 2rem;
  margin-right: 0.75rem;
  color: #667eea;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.no-alarms {
  text-align: center;
  padding: 3rem 2rem;
  color: #6c757d;
}

.no-alarms i {
  font-size: 3rem;
  margin-bottom: 1.5rem;
  color: #28a745;
  opacity: 0.7;
}

.no-alarms p {
  margin: 0;
  font-size: 1rem;
  color: #495057;
}

.alarm-records-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.alarm-record-item {
  border: none;
  border-radius: 12px;
  padding: 1rem;
  background: white;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: relative;
  overflow: hidden;
}

.alarm-record-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #e9ecef;
  transition: all 0.3s ease;
}

.alarm-record-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.alarm-record-item.sos-alarm::before {
  background: linear-gradient(135deg, #ff6b6b 0%, #dc3545 100%);
}

.alarm-record-item.sos-recovery::before {
  background: linear-gradient(135deg, #51cf66 0%, #28a745 100%);
}

.alarm-record-item.clickable {
  cursor: pointer;
  position: relative;
}

.alarm-record-item.clickable::after {
  content: '';
  position: absolute;
  right: 1rem;
  top: 1rem;
  width: 0;
  height: 0;
  border-left: 8px solid #6c757d;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  opacity: 0.6;
  transition: all 0.3s ease;
}

.alarm-record-item.clickable:hover::after {
  opacity: 1;
  border-left-color: #495057;
  transform: translateX(3px);
}

.alarm-record-item.clickable:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.alarm-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.alarm-type {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
  font-size: 1.1rem;
  flex: 1;
}

.alarm-time-detail {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  font-size: 0.9rem;
  color: #495057;
}

.alarm-time-detail i {
  color: #6c757d;
  width: 18px;
  text-align: center;
  font-size: 1rem;
}

.alarm-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  font-size: 0.9rem;
  color: #495057;
}

.alarm-location,
.alarm-map,
.alarm-pos-type {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.alarm-location i {
  color: #dc3545;
  width: 18px;
  text-align: center;
  font-size: 1rem;
}

.alarm-map i {
  color: #28a745;
  width: 18px;
  text-align: center;
  font-size: 1rem;
}

.alarm-pos-type i {
  color: #17a2b8;
  width: 18px;
  text-align: center;
  font-size: 1rem;
}

.pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding: 1rem 0.5rem 0.5rem;
  border-top: 2px solid #f1f3f4;
  background: linear-gradient(to bottom, transparent 0%, #fafbfc 100%);
}

.page-button {
  padding: 0.5rem 1rem;
  border: 1px solid #e3e6ea;
  background: white;
  color: #495057;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.page-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: #667eea;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.page-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #f8f9fa;
  color: #adb5bd;
}

.page-info {
  font-size: 0.8rem;
  color: #6c757d;
  font-weight: 500;
  background: white;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  text-align: center;
}

@media (max-width: 768px) {
  .alarm-view-header {
    padding: 0.75rem;
    gap: 0.75rem;
  }
  
  .back-btn {
    width: 32px;
    height: 32px;
    font-size: 0.9rem;
  }
  
  .title-content h4 {
    font-size: 1rem;
  }
  
  .device-id {
    font-size: 0.8rem;
  }
  
  .alarm-view-body {
    padding: 0.75rem;
  }
  
  .alarm-record-item {
    padding: 0.75rem;
  }
  
  .alarm-header {
    margin-bottom: 0.375rem;
  }
  
  .alarm-type {
    font-size: 1rem;
  }
  
  .alarm-time-detail {
    padding: 0.375rem;
    gap: 0.5rem;
    font-size: 0.85rem;
  }
  
  .alarm-details {
    gap: 0.5rem;
  }
  
  .alarm-location,
  .alarm-map,
  .alarm-pos-type {
    padding: 0.375rem;
    gap: 0.5rem;
    font-size: 0.85rem;
  }
  
  .pagination-controls {
    flex-direction: column;
    gap: 0.75rem;
    padding: 0.75rem 0.25rem 0.25rem;
  }
  
  .page-button {
    width: 100%;
    justify-content: center;
    padding: 0.625rem 1rem;
  }
  
  .page-info {
    order: -1;
  }
}
</style>
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
        <!-- Tracker 列表视图 -->
        <div class="tracker-list-view">
          <div class="tracker-list-header">
            <h4>{{ t('tracker.trackers') }} ({{ trackerList.length }})</h4>
            <!-- Show Trails按钮暂时注释掉，以后需要时可以恢复 -->
            <!-- <button @click="toggleTrails" class="button-secondary map-trail-toggle-btn">
              <i :class="['fas', localShowTrails ? 'fa-eye-slash' : 'fa-eye']"></i> {{ localShowTrails ? t('tracker.hideTrails') : t('tracker.showTrails') }}
            </button> -->
          </div>
          <ul v-if="trackerList.length > 0">
            <li v-for="tracker in trackerList" :key="tracker.trackerId" class="tracker-item" :class="{ 'tracker-sos': tracker.sos === 1 }" @click="showAlarmHistoryModal(tracker)">
              <strong>{{ tracker.device_name || tracker.trackerId }}</strong>
              
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
              <div v-else-if="tracker.radius && tracker.last_detected_beacons && tracker.last_detected_beacons.length > 0" class="tracker-pos tracker-pos-area">
                {{ t('tracker.areaPositioning') }}: {{ t('tracker.radius') }} {{ tracker.radius.toFixed(2) }}m
                <div class="tracker-beacon-info">
                  {{ t('tracker.nearBeacon') }}: {{ tracker.last_detected_beacons[0].name || 'Unknown' }}
                  (X: {{ tracker.last_detected_beacons[0].configured_x?.toFixed(2) }}, Y: {{ tracker.last_detected_beacons[0].configured_y?.toFixed(2) }})
                </div>
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
<!--                  {{ t('tracker.strongestRssi') }}: {{ Math.max(...tracker.last_detected_beacons.map(b => b.rssi).filter(v => !isNaN(v))) }} dBm-->
<!--                  {{ t('tracker.strongestRssi') }}: {{ Math.max(...tracker.last_detected_beacons.map(b => b.rssi)) }} dBm-->
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
    
    <!-- 告警历史弹窗 -->
    <AlarmHistoryModal 
      :isVisible="showAlarmModal"
      :selectedTracker="selectedTrackerForAlarm"
      @close="closeAlarmModal"
    />
    
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, defineEmits, computed, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import httpClient from '@/utils/httpClient.js';
import { loadTrackers } from '@/services/configApiService.js';
import { API_ENDPOINTS } from '@/config/api.js';
import AlarmHistoryModal from '@/components/AlarmHistoryModal.vue';

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

// 地图背景图
const mapImage = ref(null);

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
        if (props.config.map.name === tracker.map) {
            return true;
        } else {
            return false;
        }
    });

    return result;
});

// 再次过滤：基于 beacon 检测的 trackers
const trackerList = computed(() => {
    return filteredTrackers.value.sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});

const canvasWidth = ref(600); // Default canvas width  
const canvasHeight = ref(450); // Default canvas height
const localShowTrails = ref(props.initialShowTrails); // Initialize with prop

// 告警历史弹窗相关状态
const showAlarmModal = ref(false);
const selectedTrackerForAlarm = ref(null);


// Watch for prop changes to update localShowTrails
watch(() => props.initialShowTrails, (newValue) => {
  localShowTrails.value = newValue;
});

// 这里只是通过地图的长宽比与容器的宽度高度, 计算画布尺寸, 并同步到全局变量
const updateCanvasSize = () => {
  const mapContainer = mapCanvas.value?.parentElement;
  if (!mapContainer || !props.config?.map) {
    // 如果没有配置，使用默认值
    canvasWidth.value = 600;
    canvasHeight.value = 450;
    return;
  }

  const containerWidth = mapContainer.clientWidth;
  const containerHeight = mapContainer.clientHeight;
  
  // 如果容器大小还没有渲染完成，使用默认值
  if (containerWidth === 0 || containerHeight === 0) {
    console.warn('[MapPreview] Container size is 0, using default canvas size');
    canvasWidth.value = 600;
    canvasHeight.value = 450;
    return;
  }
  
  // 获取地图宽高比
  const mapWidthMeters = props.config.map.width || 100;
  const mapHeightMeters = props.config.map.height || 100;
  const mapAspectRatio = mapWidthMeters / mapHeightMeters;
  
  // 根据地图宽高比和容器可用空间计算画布大小，保持地图宽高比
  const containerAspectRatio = containerWidth / containerHeight;
  
  if (mapAspectRatio > containerAspectRatio) {
    // 地图更宽，以宽度为准
    canvasWidth.value = Math.floor(containerWidth);
    canvasHeight.value = Math.floor(containerWidth / mapAspectRatio);
  } else {
    // 地图更高，以高度为准
    canvasHeight.value = Math.floor(containerHeight);
    canvasWidth.value = Math.floor(containerHeight * mapAspectRatio);
  }
  
  // 确保画布不会超出容器
  if (canvasWidth.value > containerWidth) {
    canvasWidth.value = Math.floor(containerWidth);
    canvasHeight.value = Math.floor(containerWidth / mapAspectRatio);
  }
  if (canvasHeight.value > containerHeight) {
    canvasHeight.value = Math.floor(containerHeight);
    canvasWidth.value = Math.floor(containerHeight * mapAspectRatio);
  }
  
  console.log(`[DEBUG] Canvas size updated:`, {
    containerWidth,
    containerHeight,
    mapAspectRatio: mapAspectRatio.toFixed(3),
    canvasWidth: canvasWidth.value,
    canvasHeight: canvasHeight.value
  });
};

const toggleTrails = () => {
  localShowTrails.value = !localShowTrails.value;
  emit('trails-toggled', localShowTrails.value);
};

// 显示告警历史弹窗
const showAlarmHistoryModal = (tracker) => {
  selectedTrackerForAlarm.value = tracker;
  showAlarmModal.value = true;
};

// 关闭告警历史弹窗
const closeAlarmModal = () => {
  showAlarmModal.value = false;
  selectedTrackerForAlarm.value = null;
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
  const canvas = ctx.canvas;
  const parentContainer = canvas.parentElement;
  const containerHeight = parentContainer.clientHeight;  // 内容高度（不含 padding）
  const containerWidth = parentContainer.clientWidth;
  let containerRatio =  containerWidth / containerHeight;


  if (!props.config || !props.config.map || !ctx) {
    console.warn("[MapView] Attempted to drawMap without valid config.map data.");
    if (ctx) {
        ctx.clearRect(0, 0, containerWidth, containerHeight);
    }
    return;
  }

  const { width: mapWidthMeters, height: mapHeightMeters } = props.config.map;
  let mapWidth = props.config.map.width
  let mapHeight = props.config.map.height
  let mapRatio = mapWidth / mapHeight


  let availableWidth = 0
  let availableHeight = 0

  if (containerRatio > mapRatio) {
    // 更矮胖, 直接使用容器高度
    availableHeight = containerHeight
    availableWidth = availableHeight * mapRatio
  } else {
    availableWidth = containerWidth
    availableHeight = availableWidth / mapRatio
  }
  console.log("容器比例: ", containerRatio, "地图比例: ", mapRatio)
  console.log("容器宽: ", containerWidth, "可用宽: ", availableWidth)
  console.log("容器高: ", containerHeight, "可用高: ", availableHeight)

  const beacons = props.config.beacons || [];
  
  // Calculate actual bounds of map data
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

  // 如果没有实体数据，使用地图配置的宽高
  if (minX === Infinity || maxX === -Infinity) {
    minX = 0;
    maxX = mapWidthMeters || 100;
    minY = 0;
    maxY = mapHeightMeters || 100;
  }

  // Ensure canvas internal drawing buffer matches these dimensions.
  // 确保画布大小有效
  if (containerWidth <= 0 || containerHeight <= 0) {
    console.log("容器尺寸无效，使用默认值")
    return;
  }
  
  // 只在画布尺寸真正改变时才设置，避免不必要的清空画布
  if (ctx.canvas.width !== containerWidth) {
    ctx.canvas.width = containerWidth;
  }
  if (ctx.canvas.height !== containerHeight) {
    ctx.canvas.height = containerHeight;
  }

  // Use actual data bounds for scaling
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  
  // Calculate scale to fit map into the canvas, maintaining aspect ratio
  // 画布直接按地图比例绘制，铺满整个画布
  let currentScale;
  if (dataWidth <= 0 || dataHeight <= 0) {
    // Avoid division by zero or negative scales if map dimensions are invalid
    currentScale = 1;
  } else {
    const scaleX = containerWidth / dataWidth;
    const scaleY = containerHeight / dataHeight;
    currentScale = Math.min(scaleX, scaleY);
  }

  // Prevent scale from being zero or negative if map dimensions are very large or canvas is small
  if (currentScale <= 0) {
      currentScale = 1; // Fallback to a minimal positive scale
  }

  // Clear canvas
  ctx.clearRect(0, 0, containerWidth, containerHeight);

  // --- Draw Map Background Image (先绘制背景图，不翻转Y轴) ---
  if (mapImage.value && mapImage.value.complete) {
    // 根据地图长宽比计算背景图尺寸：高度占满，宽度按比例拉伸
    const mapRatio = mapWidthMeters / mapHeightMeters;
    const bgImageHeight = containerHeight; // 高度占满
    const bgImageWidth = bgImageHeight * mapRatio; // 宽度根据地图长宽比拉伸
    
    // 计算居中位置
    const bgImageX = (containerWidth - bgImageWidth) / 2; // 水平居中
    const bgImageY = 0; // 从顶部开始（高度占满）
    
    // 绘制背景图（Canvas 默认坐标系，Y轴向下）
    ctx.drawImage(
      mapImage.value,
      0, 0, // 源图片起始位置
      mapImage.value.width, mapImage.value.height, // 源图片尺寸
      bgImageX, bgImageY, // 目标位置（居中，顶部对齐）
      bgImageWidth, bgImageHeight // 目标尺寸（高度占满，宽度按比例）
    );
  }

  // --- 翻转Y轴，让坐标系统变成数学坐标系（Y轴向上）用于绘制其他内容 ---
  ctx.save();
  // 先平移到画布底部，然后翻转Y轴
  ctx.translate(0, containerHeight);
  ctx.scale(1, -1);

  // --- Draw Map Entities (暂时注释掉，使用背景图) ---
  // entities.forEach((entity, index) => {
  //   if (entity.type === 'polyline' && entity.points && entity.points.length > 0) {
  //     ctx.beginPath();
  //     ctx.strokeStyle = entity.color || '#333333';
  //     ctx.lineWidth = entity.lineWidth || 1;

  //     const startPoint = entity.points[0];
  //     ctx.moveTo((startPoint[0] - minX) * currentScale, (startPoint[1] - minY) * currentScale);

  //     for (let i = 1; i < entity.points.length; i++) {
  //       ctx.lineTo((entity.points[i][0] - minX) * currentScale, (entity.points[i][1] - minY) * currentScale);
  //     }

  //     if (entity.closed) {
  //       ctx.closePath();
  //     }
  //     ctx.stroke();
  //   }
  // });

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
   // filteredTrackers.value.forEach(tracker => {
   //     console.log(`[DEBUG] 处理tracker: ${tracker.trackerId}, position:`, tracker.position, ', radius:', tracker.radius, ', last_detected_beacons:', tracker.last_detected_beacons?.length);
   //     if (tracker.position && tracker.position.x !== null && tracker.position.y !== null) {
   //         // 精确定位绘制
   //         const trackerX = (tracker.position.x - minX) * currentScale;
   //         const trackerY = (tracker.position.y - minY) * currentScale;
   //
   //         // Draw tracker circle with transparency
   //         ctx.beginPath();
   //         ctx.arc(trackerX, trackerY, 8, 0, 2 * Math.PI); // Slightly larger circle
   //
   //         // Change color based on SOS status
   //         console.log(`[DEBUG] Tracker ${tracker.trackerId}: sos=${tracker.sos}, type=${typeof tracker.sos}, sos===1=${tracker.sos === 1}`);
   //         if (tracker.sos === 1) {
   //           ctx.fillStyle = 'rgba(255, 0, 0, 0.8)'; // Red with 80% opacity for SOS
   //           ctx.strokeStyle = 'rgba(220, 0, 0, 1)'; // Darker red border for SOS
   //           console.log(`[DEBUG] Drawing ${tracker.trackerId} as SOS (RED)`);
   //         } else {
   //           ctx.fillStyle = 'rgba(0, 123, 255, 0.7)'; // Blue with 70% opacity (normal)
   //           ctx.strokeStyle = 'rgba(0, 123, 255, 0.9)'; // Darker blue border (normal)
   //           console.log(`[DEBUG] Drawing ${tracker.trackerId} as NORMAL (BLUE)`);
   //         }
   //
   //         ctx.fill();
   //
   //         // Add border for better visibility
   //         ctx.lineWidth = 2;
   //         ctx.stroke();
   //
   //         // Draw text to the right of the circle
   //         ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'; // Dark text with slight transparency
   //         ctx.font = 'bold 11px Arial';
   //         ctx.textAlign = 'left';
   //         ctx.textBaseline = 'middle';
   //
   //         // Draw text upright despite flipped context
   //         ctx.save();
   //         ctx.translate(trackerX + 12, trackerY); // Position text to the right of circle
   //         ctx.scale(1, -1); // Flip text back
   //         ctx.fillText(tracker.trackerId.substring(10), 0, 0); // Show more chars
   //         ctx.restore();
   //
   //         console.log(`tracker(${tracker.trackerId}) 绘制成功`)
   //       return
   //     } else if (tracker.radius && tracker.last_detected_beacons && tracker.last_detected_beacons.length > 0) {
   //         // 区域定位绘制
   //         const beacon = tracker.last_detected_beacons[0]; // 使用第一个检测到的beacon
   //         if (beacon.configured_x !== undefined && beacon.configured_y !== undefined) {
   //           const centerX = (beacon.configured_x - minX) * currentScale;
   //           const centerY = (beacon.configured_y - minY) * currentScale;
   //           const radius = tracker.radius * currentScale;
   //
   //           // 根据SOS状态绘制不同颜色的圆圈
   //           ctx.beginPath();
   //           ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
   //           if (tracker.sos === 1) {
   //             ctx.fillStyle = 'rgba(255, 182, 193, 0.3)'; // 浅红色，半透明
   //             ctx.strokeStyle = 'rgba(220, 53, 69, 0.6)'; // 深红色边框
   //           } else {
   //             ctx.fillStyle = 'rgba(144, 238, 144, 0.3)'; // 浅绿色，半透明
   //             ctx.strokeStyle = 'rgba(34, 139, 34, 0.6)'; // 深绿色边框
   //           }
   //           ctx.lineWidth = 2;
   //           ctx.fill();
   //           ctx.stroke();
   //
   //           // 在圆圈内显示tracker ID的后5位
   //           const trackerId = tracker.trackerId;
   //           const displayId = trackerId.length > 5 ? trackerId.substring(trackerId.length - 5) : trackerId;
   //
   //           ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'; // 黑色文字
   //           ctx.font = 'bold 14px Arial';
   //           ctx.textAlign = 'center';
   //           ctx.textBaseline = 'middle';
   //
   //           // Draw text upright despite flipped context
   //           ctx.save();
   //           ctx.translate(centerX, centerY);
   //           ctx.scale(1, -1); // Flip text back
   //           ctx.fillText(displayId, 0, 0);
   //           ctx.restore();
   //
   //           console.log(`tracker(${tracker.trackerId}) 区域定位绘制成功, radius: ${tracker.radius}, center: (${beacon.configured_x}, ${beacon.configured_y})`);
   //           return;
   //         }
   //     }
   //     console.log(`tracker(${tracker.trackerId}) 绘制失败, 无定位信息`)
   // });


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

// 加载地图背景图的函数
const loadMapBackgroundImage = () => {
  if (!props.config?.map?.background) {
    console.warn('[MapPreview] No background image URL in config');
    mapImage.value = null;
    // 即使没有背景图，也继续绘制其他内容（beacons, trackers等）
    const ctx = mapCanvas.value?.getContext('2d');
    if (ctx) {
      drawMap(ctx);
    }
    return;
  }

  const img = new Image();
  img.crossOrigin = 'anonymous'; // 允许跨域加载图片
  
  img.onload = () => {
    mapImage.value = img;
    console.log('[MapPreview] Background image loaded successfully:', props.config.map.background);
    // 图片加载完成后重新绘制
    const ctx = mapCanvas.value?.getContext('2d');
    if (ctx) {
      drawMap(ctx);
    }
  };
  
  img.onerror = (error) => {
    console.error('[MapPreview] Failed to load map background image:', props.config.map.background, error);
    mapImage.value = null;
    // 即使图片加载失败，也继续绘制其他内容
    const ctx = mapCanvas.value?.getContext('2d');
    if (ctx) {
      drawMap(ctx);
    }
  };
  
  img.src = props.config.map.background;
};

onMounted(async () => {
  // 加载地图背景图
  loadMapBackgroundImage();
  
  // 预加载 tracker 数据
  await preloadTrackers();
  
  // 等待 DOM 渲染完成后再计算画布大小
  await nextTick();

  // todo 这里是延迟渲染, 但此处的问题是重新渲染会造成图片丢失
  // 使用 setTimeout 确保容器已经渲染完成
  // setTimeout(() => {
  //   updateCanvasSize();
  //   const ctx = mapCanvas.value?.getContext('2d');
  //   if (ctx) {
  //     console.log("开始绘图")
  //     drawMap(ctx);
  //   }
  // }, 100);
  
  // 监听窗口大小变化
  resizeHandler = () => {
    // updateCanvasSize();
    // const ctx = mapCanvas.value?.getContext('2d');
    // if (ctx) {
    //   drawMap(ctx);
    // }
  };

  // todo size 变化时
  // window.addEventListener('resize', resizeHandler);
});

onUnmounted(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
  }
  
});

// Watch for changes in background image URL
watch(() => props.config?.map?.background, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl && newUrl) {
    console.log('[MapPreview] Background image URL changed, reloading...', { old: oldUrl, new: newUrl });
    loadMapBackgroundImage();
  }
});

// // todo 地图宽度变更
// watch(() => props.config?.map?.width, () => {
//   updateCanvasSize();
//   const ctx = mapCanvas.value?.getContext('2d');
//   if (ctx) {
//     drawMap(ctx);
//   }
// });

// todo 地图高度变更
// watch(() => props.config?.map?.height, () => {
//   updateCanvasSize();
//   const ctx = mapCanvas.value?.getContext('2d');
//   if (ctx) {
//     drawMap(ctx);
//   }
// });

// todo 地图/tracker之类的数据更新, 是否重新绘制
// watch([() => props.config, () => props.trackers, mergedTrackers, localShowTrails], () => {
//    // 如果 config 变化，可能需要重新计算画布大小
//    if (props.config?.map) {
//      updateCanvasSize();
//    }
//    const ctx = mapCanvas.value?.getContext('2d');
//    if (ctx) {
//        drawMap(ctx);
//    }
// }, { deep: true });


// 暴露方法给父组件使用
defineExpose({
  isTrackerInCurrentMap
});

</script>

<style scoped>
/* 规则1: 只有最外层容器有 flex-grow: 1 */
.map-preview-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.content-columns {
  display: flex;
  gap: 10px;
  flex: 1;
  min-height: 0; /* 允许 flex 子元素收缩 */
}

/* 规则1: 只有这一个 flex-grow: 1 */
.map-view-wrapper {
  flex-grow: 1;
  min-height: 0; /* 允许 flex 子元素收缩 */
  display: flex;
  flex-direction: column;
}

/* 规则3: 使用 position:relative + width/height:100% */
.map-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;           /* 添加：flexbox 布局 */
  justify-content: center; /* 添加：水平居中 */
  align-items: center;     /* 添加：垂直居中 */
  box-sizing: border-box;
}

/* Canvas 的显示尺寸由 width/height 属性控制，不铺满父容器 */
canvas {
  display: block;
  /* 移除 width: 100% 和 height: 100%，让 canvas 根据 width/height 属性显示 */
  /* Canvas 的显示尺寸会等于它的 width/height 属性值 */
}

.tracker-list-aside {
  width: 300px;
  flex-shrink: 0;
  background-color: #f9f9f9;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #eee;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许 flex 子元素收缩 */
  overflow: hidden; /* 由子元素控制滚动 */
}

/* 规则5: 父容器负责布局，子容器只负责内容 */
/* Tracker 列表视图样式 */
.tracker-list-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto; /* 内容溢出时滚动 */
  min-height: 0; /* 允许 flex 子元素收缩 */
}

.tracker-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-shrink: 0; /* 头部不收缩 */
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
.tracker-pos-area {
  color: #28a745;
  background-color: rgba(40, 167, 69, 0.1);
  padding: 4px 6px;
  border-radius: 4px;
  border-left: 3px solid #28a745;
}
.tracker-beacon-info {
  font-size: 0.85em;
  color: #666;
  margin-top: 2px;
  font-style: italic;
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

</style>
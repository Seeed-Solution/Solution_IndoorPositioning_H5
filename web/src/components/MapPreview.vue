<!-- web/src/components/MapPreview.vue -->
<template>
  <div class="map-preview-container">
    <div class="content-columns">
      <div class="map-view-wrapper">
        <div class="map-container">
          <canvas
            ref="mapCanvas"
            :width="canvasWidth"
            :height="canvasHeight"
            :class="{ 'is-interactive': interactive, 'is-panning': isPanning }"
            style="border: 1px solid #ccc;"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointercancel="onPointerUp"
            @pointerleave="onPointerLeave"
            @wheel.prevent="onWheel"
            @dblclick="onDoubleClick"
          ></canvas>
          <!-- Tooltip 用 DOM 浮层, 不画进 canvas: 文字缩放不失真, 也能选中复制 -->
          <div
            v-if="interactive && tooltip"
            class="canvas-tooltip"
            :style="{ left: tooltip.left + 'px', top: tooltip.top + 'px' }"
          >
            <div class="canvas-tooltip__name">{{ tooltip.name }}</div>
            <div class="canvas-tooltip__row">{{ tooltip.status }}</div>
            <div class="canvas-tooltip__row">{{ tooltip.source }}</div>
            <div class="canvas-tooltip__row">{{ tooltip.time }}</div>
          </div>
          <div v-if="interactive" class="canvas-zoom-controls">
            <button type="button" @click="zoomButton(1.25)" title="Zoom in"><i class="fas fa-plus"></i></button>
            <button type="button" @click="zoomButton(0.8)" title="Zoom out"><i class="fas fa-minus"></i></button>
            <button type="button" @click="resetZoom" title="Reset view"><i class="fas fa-compress"></i></button>
          </div>
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
      <aside v-if="!interactive" class="tracker-list-aside">
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
<!--              <div v-if="tracker && typeof tracker.x === 'number' && typeof tracker.y === 'number'" class="tracker-pos">-->
              <div v-if="tracker && typeof tracker.x === 'number' && typeof tracker.y === 'number' && tracker.type === 'calculation'" class="tracker-pos">
                X: {{ tracker.x.toFixed(2) }}, Y: {{ tracker.y.toFixed(2) }}
                <span v-if="tracker.accuracy && typeof tracker.accuracy === 'number'">, {{ t('tracker.accuracy') }}: {{ tracker.accuracy.toFixed(2) }}m</span>
              </div>
              <div v-else-if="tracker.radius && tracker.used_beacons && tracker.used_beacons.length > 0" class="tracker-pos tracker-pos-area">
                {{ t('tracker.areaPositioning') }}: {{ t('tracker.radius') }} {{ tracker.radius.toFixed(2) }}m
                <div class="tracker-beacon-info">
                  {{ t('tracker.nearBeacon') }}: {{ tracker.used_beacons[0].name || 'Unknown' }}
                  (X: {{ tracker.used_beacons[0].configured_x?.toFixed(2) }}, Y: {{ tracker.used_beacons[0].configured_y?.toFixed(2) }})
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
                <div v-if="tracker.used_beacons && tracker.used_beacons.length > 0" class="tracker-meta-item">
                  {{ t('tracker.strongestRssi') }}: {{ Math.max(...tracker.used_beacons.map(b => b.rssi)) }} dBm
<!--                  {{ t('tracker.strongestRssi') }}: {{ Math.max(...tracker.used_beacons.map(b => b.rssi).filter(v => !isNaN(v))) }} dBm-->
<!--                  {{ t('tracker.strongestRssi') }}: {{ Math.max(...tracker.used_beacons.map(b => b.rssi)) }} dBm-->
                  ({{ t('tracker.detected') }} {{ tracker.used_beacons.length }} {{ t('tracker.beacons') }})
                </div>
                <div v-else-if="tracker.used_beacons" class="tracker-meta-item">
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
import { indoorSegments } from '@/utils/trail.js';
import {
  applyView,
  canvasToWorld,
  clampZoom,
  cssRadiusToCanvas,
  cssToCanvasPoint,
  fitTransform,
  hitTest,
  panBy,
  resetView,
  worldToCanvas,
  zoomAt,
} from '@/utils/canvasTransform.js';
import { fitAllView, toBasePoint, viewChangedEnough } from '@/utils/displayCamera.js';
import { ref, onMounted, onUnmounted, watch, defineEmits, computed, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { loadTrackers } from '@/services/configApiService.js';
import { API_ENDPOINTS, buildImageUrl } from '@/config/api.js';
import AlarmHistoryModal from '@/components/AlarmHistoryModal.vue';

const { t } = useI18n();

const props = defineProps({
  config: {
    type: Object,
    default: null
  },
  trackers: {
    type: [Array, Object],
    default: () => []
  },
  initialShowTrails: {
    type: Boolean,
    default: false
  },
  // 受控轨迹开关: 传了就以它为准（/map 的共享开关），不传沿用 initialShowTrails
  showTrails: {
    type: Boolean,
    default: null
  },
  // 交互模式: 命中检测 / zoom-pan / tooltip / 选中态。旧页面不传, 行为不变。
  interactive: {
    type: Boolean,
    default: false
  },
  selectedId: {
    type: String,
    default: ''
  },
  hoveredId: {
    type: String,
    default: ''
  },
  // 展示模式: 标签显示设备名并放大到远距离可读（spec §9.2, >=16 px）
  displayMode: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['trails-toggled', 'select-tracker', 'hover-tracker']);

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
const trailsVisible = computed(
  () => (props.showTrails === null ? localShowTrails.value : props.showTrails),
);

// 视图叠加变换 {zoom, panX, panY}: 命中和绘制共用, 见 utils/canvasTransform.js
const view = ref(resetView());
const isPanning = ref(false);
const tooltip = ref(null);
// 每次绘制记录 tracker 在 canvas backing 空间的中心与命中半径
let hitTargets = [];
let panOrigin = null;
let pointerMoved = false;

// 告警历史弹窗相关状态
const showAlarmModal = ref(false);
const selectedTrackerForAlarm = ref(null);


// Watch for prop changes to update localShowTrails
watch(() => props.initialShowTrails, (newValue) => {
  localShowTrails.value = newValue;
});

// 换地图就复位视图, 否则上一张图的缩放会带到新图上
watch(() => props.config?.map?.name, () => {
  view.value = resetView();
  tooltip.value = null;
});

const updateCanvasSize = () => {
  const mapContainer = mapCanvas.value?.parentElement;
  if (mapContainer) {
    const containerWidth = mapContainer.clientWidth;
    const containerHeight = mapContainer.clientHeight;

    // 计算可用空间，减少预留空间（因为隐藏了map-info）
    // 不再给 canvas 兜 400px 最小宽度: 那是窄屏横向溢出的直接来源。
    const availableWidth = Math.max(containerWidth - 20, 1);
    const availableHeight = Math.max(containerHeight - 50, 200);

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

  if (!tracker.used_beacons) {
    console.log(`[Beacon检测] tracker ${tracker.trackerId} 没有 used_beacons 数据`);
    return true; // 临时改为 true，如果没有 beacon 数据就直接显示
  }

  const mapBeacons = props.config.beacons;
  const trackerBeacons = tracker.used_beacons;

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

const isValidNumber = (value) => {
  return typeof value === 'number' && !isNaN(value);
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
  // 优先从地图配置中获取边界值，如果没有则使用默认值
  let minX, maxX, minY, maxY;
  
  if (isValidNumber(props.config.map.minX)) {
    minX = props.config.map.minX;
  } else {
    minX = 0;
  }

  if (isValidNumber(props.config.map.maxX)) {
    maxX = props.config.map.maxX;
  } else {
    maxX = mapWidthMeters;
  }

  if (isValidNumber(props.config.map.minY)) {
    minY = props.config.map.minY;
  } else {
    minY = 0;
  }

  if (isValidNumber(props.config.map.maxY)) {
    maxY = props.config.map.maxY;
  } else {
    maxY = mapHeightMeters;
  }

  // Ensure canvas internal drawing buffer matches these dimensions.
  // 只在真的变了才写: 给 canvas.width 赋值（哪怕是同一个数）会重建整个
  // backing buffer, 拖动时每帧重来一次没必要, 后面的 clearRect 已经够了。
  if (ctx.canvas.width !== canvasWidth.value) ctx.canvas.width = canvasWidth.value;
  if (ctx.canvas.height !== canvasHeight.value) ctx.canvas.height = canvasHeight.value;

  const hasImage = !!(mapImage.value && mapImage.value.complete && mapImage.value.height);
  const imageAspect = hasImage ? (mapImage.value.width / mapImage.value.height) : null;

  // 贴合变换 + 视图叠加: 绘制与命中检测共用同一个 t
  const base = fitTransform({
    minX, minY, maxX, maxY,
    canvasWidth: canvasWidth.value,
    canvasHeight: canvasHeight.value,
    padding: 0.9,
    imageAspect,
  });
  const t = applyView(base, view.value);
  const z = clampZoom(view.value.zoom);
  const toPx = (x, y) => worldToCanvas(t, x, y);

  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);

  // --- Draw Map Background Image ---
  if (hasImage) {
    const imgHeight = (maxY - minY) * base.scale * z;
    const imgWidth = imgHeight * imageAspect;
    ctx.drawImage(
      mapImage.value,
      0, 0, mapImage.value.width, mapImage.value.height,
      base.originX * z + view.value.panX,
      base.originY * z + view.value.panY,
      imgWidth, imgHeight,
    );
  }

  // --- Draw Beacons ---
  beacons.forEach((beacon) => {
    const p = toPx(beacon.x, beacon.y);
    ctx.beginPath();
    ctx.arc(p.x, p.y, 5, 0, 2 * Math.PI);
    ctx.fillStyle = 'orange';
    ctx.fill();
    ctx.fillStyle = 'black';
    ctx.font = '10px Arial';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(beacon.displayName || `B(${beacon.major},${beacon.minor})`, p.x + 8, p.y);
  });

  // --- Draw Tracker Trails (轨迹先画, 当前点和选中环压在上面) ---
  if (trailsVisible.value) {
    filteredTrackers.value.forEach((tracker) => {
      // 统一时间轴按坐标系切段: 这里只画室内 (metric) 段。
      // 室外 (wgs84) 段由 OutdoorMapView 的 Leaflet 图层负责,
      // 段与段之间不连线, 所以进出楼的切换点不会被画成一条直线。
      indoorSegments(tracker.position_history).forEach((segment) => {
        if (segment.points.length < 2) return;
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(0, 0, 255, 0.3)';
        ctx.lineWidth = 2;
        const first = toPx(segment.points[0].x, segment.points[0].y);
        ctx.moveTo(first.x, first.y);
        for (let i = 1; i < segment.points.length; i += 1) {
          const pt = toPx(segment.points[i].x, segment.points[i].y);
          ctx.lineTo(pt.x, pt.y);
        }
        ctx.stroke();
      });
    });
  }

  // --- Draw Trackers ---
  const targets = [];
  const selected = props.interactive ? props.selectedId : '';
  const hovered = props.interactive ? props.hoveredId : '';

  filteredTrackers.value.forEach((tracker) => {
    const id = tracker.trackerId;
    const isSelected = !!selected && id === selected;
    const isHovered = !!hovered && id === hovered;
    // 有选中时其余降到 40% 透明度; SOS 仍保留红色语义, 只是变淡。
    const dim = props.interactive && !!selected && !isSelected;
    ctx.save();
    if (dim) ctx.globalAlpha = 0.4;

    if (tracker && tracker.x !== null && tracker.y !== null && tracker.type === 'calculation') {
      const p = toPx(tracker.x, tracker.y);
      const radius = (isSelected ? 8 * 1.4 : 8) * (isHovered ? 1.15 : 1);
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, 2 * Math.PI);
      if (tracker.sos === 1) {
        ctx.fillStyle = 'rgba(255, 0, 0, 0.8)';
        ctx.strokeStyle = 'rgba(220, 0, 0, 1)';
      } else {
        ctx.fillStyle = 'rgba(0, 123, 255, 0.7)';
        ctx.strokeStyle = 'rgba(0, 123, 255, 0.9)';
      }
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.stroke();

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius + 4, 0, 2 * Math.PI);
        ctx.lineWidth = 2;
        ctx.strokeStyle = tracker.sos === 1 ? '#d93025' : '#1a73e8';
        ctx.stroke();
      }

      ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
      ctx.font = props.displayMode ? 'bold 18px Arial' : 'bold 11px Arial';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(
        props.displayMode ? (tracker.device_name || String(id)) : String(id).substring(10),
        p.x + radius + 4,
        p.y,
      );

      targets.push({ id, x: p.x, y: p.y, hitRadius: radius });
    } else if (tracker.radius && tracker.used_beacons && tracker.used_beacons.length > 0) {
      const beacon = tracker.used_beacons[0];
      if (beacon.configured_x !== undefined && beacon.configured_y !== undefined) {
        const c = toPx(beacon.configured_x, beacon.configured_y);
        const radius = tracker.radius * t.k;
        ctx.beginPath();
        ctx.arc(c.x, c.y, radius, 0, 2 * Math.PI);
        if (tracker.sos === 1) {
          ctx.fillStyle = 'rgba(255, 182, 193, 0.3)';
          ctx.strokeStyle = 'rgba(220, 53, 69, 0.6)';
        } else {
          ctx.fillStyle = 'rgba(144, 238, 144, 0.3)';
          ctx.strokeStyle = 'rgba(34, 139, 34, 0.6)';
        }
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.fill();
        ctx.stroke();

        const displayId = props.displayMode
          ? (tracker.device_name || String(id))
          : (String(id).length > 5 ? String(id).slice(-5) : String(id));
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        ctx.font = props.displayMode ? 'bold 18px Arial' : 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(displayId, c.x, c.y);

        // 区域圆只把圆心附近算成命中目标: 用整个半径的话一个大圆会盖住整张图
        targets.push({ id, x: c.x, y: c.y, hitRadius: 10 });
      }
    }
    ctx.restore();
  });

  hitTargets = targets;
};

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
  
  // 构建完整的图片URL（如果是相对路径，则拼接当前页面的协议+域名）
  img.src = buildImageUrl(props.config.map.background);
};

// --------------------------------------------------------------------------- //
// 指针交互: 命中检测 / zoom-pan / tooltip
// --------------------------------------------------------------------------- //
const HIT_TOLERANCE_CSS = 12;   // spec: 12 CSS px
const DRAG_THRESHOLD_CSS = 4;

const redraw = () => {
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) drawMap(ctx);
};

const canvasPointFromEvent = (event) => {
  const el = mapCanvas.value;
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  return {
    point: cssToCanvasPoint(rect, el.width, el.height, event.clientX, event.clientY),
    tolerance: cssRadiusToCanvas(rect, el.width, el.height, HIT_TOLERANCE_CSS),
    rect,
  };
};

const pickTracker = (event) => {
  const ctx = canvasPointFromEvent(event);
  if (!ctx) return null;
  return hitTest(hitTargets, ctx.point, ctx.tolerance);
};

const trackerById = (id) => filteredTrackers.value.find((tr) => tr.trackerId === id) || null;

const statusLabel = (tracker) => {
  if (tracker?.online === 'online') return t('tracker.trackerList.online');
  if (tracker?.online === 'offline') return t('tracker.trackerList.offline');
  if (tracker?.online === 'unknown') return t('common.unknown');
  return tracker?.sos === 1 ? t('tracker.sosAlert') : t('common.unknown');
};

const sourceLabel = (tracker) => {
  if (tracker?.type === 'approximate') return 'Indoor · BLE';
  if (tracker?.type === 'calculation') return 'Indoor · Calculated';
  return `Indoor · ${tracker?.type || 'unknown'}`;
};

const updateTooltip = (id, event) => {
  const tracker = trackerById(id);
  if (!tracker || !mapCanvas.value) {
    tooltip.value = null;
    return;
  }
  const rect = mapCanvas.value.getBoundingClientRect();
  tooltip.value = {
    left: event.clientX - rect.left + 14,
    top: event.clientY - rect.top + 14,
    name: tracker.device_name || tracker.trackerId,
    status: statusLabel(tracker),
    source: sourceLabel(tracker),
    time: tracker.timestamp ? new Date(tracker.timestamp).toLocaleString() : '—',
  };
};

const onPointerDown = (event) => {
  if (!props.interactive) return;
  // 只认第一根手指 / 主指针与鼠标左键: 双指时第二个 pointerdown 会把 panOrigin
  // 挪到新触点上, 画面直接跳一段; 右键同理不该开始平移。
  if (panOrigin || event.isPrimary === false) return;
  if (event.pointerType === 'mouse' && event.button !== 0) return;
  pointerMoved = false;
  panOrigin = {
    id: event.pointerId, x: event.clientX, y: event.clientY, view: { ...view.value },
  };
  mapCanvas.value?.setPointerCapture?.(event.pointerId);
};

const onPointerMove = (event) => {
  if (!props.interactive) return;
  if (panOrigin) {
    if (panOrigin.id !== event.pointerId) return;
    const dx = event.clientX - panOrigin.x;
    const dy = event.clientY - panOrigin.y;
    if (!pointerMoved && Math.hypot(dx, dy) > DRAG_THRESHOLD_CSS) pointerMoved = true;
    if (pointerMoved) {
      isPanning.value = true;
      const el = mapCanvas.value;
      const rect = el.getBoundingClientRect();
      const sx = el.width / Math.max(rect.width, 1);
      const sy = el.height / Math.max(rect.height, 1);
      view.value = panBy(panOrigin.view, dx * sx, dy * sy);
      tooltip.value = null;
      redraw();
      return;
    }
  }
  const id = pickTracker(event);
  emit('hover-tracker', id);
  if (id) updateTooltip(id, event);
  else tooltip.value = null;
};

const onPointerUp = (event) => {
  if (!props.interactive) return;
  // 没被 pointerdown 认领的指针（第二根手指、右键）不参与选中与平移收尾
  if (!panOrigin || panOrigin.id !== event.pointerId) return;
  mapCanvas.value?.releasePointerCapture?.(event.pointerId);
  const wasDrag = pointerMoved;
  panOrigin = null;
  pointerMoved = false;
  isPanning.value = false;
  if (wasDrag) return;
  const id = pickTracker(event);
  if (id) emit('select-tracker', id);
};

const onPointerLeave = () => {
  if (!props.interactive) return;
  panOrigin = null;
  pointerMoved = false;
  isPanning.value = false;
  tooltip.value = null;
  emit('hover-tracker', null);
};

const onWheel = (event) => {
  if (!props.interactive) return;
  const ctx = canvasPointFromEvent(event);
  if (!ctx) return;
  const factor = event.deltaY < 0 ? 1.15 : 1 / 1.15;
  view.value = zoomAt(view.value, ctx.point, factor);
  tooltip.value = null;
  redraw();
};

const zoomButton = (factor) => {
  const el = mapCanvas.value;
  if (!el) return;
  view.value = zoomAt(view.value, { x: el.width / 2, y: el.height / 2 }, factor);
  redraw();
};

const resetZoom = () => {
  view.value = resetView();
  redraw();
};

const onDoubleClick = () => {
  if (!props.interactive) return;
  resetZoom();
};

/** 把某个 tracker 挪到画布中心（不改缩放）。/map 的 focusTracker 走这里。 */
const focusTracker = (id) => {
  const tracker = trackerById(id);
  const el = mapCanvas.value;
  if (!tracker || !el) return false;
  const target = hitTargets.find((h) => h.id === id);
  if (!target) return false;
  view.value = panBy(view.value, el.width / 2 - target.x, el.height / 2 - target.y);
  redraw();
  return true;
};

/**
 * fit-all：把当前平面图上所有 tracker 一并框进画布（展示模式相机）。
 *
 * hitTargets 是上一帧「带着当前 view」的 canvas 坐标，先反解回 base 空间再算，
 * 这样连续调用不会自我放大。差异小于抖动阈值时不动，返回 false。
 */
const fitAllTrackers = ({ paddingRatio, jitterRatio } = {}) => {
  const el = mapCanvas.value;
  if (!el || hitTargets.length === 0) return false;
  const points = hitTargets.map((h) => toBasePoint(h, view.value));
  const next = fitAllView({
    points,
    viewWidth: el.width,
    viewHeight: el.height,
    paddingRatio,
  });
  if (!next) return false;
  if (!viewChangedEnough(view.value, next, {
    viewWidth: el.width, viewHeight: el.height, jitterRatio,
  })) return false;
  view.value = next;
  redraw();
  return true;
};

let resizeHandler;
let containerObserver = null;

// 等待组件初始化完成的方法（用于父组件等待布局计算完成）
const waitForReady = async () => {
  // 等待 Vue DOM 更新
  await nextTick();
  
  // 等待浏览器布局计算完成（使用双重 requestAnimationFrame 确保布局计算完成）
  await new Promise(resolve => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        // 强制触发布局计算，确保容器尺寸已计算
        const mapContainer = mapCanvas.value?.parentElement;
        if (mapContainer) {
          void mapContainer.offsetHeight; // 强制 reflow
        }
        resolve();
      });
    });
  });
  
  // 确保 updateCanvasSize 能获取到正确的容器尺寸
  updateCanvasSize();
  
  // 再次等待布局计算完成，确保 canvas 尺寸已更新
  await new Promise(resolve => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        resolve();
      });
    });
  });
};

onMounted(async () => {
  // 加载地图背景图
  loadMapBackgroundImage();
  
  // 预加载 tracker 数据
  await preloadTrackers();

  // 等待布局计算完成后再更新 canvas 尺寸
  await waitForReady();
  
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) {
    drawMap(ctx);
  }

  // 监听窗口大小变化
  resizeHandler = () => {
    updateCanvasSize();
    // 使用 nextTick 等待 Vue 更新 DOM（canvas 的 width/height 属性）后再绘制
    nextTick(() => {
      const ctx = mapCanvas.value?.getContext('2d');
      if (ctx) {
        drawMap(ctx);
      }
    });
  };
  window.addEventListener('resize', resizeHandler);

  // 侧栏折叠、drawer 开合都改容器宽度但不发 window resize
  if (typeof ResizeObserver !== 'undefined' && mapCanvas.value?.parentElement) {
    containerObserver = new ResizeObserver(() => resizeHandler());
    containerObserver.observe(mapCanvas.value.parentElement);
  }
});

onUnmounted(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
  }
  if (containerObserver) {
    containerObserver.disconnect();
    containerObserver = null;
  }
});

// Watch for changes in background image URL
watch(() => props.config?.map?.background, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl && newUrl) {
    console.log('[MapPreview] Background image URL changed, reloading...', { old: oldUrl, new: newUrl });
    loadMapBackgroundImage();
  }
});

// Watch for changes in config, trackers, trail visibility and redraw
// mergedTrackers 已经派生自 props.trackers, 不必再单独订阅一次。
watch([
  () => props.config,
  mergedTrackers,
  trailsVisible,
  () => props.selectedId,
  () => props.hoveredId,
  () => props.displayMode,
], () => {
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) {
    drawMap(ctx);
  }
}, { deep: true });


// 暴露方法给父组件使用
defineExpose({
  isTrackerInCurrentMap,
  waitForReady,
  focusTracker,
  fitAllTrackers,
  resetZoom,
});

</script>

<style scoped>
.map-preview-container {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.content-columns {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.map-view-wrapper {
  flex: 1 1 320px;
  min-width: 0;
  min-height: 320px;
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
  min-width: 0;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

/* 溢出根因 4: 300px 定宽且 flex-shrink:0, 窄屏必然顶出容器 */
.tracker-list-aside {
  flex: 1 1 260px;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  background-color: var(--sc-color-bg-layout);
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #eee;
  max-height: 500px;
  overflow-y: auto;
}

.tracker-list-aside h4 {
  margin: 0;
  color: var(--sc-color-text);
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
  color: var(--sc-color-info);
  display: block;
  margin-bottom: 3px;
}
.tracker-pos {
  color: var(--sc-color-text);
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-pos-area {
  color: var(--sc-color-success);
  background-color: rgba(40, 167, 69, 0.1);
  padding: 4px 6px;
  border-radius: 4px;
  border-left: 3px solid var(--sc-color-success);
}
.tracker-beacon-info {
  font-size: 0.85em;
  color: var(--sc-color-text-secondary);
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
  color: var(--sc-color-text-secondary);
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
  color: var(--sc-color-text-secondary);
  margin-top: 2px;
}


.map-trail-toggle-btn {
  padding: 4px 8px;
  font-size: 0.75em;
  background-color: #fff;
  border: 1px solid var(--sc-color-border);
  color: var(--sc-color-text);
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
    color: var(--sc-color-text-secondary);
    border: 1px solid rgba(0, 0, 0, 0.1);
}
canvas {
    display: block; /* Prevents extra space below canvas */
    max-width: 100%;
    height: auto;
}

canvas.is-interactive {
  cursor: crosshair;
  touch-action: none;
}

canvas.is-panning {
  cursor: grabbing;
}

.canvas-tooltip {
  position: absolute;
  z-index: 900;
  pointer-events: none;
  max-width: 220px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(32, 33, 36, 0.92);
  color: #fff;
  font-size: 12px;
  line-height: 1.4;
}

.canvas-tooltip__name {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-tooltip__row {
  color: rgba(255, 255, 255, 0.8);
}

.canvas-zoom-controls {
  position: absolute;
  right: 10px;
  bottom: 10px;
  z-index: 800;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.canvas-zoom-controls button {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--sc-color-border);
  border-radius: 4px;
  background: #fff;
  color: var(--sc-color-text);
  cursor: pointer;
  box-shadow: none;
}

.canvas-zoom-controls button:hover {
  border-color: var(--sc-color-primary);
  color: var(--sc-color-primary);
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
  color: var(--sc-color-primary);
}

.loading-content span {
  color: var(--sc-color-text);
  font-size: 0.9rem;
}


.pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding: 1rem 0.5rem 0.5rem;
  border-top: 2px solid var(--sc-color-bg-layout);
  background: linear-gradient(to bottom, transparent 0%, var(--sc-color-bg-container) 100%);
}

.page-button {
  padding: 0.5rem 1rem;
  border: 1px solid #e3e6ea;
  background: white;
  color: var(--sc-color-text);
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
  background: var(--sc-color-primary);
  color: white;
  border-color: var(--sc-color-primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.page-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: var(--sc-color-bg-layout);
  color: var(--sc-color-text-tertiary);
}

.page-info {
  font-size: 0.8rem;
  color: var(--sc-color-text-secondary);
  font-weight: 500;
  background: white;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--sc-color-border);
  text-align: center;
}

</style>
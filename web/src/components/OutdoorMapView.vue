<!-- web/src/components/OutdoorMapView.vue
     室内外统一追踪视图。底图默认 OSM, 瓦片 URL / 署名 / 坐标制均由
     dashboard_config.json 的 outdoor 段配置。每个 tracker 的 metric 历史段
     (按配准投影) 与 wgs84 历史段同图共存, 只在坐标系切换点断线; 只有
     "当前点" marker 的样式按 tracker 当下是否室外二选一。 -->
<template>
  <div class="outdoor-map-view">
    <div class="outdoor-toolbar">
      <label class="tile-select-label">
        {{ t('outdoorMap.tileSource') || 'Base map' }}
        <select v-model="activeSourceId" class="tile-select">
          <option v-for="src in tileSources" :key="src.id" :value="src.id">{{ src.name }}</option>
        </select>
      </label>
      <label v-if="!interactive" class="trail-toggle">
        <input type="checkbox" v-model="localShowTrails" />
        {{ t('outdoorMap.showTrails') || 'Show trails' }}
      </label>
      <span v-if="activeSource && activeSource.gcj02Correction" class="gcj-warning">
        {{ t('outdoorMap.gcj02Notice')
          || 'Tiles use GCJ-02; device fixes are WGS84. Offset correction is not applied.' }}
      </span>
      <button
        v-if="registrableMaps.length > 0"
        class="reg-toggle"
        :class="{ active: regActive }"
        @click="regActive ? cancelRegistration() : startRegistration()"
      >
        {{ regActive
          ? (t('outdoorMap.registration.exit') || 'Exit registration')
          : (t('outdoorMap.registration.enter') || 'Align floor plan') }}
      </button>
      <span class="tracker-count">{{ outdoorTrackers.length }}</span>
    </div>

    <!-- 配准控件放在地图上方的工具条里, 不做侧栏: MapOverview 的容器本身
         就比 1280 视口宽, 侧栏会被裁掉。 -->
    <div v-if="regActive" class="registration-bar">
      <span class="reg-title">{{ t('outdoorMap.registration.title') || 'Floor plan registration' }}</span>

      <label class="reg-field">
        <span>{{ t('outdoorMap.registration.map') || 'Floor plan' }}</span>
        <select v-model="regMapName" @change="onRegMapChange">
          <option v-for="m in registrableMaps" :key="m.map.name" :value="m.map.name">
            {{ m.map.name }}
          </option>
        </select>
      </label>

      <div class="reg-modes">
        <button v-for="m in REG_MODES" :key="m"
                :class="{ active: regMode === m }"
                @click="setRegMode(m)">
          {{ t(`outdoorMap.registration.mode.${m}`) || m }}
        </button>
      </div>

      <label class="reg-field narrow">
        <span>{{ t('outdoorMap.registration.originLat') || 'Origin latitude' }}</span>
        <input type="number" step="0.0000001" v-model.number="regForm.origin_lat"
               @change="applyFormToOverlay" />
      </label>
      <label class="reg-field narrow">
        <span>{{ t('outdoorMap.registration.originLon') || 'Origin longitude' }}</span>
        <input type="number" step="0.0000001" v-model.number="regForm.origin_lon"
               @change="applyFormToOverlay" />
      </label>
      <label class="reg-field narrow">
        <span>{{ t('outdoorMap.registration.rotation') || 'Rotation (deg, CW from north)' }}</span>
        <input type="number" step="0.01" v-model.number="regForm.rotation_deg"
               @change="applyFormToOverlay" />
      </label>
      <label class="reg-field narrow">
        <span>{{ t('outdoorMap.registration.scale') || 'Scale' }}</span>
        <input type="number" step="0.0001" min="0.0001" v-model.number="regForm.scale"
               @change="applyFormToOverlay" />
      </label>

      <div class="reg-actions">
        <button class="primary" :disabled="regSaving" @click="saveRegistration">
          {{ t('common.save') || 'Save' }}
        </button>
        <button :disabled="regSaving" @click="resetRegistration">
          {{ t('common.reset') || 'Reset' }}
        </button>
        <button :disabled="regSaving" @click="cancelRegistration">
          {{ t('common.cancel') || 'Cancel' }}
        </button>
      </div>

      <p class="reg-hint">
        {{ t('outdoorMap.registration.aspectLocked')
          || 'Aspect ratio is locked: only drag, rotate and uniform scale are available.' }}
      </p>
      <p v-if="regError" class="reg-error">{{ regError }}</p>
      <p v-if="regStatus" class="reg-status">{{ regStatus }}</p>
    </div>

    <div class="outdoor-body">
      <div ref="mapEl" class="outdoor-map-container"></div>
    </div>

    <div v-if="outdoorTrackers.length === 0" class="outdoor-empty">
      {{ t('outdoorMap.noOutdoorTrackers') || 'No tracker reporting a GNSS fix.' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { normalizeOutdoorConfig, TILE_KIND_PMTILES } from '@/config/outdoor.js';
import { isOutdoorTracker } from '@/utils/trail.js';
import { buildIndoorPolylines, buildOutdoorPolylines } from '@/utils/renderPlan.js';
import {
  localToWgs84,
  isRegistered,
  imageFootprintLocal,
  cornersFromRegistration,
  registrationFromCorners,
  initialRegistration,
  validateRegistration,
} from '@/utils/affine.js';
import { buildImageUrl } from '@/config/api.js';
import { saveMapRegistration } from '@/services/configApiService.js';

const { t } = useI18n();

const props = defineProps({
  // { [trackerId]: trackerState }, 或数组
  trackers: { type: [Object, Array], default: () => ({}) },
  // dashboard_config.json 的 outdoor 段, 缺失时自动补 OSM
  outdoor: { type: Object, default: null },
  initialShowTrails: { type: Boolean, default: true },
  // 受控轨迹开关（/map 的共享开关）。null 表示沿用组件自身的 initialShowTrails。
  showTrails: { type: Boolean, default: null },
  // 交互模式: marker registry + 选中/悬停联动，由页面级 controller 驱动
  interactive: { type: Boolean, default: false },
  selectedId: { type: String, default: '' },
  hoveredId: { type: String, default: '' },
  // dashboard_config.json 的 maps 数组, 配准模式需要地图米数与背景图。
  maps: { type: Array, default: () => [] },
});

const emit = defineEmits(['registration-saved', 'select-tracker', 'hover-tracker']);

const mapEl = ref(null);
const localShowTrails = ref(props.initialShowTrails);
const showTrails = computed(
  () => (props.showTrails === null ? localShowTrails.value : props.showTrails),
);

/** id -> circleMarker。focusTracker / 选中态都靠它，不重建整层。 */
const markerRegistry = new Map();

const outdoorConfig = computed(() => normalizeOutdoorConfig(props.outdoor));
const tileSources = computed(() => outdoorConfig.value.tileSources);
const activeSourceId = ref(outdoorConfig.value.defaultSource);
const activeSource = computed(
  () => tileSources.value.find((s) => s.id === activeSourceId.value) || tileSources.value[0],
);

const allTrackers = computed(
  () => (Array.isArray(props.trackers) ? props.trackers : Object.values(props.trackers || {})),
);

const outdoorTrackers = computed(() => allTrackers.value.filter(isOutdoorTracker));

/** 已配准的平面图: 名字 -> registration。未配准的地图不进这张图。 */
const registrationByMap = computed(() => {
  const byName = {};
  (props.maps || []).forEach((entry) => {
    if (entry?.map?.name && isRegistered(entry.map)) {
      byName[entry.map.name] = entry.map.registration;
    }
  });
  return byName;
});

/** 米制点 -> [lat, lon]，地图未配准或坐标非法返回 null。 */
const projectMetric = (x, y, mapName) => {
  const reg = registrationByMap.value[mapName];
  if (!reg) return null;
  const px = Number(x);
  const py = Number(y);
  if (!Number.isFinite(px) || !Number.isFinite(py)) return null;
  try {
    const p = localToWgs84(px, py, reg);
    return [p.lat, p.lon];
  } catch (err) {
    return null;
  }
};

let map = null;
let tileLayer = null;
let overlay = null;
let hasFitted = false;

const trackerLatLng = (tracker) => {
  const lat = Number(tracker.lat ?? tracker.position?.lat);
  const lon = Number(tracker.lon ?? tracker.position?.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return [lat, lon];
};

const applyTileLayer = async () => {
  if (!map || !activeSource.value) return;
  if (tileLayer) map.removeLayer(tileLayer);
  const src = activeSource.value;
  if (src.kind === TILE_KIND_PMTILES) {
    // 离线归档: protomaps-leaflet 直接对 .pmtiles 发 HTTP Range 请求。
    // 归档缺失时不要把整张图打崩, 回落到栅格源。
    try {
      const { leafletLayer } = await import('protomaps-leaflet');
      tileLayer = leafletLayer({
        url: src.url,
        attribution: src.attribution,
        maxDataZoom: src.maxZoom || 18,
      }).addTo(map);
      return;
    } catch (err) {
      console.error('[OutdoorMapView] PMTiles layer failed, falling back to raster:', err);
      const fallback = tileSources.value.find((s) => s.kind !== TILE_KIND_PMTILES);
      if (!fallback) return;
      activeSourceId.value = fallback.id;
      return;
    }
  }
  const options = { attribution: src.attribution, maxZoom: src.maxZoom || 19 };
  if (src.subdomains) options.subdomains = src.subdomains;
  tileLayer = L.tileLayer(src.url, options).addTo(map);
};

const redraw = () => {
  if (!map) return;
  if (overlay) map.removeLayer(overlay);
  overlay = L.layerGroup().addTo(map);
  markerRegistry.clear();

  const bounds = [];
  const selected = props.interactive ? props.selectedId : '';
  const hovered = props.interactive ? props.hoveredId : '';

  /** 选中/悬停/淡出三态在两类当前点 marker 上是同一套, 只有基础半径不同。 */
  const markerState = (tracker, baseRadius) => {
    const isSelected = !!selected && tracker.trackerId === selected;
    const isHovered = !!hovered && tracker.trackerId === hovered;
    const dim = !!selected && !isSelected;
    return {
      radius: (isSelected ? baseRadius * 1.4 : baseRadius) * (isHovered ? 1.15 : 1),
      fillOpacity: dim ? 0.4 : 0.9,
      opacity: dim ? 0.4 : 1,
      weight: isSelected ? 4 : 2,
    };
  };

  /** 当前点 marker 统一在这里登记并绑事件, 室内投影点和室外 GNSS 点都走它。 */
  const registerMarker = (marker, tracker) => {
    const id = tracker.trackerId;
    if (!id) return marker;
    markerRegistry.set(id, marker);
    if (props.interactive) {
      marker.on('click', () => emit('select-tracker', id));
      marker.on('mouseover', () => emit('hover-tracker', id));
      marker.on('mouseout', () => emit('hover-tracker', null));
    }
    return marker;
  };

  // 每个 tracker 无条件画两类历史段: metric 段按配准投影, wgs84 段原样连线。
  // 两类互不依赖 tracker 的"当前"状态, 只有当前点 marker 的样式才按
  // isOutdoorTracker(tracker) 二选一 —— 这样同一设备在切换过坐标系之后,
  // 室内/室外历史段能同图共存, 只在切换点断线。
  allTrackers.value.forEach((tracker) => {
    if (showTrails.value) {
      buildIndoorPolylines(tracker, projectMetric).forEach((run) => {
        run.forEach((pt) => bounds.push(pt));
        L.polyline(run, {
          color: '#188038', weight: 2, opacity: 0.45, dashArray: '4,4',
        }).addTo(overlay);
      });
      buildOutdoorPolylines(tracker).forEach((line) => {
        line.forEach((pt) => bounds.push(pt));
        L.polyline(line, { color: '#1a73e8', weight: 2, opacity: 0.45 }).addTo(overlay);
      });
    }

    const isSos = tracker.sos === 1;
    if (isOutdoorTracker(tracker)) {
      const latlng = trackerLatLng(tracker);
      if (!latlng) return;
      bounds.push(latlng);

      registerMarker(L.circleMarker(latlng, {
        ...markerState(tracker, 7),
        color: isSos ? '#d93025' : '#1a73e8',
        fillColor: isSos ? '#d93025' : '#1a73e8',
      })
        .bindTooltip(tracker.device_name || tracker.trackerId, { permanent: false })
        .addTo(overlay), tracker);

      // 精度圈
      const accuracy = Number(tracker.accuracy ?? tracker.position?.accuracy);
      if (Number.isFinite(accuracy) && accuracy > 0) {
        L.circle(latlng, {
          radius: accuracy,
          color: '#1a73e8',
          weight: 1,
          opacity: 0.4,
          fillOpacity: 0.08,
        }).addTo(overlay);
      }
    } else {
      const latlng = projectMetric(tracker.x, tracker.y, tracker.map);
      if (!latlng) return;
      bounds.push(latlng);

      registerMarker(L.circleMarker(latlng, {
        ...markerState(tracker, 6),
        color: isSos ? '#d93025' : '#188038',
        fillColor: '#ffffff',
        dashArray: '3,2',
      })
        .bindTooltip(`${tracker.device_name || tracker.trackerId} · ${tracker.map}`,
          { permanent: false })
        .addTo(overlay), tracker);
    }
  });

  if (bounds.length > 0 && !hasFitted) {
    map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40], maxZoom: 18 });
    hasFitted = true;
  }
};

// --------------------------------------------------------------------------- //
// 配准模式
// --------------------------------------------------------------------------- //
// 只开放 drag / rotate / scale: 不加 DistortAction 与 FreeRotateAction, 四角
// 始终保持相似变换, 宽高比自然被锁住, 逆解也只需要一条边。
const REG_MODES = ['drag', 'rotate', 'scale'];

const regActive = ref(false);
const regMapName = ref('');
const regMode = ref('drag');
const regSaving = ref(false);
const regError = ref('');
const regStatus = ref('');
const regForm = ref({ origin_lat: 0, origin_lon: 0, rotation_deg: 0, scale: 1 });

let regOverlay = null;       // L.DistortableImageOverlay
let regFootprint = null;     // 背景图在局部米制坐标里的落位
let regInitial = null;       // 进入配准时的初值, 供"重置"回退
let regSyncing = false;      // 防止 setCorners -> update -> setCorners 回环

const registrableMaps = computed(
  () => (props.maps || []).filter((m) => m?.map?.name && m?.map?.background),
);

const currentRegMap = computed(
  () => registrableMaps.value.find((m) => m.map.name === regMapName.value) || null,
);

const loadImageSize = (url) => new Promise((resolve, reject) => {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
  img.onerror = () => reject(new Error(`failed to load ${url}`));
  img.src = url;
});

const destroyRegOverlay = () => {
  if (regOverlay && map) {
    try { map.removeLayer(regOverlay); } catch (err) { /* already gone */ }
  }
  regOverlay = null;
};

/** 四角 -> 表单三参数（+ 原点）。 */
const syncFormFromOverlay = () => {
  if (!regOverlay || !regFootprint || regSyncing) return;
  try {
    const reg = registrationFromCorners(regFootprint, regOverlay.getCorners());
    regForm.value = {
      origin_lat: reg.origin_lat,
      origin_lon: reg.origin_lon,
      rotation_deg: reg.rotation_deg,
      scale: reg.scale,
    };
    regError.value = '';
  } catch (err) {
    regError.value = err.message;
  }
};

/**
 * 表单三参数 -> 四角。
 *
 * 侧栏改经纬度会把图片挪到别处, 视野不跟过去的话屏幕上就只剩底图。
 * 因此表单驱动的改动一律把视野带到图片上; 拖拽/旋转驱动的 'update'
 * 不走这里, 视野不动。
 */
const applyFormToOverlay = (recenter = true) => {
  if (!regOverlay || !regFootprint) return;
  try {
    validateRegistration(regForm.value);
    const corners = cornersFromRegistration(regFootprint, regForm.value)
      .map((c) => L.latLng(c.lat, c.lon));
    regSyncing = true;
    regOverlay.setCorners(corners);
    regError.value = '';
    if (recenter && map) {
      map.fitBounds(L.latLngBounds(corners), { padding: [60, 60], maxZoom: 20 });
    }
  } catch (err) {
    regError.value = err.message;
  } finally {
    regSyncing = false;
  }
};

const setRegMode = (mode) => {
  regMode.value = mode;
  applyRegMode();
};

/**
 * 把当前模式推给插件。
 *
 * 两个时序坑：editing 句柄要等 `editing.enable()` 建好 `_modes`，
 * rotate/scale 句柄还要读图片元素的 matrix3d transform（`getAngle`），
 * 图片没渲染就调会抛 `reading 'slice'`。所以只在两者都就绪时才切，
 * 否则记住模式，等 overlay 的 load + 一个 tick 之后由 load 回调重试。
 */
const applyRegMode = () => {
  const edit = regOverlay?.editing;
  if (!edit?.setMode || !edit._modes || !regOverlay._image) return false;
  try {
    edit.setMode(regMode.value);
    return true;
  } catch (err) {
    console.warn('[OutdoorMapView] setMode failed:', err.message);
    return false;
  }
};

const mountRegOverlay = async () => {
  destroyRegOverlay();
  regError.value = '';
  regStatus.value = '';
  const entry = currentRegMap.value;
  if (!entry || !map) return;

  const url = buildImageUrl(entry.map.background);
  let size;
  try {
    size = await loadImageSize(url);
  } catch (err) {
    regError.value = t('outdoorMap.registration.imageLoadFailed')
      || `Cannot load floor plan image: ${entry.map.background}`;
    return;
  }
  regFootprint = imageFootprintLocal(entry.map, size.width, size.height);

  // 已有配准就从它起步, 否则用当前视图中心 + 正北 + scale 1 做初猜。
  let start = entry.map.registration || null;
  try {
    if (start) validateRegistration(start);
  } catch (err) {
    start = null;
  }
  if (!start) {
    const c = map.getCenter();
    start = initialRegistration(regFootprint, c.lat, c.lng);
  }
  regInitial = { ...start };
  regForm.value = {
    origin_lat: start.origin_lat,
    origin_lon: start.origin_lon,
    rotation_deg: start.rotation_deg ?? 0,
    scale: start.scale ?? 1,
  };

  const corners = cornersFromRegistration(regFootprint, regForm.value)
    .map((c) => L.latLng(c.lat, c.lon));

  try {
    // 插件是 UMD, 只往全局 L 上挂 DragAction/RotateAction/ScaleAction。
    // Leaflet 这里是 ESM import, window.L 不会自动存在, 得先补上。
    if (typeof window !== 'undefined' && !window.L) window.L = L;
    // vendor.js 提供 L.Toolbar2, 主 bundle 在模块求值期就要用它, 必须先加载。
    await import('leaflet-distortableimage/dist/vendor.css');
    await import('leaflet-distortableimage/dist/vendor.js');
    await import('leaflet-distortableimage/dist/leaflet.distortableimage.css');
    await import('leaflet-distortableimage/dist/leaflet.distortableimage.js');
  } catch (err) {
    regError.value = `leaflet-distortableimage failed to load: ${err.message}`;
    return;
  }

  const LD = (typeof window !== 'undefined' && window.L) ? window.L : L;
  if (!LD.DragAction || !LD.RotateAction || !LD.ScaleAction) {
    regError.value = 'leaflet-distortableimage actions are unavailable';
    return;
  }
  regOverlay = LD.distortableImageOverlay(url, {
    corners,
    // 不含 DistortAction / FreeRotateAction: 宽高比锁死。
    actions: [LD.DragAction, LD.RotateAction, LD.ScaleAction],
    mode: regMode.value,
    editable: true,
    suppressToolbar: true,
    opacity: 0.7,
  });
  map.addLayer(regOverlay);
  regOverlay.on('update', syncFormFromOverlay);
  regOverlay.once('load', () => {
    const corners = regOverlay.getCorners();
    console.info('[OutdoorMapView] registration overlay loaded:', url,
      `${size.width}x${size.height}px`,
      `corners=${corners.length}`,
      `nw=${corners[0].lat.toFixed(6)},${corners[0].lng.toFixed(6)}`);
    // editing 句柄可能还没建好, 让出一个 tick 再切模式。
    if (!applyRegMode()) setTimeout(applyRegMode, 0);
  });
  map.fitBounds(L.latLngBounds(corners), { padding: [60, 60], maxZoom: 20 });
};

const startRegistration = async () => {
  if (registrableMaps.value.length === 0) return;
  regActive.value = true;
  if (!currentRegMap.value) regMapName.value = registrableMaps.value[0].map.name;
  await nextTick();
  await mountRegOverlay();
};

const onRegMapChange = async () => {
  await mountRegOverlay();
};

const resetRegistration = () => {
  if (!regInitial) return;
  regForm.value = {
    origin_lat: regInitial.origin_lat,
    origin_lon: regInitial.origin_lon,
    rotation_deg: regInitial.rotation_deg ?? 0,
    scale: regInitial.scale ?? 1,
  };
  regStatus.value = '';
  applyFormToOverlay();
};

const cancelRegistration = () => {
  // 取消: 丢弃草稿, 不发请求, 不动 props.maps。
  destroyRegOverlay();
  regFootprint = null;
  regInitial = null;
  regActive.value = false;
  regError.value = '';
  regStatus.value = '';
};

const saveRegistration = async () => {
  const entry = currentRegMap.value;
  if (!entry) return;
  regError.value = '';
  regStatus.value = '';
  let payload;
  try {
    validateRegistration(regForm.value);
    payload = {
      origin_lat: Number(regForm.value.origin_lat),
      origin_lon: Number(regForm.value.origin_lon),
      rotation_deg: Number(regForm.value.rotation_deg),
      scale: Number(regForm.value.scale),
    };
  } catch (err) {
    regError.value = err.message;
    return;
  }
  regSaving.value = true;
  try {
    await saveMapRegistration(entry.map.name, payload);
    // 本地也更新一份, 保存后立刻能按配准渲染, 不用等重新拉配置。
    entry.map.registration = { ...payload };
    regInitial = { ...payload };
    regStatus.value = t('outdoorMap.registration.saved') || 'Registration saved.';
    emit('registration-saved', { mapName: entry.map.name, registration: { ...payload } });
    redraw();
  } catch (err) {
    regError.value = err.message;
  } finally {
    regSaving.value = false;
  }
};

/**
 * 把某个 tracker 居中。用 flyTo / panTo，不复用只跑一次的初始 fitBounds ——
 * fitBounds 会把整层重新框一遍，用户手动调过的缩放全丢。
 */
const focusTracker = (id) => {
  const marker = markerRegistry.get(id);
  if (!marker || !map) return false;
  const latlng = marker.getLatLng();
  const zoom = Math.max(map.getZoom(), 17);
  if (typeof map.flyTo === 'function') map.flyTo(latlng, zoom, { duration: 0.5 });
  else map.panTo(latlng);
  return true;
};

defineExpose({ focusTracker });

// Leaflet 只在 window resize 时自己重算尺寸。容器尺寸还会被侧栏折叠、工具栏
// 换行（切语言时文字变长）改掉，这些都不发 window 事件，不重算就是灰块加点击偏移。
let containerObserver = null;

onMounted(async () => {
  await nextTick();
  map = L.map(mapEl.value, { zoomControl: true }).setView([0, 0], 2);
  applyTileLayer();
  redraw();

  if (typeof ResizeObserver !== 'undefined') {
    containerObserver = new ResizeObserver(() => {
      map?.invalidateSize({ animate: false });
    });
    containerObserver.observe(mapEl.value);
  }
});

onBeforeUnmount(() => {
  destroyRegOverlay();
  if (containerObserver) {
    containerObserver.disconnect();
    containerObserver = null;
  }
  if (map) {
    map.remove();
    map = null;
  }
});

watch(activeSourceId, applyTileLayer);
watch(() => props.outdoor, () => {
  activeSourceId.value = outdoorConfig.value.defaultSource;
  applyTileLayer();
});
watch([() => props.trackers, () => props.maps, showTrails,
  () => props.selectedId, () => props.hoveredId], redraw, { deep: true });
</script>

<style scoped>
.outdoor-map-view {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
}

.outdoor-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px;
  font-size: 13px;
  background: #f7f8fa;
  border-bottom: 1px solid var(--sc-color-border);
  flex-wrap: wrap;
}

.tile-select {
  margin-left: 6px;
}

.gcj-warning {
  color: #b06000;
}

.tracker-count {
  margin-left: auto;
  color: var(--sc-color-text-secondary);
}

.outdoor-body {
  flex: 1;
  display: flex;
  min-height: 380px;
  min-width: 0;
}

.outdoor-map-container {
  /* width: 100% 会把侧栏挤出容器, 这里只能让它吃剩下的宽度。 */
  flex: 1 1 auto;
  min-width: 0;
  min-height: 380px;
}

.reg-toggle {
  padding: 4px 10px;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
  background: #fff;
  color: #202124;
  cursor: pointer;
}

.reg-toggle.active {
  background: var(--sc-color-info);
  border-color: var(--sc-color-info);
  color: #fff;
}

.registration-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px 14px;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid var(--sc-color-border);
  font-size: 13px;
}

.reg-title {
  align-self: center;
  font-weight: 600;
}

.reg-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.reg-field.narrow input {
  width: 118px;
}

.reg-field span {
  color: var(--sc-color-text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.reg-field input,
.reg-field select {
  padding: 4px 6px;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
}

.reg-modes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reg-modes button {
  min-width: 64px;
  padding: 5px 8px;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
  background: #fff;
  /* 全局 button 样式是白字, 白底上看不见, 这里显式覆盖 */
  color: #202124;
  cursor: pointer;
}

.reg-modes button.active {
  background: var(--sc-color-info);
  border-color: var(--sc-color-info);
  color: #fff;
}

.reg-hint {
  flex-basis: 100%;
  margin: 0;
  color: var(--sc-color-text-secondary);
}

.reg-error {
  flex-basis: 100%;
  margin: 0;
  color: var(--sc-color-error);
}

.reg-status {
  flex-basis: 100%;
  margin: 0;
  color: #188038;
}

.reg-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reg-actions button {
  min-width: 64px;
  padding: 5px 10px;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
  background: #fff;
  color: #202124;
  cursor: pointer;
}

.reg-actions button.primary {
  background: var(--sc-color-info);
  border-color: var(--sc-color-info);
  color: #fff;
}


.outdoor-empty {
  position: absolute;
  bottom: 12px;
  left: 12px;
  z-index: 500;
  padding: 6px 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--sc-color-text-secondary);
  font-size: 13px;
}
</style>

<!-- web/src/components/OutdoorMapView.vue
     室外 (WGS84) 追踪视图。底图默认 OSM, 瓦片 URL / 署名 / 坐标制均由
     dashboard_config.json 的 outdoor 段配置。轨迹只画 wgs84 段, 室内段留给
     Canvas 的 MapPreview, 两者在切换点不连线。 -->
<template>
  <div class="outdoor-map-view">
    <div class="outdoor-toolbar">
      <label class="tile-select-label">
        {{ t('outdoorMap.tileSource') || 'Base map' }}
        <select v-model="activeSourceId" class="tile-select">
          <option v-for="src in tileSources" :key="src.id" :value="src.id">{{ src.name }}</option>
        </select>
      </label>
      <label class="trail-toggle">
        <input type="checkbox" v-model="showTrails" />
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

    <div class="outdoor-body">
      <div ref="mapEl" class="outdoor-map-container"></div>

      <aside v-if="regActive" class="registration-panel">
        <h4>{{ t('outdoorMap.registration.title') || 'Floor plan registration' }}</h4>

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
        <p class="reg-hint">
          {{ t('outdoorMap.registration.aspectLocked')
            || 'Aspect ratio is locked: only drag, rotate and uniform scale are available.' }}
        </p>

        <label class="reg-field">
          <span>{{ t('outdoorMap.registration.originLat') || 'Origin latitude' }}</span>
          <input type="number" step="0.0000001" v-model.number="regForm.origin_lat"
                 @change="applyFormToOverlay" />
        </label>
        <label class="reg-field">
          <span>{{ t('outdoorMap.registration.originLon') || 'Origin longitude' }}</span>
          <input type="number" step="0.0000001" v-model.number="regForm.origin_lon"
                 @change="applyFormToOverlay" />
        </label>
        <label class="reg-field">
          <span>{{ t('outdoorMap.registration.rotation') || 'Rotation (deg, CW from north)' }}</span>
          <input type="number" step="0.01" v-model.number="regForm.rotation_deg"
                 @change="applyFormToOverlay" />
        </label>
        <label class="reg-field">
          <span>{{ t('outdoorMap.registration.scale') || 'Scale' }}</span>
          <input type="number" step="0.0001" min="0.0001" v-model.number="regForm.scale"
                 @change="applyFormToOverlay" />
        </label>

        <p v-if="regError" class="reg-error">{{ regError }}</p>
        <p v-if="regStatus" class="reg-status">{{ regStatus }}</p>

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
      </aside>
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
import { outdoorSegments, isOutdoorTracker } from '@/utils/trail.js';
import {
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
  // dashboard_config.json 的 maps 数组, 配准模式需要地图米数与背景图。
  maps: { type: Array, default: () => [] },
});

const emit = defineEmits(['registration-saved']);

const mapEl = ref(null);
const showTrails = ref(props.initialShowTrails);

const outdoorConfig = computed(() => normalizeOutdoorConfig(props.outdoor));
const tileSources = computed(() => outdoorConfig.value.tileSources);
const activeSourceId = ref(outdoorConfig.value.defaultSource);
const activeSource = computed(
  () => tileSources.value.find((s) => s.id === activeSourceId.value) || tileSources.value[0],
);

const outdoorTrackers = computed(() => {
  const list = Array.isArray(props.trackers) ? props.trackers : Object.values(props.trackers || {});
  return list.filter(isOutdoorTracker);
});

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

  const bounds = [];
  outdoorTrackers.value.forEach((tracker) => {
    const latlng = trackerLatLng(tracker);
    if (!latlng) return;
    bounds.push(latlng);

    const isSos = tracker.sos === 1;
    L.circleMarker(latlng, {
      radius: 7,
      color: isSos ? '#d93025' : '#1a73e8',
      fillColor: isSos ? '#d93025' : '#1a73e8',
      fillOpacity: 0.9,
      weight: 2,
    })
      .bindTooltip(tracker.device_name || tracker.trackerId, { permanent: false })
      .addTo(overlay);

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

    if (!showTrails.value) return;
    // 只画 wgs84 段: 室内段不在这张图上, 切换点不连线。
    outdoorSegments(tracker.position_history).forEach((segment) => {
      if (segment.points.length < 2) return;
      const line = segment.points.map((p) => [p.lat, p.lon]);
      line.forEach((pt) => bounds.push(pt));
      L.polyline(line, { color: '#1a73e8', weight: 2, opacity: 0.45 }).addTo(overlay);
    });
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

/** 表单三参数 -> 四角。 */
const applyFormToOverlay = () => {
  if (!regOverlay || !regFootprint) return;
  try {
    validateRegistration(regForm.value);
    const corners = cornersFromRegistration(regFootprint, regForm.value)
      .map((c) => L.latLng(c.lat, c.lon));
    regSyncing = true;
    regOverlay.setCorners(corners);
    regError.value = '';
  } catch (err) {
    regError.value = err.message;
  } finally {
    regSyncing = false;
  }
};

const setRegMode = (mode) => {
  regMode.value = mode;
  if (regOverlay?.editing?.setMode) regOverlay.editing.setMode(mode);
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
    await import('leaflet-distortableimage/dist/leaflet.distortableimage.css');
    await import('leaflet-distortableimage');
  } catch (err) {
    regError.value = `leaflet-distortableimage failed to load: ${err.message}`;
    return;
  }

  regOverlay = L.distortableImageOverlay(url, {
    corners,
    // 不含 DistortAction / FreeRotateAction: 宽高比锁死。
    actions: [L.DragAction, L.RotateAction, L.ScaleAction],
    mode: regMode.value,
    editable: true,
    suppressToolbar: true,
    opacity: 0.7,
  });
  map.addLayer(regOverlay);
  regOverlay.on('update', syncFormFromOverlay);
  setRegMode(regMode.value);
  map.fitBounds(L.latLngBounds(corners), { padding: [40, 40] });
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

onMounted(async () => {
  await nextTick();
  map = L.map(mapEl.value, { zoomControl: true }).setView([0, 0], 2);
  applyTileLayer();
  redraw();
});

onBeforeUnmount(() => {
  destroyRegOverlay();
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
watch([() => props.trackers, showTrails], redraw, { deep: true });
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
  border-bottom: 1px solid #e3e5e8;
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
  color: #5f6368;
}

.outdoor-body {
  flex: 1;
  display: flex;
  min-height: 380px;
}

.outdoor-map-container {
  flex: 1;
  min-height: 380px;
  width: 100%;
}

.reg-toggle {
  padding: 4px 10px;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.reg-toggle.active {
  background: #1a73e8;
  border-color: #1a73e8;
  color: #fff;
}

.registration-panel {
  width: 280px;
  flex: 0 0 280px;
  padding: 12px;
  overflow-y: auto;
  background: #fff;
  border-left: 1px solid #e3e5e8;
  font-size: 13px;
}

.registration-panel h4 {
  margin: 0 0 10px;
  font-size: 14px;
}

.reg-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.reg-field input,
.reg-field select {
  padding: 4px 6px;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
}

.reg-modes {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}

.reg-modes button {
  flex: 1;
  padding: 4px 0;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.reg-modes button.active {
  background: #1a73e8;
  border-color: #1a73e8;
  color: #fff;
}

.reg-hint {
  margin: 0 0 12px;
  color: #5f6368;
  line-height: 1.4;
}

.reg-error {
  color: #d93025;
  margin: 0 0 8px;
}

.reg-status {
  color: #188038;
  margin: 0 0 8px;
}

.reg-actions {
  display: flex;
  gap: 6px;
}

.reg-actions button {
  flex: 1;
  padding: 6px 0;
  border: 1px solid #c6c9cd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.reg-actions button.primary {
  background: #1a73e8;
  border-color: #1a73e8;
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
  color: #5f6368;
  font-size: 13px;
}
</style>

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
      <span class="tracker-count">{{ outdoorTrackers.length }}</span>
    </div>

    <div ref="mapEl" class="outdoor-map-container"></div>

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

const { t } = useI18n();

const props = defineProps({
  // { [trackerId]: trackerState }, 或数组
  trackers: { type: [Object, Array], default: () => ({}) },
  // dashboard_config.json 的 outdoor 段, 缺失时自动补 OSM
  outdoor: { type: Object, default: null },
  initialShowTrails: { type: Boolean, default: true },
});

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

onMounted(async () => {
  await nextTick();
  map = L.map(mapEl.value, { zoomControl: true }).setView([0, 0], 2);
  applyTileLayer();
  redraw();
});

onBeforeUnmount(() => {
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

.outdoor-map-container {
  flex: 1;
  min-height: 380px;
  width: 100%;
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

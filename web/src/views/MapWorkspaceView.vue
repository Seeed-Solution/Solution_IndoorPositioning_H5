<!-- web/src/views/MapWorkspaceView.vue
     /map: 定位业务的唯一入口。左栏常驻 tracker 列表, 中栏 indoor/outdoor
     图层画布, 右栏 tracker 详情。界面状态全部编码在 URL query 里。 -->
<template>
  <div class="map-workspace">
    <!-- 左栏: 常驻 tracker 列表 -->
    <aside class="ws-pane ws-pane--list" :class="{ 'is-open': listOpen }">
      <TrackerList
        :trackers="trackers"
        compact
        :selected-id="state.tracker"
        :hovered-id="hoveredId"
        @select-tracker="onSelectTracker"
        @hover-tracker="onHoverTracker"
        @refresh-data="preloadTrackers"
      />
    </aside>

    <!-- 中栏: 地图 -->
    <section class="ws-pane ws-pane--map">
    <div class="map-toolbar">
      <div class="layer-switch" role="group" aria-label="layer">
        <button
          type="button"
          :class="['layer-btn', { active: state.layer === 'indoor' }]"
          @click="setLayer('indoor')"
        >
          <i class="fas fa-map"></i>
          <span class="layer-btn__text">{{ t('map.layerIndoor', 'Indoor') }}</span>
        </button>
        <button
          type="button"
          :class="['layer-btn', { active: state.layer === 'outdoor' }]"
          @click="setLayer('outdoor')"
        >
          <i class="fas fa-globe-asia"></i>
          <span class="layer-btn__text">{{ t('map.layerOutdoor', 'Outdoor') }}</span>
        </button>
      </div>

      <label v-if="state.layer === 'indoor'" class="floor-picker">
        <span class="floor-picker__label">{{ t('map.floor', 'Floor plan') }}</span>
        <select v-model="selectedMapName" class="floor-select">
          <option v-for="entry in availableMaps" :key="entry.map.name" :value="entry.map.name">
            {{ entry.map.name }}
          </option>
        </select>
      </label>

      <span class="map-badge" v-if="selectedTracker">{{ layerBadge }}</span>

      <span class="ws-badge" :class="wsStatus">{{ wsStatusText }}</span>
    </div>

    <div v-if="layerSuggestion" class="layer-suggestion">
      <span>{{ t('map.layerSuggestion', 'This tracker is currently on the other layer.') }}</span>
      <button type="button" class="layer-suggestion__accept" @click="acceptLayerSuggestion">
        {{ layerSuggestion === 'outdoor' ? t('map.layerOutdoor', 'Outdoor') : t('map.layerIndoor', 'Indoor') }}
      </button>
      <button type="button" class="layer-suggestion__dismiss" @click="dismissLayerSuggestion">
        <i class="fas fa-times"></i>
      </button>
    </div>

    <div class="map-stage">
      <OutdoorMapView
        v-if="state.layer === 'outdoor'"
        ref="outdoorMapRef"
        interactive
        :trackers="trackers"
        :outdoor="outdoorConfig"
        :maps="availableMaps"
        :show-trails="state.trails"
        :selected-id="state.tracker"
        :hovered-id="hoveredId"
        @registration-saved="onRegistrationSaved"
        @select-tracker="onSelectTracker"
        @hover-tracker="onHoverTracker"
      />
      <MapPreview
        v-else-if="selectedMap"
        ref="indoorMapRef"
        interactive
        :config="selectedMap"
        :trackers="indoorTrackersForSelectedMap"
        :show-trails="state.trails"
        :selected-id="state.tracker"
        :hovered-id="hoveredId"
        @select-tracker="onSelectTracker"
        @hover-tracker="onHoverTracker"
      />
      <div v-else class="map-empty">
        <i class="fas fa-map-marked-alt"></i>
        <p>{{ t('mapOverview.selectMapToView') }}</p>
      </div>
    </div>
    </section>

    <!-- 右栏: 详情抽屉 -->
    <aside class="ws-pane ws-pane--detail" :class="{ 'is-open': detailOpen }">
      <TrackerDetailPanel
        :tracker="selectedTracker"
        @close="closeDetail"
        @focus="onFocusTracker"
      />
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import MapPreview from '@/components/MapPreview.vue';
import OutdoorMapView from '@/components/OutdoorMapView.vue';
import TrackerList from '@/components/TrackerList.vue';
import TrackerDetailPanel from '@/components/TrackerDetailPanel.vue';
import { isOutdoorTracker } from '@/utils/trail.js';
import { loadDashboardConfiguration, loadTrackers } from '@/services/configApiService.js';
import { buildWsUrl } from '@/config/api.js';
import { parseMapQuery, serializeMapState, sameQuery } from '@/utils/mapUrlState.js';
import { createMapController } from '@/controllers/mapPageController.js';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const state = ref(parseMapQuery(route.query));
const availableMaps = ref([]);
const outdoorConfig = ref(null);
const trackers = ref({});
const wsStatus = ref('disconnected');
const ws = ref(null);

const hoveredId = ref('');

const wsStatusText = computed(() => t(`mapOverview.connectionStatus.${wsStatus.value}`, wsStatus.value));

const selectedTracker = computed(() => trackers.value?.[state.value.tracker] || null);

const listOpen = computed(() => state.value.panel === 'list');
const detailOpen = computed(() => state.value.panel === 'detail' && !!state.value.tracker);

const layerBadge = computed(() => {
  const tr = selectedTracker.value;
  if (!tr) return '';
  if (isOutdoorTracker(tr)) return 'Outdoor · GNSS';
  return tr.type === 'approximate' ? 'Indoor · BLE' : 'Indoor · Calculated';
});

const indoorMapRef = ref(null);
const outdoorMapRef = ref(null);
const layerSuggestion = ref(null);

const controller = createMapController({
  getTrackers: () => trackers.value,
  getState: () => state.value,
  setState: (patch, opts = {}) => {
    if (opts.history === 'replace') replaceState(patch);
    else pushState(patch);
  },
  getHovered: () => hoveredId.value,
  setHovered: (id) => { hoveredId.value = id || ''; },
  focusHandlers: {
    indoor: (id) => indoorMapRef.value?.focusTracker?.(id),
    outdoor: (id) => outdoorMapRef.value?.focusTracker?.(id),
  },
});

const onSelectTracker = (id) => {
  if (!controller.selectTracker(id)) return;
  // 设备当下落在另一个图层时只提示, 不自动换层（spec §5）
  layerSuggestion.value = controller.suggestLayerFor(id);
};

const onHoverTracker = (id) => controller.hoverTracker(id);

const onFocusTracker = (id) => controller.focusTracker(id);

const acceptLayerSuggestion = () => {
  if (!layerSuggestion.value) return;
  controller.setLayer(layerSuggestion.value);
  layerSuggestion.value = null;
  nextTick(() => controller.focusTracker(state.value.tracker));
};

const dismissLayerSuggestion = () => { layerSuggestion.value = null; };

const closeDetail = () => controller.clearSelection();

const selectedMapName = computed({
  get() {
    if (state.value.map) return state.value.map;
    return availableMaps.value[0]?.map?.name || '';
  },
  set(name) {
    pushState({ map: name });
  },
});

const selectedMap = computed(
  () => availableMaps.value.find((m) => m.map?.name === selectedMapName.value) || null,
);

const indoorTrackersForSelectedMap = computed(() => {
  const name = selectedMap.value?.map?.name;
  if (!name) return {};
  const out = {};
  Object.entries(trackers.value || {}).forEach(([id, tracker]) => {
    if (tracker.map === name && !isOutdoorTracker(tracker)) out[id] = tracker;
  });
  return out;
});

// --------------------------------------------------------------------------- //
// URL <-> state
// --------------------------------------------------------------------------- //
let applyingFromRoute = false;

const writeQuery = (next, mode) => {
  const query = serializeMapState(next);
  if (sameQuery(query, route.query)) return;
  router[mode]({ path: route.path, query });
};

/** 明确的用户选择走 push（前进/后退能回到上一个选择）。 */
const pushState = (patch) => {
  state.value = { ...state.value, ...patch };
  if (!applyingFromRoute) writeQuery(state.value, 'push');
};

/** 派生/去抖类改动走 replace, 不打历史。 */
const replaceState = (patch) => {
  state.value = { ...state.value, ...patch };
  if (!applyingFromRoute) writeQuery(state.value, 'replace');
};

const setLayer = (layer) => {
  layerSuggestion.value = null;
  pushState({ layer });
};

watch(() => route.query, (q) => {
  applyingFromRoute = true;
  state.value = parseMapQuery(q);
  applyingFromRoute = false;
});

// --------------------------------------------------------------------------- //
// 数据
// --------------------------------------------------------------------------- //
const onRegistrationSaved = ({ mapName, registration }) => {
  const entry = availableMaps.value.find((m) => m.map?.name === mapName);
  if (entry && entry.map) entry.map.registration = { ...registration };
};

const loadConfig = async () => {
  try {
    const config = await loadDashboardConfiguration();
    outdoorConfig.value = config?.outdoor || null;
    availableMaps.value = Array.isArray(config?.maps) ? config.maps : [];
  } catch (err) {
    console.error('[MapWorkspace] failed to load dashboard configuration:', err);
    availableMaps.value = [];
  }
};

const normalizeTrackers = (data) => {
  if (!data) return {};
  if (Array.isArray(data)) {
    return data.reduce((acc, tracker) => {
      if (tracker?.trackerId) acc[tracker.trackerId] = tracker;
      return acc;
    }, {});
  }
  return typeof data === 'object' ? data : {};
};

const preloadTrackers = async () => {
  try {
    trackers.value = normalizeTrackers(await loadTrackers());
  } catch (err) {
    console.error('[MapWorkspace] failed to preload trackers:', err);
    trackers.value = {};
  }
};

// 轮询/WebSocket 刷新后保持选择: 设备还在就不动, 没了才清掉
watch(trackers, () => controller.reconcile());

const mergeTrackerUpdate = (id, patch) => {
  const prev = trackers.value[id] || {};
  trackers.value = { ...trackers.value, [id]: { ...prev, ...patch } };
};

const connectWebSocket = () => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) return;
  ws.value = new WebSocket(buildWsUrl('/ws'));
  wsStatus.value = 'connecting';
  ws.value.onopen = () => { wsStatus.value = 'connected'; };
  ws.value.onerror = () => { wsStatus.value = 'error'; };
  ws.value.onclose = () => { wsStatus.value = 'disconnected'; };
  ws.value.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (err) {
      console.error('[MapWorkspace] bad websocket payload:', err);
      return;
    }
    if (message.type === 'initial_state') {
      trackers.value = message.data || {};
      return;
    }
    const id = Object.keys(message.data || {})[0];
    if (!id) return;
    const data = message.data[id];
    if (message.type === 'tracker_update') {
      mergeTrackerUpdate(id, {
        trackerId: data.trackerId,
        device_name: data.device_name,
        x: data.position?.x ?? null,
        y: data.position?.y ?? null,
        lat: data.lat ?? data.position?.lat ?? null,
        lon: data.lon ?? data.position?.lon ?? null,
        alt: data.alt ?? null,
        accuracy: data.accuracy ?? null,
        fix_time: data.fix_time ?? null,
        timestamp: data.timestamp,
        sos: data.sos !== undefined ? data.sos : 2,
        sos_happen: data.sos_happen,
        last_detected_beacons: data.last_detected_beacons || [],
        used_beacons: data.last_detected_beacons || [],
        position_history: data.position_history || [],
        type: data.type || 'calculation',
        map: data.map,
      });
    } else if (message.type === 'tracker_location_approximate') {
      mergeTrackerUpdate(id, {
        trackerId: data.trackerId,
        device_name: data.device_name,
        position: null,
        radius: data.radius,
        timestamp: data.timestamp,
        sos: data.sos !== undefined ? data.sos : 2,
        sos_happen: data.sos_happen,
        used_beacons: data.last_detected_beacons || [],
        type: 'approximate',
        map: data.map,
      });
    } else if (message.type === 'tracker_sos') {
      if (!trackers.value[id]) return;
      mergeTrackerUpdate(id, { sos: data.sos, sos_happen: data.timestamp });
    }
  };
};

onMounted(async () => {
  await loadConfig();
  await preloadTrackers();
  connectWebSocket();
});

onUnmounted(() => {
  if (ws.value) {
    ws.value.onclose = null;
    ws.value.close();
    ws.value = null;
  }
});

defineExpose({ state, replaceState, pushState });
</script>

<style scoped>
.map-workspace {
  /* >=1024: 240-320 列表 / minmax(0,1fr) 地图 / 280-360 详情。
     详情关掉时第三列宽度归零, 地图吃掉它。 */
  display: grid;
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr) 0;
  min-width: 0;
  width: 100%;
  height: calc(100vh - var(--sc-layout-header-height));
  box-sizing: border-box;
  overflow: hidden;
}

.map-workspace:has(.ws-pane--detail.is-open) {
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr) minmax(280px, 320px);
}

.ws-pane {
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.ws-pane--list {
  border-right: 1px solid var(--sc-color-border);
  background: var(--sc-color-bg-container);
  display: flex;
  flex-direction: column;
}

.ws-pane--map {
  display: flex;
  flex-direction: column;
}

.ws-pane--detail {
  display: none;
}

.ws-pane--detail.is-open {
  display: block;
}

.map-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--sc-status-normal-bg);
  color: var(--sc-color-primary-active);
  font-size: 12px;
  white-space: nowrap;
}

.map-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  min-width: 0;
  background: var(--sc-color-bg-container);
  border-bottom: 1px solid var(--sc-color-border);
}

.layer-switch {
  display: flex;
  border: 1px solid var(--sc-color-border);
  border-radius: var(--sc-radius-md);
  overflow: hidden;
}

.layer-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  background: var(--sc-color-bg-container);
  color: var(--sc-color-text-secondary);
  cursor: pointer;
  font-size: 13px;
  box-shadow: none;
}

.layer-btn.active {
  background: var(--sc-color-primary);
  color: #fff;
}

.floor-picker {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 13px;
  color: var(--sc-color-text-secondary);
}

.floor-select {
  min-width: 0;
  max-width: 100%;
  padding: 5px 8px;
  border: 1px solid var(--sc-color-border);
  border-radius: var(--sc-radius-md);
  background: #fff;
}

.ws-badge {
  margin-left: auto;
  font-size: 12px;
  color: var(--sc-color-text-tertiary);
}

.ws-badge.connected {
  color: var(--sc-color-success);
}

.layer-suggestion {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  min-width: 0;
  background: var(--sc-status-warning-bg, #fff7e6);
  border-bottom: 1px solid var(--sc-color-border);
  font-size: 13px;
  color: var(--sc-color-text-secondary);
}

.layer-suggestion__accept {
  padding: 3px 10px;
  border: 1px solid var(--sc-color-primary);
  border-radius: var(--sc-radius-md);
  background: var(--sc-color-primary);
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  box-shadow: none;
}

.layer-suggestion__dismiss {
  border: none;
  background: transparent;
  color: var(--sc-color-text-tertiary);
  cursor: pointer;
  box-shadow: none;
}

.map-stage {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  position: relative;
}

.map-stage :deep(.map-preview-container),
.map-stage :deep(.outdoor-map-view) {
  height: 100%;
}

.map-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--sc-color-text-tertiary);
}

.map-empty i {
  font-size: 2.5rem;
}
</style>

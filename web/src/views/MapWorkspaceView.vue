<!-- web/src/views/MapWorkspaceView.vue
     /map: 定位业务的唯一入口。左栏常驻 tracker 列表, 中栏 indoor/outdoor
     图层画布, 右栏 tracker 详情。界面状态全部编码在 URL query 里。 -->
<template>
  <div
    class="map-workspace"
    :class="[`is-${layoutMode}`, { 'has-detail': detailOpen, 'has-list': listOpen, 'is-display': displayMode }]"
  >
    <!-- 遮罩: drawer 档位下点击关掉抽屉 -->
    <div v-if="!displayMode && drawerLayout && (listOpen || detailOpen)" class="ws-scrim" @click="closePanels"></div>

    <!-- 左栏: 常驻 tracker 列表。展示模式下整条不渲染 -->
    <aside v-if="!displayMode" class="ws-pane ws-pane--list" :class="{ 'is-open': listOpen, [`sheet-${sheetState}`]: drawerLayout }">
      <div v-if="drawerLayout" class="ws-pane__grip" @click="cycleSheet"></div>
      <TrackerList
        :trackers="trackers"
        compact
        :search="state.q"
        :status="state.status"
        :group="state.group"
        :selected-id="state.tracker"
        :hovered-id="hoveredId"
        @update:search="replaceState({ q: $event })"
        @update:status="replaceState({ status: $event })"
        @update:group="replaceState({ group: $event })"
        @select-tracker="onSelectTracker"
        @hover-tracker="onHoverTracker"
        @refresh-data="preloadTrackers"
      />
    </aside>

    <!-- 中栏: 地图 -->
    <section class="ws-pane ws-pane--map">
    <!-- 展示模式浮层: 左上信息带 + 右上齿轮（spec §9.2） -->
    <div v-if="displayMode" class="display-overlay">
      <div class="display-band">
        <span class="display-band__map">{{ displayLayerText }}</span>
        <span class="display-band__stat is-online">
          <i class="fas fa-circle"></i>{{ onlineCount }} {{ t('tracker.trackerList.online', 'Online') }}
        </span>
        <span class="display-band__stat is-offline">
          <i class="fas fa-circle"></i>{{ offlineCount }} {{ t('tracker.trackerList.offline', 'Offline') }}
        </span>
        <span class="display-band__time">{{ updatedAtText }}</span>
      </div>
      <button
        v-if="showConfigGear"
        type="button"
        class="display-gear"
        :title="t('nav.mapBeaconConfig', 'Configuration')"
        aria-label="configuration"
        @click="exitDisplayMode"
      >
        <i class="fas fa-cog"></i>
      </button>
    </div>

    <div v-if="!displayMode" class="map-toolbar">
      <button
        v-if="drawerLayout"
        type="button"
        class="panel-toggle"
        :title="t('map.toggleList', 'Tracker list')"
        @click="togglePanel"
      >
        <i class="fas fa-list-ul"></i>
      </button>

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

      <!-- 轨迹开关是两套地图共享的一个状态, 写进 URL -->
      <label class="trails-toggle">
        <input type="checkbox" :checked="state.trails" @change="toggleTrails" />
        <span class="trails-toggle__text">{{ t('outdoorMap.showTrails', 'Show trails') }}</span>
      </label>

      <span class="map-badge" v-if="selectedTracker">{{ layerBadge }}</span>

      <span class="ws-badge" :class="wsStatus">{{ wsStatusText }}</span>
    </div>

    <div v-if="layerSuggestion && !displayMode" class="layer-suggestion">
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
        :display-mode="displayMode"
        @select-tracker="onSelectTracker"
        @hover-tracker="onHoverTracker"
      />
      <div v-else class="map-empty">
        <i class="fas fa-map-marked-alt"></i>
        <p>{{ t('mapOverview.selectMapToView') }}</p>
      </div>
    </div>
    </section>

    <!-- 右栏: 详情抽屉。展示模式下不渲染 -->
    <aside v-if="!displayMode" class="ws-pane ws-pane--detail" :class="{ 'is-open': detailOpen, [`sheet-${sheetState}`]: drawerLayout }">
      <div v-if="drawerLayout" class="ws-pane__grip" @click="cycleSheet"></div>
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
import { MODE_DISPLAY, parseMapQuery, serializeMapState, sameQuery } from '@/utils/mapUrlState.js';
import { createFitScheduler } from '@/utils/displayCamera.js';
import { createWakeLock } from '@/utils/wakeLock.js';
import { loadDisplayConfig } from '@/config/display.js';
import { getCurrentUsername } from '@/services/userStore.js';
import { createMapController } from '@/controllers/mapPageController.js';
import {
  LAYOUT_DESKTOP,
  LAYOUT_MOBILE,
  usesDrawer,
  watchLayoutMode,
} from '@/utils/breakpoints.js';

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

// --------------------------------------------------------------------------- //
// 展示模式 (spec §9)
// --------------------------------------------------------------------------- //
const displayConfig = loadDisplayConfig();
const displayMode = computed(() => state.value.mode === MODE_DISPLAY);
// 访客没有配置权限, 不给齿轮 (spec §9.6)
const showConfigGear = computed(() => getCurrentUsername() !== 'guest');
const lastUpdateAt = ref(null);

const visibleTrackers = computed(() => {
  const all = Object.values(trackers.value || {});
  if (state.value.layer === 'outdoor') return all.filter((tr) => isOutdoorTracker(tr));
  const name = selectedMap.value?.map?.name;
  return all.filter((tr) => !isOutdoorTracker(tr) && (!name || tr.map === name));
});

// 在线判定沿用列表页的口径: 完全依赖后端 online 字段
const onlineCount = computed(
  () => visibleTrackers.value.filter((tr) => tr.online === 'online').length,
);
const offlineCount = computed(() => visibleTrackers.value.length - onlineCount.value);

const displayLayerText = computed(() => {
  if (state.value.layer === 'outdoor') return t('map.layerOutdoor', 'Outdoor');
  const name = selectedMap.value?.map?.name;
  return name || t('map.layerIndoor', 'Indoor');
});

const updatedAtText = computed(() => {
  if (!lastUpdateAt.value) return '--:--:--';
  return new Date(lastUpdateAt.value).toLocaleTimeString();
});

const exitDisplayMode = () => {
  router.push('/config');
};

// 防熄屏: 只在展示模式里申请, 不支持/被拒静默 (spec §9.5)
const wakeLock = createWakeLock();
watch(displayMode, (on) => {
  if (on) wakeLock.start();
  else wakeLock.stop();
});

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
  // 居中要等一次 DOM flush: 两套地图都是先重绘再对外提供目标位置
  // (canvas 的 hitTargets / Leaflet 的 markerRegistry)。选中刚好换了楼层、
  // 换了图层或设备是这轮新出现的时候, 同步调用拿到的是上一帧的目标, 直接静默不居中。
  focusHandlers: {
    indoor: (id) => { nextTick(() => indoorMapRef.value?.focusTracker?.(id)); },
    outdoor: (id) => { nextTick(() => outdoorMapRef.value?.focusTracker?.(id)); },
  },
  // 展示模式的 fit-all: 同样等一次 DOM flush, 新出现的设备要先画出来才有位置
  fitAllHandlers: {
    indoor: () => {
      nextTick(() => indoorMapRef.value?.fitAllTrackers?.({
        paddingRatio: displayConfig.fitPaddingRatio,
        jitterRatio: displayConfig.fitJitterRatio,
      }));
    },
    outdoor: () => { nextTick(() => outdoorMapRef.value?.fitAllTrackers?.()); },
  },
});

// tracker 集合/位置每几秒就动一次, 每次都重框会一直抖: 合并到防抖窗口里跑一次
const fitScheduler = createFitScheduler({
  delayMs: displayConfig.fitDebounceMs,
  onFit: () => { if (displayMode.value) controller.fitAll(); },
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
  setLayer(layerSuggestion.value);
  nextTick(() => controller.focusTracker(state.value.tracker));
};

const dismissLayerSuggestion = () => { layerSuggestion.value = null; };

const closeDetail = () => controller.clearSelection();

const toggleTrails = () => replaceState({ trails: !state.value.trails });

// --------------------------------------------------------------------------- //
// 三档布局
// --------------------------------------------------------------------------- //
const layoutMode = ref(LAYOUT_DESKTOP);
const drawerLayout = computed(() => usesDrawer(layoutMode.value));
// <768 的底部 drawer 有 peek / half / full 三态
const SHEET_STATES = ['peek', 'half', 'full'];
const sheetState = ref('half');
const cycleSheet = () => {
  const i = SHEET_STATES.indexOf(sheetState.value);
  sheetState.value = SHEET_STATES[(i + 1) % SHEET_STATES.length];
};

const closePanels = () => replaceState({ panel: 'closed' });
const togglePanel = () => replaceState({ panel: state.value.panel === 'closed' ? 'list' : 'closed' });

let stopLayoutWatch = null;

// drawer 档位下默认不占屏: 进来先收起面板, 地图铺满
watch(layoutMode, (mode, prev) => {
  if (!prev) return;
  // 展示模式没有面板, 别往 URL 里写 panel
  if (displayMode.value) return;
  if (usesDrawer(mode) && !usesDrawer(prev) && state.value.panel === 'list') {
    replaceState({ panel: 'closed' });
  }
  if (mode === LAYOUT_DESKTOP && state.value.panel === 'closed') {
    replaceState({ panel: 'list' });
  }
});

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
  controller.setLayer(layer);
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
watch(trackers, () => {
  controller.reconcile();
  lastUpdateAt.value = Date.now();
  if (displayMode.value) fitScheduler.schedule();
});

// 进出展示模式、换图层、换楼层都立刻重框一次, 不等防抖窗口
watch([displayMode, () => state.value.layer, selectedMapName], () => {
  if (!displayMode.value) {
    fitScheduler.cancel();
    return;
  }
  nextTick(() => controller.fitAll());
});

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
  stopLayoutWatch = watchLayoutMode(
    typeof window !== 'undefined' ? window : null,
    (mode) => { layoutMode.value = mode; },
  );
  if (!displayMode.value && drawerLayout.value && state.value.panel === 'list' && !route.query.panel) {
    replaceState({ panel: 'closed' });
  }
  await loadConfig();
  await preloadTrackers();
  connectWebSocket();
  if (displayMode.value) {
    wakeLock.start();
    nextTick(() => controller.fitAll());
  }
});

onUnmounted(() => {
  fitScheduler.cancel();
  wakeLock.stop();
  if (stopLayoutWatch) {
    stopLayoutWatch();
    stopLayoutWatch = null;
  }
  if (ws.value) {
    ws.value.onclose = null;
    ws.value.close();
    ws.value = null;
  }
});

defineExpose({ state, replaceState, pushState, displayMode });
</script>

<style scoped>
/* --------------------------------------------------------------------- */
/* 展示模式: 地图铺满视口, 只留左上信息带与右上齿轮 (spec §9.2)            */
/* --------------------------------------------------------------------- */
.map-workspace.is-display {
  display: block;
  height: 100vh;
  height: 100dvh;
  width: 100%;
}

.map-workspace.is-display .ws-pane--map {
  height: 100%;
}

/* MapPreview 的内层默认按 320 px 起的 flex 高度排, 展示模式要一路撑到底,
   否则画布只占视口上面一条。 */
.map-workspace.is-display .map-stage :deep(.map-preview-container),
.map-workspace.is-display .map-stage :deep(.content-columns),
.map-workspace.is-display .map-stage :deep(.map-view-wrapper),
.map-workspace.is-display .map-stage :deep(.map-container) {
  height: 100%;
  min-height: 0;
}

.display-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 30;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top, 0px));
  pointer-events: none;
}

.display-band {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  min-width: 0;
  padding: 8px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(6px);
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.12);
  font-size: 16px;
  color: var(--sc-color-text-primary);
}

.display-band__map {
  font-weight: 600;
}

.display-band__stat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.display-band__stat i {
  font-size: 8px;
}

.display-band__stat.is-online i { color: var(--sc-color-success, #188038); }
.display-band__stat.is-offline i { color: var(--sc-color-text-tertiary, #9aa0a6); }

.display-band__time {
  color: var(--sc-color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.display-gear {
  pointer-events: auto;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(6px);
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.12);
  color: var(--sc-color-text-secondary);
  font-size: 16px;
  cursor: pointer;
}

.display-gear:hover {
  color: var(--sc-color-primary);
}

/* 窄屏信息带缩一点, 但字号不低于 14 保证远距离可读 */
.map-workspace.is-display.is-mobile .display-band {
  gap: 10px;
  padding: 6px 12px;
  font-size: 14px;
}

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

.ws-pane__grip {
  height: 18px;
  flex: 0 0 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
}

.ws-pane__grip::before {
  content: '';
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--sc-color-border);
}

.ws-scrim {
  position: absolute;
  inset: 0;
  z-index: 40;
  background: rgba(0, 0, 0, 0.35);
}

.panel-toggle,
.trails-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--sc-color-text-secondary);
  white-space: nowrap;
}

.panel-toggle {
  padding: 6px 10px;
  border: 1px solid var(--sc-color-border);
  border-radius: var(--sc-radius-md);
  background: var(--sc-color-bg-container);
  cursor: pointer;
  box-shadow: none;
}

/* 768-1023: 地图主视图, 列表与详情都变成右侧 drawer */
.map-workspace.is-tablet,
.map-workspace.is-mobile {
  position: relative;
  display: block;
}

.map-workspace.is-tablet .ws-pane--map,
.map-workspace.is-mobile .ws-pane--map {
  height: 100%;
}

.map-workspace.is-tablet .ws-pane--list,
.map-workspace.is-tablet .ws-pane--detail {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  width: min(360px, 85vw);
  display: none;
  flex-direction: column;
  background: var(--sc-color-bg-container);
  border-left: 1px solid var(--sc-color-border);
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.12);
}

.map-workspace.is-tablet .ws-pane--list.is-open,
.map-workspace.is-tablet .ws-pane--detail.is-open {
  display: flex;
}

/* <768: 侧栏 off-canvas 由 AppShell 负责, 这里是底部 drawer 的 peek/half/full */
.map-workspace.is-mobile .ws-pane--list,
.map-workspace.is-mobile .ws-pane--detail {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  display: none;
  flex-direction: column;
  border: none;
  border-top: 1px solid var(--sc-color-border);
  border-radius: 12px 12px 0 0;
  background: var(--sc-color-bg-container);
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.16);
  padding-bottom: env(safe-area-inset-bottom, 0px);
  transition: height 0.2s ease;
}

.map-workspace.is-mobile .ws-pane--list.is-open,
.map-workspace.is-mobile .ws-pane--detail.is-open {
  display: flex;
}

/* 抽屉里的卡片按 flex 分高度, 不能让它被内容撑出抽屉 */
.map-workspace.is-tablet .ws-pane--list > :not(.ws-pane__grip),
.map-workspace.is-tablet .ws-pane--detail > :not(.ws-pane__grip),
.map-workspace.is-mobile .ws-pane--list > :not(.ws-pane__grip),
.map-workspace.is-mobile .ws-pane--detail > :not(.ws-pane__grip) {
  flex: 1 1 auto;
  min-height: 0;
}

.map-workspace.is-mobile .sheet-peek { height: 30%; }
.map-workspace.is-mobile .sheet-half { height: 55%; }
.map-workspace.is-mobile .sheet-full { height: 92%; }

.map-workspace.is-mobile .layer-btn__text,
.map-workspace.is-mobile .floor-picker__label,
.map-workspace.is-mobile .trails-toggle__text,
.map-workspace.is-mobile .ws-badge {
  /* 窄屏按钮图标化, 文字留给屏幕阅读器之外的宽屏 */
  display: none;
}

.map-workspace.is-mobile .map-toolbar {
  gap: 8px;
  padding: 6px 8px;
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
  overflow-x: hidden;
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

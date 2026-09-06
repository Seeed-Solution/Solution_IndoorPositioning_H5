<!-- 室外 (GNSS/WGS84) 独立页面。与 /map-overview 共用同一条 WebSocket 载荷,
     只保留 tracker.type === 'wGS84' 的设备。 -->
<template>
  <div class="outdoor-overview">
    <h1 class="page-title">{{ $t('outdoorMap.title') }}</h1>
    <div class="status-bar">
      <span :class="['status-value', wsStatus === 'connected' ? 'connected' : 'disconnected']">
        {{ $t('mapOverview.webSocketLabel') }}: {{ wsStatus }}
      </span>
      <span class="tracker-count">{{ outdoorTrackerList.length }}</span>
    </div>
    <div class="outdoor-wrapper">
      <OutdoorMapView :trackers="trackers" :outdoor="outdoorConfig" :maps="availableMaps" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { buildWsUrl } from '@/config/api.js';
import { loadDashboardConfiguration, loadTrackers } from '@/services/configApiService.js';
import OutdoorMapView from '@/components/OutdoorMapView.vue';
import { isOutdoorTracker } from '@/utils/trail.js';
import { buildTrackerMapFromSnapshot, normalizeTrackerSnapshotEntry } from '@/utils/trackerSnapshot.js';

const trackers = ref({});
const outdoorConfig = ref(null);
// 已配准的平面图也要画在这张图上, 所以投屏页同样需要 maps。
const availableMaps = ref([]);
const wsStatus = ref('disconnected');
let ws = null;

const outdoorTrackerList = computed(
  () => Object.values(trackers.value || {}).filter(isOutdoorTracker),
);

const applyUpdate = (data) => {
  const trackerId = Object.keys(data)[0];
  if (!trackerId || !data[trackerId]) return;
  const normalized = normalizeTrackerSnapshotEntry({ trackerId, ...data[trackerId] });
  if (!normalized) return;
  trackers.value = {
    ...trackers.value,
    [trackerId]: normalized,
  };
};

// 页面刷新后 WS 重新连接是空白状态, 服务端也从不在连接建立时真正广播
// initial_state (server/main.py 的 websocket_endpoint 里没有这个分支) —— 靠
// REST /api/trackers 补一份当前快照 (含 position_history/lat/lon/type), 避免
// tracker 与轨迹要等下一条上行才出现。
const preloadTrackers = async () => {
  try {
    const snapshot = await loadTrackers();
    trackers.value = buildTrackerMapFromSnapshot(snapshot);
  } catch (err) {
    console.warn('[OutdoorMapOverview] tracker preload failed:', err);
  }
};

onMounted(async () => {
  try {
    const config = await loadDashboardConfiguration();
    outdoorConfig.value = config?.outdoor || null;
    availableMaps.value = config?.maps || [];
  } catch (err) {
    console.warn('[OutdoorMapOverview] dashboard config load failed:', err);
  }

  await preloadTrackers();

  ws = new WebSocket(buildWsUrl('/ws'));
  wsStatus.value = 'connecting';
  ws.onopen = () => { wsStatus.value = 'connected'; };
  ws.onclose = () => { wsStatus.value = 'disconnected'; };
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === 'initial_state') {
        trackers.value = buildTrackerMapFromSnapshot(message.data || {});
      } else if (message.type === 'tracker_update') {
        applyUpdate(message.data);
      }
    } catch (err) {
      console.error('[OutdoorMapOverview] bad ws message:', err);
    }
  };
});

onUnmounted(() => {
  if (ws) ws.close();
});
</script>

<style scoped>
.outdoor-overview {
  padding: 16px;
}

.status-bar {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
}

.status-value.connected { color: #188038; }
.status-value.disconnected { color: var(--sc-color-error); }

.outdoor-wrapper {
  height: 70vh;
  border: 1px solid var(--sc-color-border);
  border-radius: 6px;
  overflow: hidden;
}
</style>

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
      <OutdoorMapView :trackers="outdoorTrackerList" :outdoor="outdoorConfig" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { buildWsUrl } from '@/config/api.js';
import { loadDashboardConfiguration } from '@/services/configApiService.js';
import OutdoorMapView from '@/components/OutdoorMapView.vue';
import { isOutdoorTracker } from '@/utils/trail.js';

const trackers = ref({});
const outdoorConfig = ref(null);
const wsStatus = ref('disconnected');
let ws = null;

const outdoorTrackerList = computed(
  () => Object.values(trackers.value || {}).filter(isOutdoorTracker),
);

const applyUpdate = (data) => {
  const trackerId = Object.keys(data)[0];
  if (!trackerId || !data[trackerId]) return;
  const d = data[trackerId];
  trackers.value = {
    ...trackers.value,
    [trackerId]: {
      trackerId: d.trackerId,
      device_name: d.device_name,
      x: d.position?.x ?? null,
      y: d.position?.y ?? null,
      lat: d.lat ?? d.position?.lat ?? null,
      lon: d.lon ?? d.position?.lon ?? null,
      alt: d.alt ?? null,
      accuracy: d.accuracy ?? null,
      fix_time: d.fix_time ?? null,
      timestamp: d.timestamp,
      sos: d.sos ?? 2,
      type: d.type || 'calculation',
      map: d.map,
      position_history: d.position_history || [],
    },
  };
};

onMounted(async () => {
  try {
    const config = await loadDashboardConfiguration();
    outdoorConfig.value = config?.outdoor || null;
  } catch (err) {
    console.warn('[OutdoorMapOverview] dashboard config load failed:', err);
  }

  ws = new WebSocket(buildWsUrl('/ws'));
  wsStatus.value = 'connecting';
  ws.onopen = () => { wsStatus.value = 'connected'; };
  ws.onclose = () => { wsStatus.value = 'disconnected'; };
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === 'initial_state') {
        trackers.value = message.data || {};
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
.status-value.disconnected { color: #d93025; }

.outdoor-wrapper {
  height: 70vh;
  border: 1px solid #e3e5e8;
  border-radius: 6px;
  overflow: hidden;
}
</style>

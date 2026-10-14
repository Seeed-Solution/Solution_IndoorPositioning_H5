<!-- web/src/components/TrackerDetailPanel.vue
     /map 的 tracker 详情。桌面档是第三列, 平板档是右侧抽屉, 手机档是底部
     drawer 的内容 —— 组件本身只管内容, 容器形态由 MapWorkspaceView 决定。 -->
<template>
  <section class="detail-panel" :aria-hidden="!tracker">
    <header class="detail-panel__head">
      <div class="detail-panel__title">
        <span class="detail-panel__name">
          {{ tracker ? (tracker.device_name || tracker.trackerId) : t('map.detailEmptyTitle', 'No tracker selected') }}
        </span>
        <span v-if="tracker" class="detail-panel__badge" :class="locationKind">
          {{ locationLabel }}
        </span>
      </div>
      <button type="button" class="detail-panel__close" :title="t('common.close', 'Close')" @click="emit('close')">
        <i class="fas fa-times"></i>
      </button>
    </header>

    <div v-if="!tracker" class="detail-panel__empty">
      <i class="fas fa-hand-pointer"></i>
      <p>{{ t('map.detailEmptyHint', 'Pick a tracker from the list or the map.') }}</p>
    </div>

    <div v-else class="detail-panel__body">
      <dl class="detail-grid">
        <dt>{{ t('tracker.trackerList.status') }}</dt>
        <dd>
          <span :class="['sc-status-badge', statusBadgeClass]">{{ statusText }}</span>
        </dd>

        <dt>{{ t('tracker.trackerList.lastPosition') }}</dt>
        <dd>{{ positionText }}</dd>

        <dt>{{ t('map.fixSource', 'Fix source') }}</dt>
        <dd>{{ fixSourceText }}</dd>

        <dt>{{ t('tracker.lastSeen') }}</dt>
        <dd>{{ timestampText }}</dd>

        <dt>{{ t('tracker.trackerList.battery') }}</dt>
        <dd>{{ batteryText }}</dd>

        <dt>{{ t('tracker.trackerList.signal') }}</dt>
        <dd>{{ signalText }}</dd>

        <template v-if="tracker.group">
          <dt>{{ t('tracker.trackerList.group') }}</dt>
          <dd>{{ tracker.group }}</dd>
        </template>
      </dl>

      <div v-if="tracker.sos === 1" class="detail-panel__sos">
        <i class="fas fa-triangle-exclamation"></i>
        <span>{{ t('tracker.sosAlert') }}</span>
        <span v-if="tracker.sos_happen" class="detail-panel__sos-time">
          {{ formatTime(tracker.sos_happen) }}
        </span>
      </div>

      <div class="detail-panel__actions">
        <button type="button" class="detail-action" @click="emit('focus', tracker.trackerId)">
          <i class="fas fa-crosshairs"></i>
          {{ t('map.focusOnMap', 'Center on map') }}
        </button>
        <button type="button" class="detail-action" @click="showAlarmHistory = true">
          <i class="fas fa-bell"></i>
          {{ t('alarm.history', 'Alarm history') }}
        </button>
      </div>
    </div>

    <AlarmHistoryModal
      :isVisible="showAlarmHistory"
      :selectedTracker="tracker"
      @close="showAlarmHistory = false"
    />
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import AlarmHistoryModal from '@/components/AlarmHistoryModal.vue';
import { isOutdoorTracker } from '@/utils/trail.js';

const { t } = useI18n();

const props = defineProps({
  tracker: { type: Object, default: null },
});

const emit = defineEmits(['close', 'focus']);

const showAlarmHistory = ref(false);

// 换设备时把弹窗收掉, 免得历史与当前详情对不上
watch(() => props.tracker?.trackerId, () => { showAlarmHistory.value = false; });

const locationKind = computed(() => (isOutdoorTracker(props.tracker) ? 'outdoor' : 'indoor'));

/** 徽标复用 isOutdoorTracker: 服务端判为室内的设备不能因残留经纬度被写成 Outdoor。 */
const locationLabel = computed(() => {
  if (!props.tracker) return '';
  if (locationKind.value === 'outdoor') return 'Outdoor · GNSS';
  return props.tracker.type === 'approximate' ? 'Indoor · BLE' : 'Indoor · Calculated';
});

const statusText = computed(() => {
  const online = props.tracker?.online;
  if (online === 'online') return t('tracker.trackerList.online');
  if (online === 'unknown') return t('common.unknown');
  return t('tracker.trackerList.offline');
});

const statusBadgeClass = computed(() => {
  const online = props.tracker?.online;
  if (online === 'online') return 'sc-status-badge--normal';
  if (online === 'unknown') return 'sc-status-badge--warning';
  return 'sc-status-badge--offline';
});

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);

const positionText = computed(() => {
  const tr = props.tracker;
  if (!tr) return '—';
  if (locationKind.value === 'outdoor') {
    const lat = num(Number(tr.lat));
    const lon = num(Number(tr.lon));
    if (lat === null || lon === null) return '—';
    const acc = num(Number(tr.accuracy));
    return `${lat.toFixed(6)}, ${lon.toFixed(6)}${acc !== null ? ` (±${acc.toFixed(1)}m)` : ''}`;
  }
  const x = num(tr.x);
  const y = num(tr.y);
  const mapName = tr.map || t('common.unknown');
  if (tr.type === 'calculation' && x !== null && y !== null) {
    return `${mapName} (${x.toFixed(2)}, ${y.toFixed(2)})`;
  }
  if (tr.type === 'approximate' && num(tr.radius) !== null) {
    return `${mapName} (r ${tr.radius.toFixed(2)}m)`;
  }
  return mapName;
});

const fixSourceText = computed(() => {
  const tr = props.tracker;
  if (!tr) return '—';
  if (locationKind.value === 'outdoor') return 'GNSS';
  if (tr.type === 'approximate') return 'BLE beacon proximity';
  if (tr.type === 'calculation') return 'BLE trilateration';
  return tr.type || '—';
});

const formatTime = (ts) => {
  if (!ts) return '—';
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
};

const timestampText = computed(() => formatTime(props.tracker?.fix_time || props.tracker?.timestamp));

const batteryText = computed(() => {
  const b = props.tracker?.battery ?? props.tracker?.battery_level;
  return b === undefined || b === null ? '—' : `${b}%`;
});

const signalText = computed(() => {
  const beacons = props.tracker?.used_beacons || props.tracker?.last_detected_beacons;
  if (!Array.isArray(beacons) || beacons.length === 0) return '—';
  const rssis = beacons.map((b) => Number(b.rssi)).filter((v) => Number.isFinite(v));
  if (rssis.length === 0) return '—';
  return `${Math.max(...rssis)} dBm (${beacons.length})`;
});
</script>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  background: var(--sc-color-bg-container);
  border-left: 1px solid var(--sc-color-border);
}

.detail-panel__head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  min-width: 0;
  border-bottom: 1px solid var(--sc-color-border);
}

.detail-panel__title {
  flex: 1 1 auto;
  min-width: 0;
}

.detail-panel__name {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--sc-color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-panel__badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: var(--sc-status-normal-bg);
  color: var(--sc-color-primary-active);
}

.detail-panel__badge.outdoor {
  background: var(--sc-color-bg-layout);
  color: var(--sc-color-text-secondary);
}

.detail-panel__close {
  flex: 0 0 auto;
  border: none;
  background: transparent;
  color: var(--sc-color-text-secondary);
  cursor: pointer;
  padding: 4px 6px;
  box-shadow: none;
}

.detail-panel__empty {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 16px;
  color: var(--sc-color-text-tertiary);
  text-align: center;
}

.detail-panel__empty i {
  font-size: 1.8rem;
}

.detail-panel__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, auto) minmax(0, 1fr);
  gap: 6px 12px;
  margin: 0;
  font-size: 13px;
}

.detail-grid dt {
  color: var(--sc-color-text-secondary);
  white-space: nowrap;
}

.detail-grid dd {
  margin: 0;
  min-width: 0;
  color: var(--sc-color-text);
  overflow-wrap: anywhere;
}

.detail-panel__sos {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 8px 10px;
  border-radius: var(--sc-radius-md);
  background: var(--sc-status-danger-bg);
  color: var(--sc-color-error);
  font-size: 13px;
  font-weight: 600;
}

.detail-panel__sos-time {
  font-weight: 400;
  color: var(--sc-color-text-secondary);
}

.detail-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.detail-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--sc-color-border);
  border-radius: var(--sc-radius-md);
  background: var(--sc-color-bg-container);
  color: var(--sc-color-text);
  font-size: 13px;
  cursor: pointer;
  box-shadow: none;
}

.detail-action:hover {
  border-color: var(--sc-color-primary);
  color: var(--sc-color-primary);
}
</style>

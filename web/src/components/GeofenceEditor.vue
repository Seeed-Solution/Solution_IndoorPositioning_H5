<!-- web/src/components/GeofenceEditor.vue
     在 Leaflet 上画多边形 / 圆, 存成 GeoJSON。
     用 leaflet 原生 API（不引 leaflet-draw）：
       - 多边形：地图上依次点击落点，>= 3 个点可保存
       - 圆形：点一次定圆心，半径用输入框（米）
     底图与 OutdoorMapView 共用 src/config/outdoor.js 的源配置。 -->
<template>
  <div class="geofence-editor">
    <div class="gf-toolbar">
      <div class="gf-shape-switch">
        <label>
          <input type="radio" value="polygon" v-model="shape" />
          {{ $t('geofence.polygon') }}
        </label>
        <label>
          <input type="radio" value="circle" v-model="shape" />
          {{ $t('geofence.circle') }}
        </label>
      </div>

      <label class="gf-field">
        {{ $t('geofence.name') }}
        <input type="text" v-model="fenceName" maxlength="100" class="gf-input" />
      </label>

      <label v-if="shape === 'circle'" class="gf-field">
        {{ $t('geofence.radius') }}
        <input type="number" v-model.number="radiusM" min="1" step="1" class="gf-input gf-input-sm" />
      </label>

      <label class="gf-field">
        {{ $t('geofence.baseMap') }}
        <select v-model="activeSourceId" class="gf-input gf-input-sm">
          <option v-for="src in tileSources" :key="src.id" :value="src.id">{{ src.name }}</option>
        </select>
      </label>

      <button type="button" class="gf-btn" @click="clearDrawing">{{ $t('geofence.clear') }}</button>
      <button type="button" class="gf-btn gf-btn-primary" :disabled="!canSave || saving" @click="saveFence">
        {{ saving ? $t('geofence.saving') : $t('geofence.save') }}
      </button>
    </div>

    <p class="gf-hint">
      {{ shape === 'polygon' ? $t('geofence.hintPolygon') : $t('geofence.hintCircle') }}
      <span v-if="activeSource && activeSource.gcj02Correction" class="gf-warn">
        {{ $t('geofence.gcjNotice') }}
      </span>
    </p>

    <div ref="mapEl" class="gf-map"></div>

    <p v-if="errorMessage" class="gf-error">{{ errorMessage }}</p>

    <div class="gf-list">
      <div class="gf-list-title">{{ $t('geofence.existing') }}</div>
      <div v-if="fences.length === 0" class="gf-empty">{{ $t('geofence.none') }}</div>
      <ul v-else>
        <li v-for="fence in fences" :key="fence.id" :class="{ active: fence.id === selectedId }">
          <button type="button" class="gf-pick" @click="pickFence(fence)">
            {{ fence.name }}
            <span class="gf-kind">{{ fence.geometry && fence.geometry.type === 'Point'
              ? `${$t('geofence.circle')} · ${fence.radius_m}m` : $t('geofence.polygon') }}</span>
          </button>
          <button type="button" class="gf-del" @click="removeFence(fence)">×</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { apiRequest } from '@/utils/httpClient.js';
import { API_ENDPOINTS } from '@/config/api.js';
import { normalizeOutdoorConfig } from '@/config/outdoor.js';

const props = defineProps({
  // 当前选中的围栏 ID
  modelValue: { type: [Number, String], default: null },
  outdoor: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue', 'saved', 'error']);

const mapEl = ref(null);
const shape = ref('polygon');
const fenceName = ref('');
const radiusM = ref(100);
const saving = ref(false);
const errorMessage = ref('');
const fences = ref([]);
const selectedId = ref(props.modelValue ?? null);

const vertices = ref([]);      // [[lat, lon], ...]
const circleCenter = ref(null);

const outdoorConfig = computed(() => normalizeOutdoorConfig(props.outdoor));
const tileSources = computed(() => outdoorConfig.value.tileSources);
const activeSourceId = ref(outdoorConfig.value.defaultSource);
const activeSource = computed(
  () => tileSources.value.find((s) => s.id === activeSourceId.value) || tileSources.value[0],
);

const canSave = computed(() => {
  if (!fenceName.value.trim()) return false;
  if (shape.value === 'polygon') return vertices.value.length >= 3;
  return !!circleCenter.value && Number(radiusM.value) > 0;
});

let map = null;
let tileLayer = null;
let drawLayer = null;
let previewLayer = null;

const applyTileLayer = () => {
  if (!map || !activeSource.value) return;
  if (tileLayer) map.removeLayer(tileLayer);
  const src = activeSource.value;
  const options = { attribution: src.attribution, maxZoom: src.maxZoom || 19 };
  if (src.subdomains) options.subdomains = src.subdomains;
  tileLayer = L.tileLayer(src.url, options).addTo(map);
};

const redrawDrawing = () => {
  if (!map) return;
  if (drawLayer) map.removeLayer(drawLayer);
  drawLayer = L.layerGroup().addTo(map);

  if (shape.value === 'polygon') {
    vertices.value.forEach((pt, idx) => {
      L.circleMarker(pt, { radius: 4, color: '#1a73e8', fillOpacity: 1 })
        .bindTooltip(String(idx + 1), { permanent: false })
        .addTo(drawLayer);
    });
    if (vertices.value.length >= 2) {
      L.polygon(vertices.value, { color: '#1a73e8', weight: 2, fillOpacity: 0.12 }).addTo(drawLayer);
    }
    return;
  }
  if (circleCenter.value) {
    L.circleMarker(circleCenter.value, { radius: 4, color: '#1a73e8', fillOpacity: 1 }).addTo(drawLayer);
    L.circle(circleCenter.value, {
      radius: Number(radiusM.value) || 1,
      color: '#1a73e8',
      weight: 2,
      fillOpacity: 0.12,
    }).addTo(drawLayer);
  }
};

const onMapClick = (event) => {
  const pt = [event.latlng.lat, event.latlng.lng];
  if (shape.value === 'polygon') {
    vertices.value = [...vertices.value, pt];
  } else {
    circleCenter.value = pt;
  }
  redrawDrawing();
};

const clearDrawing = () => {
  vertices.value = [];
  circleCenter.value = null;
  errorMessage.value = '';
  redrawDrawing();
};

// GeoJSON 的坐标顺序是 [lon, lat], 与 Leaflet 的 [lat, lon] 相反。
const buildGeometry = () => {
  if (shape.value === 'circle') {
    return { type: 'Point', coordinates: [circleCenter.value[1], circleCenter.value[0]] };
  }
  const ring = vertices.value.map((pt) => [pt[1], pt[0]]);
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) ring.push([...first]);
  return { type: 'Polygon', coordinates: [ring] };
};

const loadFences = async () => {
  try {
    const response = await apiRequest.get(API_ENDPOINTS.GEOFENCES);
    fences.value = response?.data?.data ?? [];
  } catch (error) {
    errorMessage.value = error.message;
    emit('error', error);
  }
};

const saveFence = async () => {
  if (!canSave.value) return;
  saving.value = true;
  errorMessage.value = '';
  try {
    const body = {
      name: fenceName.value.trim(),
      geometry: buildGeometry(),
      crs: activeSource.value?.coordSystem === 'gcj02' ? 'gcj02' : 'wgs84',
      enabled: true,
    };
    if (shape.value === 'circle') body.radius_m = Number(radiusM.value);
    const response = await apiRequest.post(API_ENDPOINTS.GEOFENCES, body);
    const created = response?.data?.data;
    await loadFences();
    if (created?.id) {
      selectedId.value = created.id;
      emit('update:modelValue', created.id);
    }
    emit('saved', created);
    clearDrawing();
    fenceName.value = '';
  } catch (error) {
    errorMessage.value = error.message;
    emit('error', error);
  } finally {
    saving.value = false;
  }
};

const removeFence = async (fence) => {
  try {
    await apiRequest.delete(API_ENDPOINTS.GEOFENCE_BY_ID(fence.id));
    if (selectedId.value === fence.id) {
      selectedId.value = null;
      emit('update:modelValue', null);
    }
    await loadFences();
    renderPreview();
  } catch (error) {
    errorMessage.value = error.message;
    emit('error', error);
  }
};

const pickFence = (fence) => {
  selectedId.value = fence.id;
  emit('update:modelValue', fence.id);
  renderPreview();
};

// 选中的围栏在图上以灰色底衬显示, 与正在画的图形区分开。
const renderPreview = () => {
  if (!map) return;
  if (previewLayer) map.removeLayer(previewLayer);
  previewLayer = L.layerGroup().addTo(map);
  const fence = fences.value.find((f) => f.id === selectedId.value);
  if (!fence || !fence.geometry) return;
  const style = { color: '#5f6368', weight: 2, dashArray: '4 4', fillOpacity: 0.06 };
  if (fence.geometry.type === 'Point') {
    const [lon, lat] = fence.geometry.coordinates;
    const circle = L.circle([lat, lon], { radius: fence.radius_m || 1, ...style }).addTo(previewLayer);
    map.fitBounds(circle.getBounds(), { padding: [30, 30], maxZoom: 18 });
    return;
  }
  const layer = L.geoJSON(fence.geometry, { style }).addTo(previewLayer);
  const bounds = layer.getBounds();
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 18 });
};

onMounted(async () => {
  await nextTick();
  map = L.map(mapEl.value, { zoomControl: true }).setView([22.0, 113.0], 13);
  applyTileLayer();
  map.on('click', onMapClick);
  await loadFences();
  renderPreview();
});

onBeforeUnmount(() => {
  if (map) {
    map.off('click', onMapClick);
    map.remove();
    map = null;
  }
});

watch(activeSourceId, applyTileLayer);
watch(shape, clearDrawing);
watch(radiusM, redrawDrawing);
watch(() => props.modelValue, (value) => {
  selectedId.value = value ?? null;
  renderPreview();
});
</script>

<style scoped>
.geofence-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gf-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
}

.gf-shape-switch {
  display: flex;
  gap: 10px;
}

.gf-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.gf-input {
  padding: 4px 6px;
  border: 1px solid #d0d3d8;
  border-radius: 4px;
  font-size: 13px;
}

.gf-input-sm {
  width: 110px;
}

.gf-btn {
  padding: 5px 12px;
  border: 1px solid #d0d3d8;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}

.gf-btn-primary {
  background: var(--sc-color-info);
  border-color: var(--sc-color-info);
  color: #fff;
}

.gf-btn-primary:disabled {
  background: #b8c6de;
  border-color: #b8c6de;
  cursor: not-allowed;
}

.gf-hint {
  margin: 0;
  color: var(--sc-color-text-secondary);
  font-size: 12px;
}

.gf-warn {
  color: #b06000;
  margin-left: 8px;
}

.gf-map {
  height: 320px;
  width: 100%;
  border: 1px solid var(--sc-color-border);
  border-radius: 4px;
}

.gf-error {
  margin: 0;
  color: var(--sc-color-error);
  font-size: 12px;
}

.gf-list-title {
  font-size: 12px;
  color: var(--sc-color-text-secondary);
  margin-bottom: 4px;
}

.gf-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 120px;
  overflow-y: auto;
}

.gf-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 4px;
  border-radius: 4px;
}

.gf-list li.active {
  background: #e8f0fe;
}

.gf-pick {
  flex: 1;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  padding: 2px 0;
}

.gf-kind {
  color: var(--sc-color-text-secondary);
  font-size: 12px;
  margin-left: 8px;
}

.gf-del {
  border: none;
  background: none;
  color: var(--sc-color-error);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.gf-empty {
  color: #9aa0a6;
  font-size: 12px;
}
</style>

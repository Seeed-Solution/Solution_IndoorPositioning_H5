<template>
  <div class="map-editor-tab">
    <h3>Map File & Editing</h3>
    <div class="upload-section">
      <label for="mapFile">Upload Configuration File (JSON) - includes map, beacons, and settings:</label>
      <input type="file" id="mapFile" @change="handleFullConfigFileUpload" accept=".json" />
      <p class="info">When you upload a full configuration file here, it will update the application's current master configuration.</p>
    </div>

    <div v-if="currentMapLayout">
      <p>
        Map: {{ currentMapLayout.name || 'Unnamed' }} 
        ({{ currentMapLayout.width ? currentMapLayout.width.toFixed(1) : 'N/A' }}m x 
        {{ currentMapLayout.height ? currentMapLayout.height.toFixed(1) : 'N/A' }}m)
      </p>
      <canvas ref="mapCanvasRef" width="600" height="400" @click="handleMapClick"></canvas>
      <p class="info">Hint: {{ selectedBeaconForPlacement ? 'Click on the map to place beacon: ' + selectedBeaconForPlacement.displayName : 'Select a beacon from the Beacon Management tab, then click on the map here to place it.'.trim() }}</p>
    </div>
    <p v-else>
      Please upload a valid JSON configuration file, or ensure a configuration is loaded from the server.
    </p>

    <!-- <button @click="exportCurrentMapConfig" :disabled="!currentMapLayout">Export Current Map & Beacon Config</button> -->
    <p class="info">Hint: Full configuration import/export is available in the main action bar of the parent configuration page.</p>

  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue';

const props = defineProps({
  initialMapData: {
    type: Object,
    default: null
  },
  initialSettings: {
    type: Object,
    default: () => ({})
  },
  configuredBeacons: {
    type: Array,
    default: () => []
  },
  selectedBeaconForPlacement: {
    type: Object,
    default: null
  },
  currentLocalDevicePosition: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['mapLoaded', 'configUpdated', 'requestBeaconSelection']);

const mapCanvasRef = ref(null);
const currentMapLayout = ref(null); // Holds only the map object from the full configuration
// localBeacons and localSettings are removed as they are now managed by the parent via props/events

// displayBeacons now directly uses the prop
const displayBeacons = computed(() => {
  return props.configuredBeacons || [];
});

const validateFullConfigStructure = (jsonData) => {
  return jsonData && 
         typeof jsonData.map === 'object' && 
         typeof jsonData.map.width === 'number' && 
         typeof jsonData.map.height === 'number' &&
         Array.isArray(jsonData.beacons) &&
         typeof jsonData.settings === 'object' &&
         typeof jsonData.settings.signalPropagationFactor === 'number';
};

// This function is called when the PARENT (ConfigurationSuiteView) loads a full configuration
// and pushes it down to this component.
const loadConfiguration = (fullConfig) => {
  if (validateFullConfigStructure(fullConfig)) {
    currentMapLayout.value = JSON.parse(JSON.stringify(fullConfig.map));
    // props.configuredBeacons will be updated by the parent, which displayBeacons uses.
    // props.settings are handled by GeneralSettingsTab, but map might use some display settings from it if needed.
    // The settings relevant to map rendering (like scale, if any) should be part of currentMapLayout or directly from fullConfig.settings
    redrawMap();
    console.log("MapEditorTab: Configuration loaded via parent's loadConfiguration call.", currentMapLayout.value);
  } else {
    console.warn("MapEditorTab: Invalid fullConfig structure received in loadConfiguration.", fullConfig);
    currentMapLayout.value = null; // Clear map if invalid config is pushed
    redrawMap(); // Redraw to show empty state
  }
};

// This function is called when a user uploads a JSON file DIRECTLY into this tab.
// It should EMIT the full configuration to the parent.
const handleFullConfigFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const jsonData = JSON.parse(e.target.result);
      if (validateFullConfigStructure(jsonData)) {
        // Emit the successfully parsed and validated full configuration to the parent.
        // The parent (ConfigurationSuiteView) will then update its central state,
        // which will flow back down to this component (and others) via props.
        emit('mapLoaded', JSON.parse(JSON.stringify(jsonData))); 
        alert('Configuration file has been successfully uploaded and sent to the main configuration for processing.');
      } else {
        alert('The uploaded configuration file format is invalid. Please ensure it includes valid "map", "beacons", and "settings" objects.');
      }
    } catch (error) {
      alert('Failed to parse JSON file: ' + error.message);
      console.error("MapEditorTab: JSON file parse error during upload:", error);
    }
  };
  reader.readAsText(file);
  event.target.value = null; // Reset file input
};

// Canvas drawing parameters (will be set in drawMap)
let mapScale = 1;
let mapOffsetX = 0;
let mapOffsetY = 0;
let mapMeterWidth = 0;
let mapMeterHeight = 0;

const redrawMap = () => {
  if (!mapCanvasRef.value) { // Allow drawing a blank canvas even if no map layout
    const canvas = mapCanvasRef.value;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#777';
    ctx.textAlign = 'center';
    ctx.fillText("No map data", canvas.width / 2, canvas.height / 2);
    ctx.textAlign = 'start';
    return;
  }
  if (!currentMapLayout.value) { // If there is a canvas ref but no map layout
     const canvas = mapCanvasRef.value;
     const ctx = canvas.getContext('2d');
     ctx.clearRect(0, 0, canvas.width, canvas.height);
     ctx.fillStyle = '#e9e9e9'; // Slightly different background for no map data
     ctx.fillRect(0, 0, canvas.width, canvas.height);
     ctx.fillStyle = '#555';
     ctx.textAlign = 'center';
     ctx.font = '16px Arial';
     ctx.fillText("Please upload or load a map configuration", canvas.width / 2, canvas.height / 2);
     ctx.textAlign = 'start';
     return;
  }

  const canvas = mapCanvasRef.value;
  const ctx = canvas.getContext('2d');
  const layout = currentMapLayout.value;
  const beaconsToDraw = displayBeacons.value;

  const canvasWidth = canvas.width;
  const canvasHeight = canvas.height;

  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  ctx.fillStyle = '#f0f0f0'; // Background for the canvas element itself
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  mapMeterWidth = layout.width;
  mapMeterHeight = layout.height;
  const padding = 20;

  const tempScaleX = (canvasWidth - 2 * padding) / mapMeterWidth;
  const tempScaleY = (canvasHeight - 2 * padding) / mapMeterHeight;
  mapScale = Math.min(tempScaleX, tempScaleY);
  if (mapScale <= 0) mapScale = 1; // Prevent zero or negative scale

  const mapPixelWidth = mapMeterWidth * mapScale;
  const mapPixelHeight = mapMeterHeight * mapScale;

  mapOffsetX = (canvasWidth - mapPixelWidth) / 2;
  mapOffsetY = (canvasHeight - mapPixelHeight) / 2;

  // Draw map area background and border
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(mapOffsetX, mapOffsetY, mapPixelWidth, mapPixelHeight);
  ctx.strokeStyle = '#cccccc';
  ctx.strokeRect(mapOffsetX, mapOffsetY, mapPixelWidth, mapPixelHeight);

  if (layout.entities && Array.isArray(layout.entities)) {
    layout.entities.forEach(entity => {
      if (entity.type === 'polyline' && Array.isArray(entity.points) && entity.points.length > 0) {
        ctx.beginPath();
        entity.points.forEach((point, index) => {
          const pixelX = mapOffsetX + point.x * mapScale;
          const pixelY = mapOffsetY + (mapMeterHeight - point.y) * mapScale;
          if (index === 0) ctx.moveTo(pixelX, pixelY);
          else ctx.lineTo(pixelX, pixelY);
        });
        ctx.strokeStyle = entity.strokeColor || '#555555';
        ctx.lineWidth = entity.lineWidth || 1.5;
        if (entity.closed) ctx.closePath();
        ctx.stroke();
         if (entity.fill || entity.fillColor) {
            ctx.fillStyle = entity.fillColor || 'rgba(200, 200, 200, 0.3)';
            ctx.fill();
        }
      }
    });
  }

  beaconsToDraw.forEach(beacon => {
    if (typeof beacon.x !== 'number' || typeof beacon.y !== 'number') return;
    const beaconPixelX = mapOffsetX + beacon.x * mapScale;
    const beaconPixelY = mapOffsetY + (mapMeterHeight - beacon.y) * mapScale;
    
    ctx.beginPath();
    ctx.arc(beaconPixelX, beaconPixelY, 8, 0, 2 * Math.PI);
    ctx.fillStyle = props.selectedBeaconForPlacement === beacon ? 'rgba(255, 0, 0, 0.5)' : 'rgba(0, 123, 255, 0.5)';
    ctx.fill();
    ctx.strokeStyle = props.selectedBeaconForPlacement === beacon ? '#FF0000' : '#007bff';
    ctx.stroke();

    ctx.fillStyle = '#000000';
    ctx.textAlign = 'center';
    ctx.fillText(beacon.displayName || beacon.macAddress || 'B', beaconPixelX, beaconPixelY - 10);
  });
  ctx.textAlign = 'start'; // Reset

  // Draw current local device position (if available)
  if (props.currentLocalDevicePosition && 
      typeof props.currentLocalDevicePosition.x === 'number' && 
      typeof props.currentLocalDevicePosition.y === 'number') {
    const pos = props.currentLocalDevicePosition;
    ctx.beginPath();
    // Style for local device position marker
    ctx.arc(pos.x * mapScale, pos.y * mapScale, 7, 0, 2 * Math.PI, false);
    ctx.fillStyle = 'rgba(0, 123, 255, 0.8)'; // Blue, slightly transparent
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(0, 80, 180, 1)'; // Darker blue outline
    ctx.stroke();

    // Optional: Draw accuracy circle if available
    if (typeof pos.accuracy === 'number' && pos.accuracy > 0) {
      ctx.beginPath();
      ctx.arc(pos.x * mapScale, pos.y * mapScale, pos.accuracy * mapScale, 0, 2 * Math.PI, false);
      ctx.strokeStyle = 'rgba(0, 123, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }
};

const pixelToMeter = (pixelX, pixelY) => {
    if (mapScale <= 0) return null;

    const relativePixelX = pixelX - mapOffsetX;
    const relativePixelY = pixelY - mapOffsetY;

    // Check if click is within the drawable map area bounds
    const mapDrawWidth = mapMeterWidth * mapScale;
    const mapDrawHeight = mapMeterHeight * mapScale;

    if (relativePixelX < 0 || relativePixelX > mapDrawWidth || 
        relativePixelY < 0 || relativePixelY > mapDrawHeight) {
        return null; // Click is outside map bounds
    }

    const meterX = relativePixelX / mapScale;
    const meterY = mapMeterHeight - (relativePixelY / mapScale); // Y-axis inversion
    
    return { x: parseFloat(meterX.toFixed(2)), y: parseFloat(meterY.toFixed(2)) };
};

const handleMapClick = (event) => {
  if (!props.selectedBeaconForPlacement || !currentMapLayout.value) {
    if (!props.selectedBeaconForPlacement) {
      // emit('requestBeaconSelection'); // This can be annoying if user just clicks map
      console.log("Map click with no beacon selected for placement.")
    }
    return;
  }

  const canvas = mapCanvasRef.value;
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  const meterCoords = pixelToMeter(x, y);
  if (meterCoords) {
    console.log('Map clicked at pixel:', x, y, 'Meter:', meterCoords);
    emit('configUpdated', {
      type: 'beaconUpdateCoordinates',
      // Send a comprehensive beacon identifier
      beaconIdentifier: {
        uuid: props.selectedBeaconForPlacement.uuid,
        major: props.selectedBeaconForPlacement.major,
        minor: props.selectedBeaconForPlacement.minor,
        // Include macAddress or deviceId if available and used for unique identification by parent
        macAddress: props.selectedBeaconForPlacement.macAddress,
        id: props.selectedBeaconForPlacement.id 
      },
      newCoordinates: meterCoords
    });
  } else {
    console.log('Map click outside of effective area or invalid scale.');
  }
};

// const exportCurrentMapConfig = () => { // Commented out as parent handles full export
//   if (!currentMapLayout.value) {
//     alert('没有地图数据可导出。');
//     return;
//   }
//   const configToExport = {
//     map: currentMapLayout.value,
//     beacons: displayBeacons.value, 
//     settings: {} // Settings are not managed here anymore
//   };
//   try {
//     const jsonString = JSON.stringify(configToExport, null, 2);
//     navigator.clipboard.writeText(jsonString).then(() => {
//       alert('当前地图和信标配置已复制到剪贴板。');
//     }).catch(err => {
//       console.error('复制到剪贴板失败: ', err);
//       alert('复制失败。请查看控制台。');
//       console.log('--- 当前地图配置内容 ---\n', jsonString);
//     });
//   } catch (e) {
//     alert('导出配置失败: JSON序列化错误。');
//     console.error('JSON序列化错误:', e);
//   }
// };

// Watch for external changes to props to redraw
watch(() => [props.configuredBeacons, currentMapLayout.value, props.selectedBeaconForPlacement, props.currentLocalDevicePosition], () => {
  redrawMap();
}, { deep: true });

watch(() => currentMapLayout.value, (newLayout, oldLayout) => {
  if (newLayout) {
    redrawMap();
  } else if (oldLayout && !newLayout) { // If map was present and now it's null
    redrawMap(); // Redraw to show empty state
  }
}, { deep: true });

// Watcher for local device position changes
watch(() => props.currentLocalDevicePosition, (newPosition, oldPosition) => {
  if (newPosition && (newPosition.x !== oldPosition?.x || newPosition.y !== oldPosition?.y)) {
    console.log('MapEditorTab: Local device position changed, redrawing map.', newPosition);
    redrawMap(); // Redraw the map to show the new position
  }
  // Also redraw if it becomes null from a valid position (to remove it)
  if (!newPosition && oldPosition) {
     redrawMap();
  }
}, { deep: true });

watch(() => props.initialMapData, (newMapData) => {
  if (newMapData) {
    console.log("MapEditorTab: initialMapData prop changed, updating currentMapLayout.", newMapData);
    currentMapLayout.value = JSON.parse(JSON.stringify(newMapData));
    redrawMap();
  } else {
    // If initialMapData becomes null (e.g. parent clears config), clear local map display
    currentMapLayout.value = null;
    redrawMap(); 
  }
}, { deep: true, immediate: true }); // immediate: true to run on component mount

watch(() => props.configuredBeacons, () => {
  // console.log("MapEditorTab: configuredBeacons prop changed.");
  redrawMap();
}, { deep: true });

watch(() => props.selectedBeaconForPlacement, () => {
  // console.log("MapEditorTab: selectedBeaconForPlacement prop changed.");
  redrawMap();
});

watch(() => props.currentLocalDevicePosition, () => {
  // console.log("MapEditorTab: currentLocalDevicePosition prop changed.");
  redrawMap(); 
});

// Watch for settings changes that might affect map display if any are introduced
watch(() => props.initialSettings, (newSettings) => {
  console.log("MapEditorTab: initialSettings prop changed.", newSettings);
  // If map rendering depends on any of these settings, trigger redraw
  // For example, if settings included grid visibility, colors, etc.
  // redrawMap(); // Uncomment if settings affect map appearance
}, { deep: true });

onMounted(() => {
  // initialMapData watcher with immediate:true handles initial load.
  // redrawMap(); // Call redrawMap in onMounted to ensure canvas is ready.
  // The watcher for initialMapData should handle the very first draw.
  if (currentMapLayout.value) { // Ensure a redraw if map data was set by immediate watcher
    redrawMap();
  }
  console.log("MapEditorTab: Mounted. Current map layout:", currentMapLayout.value);
  console.log("MapEditorTab: Received initial beacons:", props.configuredBeacons);
});

// Expose the loadConfiguration method to the parent component if needed
// (e.g., if parent wants to force-push a new config outside of normal prop flow, though prop flow is preferred)
defineExpose({ loadConfiguration, redrawMap });

</script>

<style scoped>
.map-editor-tab {
  display: flex;
  flex-direction: column;
}
.upload-section {
  margin-bottom: 1rem;
  padding: 0.5rem;
  border: 1px dashed #ccc;
  background-color: #f9f9f9;
}
.upload-section label {
  display: block;
  margin-bottom: 0.5rem;
}
canvas {
  border: 1px solid #000;
  margin-top: 10px;
  max-width: 100%; /* Make canvas responsive */
  height: auto; /* Maintain aspect ratio if width is constrained */
}
.info {
  font-size: 0.9em;
  color: #555;
  margin-top: 0.5rem;
}
button {
    margin-top: 10px;
}
</style> 
<template>
  <div class="map-editor-tab">
    <h3>Map File & Editing</h3>
    <div class="upload-section">
      <label for="mapFile">Upload Configuration File (JSON) - includes map, beacons, and settings:</label>
      <input type="file" id="mapFile" @change="handleFullConfigFileUpload" accept=".json" />
      <!-- <p class="info">When you upload a full configuration file here, it will update the application's current master configuration.</p> -->
    </div>

    <div v-if="currentMapLayout">
      <p>
        Map: {{ currentMapLayout.name || 'Unnamed' }} 
        ({{ currentMapLayout.width ? currentMapLayout.width.toFixed(1) : 'N/A' }}m x 
        {{ currentMapLayout.height ? currentMapLayout.height.toFixed(1) : 'N/A' }}m)
      </p>
      <canvas ref="mapCanvasRef" width="600" height="400" @click="handleMapClick"></canvas>
      
      <div v-if="showPlacementConfirmation && selectedBeaconForPlacement && pendingPlacementCoordinates" class="placement-confirmation">
        <p>Place beacon '{{ selectedBeaconForPlacement.displayName }}' at X: {{ pendingPlacementCoordinates.x.toFixed(2) }}, Y: {{ pendingPlacementCoordinates.y.toFixed(2) }}?</p>
        <button @click="confirmBeaconPlacement">Confirm</button>
        <button @click="cancelBeaconPlacement">Cancel</button>
      </div>

      <p class="info">Hint: {{ selectedBeaconForPlacement ? (showPlacementConfirmation ? 'Confirm or cancel the pending placement above.' : 'Click on the map to place beacon: ' + selectedBeaconForPlacement.displayName) : 'Select a beacon from the Beacon Management tab, then click on the map here to place it.'.trim() }}</p>
    </div>
    <p v-else>
      <!-- Please upload a valid JSON configuration file, or ensure a configuration is loaded from the server. -->
    </p>
    <!-- <p class="info">Hint: Full configuration import/export is available in the main action bar of the parent configuration page.</p> -->
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, nextTick } from 'vue';

const padding = 20; // Define padding here
const mapPixelWidth = ref(0); // Define as ref
const mapPixelHeight = ref(0); // Define as ref

const pendingPlacementCoordinates = ref(null); // {x, y} in map meters
const showPlacementConfirmation = ref(false);
const beaconUnderPlacementInternal = ref(null); // To store the beacon being actively placed

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
  },
  processUploadedMapConfig: Function
});

const emit = defineEmits(['mapLoaded', 'configUpdated', 'requestBeaconSelection', 'beacon-coordinates-updated', 'placement-confirmed']);

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
        if (props.processUploadedMapConfig) {
          console.log("[MapEditorTab] Calling props.processUploadedMapConfig...");
          props.processUploadedMapConfig(JSON.parse(JSON.stringify(jsonData)));
          alert('Configuration file has been successfully uploaded and sent to the main configuration for processing (via prop function).');
        } else {
          console.warn("[MapEditorTab] processUploadedMapConfig prop not provided. Falling back to $emit mapLoaded (if active).");
          emit('mapLoaded', JSON.parse(JSON.stringify(jsonData))); 
          alert('Configuration file has been successfully uploaded and sent to the main configuration for processing (via event).');
        }
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

// Canvas drawing parameters
let mapScale = 1;
let mapOffsetX = 0;
let mapOffsetY = 0;
let mapMeterWidth = 0;
let mapMeterHeight = 0;
const GRID_COLOR = '#CCCCCC'; // Darker grid color
const GRID_LINE_WIDTH = 0.5;

const redrawMap = () => {
  const canvas = mapCanvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const layout = currentMapLayout.value;
  const beaconsToDraw = displayBeacons.value;

  const canvasWidth = canvas.width;
  const canvasHeight = canvas.height;

  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  if (!layout || typeof layout.width !== 'number' || typeof layout.height !== 'number') {
    ctx.fillStyle = '#555';
    ctx.textAlign = 'center';
    ctx.font = '16px Arial';
    ctx.fillText("Map data is invalid or not loaded.", canvasWidth / 2, canvasHeight / 2);
    ctx.textAlign = 'start';
    return;
  }

  mapMeterWidth = layout.width;
  mapMeterHeight = layout.height;
  const padding = 20; // Padding around the map within the canvas

  const tempScaleX = (canvasWidth - 2 * padding) / mapMeterWidth;
  const tempScaleY = (canvasHeight - 2 * padding) / mapMeterHeight;
  mapScale = Math.min(tempScaleX, tempScaleY);
  if (mapScale <= 0) mapScale = 1;

  mapPixelWidth.value = mapMeterWidth * mapScale;
  mapPixelHeight.value = mapMeterHeight * mapScale;

  mapOffsetX = (canvasWidth - mapPixelWidth.value) / 2;
  mapOffsetY = (canvasHeight - mapPixelHeight.value) / 2;

  // Draw map area background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(mapOffsetX, mapOffsetY, mapPixelWidth.value, mapPixelHeight.value);

  // --- Draw Grid ---
  ctx.strokeStyle = GRID_COLOR;
  ctx.lineWidth = GRID_LINE_WIDTH;
  ctx.beginPath();
  // Vertical lines
  for (let x = 0; x <= mapMeterWidth; x++) { // Iterate for each meter line
    const pixelX = mapOffsetX + x * mapScale;
    ctx.moveTo(pixelX, mapOffsetY);
    ctx.lineTo(pixelX, mapOffsetY + mapPixelHeight.value);
  }
  // Horizontal lines
  for (let y = 0; y <= mapMeterHeight; y++) { // Iterate for each meter line
    const pixelY = mapOffsetY + y * mapScale; // y for canvas is top-down, so this works directly
    ctx.moveTo(mapOffsetX, pixelY);
    ctx.lineTo(mapOffsetX + mapPixelWidth.value, pixelY);
  }
  ctx.stroke();
  // --- End Grid Draw ---

  // Draw map border (over the grid, slightly thicker or different color if needed)
  ctx.strokeStyle = '#aaaaaa'; // Slightly darker border than grid
  ctx.lineWidth = 1;
  ctx.strokeRect(mapOffsetX, mapOffsetY, mapPixelWidth.value, mapPixelHeight.value);

  // Draw entities (polylines, etc.)
  if (layout.entities && Array.isArray(layout.entities)) {
    layout.entities.forEach(entity => {
      if (entity.type === 'polyline' && Array.isArray(entity.points) && entity.points.length > 0) {
        ctx.beginPath();
        entity.points.forEach((point, index) => {
          const pixelX = mapOffsetX + point.x * mapScale;
          // Y is inverted: map (0,0) is bottom-left, canvas (0,0) is top-left
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

  // Draw beacons
  beaconsToDraw.forEach(beacon => {
    if (typeof beacon.x !== 'number' || typeof beacon.y !== 'number') return;
    const beaconPixelX = mapOffsetX + beacon.x * mapScale;
    const beaconPixelY = mapOffsetY + (mapMeterHeight - beacon.y) * mapScale;
    
    const isSelectedForPlacement = props.selectedBeaconForPlacement && props.selectedBeaconForPlacement.deviceId === beacon.deviceId && props.selectedBeaconForPlacement.uuid === beacon.uuid;

    ctx.beginPath();
    ctx.arc(beaconPixelX, beaconPixelY, 8, 0, 2 * Math.PI);
    ctx.fillStyle = isSelectedForPlacement ? 'rgba(255, 165, 0, 0.7)' : 'rgba(0, 123, 255, 0.5)'; // Orange if selected for placement
    ctx.fill();
    ctx.strokeStyle = isSelectedForPlacement ? '#FFA500' : '#007bff';
    ctx.stroke();

    ctx.fillStyle = '#000000';
    ctx.textAlign = 'center';
    ctx.fillText(beacon.displayName || beacon.deviceId || 'B', beaconPixelX, beaconPixelY - 10);
  });
  ctx.textAlign = 'start'; // Reset text align

  // Draw pending placement marker
  if (showPlacementConfirmation.value && pendingPlacementCoordinates.value && props.selectedBeaconForPlacement) {
    const tempX = mapOffsetX + pendingPlacementCoordinates.value.x * mapScale;
    const tempY = mapOffsetY + (mapMeterHeight - pendingPlacementCoordinates.value.y) * mapScale;
    ctx.beginPath();
    ctx.arc(tempX, tempY, 9, 0, 2 * Math.PI); // Slightly larger or different style
    ctx.fillStyle = 'rgba(0, 255, 0, 0.6)'; // Green for pending
    ctx.fill();
    ctx.strokeStyle = '#00FF00';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = '#000';
    ctx.textAlign = 'center';
    // Display beacon name if available, otherwise a question mark
    const beaconName = props.selectedBeaconForPlacement.displayName || 'B?';
    ctx.fillText(beaconName, tempX, tempY + 3); // Centered text, adjust Y for vertical alignment
    ctx.textAlign = 'start';
  }

  // Draw current local device position (if available)
  if (props.currentLocalDevicePosition && 
      typeof props.currentLocalDevicePosition.x === 'number' && 
      typeof props.currentLocalDevicePosition.y === 'number') {
    const pos = props.currentLocalDevicePosition;
    const pixelX = mapOffsetX + pos.x * mapScale;
    const pixelY = mapOffsetY + (mapMeterHeight - pos.y) * mapScale;

    ctx.beginPath();
    ctx.arc(pixelX, pixelY, 7, 0, 2 * Math.PI, false);
    ctx.fillStyle = 'rgba(40, 167, 69, 0.8)'; // Green for current position
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(23, 111, 45, 1)'; 
    ctx.stroke();

    if (typeof pos.accuracy === 'number' && pos.accuracy > 0) {
      ctx.beginPath();
      ctx.arc(pixelX, pixelY, pos.accuracy * mapScale, 0, 2 * Math.PI, false);
      ctx.strokeStyle = 'rgba(40, 167, 69, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  // If a beacon is selected for placement, give a hint or visual cue on cursor (CSS might be better)
  if (props.selectedBeaconForPlacement && !showPlacementConfirmation.value) {
    canvas.style.cursor = 'crosshair';
  } else {
    canvas.style.cursor = 'default';
  }
};

const handleMapClick = (event) => {
  if (!props.selectedBeaconForPlacement || !currentMapLayout.value || !mapCanvasRef.value || showPlacementConfirmation.value) {
    // If already showing confirmation, don't process another click until it's resolved
    return;
  }

  // Capture the beacon that is about to be placed
  beaconUnderPlacementInternal.value = JSON.parse(JSON.stringify(props.selectedBeaconForPlacement));

  const canvas = mapCanvasRef.value;
  const rect = canvas.getBoundingClientRect();
  
  // Click position relative to the displayed canvas element (CSS pixels)
  const cssPixelX = event.clientX - rect.left;
  const cssPixelY = event.clientY - rect.top;

  // Convert CSS pixel click to canvas buffer pixel click
  // This accounts for any scaling of the canvas element by CSS (e.g., max-width: 100%)
  const bufferPixelX = cssPixelX * (canvas.width / rect.width);
  const bufferPixelY = cssPixelY * (canvas.height / rect.height);

  // Check if click (in buffer pixels) is within the drawable map area
  // mapOffsetX, mapPixelWidth.value are in buffer pixels for the map content itself
  // The padding/2 allows clicking slightly outside the strict map border if desired for easier interaction.
  if (bufferPixelX >= mapOffsetX - padding/2 && bufferPixelX <= mapOffsetX + mapPixelWidth.value + padding/2 &&
      bufferPixelY >= mapOffsetY - padding/2 && bufferPixelY <= mapOffsetY + mapPixelHeight.value + padding/2) {

    // Convert buffer pixel coordinates to map meter coordinates
    const mapX = (bufferPixelX - mapOffsetX) / mapScale;
    const mapY = mapMeterHeight - ((bufferPixelY - mapOffsetY) / mapScale); // Invert Y-axis for map coordinates

    console.log(`Map clicked CSS (X:${cssPixelX.toFixed(2)}, Y:${cssPixelY.toFixed(2)}), Buffer (X:${bufferPixelX.toFixed(2)}, Y:${bufferPixelY.toFixed(2)}), converted to map (X:${mapX.toFixed(2)}, Y:${mapY.toFixed(2)})`);

    pendingPlacementCoordinates.value = { x: parseFloat(mapX.toFixed(2)), y: parseFloat(mapY.toFixed(2)) };
    showPlacementConfirmation.value = true;
    redrawMap(); 
  } else {
    // console.log('Clicked outside effective map area.');
  }
};

const confirmBeaconPlacement = () => {
  if (!beaconUnderPlacementInternal.value || !pendingPlacementCoordinates.value) {
    console.warn("[MapEditorTab] confirmBeaconPlacement called without beaconUnderPlacementInternal or pendingCoordinates.");
    return;
  }

  const updatedBeacon = { 
    ...beaconUnderPlacementInternal.value, 
    x: pendingPlacementCoordinates.value.x,
    y: pendingPlacementCoordinates.value.y
  };
  emit('beacon-coordinates-updated', updatedBeacon);
  
  pendingPlacementCoordinates.value = null;
  showPlacementConfirmation.value = false;
  beaconUnderPlacementInternal.value = null; // Clear the internally held beacon
  emit('placement-confirmed');
  // Parent should set selectedBeaconForPlacement to null after this, which will trigger redraw for cursor.
  // Or redraw explicitly if needed: redrawMap(); 
};

const cancelBeaconPlacement = () => {
  pendingPlacementCoordinates.value = null;
  showPlacementConfirmation.value = false;
  beaconUnderPlacementInternal.value = null; // Clear the internally held beacon
  redrawMap(); // Redraw to remove temporary marker and reset cursor
};

// Watch for external changes to props to redraw
watch(() => [props.configuredBeacons, currentMapLayout.value, props.selectedBeaconForPlacement, props.currentLocalDevicePosition, showPlacementConfirmation.value], () => {
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

watch(() => props.configuredBeacons, (newBeacons, oldBeacons) => {
  // console.log('[MapEditorTab] Configured beacons prop changed. Redrawing map.');
  redrawMap();
}, { deep: true });

watch(() => props.selectedBeaconForPlacement, (newSelection, oldSelection) => {
  // console.log('[MapEditorTab] Selected beacon for placement prop changed.');
  if (!newSelection) {
    // If beacon selection is cleared (e.g., after placement, or by parent)
    // ensure any pending local placement state in this component is also cleared.
    cancelBeaconPlacement(); 
  }
  redrawMap(); // Always redraw to reflect selection changes (highlighting) or clearing.
}, { deep: true });

watch(() => props.currentLocalDevicePosition, () => {
    redrawMap();
});

// Watch for settings changes that might affect map display if any are introduced
watch(() => props.initialSettings, (newSettings) => {
  console.log("MapEditorTab: initialSettings prop changed.", newSettings);
}, { deep: true });

onMounted(async () => { // Make onMounted async
  // initialMapData watcher with immediate:true handles initial map layout setup.
  // We wait for the next tick to ensure the canvas element is definitely in the DOM and
  // other reactive dependencies like currentMapLayout (set by initialMapData watcher) are settled.
  await nextTick(); 
  if (mapCanvasRef.value) { // Also ensure canvas is available
    if (currentMapLayout.value) {
      console.log("MapEditorTab: onMounted - currentMapLayout is present, calling redrawMap.");
      redrawMap();
    } else {
      console.log("MapEditorTab: onMounted - currentMapLayout is NOT present yet. Map will be drawn by watcher.");
      // If map is not loaded yet, the watcher for initialMapData will call redrawMap when it is.
    }
  } else {
    console.warn("MapEditorTab: onMounted - mapCanvasRef is not available.");
  }
  console.log("MapEditorTab: Mounted. Initial currentMapLayout state evaluated in onMounted:", currentMapLayout.value ? { ...currentMapLayout.value } : null);
  console.log("MapEditorTab: Received initial beacons in onMounted:", props.configuredBeacons ? JSON.parse(JSON.stringify(props.configuredBeacons)): null);
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

.placement-confirmation {
  margin-top: 10px;
  padding: 10px;
  background-color: #e7f3fe;
  border: 1px solid #d0eaff;
  border-radius: 4px;
}
.placement-confirmation p {
  margin-top: 0;
  margin-bottom: 8px;
}
.placement-confirmation button {
  margin-right: 8px;
}
</style> 
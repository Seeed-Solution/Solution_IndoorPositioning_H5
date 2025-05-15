<!-- web/src/components/MapView.vue -->
<template>
  <div class="map-container">
    <div class="map-controls">
      <button @click="toggleTrails" class="button-secondary map-trail-toggle-btn">
        <i :class="['fas', localShowTrails ? 'fa-eye-slash' : 'fa-eye']"></i> {{ localShowTrails ? 'Hide' : 'Show' }} Trails
      </button>
    </div>
    <canvas ref="mapCanvas" :width="canvasWidth" :height="canvasHeight" style="border: 1px solid #ccc;"></canvas>
    <div v-if="config && config.map" class="map-info">
      Map Dimensions: {{ config.map.width.toFixed(1) }}m x {{ config.map.height.toFixed(1) }}m
    </div>
    <div v-else class="map-info">
      Load configuration to display map.
    </div>
    <!-- Trackers will be drawn on the canvas -->
  </div>
</template>

<script setup>
import { ref, onMounted, watch, defineEmits } from 'vue';

const props = defineProps({
  config: {
    type: Object,
    default: null
  },
  trackers: {
    type: Array,
    default: () => []
  },
  initialShowTrails: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['trails-toggled']);

const mapCanvas = ref(null);
const canvasWidth = ref(800); // Default canvas width
const canvasHeight = ref(600); // Default canvas height
const localShowTrails = ref(props.initialShowTrails); // Initialize with prop

// Watch for prop changes to update localShowTrails
watch(() => props.initialShowTrails, (newValue) => {
  localShowTrails.value = newValue;
});

const toggleTrails = () => {
  localShowTrails.value = !localShowTrails.value;
  emit('trails-toggled', localShowTrails.value);
};

const drawMap = (ctx) => {
  if (!props.config || !props.config.map || !ctx) {
    console.warn("[MapView] Attempted to drawMap without valid config.map data.");
    if (ctx) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    }
    return;
  }

  const { width: mapWidthMeters, height: mapHeightMeters, entities } = props.config.map;
  const beacons = props.config.beacons || [];

  // Ensure canvas internal drawing buffer matches these dimensions.
  ctx.canvas.width = canvasWidth.value;
  ctx.canvas.height = canvasHeight.value;

  // Calculate the dimensions for the 80% content area
  const contentAreaWidth = canvasWidth.value * 0.9;
  const contentAreaHeight = canvasHeight.value * 0.9;

  // Calculate scale to fit map into the content area, maintaining aspect ratio
  let currentScale;
  if (mapWidthMeters <= 0 || mapHeightMeters <= 0) {
    // Avoid division by zero or negative scales if map dimensions are invalid
    currentScale = 1; 
  } else {
    const scaleX = contentAreaWidth / mapWidthMeters;
    const scaleY = contentAreaHeight / mapHeightMeters;
    currentScale = Math.min(scaleX, scaleY);
  }
  
  // Prevent scale from being zero or negative if map dimensions are very large or contentArea is small
  if (currentScale <= 0) {
      currentScale = 1; // Fallback to a minimal positive scale
  }


  // Calculate the actual pixel dimensions of the scaled map content
  const renderedMapWidth = mapWidthMeters * currentScale;
  const renderedMapHeight = mapHeightMeters * currentScale;

  // Calculate offsets to center the scaled map content within the canvas
  const offsetX = (canvasWidth.value - renderedMapWidth) / 2;
  const offsetY = (canvasHeight.value - renderedMapHeight) / 2;

  // Clear canvas
  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);

  // --- Draw Map Entities ---
  ctx.save();
  // Translate to the bottom-left corner of the centered content box, then flip Y
  ctx.translate(offsetX, canvasHeight.value - offsetY);
  ctx.scale(1, -1);

  entities.forEach(entity => {
    if (entity.type === 'polyline' && entity.points && entity.points.length > 0) {
      ctx.beginPath();
      ctx.strokeStyle = entity.color || '#333333';
      // ctx.lineWidth = (entity.lineWidth || 1) / currentScale; // If line width is in world units
      ctx.lineWidth = entity.lineWidth || 1; // Assuming line width is in pixels

      const startPoint = entity.points[0];
      ctx.moveTo(startPoint[0] * currentScale, startPoint[1] * currentScale);

      for (let i = 1; i < entity.points.length; i++) {
        ctx.lineTo(entity.points[i][0] * currentScale, entity.points[i][1] * currentScale);
      }

      if (entity.closed) {
        ctx.closePath();
      }
      ctx.stroke();
    }
    // Add drawing logic for other entity types if needed (e.g., circles, rectangles)
  });

   // --- Draw Beacons ---
   beacons.forEach(beacon => {
    const beaconX = beacon.x * currentScale;
    const beaconY = beacon.y * currentScale;
    ctx.beginPath();
    ctx.arc(beaconX, beaconY, 5, 0, 2 * Math.PI); // Draw beacon as a small circle (radius 5px)
    ctx.fillStyle = 'orange';
    ctx.fill();
    ctx.fillStyle = 'black';
    ctx.font = '10px Arial';
     // Draw text upright despite flipped context
    ctx.save();
    ctx.translate(beaconX, beaconY);
    ctx.scale(1, -1); // Flip text back
    ctx.fillText(beacon.name || `B(${beacon.major},${beacon.minor})`, 8, 4);
    ctx.restore();
  });

   // --- Draw Trackers ---
   props.trackers.forEach(tracker => {
       if (tracker.x !== null && tracker.y !== null) {
           const trackerX = tracker.x * currentScale;
           const trackerY = tracker.y * currentScale;
           ctx.beginPath();
           ctx.arc(trackerX, trackerY, 7, 0, 2 * Math.PI); // Draw tracker as a slightly larger circle
           ctx.fillStyle = 'blue';
           ctx.fill();
           ctx.fillStyle = 'white';
           ctx.font = 'bold 10px Arial';
           ctx.textAlign = 'center';
           ctx.textBaseline = 'middle';
           // Draw text upright despite flipped context
           ctx.save();
           ctx.translate(trackerX, trackerY);
           ctx.scale(1, -1); // Flip text back
           // Display first few chars of trackerId inside the circle
           ctx.fillText(tracker.trackerId.substring(0, 3), 0, 0);
           ctx.restore();
       }
   });

  // --- Draw Tracker Trails (if enabled) ---
  if (localShowTrails.value) {
    props.trackers.forEach(tracker => {
      if (tracker.position_history && tracker.position_history.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(0, 0, 255, 0.3)'; // Light blue, semi-transparent
        ctx.lineWidth = 2; // Thinner than current tracker dot
        
        // Move to the oldest point in the history for this tracker
        const firstPoint = tracker.position_history[0];
        ctx.moveTo(firstPoint[0] * currentScale, firstPoint[1] * currentScale);
        
        // Draw lines to subsequent points
        for (let i = 1; i < tracker.position_history.length; i++) {
          const point = tracker.position_history[i];
          ctx.lineTo(point[0] * currentScale, point[1] * currentScale);
        }
        ctx.stroke();
      }
    });
  }

  ctx.restore(); // Restore original context state
};

onMounted(() => {
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) {
    drawMap(ctx);
  }
});

// Watch for changes in config, trackers, or trail visibility and redraw
watch([() => props.config, () => props.trackers, localShowTrails], () => {
   const ctx = mapCanvas.value?.getContext('2d');
   if (ctx) {
       drawMap(ctx);
   }
}, { deep: true });

</script>

<style scoped>
.map-container {
  position: relative;
  display: inline-block; /* Or use flex/grid for layout */
}

.map-controls {
  position: absolute;
  top: 5px; /* Adjust as needed */
  right: 5px; /* Adjust as needed */
  z-index: 10;
  display: flex;
  gap: 5px;
}

.map-trail-toggle-btn {
  padding: 6px 10px;
  font-size: 0.85em;
  background-color: rgba(255, 255, 255, 0.7);
  border: 1px solid #ccc;
  color: #333;
}
.map-trail-toggle-btn:hover {
  background-color: rgba(240, 240, 240, 0.8);
}

.map-info {
    position: absolute;
    top: 5px;
    left: 5px;
    background-color: rgba(255, 255, 255, 0.7);
    padding: 5px;
    border-radius: 3px;
    font-size: 0.9em;
}
canvas {
    display: block; /* Prevents extra space below canvas */
}
</style> 
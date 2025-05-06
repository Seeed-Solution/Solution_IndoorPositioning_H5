<!-- web/src/components/MapView.vue -->
<template>
  <div class="map-container">
    <canvas ref="mapCanvas" :width="canvasWidth" :height="canvasHeight" style="border: 1px solid #ccc;"></canvas>
    <div v-if="config" class="map-info">
      Map Dimensions: {{ config.mapInfo.width.toFixed(1) }}m x {{ config.mapInfo.height.toFixed(1) }}m
    </div>
    <div v-else class="map-info">
      Load configuration to display map.
    </div>
    <!-- Trackers will be drawn on the canvas -->
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';

const props = defineProps({
  config: {
    type: Object,
    default: null
  },
  trackers: {
    type: Array,
    default: () => []
  }
});

const mapCanvas = ref(null);
const canvasWidth = ref(800); // Default or calculated width
const canvasHeight = ref(600); // Default or calculated height
const scale = ref(30); // Pixels per meter (adjust as needed)

const drawMap = (ctx) => {
  if (!props.config || !ctx) return;

  const { width: mapWidthMeters, height: mapHeightMeters, entities } = props.config.mapInfo;
  const beacons = props.config.beacons || [];

  // Calculate canvas size based on map dimensions and scale
  canvasWidth.value = mapWidthMeters * scale.value;
  canvasHeight.value = mapHeightMeters * scale.value;

  // Wait for next tick for canvas dimensions to update before drawing
  ctx.canvas.width = canvasWidth.value;
  ctx.canvas.height = canvasHeight.value;


  // Clear canvas
  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);

  // --- Draw Map Entities ---
  ctx.save();
  // Flip Y-axis because canvas origin (0,0) is top-left, map origin is bottom-left
  ctx.translate(0, canvasHeight.value);
  ctx.scale(1, -1);

  entities.forEach(entity => {
    if (entity.type === 'polyline' && entity.points && entity.points.length > 0) {
      ctx.beginPath();
      ctx.strokeStyle = entity.color || '#333333';
      ctx.lineWidth = (entity.lineWidth || 1) / scale.value; // Adjust line width based on scale? Or keep fixed pixel width? Let's try fixed for now.
      ctx.lineWidth = entity.lineWidth || 1;

      const startPoint = entity.points[0];
      ctx.moveTo(startPoint[0] * scale.value, startPoint[1] * scale.value);

      for (let i = 1; i < entity.points.length; i++) {
        ctx.lineTo(entity.points[i][0] * scale.value, entity.points[i][1] * scale.value);
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
    const beaconX = beacon.x * scale.value;
    const beaconY = beacon.y * scale.value;
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
           const trackerX = tracker.x * scale.value;
           const trackerY = tracker.y * scale.value;
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


  ctx.restore(); // Restore original context state
};

onMounted(() => {
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) {
    drawMap(ctx);
  }
});

// Watch for changes in config or trackers and redraw
watch([() => props.config, () => props.trackers], () => {
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
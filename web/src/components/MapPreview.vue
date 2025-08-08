<!-- web/src/components/MapPreview.vue -->
<template>
  <div class="map-preview-container">
    <div class="content-columns">
      <div class="map-view-wrapper">
        <div class="map-container">
          <canvas ref="mapCanvas" :width="canvasWidth" :height="canvasHeight" style="border: 1px solid #ccc;"></canvas>
          <div v-if="config && config.map" class="map-info" style="display: none;">
            Map Dimensions: {{ config.map.width.toFixed(1) }}m x {{ config.map.height.toFixed(1) }}m
          </div>
          <div v-else class="map-info" style="display: none;">
            Load configuration to display map.
          </div>
        </div>
      </div>
      <aside class="tracker-list-aside">
        <div class="tracker-list-header">
          <h4>Trackers ({{ trackerList.length }})</h4>
          <button @click="toggleTrails" class="button-secondary map-trail-toggle-btn">
            <i :class="['fas', localShowTrails ? 'fa-eye-slash' : 'fa-eye']"></i> {{ localShowTrails ? 'Hide' : 'Show' }} Trails
          </button>
        </div>
        <ul v-if="trackerList.length > 0">
          <li v-for="tracker in trackerList" :key="tracker.trackerId" class="tracker-item" :class="{ 'tracker-sos': tracker.sos }">
            <strong>{{ tracker.trackerId }}</strong>
            
            <!-- SOS Status -->
            <div v-if="tracker.sos" class="tracker-sos-status">
              🚨 SOS ALERT
              <div v-if="tracker.sos_happen" class="tracker-sos-time">
                {{ new Date(tracker.sos_happen).toLocaleString() }}
              </div>
            </div>
            
            <!-- Position Data -->
            <div v-if="tracker.position && typeof tracker.position.x === 'number' && typeof tracker.position.y === 'number'" class="tracker-pos">
              X: {{ tracker.position.x.toFixed(2) }}, Y: {{ tracker.position.y.toFixed(2) }}
              <span v-if="tracker.position.accuracy && typeof tracker.position.accuracy === 'number'">, Acc: {{ tracker.position.accuracy.toFixed(2) }}m</span>
            </div>
            <div v-else class="tracker-pos-na">
              No position data
            </div>

            <!-- Meta Data -->
            <div class="tracker-meta-group">
              <div v-if="tracker.timestamp" class="tracker-meta-item">
                 Last seen: {{ new Date(tracker.timestamp).toLocaleTimeString() }}
              </div>
              <div v-if="tracker.last_detected_beacons && tracker.last_detected_beacons.length > 0" class="tracker-meta-item">
                Strongest RSSI: {{ Math.max(...tracker.last_detected_beacons.map(b => b.rssi)) }} dBm
                (Detected {{ tracker.last_detected_beacons.length }} beacon(s))
              </div>
              <div v-else-if="tracker.last_detected_beacons" class="tracker-meta-item">
                No beacons detected in last update.
              </div>
            </div>
          </li>
        </ul>
        <p v-else>No trackers received yet.</p>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, defineEmits, computed } from 'vue';

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

// 过滤出属于当前地图的 trackers（基于 map 字段）
const filteredTrackers = computed(() => {
    let allTrackers;
    if (Array.isArray(props.trackers)) {
        allTrackers = props.trackers;
    } else {
        allTrackers = Object.values(props.trackers || {});
    }

    if (!props.config?.map?.name || allTrackers.length === 0) {
        // console.log(`[FilteredTrackers] 返回空数组 - config.map.name: ${props.config?.map?.name}, trackers数量: ${allTrackers.length}`);
        return [];
    }
    
    const result = allTrackers.filter(tracker => {
        // 首先基于 map 字段过滤
        if (props.config.map.name === tracker.map) {
            console.log(`[FilteredTrackers] ${props.config.map.name} 存在 tracker: ${tracker.trackerId}`);
            return true;
        } else {
            console.log(`[FilteredTrackers] ${props.config.map.name} 跳过 tracker: ${tracker.trackerId} (map字段不匹配: tracker.map=${tracker.map})`);
            return false;
        }
    });
    
    console.log(`[FilteredTrackers] 过滤结果数量: ${result.length}`);
    return result;
});

// 再次过滤：基于 beacon 检测的 trackers
const trackerList = computed(() => {
    return filteredTrackers.value.sort((a, b) => (a.trackerId || '').localeCompare(b.trackerId || ''));
});
const canvasWidth = ref(600); // Default canvas width  
const canvasHeight = ref(450); // Default canvas height
const localShowTrails = ref(props.initialShowTrails); // Initialize with prop

// Watch for prop changes to update localShowTrails
watch(() => props.initialShowTrails, (newValue) => {
  localShowTrails.value = newValue;
});

const updateCanvasSize = () => {
  const mapContainer = mapCanvas.value?.parentElement;
  if (mapContainer) {
    const containerWidth = mapContainer.clientWidth;
    const containerHeight = mapContainer.clientHeight;
    
    // 计算可用空间，减少预留空间（因为隐藏了map-info）
    const availableWidth = Math.max(containerWidth - 20, 400); // 减少边距，最小宽度 400px
    const availableHeight = Math.max(containerHeight - 50, 300); // 减少上下元素空间，最小高度 300px
    
    // 直接使用可用空间，不强制固定宽高比
    canvasWidth.value = Math.floor(availableWidth);
    canvasHeight.value = Math.floor(availableHeight);
    
    // console.log(`[DEBUG] Canvas size updated:`, {
    //   containerWidth,
    //   containerHeight,
    //   availableWidth,
    //   availableHeight,
    //   canvasWidth: canvasWidth.value,
    //   canvasHeight: canvasHeight.value
    // });
  }
};

const toggleTrails = () => {
  localShowTrails.value = !localShowTrails.value;
  emit('trails-toggled', localShowTrails.value);
};

const isTrackerInCurrentMap = (tracker) => {
  console.log(`[Beacon检测] 检查 tracker: ${tracker.trackerId}`);
  
  if (!props.config || !props.config.beacons) {
    console.log(`[Beacon检测] props.config 或 beacons 为空`);
    return true; // 临时改为 true，先让所有通过第一层过滤的 tracker 都显示
  }
  
  if (!tracker.last_detected_beacons) {
    console.log(`[Beacon检测] tracker ${tracker.trackerId} 没有 last_detected_beacons 数据`);
    return true; // 临时改为 true，如果没有 beacon 数据就直接显示
  }
  
  const mapBeacons = props.config.beacons;
  const trackerBeacons = tracker.last_detected_beacons;
  
  const result = trackerBeacons.some(trackerBeacon => {
    return mapBeacons.some(mapBeacon => {
      const match = mapBeacon.macAddress.replace(":", "").toLowerCase() === trackerBeacon.macAddress.replace(":", "").toLowerCase();
      if (match) {
        console.log(`[Beacon检测] 匹配成功: ${mapBeacon.macAddress} === ${trackerBeacon.macAddress}`);
      }
      return match;
    });
  });
  
  console.log(`[Beacon检测] tracker ${tracker.trackerId} 检测结果: ${result}`);
  return result;
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
  
  // Calculate actual bounds of map data
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  entities.forEach(entity => {
    if (entity.points) {
      entity.points.forEach(point => {
        minX = Math.min(minX, point[0]);
        maxX = Math.max(maxX, point[0]);
        minY = Math.min(minY, point[1]);
        maxY = Math.max(maxY, point[1]);
      });
    }
  });
  
  // console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Data bounds:`, {
  //   minX, maxX, minY, maxY,
  //   dataWidth: maxX - minX,
  //   dataHeight: maxY - minY
  // });

  // Ensure canvas internal drawing buffer matches these dimensions.
  ctx.canvas.width = canvasWidth.value;
  ctx.canvas.height = canvasHeight.value;

  // Calculate the dimensions for the 80% content area
  const contentAreaWidth = canvasWidth.value * 0.9;
  const contentAreaHeight = canvasHeight.value * 0.9;

  // Use actual data bounds for scaling
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  
  // Calculate scale to fit map into the content area, maintaining aspect ratio
  let currentScale;
  if (dataWidth <= 0 || dataHeight <= 0) {
    // Avoid division by zero or negative scales if map dimensions are invalid
    currentScale = 1;
  } else {
    const scaleX = contentAreaWidth / dataWidth;
    const scaleY = contentAreaHeight / dataHeight;
    currentScale = Math.min(scaleX, scaleY);
  }

  // Prevent scale from being zero or negative if map dimensions are very large or contentArea is small
  if (currentScale <= 0) {
      currentScale = 1; // Fallback to a minimal positive scale
  }

  // Calculate the actual pixel dimensions of the scaled map content
  const renderedMapWidth = dataWidth * currentScale;
  const renderedMapHeight = dataHeight * currentScale;

  // Calculate offsets to center the scaled map content within the canvas
  const offsetX = (canvasWidth.value - renderedMapWidth) / 2;
  const offsetY = (canvasHeight.value - renderedMapHeight) / 2;
  
  // console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Canvas and offset values:`, {
  //   canvasWidth: canvasWidth.value,
  //   canvasHeight: canvasHeight.value,
  //   mapWidthMeters,
  //   mapHeightMeters,
  //   currentScale,
  //   renderedMapWidth,
  //   renderedMapHeight,
  //   offsetX,
  //   offsetY,
  //   translateX: offsetX,
  //   translateY: canvasHeight.value - offsetY
  // });
  
  // console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Entity count:`, entities.length);
  // if (entities.length > 0) {
  //   console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - First entity:`, entities[0]);
  // }

  // Clear canvas
  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);

  // --- Draw Map Entities ---
  ctx.save();
  // Translate to the bottom-left corner of the centered content box, then flip Y
  ctx.translate(offsetX, canvasHeight.value - offsetY);
  ctx.scale(1, -1);

  entities.forEach((entity, index) => {
    if (entity.type === 'polyline' && entity.points && entity.points.length > 0) {
      // if (index === 0) {
      //   console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - First entity points:`, entity.points.slice(0, 3));
      //   console.log(`[DEBUG] ${props.config?.map?.name || 'Unknown Map'} - Scaled points:`, entity.points.slice(0, 3).map(p => [p[0] * currentScale, p[1] * currentScale]));
      // }
      
      ctx.beginPath();
      ctx.strokeStyle = entity.color || '#333333';
      // ctx.lineWidth = (entity.lineWidth || 1) / currentScale; // If line width is in world units
      ctx.lineWidth = entity.lineWidth || 1; // Assuming line width is in pixels

      const startPoint = entity.points[0];
      ctx.moveTo((startPoint[0] - minX) * currentScale, (startPoint[1] - minY) * currentScale);

      for (let i = 1; i < entity.points.length; i++) {
        ctx.lineTo((entity.points[i][0] - minX) * currentScale, (entity.points[i][1] - minY) * currentScale);
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
    const beaconX = (beacon.x - minX) * currentScale;
    const beaconY = (beacon.y - minY) * currentScale;
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
    ctx.fillText(beacon.displayName || `B(${beacon.major},${beacon.minor})`, 8, 4);
    ctx.restore();
  });

   // --- Draw Trackers ---
   filteredTrackers.value.forEach(tracker => {
       if (tracker.position && tracker.position.x !== null && tracker.position.y !== null) {
           const trackerX = (tracker.position.x - minX) * currentScale;
           const trackerY = (tracker.position.y - minY) * currentScale;

           // Draw tracker circle with transparency
           ctx.beginPath();
           ctx.arc(trackerX, trackerY, 8, 0, 2 * Math.PI); // Slightly larger circle
           
           // Change color based on SOS status
           if (tracker.sos) {
             ctx.fillStyle = 'rgba(255, 0, 0, 0.8)'; // Red with 80% opacity for SOS
             ctx.strokeStyle = 'rgba(220, 0, 0, 1)'; // Darker red border for SOS
           } else {
             ctx.fillStyle = 'rgba(0, 123, 255, 0.7)'; // Blue with 70% opacity (normal)
             ctx.strokeStyle = 'rgba(0, 123, 255, 0.9)'; // Darker blue border (normal)
           }
           
           ctx.fill();

           // Add border for better visibility
           ctx.lineWidth = 2;
           ctx.stroke();

           // Draw text to the right of the circle
           ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'; // Dark text with slight transparency
           ctx.font = 'bold 11px Arial';
           ctx.textAlign = 'left';
           ctx.textBaseline = 'middle';

           // Draw text upright despite flipped context
           ctx.save();
           ctx.translate(trackerX + 12, trackerY); // Position text to the right of circle
           ctx.scale(1, -1); // Flip text back
           ctx.fillText(tracker.trackerId.substring(10), 0, 0); // Show more chars
           ctx.restore();

           console.log(`tracker(${tracker.trackerId}) 绘制成功`)
         return
       }
       console.log(`tracker(${tracker.trackerId}) 绘制失败, 无定位信息`)
   });

  // --- Draw Tracker Trails (if enabled) ---
  if (localShowTrails.value) {
    filteredTrackers.value.forEach(tracker => {
      if (tracker.position_history && tracker.position_history.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(0, 0, 255, 0.3)'; // Light blue, semi-transparent
        ctx.lineWidth = 2; // Thinner than current tracker dot

        // Move to the oldest point in the history for this tracker
        const firstPoint = tracker.position_history[0];
        ctx.moveTo((firstPoint[0] - minX) * currentScale, (firstPoint[1] - minY) * currentScale);

        // Draw lines to subsequent points
        for (let i = 1; i < tracker.position_history.length; i++) {
          const point = tracker.position_history[i];
          ctx.lineTo((point[0] - minX) * currentScale, (point[1] - minY) * currentScale);
        }
        ctx.stroke();
      }
    });
  }

  ctx.restore(); // Restore original context state
};

let resizeHandler;

onMounted(() => {
  updateCanvasSize();
  const ctx = mapCanvas.value?.getContext('2d');
  if (ctx) {
    drawMap(ctx);
  }
  
  // 监听窗口大小变化
  resizeHandler = () => {
    updateCanvasSize();
    const ctx = mapCanvas.value?.getContext('2d');
    if (ctx) {
      drawMap(ctx);
    }
  };
  window.addEventListener('resize', resizeHandler);
});

onUnmounted(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
  }
});

// Watch for changes in config, trackers, or trail visibility and redraw
watch([() => props.config, () => props.trackers, localShowTrails], () => {
   const ctx = mapCanvas.value?.getContext('2d');
   if (ctx) {
       drawMap(ctx);
   }
}, { deep: true });

// 暴露方法给父组件使用
defineExpose({
  isTrackerInCurrentMap
});

</script>

<style scoped>
.map-preview-container {
  width: 100%;
}

.content-columns {
  display: flex;
  gap: 10px;
}

.map-view-wrapper {
  flex-grow: 1;
  min-height: 450px;
  display: flex;
  flex-direction: column;
}

.tracker-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.map-container {
  position: relative;
  width: 100%;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.tracker-list-aside {
  width: 300px;
  flex-shrink: 0;
  background-color: #f9f9f9;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #eee;
  max-height: 500px;
  overflow-y: auto;
}

.tracker-list-aside h4 {
  margin: 0;
  color: #333;
}

.tracker-list-aside ul {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.tracker-item {
  padding: 8px;
  border-bottom: 1px solid #eee;
  font-size: 0.9em;
}

.tracker-item.tracker-sos {
  background-color: rgba(255, 0, 0, 0.1);
  border-left: 4px solid #ff0000;
}
.tracker-item:last-child {
  border-bottom: none;
}
.tracker-item strong {
  color: #0056b3; 
  display: block;
  margin-bottom: 3px;
}
.tracker-pos {
  color: #333;
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-pos-na {
  color: #777;
  font-style: italic;
  font-size: 0.95em;
  margin-bottom: 3px;
}
.tracker-meta-group {
  font-size: 0.85em;
  color: #555;
}
.tracker-meta-item {
  margin-top: 2px;
}

.tracker-sos-status {
  color: #ff0000;
  font-weight: bold;
  font-size: 0.9em;
  margin-bottom: 4px;
  padding: 2px 4px;
  background-color: rgba(255, 0, 0, 0.1);
  border-radius: 3px;
}

.tracker-sos-time {
  font-size: 0.8em;
  font-weight: normal;
  color: #666;
  margin-top: 2px;
}


.map-trail-toggle-btn {
  padding: 4px 8px;
  font-size: 0.75em;
  background-color: #fff;
  border: 1px solid #ccc;
  color: #333;
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}
.map-trail-toggle-btn:hover {
  background-color: #f0f0f0;
}

.map-info {
    position: absolute;
    top: 5px;
    left: 5px;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 5px 8px;
    border-radius: 3px;
    font-size: 0.85em;
    color: #666;
    border: 1px solid rgba(0, 0, 0, 0.1);
}
canvas {
    display: block; /* Prevents extra space below canvas */
    max-width: 100%;
    height: auto;
}
</style>
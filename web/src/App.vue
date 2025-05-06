<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import axios from 'axios';
import MapView from './components/MapView.vue'; // Corrected import path

const selectedFile = ref(null);
const uploadStatus = ref('idle'); // idle, uploading, success, error
const uploadError = ref('');
const configStatus = ref('idle'); // idle, loading, loaded, error
const currentConfig = ref(null);
const trackers = ref({}); // Use object for efficient updates by trackerId
const wsStatus = ref('disconnected');
const ws = ref(null);

const trackerList = computed(() => {
    // Convert tracker object to a sorted array for display
    return Object.values(trackers.value).sort((a, b) => a.trackerId.localeCompare(b.trackerId));
});


const handleFileChange = (event) => {
  selectedFile.value = event.target.files[0];
  uploadStatus.value = 'idle'; // Reset status on new file select
};

const uploadConfig = async () => {
  if (!selectedFile.value) return;

  uploadStatus.value = 'uploading';
  uploadError.value = '';
  const formData = new FormData();
  formData.append('file', selectedFile.value);

  try {
    // Adjust URL if your backend runs on a different port/host
    const response = await axios.post('/api/config', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    console.log('Upload response:', response.data);
    uploadStatus.value = 'success';
    // Optionally reload config after successful upload, or wait for WebSocket update
    fetchConfig();
  } catch (error) {
    console.error('Upload error:', error);
    uploadStatus.value = 'error';
    uploadError.value = error.response?.data?.detail || error.message || 'Unknown error';
     // Also set config status to error if upload fails, as config is likely stale/wrong
     configStatus.value = 'error';
     currentConfig.value = null;
  }
};

const fetchConfig = async () => {
    configStatus.value = 'loading';
    try {
        const response = await axios.get('/api/config');
        if (response.data) {
            currentConfig.value = response.data;
            configStatus.value = 'loaded';
            console.log("Config loaded:", currentConfig.value);
        } else {
             configStatus.value = 'idle'; // No config found on server
             currentConfig.value = null;
        }
    } catch (error) {
        console.error("Failed to fetch config:", error);
        configStatus.value = 'error';
        currentConfig.value = null;
    }
};


const connectWebSocket = () => {
    // Use ws:// or wss:// depending on your backend setup (HTTP vs HTTPS)
    // Adjust host/port if needed
    // Ensure the protocol matches the window's protocol for standard ports
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    ws.value = new WebSocket(wsUrl);
    wsStatus.value = 'connecting';

    ws.value.onopen = () => {
        wsStatus.value = 'connected';
        console.log('WebSocket connected');
        // Backend should send initial state on connect
    };

    ws.value.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            // console.log('WS Message:', message);

            if (message.type === 'initial_state') {
                const initialTrackers = {};
                message.data.forEach(tracker => {
                    initialTrackers[tracker.trackerId] = tracker;
                });
                trackers.value = initialTrackers;
                 console.log('Received initial tracker state:', trackers.value);
            } else if (message.type === 'tracker_update') {
                 // Update or add tracker data using trackerId as key
                 trackers.value = {
                    ...trackers.value,
                    [message.data.trackerId]: message.data
                 };
                 // console.log('Updated tracker:', message.data.trackerId);
            } else if (message.type === 'config_update') {
                currentConfig.value = message.data;
                configStatus.value = 'loaded';
                console.log('Received config update via WebSocket:', currentConfig.value);
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    };

    ws.value.onerror = (error) => {
        wsStatus.value = 'error';
        console.error('WebSocket error:', error);
    };

    ws.value.onclose = (event) => {
        wsStatus.value = 'disconnected';
        console.log('WebSocket disconnected:', event.reason || `Code ${event.code}`);
        // Optional: Attempt to reconnect after a delay
        // setTimeout(connectWebSocket, 5000);
    };
};

onMounted(() => {
  fetchConfig(); // Fetch initial config on load
  connectWebSocket(); // Connect WebSocket
});

onUnmounted(() => {
    if (ws.value) {
        ws.value.close();
    }
});

</script>

<template>
  <div id="app">
    <h1>Beacon Positioning System</h1>

    <div class="config-section">
      <h2>Configuration</h2>
      <div v-if="configStatus === 'loaded'" class="status success">
        Configuration loaded successfully. Signal Factor (n): {{ currentConfig?.settings?.signalPropagationFactor }}
      </div>
       <div v-else-if="configStatus === 'error'" class="status error">
        Failed to load configuration. Please upload a valid config.json.
      </div>
       <div v-else-if="configStatus === 'loading'" class="status">
        Loading configuration...
      </div>
      <div v-else class="status">
        No configuration loaded.
      </div>

      <input type="file" @change="handleFileChange" accept=".json" />
      <button @click="uploadConfig" :disabled="!selectedFile || uploadStatus === 'uploading'">
        {{ uploadStatus === 'uploading' ? 'Uploading...' : 'Upload Config' }}
      </button>
      <div v-if="uploadStatus === 'success'" class="status success">Upload successful!</div>
      <div v-if="uploadStatus === 'error'" class="status error">Upload failed: {{ uploadError }}</div>
    </div>

    <div class="map-section">
        <h2>Live Map</h2>
         <div class="status">WebSocket: {{ wsStatus }}</div>
        <MapView :config="currentConfig" :trackers="trackerList" />
    </div>

     <div class="tracker-list-section">
        <h2>Trackers ({{ trackerList.length }})</h2>
        <ul>
            <li v-for="tracker in trackerList" :key="tracker.trackerId">
                <strong>{{ tracker.trackerId }}</strong>:
                Pos ({{ tracker.x?.toFixed(2) ?? 'N/A' }}, {{ tracker.y?.toFixed(2) ?? 'N/A' }}) @ {{ new Date(tracker.last_update_time).toLocaleTimeString() }}
                <span v-if="tracker.last_detected_beacons.length > 0" class="beacon-details">
                    | Seeing Beacons: {{ tracker.last_detected_beacons.map(b => `${b.major}/${b.minor}(${b.rssi})`).join(', ') }}
                </span>
            </li>
        </ul>
    </div>

  </div>
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section, .map-section, .tracker-list-section {
  border: 1px solid #eee;
  padding: 15px;
  border-radius: 5px;
}

.config-section input[type="file"] {
    margin-right: 10px;
}
.config-section button {
    padding: 5px 10px;
    cursor: pointer;
}

.status {
    margin-top: 5px;
    font-size: 0.9em;
    padding: 5px;
    border-radius: 3px;
    margin-bottom: 10px; /* Added margin */
}
.status.success {
    color: green;
    background-color: #e6ffe6;
}
.status.error {
    color: red;
     background-color: #ffe6e6;
}

.tracker-list-section ul {
    list-style: none;
    padding: 0;
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid #f0f0f0; /* Added border */
    margin-top: 5px; /* Added margin */
}
.tracker-list-section li {
    margin-bottom: 5px;
    font-size: 0.9em;
    border-bottom: 1px dashed #eee;
    padding: 3px 5px; /* Added padding */
}
.beacon-details {
    font-size: 0.8em;
    color: #555;
    margin-left: 5px; /* Added margin */
}

/* Basic layout adjustments */
.map-section {
    /* Allow map to potentially take more space if needed */
    flex-grow: 1;
}

</style>

<template>
  <div class="beacon-manager-tab">
    <h3>Beacon List & Management</h3>
    <p>Manage fixed reference beacons. You can add, edit, delete beacons, or discover new ones via the local scanning service.</p>
    <p v-if="!hasMap" class="scan-status error">
      A map is required to configure and place beacons. Please go to the "Map Editor" tab to upload or define a map first.
    </p>
    
    <div class="actions-bar">
      <button @click="showAddBeaconModal" :disabled="isScanning || !isWebSocketConnected || !hasMap">Add New Beacon</button>
      <button @click="attemptStartScan" :disabled="isScanning || !isWebSocketConnected || !hasMap" style="margin-left: 10px;">
        {{ isScanning ? 'Scanning... (Click stop button below to abort)' : (isWebSocketConnected ? 'Scan via Local Service' : 'Local Service Offline') }}
      </button>
      <button v-if="isScanning" @click="attemptStopScan" style="margin-left: 10px; background-color: #dc3545;">Stop Scan</button>
    </div>
    <p v-if="scanStatusMessage" class="scan-status" :class="scanStatusType">{{ scanStatusMessage }}</p>

    <table v-if="configuredBeacons.length > 0">
      <thead>
        <tr>
          <th>Name</th>
          <th>UUID</th>
          <th>Major</th>
          <th>Minor</th>
          <th>X</th>
          <th>Y</th>
          <th>TxPower</th>
          <th>MAC/ID</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(beacon, index) in configuredBeacons" :key="beacon.uuid + '-' + beacon.major + '-' + beacon.minor">
          <td>{{ beacon.displayName }}</td>
          <td>{{ beacon.uuid }}</td>
          <td>{{ beacon.major }}</td>
          <td>{{ beacon.minor }}</td>
          <td>{{ beacon.x }}</td>
          <td>{{ beacon.y }}</td>
          <td>{{ beacon.txPower }}</td>
          <td>{{ beacon.macAddress || beacon.deviceId }}</td>
          <td class="actions-cell">
            <div class="beacon-actions-container">
              <button @click="showEditBeaconModal(index)" :disabled="isScanning || !isWebSocketConnected">Edit</button>
              <button @click="deleteBeacon(index)" :disabled="isScanning || !isWebSocketConnected">Delete</button>
              <!-- <button @click="selectBeaconForPlacement(beacon)" :disabled="isScanning || !isWebSocketConnected || !hasMap">Place on Map</button> -->
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!isScanning">No configured beacons yet. You can add them manually or scan for nearby ones (if local service is connected).</p>

    <div v-if="isScanning && scanResults.length === 0 && !scanStatusMessage.includes('Error') && !scanStatusMessage.includes('Failed')" class="scan-results-placeholder">
      <p><i class="fas fa-spinner fa-spin"></i> Actively scanning via local service... Ensure the service is running and Bluetooth is enabled on the host.</p>
      <p>Scan will run for about 15 seconds or until you stop it manually. Detected iBeacons will appear below.</p>
    </div>

    <div v-if="scanResults.length > 0" class="scan-results">
      <h4>Discovered Beacons ({{ scanResults.length }} unique):</h4>
      <ul>
        <li v-for="beacon in sortedScanResults" :key="beacon.id" class="scan-result-item">
          <div>
            <strong>{{ beacon.displayName || beacon.name || 'Unknown Device' }}</strong> (RSSI: {{ beacon.rssi }})<br>
            ID: {{ beacon.id }} <br>
            UUID: {{ beacon.uuid }}<br>
            Major: {{ beacon.major }}, Minor: {{ beacon.minor }}, TxPower: {{ beacon.txPower }}
          </div>
          <button @click="addScannedBeaconToForm(beacon)" :disabled="isBeaconAlreadyConfigured(beacon) || isScanning || !hasMap">
            {{ isBeaconAlreadyConfigured(beacon) ? 'Already Configured' : 'Add This Beacon' }}
          </button>
        </li>
      </ul>
    </div>
    <p v-if="!isScanning && userInitiatedScan && scanResults.length === 0 && !scanStatusMessage.value.includes('Error') && !scanStatusMessage.value.includes('Starting') && !scanStatusMessage.value.includes('Failed')" class="scan-status info">
      Scan complete. No new iBeacon devices found by local service.
    </p>

    <!-- Add/Edit Beacon Modal -->
    <div v-if="showBeaconModal" class="modal-overlay">
      <div class="modal-content">
        <h4>{{ beaconModalMode === 'add' ? 'Add New Beacon' : 'Edit Beacon' }}</h4>
        <form @submit.prevent="saveBeacon">
          <div>
            <label>Display Name:</label>
            <input type="text" v-model="editingBeacon.displayName" required />
          </div>
          <div>
            <label>UUID:</label>
            <input type="text" v-model="editingBeacon.uuid" required pattern="^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$" title="Please enter a standard UUID format, e.g., XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" />
          </div>
          <div>
            <label>Major:</label>
            <input type="number" v-model.number="editingBeacon.major" required min="0" max="65535"/>
          </div>
          <div>
            <label>Minor:</label>
            <input type="number" v-model.number="editingBeacon.minor" required min="0" max="65535"/>
          </div>
           <div>
            <label>MAC Address / Device ID:</label>
            <input type="text" v-model="editingBeacon.deviceId" placeholder="e.g., C3:00:00:3E:7D:DA or Bluetooth device ID"/>
            <small>This is typically the Bluetooth device ID from the scan. For some beacons, it might be a MAC address if known.</small>
          </div>

          <div v-if="beaconModalMode === 'edit' || (beaconModalMode === 'add' && editingBeacon.uuid)" class="form-actions coordinate-actions">
             <label>Beacon Position (X, Y):</label>
             <button type="button" @click="requestPlacementFromMapForEditingBeacon" :disabled="!hasMap">
              {{ editingBeacon.x === null || editingBeacon.x === undefined ? 'Select Coordinates from Map' : 'Update Coordinates from Map' }}
            </button>
          </div>

          <div class="form-row coordinate-pair">
            <div class="form-group-inline">
              <label>X Coordinate (m):</label>
              <input type="number" v-model.number="editingBeacon.x" step="0.01" />
            </div>
            <div class="form-group-inline">
              <label>Y Coordinate (m):</label>
              <input type="number" v-model.number="editingBeacon.y" step="0.01" />
            </div>
          </div>

          <div>
            <label>TxPower (Reference RSSI@1m):</label>
            <input type="number" v-model.number="editingBeacon.txPower" required />
          </div>
          <div class="modal-actions">
            <button type="submit">Save</button>
            <button type="button" @click="hideBeaconModal">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, defineExpose } from 'vue';
// import localBeaconService from '@/services/webBluetoothService'; // DELETED FILE

const props = defineProps({
  initialBeacons: {
    type: Array,
    default: () => []
  },
  currentMapLayout: { // Added prop
    type: Object,
    default: null
  }
});

const emit = defineEmits(['beacons-updated', 'beacon-selected-for-placement']);

// WebSocket connection state and management
const socket = ref(null);
const serviceUrl = 'ws://localhost:8081';
const isWebSocketConnected = ref(false); // Renamed from isServiceConnected for clarity
const retryCount = ref(0);
const maxRetries = 5;
const retryTimeout = 5000; // 5 seconds
let connectTimeoutId = null;
let scanActiveOnServer = ref(false); // Tracks if the server confirmed scan start

const configuredBeacons = ref([]);
const scanResults = ref([]);
const isScanning = ref(false); // Reflects UI state / user's intent to scan, server confirms with scanActiveOnServer
const scanStatusMessage = ref('Attempting to connect to local beacon service...');
const scanStatusType = ref('info'); // 'info', 'success', 'error', 'warn'
const userInitiatedScan = ref(false);
let scanDurationTimeoutId = null; // For the 15-second scan duration

const showBeaconModal = ref(false);
const beaconModalMode = ref('add'); // 'add' or 'edit'
const editingBeaconIndex = ref(-1);

const initialEditingBeacon = () => ({
  uuid: '',
  major: null,
  minor: null,
  x: 0,
  y: 0,
  txPower: -59,
  displayName: '',
  macAddress: '', 
  deviceId: '' 
});
const editingBeacon = ref(initialEditingBeacon());

const hasMap = computed(() => !!props.currentMapLayout);

// --- WebSocket Logic ---
const connectWebSocket = () => {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) {
    console.log('[BeaconManagerTab] WebSocket already open.');
    return;
  }
  
  handleServiceStatusUpdate({ type: 'connecting', message: `Attempting to connect to local beacon service at ${serviceUrl}... (Attempt ${retryCount.value + 1})` });

  socket.value = new WebSocket(serviceUrl);

  socket.value.onopen = () => {
    console.log('[BeaconManagerTab] WebSocket connected to:', serviceUrl);
    isWebSocketConnected.value = true;
    retryCount.value = 0; // Reset retries on successful connection
    if (connectTimeoutId) clearTimeout(connectTimeoutId);
    handleServiceStatusUpdate({ type: 'connected', message: 'Successfully connected to local beacon service.' });
  };

  socket.value.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      // console.log('[BeaconManagerTab] WebSocket message received:', message);
      if (message.type === 'beacon' && message.data) {
        handleBeaconFound(message.data);
      } else if (message.type === 'info') {
        handleServiceStatusUpdate({ type: 'info', message: message.message });
        if (message.message === 'Scanning started.') {
          scanActiveOnServer.value = true;
        } else if (message.message === 'Scanning stopped.') {
          scanActiveOnServer.value = false;
        }
      } else if (message.type === 'error') {
        handleServiceStatusUpdate({ type: 'error', message: `Server Error: ${message.message}` });
      }
    } catch (error) {
      console.error('[BeaconManagerTab] Error processing WebSocket message:', error);
      handleServiceStatusUpdate({ type: 'error', message: 'Received malformed message from server.' });
    }
  };

  socket.value.onerror = (error) => {
    console.error('[BeaconManagerTab] WebSocket Error:', error);
    // isWebSocketConnected.value = false; // onclose will handle this
    // The onclose event will typically fire immediately after onerror.
    // To avoid double retry logic, let onclose handle reconnection attempts.
    // However, we can update the status message here.
    // handleServiceStatusUpdate({ type: 'error', message: 'WebSocket connection error. See console for details.' });
  };

  socket.value.onclose = (event) => {
    console.log('[BeaconManagerTab] WebSocket disconnected.', event.reason ? `Reason: ${event.reason}` : '', `Code: ${event.code}`);
    isWebSocketConnected.value = false;
    scanActiveOnServer.value = false; // If socket closes, scan is no longer active on server
    if (isScanning.value) { // If UI thought it was scanning
        isScanning.value = false; // Update UI scanning state
    }
    if (scanDurationTimeoutId) clearTimeout(scanDurationTimeoutId);

    if (retryCount.value < maxRetries) {
      retryCount.value++;
      handleServiceStatusUpdate({ type: 'disconnected', message: `Disconnected. Retrying connection (${retryCount.value}/${maxRetries}) in ${retryTimeout / 1000}s...` });
      if (connectTimeoutId) clearTimeout(connectTimeoutId);
      connectTimeoutId = setTimeout(connectWebSocket, retryTimeout);
    } else {
      handleServiceStatusUpdate({ type: 'error', message: `Failed to connect after ${maxRetries} retries. Please check the local service and refresh.` });
    }
  };
};

const disconnectWebSocket = () => {
  if (connectTimeoutId) clearTimeout(connectTimeoutId); // Clear any pending reconnection attempts
  retryCount.value = maxRetries; // Prevent further retries by exhausting them

  if (socket.value) {
    socket.value.close(1000, 'Client initiated disconnect'); // 1000: Normal Closure
    socket.value = null; 
  }
  isWebSocketConnected.value = false;
  scanActiveOnServer.value = false;
  if (isScanning.value) isScanning.value = false;
  console.log('[BeaconManagerTab] WebSocket explicitly disconnected by client.');
  handleServiceStatusUpdate({ type: 'disconnected', message: 'Disconnected from local beacon service by client.' });
};

const sendWebSocketMessage = (messageObject) => {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) {
    socket.value.send(JSON.stringify(messageObject));
    console.log('[BeaconManagerTab] Sent WebSocket message:', messageObject);
  } else {
    console.warn('[BeaconManagerTab] WebSocket not connected or not open. Message not sent:', messageObject);
    handleServiceStatusUpdate({ type: 'error', message: 'Cannot send command: Local service not connected.' });
  }
};
// --- End WebSocket Logic ---

const loadConfiguredBeacons = (beaconsFromProp) => {
  if (beaconsFromProp && Array.isArray(beaconsFromProp)) {
    configuredBeacons.value = JSON.parse(JSON.stringify(beaconsFromProp));
  } else {
    configuredBeacons.value = [];
  }
};

watch(() => props.initialBeacons, (newVal) => {
  loadConfiguredBeacons(newVal);
}, { deep: true, immediate: true });

watch(() => props.currentMapLayout, (newMap, oldMap) => {
  console.log('[BeaconManagerTab] watcher: props.currentMapLayout changed.', 
              'New map PRESENT?:', !!newMap, 
              'Old map PRESENT?:', !!oldMap, 
              'New map name:', newMap ? newMap.name : 'N/A', 
              'Computed hasMap value:', hasMap.value);
}, { deep: true, immediate: true });

const handleServiceStatusUpdate = (status) => {
  console.log('[BeaconManagerTab] Service Status Update:', status);
  scanStatusMessage.value = status.message;
  switch (status.type) {
    case 'connecting':
      scanStatusType.value = 'info';
      // isWebSocketConnected handled by WebSocket events
      break;
    case 'connected':
      scanStatusType.value = 'success';
      // isWebSocketConnected handled by WebSocket events
      break;
    case 'disconnected':
      scanStatusType.value = 'warn';
      // isWebSocketConnected handled by WebSocket events
      if (isScanning.value) { 
        isScanning.value = false; 
        if (scanDurationTimeoutId) clearTimeout(scanDurationTimeoutId);
         scanStatusMessage.value = status.message + " Scan aborted.";
      }
      break;
    case 'error':
      scanStatusType.value = 'error';
      if (status.message.includes('Bluetooth adapter') || status.message.includes('Failed to start')){
          isScanning.value = false; // Server failed to start scan
          scanActiveOnServer.value = false;
          if (scanDurationTimeoutId) clearTimeout(scanDurationTimeoutId);
      }
      break;
    case 'info': 
      scanStatusType.value = 'info';
      if (status.message === 'Scanning started.') {
        isScanning.value = true; // User intent is now confirmed by server
        scanActiveOnServer.value = true;
        scanStatusMessage.value = 'Actively scanning via local service... (Approx 15s)';
        if (scanDurationTimeoutId) clearTimeout(scanDurationTimeoutId);
        scanDurationTimeoutId = setTimeout(() => {
          if (scanActiveOnServer.value) { 
            attemptStopScan('timeout');
          }
        }, 15000); 
      } else if (status.message === 'Scanning stopped.') {
        isScanning.value = false;
        scanActiveOnServer.value = false;
        if (scanDurationTimeoutId) clearTimeout(scanDurationTimeoutId);
        if (userInitiatedScan.value && scanResults.value.length === 0) {
          scanStatusMessage.value = 'Scan finished. No Bluetooth devices found by local service.';
        } else if (scanResults.value.length > 0) {
          scanStatusMessage.value = `Scan finished. Found ${scanResults.value.length} unique device(s).`;
        }
      }
      break;
    default:
      scanStatusType.value = 'info';
  }
};

onMounted(() => {
  console.log('[BeaconManagerTab] Mounted. props.currentMapLayout PRESENT?:', !!props.currentMapLayout, 
              'Initial map name:', props.currentMapLayout ? props.currentMapLayout.name : 'N/A', 
              'Computed hasMap on mount:', hasMap.value);
  connectWebSocket();
});

onBeforeUnmount(() => {
  if (scanActiveOnServer.value) { // If scan was confirmed by server
    sendWebSocketMessage({ command: 'stopScan' });
  }
  disconnectWebSocket();
  if (scanDurationTimeoutId) {
    clearTimeout(scanDurationTimeoutId);
  }
  console.log("BeaconManagerTab: Unmounted. WebSocket disconnected, scan stopped if active.");
});

const handleBeaconFound = (dataFromServer) => {
  const beaconKey = dataFromServer.id;

  let parsedUuid = 'N/A';
  let parsedMajor = null;
  let parsedMinor = null;
  let parsedTxPower = -59; // Default TxPower if not available or not an iBeacon

  if (dataFromServer.iBeacon) {
    const iBeacon = dataFromServer.iBeacon;
    parsedUuid = iBeacon.uuid || 'N/A'; // UUID from iBeacon data
    if (iBeacon.major !== null && !isNaN(parseInt(iBeacon.major, 10))) {
      parsedMajor = parseInt(iBeacon.major, 10);
    }
    if (iBeacon.minor !== null && !isNaN(parseInt(iBeacon.minor, 10))) {
      parsedMinor = parseInt(iBeacon.minor, 10);
    }
    // Use txPowerCalibrated from iBeacon details for the beacon's TxPower
    if (iBeacon.txPowerCalibrated !== null && !isNaN(parseInt(iBeacon.txPowerCalibrated, 10))) {
      parsedTxPower = parseInt(iBeacon.txPowerCalibrated, 10);
    }
  }

  // Filter out beacons with incomplete essential iBeacon data
  if (parsedUuid === 'N/A' || parsedMajor === null || parsedMinor === null) {
    console.log(`[BeaconManagerTab] Filtering out beacon ${beaconKey} (${dataFromServer.localName || 'Unknown'}) due to incomplete iBeacon data (UUID/Major/Minor).`);
    // If it was already in scanResults and is now incomplete, we should remove it or mark it.
    // For simplicity, if it's incomplete now, we just don't add/update it if the user wants to remove incomplete ones.
    // If an existing one becomes incomplete, this logic means it won't be updated with incomplete data.
    // To actively remove from list if it becomes incomplete:
    // const existingIndex = scanResults.value.findIndex(b => b.id === beaconKey);
    // if (existingIndex > -1) {
    //   scanResults.value.splice(existingIndex, 1);
    // }
    return; 
  }

  const displayName = dataFromServer.localName || (parsedUuid !== 'N/A' ? `iBeacon ${parsedMajor}-${parsedMinor}` : `Device ${beaconKey.substring(0,8)}`);
  const existingResult = scanResults.value.find(b => b.id === beaconKey);

  if (existingResult) {
    existingResult.rssi = parseInt(dataFromServer.rssi, 10);
    existingResult.name = dataFromServer.localName || 'Scanned Device'; // Use localName from service
    existingResult.uuid = parsedUuid;
    existingResult.major = parsedMajor;
    existingResult.minor = parsedMinor;
    existingResult.txPower = parsedTxPower;
    existingResult.displayName = displayName;
  } else {
    scanResults.value.push({
      id: beaconKey,
      uuid: parsedUuid,
      major: parsedMajor,
      minor: parsedMinor,
      txPower: parsedTxPower,
      rssi: parseInt(dataFromServer.rssi, 10),
      name: dataFromServer.localName || 'Scanned Device', // Use localName from service
      displayName: displayName,
    });
  }

  if (scanActiveOnServer.value) { 
    scanStatusMessage.value = `Scan in progress... ${scanResults.value.length} unique device(s) detected so far.`;
    scanStatusType.value = 'info';
  }
};

const attemptStartScan = async () => {
  userInitiatedScan.value = true; // Mark that this scan was started by user action

  if (!isWebSocketConnected.value) {
    scanStatusMessage.value = 'Local service is not connected. Please ensure it is running and refresh.';
    scanStatusType.value = 'error';
    console.warn('[BeaconManagerTab] Attempted to start scan, but service is not connected.');
    return;
  }
  if (!hasMap.value) {
    scanStatusMessage.value = "A map is required. Please configure one in 'Map Editor' first.";
    scanStatusType.value = 'warn';
    alert("Please ensure a map is configured in the 'Map Editor' tab before scanning for beacons.");
    return;
  }
  if (isScanning.value || scanActiveOnServer.value) {
    scanStatusMessage.value = 'A scan is already in progress or active on the server.';
    scanStatusType.value = 'info';
    console.log('[BeaconManagerTab] Scan attempt while already scanning or server is active.');
    return;
  }

  // Get MAC addresses of already configured beacons
  const currentConfiguredBeacons = props.initialBeacons || [];
  const ignoredMacAddresses = currentConfiguredBeacons
    .map(b => b.macAddress) // Use macAddress field
    .filter(mac => mac && typeof mac === 'string' && mac.trim() !== ''); // Filter out invalid/empty MACs

  console.log("[BeaconManagerTab] Attempting to start scan, ignoring MACs:", ignoredMacAddresses);

  scanResults.value = []; 
  scanStatusMessage.value = 'Sending start scan command to local service...';
  scanStatusType.value = 'info';
  isScanning.value = true; // Optimistically set UI state

  sendWebSocketMessage({ command: 'startScan', ignoredMacAddresses: ignoredMacAddresses });

  // Set a timeout for the scan duration (e.g., 15 seconds)
  if (scanDurationTimeoutId) clearTimeout(scanDurationTimeoutId);
  scanDurationTimeoutId = setTimeout(() => {
    if (isScanning.value || scanActiveOnServer.value) { // Check both UI and server state
      console.log('[BeaconManagerTab] Scan duration timeout (15s) reached. Requesting stopScan.');
      attemptStopScan(); // Automatically stop the scan
      scanStatusMessage.value = 'Scan finished (15s duration).';
      scanStatusType.value = 'info';
    }
  }, 15000); // 15 seconds
};

const attemptStopScan = (reason = 'manual') => {
  sendWebSocketMessage({ command: 'stopScan' });
  
  if (scanDurationTimeoutId) {
    clearTimeout(scanDurationTimeoutId);
    scanDurationTimeoutId = null;
  }
  // isScanning (UI) and scanActiveOnServer will be set to false by the 'Scanning stopped.' message from the server
  
  if (reason === 'timeout' && scanResults.value.length === 0) {
      scanStatusMessage.value = 'Scan timed out. No Bluetooth devices found by local service.';
  } else if (reason === 'timeout') {
      scanStatusMessage.value = `Scan timed out. Found ${scanResults.value.length} device(s).`;
  } else if (userInitiatedScan.value && scanResults.value.length === 0 && !scanStatusMessage.value.includes('Error')) {
    scanStatusMessage.value = 'Stop command sent. Waiting for confirmation... No devices found yet.';
  } else if (scanResults.value.length > 0 && !scanStatusMessage.value.includes('Error')) {
    scanStatusMessage.value = `Stop command sent. Waiting for confirmation... ${scanResults.value.length} device(s) were found.`;
  } else if (!scanStatusMessage.value.includes('Error')) {
    scanStatusMessage.value = 'Stop command sent. Waiting for confirmation...';
  }
  scanStatusType.value = 'info';
  isScanning.value = false; // Optimistically set UI state; server message will confirm scanActiveOnServer = false
};

const sortedScanResults = computed(() => {
  return [...scanResults.value].sort((a, b) => {
    if (a.rssi < b.rssi) return 1;
    if (a.rssi > b.rssi) return -1;
    return (a.displayName || a.name || '').localeCompare(b.displayName || b.name || '');
  });
});

const showAddBeaconModal = () => {
  if (!props.currentMapLayout) {
    alert("A map is required to add beacons. Please go to the 'Map Editor' tab to define a map first.");
    return;
  }
  beaconModalMode.value = 'add';
  editingBeacon.value = initialEditingBeacon();
  showBeaconModal.value = true;
};

const showEditBeaconModal = (index) => {
  beaconModalMode.value = 'edit';
  editingBeaconIndex.value = index;
  editingBeacon.value = JSON.parse(JSON.stringify(configuredBeacons.value[index]));
  showBeaconModal.value = true;
};

const hideBeaconModal = () => {
  showBeaconModal.value = false;
};

const saveBeacon = () => {
  console.log('[BeaconManagerTab - saveBeacon] Attempting to save beacon.');
  console.log('  Editing beacon data before save:', JSON.parse(JSON.stringify(editingBeacon.value)));

  const beaconDataToSave = JSON.parse(JSON.stringify(editingBeacon.value));

  // Ensure UUID is consistently uppercase
  if (beaconDataToSave.uuid) {
    beaconDataToSave.uuid = String(beaconDataToSave.uuid).toUpperCase();
  }

  if (!beaconDataToSave.displayName || !beaconDataToSave.uuid) {
      alert("Display Name and UUID are required.");
      return;
  }

  if (beaconModalMode.value === 'add') {
    const alreadyExists = configuredBeacons.value.some(
        b => b.uuid.toUpperCase() === beaconDataToSave.uuid.toUpperCase() &&
             b.major === beaconDataToSave.major &&
             b.minor === beaconDataToSave.minor &&
             ((b.deviceId && beaconDataToSave.deviceId && b.deviceId === beaconDataToSave.deviceId) ||
              (!b.deviceId && !beaconDataToSave.deviceId))
    );

    if (alreadyExists) {
        scanStatusMessage.value = "Error: A beacon with the same UUID, Major, Minor, and Device ID already exists.";
        scanStatusType.value = 'error';
        setTimeout(() => { scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 5000);
        return; 
    }

    console.log('[BeaconManagerTab - saveBeacon] Beacon data validated. Mode:', beaconModalMode.value);
    console.log('  Configured beacons BEFORE save/push:', JSON.parse(JSON.stringify(configuredBeacons.value)));

    configuredBeacons.value.push(beaconDataToSave);
    
    console.log('  Configured beacons AFTER save/push:', JSON.parse(JSON.stringify(configuredBeacons.value)));
    console.log('  Emitting beacons-updated with this list (length '+ configuredBeacons.value.length + ').');
    emit('beacons-updated', JSON.parse(JSON.stringify(configuredBeacons.value)));
        
    scanStatusMessage.value = `Beacon '${beaconDataToSave.displayName}' added successfully. Use 'Place on Map' to position it.`;
    scanStatusType.value = 'success';
    hideBeaconModal(); 
    setTimeout(() => { scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 5000);

  } else { 
    if (editingBeaconIndex.value > -1 && editingBeaconIndex.value < configuredBeacons.value.length) {
      const otherBeacons = configuredBeacons.value.filter((_, i) => i !== editingBeaconIndex.value);
      const alreadyExistsOnEdit = otherBeacons.some(
        b => b.uuid.toUpperCase() === beaconDataToSave.uuid.toUpperCase() &&
             b.major === beaconDataToSave.major &&
             b.minor === beaconDataToSave.minor &&
             ((b.deviceId && beaconDataToSave.deviceId && b.deviceId === beaconDataToSave.deviceId) ||
              (!b.deviceId && !beaconDataToSave.deviceId))
      );
      if (alreadyExistsOnEdit) {
        scanStatusMessage.value = "Error: Editing this beacon would create a duplicate (same UUID, Major, Minor, Device ID) of another existing beacon.";
        scanStatusType.value = 'error';
        setTimeout(() => { scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 5000);
        return;
      }
      configuredBeacons.value.splice(editingBeaconIndex.value, 1, beaconDataToSave);
      console.log('  Configured beacons AFTER update:', JSON.parse(JSON.stringify(configuredBeacons.value)));
      console.log('  Emitting beacons-updated with this list (length '+ configuredBeacons.value.length + ').');
      emit('beacons-updated', JSON.parse(JSON.stringify(configuredBeacons.value)));
      scanStatusMessage.value = `Beacon '${beaconDataToSave.displayName}' updated.`;
      scanStatusType.value = 'success';
      setTimeout(() => { scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 3000);
    } else {
      scanStatusMessage.value = "Error: Could not update beacon. Index out of bounds.";
      scanStatusType.value = 'error';
      setTimeout(() => { scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 5000);
    }
    hideBeaconModal();
  }
};

const deleteBeacon = (index) => {
  if (confirm(`Are you sure you want to delete beacon: ${configuredBeacons.value[index].displayName || configuredBeacons.value[index].uuid}?`)) {
    configuredBeacons.value.splice(index, 1);
    emit('beacons-updated', JSON.parse(JSON.stringify(configuredBeacons.value)));
  }
};

const selectBeaconForPlacement = (beacon) => {
  emit('beacon-selected-for-placement', JSON.parse(JSON.stringify(beacon)));
  scanStatusMessage.value = `Beacon '${beacon.displayName || beacon.uuid}' selected. Click on the map in the 'Map Editor' tab to place it.`;
  scanStatusType.value = 'info';
};

const isBeaconAlreadyConfigured = (scannedBeacon) => {
  // console.log('[BeaconManagerTab] Checking if beacon is already configured. Scanned beacon ID:', scannedBeacon.id, 'UUID:', scannedBeacon.uuid);
  const result = configuredBeacons.value.some(
    b => {
      const uuidMatch = b.uuid && scannedBeacon.uuid && b.uuid.toUpperCase() === scannedBeacon.uuid.toUpperCase();
      const majorMatch = b.major === scannedBeacon.major;
      const minorMatch = b.minor === scannedBeacon.minor;
      const deviceIdMatch = (b.deviceId && scannedBeacon.id && b.deviceId === scannedBeacon.id);
      
      if (scannedBeacon.uuid && scannedBeacon.uuid !== 'N/A' && scannedBeacon.major !== 'N/A' && scannedBeacon.minor !== 'N/A') {
        const configuredIsSimilarIBeacon = b.uuid && b.uuid.toUpperCase() === scannedBeacon.uuid.toUpperCase() &&
                                       b.major === scannedBeacon.major &&
                                       b.minor === scannedBeacon.minor;
        if (configuredIsSimilarIBeacon) {
            return true; 
        }
      }
      return deviceIdMatch;
    }
  );
  // console.log('[BeaconManagerTab] isBeaconAlreadyConfigured result for ID', scannedBeacon.id, ':', result);
  return result;
};

const addScannedBeaconToForm = (scannedBeaconData) => {
  // console.log('[BeaconManagerTab] addScannedBeaconToForm CALLED with:', JSON.parse(JSON.stringify(scannedBeaconData)));
  // console.log('[BeaconManagerTab] Current isScanning state:', isScanning.value);

  if (isBeaconAlreadyConfigured(scannedBeaconData)) {
    // console.warn('[BeaconManagerTab] Add aborted: Beacon is considered already configured.', JSON.parse(JSON.stringify(scannedBeaconData)));
    scanStatusMessage.value = `Beacon '${scannedBeaconData.displayName || scannedBeaconData.id}' is already configured or has identical key parameters.`;
    scanStatusType.value = 'warn';
    setTimeout(() => { scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 5000);
    return;
  }

  // console.log('[BeaconManagerTab] Beacon not configured. Proceeding to populate form and show modal.');
  editingBeacon.value = {
    uuid: scannedBeaconData.uuid && scannedBeaconData.uuid !== 'N/A' ? scannedBeaconData.uuid.toUpperCase() : '',
    major: scannedBeaconData.major, // Already a number or null from handleBeaconFound
    minor: scannedBeaconData.minor, // Already a number or null from handleBeaconFound
    x: 0, 
    y: 0, 
    txPower: scannedBeaconData.txPower, // Already a number (default or parsed) from handleBeaconFound
    displayName: scannedBeaconData.displayName, // Already prepared by handleBeaconFound
    macAddress: '', // MAC address is not consistently available from noble scan result's main properties for iBeacons
    deviceId: scannedBeaconData.id 
  };
  editingBeaconIndex.value = -1;
  beaconModalMode.value = 'add';
  showBeaconModal.value = true;
  scanStatusMessage.value = `Adding beacon '${editingBeacon.value.displayName}'. Please verify details and save.`;
  scanStatusType.value = 'info';
  setTimeout(() => { if(scanStatusMessage.value.startsWith('Adding beacon')) scanStatusMessage.value = ''; scanStatusType.value = 'info'; }, 5000);
};

const requestPlacementFromMapForEditingBeacon = () => {
  if (!props.currentMapLayout) {
    alert("A map is required to place beacons. Please go to the 'Map Editor' tab to define a map first.");
    return;
  }
  emit('beacon-selected-for-placement', { ...editingBeacon.value });
  // Modal can remain open, parent handles tab switch.
};

const updateCoordinatesForBeaconInModal = (uuid, major, minor, newX, newY) => {
  if (showBeaconModal.value && editingBeacon.value) {
    // Ensure major/minor are numbers for comparison, as they might come as strings from parent
    const numMajor = Number(major);
    const numMinor = Number(minor);
    const numNewX = Number(newX);
    const numNewY = Number(newY);

    if (
      editingBeacon.value.uuid === uuid &&
      editingBeacon.value.major === numMajor &&
      editingBeacon.value.minor === numMinor
    ) {
      editingBeacon.value.x = parseFloat(numNewX.toFixed(2)); // Apply new X, rounded to 2 decimal places
      editingBeacon.value.y = parseFloat(numNewY.toFixed(2)); // Apply new Y, rounded to 2 decimal places
      console.log(`[BeaconManagerTab] Updated coordinates in modal for ${uuid}/${major}/${minor} to X:${editingBeacon.value.x}, Y:${editingBeacon.value.y}`);
    } else {
      console.warn(
        '[BeaconManagerTab] Received coordinate update, but it does not match the currently editing beacon.',
        'CurrentEditing:', {uuid: editingBeacon.value.uuid, major: editingBeacon.value.major, minor: editingBeacon.value.minor},
        'ReceivedFor:', {uuid, major, minor}
      );
    }
  } else {
    console.warn('[BeaconManagerTab] Received coordinate update, but beacon modal is not open or no beacon is being edited.');
  }
};

defineExpose({
  updateCoordinatesForBeaconInModal
});

</script>

<style scoped>
.beacon-manager-tab {
  padding: 1rem;
}
.actions-bar {
  margin-bottom: 1rem;
}
.scan-status {
  margin: 0.5rem 0;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.9em;
}
.scan-status.info { background-color: #e7f3fe; border: 1px solid #d0eaff; color: #0c5460; }
.scan-status.success { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
.scan-status.error { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
.scan-status.warn { background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; }

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
th {
  background-color: #f2f2f2;
}
.scan-results-placeholder {
  padding: 1rem;
  text-align: center;
  color: #666;
  border: 1px dashed #ccc;
  margin-top: 1rem;
  background-color: #f9f9f9;
}
.scan-results {
  margin-top: 1rem;
  border: 1px solid #eee;
  padding: 1rem;
}
.scan-results h4 {
  margin-top: 0;
}
.scan-results ul {
  list-style-type: none;
  padding: 0;
}
.scan-result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}
.scan-result-item:last-child {
  border-bottom: none;
}
.scan-result-item div {
  font-size: 0.9em;
  line-height: 1.4;
}
.scan-result-item strong {
  font-size: 1em;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background-color: white;
  padding: 25px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  width: 90%;
  max-width: 500px;
}
.modal-content h4 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.3em;
  color: #333;
}
.modal-content form div {
  margin-bottom: 15px;
}
.modal-content form label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #555;
}
.modal-content form input[type="text"],
.modal-content form input[type="number"] {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 0.95em;
}
.modal-content form input[type="text"]:focus,
.modal-content form input[type="number"]:focus {
  border-color: #007bff;
  outline: none;
}
.modal-content form .coordinate-actions {
  margin-bottom: 10px; /* Add some space below the button and its label */
}
.modal-content form .coordinate-actions label {
  /* Style for the new label above the button, if needed */
  margin-bottom: 8px; /* Space between this label and the button */
  font-weight: bold; /* Make it stand out a bit */
}
.modal-content form .coordinate-actions button {
  width: 100%; /* Make button full width */
  padding: 10px;
  margin-bottom: 10px; /* Space below the button, before X coord */
}
.modal-content form small {
    font-size: 0.8em;
    color: #777;
    display: block;
    margin-top: 3px;
}
.modal-actions {
  margin-top: 25px;
  text-align: right;
}
.modal-actions button {
  margin-left: 10px;
  padding: 10px 18px;
}
.modal-actions button[type="submit"] {
  background-color: #007bff;
  color: white;
  border: none;
}
.modal-actions button[type="submit"]:hover {
  background-color: #0056b3;
}
.modal-actions button[type="button"] {
  background-color: #f0f0f0;
  color: #333;
  border: 1px solid #ccc;
}
.modal-actions button[type="button"]:hover {
  background-color: #e0e0e0;
}

.beacon-actions-container {
  display: flex;
  gap: 5px;
  align-items: center; /* Vertically align items if they have different heights */
}

.beacon-actions-container button {
  padding: 6px 10px; /* Adjust padding for a more compact look if needed */
  white-space: nowrap; /* Prevent text wrapping within buttons */
  flex-shrink: 0; /* Prevent buttons from shrinking too much if space is tight */
}

.form-row.coordinate-pair {
  display: flex;
  gap: 15px; /* Space between X and Y input groups */
  align-items: flex-start; /* Align items to the top if labels cause height differences */
}

.form-group-inline {
  flex: 1; /* Allow each group to take equal space */
}

.form-group-inline label {
  display: block;
  margin-bottom: 5px;
}

.form-group-inline input[type="number"] {
  width: 100%; /* Make inputs take full width of their flex container */
}
</style> 
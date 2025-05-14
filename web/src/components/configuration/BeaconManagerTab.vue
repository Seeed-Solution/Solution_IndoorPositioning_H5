<template>
  <div class="beacon-manager-tab">
    <h3>Beacon List & Management</h3>
    <p>Manage fixed reference beacons. You can add, edit, delete beacons, or discover new ones via Bluetooth scan.</p>
    
    <div class="actions-bar">
      <button @click="showAddBeaconModal" :disabled="isScanning">Add New Beacon</button>
      <button @click="startScan" :disabled="isScanning" style="margin-left: 10px;">
        {{ isScanning ? 'Scanning... (Click stop button below to abort)' : 'Scan for Nearby Beacons (Web Bluetooth)' }}
      </button>
      <button v-if="isScanning" @click="stopScan" style="margin-left: 10px; background-color: #dc3545;">Stop Scan</button>
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
          <td>
            <button @click="showEditBeaconModal(index)" :disabled="isScanning">Edit</button>
            <button @click="deleteBeacon(index)" :disabled="isScanning" style="margin-left: 5px;">Delete</button>
            <button @click="selectBeaconForPlacement(beacon)" :disabled="isScanning" style="margin-left: 5px;">Place on Map</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!isScanning">No configured beacons yet. You can add them manually or scan for nearby ones.</p>

    <div v-if="isScanning && scanResults.length === 0 && !scanStatusMessage.includes('Error')" class="scan-results-placeholder">
      <p><i class="fas fa-spinner fa-spin"></i> Actively scanning for Bluetooth devices... Please ensure Bluetooth is enabled and the browser has permission.</p>
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
          <button @click="addScannedBeaconToForm(beacon)" :disabled="isBeaconAlreadyConfigured(beacon) || isScanning">
            {{ isBeaconAlreadyConfigured(beacon) ? 'Already Configured' : 'Add This Beacon' }}
          </button>
        </li>
      </ul>
    </div>
    <p v-if="!isScanning && userInitiatedScan && scanResults.length === 0 && !scanStatusMessage.includes('Error') && !scanStatusMessage.includes('Starting')" class="scan-status info">
      Scan complete. No new iBeacon devices found.
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
            <small>This is typically the Bluetooth device ID. For some beacons, it might be a MAC address if known.</small>
          </div>
          <div>
            <label>X Coordinate (meters):</label>
            <input type="number" v-model.number="editingBeacon.x" step="0.1" required />
          </div>
          <div>
            <label>Y Coordinate (meters):</label>
            <input type="number" v-model.number="editingBeacon.y" step="0.1" required />
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
import { ref, watch, computed, onBeforeUnmount } from 'vue';
import webBluetoothService from '@/services/webBluetoothService';

const props = defineProps({
  initialBeacons: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['beacons-updated', 'beacon-selected-for-placement']);

const configuredBeacons = ref([]);
const scanResults = ref([]);
const isScanning = ref(false);
const scanStatusMessage = ref('');
const scanStatusType = ref('info'); // 'info', 'success', 'error'
const userInitiatedScan = ref(false);
let scanTimeoutId = null;

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
  macAddress: '', // Legacy, will be populated by deviceId if that's what's available
  deviceId: '' // From Bluetooth scan event.device.id
});
const editingBeacon = ref(initialEditingBeacon());

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

onBeforeUnmount(() => {
  if (isScanning.value) {
    webBluetoothService.stopScan(); // Ensure service stops listening
    isScanning.value = false;
  }
  if (scanTimeoutId) {
    clearTimeout(scanTimeoutId);
  }
  console.log("BeaconManagerTab: Unmounted. Scan stopped if active.");
});

const handleBeaconFound = (beacon) => {
  // beacon: { id, name, rssi, uuid, major, minor, txPower, type, deviceId, deviceName }
  // Note: webBluetoothService already provides 'id' which is event.device.id
  // and 'deviceId'/'deviceName' within the parsed iBeacon data itself. Let's be consistent.
  // The key for scanResults should be unique, event.device.id is good for that.
  
  const beaconKey = beacon.id; // This is event.device.id from webBluetoothService

  const existingResult = scanResults.value.find(b => b.id === beaconKey);

  if (existingResult) {
    existingResult.rssi = beacon.rssi; // Update RSSI
    if (!existingResult.name && beacon.name) existingResult.name = beacon.name; // Update name if it was generic
    if (!existingResult.displayName && beacon.displayName) existingResult.displayName = beacon.displayName;
  } else {
    scanResults.value.push({
      id: beaconKey, // This is the actual Bluetooth device ID
      uuid: beacon.uuid.toUpperCase(),
      major: parseInt(beacon.major, 10),
      minor: parseInt(beacon.minor, 10),
      txPower: parseInt(beacon.txPower, 10),
      rssi: parseInt(beacon.rssi, 10),
      name: beacon.deviceName || beacon.name || 'iBeacon Device', // From BLE advertisement or iBeacon data
      displayName: beacon.deviceName || beacon.name || `iBeacon (${beacon.major}-${beacon.minor})`, // For UI display
      // Keep deviceId in the editingBeacon model consistent with this 'id'
    });
  }
};

const startScan = async () => {
  if (isScanning.value) return;

  isScanning.value = true;
  userInitiatedScan.value = true;
  scanResults.value = [];
  scanStatusMessage.value = 'Initializing Bluetooth scan... Please grant permissions if prompted.';
  scanStatusType.value = 'info';

  if (scanTimeoutId) clearTimeout(scanTimeoutId);

  try {
    // The onBeaconFoundCallback is handleBeaconFound
    // scanDuration is handled by webBluetoothService itself now.
    await webBluetoothService.scanForIBeacons(handleBeaconFound); 
    
    scanStatusMessage.value = 'Actively scanning for iBeacons... This will run for about 15 seconds or until you stop. Detected devices will appear below.';
    scanStatusType.value = 'info';

    // Set a timeout to update UI after the scan duration (service stops itself)
    scanTimeoutId = setTimeout(() => {
      if (isScanning.value) { // Check if it wasn't stopped manually
        isScanning.value = false; // Mark as not scanning
        if (scanResults.value.length === 0) {
          scanStatusMessage.value = 'Scan finished. No iBeacon devices found.';
          scanStatusType.value = 'info';
        } else {
          scanStatusMessage.value = `Scan finished. Found ${scanResults.value.length} unique iBeacon(s).`;
          scanStatusType.value = 'success';
        }
      }
    }, 15500); // Slightly longer than the service's typical 15s scan

  } catch (error) {
    console.error('Error starting beacon scan:', error);
    scanStatusMessage.value = `Scan Error: ${error.message || 'Failed to start Bluetooth scan. Check browser compatibility and permissions.'}`;
    scanStatusType.value = 'error';
    isScanning.value = false;
    userInitiatedScan.value = false;
  }
};

const stopScan = () => {
  if (scanTimeoutId) clearTimeout(scanTimeoutId);
  webBluetoothService.stopScan(); // This will also clear the callback in the service
  isScanning.value = false;
  scanStatusMessage.value = 'Scan stopped by user.';
  scanStatusType.value = 'info';
  if (scanResults.value.length === 0 && userInitiatedScan.value) {
    scanStatusMessage.value += ' No iBeacons found before stopping.';
  }
  // userInitiatedScan.value = false; // Keep true to show "no devices found" if applicable after manual stop
};

const sortedScanResults = computed(() => {
  // Sort by RSSI (strongest signal first)
  return [...scanResults.value].sort((a, b) => b.rssi - a.rssi);
});


const showAddBeaconModal = () => {
  beaconModalMode.value = 'add';
  editingBeacon.value = initialEditingBeacon();
  showBeaconModal.value = true;
};

const showEditBeaconModal = (index) => {
  beaconModalMode.value = 'edit';
  editingBeaconIndex.value = index;
  const beaconToEdit = configuredBeacons.value[index];
  editingBeacon.value = JSON.parse(JSON.stringify({
      ...initialEditingBeacon(), // Start with defaults
      ...beaconToEdit, // Overlay with actual data
      // Ensure deviceId is correctly mapped if it was stored as macAddress previously
      deviceId: beaconToEdit.deviceId || beaconToEdit.macAddress || '' 
  }));
  showBeaconModal.value = true;
};

const hideBeaconModal = () => {
  showBeaconModal.value = false;
};

const saveBeacon = () => {
  if (!editingBeacon.value.displayName || !editingBeacon.value.uuid ||
      editingBeacon.value.major === null || editingBeacon.value.minor === null ||
      editingBeacon.value.txPower === null) {
    alert('Please fill in Display Name, UUID, Major, Minor, and TxPower.');
    return;
  }
  const uuidRegex = /^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$/i;
  if (!uuidRegex.test(editingBeacon.value.uuid)) {
    alert('Invalid UUID format.');
    return;
  }

  const beaconDataToSave = JSON.parse(JSON.stringify(editingBeacon.value));
  beaconDataToSave.uuid = beaconDataToSave.uuid.toUpperCase();
  beaconDataToSave.major = parseInt(beaconDataToSave.major, 10);
  beaconDataToSave.minor = parseInt(beaconDataToSave.minor, 10);
  beaconDataToSave.txPower = parseInt(beaconDataToSave.txPower, 10);
  beaconDataToSave.x = parseFloat(beaconDataToSave.x) || 0;
  beaconDataToSave.y = parseFloat(beaconDataToSave.y) || 0;
  // deviceId should already be populated in editingBeacon.value

  if (beaconModalMode.value === 'add') {
    const exists = configuredBeacons.value.some(b =>
        b.uuid === beaconDataToSave.uuid &&
        b.major === beaconDataToSave.major &&
        b.minor === beaconDataToSave.minor
    );
    if (exists) {
      alert('A beacon with the same UUID, Major, and Minor already exists.');
      return;
    }
    configuredBeacons.value.push(beaconDataToSave);
  } else {
    if (editingBeaconIndex.value >= 0 && editingBeaconIndex.value < configuredBeacons.value.length) {
      configuredBeacons.value.splice(editingBeaconIndex.value, 1, beaconDataToSave);
    } else {
      alert('Error editing beacon: Invalid index.');
      hideBeaconModal();
      return;
    }
  }
  emit('beacons-updated', JSON.parse(JSON.stringify(configuredBeacons.value)));
  hideBeaconModal();
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
  // Compare based on UUID, Major, Minor
  return configuredBeacons.value.some(configured =>
    configured.uuid.toUpperCase() === scannedBeacon.uuid.toUpperCase() &&
    configured.major === scannedBeacon.major &&
    configured.minor === scannedBeacon.minor
  );
};

const addScannedBeaconToForm = (scannedBeacon) => {
  beaconModalMode.value = 'add'; // Always add mode for scanned beacons
  editingBeacon.value = {
    ...initialEditingBeacon(), // Start with defaults
    uuid: scannedBeacon.uuid.toUpperCase(),
    major: scannedBeacon.major,
    minor: scannedBeacon.minor,
    txPower: scannedBeacon.txPower,
    displayName: scannedBeacon.displayName || scannedBeacon.name || `Scanned iBeacon ${scannedBeacon.major}-${scannedBeacon.minor}`,
    deviceId: scannedBeacon.id, // This is the Bluetooth device ID
    macAddress: '' // Clear macAddress, as deviceId is the primary identifier from scan
  };
  showBeaconModal.value = true;
};

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
</style> 
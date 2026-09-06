<template>
  <div class="beacon-manager-tab">
    <h3>Beacon List & Management</h3>
    <p>Manage fixed reference beacons. You can add, edit, and delete beacons for positioning configuration.</p>
    <p v-if="!hasMap" class="scan-status error">
      A map is required to configure and place beacons. Please go to the "Map Editor" tab to upload or define a map first.
    </p>
    
    <div class="actions-bar">
      <button @click="showAddBeaconModal" :disabled="!hasMap" class="action-btn primary-btn">
        <i class="fas fa-plus"></i> Add New Beacon
      </button>
    </div>

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
          <td>{{ formatMacAddress(beacon.macAddress || beacon.deviceId) }}</td>
          <td class="actions-cell">
            <div class="beacon-actions-container">
              <button @click="showEditBeaconModal(index)" class="action-btn edit-btn">
                <i class="fas fa-edit"></i> Edit
              </button>
              <button @click="deleteBeacon(index)" class="action-btn delete-btn">
                <i class="fas fa-trash"></i> Delete
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-state">
      <div class="empty-state-content">
        <i class="fas fa-broadcast-tower empty-state-icon"></i>
        <h4>No beacons configured</h4>
        <p>Click "Add New Beacon" to manually add beacons for positioning configuration.</p>
      </div>
    </div>


    <!-- Add/Edit Beacon Modal -->
    <div v-if="showBeaconModal" class="modal-overlay" @wheel="preventBackgroundScroll" @touchmove="preventBackgroundScroll" @scroll.stop>
      <div class="modal-content" @wheel="preventBackgroundScroll" @touchmove="preventBackgroundScroll">
        <h4>{{ beaconModalMode === 'add' ? 'Add New Beacon' : 'Edit Beacon' }}</h4>
        <form @submit.prevent="saveBeacon">
          <div class="form-scrollable" @wheel="preventBackgroundScroll" @touchmove="preventBackgroundScroll">
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
              <input type="text" v-model="editingBeacon.macAddress" placeholder="e.g., C3:00:00:3E:7D:DA or Bluetooth device ID"/>
              <small>This is the physical MAC address (Device ID) from the scan. This is the ONLY identifier used to detect duplicate devices. UUID/Major/Minor can be the same for devices from the same manufacturer.</small>
            </div>

            <div v-if="beaconModalMode === 'edit' || (beaconModalMode === 'add' && editingBeacon.uuid)" class="form-actions coordinate-actions">
               <label>Beacon Position (X, Y):</label>
               <button 
                 type="button" 
                 @click="requestPlacementFromMapForEditingBeacon" 
                 :disabled="!hasMapWithBackground"
                 :title="!hasMapWithBackground ? '需要先上传地图背景图才能使用地图选点功能' : ''"
               >
                {{ editingBeacon.x === null || editingBeacon.x === undefined ? 'Select Coordinates from Map' : 'Update Coordinates from Map' }}
              </button>
              <p v-if="!hasMapWithBackground" class="map-required-hint">
                <i class="fas fa-info-circle"></i>
                需要先上传地图背景图才能使用地图选点功能，否则请手动输入坐标值
              </p>
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
import { notificationService } from '@/services/notificationService.js';
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

const configuredBeacons = ref([]);

const showBeaconModal = ref(false);
const beaconModalMode = ref('add'); // 'add' or 'edit'
const editingBeaconIndex = ref(-1);

const initialEditingBeacon = () => ({
  uuid: 'FDA50693-A4E2-4FB1-AFCF-C6EB07647825',
  major: 10001,
  minor: 19641,
  x: 0,
  y: 0,
  txPower: -59,
  displayName: 'BC01',
  macAddress: 'c3000056dda1',
  deviceId: 'c3000056dda1'
});
const editingBeacon = ref(initialEditingBeacon());

const hasMap = computed(() => !!props.currentMapLayout);

const hasMapWithBackground = computed(() => 
  props.currentMapLayout && 
  props.currentMapLayout.background && 
  typeof props.currentMapLayout.background === 'string' &&
  props.currentMapLayout.background.trim() !== ''
);

// 格式化MAC地址为标准格式
const formatMacAddress = (macAddress) => {
  if (!macAddress || typeof macAddress !== 'string') {
    return macAddress || '';
  }
  
  // 移除所有非十六进制字符
  const cleanMac = macAddress.replace(/[^0-9A-Fa-f]/g, '');
  
  // 如果长度不是12位，直接返回原值
  if (cleanMac.length !== 12) {
    return macAddress;
  }
  
  // 转换为大写并按每两位分组，用冒号连接
  return cleanMac.toUpperCase().match(/.{2}/g).join(':');
};

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

// 监听模态框显示状态，锁定/解锁 body 滚动
watch(showBeaconModal, (isOpen) => {
  if (isOpen) {
    // 锁定 body 滚动
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = '0px'; // 防止滚动条消失导致的布局偏移
  } else {
    // 解锁 body 滚动
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
  }
});

// 组件卸载时确保恢复 body 滚动
onBeforeUnmount(() => {
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
});


const showAddBeaconModal = () => {
  if (!props.currentMapLayout) {
    notificationService.warning("A map is required to add beacons. Please go to the 'Map Editor' tab to define a map first.");
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

// 阻止模态框外部的滚动事件
const preventBackgroundScroll = (e) => {
  // 如果滚动发生在 .form-scrollable 内部，允许滚动但阻止冒泡
  const target = e.target;
  const scrollableElement = target.closest('.form-scrollable');
  if (scrollableElement) {
    // 允许内部滚动，但阻止事件冒泡到外部
    e.stopPropagation();
    return;
  }
  // 如果不在可滚动区域内，阻止所有滚动
  e.preventDefault();
  e.stopPropagation();
};

const saveBeacon = () => {
  console.log('[BeaconManagerTab - saveBeacon] Attempting to save beacon.');
  console.log('  Editing beacon data before save:', JSON.parse(JSON.stringify(editingBeacon.value)));

  const beaconDataToSave = JSON.parse(JSON.stringify(editingBeacon.value));

  // 处理MAC地址：清理格式并自动补0
  if (beaconDataToSave.macAddress) {
    // 移除所有非十六进制字符
    let cleanMac = beaconDataToSave.macAddress.replace(/[^0-9A-Fa-f]/g, '');
    
    // 如果长度不足12位，在末尾补0
    if (cleanMac.length < 12) {
      cleanMac = cleanMac.padEnd(12, '0');
    }
    
    // 如果超过12位，截取前12位
    if (cleanMac.length > 12) {
      cleanMac = cleanMac.substring(0, 12);
    }
    
    // 更新MAC地址
    beaconDataToSave.macAddress = cleanMac.toLowerCase();
    beaconDataToSave.deviceId = beaconDataToSave.macAddress;
  }

  // Ensure UUID is consistently uppercase
  if (beaconDataToSave.uuid) {
    beaconDataToSave.uuid = String(beaconDataToSave.uuid).toUpperCase();
  }

  if (!beaconDataToSave.displayName || !beaconDataToSave.uuid) {
      notificationService.error("Display Name and UUID are required.");
      return;
  }

  if (beaconModalMode.value === 'add') {
    const alreadyExists = configuredBeacons.value.some(
        b => {
          // 只基于物理MAC地址（deviceId）检测重复
          // UUID、Major、Minor相同没关系，可能是同一厂商的多个设备
          const deviceIdMatch = (b.deviceId && beaconDataToSave.deviceId && b.deviceId === beaconDataToSave.deviceId);
          return deviceIdMatch;
        }
    );

    if (alreadyExists) {
        notificationService.error("Error: A beacon with the same Device ID (MAC address) already exists.");
        return; 
    }

    console.log('[BeaconManagerTab - saveBeacon] Beacon data validated. Mode:', beaconModalMode.value);
    console.log('  Configured beacons BEFORE save/push:', JSON.parse(JSON.stringify(configuredBeacons.value)));

    configuredBeacons.value.push(beaconDataToSave);
    
    console.log('  Configured beacons AFTER save/push:', JSON.parse(JSON.stringify(configuredBeacons.value)));
    console.log('  Emitting beacons-updated with this list (length '+ configuredBeacons.value.length + ').');
    emit('beacons-updated', JSON.parse(JSON.stringify(configuredBeacons.value)));
        
    hideBeaconModal();

  } else { 
    if (editingBeaconIndex.value > -1 && editingBeaconIndex.value < configuredBeacons.value.length) {
      const otherBeacons = configuredBeacons.value.filter((_, i) => i !== editingBeaconIndex.value);
      const alreadyExistsOnEdit = otherBeacons.some(
        b => {
          // 只基于物理MAC地址（deviceId）检测重复
          // UUID、Major、Minor相同没关系，可能是同一厂商的多个设备
          const deviceIdMatch = (b.deviceId && beaconDataToSave.deviceId && b.deviceId === beaconDataToSave.deviceId);
          return deviceIdMatch;
        }
      );
      if (alreadyExistsOnEdit) {
        notificationService.error("Error: Editing this beacon would create a duplicate (same Device ID/MAC address) of another existing beacon.");
        return;
      }
      configuredBeacons.value.splice(editingBeaconIndex.value, 1, beaconDataToSave);
      console.log('  Configured beacons AFTER update:', JSON.parse(JSON.stringify(configuredBeacons.value)));
      console.log('  Emitting beacons-updated with this list (length '+ configuredBeacons.value.length + ').');
      emit('beacons-updated', JSON.parse(JSON.stringify(configuredBeacons.value)));
    } else {
      notificationService.error("Error: Could not update beacon. Index out of bounds.");
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


const requestPlacementFromMapForEditingBeacon = () => {
  if (!props.currentMapLayout) {
    notificationService.warning("A map is required to place beacons. Please go to the 'Map Editor' tab to define a map first.");
    return;
  }
  // 隐藏模态框，让用户能看到地图
  showBeaconModal.value = false;
  emit('beacon-selected-for-placement', { ...editingBeacon.value });
};

const updateCoordinatesForBeaconInModal = (uuid, major, minor, newX, newY) => {
  // 检查是否有正在编辑的信标（即使模态框当前隐藏）
  if (editingBeacon.value) {
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
      
      // 重新显示模态框，让用户看到更新后的坐标
      showBeaconModal.value = true;
    } else {
      console.warn(
        '[BeaconManagerTab] Received coordinate update, but it does not match the currently editing beacon.',
        'CurrentEditing:', {uuid: editingBeacon.value.uuid, major: editingBeacon.value.major, minor: editingBeacon.value.minor},
        'ReceivedFor:', {uuid, major, minor}
      );
    }
  } else {
    console.warn('[BeaconManagerTab] Received coordinate update, but no beacon is being edited.');
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
.scan-status.error { 
  margin: 0.5rem 0;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.9em;
  background-color: var(--sc-status-danger-bg); 
  border: 1px solid var(--sc-status-danger-bg); 
  color: var(--sc-status-danger-fg); 
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}
th, td {
  border: 1px solid var(--sc-color-border);
  padding: 8px;
  text-align: left;
}
th {
  background-color: #f2f2f2;
}
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  border: 2px dashed var(--sc-color-border);
  border-radius: 8px;
  margin: 1rem 0;
}

.empty-state-content {
  text-align: center;
  color: var(--sc-color-text-secondary);
}

.empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1.2rem;
  color: var(--sc-color-text);
}

.empty-state p {
  margin: 0;
  font-size: 0.9rem;
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
  z-index: 10000;
  overflow: hidden;
  touch-action: none;
}
.modal-content {
  background-color: white;
  padding: 25px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  width: 90%;
  max-width: 500px;
  height: 85vh;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-content h4 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.3em;
  color: var(--sc-color-text);
  flex-shrink: 0;
}
.modal-content form {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}
.modal-content form > div:not(.modal-actions) {
  margin-bottom: 15px;
  flex-shrink: 0;
}
.modal-content .form-scrollable {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
  margin-right: -8px;
  scrollbar-width: thin;
  scrollbar-color: var(--sc-color-text-tertiary) #f1f1f1;
  touch-action: pan-y;
}
.modal-content .form-scrollable::-webkit-scrollbar {
  width: 8px;
}
.modal-content .form-scrollable::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
  margin: 5px 0;
}
.modal-content .form-scrollable::-webkit-scrollbar-thumb {
  background: var(--sc-color-text-tertiary);
  border-radius: 4px;
}
.modal-content .form-scrollable::-webkit-scrollbar-thumb:hover {
  background: var(--sc-color-text-secondary);
}
.modal-content form label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: var(--sc-color-text-secondary);
}
.modal-content form input[type="text"],
.modal-content form input[type="number"] {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--sc-color-border);
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 0.95em;
}
.modal-content form input[type="text"]:focus,
.modal-content form input[type="number"]:focus {
  border-color: var(--sc-color-info);
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
  flex-shrink: 0;
}
.modal-actions button {
  margin-left: 10px;
  padding: 10px 18px;
}
.modal-actions button[type="submit"] {
  background-color: var(--sc-color-info);
  color: white;
  border: none;
}
.modal-actions button[type="submit"]:hover {
  background-color: var(--sc-color-info);
}
.modal-actions button[type="button"] {
  background-color: #f0f0f0;
  color: var(--sc-color-text);
  border: 1px solid var(--sc-color-border);
}
.modal-actions button[type="button"]:hover {
  background-color: var(--sc-color-border);
}

.beacon-actions-container {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
}

/* 统一的按钮样式 */
.action-btn {
  padding: 6px 12px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Primary按钮和Edit按钮样式 */
.primary-btn, .edit-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

.primary-btn:hover:not(:disabled), .edit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

/* Delete按钮样式 */
.delete-btn {
  background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 4px rgba(74, 85, 104, 0.3);
}

.delete-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #3a4553 0%, #1a202c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(74, 85, 104, 0.4);
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

.map-required-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.75rem;
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 6px;
  color: #856404;
  font-size: 0.85rem;
  line-height: 1.4;
}

.map-required-hint i {
  color: #f39c12;
  font-size: 1rem;
}

</style> 
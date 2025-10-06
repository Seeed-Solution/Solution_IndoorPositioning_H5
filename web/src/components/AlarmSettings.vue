<template>
  <div class="alarm-settings-section card">
    <div class="card-header">
      <h2><i class="fas fa-bell"></i> Alarm Settings</h2>
      <div class="header-actions">
        <button 
          @click="openCreateAlarmModal"
          class="create-alarm-btn"
        >
          <i class="fas fa-plus"></i> Create Alarm
        </button>
      </div>
    </div>
    <div class="card-content">
      <div v-if="alarmList.length === 0" class="empty-alarm-list">
        <i class="fas fa-bell-slash empty-icon"></i>
        <p>No alarms configured</p>
        <p class="hint">Click "Create Alarm" to add your first alarm</p>
      </div>
      <div v-else class="alarm-table-container">
        <table class="alarm-table">
          <thead>
            <tr>
              <th>Alarm Name</th>
              <th>Alarm Type</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(alarm, index) in paginatedAlarms" :key="alarm.id" class="alarm-row">
              <td class="alarm-name">{{ alarm.name }}</td>
              <td class="alarm-type">
                <span class="alarm-type-badge" :class="getAlarmTypeClass(alarm.type)">
                  {{ getAlarmTypeLabel(alarm.type) }}
                </span>
              </td>
              <td>
                <div class="alarm-status">
                  <label class="status-toggle">
                    <input 
                      type="checkbox" 
                      v-model="alarm.enabled"
                      @change="toggleAlarmStatus(alarm)"
                      class="status-input"
                    />
                    <span class="status-slider"></span>
                  </label>
                  <span class="status-text" :class="{ enabled: alarm.enabled, disabled: !alarm.enabled }">
                    {{ alarm.enabled ? 'Enabled' : 'Disabled' }}
                  </span>
                </div>
              </td>
              <td>
                <div class="alarm-actions">
                  <button 
                    @click="editAlarm(alarm)"
                    class="action-btn edit-btn"
                    :title="'Edit'"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button 
                    @click="deleteAlarm(alarm.id, index)"
                    class="action-btn delete-btn"
                    :title="'Delete'"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        
        <!-- 分页和统计 -->
        <div class="alarm-table-footer">
          <div class="alarm-stats">
            Total {{ alarmList.length }} alarms
          </div>
          <div class="alarm-pagination" v-if="totalPages > 1">
            <button 
              @click="currentPage = Math.max(1, currentPage - 1)"
              :disabled="currentPage === 1"
              class="pagination-btn"
            >
              <i class="fas fa-chevron-left"></i>
            </button>
            <span class="pagination-info">
              {{ currentPage }} / {{ totalPages }}
            </span>
            <button 
              @click="currentPage = Math.min(totalPages, currentPage + 1)"
              :disabled="currentPage === totalPages"
              class="pagination-btn"
            >
              <i class="fas fa-chevron-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑报警模态框 -->
    <div v-if="showAlarmModal" class="modal-overlay" @click="closeAlarmModal">
      <div class="alarm-modal" @click.stop>
        <div class="modal-header">
          <h3>
            <i class="fas fa-bell"></i>
            {{ isEditingAlarm ? 'Edit Alarm' : 'Create Alarm' }}
          </h3>
          <button @click="closeAlarmModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveAlarm">
            <div class="form-group">
              <label for="alarmName">Alarm Name <span class="required">*</span></label>
              <input 
                type="text" 
                id="alarmName"
                v-model="alarmForm.name" 
                class="form-input"
                :class="{ 'error': alarmErrors.name }"
                :placeholder="'Enter alarm name'"
                required
              />
              <span v-if="alarmErrors.name" class="error-message">{{ alarmErrors.name }}</span>
            </div>
            
            <div class="form-group">
              <label for="alarmType">Alarm Type <span class="required">*</span></label>
              <select 
                id="alarmType"
                v-model="alarmForm.type" 
                class="form-input"
                :class="{ 'error': alarmErrors.type }"
                required
              >
                <option value="" disabled>Select alarm type</option>
                <option value="sos">SOS Alarm</option>
                <option value="offline">Offline Alarm</option>
                <option value="checkin">Check-in Event</option>
                <option value="position">Position Detection</option>
              </select>
              <span v-if="alarmErrors.type" class="error-message">{{ alarmErrors.type }}</span>
            </div>
            
            <div class="form-group">
              <label for="deviceScope">Device Scope <span class="required">*</span></label>
              <div class="device-scope-dropdown" ref="deviceScopeDropdown">
                <div class="dropdown-trigger" @click="toggleDeviceDropdown">
                  <span class="selected-text">{{ getSelectedDevicesText() }}</span>
                  <i class="fas fa-chevron-down" :class="{ 'rotated': showDeviceDropdown }"></i>
                </div>
                <div v-if="showDeviceDropdown" class="dropdown-content">
                  <!-- 加载状态 -->
                  <div v-if="isLoadingDevices" class="loading-devices">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Loading devices...</span>
                  </div>
                  
                  <!-- 加载错误 -->
                  <div v-else-if="deviceLoadError" class="device-load-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>{{ deviceLoadError }}</span>
                    <button @click="reloadDevices" class="retry-btn">
                      <i class="fas fa-redo"></i> Retry
                    </button>
                  </div>
                  
                  <!-- 设备列表 -->
                  <div v-else-if="deviceGroups.length > 0" class="device-group">
                    <div class="group-header" @click="toggleAllDevices">
                      <i class="fas fa-chevron-down" :class="{ 'rotated': !allDevicesExpanded }"></i>
                      <label class="group-checkbox">
                        <input 
                          type="checkbox" 
                          :checked="isAllDevicesSelected"
                          @change="selectAllDevices"
                        />
                        <span class="checkmark"></span>
                        All Devices
                      </label>
                    </div>
                    <div v-if="allDevicesExpanded" class="group-content">
                      <div v-for="group in deviceGroups" :key="group.id" class="device-group">
                        <div class="group-header" @click="toggleGroup(group.id)">
                          <i class="fas fa-chevron-down" :class="{ 'rotated': !group.expanded }"></i>
                          <label class="group-checkbox">
                            <input 
                              type="checkbox" 
                              :checked="isGroupSelected(group.id)"
                              :indeterminate="isGroupIndeterminate(group.id)"
                              @change="selectGroup(group.id)"
                            />
                            <span class="checkmark"></span>
                            {{ group.name }}
                          </label>
                        </div>
                        <div v-if="group.expanded" class="group-devices">
                          <label v-for="device in group.devices" :key="device.id" class="device-checkbox">
                            <input 
                              type="checkbox" 
                              :value="device.id"
                              v-model="alarmForm.selectedDevices"
                            />
                            <span class="checkmark"></span>
                            {{ device.name }}
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 无设备数据 -->
                  <div v-else class="no-devices">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>No devices available</span>
                  </div>
                </div>
              </div>
              <span v-if="alarmErrors.deviceScope" class="error-message">{{ alarmErrors.deviceScope }}</span>
            </div>
            
            <!-- Bluetooth Beacons 选择 (仅在 checkin 和 position 类型时显示) -->
            <div v-if="alarmForm.type === 'checkin' || alarmForm.type === 'position'" class="form-group">
              <label for="beaconScope">Bluetooth Beacons <span class="required">*</span></label>
              <div class="beacon-scope-dropdown" ref="beaconScopeDropdown">
                <div class="dropdown-trigger" @click="toggleBeaconDropdown">
                  <span class="selected-text">{{ getSelectedBeaconsText() }}</span>
                  <i class="fas fa-chevron-down" :class="{ 'rotated': showBeaconDropdown }"></i>
                </div>
                <div v-if="showBeaconDropdown" class="dropdown-content">
                  <!-- 加载状态 -->
                  <div v-if="isLoadingBeacons" class="loading-beacons">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Loading beacons...</span>
                  </div>
                  
                  <!-- 加载错误 -->
                  <div v-else-if="beaconLoadError" class="beacon-load-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>{{ beaconLoadError }}</span>
                    <button @click="reloadBeacons" class="retry-btn">
                      <i class="fas fa-redo"></i> Retry
                    </button>
                  </div>
                  
                  <!-- Beacon 地图分组列表 -->
                  <div v-else-if="beaconMaps.length > 0" class="beacon-maps">
                    <div v-for="map in beaconMaps" :key="map.name" class="beacon-map-group">
                      <div class="map-header" @click="toggleBeaconMap(map.name)">
                        <i class="fas fa-chevron-down" :class="{ 'rotated': !map.expanded }"></i>
                        <label class="map-checkbox" @click.stop>
                          <input 
                            type="checkbox" 
                            :checked="isMapSelected(map.name)"
                            :indeterminate="isMapIndeterminate(map.name)"
                            @change="(e) => handleMapCheckboxChange(e, map.name)"
                            @click.stop
                          />
                          <span class="checkmark"></span>
                          {{ map.name }} ({{ map.beacons.length }})
                        </label>
                      </div>
                      <div v-if="map.expanded" class="map-beacons">
                        <div v-for="beacon in map.beacons" :key="beacon.id" class="beacon-checkbox">
                          <label @click.stop>
                            <input 
                              type="checkbox" 
                              :checked="isBeaconSelected(beacon.id)"
                              @change="toggleBeaconSelection(beacon.id)"
                            />
                            <span class="checkmark"></span>
                            {{ beacon.displayName }}
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 无 beacon 数据 -->
                  <div v-else class="no-beacons">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>No beacons available</span>
                  </div>
                </div>
              </div>
              <span v-if="alarmErrors.beaconScope" class="error-message">{{ alarmErrors.beaconScope }}</span>
            </div>
            
            <div class="form-group">
              <label>Enable Alarm</label>
              <div class="alarm-status">
                <label class="status-toggle">
                  <input 
                    type="checkbox" 
                    v-model="alarmForm.enabled"
                    class="status-input"
                  />
                  <span class="status-slider"></span>
                </label>
                <span class="status-text" :class="{ enabled: alarmForm.enabled, disabled: !alarmForm.enabled }">
                  {{ alarmForm.enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>
          </form>
          
          <div v-if="alarmSaveError" class="error-message">
            {{ alarmSaveError }}
          </div>
        </div>
        <div class="modal-footer">
          <button 
            @click="saveAlarm"
            class="save-btn"
            :disabled="alarmSaving"
          >
            <i class="fas fa-save"></i> 
            {{ alarmSaving ? 'Saving...' : 'Save' }}
          </button>
          <button 
            @click="closeAlarmModal"
            class="cancel-btn"
            :disabled="alarmSaving"
          >
            <i class="fas fa-times"></i> Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { fetchApi } from '@/utils/httpClient.js';
import { API_ENDPOINTS } from '@/config/api.js';

// Props
const props = defineProps({
  statusMessage: {
    type: String,
    default: ''
  }
});

// Emits
const emit = defineEmits(['update-status']);

// Alarm Settings 相关状态
const alarmList = ref([
  {
    id: 1,
    name: 'SOS Alarm',
    type: 'sos',
    selectedDevices: [], // 从API加载后填充真实的trackerId
    enabled: true,
    createdAt: '2023-12-01'
  },
  {
    id: 2,
    name: 'Offline Alarm',
    type: 'offline',
    selectedDevices: [],
    enabled: true,
    createdAt: '2023-12-02'
  },
  {
    id: 3,
    name: 'Check-in Event',
    type: 'checkin',
    selectedDevices: [],
    enabled: false,
    createdAt: '2023-12-03'
  },
  {
    id: 4,
    name: 'Position Detection',
    type: 'position',
    selectedDevices: [],
    enabled: true,
    createdAt: '2023-12-04'
  }
]);

const showAlarmModal = ref(false);
const isEditingAlarm = ref(false);
const editingAlarmId = ref(null);
const alarmSaving = ref(false);
const alarmSaveError = ref('');

const alarmForm = ref({
  name: '',
  type: '',
  selectedDevices: [],
  selectedBeacons: [],
  enabled: true
});

const alarmErrors = ref({
  name: '',
  type: '',
  deviceScope: '',
  beaconScope: ''
});

// 分页相关
const currentPage = ref(1);
const itemsPerPage = 5;

// Device Scope 相关状态
const showDeviceDropdown = ref(false);
const allDevicesExpanded = ref(true);
const deviceGroups = ref([]);
const isLoadingDevices = ref(false);
const deviceLoadError = ref('');
const deviceScopeDropdown = ref(null);

// Beacon Scope 相关状态
const showBeaconDropdown = ref(false);
const beaconMaps = ref([]);
const isLoadingBeacons = ref(false);
const beaconLoadError = ref('');
const beaconScopeDropdown = ref(null);

// 计算属性
const totalPages = computed(() => {
  return Math.ceil(alarmList.value.length / itemsPerPage);
});

const paginatedAlarms = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return alarmList.value.slice(start, end);
});

// Device Scope 相关计算属性
const allDeviceIds = computed(() => {
  return deviceGroups.value.flatMap(group => group.devices.map(device => device.id));
});

const isAllDevicesSelected = computed(() => {
  return allDeviceIds.value.length > 0 && 
         allDeviceIds.value.every(id => alarmForm.value.selectedDevices.includes(id));
});

const isGroupSelected = computed(() => {
  return (groupId) => {
    const group = deviceGroups.value.find(g => g.id === groupId);
    if (!group) return false;
    const groupDeviceIds = group.devices.map(d => d.id);
    return groupDeviceIds.length > 0 && 
           groupDeviceIds.every(id => alarmForm.value.selectedDevices.includes(id));
  };
});

const isGroupIndeterminate = computed(() => {
  return (groupId) => {
    const group = deviceGroups.value.find(g => g.id === groupId);
    if (!group) return false;
    const groupDeviceIds = group.devices.map(d => d.id);
    const selectedInGroup = groupDeviceIds.filter(id => alarmForm.value.selectedDevices.includes(id));
    return selectedInGroup.length > 0 && selectedInGroup.length < groupDeviceIds.length;
  };
});

// 方法
const getAlarmTypeClass = (type) => {
  const classMap = {
    'sos': 'alarm-type-sos',
    'offline': 'alarm-type-offline', 
    'checkin': 'alarm-type-checkin',
    'position': 'alarm-type-position'
  };
  return classMap[type] || 'alarm-type-default';
};

const getAlarmTypeLabel = (type) => {
  const labelMap = {
    'sos': 'SOS Alarm',
    'offline': 'Offline Alarm',
    'checkin': 'Check-in Event',
    'position': 'Position Detection'
  };
  return labelMap[type] || type;
};

// Device Scope 相关方法
const toggleDeviceDropdown = () => {
  showDeviceDropdown.value = !showDeviceDropdown.value;
};

const toggleAllDevices = () => {
  allDevicesExpanded.value = !allDevicesExpanded.value;
};

const toggleGroup = (groupId) => {
  const group = deviceGroups.value.find(g => g.id === groupId);
  if (group) {
    group.expanded = !group.expanded;
  }
};

const selectAllDevices = () => {
  if (isAllDevicesSelected.value) {
    alarmForm.value.selectedDevices = [];
  } else {
    alarmForm.value.selectedDevices = [...allDeviceIds.value];
  }
};

const selectGroup = (groupId) => {
  const group = deviceGroups.value.find(g => g.id === groupId);
  if (!group) return;
  
  const groupDeviceIds = group.devices.map(d => d.id);
  
  if (isGroupSelected.value(groupId)) {
    // 取消选择该组的所有设备
    alarmForm.value.selectedDevices = alarmForm.value.selectedDevices.filter(
      id => !groupDeviceIds.includes(id)
    );
  } else {
    // 选择该组的所有设备
    const newSelected = [...alarmForm.value.selectedDevices];
    groupDeviceIds.forEach(id => {
      if (!newSelected.includes(id)) {
        newSelected.push(id);
      }
    });
    alarmForm.value.selectedDevices = newSelected;
  }
};

const getSelectedDevicesText = () => {
  const selectedCount = alarmForm.value.selectedDevices.length;
  const totalCount = allDeviceIds.value.length;
  
  if (selectedCount === 0) {
    return 'Select devices...';
  } else if (selectedCount === totalCount) {
    return 'All Devices';
  } else {
    return `${selectedCount} device(s) selected`;
  }
};

// 加载设备分组和设备数据
const loadDevicesAndGroups = async () => {
  try {
    isLoadingDevices.value = true;
    deviceLoadError.value = '';
    
    // 并行加载分组和设备数据
    const [groupsResponse, trackersResponse] = await Promise.all([
      fetchApi('/groups'),
      fetchApi('/trackers')
    ]);
    
    // 解析响应数据
    const [groupsData, trackersData] = await Promise.all([
      groupsResponse.json(),
      trackersResponse.json()
    ]);
    
    // 处理分组数据
    const groups = Array.isArray(groupsData) ? groupsData : [];
    
    // 处理设备数据
    const trackers = trackersData && typeof trackersData === 'object' ? trackersData : {};
    
    // 将设备按group_id分组
    const devicesByGroup = {};
    let hasDefaultGroup = false; // 检查是否有默认分组的设备
    
    Object.values(trackers).forEach(tracker => {
      const groupId = tracker.group_id;
      if (!devicesByGroup[groupId]) {
        devicesByGroup[groupId] = [];
      }
      devicesByGroup[groupId].push({
        id: tracker.trackerId, // 用于提交后台的是trackerId
        name: tracker.device_name || tracker.trackerId, // 显示device_name
        trackerId: tracker.trackerId
      });
      
      // 检查是否有group_id为0的设备
      if (groupId === 0) {
        hasDefaultGroup = true;
      }
    });
    
    // 构建最终的设备分组数据
    deviceGroups.value = groups.map(group => ({
      id: group.id,
      name: group.group_name,
      expanded: true,
      devices: devicesByGroup[group.id] || []
    }));
    
    // 如果有group_id为0的设备，添加默认分组
    if (hasDefaultGroup && devicesByGroup[0] && devicesByGroup[0].length > 0) {
      deviceGroups.value.unshift({
        id: 0,
        name: 'Default',
        expanded: true,
        devices: devicesByGroup[0]
      });
    }
    
    console.log('Device groups loaded:', deviceGroups.value);
    
  } catch (error) {
    console.error('Failed to load devices and groups:', error);
    deviceLoadError.value = `Failed to load devices: ${error.message}`;
    emit('update-status', `Failed to load devices: ${error.message}`);
  } finally {
    isLoadingDevices.value = false;
  }
};

// 重新加载设备数据
const reloadDevices = async () => {
  await loadDevicesAndGroups();
};

// 加载 Beacon 数据
const loadBeacons = async () => {
  try {
    isLoadingBeacons.value = true;
    beaconLoadError.value = '';
    
    const response = await fetchApi('/beacons');
    const beaconData = await response.json();
    
    // 将数据转换为地图分组格式
    beaconMaps.value = Object.entries(beaconData).map(([mapName, beacons]) => ({
      name: mapName,
      expanded: true,
      beacons: beacons.map(beacon => ({
        ...beacon,
        id: beacon.macAddress // 使用 MAC 地址作为唯一ID
      }))
    }));
    
    console.log('Beacon maps loaded:', beaconMaps.value);
    
  } catch (error) {
    console.error('Failed to load beacons:', error);
    beaconLoadError.value = `Failed to load beacons: ${error.message}`;
    emit('update-status', `Failed to load beacons: ${error.message}`);
  } finally {
    isLoadingBeacons.value = false;
  }
};

// 重新加载 beacon 数据
const reloadBeacons = async () => {
  await loadBeacons();
};

// Beacon Scope 相关方法
const toggleBeaconDropdown = async () => {
  showBeaconDropdown.value = !showBeaconDropdown.value;
  
  // 在打开下拉框时总是重新加载 beacon 数据，确保数据最新
  if (showBeaconDropdown.value) {
    await loadBeacons();
  }
};

const toggleBeaconMap = (mapName) => {
  const map = beaconMaps.value.find(m => m.name === mapName);
  if (map) {
    map.expanded = !map.expanded;
  }
};

const isMapSelected = computed(() => {
  return (mapName) => {
    const map = beaconMaps.value.find(m => m.name === mapName);
    if (!map) return false;
    const mapBeaconIds = map.beacons.map(b => b.id);
    return mapBeaconIds.length > 0 && 
           mapBeaconIds.every(id => alarmForm.value.selectedBeacons.includes(id));
  };
});

const isMapIndeterminate = computed(() => {
  return (mapName) => {
    const map = beaconMaps.value.find(m => m.name === mapName);
    if (!map) return false;
    const mapBeaconIds = map.beacons.map(b => b.id);
    const selectedInMap = mapBeaconIds.filter(id => alarmForm.value.selectedBeacons.includes(id));
    return selectedInMap.length > 0 && selectedInMap.length < mapBeaconIds.length;
  };
});

const selectBeaconMap = (mapName) => {
  const map = beaconMaps.value.find(m => m.name === mapName);
  if (!map) return;
  
  const mapBeaconIds = map.beacons.map(b => b.id);
  
  if (isMapSelected.value(mapName)) {
    // 取消选择该地图的所有 beacon
    alarmForm.value.selectedBeacons = alarmForm.value.selectedBeacons.filter(
      id => !mapBeaconIds.includes(id)
    );
  } else {
    // 选择该地图的所有 beacon
    const newSelected = [...alarmForm.value.selectedBeacons];
    mapBeaconIds.forEach(id => {
      if (!newSelected.includes(id)) {
        newSelected.push(id);
      }
    });
    alarmForm.value.selectedBeacons = newSelected;
  }
};

const handleMapCheckboxChange = (event, mapName) => {
  event.stopPropagation();
  selectBeaconMap(mapName);
};

const isBeaconSelected = (beaconId) => {
  return alarmForm.value.selectedBeacons.includes(beaconId);
};

const toggleBeaconSelection = (beaconId) => {
  const currentSelected = [...alarmForm.value.selectedBeacons];
  const index = currentSelected.indexOf(beaconId);
  
  if (index > -1) {
    // 取消选择
    currentSelected.splice(index, 1);
  } else {
    // 选择
    currentSelected.push(beaconId);
  }
  
  alarmForm.value.selectedBeacons = currentSelected;
};

const getSelectedBeaconsText = () => {
  const selectedCount = alarmForm.value.selectedBeacons.length;
  
  if (selectedCount === 0) {
    return 'Select beacons...';
  } else if (selectedCount === 1) {
    return '1 beacon selected';
  } else {
    return `${selectedCount} beacons selected`;
  }
};

const openCreateAlarmModal = async () => {
  isEditingAlarm.value = false;
  editingAlarmId.value = null;
  alarmForm.value = {
    name: '',
    type: '',
    selectedDevices: [],
    selectedBeacons: [],
    enabled: true
  };
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: ''
  };
  alarmSaveError.value = '';
  showDeviceDropdown.value = false;
  showBeaconDropdown.value = false;
  showAlarmModal.value = true;
  
  // 加载设备数据
  if (deviceGroups.value.length === 0) {
    await loadDevicesAndGroups();
  }
};

const editAlarm = async (alarm) => {
  isEditingAlarm.value = true;
  editingAlarmId.value = alarm.id;
  alarmForm.value = {
    name: alarm.name,
    type: alarm.type,
    selectedDevices: alarm.selectedDevices || [],
    selectedBeacons: alarm.selectedBeacons || [],
    enabled: alarm.enabled
  };
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: ''
  };
  alarmSaveError.value = '';
  showDeviceDropdown.value = false;
  showBeaconDropdown.value = false;
  showAlarmModal.value = true;
  
  // 加载设备数据
  if (deviceGroups.value.length === 0) {
    await loadDevicesAndGroups();
  }
};

const closeAlarmModal = () => {
  if (alarmSaving.value) {
    return; // 保存中不允许关闭
  }
  showAlarmModal.value = false;
  isEditingAlarm.value = false;
  editingAlarmId.value = null;
  alarmForm.value = {
    name: '',
    type: '',
    selectedDevices: [],
    selectedBeacons: [],
    enabled: true
  };
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: ''
  };
  alarmSaveError.value = '';
  showDeviceDropdown.value = false;
  showBeaconDropdown.value = false;
};

const validateAlarmForm = () => {
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: ''
  };

  let isValid = true;

  // 验证名称
  if (!alarmForm.value.name || !alarmForm.value.name.trim()) {
    alarmErrors.value.name = 'Alarm name is required';
    isValid = false;
  } else if (alarmForm.value.name.trim().length > 50) {
    alarmErrors.value.name = 'Alarm name is too long';
    isValid = false;
  } else {
    // 检查名称是否重复（编辑时排除自己）
    const isDuplicate = alarmList.value.some(alarm => 
      alarm.name.toLowerCase() === alarmForm.value.name.trim().toLowerCase() &&
      alarm.id !== editingAlarmId.value
    );
    if (isDuplicate) {
      alarmErrors.value.name = 'Alarm name already exists';
      isValid = false;
    }
  }

  // 验证类型
  if (!alarmForm.value.type) {
    alarmErrors.value.type = 'Alarm type is required';
    isValid = false;
  }

  // 验证设备范围
  if (!alarmForm.value.selectedDevices || alarmForm.value.selectedDevices.length === 0) {
    alarmErrors.value.deviceScope = 'At least one device must be selected';
    isValid = false;
  }

  // 验证 beacon 范围 (仅对 checkin 和 position 类型)
  if (alarmForm.value.type === 'checkin' || alarmForm.value.type === 'position') {
    if (!alarmForm.value.selectedBeacons || alarmForm.value.selectedBeacons.length === 0) {
      alarmErrors.value.beaconScope = 'At least one beacon must be selected for this alarm type';
      isValid = false;
    }
  }

  return isValid;
};

const saveAlarm = async () => {
  if (!validateAlarmForm()) {
    return;
  }

  try {
    alarmSaving.value = true;
    alarmSaveError.value = '';

    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 800));

    if (isEditingAlarm.value) {
      // 编辑现有报警
      const index = alarmList.value.findIndex(alarm => alarm.id === editingAlarmId.value);
      if (index !== -1) {
        alarmList.value[index] = {
          ...alarmList.value[index],
          name: alarmForm.value.name.trim(),
          type: alarmForm.value.type,
          selectedDevices: [...alarmForm.value.selectedDevices],
          selectedBeacons: [...alarmForm.value.selectedBeacons],
          enabled: alarmForm.value.enabled,
          updatedAt: new Date().toISOString().split('T')[0]
        };
      }
      emit('update-status', 'Alarm updated successfully');
    } else {
      // 创建新报警
      const newAlarm = {
        id: Math.max(...alarmList.value.map(a => a.id), 0) + 1,
        name: alarmForm.value.name.trim(),
        type: alarmForm.value.type,
        selectedDevices: [...alarmForm.value.selectedDevices],
        selectedBeacons: [...alarmForm.value.selectedBeacons],
        enabled: alarmForm.value.enabled,
        createdAt: new Date().toISOString().split('T')[0]
      };
      alarmList.value.push(newAlarm);
      emit('update-status', 'Alarm created successfully');
    }

    closeAlarmModal();

  } catch (error) {
    console.error('保存报警失败:', error);
    alarmSaveError.value = `Failed to save alarm: ${error.message}`;
  } finally {
    alarmSaving.value = false;
  }
};

const toggleAlarmStatus = async (alarm) => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const message = alarm.enabled ? 'Alarm enabled' : 'Alarm disabled';
    emit('update-status', message);
    
  } catch (error) {
    console.error('切换报警状态失败:', error);
    // 回滚状态
    alarm.enabled = !alarm.enabled;
    emit('update-status', `Failed to toggle alarm status: ${error.message}`);
  }
};

const deleteAlarm = async (alarmId, index) => {
  const alarm = alarmList.value.find(a => a.id === alarmId);
  if (!alarm) return;

  const confirmed = confirm(`Are you sure you want to delete "${alarm.name}"?`);
  if (!confirmed) return;

  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500));
    
    alarmList.value = alarmList.value.filter(a => a.id !== alarmId);
    
    // 调整当前页码，防止超出范围
    const newTotalPages = Math.ceil(alarmList.value.length / itemsPerPage);
    if (currentPage.value > newTotalPages && newTotalPages > 0) {
      currentPage.value = newTotalPages;
    }
    
    emit('update-status', 'Alarm deleted successfully');
    
  } catch (error) {
    console.error('删除报警失败:', error);
    emit('update-status', `Failed to delete alarm: ${error.message}`);
  }
};

// 处理点击外部关闭下拉框
const handleClickOutside = (event) => {
  // 检查设备选择下拉框
  if (showDeviceDropdown.value && deviceScopeDropdown.value && !deviceScopeDropdown.value.contains(event.target)) {
    showDeviceDropdown.value = false;
  }
  
  // 检查beacon选择下拉框
  if (showBeaconDropdown.value && beaconScopeDropdown.value && !beaconScopeDropdown.value.contains(event.target)) {
    showBeaconDropdown.value = false;
  }
};

// 组件挂载时预加载设备数据和添加事件监听
onMounted(() => {
  loadDevicesAndGroups();
  document.addEventListener('click', handleClickOutside);
});

// 组件卸载时移除事件监听
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* === Alarm Settings 样式 === */
.alarm-settings-section {
  margin-bottom: 2rem;
}

.create-alarm-btn {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
}

.create-alarm-btn:hover {
  background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.4);
}

.empty-alarm-list {
  text-align: center;
  padding: 3rem;
  color: #6c757d;
}

.empty-alarm-list .empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
  color: #adb5bd;
}

.empty-alarm-list p {
  margin: 0.5rem 0;
  font-size: 1rem;
}

.empty-alarm-list .hint {
  font-size: 0.9rem;
  opacity: 0.8;
}

.alarm-table-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.alarm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  table-layout: fixed;
}

.alarm-table th {
  background: #f8f9fa;
  color: #495057;
  font-weight: 600;
  padding: 1rem;
  text-align: center;
  border-bottom: 2px solid #dee2e6;
  white-space: nowrap;
}

.alarm-table th:nth-child(1) {
  text-align: left;
}

.alarm-table th:nth-child(1) { width: 25%; } /* Alarm Name */
.alarm-table th:nth-child(2) { width: 25%; } /* Alarm Type */
.alarm-table th:nth-child(3) { width: 25%; } /* Status */
.alarm-table th:nth-child(4) { width: 25%; } /* Actions */

.alarm-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
  height: 60px;
  text-align: center;
}

.alarm-table td:nth-child(1) {
  text-align: left;
}

.alarm-table td:nth-child(3) {
  text-align: center;
}

.alarm-row {
  height: 60px;
}

.alarm-row:hover {
  background: #f8f9fa;
}

.alarm-name {
  font-weight: 500;
  color: #2c3e50;
}

.alarm-type-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
  white-space: nowrap;
}

.alarm-type-sos {
  background: #ffeaa7;
  color: #d63031;
}

.alarm-type-offline {
  background: #a29bfe;
  color: #6c5ce7;
}

.alarm-type-checkin {
  background: #74b9ff;
  color: #0984e3;
}

.alarm-type-position {
  background: #fd79a8;
  color: #e84393;
}

.alarm-type-default {
  background: #ddd6fe;
  color: #7c3aed;
}

.alarm-status {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.75rem;
}

.status-toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 22px;
  cursor: pointer;
}

.status-input {
  opacity: 0;
  width: 0;
  height: 0;
}

.status-slider {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 22px;
}

.status-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.status-input:checked + .status-slider {
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
}

.status-input:checked + .status-slider:before {
  transform: translateX(22px);
}

.status-text {
  font-size: 0.85rem;
  font-weight: 500;
  min-width: 60px;
}

.status-text.enabled {
  color: #28a745;
}

.status-text.disabled {
  color: #6c757d;
}

.alarm-actions {
  display: flex;
  gap: 0.25rem;
  justify-content: center;
  align-items: center;
}

.action-btn {
  padding: 0.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
}

.edit-btn {
  background: #007bff;
  color: white;
}

.edit-btn:hover {
  background: #0056b3;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 123, 255, 0.3);
}

.delete-btn {
  background: #dc3545;
  color: white;
}

.delete-btn:hover {
  background: #c82333;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
}

.alarm-table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
}

.alarm-stats {
  color: #6c757d;
  font-size: 0.9rem;
  font-weight: 500;
}

.alarm-pagination {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.pagination-btn {
  padding: 0.4rem 0.6rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #495057;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.pagination-btn:hover:not(:disabled) {
  background: #e9ecef;
  border-color: #adb5bd;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 0.9rem;
  color: #495057;
  font-weight: 500;
  min-width: 60px;
  text-align: center;
}

/* Modal 样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  z-index: 1000;
  backdrop-filter: blur(2px);
  padding: 1rem 0;
  box-sizing: border-box;
  overflow-y: auto;
}

.alarm-modal {
  background: white;
  border-radius: 12px;
  width: 95%;
  max-width: 700px;
  max-height: 95vh;
  min-height: 70vh;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
  display: flex;
  flex-direction: column;
}

@keyframes modalSlideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.alarm-modal .modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alarm-modal .modal-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.25rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.alarm-modal .modal-header h3 i {
  color: #667eea;
}

.alarm-modal .modal-body {
  padding: 1.5rem;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.alarm-modal .modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
}

.required {
  color: #dc3545;
  font-weight: bold;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input.error,
.form-textarea.error {
  border-color: #dc3545;
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.error-message {
  margin-top: 0.5rem;
  color: #dc2626;
  font-size: 0.8rem;
  font-weight: 500;
}

/* Device Scope Dropdown 样式 */
.device-scope-dropdown {
  position: relative;
  width: 100%;
}

.dropdown-trigger {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 50px;
  box-sizing: border-box;
}

.dropdown-trigger:hover {
  border-color: #667eea;
}

.dropdown-trigger.error {
  border-color: #dc3545;
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.selected-text {
  flex: 1;
  text-align: left;
  color: #495057;
  font-size: 0.95rem;
}

.selected-text:empty::before {
  content: 'Select devices...';
  color: #9ca3af;
}

.dropdown-trigger i {
  color: #6c757d;
  transition: transform 0.2s ease;
}

.dropdown-trigger i.rotated {
  transform: rotate(180deg);
}

.dropdown-content {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  max-height: 400px;
  overflow-y: auto;
  margin-top: 2px;
}

.device-group {
  border-bottom: 1px solid #f1f3f4;
}

.device-group:last-child {
  border-bottom: none;
}

.group-header {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  gap: 0.5rem;
  min-height: 44px;
  height: 44px;
}

.group-header:hover {
  background: #f8f9fa;
}

.group-header i {
  color: #6c757d;
  transition: transform 0.2s ease;
  font-size: 0.8rem;
}

.group-header i.rotated {
  transform: rotate(-90deg);
}

.group-checkbox,
.device-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: #495057;
  user-select: none;
  flex: 1;
}

.group-checkbox {
  font-weight: 500;
  min-height: 20px;
  height: 20px;
  align-items: center;
}

.group-checkbox input,
.device-checkbox input {
  margin: 0;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkmark {
  position: relative;
  display: inline-block;
  width: 16px;
  height: 16px;
}

.group-content {
  padding-left: 1.5rem;
}

.group-devices {
  padding: 0.5rem 0 0.5rem 2rem;
  border-top: 1px solid #f1f3f4;
}

.device-checkbox {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  margin: 0;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.device-checkbox:hover {
  background: #f8f9fa;
}

.device-checkbox input {
  margin-right: 0.5rem;
}

/* 加载和错误状态样式 */
.loading-devices,
.device-load-error,
.no-devices,
.loading-beacons,
.beacon-load-error,
.no-beacons {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 0.75rem;
  color: #6c757d;
  font-size: 0.9rem;
}

.loading-devices i {
  color: #007bff;
  font-size: 1.1rem;
}

.device-load-error {
  flex-direction: column;
  text-align: center;
}

.device-load-error i {
  color: #dc3545;
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.retry-btn {
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.retry-btn:hover {
  background: #0056b3;
}

.no-devices i,
.no-beacons i {
  color: #ffc107;
  font-size: 1.2rem;
}

/* Beacon Scope Dropdown 样式 */
.beacon-scope-dropdown {
  position: relative;
  width: 100%;
}

.beacon-maps {
  padding: 0;
}

.beacon-map-group {
  border-bottom: 1px solid #f1f3f4;
}

.beacon-map-group:last-child {
  border-bottom: none;
}

.map-header {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  gap: 0.5rem;
  min-height: 44px;
  height: 44px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.map-header:hover {
  background: #e9ecef;
}

.map-header i {
  color: #6c757d;
  transition: transform 0.2s ease;
  font-size: 0.8rem;
}

.map-header i.rotated {
  transform: rotate(-90deg);
}

.map-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: #495057;
  user-select: none;
  flex: 1;
  font-weight: 500;
  min-height: 20px;
  height: 20px;
}

.map-checkbox input {
  margin: 0;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.map-beacons {
  padding: 0.5rem 0 0.5rem 2rem;
  background: #ffffff;
}

.beacon-checkbox {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  margin: 0;
  cursor: pointer;
  transition: background-color 0.2s ease;
  color: #495057;
  font-size: 0.9rem;
  gap: 0.5rem;
}

.beacon-checkbox:hover {
  background: #f8f9fa;
}

.beacon-checkbox input {
  margin: 0;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.loading-beacons i {
  color: #007bff;
  font-size: 1.1rem;
}

.beacon-load-error {
  flex-direction: column;
  text-align: center;
}

.beacon-load-error i {
  color: #dc3545;
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.save-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

.save-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.save-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.cancel-btn {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cancel-btn:hover:not(:disabled) {
  background: #5a6268;
  transform: translateY(-1px);
}

.cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.close-btn {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: color 0.2s ease;
}

.close-btn:hover {
  color: #dc3545;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .alarm-table-container {
    overflow-x: auto;
  }
  
  .alarm-table {
    min-width: 600px;
  }
  
  .alarm-table th,
  .alarm-table td {
    padding: 0.75rem 0.5rem;
  }
  
  .alarm-table-footer {
    flex-direction: column;
    gap: 1rem;
    align-items: center;
  }
  
  .alarm-modal {
    width: 98%;
    margin: 0.5rem;
    max-width: none;
    max-height: calc(100vh - 1rem);
    min-height: calc(100vh - 2rem);
  }
  
  .modal-overlay {
    padding: 0.5rem 0;
  }
  
  .alarm-modal .modal-footer {
    flex-direction: column;
  }
  
  .alarm-modal .save-btn,
  .alarm-modal .cancel-btn {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .alarm-status {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
  
  .alarm-actions {
    gap: 0.25rem;
  }
  
  .action-btn {
    width: 28px;
    height: 28px;
    font-size: 0.8rem;
  }
}
</style>
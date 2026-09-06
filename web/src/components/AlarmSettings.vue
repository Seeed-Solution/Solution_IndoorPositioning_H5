<template>
  <div class="alarm-settings-section card">
    <div class="card-header">
      <h2><i class="fas fa-bell"></i> {{ $t('alarmSettings.title') }}</h2>
      <div class="header-actions">
        <button 
          @click="openCreateAlarmModal"
          class="create-alarm-btn"
        >
          <i class="fas fa-plus"></i> {{ $t('alarmSettings.createAlarm') }}
        </button>
      </div>
    </div>
    <div class="card-content">
      <!-- 加载状态 -->
      <div v-if="isLoadingAlarms" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <p>{{ $t('alarmSettings.loading') }}</p>
      </div>
      
      <!-- 加载错误 -->
      <div v-else-if="alarmLoadError" class="error-state">
        <i class="fas fa-exclamation-triangle"></i>
        <p>{{ alarmLoadError }}</p>
        <button @click="loadAlarmList" class="retry-btn">
          <i class="fas fa-redo"></i> {{ $t('alarmSettings.retry') }}
        </button>
      </div>
      
      <!-- 空告警列表 -->
      <div v-else-if="alarmList.length === 0" class="empty-alarm-list">
        <i class="fas fa-bell-slash empty-icon"></i>
        <p>{{ $t('alarmSettings.noAlarms') }}</p>
        <p class="hint">{{ $t('alarmSettings.noAlarmsHint') }}</p>
      </div>
      <div v-else class="alarm-table-container">
        <table class="alarm-table">
          <thead>
            <tr>
              <th>{{ $t('alarmSettings.table.alarmName') }}</th>
              <th>{{ $t('alarmSettings.table.alarmType') }}</th>
              <th>{{ $t('alarmSettings.table.status') }}</th>
              <th>{{ $t('alarmSettings.table.actions') }}</th>
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
                    {{ alarm.enabled ? $t('alarmSettings.enabled') : $t('alarmSettings.disabled') }}
                  </span>
                </div>
              </td>
              <td>
                <div class="alarm-actions">
                  <button 
                    @click="editAlarm(alarm)"
                    class="action-btn edit-btn"
                    :title="$t('alarmSettings.edit')"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button 
                    @click="deleteAlarm(alarm.id, index)"
                    class="action-btn delete-btn"
                    :title="$t('alarmSettings.delete')"
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
            {{ $t('alarmSettings.pagination.total') }} {{ totalAlarms }} {{ $t('alarmSettings.pagination.alarms') }}
          </div>
          <div class="alarm-pagination" v-if="totalPages > 1">
            <button 
              @click="goToPreviousPage"
              :disabled="currentPage === 1"
              class="pagination-btn"
            >
              <i class="fas fa-chevron-left"></i>
            </button>
            <span class="pagination-info">
              {{ currentPage }} / {{ totalPages }}
            </span>
            <button 
              @click="goToNextPage"
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
      <div class="alarm-modal" @click.stop="handleModalClick">
        <div class="modal-header">
          <h3>
            <i class="fas fa-bell"></i>
            {{ isEditingAlarm ? $t('alarmSettings.editAlarm') : $t('alarmSettings.createAlarm') }}
          </h3>
          <button @click="closeAlarmModal" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveAlarm">
            <div class="form-group">
              <label for="alarmName">{{ $t('alarmSettings.form.alarmName') }} <span class="required">{{ $t('alarmSettings.form.required') }}</span></label>
              <input 
                type="text" 
                id="alarmName"
                v-model="alarmForm.name" 
                class="form-input"
                :class="{ 'error': alarmErrors.name }"
                :placeholder="$t('alarmSettings.form.alarmNamePlaceholder')"
                required
              />
              <span v-if="alarmErrors.name" class="error-message">{{ alarmErrors.name }}</span>
            </div>
            
            <div class="form-group">
              <label for="alarmType">{{ $t('alarmSettings.form.alarmType') }} <span class="required">{{ $t('alarmSettings.form.required') }}</span></label>
              <select 
                id="alarmType"
                v-model="alarmForm.type" 
                class="form-input"
                :class="{ 'error': alarmErrors.type }"
                required
              >
                <option value="" disabled>{{ $t('alarmSettings.form.selectAlarmType') }}</option>
                <option value="sos">{{ $t('alarmSettings.types.sos') }}</option>
                <option value="offline">{{ $t('alarmSettings.types.offline') }}</option>
                <option value="checkin">{{ $t('alarmSettings.types.checkin') }}</option>
                <option value="position">{{ $t('alarmSettings.types.position') }}</option>
              </select>
              <span v-if="alarmErrors.type" class="error-message">{{ alarmErrors.type }}</span>
            </div>
            
            <div class="form-group">
              <label for="deviceScope">{{ $t('alarmSettings.form.deviceScope') }} <span class="required">{{ $t('alarmSettings.form.required') }}</span></label>
              <div class="device-scope-dropdown" ref="deviceScopeDropdown">
                <div class="dropdown-trigger" @click="toggleDeviceDropdown">
                  <span class="selected-text">{{ getSelectedDevicesText() }}</span>
                  <i class="fas fa-chevron-down" :class="{ 'rotated': showDeviceDropdown }"></i>
                </div>
                <div v-if="showDeviceDropdown" class="dropdown-content">
                  <!-- 加载状态 -->
                  <div v-if="isLoadingDevices" class="loading-devices">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>{{ $t('alarmSettings.deviceScope.loadingDevices') }}</span>
                  </div>
                  
                  <!-- 加载错误 -->
                  <div v-else-if="deviceLoadError" class="device-load-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>{{ deviceLoadError }}</span>
                    <button @click="reloadDevices" class="retry-btn">
                      <i class="fas fa-redo"></i> {{ $t('alarmSettings.retry') }}
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
                        {{ $t('alarmSettings.deviceScope.allDevices') }}
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
                    <span>{{ $t('alarmSettings.deviceScope.noDevices') }}</span>
                  </div>
                </div>
              </div>
              <span v-if="alarmErrors.deviceScope" class="error-message">{{ alarmErrors.deviceScope }}</span>
            </div>
            
            <!-- 判定模式: BLE 信标白名单 vs 地理围栏 (仅 checkin / position) -->
            <div v-if="alarmForm.type === 'checkin' || alarmForm.type === 'position'" class="form-group">
              <label>{{ $t('alarmGeo.mode') }}</label>
              <div class="location-mode-options">
                <label class="location-mode-option">
                  <input type="radio" value="ble" v-model="alarmForm.locationMode" name="locationMode" />
                  <span>{{ $t('alarmGeo.modeBle') }}</span>
                </label>
                <label class="location-mode-option">
                  <input type="radio" value="geo" v-model="alarmForm.locationMode" name="locationMode" />
                  <span>{{ $t('alarmGeo.modeGeo') }}</span>
                </label>
              </div>
            </div>

            <!-- 地理围栏配置 -->
            <div v-if="isGeoMode" class="form-group">
              <label>{{ $t('alarmGeo.transition') }}</label>
              <div class="location-mode-options">
                <label class="location-mode-option">
                  <input type="radio" value="enter" v-model="alarmForm.transition" name="transition" />
                  <span>{{ $t('alarmGeo.transitionEnter') }}</span>
                </label>
                <label class="location-mode-option">
                  <input type="radio" value="exit" v-model="alarmForm.transition" name="transition" />
                  <span>{{ $t('alarmGeo.transitionExit') }}</span>
                </label>
                <label class="location-mode-option">
                  <input type="radio" value="both" v-model="alarmForm.transition" name="transition" />
                  <span>{{ $t('alarmGeo.transitionBoth') }}</span>
                </label>
              </div>

              <label class="geofence-label">{{ $t('alarmGeo.fence') }} <span class="required">{{ $t('alarmSettings.form.required') }}</span></label>
              <GeofenceEditor v-model="alarmForm.geofenceId" />
              <span v-if="alarmErrors.geofence" class="error-message">{{ alarmErrors.geofence }}</span>
            </div>

            <!-- Bluetooth Beacons 选择 (BLE 模式下的 checkin 和 position 类型) -->
            <div v-if="!isGeoMode && (alarmForm.type === 'checkin' || alarmForm.type === 'position')" class="form-group">
              <label for="beaconScope">{{ $t('alarmSettings.form.bluetoothBeacons') }} <span class="required">{{ $t('alarmSettings.form.required') }}</span></label>
              <div class="beacon-scope-dropdown" ref="beaconScopeDropdown">
                <div class="dropdown-trigger" @click="toggleBeaconDropdown">
                  <span class="selected-text">{{ getSelectedBeaconsText() }}</span>
                  <i class="fas fa-chevron-down" :class="{ 'rotated': showBeaconDropdown }"></i>
                </div>
                <div v-if="showBeaconDropdown" class="dropdown-content">
                  <!-- 加载状态 -->
                  <div v-if="isLoadingBeacons" class="loading-beacons">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>{{ $t('alarmSettings.beaconScope.loadingBeacons') }}</span>
                  </div>
                  
                  <!-- 加载错误 -->
                  <div v-else-if="beaconLoadError" class="beacon-load-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>{{ beaconLoadError }}</span>
                    <button @click="reloadBeacons" class="retry-btn">
                      <i class="fas fa-redo"></i> {{ $t('alarmSettings.retry') }}
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
                    <span>{{ $t('alarmSettings.beaconScope.noBeacons') }}</span>
                  </div>
                </div>
              </div>
              <span v-if="alarmErrors.beaconScope" class="error-message">{{ alarmErrors.beaconScope }}</span>
            </div>
            
            <!-- Check-in Event 额外配置项 -->
            <div v-if="alarmForm.type === 'checkin'" class="form-group">
              <label>{{ $t('alarmSettings.form.checkinRule') }}</label>
              <div class="checkin-rule-options">
                <!-- 暂时屏蔽，后期根据需要启用 -->
                <!-- 
                <label class="checkin-option">
                  <input 
                    type="radio" 
                    value="sequential"
                    v-model="alarmForm.checkinRule"
                    name="checkinRule"
                  />
                  <span class="radio-mark"></span>
                  <div class="checkin-content">
                    <div class="checkin-title">Sequential check-in at all beacons</div>
                    <div class="checkin-description">Trigger when device beacons in all configured beacons in order</div>
                  </div>
                </label>
                
                <label class="checkin-option">
                  <input 
                    type="radio" 
                    value="all"
                    v-model="alarmForm.checkinRule"
                    name="checkinRule"
                  />
                  <span class="radio-mark"></span>
                  <div class="checkin-content">
                    <div class="checkin-title">Check-in at all beacons</div>
                    <div class="checkin-description">Trigger when device checks in at all of the configured beacons in any order</div>
                  </div>
                </label>
                -->
                
                <label class="checkin-option">
                  <input 
                    type="radio" 
                    value="any"
                    v-model="alarmForm.checkinRule"
                    name="checkinRule"
                  />
                  <span class="radio-mark"></span>
                  <div class="checkin-content">
                    <div class="checkin-title">{{ $t('alarmSettings.checkinOptions.anyBeacon') }}</div>
                    <div class="checkin-description">{{ $t('alarmSettings.checkinOptions.anyBeaconDesc') }}</div>
                  </div>
                </label>
              </div>
            </div>

            <!-- Check-in Range Configuration -->
            <div v-if="alarmForm.type === 'checkin'" class="form-group">
              <label for="checkinRange">{{ $t('alarmSettings.form.checkinRange') }}</label>
              <div class="range-input-group">
                <input 
                  type="number" 
                  id="checkinRange"
                  v-model="alarmForm.checkinRange"
                  class="form-input range-input"
                  :class="{ 'error': alarmErrors.checkinRange }"
                  placeholder="10"
                  min="1"
                  max="100"
                  step="0.1"
                />
                <span class="range-unit">{{ $t('alarmSettings.units.meters') }}</span>
              </div>
              <div class="range-help-text">
                {{ $t('alarmSettings.helpText.checkinRange') }}
              </div>
              <span v-if="alarmErrors.checkinRange" class="error-message">{{ alarmErrors.checkinRange }}</span>
            </div>
            
            <!-- Position Detection 额外配置项 -->
            <div v-if="alarmForm.type === 'position'" class="form-group">
              <label>{{ $t('alarmSettings.form.triggerDuration') }}</label>
              <div class="trigger-duration-options">
                <label class="trigger-option">
                  <input 
                    type="radio" 
                    value="immediate"
                    v-model="alarmForm.triggerType"
                    name="triggerType"
                  />
                  <span class="radio-mark"></span>
                  <div class="trigger-content">
                    <div class="trigger-title">{{ $t('alarmSettings.triggerOptions.immediate') }}</div>
                    <div class="trigger-description">{{ $t('alarmSettings.triggerOptions.immediateDesc') }}</div>
                  </div>
                </label>
                
                <label class="trigger-option">
                  <input 
                    type="radio" 
                    value="duration"
                    v-model="alarmForm.triggerType"
                    name="triggerType"
                  />
                  <span class="radio-mark"></span>
                  <div class="trigger-content">
                    <div class="trigger-title">{{ $t('alarmSettings.triggerOptions.duration') }}</div>
                    <div class="trigger-description">{{ $t('alarmSettings.triggerOptions.durationDesc') }}</div>
                  </div>
                </label>
              </div>
            </div>

            <!-- Duration Configuration (只在选择了 duration-based trigger 时显示) -->
            <div v-if="alarmForm.type === 'position' && alarmForm.triggerType === 'duration'" class="form-group">
              <label for="durationConfig">{{ $t('alarmSettings.form.durationConfig') }}</label>
              <div class="duration-input-group">
                <input 
                  type="number" 
                  id="durationConfig"
                  v-model="alarmForm.triggerDuration"
                  class="form-input duration-input"
                  :class="{ 'error': alarmErrors.triggerDuration }"
                  placeholder="10"
                  min="1"
                  max="1440"
                />
                <span class="duration-unit">{{ $t('alarmSettings.units.minutes') }}</span>
              </div>
              <div class="duration-help-text">
                {{ $t('alarmSettings.helpText.durationConfig') }}
              </div>
              <span v-if="alarmErrors.triggerDuration" class="error-message">{{ alarmErrors.triggerDuration }}</span>
            </div>
            
            <div class="form-group">
              <label>{{ $t('alarmSettings.form.enableAlarm') }}</label>
              <div class="alarm-status form-alarm-status">
                <label class="status-toggle">
                  <input 
                    type="checkbox" 
                    v-model="alarmForm.enabled"
                    class="status-input"
                  />
                  <span class="status-slider"></span>
                </label>
                <span class="status-text" :class="{ enabled: alarmForm.enabled, disabled: !alarmForm.enabled }">
                  {{ alarmForm.enabled ? $t('alarmSettings.enabled') : $t('alarmSettings.disabled') }}
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
            {{ alarmSaving ? $t('alarmSettings.saving') : $t('alarmSettings.save') }}
          </button>
          <button 
            @click="closeAlarmModal"
            class="cancel-btn"
            :disabled="alarmSaving"
          >
            <i class="fas fa-times"></i> {{ $t('alarmSettings.cancel') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="delete-confirm-modal" @click.stop>
        <div class="modal-header">
          <h3>
            <i class="fas fa-exclamation-triangle"></i>
            {{ $t('alarmSettings.deleteConfirm.title') }}
          </h3>
        </div>
        <div class="modal-body">
          <p class="delete-message">
            {{ $t('alarmSettings.deleteConfirm.message') }} 
            <strong>"{{ deleteTargetAlarm?.name }}"</strong>?
          </p>
          <p class="delete-warning">
            {{ $t('alarmSettings.deleteConfirm.warning') }}
          </p>
        </div>
        <div class="modal-footer">
          <button 
            @click="confirmDelete"
            class="delete-confirm-btn"
          >
            <i class="fas fa-trash"></i> 
            {{ $t('alarmSettings.deleteConfirm.confirm') }}
          </button>
          <button 
            @click="cancelDelete"
            class="delete-cancel-btn"
          >
            <i class="fas fa-times"></i> {{ $t('alarmSettings.deleteConfirm.cancel') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 错误提示弹窗 -->
    <div v-if="showErrorModal" class="modal-overlay" @click="closeErrorModal">
      <div class="error-modal" @click.stop>
        <div class="modal-header">
          <h3>
            <i class="fas fa-exclamation-circle"></i>
            {{ $t('alarmSettings.errorModal.title') }}
          </h3>
        </div>
        <div class="modal-body">
          <p class="error-message-text" v-html="errorMessage.replace('\n', '<br>')"></p>
        </div>
        <div class="modal-footer">
          <button 
            @click="closeErrorModal"
            class="error-confirm-btn"
          >
            <i class="fas fa-check"></i> 
            {{ $t('alarmSettings.errorModal.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import GeofenceEditor from '@/components/GeofenceEditor.vue';
import { apiRequest } from '@/utils/httpClient.js';
import { API_ENDPOINTS } from '@/config/api.js';

const { t: $t } = useI18n();

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
const alarmList = ref([]);
const isLoadingAlarms = ref(false);
const alarmLoadError = ref('');
const totalAlarms = ref(0);
const totalPagesFromAPI = ref(0);
const hasNextPage = ref(false);

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
  checkinRule: 'any',
  checkinRange: 10,
  triggerType: 'immediate',
  triggerDuration: 5,
  enabled: true,
  // 步骤 3: ble = 信标白名单(原行为), geo = 经纬度围栏
  locationMode: 'ble',
  geofenceId: null,
  transition: 'both'
});

const isGeoMode = computed(
  () => alarmForm.value.locationMode === 'geo'
    && (alarmForm.value.type === 'checkin' || alarmForm.value.type === 'position'),
);

const alarmErrors = ref({
  name: '',
  type: '',
  deviceScope: '',
  beaconScope: '',
  geofence: '',
  checkinRange: '',
  triggerDuration: ''
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

// 删除确认弹窗相关状态
const showDeleteConfirm = ref(false);
const deleteTargetAlarm = ref(null);

// 错误提示弹窗相关状态
const showErrorModal = ref(false);
const errorMessage = ref('');

// 计算属性  
const totalPages = computed(() => {
  return totalPagesFromAPI.value || 1;
});

const paginatedAlarms = computed(() => {
  // 由于后端已经分页，直接返回当前加载的数据
  return alarmList.value;
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

// 数据转换方法
const eventTypeToString = (eventType) => {
  const typeMap = {
    1: 'sos',
    2: 'offline', 
    3: 'checkin',
    4: 'position'
  };
  return typeMap[eventType] || 'unknown';
};

const stringToEventType = (typeString) => {
  const typeMap = {
    'sos': 1,
    'offline': 2,
    'checkin': 3,
    'position': 4
  };
  return typeMap[typeString] || 1;
};

const convertBackendToFrontend = (backendEvent) => {
  const isImmediate = backendEvent.time_range === 0;
  
  // 处理设备范围：如果接收到 ["all"]，转换为选择所有设备
  let selectedDevices = backendEvent.device_range || [];
  if (selectedDevices.length === 1 && selectedDevices[0] === "all") {
    // 如果设备数据已加载，使用所有设备ID；否则保持 ["all"] 等待后续处理
    selectedDevices = allDeviceIds.value.length > 0 ? [...allDeviceIds.value] : ["all"];
  }
  
  return {
    id: backendEvent.id,
    name: backendEvent.event_name,
    type: eventTypeToString(backendEvent.event_type),
    selectedDevices: selectedDevices,
    selectedBeacons: backendEvent.ble_range || [],
    checkinRule: backendEvent.ble_rule === 1 ? 'any' : 'all',
    checkinRange: backendEvent.dis_range || 10,
    triggerType: isImmediate ? 'immediate' : 'duration',
    // 保留原始的 time_range 值，这样编辑时能正确判断
    triggerDuration: isImmediate ? 10 : backendEvent.time_range,
    locationMode: backendEvent.location_mode || 'ble',
    geofenceId: backendEvent.geofence_id ?? null,
    transition: backendEvent.transition || 'both',
    // 添加原始值以便编辑时参考
    time_range: backendEvent.time_range,
    enabled: backendEvent.enable_status,
    createdAt: backendEvent.create_time ? new Date(backendEvent.create_time).toISOString().split('T')[0] : ''
  };
};

const convertFrontendToBackend = (frontendEvent) => {
  // 处理设备范围：如果选择了所有设备，只推送 ["all"]
  let deviceRange = frontendEvent.selectedDevices || [];
  if (deviceRange.length > 0 && allDeviceIds.value.length > 0) {
    // 检查是否选择了所有设备
    const isAllDevicesSelected = allDeviceIds.value.every(id => deviceRange.includes(id));
    if (isAllDevicesSelected) {
      deviceRange = ["all"];
    }
  }
  
  const baseData = {
    event_name: frontendEvent.name,
    event_type: stringToEventType(frontendEvent.type),
    device_range: deviceRange,
    enable_status: frontendEvent.enabled
  };

  const geoMode = frontendEvent.locationMode === 'geo'
    && (frontendEvent.type === 'checkin' || frontendEvent.type === 'position');
  if (frontendEvent.type === 'checkin' || frontendEvent.type === 'position') {
    baseData.location_mode = geoMode ? 'geo' : 'ble';
    baseData.transition = frontendEvent.transition || 'both';
    baseData.geofence_id = geoMode ? frontendEvent.geofenceId : null;
  }

  // 根据告警类型添加相应的字段
  switch (frontendEvent.type) {
    case 'sos':
    case 'offline':
      // SOS和离线告警只需要基础字段，不需要beacon相关配置
      break;
      
    case 'checkin':
      // 签到事件需要beacon配置和签到规则; geo 模式不依赖 beacon
      baseData.ble_range = geoMode ? [] : (frontendEvent.selectedBeacons || []);
      baseData.ble_rule = frontendEvent.checkinRule === 'any' ? 1 : 2;
      baseData.dis_range = frontendEvent.checkinRange || 10;
      // 签到事件不需要time_range
      break;
      
    case 'position':
      // 位置检测需要beacon配置和触发时间; geo 模式不依赖 beacon
      baseData.ble_range = geoMode ? [] : (frontendEvent.selectedBeacons || []);
      baseData.time_range = frontendEvent.triggerType === 'immediate' ? 0 : (frontendEvent.triggerDuration || 10);
      // 位置检测不需要ble_rule和dis_range
      break;
  }

  return baseData;
};

// 加载告警列表
const loadAlarmList = async (page = null) => {
  try {
    isLoadingAlarms.value = true;
    alarmLoadError.value = '';
    
    // 使用传入的页码或当前页码
    const targetPage = page !== null ? page : currentPage.value;
    
    // 使用axios进行请求
    const params = {
      page: targetPage.toString(),
      page_size: itemsPerPage.toString()
    };
    
    const response = await apiRequest.get(API_ENDPOINTS.EVENTS, { params });
    const responseData = response.data;
    
    // 转换后端数据格式到前端格式
    alarmList.value = responseData.data.map(convertBackendToFrontend);
    
    // 更新分页信息
    const pagination = responseData.pagination;
    totalAlarms.value = pagination.total;
    totalPagesFromAPI.value = pagination.total_pages;
    hasNextPage.value = targetPage < pagination.total_pages;
    
    console.log('Alarm list loaded:', alarmList.value);
    console.log('Pagination info:', pagination);
    emit('update-status', `Loaded ${alarmList.value.length} alarms (page ${targetPage} of ${pagination.total_pages}, total: ${pagination.total})`);
    
  } catch (error) {
    console.error('Failed to load alarm list:', error);
    alarmLoadError.value = `${$t('alarmSettings.messages.loadFailed')}: ${error.message}`;
    emit('update-status', `${$t('alarmSettings.messages.loadFailed')}: ${error.message}`);
    // 发生错误时重置分页信息
    totalAlarms.value = 0;
    totalPagesFromAPI.value = 0;
    hasNextPage.value = false;
  } finally {
    isLoadingAlarms.value = false;
  }
};

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
    'sos': 'alarmSettings.types.sos',
    'offline': 'alarmSettings.types.offline',
    'checkin': 'alarmSettings.types.checkin',
    'position': 'alarmSettings.types.position'
  };
  return labelMap[type] ? $t(labelMap[type]) : type;
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
    return $t('alarmSettings.deviceScope.selectDevices');
  } else if (selectedCount === totalCount) {
    return $t('alarmSettings.deviceScope.allDevices');
  } else {
    return `${selectedCount} ${$t('alarmSettings.deviceScope.deviceSelected')}`;
  }
};

// 加载设备分组和设备数据
const loadDevicesAndGroups = async () => {
  try {
    isLoadingDevices.value = true;
    deviceLoadError.value = '';
    
    // 并行加载分组和设备数据
    const [groupsResponse, trackersResponse] = await Promise.all([
      apiRequest.get('/groups'),
      apiRequest.get('/trackers')
    ]);
    
    // 解析响应数据
    const groupsData = groupsResponse.data;
    const trackersData = trackersResponse.data;
    
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
    
    // 设备数据加载完成后，处理可能存在的 ["all"] 特殊情况
    if (alarmForm.value.selectedDevices.length === 1 && alarmForm.value.selectedDevices[0] === "all") {
      // 将 ["all"] 转换为所有设备ID
      alarmForm.value.selectedDevices = [...allDeviceIds.value];
      console.log('Converted ["all"] to all device IDs:', alarmForm.value.selectedDevices.length, 'devices');
    }
    
  } catch (error) {
    console.error('Failed to load devices and groups:', error);
    deviceLoadError.value = `${$t('alarmSettings.messages.loadFailed')}: ${error.message}`;
    emit('update-status', `${$t('alarmSettings.messages.loadFailed')}: ${error.message}`);
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
    
    const response = await apiRequest.get('/beacons');
    const beaconData = response.data;
    
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
    beaconLoadError.value = `${$t('alarmSettings.messages.loadFailed')}: ${error.message}`;
    emit('update-status', `${$t('alarmSettings.messages.loadFailed')}: ${error.message}`);
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
    return $t('alarmSettings.beaconScope.selectBeacons');
  } else if (selectedCount === 1) {
    return `1 ${$t('alarmSettings.beaconScope.beaconSelected')}`;
  } else {
    return `${selectedCount} ${$t('alarmSettings.beaconScope.beaconsSelected')}`;
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
    checkinRule: 'any',
    checkinRange: 10,
    triggerType: 'immediate',
    triggerDuration: 10, // 修改默认值为10分钟
    enabled: true,
    locationMode: 'ble',
    geofenceId: null,
    transition: 'both'
  };
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: '',
    geofence: '',
    checkinRange: '',
    triggerDuration: ''
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
  
  // 确保数据格式正确，处理可能的后端格式数据
  const timeRange = alarm.time_range !== undefined ? alarm.time_range : alarm.triggerDuration;
  const isImmediate = alarm.triggerType === 'immediate' || timeRange === 0;
  
  alarmForm.value = {
    name: alarm.name || alarm.event_name || '',
    type: alarm.type || eventTypeToString(alarm.event_type) || '',
    selectedDevices: alarm.selectedDevices || alarm.device_range || [],
    selectedBeacons: alarm.selectedBeacons || alarm.ble_range || [],
    checkinRule: alarm.checkinRule || (alarm.ble_rule === 1 ? 'any' : 'all') || 'any',
    checkinRange: alarm.checkinRange || alarm.dis_range || 10,
    triggerType: alarm.triggerType || (timeRange === 0 ? 'immediate' : 'duration') || 'immediate',
    // 编辑时：如果是duration模式，显示实际值；如果是immediate模式，保存一个默认值但不显示
    triggerDuration: isImmediate ? 10 : (alarm.triggerDuration || timeRange || 10),
    enabled: alarm.enabled !== undefined ? alarm.enabled : (alarm.enable_status !== undefined ? alarm.enable_status : true)
  };
  
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: '',
    geofence: '',
    checkinRange: '',
    triggerDuration: ''
  };
  alarmSaveError.value = '';
  showDeviceDropdown.value = false;
  showBeaconDropdown.value = false;
  showAlarmModal.value = true;
  
  // 加载设备数据
  if (deviceGroups.value.length === 0) {
    await loadDevicesAndGroups();
  }
  
  // 设备数据加载完成后，处理 ["all"] 的特殊情况
  if (alarmForm.value.selectedDevices.length === 1 && alarmForm.value.selectedDevices[0] === "all") {
    // 将 ["all"] 转换为所有设备ID
    alarmForm.value.selectedDevices = [...allDeviceIds.value];
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
    checkinRule: 'any',
    checkinRange: 10,
    triggerType: 'immediate',
    triggerDuration: 10, // 修改默认值为10分钟
    enabled: true,
    locationMode: 'ble',
    geofenceId: null,
    transition: 'both'
  };
  alarmErrors.value = {
    name: '',
    type: '',
    deviceScope: '',
    beaconScope: '',
    geofence: '',
    checkinRange: '',
    triggerDuration: ''
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
    beaconScope: '',
    geofence: '',
    checkinRange: '',
    triggerDuration: ''
  };

  let isValid = true;

  // 验证名称
  if (!alarmForm.value.name || !alarmForm.value.name.trim()) {
    alarmErrors.value.name = $t('alarmSettings.validation.nameRequired');
    isValid = false;
  } else if (alarmForm.value.name.trim().length > 50) {
    alarmErrors.value.name = $t('alarmSettings.validation.nameTooLong');
    isValid = false;
  } else {
    // 检查名称是否重复（编辑时排除自己）
    const isDuplicate = alarmList.value.some(alarm => 
      alarm.name.toLowerCase() === alarmForm.value.name.trim().toLowerCase() &&
      alarm.id !== editingAlarmId.value
    );
    if (isDuplicate) {
      alarmErrors.value.name = $t('alarmSettings.validation.nameExists');
      isValid = false;
    }
  }

  // 验证类型
  if (!alarmForm.value.type) {
    alarmErrors.value.type = $t('alarmSettings.validation.typeRequired');
    isValid = false;
  }

  // 验证设备范围
  if (!alarmForm.value.selectedDevices || alarmForm.value.selectedDevices.length === 0) {
    alarmErrors.value.deviceScope = $t('alarmSettings.validation.deviceRequired');
    isValid = false;
  }

  // 验证 beacon 范围 (仅 BLE 模式下的 checkin / position); geo 模式改验围栏
  if (alarmForm.value.type === 'checkin' || alarmForm.value.type === 'position') {
    if (isGeoMode.value) {
      if (!alarmForm.value.geofenceId) {
        alarmErrors.value.geofence = $t('alarmGeo.fenceRequired');
        isValid = false;
      }
    } else if (!alarmForm.value.selectedBeacons || alarmForm.value.selectedBeacons.length === 0) {
      alarmErrors.value.beaconScope = $t('alarmSettings.validation.beaconRequired');
      isValid = false;
    }
  }

  // 验证签到范围 (仅对 checkin 类型)
  if (alarmForm.value.type === 'checkin') {
    if (!alarmForm.value.checkinRange || alarmForm.value.checkinRange < 0.5) {
      alarmErrors.value.checkinRange = $t('alarmSettings.validation.rangeMin');
      isValid = false;
    } else if (alarmForm.value.checkinRange > 100) {
      alarmErrors.value.checkinRange = $t('alarmSettings.validation.rangeMax');
      isValid = false;
    }
  }

  // 验证触发持续时间 (仅对 position 类型且选择了 duration 模式)
  if (alarmForm.value.type === 'position' && alarmForm.value.triggerType === 'duration') {
    if (!alarmForm.value.triggerDuration || alarmForm.value.triggerDuration < 1) {
      alarmErrors.value.triggerDuration = $t('alarmSettings.validation.durationMin');
      isValid = false;
    } else if (alarmForm.value.triggerDuration > 1440) {
      alarmErrors.value.triggerDuration = $t('alarmSettings.validation.durationMax');
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

    // 转换前端数据格式到后端格式
    const backendData = convertFrontendToBackend(alarmForm.value);

    if (isEditingAlarm.value) {
      // 编辑现有报警 - PUT /api/events/{id}
      await apiRequest.put(API_ENDPOINTS.EVENT_BY_ID(editingAlarmId.value), backendData);

      emit('update-status', $t('alarmSettings.messages.alarmUpdated'));
    } else {
      // 创建新报警 - POST /api/events
      await apiRequest.post(API_ENDPOINTS.EVENTS, backendData);

      emit('update-status', $t('alarmSettings.messages.alarmCreated'));
    }

    emit('update-status', isEditingAlarm.value ? $t('alarmSettings.messages.alarmUpdated') : $t('alarmSettings.messages.alarmCreated'));

  } catch (error) {
    console.error('保存报警失败:', error);
    
    // 解析状态码
    const statusCode = error.message.includes('status:') ? 
      parseInt(error.message.match(/status: (\d+)/)?.[1]) : null;
    
    // 显示错误弹窗
    showError(error, statusCode);
  } finally {
    // 无论成功还是失败都重置保存状态
    alarmSaving.value = false;
    
    // 成功时关闭弹窗，失败时保持弹窗打开让用户可以重试
    if (!showErrorModal.value) {
      closeAlarmModal();
    }
    
    // 无论成功还是失败都重新加载列表数据
    await loadAlarmList();
  }
};

const toggleAlarmStatus = async (alarm) => {
  const originalStatus = alarm.enabled;
  
  try {
    // 调用切换状态 API - PUT /api/events/{id}
    await apiRequest.put(API_ENDPOINTS.EVENT_BY_ID(alarm.id), {
      id: alarm.id,
      enable_status: alarm.enabled
    });
    
    const message = alarm.enabled ? $t('alarmSettings.messages.alarmEnabled') : $t('alarmSettings.messages.alarmDisabled');
    emit('update-status', message);
    
  } catch (error) {
    console.error('切换报警状态失败:', error);
    // 回滚状态
    alarm.enabled = originalStatus;
    
    // 解析状态码
    const statusCode = error.message.includes('status:') ? 
      parseInt(error.message.match(/status: (\d+)/)?.[1]) : null;
    
    // 显示错误弹窗
    showError(error, statusCode);
    emit('update-status', $t('alarmSettings.messages.toggleFailed'));
  } finally {
    // 无论成功还是失败都重新加载列表数据
    await loadAlarmList();
  }
};

// 显示删除确认弹窗
const showDeleteConfirmModal = (alarmId, index) => {
  const alarm = alarmList.value.find(a => a.id === alarmId);
  if (!alarm) return;
  
  deleteTargetAlarm.value = { ...alarm, index };
  showDeleteConfirm.value = true;
};

// 取消删除
const cancelDelete = () => {
  showDeleteConfirm.value = false;
  deleteTargetAlarm.value = null;
};

// 确认删除
const confirmDelete = async () => {
  if (!deleteTargetAlarm.value) return;
  
  try {
    // 调用删除 API - DELETE /api/events/{id}
    await apiRequest.delete(API_ENDPOINTS.EVENT_BY_ID(deleteTargetAlarm.value.id));
    
    emit('update-status', $t('alarmSettings.messages.alarmDeleted'));
    
  } catch (error) {
    console.error('删除报警失败:', error);
    
    // 解析状态码
    const statusCode = error.message.includes('status:') ? 
      parseInt(error.message.match(/status: (\d+)/)?.[1]) : null;
    
    // 显示错误弹窗
    showError(error, statusCode);
    emit('update-status', $t('alarmSettings.messages.deleteFailed'));
  } finally {
    // 关闭确认弹窗
    showDeleteConfirm.value = false;
    deleteTargetAlarm.value = null;
    
    // 无论成功还是失败都重新加载列表数据
    await loadAlarmList();
    
    // 如果当前页没有数据了，且不是第一页，回到上一页
    if (alarmList.value.length === 0 && currentPage.value > 1) {
      currentPage.value--;
      await loadAlarmList();
    }
  }
};

// 兼容原有的删除方法名
const deleteAlarm = showDeleteConfirmModal;

// 错误处理方法
const showError = (error, statusCode = null) => {
  let message = $t('alarmSettings.messages.contactAdmin');
  
  // 根据状态码显示特定错误信息
  if (statusCode) {
    switch (statusCode) {
      case 403:
        message = $t('alarmSettings.messages.noPermission');
        break;
      case 404:
        message = $t('alarmSettings.messages.resourceNotFound');
        break;
      case 409:
        message = $t('alarmSettings.messages.duplicateName');
        break;
      default:
        message = $t('alarmSettings.messages.contactAdmin');
    }
  }
  
  // 如果有具体的错误信息，可以添加到默认消息后面
  if (error && error.message && !error.message.includes('HTTP error')) {
    message += `\n错误详情: ${error.message}`;
  }
  
  errorMessage.value = message;
  showErrorModal.value = true;
};

const closeErrorModal = () => {
  showErrorModal.value = false;
  errorMessage.value = '';
};

// 分页相关方法
const goToPreviousPage = async () => {
  if (currentPage.value > 1) {
    currentPage.value--;
    await loadAlarmList(currentPage.value);
  }
};

const goToNextPage = async () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    await loadAlarmList(currentPage.value);
  }
};

// 处理模态框内的点击事件
const handleModalClick = (event) => {
  // 检查设备选择下拉框
  if (showDeviceDropdown.value && deviceScopeDropdown.value) {
    const deviceDropdownElement = deviceScopeDropdown.value;
    if (deviceDropdownElement && !deviceDropdownElement.contains(event.target)) {
      showDeviceDropdown.value = false;
    }
  }
  
  // 检查beacon选择下拉框
  if (showBeaconDropdown.value && beaconScopeDropdown.value) {
    const beaconDropdownElement = beaconScopeDropdown.value;
    if (beaconDropdownElement && !beaconDropdownElement.contains(event.target)) {
      showBeaconDropdown.value = false;
    }
  }
};

// 处理点击外部关闭下拉框（保留作为备用）
const handleClickOutside = (event) => {
  // 只在模态框外部生效
  if (!showAlarmModal.value) return;
  
  // 检查设备选择下拉框
  if (showDeviceDropdown.value && deviceScopeDropdown.value) {
    const deviceDropdownElement = deviceScopeDropdown.value;
    if (deviceDropdownElement && !deviceDropdownElement.contains(event.target)) {
      showDeviceDropdown.value = false;
    }
  }
  
  // 检查beacon选择下拉框
  if (showBeaconDropdown.value && beaconScopeDropdown.value) {
    const beaconDropdownElement = beaconScopeDropdown.value;
    if (beaconDropdownElement && !beaconDropdownElement.contains(event.target)) {
      showBeaconDropdown.value = false;
    }
  }
};

// 监听触发类型变化，当从 immediate 切换到 duration 时设置合理的默认值
watch(() => alarmForm.value.triggerType, (newValue, oldValue) => {
  // 只在 position 类型告警时处理
  if (alarmForm.value.type === 'position' && oldValue === 'immediate' && newValue === 'duration') {
    // 从 immediate 切换到 duration 时，总是设置为默认值 10
    // 这样用户看到的是有意义的数值，而不是 0
    alarmForm.value.triggerDuration = 10;
  }
});

// 组件挂载时预加载数据和添加事件监听
onMounted(() => {
  loadAlarmList();
  loadDevicesAndGroups();
  document.addEventListener('click', handleClickOutside);
});

// 组件卸载时移除事件监听
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.location-mode-options {
  display: flex;
  gap: 18px;
  align-items: center;
  margin-bottom: 8px;
}

.location-mode-option {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.geofence-label {
  display: block;
  margin: 10px 0 6px;
}

/* === Alarm Settings 样式 === */
.alarm-settings-section {
  margin-bottom: 2rem;
}

.create-alarm-btn {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, var(--sc-color-success) 0%, var(--sc-color-success) 100%);
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
  background: linear-gradient(135deg, var(--sc-color-success) 0%, var(--sc-color-success) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.4);
}

.empty-alarm-list {
  text-align: center;
  padding: 3rem;
  color: var(--sc-color-text-secondary);
}

.empty-alarm-list .empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
  color: var(--sc-color-text-tertiary);
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
  background: var(--sc-color-bg-layout);
  color: var(--sc-color-text);
  font-weight: 600;
  padding: 1rem;
  text-align: center;
  border-bottom: 2px solid var(--sc-color-border);
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
  border-bottom: 1px solid var(--sc-color-border);
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
  background: var(--sc-color-bg-layout);
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
  background: var(--sc-status-danger-bg);
  color: var(--sc-status-danger-fg);
}

.alarm-type-offline {
  background: var(--sc-status-warning-bg);
  color: var(--sc-status-warning-fg);
}

.alarm-type-checkin {
  background: var(--sc-color-bg-layout);
  color: var(--sc-color-info);
}

.alarm-type-position {
  background: var(--sc-status-normal-bg);
  color: var(--sc-status-normal-fg);
}

.alarm-type-default {
  background: var(--sc-status-disabled-bg);
  color: var(--sc-status-disabled-fg);
}

.alarm-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

/* 表单中的alarm-status样式 - 靠左对齐 */
.form-alarm-status {
  justify-content: flex-start !important;
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
  background-color: var(--sc-color-border);
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
  background: linear-gradient(135deg, var(--sc-color-success) 0%, var(--sc-color-success) 100%);
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
  color: var(--sc-status-normal-fg);
}

.status-text.disabled {
  color: var(--sc-status-disabled-fg);
}

.alarm-actions {
  display: flex;
  gap: 0.25rem;
  justify-content: center;
  align-items: center;
}

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
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  justify-content: center;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.edit-btn {
  background: linear-gradient(135deg, var(--sc-color-primary) 0%, var(--sc-color-primary-active) 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

.edit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--sc-color-primary-hover) 0%, var(--sc-color-primary-active) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.delete-btn {
  background: linear-gradient(135deg, var(--sc-color-text-secondary) 0%, var(--sc-color-text) 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 4px rgba(74, 85, 104, 0.3);
}

.delete-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--sc-color-text-secondary) 0%, var(--sc-color-text) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(74, 85, 104, 0.4);
}

.alarm-table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--sc-color-bg-layout);
  border-top: 1px solid var(--sc-color-border);
}

.alarm-stats {
  color: var(--sc-color-text-secondary);
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
  border: 1px solid var(--sc-color-border);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--sc-color-text);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--sc-color-border);
  border-color: var(--sc-color-text-tertiary);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 0.9rem;
  color: var(--sc-color-text);
  font-weight: 500;
  min-width: 60px;
  text-align: center;
}

/* Modal 样式 */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background-color: rgba(0, 0, 0, 0.5) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: flex-start !important;
  z-index: 1000 !important;
  backdrop-filter: blur(2px);
  padding: 1rem 0 !important;
  box-sizing: border-box !important;
  overflow-y: auto !important;
}

.alarm-modal {
  background: white !important;
  border-radius: 12px;
  width: 95% !important;
  max-width: 700px !important;
  max-height: 95vh !important;
  min-height: 80vh !important;
  height: auto !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
  display: flex !important;
  flex-direction: column !important;
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
  border-bottom: 1px solid var(--sc-color-border);
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
  color: var(--sc-color-primary);
}

.alarm-modal .modal-body {
  padding: 1.5rem !important;
  flex: 1 !important;
  overflow-y: auto !important;
  min-height: 400px !important;
  max-height: none !important;
}

.alarm-modal .modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--sc-color-border);
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
  color: var(--sc-color-text);
  font-size: 0.9rem;
}

.required {
  color: var(--sc-color-error);
  font-weight: bold;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid var(--sc-color-border);
  border-radius: 6px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--sc-color-primary);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input.error,
.form-textarea.error {
  border-color: var(--sc-color-error);
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.error-message {
  margin-top: 0.5rem;
  color: var(--sc-color-error);
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
  border: 2px solid var(--sc-color-border);
  border-radius: 6px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 50px;
  box-sizing: border-box;
}

.dropdown-trigger:hover {
  border-color: var(--sc-color-primary);
}

.dropdown-trigger.error {
  border-color: var(--sc-color-error);
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
}

.selected-text {
  flex: 1;
  text-align: left;
  color: var(--sc-color-text);
  font-size: 0.95rem;
}

.selected-text:empty::before {
  content: 'Select devices...';
  color: var(--sc-color-text-tertiary);
}

.dropdown-trigger i {
  color: var(--sc-color-text-secondary);
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
  border: 1px solid var(--sc-color-border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  max-height: 400px;
  overflow-y: auto;
  margin-top: 2px;
}

.device-group {
  border-bottom: 1px solid var(--sc-color-bg-layout);
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
  background: var(--sc-color-bg-layout);
}

.group-header i {
  color: var(--sc-color-text-secondary);
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
  color: var(--sc-color-text);
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
  border-top: 1px solid var(--sc-color-bg-layout);
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
  background: var(--sc-color-bg-layout);
}

.device-checkbox input {
  margin-right: 0.5rem;
}

/* 加载和错误状态样式 */
.loading-state,
.error-state,
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
  color: var(--sc-color-text-secondary);
  font-size: 0.9rem;
}

.loading-state {
  flex-direction: column;
  text-align: center;
}

.loading-state i {
  color: var(--sc-color-info);
  font-size: 2rem;
  margin-bottom: 1rem;
}

.error-state {
  flex-direction: column;
  text-align: center;
}

.error-state i {
  color: var(--sc-color-error);
  font-size: 2rem;
  margin-bottom: 1rem;
}

.loading-devices i {
  color: var(--sc-color-info);
  font-size: 1.1rem;
}

.device-load-error {
  flex-direction: column;
  text-align: center;
}

.device-load-error i {
  color: var(--sc-color-error);
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.retry-btn {
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  background: var(--sc-color-info);
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
  background: var(--sc-color-info);
}

.no-devices i,
.no-beacons i {
  color: var(--sc-color-warning);
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
  border-bottom: 1px solid var(--sc-color-bg-layout);
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
  background: var(--sc-color-bg-layout);
  border-bottom: 1px solid var(--sc-color-border);
}

.map-header:hover {
  background: var(--sc-color-border);
}

.map-header i {
  color: var(--sc-color-text-secondary);
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
  color: var(--sc-color-text);
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
  color: var(--sc-color-text);
  font-size: 0.9rem;
  gap: 0.5rem;
}

.beacon-checkbox:hover {
  background: var(--sc-color-bg-layout);
}

.beacon-checkbox input {
  margin: 0;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.loading-beacons i {
  color: var(--sc-color-info);
  font-size: 1.1rem;
}

.beacon-load-error {
  flex-direction: column;
  text-align: center;
}

.beacon-load-error i {
  color: var(--sc-color-error);
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

/* Check-in Event 额外配置样式 */
.checkin-rule-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 0.5rem;
}

.checkin-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 2px solid var(--sc-color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.checkin-option:hover {
  border-color: var(--sc-color-primary);
  background: var(--sc-color-bg-layout);
}

.checkin-option input[type="radio"] {
  margin: 0;
  width: 18px;
  height: 18px;
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 2px;
}

.checkin-option input[type="radio"]:checked + .radio-mark + .checkin-content .checkin-title {
  color: var(--sc-color-primary);
  font-weight: 600;
}

.checkin-option:has(input[type="radio"]:checked) {
  border-color: var(--sc-color-primary);
  background: #f0f4ff;
}

.checkin-content {
  flex: 1;
}

.checkin-title {
  font-size: 1rem;
  font-weight: 500;
  color: var(--sc-color-text);
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.checkin-description {
  font-size: 0.85rem;
  color: var(--sc-color-text-secondary);
  line-height: 1.4;
}

.range-input-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.range-input {
  width: 120px !important;
  text-align: center;
}

.range-unit {
  font-size: 0.9rem;
  color: var(--sc-color-text);
  font-weight: 500;
}

.range-help-text {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--sc-color-text-secondary);
  line-height: 1.4;
}

/* Position Detection 额外配置样式 */
.trigger-duration-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 0.5rem;
}

.trigger-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 2px solid var(--sc-color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.trigger-option:hover {
  border-color: var(--sc-color-primary);
  background: var(--sc-color-bg-layout);
}

.trigger-option input[type="radio"] {
  margin: 0;
  width: 18px;
  height: 18px;
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 2px;
}

.trigger-option input[type="radio"]:checked + .radio-mark + .trigger-content .trigger-title {
  color: var(--sc-color-primary);
  font-weight: 600;
}

.trigger-option:has(input[type="radio"]:checked) {
  border-color: var(--sc-color-primary);
  background: #f0f4ff;
}

.radio-mark {
  display: none;
}

.trigger-content {
  flex: 1;
}

.trigger-title {
  font-size: 1rem;
  font-weight: 500;
  color: var(--sc-color-text);
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.trigger-description {
  font-size: 0.85rem;
  color: var(--sc-color-text-secondary);
  line-height: 1.4;
}

.duration-input-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.duration-input {
  width: 120px !important;
  text-align: center;
}

.duration-unit {
  font-size: 0.9rem;
  color: var(--sc-color-text);
  font-weight: 500;
}

.duration-help-text {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--sc-color-text-secondary);
  line-height: 1.4;
}

.save-btn {
  background: linear-gradient(135deg, var(--sc-color-primary) 0%, var(--sc-color-primary-active) 100%);
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
  background: linear-gradient(135deg, var(--sc-color-primary-hover) 0%, var(--sc-color-primary-active) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.save-btn:disabled {
  background: var(--sc-color-text-tertiary);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.cancel-btn {
  background: var(--sc-color-text-secondary);
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
  color: var(--sc-color-text-secondary);
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: color 0.2s ease;
}

.close-btn:hover {
  color: var(--sc-color-error);
}

/* 删除确认弹窗样式 */
.delete-confirm-modal {
  background: white !important;
  border-radius: 12px;
  width: 90% !important;
  max-width: 450px !important;
  height: auto !important;
  max-height: none !important;
  min-height: auto !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
  display: flex !important;
  flex-direction: column !important;
}

.delete-confirm-modal .modal-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  border-bottom: 1px solid var(--sc-color-border);
  display: flex;
  justify-content: center;
  align-items: center;
}

.delete-confirm-modal .modal-header h3 {
  margin: 0;
  color: var(--sc-color-error);
  font-size: 1.25rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.delete-confirm-modal .modal-header h3 i {
  color: var(--sc-color-error);
  font-size: 1.5rem;
}

.delete-confirm-modal .modal-body {
  padding: 1.5rem !important;
  text-align: center;
  flex: 1 !important;
}

.delete-message {
  font-size: 1rem;
  color: var(--sc-color-text);
  margin-bottom: 1rem;
  line-height: 1.5;
}

.delete-message strong {
  color: var(--sc-color-error);
  font-weight: 600;
}

.delete-warning {
  font-size: 0.9rem;
  color: var(--sc-color-text-secondary);
  margin: 0;
  font-style: italic;
}

.delete-confirm-modal .modal-footer {
  padding: 1rem 1.5rem 1.5rem 1.5rem;
  border-top: 1px solid var(--sc-color-border);
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.delete-confirm-btn {
  background: linear-gradient(135deg, var(--sc-color-error) 0%, var(--sc-color-error) 100%);
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
  box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
  min-width: 120px;
  justify-content: center;
}

.delete-confirm-btn:hover {
  background: linear-gradient(135deg, var(--sc-color-error) 0%, var(--sc-color-error) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(220, 53, 69, 0.4);
}

.delete-cancel-btn {
  background: var(--sc-color-text-secondary);
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
  min-width: 120px;
  justify-content: center;
}

.delete-cancel-btn:hover {
  background: #5a6268;
  transform: translateY(-1px);
}

/* 错误提示弹窗样式 */
.error-modal {
  background: white !important;
  border-radius: 12px;
  width: 90% !important;
  max-width: 450px !important;
  height: auto !important;
  max-height: none !important;
  min-height: auto !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
  display: flex !important;
  flex-direction: column !important;
}

.error-modal .modal-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  border-bottom: 1px solid var(--sc-color-border);
  display: flex;
  justify-content: center;
  align-items: center;
}

.error-modal .modal-header h3 {
  margin: 0;
  color: var(--sc-color-error);
  font-size: 1.25rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.error-modal .modal-header h3 i {
  color: var(--sc-color-error);
  font-size: 1.5rem;
}

.error-modal .modal-body {
  padding: 1.5rem !important;
  text-align: center;
  flex: 1 !important;
}

.error-message-text {
  font-size: 1rem;
  color: var(--sc-color-text);
  margin: 0;
  line-height: 1.6;
  white-space: pre-line;
}

.error-modal .modal-footer {
  padding: 1rem 1.5rem 1.5rem 1.5rem;
  border-top: 1px solid var(--sc-color-border);
  display: flex;
  justify-content: center;
}

.error-confirm-btn {
  background: linear-gradient(135deg, var(--sc-color-info) 0%, var(--sc-color-info) 100%);
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
  box-shadow: 0 2px 4px rgba(0, 123, 255, 0.3);
  min-width: 120px;
  justify-content: center;
}

.error-confirm-btn:hover {
  background: linear-gradient(135deg, var(--sc-color-info) 0%, var(--sc-color-info) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.4);
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
  
  .delete-confirm-modal {
    width: 95% !important;
    max-width: 400px !important;
  }
  
  .delete-confirm-modal .modal-footer {
    flex-direction: column;
  }
  
  .delete-confirm-btn,
  .delete-cancel-btn {
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
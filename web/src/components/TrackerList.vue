<template>
  <div class="tracker-list-card card">
    <div class="card-content">
      <div class="tracker-list-header">
        <h3 class="tracker-list-title">{{ $t('tracker.trackerList.title') }}</h3>
        <div class="tracker-filter-controls">
          <div class="group-filter-dropdown">
            <button 
              class="group-filter-button"
              @click="toggleGroupFilter"
              :disabled="groups.length === 0"
            >
              <span>{{ selectedGroup || $t('tracker.allGroups') }}</span>
              <i class="fas fa-chevron-down dropdown-icon" :class="{ 'rotated': showGroupFilter }"></i>
            </button>
            <div v-if="showGroupFilter" class="group-menu group-filter-menu">
              <div class="group-menu-item" @click="selectGroupFilter('')">
                <span>{{ $t('tracker.allGroups') }}</span>
                <i v-if="!selectedGroup" class="fas fa-check selected-icon"></i>
              </div>
              <div 
                v-for="group in groups" 
                :key="group" 
                class="group-menu-item"
                @click="selectGroupFilter(group)"
              >
                <span>{{ group }}</span>
                <i v-if="selectedGroup === group" class="fas fa-check selected-icon"></i>
              </div>
            </div>
          </div>
          <div class="group-actions-dropdown">
            <button class="btn-icon" @click="toggleGroupMenu" :title="$t('tracker.trackerList.groupManagement')">
              <i class="fas fa-edit"></i>
            </button>
            <div v-if="showGroupMenu" class="group-menu">
              <div class="group-menu-item" @click="createGroup">
                <i class="fas fa-plus-circle"></i>
                <span>{{ $t('tracker.trackerList.createGroup') }}</span>
              </div>
              <div 
                class="group-menu-item" 
                :class="{ 'disabled': selectedDevices.size === 0 }"
                @click="moveGroup"
              >
                <i class="fas fa-arrows-alt"></i>
                <span>{{ $t('tracker.trackerList.moveGroup') }}</span>
                <span v-if="selectedDevices.size > 0" class="selected-count">({{ selectedDevices.size }})</span>
              </div>
              <div class="group-menu-item" @click="groupManagement">
                <i class="fas fa-cogs"></i>
                <span>{{ $t('tracker.trackerList.groupManagement') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="tracker-filter-tabs">
        <button 
          v-for="filter in filters" 
          :key="filter.key"
          :class="['filter-tab', { active: activeFilter === filter.key }]"
          @click="handleFilterClick(filter.key)"
        >
          {{ filter.label }}
          <span class="filter-count">({{ filter.count }})</span>
        </button>
      </div>

      <!-- 选择状态栏 -->
      <div v-if="selectedDevices.size > 0" class="selection-status-bar">
        <div class="selection-info">
          <i class="fas fa-check-square"></i>
          <span>{{ $t('tracker.trackerList.selectedDevices', getPluralizationParams(selectedDevices.size)) }}</span>
        </div>
        <button class="btn-clear-selection" @click="clearSelection" :title="$t('tracker.trackerList.clearSelection')">
          <i class="fas fa-times"></i>
          {{ $t('tracker.trackerList.clearSelection') }}
        </button>
      </div>

      <div class="tracker-table-container">
        <table class="tracker-table">
          <thead>
            <tr>
              <th class="checkbox-header">
                <input 
                  type="checkbox" 
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                  class="select-checkbox"
                />
              </th>
              <th>{{ $t('tracker.trackerList.deviceInfo') }}</th>
              <th>{{ $t('tracker.trackerList.group') }}</th>
              <th>{{ $t('tracker.trackerList.status') }}</th>
              <th>{{ $t('tracker.trackerList.lastPosition') }}</th>
              <th>{{ $t('tracker.trackerList.signalBattery') }}</th>
              <th>{{ $t('common.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tracker in filteredTrackers" :key="tracker.trackerId" class="tracker-row">
              <td class="checkbox-cell">
                <input 
                  type="checkbox" 
                  :checked="selectedDevices.has(tracker.trackerId)"
                  @change="toggleDeviceSelection(tracker.trackerId)"
                  class="select-checkbox"
                />
              </td>
              <td class="device-info">
                <div class="device-name">
                  {{ tracker.name || tracker.trackerId }}
                  <span v-if="tracker.sos === 1" class="sos-indicator">SOS</span>
                </div>
                <div class="device-id">EUI: {{ tracker.trackerId }}</div>
              </td>
              <td class="group-cell">
                <span :class="['group-badge', getGroupColor(tracker.group)]">
<!--                  {{ tracker.group || $t('tracker.defaultGroup') }}-->
                  {{ tracker.group || "Default" }}
                </span>
              </td>
              <td class="status-cell">
                <div class="status-indicator">
                  <i :class="['status-icon', getStatusIcon(tracker.status)]"></i>
                  <span :class="['status-text', tracker.status?.toLowerCase()]">
                    {{ getStatusText(tracker.status) }}
                  </span>
                </div>
              </td>
              <td class="position-cell">
                <div class="position-info">
                  <!-- 所在地图和坐标/区域信息 -->
                  <div class="position-coords">
                    <!-- type=calculation 且有坐标时显示地图名和坐标 -->
                    <span v-if="tracker.type === 'calculation' && tracker.x !== null && tracker.y !== null">
                      {{ tracker.map || $t('common.unknown') }} ({{ tracker.x.toFixed(1) }}, {{ tracker.y.toFixed(1) }})
                    </span>
                    <!-- type=approximate 时显示地图名和距离（从radius获取） -->
                    <span v-else-if="tracker.type === 'approximate' && tracker.radius">
                      {{ tracker.map || $t('common.unknown') }} ({{ tracker.radius.toFixed(2) }}m)
                    </span>
                    <!-- 其他情况显示地图名 -->
                    <span v-else>
                      {{ tracker.map || $t('common.unknown') }}
                    </span>
                  </div>
                  <!-- 时间和定位类型 -->
                  <div class="position-time">
                    {{ formatLastKnownTime(tracker.last_known_measurement_time) }}
                    <span class="position-type">
                      <span v-if="tracker.type === 'calculation' && tracker.x !== null && tracker.y !== null" class="precise-label">
                        {{ $t('tracker.trackerList.precise') }}
                      </span>
                      <span v-else-if="tracker.type === 'approximate'" class="area-label">
                        {{ $t('tracker.trackerList.area') }}
                      </span>
                    </span>
                  </div>
                </div>
              </td>
              <td class="signal-battery">
                <div class="signal-info">
                  <span class="signal-strength">{{ $t('tracker.trackerList.signal') }}: {{ getSignalStrength(tracker) }}</span>
                  <div class="battery-info">
                    <span class="battery-text">{{ $t('tracker.trackerList.battery') }}: {{ getBatteryLevel(tracker) }}</span>
                  </div>
                </div>
              </td>
              <td class="actions-cell">
                <div class="tracker-actions">
                  <button 
                    :class="['btn-action', 'btn-star', { starred: tracker.starred }]"
                    @click="toggleStar(tracker)"
                    :title="tracker.starred ? $t('tracker.trackerList.unfavorite') : $t('tracker.trackerList.favorite')"
                  >
                    <i :class="[tracker.starred ? 'fas fa-star' : 'far fa-star']"></i>
                  </button>
                  <button 
                    class="btn-action btn-edit"
                    @click="editTracker(tracker)"
                    :title="$t('tracker.trackerList.editDevice')"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button 
                    class="btn-action btn-alert"
                    @click="showTrackerAlert(tracker)"
                    :title="$t('tracker.trackerList.alertSettings')"
                  >
                    <i class="fas fa-exclamation-triangle"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filteredTrackers.length === 0" class="no-trackers">
          <i class="fas fa-map-marker-alt fa-2x"></i>
          <p>{{ $t('tracker.trackerList.noTrackers') }}</p>
        </div>
      </div>

      <div class="tracker-pagination">
        <div class="pagination-info">
          {{ $t('tracker.trackerList.totalDevices', getPluralizationParams(totalTrackers)) }}
        </div>
        <div class="pagination-controls">
          <button 
            class="btn-page"
            @click="handlePageChange(currentPage - 1)"
            :disabled="currentPage <= 1 || totalPages <= 1"
          >
            <i class="fas fa-chevron-left"></i>
          </button>
          <span class="page-info">{{ currentPage }}</span>
          <button 
            class="btn-page"
            @click="handlePageChange(currentPage + 1)"
            :disabled="currentPage >= totalPages || totalPages <= 1"
          >
            <i class="fas fa-chevron-right"></i>
          </button>
        </div>
        <div class="items-per-page">
          <select 
            v-model="itemsPerPage" 
            @change="handleItemsPerPageChange"
            class="items-per-page-select"
          >
            <option v-for="option in itemsPerPageOptions" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
          <span class="per-page-label">{{ $t('common.perPage') }}</span>
        </div>
      </div>
    </div>

    <!-- 创建分组模态框 -->
    <div v-if="showCreateGroupModal" class="modal-overlay" @click="closeCreateGroupModal">
      <div class="create-group-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">{{ $t('tracker.trackerList.createNewGroup') }}</h3>
          <button class="btn-close" @click="closeCreateGroupModal">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">
              <span class="required-star">*</span> {{ $t('tracker.trackerList.groupName') }}
            </label>
            <div class="input-wrapper">
              <input 
                v-model="newGroupName"
                type="text" 
                class="form-input"
                :class="{ 'error': createGroupError || !isGroupNameValid.valid }"
                :placeholder="$t('tracker.trackerList.enterGroupName', { max: maxGroupNameLength })"
                :maxlength="maxGroupNameLength"
                :disabled="isCreatingGroup"
                @keyup.enter="handleCreateGroup"
                @input="createGroupError = ''"
              />
              <div class="char-counter">
                {{ newGroupName.length }} / {{ maxGroupNameLength }}
              </div>
            </div>
            
            <!-- 实时验证错误提示 -->
            <div v-if="newGroupName.trim() && !isGroupNameValid.valid" class="error-message">
              {{ isGroupNameValid.error }}
            </div>
            
            <!-- API错误提示 -->
            <div v-if="createGroupError" class="error-message">
              {{ createGroupError }}
            </div>
          </div>
          
          <div class="note-section">
            <div class="note-label">{{ $t('tracker.trackerList.note') }}</div>
            <div class="note-content">
              <i class="fas fa-info-circle note-icon"></i>
              {{ $t('tracker.trackerList.defaultGroupNote') }}
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button 
            class="btn btn-cancel" 
            @click="closeCreateGroupModal"
            :disabled="isCreatingGroup"
          >
            {{ $t('common.cancel') }}
          </button>
          <button 
            class="btn btn-create"
            :disabled="!isGroupNameValid.valid || isCreatingGroup"
            @click="handleCreateGroup"
          >
            <span v-if="isCreatingGroup">
              <i class="fas fa-spinner fa-spin"></i> {{ $t('tracker.trackerList.creating') }}
            </span>
            <span v-else>{{ $t('tracker.trackerList.create') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 分组管理模态框 -->
    <div v-if="showGroupManagementModal" class="modal-overlay" @click="closeGroupManagementModal">
      <div class="group-management-modal" @click.stop>
        <div class="modal-header">
          <div class="modal-title-section">
            <h3 class="modal-title">
              <i class="fas fa-cogs"></i> {{ $t('tracker.trackerList.groupManagementTitle') }}
            </h3>
            <p class="modal-subtitle">
              {{ $t('tracker.trackerList.groupManagementDescription') }}
            </p>
          </div>
          <button class="btn-close" @click="closeGroupManagementModal">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="management-header">
            <h4>{{ $t('tracker.trackerList.existingGroups') }}</h4>
            <button 
              class="btn btn-create-new" 
              @click="openCreateGroupFromManagement"
              :disabled="isManagementLoading"
            >
              <i class="fas fa-plus"></i> {{ $t('tracker.trackerList.createNewGroupFromManagement') }}
            </button>
          </div>
          
          <div class="groups-table-container">
            <table class="groups-table">
              <thead>
                <tr>
                  <th>{{ $t('tracker.trackerList.groupName') }}</th>
                  <th>{{ $t('tracker.trackerList.deviceCount', getPluralizationParams(0)) }}</th>
                  <th>{{ $t('common.actions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="group in availableGroups" :key="group.id" class="group-row">
                  <td class="group-name-cell">
                    <div v-if="editingGroupId === group.id" class="edit-group-input">
                      <div class="edit-input-wrapper">
                        <input 
                          v-model="editingGroupName"
                          type="text"
                          class="form-input-inline"
                          :class="{ 'error': managementError }"
                          :maxlength="maxGroupNameLength"
                          :disabled="isManagementLoading"
                          @keyup.enter="saveGroupName(group)"
                          @keyup.escape="cancelEdit"
                          @input="managementError = ''"
                          ref="editInput"
                        />
                        <div class="edit-char-counter">
                          {{ editingGroupName.length }} / {{ maxGroupNameLength }}
                        </div>
                      </div>
                    </div>
                    <div v-else class="group-name-display">
                      {{ group.group_name }}
                      <span v-if="group.id === 0" class="system-badge">{{ $t('tracker.trackerList.systemGroup') }}</span>
                    </div>
                  </td>
                  <td class="device-count-cell">
                    <span class="device-count">
                      {{ $t('tracker.trackerList.deviceCount', getPluralizationParams(getGroupDeviceCount(group.group_name))) }}
                    </span>
                  </td>
                  <td class="actions-cell">
                    <div class="group-actions">
                      <template v-if="editingGroupId === group.id">
                        <button 
                          class="btn-action btn-save"
                          @click="saveGroupName(group)"
                          :disabled="isManagementLoading || !editingGroupName.trim()"
                          :title="isManagementLoading ? $t('tracker.trackerList.saving') : $t('tracker.trackerList.saveChanges')"
                        >
                          <i v-if="isManagementLoading" class="fas fa-spinner fa-spin"></i>
                          <i v-else class="fas fa-check"></i>
                        </button>
                        <button 
                          class="btn-action btn-cancel-edit"
                          @click="cancelEdit"
                          :disabled="isManagementLoading"
                          :title="$t('tracker.trackerList.cancel')"
                        >
                          <i class="fas fa-times"></i>
                        </button>
                      </template>
                      <template v-else>
                        <button 
                          v-if="group.id !== 0"
                          class="btn-action btn-edit"
                          @click="startEdit(group)"
                          :disabled="isManagementLoading"
                          :title="$t('tracker.trackerList.editName')"
                        >
                          <i class="fas fa-edit"></i>
                        </button>
                        <button 
                          v-if="group.id !== 0"
                          class="btn-action btn-delete"
                          @click="deleteGroup(group)"
                          :disabled="getGroupDeviceCount(group.group_name) > 0 || isManagementLoading"
                          :title="isManagementLoading ? $t('tracker.trackerList.deleting') : getGroupDeviceCount(group.group_name) > 0 ? $t('tracker.trackerList.cannotDeleteGroupWithDevices') : $t('tracker.trackerList.deleteGroup')"
                        >
                          <i v-if="isManagementLoading" class="fas fa-spinner fa-spin"></i>
                          <i v-else class="fas fa-trash"></i>
                        </button>
                        <span v-if="group.id === 0" class="system-note">{{ $t('tracker.trackerList.systemGroup') }}</span>
                      </template>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- 错误提示 -->
          <div v-if="managementError" class="error-message">
            {{ managementError }}
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-close-modal" @click="closeGroupManagementModal">
            {{ $t('tracker.trackerList.close') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 移动分组模态框 -->
    <div v-if="showMoveGroupModal" class="modal-overlay" @click="closeMoveGroupModal">
      <div class="move-group-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">{{ $t('tracker.trackerList.moveDevices', getPluralizationParams(selectedDevices.size)) }}</h3>
          <button class="btn-close" @click="closeMoveGroupModal">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="selected-devices-section">
            <h4>{{ $t('tracker.trackerList.selectedDevicesTitle') }}</h4>
            <div class="selected-devices-list">
              <div 
                v-for="deviceId in Array.from(selectedDevices)" 
                :key="deviceId"
                class="selected-device-item"
              >
                <div class="device-name">{{ getDeviceName(deviceId) }}</div>
                <div class="device-group">{{ getDeviceGroup(deviceId) }}</div>
              </div>
            </div>
          </div>
          
          <div class="target-group-section">
            <label class="form-label">
              <span class="required-star">*</span> {{ $t('tracker.trackerList.targetGroup') }}
            </label>
            <select v-model="targetGroup" class="target-group-select">
              <option value="">{{ $t('tracker.trackerList.selectTargetGroup') }}</option>
              <option v-for="group in groups" :key="group" :value="group">{{ group }}</option>
            </select>
          </div>
          
          <!-- 错误提示 -->
          <div v-if="moveGroupError" class="error-message">
            {{ moveGroupError }}
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-cancel" @click="closeMoveGroupModal" :disabled="isMovingDevices">
            {{ $t('common.cancel') }}
          </button>
          <button 
            class="btn btn-move"
            :disabled="!targetGroup || isMovingDevices"
            @click="handleMoveDevices"
          >
            <span v-if="isMovingDevices">
              <i class="fas fa-spinner fa-spin"></i> {{ $t('tracker.trackerList.moving') }}
            </span>
            <span v-else>{{ $t('tracker.trackerList.move') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑设备模态框 -->
    <EditTrackerModal
      :show="showEditTrackerModal"
      :tracker="currentEditingTracker"
      :available-groups="availableGroups"
      :external-error="editTrackerError"
      @close="closeEditTrackerModal"
      @save="handleSaveTracker"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import EditTrackerModal from './EditTrackerModal.vue'
import httpClient from '../utils/httpClient.js'
import { API_ENDPOINTS } from '../config/api.js'

const props = defineProps({
  trackers: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['edit-tracker', 'add-tracker', 'toggle-star', 'show-alert', 'refresh-data'])

// i18n - 只用于JavaScript函数中
const { t } = useI18n()

// 响应式数据
const activeFilter = ref('all')
const selectedGroup = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(20)
const itemsPerPageOptions = [5, 10, 20]
const showGroupMenu = ref(false)
const showGroupFilter = ref(false)
const availableGroups = ref([{ id: 0, group_name: 'Default' }]) // 默认包含Default分组

// 创建分组模态框相关
const showCreateGroupModal = ref(false)
const newGroupName = ref('')
const maxGroupNameLength = 24
const createGroupError = ref('')
const isCreatingGroup = ref(false)

// 分组管理模态框相关
const showGroupManagementModal = ref(false)
const editingGroupId = ref(null)
const editingGroupName = ref('')
const managementError = ref('')
const isManagementLoading = ref(false)
const groupDeviceCounts = ref({})

// 移动分组相关
const showMoveGroupModal = ref(false)
const selectedDevices = ref(new Set())
const targetGroup = ref('')
const moveGroupError = ref('')
const isMovingDevices = ref(false)

// 编辑设备相关
const showEditTrackerModal = ref(false)
const currentEditingTracker = ref(null)
const editTrackerError = ref('')

// 计算属性
const trackerList = computed(() => {
  return Object.values(props.trackers).map(tracker => ({
    ...tracker,
    name: tracker.device_name || tracker.trackerId, // 优先使用device_name，如果没有则用trackerId
    group: getGroupNameByGroupId(tracker.group_id), // 根据group_id获取分组名
    status: getTrackerStatus(tracker),
    starred: tracker.starred || false
  }))
})

const groups = computed(() => {
  // 返回从后端获取的分组名称列表
  return availableGroups.value.map(group => group.group_name).sort()
})

const filters = computed(() => {
  const online = trackerList.value.filter(t => t.status === 'online').length
  const offline = trackerList.value.filter(t => t.status === 'offline').length
  const starred = trackerList.value.filter(t => t.starred).length
  
  return [
    { key: 'all', label: t('tracker.trackerList.all'), count: trackerList.value.length },
    { key: 'online', label: t('tracker.trackerList.online'), count: online },
    { key: 'offline', label: t('tracker.trackerList.offline'), count: offline },
    { key: 'starred', label: t('tracker.trackerList.starred'), count: starred }
  ]
})

// 筛选后但未分页的数据
const filteredTrackersBeforePaging = computed(() => {
  let filtered = trackerList.value

  // 按状态筛选
  if (activeFilter.value === 'online') {
    filtered = filtered.filter(t => t.status === 'online')
  } else if (activeFilter.value === 'offline') {
    filtered = filtered.filter(t => t.status === 'offline')
  } else if (activeFilter.value === 'starred') {
    filtered = filtered.filter(t => t.starred)
  }

  // 按分组筛选
  if (selectedGroup.value) {
    filtered = filtered.filter(t => t.group === selectedGroup.value)
  }

  return filtered
})

// 分页后的数据
const filteredTrackers = computed(() => {
  const filtered = filteredTrackersBeforePaging.value
  
  // 分页
  const start = (currentPage.value - 1) * itemsPerPage.value
  return filtered.slice(start, start + itemsPerPage.value)
})

// 显示过滤后的总数
const totalTrackers = computed(() => filteredTrackersBeforePaging.value.length)
const totalPages = computed(() => Math.ceil(filteredTrackersBeforePaging.value.length / itemsPerPage.value))

// 设备选择相关计算属性
const isAllSelected = computed(() => {
  return filteredTrackers.value.length > 0 && 
         filteredTrackers.value.every(tracker => selectedDevices.value.has(tracker.trackerId))
})

// 分组名称验证
const isGroupNameValid = computed(() => {
  const trimmedName = newGroupName.value.trim()
  
  // 检查是否为空
  if (!trimmedName) {
    return { valid: false, error: '' }
  }
  
  // 检查长度
  if (trimmedName.length > maxGroupNameLength) {
    return { valid: false, error: t('tracker.trackerList.groupNameTooLong', { max: maxGroupNameLength }) }
  }
  
  // 检查是否为Default（不区分大小写）
  if (trimmedName.toLowerCase() === 'default') {
    return { valid: false, error: t('tracker.trackerList.groupNameReserved') }
  }
  
  // 检查是否与现有分组重复（不区分大小写）
  const existingNames = availableGroups.value.map(g => g.group_name.toLowerCase())
  if (existingNames.includes(trimmedName.toLowerCase())) {
    return { valid: false, error: t('tracker.trackerList.groupNameExists') }
  }
  
  return { valid: true, error: '' }
})

// 辅助方法 - 处理复数形式的国际化文本
const getPluralizationParams = (count) => {
  // 英文需要复数形式，中文不需要
  const currentLocale = t('common.unknown') === 'Unknown' ? 'en' : 'zh'
  return {
    count,
    plural: currentLocale === 'en' && count !== 1 ? 's' : ''
  }
}

// 方法 - 完全依赖后端online字段
const getTrackerStatus = (tracker) => {
  // 完全依赖后端的online字段：'online'=在线，'offline'/'unknown'=离线
  if (tracker.online === 'online') {
    return 'online'
  } else if (tracker.online === 'offline' || tracker.online === 'unknown') {
    return 'offline'
  }
  
  // 如果没有online字段，默认为离线
  return 'offline'
}

const getStatusIcon = (status) => {
  return status === 'online' ? 'fas fa-circle status-online' : 'fas fa-circle status-offline'
}

const getStatusText = (status) => {
  return status === 'online' ? t('tracker.trackerList.online') : t('tracker.trackerList.offline')
}

const getGroupColor = (group) => {
  const colors = ['blue', 'green', 'orange', 'purple', 'red']
  const index = Math.abs(group?.charCodeAt(0) || 0) % colors.length
  return colors[index]
}

const getSignalStrength = (tracker) => {
  if (!tracker.last_detected_beacons || tracker.last_detected_beacons.length === 0) {
    return t('common.unknown')
  }
  
  // 找到信号最强的beacon（RSSI值最大，因为是负数，所以是最接近0的）
  const strongestBeacon = tracker.last_detected_beacons.reduce((strongest, beacon) => {
    const currentRssi = beacon.rssi || -100
    const strongestRssi = strongest.rssi || -100
    return currentRssi > strongestRssi ? beacon : strongest
  })
  
  if (!strongestBeacon.rssi) {
    return t('common.unknown')
  }
  
  return `${strongestBeacon.rssi}dBm`
}

const getBatteryLevel = (tracker) => {
  // 从tracker.battery字段获取电池电量
  const battery = tracker.battery
  
  // 处理null和undefined - 严格检查
  if (battery === null || battery === undefined) {
    return t('common.unknown')
  }
  
  // 处理特殊值：-1、unknown字符串、NaN
  if (battery === -1 || battery === 'unknown' || battery === 'Unknown' || battery === '') {
    return t('common.unknown')
  }
  
  // 处理数字类型
  if (typeof battery === 'number') {
    // 检查是否为NaN
    if (isNaN(battery)) {
      return t('common.unknown')
    }
    // 确保在0-100范围内
    if (battery >= 0 && battery <= 100) {
      return `${Math.round(battery)}%`
    } else {
      return t('common.unknown')
    }
  }
  
  // 处理字符串数字
  if (typeof battery === 'string') {
    // 检查空字符串或仅空白字符
    if (battery.trim() === '') {
      return t('common.unknown')
    }
    
    // 检查是否为特殊字符串值
    const trimmedBattery = battery.trim().toLowerCase()
    if (trimmedBattery === 'null' || trimmedBattery === 'undefined' || trimmedBattery === 'nan') {
      return t('common.unknown')
    }
    
    const numBattery = parseFloat(battery)
    if (!isNaN(numBattery) && numBattery >= 0 && numBattery <= 100) {
      return `${Math.round(numBattery)}%`
    } else {
      return t('common.unknown')
    }
  }
  
  // 其他任何情况都显示Unknown
  return t('common.unknown')
}

const getDistanceString = (tracker) => {
  // 计算距离，这里简化为使用坐标的模长
  if (tracker.x !== null && tracker.y !== null) {
    const distance = Math.sqrt(tracker.x * tracker.x + tracker.y * tracker.y)
    return `${distance.toFixed(1)}F`
  }
  return tracker.map || t('common.unknown')
}

const formatTime = (timestamp) => {
  if (!timestamp) return t('tracker.trackerList.never')
  
  const date = new Date(timestamp)
  
  // 显示具体时间 HH:mm:ss 格式
  return date.toLocaleTimeString('en-GB', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatLastKnownTime = (timestamp) => {
  if (!timestamp) return t('tracker.trackerList.never')
  
  // last_known_measurement_time 是毫秒时间戳
  const date = new Date(timestamp)
  
  // 显示具体时间 HH:mm:ss 格式
  return date.toLocaleTimeString('en-GB', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 事件处理
const editTracker = async (tracker) => {
  console.log('[TrackerList] Edit tracker clicked:', tracker)
  
  // 清除之前的错误状态
  editTrackerError.value = ''
  
  // 刷新分组列表以获取最新数据
  await fetchGroups()
  
  currentEditingTracker.value = tracker
  showEditTrackerModal.value = true
}

const addTracker = () => {
  emit('add-tracker')
}

const toggleStar = async (tracker) => {
  console.log('[TrackerList] Toggle star clicked:', tracker.trackerId, 'current starred:', tracker.starred)
  
  const newStarredState = !tracker.starred
  
  try {
    // 调用后端API更新收藏状态
    const { updateDevice } = await import('@/services/configApiService.js')
    
    const updateData = {
      is_favorite: newStarredState
    }
    
    const response = await updateDevice(tracker.trackerId, updateData)
    
    if (response.success) {
      console.log('[TrackerList] Star status updated successfully')
      
      // 更新本地状态
      tracker.starred = newStarredState
      
      // 发射事件通知父组件
      emit('toggle-star', tracker)
    } else {
      throw new Error(response.message || t('tracker.trackerList.failedToUpdateStarStatus'))
    }
    
  } catch (error) {
    console.error('[TrackerList] Error updating star status:', error)
    // 可以选择显示错误提示，这里暂时只在控制台输出
    alert(`${t('tracker.trackerList.failedToUpdateStarStatus')}: ${error.message}`)
  }
}

const showTrackerAlert = (tracker) => {
  emit('show-alert', tracker)
}

// API调用函数
const fetchGroups = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.GROUPS)
    const groups = response.data
    
    // 自动添加Default分组到列表开头
    const groupsWithDefault = [
      { id: 0, group_name: 'Default' },
      ...groups
    ]
    
    availableGroups.value = groupsWithDefault
    console.log('[TrackerList] Groups loaded:', groupsWithDefault)
  } catch (error) {
    console.error('[TrackerList] Error fetching groups:', error)
    // 保持默认的Default分组
    availableGroups.value = [{ id: 0, group_name: 'Default' }]
  }
}

// 筛选按钮事件处理
const handleFilterClick = async (filterKey) => {
  console.log('[TrackerList] Filter clicked:', filterKey)
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  // 设置筛选状态
  activeFilter.value = filterKey
}

// 分组筛选事件处理
const toggleGroupFilter = async () => {
  console.log('[TrackerList] Group filter dropdown clicked')
  
  // 刷新分组列表以获取最新数据
  await fetchGroups()
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  showGroupFilter.value = !showGroupFilter.value
  // 关闭其他菜单
  showGroupMenu.value = false
}

const selectGroupFilter = async (group) => {
  console.log('[TrackerList] Group filter selected:', group)
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  selectedGroup.value = group
  showGroupFilter.value = false
}

// 分组菜单事件处理
const toggleGroupMenu = () => {
  showGroupMenu.value = !showGroupMenu.value
  // 关闭其他菜单
  showGroupFilter.value = false
}

const createGroup = async () => {
  console.log('Create Group clicked')
  
  // 刷新分组列表获取最新数据
  await fetchGroups()
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  showGroupMenu.value = false
  showCreateGroupModal.value = true
  newGroupName.value = '' // 重置输入框
}

const moveGroup = async () => {
  console.log('Move Group clicked')
  
  // 刷新分组列表获取最新数据
  await fetchGroups()
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  showGroupMenu.value = false
  
  if (selectedDevices.value.size === 0) {
    return // 没有选择设备时不执行
  }
  
  showMoveGroupModal.value = true
  targetGroup.value = ''
  moveGroupError.value = ''
}

const groupManagement = async () => {
  console.log('Group Management clicked')
  
  // 刷新分组列表获取最新数据
  await fetchGroups()
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  showGroupMenu.value = false
  showGroupManagementModal.value = true
  managementError.value = ''
  calculateGroupDeviceCounts()
}

// 暴露刷新分组列表的方法
const refreshGroups = () => {
  fetchGroups()
}

// 创建分组模态框处理函数
const closeCreateGroupModal = () => {
  showCreateGroupModal.value = false
  newGroupName.value = ''
  createGroupError.value = ''
  isCreatingGroup.value = false
}

const handleCreateGroup = async () => {
  // 清除之前的错误
  createGroupError.value = ''
  
  // 前端验证
  const validation = isGroupNameValid.value
  if (!validation.valid) {
    createGroupError.value = validation.error
    return
  }
  
  const trimmedName = newGroupName.value.trim()
  isCreatingGroup.value = true
  
  try {
    const response = await httpClient.post(API_ENDPOINTS.GROUPS, {
      group_name: trimmedName
    })
    
    const result = response.data
    
    if (result.success) {
      console.log('[TrackerList] Group created successfully:', result.data)
      // 关闭模态框
      closeCreateGroupModal()
      // 刷新分组列表
      await fetchGroups()
      // 如果从管理界面创建的，重新打开管理界面
      if (showGroupManagementModal.value === false) {
        showGroupManagementModal.value = true
        calculateGroupDeviceCounts()
      }
    } else {
      createGroupError.value = result.message || t('tracker.trackerList.failedToCreateGroup')
    }
    
  } catch (error) {
    console.error('[TrackerList] Error creating group:', error)
    if (error.response?.status === 409) {
      // 分组名称重复
      createGroupError.value = t('tracker.trackerList.groupNameExists')
    } else {
      createGroupError.value = t('tracker.trackerList.networkError')
    }
  } finally {
    isCreatingGroup.value = false
  }
}

// 分组管理相关函数
const closeGroupManagementModal = () => {
  showGroupManagementModal.value = false
  editingGroupId.value = null
  editingGroupName.value = ''
  managementError.value = ''
}

const calculateGroupDeviceCounts = () => {
  const counts = {}
  Object.values(props.trackers).forEach(tracker => {
    // 使用getGroupNameByGroupId来获取正确的分组名
    const groupName = getGroupNameByGroupId(tracker.group_id)
    counts[groupName] = (counts[groupName] || 0) + 1
  })
  groupDeviceCounts.value = counts
  
  console.log('[TrackerList] Group device counts calculated:', counts)
}

const getGroupDeviceCount = (groupName) => {
  return groupDeviceCounts.value[groupName] || 0
}

const openCreateGroupFromManagement = () => {
  showGroupManagementModal.value = false
  showCreateGroupModal.value = true
  newGroupName.value = ''
  createGroupError.value = ''
}

const startEdit = (group) => {
  // 防止编辑Default分组
  if (group.id === 0) {
    managementError.value = t('tracker.trackerList.cannotEditDefault')
    return
  }
  
  editingGroupId.value = group.id
  editingGroupName.value = group.group_name
  managementError.value = ''
  
  // 下一个tick后聚焦输入框
  nextTick(() => {
    const editInput = document.querySelector('.form-input-inline')
    if (editInput) {
      editInput.focus()
      editInput.select()
    }
  })
}

const cancelEdit = () => {
  editingGroupId.value = null
  editingGroupName.value = ''
  managementError.value = ''
}

const saveGroupName = async (group) => {
  // 防止编辑Default分组（双重保险）
  if (group.id === 0) {
    managementError.value = t('tracker.trackerList.cannotEditDefault')
    return
  }
  
  const trimmedName = editingGroupName.value.trim()
  
  // 基本验证
  if (!trimmedName) {
    managementError.value = t('tracker.trackerList.groupNameRequired')
    return
  }
  
  // 长度验证
  if (trimmedName.length > maxGroupNameLength) {
    managementError.value = t('tracker.trackerList.groupNameTooLong', { max: maxGroupNameLength })
    return
  }
  
  // 禁用Default验证
  if (trimmedName.toLowerCase() === 'default') {
    managementError.value = t('tracker.trackerList.groupNameReserved')
    return
  }
  
  // 检查是否与现有分组重复（排除当前编辑的分组）
  const existingNames = availableGroups.value
    .filter(g => g.id !== group.id)
    .map(g => g.group_name.toLowerCase())
  if (existingNames.includes(trimmedName.toLowerCase())) {
    managementError.value = t('tracker.trackerList.groupNameExists')
    return
  }
  
  // 如果名称没有变化，直接取消编辑
  if (trimmedName === group.group_name) {
    cancelEdit()
    return
  }
  
  try {
    isManagementLoading.value = true
    managementError.value = ''
    
    const response = await httpClient.put(API_ENDPOINTS.GROUP_BY_ID(group.id), {
      group_name: trimmedName
    })
    
    const result = response.data
    
    if (result.success) {
      console.log('[TrackerList] Group updated successfully:', result.data)
      // 取消编辑状态
      cancelEdit()
      // 刷新分组列表
      await fetchGroups()
      // 重新计算设备统计
      calculateGroupDeviceCounts()
    } else {
      managementError.value = result.message || t('tracker.trackerList.failedToUpdateGroupName')
    }
    
  } catch (error) {
    console.error('[TrackerList] Error updating group:', error)
    if (error.response?.status === 409) {
      // 分组名称重复
      managementError.value = t('tracker.trackerList.groupNameExists')
    } else {
      managementError.value = t('tracker.trackerList.networkError')
    }
  } finally {
    isManagementLoading.value = false
  }
}

const deleteGroup = async (group) => {
  // 防止删除Default分组
  if (group.id === 0) {
    managementError.value = t('tracker.trackerList.cannotDeleteDefault')
    return
  }
  
  // 检查分组是否有设备
  if (getGroupDeviceCount(group.group_name) > 0) {
    managementError.value = t('tracker.trackerList.cannotDeleteGroupWithDevices')
    return
  }
  
  // 确认删除
  if (!confirm(t('tracker.trackerList.confirmDeleteGroup', { name: group.group_name }))) {
    return
  }
  
  try {
    isManagementLoading.value = true
    managementError.value = ''
    
    const response = await httpClient.delete(API_ENDPOINTS.GROUP_BY_ID(group.id))
    
    const result = response.data
    
    if (result.success) {
      console.log('[TrackerList] Group deleted successfully:', group.group_name)
      // 刷新分组列表
      await fetchGroups()
      // 重新计算设备统计
      calculateGroupDeviceCounts()
      // 显示成功信息（可选）
      console.log(`Group "${group.group_name}" has been deleted successfully`)
    } else {
      managementError.value = result.message || t('tracker.trackerList.failedToDeleteGroup')
    }
    
  } catch (error) {
    console.error('[TrackerList] Error deleting group:', error)
    if (error.response?.status === 400) {
      // 分组仍有设备或其他业务错误
      const errorResult = error.response.data
      managementError.value = errorResult?.message || t('tracker.trackerList.cannotDeleteGroup')
    } else {
      managementError.value = t('tracker.trackerList.networkError')
    }
  } finally {
    isManagementLoading.value = false
  }
}

// 设备选择相关方法
const toggleDeviceSelection = (deviceId) => {
  if (selectedDevices.value.has(deviceId)) {
    selectedDevices.value.delete(deviceId)
  } else {
    selectedDevices.value.add(deviceId)
  }
  // 强制更新响应式
  selectedDevices.value = new Set(selectedDevices.value)
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    // 取消全选
    selectedDevices.value.clear()
  } else {
    // 全选当前页面的设备
    filteredTrackers.value.forEach(tracker => {
      selectedDevices.value.add(tracker.trackerId)
    })
  }
  // 强制更新响应式
  selectedDevices.value = new Set(selectedDevices.value)
}

const clearSelection = () => {
  selectedDevices.value.clear()
  // 强制更新响应式
  selectedDevices.value = new Set(selectedDevices.value)
}

// 移动分组相关方法
const closeMoveGroupModal = () => {
  showMoveGroupModal.value = false
  targetGroup.value = ''
  moveGroupError.value = ''
  isMovingDevices.value = false
}

const getDeviceName = (deviceId) => {
  const tracker = Object.values(props.trackers).find(t => t.trackerId === deviceId)
  return tracker?.name || deviceId
}

const getDeviceGroup = (deviceId) => {
  const tracker = Object.values(props.trackers).find(t => t.trackerId === deviceId)
  return tracker?.group || t('tracker.defaultGroup')
}

const getGroupIdByName = (groupName) => {
  if (groupName === 'Default') {
    return 0
  }
  const group = availableGroups.value.find(g => g.group_name === groupName)
  return group ? group.id : null
}

const getGroupNameByGroupId = (groupId) => {
  if (groupId === 0 || groupId === null || groupId === undefined) {
    return t('tracker.defaultGroup')
  }
  const group = availableGroups.value.find(g => g.id === groupId)
  return group ? group.group_name : t('tracker.defaultGroup')
}

const handleMoveDevices = async () => {
  if (!targetGroup.value || selectedDevices.value.size === 0) {
    return
  }
  
  try {
    isMovingDevices.value = true
    moveGroupError.value = ''
    
    // 获取目标分组的ID
    const groupId = getGroupIdByName(targetGroup.value)
    if (groupId === null && targetGroup.value !== 'Default') {
      moveGroupError.value = t('tracker.trackerList.invalidTargetGroup')
      return
    }
    
    // 准备请求数据
    const requestData = {
      dev_eui_list: Array.from(selectedDevices.value),
      group_id: groupId
    }
    
    console.log('[TrackerList] Moving devices to group:', requestData)
    
    const response = await httpClient.post(API_ENDPOINTS.DEVICES_BATCH_UPDATE_GROUP, requestData)
    
    const result = response.data
    
    if (result.success) {
      console.log('[TrackerList] Devices moved successfully:', result)
      
      // 关闭模态框
      closeMoveGroupModal()
      // 清空选择
      selectedDevices.value.clear()
      // 重新计算设备统计
      calculateGroupDeviceCounts()
      
      // 刷新页面数据
      emit('refresh-data')
      
      // 显示成功信息（可选）
      const deviceCount = requestData.dev_eui_list.length
      console.log(`Successfully moved ${deviceCount} device${deviceCount !== 1 ? 's' : ''} to "${targetGroup.value}" group`)
      
    } else {
      moveGroupError.value = result.message || t('tracker.trackerList.failedToMoveDevices')
    }
    
  } catch (error) {
    console.error('[TrackerList] Error moving devices:', error)
    moveGroupError.value = 'Network error. Please try again.'
  } finally {
    isMovingDevices.value = false
  }
}

// 编辑设备相关方法
const closeEditTrackerModal = () => {
  showEditTrackerModal.value = false
  currentEditingTracker.value = null
  editTrackerError.value = ''
}

const handleSaveTracker = async (trackerData) => {
  console.log('[TrackerList] Saving tracker data:', trackerData)
  
  try {
    // 清除之前的错误
    editTrackerError.value = ''
    
    // 1. 刷新分组列表，避免提交过时数据
    await fetchGroups()
    
    // 2. 调用后端API更新设备信息
    const { updateDevice } = await import('@/services/configApiService.js')
    const trackerId = currentEditingTracker.value.trackerId
    
    const response = await updateDevice(trackerId, trackerData)
    
    if (response.success) {
      console.log('[TrackerList] Device updated successfully:', response)
      
      // 发射事件通知父组件刷新数据
      emit('edit-tracker', {
        ...currentEditingTracker.value,
        ...trackerData,
        trackerId: trackerId
      })
      
      // 关闭模态框
      closeEditTrackerModal()
      
      console.log('[TrackerList] Tracker saved successfully')
    } else {
      throw new Error(response.message || t('tracker.trackerList.failedToUpdateDevice'))
    }
    
  } catch (error) {
    console.error('[TrackerList] Error saving tracker:', error)
    // 设置错误信息传递给EditTrackerModal
    editTrackerError.value = error.message || t('tracker.trackerList.failedToSaveDevice')
  }
}

// 分页处理函数
const handlePageChange = async (newPage) => {
  console.log('[TrackerList] Page change requested:', newPage)
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  // 更新页码
  currentPage.value = newPage
}

// 每页数量变化处理函数
const handleItemsPerPageChange = async () => {
  console.log('[TrackerList] Items per page changed to:', itemsPerPage.value)
  
  // 发射刷新数据事件
  emit('refresh-data')
  
  // 重置到第一页
  currentPage.value = 1
}

// 点击外部关闭菜单
const handleClickOutside = (event) => {
  if (!event.target.closest('.group-actions-dropdown')) {
    showGroupMenu.value = false
  }
  if (!event.target.closest('.group-filter-dropdown')) {
    showGroupFilter.value = false
  }
}

// 监听筛选条件变化，重置到第一页并刷新数据
watch([activeFilter, selectedGroup], () => {
  currentPage.value = 1
})

// 监听trackers数据变化，重新计算设备统计
watch(() => props.trackers, () => {
  calculateGroupDeviceCounts()
}, { deep: true })

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  // 组件挂载时获取分组列表
  fetchGroups()
  // 计算初始设备统计
  calculateGroupDeviceCounts()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.tracker-list-card {
  margin-bottom: 1.5rem;
}

.tracker-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.tracker-list-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
}

.tracker-filter-controls {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.group-filter-dropdown {
  position: relative;
  min-width: 240px;
}

.group-filter-button {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid var(--border-color, #ddd);
  border-radius: var(--border-radius, 4px);
  background-color: var(--card-background, white);
  color: var(--text-color, #333);
  font-size: 0.95rem;
  text-align: center;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 48px;
  box-sizing: border-box;
  transition: all 0.2s ease;
  margin: 0;
  vertical-align: top;
}

.group-filter-button:hover:not(:disabled) {
  border-color: var(--primary-color, #0056b3);
  box-shadow: 0 0 0 2px rgba(115, 199, 77, 0.1);
}

.group-filter-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dropdown-icon {
  transition: transform 0.2s ease;
  color: var(--secondary-color, #6c757d);
}

.dropdown-icon.rotated {
  transform: rotate(180deg);
}

.group-filter-menu {
  left: 0;
  right: auto;
  min-width: 240px;
}

.selected-icon {
  color: var(--primary-color, #0056b3);
  font-size: 0.8rem;
}

.selected-count {
  color: var(--primary-color, #0056b3);
  font-weight: 600;
  margin-left: 0.25rem;
}

.group-menu-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-icon {
  width: 48px;
  height: 48px;
  border: 2px solid var(--border-color, #ddd);
  background-color: var(--card-background, white);
  color: var(--text-color, #333);
  border-radius: var(--border-radius, 4px);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 1rem;
  box-sizing: border-box;
  flex-shrink: 0;
  margin: 0;
  padding: 0;
  vertical-align: top;
}

.btn-icon:hover {
  border-color: var(--primary-color, #0056b3);
  box-shadow: 0 0 0 2px rgba(115, 199, 77, 0.1);
  color: var(--primary-color, #0056b3);
}

.group-actions-dropdown {
  position: relative;
}

.group-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background-color: var(--card-background, white);
  border: 2px solid var(--border-color, #ddd);
  border-radius: var(--border-radius, 4px);
  box-shadow: var(--box-shadow, 0 4px 12px rgba(0, 0, 0, 0.15));
  z-index: 1000;
  min-width: 180px;
  padding: 0.5rem 0;
  margin-top: 0.25rem;
}

.group-menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-size: 0.95rem;
  color: var(--text-color, #333);
  transition: background-color 0.2s;
  white-space: nowrap;
}

.group-menu-item:hover {
  background-color: rgba(115, 199, 77, 0.05);
}

.group-menu-item i {
  width: 16px;
  text-align: center;
  color: var(--secondary-color, #6c757d);
  font-size: 0.85rem;
}

.group-menu-item span {
  flex: 1;
  font-weight: 500;
}

.tracker-filter-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid #e9ecef;
}

.filter-tab {
  padding: 0.75rem 1rem;
  border: none;
  background: none;
  color: #6c757d;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-tab:hover {
  color: #0056b3;
}

.filter-tab.active {
  color: #0056b3;
  border-bottom-color: #0056b3;
}

.filter-count {
  background: #e9ecef;
  color: #6c757d;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.filter-tab.active .filter-count {
  background: #0056b3;
  color: white;
}

.tracker-table-container {
  min-height: 400px;
  overflow-x: auto;
}

.tracker-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.tracker-table th {
  background: #f8f9fa;
  color: #495057;
  font-weight: 600;
  padding: 0.75rem;
  text-align: left;
  border-bottom: 2px solid #dee2e6;
  white-space: nowrap;
}

.tracker-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
}

.tracker-row:hover {
  background-color: #f8f9fa;
}

.device-info {
  min-width: 180px;
}

.device-name {
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.device-id {
  font-size: 0.8rem;
  color: #6c757d;
}

.sos-indicator {
  display: inline-block;
  background-color: #dc3545;
  color: white;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  margin-left: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  vertical-align: top;
}

.group-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.group-badge.blue { background: #e3f2fd; color: #1976d2; }
.group-badge.green { background: #e8f5e8; color: #2e7d32; }
.group-badge.orange { background: #fff3e0; color: #f57c00; }
.group-badge.purple { background: #f3e5f5; color: #7b1fa2; }
.group-badge.red { background: #ffebee; color: #c62828; }

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-icon {
  font-size: 0.8rem;
}

.status-icon.status-online {
  color: #28a745;
}

.status-icon.status-offline {
  color: #dc3545;
}

.status-text {
  font-weight: 500;
}

.status-text.online {
  color: #28a745;
}

.status-text.offline {
  color: #dc3545;
}

.position-info {
  min-width: 150px;
}

.position-coords {
  font-weight: 500;
  color: #333;
  margin-bottom: 0.25rem;
}

.position-time {
  font-size: 0.8rem;
  color: #6c757d;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.position-type {
  font-size: 0.75rem;
  font-weight: 500;
}

.precise-label {
  color: #28a745;
  background: rgba(40, 167, 69, 0.1);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

.area-label {
  color: #17a2b8;
  background: rgba(23, 162, 184, 0.1);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

.signal-battery {
  min-width: 120px;
}

.signal-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.signal-strength {
  font-size: 0.8rem;
  color: #6c757d;
}

.battery-info {
  font-size: 0.8rem;
  color: #6c757d;
}

.tracker-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-action {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.btn-star {
  background: none;
  color: #ffc107;
}

.btn-star:hover {
  background: #fff3cd;
}

.btn-star.starred {
  color: #ff8f00;
}

.btn-edit {
  background: none;
  color: #6c757d;
}

.btn-edit:hover {
  background: #e9ecef;
  color: #0056b3;
}

.btn-alert {
  background: none;
  color: #dc3545;
}

.btn-alert:hover {
  background: #f8d7da;
}

.no-trackers {
  text-align: center;
  padding: 3rem 1rem;
  color: #6c757d;
}

.no-trackers i {
  margin-bottom: 1rem;
}

.tracker-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1rem 0.5rem 1rem;
  border-top: 1px solid #e9ecef;
  margin-top: 1rem;
  background: #f8f9fa;
  border-radius: 0 0 8px 8px;
  min-height: 60px;
  flex-wrap: nowrap;
}

.pagination-info {
  font-size: 0.9rem;
  color: #495057;
  font-weight: 500;
  flex: 1;
  min-width: 120px;
  white-space: nowrap;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 0 0 auto;
  min-width: 80px;
  justify-content: center;
}

.btn-page {
  width: 22px;
  height: 22px;
  border: 1px solid #dee2e6;
  background: white;
  color: #495057;
  border-radius: 3px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  font-size: 0.75rem;
  vertical-align: baseline;
}

.btn-page:hover:not(:disabled) {
  background: #e9ecef;
  border-color: #adb5bd;
}

.btn-page:disabled {
  background: #f8f9fa;
  color: #adb5bd;
  cursor: not-allowed;
  border-color: #e9ecef;
}

.page-info {
  font-weight: 600;
  color: #495057;
  min-width: 24px;
  text-align: center;
  padding: 0 0.5rem;
  font-size: 0.9rem;
  line-height: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: baseline;
}

.items-per-page {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 0 0 auto;
  min-width: 100px;
  white-space: nowrap;
}

.items-per-page-select {
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: white;
  color: #495057;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  width: 52px;
  height: 22px;
  text-align: center;
  padding: 0 4px;
  margin: 0;
  box-sizing: border-box;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  vertical-align: baseline;
  line-height: normal;
}

.items-per-page-select:focus {
  outline: none;
  border-color: #0056b3;
  box-shadow: 0 0 0 2px rgba(0, 86, 179, 0.1);
}

.items-per-page-select:hover {
  border-color: #adb5bd;
}

.per-page-label {
  font-size: 0.9rem;
  color: #6c757d;
  font-weight: 500;
  line-height: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  vertical-align: baseline;
}

/* 创建分组模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.create-group-modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.modal-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.btn-close {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: #6c757d;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f8f9fa;
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
  margin-bottom: 0.5rem;
}

.required-star {
  color: #dc3545;
  margin-right: 0.25rem;
}

.input-wrapper {
  position: relative;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #0056b3;
  box-shadow: 0 0 0 2px rgba(0, 86, 179, 0.1);
}

.form-input.error {
  border-color: #dc3545;
}

.form-input.error:focus {
  border-color: #dc3545;
  box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.1);
}

.form-input:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
  opacity: 0.6;
}

.char-counter {
  position: absolute;
  right: 0.75rem;
  bottom: -1.5rem;
  font-size: 0.8rem;
  color: #6c757d;
}

.error-message {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-message::before {
  content: "\f071";
  font-family: "Font Awesome 5 Free";
  font-weight: 900;
  color: #dc3545;
  flex-shrink: 0;
}

.note-section {
  background: #f8f9fa;
  border-radius: 4px;
  padding: 1rem;
  margin-top: 1rem;
}

.note-label {
  font-weight: 500;
  color: #333;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.note-content {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #6c757d;
  line-height: 1.4;
}

.note-icon {
  color: #17a2b8;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 80px;
}

.btn-cancel {
  background: #6c757d;
  color: white;
}

.btn-cancel:hover {
  background: #545b62;
}

.btn-create {
  background: #0056b3;
  color: white;
}

.btn-create:hover:not(:disabled) {
  background: #004494;
}

.btn-create:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

/* 分组管理模态框样式 */
.group-management-modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-title-section {
  flex: 1;
}

.modal-subtitle {
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: #6c757d;
  line-height: 1.4;
}

.management-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.management-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.btn-create-new {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #0056b3;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-create-new:hover {
  background: #004494;
}

.groups-table-container {
  border: 1px solid #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.groups-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.groups-table th {
  background: #f8f9fa;
  color: #495057;
  font-weight: 600;
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
}

.groups-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #f1f3f4;
  vertical-align: middle;
}

.group-row:hover {
  background-color: #f8f9fa;
}

.group-name-cell {
  min-width: 200px;
}

.group-name-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.system-badge {
  padding: 0.2rem 0.5rem;
  background: #e9ecef;
  color: #6c757d;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 500;
}

.edit-group-input {
  width: 100%;
}

.edit-input-wrapper {
  position: relative;
  width: 100%;
}

.form-input-inline {
  width: 100%;
  padding: 0.5rem;
  border: 2px solid #0056b3;
  border-radius: 4px;
  font-size: 0.9rem;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-input-inline:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 86, 179, 0.1);
}

.form-input-inline.error {
  border-color: #dc3545;
}

.form-input-inline.error:focus {
  border-color: #dc3545;
  box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.1);
}

.form-input-inline:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
  opacity: 0.6;
}

.edit-char-counter {
  position: absolute;
  right: 0.5rem;
  bottom: -1.2rem;
  font-size: 0.7rem;
  color: #6c757d;
}

.device-count-cell {
  text-align: center;
  min-width: 100px;
}

.device-count {
  color: #6c757d;
  font-size: 0.85rem;
}

.actions-cell {
  text-align: right;
  min-width: 120px;
}

.group-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
}

.btn-action {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.btn-edit {
  background: none;
  color: #6c757d;
}

.btn-edit:hover {
  background: #e9ecef;
  color: #0056b3;
}

.btn-delete {
  background: none;
  color: #dc3545;
}

.btn-delete:hover:not(:disabled) {
  background: #f8d7da;
}

.btn-delete:disabled {
  color: #adb5bd;
  cursor: not-allowed;
}

.btn-save {
  background: #28a745;
  color: white;
}

.btn-save:hover {
  background: #218838;
}

.btn-cancel-edit {
  background: #6c757d;
  color: white;
}

.btn-cancel-edit:hover {
  background: #545b62;
}

.system-note {
  font-size: 0.8rem;
  color: #6c757d;
  font-style: italic;
}

.btn-close-modal {
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-close-modal:hover {
  background: #545b62;
}

/* 选择状态栏 */
.selection-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border: 1px solid #b3e5fc;
  border-radius: 6px;
  margin-bottom: 1rem;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #1976d2;
  font-weight: 500;
}

.selection-info i {
  color: #1976d2;
  font-size: 1rem;
}

.btn-clear-selection {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear-selection:hover {
  background: #f5f5f5;
  border-color: #bbb;
  color: #333;
}

.btn-clear-selection i {
  font-size: 0.8rem;
}

/* 复选框样式 */
.checkbox-header,
.checkbox-cell {
  width: 40px;
  text-align: center;
  padding: 0.75rem 0.5rem;
}

.select-checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--primary-color, #0056b3);
  cursor: pointer;
}

/* 移动分组模态框样式 */
.move-group-modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
}

.selected-devices-section {
  margin-bottom: 1.5rem;
}

.selected-devices-section h4 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.selected-devices-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 0.5rem;
}

.selected-device-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border-bottom: 1px solid #f1f3f4;
  font-size: 0.9rem;
}

.selected-device-item:last-child {
  border-bottom: none;
}

.selected-device-item .device-name {
  font-weight: 500;
  color: #333;
}

.selected-device-item .device-group {
  color: #6c757d;
  font-size: 0.8rem;
  background: #f8f9fa;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
}

.target-group-section {
  margin-bottom: 1rem;
}

.target-group-select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 4px;
  font-size: 0.9rem;
  background: white;
  transition: border-color 0.2s;
}

.target-group-select:focus {
  outline: none;
  border-color: #0056b3;
  box-shadow: 0 0 0 2px rgba(0, 86, 179, 0.1);
}

.btn-move {
  background: #0056b3;
  color: white;
}

.btn-move:hover:not(:disabled) {
  background: #004494;
}

.btn-move:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tracker-table-container {
    overflow-x: scroll;
  }
  
  .tracker-table {
    min-width: 800px;
  }
  
  .tracker-filter-controls {
    flex-direction: column;
    gap: 0.5rem;
    align-items: stretch;
  }
  
  .group-filter-dropdown {
    min-width: 100%;
  }
  
  .tracker-pagination {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0.5rem;
    min-height: auto;
  }
  
  .pagination-info,
  .pagination-controls,
  .items-per-page {
    min-width: auto;
    justify-content: center;
  }
  
  .selection-status-bar {
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }
  
  .create-group-modal {
    width: 95%;
    margin: 1rem;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }
  
  .group-management-modal {
    width: 95%;
    max-height: 95vh;
  }
  
  .management-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .groups-table-container {
    overflow-x: auto;
  }
  
  .groups-table {
    min-width: 500px;
  }
}
</style>
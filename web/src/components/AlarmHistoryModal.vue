<template>
  <div v-if="isVisible" class="alarm-history-modal-overlay" @click="handleOverlayClick">
    <div class="alarm-history-modal" @click.stop>
      <div class="modal-header">
        <div class="modal-title">
          <i class="fas fa-exclamation-triangle"></i>
          {{ $t('alarm.alarmInformationList') }}
        </div>
        <button class="close-button" @click="closeModal">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="modal-content">
        <!-- Device Info -->
        <div v-if="selectedTracker" class="device-info">
          <div class="device-name">
            <i class="fas fa-microchip"></i>
            {{ selectedTracker.device_name || selectedTracker.trackerId }}
          </div>
          <div v-if="selectedTracker.position" class="current-position">
            <i class="fas fa-map-marker-alt"></i>
            {{ $t('alarm.currentPosition') }}: {{ selectedTracker.map || $t('common.unknown') }}
            <span v-if="selectedTracker.position.x !== null && selectedTracker.position.y !== null">
              ({{ selectedTracker.position.x.toFixed(2) }}, {{ selectedTracker.position.y.toFixed(2) }})
            </span>
          </div>
          <div class="alarm-count">{{ alarms.length }} {{ $t('alarm.alarms') }}</div>
        </div>
        
        <!-- Alarm List -->
        <div class="alarm-list-container">
          <div v-if="loading" class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            {{ $t('alarm.loadingAlarms') }}
          </div>
          
          <div v-else-if="alarms.length === 0" class="empty-state">
            <i class="fas fa-info-circle"></i>
            {{ $t('alarm.noAlarmsFound') }}
          </div>
          
          <div v-else class="alarm-table">
            <div class="table-header">
              <div class="header-row">
                <div class="header-cell alarm-name">{{ $t('alarm.alarmName') }}</div>
                <div class="header-cell alarm-time">{{ $t('alarm.alarmTime') }}</div>
                <div class="header-cell alarm-position">{{ $t('alarm.alarmPosition') }}</div>
                <div class="header-cell position-type">{{ $t('alarm.positionType') }}</div>
<!--                <div class="header-cell actions">{{ $t('common.actions') }}</div>-->
              </div>
            </div>
            
            <div class="table-body">
              <div v-for="alarm in paginatedAlarms" :key="alarm.id" class="table-row">
                <div class="table-cell alarm-name">
                  <span class="alarm-title" :class="getAlarmTypeClass(alarm.type)">
                    {{ alarm.name }}
                  </span>
                </div>
                
                <div class="table-cell alarm-time">
                  <div class="time-wrapper">
                    <i class="fas fa-clock"></i>
                    <span>{{ formatDateTime(alarm.timestamp) }}</span>
                  </div>
                </div>
                
                <div class="table-cell alarm-position">
                  <div v-if="alarm.position && (alarm.position.x !== null || alarm.position.y !== null || alarm.position.radius !== null)" class="position-info">
                    <div class="position-map">
                      <i class="fas fa-map-marker-alt"></i>
                      {{ alarm.position.map || $t('common.unknown') }}
                    </div>
                    <div class="position-coords">
                      <span v-if="alarm.position.x !== null && alarm.position.y !== null">
                        ({{ alarm.position.x.toFixed(2) }}, {{ alarm.position.y.toFixed(2) }})
                      </span>
                      <span v-else>-</span>
                    </div>
                  </div>
                  <span v-else class="no-position">{{ $t('common.unknown') }}</span>
                </div>
                
                <div class="table-cell position-type">
                  <div v-if="alarm.position && (alarm.position.x !== null || alarm.position.y !== null || alarm.position.radius !== null)">
                    <span v-if="alarm.position.positionType === 'precise'" class="position-type-badge precise">
                      <i class="fas fa-crosshairs"></i>
                      {{ $t('alarm.precise') }}
                    </span>
                    <span v-else-if="alarm.position.positionType === 'area'" class="position-type-badge area">
                      <i class="fas fa-dot-circle"></i>
                      {{ $t('alarm.area') }}
                    </span>
                    <span v-else class="position-type-badge unknown">
                      <i class="fas fa-question"></i>
                      {{ $t('common.unknown') }}
                    </span>
                  </div>
                  <span v-else class="position-type-badge unknown">
                    <i class="fas fa-question"></i>
                    {{ $t('common.unknown') }}
                  </span>
                </div>
                
<!--                <div class="table-cell actions">-->
<!--                  <button -->
<!--                    v-if="alarm.position && (alarm.position.x !== null || alarm.position.y !== null || alarm.position.radius !== null)"-->
<!--                    class="action-button view-map" -->
<!--                    @click="viewOnMap(alarm)" -->
<!--                    title="View on Map"-->
<!--                  >-->
<!--                    {{ $t('alarm.viewMap') }}-->
<!--                  </button>-->
<!--                  <span v-else class="no-action">{{ $t('common.dash') }}</span>-->
<!--                </div>-->
              </div>
            </div>
          </div>
        </div>
        
        <!-- Pagination -->
        <div v-if="(totalPages || 0) > 1" class="pagination">
          <div class="pagination-info">
            {{ $t('common.total') }} {{ totalAlarms || 0 }} {{ $t('common.items') }}
          </div>
          <div class="pagination-controls">
            <button 
              class="pagination-button" 
              :disabled="currentPage <= 1"
              @click="changePage(currentPage - 1)"
            >
              <i class="fas fa-chevron-left"></i>
            </button>
            
            <div class="page-numbers">
              <button 
                v-for="page in visiblePages" 
                :key="page"
                class="page-number"
                :class="{ active: page === currentPage }"
                @click="changePage(page)"
              >
                {{ page }}
              </button>
            </div>
            
            <button 
              class="pagination-button" 
              :disabled="currentPage >= (totalPages || 0)"
              @click="changePage(currentPage + 1)"
            >
              <i class="fas fa-chevron-right"></i>
            </button>
          </div>
          <div class="per-page-selector">
            <span>{{ $t('common.perPage') }}:</span>
            <select v-model="itemsPerPage" @change="handleItemsPerPageChange">
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="close-footer-button" @click="closeModal">
          {{ $t('common.close') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { loadAlarmHistory } from '@/services/configApiService.js';

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  selectedTracker: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'view-on-map', 'view-details']);

const { t } = useI18n();

// Data
const loading = ref(false);
const alarms = ref([]);
const currentPage = ref(1);
const itemsPerPage = ref(50);
const totalAlarms = ref(0);
const totalPages = ref(0);

// Computed - 由于使用后端分页，直接显示当前页的数据
const paginatedAlarms = computed(() => {
  return alarms.value;
});

const visiblePages = computed(() => {
  const pages = [];
  const maxVisible = 5;
  const currentTotal = totalPages.value || 0;
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2));
  let end = Math.min(currentTotal, start + maxVisible - 1);
  
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  
  return pages;
});

// 数据转换函数：将后端数据转换为前端格式
const convertAlarmData = (backendRecord) => {
  // 根据event_type确定告警类型 - 修正映射关系
  const getAlarmTypeFromEventType = (eventType) => {
    // 根据后端常量定义的映射关系：
    // ALARM_TYPE_SOS = 1
    // ALARM_TYPE_OFFLINE = 2  
    // ALARM_TYPE_CHECKIN = 3
    // ALARM_TYPE_POSITION_DETECTION = 4
    const typeMap = {
      1: 'sos',           // SOS紧急求助
      2: 'offline',       // 设备离线告警  
      3: 'checkin',       // 长时间静止告警
      4: 'position'       // 位置检测
    };
    return typeMap[eventType] || 'unknown';
  };

  // 处理位置信息：检查loc是否为空对象或null
  const hasValidLocation = backendRecord.loc && 
                          typeof backendRecord.loc === 'object' && 
                          Object.keys(backendRecord.loc).length > 0;

  // 确定位置类型：Area 或 Precise
  const getPositionType = () => {
    if (!hasValidLocation) return null;
    
    const { pos_type } = backendRecord;
    const { x, y, radius } = backendRecord.loc;
    
    // 如果pos_type是approximate且存在radius，显示为Area
    if (pos_type === 'approximate' && radius !== undefined && radius !== null) {
      return 'area';
    }
    
    // 如果pos_type是calculation且有x,y坐标，显示为Precise
    if (pos_type === 'calculation' && x !== undefined && x !== null && y !== undefined && y !== null) {
      return 'precise';
    }
    
    return null;
  };

  // 根据status确定是否已解决
  const isResolved = backendRecord.status === 0; // 假设0表示已解决，1表示未解决
  
  return {
    id: backendRecord.id.toString(),
    name: backendRecord.event_name || t('alarm.unknownAlarm'),
    type: getAlarmTypeFromEventType(backendRecord.event_type),
    timestamp: new Date(backendRecord.alarm_time).getTime(),
    position: hasValidLocation ? {
      map: backendRecord.map_name || t('common.unknown'),
      x: backendRecord.loc.x,
      y: backendRecord.loc.y,
      radius: backendRecord.loc.radius,
      positionType: getPositionType() // 添加位置类型标识
    } : null,
    resolved: isResolved,
    resolveType: isResolved ? 'auto' : null, // 可以根据具体业务逻辑调整
    duration: null, // 后端数据中暂无持续时间，可以根据业务需求计算
    devEui: backendRecord.dev_eui,
    createTime: new Date(backendRecord.create_time).getTime(),
    posType: backendRecord.pos_type,
    beacons: (backendRecord.beacons && Array.isArray(backendRecord.beacons)) ? backendRecord.beacons : [],
    description: backendRecord.desc || {}
  };
};

// Methods
const loadAlarmHistoryData = async () => {
  if (!props.selectedTracker) return;
  
  loading.value = true;
  try {
    console.log('[AlarmHistory] Loading alarm history for tracker:', props.selectedTracker.trackerId);
    
    // 使用trackerId作为dev_eui参数
    const response = await loadAlarmHistory(
      props.selectedTracker.trackerId,
      currentPage.value,
      itemsPerPage.value
    );
    
    if (response && response.data) {
      // 转换数据格式
      alarms.value = response.data.records.map(convertAlarmData);
      
      // 更新分页信息
      if (response.data.pagination) {
        totalAlarms.value = response.data.pagination.total;
        totalPages.value = response.data.pagination.total_pages;
      }
      
      console.log(`[AlarmHistory] Loaded ${alarms.value.length} alarms, total: ${totalAlarms.value}`);
    } else {
      alarms.value = [];
      totalAlarms.value = 0;
      totalPages.value = 0;
    }
  } catch (error) {
    console.error('Error loading alarm history:', error);
    alarms.value = [];
    totalAlarms.value = 0;
    totalPages.value = 0;
    
    // 显示错误信息
    // TODO: 可以通过emit事件向父组件传递错误信息
  } finally {
    loading.value = false;
  }
};

const formatDateTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const formatDuration = (durationMs) => {
  if (!durationMs) return '';
  
  const seconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`;
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds % 60}秒`;
  } else {
    return `${seconds}秒`;
  }
};

const getAlarmTypeClass = (type) => {
  const classes = {
    'offline': 'type-offline',
    'checkin': 'type-checkin',
    'sos': 'type-sos',
    'position': 'type-position',
    'unknown': 'type-default'
  };
  return classes[type] || 'type-default';
};

const getAlarmTypeIcon = (type) => {
  const icons = {
    'offline': 'fas fa-wifi-slash',
    'checkin': 'fas fa-clock',
    'sos': 'fas fa-exclamation-triangle',
    'position': 'fas fa-map-marker-alt',
    'unknown': 'fas fa-bell'
  };
  return icons[type] || 'fas fa-bell';
};

const getAlarmTypeText = (type) => {
  const texts = {
    'offline': t('alarm.type.offline'),
    'checkin': t('alarm.type.checkin'), 
    'sos': t('alarm.type.sos'),
    'position': t('alarm.type.position'),
    'unknown': t('alarm.type.unknown')
  };
  return texts[type] || t('alarm.type.unknown');
};

const getResolveTypeClass = (resolveType) => {
  const classes = {
    'auto': 'resolve-auto',
    'manual': 'resolve-manual'
  };
  return classes[resolveType] || 'resolve-default';
};

const getResolveTypeIcon = (resolveType) => {
  const icons = {
    'auto': 'fas fa-magic',
    'manual': 'fas fa-user'
  };
  return icons[resolveType] || 'fas fa-check';
};

const getResolveTypeText = (resolveType) => {
  const texts = {
    'auto': t('alarm.resolve.auto'),
    'manual': t('alarm.resolve.manual')
  };
  return texts[resolveType] || t('alarm.resolved');
};

const changePage = async (page) => {
  const maxPages = totalPages.value || 0;
  if (page >= 1 && page <= maxPages && page !== currentPage.value) {
    currentPage.value = page;
    await loadAlarmHistoryData(); // 重新加载数据
  }
};

const handleItemsPerPageChange = async () => {
  currentPage.value = 1; // Reset to first page when changing items per page
  await loadAlarmHistoryData(); // 重新加载数据
};

const closeModal = () => {
  emit('close');
};

const handleOverlayClick = () => {
  closeModal();
};

const viewOnMap = (alarm) => {
  emit('view-on-map', alarm);
};

const viewDetails = (alarm) => {
  emit('view-details', alarm);
};

// Watch for both tracker and visibility changes to avoid duplicate calls
watch([() => props.selectedTracker, () => props.isVisible], ([newTracker, isVisible], [oldTracker, wasVisible]) => {
  // Only load data when modal becomes visible with a valid tracker
  // or when tracker changes while modal is already visible
  if (isVisible && newTracker) {
    // Reset to first page only if tracker changed or modal just opened
    if (newTracker !== oldTracker || !wasVisible) {
      currentPage.value = 1;
    }
    loadAlarmHistoryData();
  }
}, { immediate: true });
</script>

<style scoped>
.alarm-history-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.alarm-history-modal {
  background: var(--card-background);
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  width: 100%;
  max-width: 1000px;
  max-height: 95vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--background-color);
  border-radius: var(--border-radius) var(--border-radius) 0 0;
}

.modal-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modal-title i {
  color: var(--warning-color);
}

.close-button {
  background: none;
  border: none;
  font-size: 1.2rem;
  color: var(--secondary-color);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 50%;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: var(--danger-color);
  color: white;
}

.modal-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 1rem 1.5rem;
}

.device-info {
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--background-color);
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
}

.device-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.device-name i {
  color: var(--primary-color);
}

.current-position {
  font-size: 0.9rem;
  color: var(--secondary-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.current-position i {
  color: var(--danger-color);
}

.alarm-count {
  font-size: 1rem;
  font-weight: 600;
  color: var(--warning-color);
  text-align: right;
}

.alarm-list-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 确保flex容器可以收缩 */
}

.loading-state, .empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 3rem;
  color: var(--secondary-color);
  font-size: 0.95rem;
}

.loading-state i {
  color: var(--primary-color);
}

.alarm-table {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  width: 100%;
  display: block;
  max-height: 400px;
  overflow-y: auto;
}

.table-header {
  display: block;
  background: var(--background-color);
  border-bottom: 2px solid var(--border-color);
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-color);
  position: sticky;
  top: 0;
  z-index: 1;
}

.header-row {
  display: flex;
}

.header-cell {
  padding: 0.75rem 0.5rem;
  border-right: 1px solid var(--border-color);
  text-align: left;
  display: flex;
  align-items: center;
}

.header-cell:nth-child(1) { width: 23%; } /* Alarm Name */
.header-cell:nth-child(2) { width: 18%; } /* Alarm Time */  
.header-cell:nth-child(3) { width: 23%; } /* Alarm Position */
.header-cell:nth-child(4) { width: 15%; } /* Position Type */
.header-cell:nth-child(5) { width: 12%; } /* Actions */

.header-cell:last-child {
  border-right: none;
}

.table-body {
  display: block;
}

.table-row {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  transition: background-color 0.2s ease;
}

.table-row:hover {
  background: rgba(115, 199, 77, 0.05);
}

.table-cell {
  padding: 0.75rem 0.5rem;
  border-right: 1px solid var(--border-color);
  font-size: 0.9rem;
  text-align: left;
  display: flex;
  align-items: center;
}

.table-cell:nth-child(1) { width: 23%; } /* Alarm Name */
.table-cell:nth-child(2) { width: 18%; } /* Alarm Time */  
.table-cell:nth-child(3) { width: 23%; } /* Alarm Position */
.table-cell:nth-child(4) { width: 15%; } /* Position Type */
.table-cell:nth-child(5) { width: 12%; } /* Actions */

.table-cell:last-child {
  border-right: none;
}

/* Alarm Name Cell */
.alarm-title {
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* Alarm Time Cell */  
.time-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--secondary-color);
  white-space: nowrap;
  overflow: hidden;
  width: 100%;
}

.time-wrapper span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.time-wrapper i {
  color: var(--info-color);
}

/* Position Info Cell */
.position-info {
  display: block;
  width: 100%;
  min-width: 0;
}

.position-map {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-weight: 500;
  color: var(--text-color);
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  margin-bottom: 0.25rem;
}

.position-map i {
  color: var(--danger-color);
  flex-shrink: 0;
}

.position-coords {
  font-size: 0.8rem;
  color: var(--secondary-color);
  font-family: monospace;
  margin-left: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.alarm-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--border-radius);
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.type-offline {
  color: var(--secondary-color);
}

.type-battery {
  color: var(--warning-color);
}

.type-sos {
  color: var(--danger-color);
}

.type-checkin {
  color: var(--warning-color);
}

.type-position {
  color: var(--success-color);
}

.type-default, .type-unknown {
  color: var(--secondary-color);
}

.position-map {
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 0.125rem;
}

.position-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.position-coords, .position-area {
  font-size: 0.75rem;
  color: var(--secondary-color);
  font-family: monospace;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.position-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.375rem;
  border-radius: var(--border-radius);
  font-size: 0.65rem;
  font-weight: 600;
  font-family: sans-serif;
  white-space: nowrap;
}

.position-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--border-radius);
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.position-type-badge.precise {
  background: rgba(115, 199, 77, 0.1);
  color: var(--success-color);
  border: 1px solid rgba(115, 199, 77, 0.3);
}

.position-type-badge.area {
  background: rgba(255, 152, 0, 0.1);
  color: #FF9800;
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.position-type-badge.unknown {
  background: rgba(158, 158, 158, 0.1);
  color: #757575;
  border: 1px solid rgba(158, 158, 158, 0.3);
}

.no-position {
  color: var(--secondary-color);
  font-style: italic;
}

.resolve-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--border-radius);
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.resolved.resolve-auto {
  background: rgba(115, 199, 77, 0.1);
  color: var(--success-color);
}

.resolved.resolve-manual {
  background: rgba(66, 133, 244, 0.1);
  color: var(--info-color);
}

.unresolved {
  background: rgba(230, 162, 60, 0.1);
  color: var(--warning-color);
}

.actions {
  text-align: center;
}

.action-button {
  background: none;
  border: none;
  color: var(--info-color);
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0.25rem 0.5rem;
  text-decoration: underline;
  transition: all 0.2s ease;
}

.action-button:hover {
  color: var(--primary-color);
  text-decoration: none;
}

.no-action {
  color: var(--secondary-color);
  font-size: 0.85rem;
  font-style: italic;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-top: 1px solid var(--border-color);
  margin-top: 1rem;
  gap: 1rem;
}

.pagination-info {
  font-size: 0.85rem;
  color: var(--secondary-color);
  white-space: nowrap;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pagination-button {
  background: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  color: var(--text-color);
  transition: all 0.2s ease;
}

.pagination-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-button:not(:disabled):hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.page-number {
  background: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  color: var(--text-color);
  transition: all 0.2s ease;
  min-width: 2.5rem;
  text-align: center;
}

.page-number.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.page-number:not(.active):hover {
  background: rgba(115, 199, 77, 0.1);
  border-color: var(--primary-color);
}

.per-page-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--secondary-color);
  white-space: nowrap;
}

.per-page-selector select {
  background: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.25rem 0.5rem;
  color: var(--text-color);
  font-size: 0.85rem;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  background: var(--background-color);
  display: flex;
  justify-content: flex-end;
  border-radius: 0 0 var(--border-radius) var(--border-radius);
}

.close-footer-button {
  background: var(--secondary-color);
  color: white;
  border: none;
  border-radius: var(--border-radius);
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.close-footer-button:hover {
  background: var(--text-color);
}

/* Responsive */
@media (max-width: 1024px) {
  .alarm-history-modal {
    margin: 0.5rem;
    max-width: none;
  }
  
  .header-cell:nth-child(1), .table-cell:nth-child(1) { width: 25%; }
  .header-cell:nth-child(2), .table-cell:nth-child(2) { width: 16%; }  
  .header-cell:nth-child(3), .table-cell:nth-child(3) { width: 25%; }
  .header-cell:nth-child(4), .table-cell:nth-child(4) { width: 16%; }
  .header-cell:nth-child(5), .table-cell:nth-child(5) { width: 13%; }
  
  .pagination {
    flex-direction: column;
    gap: 0.75rem;
    align-items: stretch;
  }
  
  .pagination-controls {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .modal-header, .modal-content, .modal-footer {
    padding-left: 1rem;
    padding-right: 1rem;
  }
  
  .header-cell:nth-child(1), .table-cell:nth-child(1) { width: 28%; }
  .header-cell:nth-child(2), .table-cell:nth-child(2) { width: 18%; }  
  .header-cell:nth-child(3), .table-cell:nth-child(3) { width: 22%; }
  .header-cell:nth-child(4), .table-cell:nth-child(4) { width: 18%; }
  .header-cell:nth-child(5), .table-cell:nth-child(5) { width: 14%; }
  
  .table-header, .table-body, .table-row {
    font-size: 0.8rem;
  }
  
  .table-cell {
    padding: 0.5rem 0.25rem;
  }
  
  .alarm-meta {
    gap: 0;
  }
  
  .alarm-time, .alarm-duration {
    font-size: 0.7rem;
  }
  
  .page-numbers {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
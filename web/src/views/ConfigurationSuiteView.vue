<template>
  <div class="configuration-suite page-container">
    <h1 class="page-title">{{ t('config.management.title') }}</h1>
    
    <p class="info-banner status-display info" v-if="configStatusMessage">{{ configStatusMessage }}</p>
    
    <!-- 统一配置概览 -->
    <div class="unified-stats-overview card">
      <div class="card-header"><h2>{{ t('config.management.overview') }}</h2></div>
      <div class="card-content">
        <div class="stats-grid">
          <!-- 地图与信标统计 -->
          <div class="stat-item map-beacon-stats">
            <div class="stat-number">{{ dashboardStats.totalMaps }}</div>
            <div class="stat-label">{{ t('config.management.totalMaps') }}</div>
          </div>
          <div class="stat-item map-beacon-stats">
            <div class="stat-number">{{ dashboardStats.totalBeacons }}</div>
            <div class="stat-label">{{ t('config.management.totalBeacons') }}</div>
          </div>
          
          <!-- Tracker统计 -->
          <div class="stat-item tracker-stats">
            <div class="stat-number">{{ allowTrackerList.length }}</div>
            <div class="stat-label">{{ t('config.management.totalTrackers') }}</div>
          </div>
          <div class="stat-item tracker-stats">
            <div class="stat-number">{{ onlineTrackersCount }}</div>
            <div class="stat-label">{{ t('config.management.onlineDevices') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 配置项切换标签 -->
    <div class="config-tabs-navigation">
      <button 
        @click="activeMainTab = 'map-beacon'" 
        :class="{ active: activeMainTab === 'map-beacon' }"
        class="config-tab-button"
      >
        <i class="fas fa-map-marked-alt"></i> {{ t('config.management.mapBeaconConfig') }}
      </button>
      <button 
        @click="activeMainTab = 'tracker'" 
        :class="{ active: activeMainTab === 'tracker' }"
        class="config-tab-button"
      >
        <i class="fas fa-satellite-dish"></i> {{ t('config.management.trackerConfig') }}
      </button>
    </div>

    <!-- 地图与信标配置标签内容 -->
    <div v-if="activeMainTab === 'map-beacon'" class="main-tab-content">
      <!-- 地图选择器 -->
    <div class="map-selector card">
      <div class="card-header">
        <h2>{{ t('config.mapSelector.title') }}</h2>
        <div class="header-actions">
          <button @click="exportDashboardConfiguration" class="export-config-btn">
            <i class="fas fa-download"></i> {{ t('config.actions.downloadAllMaps') }}
          </button>
          <button @click="loadDashboardConfigurationData" :disabled="isLoadingConfig" class="refresh-config-btn">
            <i class="fas fa-sync-alt"></i> {{ isLoadingConfig ? t('common.loading') : t('config.mapSelector.refresh') }}
          </button>
        </div>
      </div>
      <div class="card-content">
        <div v-if="availableMaps.length === 0" class="no-maps-message">
          <p>📭 {{ t('config.mapSelector.noMaps') }}</p>
          <p class="hint">{{ t('config.mapSelector.noMapsHint') }}</p>
        </div>
        <div v-else class="map-selector-dropdown">
          <div class="dropdown-wrapper">
            <label for="map-select" class="dropdown-label">{{ t('config.mapSelector.selectLabel') }}</label>
            <select 
              id="map-select"
              v-model="selectedMapIndex" 
              @change="selectMap(selectedMapIndex)"
              class="map-dropdown"
            >
              <option value="" disabled selected>{{ t('config.mapSelector.selectPlaceholder') }}</option>
              <option 
                v-for="(mapConfig, index) in availableMaps" 
                :key="index"
                :value="index"
              >
                {{ mapConfig.map?.name || `${t('tracker.unnamedMap')} ${index + 1}` }} 
                ({{ mapConfig.beacons.length }} {{ t('tracker.beacons') }} | 
                {{ mapConfig.map?.width?.toFixed(1) || 'N/A' }}×{{ mapConfig.map?.height?.toFixed(1) || 'N/A' }}m)
              </option>
            </select>
            
            <!-- 地图管理按钮 -->
            <div class="map-actions">
              <!-- 当有任何更改时显示保存按钮 -->
              <template v-if="shouldShowSaveFunction">
                <button 
                  @click="saveChanges" 
                  class="action-button save-button"
                  :title="t('config.actions.saveAllChanges')"
                >
                  <i class="fas fa-save"></i> {{ t('config.actions.saveChanges') }}
                </button>
                <button 
                  @click="cancelAllChanges" 
                  class="action-button cancel-button"
                  :title="t('config.actions.cancelAllChanges')"
                >
                  <i class="fas fa-times"></i> {{ t('config.actions.cancel') }}
                </button>
              </template>
              
              <!-- 正常状态下的操作按钮 -->
              <template v-else>
                <button 
                  @click="createNewMap" 
                  class="action-button create-button"
                  :title="t('config.createNewMap')"
                >
                  <i class="fas fa-plus"></i> {{ t('config.actions.create') }}
                </button>
                <button 
                  @click="toggleEditMode" 
                  :disabled="!selectedMapConfig"
                  class="action-button edit-button"
                  :title="t('config.actions.edit')"
                >
                  <i class="fas fa-edit"></i> {{ t('config.actions.edit') }}
                </button>
                <button 
                  @click="deleteCurrentMap" 
                  :disabled="!selectedMapConfig || availableMaps.length <= 1"
                  class="action-button delete-button"
                  :title="t('config.actions.delete')"
                >
                  <i class="fas fa-trash"></i> {{ t('config.actions.delete') }}
                </button>
              </template>
            </div>
          </div>
          
          <!-- 创建新地图模式提示 -->
          <div v-if="isCreatingNewMap" class="create-mode-banner">
            <i class="fas fa-plus-circle"></i>
            <span>{{ t('config.status.creating') }} "{{ tempMapName }}" - {{ t('config.status.creatingHint') }}</span>
          </div>
          
          <!-- 编辑模式提示 -->
          <div v-else-if="isEditMode" class="edit-mode-banner">
            <i class="fas fa-edit"></i>
            <span>{{ t('config.status.editMode') }}</span>
          </div>
          
          <!-- 有未保存更改的提示 -->
          <div v-else-if="hasUnsavedChanges" class="unsaved-changes-banner">
            <i class="fas fa-exclamation-triangle"></i>
            <span>{{ t('config.status.unsavedChanges') }}</span>
          </div>
        </div>
      </div>
    </div>


    <!-- 只有选择了地图或在创建新地图时才显示标签页和内容 -->
    <div v-if="selectedMapConfig || isCreatingNewMap" class="tabs-navigation">
      <button @click="activeTab = 'map'" :class="{ active: activeTab === 'map' }">{{ t('config.mapSelector.mapTab') }}</button>
      <button @click="activeTab = 'beacons'" :class="{ active: activeTab === 'beacons' }">{{ t('config.mapSelector.beaconsTab') }}</button>
      <button @click="activeTab = 'settings'" :class="{ active: activeTab === 'settings' }">{{ t('config.mapSelector.settingsTab') }}</button>
    </div>

    <div v-if="selectedMapConfig || isCreatingNewMap" class="tab-content card">
      <div class="card-content">
        <BeaconManagerTab
          v-if="activeTab === 'beacons'"
          ref="beaconManagerTabRef"
          :initial-beacons="currentConfiguration.beacons"
          :current-map-layout="currentConfiguration.map"
          :read-only="!isEditMode"
          @beacons-updated="handleBeaconsUpdated"
          @beacon-selected-for-placement="handleBeaconSelectedForPlacement"
        />
        <!-- 隐藏的MapEditorTab，用于编辑模式和信标放置功能 -->
        <MapEditorTab 
          v-show="false"
          ref="mapEditorTabRef"
          :initial-map-data="currentConfiguration.map"
          :configured-beacons="currentConfiguration.beacons"
          :selected-beacon-for-placement="selectedBeaconForPlacement"
          :process-uploaded-map-config="updateConfigFromMapEditor"
          :read-only="!isEditMode"
          @beacon-coordinates-updated="handleBeaconCoordinatesUpdated"
          @request-beacon-selection="handleRequestBeaconSelection"
        />
        <!-- Map标签页内容 -->
        <div v-if="activeTab === 'map'" class="map-tab-content">
          <!-- 地图基本信息 -->
          <div class="map-basic-info card">
            <div class="card-header">
              <h3><i class="fas fa-info-circle"></i> {{ t('config.mapInfo.title') }}</h3>
              <button 
                v-if="isEditMode || isCreatingNewMap" 
                @click="triggerMapJsonImport" 
                class="import-json-btn"
                :title="t('config.actions.importTooltip')"
              >
                <i class="fas fa-file-import"></i> {{ t('config.actions.import') }}
              </button>
            </div>
            <div class="card-content">
              <!-- 只读模式 -->
              <div v-if="!isEditMode && !isCreatingNewMap" class="info-grid">
                <div class="info-item">
                  <label>{{ t('config.mapInfo.name') }}</label>
                  <span class="info-value">{{ currentConfiguration.map?.name || t('config.mapInfo.nameNotSet') }}</span>
                </div>
                <div class="info-item">
                  <label>{{ t('config.mapInfo.dimensions') }}</label>
                  <span class="info-value">
                    {{ (currentConfiguration.map?.width || 0).toFixed(3) }}{{ t('config.mapInfo.meters') }} × {{ (currentConfiguration.map?.height || 0).toFixed(3) }}{{ t('config.mapInfo.meters') }}
                  </span>
                </div>
                <div v-if="currentConfiguration.map?.entities?.length > 0" class="info-item">
                  <label>{{ t('config.mapInfo.entities') }}</label>
                  <span class="info-value">{{ currentConfiguration.map?.entities?.length }} {{ t('config.mapInfo.entitiesUnit') }}</span>
                </div>
              </div>
              
              <!-- 编辑模式 -->
              <div v-else class="edit-grid">
                <div class="edit-item">
                  <label for="mapName">{{ t('config.mapInfo.name') }}</label>
                  <input 
                    type="text" 
                    id="mapName"
                    v-model="currentConfiguration.map.name"
                    :maxlength="10"
                    class="map-info-input"
                    @input="validateEditingMapName"
                    :placeholder="t('config.mapInfo.namePlaceholder')"
                  />
                  <div v-if="editingMapNameError" class="error-message-small">
                    <i class="fas fa-exclamation-triangle"></i>
                    {{ editingMapNameError }}
                  </div>
                </div>
                
                <div class="edit-item">
                  <label for="mapWidth">{{ t('config.mapInfo.width') }}</label>
                  <input 
                    type="number" 
                    id="mapWidth"
                    v-model.number="currentConfiguration.map.width"
                    min="1"
                    max="1000"
                    step="0.1"
                    class="map-info-input"
                    :placeholder="t('config.mapInfo.widthPlaceholder')"
                  />
                </div>
                
                <div class="edit-item">
                  <label for="mapHeight">{{ t('config.mapInfo.height') }}</label>
                  <input 
                    type="number" 
                    id="mapHeight"
                    v-model.number="currentConfiguration.map.height"
                    min="1"
                    max="1000"
                    step="0.1"
                    class="map-info-input"
                    :placeholder="t('config.mapInfo.heightPlaceholder')"
                  />
                </div>
                
                <div v-if="currentConfiguration.map?.entities?.length > 0" class="edit-item">
                  <label>{{ t('config.mapInfo.entities') }}</label>
                  <span class="info-value readonly">{{ currentConfiguration.map?.entities?.length }} {{ t('config.mapInfo.entitiesUnit') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <GeneralSettingsTab 
          v-if="activeTab === 'settings'"
          ref="generalSettingsTabRef"
          :initial-settings="currentConfiguration.settings"
          :read-only="!isEditMode"
          @settings-updated="handleSettingsUpdated"
        />
        
        <!-- 共享地图预览 - 所有标签页都能看到，在有绘图实体或需要放置信标时显示 -->
        <div v-if="currentConfiguration.map?.entities?.length > 0 || selectedBeaconForPlacement" class="shared-map-preview card" ref="mapPreviewCardRef">
          <div class="card-header">
            <h3><i class="fas fa-map"></i> {{ t('config.mapPreview.title') }}</h3>
            <div v-if="selectedBeaconForPlacement" class="placement-hint">
              <span><i class="fas fa-mouse-pointer"></i> {{ t('config.mapPreview.placementHint') }} {{ selectedBeaconForPlacement.displayName }}</span>
            </div>
          </div>
          <div class="card-content">
            <div class="map-canvas-container">
              <canvas 
                ref="mapPreviewCanvasRef" 
                class="map-preview-canvas"
                :class="{ 'clickable': selectedBeaconForPlacement }"
                width="600" 
                height="400"
                @click="handleMapPreviewClick"
              ></canvas>
            </div>
            <div v-if="currentConfiguration.beacons?.length > 0" class="beacon-summary">
              <p><i class="fas fa-info-circle"></i> {{ currentConfiguration.beacons.length }} {{ t('config.mapPreview.beaconSummary') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

      <!-- 未选择地图时的提示信息 -->
      <div v-if="!selectedMapConfig && !isCreatingNewMap && availableMaps.length > 0" class="no-map-selected-message card">
        <div class="card-content">
          <div class="empty-state">
            <i class="fas fa-map-marked-alt empty-state-icon"></i>
            <h3>{{ t('config.emptyState.noMapSelected') }}</h3>
            <p>{{ t('config.emptyState.selectMapHint') }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Tracker配置标签内容 -->
    <div v-if="activeMainTab === 'tracker'" class="main-tab-content">
      <div class="tracker-config-section card">
        <div class="card-header">
          <h2><i class="fas fa-satellite-dish"></i> {{ t('tracker.configuration.title') }}</h2>
        </div>
        <div class="card-content">
          <div class="config-section">
            <h3>{{ t('tracker.configuration.allowList.title') }}</h3>
            <p class="section-description">{{ t('tracker.configuration.allowList.description') }}</p>
            
            <div class="tracker-list-management">
              <div class="input-group">
                <input 
                  type="text" 
                  v-model="newTrackerEui"
                  :placeholder="t('tracker.configuration.allowList.inputPlaceholder')"
                  class="tracker-input"
                  @keyup.enter="addTrackerToList"
                />
                <button 
                  @click="addTrackerToList" 
                  :disabled="!newTrackerEui.trim()"
                  class="add-button"
                >
                  <i class="fas fa-plus"></i> {{ t('tracker.configuration.allowList.add') }}
                </button>
              </div>
              
              <div v-if="allowTrackerList.length > 0" class="tracker-list">
                <h4>{{ t('tracker.configuration.allowList.current') }} ({{ allowTrackerList.length }}{{ t('tracker.configuration.allowList.count') }}):</h4>
                <div class="tracker-items">
                  <div 
                    v-for="(eui, index) in allowTrackerList" 
                    :key="index"
                    class="tracker-item"
                  >
                    <span class="tracker-eui">{{ eui }}</span>
                    <button 
                      @click="removeTrackerFromList(index)"
                      class="remove-button"
                      :title="t('tracker.configuration.allowList.remove')"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </div>
                
                <div class="tracker-actions">
                  <button 
                    @click="saveTrackerList"
                    class="save-button"
                    :disabled="isSavingTrackers"
                  >
                    <i class="fas fa-save"></i> 
                    {{ isSavingTrackers ? t('tracker.configuration.allowList.saving') : t('tracker.configuration.allowList.save') }}
                  </button>
                  <button 
                    @click="loadTrackerList"
                    class="reload-button"
                  >
                    <i class="fas fa-sync-alt"></i> {{ t('tracker.configuration.allowList.reload') }}
                  </button>
                </div>
              </div>
              
              <div v-else class="empty-tracker-list">
                <i class="fas fa-satellite-dish empty-icon"></i>
                <p>{{ t('tracker.configuration.allowList.empty') }}</p>
                <p class="hint">{{ t('tracker.configuration.allowList.emptyHint') }}</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- 隐藏的文件输入元素 -->
    <input 
      type="file" 
      ref="mapJsonFileInputRef" 
      @change="handleMapJsonFileImport" 
      accept=".json" 
      style="display: none;"
    />

    <!-- 创建新地图名称输入模态框 -->
    <div v-if="showNewMapModal" class="modal-overlay">
      <div class="modal-content">
        <h4><i class="fas fa-map-plus"></i> {{ t('config.newMapModal.title') }}</h4>
        <form @submit.prevent="confirmCreateMap">
          <div class="form-group">
            <label for="newMapName">{{ t('config.newMapModal.nameLabel') }}</label>
            <input 
              type="text" 
              id="newMapName"
              v-model="newMapName" 
              :maxlength="10"
              :placeholder="t('config.newMapModal.namePlaceholder')"
              class="map-name-input"
              @input="validateMapName"
              ref="mapNameInputRef"
            />
            <div class="input-help">
              <span class="char-counter" :class="{ 'warning': newMapName.length > 8 }">
                {{ newMapName.length }}/10
              </span>
            </div>
            <div v-if="mapNameError" class="error-message">
              <i class="fas fa-exclamation-triangle"></i>
              {{ mapNameError }}
            </div>
          </div>
          
          <div class="modal-actions">
            <button type="submit" class="btn-primary" :disabled="!isMapNameValid">
              <i class="fas fa-check"></i> {{ t('config.newMapModal.confirm') }}
            </button>
            <button type="button" @click="cancelCreateMap" class="btn-secondary">
              <i class="fas fa-times"></i> {{ t('config.newMapModal.cancel') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import BeaconManagerTab from '@/components/configuration/BeaconManagerTab.vue';
import MapEditorTab from '@/components/configuration/MapEditorTab.vue';
import GeneralSettingsTab from '@/components/configuration/GeneralSettingsTab.vue';
import { 
  loadDashboardConfiguration, 
  saveDashboardConfiguration,
  loadAllowTrackerList,
  saveAllowTrackerList,
  loadTrackers
} from '@/services/configApiService.js';

// i18n setup
const { t } = useI18n();

const activeTab = ref('map');
const activeMainTab = ref('map-beacon'); // 主标签

// Refs for child components
const beaconManagerTabRef = ref(null);
const mapEditorTabRef = ref(null);
const generalSettingsTabRef = ref(null);
const mapPreviewCanvasRef = ref(null);
const mapJsonFileInputRef = ref(null);
const mapPreviewCardRef = ref(null);

const isLoadingConfig = ref(false);
const configStatusMessage = ref('');

// Dashboard configuration data
const dashboardConfig = ref(null);
const availableMaps = ref([]);
const selectedMapIndex = ref('');

// Legacy configuration for compatibility
const currentConfiguration = ref({
  map: null,
  beacons: [],
  settings: { signalPropagationFactor: 2.5 }
});
const selectedBeaconForPlacement = ref(null);

// 编辑模式状态
const isEditMode = ref(false);
// 是否有未保存的更改（beacon或设置）
const hasUnsavedChanges = ref(false);

// 新地图创建相关
const showNewMapModal = ref(false);
const newMapName = ref('');
const mapNameError = ref('');
const mapNameInputRef = ref(null);
const isCreatingNewMap = ref(false); // 标识是否在创建新地图状态
const tempMapName = ref(''); // 临时存储新地图名称
const editingMapNameError = ref(''); // 编辑地图名称时的错误信息

// Tracker配置相关
const newTrackerEui = ref('');
const allowTrackerList = ref([]);
const isSavingTrackers = ref(false);
const trackersData = ref({}); // 用于存储tracker实时状态
const allTrackers = ref([]); // 所有trackers数据（用于在线统计）

// 计算属性
const selectedMapConfig = computed(() => {
  // 如果正在创建新地图，返回一个标识对象，避免循环引用
  if (isCreatingNewMap.value) {
    return { isNewMap: true };
  }
  
  if (selectedMapIndex.value === '' || selectedMapIndex.value < 0) {
    return null;
  }
  return availableMaps.value[selectedMapIndex.value] || null;
});

const dashboardStats = computed(() => {
  const maps = availableMaps.value;
  const totalBeacons = maps.reduce((sum, map) => sum + (map.beacons?.length || 0), 0);
  
  return {
    totalMaps: maps.length,
    totalBeacons: totalBeacons,
    mapsWithBeacons: maps.filter(m => m.beacons && m.beacons.length > 0).length,
    averageBeaconsPerMap: maps.length > 0 ? (totalBeacons / maps.length).toFixed(1) : '0'
  };
});

// 地图名称验证
const isMapNameValid = computed(() => {
  const trimmedName = newMapName.value.trim();
  return trimmedName.length > 0 && 
         trimmedName.length <= 10 && 
         !mapNameError.value;
});

// 是否应该显示保存功能（编辑模式或有未保存的更改）
const shouldShowSaveFunction = computed(() => {
  return isEditMode.value || hasUnsavedChanges.value;
});

// Tracker相关统计
const onlineTrackersCount = computed(() => {
  // 统计15分钟内有更新的tracker（与TrackerModeConfigView保持一致）
  const now = Date.now();
  const fifteenMinutesMs = 15 * 60 * 1000; // 15 minutes in milliseconds
  
  return allTrackers.value.filter(tracker => {
    if (!tracker.last_update_time) return false;
    const lastUpdateTime = new Date(tracker.last_update_time).getTime();
    return (now - lastUpdateTime) <= fifteenMinutesMs;
  }).length;
});

const recentActiveTrackersCount = computed(() => {
  // 统计最近5分钟内有数据的tracker
  const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
  const trackerArray = Object.values(trackersData.value);
  return trackerArray.filter(tracker => 
    tracker.timestamp && tracker.timestamp > fiveMinutesAgo
  ).length;
});

// 加载仪表板配置数据
const loadDashboardConfigurationData = async () => {
  try {
    isLoadingConfig.value = true;
    configStatusMessage.value = t('common.loading') + '...';
    
    const dashboardData = await loadDashboardConfiguration();
    console.log('[ConfigurationSuiteView] Dashboard data loaded:', dashboardData);
    
    if (dashboardData && Array.isArray(dashboardData.maps)) {
      dashboardConfig.value = dashboardData;
      availableMaps.value = dashboardData.maps;
      
      // 加载地图后不默认选择，让用户主动选择
      if (dashboardData.maps.length > 0) {
        configStatusMessage.value = `${t('config.mapSelector.refresh')} ${dashboardData.maps.length} ${t('config.management.totalMaps')}`;
      } else {
        configStatusMessage.value = t('config.mapSelector.noMaps');
      }
    } else {
      availableMaps.value = [];
      configStatusMessage.value = t('common.error');
    }
  } catch (error) {
    console.error('[ConfigurationSuiteView] Failed to load dashboard configuration:', error);
    configStatusMessage.value = `${t('common.error')}: ${error.message}`;
    availableMaps.value = [];
  } finally {
    isLoadingConfig.value = false;
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  }
};

// 导出仪表板配置
const exportDashboardConfiguration = async () => {
  try {
    configStatusMessage.value = '正在导出配置...';
    
    // 从后端获取最新的配置数据
    const dashboardData = await loadDashboardConfiguration();
    
    if (!dashboardData) {
      configStatusMessage.value = '没有配置数据可导出';
      setTimeout(() => { configStatusMessage.value = '' }, 3000);
      return;
    }
    
    // 生成文件名，包含当前时间戳
    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `dashboard_config_${timestamp}.json`;
    
    // 将配置数据转换为格式化的JSON字符串
    const jsonString = JSON.stringify(dashboardData, null, 2);
    
    // 创建Blob对象
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    // 创建下载链接
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    // 触发下载
    document.body.appendChild(link);
    link.click();
    
    // 清理资源
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    configStatusMessage.value = `配置已导出为 ${filename}`;
    console.log('[ConfigurationSuiteView] Dashboard configuration exported:', filename);
    
  } catch (error) {
    console.error('[ConfigurationSuiteView] Failed to export dashboard configuration:', error);
    configStatusMessage.value = `导出失败: ${error.message}`;
  } finally {
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  }
};

// 选择地图
const selectMap = (index) => {
  // 切换地图时清除未保存的更改标记
  hasUnsavedChanges.value = false;
  
  if (index === '' || index === null || index === undefined) {
    // 清空选择
    selectedMapIndex.value = '';
    currentConfiguration.value = {
      map: null,
      beacons: [],
      settings: { signalPropagationFactor: 2.5 }
    };
    configStatusMessage.value = t('config.emptyState.noMapSelected');
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
    return;
  }
  
  if (index >= 0 && index < availableMaps.value.length) {
    selectedMapIndex.value = index;
    updateCurrentConfiguration();
    configStatusMessage.value = `${t('config.mapSelector.selectLabel')} ${availableMaps.value[index].map?.name || `${t('tracker.unnamedMap')} ${index + 1}`}`;
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
  }
};

// 更新当前配置以保持子组件兼容性
const updateCurrentConfiguration = () => {
  const selectedMap = selectedMapConfig.value;
  if (selectedMap && !selectedMap.isNewMap) {
    currentConfiguration.value = {
      map: selectedMap.map,
      beacons: selectedMap.beacons || [],
      settings: selectedMap.settings || { signalPropagationFactor: 2.5 }
    };
    
    // 通知子组件更新
    nextTick(() => {
      if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
      if (mapEditorTabRef.value?.loadConfiguration) {
        mapEditorTabRef.value.loadConfiguration(currentConfiguration.value);
      }
      if (generalSettingsTabRef.value?.loadSettings) {
        generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
    });
  }
};

// 监听选中地图变化
watch(() => selectedMapConfig.value, (newMapConfig) => {
  // 只有在不是创建新地图模式下才更新配置，避免循环依赖
  if (newMapConfig && !isCreatingNewMap.value) {
    updateCurrentConfiguration();
  }
}, { deep: true });

// 监听配置变化以重绘地图预览
watch(() => currentConfiguration.value, () => {
  nextTick(() => {
    drawMapPreview();
  });
}, { deep: true });

// 监听选中信标变化以重绘地图预览
watch(() => selectedBeaconForPlacement.value, () => {
  nextTick(() => {
    drawMapPreview();
  });
}, { deep: true });

// --- 数据管理和验证 ---

// 验证地图配置数据
const validateMapConfig = (mapConfig) => {
  const errors = [];
  
  // 验证地图基本信息
  if (!mapConfig.map) {
    errors.push('地图对象不能为空');
  } else {
    if (!mapConfig.map.name || mapConfig.map.name.trim() === '') {
      errors.push('地图名称不能为空');
    }
    if (typeof mapConfig.map.width !== 'number' || mapConfig.map.width <= 0) {
      errors.push('地图宽度必须是大于0的数字');
    }
    if (typeof mapConfig.map.height !== 'number' || mapConfig.map.height <= 0) {
      errors.push('地图高度必须是大于0的数字');
    }
    if (!Array.isArray(mapConfig.map.entities)) {
      errors.push('地图实体必须是数组');
    }
  }
  
  // 验证信标配置
  if (!Array.isArray(mapConfig.beacons)) {
    errors.push('信标配置必须是数组');
  } else {
    mapConfig.beacons.forEach((beacon, index) => {
      if (!beacon.uuid || typeof beacon.uuid !== 'string') {
        errors.push(`信标 ${index + 1}: UUID不能为空且必须是字符串`);
      }
      if (typeof beacon.major !== 'number' || beacon.major < 0 || beacon.major > 65535) {
        errors.push(`信标 ${index + 1}: Major必须是0-65535之间的数字`);
      }
      if (typeof beacon.minor !== 'number' || beacon.minor < 0 || beacon.minor > 65535) {
        errors.push(`信标 ${index + 1}: Minor必须是0-65535之间的数字`);
      }
      if (typeof beacon.x !== 'number') {
        errors.push(`信标 ${index + 1}: X坐标必须是数字`);
      }
      if (typeof beacon.y !== 'number') {
        errors.push(`信标 ${index + 1}: Y坐标必须是数字`);
      }
    });
  }
  
  // 验证设置
  if (!mapConfig.settings) {
    errors.push('设置对象不能为空');
  } else {
    if (typeof mapConfig.settings.signalPropagationFactor !== 'number' || 
        mapConfig.settings.signalPropagationFactor < 1 || 
        mapConfig.settings.signalPropagationFactor > 6) {
      errors.push('信号传播因子必须是1-6之间的数字');
    }
  }
  
  return errors;
};

// 格式化地图配置数据
const formatMapConfig = (mapConfig) => {
  return {
    map: {
      name: String(mapConfig.map?.name || '').trim(),
      width: Number(mapConfig.map?.width || 50),
      height: Number(mapConfig.map?.height || 50),
      entities: Array.isArray(mapConfig.map?.entities) ? mapConfig.map.entities : []
    },
    beacons: Array.isArray(mapConfig.beacons) ? mapConfig.beacons.map(beacon => ({
      uuid: String(beacon.uuid || '').toUpperCase(),
      major: Number(beacon.major || 0),
      minor: Number(beacon.minor || 0),
      x: Number(beacon.x || 0),
      y: Number(beacon.y || 0),
      txPower: Number(beacon.txPower || -59),
      displayName: String(beacon.displayName || ''),
      macAddress: String(beacon.macAddress || ''),
      deviceId: String(beacon.deviceId || beacon.macAddress || '')
    })) : [],
    settings: {
      signalPropagationFactor: Number(mapConfig.settings?.signalPropagationFactor || 2.5)
    },
    is_darwin: Boolean(mapConfig.is_darwin || false)
  };
};

// 生成完整的Dashboard配置
const generateDashboardConfig = () => {
  const formattedMaps = availableMaps.value.map(mapConfig => {
    const formatted = formatMapConfig(mapConfig);
    const errors = validateMapConfig(formatted);
    
    if (errors.length > 0) {
      console.warn(`地图 "${formatted.map.name}" 验证失败:`, errors);
    }
    
    return formatted;
  });
  
  return {
    maps: formattedMaps
  };
};

// 保存配置到后端
const saveDashboardToServer = async () => {
  try {
    configStatusMessage.value = '正在保存配置到服务器...';
    
    const dashboardConfig = generateDashboardConfig();
    
    // 验证整个配置
    let totalErrors = [];
    dashboardConfig.maps.forEach((mapConfig, index) => {
      const errors = validateMapConfig(mapConfig);
      if (errors.length > 0) {
        totalErrors.push(`地图 ${index + 1} (${mapConfig.map.name}): ${errors.join(', ')}`);
      }
    });
    
    if (totalErrors.length > 0) {
      const errorMessage = '配置验证失败:\n' + totalErrors.join('\n');
      configStatusMessage.value = '配置验证失败，请检查数据格式';
      alert(errorMessage);
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
      return false;
    }
    
    console.log('即将保存的Dashboard配置:', dashboardConfig);
    console.log(`配置包含 ${dashboardConfig.maps.length} 个地图:`);
    dashboardConfig.maps.forEach((map, index) => {
      console.log(`  地图 ${index + 1}: "${map.map.name}" (${map.beacons.length} 个信标)`);
    });
    
    // 调用后端API保存
    const response = await saveDashboardConfiguration(dashboardConfig);
    
    configStatusMessage.value = '配置已成功保存到服务器';
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
    
    return true;
    
  } catch (error) {
    console.error('保存Dashboard配置失败:', error);
    
    if (error.message.includes('404') || error.message.includes('Not Found')) {
      configStatusMessage.value = '后端暂不支持Dashboard配置保存，数据已在本地更新';
    } else {
      configStatusMessage.value = `保存失败: ${error.message}`;
    }
    
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
    return false;
  }
};

// --- 地图管理功能 ---

// 创建新地图
// 地图名称验证函数
const validateMapName = () => {
  const trimmedName = newMapName.value.trim();
  
  // 清除之前的错误
  mapNameError.value = '';
  
  // 检查是否为空或纯空格
  if (trimmedName.length === 0) {
    mapNameError.value = '地图名称不能为空';
    return false;
  }
  
  // 检查长度
  if (trimmedName.length > 10) {
    mapNameError.value = '地图名称不能超过10个字符';
    return false;
  }
  
  // 检查是否已存在（不区分大小写）
  const nameExists = availableMaps.value.some(map => 
    map.map?.name?.toLowerCase() === trimmedName.toLowerCase()
  );
  
  if (nameExists) {
    mapNameError.value = '地图名称已存在，请使用不同的名称';
    return false;
  }
  
  return true;
};

// 打开创建新地图模态框
const createNewMap = () => {
  newMapName.value = '';
  mapNameError.value = '';
  showNewMapModal.value = true;
  
  // 等待DOM更新后聚焦到输入框
  nextTick(() => {
    if (mapNameInputRef.value) {
      mapNameInputRef.value.focus();
    }
  });
};

// 确认地图名称并进入创建界面
const confirmCreateMap = async () => {
  if (!validateMapName() || !isMapNameValid.value) {
    return;
  }
  
  const trimmedName = newMapName.value.trim();
  
  // 保存临时地图名称
  tempMapName.value = trimmedName;
  
  // 创建临时地图配置用于编辑界面
  const tempMapConfig = {
    map: {
      name: trimmedName,
      width: 50,
      height: 50,
      entities: []
    },
    beacons: [],
    settings: {
      signalPropagationFactor: 2.5
    },
    is_darwin: false
  };
  
  // 设置临时配置到currentConfiguration，但不添加到availableMaps
  currentConfiguration.value = formatMapConfig(tempMapConfig);
  
  // 标记为创建新地图状态
  isCreatingNewMap.value = true;
  
  // 关闭模态框
  showNewMapModal.value = false;
  
  // 清空地图选择（因为这是新地图，还未保存）
  selectedMapIndex.value = '';
  
  // 自动进入编辑模式
  isEditMode.value = true;
  
  configStatusMessage.value = `正在创建新地图 "${trimmedName}"，请开始编辑地图内容`;
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
  
  console.log('进入新地图创建界面:', tempMapConfig);
};

// 取消创建地图
const cancelCreateMap = () => {
  showNewMapModal.value = false;
  newMapName.value = '';
  mapNameError.value = '';
};

// 验证编辑地图名称
const validateEditingMapName = () => {
  const trimmedName = currentConfiguration.value.map?.name?.trim() || '';
  
  // 清除之前的错误
  editingMapNameError.value = '';
  
  // 检查是否为空或纯空格
  if (trimmedName.length === 0) {
    editingMapNameError.value = '地图名称不能为空';
    return false;
  }
  
  // 检查长度
  if (trimmedName.length > 10) {
    editingMapNameError.value = '地图名称不能超过10个字符';
    return false;
  }
  
  // 检查是否已存在（不区分大小写），排除当前地图
  const currentIndex = selectedMapIndex.value;
  const nameExists = availableMaps.value.some((map, index) => 
    index !== currentIndex && 
    map.map?.name?.toLowerCase() === trimmedName.toLowerCase()
  );
  
  if (nameExists) {
    editingMapNameError.value = '地图名称已存在，请使用不同的名称';
    return false;
  }
  
  return true;
};

// 触发地图JSON文件导入
const triggerMapJsonImport = () => {
  if (mapJsonFileInputRef.value) {
    mapJsonFileInputRef.value.click();
  }
};

// 处理地图JSON文件导入（支持WebUIConfig格式）
const handleMapJsonFileImport = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const jsonData = JSON.parse(e.target.result);
      
      // 检测并处理不同的JSON格式
      if (isWebUIConfigFormat(jsonData)) {
        // WebUIConfig 格式：包含 map, beacons, settings
        handleWebUIConfigImport(jsonData);
      } else if (isLegacyMapFormat(jsonData)) {
        // 旧的地图格式：直接包含 width, height, entities
        handleLegacyMapImport(jsonData);
      } else {
        alert(`不支持的JSON格式。\n\n支持的格式：\n1. WebUIConfig格式（包含map、beacons、settings字段）\n2. 地图格式（包含width、height、entities字段）`);
        return;
      }
      
    } catch (error) {
      console.error('JSON文件解析失败:', error);
      alert(`JSON文件解析失败: ${error.message}\n\n请确保文件格式正确。`);
    }
  };
  
  reader.onerror = () => {
    alert('文件读取失败，请重试。');
  };
  
  reader.readAsText(file);
  
  // 清空文件输入，以便可以重复选择同一文件
  event.target.value = '';
};

// 检测是否为WebUIConfig格式
const isWebUIConfigFormat = (jsonData) => {
  return jsonData && 
         typeof jsonData === 'object' && 
         (jsonData.map || jsonData.beacons || jsonData.settings);
};

// 检测是否为旧的地图格式
const isLegacyMapFormat = (jsonData) => {
  return jsonData && 
         typeof jsonData === 'object' && 
         typeof jsonData.width === 'number' && 
         typeof jsonData.height === 'number' && 
         Array.isArray(jsonData.entities);
};

// 处理WebUIConfig格式导入
const handleWebUIConfigImport = (webUIConfig) => {
  const importedItems = [];
  let hasErrors = false;

  try {
    // 导入地图信息
    if (webUIConfig.map && currentConfiguration.value.map) {
      if (typeof webUIConfig.map.width === 'number' && 
          typeof webUIConfig.map.height === 'number' && 
          Array.isArray(webUIConfig.map.entities)) {
        
        currentConfiguration.value.map.width = webUIConfig.map.width;
        currentConfiguration.value.map.height = webUIConfig.map.height;
        currentConfiguration.value.map.entities = webUIConfig.map.entities;
        
        if (webUIConfig.map.name && typeof webUIConfig.map.name === 'string') {
          currentConfiguration.value.map.name = webUIConfig.map.name.trim();
        }
        
        importedItems.push(`地图 (${webUIConfig.map.width}m×${webUIConfig.map.height}m, ${webUIConfig.map.entities.length}个实体)`);
      } else {
        console.warn('地图数据格式不完整，跳过地图导入');
      }
    }

    // 导入信标配置
    if (Array.isArray(webUIConfig.beacons) && webUIConfig.beacons.length > 0) {
      const validBeacons = [];
      const invalidBeacons = [];

      webUIConfig.beacons.forEach((beacon, index) => {
        if (validateBeaconData(beacon)) {
          validBeacons.push({
            uuid: beacon.uuid?.toUpperCase() || '',
            major: beacon.major || 0,
            minor: beacon.minor || 0,
            x: beacon.x || 0,
            y: beacon.y || 0,
            txPower: beacon.txPower || -59,
            displayName: beacon.displayName || `信标${index + 1}`,
            macAddress: beacon.macAddress || '',
            deviceId: beacon.deviceId || beacon.macAddress || '',
            map: beacon.map
          });
        } else {
          invalidBeacons.push(index + 1);
        }
      });

      if (validBeacons.length > 0) {
        currentConfiguration.value.beacons = validBeacons;
        importedItems.push(`${validBeacons.length}个信标`);
        
        // 标记有未保存的更改
        hasUnsavedChanges.value = true;
      }

      if (invalidBeacons.length > 0) {
        console.warn(`信标 ${invalidBeacons.join(', ')} 的数据格式无效，已跳过`);
      }
    }

    // 导入设置
    if (webUIConfig.settings && typeof webUIConfig.settings === 'object') {
      if (typeof webUIConfig.settings.signalPropagationFactor === 'number' &&
          webUIConfig.settings.signalPropagationFactor >= 1 &&
          webUIConfig.settings.signalPropagationFactor <= 6) {
        
        currentConfiguration.value.settings.signalPropagationFactor = webUIConfig.settings.signalPropagationFactor;
        importedItems.push(`设置 (信号传播因子: ${webUIConfig.settings.signalPropagationFactor})`);
        
        // 标记有未保存的更改
        hasUnsavedChanges.value = true;
      }
    }

    if (importedItems.length > 0) {
      configStatusMessage.value = `WebUIConfig 导入成功：${importedItems.join('、')}`;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
      console.log('WebUIConfig数据导入成功:', webUIConfig);
    } else {
      alert('导入的WebUIConfig文件中没有找到有效的配置数据');
    }

  } catch (error) {
    console.error('WebUIConfig导入处理失败:', error);
    alert(`WebUIConfig导入失败: ${error.message}`);
  }
};

// 处理旧格式地图导入
const handleLegacyMapImport = (jsonData) => {
  if (!currentConfiguration.value.map) {
    alert('导入失败：当前没有可用的地图配置');
    return;
  }

  currentConfiguration.value.map.width = jsonData.width;
  currentConfiguration.value.map.height = jsonData.height;
  currentConfiguration.value.map.entities = jsonData.entities;
  
  // 如果JSON中有name字段，也更新名称
  if (typeof jsonData.name === 'string' && jsonData.name.trim().length > 0) {
    currentConfiguration.value.map.name = jsonData.name.trim();
  }
  
  configStatusMessage.value = `地图数据已导入 (宽度: ${jsonData.width}m, 高度: ${jsonData.height}m, 实体数量: ${jsonData.entities.length})`;
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
  
  console.log('地图JSON数据导入成功:', jsonData);
};

// 验证信标数据
const validateBeaconData = (beacon) => {
  return beacon && 
         typeof beacon === 'object' && 
         (beacon.uuid || beacon.macAddress) && 
         typeof beacon.x === 'number' && 
         typeof beacon.y === 'number';
};

// 切换编辑模式
const toggleEditMode = () => {
  // 如果正在创建新地图且要退出编辑模式，需要确认
  if (isCreatingNewMap.value && isEditMode.value) {
    const confirmed = confirm(`您正在创建新地图 "${tempMapName.value}"，退出编辑模式将丢失未保存的更改。是否确认退出？`);
    if (!confirmed) {
      return;
    }
    
    // 取消创建新地图
    isCreatingNewMap.value = false;
    tempMapName.value = '';
    
    // 重置到未选择地图的状态
    selectedMapIndex.value = '';
    currentConfiguration.value = {
      map: null,
      beacons: [],
      settings: { signalPropagationFactor: 2.5 }
    };
  }
  
  isEditMode.value = !isEditMode.value;
  
  if (isEditMode.value) {
    configStatusMessage.value = '已进入编辑模式 - 可以修改地图和信标配置';
  } else {
    configStatusMessage.value = '已退出编辑模式 - 地图和信标配置为只读状态';
  }
  
  setTimeout(() => { configStatusMessage.value = '' }, 3000);
};

// 删除当前地图
const deleteCurrentMap = async () => {
  if (isCreatingNewMap.value || !selectedMapConfig.value || availableMaps.value.length <= 1) {
    configStatusMessage.value = '无法删除地图：至少需要保留一个地图';
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
    return;
  }
  
  const mapName = selectedMapConfig.value.map?.name || `地图 ${selectedMapIndex.value + 1}`;
  const confirmed = confirm(`确定要删除地图 "${mapName}" 吗？\n\n此操作将删除该地图及其所有信标配置，且不可恢复。`);
  
  if (confirmed) {
    // 保存要删除的地图索引和信息，以便在保存失败时能够恢复
    const deletedMapIndex = selectedMapIndex.value;
    const deletedMapConfig = JSON.parse(JSON.stringify(availableMaps.value[deletedMapIndex]));
    
    // 从数组中移除地图
    availableMaps.value.splice(selectedMapIndex.value, 1);
    
    // 调整选中的地图索引
    if (selectedMapIndex.value >= availableMaps.value.length) {
      selectedMapIndex.value = availableMaps.value.length - 1;
    }
    
    // 更新当前配置以反映新的选择
    updateCurrentConfiguration();
    isEditMode.value = false; // 删除后退出编辑模式
    
    // 保存到服务器
    const success = await saveDashboardToServer();
    
    if (success) {
      configStatusMessage.value = `地图 "${mapName}" 已删除并同步到服务器`;
      setTimeout(() => { configStatusMessage.value = '' }, 3000);
    } else {
      // 保存失败，恢复删除的地图
      availableMaps.value.splice(deletedMapIndex, 0, deletedMapConfig);
      selectedMapIndex.value = deletedMapIndex;
      updateCurrentConfiguration();
      
      configStatusMessage.value = `删除地图失败：无法同步到服务器，已恢复地图 "${mapName}"`;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
    }
  }
};

// 取消所有更改
const cancelAllChanges = () => {
  if (isCreatingNewMap.value) {
    // 取消创建新地图
    const confirmed = confirm(`确定要取消创建新地图 "${tempMapName.value}" 吗？所有未保存的更改将丢失。`);
    if (!confirmed) return;
    
    // 重置创建状态
    isCreatingNewMap.value = false;
    tempMapName.value = '';
    isEditMode.value = false;
    hasUnsavedChanges.value = false;
    
    // 重置到未选择地图的状态
    selectedMapIndex.value = '';
    currentConfiguration.value = {
      map: null,
      beacons: [],
      settings: { signalPropagationFactor: 2.5 }
    };
    
    configStatusMessage.value = '已取消创建新地图';
  } else if (isEditMode.value || hasUnsavedChanges.value) {
    // 取消编辑或beacon更改
    const confirmed = confirm('确定要取消所有更改吗？所有未保存的更改将丢失。');
    if (!confirmed) return;
    
    // 重置编辑状态
    isEditMode.value = false;
    hasUnsavedChanges.value = false;
    
    // 重新加载当前地图配置
    if (selectedMapConfig.value && !selectedMapConfig.value.isNewMap) {
      updateCurrentConfiguration();
    }
    
    configStatusMessage.value = '已取消所有更改';
  }
  
  setTimeout(() => { configStatusMessage.value = '' }, 3000);
};

// 保存更改
const saveChanges = async () => {
  // 在保存前先记录状态，因为保存过程中状态会被修改
  const wasCreatingNewMap = isCreatingNewMap.value;
  const hadUnsavedChanges = hasUnsavedChanges.value;
  const mapNameForDisplay = currentConfiguration.value.map?.name || '';
  
  // 检查是否在创建新地图
  if (wasCreatingNewMap) {
    // 验证新地图配置
    const errors = validateMapConfig(currentConfiguration.value);
    if (errors.length > 0) {
      configStatusMessage.value = '保存失败：配置验证错误';
      console.error('地图配置验证失败:', errors);
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
      return;
    }
    
    // 再次检查名称唯一性（以防在编辑过程中有其他地图被创建）
    const nameExists = availableMaps.value.some(map => 
      map.map?.name?.toLowerCase() === tempMapName.value.toLowerCase()
    );
    
    if (nameExists) {
      configStatusMessage.value = `保存失败：地图名称 "${tempMapName.value}" 已存在`;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
      return;
    }
    
    // 添加到地图列表 - 这必须在saveDashboardToServer之前完成，这样服务器才能收到完整配置
    availableMaps.value.push({
      map: currentConfiguration.value.map,
      beacons: currentConfiguration.value.beacons,
      settings: currentConfiguration.value.settings,
      is_darwin: false
    });
    
    // 选择新创建的地图
    selectedMapIndex.value = availableMaps.value.length - 1;
    
    // 重置创建状态
    isCreatingNewMap.value = false;
    tempMapName.value = '';
    
    console.log('新地图已添加到配置列表，准备保存到服务器:', currentConfiguration.value);
  } else if (selectedMapConfig.value && !selectedMapConfig.value.isNewMap) {
    // 更新现有地图配置 - 这也必须在saveDashboardToServer之前完成
    const currentIndex = selectedMapIndex.value;
    if (currentIndex >= 0 && currentIndex < availableMaps.value.length) {
      availableMaps.value[currentIndex] = {
        map: currentConfiguration.value.map,
        beacons: currentConfiguration.value.beacons,
        settings: currentConfiguration.value.settings,
        is_darwin: availableMaps.value[currentIndex].is_darwin || false
      };
      console.log('地图配置已更新，准备保存到服务器:', availableMaps.value[currentIndex]);
    }
  }
  
  // 调用后端保存完整的配置
  const success = await saveDashboardToServer();
  
  if (success) {
    // 保存成功后退出编辑模式并清除未保存标记
    isEditMode.value = false;
    hasUnsavedChanges.value = false;
    
    if (wasCreatingNewMap) {
      configStatusMessage.value = `新地图 "${mapNameForDisplay}" 已创建并保存到服务器`;
    } else if (hadUnsavedChanges) {
      configStatusMessage.value = '配置更改已保存到服务器';
    } else {
      configStatusMessage.value = '更改已保存到服务器并退出编辑模式';
    }
    
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
  } else {
    // 保存失败，如果是新建地图，需要回滚操作
    if (wasCreatingNewMap) {
      // 回滚：移除刚添加的地图
      availableMaps.value.pop();
      
      // 恢复创建状态
      isCreatingNewMap.value = true;
      tempMapName.value = mapNameForDisplay;
      selectedMapIndex.value = '';
      
      console.log('保存失败，已回滚新地图创建操作');
    }
  }
};

// 同步当前配置到主地图数组
const syncCurrentConfigurationToMaps = () => {
  if (isEditMode.value && selectedMapConfig.value && !selectedMapConfig.value.isNewMap) {
    const currentIndex = selectedMapIndex.value;
    if (currentIndex >= 0 && currentIndex < availableMaps.value.length) {
      // 实时同步当前编辑的配置到主数组
      availableMaps.value[currentIndex] = {
        map: JSON.parse(JSON.stringify(currentConfiguration.value.map)),
        beacons: JSON.parse(JSON.stringify(currentConfiguration.value.beacons)),
        settings: JSON.parse(JSON.stringify(currentConfiguration.value.settings)),
        is_darwin: availableMaps.value[currentIndex].is_darwin || false
      };
      
      console.log('配置已同步到主数组:', availableMaps.value[currentIndex]);
    }
  }
};

// --- Event Handlers from Child Components ---

const handleBeaconsUpdated = (newBeacons) => {
  currentConfiguration.value.beacons = JSON.parse(JSON.stringify(newBeacons));
  console.log("ConfigurationSuiteView: Beacons updated", currentConfiguration.value.beacons);
  
  // 标记有未保存的更改
  hasUnsavedChanges.value = true;
  
  // 同步到主地图数组
  syncCurrentConfigurationToMaps();
};

const handleBeaconSelectedForPlacement = (beacon) => {
  selectedBeaconForPlacement.value = beacon;
  if (beacon) {
    configStatusMessage.value = `信标 "${beacon.displayName}" 已选定。请向下滑动到地图预览区域，然后在地图上点击以放置该信标。`;
    setTimeout(() => { configStatusMessage.value = '' }, 7000);
    
    // 滚动到地图预览位置
    nextTick(() => {
      if (mapPreviewCardRef.value) {
        mapPreviewCardRef.value.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }
    });
  }
};

const updateConfigFromMapEditor = (configData) => {
  console.log("[ConfigurationSuiteView] updateConfigFromMapEditor function called with:", JSON.parse(JSON.stringify(configData)));
  if (configData && configData.map && Array.isArray(configData.beacons) && typeof configData.settings === 'object') {
    // Update properties individually for potentially better reactivity propagation
    currentConfiguration.value.map = JSON.parse(JSON.stringify(configData.map));
    currentConfiguration.value.beacons = JSON.parse(JSON.stringify(configData.beacons));
    currentConfiguration.value.settings = JSON.parse(JSON.stringify(configData.settings));
    
    console.log("[ConfigurationSuiteView] Updated currentConfiguration.value properties via updateConfigFromMapEditor. New map name:", currentConfiguration.value.map ? currentConfiguration.value.map.name : "null");
    selectedBeaconForPlacement.value = null;

    // 同步到主地图数组
    syncCurrentConfigurationToMaps();

    nextTick(() => {
      if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
      if (generalSettingsTabRef.value?.loadSettings) {
        generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
    });

    configStatusMessage.value = '配置已成功从地图编辑器加载并应用 (via prop function).';
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  } else {
    console.error("[ConfigurationSuiteView] updateConfigFromMapEditor: Invalid config.", configData);
    configStatusMessage.value = '错误：从地图编辑器加载的配置数据格式无效 (via prop function)。';
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  }
};

const handleSettingsUpdated = (newSettings) => {
  currentConfiguration.value.settings = JSON.parse(JSON.stringify(newSettings));
  console.log("ConfigurationSuiteView: Settings updated", currentConfiguration.value.settings);
  
  // 标记有未保存的更改
  hasUnsavedChanges.value = true;
  
  // 同步到主地图数组
  syncCurrentConfigurationToMaps();
};

// --- Global Actions ---

const triggerImportFile = () => {
  selectedBeaconForPlacement.value = null; // Clear any pending placement
  importFileRef.value.click(); 
};

const handleImportFullConfigurationFile = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  isLoadingConfig.value = true;
  configStatusMessage.value = '正在导入配置文件...';

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const jsonData = JSON.parse(e.target.result);
      processAndApplyFullConfig(jsonData, '配置文件已成功从本地文件导入并应用。');
    } catch (error) {
      console.error("Configuration import error:", error);
      configStatusMessage.value = `导入JSON文件失败: ${error.message}`;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
    }
    isLoadingConfig.value = false;
  };
  reader.onerror = () => {
      configStatusMessage.value = '读取文件时发生错误。';
      isLoadingConfig.value = false;
      setTimeout(() => { configStatusMessage.value = '' }, 5000);
  };
  reader.readAsText(file);
  event.target.value = null; // Reset file input
};

const exportFullConfiguration = () => {
  if (!currentConfiguration.value.map) {
    alert('没有配置数据可导出。请先导入或创建配置。');
    return;
  }
  try {
    const jsonString = JSON.stringify(currentConfiguration.value, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      alert('完整配置已复制到剪贴板。');
    }).catch(err => {
      console.error('复制到剪贴板失败: ', err);
      alert('复制失败。请查看控制台，并可手动复制。' + jsonString);
    });
  } catch (e) {
    alert('导出配置失败: JSON序列化错误。');
    console.error('JSON序列化错误:', e);
  }
};




// Lifecycle Hooks
onMounted(async () => {
  console.log("[ConfigurationSuiteView] Component mounted, loading configuration data...");
  
  // 设置默认值
  activeTab.value = 'map';
  
  // 并行加载基础数据
  await Promise.all([
    loadDashboardConfigurationData(),
    loadTrackersData(), // 加载tracker状态数据用于统计
    loadTrackerList()   // 加载tracker配置列表
  ]);
});

// 监听主标签变化，切换到tracker标签时加载数据
watch(() => activeMainTab.value, async (newTab) => {
  if (newTab === 'tracker') {
    await loadTrackerList();
    await loadTrackersData(); // 刷新tracker状态
  }
});

// 定期刷新tracker数据（用于实时统计）
let trackerDataInterval;
onMounted(() => {
  trackerDataInterval = setInterval(loadTrackersData, 30000); // 每30秒刷新
});

// 清理定时器
onUnmounted(() => {
  if (trackerDataInterval) {
    clearInterval(trackerDataInterval);
  }
});

// Watchers to potentially help propagate changes if props aren't deep enough by default
// or if child components need explicit reload calls.

watch(() => currentConfiguration.value.beacons, (newBeacons) => {
    // This watcher helps if BeaconManagerTab needs to be explicitly told about external beacon changes
    // that didn't originate from itself.
    if (beaconManagerTabRef.value && beaconManagerTabRef.value.loadConfiguredBeacons) {
        // beaconManagerTabRef.value.loadConfiguredBeacons(newBeacons); // Already handled by initial-beacons prop?
    }
    // MapEditorTab receives beacons as a prop, so it should update.
}, { deep: true });


watch(() => currentConfiguration.value.settings, (newSettings) => {
    if (generalSettingsTabRef.value && generalSettingsTabRef.value.loadSettings) {
        // generalSettingsTabRef.value.loadSettings(newSettings); // Already handled by initial-settings prop?
    }
}, { deep: true });


// Unified function to apply a loaded configuration (from file import or server)
const applyFullConfiguration = (configData) => {
  console.log("[ConfigurationSuiteView] applyFullConfiguration called with:", JSON.parse(JSON.stringify(configData)));
  if (configData && configData.map && Array.isArray(configData.beacons) && configData.settings) {
    currentConfiguration.value.map = JSON.parse(JSON.stringify(configData.map));
    currentConfiguration.value.beacons = JSON.parse(JSON.stringify(configData.beacons));
    currentConfiguration.value.settings = JSON.parse(JSON.stringify(configData.settings));
    
    console.log('[ConfigurationSuiteView] applyFullConfiguration: currentConfiguration.map updated. Name:', 
                currentConfiguration.value.map ? currentConfiguration.value.map.name : 'null',
                'Width:', currentConfiguration.value.map ? currentConfiguration.value.map.width : 'N/A');

    selectedBeaconForPlacement.value = null;

    nextTick(() => {
      if (beaconManagerTabRef.value?.loadConfiguredBeacons) {
        beaconManagerTabRef.value.loadConfiguredBeacons(currentConfiguration.value.beacons);
      }
      if (mapEditorTabRef.value?.loadConfiguration) {
        mapEditorTabRef.value.loadConfiguration(currentConfiguration.value); 
      }
      if (generalSettingsTabRef.value?.loadSettings) {
        generalSettingsTabRef.value.loadSettings(currentConfiguration.value.settings);
      }
    });
    console.log("ConfigurationSuiteView: Full configuration applied.", currentConfiguration.value);
    return true;
  } else {
    console.error("ConfigurationSuiteView: Attempted to apply invalid full configuration structure.", configData);
    return false;
  }
};

// Renamed handleMapLoaded to reflect its primary use (processing config for application)
// This is called by file upload in MapEditorTab or by global file import, or by loading from server.
const processAndApplyFullConfig = (loadedConfig, sourceMessage = '配置已成功加载并应用。') => {
  if (applyFullConfiguration(loadedConfig)) {
    configStatusMessage.value = sourceMessage;
  } else {
    configStatusMessage.value = '错误：加载的配置数据格式无效。';
    // Optionally, reset to a known good state or initial state
    // currentConfiguration.value = initialConfiguration();
    // applyFullConfiguration(currentConfiguration.value); // to update children
  }
  // Clear message after a few seconds
  setTimeout(() => { configStatusMessage.value = '' }, 5000);
};

const handleBeaconCoordinatesUpdated = (updatedBeacon) => {
  if (!updatedBeacon || typeof updatedBeacon.x !== 'number' || typeof updatedBeacon.y !== 'number') {
    console.warn("ConfigurationSuiteView: Invalid beacon data received for coordinate update.", updatedBeacon);
    return;
  }

  console.log("--- [CSV] Attempting to Update Beacon Coordinates --- ");
  console.log("[CSV] TARGET Beacon (from map click):", JSON.parse(JSON.stringify(updatedBeacon)));
  
  const currentBeaconList = currentConfiguration.value.beacons;
  console.log("[CSV] SEARCH LIST (currentConfiguration.beacons at time of search):", JSON.parse(JSON.stringify(currentBeaconList)));

  if (!currentBeaconList || currentBeaconList.length === 0) {
    console.warn("[CSV] The SEARCH LIST (currentConfiguration.value.beacons) is EMPTY. Cannot find the target beacon.");
  }

  const beaconToUpdateUUID = updatedBeacon.uuid ? String(updatedBeacon.uuid).toUpperCase() : null;
  const beaconToUpdateMajor = updatedBeacon.major;
  const beaconToUpdateMinor = updatedBeacon.minor;
  // const beaconToUpdateDeviceId = updatedBeacon.deviceId || updatedBeacon.macAddress; // For reference if needed later

  const beaconIndex = currentConfiguration.value.beacons.findIndex((b, index) => {
    console.log(`[CSV - findIndex] Comparing with beacon at index ${index} in list:`, JSON.parse(JSON.stringify(b)));
    const listBeaconUUID = b.uuid ? String(b.uuid).toUpperCase() : null;
    
    console.log(`  Target (from map click): UUID=${beaconToUpdateUUID}, Major=${beaconToUpdateMajor}, Minor=${beaconToUpdateMinor}`);
    console.log(`  List item (index ${index}):   UUID=${listBeaconUUID}, Major=${b.major}, Minor=${b.minor}`);

    const canCompareByFullIBProperties = 
      beaconToUpdateUUID && typeof beaconToUpdateMajor === 'number' && typeof beaconToUpdateMinor === 'number' &&
      listBeaconUUID && typeof b.major === 'number' && typeof b.minor === 'number';

    console.log(`  Can compare by full iBeacon properties? ${canCompareByFullIBProperties}`);

    if (canCompareByFullIBProperties) {
      const isMatch = listBeaconUUID === beaconToUpdateUUID &&
                      b.major === beaconToUpdateMajor &&
                      b.minor === beaconToUpdateMinor;
      console.log(`  Full iBeacon properties match result: ${isMatch}`);
      return isMatch;
    }
    
    console.log('  Comparison by full iBeacon properties skipped (incomplete data on one or both sides).');
    return false;
  });

  console.log(`[CSV] Result of findIndex on SEARCH LIST: ${beaconIndex}`);
  console.log("--- [CSV] Finished Attempt to Update Beacon Coordinates --- ");

  if (beaconIndex !== -1) {
    currentConfiguration.value.beacons[beaconIndex].x = updatedBeacon.x;
    currentConfiguration.value.beacons[beaconIndex].y = updatedBeacon.y;
    console.log(`ConfigurationSuiteView: Beacon '${currentConfiguration.value.beacons[beaconIndex].displayName || updatedBeacon.deviceId || updatedBeacon.uuid}' coordinates updated to (X: ${updatedBeacon.x}, Y: ${updatedBeacon.y}).`);
    
    // 同时更新BeaconManagerTab中的编辑模态框坐标
    if (beaconManagerTabRef.value?.updateCoordinatesForBeaconInModal) {
      beaconManagerTabRef.value.updateCoordinatesForBeaconInModal(
        updatedBeacon.uuid, 
        updatedBeacon.major, 
        updatedBeacon.minor, 
        updatedBeacon.x, 
        updatedBeacon.y
      );
    }
    
    selectedBeaconForPlacement.value = null; 
    // 不自动切换标签页，让用户看到更新结果
    // activeTab.value = 'beacons'; 
    configStatusMessage.value = `信标 '${currentConfiguration.value.beacons[beaconIndex].displayName || updatedBeacon.deviceId || updatedBeacon.uuid}' 位置已更新。`;
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  } else {
    console.warn(
        "[CSV] Beacon to update coordinates for NOT FOUND in the list.",
        "Target Beacon (from map click):", JSON.parse(JSON.stringify(updatedBeacon)),
        "Searched List (currentConfiguration.beacons at time of search):", JSON.parse(JSON.stringify(currentConfiguration.value.beacons))
    );
    configStatusMessage.value = "错误：尝试更新位置的信标未找到。请检查控制台中的 '[CSV - findIndex]' 日志以获取详细比较步骤。";
    setTimeout(() => { configStatusMessage.value = '' }, 7000); // Slightly longer timeout for this more detailed error message
  }
};

const handleRequestBeaconSelection = () => {
  alert("请先从'信标管理'标签页选择一个信标，然后才能在地图上放置。");
  activeTab.value = 'beacons';
};

// 处理地图预览点击事件 - 修复坐标转换
const handleMapPreviewClick = (event) => {
  // 只有在信标选择模式下才处理点击
  if (!selectedBeaconForPlacement.value) {
    // 静默忽略，不显示任何提示
    return;
  }

  if (!currentConfiguration.value.map) {
    console.log('❌ 没有地图配置，退出');
    return;
  }

  console.log('=== 地图预览点击开始 ===');
  console.log('selectedBeaconForPlacement:', selectedBeaconForPlacement.value);

  const canvas = mapPreviewCanvasRef.value;
  if (!canvas) {
    console.log('❌ Canvas不存在，退出');
    return;
  }

  // 使用与drawMapPreview相同的坐标转换逻辑
  const rect = canvas.getBoundingClientRect();
  const cssPixelX = event.clientX - rect.left;
  const cssPixelY = event.clientY - rect.top;

  // 转换为canvas内部坐标
  const bufferPixelX = cssPixelX * (canvas.width / rect.width);
  const bufferPixelY = cssPixelY * (canvas.height / rect.height);

  const map = currentConfiguration.value.map;
  const mapWidthMeters = map.width || 50;
  const mapHeightMeters = map.height || 50;
  const entities = map.entities || [];

  // 计算实际地图数据边界（与drawMapPreview中的逻辑完全一致）
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  if (entities && entities.length > 0) {
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
  } else {
    // 如果没有entities，使用地图的尺寸作为边界
    minX = 0;
    minY = 0;
    maxX = mapWidthMeters || 50;
    maxY = mapHeightMeters || 50;
  }

  // 计算缩放比例和偏移量
  const contentAreaWidth = canvas.width * 0.9;
  const contentAreaHeight = canvas.height * 0.9;
  
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  
  let currentScale = 1;
  if (dataWidth > 0 && dataHeight > 0) {
    const scaleX = contentAreaWidth / dataWidth;
    const scaleY = contentAreaHeight / dataHeight;
    currentScale = Math.min(scaleX, scaleY);
  }

  const renderedMapWidth = dataWidth * currentScale;
  const renderedMapHeight = dataHeight * currentScale;
  const offsetX = (canvas.width - renderedMapWidth) / 2;
  const offsetY = (canvas.height - renderedMapHeight) / 2;

  // 检查点击是否在地图区域内
  if (bufferPixelX >= offsetX && bufferPixelX <= offsetX + renderedMapWidth &&
      bufferPixelY >= offsetY && bufferPixelY <= offsetY + renderedMapHeight) {
    
    // 转换为地图坐标（使用数据边界归一化，注意Y轴翻转）
    const relativeX = ((bufferPixelX - offsetX) / currentScale) + minX;
    const relativeY = ((dataHeight - ((bufferPixelY - offsetY) / currentScale)) + minY);

    const mapX = parseFloat(relativeX.toFixed(2));
    const mapY = parseFloat(relativeY.toFixed(2));

    console.log(`✅ 计算得到地图坐标: (${mapX}, ${mapY})`);

    // 直接调用BeaconManagerTab的更新函数
    if (beaconManagerTabRef.value?.updateCoordinatesForBeaconInModal) {
      console.log('✅ 调用BeaconManagerTab更新坐标');
      beaconManagerTabRef.value.updateCoordinatesForBeaconInModal(
        selectedBeaconForPlacement.value.uuid,
        selectedBeaconForPlacement.value.major,
        selectedBeaconForPlacement.value.minor,
        mapX,
        mapY
      );
    } else {
      console.log('❌ BeaconManagerTab的更新函数不存在');
    }

    // 清除选中状态
    selectedBeaconForPlacement.value = null;
    console.log('=== 地图预览点击结束 ===');
  } else {
    console.log('❌ 点击位置在地图区域外');
    alert('请点击地图区域内的位置');
  }
};

// 绘制地图预览 - 修复偏移问题，参考MapPreview.vue的实现
const drawMapPreview = () => {
  if (!mapPreviewCanvasRef.value || !currentConfiguration.value.map) {
    return;
  }

  const canvas = mapPreviewCanvasRef.value;
  const ctx = canvas.getContext('2d');
  const map = currentConfiguration.value.map;
  const beacons = currentConfiguration.value.beacons || [];

  console.log('[MapPreview] Drawing map:', map.name, 'with', beacons.length, 'beacons');

  if (!map) {
    console.warn("[MapPreview] Attempted to drawMap without valid config.map data.");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }

  const { width: mapWidthMeters, height: mapHeightMeters, entities } = map;

  // 确保画布内部绘制缓冲区与尺寸匹配
  ctx.canvas.width = canvas.width;
  ctx.canvas.height = canvas.height;

  // 计算实际地图数据边界（与MapPreview.vue相同的逻辑）
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  if (entities && entities.length > 0) {
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
  } else {
    // 如果没有entities，使用地图的尺寸作为边界
    minX = 0;
    minY = 0;
    maxX = mapWidthMeters || 50;
    maxY = mapHeightMeters || 50;
  }

  // 计算90%内容区域的尺寸
  const contentAreaWidth = canvas.width * 0.9;
  const contentAreaHeight = canvas.height * 0.9;

  // 使用实际数据边界计算缩放比例
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  
  let currentScale;
  if (dataWidth <= 0 || dataHeight <= 0) {
    currentScale = 1;
  } else {
    const scaleX = contentAreaWidth / dataWidth;
    const scaleY = contentAreaHeight / dataHeight;
    currentScale = Math.min(scaleX, scaleY);
  }
  
  if (currentScale <= 0) {
    currentScale = 1;
  }

  // 计算缩放后地图内容的实际像素尺寸
  const renderedMapWidth = dataWidth * currentScale;
  const renderedMapHeight = dataHeight * currentScale;

  // 计算偏移量以在画布内居中显示缩放后的地图内容
  const offsetX = (canvas.width - renderedMapWidth) / 2;
  const offsetY = (canvas.height - renderedMapHeight) / 2;

  // 清空画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // --- 绘制地图边框 ---
  ctx.strokeStyle = '#cccccc';
  ctx.lineWidth = 2;
  ctx.strokeRect(offsetX, offsetY, renderedMapWidth, renderedMapHeight);

  // --- 绘制地图实体（如果存在） ---
  if (entities && Array.isArray(entities)) {
    ctx.save();
    // 平移到居中内容框的左下角，然后翻转Y轴
    ctx.translate(offsetX, canvas.height - offsetY);
    ctx.scale(1, -1);

    entities.forEach(entity => {
      if (entity.type === 'polyline' && entity.points && entity.points.length > 0) {
        ctx.beginPath();
        ctx.strokeStyle = entity.color || '#333333';
        ctx.lineWidth = entity.lineWidth || 1;

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
    });

    ctx.restore(); // 恢复平移和翻转
  }

  // --- 绘制信标 ---
  ctx.save();
  // 为信标绘制设置坐标变换
  ctx.translate(offsetX, canvas.height - offsetY);
  ctx.scale(1, -1);
  
  beacons.forEach(beacon => {
    if (typeof beacon.x === 'number' && typeof beacon.y === 'number') {
      // 使用数据边界归一化的坐标（修复偏移问题）
      const beaconX = (beacon.x - minX) * currentScale;
      const beaconY = (beacon.y - minY) * currentScale;
      
      // 检查是否为选中要放置的信标
      const isSelectedForPlacement = selectedBeaconForPlacement.value && 
        selectedBeaconForPlacement.value.uuid === beacon.uuid &&
        selectedBeaconForPlacement.value.major === beacon.major &&
        selectedBeaconForPlacement.value.minor === beacon.minor;
      
      ctx.beginPath();
      ctx.arc(beaconX, beaconY, isSelectedForPlacement ? 7 : 5, 0, 2 * Math.PI);
      ctx.fillStyle = isSelectedForPlacement ? 'lime' : 'orange';
      ctx.fill();
      
      if (isSelectedForPlacement) {
        ctx.strokeStyle = 'darkgreen';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      
      ctx.fillStyle = 'black';
      ctx.font = '10px Arial';
      
      // 在翻转的上下文中绘制直立的文本
      ctx.save();
      ctx.translate(beaconX, beaconY);
      ctx.scale(1, -1); // 翻转文本
      ctx.fillText(beacon.displayName || `B(${beacon.major},${beacon.minor})`, 8, 4);
      ctx.restore();
    }
  });

  ctx.restore(); // 恢复原始上下文状态
};

// --- Tracker配置管理函数 ---

// 添加Tracker到列表
const addTrackerToList = () => {
  const trimmedEui = newTrackerEui.value.trim().toUpperCase();
  if (!trimmedEui) {
    alert('请输入有效的Tracker EUI');
    return;
  }
  
  // 检查是否已存在
  if (allowTrackerList.value.includes(trimmedEui)) {
    alert('此Tracker已存在于列表中');
    return;
  }
  
  // 简单的EUI格式验证（16位十六进制）
  if (!/^[0-9A-F]{16}$/.test(trimmedEui)) {
    alert('EUI格式不正确，应为16位十六进制字符');
    return;
  }
  
  allowTrackerList.value.push(trimmedEui);
  newTrackerEui.value = '';
};

// 从列表中移除Tracker
const removeTrackerFromList = (index) => {
  if (index >= 0 && index < allowTrackerList.value.length) {
    const eui = allowTrackerList.value[index];
    if (confirm(`确定要移除Tracker "${eui}" 吗？`)) {
      allowTrackerList.value.splice(index, 1);
    }
  }
};

// 保存Tracker列表到服务器
const saveTrackerList = async () => {
  try {
    isSavingTrackers.value = true;
    await saveAllowTrackerList(allowTrackerList.value);
    configStatusMessage.value = 'Tracker列表已成功保存';
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
  } catch (error) {
    console.error('保存Tracker列表失败:', error);
    configStatusMessage.value = `保存失败: ${error.message}`;
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  } finally {
    isSavingTrackers.value = false;
  }
};

// 从服务器加载Tracker列表
const loadTrackerList = async () => {
  try {
    const response = await loadAllowTrackerList();
    allowTrackerList.value = response.tracker_list || [];
    configStatusMessage.value = `已加载 ${allowTrackerList.value.length} 个Tracker配置`;
    setTimeout(() => { configStatusMessage.value = '' }, 3000);
  } catch (error) {
    console.error('加载Tracker列表失败:', error);
    configStatusMessage.value = `加载失败: ${error.message}`;
    setTimeout(() => { configStatusMessage.value = '' }, 5000);
  }
};


// 加载tracker状态数据
const loadTrackersData = async () => {
  try {
    const data = await loadTrackers();
    // 处理返回的数据格式（可能是对象或数组）
    if (Array.isArray(data)) {
      allTrackers.value = data;
      trackersData.value = {};
    } else if (data && typeof data === 'object') {
      // 如果是对象格式，转换为数组用于统计
      allTrackers.value = Object.values(data);
      trackersData.value = data;
    } else {
      allTrackers.value = [];
      trackersData.value = {};
    }
  } catch (error) {
    console.error('加载tracker数据失败:', error);
    allTrackers.value = [];
    trackersData.value = {};
  }
};

</script>

<style scoped>
.page-container {
  padding: 1.5rem; /* Consistent padding with global .main-content-global if used */
  width: 100%;
  max-width: 1200px; /* Optional: constrain max width */
  margin: 0 auto; /* Center if max-width is used */
  box-sizing: border-box;
}

.page-title {
  font-size: 1.8rem; /* Larger page title */
  color: var(--primary-color-dark);
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
}

.info-banner {
  /* Uses global .status-display.info now */
  text-align: center;
}

.global-actions,
.tab-content,
.positioning-mode-switcher {
  /* Now uses global .card styling by having class="card" */
  /* Removed specific background, border, padding from here if handled by .card */
  margin-bottom: 1.5rem;
}

.card-content {
 padding: 1rem; /* Add padding inside cards if not directly on child elements */
}

.global-actions .card-content button {
  margin-right: 10px;
  margin-bottom: 5px; /* Spacing for buttons if they wrap */
  /* Button styling now comes from global button classes */
}

.tabs-navigation {
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.tabs-navigation button {
  padding: 0.6rem 1rem;
  margin-right: 0.5rem;
  border: 1px solid transparent; /* Cleaner look */
  border-bottom: none;
  background-color: transparent; /* Use theme colors */
  color: var(--primary-color);
  cursor: pointer;
  border-radius: var(--border-radius) var(--border-radius) 0 0; /* Rounded top corners */
  font-size: 1rem;
  font-weight: 500;
}

.tabs-navigation button.active {
  background-color: var(--primary-color);
  color: white;
  border-color: var(--primary-color-dark);
}
.tabs-navigation button:hover:not(.active) {
  background-color: #e7f3ff; /* Light hover for non-active tabs */
  color: var(--primary-color-dark);
}

/* Ensure .tab-content has some top margin if .tabs-navigation border is removed or styled differently */
/* .tab-content {
  margin-top: 0; 
}*/


select {
  /* Uses global select style from style.css */
  padding: 0.5rem;
  font-size: 0.95rem;
}

/* 统计项样式 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.stat-number {
  font-size: 2.5rem;
  font-weight: bold;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  opacity: 0.9;
}

/* 地图选择器样式 */
.map-selector {
  margin-bottom: 1.5rem;
}

.map-selector .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.export-config-btn {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-width: 140px;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

.export-config-btn:hover {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.export-config-btn i {
  font-size: 0.9rem;
}

.refresh-config-btn {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-width: 140px;
  box-shadow: 0 2px 4px rgba(17, 153, 142, 0.3);
}

.refresh-config-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #0f8578 0%, #32d96f 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(17, 153, 142, 0.4);
}

.refresh-config-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 0 2px 4px rgba(17, 153, 142, 0.2);
}

.refresh-config-btn i {
  font-size: 0.9rem;
}

.no-maps-message {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 8px;
  color: #6c757d;
}

.no-maps-message .hint {
  font-size: 0.9rem;
  margin-top: 0.5rem;
  opacity: 0.8;
}

/* 下拉选择器样式 */
.map-selector-dropdown {
  width: 100%;
}

.dropdown-wrapper {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.dropdown-label {
  font-weight: 600;
  color: #495057;
  white-space: nowrap;
  font-size: 1rem;
}

.map-dropdown {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  background: white;
  font-size: 1rem;
  color: #495057;
  cursor: pointer;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.map-dropdown:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.map-dropdown:hover {
  border-color: #007bff;
}

/* 地图管理按钮样式 */
.map-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: 1rem;
}

.action-button {
  padding: 0.6rem 1rem;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  background: white;
  color: #495057;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}

.action-button:hover:not(:disabled) {
  border-color: #007bff;
  color: #007bff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 123, 255, 0.1);
}

.action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.create-button:hover:not(:disabled) {
  border-color: #28a745;
  color: #28a745;
  box-shadow: 0 2px 4px rgba(40, 167, 69, 0.1);
}

.edit-button.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.edit-button.active:hover {
  background: #0056b3;
  border-color: #0056b3;
}

.delete-button:hover:not(:disabled) {
  border-color: #dc3545;
  color: #dc3545;
  box-shadow: 0 2px 4px rgba(220, 53, 69, 0.1);
}

.save-button {
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  border: 1px solid transparent;
}

.save-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
}

.cancel-button {
  background: #6c757d;
  color: white;
  border: 1px solid #6c757d;
}

.cancel-button:hover:not(:disabled) {
  background: #5a6268;
  border-color: #545b62;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(108, 117, 125, 0.3);
}

/* 创建新地图模式横幅 */
.create-mode-banner {
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
}

.create-mode-banner i {
  font-size: 1.2rem;
  color: white;
}

.create-mode-banner span {
  flex: 1;
  font-weight: 500;
}


/* 编辑模式横幅 */
.edit-mode-banner {
  background: linear-gradient(135deg, #ffc107 0%, #ff8c00 100%);
  color: #495057;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 2px 4px rgba(255, 193, 7, 0.2);
}

.edit-mode-banner i {
  font-size: 1.2rem;
}

.edit-mode-banner span {
  flex: 1;
  font-weight: 500;
}

/* 未保存更改横幅 */
.unsaved-changes-banner {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 2px 4px rgba(243, 156, 18, 0.3);
}

.unsaved-changes-banner i {
  font-size: 1.2rem;
  color: white;
}

.unsaved-changes-banner span {
  flex: 1;
  font-weight: 500;
}


/* Map标签页样式 */
.map-tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 共享地图预览样式 */
.shared-map-preview {
  margin-top: 1.5rem;
}

.beacon-summary {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #e7f3ff 0%, #f0f8ff 100%);
  border-radius: 6px;
  border-left: 4px solid #007bff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.beacon-summary p {
  margin: 0;
  color: #495057;
  font-size: 0.9rem;
  font-weight: 500;
}

.beacon-summary i {
  color: #007bff;
  margin-right: 0.5rem;
}

.map-basic-info {
  margin-bottom: 0;
}

.map-basic-info .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.import-json-btn {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
}

.import-json-btn:hover {
  background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.4);
}

.import-json-btn i {
  font-size: 0.9rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-item label {
  font-weight: 600;
  color: var(--secondary-color);
  font-size: 0.9rem;
}

.info-value {
  font-size: 1rem;
  color: var(--text-color);
  font-weight: 500;
}

.info-value.readonly {
  color: var(--secondary-color);
  font-style: italic;
}

/* 编辑模式样式 */
.edit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.edit-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.edit-item label {
  font-weight: 600;
  color: var(--secondary-color);
  font-size: 0.9rem;
}

.map-info-input {
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
  background: white;
}

.map-info-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.error-message-small {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.25rem;
  padding: 0.4rem 0.6rem;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  color: #dc2626;
  font-size: 0.8rem;
}

.error-message-small i {
  color: #dc2626;
  font-size: 0.9rem;
}

.map-preview {
  margin-bottom: 0;
}

.map-canvas-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: #f8f9fa;
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
}

.map-preview-canvas {
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.map-preview-canvas.clickable {
  cursor: crosshair;
  border-color: #28a745;
  box-shadow: 0 0 0 2px rgba(40, 167, 69, 0.2);
}

.shared-map-preview .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.placement-hint {
  color: #28a745;
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.placement-hint i {
  color: #28a745;
}

/* 未选择地图时的提示信息 */
.no-map-selected-message {
  margin-bottom: 1.5rem;
}

.no-map-selected-message .empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--secondary-color);
}

.no-map-selected-message .empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.6;
  color: var(--primary-color);
}

.no-map-selected-message .empty-state h3 {
  margin: 0 0 0.5rem 0;
  color: var(--text-color);
  font-size: 1.2rem;
}

.no-map-selected-message .empty-state p {
  margin: 0;
  font-size: 0.95rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .unified-stats-overview .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
  
  .unified-stats-overview .stat-item {
    padding: 0.75rem 0.5rem;
  }
  
  .config-tabs-navigation {
    gap: 0.25rem;
  }
  
  .config-tab-button {
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
  }
  
  .config-tab-button i {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .unified-stats-overview .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .config-tabs-navigation {
    flex-direction: column;
    align-items: center;
  }
  
  .config-tab-button {
    width: 100%;
    max-width: 300px;
    justify-content: center;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .dropdown-wrapper {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .dropdown-label {
    white-space: normal;
  }
  
  .map-dropdown {
    width: 100%;
  }
  
  .map-actions {
    margin-left: 0;
    flex-wrap: wrap;
    width: 100%;
  }
  
  .action-button {
    flex: 1;
    justify-content: center;
    min-width: 0;
    font-size: 0.85rem;
    padding: 0.5rem 0.75rem;
  }
  
  .edit-mode-banner, .create-mode-banner, .unsaved-changes-banner {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
    text-align: left;
  }
}

/* 创建地图模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 480px;
  padding: 2rem;
  position: relative;
  animation: modalSlideIn 0.3s ease-out;
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

.modal-content h4 {
  margin: 0 0 1.5rem 0;
  color: #2c3e50;
  font-size: 1.25rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modal-content h4 i {
  color: #667eea;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
}

.map-name-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.map-name-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input-help {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
}

.char-counter {
  font-size: 0.8rem;
  color: #6b7280;
  font-weight: 500;
}

.char-counter.warning {
  color: #f59e0b;
}

.error-message {
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-message i {
  color: #dc2626;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 100px;
  justify-content: center;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

/* Override global button disabled style if needed for specific contexts, */
/* or rely on global button:disabled */
/* .global-actions button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
} */

/* 统一概览样式 */
.unified-stats-overview {
  margin-bottom: 2rem;
}

.unified-stats-overview .stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.unified-stats-overview .stat-item.map-beacon-stats {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.unified-stats-overview .stat-item.tracker-stats {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
}

/* 配置项切换标签样式 */
.config-tabs-navigation {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 0.5rem;
  justify-content: center;
}

.config-tab-button {
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 8px 8px 0 0;
  background: #f8f9fa;
  color: #495057;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  position: relative;
}

.config-tab-button:hover:not(.active) {
  background: #e9ecef;
  color: #495057;
  transform: translateY(-2px);
}

.config-tab-button.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transform: translateY(-2px);
}

.config-tab-button i {
  font-size: 1.1rem;
}

.main-tab-content {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Tracker配置样式 */
.tracker-config-section {
  margin-bottom: 1.5rem;
}

.config-section {
  margin-bottom: 2rem;
}

.config-section:last-child {
  margin-bottom: 0;
}

.config-section h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary-color-dark);
  font-size: 1.2rem;
  font-weight: 600;
}

.section-description {
  margin: 0 0 1rem 0;
  color: #6c757d;
  font-size: 0.9rem;
  line-height: 1.4;
}

.tracker-list-management {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
}

.input-group {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tracker-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 0.9rem;
  font-family: monospace;
  transition: border-color 0.3s ease;
}

.tracker-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.add-button {
  padding: 0.75rem 1.2rem;
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}

.add-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
}

.add-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.tracker-list h4 {
  margin: 0 0 1rem 0;
  color: #495057;
  font-size: 1rem;
}

.tracker-items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tracker-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.tracker-item:hover {
  border-color: #adb5bd;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.tracker-eui {
  font-family: monospace;
  font-size: 0.9rem;
  color: #495057;
  font-weight: 500;
}

.remove-button {
  padding: 0.4rem 0.6rem;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.8rem;
}

.remove-button:hover {
  background: #c82333;
  transform: translateY(-1px);
}

.tracker-actions {
  display: flex;
  gap: 0.75rem;
}

.save-button, .reload-button {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.save-button {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
}

.save-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
}

.reload-button {
  background: #6c757d;
  color: white;
}

.reload-button:hover {
  background: #5a6268;
  transform: translateY(-1px);
}

.empty-tracker-list {
  text-align: center;
  padding: 2rem;
  color: #6c757d;
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-tracker-list p {
  margin: 0.5rem 0;
}

.empty-tracker-list .hint {
  font-size: 0.9rem;
  opacity: 0.8;
}

</style> 
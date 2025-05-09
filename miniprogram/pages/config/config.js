// config.js
const app = getApp();
const appManager = require('../../utils/appManager');
const bleScanConfig = require('../../config/ble_scan_config.js'); // Corrected path

// Import the key definition from appManager or define it consistently
// Assuming appManager is correctly required:
// const appManager = require('../../utils/appManager'); 
// const MAP_STORAGE_KEY = appManager.STORAGE_KEYS.MAP_INFO; 
// If direct import isn't feasible, define it explicitly:
const MAP_STORAGE_KEY = 'app_map_info';

Page({
  data: {
    activeTab: 'beacon', // 当前激活的标签页: beacon, map, settings
    beacons: [], // Beacon配置列表
    mapInfo: {
      jsonContent: null, // JSON地图数据
      fileType: 'json' // 仅支持JSON
    },
    signalPathLossExponent: 2.5, // 信号传播因子n
    
    // --- 弹窗状态 ---
    showBeaconModal: false, // 是否显示Beacon编辑弹窗
    beaconModalMode: 'add', // 弹窗模式：add, edit
    editingBeaconIndex: -1, // 当前编辑的Beacon索引
    // Beacon编辑表单数据
    editingBeacon: {
      uuid: '',
      major: '',
      minor: '',
      x: '',
      y: '',
      txPower: '-59' // 默认值
    },
    showDeleteConfirmModal: false, // 删除确认弹窗
    deletingBeaconIndex: -1,
    showScanResultModal: false, // 扫描结果弹窗

    // --- 扫描状态 ---
    isScanning: false,
    scanResults: [], // 扫描到的Beacon列表
    latestBluetoothError: null, // To store the last BT error object {errCode, errMsg}
    showDebugDetails: false, // To toggle visibility of debug info
    lastActionLog: '', // To store simple status messages
    platform: wx.getSystemInfoSync().platform, // Store platform info

    // --- 地图交互状态 ---
    coordSelectMode: false, // 是否处于坐标选择模式
    tempBeaconData: null, // 临时保存的Beacon数据 (用于地图选点)
    tempSelectedCoords: null, // 临时选择的坐标 {x, y, pixelX, pixelY}
  },

  // --- 页面实例变量 (非响应式，用于内部逻辑) ---
  canvasInstance: null, // 保存Canvas节点
  canvasContext: null, // 保存2D上下文
  initMapPreviewInProgress: false, // 防止重复初始化地图预览
  // 地图绘制参数 (从Canvas计算得到，不放入data)
  mapScale: 1,
  mapOffset: { x: 0, y: 0 },
  mapSize: { width: 0, height: 0 },

  // --- 页面生命周期 ---
  onLoad() {
    this.initParsers(); // Call parser initialization
    this.setData({
      iOSScanUUIDs: bleScanConfig.iOSScanUUIDs || [] // Load UUIDs from config, default to empty array
    });
    this.loadData();
  },
  
  onShow() {
    // 每次显示页面时，检查是否需要重新加载数据或更新状态
    this.loadData(); // 重新加载数据以同步最新状态

    // 如果当前是地图标签页，确保地图预览是最新的
    if (this.data.activeTab === 'map') {
      if (this.data.mapInfo && this.data.mapInfo.jsonContent) {
        // 延迟初始化以确保WXML渲染完成
        setTimeout(() => { this.initMapPreview(); }, 100);
      } else {
        // 如果没有地图数据，也尝试初始化（会显示提示）
        setTimeout(() => { this.initMapPreview(); }, 100);
      }
    }

    // 清理可能残留的坐标选择状态
    if (this.data.coordSelectMode) {
      this.coordinateSelectionCleanup();
    }
  },

  // --- 数据加载与保存 ---
  loadData() {
    // 优先从appManager获取状态和配置
    if (appManager && appManager.getState) {
      const state = appManager.getState();
      const configuredBeacons = state.configuredBeacons || [];
      const factor = state.signalFactor;

      // --- Revised Map Loading Logic ---
      let mapToSet = this.data.mapInfo; // Start with current map data
      let loadedMapFromStorage = null;

      // Only attempt to load from storage if there isn't an unsaved map currently
      if (!this.data.mapInfo || !this.data.mapInfo.jsonContent) { 
          try {
              const mapInfoStr = wx.getStorageSync(MAP_STORAGE_KEY); // Use correct key
              if (mapInfoStr) {
                  const parsedMap = JSON.parse(mapInfoStr);
                  // Basic validation of loaded data
                  if (this.validateMapJSON(parsedMap)) {
                      loadedMapFromStorage = parsedMap;
                      mapToSet = { jsonContent: loadedMapFromStorage, fileType: 'json' };
                  } else {
                      console.warn('Invalid map data found in storage, ignoring.');
                      mapToSet = { jsonContent: null, fileType: 'json' }; // Reset if invalid
                  }
              } else {
                   mapToSet = { jsonContent: null, fileType: 'json' }; // No saved map
              }
          } catch (e) {
              console.error('Error loading/parsing map from storage:', e);
              mapToSet = { jsonContent: null, fileType: 'json' }; // Reset on error
          }
      }
      // Else: Keep the existing `this.data.mapInfo` which holds the unsaved uploaded map

      this.setData({
        beacons: configuredBeacons,
        signalPathLossExponent: factor || this.data.signalPathLossExponent,
        mapInfo: mapToSet // Set the determined map data
      }, () => {
        // Refresh preview if needed AFTER data is set
        if (this.data.activeTab === 'map') {
             wx.nextTick(() => { this.initMapPreview(); });
        }
      });
      // --- End Revised Map Loading Logic ---

        } else {
      // appManager不可用时的备用方案
      console.error('appManager未初始化或不可用，尝试从本地存储加载');
      this.loadFromLocalStorage();
    }
  },

  loadFromLocalStorage() { // Fallback method needs same logic
    try {
      const beacons = wx.getStorageSync('beacons') || [];
      const factor = wx.getStorageSync('signalPathLossExponent');

      // --- Revised Map Loading for Fallback ---
      let mapToSet = this.data.mapInfo; // Start with current
      if (!this.data.mapInfo || !this.data.mapInfo.jsonContent) { // Only load if no unsaved map
           let loadedMapFromStorage = null;
           try {
                const mapInfoStr = wx.getStorageSync(MAP_STORAGE_KEY); // Use correct key
                if (mapInfoStr) {
                    const parsedMap = JSON.parse(mapInfoStr);
                    if (this.validateMapJSON(parsedMap)) {
                        loadedMapFromStorage = parsedMap;
                        mapToSet = { jsonContent: loadedMapFromStorage, fileType: 'json' };
                    } else {
                         mapToSet = { jsonContent: null, fileType: 'json' }; // Reset if invalid
                    }
                } else {
                     mapToSet = { jsonContent: null, fileType: 'json' }; // No saved map
                }
            } catch (e) {
                console.error('Fallback: Error loading/parsing map from storage:', e);
                mapToSet = { jsonContent: null, fileType: 'json' }; // Reset on error
            }
      } // Else: Keep unsaved map

              this.setData({ 
        beacons: Array.isArray(beacons) ? beacons : [],
        mapInfo: mapToSet,
        signalPathLossExponent: (factor && !isNaN(parseFloat(factor))) ? parseFloat(factor) : this.data.signalPathLossExponent
      }, () => {
         // Refresh preview if needed AFTER data is set
         if (this.data.activeTab === 'map') {
             wx.nextTick(() => { this.initMapPreview(); });
         }
      });
      // --- End Revised Map Loading for Fallback ---

    } catch (e) {
      console.error('从本地存储加载基础配置失败:', e);
      wx.showToast({ title: '加载本地配置失败', icon: 'none' });
      // Ensure mapInfo is reset if outer try fails
      this.setData({ mapInfo: { jsonContent: null, fileType: 'json' } });
    }
  },

  // 保存Beacon列表 (通过appManager)
  saveBeaconList(beacons, successMessage) {
    appManager.saveBeaconsToStorage(beacons)
      .then(() => {
        wx.showToast({ title: successMessage, icon: 'success' });
        // 保存成功后，检查是否需要更新预览 (使用 wx.nextTick 确保 setData 完成)
        wx.nextTick(() => {
             if (this.data.activeTab === 'map' && this.data.mapInfo.jsonContent) {
                this.initMapPreview();
            }
        });
      })
      .catch(err => {
        console.error('通过appManager保存Beacon失败:', err);
        wx.showToast({ title: '保存失败', icon: 'none' });
    });
  },
  
  // 保存地图配置 (通过appManager)
  saveMapConfigAction() {
    console.log('[saveMapConfigAction] Function called.');
    const fullConfig = this.data.mapInfo.jsonContent; // Get the full loaded config
    if (!fullConfig || typeof fullConfig.map !== 'object') { // Check if it has the expected structure
      console.log('[saveMapConfigAction] Invalid or missing map data structure in jsonContent.');
      wx.showToast({ title: '地图数据结构无效', icon: 'none' });
      return;
    }
    
    const mapDataToSave = fullConfig.map; // Extract ONLY the map object

    wx.showLoading({ title: '保存中...', mask: true });
    console.log('[saveMapConfigAction] Calling appManager.loadMapData with map object:', mapDataToSave);
    appManager.loadMapData(mapDataToSave) // Pass only the map object
      .then(() => {
        console.log('[saveMapConfigAction] appManager.loadMapData resolved (Success).');
        wx.hideLoading();
        wx.showToast({ title: '地图配置已保存', icon: 'success' });
    // 重新绘制预览
        wx.nextTick(() => { // 确保在下一个事件循环绘制
            if (this.data.activeTab === 'map') {
    this.initMapPreview();
            }
        });
      })
      .catch(err => {
        console.error('[saveMapConfigAction] appManager.loadMapData rejected (Error):', err);
        wx.hideLoading();
        wx.showModal({ title: '保存失败', content: '保存地图配置失败: ' + (err.message || String(err)), showCancel: false });
      });
  },

  // 保存通用设置 (信号因子)
  saveSettingsAction() {
    console.log('[config.js] saveSettingsAction called!');
    const factor = parseFloat(this.data.signalPathLossExponent);
    if (isNaN(factor) || factor <= 0) {
      wx.showToast({ title: '请输入有效的信号因子(正数)', icon: 'none' });
      return;
    }
    appManager.saveSignalFactorToStorage(factor)
      .then(() => {
        wx.showToast({ title: '设置已保存', icon: 'success' });
      })
      .catch(err => {
        console.error('通过appManager保存信号因子失败:', err);
        wx.showToast({ title: '保存失败', icon: 'none' });
        // 可选：增加本地备份保存
        // wx.setStorageSync('signalPathLossExponent', factor);
    });
  },
  
  // --- NEW: Function to handle slider change ---
  updateSignalFactor(e) {
    if (e && e.detail) {
      this.setData({ signalPathLossExponent: e.detail.value });
    }
  },
  // --- END NEW ---

  // --- 标签页切换 ---
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (this.data.activeTab === tab) return; // 避免重复切换

    // 清理地图选择状态
    if (this.data.coordSelectMode) {
        this.coordinateSelectionCleanup();
    }

    this.setData({ activeTab: tab });

    // 切换到地图标签页时，初始化预览
    if (tab === 'map') {
      if (this.data.mapInfo && this.data.mapInfo.jsonContent) {
        setTimeout(() => { this.initMapPreview(); }, 100);
      } else {
        // 即使没有地图，也调用初始化以显示提示信息
        setTimeout(() => { this.initMapPreview(); }, 100);
      }
    }
  },

  // --- Beacon 配置相关 ---
  showAddBeaconModal() {
      this.setData({
        showBeaconModal: true,
        beaconModalMode: 'add',
        editingBeaconIndex: -1,
      editingBeacon: { uuid: '', major: '', minor: '', x: '', y: '', txPower: '-59' }
    });
  },

  showEditBeaconModal(e) {
    const index = e.currentTarget.dataset.index;
    const beacon = this.data.beacons[index];
    this.setData({
      showBeaconModal: true,
      beaconModalMode: 'edit',
      editingBeaconIndex: index,
      editingBeacon: { ...beacon } // 复制一份进行编辑
    });
  },
  
  hideBeaconModal() {
    this.setData({ showBeaconModal: false });
    // 关闭弹窗时清理地图选点状态
    if (this.data.coordSelectMode) {
    this.coordinateSelectionCleanup();
    }
  },
  
  updateBeaconField(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({ [`editingBeacon.${field}`]: value });
  },
  
  confirmBeaconEdit() {
    const beacon = this.data.editingBeacon;
    // 数据验证
    if (!beacon.uuid || !beacon.x || !beacon.y || !beacon.txPower) {
      wx.showToast({ title: '请填写所有必填项', icon: 'none' }); return;
    }
    const x = parseFloat(beacon.x); const y = parseFloat(beacon.y); const txPower = parseFloat(beacon.txPower);
    if (isNaN(x) || isNaN(y) || isNaN(txPower)) {
      wx.showToast({ title: '坐标和功率必须是数字', icon: 'none' }); return;
    }
    const major = beacon.major ? parseInt(beacon.major) : 0;
    const minor = beacon.minor ? parseInt(beacon.minor) : 0;
    if (isNaN(major) || isNaN(minor)) {
      wx.showToast({ title: 'Major/Minor必须是数字', icon: 'none' }); return;
    }

    // --- Modified displayName Logic for Saving ---
    // Use user-provided displayName if not empty, otherwise fallback
    let finalDisplayName = beacon.displayName?.trim();
    if (!finalDisplayName) {
        // Fallback: Use deviceId if available, else short UUID
        finalDisplayName = beacon.deviceId ? `Dev-${beacon.deviceId.substring(beacon.deviceId.length - 6)}` : `UUID-${beacon.uuid.substring(0, 4)}`;
    }
    // --- End Modification ---

    const beaconToSave = {
      uuid: beacon.uuid.trim().toUpperCase(),
      displayName: finalDisplayName, // Use the final derived/fallback name
      deviceId: beacon.deviceId || null,
      major: major,
      minor: minor,
      x: x, y: y, txPower: txPower
    };

    // UUID格式验证 (非强制)
    const uuidRegex = /^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/i;
    if (!uuidRegex.test(beaconToSave.uuid)) {
      wx.showModal({
        title: 'UUID格式警告',
        content: 'UUID格式不是标准格式，可能导致无法匹配。是否继续保存？',
        success: (res) => { if (res.confirm) { this.processBeaconSave(beaconToSave); } }
      });
    } else {
      this.processBeaconSave(beaconToSave);
    }
  },

  processBeaconSave(beaconToSave) {
    const beacons = [...this.data.beacons];
    let successMessage = '';
    let shouldUpdatePreview = false;

    if (this.data.beaconModalMode === 'add') {
      const existingIndex = beacons.findIndex(b =>
        b.uuid === beaconToSave.uuid &&
        b.major === beaconToSave.major &&
        b.minor === beaconToSave.minor
      );
      if (existingIndex >= 0) {
      wx.showModal({
          title: '重复Beacon',
          content: '已存在相同UUID/Major/Minor的Beacon，是否覆盖更新？',
          success: (res) => {
            if (res.confirm) {
              beacons[existingIndex] = beaconToSave;
              // 更新后需要刷新预览
              this.setData({ beacons: beacons, showBeaconModal: false }, () => {
                this.saveBeaconList(beacons, 'Beacon更新成功');
              });
            }
          }
        });
        return; // 等待用户确认
      }
      beacons.push(beaconToSave);
      successMessage = 'Beacon添加成功';
      shouldUpdatePreview = true;
    } else { // edit mode
      const index = this.data.editingBeaconIndex;
      if (index >= 0 && index < beacons.length) {
        const conflictIndex = beacons.findIndex((b, i) =>
          i !== index &&
          b.uuid === beaconToSave.uuid &&
          b.major === beaconToSave.major &&
          b.minor === beaconToSave.minor
        );
        if (conflictIndex >= 0) {
          wx.showToast({ title: '编辑失败：与其他Beacon冲突', icon: 'none' });
      return;
    }
        beacons[index] = beaconToSave;
        successMessage = 'Beacon更新成功';
        shouldUpdatePreview = true;
    } else {
        console.error('无效的Beacon索引:', index);
        wx.showToast({ title: '更新失败：无效索引', icon: 'none' });
        return;
      }
    }

    // 如果不是覆盖更新的情况，在此处setData并保存
    if (shouldUpdatePreview) {
        this.setData({ beacons: beacons, showBeaconModal: false }, () => {
            this.saveBeaconList(beacons, successMessage);
        });
    }
  },

  showDeleteConfirm(e) {
    this.setData({ showDeleteConfirmModal: true, deletingBeaconIndex: e.currentTarget.dataset.index });
  },

  cancelDelete() {
    this.setData({ showDeleteConfirmModal: false, deletingBeaconIndex: -1 });
  },
  
  confirmDelete() {
    const index = this.data.deletingBeaconIndex;
    if (index < 0 || index >= this.data.beacons.length) { this.cancelDelete(); return; }

    const beacons = [...this.data.beacons];
    beacons.splice(index, 1);
    
    // 使用 setData 回调确保状态更新后再保存和刷新预览
    this.setData({
      beacons: beacons,
      showDeleteConfirmModal: false,
      deletingBeaconIndex: -1
    }, () => {
        this.saveBeaconList(beacons, '删除成功');
    });
  },
  
  // --- Beacon 扫描相关 ---
  startScanBeacons() {
    console.log(`[BT LOG] startScanBeacons called on platform: ${this.data.platform}.`); // LOG
    this.setData({ 
        isScanning: false, // Reset just in case
        scanResults: [], 
        latestBluetoothError: null, 
        lastActionLog: '尝试启动扫描...' // Trying to start scan...
    }); 
    if (this.data.isScanning) { 
        console.log('[BT LOG] Scan already in progress, returning.');
        return; 
    }
    this.initBluetooth()
      .then(() => {
        if (this.data.platform === 'android') {
          this.startAndroidDiscovery();
        } else { // Use BeaconDiscovery for iOS and any other non-Android platform
          this.startBeaconDiscovery(); // Renamed from startIOSBeaconDiscovery
        }
      })
      .catch(err => { 
          console.error('[BT LOG] initBluetooth failed in startScanBeacons chain.');
          this.setData({ lastActionLog: '蓝牙初始化失败' }); // Bluetooth init failed
      });
  },

  initBluetooth() {
    console.log('[BT LOG] initBluetooth called.'); // LOG
    this.setData({ lastActionLog: '初始化蓝牙适配器...' }); // Initializing BT adapter...
    return new Promise((resolve, reject) => {
    wx.openBluetoothAdapter({
        success: (res) => {
          console.log('[BT LOG] wx.openBluetoothAdapter SUCCESS:', res); // LOG
          this.setData({ lastActionLog: '蓝牙适配器打开成功' }); // BT adapter opened successfully
          wx.onBluetoothAdapterStateChange((res) => {
            console.log('[BT LOG] BluetoothAdapterStateChange:', res); // LOG
            if (!res.available && this.data.isScanning) {
              console.log('[BT LOG] Adapter became unavailable during scan. Stopping.'); // LOG
              this.stopScanBeacons();
              wx.showToast({ title: '蓝牙已断开', icon: 'none' });
              this.setData({ lastActionLog: '蓝牙适配器状态改变: 不可用' }); // BT adapter state change: unavailable
            } else if (res.available) {
                 this.setData({ lastActionLog: '蓝牙适配器状态改变: 可用' }); // BT adapter state change: available
            }
          });
          resolve(res); // Resolve with the success response
        },
        fail: (err) => {
          console.error('[BT LOG] wx.openBluetoothAdapter FAILED:', err); // LOG Full Error
          const errorInfo = { errCode: err.errCode, errMsg: err.errMsg };
          this.setData({ 
              latestBluetoothError: errorInfo,
              lastActionLog: `蓝牙适配器失败: ${err.errMsg}` // BT adapter failed
          }); 
          this.showBluetoothError(err); 
          reject(err);
        }
      });
    });
  },

  showBluetoothError(err) {
    console.error('[BT LOG] showBluetoothError called with:', err); // LOG
    let errorMsg = '蓝牙操作失败';
    let detail = err.errMsg || '未知错误';
    let code = err.errCode;

    // Log detailed error info regardless of modal message
    console.error(`[BT LOG] Bluetooth Error Details: Code=${code}, Message=${detail}`);

    if (code === 10001) { errorMsg = '请先打开设备蓝牙'; }
    else if (code === 10008) { errorMsg = '请开启系统定位服务'; } // System location service often needed on iOS
    else if (code === 10009) { errorMsg = '请授权小程序蓝牙权限'; }
    else if (detail && detail.includes('support')) { errorMsg = '设备不支持蓝牙'; }
    else if (detail) { errorMsg = `错误: ${detail}`; } // Show full message if generic

    wx.showModal({ 
        title: '蓝牙错误', 
        content: `${errorMsg} (错误码: ${code})`, 
        showCancel: false 
    });
    // Also update log state
    this.setData({ lastActionLog: `蓝牙错误: ${errorMsg}` });
  },

  startAndroidDiscovery() {
    console.log('[BT LOG] startAndroidDiscovery called.'); // LOG
    this.setData({ 
        isScanning: true, 
        showScanResultModal: true, 
        scanResults: [], 
        latestBluetoothError: null,
        lastActionLog: '开始搜索蓝牙设备 (Android)...'
    });
    wx.startBluetoothDevicesDiscovery({
      allowDuplicatesKey: true, 
      interval: 0, 
      success: (res) => {
        console.log('[BT LOG] wx.startBluetoothDevicesDiscovery SUCCESS:', res); // LOG
        this.setData({ lastActionLog: '设备搜索已启动 (Android)' });
        console.log('[BT LOG] Registering wx.onBluetoothDeviceFound listener.'); // LOG
        wx.onBluetoothDeviceFound(this.handleAndroidDeviceFound); // Use specific handler
         setTimeout(() => { 
             if (this.data.isScanning) { 
                 console.log('[BT LOG] Android Scan timeout reached. Stopping.'); // LOG
                 this.stopScanBeacons(); 
             } 
         }, 30000); // 30 seconds timeout
      },
      fail: (err) => {
        console.error('[BT LOG] wx.startBluetoothDevicesDiscovery FAILED:', err); // LOG Full Error
        const errorInfo = { errCode: err.errCode, errMsg: err.errMsg };
        this.setData({ 
            isScanning: false, 
            latestBluetoothError: errorInfo,
            lastActionLog: `启动Android搜索失败: ${err.errMsg}`
        }); 
        this.showBluetoothError(err);
        this.setData({ showScanResultModal: false });
      }
    });
  },

  // NEW: Start Beacon Discovery for iOS / Non-Android
  startBeaconDiscovery() { // Renamed from startIOSBeaconDiscovery
    console.log('[BT LOG] startBeaconDiscovery called (for non-Android).'); // LOG
    if (!this.data.iOSScanUUIDs || this.data.iOSScanUUIDs.length === 0) {
      console.error('[BT LOG] No UUIDs configured to scan for.');
      this.setData({ lastActionLog: '扫描错误: 未配置UUID' });
      wx.showModal({ title: '错误', content: '未配置用于iBeacon扫描的UUID', showCancel: false });
      return;
    }
    this.setData({ 
        isScanning: true, 
        showScanResultModal: true, 
        scanResults: [], 
        latestBluetoothError: null,
        lastActionLog: '开始搜索iBeacon (非安卓)...',
    });

    // Ensure UUIDs are uppercase without extra spaces
    const cleanUUIDs = this.data.iOSScanUUIDs.map(uuid => uuid.toUpperCase().trim());
    console.log('[BT LOG] Starting beacon discovery for UUIDs:', cleanUUIDs);

    wx.startBeaconDiscovery({
      uuids: cleanUUIDs,
      ignoreBluetoothAvailable: false, // Recommended default
      success: (res) => {
        console.log('[BT LOG] wx.startBeaconDiscovery SUCCESS:', res); // LOG
        this.setData({ lastActionLog: 'iBeacon搜索已启动 (非安卓)' });
        console.log('[BT LOG] Registering wx.onBeaconUpdate listener.'); // LOG
        wx.onBeaconUpdate(this.handleBeaconUpdate); // Renamed from handleIOSBeaconUpdate

         setTimeout(() => { 
             if (this.data.isScanning) { 
                 console.log('[BT LOG] BeaconDiscovery Scan timeout reached. Stopping.'); // LOG
                 this.stopScanBeacons(); 
             } 
         }, 30000); // 30 seconds timeout
      },
      fail: (err) => {
        console.error('[BT LOG] wx.startBeaconDiscovery FAILED:', err); // LOG Full Error
        const errorInfo = { errCode: err.errCode, errMsg: err.errMsg };
        this.setData({ 
            isScanning: false, 
            latestBluetoothError: errorInfo,
            lastActionLog: `启动iBeacon搜索失败: ${err.errMsg}`
        }); 
        this.showBluetoothError(err);
        this.setData({ showScanResultModal: false });
      }
    });
  },

  // Renamed from handleDeviceFound
  handleAndroidDeviceFound(res) {
    // console.log('[BT LOG] wx.onBluetoothDeviceFound received (Android):', res);
    if (!res.devices || res.devices.length === 0) return;
    
    res.devices.forEach(device => {
        const deviceId = device.deviceId || '(no ID)';
        const name = device.name || '(no name)';
        const localName = device.localName || '(no local name)';
        const rssi = device.RSSI;
        console.log(`[BT LOG Android] Device Found: ID=${deviceId}, Name=${name}, RSSI=${rssi}`);
        // this.setData({ lastActionLog: `Android发现: ${name} (${deviceId})` });

        let beaconInfo = null;
        // Parsing logic (advertisData / manufacturerData) remains here for Android
        if (device.advertisData) {
             try {
                 const hexAdvData = Array.prototype.map.call(new Uint8Array(device.advertisData), x => ('00' + x.toString(16)).slice(-2)).join(' ');
                 console.log(`[BT LOG Android]   Adv Data (Hex): ${hexAdvData}`);
             } catch (e) { console.warn('[BT LOG Android]   Error converting AdvData to hex', e); }

            beaconInfo = this.parseAdvertisDataStandard(device.advertisData);
            if (!beaconInfo) {
                beaconInfo = this.parseAdvertisDataAlternative(device.advertisData);
            }
            if (!beaconInfo) {
                 console.log('[BT LOG Android]   advertisData exists but did not parse as iBeacon.');
            }
        } else {
             console.log(`[BT LOG Android]   Device ${deviceId} has no AdvData.`);
        }

        if (!beaconInfo && device.manufacturerData) {
             console.log('[BT LOG Android]   Attempting to parse manufacturerData.');
             try {
                 const hexManuData = Array.prototype.map.call(new Uint8Array(device.manufacturerData), x => ('00' + x.toString(16)).slice(-2)).join(' ');
                 console.log(`[BT LOG Android]   Manu Data (Hex): ${hexManuData}`);
             } catch (e) { console.warn('[BT LOG Android]   Error converting ManuData to hex', e); }
            beaconInfo = this.parseManufacturerDataForIBeacon(device.manufacturerData); // Reuse parser if needed
        } else if (!beaconInfo) {
             console.log(`[BT LOG Android]   Device ${deviceId} has no ManufacturerData either.`);
        }

        if (beaconInfo && beaconInfo.isIBeacon) {
            console.log(`[BT LOG Android]   Parsed as iBeacon: UUID=${beaconInfo.uuid}, Major=${beaconInfo.major}, Minor=${beaconInfo.minor}, TxPower=${beaconInfo.txPower}`);
            this.setData({ lastActionLog: `Android解析iBeacon: ${name}` });
            this.addBeaconToScanResults({
                ...beaconInfo,
                rssi: device.RSSI,
                deviceId: device.deviceId, // Android uses MAC address here
                name: device.name,
                localName: device.localName
            });
        } else {
             console.log(`[BT LOG Android]   Device ${deviceId} not parsed as iBeacon.`);
        }
    });
  },

  // NEW: Handler for iOS beacon updates (Now generalized)
  handleBeaconUpdate(res) { // Renamed from handleIOSBeaconUpdate
      console.log(`[BT LOG BeaconDiscovery] wx.onBeaconUpdate received ${res.beacons.length} beacons.`);
      if (!res.beacons || res.beacons.length === 0) return;

      res.beacons.forEach(beacon => {
          const { uuid, major, minor, proximity, accuracy, rssi } = beacon;
          console.log(`[BT LOG BeaconDiscovery] Update: UUID=${uuid}, Major=${major}, Minor=${minor}, RSSI=${rssi}, Acc=${accuracy}`);
          this.setData({ lastActionLog: `发现iBeacon: ${major}-${minor}` });

          // Adapt the beacon data structure
          this.addBeaconToScanResults({
              isIBeacon: true, // Mark as confirmed iBeacon
              uuid: uuid.toUpperCase(),
              major: major,
              minor: minor,
              rssi: rssi,
              txPower: -59, // Assign a default/placeholder TxPower, as it's often unreliable from onBeaconUpdate
              deviceId: '', // deviceId (MAC) is not available from this iOS API
              name: 'iBeacon', // Generic name, can refine if needed
              localName: '',
              // Optional: Include accuracy/proximity if useful for display
              accuracy: accuracy,
              proximity: proximity
          });
      });
  },

  // --- Parsing Functions (Moved to separate init method) ---
  // parseAdvertisDataStandard, parseAdvertisDataAlternative, parseManufacturerDataForIBeacon definitions removed from here

  // --- NEW: Method to initialize parser functions on the instance --- 
  initParsers() {
    this.parseAdvertisDataStandard = (advertisData) => {
      // Standard iBeacon parsing (Major/Minor Big-Endian)
      try {
          const dataView = new DataView(advertisData);
          // Find 4C 00 02 15 (Apple iBeacon identifier)
          for (let i = 0; i <= dataView.byteLength - 25; i++) { 
              if (dataView.getUint8(i) === 0x4C && dataView.getUint8(i + 1) === 0x00 &&
                  dataView.getUint8(i + 2) === 0x02 && dataView.getUint8(i + 3) === 0x15) {
                  const startIndex = i + 4;
                  let uuid = '';
                  for (let j = 0; j < 16; j++) {
                      uuid += dataView.getUint8(startIndex + j).toString(16).padStart(2, '0');
                      if (j === 3 || j === 5 || j === 7 || j === 9) uuid += '-';
                  }
                  const major = dataView.getUint16(startIndex + 16, false); 
                  const minor = dataView.getUint16(startIndex + 18, false); 
                  const txPower = dataView.getInt8(startIndex + 20);
                  return { isIBeacon: true, uuid: uuid.toUpperCase(), major, minor, txPower };
              }
          }
      } catch (e) { console.error('[BT Parser] Standard parse error', e); }
      return null;
    };

    this.parseAdvertisDataAlternative = (advertisData) => {
      // Alt parsing (Maybe missing Apple ID 4C 00)
      try {
            const dataView = new DataView(advertisData);
            // Find 02 15 (iBeacon type and length)
            for (let i = 0; i <= dataView.byteLength - 23; i++) { 
                if (dataView.getUint8(i) === 0x02 && dataView.getUint8(i + 1) === 0x15) {
                    const startIndex = i + 2;
                    let uuid = '';
                    for (let j = 0; j < 16; j++) {
                        uuid += dataView.getUint8(startIndex + j).toString(16).padStart(2, '0');
                        if (j === 3 || j === 5 || j === 7 || j === 9) uuid += '-';
                    }
                    const major = dataView.getUint16(startIndex + 16, false);
                    const minor = dataView.getUint16(startIndex + 18, false);
                    const txPower = dataView.getInt8(startIndex + 20);
                    return { isIBeacon: true, uuid: uuid.toUpperCase(), major, minor, txPower };
                }
            }
        } catch (e) { console.error('[BT Parser] Alternative parse error', e); } 
        return null;
    };

    this.parseManufacturerDataForIBeacon = (manufacturerData) => {
      // Parse manufacturerData directly (common iOS format)
      if (!manufacturerData || manufacturerData.byteLength !== 23) {
        // console.log(`[BT Parser] ManufacturerData length not 23.`);
        return null;
      }
      try {
        const dataView = new DataView(manufacturerData);
        // Check for iBeacon type (0x02) and length (0x15)
        if (dataView.getUint8(0) === 0x02 && dataView.getUint8(1) === 0x15) {
          const startIndex = 2; 
          let uuid = '';
          for (let j = 0; j < 16; j++) {
            uuid += dataView.getUint8(startIndex + j).toString(16).padStart(2, '0');
            if (j === 3 || j === 5 || j === 7 || j === 9) uuid += '-';
          }
          const major = dataView.getUint16(startIndex + 16, false); 
          const minor = dataView.getUint16(startIndex + 18, false); 
          const txPower = dataView.getInt8(startIndex + 20);
          console.log('[BT Parser] Successfully parsed iBeacon from manufacturerData.');
          return { isIBeacon: true, uuid: uuid.toUpperCase(), major, minor, txPower };
        } else {
          // console.log('[BT Parser] ManufacturerData prefix not 0x02 0x15.');
        }
      } catch (e) {
        console.error('[BT Parser] ManufacturerData parse error:', e);
      }
      return null;
    };
  },
  // --- END NEW PARSER INIT ---

  addBeaconToScanResults(beacon) {
    if (!beacon || !beacon.uuid) { 
        console.warn('[addBeaconToScanResults] Invalid beacon data received:', beacon);
        return; 
    }
    const platform = this.data.platform; // Get platform info
    console.log(`[addBeaconToScanResults] Platform: ${platform}, Processing Beacon:`, beacon);

    // --- Platform-Aware Filtering against Configured Beacons ---
    let isAlreadyConfigured = false;
    if (platform === 'android') {
        // Android: Filter based on deviceId (MAC Address)
        if (beacon.deviceId) { 
            isAlreadyConfigured = this.data.beacons.some(configuredBeacon =>
                configuredBeacon.deviceId && 
                configuredBeacon.deviceId === beacon.deviceId
            );
            if(isAlreadyConfigured) console.log(`[addBeaconToScanResults Android] Filtered: Device ID ${beacon.deviceId} already configured.`);
        } else {
             console.log(`[addBeaconToScanResults Android] Skipping beacon with missing deviceId:`, beacon);
             return; // Exit the function, do not add this beacon
        }
    } else {
        // Non-Android (iOS, etc.): Filter based on UUID/Major/Minor
        isAlreadyConfigured = this.data.beacons.some(configuredBeacon =>
            configuredBeacon.uuid === beacon.uuid &&
            configuredBeacon.major === beacon.major &&
            configuredBeacon.minor === beacon.minor
        );
         if(isAlreadyConfigured) console.log(`[addBeaconToScanResults Non-Android] Filtered: UUID/Major/Minor ${beacon.uuid}/${beacon.major}/${beacon.minor} already configured.`);
    }
    // --- END Platform-Aware Filtering ---
    
    if (isAlreadyConfigured) {
        return; // Don't add to scan results if already configured
    }

    const scanResults = [...this.data.scanResults];
    let existingIndex = -1;

    // --- Platform-Aware De-duplication/Update within Scan Results List ---
    if (platform === 'android') {
        // Android: Find existing ONLY by deviceId (MAC address)
        if (beacon.deviceId) {
             existingIndex = scanResults.findIndex(item => item.deviceId === beacon.deviceId);
        } else {
             // If no deviceId on Android, we cannot reliably de-duplicate or identify.
             // Options: Skip, or add anyway (might lead to UUID/Major/Minor duplicates shown).
             // Let's skip for now to enforce MAC-based uniqueness on Android.
             console.warn('[addBeaconToScanResults Android] Skipping beacon with missing deviceId:', beacon);
             return; // Exit the function, do not add this beacon
        }
    } else {
        // Non-Android (iOS, etc.): Find existing by UUID/Major/Minor
        existingIndex = scanResults.findIndex(item =>
            item.uuid === beacon.uuid &&
            item.major === beacon.major &&
            item.minor === beacon.minor
        );
    }
    // --- END Platform-Aware De-duplication ---

    // Determine Display Name
    let displayName = beacon.localName || beacon.name;
    if (!displayName) {
        // Android gets MAC suffix, others get Major-Minor
        displayName = platform === 'android' && beacon.deviceId 
                      ? beacon.deviceId.substring(beacon.deviceId.length - 6) 
                      : `${beacon.major}-${beacon.minor}`;
    }

    // Ensure consistent structure for list items
    const beaconInfo = {
      uuid: beacon.uuid,
      major: beacon.major,
      minor: beacon.minor,
      rssi: beacon.rssi,
      txPower: beacon.txPower, // Keep TxPower from parsing (Android) or default (iOS)
      deviceId: beacon.deviceId || '', // Use empty string if not available (iOS)
      name: beacon.name || '',
      localName: beacon.localName || '',
      displayName: displayName,
      // Include optional iOS fields if present
      accuracy: beacon.accuracy,
      proximity: beacon.proximity
    };

    if (existingIndex >= 0) {
      scanResults[existingIndex] = beaconInfo;
      console.log(`[addBeaconToScanResults ${platform}] Updated existing entry index ${existingIndex}.`);
    } else {
      scanResults.push(beaconInfo);
      scanResults.sort((a, b) => b.rssi - a.rssi); // Sort by RSSI descending
      console.log(`[addBeaconToScanResults ${platform}] Added new entry.`);
    }
    this.setData({ scanResults: scanResults });
  },

  selectBeaconFromScan(e) {
    const index = e.currentTarget.dataset.index;
    const beacon = this.data.scanResults[index];
    if (!beacon || !beacon.uuid) {
      wx.showToast({ title: '选择的设备无效', icon: 'none' }); return;
    }
    this.stopScanBeacons(); // Stop whichever scan is running
    this.setData({ showScanResultModal: false });
    
    // --- Determine platform-aware prefilledDisplayName ---
    let prefilledDisplayName = '';
    const platform = this.data.platform;

    if (platform === 'android') {
      if (beacon.localName && beacon.localName.trim() !== '') {
        prefilledDisplayName = beacon.localName.trim();
      } else if (beacon.name && beacon.name.trim() !== '') {
        prefilledDisplayName = beacon.name.trim();
      } else if (beacon.deviceId) {
        // Fallback for Android if no name/localName, use part of deviceId
        prefilledDisplayName = beacon.deviceId.substring(beacon.deviceId.length - 6);
      } else {
        // Further fallback if no deviceId either (unlikely for Android scan)
        prefilledDisplayName = `${beacon.major}-${beacon.minor}`;
      }
    } else { // iOS or other platforms
      prefilledDisplayName = `${beacon.major}-${beacon.minor}`; // Default for iOS
    }
    // Ensure displayName is not just an empty string if previous logic resulted in one accidentally
    if (!prefilledDisplayName || prefilledDisplayName.trim() === '') {
        prefilledDisplayName = `Beacon ${beacon.major}-${beacon.minor}` // Generic fallback
    }
    // --- End display name logic ---

    const prefilledTxPower = (beacon.txPower !== undefined && beacon.txPower !== 0) // Check if txPower is valid (not 0 from iOS onBeaconUpdate)
                             ? beacon.txPower.toString() 
                             : '-59'; // Default if invalid/missing

    this.setData({
      showBeaconModal: true,
      beaconModalMode: 'add',
      editingBeaconIndex: -1,
      editingBeacon: {
        uuid: beacon.uuid,
        major: beacon.major !== undefined ? beacon.major.toString() : '',
        minor: beacon.minor !== undefined ? beacon.minor.toString() : '',
        deviceId: beacon.deviceId || '', // Include deviceId if available (Android)
        displayName: prefilledDisplayName,
        x: '', y: '',
        txPower: prefilledTxPower // Use default if scan didn't provide valid one
      }
    });
    wx.showToast({ title: '请设置位置信息', icon: 'none' });
  },

  stopScanBeacons() {
    if (!this.data.isScanning) return;
    console.log(`[BT LOG] stopScanBeacons called on platform: ${this.data.platform}.`); // LOG
    this.setData({ isScanning: false, lastActionLog: '停止扫描...' });

    if (this.data.platform === 'android') {
        wx.stopBluetoothDevicesDiscovery({ 
             success: () => console.log('[BT LOG] wx.stopBluetoothDevicesDiscovery success.'),
            fail: (err) => console.warn('[BT LOG] wx.stopBluetoothDevicesDiscovery failed', err) 
        });
        wx.offBluetoothDeviceFound(this.handleAndroidDeviceFound); // Unregister Android listener
        console.log('[BT LOG] Unregistered wx.onBluetoothDeviceFound listener.');
    } else {
        // Stop BeaconDiscovery for iOS and other platforms
        wx.stopBeaconDiscovery({ 
            success: () => console.log('[BT LOG] wx.stopBeaconDiscovery success.'),
            fail: (err) => console.warn('[BT LOG] wx.stopBeaconDiscovery failed', err) 
        });
        wx.offBeaconUpdate(this.handleBeaconUpdate); // Unregister BeaconUpdate listener
        console.log('[BT LOG] Unregistered wx.onBeaconUpdate listener.');
    }
    
    // Keep closing adapter common for now
    wx.closeBluetoothAdapter({ 
        success: () => console.log('[BT LOG] wx.closeBluetoothAdapter success.'),
        fail: (err) => console.warn('[BT LOG] wx.closeBluetoothAdapter failed', err) 
    });
    this.setData({ lastActionLog: '扫描已停止' });
  },

  hideScanResultModal() {
    console.log('[BT LOG] hideScanResultModal called, stopping scan.'); // LOG
    this.stopScanBeacons();
    this.setData({ showScanResultModal: false });
  },
  
  // --- 地图预览与交互 ---
  initMapPreview() {
    if (this.initMapPreviewInProgress) { return; }
    this.initMapPreviewInProgress = true;

    const query = wx.createSelectorQuery().in(this);
    query.select('#mapCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        this.initMapPreviewInProgress = false;
        if (!res || !res[0] || !res[0].node) {
          console.error('获取地图预览Canvas节点失败');
          // 不显示Toast，避免干扰，允许后续重试
          return;
        }
        const canvas = res[0].node;
    this.canvasInstance = canvas;
        if (!canvas || typeof canvas.getContext !== 'function') {
          console.error('Canvas节点无效'); return;
        }
        const ctx = canvas.getContext('2d');
        if (!ctx) { console.error('获取2d上下文失败'); return; }
        this.canvasContext = ctx;

        const dpr = wx.getSystemInfoSync().pixelRatio;
        const width = res[0].width;
        const height = res[0].height;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = '#f8f8f8'; ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = '#cccccc'; ctx.lineWidth = 1; ctx.strokeRect(0, 0, width, height);

        const mapInfo = this.data.mapInfo;
        if (mapInfo && mapInfo.jsonContent && this.validateMapJSON(mapInfo.jsonContent)) {
          this.drawJSONMap(ctx, width, height); // 绘制地图和信标
          this.setupMapClickEvent(); // 设置点击事件处理
        } else {
          ctx.fillStyle = '#666666'; ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
          ctx.fillText('请上传有效的JSON地图', width/2, height/2 - 10);
          ctx.fillText('(含width, height, entities)', width/2, height/2 + 20);
        }
      });
  },

  setupMapClickEvent() {
    // 事件通过 WXML 的 bindtouchstart='onMapCanvasTouchStart' 绑定
    // 此函数仅用于逻辑分离或未来扩展
  },

  selectCoordinateFromMap() {
    if (!this.data.mapInfo.jsonContent || !this.validateMapJSON(this.data.mapInfo.jsonContent)) {
      wx.showModal({ title: '提示', content: '请先上传有效的地图', showCancel: false }); return;
    }
    const currentBeacon = {...this.data.editingBeacon};
    this.setData({
      showBeaconModal: false, // 隐藏原弹窗
      tempBeaconData: currentBeacon, // 保存当前编辑数据
      activeTab: 'map', // 切换到地图页
      coordSelectMode: true, // 开启选点模式
      tempSelectedCoords: null // 清空上次选择
    });
    setTimeout(() => { this.initMapPreview(); }, 100); // 确保地图绘制
    wx.showToast({ title: '请在地图上点击选择位置', icon: 'none', duration: 2000 });
  },

  onMapCanvasTouchStart(e) {
    if (!this.data.coordSelectMode) { return; }
    const touch = e.touches[0];
    const mapCoords = this.pixelToMeter(touch.x, touch.y);
    if (!mapCoords) {
      wx.showToast({ title: '请在地图区域内点击', icon: 'none' }); return;
    }
    this.setData({
        tempSelectedCoords: { x: mapCoords.x, y: mapCoords.y, pixelX: touch.x, pixelY: touch.y }
    });
    this.drawSelectedPoint(); // 绘制选中点反馈
    wx.showToast({ title: '点击"确认"使用该位置', icon: 'none', duration: 1500 });
  },

  // 将像素坐标转换为地图米坐标
  pixelToMeter(pixelX, pixelY) {
    const { mapScale, mapOffset, mapSize } = this; // 使用实例变量
    if (mapScale <= 0 || !mapSize || mapSize.width === undefined || mapSize.height === undefined) return null;
    // 检查点击是否在绘制的地图区域内 (基于offset和缩放后的尺寸)
    const mapDrawWidth = mapSize.width * mapScale;
    const mapDrawHeight = mapSize.height * mapScale;
    if (pixelX < mapOffset.x || pixelX > mapOffset.x + mapDrawWidth ||
        pixelY < mapOffset.y || pixelY > mapOffset.y + mapDrawHeight) {
      return null; // 点击在地图边界外
    }
    // 计算米坐标 (注意Y轴反转)
    const x = (pixelX - mapOffset.x) / mapScale;
    const y = mapSize.height - ((pixelY - mapOffset.y) / mapScale);
    return { x: parseFloat(x.toFixed(2)), y: parseFloat(y.toFixed(2)) };
  },

  // 将地图米坐标转换为像素坐标
  meterToPixel(meterX, meterY) {
    const { mapScale, mapOffset, mapSize } = this; // 使用实例变量
    if (!mapSize || mapSize.height === undefined || mapSize.width === undefined || mapScale === undefined || !mapOffset) return null;
    const x = mapOffset.x + meterX * mapScale;
    const y = mapOffset.y + (mapSize.height - meterY) * mapScale; // Y轴反转
    return { x, y };
  },

  drawSelectedPoint() {
    if (!this.canvasContext || !this.data.tempSelectedCoords) return;
    const ctx = this.canvasContext;
    const { x, y, pixelX, pixelY } = this.data.tempSelectedCoords;
    // 重绘地图和Beacons (避免选中点残留)
    this.drawJSONMap(ctx, this.canvasInstance.width / wx.getSystemInfoSync().pixelRatio, this.canvasInstance.height / wx.getSystemInfoSync().pixelRatio);
    // 绘制选中点标记
    ctx.beginPath();
    ctx.arc(pixelX, pixelY, 8, 0, Math.PI * 2); ctx.fillStyle = 'rgba(255, 0, 0, 0.7)'; ctx.fill();
    ctx.strokeStyle = 'white'; ctx.lineWidth = 2; ctx.stroke();
    // 绘制坐标文本
    ctx.font = '12px sans-serif'; ctx.fillStyle = 'white'; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    ctx.fillText(`(${x.toFixed(1)}, ${y.toFixed(1)})`, pixelX, pixelY - 12);
    // 恢复默认对齐方式
    ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';
  },

  coordinateSelectionCleanup() {
      this.setData({ tempSelectedCoords: null, coordSelectMode: false });
      // 如果在地图tab，重绘地图以清除选中点
      if (this.data.activeTab === 'map') {
          if (this.canvasContext && this.data.mapInfo && this.data.mapInfo.jsonContent) {
              this.drawJSONMap(this.canvasContext, this.canvasInstance.width / wx.getSystemInfoSync().pixelRatio, this.canvasInstance.height / wx.getSystemInfoSync().pixelRatio);
        } else {
              this.initMapPreview(); // 尝试重新初始化以显示提示
          }
      }
  },

  cancelCoordinateSelection() {
      const tempBeacon = this.data.tempBeaconData;
    this.setData({
          coordSelectMode: false,
          tempSelectedCoords: null,
          tempBeaconData: null,
          activeTab: 'beacon', // 切回Beacon Tab
          showBeaconModal: true, // 重新显示Beacon编辑弹窗
          editingBeacon: tempBeacon || this.data.editingBeacon // 恢复之前的Beacon数据
      });
      // 不需要手动重绘，切换tab会触发onShow逻辑
  },

  confirmCoordinateSelection() {
    const { tempSelectedCoords, tempBeaconData } = this.data;
    if (!tempSelectedCoords) {
      wx.showToast({ title: '请先在地图上选择坐标', icon: 'none' }); return;
    }
    if (!tempBeaconData) { console.error('没有临时Beacon数据'); return; }

    const updatedBeacon = {
        ...tempBeaconData,
        x: tempSelectedCoords.x,
        y: tempSelectedCoords.y
    };

    this.setData({
      coordSelectMode: false,
      tempSelectedCoords: null,
      tempBeaconData: null,
      activeTab: 'beacon', // 切回Beacon Tab
      showBeaconModal: true, // 重新显示Beacon编辑弹窗
      editingBeacon: updatedBeacon // 将带坐标的数据填回编辑框
    });
    // 不需要手动重绘，切换tab会触发onShow逻辑
  },

  // --- 地图绘制 ---
  drawJSONMap(ctx, canvasWidth, canvasHeight) {
    const fullConfig = this.data.mapInfo.jsonContent;
    // Validate that we have the map object within the loaded config
    if (!fullConfig || typeof fullConfig.map !== 'object' || !this.validateMapJSON(fullConfig)) { 
        console.error('[drawJSONMap] Invalid or missing map data structure.');
        // Draw placeholder text if data is invalid after loading
        ctx.fillStyle = '#666666'; ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText('无效或缺失地图数据', canvasWidth / 2, canvasHeight / 2 - 10);
        ctx.textAlign = 'start'; // Reset alignment
        return; 
    }

    const jsonData = fullConfig.map; // Use the nested map object for drawing
    const mapWidth = jsonData.width; 
    const mapHeight = jsonData.height;
    const mapEntities = jsonData.entities || []; // Use entities from the nested map object

    // Calculation of scale/offset remains the same, using mapWidth/mapHeight
    const scale = Math.min((canvasWidth - 40) / mapWidth, (canvasHeight - 40) / mapHeight) * 0.9;
    const offsetX = (canvasWidth - mapWidth * scale) / 2;
    const offsetY = (canvasHeight - mapHeight * scale) / 2;
    
    // 保存绘制参数到实例变量
    this.mapScale = scale;
    this.mapOffset = { x: offsetX, y: offsetY };
    this.mapSize = { width: mapWidth, height: mapHeight };
    
    // 清空画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx.fillStyle = '#f8f8f8'; ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // 绘制网格 (1米间隔)
    ctx.strokeStyle = '#eeeeee'; ctx.lineWidth = 0.5;
    for (let y = 0; y <= mapHeight; y += 1) { const screenY = this.meterToPixel(0, y)?.y; if (screenY === null) continue; ctx.beginPath(); ctx.moveTo(offsetX, screenY); ctx.lineTo(offsetX + mapWidth * scale, screenY); ctx.stroke(); }
    for (let x = 0; x <= mapWidth; x += 1) { const screenX = this.meterToPixel(x, 0)?.x; if (screenX === null) continue; ctx.beginPath(); ctx.moveTo(screenX, offsetY); ctx.lineTo(screenX, offsetY + mapHeight * scale); ctx.stroke(); }
    
    // 绘制地图边界
    ctx.strokeStyle = '#999999'; ctx.lineWidth = 1;
    ctx.strokeRect(offsetX, offsetY, mapWidth * scale, mapHeight * scale);

    // 绘制地图实体 (只处理polyline)
    ctx.strokeStyle = '#333333'; ctx.lineWidth = 1.5;
    mapEntities.forEach(entity => { // Iterate through mapEntities from the nested map object
      if (entity && entity.type === 'polyline' && Array.isArray(entity.points) && entity.points.length >= 2) {
      ctx.beginPath();
        const startPixel = this.meterToPixel(entity.points[0][0], entity.points[0][1]);
        if (!startPixel) return;
        ctx.moveTo(startPixel.x, startPixel.y);
        for (let i = 1; i < entity.points.length; i++) {
          const pixel = this.meterToPixel(entity.points[i][0], entity.points[i][1]);
          if (pixel) ctx.lineTo(pixel.x, pixel.y);
        }
        if (entity.closed) ctx.closePath();
        // 设置样式
        ctx.strokeStyle = entity.strokeColor || entity.color || '#555555';
        ctx.lineWidth = entity.lineWidth || 1.5;
        if (entity.fill || entity.fillColor) {
          ctx.fillStyle = entity.fillColor || 'rgba(220, 220, 220, 0.5)';
          ctx.fill();
        }
      ctx.stroke();
    }
    });

    // 绘制坐标轴标签 (简化)
    ctx.fillStyle = '#666666'; ctx.font = '10px sans-serif';
    for (let x = 0; x <= mapWidth; x += Math.max(1, Math.floor(mapWidth / 10))) { const px = this.meterToPixel(x, 0)?.x; if(px === null) continue; ctx.fillText(x.toString(), px - 3, offsetY + mapHeight * scale + 12); }
    for (let y = 0; y <= mapHeight; y += Math.max(1, Math.floor(mapHeight / 8))) { const py = this.meterToPixel(0, y)?.y; if(py === null) continue; ctx.fillText(y.toString(), offsetX - 15, py + 4); }

    // 最后绘制Beacons
    this.drawBeaconsOnMap(ctx);
  },

  drawBeaconsOnMap(ctx) {
    const beacons = this.data.beacons;
    if (!beacons || beacons.length === 0) return;
    beacons.forEach((beacon, index) => {
      const pixelCoords = this.meterToPixel(beacon.x, beacon.y);
      if (!pixelCoords) { return; }
      const x = pixelCoords.x; const y = pixelCoords.y;
      // Draw circles (unchanged)
      ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2); ctx.fillStyle = 'rgba(51, 102, 204, 0.2)'; ctx.fill();
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fillStyle = 'rgba(51, 102, 204, 0.7)'; ctx.fill();
      ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.stroke();
      
      // --- FIX: Draw only displayName in center --- 
      let label = beacon.displayName || 'No Name'; // Use displayName, fallback to 'No Name'
      let fontSize = 10;
      if (label.length > 6) fontSize = 8;
      if (label.length > 10) fontSize = 6; 
      
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = '#333333'; 
      ctx.textAlign = 'center'; 
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x, y);
      // --- END FIX ---
    });
    // Restore default alignment
    ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';
  },

  // --- 文件上传与验证 ---
  uploadMap() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['json'],
      success: (res) => {
        if (!res.tempFiles || !res.tempFiles.length) {
          wx.showModal({ title: '上传失败', content: '未能获取所选文件', showCancel: false }); return;
        }
        const tempFilePath = res.tempFiles[0].path;
        wx.showLoading({ title: '解析地图文件...', mask: true });
        wx.getFileSystemManager().readFile({
          filePath: tempFilePath,
          encoding: 'utf8',
          success: (readRes) => {
            wx.hideLoading();
            try {
              if (!readRes || !readRes.data) { throw new Error('文件内容为空'); }
              let jsonData;
              try { jsonData = JSON.parse(readRes.data); }
              catch (parseErr) { throw new Error('文件不是有效的JSON格式: ' + parseErr.message); }

              if (!this.validateMapJSON(jsonData)) {
                throw new Error('地图文件格式无效，请检查width/height/entities');
              }
              // 更新地图数据，但不立即保存
              this.setData({ 
                  'mapInfo.jsonContent': jsonData, 
                  'mapInfo.fileType': 'json' 
              }, () => {
                  // setData 回调中切换tab并初始化预览
                  this.setData({ activeTab: 'map' }, () => {
                      wx.nextTick(() => { // 确保tab切换渲染完成后再初始化预览
                         this.initMapPreview(); 
                         wx.showToast({ title: '地图加载成功，请保存', icon: 'success', duration: 2000 });
                      });
                  });
              });
            } catch (e) {
              wx.showModal({ title: '解析错误', content: e.message, showCancel: false });
            }
          },
          fail: (err) => {
            wx.hideLoading();
            console.error('读取文件失败:', err);
            wx.showModal({ title: '读取失败', content: '无法读取文件: ' + (err.errMsg || '未知错误'), showCancel: false });
          }
        });
      },
      fail: (err) => {
        if (err.errMsg.indexOf('cancel') === -1) {
          wx.showToast({ title: '选择文件失败', icon: 'none' });
        }
      }
    });
  },

  validateMapJSON(jsonData) {
    // Basic validation: check for map and beacons keys
    return jsonData && typeof jsonData.map === 'object' && Array.isArray(jsonData.beacons);
  },

  toggleDebugInfo: function() {
    this.setData({
      showDebugDetails: !this.data.showDebugDetails
    });
    console.log("Toggled debug info visibility to:", this.data.showDebugDetails);
    // Consider if you need to refresh what 'latestBluetoothError' shows, 
    // but it should ideally be updated when the error actually occurs.
  },

  exportConfig() {
    console.log('Exporting configuration...');
    const mapInfoContent = this.data.mapInfo.jsonContent;
    const rawBeacons = this.data.beacons || [];
    const signalFactor = parseFloat(this.data.signalPathLossExponent) || 2.5;

    if (!mapInfoContent || typeof mapInfoContent.map !== 'object') {
      wx.showToast({ title: '地图数据无效，无法导出', icon: 'none' });
      return;
    }

    // Extract the actual map object (width, height, entities, etc.)
    const mapToExport = { ...mapInfoContent.map }; // Shallow copy to avoid modifying original state if needed

    // Prepare beacons for export, ensuring macAddress is present
    const exportableBeacons = rawBeacons.map(beacon => {
      // Ensure all numeric fields are actual numbers, not strings
      const major = parseInt(beacon.major);
      const minor = parseInt(beacon.minor);
      const x = parseFloat(beacon.x);
      const y = parseFloat(beacon.y);
      const txPower = parseInt(beacon.txPower);

      const preparedBeacon = {
        uuid: beacon.uuid || '', // Default to empty string if somehow missing
        major: !isNaN(major) ? major : 0,
        minor: !isNaN(minor) ? minor : 0,
        x: !isNaN(x) ? x : 0,
        y: !isNaN(y) ? y : 0,
        txPower: !isNaN(txPower) ? txPower : -59,
        displayName: beacon.displayName || '',
        // Backend expects 'macAddress'. Use miniprogram's 'deviceId' for this.
        // If deviceId is missing, this beacon might fail backend validation or require a placeholder.
        // For now, we directly map it. User needs to ensure deviceId is populated in miniprogram.
        macAddress: beacon.deviceId || '' // Or some placeholder like `UNKNOWN_MAC_${index}` if required
      };
      // Optionally, include deviceId if the backend model also has a separate deviceId field
      // if (beacon.deviceId) {
      //   preparedBeacon.deviceId = beacon.deviceId; 
      // }
      return preparedBeacon;
    });

    const settingsToExport = {
      signalPropagationFactor: signalFactor
      // Add other settings if the backend expects them under a 'settings' object
    };

    const configToExport = {
      map: mapToExport, // Use the extracted map object
      beacons: exportableBeacons,
      settings: settingsToExport
    };

    try {
      const jsonString = JSON.stringify(configToExport, null, 2); // Pretty print JSON
      wx.setClipboardData({
        data: jsonString,
        success: () => {
          wx.showToast({ title: '配置已复制到剪贴板', icon: 'success' });
        },
        fail: (err) => {
          console.error('复制到剪贴板失败:', err);
          wx.showModal({
            title: '复制失败',
            content: '无法将配置复制到剪贴板。请检查小程序权限或手动复制以下内容。\n\n' + jsonString,
            showCancel: false,
            confirmText: '知道了'
          });
        }
      });
    } catch (e) {
      console.error('导出配置失败 (JSON序列化错误):', e);
      wx.showToast({ title: '导出失败: JSON错误', icon: 'none' });
    }
  },
}); 
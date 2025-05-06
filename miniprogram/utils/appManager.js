/**
 * 应用程序管理器 - Refactored for Config Only
 * Manages configuration loading/saving and Bluetooth state for scanning.
 */

const beaconManager = require('./beaconManager');
const jsonMapRenderer = require('./jsonMapRenderer'); // Keep for map preview in config?
// const positionCalculator = require('./positionCalculator'); // REMOVED
// const KalmanFilter = require('./kalmanFilter'); // REMOVED

// 全局状态 - Simplified
let state = {
  initialized: false,
  // locating: false, // REMOVED
  hasMap: false,
  configuredBeaconCount: 0,
  bluetoothState: beaconManager.BLUETOOTH_STATE.CLOSED, // Still needed for scanning
  // lastPosition: null, // REMOVED
  // positionTimestamp: 0, // REMOVED
  // positionCount: 0, // REMOVED
  // detectedBeacons: [], // REMOVED - Config page scan handles its own list
  errorMessage: null
};

// 存储命名空间 (Keep)
const STORAGE_KEYS = {
  MAP_INFO: 'app_map_info',
  BEACONS: 'app_beacons',
  SIGNAL_FACTOR: 'app_signal_factor', // Kept for direct saving, though included in SETTINGS
  SETTINGS: 'app_settings' // General settings object storage key
};

// 全局设置 - Simplified
let settings = {
  // positioningMethod: positionCalculator.POSITIONING_METHOD.TRILATERATION, // REMOVED
  // enableTrajectory: true, // REMOVED
  // showBeaconInfo: true, // REMOVED
  signalFactor: 2.5, // Default signal factor
  debugMode: false // Keep debug mode? Could be useful.
};

// 回调函数 - Simplified
let callbacks = {
  // onPositionUpdate: null, // REMOVED
  onStateChange: null,
  onBluetoothStateChange: null,
  onError: null,
  onMapLoaded: null, // For config page map preview
  onBeaconsConfigured: null // For config page beacon list
};

// REMOVED: Kalman Filter Instances & Config
// REMOVED: Calibration State

/**
 * 初始化应用程序管理器 - Simplified
 * @param {Object} options 初始化选项
 * @returns {Promise} 初始化结果
 */
function init(options = {}) {
  return new Promise((resolve, reject) => {
    if (state.initialized) {
      resolve(true);
      return;
    }
    console.log('初始化应用程序管理器 (配置模式)...');
    try {
      if (options.callbacks) {
        setCallbacks(options.callbacks);
      }
      // Only init beaconManager for scanning features & Bluetooth state
      beaconManager.init({
        callbacks: {
          // onBeaconsDetected: handleBeaconsDetected, // REMOVED - Config handles scan results directly
          onBluetoothStateChanged: handleBluetoothStateChanged, // Keep for state display
          onError: handleError // Keep for error handling
        }
      })
      .then(() => loadStoredData()) // Load config data
      .then(() => {
        state.initialized = true;
        updateState(); // Update initial state based on loaded data
        console.log('应用程序管理器初始化完成 (配置模式)');
        resolve(true);
      })
      .catch(err => {
        console.error('初始化应用程序管理器失败:', err);
        state.errorMessage = '初始化失败: ' + (err.message || err);
        updateState();
        reject(err);
      });
    } catch (err) {
      console.error('初始化应用程序管理器发生异常:', err);
      state.errorMessage = '初始化异常: ' + (err.message || err);
      updateState();
      reject(err);
    }
  });
}

/**
 * 设置回调函数
 * @param {Object} newCallbacks 回调函数
 */
function setCallbacks(newCallbacks) {
  if (typeof newCallbacks !== 'object') return;
  // 更新回调
  for (const key in newCallbacks) {
    if (typeof newCallbacks[key] === 'function' && callbacks.hasOwnProperty(key)) {
      callbacks[key] = newCallbacks[key];
    }
  }
}

/**
 * 加载存储的数据
 * @returns {Promise} 加载结果
 */
function loadStoredData() {
  return Promise.allSettled([
    loadMapFromStorage(),
    loadBeaconsFromStorage(),
    loadSettingsFromStorage(), // Load combined settings
  ])
  .then(results => {
    console.log('存储数据加载完成:',
      `Map=${results[0].status}, Beacons=${results[1].status}, Settings=${results[2].status}`
    );
    results.forEach(result => {
      if (result.status === 'rejected') {
        console.warn('加载部分存储数据失败:', result.reason);
      }
    });
    return true;
  });
}

/**
 * 从存储加载地图
 * @returns {Promise} 加载结果
 */
function loadMapFromStorage() {
  return new Promise((resolve, reject) => {
    try {
      const mapInfoStr = wx.getStorageSync(STORAGE_KEYS.MAP_INFO);
      if (!mapInfoStr) {
        state.hasMap = false;
        jsonMapRenderer.setMapInfo(null); // Clear renderer map info
        updateState();
        resolve(false);
        return;
      }
      let mapInfo;
      try {
        mapInfo = JSON.parse(mapInfoStr);
      } catch (parseErr) {
        console.error('地图数据解析失败:', parseErr);
        reject(new Error('地图数据格式无效'));
        return;
      }
      if (!mapInfo || typeof mapInfo.width !== 'number' || typeof mapInfo.height !== 'number' || !Array.isArray(mapInfo.entities)) {
        console.warn('存储的地图数据无效, 结构:', JSON.stringify({ hasWidth: typeof mapInfo.width === 'number', hasHeight: typeof mapInfo.height === 'number', hasEntities: Array.isArray(mapInfo.entities) }));
        reject(new Error('地图数据结构无效'));
        return;
      }
      state.hasMap = true;
      state.errorMessage = null;
      // Update renderer only if map is valid
      jsonMapRenderer.setMapInfo(mapInfo);
      updateState(); // Update after setting map status
      if (typeof callbacks.onMapLoaded === 'function') {
        callbacks.onMapLoaded(mapInfo);
      }
      resolve(true);
    } catch (err) {
      console.error('从存储加载地图失败:', err);
      state.hasMap = false;
      state.errorMessage = '加载地图失败: ' + (err.message || String(err));
      jsonMapRenderer.setMapInfo(null); // Clear renderer map info on error
      updateState();
      reject(err);
    }
  });
}

/**
 * 从存储加载信标配置
 * @returns {Promise} 加载结果
 */
function loadBeaconsFromStorage() {
  return new Promise((resolve) => {
    let beacons = [];
    try {
      const beaconsStr = wx.getStorageSync(STORAGE_KEYS.BEACONS);
      if (beaconsStr) {
        try {
          beacons = JSON.parse(beaconsStr);
          if (!Array.isArray(beacons)) {
            console.warn('存储的信标数据不是数组，重置为空数组');
            beacons = [];
          }
        } catch (parseErr) {
          console.error('信标数据解析失败:', parseErr);
          state.errorMessage = '信标数据格式无效';
          beacons = [];
        }
      } else {
        console.log('存储中无信标数据');
      }
    } catch (err) {
      console.error('从存储加载信标失败:', err);
      state.errorMessage = '加载信标失败: ' + (err.message || String(err));
      beacons = []; // Ensure beacons is an array on error
    }
    state.configuredBeaconCount = beacons.length;
    beaconManager.setConfiguredBeacons(beacons); // Update beaconManager's list
    updateState();
    if (typeof callbacks.onBeaconsConfigured === 'function') {
      callbacks.onBeaconsConfigured(beacons); // Notify listeners
    }
    resolve(true); // Resolve even if loading failed, state is handled
  });
}

/**
 * 从存储加载设置 (包括信号因子和调试模式)
 * @returns {Promise} 加载结果
 */
function loadSettingsFromStorage() {
    return new Promise((resolve) => {
        try {
            const settingsStr = wx.getStorageSync(STORAGE_KEYS.SETTINGS);
            if (settingsStr) {
                const loadedSettings = JSON.parse(settingsStr);
                // Validate and merge loaded settings
                if (typeof loadedSettings.signalFactor === 'number' && loadedSettings.signalFactor > 0) {
                    settings.signalFactor = loadedSettings.signalFactor;
                } else {
                    console.warn('存储的信号因子无效，使用默认值:', settings.signalFactor);
                }
                if (typeof loadedSettings.debugMode === 'boolean' && loadedSettings.debugMode === true) {
                    settings.debugMode = loadedSettings.debugMode;
                }
                console.log('从存储加载设置:', settings);
            } else {
                console.log('未找到存储的设置，使用默认值');
                // Keep default settings
            }
        } catch (e) {
            console.error('加载设置失败:', e);
            // Keep default settings on error
        }
        // Update positionCalculator if it exists and has the method (though positionCalculator itself might be removed)
        // if (positionCalculator && typeof positionCalculator.setSignalPathLossExponent === 'function') {
        //     positionCalculator.setSignalPathLossExponent(settings.signalFactor);
        // }
        // Apply debug mode setting if relevant elsewhere
        resolve(true);
    });
}


/**
 * 保存地图到存储
 * @param {Object} mapInfo 地图信息
 * @returns {Promise} 保存结果
 */
function saveMapToStorage(mapInfo) {
  return new Promise((resolve, reject) => {
    // Validate before saving
    if (!mapInfo || typeof mapInfo.width !== 'number' || typeof mapInfo.height !== 'number' || !Array.isArray(mapInfo.entities)) {
      const errorMsg = '尝试保存无效的地图数据';
      console.error(errorMsg);
      state.errorMessage = errorMsg;
      updateState();
      reject(new Error(errorMsg));
      return;
    }
    console.log('保存地图到存储...');
    wx.setStorage({
      key: STORAGE_KEYS.MAP_INFO,
      data: JSON.stringify(mapInfo), // Always store as string
      success() {
        console.log('地图保存成功');
        state.hasMap = true;
        state.errorMessage = null;
        // Update renderer after successful save
        jsonMapRenderer.setMapInfo(mapInfo);
        updateState();
        if (typeof callbacks.onMapLoaded === 'function') {
            callbacks.onMapLoaded(mapInfo); // Notify map update
        }
        resolve(true);
      },
      fail(err) {
        console.error('地图保存失败:', err);
        state.errorMessage = '地图保存失败: ' + (err.errMsg || err);
        updateState();
        reject(err);
      }
    });
  });
}

/**
 * 保存信标配置到存储
 * @param {Array} beacons 信标列表
 * @returns {Promise} 保存结果
 */
function saveBeaconsToStorage(beacons) {
  return new Promise((resolve, reject) => {
    if (!Array.isArray(beacons)) {
      const errorMsg = '尝试保存无效的信标数据 (非数组)';
      console.error(errorMsg);
      reject(new Error(errorMsg));
      return;
    }
    console.log(`保存 ${beacons.length} 个信标到存储...`);
    wx.setStorage({
      key: STORAGE_KEYS.BEACONS,
      data: JSON.stringify(beacons),
      success() {
        console.log('信标保存成功');
        state.configuredBeaconCount = beacons.length;
        beaconManager.setConfiguredBeacons(beacons); // Update manager's list
        updateState();
        if (typeof callbacks.onBeaconsConfigured === 'function') {
          callbacks.onBeaconsConfigured(beacons); // Notify update
        }
        resolve(true);
      },
      fail(err) {
        console.error('信标保存失败:', err);
        state.errorMessage = '信标保存失败: ' + (err.errMsg || err);
        updateState();
        reject(err);
      }
    });
  });
}

/**
 * 保存信号传播因子到存储 (独立保存)
 * @param {number} factor 信号因子
 * @returns {Promise} 保存结果
 */
function saveSignalFactorToStorage(factor) {
    return new Promise((resolve, reject) => {
        if (typeof factor !== 'number' || factor <= 0) {
            reject(new Error('无效的信号因子'));
            return;
        }
        settings.signalFactor = factor; // Update in-memory settings
        // Update calculator if exists (though likely removed)
        // if (positionCalculator && typeof positionCalculator.setSignalPathLossExponent === 'function') {
        //     positionCalculator.setSignalPathLossExponent(factor);
        // }
        // Save the entire settings object now
        saveSettingsToStorage()
            .then(resolve)
            .catch(reject);

        // Kept old direct save logic commented out, prefer saving whole object
        /*
        wx.setStorage({
            key: STORAGE_KEYS.SIGNAL_FACTOR, // Use dedicated key if needed, but settings obj is better
            data: factor.toString(),
            success() {
                console.log('信号因子保存成功:', factor);
                resolve(true);
            },
            fail(err) {
                console.error('信号因子保存失败:', err);
                reject(err);
            }
        });
        */
    });
}

/**
 * 保存设置对象到存储
 * @returns {Promise} 保存结果
 */
function saveSettingsToStorage() {
    return new Promise((resolve, reject) => {
        console.log('保存设置到存储:', settings);
        wx.setStorage({
            key: STORAGE_KEYS.SETTINGS,
            data: JSON.stringify(settings),
            success() {
                console.log('设置保存成功');
                resolve(true);
            },
            fail(err) {
                console.error('设置保存失败:', err);
                reject(err);
            }
        });
    });
}


/**
 * 更新设置
 * @param {Object} newSettings 新设置
 */
function updateSettings(newSettings) {
    if (typeof newSettings !== 'object' || newSettings === null) return;
    let changed = false;
    if (typeof newSettings.signalFactor === 'number' && newSettings.signalFactor > 0 && settings.signalFactor !== newSettings.signalFactor) {
        settings.signalFactor = newSettings.signalFactor;
        // Update calculator if exists
        // if (positionCalculator && typeof positionCalculator.setSignalPathLossExponent === 'function') {
        //     positionCalculator.setSignalPathLossExponent(settings.signalFactor);
        // }
        changed = true;
    }
    if (typeof newSettings.debugMode === 'boolean' && settings.debugMode !== newSettings.debugMode) {
        settings.debugMode = newSettings.debugMode;
        changed = true;
    }
    // Add other settings here if needed

    if (changed) {
        console.log('设置已更新:', settings);
        saveSettingsToStorage(); // Save updated settings
        updateState(); // Notify state change if settings affect state display
    }
}


// REMOVED: startLocating
// REMOVED: stopLocating
// REMOVED: handleBeaconsDetected

/**
 * 处理蓝牙状态变更
 * @param {String} newState 新状态
 */
function handleBluetoothStateChanged(newState) {
    if (state.bluetoothState !== newState) {
        console.log('蓝牙状态变更:', newState);
        state.bluetoothState = newState;
        updateState(); // Update overall state
        if (typeof callbacks.onBluetoothStateChange === 'function') {
            callbacks.onBluetoothStateChange(newState); // Notify specific listener
        }
        // Stop scanning if Bluetooth becomes unavailable (handled in beaconManager now)
        // if (newState !== beaconManager.BLUETOOTH_STATE.AVAILABLE && state.locating) {
        //     stopLocating(); // No longer relevant
        // }
    }
}

/**
 * 处理错误
 * @param {Error} error 错误对象
 */
function handleError(error) {
    console.error('appManager 捕获到错误:', error);
    state.errorMessage = error.message || String(error);
    updateState(); // Update state with error message
    if (typeof callbacks.onError === 'function') {
        callbacks.onError(error); // Notify listener
    }
    // Optionally stop operations on critical errors?
}

/**
 * 更新并通知状态变更 - Simplified
 */
function updateState() {
    // Recalculate beacon count based on beaconManager's data
    const currentBeacons = beaconManager.getConfiguredBeacons ? beaconManager.getConfiguredBeacons() : [];
    state.configuredBeaconCount = currentBeacons.length;

    if (typeof callbacks.onStateChange === 'function') {
        // Pass a copy of the simplified state
        callbacks.onStateChange({
             initialized: state.initialized,
             hasMap: state.hasMap,
             configuredBeaconCount: state.configuredBeaconCount,
             bluetoothState: state.bluetoothState,
             errorMessage: state.errorMessage
        });
    }
}

/**
 * 获取当前状态 - Simplified
 * @returns {Object} 当前状态
 */
function getState() {
    // Ensure count is up-to-date before returning
    const currentBeacons = beaconManager.getConfiguredBeacons ? beaconManager.getConfiguredBeacons() : [];
    state.configuredBeaconCount = currentBeacons.length;

    // Return a copy of the simplified state
    return {
        initialized: state.initialized,
        hasMap: state.hasMap,
        configuredBeaconCount: state.configuredBeaconCount,
        bluetoothState: state.bluetoothState,
        errorMessage: state.errorMessage
        // REMOVED: locating, lastPosition, positionTimestamp, positionCount, detectedBeacons
    };
}

/**
 * 获取当前设置
 * @returns {Object} 当前设置
 */
function getSettings() {
  return { ...settings }; // 返回副本
}

// --- Map Rendering functions (kept for config preview) ---

/**
 * 初始化地图渲染器
 * @param {Object} context Canvas 2D上下文
 * @param {number} width 画布宽度
 * @param {number} height 画布高度
 * @returns {boolean} 是否成功
 */
function initRenderer(context, width, height) {
    try {
        jsonMapRenderer.setCanvas(context, width, height);
        console.log('地图渲染器Canvas设置成功');
        // Load map if already available in state? Or rely on caller to call render?
        // Let's assume caller handles loading map data into renderer via loadMapData/setMapInfo
        return true;
    } catch (err) {
        console.error('设置地图渲染器Canvas失败:', err);
        handleError(new Error('设置渲染器Canvas失败: ' + err.message));
        return false;
    }
}


/**
 * 加载地图数据并更新渲染器和存储 (Used by Config Page Save)
 * @param {Object} mapData 地图数据对象
 * @returns {Promise}
 */
function loadMapData(mapData) {
    return new Promise((resolve, reject) => {
        // Validate the map data first
        if (!mapData || typeof mapData.width !== 'number' || typeof mapData.height !== 'number' || !Array.isArray(mapData.entities)) {
            const errorMsg = '提供的地图数据无效';
            console.error(errorMsg, mapData);
            handleError(new Error(errorMsg));
            reject(new Error(errorMsg));
            return;
        }

        console.log('加载并保存地图数据...');
        // 1. Update renderer
        try {
            const success = jsonMapRenderer.setMapInfo(mapData);
            if (!success) {
                // This case might not happen if validation passes, but handle defensively
                throw new Error('jsonMapRenderer.setMapInfo返回false');
            }
            console.log('地图数据已设置到渲染器');
        } catch (renderErr) {
            console.error('设置地图到渲染器失败:', renderErr);
            handleError(new Error('设置地图渲染器失败: ' + renderErr.message));
            reject(renderErr); // Reject the promise if setting renderer fails
            return;
        }

        // 2. Save to storage
        saveMapToStorage(mapData)
            .then(() => {
                console.log('loadMapData: 地图数据加载、渲染设置、存储均成功');
                resolve(true); // Resolve outer promise only after saving is confirmed
            })
            .catch(saveErr => {
                console.error('loadMapData: 地图数据设置到渲染器成功，但保存到存储失败:', saveErr);
                // Error already handled in saveMapToStorage, just reject outer promise
                reject(saveErr);
            });
    });
}


/**
 * 渲染地图 (Used by Config Page Preview?)
 * @param {Object} options 渲染选项 (Optional)
 * @returns {boolean} 是否成功
 */
function render(options = {}) {
    // Simplified render options for config preview
    const renderOptions = {
        showGrid: options.showGrid !== undefined ? options.showGrid : true,
        showAxes: options.showAxes !== undefined ? options.showAxes : true,
        showMap: true, // Always show map entities
        showBeacons: true, // Always show configured beacons
        showPosition: false, // Never show position
        showTrajectory: false // Never show trajectory
    };

    try {
        // Get beacons directly from beaconManager to ensure consistency
        const configuredBeacons = beaconManager.getConfiguredBeacons ? beaconManager.getConfiguredBeacons() : [];
        // console.log('渲染地图，信标数量:', configuredBeacons.length); // Debug log
        const success = jsonMapRenderer.render(configuredBeacons, [], null, renderOptions); // Pass empty trajectory, null position
        if (!success) {
            console.warn('地图渲染器render方法返回false');
        }
        return success;
    } catch (err) {
        console.error('渲染地图时发生错误:', err);
        handleError(new Error('地图渲染失败: ' + err.message));
        return false;
    }
}


/**
 * 获取渲染器状态 (Used by Config Page Preview?)
 * @returns {Object | null} 渲染器状态
 */
function getRendererState() {
    try {
        return jsonMapRenderer.getRendererState();
    } catch (err) {
        console.error('获取渲染器状态失败:', err);
        return null;
    }
}

// REMOVED: clearTrajectoryData
// REMOVED: finishCalibration

// --- Exports ---
module.exports = {
  STORAGE_KEYS, // Export keys for config page usage
  BLUETOOTH_STATE: beaconManager.BLUETOOTH_STATE, // Export enum

  init,
  setCallbacks,
  getState,
  getSettings,
  updateSettings,

  // Config Loading/Saving
  loadMapFromStorage,
  loadBeaconsFromStorage,
  loadSettingsFromStorage, // Includes Signal Factor now
  saveMapToStorage,
  saveBeaconsToStorage,
  saveSignalFactorToStorage, // Keep for direct setting save action
  saveSettingsToStorage, // Keep for saving the whole object

  // Config Map Preview Related (Potentially)
  initRenderer,
  loadMapData, // Keep for config page map save action
  render,
  getRendererState

  // REMOVED: startLocating, stopLocating, clearTrajectoryData
}; 
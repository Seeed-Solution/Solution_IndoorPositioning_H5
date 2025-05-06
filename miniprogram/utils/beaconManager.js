/**
 * 蓝牙信标管理器
 * 负责扫描和处理蓝牙信标数据 (Refactored for Config Tool Scanning)
 */

// 蓝牙状态常量
const BLUETOOTH_STATE = {
  CLOSED: 'closed',          // 蓝牙关闭
  UNAUTHORIZED: 'unauthorized', // 未授权
  UNSUPPORTED: 'unsupported',   // 设备不支持
  AVAILABLE: 'available'      // 可用
};

// REMOVED: DISTANCE_CALIBRATION
// let signalFactor = 2.5; // Defined/Managed in appManager now or loaded directly

// REMOVED: RSSI Filter Settings
// const RSSI_FILTER_WINDOW_SIZE = 5;
// let rssiHistory = {};

const SIGNAL_FACTOR_STORAGE_KEY = 'app_signal_factor'; // Keep for direct access if needed? Or remove if only managed by appManager? Let's keep for now.

// 内部状态
let initialized = false;
let isScanning = false;
let bluetoothState = BLUETOOTH_STATE.CLOSED;
let configuredBeacons = [];
// REMOVED: Buffer related state
// let beaconBuffer = [];
// let lastBufferProcessTime = 0;
// let processTimer = null;

// 回调函数
let callbacks = {
  // onBeaconsDetected: null, // REMOVED - Config page uses wx.onBluetoothDeviceFound directly
  onBluetoothStateChanged: null,
  onError: null
};

/**
 * 初始化信标管理器
 * @param {Object} options 初始化选项
 * @returns {Promise} 初始化结果
 */
function init(options = {}) {
  return new Promise((resolve, reject) => {
    try {
      if (initialized) {
        resolve(true);
        return;
      }
      console.log('初始化信标管理器...');
      if (options.callbacks) {
        setCallbacks(options.callbacks);
      }

      // REMOVED: Loading signal factor here - assume managed by appManager or loaded by config page if needed
      
      checkBluetoothState()
        .then(state => {
          bluetoothState = state;
          console.log('蓝牙状态:', state);
          initialized = true;
          resolve(true);
        })
        .catch(err => {
          console.error('检查蓝牙状态失败:', err);
          bluetoothState = BLUETOOTH_STATE.UNSUPPORTED;
          initialized = true;
          if (callbacks.onBluetoothStateChanged) {
            callbacks.onBluetoothStateChanged(bluetoothState);
          }
          resolve(false); // Resolve false as init partially failed but manager is 'initialized'
        });
    } catch (error) {
      console.error('初始化信标管理器出错:', error);
      reject(error);
    }
  });
}

/**
 * 设置回调函数
 * @param {Object} newCallbacks 回调函数集合
 */
function setCallbacks(newCallbacks) {
    // Simplified: only handle expected callbacks
  if (typeof newCallbacks !== 'object') return;
    if (typeof newCallbacks.onBluetoothStateChanged === 'function') {
        callbacks.onBluetoothStateChanged = newCallbacks.onBluetoothStateChanged;
    }
    if (typeof newCallbacks.onError === 'function') {
        callbacks.onError = newCallbacks.onError;
  }
}

/**
 * 检查蓝牙状态
 * @returns {Promise<string>} 蓝牙状态
 */
function checkBluetoothState() {
  return new Promise((resolve, reject) => {
    wx.onBluetoothAdapterStateChange((res) => {
      const newRawState = res.available;
      let newState = newRawState ? BLUETOOTH_STATE.AVAILABLE : BLUETOOTH_STATE.CLOSED;

      if (newState !== bluetoothState) {
        console.log(`[beaconManager] 蓝牙状态改变: ${bluetoothState} -> ${newState}`);
        bluetoothState = newState;
        if (callbacks.onBluetoothStateChanged) {
          try {
            callbacks.onBluetoothStateChanged(bluetoothState);
          } catch (callbackErr) {
             console.error('[beaconManager] Error executing onBluetoothStateChanged callback:', callbackErr);
          }
        }
        // If scanning and BT becomes unavailable, stop the scan attempt internally
        if (!newRawState && isScanning) {
            console.warn('[beaconManager] Bluetooth became unavailable during scan, stopping.');
            stopScanInternal(); // Call internal stop without promise return needed here
        }
      }
    });
    
    wx.openBluetoothAdapter({
      success: (res) => {
        // Check if state changed before adapter opened successfully
        if (bluetoothState !== BLUETOOTH_STATE.AVAILABLE) {
        bluetoothState = BLUETOOTH_STATE.AVAILABLE;
        if (callbacks.onBluetoothStateChanged) {
          callbacks.onBluetoothStateChanged(bluetoothState);
            }
        }
        resolve(bluetoothState);
      },
      fail: (err) => {
        console.error('[beaconManager] openBluetoothAdapter failed:', err);
        let errorState = BLUETOOTH_STATE.CLOSED;
        if (err.errCode === 10001) {
          console.error('[beaconManager] Error: Bluetooth not enabled on device.');
          errorState = BLUETOOTH_STATE.CLOSED;
        } else if (err.errCode === 10009 || err.errMsg.includes('auth')) {
          console.error('[beaconManager] Error: Bluetooth permission denied.');
          errorState = BLUETOOTH_STATE.UNAUTHORIZED;
        } else {
          console.error('[beaconManager] Error: Bluetooth adapter unavailable or unsupported.');
          errorState = BLUETOOTH_STATE.UNSUPPORTED;
        }
        // Check if state changed
        if (bluetoothState !== errorState) {
        bluetoothState = errorState;
        if (callbacks.onBluetoothStateChanged) {
          callbacks.onBluetoothStateChanged(bluetoothState);
        }
        }
        reject(err); // Reject the promise on failure
      }
    });
  });
}

/**
 * 设置已配置的信标列表
 * @param {Array} beacons 信标数组
 * @returns {Boolean} 设置是否成功
 */
function setConfiguredBeacons(beacons) {
  if (!Array.isArray(beacons)) {
    console.error('设置信标列表失败：参数必须是数组');
    return false;
  }
  
  // 过滤并验证信标数据
  configuredBeacons = beacons.filter(beacon => {
    // 必须有UUID且为字符串
    if (!beacon.uuid || typeof beacon.uuid !== 'string') {
      console.warn('忽略无效信标：缺少UUID', beacon);
      return false;
    }
    
    // 必须有坐标且为数字
    if (typeof beacon.x !== 'number' || typeof beacon.y !== 'number') {
      console.warn('忽略无效信标：缺少有效坐标', beacon);
      return false;
    }
    
    // 必须有发射功率且为数字
    if (typeof beacon.txPower !== 'number') {
      console.warn('忽略无效信标：缺少发射功率', beacon);
      return false;
    }
    
    return true;
  });
  
  console.log('已设置', configuredBeacons.length, '个有效信标');
  return true;
}

/**
 * 获取已配置的信标列表
 * @returns {Array} 信标数组
 */
function getConfiguredBeacons() {
  return [...configuredBeacons];
}

/**
 * 开始扫描信标 (Simplified for Config Tool)
 * Note: Config page seems to call wx APIs directly, but providing this might be useful
 * if appManager needs to trigger scans later.
 * @returns {Promise} 扫描结果
 */
function startScan() {
  return new Promise((resolve, reject) => {
      if (isScanning) {
            console.log('[beaconManager] Already scanning.');
            resolve(true); // Resolve true if already scanning
            return;
          }
        console.log('[beaconManager] Starting scan...');
        checkBluetoothState() // Ensure BT is available before starting discovery
            .then(state => {
                if (state !== BLUETOOTH_STATE.AVAILABLE) {
                    throw new Error(`Cannot start scan, Bluetooth state is ${state}`);
                }
                // Start discovery using the internal helper
                return startBluetoothDiscovery();
            })
                .then(() => {
                  isScanning = true;
                console.log('[beaconManager] Scan started successfully.');
                  resolve(true);
                })
                .catch(err => {
                console.error('[beaconManager] Failed to start scan:', err);
                isScanning = false; // Ensure state is correct on failure
                if (callbacks.onError) {
                    callbacks.onError(err);
                }
          reject(err);
        });
  });
}

/**
 * 停止扫描信标 (Simplified for Config Tool)
 * @returns {Promise} 停止结果
 */
function stopScan() {
  return new Promise((resolve, reject) => {
    if (!isScanning) {
      // console.log('[beaconManager] Not scanning.');
      resolve(true); // Resolve true if not scanning
      return;
    }
    console.log('[beaconManager] Stopping scan...');
    stopScanInternal(resolve, reject);
  });
}

// Internal stop function without promise return for internal use
function stopScanInternal(resolve = () => {}, reject = () => {}) {
     isScanning = false; // Set state immediately
     wx.offBluetoothDeviceFound(onDeviceFound); // Crucial: Remove listener
    wx.stopBluetoothDevicesDiscovery({
        success: (res) => {
            console.log('[beaconManager] stopBluetoothDevicesDiscovery success.');
            // Optionally close adapter, but maybe keep it open if scans are frequent?
            // wx.closeBluetoothAdapter({
            //     success: () => console.log('[beaconManager] Bluetooth adapter closed.'),
            //     fail: (err) => console.warn('[beaconManager] Failed to close Bluetooth adapter:', err)
            // });
            resolve(true);
          },
        fail: (err) => {
            console.error('[beaconManager] stopBluetoothDevicesDiscovery failed:', err);
            // Even if stop fails, consider the scan 'stopped' from our perspective
            if (callbacks.onError) {
                 callbacks.onError(new Error('Failed to stop Bluetooth discovery'));
            }
            reject(err);
          }
  });
}

/**
 * Internal helper to start Bluetooth device discovery
 * @returns {Promise}
 */
function startBluetoothDiscovery() {
  return new Promise((resolve, reject) => {
        console.log('[beaconManager] Starting Bluetooth device discovery...');
        wx.startBluetoothDevicesDiscovery({
            allowDuplicatesKey: true, // Allow updates for RSSI - Important for config scan too
            interval: 0, // Report as fast as possible
            success: (res) => {
                console.log('[beaconManager] startBluetoothDevicesDiscovery success.');
                // Register the listener *after* successfully starting discovery
    wx.onBluetoothDeviceFound(onDeviceFound);
                resolve(res);
            },
            fail: (err) => {
                console.error('[beaconManager] startBluetoothDevicesDiscovery failed:', err);
                reject(err); // Reject the promise on failure
      }
    });
  });
}

/**
 * 处理发现的设备 (Simplified for Config Tool)
 * Config page seems to handle discovered devices directly via its own `wx.onBluetoothDeviceFound` handler.
 * This function might become redundant unless appManager calls it.
 * For now, keep it minimal, just parsing and logging.
 * @param {Object} res Event data from wx.onBluetoothDeviceFound
 */
function onDeviceFound(res) {
    if (!res || !res.devices || res.devices.length === 0) {
        // console.log('[beaconManager.onDeviceFound] No devices in event');
        return;
    }
    res.devices.forEach(device => {
        // console.log(`[beaconManager.onDeviceFound] Processing device: ${device.deviceId}`);
      processDevice(device); 
    });
}

/**
 * 处理单个设备数据 (Simplified) - Parses but doesn't filter/buffer/callback
 * @param {Object} device 设备对象
 */
function processDevice(device) {
    if (!device || !device.advertisData) {
        // console.log(`[beaconManager.processDevice] Device ${device?.deviceId} has no advertisData.`);
        return;
    }

    // Try parsing as iBeacon
    let beaconInfo = parseAdvertisDataStandard(device.advertisData);
    if (!beaconInfo) {
        beaconInfo = parseAdvertisDataAlternative(device.advertisData);
  }

    if (beaconInfo && beaconInfo.isIBeacon) {
        const fullBeaconInfo = {
            ...beaconInfo,
            rssi: device.RSSI,
            deviceId: device.deviceId,
            name: device.name,
            localName: device.localName
        };
         // Log the parsed beacon info for debugging if needed by config page developer
         // console.log('[beaconManager.processDevice] Parsed iBeacon:', fullBeaconInfo);

        // REMOVED: RSSI Filtering
        // REMOVED: Adding to buffer (addToBuffer)
    } else {
        // console.log(`[beaconManager.processDevice] Device ${device.deviceId} not parsed as iBeacon.`);
    }
}

// REMOVED: addToBuffer
// REMOVED: startBufferProcessing
// REMOVED: stopBufferProcessing
// REMOVED: processBuffer
// REMOVED: calculateDistance

// arrayToHex (Keep as potentially useful utility, though not directly used now)
function arrayToHex(array) {
  if (!array) return '';
  return Array.prototype.map.call(new Uint8Array(array), x => ('00' + x.toString(16)).slice(-2)).join('');
}

// parseAdvertisDataStandard (Keep for config scanning)
function parseAdvertisDataStandard(advertisData) {
  try {
      const dataView = new DataView(advertisData);
        // 查找 4C 00 02 15 (Apple iBeacon identifier)
        for (let i = 0; i <= dataView.byteLength - 25; i++) { // 至少需要25字节
          if (dataView.getUint8(i) === 0x4C && dataView.getUint8(i + 1) === 0x00 &&
              dataView.getUint8(i + 2) === 0x02 && dataView.getUint8(i + 3) === 0x15) {
              const startIndex = i + 4;
              let uuid = '';
              for (let j = 0; j < 16; j++) {
                  uuid += dataView.getUint8(startIndex + j).toString(16).padStart(2, '0');
                  if (j === 3 || j === 5 || j === 7 || j === 9) uuid += '-';
              }
              const major = dataView.getUint16(startIndex + 16, false); // Big-endian
              const minor = dataView.getUint16(startIndex + 18, false); // Big-endian
              const txPower = dataView.getInt8(startIndex + 20);
              return { isIBeacon: true, uuid: uuid.toUpperCase(), major, minor, txPower };
          }
      }
    } catch (e) { /* console.error('标准解析错误', e); */ } // Keep error silent
  return null;
}

// parseAdvertisDataAlternative (Keep for config scanning)
function parseAdvertisDataAlternative(advertisData) {
  try {
      const dataView = new DataView(advertisData);
        // 查找 02 15 (iBeacon type and length)
        for (let i = 0; i <= dataView.byteLength - 23; i++) { // 至少需要23字节
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
    } catch (e) { /* console.error('备用解析错误', e); */ } // Keep error silent
  return null;
}

module.exports = {
  BLUETOOTH_STATE,
  init,
  setCallbacks,
  checkBluetoothState,
  setConfiguredBeacons,
  getConfiguredBeacons,
  // setSignalFactor, // Removed - Use appManager.updateSettings or saveSignalFactorToStorage
  // getSignalFactor, // Removed - Use appManager.getSettings
  startScan, // Keep for potential external control
  stopScan   // Keep for potential external control
}; 
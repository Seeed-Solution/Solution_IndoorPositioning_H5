/**
 * 扫描管理器
 * 管理蓝牙扫描和Beacon发现
 */

/**
 * 初始化蓝牙适配器
 * @returns {Promise} 成功返回resolved Promise, 失败返回rejected Promise
 */
function initBluetooth() {
  return new Promise((resolve, reject) => {
    console.log('初始化蓝牙适配器');
    
    wx.openBluetoothAdapter({
      success: (res) => {
        console.log('蓝牙适配器初始化成功', res);
        resolve(res);
      },
      fail: (err) => {
        console.error('蓝牙适配器初始化失败', err);
        reject(err);
      }
    });
  });
}

/**
 * 关闭蓝牙适配器
 * @returns {Promise} 成功返回resolved Promise, 失败返回rejected Promise
 */
function closeBluetooth() {
  return new Promise((resolve, reject) => {
    wx.closeBluetoothAdapter({
      success: (res) => {
        console.log('蓝牙适配器已关闭');
        resolve(res);
      },
      fail: (err) => {
        console.warn('关闭蓝牙适配器失败:', err);
        reject(err);
      }
    });
  });
}

/**
 * 开始设备扫描
 * @param {Function} onDeviceFound 发现设备时的回调
 * @returns {Promise} 成功返回resolved Promise, 失败返回rejected Promise
 */
function startDeviceScan(onDeviceFound) {
  return new Promise((resolve, reject) => {
    // 先停止之前的扫描
    wx.stopBluetoothDevicesDiscovery({
      complete: () => {
        // 开始新的扫描
        wx.startBluetoothDevicesDiscovery({
          allowDuplicatesKey: true, // 允许重复上报同一设备
          success: (res) => {
            console.log('开始蓝牙设备扫描', res);
            
            // 监听新设备
            wx.onBluetoothDeviceFound((deviceRes) => {
              if (deviceRes && deviceRes.devices && deviceRes.devices.length > 0) {
                deviceRes.devices.forEach(device => {
                  if (onDeviceFound && typeof onDeviceFound === 'function') {
                    onDeviceFound(device);
                  }
                });
              }
            });
            
            resolve(res);
          },
          fail: (err) => {
            console.error('开始蓝牙设备扫描失败', err);
            reject(err);
          }
        });
      }
    });
  });
}

/**
 * 停止设备扫描
 * @returns {Promise} 成功返回resolved Promise, 失败返回rejected Promise
 */
function stopDeviceScan() {
  return new Promise((resolve, reject) => {
    wx.stopBluetoothDevicesDiscovery({
      success: (res) => {
        console.log('停止蓝牙设备扫描');
        resolve(res);
      },
      fail: (err) => {
        console.error('停止蓝牙设备扫描失败', err);
        reject(err);
      }
    });
  });
}

/**
 * 开始iBeacon扫描
 * @param {Array} uuids UUID数组
 * @param {Function} onBeaconUpdate 发现Beacon时的回调
 * @returns {Promise} 成功返回resolved Promise, 失败返回rejected Promise
 */
function startBeaconDiscovery(uuids, onBeaconUpdate) {
  // 验证UUID列表
  if (!Array.isArray(uuids) || uuids.length === 0) {
    return Promise.reject(new Error('UUID列表无效或为空'));
  }
  
  // 确保UUID格式正确（全部大写）
  const formattedUuids = uuids.map(uuid => uuid.toUpperCase());
  
  console.log('开始搜索以下UUID的Beacon:', formattedUuids);
  
  return new Promise((resolve, reject) => {
    // 先尝试停止现有的搜索
    wx.stopBeaconDiscovery({
      complete: () => {
        // 开始新的搜索
        wx.startBeaconDiscovery({
          uuids: formattedUuids,
          ignoreBluetoothAvailable: false, // 确保蓝牙可用
          success: (res) => {
            console.log('开始Beacon扫描成功:', res);
            
            // 设置更新回调
            if (onBeaconUpdate && typeof onBeaconUpdate === 'function') {
              wx.onBeaconUpdate((beaconRes) => {
                onBeaconUpdate(beaconRes);
              });
            }
            
            resolve(res);
          },
          fail: (err) => {
            console.error('开始Beacon扫描失败:', err);
            reject(err);
          }
        });
      }
    });
  });
}

/**
 * 停止iBeacon扫描
 * @returns {Promise} 成功返回resolved Promise, 失败返回rejected Promise
 */
function stopBeaconDiscovery() {
  return new Promise((resolve, reject) => {
    try {
      wx.stopBeaconDiscovery({
        success: () => {
          console.log('停止搜索iBeacon设备');
          
          // 移除监听器
          try {
            wx.offBeaconUpdate();
          } catch (e) {
            console.warn('移除Beacon监听器失败:', e);
          }
          
          resolve();
        },
        fail: (err) => {
          console.error('停止搜索iBeacon设备失败', err);
          reject(err);
        },
        complete: () => {
          // 关闭蓝牙适配器
          closeBluetooth().catch(e => console.warn('关闭蓝牙适配器失败:', e));
        }
      });
    } catch (e) {
      console.error('停止搜索iBeacon设备异常:', e);
      // 尝试关闭适配器
      closeBluetooth().catch(err => console.warn('关闭蓝牙适配器失败:', err));
      reject(e);
    }
  });
}

/**
 * 解析广播数据为iBeacon格式
 * @param {ArrayBuffer} advertisData 广播数据
 * @returns {Object|null} iBeacon对象或null
 */
function parseAdvertisData(advertisData) {
  if (!advertisData || advertisData.byteLength < 30) {
    return null;
  }

  try {
    const dataView = new DataView(advertisData);
    
    // 检查是否是iBeacon格式
    // iBeacon前缀通常是: 0x02, 0x15
    if (dataView.getUint8(0) === 0x02 && dataView.getUint8(1) === 0x15) {
      // 解析UUID (16字节)
      let uuid = '';
      for (let i = 2; i < 18; i++) {
        const hex = dataView.getUint8(i).toString(16).padStart(2, '0');
        uuid += hex;
        
        // 添加连字符以标准UUID格式展示
        if (i === 5 || i === 7 || i === 9 || i === 11) {
          uuid += '-';
        }
      }
      
      // 解析Major和Minor (各2字节)
      const major = dataView.getUint16(18, false);
      const minor = dataView.getUint16(20, false);
      
      // 解析测量功率 (1字节)
      const txPower = dataView.getInt8(22);
      
      return {
        uuid: uuid.toUpperCase(),
        major,
        minor,
        txPower,
        isBeacon: true
      };
    }
  } catch (e) {
    console.warn('解析广播数据失败:', e);
  }
  
  return null;
}

module.exports = {
  initBluetooth,
  closeBluetooth,
  startDeviceScan,
  stopDeviceScan,
  startBeaconDiscovery,
  stopBeaconDiscovery,
  parseAdvertisData
}; 
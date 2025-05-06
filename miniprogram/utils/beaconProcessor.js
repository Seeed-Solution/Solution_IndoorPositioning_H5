/**
 * Beacon数据处理模块
 * 用于处理和管理检测到的信标数据
 */

const positionCalculator = require('./positionCalculator');

// 存储检测到的信标数据的缓冲区
let beaconBuffer = [];

// 存储已知信标的RSSI滤波状态
const rssiFilterState = new Map();

/**
 * 清空信标数据缓冲区
 */
function clearBeaconBuffer() {
  beaconBuffer = [];
  rssiFilterState.clear();
  console.log('Beacon数据缓冲区已清空');
}

/**
 * 添加检测到的信标到缓冲区
 * @param {Object} beacon 检测到的信标数据
 */
function addBeaconToBuffer(beacon) {
  if (!beacon || !beacon.uuid) {
    console.warn('添加到缓冲区的Beacon数据无效');
    return;
  }
  
  // 添加时间戳
  beacon.timestamp = Date.now();
  beaconBuffer.push(beacon);
  
  // 保持缓冲区大小合理
  if (beaconBuffer.length > 100) {
    beaconBuffer.shift();
  }
}

/**
 * 获取指定时间范围内的信标数据
 * @param {Number} timeRange 时间范围（毫秒），默认为1000ms
 * @returns {Array} 该时间范围内的信标数据
 */
function getRecentBeacons(timeRange = 1000) {
  const now = Date.now();
  return beaconBuffer.filter(beacon => (now - beacon.timestamp) <= timeRange);
}

/**
 * 根据UUID合并最近的信标数据
 * 对相同UUID的信标取平均RSSI值
 * @param {Array} beacons 信标数据数组
 * @returns {Object} 以UUID为键的合并信标数据
 */
function mergeBeaconsByUUID(beacons) {
  if (!Array.isArray(beacons) || beacons.length === 0) {
    return {};
  }
  
  const mergedBeacons = {};
  
  beacons.forEach(beacon => {
    if (!beacon || !beacon.uuid) return;
    
    const uuid = beacon.uuid;
    
    if (!mergedBeacons[uuid]) {
      mergedBeacons[uuid] = {
        uuid,
        major: beacon.major,
        minor: beacon.minor,
        rssiSum: beacon.rssi,
        rssiCount: 1,
        rssi: beacon.rssi,
        timestamp: beacon.timestamp
      };
    } else {
      mergedBeacons[uuid].rssiSum += beacon.rssi;
      mergedBeacons[uuid].rssiCount += 1;
      mergedBeacons[uuid].rssi = mergedBeacons[uuid].rssiSum / mergedBeacons[uuid].rssiCount;
      
      // 更新时间戳为最新的
      if (beacon.timestamp > mergedBeacons[uuid].timestamp) {
        mergedBeacons[uuid].timestamp = beacon.timestamp;
      }
    }
  });
  
  return mergedBeacons;
}

/**
 * 应用滤波器处理RSSI信号
 * @param {String} uuid 信标UUID
 * @param {Number} rssi 当前RSSI值
 * @returns {Number} 滤波后的RSSI值
 */
function filterRSSI(uuid, rssi) {
  if (!uuid || typeof rssi !== 'number') {
    return rssi;
  }
  
  // 获取之前的滤波状态
  let state = rssiFilterState.get(uuid);
  
  // 应用卡尔曼滤波
  const filtered = positionCalculator.kalmanFilter(
    rssi, 
    state ? state.rssi : null, 
    state ? state.error : null
  );
  
  // 更新滤波状态
  rssiFilterState.set(uuid, filtered);
  
  return filtered.rssi;
}

/**
 * 将检测到的信标与已配置的信标匹配，并计算距离
 * @param {Object} detectedBeacons 检测到的信标（合并后）
 * @param {Array} configuredBeacons 已配置的信标
 * @returns {Array} 包含距离信息的信标数组
 */
function matchAndCalculateDistances(detectedBeacons, configuredBeacons) {
  if (!detectedBeacons || !Array.isArray(configuredBeacons)) {
    console.warn('无法匹配信标: 参数无效');
    return [];
  }
  
  const beaconsWithDistance = [];
  
  // 遍历已配置的信标
  configuredBeacons.forEach(configBeacon => {
    const uuid = configBeacon.uuid;
    
    // 检查是否检测到该信标
    if (detectedBeacons[uuid]) {
      const detected = detectedBeacons[uuid];
      
      // 应用RSSI滤波
      const filteredRSSI = filterRSSI(uuid, detected.rssi);
      
      // 计算距离
      const distance = positionCalculator.calculateDistance(
        filteredRSSI, 
        configBeacon.txPower
      );
      
      // 只有当能计算出有效距离时才添加
      if (distance !== null) {
        beaconsWithDistance.push({
          uuid: uuid,
          name: configBeacon.name,
          x: configBeacon.x,
          y: configBeacon.y,
          rssi: filteredRSSI,
          distance: distance,
          txPower: configBeacon.txPower
        });
      }
    }
  });
  
  return beaconsWithDistance;
}

/**
 * 处理检测到的信标数据，计算位置
 * @param {Array} configuredBeacons 已配置的信标列表
 * @param {Number} timeRange 使用多长时间范围内的信标数据（毫秒）
 * @returns {Object} 处理结果 {position, beaconsWithDistance}
 */
function processBeaconData(configuredBeacons, timeRange = 1000) {
  // 检查参数
  if (!Array.isArray(configuredBeacons) || configuredBeacons.length === 0) {
    console.warn('处理信标数据失败: 没有配置的信标');
    return {
      position: null,
      beaconsWithDistance: []
    };
  }
  
  try {
    // 获取最近的信标数据
    const recentBeacons = getRecentBeacons(timeRange);
    
    if (recentBeacons.length === 0) {
      console.log('没有检测到信标');
      return {
        position: null,
        beaconsWithDistance: []
      };
    }
    
    // 合并相同UUID的信标
    const mergedBeacons = mergeBeaconsByUUID(recentBeacons);
    
    // 匹配信标并计算距离
    const beaconsWithDistance = matchAndCalculateDistances(mergedBeacons, configuredBeacons);
    
    // 计算位置
    const position = (beaconsWithDistance.length > 0) 
      ? positionCalculator.calculatePosition(beaconsWithDistance) 
      : null;
    
    return {
      position,
      beaconsWithDistance
    };
  } catch (e) {
    console.error('处理信标数据时发生错误:', e);
    return {
      position: null,
      beaconsWithDistance: []
    };
  }
}

module.exports = {
  clearBeaconBuffer,
  addBeaconToBuffer,
  getRecentBeacons,
  mergeBeaconsByUUID,
  filterRSSI,
  matchAndCalculateDistances,
  processBeaconData
}; 
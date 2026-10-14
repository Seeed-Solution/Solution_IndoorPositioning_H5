/**
 * 平台兼容性工具函数
 * 处理不同操作系统下的MAC地址和设备ID映射
 */

/**
 * 检测当前操作系统
 * @returns {string} 'macos' | 'windows' | 'linux' | 'unknown'
 */
export function detectOperatingSystem() {
  const userAgent = navigator.userAgent.toLowerCase();
  const platform = navigator.platform.toLowerCase();
  
  if (userAgent.includes('mac') || platform.includes('mac')) {
    return 'macos';
  } else if (userAgent.includes('win') || platform.includes('win')) {
    return 'windows';
  } else if (userAgent.includes('linux') || platform.includes('linux')) {
    return 'linux';
  }
  
  return 'unknown';
}

/**
 * 根据操作系统处理beacon的MAC地址映射
 * @param {Object} beacon - beacon对象
 * @param {string} os - 操作系统类型
 * @returns {Object} 处理后的beacon对象
 */
export function processBeaconForPlatform(beacon, os = null) {
  if (!os) {
    os = detectOperatingSystem();
  }
  
  const processedBeacon = { ...beacon };
  
  // 统一处理：直接将 deviceId 映射为 macAddress，然后删除 deviceId
  if (processedBeacon.deviceId) {
    // 如果 macAddress 为空或未设置，则使用 deviceId 的值
    if (!processedBeacon.macAddress || processedBeacon.macAddress.trim() === '') {
      processedBeacon.macAddress = processedBeacon.deviceId;
      console.log(`[Platform Utils] ${os} detected: mapped deviceId "${processedBeacon.deviceId}" to macAddress`);
    }
    
    // 删除 deviceId 字段，统一使用 macAddress
    delete processedBeacon.deviceId;
    console.log(`[Platform Utils] Removed deviceId field, using macAddress: "${processedBeacon.macAddress}"`);
    
    // 为 macOS 添加虚构地址标识
    if (os === 'macos') {
      processedBeacon.is_darwin = true;
      console.log('[Platform Utils] macOS detected: marked address as virtual with is_darwin=true');
    }
  }
  
  return processedBeacon;
}

/**
 * 批量处理beacon列表的平台兼容性
 * @param {Array} beacons - beacon数组
 * @param {string} os - 操作系统类型
 * @returns {Array} 处理后的beacon数组
 */
export function processBeaconsForPlatform(beacons, os = null) {
  if (!Array.isArray(beacons)) {
    return beacons;
  }
  
  if (!os) {
    os = detectOperatingSystem();
  }
  
  console.log(`[Platform Utils] Processing ${beacons.length} beacons for platform: ${os}`);
  
  return beacons.map(beacon => processBeaconForPlatform(beacon, os));
}

/**
 * 检查当前平台是否支持MAC地址获取
 * @returns {boolean}
 */
export function isMacAddressSupported() {
  const os = detectOperatingSystem();
  return os === 'windows' || os === 'linux';
}

/**
 * 获取平台特定的MAC地址字段名
 * @returns {string} 'deviceId' | 'macAddress'
 */
export function getMacAddressFieldName() {
  return isMacAddressSupported() ? 'macAddress' : 'deviceId';
} 
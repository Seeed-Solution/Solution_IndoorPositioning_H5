/**
 * 验证工具模块
 * 提供各种数据验证函数
 */

/**
 * 验证地图JSON格式是否有效
 * @param {Object} jsonData JSON数据对象
 * @returns {Boolean} 是否有效
 */
function validateMapJSON(jsonData) {
  // 检查必须的字段
  if (!jsonData) {
    console.error('JSON数据为空');
    return false;
  }
  
  if (typeof jsonData.width !== 'number' || jsonData.width <= 0) {
    console.error('JSON地图缺少有效的width字段');
    return false;
  }
  
  if (typeof jsonData.height !== 'number' || jsonData.height <= 0) {
    console.error('JSON地图缺少有效的height字段');
    return false;
  }
  
  if (!Array.isArray(jsonData.entities)) {
    console.error('JSON地图缺少entities数组');
    return false;
  }
  
  // 检查实体是否有效
  if (jsonData.entities.length === 0) {
    console.warn('警告: 地图JSON不包含任何实体');
    // 仍然允许空地图，但提出警告
  } else {
    // 验证至少有一个有效的实体
    let hasValidEntity = false;
    for (const entity of jsonData.entities) {
      if (entity && entity.type) {
        hasValidEntity = true;
        break;
      }
    }
    
    if (!hasValidEntity) {
      console.error('JSON地图不包含任何有效实体');
      return false;
    }
  }
  
  console.log('JSON地图验证通过');
  return true;
}

/**
 * 验证UUID格式是否正确
 * @param {String} uuid 要验证的UUID
 * @returns {Boolean} 是否符合标准UUID格式
 */
function validateUUID(uuid) {
  if (!uuid) return false;
  
  // 标准UUID格式: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
  const uuidRegex = /^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/i;
  return uuidRegex.test(uuid);
}

/**
 * 验证坐标是否有效
 * @param {String|Number} value 坐标值
 * @returns {Boolean} 是否有效
 */
function validateCoordinate(value) {
  if (value === undefined || value === null || value === '') return false;
  
  const num = parseFloat(value);
  return !isNaN(num);
}

/**
 * 验证Beacon数据是否有效
 * @param {Object} beacon Beacon数据对象
 * @returns {Object} 验证结果 {isValid, errors, warnings}
 */
function validateBeacon(beacon) {
  const result = {
    isValid: true,
    errors: [],
    warnings: []
  };
  
  // 验证UUID
  if (!beacon.uuid || beacon.uuid.trim() === '') {
    result.isValid = false;
    result.errors.push('UUID不能为空');
  } else if (!validateUUID(beacon.uuid)) {
    result.warnings.push('UUID格式不标准，这可能影响Beacon识别');
  }
  
  // 验证坐标
  if (!validateCoordinate(beacon.x)) {
    result.isValid = false;
    result.errors.push('X坐标必须是有效数字');
  }
  
  if (!validateCoordinate(beacon.y)) {
    result.isValid = false;
    result.errors.push('Y坐标必须是有效数字');
  }
  
  // 验证发射功率
  if (!validateCoordinate(beacon.txPower)) {
    result.isValid = false;
    result.errors.push('发射功率必须是有效数字');
  }
  
  return result;
}

module.exports = {
  validateMapJSON,
  validateUUID,
  validateCoordinate,
  validateBeacon
}; 
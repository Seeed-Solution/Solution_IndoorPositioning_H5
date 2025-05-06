/**
 * 位置管理器模块
 * 负责基于信标数据的位置计算和跟踪
 */

// 当前位置
let currentPosition = null;
// 位置历史
let positionHistory = [];
// 最大历史记录数
const MAX_HISTORY_SIZE = 50;
// 位置更新回调
let onPositionUpdateCallback = null;
// 位置平滑参数
const POSITION_SMOOTHING_FACTOR = 0.3;
// 上次位置更新时间
let lastUpdateTime = 0;
// 调试信息
let debugInfo = {
  calculationMethod: '',
  inputBeacons: [],
  calculationTime: 0,
  errors: []
};

/**
 * 初始化位置管理器
 * @param {Function} callback 位置更新回调函数
 */
function init(callback) {
  // 重置位置数据
  currentPosition = null;
  positionHistory = [];
  lastUpdateTime = 0;
  
  // 设置回调
  if (typeof callback === 'function') {
    onPositionUpdateCallback = callback;
  }
  
  console.log('位置管理器已初始化');
  return true;
}

/**
 * 设置位置更新回调
 * @param {Function} callback 位置更新回调函数
 */
function setPositionUpdateCallback(callback) {
  if (typeof callback === 'function') {
    onPositionUpdateCallback = callback;
    return true;
  }
  return false;
}

/**
 * 获取当前位置
 * @returns {Object|null} 当前位置对象，包含x, y坐标和时间戳
 */
function getCurrentPosition() {
  return currentPosition ? { ...currentPosition } : null;
}

/**
 * 获取位置历史
 * @param {Number} limit 限制返回的历史记录数量
 * @returns {Array} 位置历史数组
 */
function getPositionHistory(limit = MAX_HISTORY_SIZE) {
  if (limit <= 0 || limit > positionHistory.length) {
    return [...positionHistory];
  }
  return positionHistory.slice(positionHistory.length - limit);
}

/**
 * 清除位置历史
 */
function clearPositionHistory() {
  positionHistory = [];
  console.log('位置历史已清除');
}

/**
 * 根据信标数据更新位置
 * @param {Array} beacons 检测到的信标数据，包含距离信息
 * @returns {Object|null} 计算的位置对象
 */
function updatePosition(beacons) {
  if (!Array.isArray(beacons) || beacons.length === 0) {
    console.log('没有信标数据可用于位置更新');
    return null;
  }
  
  // 重置调试信息
  debugInfo = {
    calculationMethod: '',
    inputBeacons: beacons.map(b => ({
      uuid: b.uuid, 
      distance: b.distance, 
      x: b.x, 
      y: b.y
    })),
    calculationTime: 0,
    errors: []
  };
  
  // 过滤有效的信标（有距离和坐标信息）
  const validBeacons = beacons.filter(beacon => {
    const isValid = 
      typeof beacon.distance === 'number' && 
      beacon.distance > 0 &&
      typeof beacon.x === 'number' && 
      typeof beacon.y === 'number';
    
    if (!isValid) {
      debugInfo.errors.push(`信标 ${beacon.uuid} 缺少有效的距离或坐标信息`);
    }
    
    return isValid;
  });
  
  if (validBeacons.length === 0) {
    debugInfo.errors.push('没有有效的信标数据用于定位计算');
    console.warn('没有有效的信标数据用于位置计算');
    return null;
  }
  
  // 选择定位方法并计算位置
  let newPosition = null;
  const startTime = Date.now();
  
  try {
    if (validBeacons.length >= 3) {
      // 使用三边测量法
      newPosition = calculatePositionByTrilateration(validBeacons);
      debugInfo.calculationMethod = '三边测量法';
    } else {
      // 使用质心法
      newPosition = calculatePositionByCentroid(validBeacons);
      debugInfo.calculationMethod = '质心法';
    }
  } catch (err) {
    debugInfo.errors.push(`位置计算出错: ${err.message}`);
    console.error('位置计算出错:', err);
  }
  
  debugInfo.calculationTime = Date.now() - startTime;
  
  // 如果计算失败，返回null
  if (!newPosition) {
    debugInfo.errors.push('位置计算失败，无法得到有效结果');
    return null;
  }
  
  // 添加时间戳
  newPosition.timestamp = Date.now();
  
  // 平滑处理
  if (currentPosition) {
    newPosition = smoothPosition(currentPosition, newPosition);
  }
  
  // 更新当前位置
  currentPosition = { ...newPosition };
  
  // 添加到历史记录
  addToHistory(currentPosition);
  
  // 调用回调函数
  if (onPositionUpdateCallback) {
    onPositionUpdateCallback(currentPosition);
  }
  
  // 记录更新时间
  lastUpdateTime = newPosition.timestamp;
  
  return { ...currentPosition };
}

/**
 * 使用三边测量法计算位置
 * @param {Array} beacons 至少3个信标数据，包含距离信息
 * @returns {Object|null} 计算的位置对象
 */
function calculatePositionByTrilateration(beacons) {
  if (!Array.isArray(beacons) || beacons.length < 3) {
    debugInfo.errors.push('三边测量需要至少3个有效信标');
    return null;
  }
  
  // 确保所有信标都有有效的距离和坐标
  const validBeacons = beacons.filter(beacon => 
    typeof beacon.distance === 'number' && 
    beacon.distance > 0 &&
    typeof beacon.x === 'number' && 
    typeof beacon.y === 'number'
  );
  
  if (validBeacons.length < 3) {
    debugInfo.errors.push(`三边测量法信标数量不足: ${validBeacons.length}/3`);
    return null;
  }
  
  try {
    // 排序信标（按距离从小到大）
    const sortedBeacons = [...validBeacons].sort((a, b) => a.distance - b.distance);
    
    // 取前三个信标
    const beaconA = sortedBeacons[0];
    const beaconB = sortedBeacons[1];
    const beaconC = sortedBeacons[2];
    
    // 检查三个点是否成一条直线
    const area = Math.abs(
      (beaconA.x * (beaconB.y - beaconC.y) + 
       beaconB.x * (beaconC.y - beaconA.y) + 
       beaconC.x * (beaconA.y - beaconB.y)) / 2
    );
    
    if (area < 0.01) {
      debugInfo.errors.push('三个信标几乎在一条直线上，无法进行精确三边测量');
      console.warn('三个信标几乎在一条直线上，无法进行精确三边测量');
      // 回退到质心法
      return calculatePositionByCentroid(validBeacons);
    }
    
    // 使用非线性最小二乘法解决三边测量
    const result = nonLinearLeastSquares(sortedBeacons);
    
    if (!result || typeof result.x !== 'number' || typeof result.y !== 'number') {
      debugInfo.errors.push('三边测量计算结果无效');
      return null;
    }
    
    // 计算误差
    const errors = sortedBeacons.map(beacon => {
      const dx = beacon.x - result.x;
      const dy = beacon.y - result.y;
      const calculatedDistance = Math.sqrt(dx * dx + dy * dy);
      return Math.abs(calculatedDistance - beacon.distance);
    });
    
    const avgError = errors.reduce((sum, err) => sum + err, 0) / errors.length;
    
    return {
      x: result.x,
      y: result.y,
      accuracy: avgError,
      method: '三边测量法',
      beaconCount: sortedBeacons.length
    };
  } catch (err) {
    debugInfo.errors.push(`三边测量计算错误: ${err.message}`);
    console.error('三边测量计算错误:', err);
    // 回退到质心法
    return calculatePositionByCentroid(validBeacons);
  }
}

/**
 * 使用非线性最小二乘法求解三边测量
 * @param {Array} beacons 信标数组
 * @returns {Object} 位置对象
 */
function nonLinearLeastSquares(beacons) {
  // 初始猜测位置（使用质心法）
  let position = calculatePositionByCentroid(beacons);
  
  if (!position) {
    position = { x: 0, y: 0 };
  }
  
  // 最大迭代次数
  const MAX_ITERATIONS = 10;
  // 收敛阈值
  const CONVERGENCE_THRESHOLD = 0.01;
  
  // 梯度下降迭代
  for (let i = 0; i < MAX_ITERATIONS; i++) {
    // 计算当前误差
    let errorSum = 0;
    let gradientX = 0;
    let gradientY = 0;
    
    for (const beacon of beacons) {
      const dx = position.x - beacon.x;
      const dy = position.y - beacon.y;
      const calculatedDistance = Math.sqrt(dx * dx + dy * dy);
      const error = calculatedDistance - beacon.distance;
      
      // 更新误差和梯度
      errorSum += error * error;
      
      // 防止除以零
      if (calculatedDistance > 0.0001) {
        gradientX += error * dx / calculatedDistance;
        gradientY += error * dy / calculatedDistance;
      }
    }
    
    // 步长（简化的自适应步长）
    const stepSize = 1.0 / (beacons.length + i);
    
    // 更新位置
    const newX = position.x - stepSize * gradientX;
    const newY = position.y - stepSize * gradientY;
    
    // 检查收敛
    const moveDistance = Math.sqrt(
      Math.pow(newX - position.x, 2) + 
      Math.pow(newY - position.y, 2)
    );
    
    position.x = newX;
    position.y = newY;
    
    if (moveDistance < CONVERGENCE_THRESHOLD) {
      console.log(`非线性最小二乘法收敛于第${i + 1}次迭代`);
      break;
    }
  }
  
  return position;
}

/**
 * 使用质心法计算位置
 * @param {Array} beacons 信标数据，包含距离信息
 * @returns {Object|null} 计算的位置对象
 */
function calculatePositionByCentroid(beacons) {
  if (!Array.isArray(beacons) || beacons.length === 0) {
    debugInfo.errors.push('质心法计算需要至少一个有效信标');
    return null;
  }
  
  // 确保所有信标都有有效的距离和坐标
  const validBeacons = beacons.filter(beacon => 
    typeof beacon.distance === 'number' && 
    beacon.distance > 0 &&
    typeof beacon.x === 'number' && 
    typeof beacon.y === 'number'
  );
  
  if (validBeacons.length === 0) {
    debugInfo.errors.push('没有可用于质心法计算的有效信标');
    return null;
  }
  
  try {
    // 计算权重（距离的倒数）
    let totalWeight = 0;
    let weightedX = 0;
    let weightedY = 0;
    
    validBeacons.forEach(beacon => {
      // 权重是距离的倒数的平方（距离越近权重越大）
      const weight = 1 / (beacon.distance * beacon.distance);
      totalWeight += weight;
      weightedX += beacon.x * weight;
      weightedY += beacon.y * weight;
    });
    
    if (totalWeight === 0) {
      debugInfo.errors.push('质心法计算总权重为零');
      return null;
    }
    
    const x = weightedX / totalWeight;
    const y = weightedY / totalWeight;
    
    return {
      x,
      y,
      accuracy: estimateAccuracy(validBeacons, { x, y }),
      method: '质心法',
      beaconCount: validBeacons.length
    };
  } catch (err) {
    debugInfo.errors.push(`质心法计算错误: ${err.message}`);
    console.error('质心法计算错误:', err);
    return null;
  }
}

/**
 * 估计定位精度
 * @param {Array} beacons 信标数组
 * @param {Object} position 计算的位置
 * @returns {Number} 估计精度（米）
 */
function estimateAccuracy(beacons, position) {
  if (!Array.isArray(beacons) || beacons.length === 0 || !position) {
    return -1;
  }
  
  // 计算每个信标的实际距离与测量距离的偏差
  const errors = beacons.map(beacon => {
    const dx = beacon.x - position.x;
    const dy = beacon.y - position.y;
    const calculatedDistance = Math.sqrt(dx * dx + dy * dy);
    return Math.abs(calculatedDistance - beacon.distance);
  });
  
  // 使用平均偏差作为精度指标
  return errors.reduce((sum, err) => sum + err, 0) / errors.length;
}

/**
 * 平滑处理位置变化
 * @param {Object} oldPosition 旧位置
 * @param {Object} newPosition 新位置
 * @returns {Object} 平滑后的位置
 */
function smoothPosition(oldPosition, newPosition) {
  if (!oldPosition || !newPosition) {
    return newPosition;
  }
  
  // 时间差过大时不平滑
  const timeDiff = newPosition.timestamp - oldPosition.timestamp;
  if (timeDiff > 3000) {
    return newPosition;
  }
  
  // 使用指数移动平均进行平滑
  const alpha = POSITION_SMOOTHING_FACTOR;
  
  return {
    x: alpha * newPosition.x + (1 - alpha) * oldPosition.x,
    y: alpha * newPosition.y + (1 - alpha) * oldPosition.y,
    timestamp: newPosition.timestamp,
    accuracy: newPosition.accuracy,
    method: newPosition.method,
    beaconCount: newPosition.beaconCount,
    smoothed: true
  };
}

/**
 * 添加位置到历史记录
 * @param {Object} position 位置对象
 */
function addToHistory(position) {
  if (!position) return;
  
  positionHistory.push({ ...position });
  
  // 限制历史记录大小
  if (positionHistory.length > MAX_HISTORY_SIZE) {
    positionHistory = positionHistory.slice(positionHistory.length - MAX_HISTORY_SIZE);
  }
}

/**
 * 获取调试信息
 * @returns {Object} 调试信息
 */
function getDebugInfo() {
  return { ...debugInfo };
}

/**
 * 直接设置当前位置（用于测试或手动覆盖）
 * @param {Number} x X坐标
 * @param {Number} y Y坐标
 * @returns {Object} 设置的位置
 */
function setPosition(x, y) {
  if (typeof x !== 'number' || typeof y !== 'number') {
    console.error('设置位置失败：无效的坐标');
    return null;
  }
  
  const position = {
    x,
    y,
    timestamp: Date.now(),
    accuracy: 0,
    method: '手动设置',
    beaconCount: 0
  };
  
  currentPosition = { ...position };
  addToHistory(currentPosition);
  
  // 调用回调函数
  if (onPositionUpdateCallback) {
    onPositionUpdateCallback(currentPosition);
  }
  
  return { ...currentPosition };
}

module.exports = {
  init,
  getCurrentPosition,
  getPositionHistory,
  clearPositionHistory,
  updatePosition,
  calculatePositionByTrilateration,
  calculatePositionByCentroid,
  setPosition,
  getDebugInfo,
  setPositionUpdateCallback
}; 
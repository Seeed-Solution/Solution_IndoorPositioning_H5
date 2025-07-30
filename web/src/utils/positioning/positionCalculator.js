/**
 * 位置计算模块
 * 用于实现三边测量和最小二乘法定位算法
 */

/**
 * 定位方法常量
 */
export const POSITIONING_METHOD = {
  TRILATERATION: 'trilateration',   // 三边测量法
  LEAST_SQUARES: 'least_squares',   // 最小二乘法
  WEIGHTED_AVERAGE: 'weighted_average' // 加权平均法
};

/**
 * 信号衰减模型参数
 * 信号因子默认值为2.5
 */
let SIGNAL_FACTOR = 2.5;

/**
 * 设置信号衰减因子
 * @param {Number} factor 信号因子
 */
export function setSignalFactor(factor) {
  if (typeof factor === 'number' && factor > 0) {
    SIGNAL_FACTOR = factor;
    console.log('信号衰减因子已更新为:', factor);
    return true;
  } else {
    console.warn('信号衰减因子无效, 使用默认值:', SIGNAL_FACTOR);
    return false;
  }
}

/**
 * 获取当前的信号衰减因子
 * @returns {Number} 当前的信号衰减因子
 */
export function getSignalFactor() {
  return SIGNAL_FACTOR;
}

/**
 * 根据RSSI和发射功率计算距离
 * 使用对数衰减模型: d = 10^((txPower - rssi) / (10 * SIGNAL_FACTOR))
 * @param {Number} rssi 接收信号强度指标
 * @param {Number} txPower 发射功率（1米处测量的RSSI值）
 * @returns {Number} 估算的距离（米）
 */
export function calculateDistance(rssi, txPower) {
  if (typeof rssi !== 'number' || typeof txPower !== 'number') {
    console.warn('计算距离失败: RSSI或发射功率参数无效', {rssi, txPower});
    return null;
  }
  
  // 防止RSSI大于txPower的情况（这可能因干扰或位置过近导致）
  if (rssi > txPower) {
    return 0.1; // 返回一个很小的距离
  }
  
  // 使用对数衰减模型
  const distance = Math.pow(10, (txPower - rssi) / (10 * SIGNAL_FACTOR));
  
  if (isNaN(distance) || !isFinite(distance)) {
    console.warn('计算出无效距离:', {distance, rssi, txPower, SIGNAL_FACTOR});
    return null;
  }
  
  // 限制距离在合理范围内
  return Math.min(Math.max(distance, 0.1), 100);
}

/**
 * 应用卡尔曼滤波平滑RSSI值
 * @param {Number} rssi 当前RSSI
 * @param {Number} prevRssi 先前RSSI
 * @param {Number} prevError 先前误差
 * @returns {Object} 包含滤波后的RSSI和新误差
 */
export function kalmanFilter(rssi, prevRssi, prevError) {
  // 卡尔曼滤波器参数
  const Q = 0.008; // 过程噪声方差
  const R = 4; // 测量噪声方差
  
  if (prevRssi === null || prevError === null) {
    // 首次测量，没有之前的状态
    return { rssi: rssi, error: R };
  }
  
  // 预测步骤
  const predictedRssi = prevRssi;
  const predictedError = prevError + Q;
  
  // 更新步骤
  const K = predictedError / (predictedError + R); // 卡尔曼增益
  const updatedRssi = predictedRssi + K * (rssi - predictedRssi);
  const updatedError = (1 - K) * predictedError;
  
  return { rssi: updatedRssi, error: updatedError };
}

/**
 * 三边测量定位算法
 * 利用三个信标的坐标和距离计算当前位置
 * @param {Array} beacons 包含至少三个信标的数组，每个信标具有 x, y, distance 属性
 * @returns {Object|null} 计算出的位置 {x, y} 或 null（如果计算失败）
 */
export function trilateration(beacons) {
  try {
    // 确保至少有三个信标
    if (!Array.isArray(beacons) || beacons.length < 3) {
      console.warn('三边测量失败：需要至少3个信标');
      return null;
    }

    // 筛选出有效的信标（具有完整坐标和距离信息）
    const validBeacons = beacons.filter(b => 
      typeof b.x === 'number' && 
      typeof b.y === 'number' && 
      typeof b.distance === 'number' && 
      b.distance > 0
    );
    
    if (validBeacons.length < 3) {
      console.warn('三边测量失败：有效信标数量不足', validBeacons.length);
      return null;
    }

    // 选择前三个信标
    const b1 = validBeacons[0];
    const b2 = validBeacons[1];
    const b3 = validBeacons[2];

    // 计算中间变量
    const A = 2 * (b2.x - b1.x);
    const B = 2 * (b2.y - b1.y);
    const C = b1.distance * b1.distance - b2.distance * b2.distance - b1.x * b1.x + b2.x * b2.x - b1.y * b1.y + b2.y * b2.y;
    const D = 2 * (b3.x - b2.x);
    const E = 2 * (b3.y - b2.y);
    const F = b2.distance * b2.distance - b3.distance * b3.distance - b2.x * b2.x + b3.x * b3.x - b2.y * b2.y + b3.y * b3.y;

    // 计算行列式
    const det = A * E - B * D;
    
    if (Math.abs(det) < 1e-10) {
      console.warn('三边测量失败：信标位置共线或过近');
      return null;
    }

    // 求解位置坐标
    const x = (C * E - B * F) / det;
    const y = (A * F - C * D) / det;

    // 验证结果是否合理
    if (isNaN(x) || isNaN(y) || !isFinite(x) || !isFinite(y)) {
      console.warn('三边测量失败：计算结果无效');
      return null;
    }

    return { x, y };
  } catch (e) {
    console.error('三边测量算法执行出错:', e);
    return null;
  }
}

/**
 * 最小二乘法多边定位算法
 * 利用多个信标的位置和距离，通过最小化误差平方和计算位置
 * @param {Array} beacons 信标数组，每个信标具有 x, y, distance 属性
 * @param {Number} maxIterations 最大迭代次数，默认为20
 * @param {Number} tolerance 收敛容差，默认为0.01
 * @returns {Object|null} 计算出的位置 {x, y} 或 null（如果计算失败）
 */
export function leastSquaresPositioning(beacons, maxIterations = 20, tolerance = 0.01) {
  try {
    // 确保至少有三个信标
    if (!Array.isArray(beacons) || beacons.length < 3) {
      console.warn('最小二乘法定位失败：需要至少3个信标');
      return null;
    }

    // 筛选出有效的信标
    const validBeacons = beacons.filter(b => 
      typeof b.x === 'number' && 
      typeof b.y === 'number' && 
      typeof b.distance === 'number' && 
      b.distance > 0
    );
    
    if (validBeacons.length < 3) {
      console.warn('最小二乘法定位失败：有效信标数量不足', validBeacons.length);
      return null;
    }

    // 初始位置估计（使用信标的平均位置）
    let position = {
      x: validBeacons.reduce((sum, b) => sum + b.x, 0) / validBeacons.length,
      y: validBeacons.reduce((sum, b) => sum + b.y, 0) / validBeacons.length
    };

    // Gauss-Newton 迭代求解
    let iteration = 0;
    let delta = Infinity;

    while (iteration < maxIterations && delta > tolerance) {
      // 计算 Jacobian 矩阵 J 和误差向量 e
      const J = [];  // Jacobian 矩阵
      const e = [];  // 误差向量
      
      validBeacons.forEach(beacon => {
        const dx = position.x - beacon.x;
        const dy = position.y - beacon.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 1e-10) {
          // 避免除以零，跳过此信标
          return;
        }

        // 添加一行到 Jacobian 矩阵
        J.push([dx / distance, dy / distance]);
        
        // 添加一个元素到误差向量
        e.push(distance - beacon.distance);
      });

      // 检查是否有足够的方程
      if (J.length < 2) {
        console.warn('最小二乘法定位失败：有效方程数量不足');
        return null;
      }

      // 计算 J^T * J 和 J^T * e
      const JTJ = [
        [0, 0],
        [0, 0]
      ];
      
      const JTe = [0, 0];
      
      for (let i = 0; i < J.length; i++) {
        JTJ[0][0] += J[i][0] * J[i][0];
        JTJ[0][1] += J[i][0] * J[i][1];
        JTJ[1][0] += J[i][1] * J[i][0];
        JTJ[1][1] += J[i][1] * J[i][1];
        
        JTe[0] += J[i][0] * e[i];
        JTe[1] += J[i][1] * e[i];
      }

      // 计算 (J^T * J)^(-1)
      const det = JTJ[0][0] * JTJ[1][1] - JTJ[0][1] * JTJ[1][0];
      
      if (Math.abs(det) < 1e-10) {
        console.warn('最小二乘法定位失败：矩阵奇异');
        break;
      }
      
      const invJTJ = [
        [JTJ[1][1] / det, -JTJ[0][1] / det],
        [-JTJ[1][0] / det, JTJ[0][0] / det]
      ];

      // 计算更新量 Δp = (J^T * J)^(-1) * J^T * e
      const deltaX = invJTJ[0][0] * JTe[0] + invJTJ[0][1] * JTe[1];
      const deltaY = invJTJ[1][0] * JTe[0] + invJTJ[1][1] * JTe[1];

      // 更新位置
      position.x -= deltaX;
      position.y -= deltaY;

      // 计算收敛程度
      delta = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
      
      iteration++;
    }

    // 检查结果是否合理
    if (isNaN(position.x) || isNaN(position.y) || !isFinite(position.x) || !isFinite(position.y)) {
      console.warn('最小二乘法定位失败：计算结果无效');
      return null;
    }

    return position;
  } catch (e) {
    console.error('最小二乘法定位算法执行出错:', e);
    return null;
  }
}

/**
 * 加权质心定位算法
 * 使用距离的倒数作为权重计算加权质心位置
 * @param {Array} beacons 信标数组，每个信标具有 x, y, distance 属性
 * @returns {Object|null} 计算出的位置 {x, y} 或 null（如果计算失败）
 */
export function weightedCentroidPositioning(beacons) {
  try {
    // 确保至少有一个信标
    if (!Array.isArray(beacons) || beacons.length < 1) {
      console.warn('加权质心定位失败：没有信标');
      return null;
    }

    // 筛选出有效的信标
    const validBeacons = beacons.filter(b => 
      typeof b.x === 'number' && 
      typeof b.y === 'number' && 
      typeof b.distance === 'number' && 
      b.distance > 0
    );
    
    if (validBeacons.length < 1) {
      console.warn('加权质心定位失败：没有有效信标');
      return null;
    }

    // 如果只有一个信标，直接返回其位置
    if (validBeacons.length === 1) {
      return { x: validBeacons[0].x, y: validBeacons[0].y };
    }

    // 计算权重（距离的倒数）
    let totalWeight = 0;
    let weightedX = 0;
    let weightedY = 0;

    validBeacons.forEach(beacon => {
      // 使用距离的倒数作为权重
      const weight = 1 / (beacon.distance * beacon.distance);
      totalWeight += weight;
      
      weightedX += beacon.x * weight;
      weightedY += beacon.y * weight;
    });

    // 避免除以零
    if (totalWeight < 1e-10) {
      console.warn('加权质心定位失败：总权重接近零');
      return null;
    }

    const x = weightedX / totalWeight;
    const y = weightedY / totalWeight;

    // 检查结果是否合理
    if (isNaN(x) || isNaN(y) || !isFinite(x) || !isFinite(y)) {
      console.warn('加权质心定位失败：计算结果无效');
      return null;
    }

    return { x, y };
  } catch (e) {
    console.error('加权质心定位算法执行出错:', e);
    return null;
  }
}

/**
 * 选择合适的定位算法并计算位置
 * @param {Array} beacons 信标数组，每个信标具有 x, y, distance 属性
 * @returns {Object} 计算出的位置 {x, y, method}，method 表示使用的方法
 */
export function calculatePosition(beacons) {
  try {
    if (!Array.isArray(beacons) || beacons.length === 0) {
      console.warn('定位失败：没有信标数据');
      return null;
    }

    // 筛选有效信标（具有坐标和距离信息）
    const validBeacons = beacons.filter(b => 
      typeof b.x === 'number' && 
      typeof b.y === 'number' && 
      typeof b.distance === 'number' && 
      b.distance > 0
    );

    if (validBeacons.length === 0) {
      console.warn('定位失败：没有有效信标');
      return null;
    }

    let position = null;
    let method = '';

    // 根据有效信标的数量选择算法
    if (validBeacons.length >= 3) {
      // 尝试三边测量
      position = trilateration(validBeacons);
      method = '三边测量';
      
      // 如果三边测量失败，尝试最小二乘法
      if (!position) {
        position = leastSquaresPositioning(validBeacons);
        method = '最小二乘法';
      }
    }

    // 如果上述方法都失败或信标不足三个，使用加权质心
    if (!position) {
      position = weightedCentroidPositioning(validBeacons);
      method = '加权质心';
    }

    // 如果所有方法都失败，返回 null
    if (!position) {
      console.warn('所有定位方法都失败');
      return null;
    }

    // 添加使用的方法信息
    position.method = method;
    return position;
  } catch (e) {
    console.error('定位计算执行出错:', e);
    return null;
  }
} 
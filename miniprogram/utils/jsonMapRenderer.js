/**
 * JSON地图渲染器
 * 负责加载、渲染、处理地图及相关元素
 */

// 地图信息
let mapInfo = {
  width: 0,
  height: 0,
  entities: []
};

// 绘图参数
let scale = 100; // 缩放比例（像素/米）
let offset = { x: 0, y: 0 }; // 偏移量（像素）
let canvasContext = null; // 绘图上下文
let canvasSize = { width: 0, height: 0 }; // 画布尺寸（像素）

// 位置信息
let currentPosition = null; // 当前位置（米）
let trajectoryPoints = []; // 轨迹点列表（米）
let beaconPoints = []; // 信标点列表（米）

// 颜色设置
const COLOR = {
  BACKGROUND: '#f5f5f5',
  GRID: '#e0e0e0',
  ENTITIES: '#2196F3', // 用于圆形、文本等
  TEXT: '#212121',
  POSITION: '#4CAF50',
  AXES: '#CCCCCC',
  MAP_BORDER: '#555555',
  MAP_ENTITY: '#4CAF50', // 折线默认颜色
  TRAJECTORY: '#03A9F4',
  BEACON_TEXT: '#333333',
  BEACON_RADIUS: '#FFB74D'
};

/**
 * 初始化地图渲染器
 * @param {Object} context Canvas绘图上下文
 * @param {Number} width 画布宽度（像素）
 * @param {Number} height 画布高度（像素）
 * @returns {Boolean} 初始化是否成功
 */
function init(context, width, height) {
  try {
    console.log(`jsonMapRenderer.init - 画布尺寸: ${width} x ${height}`);
    
    if (!context) {
      console.error('初始化地图渲染器失败：上下文为null或undefined');
      return false;
    }
    
    if (typeof context.fillRect !== 'function') {
      console.error('初始化地图渲染器失败：无效的绘图上下文，缺少fillRect方法');
      // 打印上下文的可用方法，帮助调试
      console.log('上下文可用方法:', Object.keys(context).filter(key => typeof context[key] === 'function'));
      return false;
    }
    
    if (!width || width <= 0 || !height || height <= 0) {
      console.error(`初始化地图渲染器失败：无效的画布尺寸 (${width} x ${height})`);
      return false;
    }
    
    canvasContext = context;
    setCanvasSize(width, height);
    
    return true;
  } catch (err) {
    console.error('初始化地图渲染器发生异常:', err);
    return false;
  }
}

/**
 * 重置渲染器状态
 */
function reset() {
  scale = 100; // 默认比例：100像素/米
  offset = {
    x: canvasSize.width / 2,
    y: canvasSize.height / 2
  };
  currentPosition = null;
  trajectoryPoints = [];
  beaconPoints = [];
}

/**
 * 设置地图信息
 * @param {Object} info 地图信息对象
 * @returns {Boolean} 设置是否成功
 */
function setMapInfo(info) {
  try {
    if (!info || typeof info !== 'object') {
      console.error('设置地图信息失败：无效的地图数据');
      return false;
    }
    
    if (typeof info.width !== 'number' || typeof info.height !== 'number' || !Array.isArray(info.entities)) {
      console.error('设置地图信息失败：地图数据缺少必要字段');
      return false;
    }
    
    mapInfo = {
      width: info.width,
      height: info.height,
      entities: Array.isArray(info.entities) ? [...info.entities] : []
    };
    
    // 自动调整比例和偏移，以适应画布
    fitMapToCanvas();
    
    console.log('地图信息已更新，尺寸:', mapInfo.width, 'x', mapInfo.height, '米，实体数量:', mapInfo.entities.length);
    return true;
  } catch (err) {
    console.error('设置地图信息出错:', err);
    return false;
  }
}

/**
 * 获取地图信息
 * @returns {Object} 地图信息
 */
function getMapInfo() {
  return { ...mapInfo };
}

/**
 * 调整地图以适应画布
 * @private
 */
function fitMapToCanvas() {
  if (mapInfo.width <= 0 || mapInfo.height <= 0 || canvasSize.width <= 0 || canvasSize.height <= 0) {
    console.warn('无法调整地图：无效的地图或画布尺寸');
    return;
  }
  
  console.log('fitMapToCanvas: 地图已自动调整，比例:', scale.toFixed(2), '像素/米，偏移量:', offset.x.toFixed(1), ',', offset.y.toFixed(1));
  
  // --- 模仿 config.js 的缩放计算 ---
  const mapWidth = mapInfo.width;
  const mapHeight = mapInfo.height;
  const canvasWidth = canvasSize.width;
  const canvasHeight = canvasSize.height;
  
  // 计算缩放比例，与 config.js 保持一致
  let newScale = Math.min(
    (canvasWidth - 40) / mapWidth,  // 模仿 config.js 的边距
    (canvasHeight - 40) / mapHeight
  ) * 0.85; // 模仿 config.js 的额外缩放因子
  
  // 防止缩放比例过小或过大 (保留之前的限制)
  const minScale = 10;
  const maxScale = 500; 
  if (newScale < minScale) {
    console.log(`缩放比例过小(${newScale})，设置为最小值${minScale}`);
    newScale = minScale;
  } else if (newScale > maxScale) {
    console.log(`缩放比例过大(${newScale})，设置为最大值${maxScale}`);
    newScale = maxScale;
  }
  
  scale = newScale;
  
  // --- 模仿 config.js 的偏移计算 ---
  // 直接计算左上角的偏移量，使缩放后的地图居中
  offset = {
    x: (canvasWidth - mapWidth * scale) / 2,
    y: (canvasHeight - mapHeight * scale) / 2
  };
  // --- 结束模仿计算 ---
}

/**
 * 设置缩放比例
 * @param {Number} newScale 新的缩放比例（像素/米）
 * @returns {Boolean} 设置是否成功
 */
function setScale(newScale) {
  if (typeof newScale !== 'number' || newScale <= 0) {
    console.error('设置比例失败：无效的比例值');
    return false;
  }
  
  scale = newScale;
  return true;
}

/**
 * 获取当前缩放比例
 * @returns {Number} 缩放比例（像素/米）
 */
function getScale() {
  return scale;
}

/**
 * 设置绘图偏移量
 * @param {Number} x X偏移量（像素）
 * @param {Number} y Y偏移量（像素）
 * @returns {Boolean} 设置是否成功
 */
function setOffset(x, y) {
  if (typeof x !== 'number' || typeof y !== 'number') {
    console.error('设置偏移量失败：无效的参数');
    return false;
  }
  
  offset = { x, y };
  return true;
}

/**
 * 获取当前偏移量
 * @returns {Object} 偏移量对象
 */
function getOffset() {
  return { ...offset };
}

/**
 * 设置画布尺寸
 * @param {Number} width 宽度（像素）
 * @param {Number} height 高度（像素）
 * @returns {Boolean} 设置是否成功
 */
function setCanvasSize(width, height) {
  if (typeof width !== 'number' || width <= 0 || typeof height !== 'number' || height <= 0) {
    console.error('设置画布尺寸失败：无效的参数');
    return false;
  }
  
  // 仅在尺寸实际变化时才更新
  if (canvasSize.width === width && canvasSize.height === height) {
    return true;
  }
  
  canvasSize = { width, height };
  
  fitMapToCanvas();
  
  return true;
}

/**
 * 设置当前位置
 * @param {Number} x X坐标（米）
 * @param {Number} y Y坐标（米）
 * @returns {Boolean} 设置是否成功
 */
function setCurrentPosition(x, y) {
  if (typeof x !== 'number' || typeof y !== 'number') {
    console.error('设置当前位置失败：无效的坐标');
    return false;
  }
  
  currentPosition = { x, y };
  
  // 添加到轨迹
  addTrajectoryPoint(x, y);
  
  return true;
}

/**
 * 获取当前位置
 * @returns {Object|null} 当前位置对象
 */
function getCurrentPosition() {
  return currentPosition ? { ...currentPosition } : null;
}

/**
 * 添加轨迹点
 * @param {Number} x X坐标（米）
 * @param {Number} y Y坐标（米）
 * @returns {Boolean} 添加是否成功
 */
function addTrajectoryPoint(x, y) {
  if (typeof x !== 'number' || typeof y !== 'number') {
    console.error('添加轨迹点失败：无效的坐标');
    return false;
  }
  
  // 限制轨迹点数量，避免内存占用过大
  const MAX_TRAJECTORY_POINTS = 100;
  
  trajectoryPoints.push({ x, y, timestamp: Date.now() });
  
  if (trajectoryPoints.length > MAX_TRAJECTORY_POINTS) {
    trajectoryPoints = trajectoryPoints.slice(trajectoryPoints.length - MAX_TRAJECTORY_POINTS);
  }
  
  return true;
}

/**
 * 清除轨迹
 */
function clearTrajectory() {
  trajectoryPoints = [];
}

/**
 * 设置信标点
 * @param {Array} beacons 信标点数组，每个包含x、y坐标及其他信息
 * @returns {Boolean} 设置是否成功
 */
function setBeaconPoints(beacons) {
  if (!Array.isArray(beacons)) {
    console.error('设置信标点失败：无效的信标数组');
    return false;
  }
  
  beaconPoints = beacons.map(beacon => {
    return {
      x: beacon.x,
      y: beacon.y,
      name: beacon.name || '',
      displayName: beacon.displayName || beacon.name || '',
      uuid: beacon.uuid || '',
      distance: beacon.distance || null
    };
  }).filter(bp => typeof bp.x === 'number' && typeof bp.y === 'number');
  
  return true;
}

/**
 * 获取信标点
 * @returns {Array} 信标点数组
 */
function getBeaconPoints() {
  return [...beaconPoints];
}

/**
 * 渲染地图和所有元素
 * @param {Object} options 渲染选项
 * @returns {Boolean} 渲染是否成功
 */
function render(options = {}) {
  try {
    if (!canvasContext) {
      console.error('渲染地图失败：未初始化绘图上下文');
      return false;
    }
    
    // 检查地图状态
    if (!mapInfo || typeof mapInfo !== 'object') {
      console.warn('渲染失败：地图数据为空或无效');
      return false;
    }
    
    // 检查地图尺寸
    if (!mapInfo.width || !mapInfo.height || mapInfo.width <= 0 || mapInfo.height <= 0) {
      console.warn(`渲染失败：无效的地图尺寸 (${mapInfo.width} x ${mapInfo.height})`);
      return false;
    }
    
    // 检查实体数组
    if (!Array.isArray(mapInfo.entities)) {
      console.warn('渲染失败：地图实体不是数组');
      return false;
    }
    
    // 检查是否有任何有效的实体
    const validEntities = mapInfo.entities.filter(entity => 
      entity && entity.type && (
        (entity.type === 'polyline' && Array.isArray(entity.points) && entity.points.length > 1) ||
        (entity.type === 'circle' && entity.center && typeof entity.radius === 'number') ||
        (entity.type === 'text' && entity.position && entity.text)
      )
    );
    
    if (validEntities.length === 0) {
      console.warn('渲染失败：没有有效的地图实体');
      // 继续渲染其他元素，但记录警告
    }
    
    // 为调试目的打印第一个实体的详细信息
    if (mapInfo.entities.length > 0) {
      const firstEntity = mapInfo.entities[0];
      console.log('第一个实体类型:', firstEntity.type);
      
      if (firstEntity.type === 'polyline' && Array.isArray(firstEntity.points)) {
        console.log('第一个实体点数:', firstEntity.points.length);
        console.log('第一个实体点示例:', firstEntity.points.slice(0, 3));
        console.log('闭合性:', firstEntity.closed ? '是' : '否');
        console.log('填充:', firstEntity.fill ? '是' : '否');
      }
    }
    
    const opts = {
      showGrid: options.showGrid !== false,
      showAxes: options.showAxes !== false,
      showMap: options.showMap !== false,
      showBeacons: options.showBeacons !== false,
      showPosition: options.showPosition !== false,
      showTrajectory: options.showTrajectory !== false
    };
    
    // 清空画布
    canvasContext.clearRect(0, 0, canvasSize.width, canvasSize.height);
    canvasContext.fillStyle = COLOR.BACKGROUND; // 使用背景色常量
    canvasContext.fillRect(0, 0, canvasSize.width, canvasSize.height);

    // 渲染调用
    if (opts.showGrid) { renderGrid(); }
    if (opts.showAxes) { renderAxes(); }
    if (opts.showMap && validEntities.length > 0) { renderMapEntities(); }
    if (opts.showBeacons && beaconPoints.length > 0) { renderBeacons(); }
    if (opts.showTrajectory && trajectoryPoints.length > 1) { renderTrajectory(); }
    if (opts.showPosition && currentPosition) { renderCurrentPosition(); }

    return true;
  } catch (err) {
    console.error('渲染地图过程中发生异常:', err);
    return false;
  }
}

/**
 * 渲染网格
 * @private
 */
function renderGrid() {
  if (!canvasContext || mapInfo.width <= 0 || mapInfo.height <= 0) {
    console.warn('renderGrid: 无法渲染网格，上下文或地图尺寸无效');
    return;
  }
  
  // 设置网格样式
  canvasContext.strokeStyle = COLOR.GRID;
  canvasContext.lineWidth = 0.5; // 更细的网格线
  
  const gridSpacing = 1; // 网格间距（米）
  
  // 绘制垂直网格线 (基于地图X坐标)
  for (let mapX = 0; mapX <= mapInfo.width; mapX += gridSpacing) {
    const screenX = mapToScreenX(mapX);
    const screenYTop = mapToScreenY(mapInfo.height); // 地图顶边对应的屏幕Y
    const screenYBottom = mapToScreenY(0); // 地图底边对应的屏幕Y
    
    canvasContext.beginPath();
    canvasContext.moveTo(screenX, screenYTop);
    canvasContext.lineTo(screenX, screenYBottom);
    canvasContext.stroke();
  }
  
  // 绘制水平网格线 (基于地图Y坐标)
  for (let mapY = 0; mapY <= mapInfo.height; mapY += gridSpacing) {
    const screenY = mapToScreenY(mapY);
    const screenXLeft = mapToScreenX(0); // 地图左边对应的屏幕X
    const screenXRight = mapToScreenX(mapInfo.width); // 地图右边对应的屏幕X
    
    canvasContext.beginPath();
    canvasContext.moveTo(screenXLeft, screenY);
    canvasContext.lineTo(screenXRight, screenY);
    canvasContext.stroke();
  }
}

/**
 * 渲染坐标轴
 * @private
 */
function renderAxes() {
  if (!canvasContext) {
    return;
  }
  
  // 设置坐标轴样式
  canvasContext.strokeStyle = COLOR.AXES;
  canvasContext.lineWidth = 1; // 使用稍细的线宽
  
  // 计算地图原点 (0,0) 在屏幕上的坐标
  const originScreenX = mapToScreenX(0);
  const originScreenY = mapToScreenY(0);
  
  // 绘制X轴 (水平线，穿过地图原点的屏幕Y坐标)
  canvasContext.beginPath();
  canvasContext.moveTo(0, originScreenY);
  canvasContext.lineTo(canvasSize.width, originScreenY);
  canvasContext.stroke();
  
  // 绘制Y轴 (垂直线，穿过地图原点的屏幕X坐标)
  canvasContext.beginPath();
  canvasContext.moveTo(originScreenX, 0);
  canvasContext.lineTo(originScreenX, canvasSize.height);
  canvasContext.stroke();
}

/**
 * 渲染地图实体
 * @private
 */
function renderMapEntities() {
  if (!canvasContext || !mapInfo || !mapInfo.entities || !Array.isArray(mapInfo.entities)) {
    console.warn('无法渲染地图实体：数据不完整');
    return;
  }

  const entities = mapInfo.entities;
  
  // 按类型对实体进行分类并计数
  const polylines = entities.filter(e => e && e.type === 'polyline');
  const circles = entities.filter(e => e && e.type === 'circle');
  const texts = entities.filter(e => e && e.type === 'text');
  const others = entities.filter(e => e && e.type && e.type !== 'polyline' && e.type !== 'circle' && e.type !== 'text');
  
  let successfulRenders = 0;
  
  // 优先渲染非多边形实体（它们通常是边界或文本标签）
  if (circles.length > 0 || texts.length > 0 || others.length > 0) {
    [...circles, ...texts, ...others].forEach((entity, index) => {
      if (!entity || !entity.type) {
        console.warn(`跳过无效的非折线实体 #${index}`);
        return;
      }
      
      try {
        let rendered = false;
        
        switch (entity.type.toLowerCase()) {
          case 'circle':
            rendered = renderCircle(entity);
            break;
          case 'text':
            rendered = renderText(entity);
            break;
          default:
            console.warn('未知的实体类型:', entity.type);
        }
        
        if (rendered) {
          successfulRenders++;
        }
      } catch (error) {
        console.error(`渲染非折线实体 #${index} (${entity.type}) 时出错:`, error);
      }
    });
  }
  
  // 然后渲染折线（通常是主要的地图元素）
  if (polylines.length > 0) {
    // 先渲染闭合的折线（通常是房间或区域）
    const closedPolylines = polylines.filter(p => p.closed);
    const openPolylines = polylines.filter(p => !p.closed);
    
    // 先渲染闭合的折线
    closedPolylines.forEach((entity, index) => {
      try {
        const rendered = renderPolyline(entity);
        if (rendered) {
          successfulRenders++;
        }
      } catch (error) {
        console.error(`渲染闭合折线 #${index} 时出错:`, error);
      }
    });
    
    // 再渲染开放的折线
    openPolylines.forEach((entity, index) => {
      try {
        const rendered = renderPolyline(entity);
        if (rendered) {
          successfulRenders++;
        }
      } catch (error) {
        console.error(`渲染开放折线 #${index} 时出错:`, error);
      }
    });
  }
}

/**
 * 渲染折线
 * @param {Object} entity - 折线实体
 * @returns {Boolean} 是否成功渲染
 * @private
 */
function renderPolyline(entity) {
  if (!canvasContext || !entity || !entity.points || !Array.isArray(entity.points)) {
    console.warn('renderPolyline: 无效的实体或点数组', entity);
    return false;
  }
  
  // 检查是否有足够的点
  if (entity.points.length < 2) {
    console.warn(`renderPolyline: 点数不足 (${entity.points.length}), 至少需要2个点`);
    return false;
  }
  
  // 验证点坐标
  const validPoints = entity.points.filter(point => 
    Array.isArray(point) && point.length >= 2 && 
    typeof point[0] === 'number' && typeof point[1] === 'number'
  );
  
  if (validPoints.length !== entity.points.length) {
    console.warn(`renderPolyline: 部分点坐标无效，总点数=${entity.points.length}，有效点数=${validPoints.length}`);
    if (validPoints.length < 2) {
      console.error('renderPolyline: 有效点不足，无法渲染');
      return false;
    }
  }
  
  try {
    // --- 恢复原始样式设置 --- 
    canvasContext.strokeStyle = entity.color || entity.strokeColor || COLOR.MAP_ENTITY;
    canvasContext.lineWidth = entity.width || 2;
    const isClosed = Boolean(entity.closed);
    const shouldFill = Boolean(entity.fill) || Boolean(entity.fillColor);
    const fillColor = entity.fillColor || 'rgba(240, 248, 255, 0.5)'; // 默认浅蓝色半透明
    
    // 绘制折线
    canvasContext.beginPath();
    
    // 移动到第一个点
    const firstPoint = validPoints[0];
    const startX = mapToScreenX(firstPoint[0]);
    const startY = mapToScreenY(firstPoint[1]);
    canvasContext.moveTo(startX, startY);
    
    // 连接后续点
    for (let i = 1; i < validPoints.length; i++) {
      const point = validPoints[i];
      const x = mapToScreenX(point[0]);
      const y = mapToScreenY(point[1]);
      canvasContext.lineTo(x, y);
    }
    
    // 如果是闭合的，连接回起点
    if (isClosed) {
      canvasContext.closePath();
    }
    
    // 如果需要填充
    if (shouldFill) {
      canvasContext.fillStyle = fillColor;
      canvasContext.fill();
    }
    
    // 绘制边框
    canvasContext.stroke();
    
    return true;
  } catch (err) {
    console.error('renderPolyline: 绘制过程中出错', err);
    return false;
  }
}

/**
 * 渲染圆形
 * @param {Object} entity - 圆形实体
 * @private
 */
function renderCircle(entity) {
  if (!canvasContext || !entity || !entity.center || typeof entity.radius !== 'number') {
    return;
  }
  
  const center = entity.center;
  if (typeof center.x !== 'number' || typeof center.y !== 'number') {
    return;
  }
  
  const x = offset.x + center.x * scale;
  const y = offset.y - center.y * scale;
  const radius = entity.radius * scale;
  
  // 设置圆形样式
  canvasContext.strokeStyle = entity.color || COLOR.ENTITIES;
  canvasContext.lineWidth = entity.width || 2;
  
  // 绘制圆形
  canvasContext.beginPath();
  canvasContext.arc(x, y, radius, 0, 2 * Math.PI);
  canvasContext.stroke();
  
  // 如果需要填充
  if (entity.fill) {
    canvasContext.fillStyle = entity.fillColor || 'rgba(76, 175, 80, 0.2)';
    canvasContext.fill();
  }
}

/**
 * 渲染文本
 * @param {Object} entity - 文本实体
 * @private
 */
function renderText(entity) {
  if (!canvasContext || !entity || !entity.position || !entity.text) {
    return;
  }
  
  const position = entity.position;
  if (typeof position.x !== 'number' || typeof position.y !== 'number') {
    return;
  }
  
  const x = offset.x + position.x * scale;
  const y = offset.y - position.y * scale;
  
  // 设置文本样式
  canvasContext.fillStyle = entity.color || COLOR.TEXT;
  canvasContext.font = entity.font || '14px Arial';
  canvasContext.textAlign = entity.align || 'center';
  canvasContext.textBaseline = entity.baseline || 'middle';
  
  // 绘制文本
  canvasContext.fillText(entity.text, x, y);
}

/**
 * 渲染信标
 * @private
 */
function renderBeacons() {
  if (!canvasContext || !Array.isArray(beaconPoints) || beaconPoints.length === 0) return;

  beaconPoints.forEach((beacon, index) => {
    if (typeof beacon.x !== 'number' || typeof beacon.y !== 'number') return;
    try {
      const screenX = mapToScreenX(beacon.x);
      const screenY = mapToScreenY(beacon.y);
      const outerRadius = 10;
      const innerRadius = 6;
      const outerColor = 'rgba(33, 150, 243, 0.2)';
      const innerColor = 'rgba(33, 150, 243, 0.7)';
      const borderColor = '#ffffff';
      const textColor = '#333333';
      
      let label = beacon.displayName || 'No Name';
      let fontSize = 10;
      if (label.length > 6) fontSize = 8;
      if (label.length > 10) fontSize = 6; 

      // Outer circle
      canvasContext.fillStyle = outerColor;
      canvasContext.beginPath();
      canvasContext.arc(screenX, screenY, outerRadius, 0, 2 * Math.PI);
      canvasContext.fill();
      
      // Inner circle
      canvasContext.fillStyle = innerColor;
      canvasContext.strokeStyle = borderColor;
      canvasContext.lineWidth = 1.5;
      canvasContext.beginPath();
      canvasContext.arc(screenX, screenY, innerRadius, 0, 2 * Math.PI);
      canvasContext.fill();
      canvasContext.stroke();
      
      // Label
      canvasContext.font = `bold ${fontSize}px sans-serif`; 
      canvasContext.fillStyle = textColor;
      canvasContext.textAlign = 'center'; 
      canvasContext.textBaseline = 'middle';
      canvasContext.fillText(label, screenX, screenY);
      canvasContext.textAlign = 'start'; // Reset alignment
      canvasContext.textBaseline = 'alphabetic';

      // Distance radius (keep this)
      if (typeof beacon.distance === 'number' && beacon.distance > 0) {
        const radiusPixels = beacon.distance * scale;
        canvasContext.strokeStyle = COLOR.BEACON_RADIUS;
        canvasContext.lineWidth = 1;
        canvasContext.beginPath();
        canvasContext.arc(screenX, screenY, radiusPixels, 0, 2 * Math.PI);
        canvasContext.stroke();
      }
    } catch (err) {
      console.error(`Error rendering beacon #${index}:`, err);
    }
  });
}

/**
 * 渲染轨迹
 * @private
 */
function renderTrajectory() {
  if (!canvasContext || !Array.isArray(trajectoryPoints) || trajectoryPoints.length < 2) {
    return;
  }
  
  // 设置轨迹样式
  canvasContext.strokeStyle = COLOR.TRAJECTORY;
  canvasContext.lineWidth = 2;
  
  canvasContext.beginPath();
  
  // 移动到第一个点
  const firstPoint = trajectoryPoints[0];
  canvasContext.moveTo(mapToScreenX(firstPoint.x), mapToScreenY(firstPoint.y));
  
  // 连接其余点
  for (let i = 1; i < trajectoryPoints.length; i++) {
    const point = trajectoryPoints[i];
    canvasContext.lineTo(mapToScreenX(point.x), mapToScreenY(point.y));
  }
  
  // 绘制线条
  canvasContext.stroke();
  
  // 绘制轨迹点
  trajectoryPoints.forEach((point, index) => {
    // 计算点的透明度（越新的点越不透明）
    const opacity = 0.3 + 0.7 * (index / trajectoryPoints.length);
    
    canvasContext.fillStyle = `rgba(3, 169, 244, ${opacity})`;
    canvasContext.beginPath();
    canvasContext.arc(mapToScreenX(point.x), mapToScreenY(point.y), 3, 0, 2 * Math.PI);
    canvasContext.fill();
  });
}

/**
 * 渲染当前位置
 * @private
 */
function renderCurrentPosition() {
  if (!canvasContext || !currentPosition) {
    return;
  }
  
  // 计算屏幕坐标
  const screenX = mapToScreenX(currentPosition.x);
  const screenY = mapToScreenY(currentPosition.y);
  
  // --- 恢复并美化样式 --- 
  const positionColor = COLOR.POSITION; // 使用预定义的绿色
  const haloColor = 'rgba(76, 175, 80, 0.2)'; // 浅绿色半透明光晕
  const pointRadius = 6; // 主点半径
  const haloRadius = 12; // 光晕半径
  
  // 重置透明度
  canvasContext.globalAlpha = 1.0;
  
  // 1. 绘制光晕 (半透明大圆)
  canvasContext.fillStyle = haloColor;
  canvasContext.beginPath();
  canvasContext.arc(screenX, screenY, haloRadius, 0, 2 * Math.PI);
  canvasContext.fill();

  // 2. 绘制位置点 (实心小圆)
  canvasContext.fillStyle = positionColor;
  canvasContext.beginPath();
  canvasContext.arc(screenX, screenY, pointRadius, 0, 2 * Math.PI);
  canvasContext.fill();
}

/**
 * 地图坐标转屏幕X坐标
 * @param {Number} mapX 地图X坐标（米）
 * @returns {Number} 屏幕X坐标（像素）
 */
function mapToScreenX(mapX) {
  return offset.x + mapX * scale;
}

/**
 * 地图坐标转屏幕Y坐标
 * @param {Number} mapY 地图Y坐标（米）
 * @returns {Number} 屏幕Y坐标（像素）
 */
function mapToScreenY(mapY) {
  // 模仿 config.js 中的绘制逻辑: offsetY + mapHeight * scale - mapY * scale
  // 注意: 这里的 offset.y 已经是 config.js 中的 offsetY (左上角偏移)
  // mapInfo.height 需要可用
  if (!mapInfo || mapInfo.height <= 0) {
    console.warn('[mapToScreenY] mapInfo or mapInfo.height is invalid, using fallback calculation');
    // 提供一个备用计算，虽然可能不完全准确
    return canvasSize.height - (offset.y + mapY * scale);
  }
  return offset.y + mapInfo.height * scale - mapY * scale;
}

/**
 * 屏幕坐标转地图X坐标
 * @param {Number} screenX 屏幕X坐标（像素）
 * @returns {Number} 地图X坐标（米）
 */
function screenToMapX(screenX) {
  return (screenX - offset.x) / scale;
}

/**
 * 屏幕坐标转地图Y坐标
 * @param {Number} screenY 屏幕Y坐标（像素）
 * @returns {Number} 地图Y坐标（米）
 */
function screenToMapY(screenY) {
  // Y轴方向相反, 从 mapToScreenY 反推:
  // screenY = offset.y + mapInfo.height * scale - mapY * scale
  // mapY * scale = offset.y + mapInfo.height * scale - screenY
  // mapY = (offset.y + mapInfo.height * scale - screenY) / scale
  if (scale === 0) return 0;
  if (!mapInfo || mapInfo.height <= 0) {
     console.warn('[screenToMapY] mapInfo or mapInfo.height is invalid, using fallback calculation');
     return (canvasSize.height - screenY - offset.y) / scale;
  }
  return (offset.y + mapInfo.height * scale - screenY) / scale;
}

/**
 * 获取渲染器状态
 * @returns {Object} 渲染器状态
 */
function getRendererState() {
  return {
    mapInfo: { ...mapInfo },
    scale,
    offset: { ...offset },
    canvasSize: { ...canvasSize },
    hasCurrentPosition: currentPosition !== null,
    trajectoryPointsCount: trajectoryPoints.length,
    beaconPointsCount: beaconPoints.length
  };
}

module.exports = {
  init,
  reset,
  setMapInfo,
  getMapInfo,
  setScale,
  getScale,
  setOffset,
  getOffset,
  setCanvasSize,
  setCurrentPosition,
  getCurrentPosition,
  addTrajectoryPoint,
  clearTrajectory,
  setBeaconPoints,
  getBeaconPoints,
  render,
  mapToScreenX,
  mapToScreenY,
  screenToMapX,
  screenToMapY,
  getRendererState
}; 
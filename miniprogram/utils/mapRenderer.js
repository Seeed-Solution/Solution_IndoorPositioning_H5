/**
 * 地图渲染器
 * 负责地图的加载和绘制
 */

// 地图信息
let mapInfo = null;
// 地图缩放比例
let mapScale = 1.0;
// 地图偏移量
let mapOffset = { x: 0, y: 0 };
// 当前位置点
let currentPosition = null;
// 历史轨迹点
let trajectoryPoints = [];
// 信标点
let beaconPoints = [];
// 地图配色
const mapColors = {
  background: '#f5f5f5',
  wall: '#333333',
  grid: '#dddddd',
  position: '#ff3b30',
  trajectory: '#5ac8fa',
  beacon: '#4cd964',
  beaconLabel: '#333333',
  axes: '#999999',
  axesLabel: '#666666'
};

/**
 * 初始化地图渲染器
 * @param {Object} map 地图信息
 * @returns {Boolean} 初始化是否成功
 */
function init(map) {
  if (!map) {
    console.error('初始化地图渲染器失败：无效的地图数据');
    return false;
  }
  
  mapInfo = { ...map };
  mapScale = 1.0;
  mapOffset = { x: 0, y: 0 };
  currentPosition = null;
  trajectoryPoints = [];
  
  console.log('地图渲染器初始化成功，地图尺寸:', mapInfo.width, 'x', mapInfo.height);
  return true;
}

/**
 * 设置地图信息
 * @param {Object} map 地图信息
 * @returns {Boolean} 设置是否成功
 */
function setMapInfo(map) {
  if (!map || typeof map.width !== 'number' || typeof map.height !== 'number') {
    console.error('设置地图信息失败：无效的地图数据');
    return false;
  }
  
  mapInfo = { ...map };
  console.log('地图信息已更新，尺寸:', mapInfo.width, 'x', mapInfo.height);
  return true;
}

/**
 * 获取当前地图信息
 * @returns {Object|null} 地图信息
 */
function getMapInfo() {
  return mapInfo ? { ...mapInfo } : null;
}

/**
 * 设置地图缩放比例
 * @param {Number} scale 缩放比例
 * @returns {Boolean} 设置是否成功
 */
function setMapScale(scale) {
  if (typeof scale !== 'number' || scale <= 0) {
    console.error('设置地图缩放比例失败：无效的比例值');
    return false;
  }
  
  mapScale = scale;
  return true;
}

/**
 * 设置地图偏移量
 * @param {Number} x X轴偏移量
 * @param {Number} y Y轴偏移量
 * @returns {Boolean} 设置是否成功
 */
function setMapOffset(x, y) {
  if (typeof x !== 'number' || typeof y !== 'number') {
    console.error('设置地图偏移量失败：无效的坐标值');
    return false;
  }
  
  mapOffset = { x, y };
  return true;
}

/**
 * 设置当前位置
 * @param {Object} position 位置对象，包含x、y坐标
 * @returns {Boolean} 设置是否成功
 */
function setCurrentPosition(position) {
  if (!position || typeof position.x !== 'number' || typeof position.y !== 'number') {
    currentPosition = null;
    return false;
  }
  
  currentPosition = { ...position };
  return true;
}

/**
 * 添加轨迹点
 * @param {Object} point 位置点，包含x、y坐标
 * @returns {Boolean} 添加是否成功
 */
function addTrajectoryPoint(point) {
  if (!point || typeof point.x !== 'number' || typeof point.y !== 'number') {
    console.error('添加轨迹点失败：无效的位置点');
    return false;
  }
  
  trajectoryPoints.push({ ...point });
  
  // 限制轨迹点数量
  const MAX_TRAJECTORY_POINTS = 200;
  if (trajectoryPoints.length > MAX_TRAJECTORY_POINTS) {
    trajectoryPoints = trajectoryPoints.slice(trajectoryPoints.length - MAX_TRAJECTORY_POINTS);
  }
  
  return true;
}

/**
 * 清除轨迹点
 */
function clearTrajectoryPoints() {
  trajectoryPoints = [];
  console.log('轨迹点已清除');
}

/**
 * 设置信标点
 * @param {Array} beacons 信标数组
 * @returns {Boolean} 设置是否成功
 */
function setBeaconPoints(beacons) {
  if (!Array.isArray(beacons)) {
    console.error('设置信标点失败：无效的信标数组');
    return false;
  }
  
  beaconPoints = beacons.map(beacon => {
    // 确保每个信标都有必要的属性
    return {
      uuid: beacon.uuid || '',
      major: beacon.major || 0,
      minor: beacon.minor || 0,
      x: beacon.x || 0,
      y: beacon.y || 0,
      name: beacon.name || `Beacon ${beacon.major || ''}-${beacon.minor || ''}`
    };
  });
  
  return true;
}

/**
 * 渲染地图到画布上
 * @param {Object} ctx 画布上下文
 * @param {Number} canvasWidth 画布宽度
 * @param {Number} canvasHeight 画布高度
 * @param {Object} options 渲染选项
 * @returns {Boolean} 渲染是否成功
 */
function renderMap(ctx, canvasWidth, canvasHeight, options = {}) {
  if (!ctx || !mapInfo) {
    console.error('渲染地图失败：无效的上下文或地图数据');
    return false;
  }
  
  const opts = {
    showGrid: options.showGrid !== false,
    showAxes: options.showAxes !== false,
    showBeacons: options.showBeacons !== false,
    showTrajectory: options.showTrajectory !== false,
    showCurrentPosition: options.showCurrentPosition !== false,
    ...options
  };
  
  try {
    // 清除画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // 绘制背景
    ctx.fillStyle = mapColors.background;
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    
    // 计算地图在画布上的实际位置和尺寸
    const mapWidth = mapInfo.width * mapScale;
    const mapHeight = mapInfo.height * mapScale;
    const mapLeft = (canvasWidth - mapWidth) / 2 + mapOffset.x;
    const mapTop = (canvasHeight - mapHeight) / 2 + mapOffset.y;
    
    // 绘制网格
    if (opts.showGrid) {
      renderGrid(ctx, mapLeft, mapTop, mapWidth, mapHeight);
    }
    
    // 绘制坐标轴
    if (opts.showAxes) {
      renderAxes(ctx, mapLeft, mapTop, mapWidth, mapHeight);
    }
    
    // 绘制地图实体（墙、门等）
    renderEntities(ctx, mapLeft, mapTop);
    
    // 绘制信标
    if (opts.showBeacons && beaconPoints.length > 0) {
      renderBeacons(ctx, mapLeft, mapTop);
    }
    
    // 绘制轨迹
    if (opts.showTrajectory && trajectoryPoints.length > 0) {
      renderTrajectory(ctx, mapLeft, mapTop);
    }
    
    // 绘制当前位置
    if (opts.showCurrentPosition && currentPosition) {
      renderCurrentPosition(ctx, mapLeft, mapTop);
    }
    
    return true;
  } catch (err) {
    console.error('渲染地图出错:', err);
    return false;
  }
}

/**
 * 绘制网格
 * @private
 */
function renderGrid(ctx, mapLeft, mapTop, mapWidth, mapHeight) {
  ctx.strokeStyle = mapColors.grid;
  ctx.lineWidth = 1;
  
  // 确定网格间距（实际坐标中1米对应的像素数）
  const gridSize = 1 * mapScale; // 1米
  
  // 绘制垂直线
  for (let x = 0; x <= mapInfo.width; x += 1) {
    const pixelX = mapLeft + x * mapScale;
    ctx.beginPath();
    ctx.moveTo(pixelX, mapTop);
    ctx.lineTo(pixelX, mapTop + mapHeight);
    ctx.stroke();
  }
  
  // 绘制水平线
  for (let y = 0; y <= mapInfo.height; y += 1) {
    const pixelY = mapTop + y * mapScale;
    ctx.beginPath();
    ctx.moveTo(mapLeft, pixelY);
    ctx.lineTo(mapLeft + mapWidth, pixelY);
    ctx.stroke();
  }
}

/**
 * 绘制坐标轴
 * @private
 */
function renderAxes(ctx, mapLeft, mapTop, mapWidth, mapHeight) {
  // 绘制X轴
  ctx.strokeStyle = mapColors.axes;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(mapLeft, mapTop + mapHeight);
  ctx.lineTo(mapLeft + mapWidth, mapTop + mapHeight);
  ctx.stroke();
  
  // 绘制Y轴
  ctx.beginPath();
  ctx.moveTo(mapLeft, mapTop + mapHeight);
  ctx.lineTo(mapLeft, mapTop);
  ctx.stroke();
  
  // 绘制刻度和标签
  ctx.fillStyle = mapColors.axesLabel;
  ctx.font = '12px Arial';
  ctx.textAlign = 'center';
  
  // X轴刻度和标签
  for (let x = 0; x <= mapInfo.width; x += 1) {
    const pixelX = mapLeft + x * mapScale;
    
    // 刻度线
    ctx.beginPath();
    ctx.moveTo(pixelX, mapTop + mapHeight);
    ctx.lineTo(pixelX, mapTop + mapHeight + 5);
    ctx.stroke();
    
    // 标签
    ctx.fillText(x.toString(), pixelX, mapTop + mapHeight + 15);
  }
  
  // Y轴刻度和标签
  ctx.textAlign = 'right';
  for (let y = 0; y <= mapInfo.height; y += 1) {
    const pixelY = mapTop + mapHeight - y * mapScale;
    
    // 刻度线
    ctx.beginPath();
    ctx.moveTo(mapLeft, pixelY);
    ctx.lineTo(mapLeft - 5, pixelY);
    ctx.stroke();
    
    // 标签
    ctx.fillText(y.toString(), mapLeft - 8, pixelY + 4);
  }
}

/**
 * 绘制地图实体
 * @private
 */
function renderEntities(ctx, mapLeft, mapTop) {
  if (!mapInfo.entities || !Array.isArray(mapInfo.entities)) {
    return;
  }
  
  for (const entity of mapInfo.entities) {
    switch (entity.type) {
      case 'polyline':
        renderPolyline(ctx, entity, mapLeft, mapTop);
        break;
      case 'polygon':
        renderPolygon(ctx, entity, mapLeft, mapTop);
        break;
      case 'circle':
        renderCircle(ctx, entity, mapLeft, mapTop);
        break;
      default:
        console.warn('未知的实体类型:', entity.type);
    }
  }
}

/**
 * 绘制折线
 * @private
 */
function renderPolyline(ctx, entity, mapLeft, mapTop) {
  if (!entity.points || entity.points.length < 2) {
    return;
  }
  
  ctx.strokeStyle = entity.strokeColor || mapColors.wall;
  ctx.lineWidth = entity.strokeWidth || 2;
  
  ctx.beginPath();
  
  // 移动到第一个点
  const firstPoint = entity.points[0];
  ctx.moveTo(
    mapLeft + firstPoint.x * mapScale,
    mapTop + (mapInfo.height - firstPoint.y) * mapScale
  );
  
  // 连接其余点
  for (let i = 1; i < entity.points.length; i++) {
    const point = entity.points[i];
    ctx.lineTo(
      mapLeft + point.x * mapScale,
      mapTop + (mapInfo.height - point.y) * mapScale
    );
  }
  
  // 如果是闭合折线，连接回第一个点
  if (entity.closed) {
    ctx.closePath();
  }
  
  ctx.stroke();
  
  // 如果有填充色，填充多边形
  if (entity.fillColor) {
    ctx.fillStyle = entity.fillColor;
    ctx.fill();
  }
}

/**
 * 绘制多边形
 * @private
 */
function renderPolygon(ctx, entity, mapLeft, mapTop) {
  // 多边形实际上是闭合的折线
  renderPolyline(ctx, { ...entity, closed: true }, mapLeft, mapTop);
}

/**
 * 绘制圆
 * @private
 */
function renderCircle(ctx, entity, mapLeft, mapTop) {
  if (!entity.center || typeof entity.radius !== 'number') {
    return;
  }
  
  ctx.strokeStyle = entity.strokeColor || mapColors.wall;
  ctx.lineWidth = entity.strokeWidth || 2;
  
  ctx.beginPath();
  ctx.arc(
    mapLeft + entity.center.x * mapScale,
    mapTop + (mapInfo.height - entity.center.y) * mapScale,
    entity.radius * mapScale,
    0,
    2 * Math.PI
  );
  ctx.stroke();
  
  // 如果有填充色，填充圆
  if (entity.fillColor) {
    ctx.fillStyle = entity.fillColor;
    ctx.fill();
  }
}

/**
 * 绘制信标
 * @private
 */
function renderBeacons(ctx, mapLeft, mapTop) {
  const BEACON_RADIUS = 8;
  
  for (const beacon of beaconPoints) {
    if (typeof beacon.x !== 'number' || typeof beacon.y !== 'number') {
      continue;
    }
    
    const x = mapLeft + beacon.x * mapScale;
    const y = mapTop + (mapInfo.height - beacon.y) * mapScale;
    
    // 绘制信标点
    ctx.fillStyle = mapColors.beacon;
    ctx.beginPath();
    ctx.arc(x, y, BEACON_RADIUS, 0, 2 * Math.PI);
    ctx.fill();
    
    // 绘制信标标签
    ctx.fillStyle = mapColors.beaconLabel;
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(beacon.name || `B${beacon.major}-${beacon.minor}`, x, y - BEACON_RADIUS - 5);
  }
}

/**
 * 绘制轨迹
 * @private
 */
function renderTrajectory(ctx, mapLeft, mapTop) {
  if (trajectoryPoints.length < 2) {
    return;
  }
  
  // 绘制线段
  ctx.strokeStyle = mapColors.trajectory;
  ctx.lineWidth = 2;
  ctx.beginPath();
  
  const firstPoint = trajectoryPoints[0];
  ctx.moveTo(
    mapLeft + firstPoint.x * mapScale,
    mapTop + (mapInfo.height - firstPoint.y) * mapScale
  );
  
  for (let i = 1; i < trajectoryPoints.length; i++) {
    const point = trajectoryPoints[i];
    ctx.lineTo(
      mapLeft + point.x * mapScale,
      mapTop + (mapInfo.height - point.y) * mapScale
    );
  }
  
  ctx.stroke();
  
  // 绘制轨迹点
  const POINT_RADIUS = 3;
  ctx.fillStyle = mapColors.trajectory;
  
  for (const point of trajectoryPoints) {
    ctx.beginPath();
    ctx.arc(
      mapLeft + point.x * mapScale,
      mapTop + (mapInfo.height - point.y) * mapScale,
      POINT_RADIUS,
      0,
      2 * Math.PI
    );
    ctx.fill();
  }
}

/**
 * 绘制当前位置
 * @private
 */
function renderCurrentPosition(ctx, mapLeft, mapTop) {
  if (!currentPosition) {
    return;
  }
  
  const x = mapLeft + currentPosition.x * mapScale;
  const y = mapTop + (mapInfo.height - currentPosition.y) * mapScale;
  
  // 绘制定位精度圆
  if (typeof currentPosition.accuracy === 'number' && currentPosition.accuracy > 0) {
    ctx.fillStyle = 'rgba(255, 59, 48, 0.2)';
    ctx.beginPath();
    ctx.arc(x, y, currentPosition.accuracy * mapScale, 0, 2 * Math.PI);
    ctx.fill();
  }
  
  // 绘制位置点
  const POSITION_RADIUS = 6;
  ctx.fillStyle = mapColors.position;
  ctx.beginPath();
  ctx.arc(x, y, POSITION_RADIUS, 0, 2 * Math.PI);
  ctx.fill();
  
  // 绘制十字线
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x - POSITION_RADIUS, y);
  ctx.lineTo(x + POSITION_RADIUS, y);
  ctx.moveTo(x, y - POSITION_RADIUS);
  ctx.lineTo(x, y + POSITION_RADIUS);
  ctx.stroke();
}

/**
 * 坐标转换：屏幕坐标转换为地图坐标
 * @param {Number} screenX 屏幕X坐标
 * @param {Number} screenY 屏幕Y坐标
 * @param {Number} canvasWidth 画布宽度
 * @param {Number} canvasHeight 画布高度
 * @returns {Object|null} 地图坐标
 */
function screenToMapCoordinates(screenX, screenY, canvasWidth, canvasHeight) {
  if (!mapInfo) {
    return null;
  }
  
  // 计算地图在画布上的实际位置和尺寸
  const mapWidth = mapInfo.width * mapScale;
  const mapHeight = mapInfo.height * mapScale;
  const mapLeft = (canvasWidth - mapWidth) / 2 + mapOffset.x;
  const mapTop = (canvasHeight - mapHeight) / 2 + mapOffset.y;
  
  // 检查点是否在地图范围内
  if (
    screenX < mapLeft ||
    screenX > mapLeft + mapWidth ||
    screenY < mapTop ||
    screenY > mapTop + mapHeight
  ) {
    return null;
  }
  
  // 转换坐标
  const mapX = (screenX - mapLeft) / mapScale;
  const mapY = mapInfo.height - (screenY - mapTop) / mapScale;
  
  return { x: mapX, y: mapY };
}

/**
 * 坐标转换：地图坐标转换为屏幕坐标
 * @param {Number} mapX 地图X坐标
 * @param {Number} mapY 地图Y坐标
 * @param {Number} canvasWidth 画布宽度
 * @param {Number} canvasHeight 画布高度
 * @returns {Object} 屏幕坐标
 */
function mapToScreenCoordinates(mapX, mapY, canvasWidth, canvasHeight) {
  if (!mapInfo) {
    return null;
  }
  
  // 计算地图在画布上的实际位置和尺寸
  const mapWidth = mapInfo.width * mapScale;
  const mapHeight = mapInfo.height * mapScale;
  const mapLeft = (canvasWidth - mapWidth) / 2 + mapOffset.x;
  const mapTop = (canvasHeight - mapHeight) / 2 + mapOffset.y;
  
  // 转换坐标
  const screenX = mapLeft + mapX * mapScale;
  const screenY = mapTop + (mapInfo.height - mapY) * mapScale;
  
  return { x: screenX, y: screenY };
}

module.exports = {
  init,
  setMapInfo,
  getMapInfo,
  setMapScale,
  setMapOffset,
  setCurrentPosition,
  addTrajectoryPoint,
  clearTrajectoryPoints,
  setBeaconPoints,
  renderMap,
  screenToMapCoordinates,
  mapToScreenCoordinates
}; 
// dxfParser.js
// DXF文件解析工具

/**
 * 解析DXF文件内容
 * @param {string} dxfContent DXF文件内容
 * @returns {Object} 解析后的图形数据
 */
function parseDXF(dxfContent) {
  console.log('开始解析DXF，内容长度:', dxfContent.length);
  
  // 将DXF内容按行分割
  const lines = dxfContent.split(/\r\n|\r|\n/);
  console.log('DXF总行数:', lines.length);
  
  // 解析结果
  const result = {
    entities: [],
    viewBox: { x: 0, y: 0, width: 0, height: 0 },
    bounds: { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
  };
  
  // 当前正在处理的实体
  let currentEntity = null;
  
  // 当前正在处理的段落
  let currentSection = null;
  
  // 临时保存坐标值
  let x1, y1, x2, y2, cx, cy, radius;
  
  // 存储POLYLINE实体，用于后续与VERTEX关联
  let activePoly = null;
  
  // 用于直接提取POLYLINE顶点的临时变量
  let lastVertexX = null;
  let lastVertexY = null;
  let inVertexMode = false;
  
  // 调试信息：记录部分DXF内容
  if (lines.length > 20) {
    console.log('DXF文件前20行:', lines.slice(0, 20));
    
    // 查找ENTITIES部分
    const entitiesIndex = lines.findIndex((line, i) => 
      line.trim() === '0' && 
      lines[i+1]?.trim() === 'SECTION' && 
      lines[i+3]?.trim() === 'ENTITIES'
    );
    
    if (entitiesIndex >= 0) {
      console.log('找到ENTITIES部分，从行:', entitiesIndex);
      console.log('ENTITIES部分开始的内容:', lines.slice(entitiesIndex, entitiesIndex + 20));
      
      // 尝试寻找第一个完整的实体定义
      let entityStart = -1;
      for (let i = entitiesIndex + 4; i < Math.min(lines.length, entitiesIndex + 100); i++) {
        if (lines[i]?.trim() === '0') {
          entityStart = i;
          break;
        }
      }
      
      if (entityStart > 0) {
        console.log('第一个实体定义开始于行:', entityStart);
        console.log('实体详情:', lines.slice(entityStart, entityStart + 30));
      }
    } else {
      console.warn('未找到ENTITIES部分!');
    }
  }
  
  // 检查是否为2D文件
  let is3DFile = false;
  
  // 记录实体创建与处理
  let entityStats = {
    found: 0,
    processed: 0,
    polylineVertices: 0,
    types: {}
  };
  
  // 直接扫描第一遍，收集所有POLYLINE的VERTEX
  let polylines = [];
  let currentPolyline = null;
  
  // 第一遍：收集所有POLYLINE和VERTEX
  console.log('======= 第一遍扫描：收集POLYLINE和VERTEX =======');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]?.trim() || '';
    const nextLine = (i < lines.length - 1) ? lines[i + 1]?.trim() || '' : '';
    
    // 空行跳过
    if (line === '') continue;
    
    // 开始新段落
    if (line === '0' && nextLine === 'SECTION') {
      i += 2; // 跳过SECTION和组码
      if (i < lines.length) {
        currentSection = lines[i]?.trim() || '';
      }
      continue;
    }
    
    // 结束段落
    if (line === '0' && nextLine === 'ENDSEC') {
      currentSection = null;
      i++; // 跳过ENDSEC
      continue;
    }
    
    // 只处理ENTITIES段落
    if (currentSection !== 'ENTITIES') continue;
    
    // 实体类型
    if (line === '0' && nextLine !== 'SECTION' && nextLine !== 'ENDSEC') {
      // 实体开始
      entityStats.found++;
      
      // 实体统计
      entityStats.types[nextLine] = (entityStats.types[nextLine] || 0) + 1;
      
      if (nextLine === 'POLYLINE') {
        // 新建POLYLINE
        currentPolyline = {
          type: 'POLYLINE',
          points: [],
          closed: false
        };
        polylines.push(currentPolyline);
        console.log(`发现POLYLINE #${polylines.length}`);
      } else if (nextLine === 'VERTEX' && currentPolyline) {
        // 在VERTEX模式下
        inVertexMode = true;
        lastVertexX = null;
        lastVertexY = null;
      } else if (nextLine === 'SEQEND' && currentPolyline) {
        // POLYLINE结束
        console.log(`POLYLINE #${polylines.length} 完成，点数: ${currentPolyline.points.length}`);
        currentPolyline = null;
        inVertexMode = false;
      }
      
      i++; // 跳过下一行
      continue;
    }
    
    // 处理POLYLINE属性
    if (currentPolyline) {
      if (line === '70') { // 闭合标志
        const flags = parseInt(nextLine) || 0;
        currentPolyline.closed = (flags & 1) === 1;
        console.log(`POLYLINE闭合标志: ${flags}, 闭合状态: ${currentPolyline.closed}`);
        i++;
        continue;
      }
      
      // 处理VERTEX坐标
      if (inVertexMode) {
        if (line === '10') { // X坐标
          lastVertexX = parseFloat(nextLine);
          i++;
          continue;
        }
        
        if (line === '20') { // Y坐标
          lastVertexY = parseFloat(nextLine);
          i++;
          
          // 如果X和Y都有了，添加点
          if (lastVertexX !== null && lastVertexY !== null) {
            currentPolyline.points.push({ x: lastVertexX, y: lastVertexY });
            entityStats.polylineVertices++;
            console.log(`添加VERTEX点 (${lastVertexX}, ${lastVertexY}) 到POLYLINE`);
            
            // 更新边界
            updateBounds(result.bounds, lastVertexX, lastVertexY);
            
            lastVertexX = null;
            lastVertexY = null;
          }
          continue;
        }
      }
    }
  }
  
  console.log('POLYLINE扫描结果:', polylines.length, '个多段线，', entityStats.polylineVertices, '个顶点');
  
  // 第二遍：处理常规实体
  console.log('======= 第二遍扫描：处理常规实体 =======');
  currentSection = null;
  
  // 逐行解析
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]?.trim() || '';
    const nextLine = (i < lines.length - 1) ? lines[i + 1]?.trim() || '' : '';
    
    // 空行跳过
    if (line === '') continue;
    
    // 检查是否有3D指示符
    if ((line === '70' || line === '100') && (nextLine === 'AcDb3dPolyline' || nextLine === '3DFACE')) {
      is3DFile = true;
      console.warn('检测到3D元素，这可能不被完全支持');
    }
    
    // 处理AcDb2dPolyline等CAD实体类型标识
    if (line === '100' && nextLine === 'AcDb2dPolyline') {
      console.log('发现AcDb2dPolyline标识，当前位置:', i);
      
      // 尝试提取后续30行，查看多段线定义格式
      console.log('AcDb2dPolyline后续内容:', lines.slice(i+2, i+30));
    }
    
    // 开始新段落
    if (line === '0' && nextLine === 'SECTION') {
      i += 2; // 跳过SECTION和组码
      if (i < lines.length) {
        currentSection = lines[i]?.trim() || '';
        console.log('开始新段落:', currentSection);
      }
      continue;
    }
    
    // 结束段落
    if (line === '0' && nextLine === 'ENDSEC') {
      currentSection = null;
      i++; // 跳过ENDSEC
      continue;
    }
    
    // 只处理ENTITIES段落
    if (currentSection !== 'ENTITIES') continue;
    
    // 实体类型
    if (line === '0' && nextLine !== 'SECTION' && nextLine !== 'ENDSEC') {
      // 保存上一个实体（如果不是VERTEX或POLYLINE）
      if (currentEntity && Object.keys(currentEntity).length > 2 && 
          currentEntity.type !== 'VERTEX' && currentEntity.type !== 'POLYLINE') {
        console.log('添加实体:', currentEntity.type, 
                    currentEntity.points ? `点数:${currentEntity.points.length}` : '');
        result.entities.push(currentEntity);
        entityStats.processed++;
      }
      
      // 处理VERTEX结束，转到下一个VERTEX或结束POLYLINE
      if (nextLine !== 'VERTEX' && nextLine !== 'SEQEND' && activePoly) {
        // 结束当前多段线，保存它
        console.log('多段线结束，点数:', activePoly.points.length);
        if (activePoly.points.length > 0) {
          result.entities.push(activePoly);
          entityStats.processed++;
        }
        activePoly = null;
      }
      
      // 创建新实体
      currentEntity = {
        type: nextLine,
        points: []
      };
      
      if (nextLine === 'SEQEND') {
        // 遇到SEQEND，结束POLYLINE
        if (activePoly) {
          console.log('SEQEND: 多段线结束，点数:', activePoly.points.length);
          if (activePoly.points.length > 0) {
            result.entities.push(activePoly);
            entityStats.processed++;
          }
          activePoly = null;
        }
        currentEntity = null;
      } else if (nextLine === 'POLYLINE') {
        // 创建新的多段线对象
        activePoly = {
          type: 'POLYLINE',
          points: [],
          closed: false
        };
        console.log('开始新的POLYLINE');
      } else if (nextLine === 'VERTEX' && activePoly) {
        // 将顶点关联到当前的多段线
        currentEntity.parentPolyline = activePoly;
        console.log('VERTEX: 关联到当前POLYLINE');
      } else {
        console.log('发现新实体类型:', nextLine);
      }
      
      // 重置临时变量
      x1 = y1 = x2 = y2 = cx = cy = radius = undefined;
      
      i++; // 跳过下一行
      continue;
    }
    
    // 解析实体数据
    if (currentEntity || activePoly) {
      // 处理LWPOLYLINE特殊情况（AutoCAD常用格式）
      if (currentEntity && currentEntity.type === 'LWPOLYLINE') {
        if (line === '90') {  // 顶点数量
          currentEntity.vertexCount = parseInt(nextLine) || 0;
          console.log('LWPOLYLINE顶点数:', currentEntity.vertexCount);
          i++;
          continue;
        }
        
        if (line === '70') {  // 闭合标志
          currentEntity.closed = parseInt(nextLine) & 1 ? true : false;
          i++;
          continue;
        }
        
        // LWPOLYLINE格式中的点是连续的X,Y值，用组码10,20标识
        if (line === '10') {  // X坐标
          const x = parseFloat(nextLine);
          i++;
          
          // 查找对应的Y坐标
          while (i < lines.length && lines[i]?.trim() !== '20') {
            i++;
          }
          
          if (i < lines.length && lines[i]?.trim() === '20') {
            const y = parseFloat(lines[i+1]?.trim() || '0');
            i += 2;
            
            // 添加点到多段线
            const point = { x, y };
            currentEntity.points.push(point);
            
            // 更新边界
            updateBounds(result.bounds, x, y);
          }
          
          continue;
        }
      }
      
      // POLYLINE特殊处理
      if (activePoly && !currentEntity) {
        if (line === '70') {  // 闭合标志
          const flags = parseInt(nextLine) || 0;
          activePoly.closed = (flags & 1) === 1;
          console.log('POLYLINE闭合标志:', flags, '是否闭合:', activePoly.closed);
          i++;
          continue;
        }
      }
      
      // 通用实体处理
      switch (line) {
        case '10':  // X坐标
          const x = parseFloat(nextLine);
          i++;
          
          // 不同实体类型的处理
          switch (currentEntity?.type) {
            case 'LINE':
              x1 = x;
              currentEntity.x1 = x;
              break;
            case 'CIRCLE':
            case 'ARC':
              cx = x;
              currentEntity.cx = x;
              break;
            case 'TEXT':
            case 'MTEXT':
              currentEntity.x = x;
              break;
            case 'POLYLINE':
              // POLYLINE中的10,20通常不是点坐标，而是某种偏移
              break;
            case 'VERTEX':
              if (currentEntity.parentPolyline) {
                // 记录顶点位置准备添加到父多段线
                currentEntity.x = x;
              } else {
                // 处理孤立的VERTEX
                currentEntity.x = x;
              }
              break;
            case 'RECTANGLE':
              // 某些CAD可能将矩形表示为RECTANGLE
              if (!currentEntity.x1) {
                currentEntity.x1 = x;
              } else {
                currentEntity.x2 = x;
              }
              break;
          }
          break;
          
        case '20':  // Y坐标
          const y = parseFloat(nextLine);
          i++;
          
          // 不同实体类型的处理
          switch (currentEntity?.type) {
            case 'LINE':
              y1 = y;
              currentEntity.y1 = y;
              break;
            case 'CIRCLE':
            case 'ARC':
              cy = y;
              currentEntity.cy = y;
              break;
            case 'TEXT':
            case 'MTEXT':
              currentEntity.y = y;
              break;
            case 'VERTEX':
              if (currentEntity.parentPolyline) {
                currentEntity.y = y;
                
                // 添加点到父多段线
                if (currentEntity.x !== undefined && currentEntity.y !== undefined) {
                  const point = { x: currentEntity.x, y: currentEntity.y };
                  currentEntity.parentPolyline.points.push(point);
                  
                  // 更新边界
                  updateBounds(result.bounds, currentEntity.x, currentEntity.y);
                  console.log('添加点到POLYLINE:', point);
                }
              } else {
                currentEntity.y = y;
                
                // 坐标已收集完成，更新边界
                updateBounds(result.bounds, currentEntity.x, currentEntity.y);
              }
              break;
            case 'RECTANGLE':
              if (!currentEntity.y1) {
                currentEntity.y1 = y;
              } else {
                currentEntity.y2 = y;
              }
              
              // 如果已经有x1,y1,x2,y2，计算边界
              if (currentEntity.x1 !== undefined && currentEntity.y1 !== undefined &&
                  currentEntity.x2 !== undefined && currentEntity.y2 !== undefined) {
                updateBounds(result.bounds, currentEntity.x1, currentEntity.y1);
                updateBounds(result.bounds, currentEntity.x2, currentEntity.y2);
              }
              break;
          }
          break;
          
        case '11':  // 第二个X坐标（LINE终点）
          x2 = parseFloat(nextLine);
          currentEntity.x2 = x2;
          i++;
          break;
          
        case '21':  // 第二个Y坐标（LINE终点）
          y2 = parseFloat(nextLine);
          currentEntity.y2 = y2;
          i++;
          
          // 更新LINE实体的边界
          if (currentEntity?.type === 'LINE' && 
              x1 !== undefined && y1 !== undefined && 
              x2 !== undefined && y2 !== undefined) {
            updateBounds(result.bounds, x1, y1);
            updateBounds(result.bounds, x2, y2);
          }
          break;
          
        case '40':  // 半径/高度
          const value = parseFloat(nextLine);
          i++;
          
          if (currentEntity?.type === 'CIRCLE' || currentEntity?.type === 'ARC') {
            radius = value;
            currentEntity.radius = value;
            
            // 更新圆的边界
            if (cx !== undefined && cy !== undefined && radius !== undefined) {
              updateBounds(result.bounds, cx - radius, cy - radius);
              updateBounds(result.bounds, cx + radius, cy + radius);
            }
          } 
          else if (currentEntity?.type === 'TEXT' || currentEntity?.type === 'MTEXT') {
            currentEntity.height = value;
          }
          break;
          
        case '50':  // 起始角度
          if (currentEntity) {
            currentEntity.startAngle = parseFloat(nextLine) * (Math.PI / 180);
          }
          i++;
          break;
          
        case '51':  // 结束角度
          if (currentEntity) {
            currentEntity.endAngle = parseFloat(nextLine) * (Math.PI / 180);
          }
          i++;
          break;
          
        case '1':  // 文本内容
          if (currentEntity?.type === 'TEXT' || currentEntity?.type === 'MTEXT') {
            currentEntity.text = nextLine;
            i++;
            
            // 更新文本边界
            if (currentEntity.x !== undefined && currentEntity.y !== undefined) {
              updateBounds(result.bounds, currentEntity.x, currentEntity.y);
            }
          } else {
            i++;  // 其他实体中的字符串属性，跳过
          }
          break;
          
        case '62':  // 颜色
          if (currentEntity) {
            currentEntity.color = parseInt(nextLine);
          }
          i++;
          break;
          
        case '66':  // Vertex follows flag (for POLYLINE)
          const flag = parseInt(nextLine) || 0;
          if (currentEntity?.type === 'POLYLINE' && flag === 1) {
            console.log('POLYLINE: 设置顶点跟随标志');
            currentEntity.hasVertices = true;
          }
          i++;
          break;
          
        default:
          i++;  // 跳过未识别的组码及其值
          break;
      }
    }
  }
  
  // 添加最后一个实体
  if (currentEntity && Object.keys(currentEntity).length > 2 && currentEntity.type !== 'VERTEX') {
    console.log('添加最后一个实体:', currentEntity.type);
    result.entities.push(currentEntity);
    entityStats.processed++;
  }
  
  // 确保添加最后活动的POLYLINE
  if (activePoly && activePoly.points.length > 0) {
    console.log('添加最后活动的POLYLINE, 点数:', activePoly.points.length);
    result.entities.push(activePoly);
    entityStats.processed++;
  }
  
  // 如果直接扫描到的POLYLINE有效，添加到结果
  if (polylines.length > 0) {
    console.log('从第一遍扫描添加POLYLINE实体');
    for (const poly of polylines) {
      if (poly.points.length > 0) {
        console.log(`添加POLYLINE，点数: ${poly.points.length}`);
        result.entities.push(poly);
        entityStats.processed++;
      }
    }
  }
  
  // 如果没有实体，但找到了多段线，则转换ACAD POLYLINE特殊格式
  if (result.entities.length === 0 && entityStats.types['POLYLINE'] > 0) {
    console.log('尝试采用特殊方式处理AutoCAD POLYLINE');
    
    // 从头再扫描一遍，专门处理AutoCAD特殊格式的POLYLINE
    const specialPolylines = [];
    let currentSpecialPoly = null;
    let collectingVertices = false;
    let tempX = null, tempY = null;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]?.trim() || '';
      const nextLine = (i < lines.length - 1) ? lines[i + 1]?.trim() || '' : '';
      
      if (line === '0' && nextLine === 'POLYLINE') {
        currentSpecialPoly = { type: 'POLYLINE', points: [], closed: false };
        specialPolylines.push(currentSpecialPoly);
        collectingVertices = true;
        i++; // 跳过POLYLINE
        continue;
      }
      
      if (collectingVertices && line === '0' && nextLine === 'SEQEND') {
        collectingVertices = false;
        i++; // 跳过SEQEND
        continue;
      }
      
      if (collectingVertices && line === '0' && nextLine === 'VERTEX') {
        tempX = tempY = null;
        i++; // 跳过VERTEX
        continue;
      }
      
      if (collectingVertices) {
        if (line === '10') { // X坐标
          tempX = parseFloat(nextLine);
          i++;
          continue;
        }
        
        if (line === '20' && tempX !== null) { // Y坐标
          tempY = parseFloat(nextLine);
          i++;
          
          // 添加点
          if (currentSpecialPoly && tempX !== null && tempY !== null) {
            currentSpecialPoly.points.push({ x: tempX, y: tempY });
            updateBounds(result.bounds, tempX, tempY);
            console.log(`添加特殊VERTEX点 (${tempX}, ${tempY})`);
          }
          
          continue;
        }
        
        if (line === '70') { // 闭合标志（可能在POLYLINE或VERTEX处）
          const flags = parseInt(nextLine) || 0;
          if (currentSpecialPoly) {
            currentSpecialPoly.closed = (flags & 1) === 1;
          }
          i++;
          continue;
        }
      }
    }
    
    // 添加有效的特殊POLYLINE
    for (const poly of specialPolylines) {
      if (poly.points.length > 0) {
        console.log(`添加特殊处理的POLYLINE，点数: ${poly.points.length}`);
        result.entities.push(poly);
      }
    }
  }
  
  // 处理空的LWPOLYLINE
  result.entities.forEach(entity => {
    if (entity.type === 'LWPOLYLINE' && entity.points.length === 0 && entity.vertexCount) {
      console.warn('发现空的LWPOLYLINE，顶点数应为:', entity.vertexCount);
    }
  });
  
  // 处理边界
  if (result.bounds.minX === Infinity) {
    // 如果没有找到有效实体，设置默认边界
    result.bounds = { minX: 0, minY: 0, maxX: 100, maxY: 100 };
    console.warn('未找到有效实体，使用默认边界');
  }
  
  // 计算视图范围
  result.viewBox = {
    x: result.bounds.minX,
    y: result.bounds.minY,
    width: Math.max(result.bounds.maxX - result.bounds.minX, 1),
    height: Math.max(result.bounds.maxY - result.bounds.minY, 1)
  };
  
  console.log('DXF解析完成，解析到实体数量:', result.entities.length);
  console.log('实体统计:', entityStats);
  console.log('实体类型统计:', result.entities.reduce((acc, entity) => {
    acc[entity.type] = (acc[entity.type] || 0) + 1;
    return acc;
  }, {}));
  console.log('视图范围:', result.viewBox);
  
  // 如果是3D文件但无实体
  if (is3DFile && result.entities.length === 0) {
    console.warn('这似乎是一个3D DXF文件，可能不被完全支持');
  }
  
  return result;
}

/**
 * 更新边界值
 * @param {Object} bounds 边界对象
 * @param {number} x X坐标
 * @param {number} y Y坐标
 */
function updateBounds(bounds, x, y) {
  if (isNaN(x) || isNaN(y)) return;
  
  if (x < bounds.minX) bounds.minX = x;
  if (y < bounds.minY) bounds.minY = y;
  if (x > bounds.maxX) bounds.maxX = x;
  if (y > bounds.maxY) bounds.maxY = y;
}

/**
 * 将解析后的DXF绘制到Canvas上
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} dxfData 解析后的DXF数据
 * @param {number} scale 缩放比例
 * @param {Object} offset 偏移量 {x, y}
 */
function drawDXFToCanvas(ctx, dxfData, scale, offset = { x: 0, y: 0 }) {
  console.log('开始绘制DXF到Canvas，实体数量:', dxfData.entities.length);
  
  // 清空画布
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  
  // 设置默认样式
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#333';
  ctx.font = '12px sans-serif';
  
  // 绘制每个实体
  let drawnEntities = 0;
  
  dxfData.entities.forEach(entity => {
    try {
      ctx.beginPath();
      
      switch (entity.type) {
        case 'LINE':
          if (entity.x1 !== undefined && entity.y1 !== undefined && 
              entity.x2 !== undefined && entity.y2 !== undefined) {
            ctx.moveTo(entity.x1 * scale + offset.x, entity.y1 * scale + offset.y);
            ctx.lineTo(entity.x2 * scale + offset.x, entity.y2 * scale + offset.y);
            ctx.stroke();
            drawnEntities++;
          }
          break;
          
        case 'CIRCLE':
          if (entity.cx !== undefined && entity.cy !== undefined && entity.radius !== undefined) {
            ctx.arc(
              entity.cx * scale + offset.x,
              entity.cy * scale + offset.y,
              entity.radius * scale,
              0,
              Math.PI * 2
            );
            ctx.stroke();
            drawnEntities++;
          }
          break;
          
        case 'ARC':
          if (entity.cx !== undefined && entity.cy !== undefined && 
              entity.radius !== undefined && 
              entity.startAngle !== undefined && entity.endAngle !== undefined) {
            ctx.arc(
              entity.cx * scale + offset.x,
              entity.cy * scale + offset.y,
              entity.radius * scale,
              entity.startAngle,
              entity.endAngle,
              false // 逆时针
            );
            ctx.stroke();
            drawnEntities++;
          }
          break;
          
        case 'TEXT':
        case 'MTEXT':
          if (entity.x !== undefined && entity.y !== undefined && entity.text) {
            ctx.fillText(
              entity.text,
              entity.x * scale + offset.x,
              entity.y * scale + offset.y
            );
            drawnEntities++;
          }
          break;
          
        case 'LWPOLYLINE':
        case 'POLYLINE':
          if (entity.points && entity.points.length > 0) {
            // 绘制多段线
            ctx.moveTo(
              entity.points[0].x * scale + offset.x,
              entity.points[0].y * scale + offset.y
            );
            
            for (let i = 1; i < entity.points.length; i++) {
              ctx.lineTo(
                entity.points[i].x * scale + offset.x,
                entity.points[i].y * scale + offset.y
              );
            }
            
            // 如果是闭合多段线，连接最后一点到第一点
            if (entity.closed) {
              ctx.closePath();
            }
            
            ctx.stroke();
            drawnEntities++;
          }
          break;
          
        case 'RECTANGLE':
          if (entity.x1 !== undefined && entity.y1 !== undefined &&
              entity.x2 !== undefined && entity.y2 !== undefined) {
            const x = Math.min(entity.x1, entity.x2) * scale + offset.x;
            const y = Math.min(entity.y1, entity.y2) * scale + offset.y;
            const width = Math.abs(entity.x2 - entity.x1) * scale;
            const height = Math.abs(entity.y2 - entity.y1) * scale;
            
            ctx.rect(x, y, width, height);
            ctx.stroke();
            drawnEntities++;
          }
          break;
          
        case 'VERTEX':
          // 单独的顶点绘制为小点
          if (entity.x !== undefined && entity.y !== undefined) {
            ctx.arc(
              entity.x * scale + offset.x,
              entity.y * scale + offset.y,
              2, // 小点半径
              0,
              Math.PI * 2
            );
            ctx.fill();
            drawnEntities++;
          }
          break;
      }
    } catch (e) {
      console.error('绘制实体出错:', entity.type, e);
    }
  });
  
  console.log('DXF绘制完成，成功绘制实体数量:', drawnEntities);
  
  // 如果没有绘制任何实体，显示提示
  if (drawnEntities === 0) {
    ctx.fillStyle = 'red';
    ctx.font = '14px sans-serif';
    ctx.fillText('未找到可绘制的DXF实体', 20, 50);
    
    // 绘制边框，以便看到Canvas位置
    ctx.strokeStyle = '#999';
    ctx.strokeRect(5, 5, ctx.canvas.width - 10, ctx.canvas.height - 10);
  }
}

module.exports = {
  parseDXF,
  drawDXFToCanvas
}; 
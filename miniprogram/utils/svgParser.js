/**
 * SVG解析器 - 简化版
 * 用于解析SVG文件并转换为Canvas绘图指令
 * 
 * 支持的SVG元素:
 * - path
 * - rect
 * - circle
 * - line
 * - polyline
 * - polygon
 */

// SVG路径命令解析正则表达式
const PATH_COMMAND_REGEX = /([a-zA-Z])([^a-zA-Z]*)/g;
// 数字解析正则表达式
const NUMBER_REGEX = /-?[\d.]+/g;
// 路径命令参数数量映射
const PATH_PARAM_COUNTS = {
  M: 2, m: 2, L: 2, l: 2, H: 1, h: 1, V: 1, v: 1,
  C: 6, c: 6, S: 4, s: 4, Q: 4, q: 4, T: 2, t: 2,
  A: 7, a: 7, Z: 0, z: 0
};

/**
 * 解析SVG字符串
 * @param {String} svgString SVG文件内容
 * @return {Object} 解析结果，包含viewBox和元素列表
 */
function parseSVG(svgString) {
  try {
    // 创建一个临时的DOM解析器
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(svgString, "application/xml");
    
    // 获取svg根元素
    const svgElement = xmlDoc.getElementsByTagName("svg")[0];
    if (!svgElement) {
      throw new Error('无效的SVG文件：未找到SVG元素');
    }
    
    // 解析viewBox
    let viewBox = { x: 0, y: 0, width: 100, height: 100 };
    if (svgElement.hasAttribute("viewBox")) {
      const vb = svgElement.getAttribute("viewBox").split(/\s+/).map(parseFloat);
      if (vb.length === 4) {
        viewBox = { x: vb[0], y: vb[1], width: vb[2], height: vb[3] };
      }
    } else if (svgElement.hasAttribute("width") && svgElement.hasAttribute("height")) {
      viewBox.width = parseFloat(svgElement.getAttribute("width"));
      viewBox.height = parseFloat(svgElement.getAttribute("height"));
    }
    
    // 解析元素
    const elements = parseElements(svgElement);
    
    return {
      viewBox,
      elements
    };
  } catch (e) {
    console.error('解析SVG时出错:', e);
    return { viewBox: {x: 0, y: 0, width: 100, height: 100}, elements: [] };
  }
}

/**
 * 递归解析SVG元素
 * @param {Element} parent 父元素
 * @return {Array} 元素列表
 */
function parseElements(parent) {
  const elements = [];
  
  // 支持的SVG元素类型
  const SUPPORTED_ELEMENTS = ['path', 'rect', 'circle', 'line', 'polyline', 'polygon'];
  
  // 遍历所有子元素
  for (let i = 0; i < parent.childNodes.length; i++) {
    const node = parent.childNodes[i];
    
    // 检查是否是元素节点
    if (node.nodeType === 1) { // ELEMENT_NODE
      const tagName = node.tagName.toLowerCase();
      
      // 检查是否是支持的元素类型
      if (SUPPORTED_ELEMENTS.includes(tagName)) {
        elements.push(parseElement(node));
      }
      
      // 处理嵌套元素 (如g元素)
      if (node.childNodes.length > 0) {
        const childElements = parseElements(node);
        elements.push(...childElements);
      }
    }
  }
  
  return elements;
}

/**
 * 解析单个SVG元素
 * @param {Element} element SVG元素
 * @return {Object} 元素对象
 */
function parseElement(element) {
  const tagName = element.tagName.toLowerCase();
  const result = {
    type: tagName,
    style: parseStyle(element)
  };
  
  // 根据元素类型解析特定属性
  switch (tagName) {
    case 'path':
      result.commands = parsePath(element.getAttribute('d') || '');
      break;
    case 'rect':
      result.x = parseFloat(element.getAttribute('x') || 0);
      result.y = parseFloat(element.getAttribute('y') || 0);
      result.width = parseFloat(element.getAttribute('width') || 0);
      result.height = parseFloat(element.getAttribute('height') || 0);
      result.rx = parseFloat(element.getAttribute('rx') || 0);
      result.ry = parseFloat(element.getAttribute('ry') || 0);
      break;
    case 'circle':
      result.cx = parseFloat(element.getAttribute('cx') || 0);
      result.cy = parseFloat(element.getAttribute('cy') || 0);
      result.r = parseFloat(element.getAttribute('r') || 0);
      break;
    case 'line':
      result.x1 = parseFloat(element.getAttribute('x1') || 0);
      result.y1 = parseFloat(element.getAttribute('y1') || 0);
      result.x2 = parseFloat(element.getAttribute('x2') || 0);
      result.y2 = parseFloat(element.getAttribute('y2') || 0);
      break;
    case 'polyline':
    case 'polygon':
      result.points = parsePoints(element.getAttribute('points') || '');
      break;
  }
  
  return result;
}

/**
 * 解析元素样式
 * @param {Element} element SVG元素
 * @return {Object} 样式对象
 */
function parseStyle(element) {
  const style = {
    fill: 'black',
    stroke: 'none',
    strokeWidth: 1,
    fillOpacity: 1,
    strokeOpacity: 1
  };
  
  // 处理直接属性
  if (element.hasAttribute('fill')) {
    style.fill = element.getAttribute('fill');
  }
  if (element.hasAttribute('stroke')) {
    style.stroke = element.getAttribute('stroke');
  }
  if (element.hasAttribute('stroke-width')) {
    style.strokeWidth = parseFloat(element.getAttribute('stroke-width'));
  }
  if (element.hasAttribute('fill-opacity')) {
    style.fillOpacity = parseFloat(element.getAttribute('fill-opacity'));
  }
  if (element.hasAttribute('stroke-opacity')) {
    style.strokeOpacity = parseFloat(element.getAttribute('stroke-opacity'));
  }
  
  // 处理style属性
  if (element.hasAttribute('style')) {
    const styleAttr = element.getAttribute('style');
    const styleParts = styleAttr.split(';');
    
    for (let part of styleParts) {
      const [key, value] = part.split(':').map(str => str.trim());
      
      if (key === 'fill') style.fill = value;
      else if (key === 'stroke') style.stroke = value;
      else if (key === 'stroke-width') style.strokeWidth = parseFloat(value);
      else if (key === 'fill-opacity') style.fillOpacity = parseFloat(value);
      else if (key === 'stroke-opacity') style.strokeOpacity = parseFloat(value);
    }
  }
  
  return style;
}

/**
 * 解析SVG路径
 * @param {String} pathData 路径数据 (d属性)
 * @return {Array} 路径命令列表
 */
function parsePath(pathData) {
  const commands = [];
  let lastCommand = null;
  
  // 匹配所有路径命令
  const matches = pathData.matchAll(PATH_COMMAND_REGEX);
  for (const match of matches) {
    const type = match[1];
    const argString = match[2].trim();
    let args = argString.match(NUMBER_REGEX)?.map(parseFloat) || [];
    
    // 分组参数，因为每个命令可能有多组参数
    const paramCount = PATH_PARAM_COUNTS[type];
    if (paramCount > 0 && args.length > 0) {
      for (let i = 0; i < args.length; i += paramCount) {
        const cmdArgs = args.slice(i, i + paramCount);
        // 如果参数不足，补充前一个命令的最后一组参数
        if (cmdArgs.length < paramCount && lastCommand) {
          const lastArgs = lastCommand.args;
          while (cmdArgs.length < paramCount) {
            cmdArgs.push(lastArgs[cmdArgs.length] || 0);
          }
        }
        
        if (cmdArgs.length === paramCount) {
          const command = {
            type,
            args: cmdArgs
          };
          commands.push(command);
          lastCommand = command;
        }
      }
    } else {
      // 处理不需要参数的命令，如Z
      commands.push({
        type,
        args: []
      });
    }
  }
  
  return commands;
}

/**
 * 解析点列表
 * @param {String} pointsString 点列表字符串
 * @return {Array} 点列表
 */
function parsePoints(pointsString) {
  const numbers = pointsString.match(NUMBER_REGEX)?.map(parseFloat) || [];
  const points = [];
  
  // 每两个数值构成一个点
  for (let i = 0; i < numbers.length; i += 2) {
    if (i + 1 < numbers.length) {
      points.push({ x: numbers[i], y: numbers[i + 1] });
    }
  }
  
  return points;
}

/**
 * 将解析的SVG绘制到Canvas上
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} parsedSVG 解析后的SVG对象
 * @param {Number} scale 缩放比例 (默认为1)
 * @param {Object} offset 偏移量 (默认为 {x: 0, y: 0})
 */
function drawSVGToCanvas(ctx, parsedSVG, scale = 1, offset = { x: 0, y: 0 }) {
  if (!parsedSVG || !parsedSVG.elements) {
    return;
  }
  
  const { viewBox, elements } = parsedSVG;
  const offsetX = offset.x || 0;
  const offsetY = offset.y || 0;
  
  // 计算和应用viewBox变换
  const vbScale = Math.min(
    ctx.canvas.width / viewBox.width,
    ctx.canvas.height / viewBox.height
  );
  
  // 保存当前状态
  ctx.save();
  
  // 应用默认变换
  ctx.translate(offsetX, offsetY);
  ctx.scale(scale, scale);
  
  // 绘制所有元素
  for (const element of elements) {
    drawElement(ctx, element);
  }
  
  // 恢复状态
  ctx.restore();
  
  return {
    viewBoxScale: vbScale,
    width: viewBox.width * scale,
    height: viewBox.height * scale
  };
}

/**
 * 绘制单个SVG元素
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} element 元素对象
 */
function drawElement(ctx, element) {
  if (!element) return;
  
  // 保存当前状态
  ctx.save();
  
  // 应用样式
  applyStyle(ctx, element.style);
  
  // 根据元素类型绘制
  switch (element.type) {
    case 'path':
      drawPath(ctx, element.commands);
      break;
    case 'rect':
      drawRect(ctx, element);
      break;
    case 'circle':
      drawCircle(ctx, element);
      break;
    case 'line':
      drawLine(ctx, element);
      break;
    case 'polyline':
      drawPolyline(ctx, element.points, false);
      break;
    case 'polygon':
      drawPolyline(ctx, element.points, true);
      break;
  }
  
  // 恢复状态
  ctx.restore();
}

/**
 * 应用样式到Canvas上下文
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} style 样式对象
 */
function applyStyle(ctx, style) {
  if (!style) return;
  
  // 填充
  if (style.fill && style.fill !== 'none') {
    ctx.fillStyle = style.fill;
    if (style.fillOpacity !== undefined && style.fillOpacity !== 1) {
      const originalFill = ctx.fillStyle;
      if (typeof originalFill === 'string' && originalFill[0] === '#') {
        // 简单处理16进制颜色
        ctx.fillStyle = convertToRGBA(originalFill, style.fillOpacity);
      }
    }
  } else {
    ctx.fillStyle = 'rgba(0, 0, 0, 0)';
  }
  
  // 描边
  if (style.stroke && style.stroke !== 'none') {
    ctx.strokeStyle = style.stroke;
    if (style.strokeOpacity !== undefined && style.strokeOpacity !== 1) {
      const originalStroke = ctx.strokeStyle;
      if (typeof originalStroke === 'string' && originalStroke[0] === '#') {
        // 简单处理16进制颜色
        ctx.strokeStyle = convertToRGBA(originalStroke, style.strokeOpacity);
      }
    }
    
    ctx.lineWidth = style.strokeWidth || 1;
  } else {
    ctx.strokeStyle = 'rgba(0, 0, 0, 0)';
  }
}

/**
 * 将十六进制颜色转换为RGBA
 * @param {String} hex 十六进制颜色
 * @param {Number} opacity 不透明度
 * @return {String} RGBA颜色字符串
 */
function convertToRGBA(hex, opacity) {
  let r = 0, g = 0, b = 0;
  
  // 移除 # 前缀
  if (hex.startsWith('#')) {
    hex = hex.substring(1);
  }
  
  // 处理3位十六进制
  if (hex.length === 3) {
    r = parseInt(hex[0] + hex[0], 16);
    g = parseInt(hex[1] + hex[1], 16);
    b = parseInt(hex[2] + hex[2], 16);
  } 
  // 处理6位十六进制
  else if (hex.length === 6) {
    r = parseInt(hex.substring(0, 2), 16);
    g = parseInt(hex.substring(2, 4), 16);
    b = parseInt(hex.substring(4, 6), 16);
  }
  
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

/**
 * 绘制路径
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Array} commands 路径命令列表
 */
function drawPath(ctx, commands) {
  if (!commands || commands.length === 0) return;
  
  ctx.beginPath();
  
  let currentX = 0;
  let currentY = 0;
  let startX = 0;
  let startY = 0;
  
  for (const cmd of commands) {
    const { type, args } = cmd;
    
    switch (type) {
      case 'M': // 绝对移动
        currentX = args[0];
        currentY = args[1];
        startX = currentX;
        startY = currentY;
        ctx.moveTo(currentX, currentY);
        break;
      case 'm': // 相对移动
        currentX += args[0];
        currentY += args[1];
        startX = currentX;
        startY = currentY;
        ctx.moveTo(currentX, currentY);
        break;
      case 'L': // 绝对直线
        currentX = args[0];
        currentY = args[1];
        ctx.lineTo(currentX, currentY);
        break;
      case 'l': // 相对直线
        currentX += args[0];
        currentY += args[1];
        ctx.lineTo(currentX, currentY);
        break;
      case 'H': // 绝对水平线
        currentX = args[0];
        ctx.lineTo(currentX, currentY);
        break;
      case 'h': // 相对水平线
        currentX += args[0];
        ctx.lineTo(currentX, currentY);
        break;
      case 'V': // 绝对垂直线
        currentY = args[0];
        ctx.lineTo(currentX, currentY);
        break;
      case 'v': // 相对垂直线
        currentY += args[0];
        ctx.lineTo(currentX, currentY);
        break;
      case 'Z':
      case 'z': // 闭合路径
        ctx.closePath();
        currentX = startX;
        currentY = startY;
        break;
      case 'C': // 绝对三次贝塞尔曲线
        ctx.bezierCurveTo(args[0], args[1], args[2], args[3], args[4], args[5]);
        currentX = args[4];
        currentY = args[5];
        break;
      case 'c': // 相对三次贝塞尔曲线
        ctx.bezierCurveTo(
          currentX + args[0], currentY + args[1],
          currentX + args[2], currentY + args[3],
          currentX + args[4], currentY + args[5]
        );
        currentX += args[4];
        currentY += args[5];
        break;
      case 'Q': // 绝对二次贝塞尔曲线
        ctx.quadraticCurveTo(args[0], args[1], args[2], args[3]);
        currentX = args[2];
        currentY = args[3];
        break;
      case 'q': // 相对二次贝塞尔曲线
        ctx.quadraticCurveTo(
          currentX + args[0], currentY + args[1],
          currentX + args[2], currentY + args[3]
        );
        currentX += args[2];
        currentY += args[3];
        break;
      // 注：这个简单实现省略了一些更复杂的命令，如S, s, T, t, A, a
    }
  }
  
  // 填充和描边
  if (ctx.fillStyle && ctx.fillStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.fill();
  }
  if (ctx.strokeStyle && ctx.strokeStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.stroke();
  }
}

/**
 * 绘制矩形
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} element 矩形元素
 */
function drawRect(ctx, element) {
  const { x, y, width, height, rx, ry } = element;
  
  if (width <= 0 || height <= 0) return;
  
  ctx.beginPath();
  
  // 绘制圆角矩形
  if (rx > 0 || ry > 0) {
    const actualRx = Math.min(rx, width / 2);
    const actualRy = Math.min(ry || rx, height / 2);
    
    ctx.moveTo(x + actualRx, y);
    ctx.lineTo(x + width - actualRx, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + actualRy);
    ctx.lineTo(x + width, y + height - actualRy);
    ctx.quadraticCurveTo(x + width, y + height, x + width - actualRx, y + height);
    ctx.lineTo(x + actualRx, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - actualRy);
    ctx.lineTo(x, y + actualRy);
    ctx.quadraticCurveTo(x, y, x + actualRx, y);
    ctx.closePath();
  } else {
    // 普通矩形
    ctx.rect(x, y, width, height);
  }
  
  // 填充和描边
  if (ctx.fillStyle && ctx.fillStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.fill();
  }
  if (ctx.strokeStyle && ctx.strokeStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.stroke();
  }
}

/**
 * 绘制圆形
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} element 圆形元素
 */
function drawCircle(ctx, element) {
  const { cx, cy, r } = element;
  
  if (r <= 0) return;
  
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  
  // 填充和描边
  if (ctx.fillStyle && ctx.fillStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.fill();
  }
  if (ctx.strokeStyle && ctx.strokeStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.stroke();
  }
}

/**
 * 绘制直线
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Object} element 直线元素
 */
function drawLine(ctx, element) {
  const { x1, y1, x2, y2 } = element;
  
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  
  // 直线只需描边
  if (ctx.strokeStyle && ctx.strokeStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.stroke();
  }
}

/**
 * 绘制折线或多边形
 * @param {CanvasRenderingContext2D} ctx Canvas上下文
 * @param {Array} points 点列表
 * @param {Boolean} closed 是否闭合路径 (polygon)
 */
function drawPolyline(ctx, points, closed) {
  if (!points || points.length === 0) return;
  
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y);
  }
  
  if (closed) {
    ctx.closePath();
  }
  
  // 填充和描边
  if (closed && ctx.fillStyle && ctx.fillStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.fill();
  }
  if (ctx.strokeStyle && ctx.strokeStyle !== 'rgba(0, 0, 0, 0)') {
    ctx.stroke();
  }
}

module.exports = {
  parseSVG,
  drawSVGToCanvas
}; 
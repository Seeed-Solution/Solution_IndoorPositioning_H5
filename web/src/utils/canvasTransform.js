// 室内 canvas 的坐标变换与命中检测。
//
// 绘制、命中和 focus 必须共用同一组正反变换，否则加了 zoom/pan 之后
// "画在哪里" 和 "点中什么" 会分家。变换在这里是纯数据，MapPreview 只负责
// 把它喂给 ctx 和指针事件。
//
// 约定的变换（世界米制 -> canvas backing 像素）：
//     cx = ox + k * x
//     cy = oy - k * y        // Y 轴向上，与 affine.js 的米制坐标一致
// 逆变换：
//     x = (cx - ox) / k
//     y = (oy - cy) / k

export const MIN_ZOOM = 0.5;
export const MAX_ZOOM = 8;

/** 视图叠加层：缺省为「贴合画布」。 */
export const IDENTITY_VIEW = Object.freeze({ zoom: 1, panX: 0, panY: 0 });

const finite = (v, fallback = 0) => (Number.isFinite(Number(v)) ? Number(v) : fallback);

export function clampZoom(z, min = MIN_ZOOM, max = MAX_ZOOM) {
  const v = finite(z, 1);
  return Math.min(max, Math.max(min, v));
}

/**
 * 贴合变换：把 [minX,maxX] x [minY,maxY] 的数据框放进画布，保持宽高比。
 *
 * `imageAspect` 是背景图的原始宽高比。有背景图时，图的高度占满渲染高度、
 * 宽度按原始比例算并水平居中；矢量内容必须对齐到图上，所以原点跟着图走。
 *
 * @returns {{k: number, ox: number, oy: number, scale: number,
 *            originX: number, originY: number}}
 */
export function fitTransform({
  minX = 0, minY = 0, maxX = 1, maxY = 1,
  canvasWidth = 1, canvasHeight = 1,
  padding = 0.9,
  imageAspect = null,
} = {}) {
  const w = Math.max(finite(canvasWidth, 1), 1);
  const h = Math.max(finite(canvasHeight, 1), 1);
  const dataWidth = finite(maxX) - finite(minX);
  const dataHeight = finite(maxY) - finite(minY);

  let scale;
  if (dataWidth <= 0 || dataHeight <= 0) {
    scale = 1;
  } else {
    scale = Math.min((w * padding) / dataWidth, (h * padding) / dataHeight);
  }
  if (!(scale > 0)) scale = 1;

  const renderedWidth = dataWidth * scale;
  const renderedHeight = dataHeight * scale;

  let originX = (w - renderedWidth) / 2;
  const originY = (h - renderedHeight) / 2;
  if (Number.isFinite(imageAspect) && imageAspect > 0) {
    originX = (w - renderedHeight * imageAspect) / 2;
  }

  return {
    k: scale,
    ox: originX - finite(minX) * scale,
    oy: h - originY + finite(minY) * scale,
    scale,
    originX,
    originY,
  };
}

/** 把 {zoom, panX, panY} 叠到贴合变换上，得到实际绘制/命中用的变换。 */
export function applyView(base, view = IDENTITY_VIEW) {
  const z = clampZoom(view?.zoom ?? 1);
  const panX = finite(view?.panX, 0);
  const panY = finite(view?.panY, 0);
  return {
    k: base.k * z,
    ox: base.ox * z + panX,
    oy: base.oy * z + panY,
  };
}

export function worldToCanvas(t, x, y) {
  return { x: t.ox + t.k * finite(x), y: t.oy - t.k * finite(y) };
}

export function canvasToWorld(t, cx, cy) {
  return { x: (finite(cx) - t.ox) / t.k, y: (t.oy - finite(cy)) / t.k };
}

/**
 * CSS 像素 -> canvas backing 像素。
 *
 * canvas 的样式是 `max-width:100%; height:auto`，显示尺寸和 backing 尺寸
 * 经常不等；不换算的话点击会整体偏移。
 */
export function cssToCanvasPoint(rect, canvasWidth, canvasHeight, clientX, clientY) {
  const rw = Math.max(finite(rect?.width, 1), 1e-6);
  const rh = Math.max(finite(rect?.height, 1), 1e-6);
  return {
    x: (finite(clientX) - finite(rect?.left)) * (canvasWidth / rw),
    y: (finite(clientY) - finite(rect?.top)) * (canvasHeight / rh),
  };
}

/** CSS 半径 -> backing 半径，用同一套比例（取两轴较大者，宁可略松不漏点）。 */
export function cssRadiusToCanvas(rect, canvasWidth, canvasHeight, radiusCss) {
  const rw = Math.max(finite(rect?.width, 1), 1e-6);
  const rh = Math.max(finite(rect?.height, 1), 1e-6);
  return finite(radiusCss) * Math.max(canvasWidth / rw, canvasHeight / rh);
}

/**
 * 以 anchor（canvas backing 像素）为不动点缩放。
 * 只依赖 view，不依赖贴合变换：贴合变换随窗口变，缩放意图不该跟着变。
 */
export function zoomAt(view, anchor, factor, { min = MIN_ZOOM, max = MAX_ZOOM } = {}) {
  const z = clampZoom(view?.zoom ?? 1, min, max);
  const panX = finite(view?.panX, 0);
  const panY = finite(view?.panY, 0);
  const nz = clampZoom(z * finite(factor, 1), min, max);
  if (nz === z) return { zoom: z, panX, panY };
  const ax = finite(anchor?.x);
  const ay = finite(anchor?.y);
  return {
    zoom: nz,
    panX: ax - (nz / z) * (ax - panX),
    panY: ay - (nz / z) * (ay - panY),
  };
}

export function panBy(view, dx, dy) {
  return {
    zoom: clampZoom(view?.zoom ?? 1),
    panX: finite(view?.panX, 0) + finite(dx),
    panY: finite(view?.panY, 0) + finite(dy),
  };
}

export function resetView() {
  return { ...IDENTITY_VIEW };
}

/**
 * 命中检测：在 tolerance 内取最近的目标，距离相同按 id 升序。
 *
 * 每个候选自带 hitRadius（精确点是描点半径；区域定位圆只把圆心附近算作
 * 目标，不用整个半径，否则一个大圆会盖住整张图）。
 *
 * @param {Array<{id: string, x: number, y: number, hitRadius?: number}>} targets
 * @param {{x: number, y: number}} point  canvas backing 像素
 * @param {number} tolerance              canvas backing 像素
 * @returns {string|null}
 */
export function hitTest(targets, point, tolerance = 12) {
  if (!Array.isArray(targets) || targets.length === 0) return null;
  const px = finite(point?.x);
  const py = finite(point?.y);
  let best = null;
  let bestDist = Infinity;
  targets.forEach((target) => {
    if (!target || target.id === undefined || target.id === null) return;
    const dx = finite(target.x) - px;
    const dy = finite(target.y) - py;
    const dist = Math.hypot(dx, dy);
    const limit = Math.max(finite(tolerance), finite(target.hitRadius));
    if (dist > limit) return;
    if (dist < bestDist - 1e-9
      || (Math.abs(dist - bestDist) <= 1e-9 && best !== null && String(target.id) < String(best))) {
      best = String(target.id);
      bestDist = dist;
    }
  });
  return best;
}

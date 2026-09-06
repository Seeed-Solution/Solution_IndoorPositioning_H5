// 展示模式的相机：把当前图层的全部 tracker 一并框进画面（spec §9.3 fit-all）。
//
// 纯数据，不碰 DOM，也不碰 canvasTransform 里绘制/命中那套变换的语义：
// 这里只产出一个 {zoom, panX, panY} 的视图叠加层，交给 MapPreview 去用。
//
// 坐标约定：入参的点是「贴合变换之后、视图叠加之前」的 canvas backing 像素
// （即 view = identity 时点会落在哪）。applyView 是线性的：
//     p_view = zoom * p_base + pan
// 所以已经带着当前 view 的点可以用 toBasePoint 反解回去，不需要知道贴合变换。

import { clampZoom, MAX_ZOOM, MIN_ZOOM } from '@/utils/canvasTransform.js';

const finite = (v, fallback = 0) => (Number.isFinite(Number(v)) ? Number(v) : fallback);

/** 带着当前 view 的点 -> base 点。 */
export function toBasePoint(point, view) {
  const z = clampZoom(view?.zoom ?? 1);
  return {
    x: (finite(point?.x) - finite(view?.panX)) / z,
    y: (finite(point?.y) - finite(view?.panY)) / z,
  };
}

/** 点集外接框；空集或全是脏数据返回 null。 */
export function boundsOf(points) {
  if (!Array.isArray(points) || points.length === 0) return null;
  let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
  let count = 0;
  points.forEach((p) => {
    const x = Number(p?.x);
    const y = Number(p?.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    count += 1;
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  });
  if (count === 0) return null;
  return {
    minX, minY, maxX, maxY,
    width: maxX - minX,
    height: maxY - minY,
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
    count,
  };
}

/**
 * fit-all：把点集外接框放进 viewWidth x viewHeight，两侧各留 paddingRatio 的边距。
 *
 * 单点（外接框退化成 0 宽 0 高）不放大，只把它挪到画面中心：一台 tracker 时
 * 无限放大既没有意义，也会把背景图糊掉。
 *
 * @returns {{zoom:number, panX:number, panY:number}|null}
 */
export function fitAllView({
  points,
  viewWidth,
  viewHeight,
  paddingRatio = 0.08,
  minZoom = MIN_ZOOM,
  maxZoom = MAX_ZOOM,
} = {}) {
  const w = Math.max(finite(viewWidth, 0), 0);
  const h = Math.max(finite(viewHeight, 0), 0);
  if (w <= 0 || h <= 0) return null;
  const b = boundsOf(points);
  if (!b) return null;

  const pad = Math.min(Math.max(finite(paddingRatio, 0), 0), 0.45);
  const usableW = w * (1 - 2 * pad);
  const usableH = h * (1 - 2 * pad);

  let zoom = 1;
  if (b.width > 0 || b.height > 0) {
    const zx = b.width > 0 ? usableW / b.width : Infinity;
    const zy = b.height > 0 ? usableH / b.height : Infinity;
    zoom = Math.min(zx, zy);
  }
  zoom = clampZoom(zoom, minZoom, maxZoom);

  return {
    zoom,
    panX: w / 2 - zoom * b.centerX,
    panY: h / 2 - zoom * b.centerY,
  };
}

/**
 * 取景目标的退化顺序（spec §9.3）：在线 tracker 为空退化到全部 beacon 的
 * 外接框，beacon 也为空再退化到平面图外框——这样 0 tracker 时展示页不会
 * 停在默认视图（beacon 全挤在角落），至少能看到有意义的取景范围。
 */
export const FIT_SOURCE_TRACKERS = 'trackers';
export const FIT_SOURCE_BEACONS = 'beacons';
export const FIT_SOURCE_PLAN = 'plan';

/**
 * 按退化顺序挑一组能算出外接框的候选点集。
 *
 * 三组入参都是同一坐标约定下的点数组（跟 fitAllView 的 points 一样：
 * 「贴合变换之后、视图叠加之前」的 base 点）。调用方各自把 tracker /
 * beacon / 平面图角点换算成这个坐标系, 这里只管挑, 不碰坐标变换。
 *
 * @returns {{source: 'trackers'|'beacons'|'plan'|null, points: Array|null, bounds: object|null}}
 */
export function resolveFitTargets({ trackers = [], beacons = [], plan = [] } = {}) {
  const candidates = [
    [FIT_SOURCE_TRACKERS, trackers],
    [FIT_SOURCE_BEACONS, beacons],
    [FIT_SOURCE_PLAN, plan],
  ];
  for (let i = 0; i < candidates.length; i += 1) {
    const [source, points] = candidates[i];
    const bounds = boundsOf(points);
    if (bounds) return { source, points, bounds };
  }
  return { source: null, points: null, bounds: null };
}

/**
 * fit-all 的完整入口：先按 resolveFitTargets 退化, 再喂给 fitAllView。
 * 三组都为空（没有 tracker、没有 beacon、平面图也没有外框点）时返回
 * source: null, view: null——调用方保持当前视图不动。
 */
export function fitAllViewWithFallback({
  trackers = [],
  beacons = [],
  plan = [],
  ...fitOptions
} = {}) {
  const resolved = resolveFitTargets({ trackers, beacons, plan });
  if (!resolved.points) return { view: null, source: null };
  return { view: fitAllView({ ...fitOptions, points: resolved.points }), source: resolved.source };
}

/**
 * 抖动阈值：新旧相机差得够多才真的动。
 *
 * tracker 位置每秒都在小幅跳，不设阈值的话画面会一直微微平移。
 * 缩放按相对变化算，平移按视口短边比例算，任一超过 jitterRatio 就重定位。
 */
export function viewChangedEnough(prev, next, {
  viewWidth = 0, viewHeight = 0, jitterRatio = 0.05,
} = {}) {
  if (!next) return false;
  if (!prev) return true;
  const ratio = Math.max(finite(jitterRatio, 0), 0);
  if (ratio === 0) return true;

  const pz = clampZoom(prev.zoom ?? 1);
  const nz = clampZoom(next.zoom ?? 1);
  if (Math.abs(nz - pz) / Math.max(pz, 1e-6) > ratio) return true;

  const span = Math.max(Math.min(finite(viewWidth, 0), finite(viewHeight, 0)), 1);
  const dx = Math.abs(finite(next.panX) - finite(prev.panX));
  const dy = Math.abs(finite(next.panY) - finite(prev.panY));
  return Math.max(dx, dy) / span > ratio;
}

/**
 * fit-all 的防抖调度器：tracker 集合/位置变化只登记一次意图，
 * 安静 delayMs 之后才真的重算相机（spec §9.3 防抖 2 s）。
 *
 * 定时器可注入，单测用 vi.useFakeTimers 直接推进。
 */
export function createFitScheduler({
  delayMs = 2000,
  onFit,
  // 同 idleReturn.js: 直接透传 window.setTimeout 会因为 this 不对而抛
  timers = {
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    clearTimeout: (h) => clearTimeout(h),
  },
} = {}) {
  let handle = null;

  const cancel = () => {
    if (handle !== null) {
      timers.clearTimeout(handle);
      handle = null;
    }
  };

  const run = () => {
    handle = null;
    if (typeof onFit === 'function') onFit();
  };

  return {
    /** 登记一次重算意图；delayMs 内的重复调用合并成一次。 */
    schedule() {
      if (handle !== null) return false;
      handle = timers.setTimeout(run, Math.max(finite(delayMs, 0), 0));
      return true;
    },
    /** 立刻执行并清掉待执行的定时器（进入展示模式、换图层时用）。 */
    flush() {
      cancel();
      run();
    },
    cancel,
    get pending() {
      return handle !== null;
    },
  };
}

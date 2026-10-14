// OutdoorMapView 的渲染计划: 把 tracker 的历史轨迹拆成 Leaflet 折线数组。
//
// 这两个函数只看 position_history 里每个点自己的 coordSystem, 与 tracker
// "当前"是室内还是室外无关 —— 修复 bug: 之前 redraw() 按 isOutdoorTracker(tracker)
// (当前状态) 把 tracker 分进两个互斥 forEach, 导致当前室外的设备不画它历史的
// 室内段 (反之亦然)。现在两类历史段总是都算, 只有"当前点" marker 的样式才按
// isOutdoorTracker 二选一。
import { indoorSegments, outdoorSegments } from './trail.js';

/**
 * metric 历史段投影到 [lat, lon], 按配准存在与否 / 换地图切段。
 * @param {object} tracker
 * @param {(x:number, y:number, map:string) => [number, number]|null} projectMetric
 *   局部米制坐标 -> [lat, lon], 地图未配准或坐标非法时返回 null。
 * @returns {Array<Array<[number, number]>>} 每条折线至少 2 个点。
 */
export function buildIndoorPolylines(tracker, projectMetric) {
  const polylines = [];
  indoorSegments(tracker?.position_history).forEach((segment) => {
    // 同一段里换地图也要断开: 两张平面图各有自己的配准。
    let run = [];
    let runMap = null;
    const flush = () => {
      if (run.length >= 2) polylines.push(run);
      run = [];
    };
    segment.points.forEach((p) => {
      if (p.map !== runMap) {
        flush();
        runMap = p.map;
      }
      const projected = projectMetric(p.x, p.y, p.map);
      if (!projected) {
        flush();
        return;
      }
      run.push(projected);
    });
    flush();
  });
  return polylines;
}

/**
 * wgs84 历史段直接取 [lat, lon], 不做任何投影。
 * @param {object} tracker
 * @returns {Array<Array<[number, number]>>} 每条折线至少 2 个点。
 */
export function buildOutdoorPolylines(tracker) {
  const polylines = [];
  outdoorSegments(tracker?.position_history).forEach((segment) => {
    if (segment.points.length < 2) return;
    polylines.push(segment.points.map((p) => [p.lat, p.lon]));
  });
  return polylines;
}

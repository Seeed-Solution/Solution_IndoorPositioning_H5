// 回归测试: OutdoorMapView.redraw() 之前按 tracker "当前" isOutdoorTracker
// 状态把 tracker 分进两个互斥 forEach, 导致当前室外的设备不画它历史的室内段
// (反之亦然)。buildIndoorPolylines / buildOutdoorPolylines 必须无条件地
// 从同一条 position_history 里各自算出自己的折线, 与 tracker 当前状态无关。
import { describe, it, expect } from 'vitest';
import { buildIndoorPolylines, buildOutdoorPolylines } from '../src/utils/renderPlan.js';
import { COORD_METRIC, COORD_WGS84 } from '../src/utils/trail.js';

// metric -> wgs84 -> metric: 一条设备先在室内, 走出楼门变室外, 又走回室内。
const mixedHistory = [
  { coordSystem: COORD_METRIC, time: 1, x: 0, y: 0, map: 'Floor 1' },
  { coordSystem: COORD_METRIC, time: 2, x: 10, y: 5, map: 'Floor 1' },
  { coordSystem: COORD_WGS84, time: 3, lat: 22.5240, lon: 113.9320 },
  { coordSystem: COORD_WGS84, time: 4, lat: 22.5245, lon: 113.9325 },
  { coordSystem: COORD_METRIC, time: 5, x: 20, y: 8, map: 'Floor 1' },
  { coordSystem: COORD_METRIC, time: 6, x: 22, y: 9, map: 'Floor 1' },
];

// 简单的假投影: 配准好的地图把 (x, y) 映射成一个可辨识的 [lat, lon]。
const fakeProjectMetric = (x, y, mapName) => {
  if (mapName !== 'Floor 1') return null;
  return [22.52 + Number(y) * 1e-5, 113.93 + Number(x) * 1e-5];
};

describe('renderPlan (redraw 层面的纯函数, 不依赖 Leaflet/DOM)', () => {
  it('produces both indoor and outdoor polylines from one mixed-history tracker, '
    + 'regardless of the tracker current position type', () => {
    // 当前点是 metric (室内), 但历史里同时含 wgs84 段。
    const trackerCurrentlyIndoor = { position_history: mixedHistory, x: 22, y: 9, map: 'Floor 1' };
    const indoor = buildIndoorPolylines(trackerCurrentlyIndoor, fakeProjectMetric);
    const outdoor = buildOutdoorPolylines(trackerCurrentlyIndoor);

    // 两段 metric run (各 2 点) + 一段 wgs84 run (2 点)。
    expect(indoor).toHaveLength(2);
    indoor.forEach((run) => expect(run.length).toBeGreaterThanOrEqual(2));
    expect(outdoor).toHaveLength(1);
    expect(outdoor[0]).toEqual([[22.524, 113.932], [22.5245, 113.9325]]);

    // 修复前的 bug: 当前是室外时, 室内段(indoor)会被整体跳过, 变成 0 条。
    // 这里显式验证"当前状态"不影响 buildIndoorPolylines/buildOutdoorPolylines
    // 的结果 —— 换一个"当前是 wgs84"的 tracker, 同一份 position_history
    // 产出的折线集合必须完全一样。
    const trackerCurrentlyOutdoor = { position_history: mixedHistory, lat: 22.5245, lon: 113.9325 };
    const indoorWhenOutdoorCurrent = buildIndoorPolylines(trackerCurrentlyOutdoor, fakeProjectMetric);
    const outdoorWhenOutdoorCurrent = buildOutdoorPolylines(trackerCurrentlyOutdoor);
    expect(indoorWhenOutdoorCurrent).toEqual(indoor);
    expect(outdoorWhenOutdoorCurrent).toEqual(outdoor);
  });

  it('drops metric points on an unregistered map without breaking the rest of the segment', () => {
    const history = [
      { coordSystem: COORD_METRIC, time: 1, x: 0, y: 0, map: 'Unregistered' },
      { coordSystem: COORD_METRIC, time: 2, x: 1, y: 1, map: 'Floor 1' },
      { coordSystem: COORD_METRIC, time: 3, x: 2, y: 2, map: 'Floor 1' },
    ];
    const polylines = buildIndoorPolylines({ position_history: history }, fakeProjectMetric);
    // 未配准的地图那一点投影失败(单点无法成线), 剩下 Floor 1 的两点成一条线。
    expect(polylines).toHaveLength(1);
    expect(polylines[0]).toHaveLength(2);
  });

  it('drops single-point outdoor segments (need >= 2 points to draw a line)', () => {
    const history = [
      { coordSystem: COORD_WGS84, time: 1, lat: 22.52, lon: 113.93 },
      { coordSystem: COORD_METRIC, time: 2, x: 0, y: 0, map: 'Floor 1' },
      { coordSystem: COORD_WGS84, time: 3, lat: 22.521, lon: 113.931 },
    ];
    const polylines = buildOutdoorPolylines({ position_history: history });
    expect(polylines).toHaveLength(0);
  });
});

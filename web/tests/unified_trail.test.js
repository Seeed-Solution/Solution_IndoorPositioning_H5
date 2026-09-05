// 统一渲染: metric 段按配准投影到 Leaflet 图，与 wgs84 段跨段不连线。
import { describe, it, expect } from 'vitest';
import { segmentTrail, indoorSegments, outdoorSegments, COORD_METRIC, COORD_WGS84 }
  from '../src/utils/trail.js';
import { localToWgs84, isRegistered } from '../src/utils/affine.js';

const REG = { origin_lat: 22.5231, origin_lon: 113.9312, rotation_deg: 12.0, scale: 1.0 };

const history = [
  { coordSystem: COORD_METRIC, time: 1, x: 0, y: 0, map: 'Floor 1' },
  { coordSystem: COORD_METRIC, time: 2, x: 10, y: 5, map: 'Floor 1' },
  { coordSystem: COORD_WGS84, time: 3, lat: 22.5240, lon: 113.9320 },
  { coordSystem: COORD_WGS84, time: 4, lat: 22.5245, lon: 113.9325 },
  { coordSystem: COORD_METRIC, time: 5, x: 20, y: 8, map: 'Floor 2' },
  { coordSystem: COORD_METRIC, time: 6, x: 22, y: 9, map: 'Floor 2' },
];

describe('mixed indoor/outdoor trail', () => {
  it('splits into three segments at each coordinate-system change', () => {
    const segs = segmentTrail(history);
    expect(segs.map((s) => s.coordSystem))
      .toEqual([COORD_METRIC, COORD_WGS84, COORD_METRIC]);
    // 切换点分属两段: 没有一段同时含 metric 与 wgs84 点。
    segs.forEach((s) => {
      const kinds = new Set(s.points.map((p) => p.coordSystem));
      expect(kinds.size).toBe(1);
    });
  });

  it('projects metric segments onto WGS84 with the map registration', () => {
    const segs = indoorSegments(history);
    expect(segs).toHaveLength(2);
    const projected = segs.map((s) => s.points.map((p) => localToWgs84(p.x, p.y, REG)));
    projected.flat().forEach((p) => {
      expect(Number.isFinite(p.lat)).toBe(true);
      expect(Number.isFinite(p.lon)).toBe(true);
    });
    // 原点投到配准原点上。
    expect(projected[0][0].lat).toBeCloseTo(REG.origin_lat, 12);
    expect(projected[0][0].lon).toBeCloseTo(REG.origin_lon, 12);
  });

  it('outdoor segments stay untouched', () => {
    const segs = outdoorSegments(history);
    expect(segs).toHaveLength(1);
    expect(segs[0].points.map((p) => p.lat)).toEqual([22.524, 22.5245]);
  });

  it('an unregistered map contributes nothing', () => {
    expect(isRegistered({ name: 'Floor 3', width: 10, height: 10 })).toBe(false);
  });
});

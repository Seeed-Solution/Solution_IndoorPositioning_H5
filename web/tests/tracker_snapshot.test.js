// 室外总览页刷新后丢轨迹的回归: initial_state/REST 快照 -> tracker map 的
// 归一化必须保留 position_history、type、lat/lon, 否则 renderPlan.js 拿不到
// 历史段, 折线在刷新后就是 0 条。
import { describe, it, expect } from 'vitest';
import { buildTrackerMapFromSnapshot, normalizeTrackerSnapshotEntry }
  from '../src/utils/trackerSnapshot.js';

describe('buildTrackerMapFromSnapshot', () => {
  it('normalizes a REST/initial_state snapshot into the tracker_update shape', () => {
    const snapshot = {
      DEV001: {
        trackerId: 'DEV001',
        device_name: 'Tag 1',
        lat: 22.5231,
        lon: 113.9312,
        alt: 10,
        accuracy: 5,
        type: 'wGS84',
        map: 'outdoor',
        sos: 2,
        timestamp: 1000,
        position_history: [
          { coordSystem: 'wgs84', time: 900, lat: 22.5230, lon: 113.9310 },
          { coordSystem: 'wgs84', time: 1000, lat: 22.5231, lon: 113.9312 },
        ],
      },
      DEV002: {
        trackerId: 'DEV002',
        device_name: 'Tag 2',
        x: 3,
        y: 4,
        map: 'Floor 1',
        type: 'calculation',
        position_history: [],
      },
    };

    const trackers = buildTrackerMapFromSnapshot(snapshot);

    expect(Object.keys(trackers)).toEqual(['DEV001', 'DEV002']);
    expect(trackers.DEV001).toMatchObject({
      trackerId: 'DEV001',
      lat: 22.5231,
      lon: 113.9312,
      type: 'wGS84',
    });
    expect(trackers.DEV001.position_history).toHaveLength(2);
    expect(trackers.DEV002).toMatchObject({ x: 3, y: 4, type: 'calculation' });
  });

  it('falls back to nested position.{x,y,lat,lon} and defaults type/sos/position_history', () => {
    const entry = normalizeTrackerSnapshotEntry({
      trackerId: 'DEV003',
      position: { x: 1, y: 2, lat: 22.1, lon: 113.1 },
    });

    expect(entry).toMatchObject({
      trackerId: 'DEV003',
      x: 1,
      y: 2,
      lat: 22.1,
      lon: 113.1,
      type: 'calculation',
      sos: 2,
    });
    expect(entry.position_history).toEqual([]);
  });

  it('returns an empty map for an empty snapshot', () => {
    expect(buildTrackerMapFromSnapshot({})).toEqual({});
    expect(buildTrackerMapFromSnapshot(undefined)).toEqual({});
  });
});

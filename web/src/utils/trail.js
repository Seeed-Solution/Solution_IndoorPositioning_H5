// 统一时间轴: 把一条 position_history 按时间排序, 再按坐标系切段.
// 室内段 (metric) 交给 Canvas 的 MapPreview, 室外段 (wgs84) 交给 Leaflet 的
// OutdoorMapView. 切换点分属两段, 因此不会被连成一条线.

export const COORD_METRIC = 'metric';
export const COORD_WGS84 = 'wgs84';

/**
 * 兼容旧的 [x, y, timestamp] 三元组与新的对象条目。
 * @returns {{coordSystem: string, time: number, x?: number, y?: number,
 *            lat?: number, lon?: number, alt?: number, accuracy?: number,
 *            map?: string}|null}
 */
export function normalizeHistoryEntry(entry) {
  if (!entry) return null;
  if (Array.isArray(entry)) {
    if (entry.length < 3) return null;
    return {
      coordSystem: COORD_METRIC,
      x: Number(entry[0]),
      y: Number(entry[1]),
      time: Number(entry[2]),
    };
  }
  if (typeof entry !== 'object') return null;
  const coordSystem = entry.coordSystem
    || (entry.lat !== undefined && entry.lat !== null ? COORD_WGS84 : COORD_METRIC);
  return {
    coordSystem,
    time: Number(entry.time ?? entry.timestamp ?? 0),
    x: entry.x ?? null,
    y: entry.y ?? null,
    lat: entry.lat ?? null,
    lon: entry.lon ?? null,
    alt: entry.alt ?? null,
    accuracy: entry.accuracy ?? null,
    map: entry.map ?? null,
  };
}

export function normalizeHistory(history) {
  if (!Array.isArray(history)) return [];
  return history
    .map(normalizeHistoryEntry)
    .filter(Boolean)
    .filter((e) => (e.coordSystem === COORD_WGS84
      ? e.lat !== null && e.lon !== null
      : e.x !== null && e.y !== null))
    .sort((a, b) => a.time - b.time);
}

/**
 * 切段: 相邻条目坐标系不同就断开。
 * @returns {Array<{coordSystem: string, points: Array<object>}>}
 */
export function segmentTrail(history) {
  const entries = normalizeHistory(history);
  const segments = [];
  let current = null;
  entries.forEach((entry) => {
    if (!current || current.coordSystem !== entry.coordSystem) {
      current = { coordSystem: entry.coordSystem, points: [] };
      segments.push(current);
    }
    current.points.push(entry);
  });
  return segments;
}

export function indoorSegments(history) {
  return segmentTrail(history).filter((s) => s.coordSystem === COORD_METRIC);
}

export function outdoorSegments(history) {
  return segmentTrail(history).filter((s) => s.coordSystem === COORD_WGS84);
}

/** tracker.type === 'wGS84' 走室外视图, 其余走室内。 */
export const TRACKER_TYPE_WGS84 = 'wGS84';

export function isOutdoorTracker(tracker) {
  if (!tracker) return false;
  if (tracker.type === TRACKER_TYPE_WGS84) return true;
  return tracker.lat !== undefined && tracker.lat !== null
    && tracker.lon !== undefined && tracker.lon !== null;
}

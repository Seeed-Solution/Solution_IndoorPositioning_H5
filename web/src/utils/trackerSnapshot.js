// 把 tracker 快照 (WS initial_state 载荷, 或 REST /api/trackers 的返回) 归一化成
// OutdoorMapOverview / MapOverview 渲染需要的 tracker map: 字段形状与 WS
// tracker_update 增量更新后的 tracker 对象一致 (x/y/lat/lon 都是顶层字段,
// position_history 保留原样交给 renderPlan.js 按 coordSystem 切段)。
//
// 之前 OutdoorMapOverview.vue 只在 WS 连接建立后靠 tracker_update 增量填充
// allTrackers, 服务端从不在连接时真正广播 initial_state (server/main.py 的
// websocket_endpoint 里没有这个分支), 所以页面一刷新轨迹就清零, 要等下一条
// 上行才重新出现。真正能在刷新后立刻拿到当前状态的是 REST `/api/trackers`
// (server/main.py `get_trackers`, 经 TrackerInfo 返回 lat/lon/type/position_history),
// 用本模块的 buildTrackerMapFromSnapshot 归一化后作为初始快照, 之后再用
// tracker_update 增量更新。

/** 单个 tracker 快照条目 -> 渲染所需的扁平字段。 */
export function normalizeTrackerSnapshotEntry(d) {
  if (!d) return null;
  return {
    trackerId: d.trackerId,
    device_name: d.device_name,
    x: d.x ?? d.position?.x ?? null,
    y: d.y ?? d.position?.y ?? null,
    lat: d.lat ?? d.position?.lat ?? null,
    lon: d.lon ?? d.position?.lon ?? null,
    alt: d.alt ?? null,
    accuracy: d.accuracy ?? null,
    fix_time: d.fix_time ?? null,
    timestamp: d.timestamp,
    sos: d.sos ?? 2,
    type: d.type || 'calculation',
    map: d.map,
    position_history: d.position_history || [],
  };
}

/**
 * tracker 快照对象 (trackerId -> 原始字段) -> 归一化后的 tracker map。
 * @param {Record<string, object>} snapshot
 * @returns {Record<string, object>}
 */
export function buildTrackerMapFromSnapshot(snapshot) {
  const result = {};
  Object.entries(snapshot || {}).forEach(([trackerId, raw]) => {
    const normalized = normalizeTrackerSnapshotEntry({ trackerId, ...raw });
    if (normalized) result[trackerId] = normalized;
  });
  return result;
}

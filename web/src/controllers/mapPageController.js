// /map 的页面级联动 controller。
//
// 两套地图实现（室内 canvas / 室外 Leaflet）只暴露"把某个 id 居中"和
// "报告某个 id 被点/被悬停"两件事，页面状态、URL、列表滚动都归这里管。
// 不 import vue：controller 是纯 JS，单测可以直接跑。

import { isOutdoorTracker } from '@/utils/trail.js';
import { LAYER_INDOOR, LAYER_OUTDOOR } from '@/utils/mapUrlState.js';

/**
 * @param {object} deps
 * @param {() => object} deps.getTrackers     当前 tracker 映射 {id: tracker}
 * @param {() => object} deps.getState        当前页面状态（parseMapQuery 的产物）
 * @param {(patch: object, opts?: {history?: 'push'|'replace'}) => void} deps.setState
 * @param {() => string} [deps.getHovered]
 * @param {(id: string) => void} [deps.setHovered]
 * @param {{indoor?: (id, tracker) => void, outdoor?: (id, tracker) => void}} [deps.focusHandlers]
 */
export function createMapController({
  getTrackers,
  getState,
  setState,
  getHovered = () => '',
  setHovered = () => {},
  focusHandlers = {},
} = {}) {
  const trackers = () => getTrackers?.() || {};
  const state = () => getState?.() || {};

  const lookup = (id) => {
    if (!id) return null;
    return trackers()[id] || null;
  };

  /** tracker 当下应该落在哪个图层。 */
  const layerOf = (tracker) => (isOutdoorTracker(tracker) ? LAYER_OUTDOOR : LAYER_INDOOR);

  const focusTracker = (id) => {
    const tracker = lookup(id);
    if (!tracker) return false;
    const layer = state().layer === LAYER_OUTDOOR ? LAYER_OUTDOOR : LAYER_INDOOR;
    const handler = focusHandlers[layer];
    if (typeof handler !== 'function') return false;
    handler(id, tracker);
    return true;
  };

  /**
   * 选中一个 tracker：更新 URL、打开详情。
   * 未知 id 直接忽略（轮询把设备刷掉、或者 URL 里带了脏 id）。
   */
  const selectTracker = (id, { focus = true, history = 'push' } = {}) => {
    const tracker = lookup(id);
    if (!tracker) return false;
    const patch = { tracker: String(id), panel: 'detail' };
    // 室内层里选中的设备如果落在别的平面图上，顺手把楼层带过去；
    // 跨图层（室内<->室外）不自动切，交给调用方确认。
    if (state().layer === LAYER_INDOOR && tracker.map && tracker.map !== state().map) {
      if (layerOf(tracker) === LAYER_INDOOR) patch.map = tracker.map;
    }
    setState(patch, { history });
    if (focus) focusTracker(id);
    return true;
  };

  const clearSelection = () => {
    setState({ tracker: '', panel: 'list' }, { history: 'replace' });
  };

  const hoverTracker = (id) => {
    if (!id) {
      setHovered('');
      return true;
    }
    if (!lookup(id)) return false;
    setHovered(String(id));
    return true;
  };

  /**
   * 数据刷新后调用：选中的设备还在就什么都不做（选择必须扛得住 5s 轮询），
   * 没了才清掉选择。悬停同理：设备被刷掉时 marker 直接消失，不会再有
   * mouseout/pointerleave 把 hover 收回来，留着会让下一个同 id 的设备莫名放大。
   */
  const reconcile = () => {
    const hovered = getHovered?.();
    if (hovered && !lookup(hovered)) setHovered('');
    const id = state().tracker;
    if (!id) return;
    if (!lookup(id)) clearSelection();
  };

  /**
   * 选中的设备当前在另一个图层时，返回建议切换的图层，否则返回 null。
   * 只做提示：切不切由用户确认，筛选和 hover 永远不触发换层。
   */
  const suggestLayerFor = (id) => {
    const tracker = lookup(id);
    if (!tracker) return null;
    const want = layerOf(tracker);
    return want === state().layer ? null : want;
  };

  const setLayer = (layer) => {
    const next = layer === LAYER_OUTDOOR ? LAYER_OUTDOOR : LAYER_INDOOR;
    if (next === state().layer) return false;
    // 换层要连 hover 一起收掉: 旧图层的 marker 被整体拆掉, mouseout 不会发出来
    setHovered('');
    setState({ layer: next }, { history: 'push' });
    return true;
  };

  return {
    selectTracker,
    clearSelection,
    focusTracker,
    hoverTracker,
    reconcile,
    suggestLayerFor,
    setLayer,
    layerOf,
    getHovered,
  };
}

// 三档布局的断点判定。
//
//   >=1024  desktop : 列表 / 地图 / 详情 三列
//   768-1023 tablet : 地图主视图，列表与详情共用侧边 drawer
//   <768    mobile  : 地图铺满，列表与详情是底部 drawer，侧栏 off-canvas
//
// 纯函数 + 一个订阅工厂，方便单测；组件只负责把 stop() 挂到 onUnmounted。

export const LAYOUT_DESKTOP = 'desktop';
export const LAYOUT_TABLET = 'tablet';
export const LAYOUT_MOBILE = 'mobile';

export const BREAKPOINT_DESKTOP = 1024;
export const BREAKPOINT_TABLET = 768;

/** 边界值归上一档：1024 是 desktop，768 是 tablet。 */
export function layoutModeForWidth(width) {
  const w = Number(width);
  if (!Number.isFinite(w)) return LAYOUT_DESKTOP;
  if (w >= BREAKPOINT_DESKTOP) return LAYOUT_DESKTOP;
  if (w >= BREAKPOINT_TABLET) return LAYOUT_TABLET;
  return LAYOUT_MOBILE;
}

export const MEDIA_DESKTOP = `(min-width: ${BREAKPOINT_DESKTOP}px)`;
export const MEDIA_TABLET = `(min-width: ${BREAKPOINT_TABLET}px)`;

function currentMode(win) {
  if (typeof win?.matchMedia === 'function') {
    if (win.matchMedia(MEDIA_DESKTOP).matches) return LAYOUT_DESKTOP;
    if (win.matchMedia(MEDIA_TABLET).matches) return LAYOUT_TABLET;
    return LAYOUT_MOBILE;
  }
  return layoutModeForWidth(win?.innerWidth);
}

/**
 * 订阅断点变化。matchMedia 只读一次是拿不到旋屏/拖窗口的，必须挂 change 监听，
 * 并且卸载时把监听摘干净。
 *
 * @param {Window} win
 * @param {(mode: string) => void} onChange  立即用当前档位回调一次
 * @returns {() => void} stop
 */
export function watchLayoutMode(win, onChange) {
  if (!win) {
    onChange?.(LAYOUT_DESKTOP);
    return () => {};
  }

  const notify = () => onChange?.(currentMode(win));
  notify();

  if (typeof win.matchMedia !== 'function') {
    win.addEventListener?.('resize', notify);
    return () => win.removeEventListener?.('resize', notify);
  }

  const queries = [win.matchMedia(MEDIA_DESKTOP), win.matchMedia(MEDIA_TABLET)];
  const disposers = queries.map((mql) => {
    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', notify);
      return () => mql.removeEventListener('change', notify);
    }
    // Safari <14 只有 addListener
    mql.addListener?.(notify);
    return () => mql.removeListener?.(notify);
  });

  return () => disposers.forEach((dispose) => dispose());
}

export function isNarrow(mode) {
  return mode === LAYOUT_MOBILE;
}

/** tablet 与 mobile 都把列表/详情收进 drawer。 */
export function usesDrawer(mode) {
  return mode !== LAYOUT_DESKTOP;
}

import { describe, it, expect, vi } from 'vitest';
import {
  BREAKPOINT_DESKTOP,
  BREAKPOINT_TABLET,
  LAYOUT_DESKTOP,
  LAYOUT_MOBILE,
  LAYOUT_TABLET,
  MEDIA_DESKTOP,
  MEDIA_TABLET,
  isNarrow,
  layoutModeForWidth,
  usesDrawer,
  watchLayoutMode,
} from '../src/utils/breakpoints.js';

describe('layoutModeForWidth', () => {
  it('断点边界归上一档', () => {
    expect(layoutModeForWidth(BREAKPOINT_DESKTOP)).toBe(LAYOUT_DESKTOP);
    expect(layoutModeForWidth(BREAKPOINT_DESKTOP - 1)).toBe(LAYOUT_TABLET);
    expect(layoutModeForWidth(BREAKPOINT_TABLET)).toBe(LAYOUT_TABLET);
    expect(layoutModeForWidth(BREAKPOINT_TABLET - 1)).toBe(LAYOUT_MOBILE);
  });

  it('三个截图视口各落一档', () => {
    expect(layoutModeForWidth(1280)).toBe(LAYOUT_DESKTOP);
    expect(layoutModeForWidth(1024)).toBe(LAYOUT_DESKTOP);
    expect(layoutModeForWidth(390)).toBe(LAYOUT_MOBILE);
  });

  it('非法宽度回落 desktop', () => {
    expect(layoutModeForWidth(undefined)).toBe(LAYOUT_DESKTOP);
    expect(layoutModeForWidth(NaN)).toBe(LAYOUT_DESKTOP);
  });
});

describe('isNarrow / usesDrawer', () => {
  it('只有 mobile 算窄屏', () => {
    expect(isNarrow(LAYOUT_MOBILE)).toBe(true);
    expect(isNarrow(LAYOUT_TABLET)).toBe(false);
  });

  it('tablet 与 mobile 都走 drawer', () => {
    expect(usesDrawer(LAYOUT_DESKTOP)).toBe(false);
    expect(usesDrawer(LAYOUT_TABLET)).toBe(true);
    expect(usesDrawer(LAYOUT_MOBILE)).toBe(true);
  });
});

/** 造一个可控的 matchMedia：改宽度后手动触发 change。 */
function fakeWindow(initialWidth) {
  let width = initialWidth;
  const listeners = [];
  const win = {
    get innerWidth() { return width; },
    matchMedia: (query) => {
      const mql = {
        media: query,
        get matches() {
          const min = Number(/(\d+)px/.exec(query)[1]);
          return width >= min;
        },
        addEventListener: (_type, cb) => {
          listeners.push({ cb, query });
        },
        removeEventListener: (_type, cb) => {
          const i = listeners.findIndex((l) => l.cb === cb && l.query === query);
          if (i >= 0) listeners.splice(i, 1);
        },
      };
      return mql;
    },
    setWidth(next) {
      width = next;
      [...listeners].forEach(({ cb }) => cb());
    },
    listenerCount: () => listeners.length,
  };
  return win;
}

describe('watchLayoutMode', () => {
  it('订阅时立即回调一次当前档位', () => {
    const win = fakeWindow(1280);
    const cb = vi.fn();
    const stop = watchLayoutMode(win, cb);
    expect(cb).toHaveBeenCalledWith(LAYOUT_DESKTOP);
    stop();
  });

  it('宽度变化时跟着换档', () => {
    const win = fakeWindow(1280);
    const seen = [];
    const stop = watchLayoutMode(win, (m) => seen.push(m));
    win.setWidth(900);
    win.setWidth(390);
    win.setWidth(1024);
    expect(seen).toEqual([LAYOUT_DESKTOP, LAYOUT_TABLET, LAYOUT_TABLET,
      LAYOUT_MOBILE, LAYOUT_MOBILE, LAYOUT_DESKTOP, LAYOUT_DESKTOP]);
    stop();
  });

  it('stop() 之后监听全部摘掉，不再回调', () => {
    const win = fakeWindow(1280);
    const cb = vi.fn();
    const stop = watchLayoutMode(win, cb);
    expect(win.listenerCount()).toBe(2);
    stop();
    expect(win.listenerCount()).toBe(0);
    cb.mockClear();
    win.setWidth(390);
    expect(cb).not.toHaveBeenCalled();
  });

  it('两条 media query 覆盖两个断点', () => {
    expect(MEDIA_DESKTOP).toContain(`${BREAKPOINT_DESKTOP}px`);
    expect(MEDIA_TABLET).toContain(`${BREAKPOINT_TABLET}px`);
  });

  it('没有 window 时不抛异常', () => {
    const cb = vi.fn();
    const stop = watchLayoutMode(null, cb);
    expect(cb).toHaveBeenCalledWith(LAYOUT_DESKTOP);
    expect(() => stop()).not.toThrow();
  });

  it('没有 matchMedia 时回落到 resize 监听', () => {
    const handlers = [];
    const win = {
      innerWidth: 500,
      addEventListener: (_t, cb) => handlers.push(cb),
      removeEventListener: (_t, cb) => {
        const i = handlers.indexOf(cb);
        if (i >= 0) handlers.splice(i, 1);
      },
    };
    const cb = vi.fn();
    const stop = watchLayoutMode(win, cb);
    expect(cb).toHaveBeenLastCalledWith(LAYOUT_MOBILE);
    expect(handlers).toHaveLength(1);
    stop();
    expect(handlers).toHaveLength(0);
  });
});

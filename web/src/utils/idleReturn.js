// 空闲自动回展示模式（spec §9.1: 空闲 5 分钟回到展示模式，可配 0 关闭）。
//
// 纯逻辑 + 可注入的事件源和定时器，单测直接用 fake timers 推进。
// 事件都用捕获阶段挂在 target 上：页面里任何一处的指针/键盘/滚动都算"人还在"。

export const IDLE_EVENTS = Object.freeze([
  'pointerdown',
  'pointermove',
  'keydown',
  'wheel',
  'scroll',
  'touchstart',
]);

const MINUTE_MS = 60_000;

/**
 * @param {object} deps
 * @param {EventTarget} [deps.target]   事件源，默认 window
 * @param {number} [deps.minutes]       空闲阈值，<=0 表示关闭
 * @param {() => void} deps.onIdle      到点回调
 * @param {{setTimeout: Function, clearTimeout: Function}} [deps.timers]
 */
export function createIdleWatcher({
  target = typeof window !== 'undefined' ? window : null,
  minutes = 5,
  onIdle,
  // 注意不能写成 { setTimeout, clearTimeout }: 那样调用时 this 是这个对象,
  // 浏览器的 window.setTimeout 会抛 Illegal invocation。
  timers = {
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    clearTimeout: (h) => clearTimeout(h),
  },
} = {}) {
  const ms = Number(minutes) > 0 ? Number(minutes) * MINUTE_MS : 0;
  let handle = null;
  let running = false;

  const clear = () => {
    if (handle !== null) {
      timers.clearTimeout(handle);
      handle = null;
    }
  };

  const fire = () => {
    handle = null;
    if (typeof onIdle === 'function') onIdle();
  };

  const arm = () => {
    clear();
    if (!running || ms <= 0) return;
    handle = timers.setTimeout(fire, ms);
  };

  const onActivity = () => { if (running) arm(); };

  return {
    /** @returns {boolean} 是否真的开始计时（minutes<=0 时不开） */
    start() {
      if (running || ms <= 0) return false;
      running = true;
      IDLE_EVENTS.forEach((evt) => {
        target?.addEventListener?.(evt, onActivity, { passive: true, capture: true });
      });
      arm();
      return true;
    },
    stop() {
      if (!running) return;
      running = false;
      IDLE_EVENTS.forEach((evt) => {
        target?.removeEventListener?.(evt, onActivity, { capture: true });
      });
      clear();
    },
    /** 手动打断计时（例如路由变化也算一次活动）。 */
    poke: onActivity,
    get enabled() {
      return ms > 0;
    },
    get running() {
      return running;
    },
    get pending() {
      return handle !== null;
    },
  };
}

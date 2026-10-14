import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createIdleWatcher, IDLE_EVENTS } from '../src/utils/idleReturn.js';
import { createWakeLock } from '../src/utils/wakeLock.js';

/** 最小事件源: 记录挂了哪些监听, 并能手动派发。 */
function fakeTarget() {
  const listeners = new Map();
  return {
    listeners,
    addEventListener(type, fn) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(fn);
    },
    removeEventListener(type, fn) {
      listeners.get(type)?.delete(fn);
    },
    emit(type) {
      listeners.get(type)?.forEach((fn) => fn({ type }));
    },
    count() {
      let n = 0;
      listeners.forEach((set) => { n += set.size; });
      return n;
    },
  };
}

describe('createIdleWatcher', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('到点回调一次', () => {
    const onIdle = vi.fn();
    const target = fakeTarget();
    const w = createIdleWatcher({ target, minutes: 5, onIdle });
    expect(w.start()).toBe(true);
    vi.advanceTimersByTime(5 * 60_000 - 1);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it('任一交互都重置计时', () => {
    const onIdle = vi.fn();
    const target = fakeTarget();
    const w = createIdleWatcher({ target, minutes: 5, onIdle });
    w.start();
    IDLE_EVENTS.forEach((evt) => {
      vi.advanceTimersByTime(4 * 60_000);
      target.emit(evt);
    });
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(5 * 60_000);
    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it('minutes=0 表示关闭: 不挂监听也不计时', () => {
    const onIdle = vi.fn();
    const target = fakeTarget();
    const w = createIdleWatcher({ target, minutes: 0, onIdle });
    expect(w.enabled).toBe(false);
    expect(w.start()).toBe(false);
    expect(target.count()).toBe(0);
    vi.advanceTimersByTime(60 * 60_000);
    expect(onIdle).not.toHaveBeenCalled();
  });

  it('stop 摘掉全部监听并取消计时', () => {
    const onIdle = vi.fn();
    const target = fakeTarget();
    const w = createIdleWatcher({ target, minutes: 5, onIdle });
    w.start();
    expect(target.count()).toBe(IDLE_EVENTS.length);
    w.stop();
    expect(target.count()).toBe(0);
    expect(w.running).toBe(false);
    vi.advanceTimersByTime(60 * 60_000);
    expect(onIdle).not.toHaveBeenCalled();
  });

  it('重复 start 不会挂两遍监听', () => {
    const target = fakeTarget();
    const w = createIdleWatcher({ target, minutes: 5, onIdle: () => {} });
    w.start();
    w.start();
    expect(target.count()).toBe(IDLE_EVENTS.length);
  });

  it('poke 可以在没有真实事件时打断计时', () => {
    const onIdle = vi.fn();
    const w = createIdleWatcher({ target: fakeTarget(), minutes: 5, onIdle });
    w.start();
    vi.advanceTimersByTime(4 * 60_000);
    w.poke();
    vi.advanceTimersByTime(4 * 60_000);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(60_000);
    expect(onIdle).toHaveBeenCalledTimes(1);
  });
});

describe('createWakeLock', () => {
  const fakeDoc = (visibility = 'visible') => {
    const t = fakeTarget();
    return Object.assign(t, { visibilityState: visibility });
  };

  it('不支持时静默降级, start/stop 不抛', () => {
    const lock = createWakeLock({ nav: {}, doc: fakeDoc() });
    expect(lock.supported).toBe(false);
    expect(() => { lock.start(); lock.stop(); }).not.toThrow();
    expect(lock.held).toBe(false);
  });

  it('申请失败静默', async () => {
    const nav = { wakeLock: { request: vi.fn().mockRejectedValue(new Error('NotAllowed')) } };
    const lock = createWakeLock({ nav, doc: fakeDoc() });
    lock.start();
    await Promise.resolve();
    await Promise.resolve();
    expect(nav.wakeLock.request).toHaveBeenCalledWith('screen');
    expect(lock.held).toBe(false);
  });

  it('回到前台重新申请, stop 释放', async () => {
    const release = vi.fn().mockResolvedValue(undefined);
    const sentinel = { release, addEventListener: () => {} };
    const nav = { wakeLock: { request: vi.fn().mockResolvedValue(sentinel) } };
    const doc = fakeDoc();
    const lock = createWakeLock({ nav, doc });

    lock.start();
    await Promise.resolve();
    expect(lock.held).toBe(true);

    // 系统在切后台时释放了 sentinel: 这里模拟成句柄没了
    lock.stop();
    await Promise.resolve();
    expect(release).toHaveBeenCalledTimes(1);
    expect(doc.count()).toBe(0);

    lock.start();
    await Promise.resolve();
    nav.wakeLock.request.mockClear();
    doc.emit('visibilitychange');
    await Promise.resolve();
    // 已经持有时不会重复申请
    expect(nav.wakeLock.request).not.toHaveBeenCalled();
    lock.stop();
  });
});

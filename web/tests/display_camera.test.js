import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  boundsOf,
  createFitScheduler,
  fitAllView,
  fitAllViewWithFallback,
  resolveFitTargets,
  toBasePoint,
  viewChangedEnough,
} from '../src/utils/displayCamera.js';
import { IDENTITY_VIEW } from '../src/utils/canvasTransform.js';

describe('boundsOf', () => {
  it('空集与全脏数据返回 null', () => {
    expect(boundsOf([])).toBeNull();
    expect(boundsOf(null)).toBeNull();
    expect(boundsOf([{ x: 'a', y: null }])).toBeNull();
  });

  it('脏点被跳过, 不污染外接框', () => {
    const b = boundsOf([{ x: 0, y: 0 }, { x: NaN, y: 5 }, { x: 10, y: 20 }]);
    expect(b).toMatchObject({ minX: 0, minY: 0, maxX: 10, maxY: 20, count: 2 });
    expect(b.centerX).toBe(5);
    expect(b.centerY).toBe(10);
  });
});

describe('fitAllView', () => {
  const canvas = { viewWidth: 800, viewHeight: 600 };

  it('所有点都进画面, 且留出边距', () => {
    const points = [{ x: 100, y: 100 }, { x: 300, y: 400 }, { x: 200, y: 250 }];
    const view = fitAllView({ ...canvas, points, paddingRatio: 0.1 });
    // fit-all 产出的是视图叠加层, 点的映射就是 zoom*p + pan
    const mapped = points.map((p) => ({
      x: view.zoom * p.x + view.panX,
      y: view.zoom * p.y + view.panY,
    }));
    mapped.forEach((p) => {
      expect(p.x).toBeGreaterThanOrEqual(canvas.viewWidth * 0.1 - 1e-6);
      expect(p.x).toBeLessThanOrEqual(canvas.viewWidth * 0.9 + 1e-6);
      expect(p.y).toBeGreaterThanOrEqual(canvas.viewHeight * 0.1 - 1e-6);
      expect(p.y).toBeLessThanOrEqual(canvas.viewHeight * 0.9 + 1e-6);
    });
  });

  it('外接框中心落到画面中心', () => {
    const points = [{ x: 0, y: 0 }, { x: 100, y: 50 }];
    const v = fitAllView({ ...canvas, points });
    expect(v.zoom * 50 + v.panX).toBeCloseTo(400, 6);
    expect(v.zoom * 25 + v.panY).toBeCloseTo(300, 6);
  });

  it('单点不放大, 只居中', () => {
    const v = fitAllView({ ...canvas, points: [{ x: 40, y: 60 }] });
    expect(v.zoom).toBe(1);
    expect(40 + v.panX).toBeCloseTo(400, 6);
    expect(60 + v.panY).toBeCloseTo(300, 6);
  });

  it('缩放被夹在 canvasTransform 的上下限内', () => {
    const tiny = fitAllView({ ...canvas, points: [{ x: 0, y: 0 }, { x: 0.001, y: 0.001 }] });
    expect(tiny.zoom).toBeLessThanOrEqual(8);
    const huge = fitAllView({ ...canvas, points: [{ x: 0, y: 0 }, { x: 1e6, y: 1e6 }] });
    expect(huge.zoom).toBeGreaterThanOrEqual(0.5);
  });

  it('空点集 / 零尺寸画布返回 null', () => {
    expect(fitAllView({ ...canvas, points: [] })).toBeNull();
    expect(fitAllView({ viewWidth: 0, viewHeight: 0, points: [{ x: 1, y: 1 }] })).toBeNull();
  });

  it('连续 fit 是幂等的: 第二次用反解回来的 base 点算, 结果不变', () => {
    const base = [{ x: 100, y: 100 }, { x: 300, y: 400 }];
    const first = fitAllView({ ...canvas, points: base });
    // 画一帧后拿到的是带 view 的点
    const drawn = base.map((p) => ({
      x: first.zoom * p.x + first.panX,
      y: first.zoom * p.y + first.panY,
    }));
    const again = fitAllView({ ...canvas, points: drawn.map((p) => toBasePoint(p, first)) });
    expect(again.zoom).toBeCloseTo(first.zoom, 9);
    expect(again.panX).toBeCloseTo(first.panX, 6);
    expect(again.panY).toBeCloseTo(first.panY, 6);
  });
});

describe('resolveFitTargets / fitAllViewWithFallback：取景目标退化（spec §9.3）', () => {
  const canvas = { viewWidth: 800, viewHeight: 600 };
  const trackers = [{ x: 100, y: 100 }, { x: 300, y: 400 }];
  const beacons = [{ x: 10, y: 10 }, { x: 90, y: 80 }];
  const plan = [{ x: 0, y: 0 }, { x: 200, y: 150 }];

  it('有在线 tracker 时用 tracker 外接框, 不看 beacon/平面图', () => {
    const resolved = resolveFitTargets({ trackers, beacons, plan });
    expect(resolved.source).toBe('trackers');
    expect(resolved.points).toBe(trackers);

    const { view, source } = fitAllViewWithFallback({ ...canvas, trackers, beacons, plan });
    expect(source).toBe('trackers');
    expect(view.zoom * 200 + view.panX).toBeCloseTo(400, 6); // tracker 外接框中心 (200,250)
  });

  it('没有 tracker 时退化到全部 beacon 的外接框', () => {
    const resolved = resolveFitTargets({ trackers: [], beacons, plan });
    expect(resolved.source).toBe('beacons');
    expect(resolved.points).toBe(beacons);

    const { view, source } = fitAllViewWithFallback({ ...canvas, trackers: [], beacons, plan });
    expect(source).toBe('beacons');
    expect(view.zoom * 50 + view.panX).toBeCloseTo(400, 6); // beacon 外接框中心 (50,45)
  });

  it('tracker 和 beacon 都为空时退化到平面图外框', () => {
    const resolved = resolveFitTargets({ trackers: [], beacons: [], plan });
    expect(resolved.source).toBe('plan');
    expect(resolved.points).toBe(plan);

    const { view, source } = fitAllViewWithFallback({ ...canvas, trackers: [], beacons: [], plan });
    expect(source).toBe('plan');
    expect(view.zoom * 100 + view.panX).toBeCloseTo(400, 6); // 平面图外框中心 (100,75)
  });

  it('三组都为空时不动: source 与 view 都是 null', () => {
    const resolved = resolveFitTargets({ trackers: [], beacons: [], plan: [] });
    expect(resolved).toEqual({ source: null, points: null, bounds: null });

    const { view, source } = fitAllViewWithFallback({ ...canvas, trackers: [], beacons: [], plan: [] });
    expect(view).toBeNull();
    expect(source).toBeNull();
  });
});

describe('toBasePoint', () => {
  it('是 applyView 线性部分的逆运算', () => {
    const view = { zoom: 2, panX: 30, panY: -10 };
    const base = { x: 12, y: 34 };
    const shown = { x: view.zoom * base.x + view.panX, y: view.zoom * base.y + view.panY };
    expect(toBasePoint(shown, view)).toEqual(base);
  });

  it('identity view 原样返回', () => {
    expect(toBasePoint({ x: 5, y: 7 }, IDENTITY_VIEW)).toEqual({ x: 5, y: 7 });
  });
});

describe('viewChangedEnough', () => {
  const box = { viewWidth: 800, viewHeight: 600, jitterRatio: 0.05 };
  const prev = { zoom: 2, panX: 100, panY: 100 };

  it('没有旧相机时总是要动', () => {
    expect(viewChangedEnough(null, prev, box)).toBe(true);
  });

  it('位移小于视口 5% 不动', () => {
    expect(viewChangedEnough(prev, { ...prev, panX: 120 }, box)).toBe(false);
  });

  it('位移超过视口 5% 要动', () => {
    expect(viewChangedEnough(prev, { ...prev, panX: 140 }, box)).toBe(true);
  });

  it('缩放相对变化超过 5% 要动', () => {
    expect(viewChangedEnough(prev, { ...prev, zoom: 2.2 }, box)).toBe(true);
    expect(viewChangedEnough(prev, { ...prev, zoom: 2.05 }, box)).toBe(false);
  });

  it('阈值为 0 表示每次都动', () => {
    expect(viewChangedEnough(prev, prev, { ...box, jitterRatio: 0 })).toBe(true);
  });
});

describe('createFitScheduler', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('窗口内的多次登记合并成一次执行', () => {
    const onFit = vi.fn();
    const s = createFitScheduler({ delayMs: 2000, onFit });
    expect(s.schedule()).toBe(true);
    expect(s.schedule()).toBe(false);
    vi.advanceTimersByTime(1999);
    expect(onFit).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onFit).toHaveBeenCalledTimes(1);
    expect(s.pending).toBe(false);
  });

  it('持续更新也会按窗口节奏跑, 不会永远推迟', () => {
    const onFit = vi.fn();
    const s = createFitScheduler({ delayMs: 2000, onFit });
    for (let i = 0; i < 20; i += 1) {
      s.schedule();
      vi.advanceTimersByTime(500);
    }
    expect(onFit.mock.calls.length).toBeGreaterThanOrEqual(4);
  });

  it('cancel 之后不再触发', () => {
    const onFit = vi.fn();
    const s = createFitScheduler({ delayMs: 2000, onFit });
    s.schedule();
    s.cancel();
    vi.advanceTimersByTime(5000);
    expect(onFit).not.toHaveBeenCalled();
  });

  it('flush 立刻执行并吃掉待跑的定时器', () => {
    const onFit = vi.fn();
    const s = createFitScheduler({ delayMs: 2000, onFit });
    s.schedule();
    s.flush();
    expect(onFit).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(5000);
    expect(onFit).toHaveBeenCalledTimes(1);
  });
});

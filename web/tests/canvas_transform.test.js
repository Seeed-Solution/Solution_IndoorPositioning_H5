import { describe, it, expect } from 'vitest';
import {
  IDENTITY_VIEW,
  MAX_ZOOM,
  MIN_ZOOM,
  applyView,
  canvasToWorld,
  clampZoom,
  cssRadiusToCanvas,
  cssToCanvasPoint,
  fitTransform,
  hitTest,
  panBy,
  resetView,
  worldToCanvas,
  zoomAt,
} from '../src/utils/canvasTransform.js';

const BOUNDS = { minX: 0, minY: 0, maxX: 40, maxY: 20 };
const CANVAS = { canvasWidth: 800, canvasHeight: 600 };

describe('fitTransform', () => {
  it('保持宽高比，取两轴较小的缩放', () => {
    const t = fitTransform({ ...BOUNDS, ...CANVAS });
    // 0.9*800/40 = 18 ; 0.9*600/20 = 27 -> 取 18
    expect(t.scale).toBeCloseTo(18, 9);
  });

  it('数据框居中', () => {
    const t = fitTransform({ ...BOUNDS, ...CANVAS });
    const c = worldToCanvas(t, 20, 10);
    expect(c.x).toBeCloseTo(400, 6);
    expect(c.y).toBeCloseTo(300, 6);
  });

  it('Y 轴向上：世界 y 大 -> canvas y 小', () => {
    const t = fitTransform({ ...BOUNDS, ...CANVAS });
    expect(worldToCanvas(t, 0, 20).y).toBeLessThan(worldToCanvas(t, 0, 0).y);
  });

  it('退化输入（宽高为 0）不产生 NaN', () => {
    const t = fitTransform({ minX: 5, maxX: 5, minY: 5, maxY: 5, ...CANVAS });
    expect(Number.isFinite(t.k)).toBe(true);
    expect(t.k).toBeGreaterThan(0);
    const p = worldToCanvas(t, 5, 5);
    expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
  });

  it('背景图宽高比影响水平原点，不影响缩放', () => {
    const a = fitTransform({ ...BOUNDS, ...CANVAS });
    const b = fitTransform({ ...BOUNDS, ...CANVAS, imageAspect: 1 });
    expect(b.scale).toBeCloseTo(a.scale, 9);
    expect(b.originX).not.toBeCloseTo(a.originX, 3);
  });
});

describe('正反变换往返', () => {
  const cases = [
    { view: IDENTITY_VIEW },
    { view: { zoom: 2.5, panX: -120, panY: 64 } },
    { view: { zoom: 0.7, panX: 33.3, panY: -18.9 } },
    { view: { zoom: MAX_ZOOM, panX: 1000, panY: -1000 } },
  ];

  it.each(cases)('worldToCanvas -> canvasToWorld 误差 < 0.5 px (%#)', ({ view }) => {
    const t = applyView(fitTransform({ ...BOUNDS, ...CANVAS }), view);
    for (const [x, y] of [[0, 0], [40, 20], [12.345, 6.789], [-3, 25]]) {
      const px = worldToCanvas(t, x, y);
      const back = worldToCanvas(t, ...Object.values(canvasToWorld(t, px.x, px.y)));
      expect(Math.hypot(back.x - px.x, back.y - px.y)).toBeLessThan(0.5);
    }
  });

  it('canvasToWorld -> worldToCanvas 回到同一像素', () => {
    const t = applyView(fitTransform({ ...BOUNDS, ...CANVAS }), { zoom: 3, panX: 77, panY: -41 });
    for (const [cx, cy] of [[0, 0], [800, 600], [123.4, 456.7]]) {
      const w = canvasToWorld(t, cx, cy);
      const p = worldToCanvas(t, w.x, w.y);
      expect(Math.hypot(p.x - cx, p.y - cy)).toBeLessThan(0.5);
    }
  });
});

describe('zoomAt', () => {
  it('缩放中心不漂移', () => {
    const base = fitTransform({ ...BOUNDS, ...CANVAS });
    const anchor = { x: 210, y: 380 };
    let view = resetView();
    const worldBefore = canvasToWorld(applyView(base, view), anchor.x, anchor.y);
    view = zoomAt(view, anchor, 1.15);
    view = zoomAt(view, anchor, 1.15);
    view = zoomAt(view, anchor, 1 / 1.15);
    const px = worldToCanvas(applyView(base, view), worldBefore.x, worldBefore.y);
    expect(Math.hypot(px.x - anchor.x, px.y - anchor.y)).toBeLessThan(0.5);
  });

  it('缩放被夹在 [MIN_ZOOM, MAX_ZOOM]', () => {
    let view = resetView();
    for (let i = 0; i < 40; i += 1) view = zoomAt(view, { x: 0, y: 0 }, 1.5);
    expect(view.zoom).toBe(MAX_ZOOM);
    for (let i = 0; i < 80; i += 1) view = zoomAt(view, { x: 0, y: 0 }, 0.5);
    expect(view.zoom).toBe(MIN_ZOOM);
  });

  it('到达边界后 pan 不再变化', () => {
    const at = zoomAt({ zoom: MAX_ZOOM, panX: 12, panY: 34 }, { x: 100, y: 100 }, 2);
    expect(at).toEqual({ zoom: MAX_ZOOM, panX: 12, panY: 34 });
  });

  it('clampZoom 处理非法值', () => {
    expect(clampZoom(NaN)).toBe(1);
    expect(clampZoom(undefined)).toBe(1);
  });
});

describe('panBy / resetView', () => {
  it('平移把点整体挪走同样的像素', () => {
    const base = fitTransform({ ...BOUNDS, ...CANVAS });
    const before = worldToCanvas(applyView(base, resetView()), 10, 10);
    const after = worldToCanvas(applyView(base, panBy(resetView(), 25, -40)), 10, 10);
    expect(after.x - before.x).toBeCloseTo(25, 6);
    expect(after.y - before.y).toBeCloseTo(-40, 6);
  });

  it('resetView 回到恒等', () => {
    expect(resetView()).toEqual({ zoom: 1, panX: 0, panY: 0 });
  });
});

describe('CSS <-> backing 换算', () => {
  const rect = { left: 100, top: 50, width: 400, height: 300 };

  it('显示尺寸是 backing 的一半时，坐标翻倍', () => {
    const p = cssToCanvasPoint(rect, 800, 600, 300, 200);
    expect(p.x).toBeCloseTo(400, 9);
    expect(p.y).toBeCloseTo(300, 9);
  });

  it('12 CSS px 半径按同一比例放大', () => {
    expect(cssRadiusToCanvas(rect, 800, 600, 12)).toBeCloseTo(24, 9);
  });

  it('rect 宽为 0 时不产生 Infinity', () => {
    const p = cssToCanvasPoint({ left: 0, top: 0, width: 0, height: 0 }, 800, 600, 10, 10);
    expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
  });
});

describe('hitTest', () => {
  const targets = [
    { id: 'b', x: 100, y: 100, hitRadius: 8 },
    { id: 'a', x: 100, y: 100, hitRadius: 8 },
    { id: 'far', x: 400, y: 400, hitRadius: 8 },
    { id: 'area', x: 200, y: 100, hitRadius: 10 },
  ];

  it('12 px 内命中', () => {
    expect(hitTest(targets, { x: 108, y: 100 }, 12)).toBeTruthy();
  });

  it('超出容差不命中', () => {
    expect(hitTest(targets, { x: 100, y: 130 }, 12)).toBeNull();
  });

  it('取最近的一个', () => {
    expect(hitTest(targets, { x: 195, y: 100 }, 12)).toBe('area');
  });

  it('距离相同按 id 升序', () => {
    expect(hitTest(targets, { x: 100, y: 100 }, 12)).toBe('a');
  });

  it('区域圆只在圆心附近命中，大半径不吞掉整图', () => {
    const big = [{ id: 'big', x: 100, y: 100, hitRadius: 10 }];
    expect(hitTest(big, { x: 100, y: 100 }, 12)).toBe('big');
    expect(hitTest(big, { x: 260, y: 100 }, 12)).toBeNull();
  });

  it('空输入返回 null', () => {
    expect(hitTest([], { x: 0, y: 0 })).toBeNull();
    expect(hitTest(null, { x: 0, y: 0 })).toBeNull();
  });
});

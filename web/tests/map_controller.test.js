import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createMapController } from '../src/controllers/mapPageController.js';
import { DEFAULT_MAP_STATE } from '../src/utils/mapUrlState.js';

const TRACKERS = {
  T1: { trackerId: 'T1', type: 'calculation', map: 'Floor 1', x: 1, y: 2 },
  T2: { trackerId: 'T2', type: 'approximate', map: 'Floor 2', radius: 3 },
  G1: { trackerId: 'G1', type: 'wGS84', lat: 22.5, lon: 114.0 },
};

function setup(initial = {}) {
  const state = { ...DEFAULT_MAP_STATE, ...initial };
  const trackers = { ...TRACKERS };
  let hovered = '';
  const history = [];
  const focusCalls = { indoor: [], outdoor: [] };

  const controller = createMapController({
    getTrackers: () => trackers,
    getState: () => state,
    setState: (patch, opts = {}) => {
      Object.assign(state, patch);
      history.push({ patch, history: opts.history || 'push' });
    },
    getHovered: () => hovered,
    setHovered: (id) => { hovered = id; },
    focusHandlers: {
      indoor: (id) => focusCalls.indoor.push(id),
      outdoor: (id) => focusCalls.outdoor.push(id),
    },
  });

  return {
    controller,
    state,
    trackers,
    history,
    focusCalls,
    getHovered: () => hovered,
  };
}

describe('selectTracker', () => {
  it('更新 tracker 与 panel，并走 push', () => {
    const { controller, state, history } = setup();
    expect(controller.selectTracker('T1')).toBe(true);
    expect(state.tracker).toBe('T1');
    expect(state.panel).toBe('detail');
    expect(history[0].history).toBe('push');
  });

  it('室内层选中别的平面图上的设备时带上楼层', () => {
    const { controller, state } = setup({ layer: 'indoor', map: 'Floor 1' });
    controller.selectTracker('T2');
    expect(state.map).toBe('Floor 2');
  });

  it('不自动跨图层：室内层选中 GNSS 设备不改 layer', () => {
    const { controller, state } = setup({ layer: 'indoor' });
    controller.selectTracker('G1');
    expect(state.layer).toBe('indoor');
    expect(controller.suggestLayerFor('G1')).toBe('outdoor');
  });

  it('未知 id 直接忽略，不动状态', () => {
    const { controller, state, history } = setup();
    expect(controller.selectTracker('NOPE')).toBe(false);
    expect(controller.selectTracker('')).toBe(false);
    expect(controller.selectTracker(null)).toBe(false);
    expect(state.tracker).toBe('');
    expect(history).toHaveLength(0);
  });

  it('选中时默认顺带 focus，可以关掉', () => {
    const { controller, focusCalls } = setup({ layer: 'indoor' });
    controller.selectTracker('T1');
    expect(focusCalls.indoor).toEqual(['T1']);
    controller.selectTracker('T2', { focus: false });
    expect(focusCalls.indoor).toEqual(['T1']);
  });
});

describe('focusTracker', () => {
  it('按当前图层派发给对应实现', () => {
    const indoor = setup({ layer: 'indoor' });
    indoor.controller.focusTracker('T1');
    expect(indoor.focusCalls.indoor).toEqual(['T1']);
    expect(indoor.focusCalls.outdoor).toEqual([]);

    const outdoor = setup({ layer: 'outdoor' });
    outdoor.controller.focusTracker('G1');
    expect(outdoor.focusCalls.outdoor).toEqual(['G1']);
    expect(outdoor.focusCalls.indoor).toEqual([]);
  });

  it('未知 id 不派发', () => {
    const { controller, focusCalls } = setup();
    expect(controller.focusTracker('NOPE')).toBe(false);
    expect(focusCalls.indoor).toEqual([]);
  });

  it('缺少图层实现时返回 false 而不是抛异常', () => {
    const controller = createMapController({
      getTrackers: () => TRACKERS,
      getState: () => ({ ...DEFAULT_MAP_STATE }),
      setState: () => {},
    });
    expect(controller.focusTracker('T1')).toBe(false);
  });
});

describe('hoverTracker', () => {
  it('设置与清空悬停 id', () => {
    const { controller, getHovered } = setup();
    expect(controller.hoverTracker('T1')).toBe(true);
    expect(getHovered()).toBe('T1');
    expect(controller.hoverTracker(null)).toBe(true);
    expect(getHovered()).toBe('');
  });

  it('未知 id 不写入', () => {
    const { controller, getHovered } = setup();
    expect(controller.hoverTracker('NOPE')).toBe(false);
    expect(getHovered()).toBe('');
  });

  it('hover 不触发换层，也不改 URL 状态', () => {
    const { controller, state, history } = setup({ layer: 'indoor' });
    controller.hoverTracker('G1');
    expect(state.layer).toBe('indoor');
    expect(history).toHaveLength(0);
  });
});

describe('reconcile', () => {
  let ctx;
  beforeEach(() => { ctx = setup({ layer: 'indoor' }); });

  it('轮询更新后设备还在，选择保持不变', () => {
    ctx.controller.selectTracker('T1');
    ctx.history.length = 0;
    ctx.trackers.T1 = { ...ctx.trackers.T1, x: 9, y: 9 };
    ctx.controller.reconcile();
    expect(ctx.state.tracker).toBe('T1');
    expect(ctx.history).toHaveLength(0);
  });

  it('设备消失后清掉选择并回到列表', () => {
    ctx.controller.selectTracker('T1');
    delete ctx.trackers.T1;
    ctx.controller.reconcile();
    expect(ctx.state.tracker).toBe('');
    expect(ctx.state.panel).toBe('list');
  });

  it('没有选中时什么都不做', () => {
    ctx.controller.reconcile();
    expect(ctx.history).toHaveLength(0);
  });

  it('悬停的设备消失后把 hover 清掉', () => {
    ctx.controller.hoverTracker('T1');
    expect(ctx.getHovered()).toBe('T1');
    delete ctx.trackers.T1;
    ctx.controller.reconcile();
    expect(ctx.getHovered()).toBe('');
  });

  it('悬停的设备还在就不动 hover', () => {
    ctx.controller.hoverTracker('T1');
    ctx.controller.reconcile();
    expect(ctx.getHovered()).toBe('T1');
  });
});

describe('setLayer / layerOf', () => {
  it('只在图层真的变化时写状态', () => {
    const { controller, history } = setup({ layer: 'indoor' });
    expect(controller.setLayer('indoor')).toBe(false);
    expect(history).toHaveLength(0);
    expect(controller.setLayer('outdoor')).toBe(true);
    expect(history[0].history).toBe('push');
  });

  it('换图层时清掉 hover', () => {
    const { controller, getHovered } = setup({ layer: 'indoor' });
    controller.hoverTracker('T1');
    controller.setLayer('outdoor');
    expect(getHovered()).toBe('');
  });

  it('layerOf 复用 isOutdoorTracker：室内类型带残留经纬度仍是室内', () => {
    const { controller } = setup();
    expect(controller.layerOf({ type: 'calculation', lat: 1, lon: 2 })).toBe('indoor');
    expect(controller.layerOf({ type: 'unknown', lat: 1, lon: 2 })).toBe('indoor');
    expect(controller.layerOf({ type: 'wGS84' })).toBe('outdoor');
  });
});

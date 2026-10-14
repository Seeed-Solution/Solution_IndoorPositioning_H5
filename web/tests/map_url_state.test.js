import { describe, it, expect } from 'vitest';
import {
  DEFAULT_MAP_STATE,
  DISPLAY_PATH,
  MODE_DISPLAY,
  isDisplayQuery,
  isDisplayRoute,
  LEGACY_ROUTE_MAP,
  MAP_PATH,
  legacyRedirect,
  migrateLastVisitedPage,
  parseMapQuery,
  parseTrails,
  sameMapState,
  sameQuery,
  serializeMapState,
} from '../src/utils/mapUrlState.js';

describe('parseMapQuery', () => {
  it('空 query 得到全缺省状态', () => {
    expect(parseMapQuery()).toEqual({ ...DEFAULT_MAP_STATE });
    expect(parseMapQuery({})).toEqual({ ...DEFAULT_MAP_STATE });
  });

  it('合法取值原样保留', () => {
    const s = parseMapQuery({
      layer: 'outdoor',
      map: 'Floor 2',
      tracker: 'EUI-001',
      q: 'fork',
      status: 'online',
      group: 'Warehouse',
      trails: '0',
      panel: 'detail',
    });
    expect(s).toEqual({
      layer: 'outdoor',
      map: 'Floor 2',
      tracker: 'EUI-001',
      q: 'fork',
      status: 'online',
      group: 'Warehouse',
      trails: false,
      panel: 'detail',
      mode: 'workspace',
    });
  });

  it('非法枚举值回落到缺省而不是抛异常', () => {
    const s = parseMapQuery({ layer: 'space', status: 'zombie', panel: '../etc' });
    expect(s.layer).toBe('indoor');
    expect(s.status).toBe('all');
    expect(s.panel).toBe('list');
  });

  it('大小写不敏感', () => {
    expect(parseMapQuery({ layer: 'OUTDOOR', status: 'Starred' })).toMatchObject({
      layer: 'outdoor',
      status: 'starred',
    });
  });

  it('数组形式的重复参数取第一个', () => {
    expect(parseMapQuery({ layer: ['outdoor', 'indoor'] }).layer).toBe('outdoor');
  });

  it('trails 只认 0/1 与 true/false', () => {
    expect(parseTrails('0')).toBe(false);
    expect(parseTrails('false')).toBe(false);
    expect(parseTrails('1')).toBe(true);
    expect(parseTrails('yes')).toBe(true); // 非法 -> 缺省(开)
    expect(parseTrails(undefined)).toBe(true);
  });
});

describe('serializeMapState', () => {
  it('缺省字段全部省略', () => {
    expect(serializeMapState(DEFAULT_MAP_STATE)).toEqual({});
  });

  it('只写非缺省字段', () => {
    expect(serializeMapState({ ...DEFAULT_MAP_STATE, layer: 'outdoor', trails: false }))
      .toEqual({ layer: 'outdoor', trails: '0' });
  });

  it('parse(serialize(x)) 幂等', () => {
    const s = {
      layer: 'outdoor', map: 'F1', tracker: 'T1', q: 'a',
      status: 'offline', group: 'G', trails: false, panel: 'closed',
      mode: 'display',
    };
    expect(parseMapQuery(serializeMapState(s))).toEqual(s);
    expect(sameMapState(s, parseMapQuery(serializeMapState(s)))).toBe(true);
  });
});

describe('sameQuery', () => {
  it('忽略空值差异', () => {
    expect(sameQuery({ layer: 'outdoor' }, { layer: 'outdoor', q: '' })).toBe(true);
    expect(sameQuery({ layer: 'outdoor' }, { layer: 'indoor' })).toBe(false);
  });
});

describe('legacyRedirect', () => {
  it('四条旧路径都有映射', () => {
    expect(Object.keys(LEGACY_ROUTE_MAP).sort())
      .toEqual(['/config-tracker', '/map-overview', '/outdoor-map', '/tracker']);
  });

  it('tracker 与 config-tracker -> 室内 + 列表面板', () => {
    for (const p of ['/tracker', '/config-tracker']) {
      expect(legacyRedirect(p)).toEqual({ path: MAP_PATH, query: {} });
    }
  });

  it('map-overview -> 室内缺省', () => {
    expect(legacyRedirect('/map-overview')).toEqual({ path: MAP_PATH, query: {} });
  });

  it('outdoor-map -> layer=outdoor', () => {
    expect(legacyRedirect('/outdoor-map')).toEqual({ path: MAP_PATH, query: { layer: 'outdoor' } });
  });

  it('带 /web base 前缀与结尾斜杠也能识别', () => {
    expect(legacyRedirect('/web/outdoor-map')).toEqual({ path: MAP_PATH, query: { layer: 'outdoor' } });
    expect(legacyRedirect('/web/outdoor-map/')).toEqual({ path: MAP_PATH, query: { layer: 'outdoor' } });
    expect(legacyRedirect('/outdoor-map?foo=1')).toEqual({ path: MAP_PATH, query: { layer: 'outdoor' } });
  });

  it('未知路径不改写', () => {
    expect(legacyRedirect('/config')).toBeNull();
    expect(legacyRedirect('')).toBeNull();
  });
});

describe('migrateLastVisitedPage', () => {
  it('旧地图路径改写到 /map', () => {
    expect(migrateLastVisitedPage('/outdoor-map')).toBe('/map?layer=outdoor');
    expect(migrateLastVisitedPage('/map-overview')).toBe('/map');
    expect(migrateLastVisitedPage('/config-tracker')).toBe('/map');
  });

  it('/config 保持不动', () => {
    expect(migrateLastVisitedPage('/config')).toBe('/config');
  });

  it('已经是新路径的 fullPath 原样返回', () => {
    expect(migrateLastVisitedPage('/map?layer=outdoor&tracker=T1')).toBe('/map?layer=outdoor&tracker=T1');
  });

  it('登录页 / 根路径 / 空值返回 null', () => {
    expect(migrateLastVisitedPage('/login')).toBeNull();
    expect(migrateLastVisitedPage('/')).toBeNull();
    expect(migrateLastVisitedPage(null)).toBeNull();
    expect(migrateLastVisitedPage('')).toBeNull();
  });
});

describe('mode（展示模式）', () => {
  it('缺省是 workspace, 序列化时省略', () => {
    expect(parseMapQuery({}).mode).toBe('workspace');
    expect(serializeMapState({ ...DEFAULT_MAP_STATE, mode: 'workspace' }).mode).toBeUndefined();
  });

  it('display 往返不丢', () => {
    const q = serializeMapState({ ...DEFAULT_MAP_STATE, mode: MODE_DISPLAY });
    expect(q).toEqual({ mode: 'display' });
    expect(parseMapQuery(q).mode).toBe('display');
  });

  it('非法值回落到 workspace', () => {
    expect(parseMapQuery({ mode: 'kiosk' }).mode).toBe('workspace');
    expect(parseMapQuery({ mode: ['display', 'workspace'] }).mode).toBe('display');
    expect(parseMapQuery({ mode: 'DISPLAY' }).mode).toBe('display');
  });

  it('mode 与其他状态并存, 互不影响', () => {
    const state = {
      ...DEFAULT_MAP_STATE, mode: MODE_DISPLAY, layer: 'outdoor', tracker: 'T1', trails: false,
    };
    const round = parseMapQuery(serializeMapState(state));
    expect(round).toEqual(state);
    expect(sameMapState(state, round)).toBe(true);
  });

  it('sameMapState 区分两种模式', () => {
    expect(sameMapState(
      { ...DEFAULT_MAP_STATE },
      { ...DEFAULT_MAP_STATE, mode: MODE_DISPLAY },
    )).toBe(false);
  });

  it('isDisplayQuery / isDisplayRoute', () => {
    expect(isDisplayQuery({ mode: 'display' })).toBe(true);
    expect(isDisplayQuery({})).toBe(false);
    expect(isDisplayRoute({ path: '/map', query: { mode: 'display' } })).toBe(true);
    expect(isDisplayRoute({ path: '/web/map', query: { mode: 'display' } })).toBe(true);
    expect(isDisplayRoute({ path: '/config', query: { mode: 'display' } })).toBe(false);
    expect(isDisplayRoute({ path: '/map', query: {} })).toBe(false);
  });

  it('默认落点常量就是展示模式的 /map', () => {
    expect(DISPLAY_PATH).toBe('/map?mode=display');
    const [path, qs] = DISPLAY_PATH.split('?');
    expect(path).toBe(MAP_PATH);
    expect(parseMapQuery(Object.fromEntries(new URLSearchParams(qs))).mode).toBe('display');
  });

  it('旧路由重定向不带 mode（旧书签仍进工作台）', () => {
    expect(legacyRedirect('/outdoor-map').query.mode).toBeUndefined();
  });
});

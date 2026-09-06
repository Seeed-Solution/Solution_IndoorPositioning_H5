// /map 单页的 URL 状态编解码。
//
// 查询参数是页面唯一的状态真相: 刷新、前进/后退、外部书签都靠它复原界面。
// 这里只做纯函数, 不碰 vue-router, 便于单测。

export const LAYER_INDOOR = 'indoor';
export const LAYER_OUTDOOR = 'outdoor';
export const LAYERS = [LAYER_INDOOR, LAYER_OUTDOOR];

export const STATUSES = ['all', 'online', 'offline', 'starred'];
export const PANELS = ['list', 'detail', 'closed'];

// 同一个 /map 页面的两种模式: workspace 是三栏工作台, display 是全屏展示。
export const MODE_WORKSPACE = 'workspace';
export const MODE_DISPLAY = 'display';
export const MODES = [MODE_WORKSPACE, MODE_DISPLAY];

/** 缺省状态。序列化时与缺省相同的字段一律省略, URL 才不会长成一条噪声。 */
export const DEFAULT_MAP_STATE = Object.freeze({
  layer: LAYER_INDOOR,
  map: '',
  tracker: '',
  q: '',
  status: 'all',
  group: '',
  trails: true,
  panel: 'list',
  mode: MODE_WORKSPACE,
});

const firstValue = (v) => (Array.isArray(v) ? v[0] : v);

const asString = (v) => {
  const raw = firstValue(v);
  if (raw === undefined || raw === null) return '';
  return String(raw);
};

const oneOf = (v, allowed, fallback) => {
  const s = asString(v).toLowerCase();
  return allowed.includes(s) ? s : fallback;
};

/**
 * trails 只认 '0'/'1'（也兼容 true/false）。其余一律回落到默认开启。
 */
export function parseTrails(v) {
  const s = asString(v).toLowerCase();
  if (s === '0' || s === 'false') return false;
  if (s === '1' || s === 'true') return true;
  return DEFAULT_MAP_STATE.trails;
}

/**
 * query 对象 -> 归一化状态。非法取值静默回落到缺省, 不抛异常:
 * 用户手改 URL 不应该把页面打崩。
 */
export function parseMapQuery(query = {}) {
  const q = query || {};
  return {
    layer: oneOf(q.layer, LAYERS, DEFAULT_MAP_STATE.layer),
    map: asString(q.map),
    tracker: asString(q.tracker),
    q: asString(q.q),
    status: oneOf(q.status, STATUSES, DEFAULT_MAP_STATE.status),
    group: asString(q.group),
    trails: parseTrails(q.trails),
    panel: oneOf(q.panel, PANELS, DEFAULT_MAP_STATE.panel),
    mode: oneOf(q.mode, MODES, DEFAULT_MAP_STATE.mode),
  };
}

/** 状态 -> query 对象; 与缺省相同的字段省略。 */
export function serializeMapState(state = {}) {
  const s = { ...DEFAULT_MAP_STATE, ...state };
  const out = {};
  if (s.layer !== DEFAULT_MAP_STATE.layer) out.layer = s.layer;
  if (s.map) out.map = s.map;
  if (s.tracker) out.tracker = s.tracker;
  if (s.q) out.q = s.q;
  if (s.status !== DEFAULT_MAP_STATE.status) out.status = s.status;
  if (s.group) out.group = s.group;
  if (s.trails !== DEFAULT_MAP_STATE.trails) out.trails = s.trails ? '1' : '0';
  if (s.panel !== DEFAULT_MAP_STATE.panel) out.panel = s.panel;
  if (s.mode !== DEFAULT_MAP_STATE.mode) out.mode = s.mode;
  return out;
}

/** 两个 query 是否等价（避免 router.replace 打无意义的历史记录）。 */
export function sameQuery(a = {}, b = {}) {
  const ka = Object.keys(a).filter((k) => a[k] !== undefined && a[k] !== '');
  const kb = Object.keys(b).filter((k) => b[k] !== undefined && b[k] !== '');
  if (ka.length !== kb.length) return false;
  return ka.every((k) => String(a[k]) === String(b[k]));
}

export function sameMapState(a, b) {
  const pa = parseMapQuery(serializeMapState(a));
  const pb = parseMapQuery(serializeMapState(b));
  return Object.keys(DEFAULT_MAP_STATE).every((k) => pa[k] === pb[k]);
}

// --------------------------------------------------------------------------- //
// 旧路由兼容
// --------------------------------------------------------------------------- //

export const MAP_PATH = '/map';

/** 登录后的默认落点: 展示模式（spec §9.1）。 */
export const DISPLAY_PATH = `${MAP_PATH}?mode=${MODE_DISPLAY}`;

/** 某个 query 是否处在展示模式。 */
export function isDisplayQuery(query = {}) {
  return parseMapQuery(query).mode === MODE_DISPLAY;
}

/** 某条 route（path + query）是否是 /map 的展示模式。 */
export function isDisplayRoute(route = {}) {
  return stripBase(route.path || '') === MAP_PATH && isDisplayQuery(route.query || {});
}

/** 旧路径 -> 新路径 + query。不认识的路径返回 null。 */
export const LEGACY_ROUTE_MAP = Object.freeze({
  '/tracker': { layer: LAYER_INDOOR, panel: 'list' },
  '/config-tracker': { layer: LAYER_INDOOR, panel: 'list' },
  '/map-overview': { layer: LAYER_INDOOR },
  '/outdoor-map': { layer: LAYER_OUTDOOR },
});

function stripBase(path) {
  if (typeof path !== 'string') return '';
  let p = path.split('?')[0].split('#')[0];
  if (p.startsWith('/web/')) p = p.slice(4);
  else if (p === '/web') p = '/';
  if (p.length > 1 && p.endsWith('/')) p = p.slice(0, -1);
  return p;
}

/**
 * @returns {{path: string, query: object}|null}
 */
export function legacyRedirect(path) {
  const p = stripBase(path);
  const preset = LEGACY_ROUTE_MAP[p];
  if (!preset) return null;
  return { path: MAP_PATH, query: serializeMapState({ ...DEFAULT_MAP_STATE, ...preset }) };
}

/**
 * lastVisitedPage 迁移: 旧值是裸 path（不带 query）。落在旧地图路由上的
 * 一律改写成对应的 /map?...，其余原样返回；空值返回 null。
 */
export function migrateLastVisitedPage(stored) {
  if (!stored || typeof stored !== 'string') return null;
  const target = legacyRedirect(stored);
  if (!target) {
    const p = stripBase(stored);
    return p === '/login' || p === '/' ? null : stored;
  }
  const qs = new URLSearchParams(target.query).toString();
  return qs ? `${target.path}?${qs}` : target.path;
}

// 展示模式（/map?mode=display）的可调参数。
//
// spec §9 只点名了 `display.idleReturnMinutes` 与 `rotateFloorsSeconds`，
// 没有指定配置载体；后端目前也没有对应字段。这里落在前端配置模块，默认值写死，
// 允许用 localStorage 的 `displaySettings`（一段 JSON）在设备上覆盖，
// 后端将来提供接口时把 loadDisplayConfig 换成读接口即可，调用方不用动。

export const DISPLAY_STORAGE_KEY = 'displaySettings';

export const DISPLAY_DEFAULTS = Object.freeze({
  // 非展示页面无交互多久自动回到展示模式；0 关闭。
  idleReturnMinutes: 5,
  // fit-all 重算的防抖窗口（毫秒）。
  fitDebounceMs: 2000,
  // fit-all 的边距，按视口短边比例算（两侧各留这么多）。
  fitPaddingRatio: 0.08,
  // 抖动阈值：新旧相机差异小于视口的这个比例就不动，避免每帧抖。
  fitJitterRatio: 0.05,
  // 楼层轮播，0 表示关闭（spec §9.3 默认关闭）。
  rotateFloorsSeconds: 0,
});

const NUMERIC_KEYS = Object.keys(DISPLAY_DEFAULTS);

/** 合并覆盖值：只接受有限数字，其余回落默认。 */
export function mergeDisplayConfig(overrides) {
  const out = { ...DISPLAY_DEFAULTS };
  if (!overrides || typeof overrides !== 'object') return out;
  NUMERIC_KEYS.forEach((key) => {
    const v = Number(overrides[key]);
    if (Number.isFinite(v) && v >= 0) out[key] = v;
  });
  return out;
}

/** 读当前生效的展示模式配置。读失败（隐私模式等）静默用默认值。 */
export function loadDisplayConfig(storage = typeof localStorage !== 'undefined' ? localStorage : null) {
  try {
    const raw = storage?.getItem(DISPLAY_STORAGE_KEY);
    if (!raw) return { ...DISPLAY_DEFAULTS };
    return mergeDisplayConfig(JSON.parse(raw));
  } catch (err) {
    return { ...DISPLAY_DEFAULTS };
  }
}

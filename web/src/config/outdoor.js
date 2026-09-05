// 室外底图源配置。后端 dashboard_config.json 的 outdoor 段缺失时用这里的默认值,
// 保证旧配置文件原样可读。
//
// gcj02Correction 只是一个标记: 高德/天地图的瓦片用 GCJ-02, 与设备上报的 WGS84
// 存在偏移。本期不实现偏移算法, 只在 UI 上提示坐标系不一致。

export const DEFAULT_TILE_SOURCES = [
  {
    id: 'osm',
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    subdomains: ['a', 'b', 'c'],
    maxZoom: 19,
    coordSystem: 'wgs84',
    gcj02Correction: false,
  },
  {
    id: 'amap',
    name: 'AMap (GCJ-02)',
    url: 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    attribution: '&copy; AutoNavi',
    subdomains: ['1', '2', '3', '4'],
    maxZoom: 18,
    coordSystem: 'gcj02',
    gcj02Correction: true,
  },
  {
    id: 'tianditu',
    name: 'Tianditu (GCJ-02)',
    url: 'https://t{s}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=YOUR_TIANDITU_KEY',
    attribution: '&copy; Tianditu',
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maxZoom: 18,
    coordSystem: 'gcj02',
    gcj02Correction: true,
  },
];

export const DEFAULT_OUTDOOR_CONFIG = {
  tileSources: DEFAULT_TILE_SOURCES,
  defaultSource: 'osm',
};

/** 补齐缺失字段, 永远返回一份可用的 outdoor 配置。 */
export function normalizeOutdoorConfig(outdoor) {
  const sources = Array.isArray(outdoor?.tileSources) && outdoor.tileSources.length > 0
    ? outdoor.tileSources.map((s) => ({
      id: s.id || s.name || 'custom',
      name: s.name || s.id || 'Custom',
      url: s.url,
      attribution: s.attribution || '',
      subdomains: s.subdomains || undefined,
      maxZoom: s.maxZoom || 19,
      coordSystem: s.coordSystem || 'wgs84',
      gcj02Correction: s.gcj02Correction === true,
    })).filter((s) => !!s.url)
    : DEFAULT_TILE_SOURCES;
  const wanted = outdoor?.defaultSource;
  const defaultSource = sources.some((s) => s.id === wanted) ? wanted : sources[0].id;
  return { tileSources: sources, defaultSource };
}

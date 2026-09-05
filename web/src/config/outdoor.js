// 室外底图源配置。后端 dashboard_config.json 的 outdoor 段缺失时用这里的默认值,
// 保证旧配置文件原样可读。
//
// kind 区分两类底图:
//   raster  —— 传统 {z}/{x}/{y} 瓦片 URL, 走 L.tileLayer, 需要联网。
//   pmtiles —— 单个 .pmtiles 归档 (protomaps-leaflet), 走 HTTP Range 请求,
//              可以完全离线。归档由 compose 只读挂载到 /uploads/pmtiles/,
//              提取命令见 docs/PMTILES.md。
//
// gcj02Correction 只是一个标记: 高德/天地图的瓦片用 GCJ-02, 与设备上报的 WGS84
// 存在偏移。本期不实现偏移算法, 只在 UI 上提示坐标系不一致。

// ODbL 要求署名可点击回到 OSM 版权页。
export const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>';

export const TILE_KIND_RASTER = 'raster';
export const TILE_KIND_PMTILES = 'pmtiles';

/** 离线 PMTiles 归档在容器里的挂载点, 与 nginx / StaticFiles 的 /uploads 一致。 */
export const PMTILES_MOUNT_PREFIX = '/uploads/pmtiles';

export const DEFAULT_TILE_SOURCES = [
  {
    id: 'osm',
    name: 'OpenStreetMap',
    kind: TILE_KIND_RASTER,
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: OSM_ATTRIBUTION,
    subdomains: ['a', 'b', 'c'],
    maxZoom: 19,
    coordSystem: 'wgs84',
    gcj02Correction: false,
  },
  {
    id: 'pmtiles-offline',
    name: 'Offline (PMTiles)',
    kind: TILE_KIND_PMTILES,
    url: `${PMTILES_MOUNT_PREFIX}/demo.pmtiles`,
    attribution: OSM_ATTRIBUTION,
    maxZoom: 18,
    coordSystem: 'wgs84',
    gcj02Correction: false,
  },
  {
    id: 'amap',
    name: 'AMap (GCJ-02)',
    kind: TILE_KIND_RASTER,
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
    kind: TILE_KIND_RASTER,
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
      kind: s.kind === TILE_KIND_PMTILES ? TILE_KIND_PMTILES : TILE_KIND_RASTER,
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

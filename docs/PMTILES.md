# 离线底图（PMTiles）

室外视图默认走 OpenStreetMap 栅格瓦片，需要联网。现场无外网时切到
`outdoor.tileSources` 里 `kind: "pmtiles"` 的源，读一个本地 `.pmtiles`
归档（protomaps-leaflet 通过 HTTP Range 请求按需取块，不解压全量）。

## 1. 装 pmtiles CLI

```bash
# macOS
brew install protomaps/tap/pmtiles
# 或直接下载 release 二进制
# https://github.com/protomaps/go-pmtiles/releases
```

## 2. 按 bbox 提取

**不要下载全球包再切**。`pmtiles extract` 直接对远端归档发 Range 请求，
只拉目标 bbox 的块：

```bash
pmtiles extract \
  https://build.protomaps.com/20240401.pmtiles \
  data/pmtiles/demo.pmtiles \
  --bbox=113.9310,22.5230,113.9450,22.5330 \
  --maxzoom=18
```

`--bbox` 是 `west,south,east,north`（WGS84 十进制度）。
上面这组是深圳一个约 1.4 km × 1.1 km 的示例范围，产物几 MB。
换成自己站点的范围时，先按平面图配准原点向外扩 1–2 km。

校验：

```bash
pmtiles show data/pmtiles/demo.pmtiles
```

## 3. 挂载

`docker-compose.yml` 已经把 `./data/pmtiles` 只读挂到
`/app/uploads/pmtiles`，复用 FastAPI 的 `StaticFiles(/uploads)` 与
nginx 的 `location /uploads`，不需要额外的 web 服务。

前端 `web/src/config/outdoor.js` 预置的 `pmtiles-offline` 源指向
`/uploads/pmtiles/demo.pmtiles`。文件名不同就改这个 URL，或在
`dashboard_config.json` 的 `outdoor.tileSources` 里覆盖。

归档缺失时 `OutdoorMapView` 会打一条 console 错误并回落到栅格源。

## 4. 署名

PMTiles 底图的数据仍然来自 OpenStreetMap，按 ODbL 必须显示
`© OpenStreetMap contributors` 并链接到
<https://www.openstreetmap.org/copyright>。`OSM_ATTRIBUTION`
（`web/src/config/outdoor.js`、`server/models.py`）已经带上这个链接，
两类底图共用。

## 5. 本仓库的现状

`data/pmtiles/demo.pmtiles` **没有**入库（`.gitignore` 排除 `*.pmtiles`）：
构建环境无法访问 `build.protomaps.com`，本次实施未真实生成该文件，
目录里只放了说明与占位。按上面的命令在有外网的机器上跑一次即可。

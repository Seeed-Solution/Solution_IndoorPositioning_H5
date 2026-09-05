# B4 第三批：室内平面图与室外地图配准 spec

来源：codex 设计 2026-09-05，主线程评审通过。项目 `~/project/solution-indoor-positioning` 分支 `feature/outdoor`（在第二批 17 commit 之上）。用户需求：加室外前要把导入的平面图与室外地图关联，能拖动、缩放、旋转对齐。

## 1. 数据模型

地图持久化在 `dashboard_config.json`，加载/保存直接读写 JSON（`server/config/config_manager.py:13-16,26-38,75-88`）；DB 无地图表，迁移器只处理 SQLite `*.sql`（`server/migrations/migrate.py:77-99`）。**不建 002 迁移、不加 DB 列**。`WebUIMapInfo` 加可选 `registration:{origin_lat, origin_lon, rotation_deg, scale}`（`server/models.py:54-62`）。缺失即纯室内模式；配置序列化保留该对象，避免白名单丢字段（`web/src/views/ConfigurationSuiteView.vue:1668-1693`）。

## 2. 共享转换模块

`server/geo/affine.py` 与 `web/src/utils/affine.js`。平面图 +Y 顺时针偏离北方为 θ，`k = scale/scale0`（scale0 由地图米宽高与图片像素推导）：`E = k(x cosθ + y sinθ)`，`N = k(−x sinθ + y cosθ)`；`lat = lat0 + N/M0`，`lon = lon0 + E/(N0 cos lat0)`（WGS84 原点曲率半径），逆向用转置。与现有米制、Y 向上一致（`MapPreview.vue:319-367,415-425`）。两端读同一 fixture：四角、往返、旋转、非零边界（`server/models.py:896-917`）。半径 ≤2 km、|纬度| ≤60° 误差上界 0.7 m；极区拒绝配准。

## 3. UI

Leaflet 固定 1.9.4，锁定 `leaflet-distortableimage@0.21.9`（MIT）、`protomaps-leaflet@5.1.0`（`web/package.json:15-20`）。`OutdoorMapView` 加配准模式：以当前视图中心、图片 naturalWidth/Height、地图米数生成初值，加载既有 background（`MapPreview.vue:556-592`）；只开放 drag/rotate/scale，禁用 distort/freeRotate，锁宽高比；侧栏三参数 + 保存/取消/重置。`MapOverview` 传 maps 与全量 trackers；保存后按历史点 `map` 投影 metric 段与实时 x/y，与 WGS84 段同图、跨段不连线（`trail.js:41-75`；`MapOverview.vue:406-433`）。`MapPreview` 保持纯室内 Canvas（`MapOverview.vue:82-95`）。

## 4. 服务端

新增 `GET/PUT /api/configuration/dashboard/maps/{mapName}/registration`，校验经纬度、有限数、`scale>0`，写回同一 JSON/cache；保留整配置 API（`server/main.py:1236-1260`）。`tracker_update` 不加投影字段：GNSS 与 metric 历史已分开（`position_resolve_handler.py:122-138,320-326`），客户端投影避免双真相源；迟滞无需改（`indoor_outdoor.py:104-118`）。

## 5. 离线底图

`outdoor.js` 加 `raster | pmtiles` 开关；OSM 保持 WGS84，高德/天地图 disabled 占位（`outdoor.js:7-37,45-61`）。`pmtiles extract SOURCE data/pmtiles/demo.pmtiles --bbox=w,s,e,n --maxzoom=18`；compose 只读挂载到 `/app/uploads/pmtiles`，复用 StaticFiles 与 nginx `/uploads`（`server/main.py:80-97`；`nginx.conf:32-38`）。界面显示并链接 "© OpenStreetMap contributors"（ODbL）。

## 6. 评估

fixture 四角：Python/JS 差 ≤1e-9°、往返 ≤1 mm、2 km 内相对 WGS84 测地线 ≤0.7 m。UI 验收：初猜、三种操作、取消/重置、保存刷新、实时点、混合轨迹。`evaluation/README.md` 补参数、图像尺寸、步骤、截图、误差表（现只有容量/频率/告警/离线：`README.md:71-105`）。

## 7. 工作量与提交

6–8 人日：模型/API 1、双端公式与测试 1.5、编辑器 2、统一渲染 1、离线与评估 1.5。风险：上传归一化 EXIF 方向（`server/main.py:1267-1296`）、大图像素上限与预览、0/90/−90° 测试锁旋转符号。六个 commit：依赖底图、模型 API、转换、编辑器、统一轨迹、离线评估。

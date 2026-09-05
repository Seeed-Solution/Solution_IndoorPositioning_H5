# 2026-09-05 平面图配准（B4 第三批）

目的：核对「平面图米制坐标 ↔ WGS84」双端实现的一致性与误差，
并走通一遍「上传平面图 → 配准 → 保存 → 刷新后仍在」。

**这不是性能测试**，`evaluation/README.md` 里定义的容量 / 更新频率 /
告警时延 / 离线时延四个指标一个都没测。

## 环境

| 项 | 值 |
| --- | --- |
| 主机 | macOS (Darwin 25.5.0), Apple Silicon |
| 分支 / commit | `feature/outdoor`，第三批 commit 1–5 之上 |
| Server | `uv run uvicorn server.main:app --host 127.0.0.1 --port 8022` |
| 前端 | `npm run build:local` 产物，`npx vite preview --port 4173` |
| 浏览器 | playwright-cli 0.0.65（headless Chrome） |
| 底图 | OpenStreetMap 栅格瓦片（在线）；PMTiles 离线源未测，归档未生成 |
| 平面图 | `raw/georef_floorplan.png`，1000×800 px，合成图 |
| 地图配置 | 临时地图 `Georef Demo`，50 m × 40 m，`minX/minY = 0` |
| MQTT | 未启动。没有设备上行，实时点与混合轨迹**未验证** |

配置改动跑完已还原：`server/config/json/dashboard_config.json` 从
`raw/dashboard_config.before.json` 复制回去，临时地图与上传的图片已删除。

## 1. 投影精度

```bash
uv run python evaluation/georef_precision.py --json raw/precision.json
```

脚本读 `tests/fixtures/georef/cases.json`（Python 与 JS 的单元测试读的是同一份），
分别跑 `server/geo/affine.py` 与 `web/src/utils/affine.js`（node 直接 import ESM，
不经打包），三列分别是双端差、往返误差、相对 Vincenty 测地线的偏差。
原始输出 `raw/precision.txt`。

| case | lat0 | rot(°) | scale | Python vs JS (°) | 往返 (m) | 相对测地线 (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| corners_rot0 | 22.5231 | 0.00 | 1.0000 | 0.000e+00 | 3.958e-10 | 0.0001 |
| corners_rot90 | 22.5231 | 90.00 | 1.0000 | 0.000e+00 | 6.182e-10 | 0.0000 |
| corners_rot_minus90 | 22.5231 | -90.00 | 1.0000 | 0.000e+00 | 6.182e-10 | 0.0000 |
| corners_rot180 | 22.5231 | 180.00 | 1.0000 | 0.000e+00 | 3.958e-10 | 0.0001 |
| corners_rot17_5_scaled | 22.5231 | 17.50 | 1.0234 | 0.000e+00 | 6.912e-10 | 0.0000 |
| nonzero_bounds | 22.5231 | 33.00 | 0.8700 | 0.000e+00 | 7.511e-10 | 0.0000 |
| southern_western | -33.8688 | -12.25 | 1.0000 | 0.000e+00 | 6.251e-10 | 0.0001 |
| equator | 0.0000 | 45.00 | 2.0000 | 2.711e-20 | 3.553e-15 | 0.0000 |
| high_lat_60 | 60.0000 | 7.00 | 1.0000 | 0.000e+00 | 3.777e-10 | 0.0002 |
| radius_2km | 22.5231 | 0.00 | 1.0000 | 0.000e+00 | 7.306e-10 | 0.0452 |

| 指标 | 实测最差 | 预算 |
| --- | ---: | ---: |
| Python vs JS | 2.711e-20 ° | 1e-9 ° |
| 往返 | 7.511e-10 m | 1e-3 m |
| 相对测地线（≤2 km，\|lat\|≤60） | 0.0452 m | 0.7 m |

单元测试里另有一组按方位角扫描的核对（`server/tests/test_geo_affine.py`
的 `test_two_km_stays_within_the_documented_error_bound`）：
lat0 = 0 / 22.5231 / 45 / 60，方位角每 15°、半径 500/1000/2000 m，
最差 0.2028 m（出现在 lat0 = 60、方位角 60°、2 km）。

`radius_2km` 那行只沿 ±X/±Y 与 45° 取点，所以数字比扫描版小；
**2 km 内的误差上界按 0.21 m 记，不是 0.045 m**。

## 2. UI 走查

步骤（截图在 `raw/`）：

| 步骤 | 结果 | 截图 |
| --- | --- | --- |
| 室外视图，底图下拉含 OSM 与 Offline (PMTiles)，署名是可点击的 OSM 版权链接 | 通过 | `ui-01-outdoor-view.png` |
| 进入配准模式，选平面图，初猜按视图中心 + 正北 + scale 1 | 通过 | `ui-02-registration-initial.png` |
| 侧栏填 22.5231 / 113.9312 / 17.5° / 1.25，图片跟随移动、旋转、等比缩放 | 通过 | `ui-03-registration-params.png` |
| 保存 → "Registration saved." | 通过 | `ui-04-registration-saved.png` |
| 浏览器刷新，重新进配准模式选同一张图，三参数仍是保存值 | 通过 | `ui-05-after-reload.png` |

上传用的是 `POST /api/upload`（curl），不是配置页的上传控件：
本次只自动化了配准这一段，配置页的上传/裁剪流程未走。

访问控制：guest 会话 PUT registration 返回 403（`guest has been deny to access
interface: /api/configuration/dashboard/maps/Georef Demo/registration`），
换 admin 登录后成功。

**未验证**：实时 x/y 投影、metric 与 wgs84 混合轨迹在同一张图上的画法、
取消/重置按钮、PMTiles 离线底图。没有设备上行，也没有生成 PMTiles 归档。

## 3. API 与落盘

原始响应见 `raw/api_registration.txt`：

- `PUT .../maps/Georef%20Demo/registration` → 200，回显四个参数
- `GET` 同一路径 → `{"origin_lat":22.5231,"origin_lon":113.9312,"rotation_deg":17.5,"scale":1.25}`
- `origin_lat=89` → 422 `georeferencing is refused above |lat| 85.0 deg`
- `scale=0` → 422 `scale must be > 0`
- 不存在的地图 → 404
- 浏览器刷新之后，`dashboard_config.json` 里 `maps[].map.registration` 仍在

## 4. 已知问题

- `leaflet-distortableimage` 发布的 `dist/leaflet.distortableimage.js` 带
  webpack dev-server 的 HMR 客户端，运行时会反复尝试连 `ws://localhost:8081/ws`
  并在 console 报 `ERR_CONNECTION_REFUSED`。只是噪音，不影响功能，
  上游 0.21.9 的产物如此。
- 插件是 UMD，只往全局 `L` 上挂 `DragAction/RotateAction/ScaleAction`；
  Leaflet 走 ESM import 时 `window.L` 不存在，必须先赋值，
  且要先加载 `dist/vendor.js`（提供 `L.Toolbar2`），否则主 bundle 模块求值就抛错。
- 插件的 rotate/scale 句柄要读图片元素的 `matrix3d` transform，
  图片还没渲染就调 `setMode` 会抛 `reading 'slice'`；
  已改成等 overlay 的 `load` 事件之后再切模式。

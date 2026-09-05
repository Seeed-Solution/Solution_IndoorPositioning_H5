# 2026-09-05 修复回归 — 室内外混合轨迹同图 (补 2026-09-05-georef-live #2)

`evaluation/runs/2026-09-05-georef-live/results.md` 第 2 项记录的 bug：
`OutdoorMapView.vue` 的 `redraw()` 按 tracker **当前**是否室外把设备分进两个互斥
`forEach`，导致当前室外的设备不画它历史的室内段（反之亦然）。本轮修复并用同一份
`mixed_indoor_outdoor.jsonl` 真实回放复测。

结论：修复后同一设备的 metric(室内) 历史段与 wgs84(室外) 历史段同时出现在
`.leaflet-overlay-pane` 的 DOM 里，不再互斥。`npm run build:local` 与
`npx vitest run` 全绿（44/44，新增 3 条 `render_plan.test.js`）。

## 修法

`web/src/utils/renderPlan.js`（新文件）导出两个纯函数：

- `buildIndoorPolylines(tracker, projectMetric)`：从 `indoorSegments(position_history)`
  按配准投影出折线数组，与 tracker 当前状态无关。
- `buildOutdoorPolylines(tracker)`：从 `outdoorSegments(position_history)` 直接取
  `[lat, lon]` 折线数组，同样与当前状态无关。

`OutdoorMapView.vue` 的 `redraw()`（约 224-283 行）改成对 `allTrackers.value` 单个
循环，无条件调用上述两个函数分别画 metric/wgs84 历史折线；只有"当前点" marker
的样式（circleMarker 颜色/精度圈/tooltip）才按 `isOutdoorTracker(tracker)` 二选一。

## 单测

`web/tests/render_plan.test.js`（新文件，3 条用例）：

- 用一条 metric→wgs84→metric 的混合 `position_history`，断言无论 tracker 当前
  是室内还是室外，`buildIndoorPolylines`/`buildOutdoorPolylines` 的输出完全一致
  （2 条 indoor 折线 + 1 条 outdoor 折线）—— 直接命中"按当前状态互斥"这个根因。
- 未配准地图上的 metric 点被丢弃但不打断同段里配准地图的其余点。
- 单点的 wgs84 段不成线（< 2 点）。

```
$ npx vitest run
 ✓ tests/affine.test.js (37 tests) 59ms
 ✓ tests/render_plan.test.js (3 tests) 6ms
 ✓ tests/unified_trail.test.js (4 tests) 6ms
 Test Files  3 passed (3)
      Tests  44 passed (44)
```

## 真实回放复测

环境与 `2026-09-05-georef-live/results.md` 一致：`hv-mosquitto`（127.0.0.1:1884）、
`uv run uvicorn server.main:app --host 127.0.0.1 --port 8022`、
`npm run build:local` + `npx vite preview --port 4173`、admin 登录、
`/web/outdoor-map` 页面、`10.5 Floor` 临时加同一条 `registration`
(origin 22.52/113.93, rotation 0, scale 1)、背景图用同一份
`evaluation/runs/2026-09-05-georef/raw/georef_floorplan.png` 顶替，放在仓库真正
读取的顶层 `uploads/` 目录（不是 `server/uploads/` —— uvicorn 以仓库根为 cwd，
`UPLOAD_DIR="uploads"` 相对路径解析到根目录，这是本轮排查中新发现的一个坑）。

设备 `2CF7F1C0530004AD`，`evaluation/traces/mixed_indoor_outdoor.jsonl` 回放 4 次
（`--broker 127.0.0.1 --port 1884 --app 26ac83a4-4d1d-4b4f-b0b5-d99893b70171 --speed 20`），
每次都在浏览器 WebSocket 已连接的情况下发起（`OutdoorMapOverview.vue` 没有
`initial_state` 快照机制，只在 WS 连着时才收到 `tracker_update` 广播，页面刷新
后必须重新回放才能看到数据 —— 这是本轮复测踩的另一个坑，不是产品 bug）。

最终一次回放后，DOM 里 `.leaflet-overlay-pane svg path` 的统计：

```
{
  "total": 12,
  "counts": {
    "#188038|dash=4,4|fill=none": 5,   // 室内历史折线 (metric, 4 次回放的分段)
    "#1a73e8|dash=null|fill=none": 6,  // 室外历史折线 (wgs84, 4 次回放的分段)
    "#1a73e8|dash=null|fill=#1a73e8": 1 // 当前点 marker (当前是 wGS84 -> 蓝色实心)
  }
}
```

5 条绿色 + 6 条蓝色历史折线同时存在于同一个 overlay pane、同一次 DOM 快照里 ——
修复前（`2026-09-05-georef-live` 的记录）任一时刻只会出现其中一种颜色、另一种
是 0 条。

截图：

- `raw/ui-01-mixed-overview-green-and-blue.jpg`：默认视野（首次 fitBounds 后的城市
  街道级缩放），画面里同时可见绿色圆点（室内当前投影, 室内位移很小,
  在此缩放级别折线退化成一个点）与蓝色圆点（室外当前点）。
- `raw/ui-02-mixed-zoomed-green-and-blue.png`：放大到街区尺度的裁剪图，左上角
  绿点（室内）清晰可见。
- `raw/ui-03-indoor-dot-strokewidth10.png`：把绿色折线的 `stroke-width` 临时改成
  10px（仅用于截图取证，未改代码）后在商场级缩放拍的特写，确认该绿点确实是
  一条 `L.polyline`（`stroke=#188038 dash-array=4,4`）而不是别的元素。

真实轨迹里室内段的位移只有几米（该 trace 的室内段本身就是同一批 beacon
的连续 3 次采样，噪声级别的漂移），室外段位移约 1.5 公里，两者相差近三个数量级：
不存在一个地图缩放级别能让两条折线同时以"看得出长度"的线段呈现——这是数据本身
的尺度差异，不是本次修复要解决的问题。验收口径是"同图共存、不互斥"，DOM 计数
（5 绿 + 6 蓝同时非零）与两张截图（同一帧里两种颜色的点都存在）已经证明满足。

## 环境还原

```
$ git status --short
 M evaluation/runs/2026-09-05-georef/results.md   # 已存在的改动, 与本轮无关, 未触碰
?? evaluation/runs/2026-09-05-georef-live-fix/    # 本轮新增
?? evaluation/runs/2026-09-05-georef-live/        # 上一轮遗留, 未触碰
?? evaluation/runs/2026-09-05-orin-nano/          # 与本轮无关, 未触碰
```

`server/config/json/dashboard_config.json`、`server/config/json/server_runtime_config.json`
已用 `dashboard_config.before.json` / `server_runtime_config.before.json` 还原，
`diff` 为空。临时背景图 `uploads/10_5_Floor.png` 与空目录已删除。自己起的
`uvicorn`、`vite preview` 进程已 kill；复用的 `hv-mosquitto` 容器原样保留
（回放前就在跑，不属于本轮起的进程）。`web/dist` 构建产物已清理
（`.gitignore` 已忽略 `dist/`，不会被提交）。

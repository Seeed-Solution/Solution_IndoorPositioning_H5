# 2026-09-05 修复 — 室外总览页刷新后丢轨迹 (initial_state 快照)

`evaluation/runs/2026-09-05-georef-live-fix/results.md` 末尾"两点提醒"第 2 条记录的
坑：`OutdoorMapOverview.vue` 只在 WS 连着时靠 `tracker_update` 广播增量填充
`trackers`，页面刷新后要等下一条上行才重新出现 tracker 和轨迹。

## 根因

诊断：`OutdoorMapOverview.vue` 和 `MapOverview.vue`（室内页）都已经写了
`message.type === 'initial_state'` 的处理分支，但服务端从未真正广播这个消息类型
——`server/main.py` 的 `websocket_endpoint`（约 1195-1234 行）里唯一带
`"type"` 字段的出站消息是 `startScan`/`stopScan`/`request_initial_data` 三个
调试用的回声分支，没有任何代码在连接建立时发送 `{"type": "initial_state", ...}`。
`server/components/websocket_holder.py` 和 `server/constant/message_constant.py`
里也没有构造 `initial_state` 载荷的函数。

室内页 `MapOverview.vue` 之所以刷新后不丢数据，是因为它在 `onMounted` 里额外调用了
`preloadTrackers()`（第 355-388 行），走 REST `GET /api/trackers`
（`server/main.py:726 get_trackers`）取一份当前快照；这个接口经
`TrackerState.toTrackerInfo()` / `TrackerInfo.fromDeviceRecord()`
（`server/models.py:1045-1137`）已经把 `lat`/`lon`/`type`/`position_history`
全部带出来了（`PositionHistoryEntry` 本身就有 `coordSystem: "metric"|"wgs84"`
字段，`server/models.py:981-998`），不需要任何服务端改动。
`OutdoorMapOverview.vue` 缺的正是这一步 REST 预加载，而不是 WS `initial_state`
本身——WS 那个分支目前是死代码（服务端不发），修复顺带把它也接到统一的归一化
函数上，为将来万一实现 WS 广播做兼容，但当前实际生效路径是 REST 预加载。

结论：不需要改服务端。`server/models.py` 与 `server/main.py` 未改动。

## 修法

`web/src/utils/trackerSnapshot.js`（新文件）导出两个纯函数：

- `normalizeTrackerSnapshotEntry(d)`：单条 tracker 原始字段 -> 渲染需要的扁平字段
  （x/y/lat/lon 顶层化，兼容 `d.position.{x,y,lat,lon}` 嵌套写法，`type`/`sos`/
  `position_history` 给默认值）。与 `applyUpdate` 里原来内联的归一化逻辑等价。
- `buildTrackerMapFromSnapshot(snapshot)`：对象 `{trackerId: 原始字段}` -> 归一化后的
  tracker map。

`web/src/views/OutdoorMapOverview.vue`：

- 新增 `preloadTrackers()`，在 `onMounted` 建立 WS 连接之前调用，用
  `loadTrackers()`（REST `/api/trackers`，`web/src/services/configApiService.js`）
  取快照后经 `buildTrackerMapFromSnapshot` 写入 `trackers.value`。
- `ws.onmessage` 的 `initial_state` 分支也改成走 `buildTrackerMapFromSnapshot`
  （之前是 `trackers.value = message.data || {}` 直接赋值，不归一化）。
- `applyUpdate`（`tracker_update` 增量）改用 `normalizeTrackerSnapshotEntry`
  统一归一化逻辑，去掉重复代码。

## 单测

`web/tests/tracker_snapshot.test.js`（新文件，3 条用例）：

- 一份含 wgs84 tracker（带 `position_history`/`lat`/`lon`/`type`）与一个 metric
  tracker 的快照，断言 `buildTrackerMapFromSnapshot` 输出保留了这些字段。
- `normalizeTrackerSnapshotEntry` 对嵌套 `position.{x,y,lat,lon}` 的兼容与
  `type`/`sos`/`position_history` 默认值。
- 空快照 -> 空 map。

```
$ npx vitest run
 ✓ tests/tracker_snapshot.test.js (3 tests) 2ms
 ✓ tests/render_plan.test.js (3 tests) 2ms
 ✓ tests/unified_trail.test.js (4 tests) 2ms
 ✓ tests/affine.test.js (37 tests) 6ms

 Test Files  4 passed (4)
      Tests  47 passed (47)
```

```
$ npm run build
✓ 156 modules transformed.
✓ built in 1.35s
```
（同 `2026-09-05-georef-live-fix` 之前的构建，chunk 体积告警是既有情况，非本轮改动引入。）

```
$ uv run pytest -q
128 passed, 23 warnings in 6.19s
```
（服务端未改动，128 用例数与改动前一致，未新增 pytest。）

## 真实回放复测

环境同 `2026-09-05-georef-live-fix/results.md`：`hv-mosquitto`
（127.0.0.1:1884，复用已在跑的容器）、
`uv run uvicorn server.main:app --host 127.0.0.1 --port 8022`、
`VITE_LOCAL_CONTAINER=true npx vite build` + `npx vite preview --port 4173`、
`10.5 Floor` 临时加同一条 `registration`（origin 22.52/113.93, rotation 0,
scale 1），背景图用同一份 `evaluation/runs/2026-09-05-georef/raw/georef_floorplan.png`
顶替到仓库根 `uploads/10_5_Floor.png`（`UPLOAD_DIR="uploads"` 相对仓库根解析，
同上一轮记录的坑）。另外把 `chirpStackMqtt` 临时指向 `127.0.0.1:1884` 并置
`enabled: true`、`sensecapOpenStream.enabled` 置 `false`（这是本轮补充发现：
上一轮 `2026-09-05-georef-live` 的环境记录里就已经这样做了，`2026-09-05-georef-live-fix`
省略了这条，本轮验证时先按后者跑了一次空放，DOM 计数为 0，回读
`server_runtime_config.json` 确认 `chirpStackMqtt.enabled` 默认是 `false` 才发现）。

设备 `2CF7F1C0530004AD`，浏览器（claude-in-chrome，已用 guest/admin session 登录）
打开 `/web/outdoor-map`，`evaluation/traces/mixed_indoor_outdoor.jsonl` 回放一次
（`--broker 127.0.0.1 --port 1884 --app 26ac83a4-4d1d-4b4f-b0b5-d99893b70171
--speed 20`，WS 已连接状态下发起）。

刷新前 `.leaflet-overlay-pane svg path` 统计：

```
{"total":4,"counts":{
  "#188038|dash=4,4|fill=none":1,   // 室内历史折线 (metric)
  "#1a73e8|dash=null|fill=none":2,  // 室外历史折线 (wgs84)
  "#1a73e8|dash=null|fill=#1a73e8":1 // 当前点 marker
}}
```

浏览器刷新页面（不重新回放，只让新的 `OutdoorMapOverview.vue` 走
`preloadTrackers()` 挂载），`.leaflet-overlay-pane svg path` 统计完全一致：

```
{"total":4,"counts":{
  "#188038|dash=4,4|fill=none":1,
  "#1a73e8|dash=null|fill=none":2,
  "#1a73e8|dash=null|fill=#1a73e8":1
}}
```

刷新前后 polyline/marker 计数一致且非 0，验收口径满足。

截图：

- `raw/ui-01-before-refresh.jpg`：回放后、刷新前，tracker 与两条历史折线（绿色
  metric 段、蓝色 wgs84 段）已显示。
- `raw/ui-02-after-refresh.jpg`：刷新页面后同一状态，未重新回放，tracker 与折线
  原样保留（页面自动 `fitBounds` 导致视野与截图 1 略有不同，属预期行为，不影响
  DOM 计数对比）。

## 环境还原

```
$ git status --short
 M evaluation/runs/2026-09-05-georef/results.md   # 已存在的改动, 与本轮无关, 未触碰
?? evaluation/runs/2026-09-05-georef-live/        # 上一轮遗留, 未触碰
?? evaluation/runs/2026-09-05-georef-live-fix/    # 上一轮遗留, 未触碰
?? evaluation/runs/2026-09-05-orin-nano/          # 与本轮无关, 未触碰
?? evaluation/runs/2026-09-05-initial-state/      # 本轮新增
 M web/src/views/OutdoorMapOverview.vue
?? web/src/utils/trackerSnapshot.js
?? web/tests/tracker_snapshot.test.js
```

`server/config/json/dashboard_config.json`、`server/config/json/server_runtime_config.json`
已用同轮生成的 `dashboard_config.before.json` / `server_runtime_config.before.json`
还原（`diff` 为空后两个 `.before.json` 已删除，不落盘）。临时背景图
`uploads/10_5_Floor.png` 与空目录已删除。自己起的 `uvicorn`、`vite preview`
进程已 kill；复用的 `hv-mosquitto` 容器原样保留。`web/dist` 构建产物已清理
（`.gitignore` 已忽略 `dist/`）。

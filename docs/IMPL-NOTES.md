# B4 第一批实施记录（步骤 1、2、4、5）

spec：`docs/SPEC-outdoor.md`（复制自 seeed-solutions-hub
`docs/specs/b4-outdoor-positioning-spec.md`）。
分支 `feature/outdoor`，基线 `origin/feature/v2025110800_map_image`。
**步骤 3（地理围栏引擎）本批不做**，但步骤 4 的迁移已把围栏表与
`event_triggers` 的新列建好，围栏表为空表。

## spec 未覆盖、本批自行取的最小选择

### 1. `accuracy` / `alt` 没有数据源

spec 要求 `TrackerState`/`TrackerInfo` 新增 `accuracy`、`alt`，
但 SenseCAP/ChirpStack 的 measurementId 里没有对应测点：
4197 是经度、4198 是纬度，两者都不带精度。

取法：字段建出来、贯通到 WebSocket 载荷，值恒为 `null`，
`extract_gnss_fix()` 只在 `loc` 里显式带了 `alt`/`accuracy` 时才填。
接入新的测点后不用改结构。

### 2. `position_history` 的兼容读法

spec 说「旧三元组按 metric 读取」，没说读在哪一层。
取法：放在 pydantic 的 `field_validator(mode="before")`
（`server/models.py` 的 `normalize_position_history`），
`TrackerState` 与 `TrackerInfo` 各挂一个。
前端 `web/src/utils/trail.js` 的 `normalizeHistoryEntry` 做同样的兼容，
两端都能吃旧数据。

### 3. 历史条目的时间取值

用上行时间戳（`report.timestamp`），缺失时回落到服务端当前时间。
排序与 30 min 裁剪都按这个时间。metric 段额外记 `map`。

### 4. BLE 早退分支不带历史

`resolve_ble()` 的几个早退分支（找不到有效 beacon、地图配置缺失、
区域定位未启用）返回的 `TrackerState` 没有 `position_history`。
如果直接往上面追加 GNSS 点，会把整条轨迹清空。
取法：`do()` 里发现 `position_history` 为空就从 `device_holder`
的上一次状态补齐，再追加。

### 5. 展示类型的判定

spec 明说第一批按「有有效 GPS fix 则 wgs84」简化，
迟滞状态机在步骤 3。实现落在 `position_resolve_handler.do()` 末尾，
以及 `message_format_hanlder.resolve_loc_type()`，两处都留了注释指向步骤 3。

### 6. 室外底图源清单

spec 只要求「默认 OSM，瓦片 URL、署名、坐标制配置化」，
没有给具体源。取法：后端 `DEFAULT_OUTDOOR_TILE_SOURCES` 只放 OSM 一条
（保证零配置可用），前端 `web/src/config/outdoor.js` 额外预置了
高德与天地图两条模板并标 `gcj02Correction=true`，
天地图的 URL 留了 `YOUR_TIANDITU_KEY` 占位。本期不实现偏移算法，
只在 UI 上提示坐标系不一致。

### 7. 室内外分流的入口

spec 说「MapOverview 按 tracker.type=wGS84 路由室外」。
取法：地图下拉多一个室外条目（`selectedMapIndex === -1`），
选中时渲染 `OutdoorMapView`，全屏模式同样生效；
`getTrackersForMap()` 把室外设备排除掉，避免同一个设备两边都画。
另外加了一个独立路由 `/outdoor-map`（`views/OutdoorMapOverview.vue`），
只订阅同一条 WebSocket，方便单独投屏。

### 8. 迁移执行方式

spec 只说「显式 SQL 迁移，不能依赖只会 create_all 的 DAO 初始化」。
取法：`server/migrations/*.sql` + `migrate.py` 执行器，
台账表 `schema_migrations` 记录已执行的文件名；
语句级幂等靠 `IF NOT EXISTS` 和忽略 `duplicate column name`。
**没有挂到服务启动流程上**，需要手工跑：

```bash
uv run python -m server.migrations.migrate --db db/app.db
```

理由：启动时自动改库属于部署策略，spec 没要求，也没有回滚方案。

### 9. 告警表的 loc/desc

spec 要求「告警表 loc/desc JSON 直接写 lat/lon/coordSystem/fence_id/transition，
旧 x/y 继续读」。这两列本来就是 JSON 列（`device_alarm_record_dao.py:17,23`），
不需要 DDL 变更；实际写入这些键的是 `event_consumer` 的围栏判定，属于步骤 3。
本批只保证结构上不阻塞。

### 10. 脱敏 fixture 的字段依据

`server/tests/fixtures/uplinks/*.json` 的字段布局对着解析器本身构造：

- SenseCAP：`parse_sensecap_payload()` 读 topic 的第 3 段为 devEUI、
  第 6 段为 measurementId，payload 取 `value` 与 `timestamp`；
  只有收到 3000 才汇总成一个 TrackerReport。
- ChirpStack：`parse_chirpstack_payload()` 读
  `object.messages[0]` 的 `{measurementId, measurementValue, timestamp}` 列表。

devEUI、applicationID、网关信息、beacon MAC 全部换成合成值。
文件头的 `_comment` 里写了这些依据。

## 顺带修掉的基线问题

- `web/src/services/userStore.js` 从未入库，`App.vue` 与 `authService.js`
  都 import 它，基线分支上 `npm run build` 直接失败。按调用点签名补了最小实现。
- `pyproject.toml` 的 dependencies 漏了 `requests` / `httpx`
  （`server/requirements.txt` 里有），`uv run uvicorn server.main:app` 起不来。

这两条都是独立 commit。

## 验证

- `uv run pytest`：27 passed。
- `npm run build`：通过。
- 迁移脚本对一个旧 sqlite 文件跑通并可重复执行，见
  `evaluation/runs/2026-09-05-smoke/raw/migration_dry_run.txt`。
- 端到端冒烟见 `evaluation/runs/2026-09-05-smoke/summary.md`。

## 留给步骤 3 的接口

- `message_format_hanlder.resolve_loc_type()` — 换成迟滞状态机的入口。
- `position_resolve_handler.do()` 末尾的 `state.type` 赋值 — 同上。
- `geofences` 表与 `event_triggers.geofence_id/location_mode/transition`
  已建好，需要补 `GeofenceDao` 与 ORM 列定义。
- `PositionHistoryEntry` 已带 `coordSystem`，围栏判定可以直接吃这条轨迹。

---

# B4 第二批实施记录（步骤 3）

分支 `feature/outdoor`，接在第一批的 `6c9a70d` 之后。
迁移 `001_outdoor_geofence.sql` 建好的 `geofences` 表与 `event_triggers`
的三列直接用，没有新增迁移。

## spec 未覆盖、本批自行取的最小选择

### 11. 围栏首次观测不产生告警

spec 只说「连续 3 点且持续 10 s 才切换」，没说初始状态怎么来。
取法：`FenceHysteresis.state` 初值为 `None`，第一个点只落地
inside/outside，不产出 transition。否则服务重启后，
第一个落在围栏内的上行会立刻补一条 enter 告警。

### 12. 精度缓冲带的判据

spec 说「精度缓冲带内保持原状态」，没给带宽定义。
取法：点到围栏边界的距离 < 该点的 `accuracy` 时视为不可信，
保持原状态且不推进 pending 计数（`Geofence.distance_to_boundary_m`）。
多边形的度→米换算按当前纬度近似（`server/geofence.py`）。
`accuracy` 为 `None` 时这条分支整个跳过——没有误差就没有缓冲带。

### 13. 围栏的精度门槛

任务书要求「accuracy 为 null 时视为通过精度门槛并在日志标注」，
但没给门槛值。取法：复用室内外迟滞的 25 m
（`DEFAULT_FENCE_ACCURACY_MAX_M`），超过就丢点。

### 14. geo 模式下 position_detection 不走 time_range

BLE 模式的 position_detection 有一套 `device_leaving_event_checker`
的延时确认（`alarm_setting.time_range` 分钟）。
geo 模式没有复用它：围栏滞回本身已经带「连续 3 点 + 10 s」的确认，
再叠一层延时会让语义变成两个不同量纲的等待。
所以 geo 模式下 checkin 与 position_detection 走同一个
`consume_geo_event()`，只由 `transition` 区分方向。
副作用：geo 模式的告警不受 `time_range` 影响，UI 上那个输入框对
geo 模式无效。

### 15. 围栏告警的广播消息类型

没有新增 WebSocket 消息类型，enter 复用 `tracker_checkin`、
exit 复用 `tracker_position_detection`，额外带一个 `geofence` 段
（`message_constant.get_geofence_message()`）。
前端不用加分支，`ws_capture.py` 靠 `geofence` 段区分围栏告警与 BLE 告警。

### 16. 滞回状态的隔离粒度

围栏滞回按 `(dev_eui, event_id)` 隔离，不是按 `(dev_eui, fence_id)`。
同一个围栏被两条告警引用（比如一条只报 enter、一条只报 exit）时，
两条各自独立计数。围栏被改过之后 `geofence_holder.invalidate()` 清编译缓存。

### 17. 迟滞状态机还没定论时的回落

`DeviceHysteresis.mode` 初值为 `None`（证据还不够）。
这时 `apply_indoor_outdoor()` 回落到第一批的简化：有经纬度就 `wGS84`。
攒够证据之后由状态机接管。所以「设备刚上线的头两个 GNSS 包」
仍然是旧行为，第 3 个包起才是迟滞。

### 18. 「有效 BLE」的定义

spec 的「15 s 无有效 BLE」没定义什么算有效。
取法：`beacon_holder` 里能查到配置的信标才算
（`position_resolve_handler.count_configured_beacons()`）。
没配置过的广播包不能证明设备在室内。
转室内还额外要求单次 ≥ 2 个已配置信标。

### 19. `resolve_loc_type()` 保持逐包语义

第一批把它标成「步骤 3 的入口」。实际改法是不改它：
`TrackerReport.locType` 描述的是「这一包带了什么数据」，是逐包事实；
界面展示的室内/室外是 `TrackerState.type`，由迟滞状态机决定。
两者分开，只把注释写清楚。

### 20. 围栏几何的跨日界线处理

shapely 在平面 lon/lat 上算，跨 180° 的多边形会被当成横跨整个地球的巨型矩形。
取法：经度跨度 > 180° 时把所有经度归一化到 `[0, 360)`，
待测点同样归一化（`Geofence.wrap`）。圆形不受影响，Haversine 本来就绕球算。

### 21. 迟滞参数的配置入口

spec 说「默认参数可配置」，没说配在哪。
取法：`indoor_outdoor.HysteresisConfig` + 模块级 `configure(**kwargs)`，
默认值就是 spec 的值。**没有接到 `server_runtime_config.json`**——
接配置文件要改配置模型与前端表单，超出本批范围。

## 顺带修掉的问题

- `EventManager.create_event()` 没有透传 `geofence_id/location_mode/transition`，
  `/api/events` 建 geo 模式告警直接报
  `unexpected keyword argument 'geofence_id'`。冒烟时踩到，独立 commit。

## 验证

- `uv run pytest`：70 passed（第一批 27 + 本批 43）。
- `npm run build`：通过。
- 围栏冒烟见 `evaluation/runs/2026-09-05-geofence-smoke/results.md`：
  进出围栏 2 条告警、门口徘徊 6 次翻转 0 条告警、type 切换 0 次。

## 仍然留着的偏差

- `accuracy` 恒为 `null`（第一批第 1 条），所以精度门槛与精度缓冲带在真机数据上
  都是「恒通过」。接入精度测点之前，这两条路径只有单元测试覆盖。
- 迁移仍需手工执行，没挂到服务启动流程上（第一批第 8 条）。
- 高德/天地图的 GCJ-02 偏移仍未纠正；围栏在 GCJ-02 底图上画出来会存偏移，
  `crs` 字段记下了它是按哪套坐标画的，但判定时不做转换。

---

# B4 第三批实施记录（室内平面图与室外地图配准）

spec：`docs/SPEC-georeference.md`（复制自 seeed-solutions-hub
`docs/specs/b4-floorplan-georeference-spec.md`）。
分支 `feature/outdoor`，基线 `443bce6`。六个 commit，顺序同 spec §7。

## spec 未覆盖、本批自行取的最小选择

### 1. `scale` 的语义：直接存比值，不存 scale0

spec 写 `k = scale/scale0`（scale0 由地图米宽高与图片像素推导）。
如果按字面存 `scale`，转换函数就得同时知道图片像素尺寸才能算出 k，
后端与轨迹投影都拿不到这个信息。

取法：`MapRegistration.scale` **直接就是 k**，1.0 表示按地图米数原样贴图。
转换只依赖 `{origin_lat, origin_lon, rotation_deg, scale}` 四个数，
不需要图片尺寸。图片像素只在配准编辑器里用一次
（`imageFootprintLocal()` 决定背景图在局部米制坐标里的落位，
与 `MapPreview` 的等比居中画法一致）。

### 2. 极区阈值取 85°

spec 只说"极区拒绝配准"，没给数字。取 `GEOREF_POLAR_LIMIT_DEG = 85.0`，
三处保持同一个值：`server/models.py`、`server/geo/affine.py`、
`web/src/utils/affine.js`，fixture 里也记了一份用于交叉断言。

### 3. fixture 的期望值由 Python 生成

`tests/fixtures/georef/cases.json` 的 `expected` 是 `server/geo/affine.py`
算出来的，JS 侧断言差 ≤ 1e-9°。单看这一项是"两端读同一条曲线"，
不是独立验证。独立参照另加：`server/tests/vincenty_ref.py` 的 Vincenty 反算，
与被测实现无共享代码，用来核对 2 km 内相对测地线的偏差 ≤ 0.7 m。

### 4. registration 的 API 只覆盖单张地图

新增 `GET/PUT /api/configuration/dashboard/maps/{mapName}/registration`。
**没有 DELETE**：spec 没要求，清除配准目前只能改整份配置。
PUT 的校验完全由 `MapRegistration` 的 pydantic validator 承担，
非法输入返回 422（不是 400），这是 FastAPI 的默认行为。

### 5. `docker-compose.yml` 是新建的

仓库原本没有 compose 文件（只有 `Dockerfile*` + `release.sh`）。
spec 要求"compose 只读挂载 `data/pmtiles/`"，因此新建了一个最小的
`docker-compose.yml`，只做单服务 + 四个挂载，不改 `release.sh` 的构建链路。

### 6. `demo.pmtiles` 没有真的生成

`pmtiles extract` 要从 `build.protomaps.com` 拉源归档，本机取不到。
`data/pmtiles/` 只放了 README 占位，`.gitignore` 排除 `*.pmtiles`，
提取命令写在 `docs/PMTILES.md`。`pmtiles-offline` 这个底图源已经进了
前后端默认列表，归档缺失时 `OutdoorMapView` 打一条 console 错误
并回落到栅格源。**PMTiles 路径本批未实测。**

### 7. JS 测试框架选 vitest

仓库原本没有前端测试。加 `vitest@2.1.9`（devDependency）与
`npm test` / `npm test:watch`，用现成的 `vite.config.js`（`@` alias 直接可用）。

### 8. leaflet-distortableimage 的三个坑

插件是 UMD 产物，在 Vue + ESM Leaflet 下要按顺序做三件事，
否则模块求值期就抛错：

1. `window.L = L`——插件只往全局 `L` 上挂 `DragAction/RotateAction/ScaleAction`。
2. 先 `import 'leaflet-distortableimage/dist/vendor.js'`——它提供 `L.Toolbar2`，
   主 bundle 求值时就要用（`L.Toolbar2.Action` 未定义会报
   `Cannot read properties of undefined (reading 'Action')`）。
3. `editing.setMode()` 要等 overlay 的 `load` 事件——rotate/scale 句柄会读
   图片元素的 `matrix3d` transform，图片没渲染时报 `reading 'slice'`。

另外插件发布的 dist 里带 webpack dev-server 的 HMR 客户端，
运行时会反复连 `ws://localhost:8081/ws` 并在 console 报错。噪音，不影响功能。

### 9. 锁宽高比靠"不给 action"

不加 `DistortAction` 与 `FreeRotateAction`，只给 drag/rotate/scale，
四角就始终保持相似变换，宽高比自然锁死。因此
`registrationFromCorners()` 只用 BL→TL 一条边反解旋转与缩放，不做最小二乘。

### 10. 反解用 BL 作切点

`registrationFromCorners()` 以左下角为切平面锚点算 E/N，再把原点换回经纬度；
`local_to_wgs84` 用的锚点是配准原点。两者不是同一个切点，
平面图尺度（< 200 m）下差异在亚毫米量级，未做补偿。

### 11. 统一渲染里的断线规则

同一条 metric 段内如果 `map` 字段变了（跨平面图），也要断开——两张平面图
各有自己的配准，连起来没有意义。未配准的地图上的点一个都不画。
metric 与 wgs84 的跨段不连线沿用 `trail.js` 已有的切段逻辑，没改。

### 12. 室内点在室外图上的样式

实时点用空心绿圈 + 虚线边，历史段用绿色虚线，与 GNSS 的蓝色实心点 / 实线区分。
spec 没规定样式。

### 13. `pmtiles-offline` 也进了后端默认列表

spec §5 只说前端 `outdoor.js` 加开关。但 `dashboard_config.json` 一旦写过
`outdoor` 段，前端就用配置里的列表，前端默认值不再生效。
因此后端 `DEFAULT_OUTDOOR_TILE_SOURCES` 也加了这一条，
保证零配置时离线源可选。

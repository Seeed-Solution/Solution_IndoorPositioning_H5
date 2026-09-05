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

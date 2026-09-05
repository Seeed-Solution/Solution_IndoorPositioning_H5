# B4 室外定位扩展实施 spec

来源：codex 设计 2026-09-05，主线程评审通过。项目 `~/project/solution-indoor-positioning`，基线分支 `feature/v2025110800_map_image`，在其上开 `feature/outdoor` 分支实施。分两批派发：第一批步骤 1、2、4、5；第二批步骤 3。

## 步骤 1：后端定位数据修复（2 人日，中风险）

- SenseCAP 按协议 4197→`lon`、4198→`lat`，用 `is not None` 校验零坐标，`loc_type` 改为 `locType="gps"`；ChirpStack 同步改键名，要求经纬度完整，移除 GPS 提前返回，继续解析 beacon（`server/handler/message_format_hanlder.py:60-98,191-224,245-274`）。
- 纠正：`sos`、`battery` 是模型字段，只有 `loc_type` 不存在；模型未禁止额外字段，所以现状不一定抛 ValidationError，更可能保留默认 `locType="bluetooth"`（`server/models.py:480-490`）。
- `TrackerState`、`TrackerInfo` 新增可空 `lat/lon/alt/accuracy/fix_time`；历史由三元组改为含 `coordSystem=metric|wgs84`、地图、时间的对象，旧三元组按 `metric` 读取（`server/models.py:827-841,887-904`）。GPS 不再写入 `x/y`（现状 `x=alt,y=lon`：`server/handler/position_resolve_handler.py:33-45`）。
- 同包 GNSS+BLE 生成一个组合报告，分别解算并原子追加两类历史；当前展示类型由步骤 3 的迟滞状态机决定（第一批先按"有有效 GPS fix 则 wgs84"简化）。
- pytest：`server/tests/fixtures/uplinks/{sensecap,chirpstack}_gnss_ble.json` 真实脱敏上行，覆盖字段映射、零坐标、缺项、错误键名、双写、beacon 不丢失。

## 步骤 2：前端室外地图（4 人日，中风险）

- 安装 `leaflet@1.9.4`。基线无地图库，只有 Canvas `MapPreview`，不存在 `MapView.vue`（`web/package.json:15-24`；`web/src/components/MapPreview.vue:3-21,306-445`）。
- 新增 `OutdoorMapView.vue`，默认 OSM，瓦片 URL、署名、坐标制配置化；高德/天地图标记 `gcj02Correction=true`，本期不实现偏移算法。
- `MapOverview` 按 `tracker.type=wGS84` 路由室外，其余室内（类型定义 `server/constant/message_constant.py:19-23`）。
- 统一时间轴按时间排序、按坐标系切段：室内段 Canvas、室外段 Leaflet，切换点不连线（现历史仅 `[x,y,time]`：`MapPreview.vue:530-550`）。
- `get_tracker_update()` 的 `position` 与载荷加 `lat/lon/alt/accuracy/type`（`server/constant/message_constant.py:80-99`）；现只广播 BLE 的监听器要广播 WGS84（`server/handler/message_listen_handler.py:45-51`）。

## 步骤 3：地理围栏引擎（8 人日，高风险，第二批）

- 新增 `geofences` 表与 `GeofenceDao`：`id/name/geometry_json/crs/enabled/created_at`；多边形 GeoJSON Polygon/MultiPolygon，圆为 Point + `radius_m`。Polygon 用 Shapely prepared geometry `covers`，圆用 Haversine。
- `event_triggers` 加可空 `geofence_id`、`location_mode=ble|geo`、`transition=enter|exit|both`（现表只有 BLE 条件：`server/dao/event_trigger_dao.py:9-23`）。
- 接入 `single_event_consume()`：纠正——checkin 在 `used_beacons` 为空时返回，position_detection 查 `last_detected_beacons`，其"围栏"实为目标 MAC 白名单（`server/handler/event_consumer.py:88-117,151-193`）。`location_mode=geo` 时两者改为经纬度判定，不依赖 beacon。
- `AlarmSettings.vue` 加模式、GeoJSON/圆编辑器、进出方向，替代强制 beacon 选择（`AlarmSettings.vue:243-292,1251-1255`）。
- 默认迟滞：20 s 内连续 3 个 `accuracy≤25 m` GNSS fix 且 15 s 无有效 BLE → 室外；10 s 内连续两次、每次 ≥2 个已配置 BLE → 室内；围栏状态连续 3 点且持续 10 s 才切换，精度缓冲带内保持原状态。

## 步骤 4：配置与数据迁移（2 人日，中风险）

- `dashboard_config.json` 保留 `maps`，新增可选 `outdoor.tileSources/defaultSource`，缺失自动补 OSM，旧文件原样可读（`server/models.py:82-97`；`server/config/json/dashboard_config.json:1-14`）。
- 显式 SQL 迁移新增围栏表与触发器字段，不能依赖只会 `create_all` 的 DAO 初始化（`server/dao/base_dao.py:23-36`）。旧 alarm 行 `location_mode=ble`；告警表 `loc/desc` JSON 直接写 `lat/lon/coordSystem/fence_id/transition`，旧 `x/y` 继续读（`server/dao/device_alarm_record_dao.py:9-24`）。

## 步骤 5：评测（3 人日，中风险）

- `evaluation/replay_chirpstack.py` + `evaluation/traces/*.jsonl`，按 `application/{app}/device/{eui}/event/up` 回放或生成 `object.messages[0]` 的 GNSS+BLE 轨迹（解析：`message_format_hanlder.py:178-208`；MQTT 入口：`server/main.py:452-460`）。
- 指标定义：容量上限 = 持续 30 min、丢失率 ≤1%、端到端 P95 ≤2 s、CPU <80% 的最大标签数；更新频率 = 每标签每分钟成功定位数；SOS/围栏延迟 = 上行时间戳到告警入库并广播；离线延迟 = 最后上行到离线广播（基线阈值 15 min、轮询 60 s：`server/handler/offline_handler.py:25,50-89`）。
- 记录格式按 hub `templates/evaluation/boundary.schema.yaml`。

## 排除

T1000 下行参数配置、GNSS 工作模式与上报周期设置。

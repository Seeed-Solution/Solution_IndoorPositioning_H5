# 2026-09-05 围栏冒烟（步骤 3）

目的：验证「GNSS 上行 → 围栏判定 → 告警入库 + WebSocket 广播」在
「进出围栏 + 门口徘徊」轨迹下的行为，并统计围栏告警时延与展示类型切换次数。

**这不是性能测试**，没有跑满 30 min，也没有并发标签，
`evaluation/README.md` 里定义的四个指标一个都不算测到。

## 环境

| 项 | 值 |
| --- | --- |
| 主机 | macOS (Darwin 25.5.0), Apple Silicon |
| Broker | mosquitto 本机 `127.0.0.1:1883`，`allow_anonymous true` |
| Server | `uv run uvicorn server.main:app --host 127.0.0.1 --port 8022` |
| 分支 / commit | `feature/outdoor` @ `6276f7e` + 未提交的评测改动 |
| 运行时配置 | `chirpStackMqtt` 临时指向本机 broker、`enabled=true`；`sensecapOpenStream.enabled=false`。**跑完已还原** |
| 轨迹 | `evaluation/traces/geofence_dwell.jsonl`，17 条上行，`--speed 1`（96 s） |
| 围栏 | `raw/fence.json`：方形多边形 113.9420..113.9440 / 22.5350..22.5370 |
| 告警 | `event_type=3`（checkin）、`location_mode=geo`、`transition=both`、`ble_range=[]` |

## 步骤

```bash
mosquitto -c /tmp/mosq-gf.conf                     # listener 1883 127.0.0.1
uv run uvicorn server.main:app --host 127.0.0.1 --port 8022
curl -X POST /api/login                            # 取 session-token
curl -X POST /api/geofences -d @raw/fence.json     # -> id=1
curl -X POST /api/events -d '{... "location_mode":"geo","geofence_id":1,"transition":"both"}'
uv run --with websockets python evaluation/ws_capture.py --seconds 115 \
    --out evaluation/runs/2026-09-05-geofence-smoke/raw/ws.jsonl
uv run python evaluation/replay_chirpstack.py \
    --trace evaluation/traces/geofence_dwell.jsonl \
    --broker 127.0.0.1 --port 1883 --speed 1
```

回放脚本把上行时间戳写成 `发送基准 + t_offset_ms`，围栏滞回的「连续 3 点 + 10 s」
判据吃的就是这个时间戳，所以 `--speed` 只影响墙钟时长，不影响判据。

## 轨迹与期望

| t_offset | 位置 | 期望 |
| --- | --- | --- |
| 0 / 5 s / 10 s | 围栏外 | 初始状态落为 outside，不告警 |
| 15 / 21 / 27 s | 围栏内 | 第 3 点距 pending 起点 12 s → **enter** |
| 33 s | 围栏内 | 状态已是 inside，无事 |
| 40–70 s | 门口来回（22.53490 / 22.53510 交替，6 次） | 每次翻转都清 pending，**不告警** |
| 78 / 84 / 90 s | 围栏外 | 第 3 点距 pending 起点 12 s → **exit** |
| 96 s | 围栏外 | 无事 |

## 结果

`raw/ws_capture_summary.txt`：

```json
{"message_counts": {"tracker_update": 17, "tracker_checkin": 1, "tracker_position_detection": 1},
 "tracker_updates_with_gnss_fix": 17,
 "geofence_alarm_count": 2,
 "geofence_latency_ms_p50": 14, "geofence_latency_ms_max": 14,
 "type_switch_count": 0, "type_switches": [],
 "final_types": {"2CF7F1C0530004AD": "wGS84"}}
```

- **围栏告警 2 条**，方向与时刻都符合期望：
  enter 落在 `t_offset=27 s` 的上行，exit 落在 `t_offset=90 s` 的上行
  （两条上行时间戳相差 63 000 ms = 90 000 − 27 000）。
- **门口徘徊 6 次翻转产生 0 条告警**：滞回的 pending 计数每次被打断。
- **围栏告警时延 9 / 14 ms**（上行时间戳 → WebSocket 广播）。
  同机 loopback，只能说明链路无堆积，不是真实部署的时延实测值。
- **展示类型切换 0 次**：整条轨迹只有 GNSS、没有 BLE，迟滞状态机在
  第 3 个 fix 时判定 outdoor 并一直保持，`type` 全程 `wGS84`。
  这条轨迹不检验 indoor↔outdoor 的切换，那部分覆盖在
  `server/tests/test_indoor_outdoor.py`。

一条原始围栏告警 WebSocket 消息（`raw/ws.jsonl`）：

```json
{"recv_time_ms": 1788582647228, "message": {"type": "tracker_checkin", "data": {
  "2CF7F1C0530004AD": {"timestamp": 1788582647214, "map": "评测围栏-方形厂区",
  "geofence": {"id": 1, "name": "评测围栏-方形厂区", "transition": "enter"},
  "position": {"lat": 22.5362, "lon": 113.9432, "accuracy": null, "coordSystem": "wgs84"},
  "last_detected_beacons": []}}}}
```

对应的告警入库记录（`raw/alarm_records.json`）：

```json
{"id": 5, "dev_eui": "2CF7F1C0530004AD", "pos_type": "gps",
 "loc": {"lat": 22.5362, "lon": 113.9432, "coordSystem": "wgs84",
         "fence_id": 1, "transition": "enter"},
 "beacons": [], "event_type": 3, "event_id": 3,
 "desc": {"fence_id": 1, "fence_name": "评测围栏-方形厂区", "transition": "enter"}}
```

`beacons` 为空数组：geo 模式确实没有依赖 BLE。

## 已知偏差

- `accuracy` 仍全为 `null`（第一批已记录：SenseCAP/ChirpStack 没有精度测点）。
  围栏判定把 `null` 当作通过精度门槛，服务端日志逐条打印
  `geofence 1: accuracy 缺失, 按通过精度门槛处理`，见 `raw/server.log`。
  因此**精度缓冲带在这次冒烟里没有被触发**，只有单元测试覆盖。
- 围栏告警时延同机 loopback，不能外推到真实部署。
- 只跑了一个标签、一个围栏、一条轨迹，没有并发与长时运行。

## 原始输出

- `raw/ws.jsonl` — WebSocket 全量广播
- `raw/ws_capture_summary.txt` — 抓包统计（含围栏告警与 type 切换）
- `raw/fence.json` / `raw/fence_create.json` — 围栏定义与创建响应
- `raw/event_create.json` — geo 模式告警的创建响应
- `raw/alarm_records.json` — 告警入库记录
- `raw/server.log` — 服务端日志

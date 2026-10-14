# 2026-09-05 端到端冒烟

目的：验证「MQTT 上行 → 解析 → 定位解算 → WebSocket 广播」这条链路在
室外（GNSS）与进出楼混合轨迹下能跑通，并确认前端 build 产物可加载。

**这不是性能测试**，没有跑满 30 min，也没有并发标签，
`evaluation/README.md` 里定义的四个指标一个都不算测到。

## 环境

| 项 | 值 |
| --- | --- |
| 主机 | macOS (Darwin 25.5.0), Apple Silicon |
| Broker | mosquitto 本机 `127.0.0.1:1883`，`allow_anonymous true` |
| Server | `uv run uvicorn server.main:app --host 127.0.0.1 --port 8022` |
| 分支 / commit | `feature/outdoor` @ `9b1644e` |
| 运行时配置 | `chirpStackMqtt` 临时指向本机 broker、`enabled=true`；`sensecapOpenStream.enabled=false`。**跑完已还原** |
| 轨迹 | `evaluation/traces/mixed_indoor_outdoor.jsonl`，10 条上行，`--speed 8` |

## 步骤

```bash
mosquitto -c mosquitto.conf                       # listener 1883 127.0.0.1
uv run uvicorn server.main:app --host 127.0.0.1 --port 8022
uv run python evaluation/ws_capture.py --seconds 30 \
    --out evaluation/runs/2026-09-05-smoke/raw/ws.jsonl
uv run python evaluation/replay_chirpstack.py \
    --trace evaluation/traces/mixed_indoor_outdoor.jsonl \
    --broker 127.0.0.1 --port 1883 --speed 8
```

## 结果

回放 10 条上行，WebSocket 侧收到 10 条 `tracker_update` + 2 条 `tracker_sos`：

```json
{"message_counts": {"tracker_update": 10, "tracker_sos": 2},
 "tracker_updates_with_gnss_fix": 7,
 "latency_ms_count": 10, "latency_ms_p95": 1}
```

- 7 条带 `lat/lon`（轨迹里 GNSS 上行正好 7 条），3 条纯 BLE 上行走室内解算。
- 最后一条 `tracker_update` 的 `position_history` 坐标系序列：
  `wgs84 × 11 → metric × 3 → wgs84 × 3`，进出楼的切段在载荷里可见。
  （前 11 个 wgs84 点来自同一进程内的上一次回放，历史窗口 30 min 内不清。）
- `latency_ms_p95 = 1 ms`：回放脚本把上行时间戳写成发送时刻，
  broker、server、抓包客户端都在同一台机器上，这个数字只说明链路没有明显堆积，
  **不能当作端到端 P95 时延的实测值**。

一条原始 `tracker_update`（门口同包 GNSS+BLE，节选）：

```json
{"recv_time_ms": 1788581499095, "message": {"type": "tracker_update", "data": {
  "2CF7F1C0530004AD": {"trackerId": "2CF7F1C0530004AD", "timestamp": 1788581560317,
  "position": {"x": 32.41, "y": 21.26, "lat": 22.53544, "lon": 113.94246,
               "alt": null, "accuracy": null, "coordSystem": "wgs84"},
  "lat": 22.53544, "lon": 113.94246, "type": "wGS84", ...}}}}
```

前端产物：`npm run build` 通过，`web/dist` 用 `python3 -m http.server` 静态托管，
`index.html` 200 / 443 B，`assets/index-CFA3J_vM.js` 200 / 646607 B，
`assets/index-*.css` 200 / 157300 B，bundle 内含 leaflet。未做真人点开验证。

## 已知偏差

- `accuracy` 全为 `null`：SenseCAP/ChirpStack 的 4197/4198 不带精度，
  设备侧也没有对应的 measurementId，`accuracy` 字段目前没有数据源。
- `alt` 全为 `null`：4197 按协议是经度而非海拔，本期没有接海拔测点。
- 室内解算落在同一个 beacon 上（`position` 的 x/y 恒为 32.41/21.26），
  因为轨迹只喂了 3 个 beacon 且 RSSI 是人工构造的，不是真实测量。
- 展示类型按「有有效 GNSS fix 即 wGS84」判定，步骤 3 的迟滞状态机未实现，
  所以门口同包 GNSS+BLE 会立刻切到室外。

## 原始输出

- `raw/ws.jsonl` — WebSocket 全量广播
- `raw/ws_capture_summary.txt` — 抓包统计
- `raw/migration_dry_run.txt` — 迁移脚本 dry-run

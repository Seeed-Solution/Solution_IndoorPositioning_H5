# 室内外定位评测

本目录提供把一条 GNSS/BLE 轨迹回放进服务端、并从 WebSocket 侧抓取结果的工具，
用于测出统一交付要求的四个指标。记录格式按 seeed-solutions-hub 的
`templates/evaluation/boundary.schema.yaml`，每个批次一个
`runs/<日期>-<主题>/` 目录。

## 目录结构

```
evaluation/
├── replay_chirpstack.py           # 轨迹回放（MQTT → ChirpStack 主题）
├── ws_capture.py                  # WebSocket 抓包与基础统计
├── traces/
│   ├── indoor_only.jsonl          # 纯室内：只有 BLE 扫描
│   ├── outdoor_only.jsonl         # 纯室外：只有 GNSS fix
│   └── mixed_indoor_outdoor.jsonl # 进出楼：门口同包 GNSS+BLE，含一次 SOS
└── runs/<日期>-<主题>/
    ├── boundary.<指标>.yaml       # 按 boundary.schema.yaml 填
    ├── summary.md
    └── raw/                       # 原始输出
```

## 轨迹格式

JSONL，每行一个上行。主题与载荷格式对齐
`server/handler/message_format_hanlder.py:parse_chirpstack_payload`：

```json
{"t_offset_ms": 0, "dev_eui": "2CF7F1C0530004AD",
 "measurements": {"4197": 113.9421, "4198": 22.5352,
                  "5002": [{"mac": "C3:00:00:3E:7D:DA", "rssi": -55}],
                  "3000": 87, "5003": [{"id": 7}]}}
```

`measurementId` 对照：4197=经度，4198=纬度，4200=SOS，5002=BLE 扫描结果，
3000=电量，5003=事件列表（id 7 为 SOS）。
`t_offset_ms` 是相对轨迹起点的偏移，回放时按它排队。
需要原样透传时改写成 `{"t_offset_ms": ..., "topic": ..., "payload": {...}}`。

## 跑法

```bash
# 0) 起一个本地 broker
docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto:2 \
    mosquitto -c /mosquitto-no-auth.conf
# 或者不用 docker：
uv run --with amqtt amqtt -c evaluation/amqtt.yaml

# 1) 把 server_runtime_config.json 的 chirpStackMqtt 指到本地 broker 并 enabled=true
#    （sensecapOpenStream 建议临时 enabled=false，避免真实设备数据混进来）

# 2) 起服务端
uv run uvicorn server.main:app --host 0.0.0.0 --port 8022

# 3) 抓 WebSocket
uv run --with websockets python evaluation/ws_capture.py \
    --seconds 120 --out evaluation/runs/$(date +%F)-smoke/raw/ws.jsonl

# 4) 回放轨迹
uv run python evaluation/replay_chirpstack.py \
    --trace evaluation/traces/mixed_indoor_outdoor.jsonl \
    --broker 127.0.0.1 --port 1883 \
    --app 26ac83a4-4d1d-4b4f-b0b5-d99893b70171 --speed 20
```

`--dry-run` 只打印将要发送的内容，不连 broker。
`--fanout N` 把同一条轨迹复制成 N 个虚拟标签并发回放，用于容量测试。
`--loop N --speed X` 控制持续时长与压缩倍率。

## 指标定义

四个指标的定义与判定口径如下。三档边界（stable / degrading / failure）写进
`boundary.<指标>.yaml`。

### 1. 容量上限（最大标签数）

同时满足以下四条的最大并发标签数：

- 持续运行 ≥ 30 min
- 上行丢失率 ≤ 1%：`1 - (WebSocket 收到的 tracker_update 数 / 回放发出的上行数)`
- 端到端 P95 ≤ 2 s：见指标 3 的时延定义
- 服务进程 CPU < 80%（单核占用，用 `top -pid <pid>` 或 `docker stats` 采样）

跑法：`--fanout` 逐档加大（如 20 / 50 / 100），每档跑满 30 min。

### 2. 更新频率

每标签每分钟的成功定位数：WebSocket 侧 `tracker_update` 中
`position` 非空的消息数 ÷ 标签数 ÷ 观测分钟数。
室外只统计 `position.coordSystem == "wgs84"` 的条目，室内只统计 `metric`。
上限受设备上报周期约束（T1000 的 GNSS 上报周期不在本期范围内）。

### 3. SOS / 围栏告警时延

从**上行时间戳**（轨迹里的 `timestamp`，回放时按发送时刻改写）到
**告警入库并广播**的时间差，取 P50 / P95。
`ws_capture.py` 会用 `recv_time_ms - message.timestamp` 算出这个差值。
围栏告警在步骤 3 落地后才有数，本批只能测 SOS。

### 4. 离线告警时延

最后一次上行到 `tracker_offline` 广播的时间差。
基线阈值 15 min、轮询周期 60 s（`server/handler/offline_handler.py:25,50-89`），
因此理论值域是 [15 min, 16 min]，实测应落在这个区间内。
跑法：回放一条轨迹后停止回放，让 `ws_capture.py` 继续抓 17 min。

### 5. 平面图配准（室内平面图 ↔ 室外地图）

不是时延类指标，是几何精度指标。三个数字：

- **双端一致性**：同一组输入下 `server/geo/affine.py` 与
  `web/src/utils/affine.js` 输出的经纬度之差，预算 ≤ 1e-9 度（约 0.1 mm）。
- **往返误差**：`local -> wgs84 -> local` 回到原点的距离，预算 ≤ 1 mm。
- **相对测地线的偏差**：局部平面距离与 Vincenty 反算的椭球测地线距离之差。
  切平面近似在原点展开，半径 ≤ 2 km、|纬度| ≤ 60° 时预算 ≤ 0.7 m。
  |纬度| > 85° 直接拒绝配准（`GEOREF_POLAR_LIMIT_DEG`）。

跑法：

```bash
uv run python evaluation/georef_precision.py --json <run>/raw/precision.json
```

脚本读 `tests/fixtures/georef/cases.json`——单元测试两端读的是同一份 fixture，
所以这里的数字与 `uv run pytest server/tests/test_geo_affine.py`、
`npm test`（`web/tests/affine.test.js`）核对的是同一条曲线。

2026-09-05 实测（`runs/2026-09-05-georef/results.md`）：

| 指标 | 实测最差 | 预算 |
| --- | ---: | ---: |
| Python vs JS | 2.711e-20 ° | 1e-9 ° |
| 往返 | 7.511e-10 m | 1e-3 m |
| 相对测地线（≤2 km，\|lat\|≤60） | 0.2028 m | 0.7 m |

误差随半径与纬度增长，几个参考点（方位角每 15° 扫描，取最差）：

| lat0 | 500 m | 1 km | 2 km |
| ---: | ---: | ---: | ---: |
| 0° | ~0.000 m | ~0.000 m | 0.000 m |
| 22.5° | — | — | 0.049 m |
| 45° | — | — | 0.117 m |
| 60° | — | — | 0.203 m |

（500 m / 1 km 两列被 2 km 列覆盖，扫描里没单独记；最差值总在 2 km。）

#### UI 验收清单

配准是交互功能，除了数字还要走一遍：

1. 进入配准模式，初猜落在当前视图中心、正北、scale 1；已有配准则从它起步。
2. 移动 / 旋转 / 等比缩放三种操作各试一次；确认没有拉伸变形（宽高比锁定）。
3. 侧栏三参数与图片双向同步：改数字图片跟着动，拖图片数字跟着变。
4. 取消丢弃草稿，重置回到初猜。
5. 保存后刷新浏览器，配准参数仍在。
6. 已配准平面图上的设备实时点与 metric 历史段出现在同一张 Leaflet 图上，
   与 wgs84 段在切换点不连线。

记录：平面图像素尺寸、地图米数、四个配准参数、每一步的截图。

## 记录要求

- 每个批次一个 `runs/<日期>-<主题>/`，原始输出放 `raw/`，
  在 `boundary.<指标>.yaml` 的 `raw_refs` 里引用相对路径。
- 估算与实测必须分开写；未测到的档位写 `value: null` 并在 `caveats` 说明原因。
- 首次测试者本人不算复现，`reproduced_by` 需要另一个人跑过才能填。

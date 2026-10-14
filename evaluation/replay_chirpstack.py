#!/usr/bin/env python3
"""把一条 GNSS/BLE 轨迹按时间回放到 ChirpStack 的 MQTT 主题上。

主题与载荷格式对齐 server/handler/message_format_hanlder.py:parse_chirpstack_payload
与 server/main.py 的订阅：

    application/{applicationID}/device/{devEUI}/event/up
    payload.object.messages[0] = [{measurementId, measurementValue, timestamp}, ...]

轨迹文件为 JSONL，每行一个上行，两种写法都支持：

1) 简写（推荐，见 evaluation/traces/*.jsonl）：
   {"t_offset_ms": 0, "dev_eui": "...", "measurements": {"4197": 113.9, "4198": 22.5,
    "5002": [{"mac": "...", "rssi": -55}], "3000": 87, "5003": [{"id": 7}]}}

2) 原样透传：
   {"t_offset_ms": 0, "topic": "application/.../event/up", "payload": { ... }}

用法：
    uv run python evaluation/replay_chirpstack.py \
        --trace evaluation/traces/mixed_indoor_outdoor.jsonl \
        --broker 127.0.0.1 --port 1883 \
        --app 26ac83a4-4d1d-4b4f-b0b5-d99893b70171

    # 不连 broker，只打印将要发送的内容
    uv run python evaluation/replay_chirpstack.py --trace ... --dry-run

    # 容量测试：把同一条轨迹复制成 N 个虚拟标签同时回放
    uv run python evaluation/replay_chirpstack.py --trace ... --fanout 50 --loop 30
"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

MEASUREMENT_TYPE_NAMES = {
    "3000": "Battery",
    "4197": "Longitude",
    "4198": "Latitude",
    "4200": "SOS",
    "5002": "Bluetooth Beacon",
    "5003": "Event Status",
}


def build_payload(dev_eui: str, measurements: dict, timestamp_ms: int) -> dict:
    """把 measurementId->value 的字典包成一条 ChirpStack uplink event。"""
    entries = []
    for measurement_id, value in measurements.items():
        entries.append({
            "type": MEASUREMENT_TYPE_NAMES.get(str(measurement_id), "Unknown"),
            "measurementId": str(measurement_id),
            "measurementValue": value,
            "timestamp": timestamp_ms,
        })
    return {
        "deduplicationId": str(uuid.uuid4()),
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(timestamp_ms / 1000)),
        "deviceInfo": {
            "applicationName": "indoor-positioning",
            "deviceName": f"replay-{dev_eui[-4:]}",
            "devEui": dev_eui.lower(),
        },
        "fPort": 5,
        "object": {"valid": True, "err": 0, "messages": [entries]},
    }


def load_trace(path: Path) -> list:
    records = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as err:
                raise SystemExit(f"{path}:{lineno}: bad JSON: {err}")
    records.sort(key=lambda r: r.get("t_offset_ms", 0))
    return records


def expand(record: dict, app_id: str, base_time_ms: int, eui_suffix: str = ""):
    """一条轨迹记录 -> (topic, payload dict)。"""
    if "topic" in record and "payload" in record:
        return record["topic"], record["payload"]
    dev_eui = record["dev_eui"]
    if eui_suffix:
        dev_eui = dev_eui[: 16 - len(eui_suffix)] + eui_suffix
    timestamp_ms = base_time_ms + int(record.get("t_offset_ms", 0))
    topic = f"application/{app_id}/device/{dev_eui.lower()}/event/up"
    return topic, build_payload(dev_eui, record.get("measurements", {}), timestamp_ms)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trace", required=True, help="JSONL trace file")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--app", default="26ac83a4-4d1d-4b4f-b0b5-d99893b70171",
                        help="ChirpStack applicationID used in the topic")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="replay speed multiplier (2.0 = twice as fast)")
    parser.add_argument("--loop", type=int, default=1, help="how many times to replay")
    parser.add_argument("--fanout", type=int, default=1,
                        help="replay the trace as N synthetic trackers in parallel")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = load_trace(Path(args.trace))
    if not records:
        raise SystemExit("trace is empty")

    client = None
    if not args.dry_run:
        import paho.mqtt.client as mqtt
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=f"replay-{uuid.uuid4().hex[:8]}")
        if args.username:
            client.username_pw_set(args.username, args.password)
        client.connect(args.broker, args.port, keepalive=30)
        client.loop_start()
        print(f"[replay] connected to {args.broker}:{args.port}")

    sent = 0
    try:
        for iteration in range(args.loop):
            base_time_ms = int(time.time() * 1000)
            started = time.monotonic()
            for record in records:
                target = (record.get("t_offset_ms", 0) / 1000.0) / max(args.speed, 0.001)
                wait = target - (time.monotonic() - started)
                if wait > 0:
                    time.sleep(wait)
                for lane in range(args.fanout):
                    suffix = "" if args.fanout == 1 else f"{lane:04X}"
                    topic, payload = expand(record, args.app, base_time_ms, suffix)
                    blob = json.dumps(payload)
                    if args.dry_run:
                        print(f"[replay] {topic} {blob}")
                    else:
                        client.publish(topic, blob, qos=0)
                    sent += 1
            print(f"[replay] pass {iteration + 1}/{args.loop} done, {sent} uplinks sent")
    except KeyboardInterrupt:
        print("[replay] interrupted", file=sys.stderr)
    finally:
        if client:
            time.sleep(0.5)
            client.loop_stop()
            client.disconnect()
    print(f"[replay] total uplinks: {sent}")


if __name__ == "__main__":
    main()

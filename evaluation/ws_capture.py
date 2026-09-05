#!/usr/bin/env python3
"""抓取服务端 WebSocket 广播，落成 JSONL 原始记录，并给出基础指标。

配合 replay_chirpstack.py 使用：先起这个抓包，再回放轨迹。

用法：
    uv run --with websockets python evaluation/ws_capture.py \
        --url ws://127.0.0.1:8022/ws --seconds 120 \
        --out evaluation/runs/2026-09-05-smoke/raw/ws.jsonl

输出的每一行是 {"recv_time_ms": ..., "message": {...}}，
recv_time_ms 与消息里的 timestamp 之差即端到端时延的一半信息
（另一半是上行时间戳，由回放脚本写入 measurements 的 timestamp）。
"""
import argparse
import asyncio
import json
import time
from pathlib import Path


async def capture(url: str, seconds: float, out_path: Path):
    import websockets

    out_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + seconds
    counts = {}
    tracker_updates_with_fix = 0
    latencies_ms = []
    # 步骤 3: 围栏告警与展示类型切换
    geofence_alarms = []          # {tracker, fence_id, transition, latency_ms}
    geofence_latencies_ms = []
    last_type = {}                # tracker -> 上一次的 tracker_update.type
    type_switches = []            # {tracker, from, to, timestamp}

    async with websockets.connect(url) as ws:
        print(f"[ws_capture] connected to {url}, capturing for {seconds}s")
        with open(out_path, "w", encoding="utf-8") as fh:
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(remaining, 0.1))
                except asyncio.TimeoutError:
                    break
                recv_ms = int(time.time() * 1000)
                fh.write(json.dumps({"recv_time_ms": recv_ms,
                                     "message": json.loads(raw)}, ensure_ascii=False) + "\n")
                fh.flush()
                message = json.loads(raw)
                mtype = message.get("type", "unknown")
                counts[mtype] = counts.get(mtype, 0) + 1
                if mtype == "tracker_update":
                    for tracker_id, payload in message.get("data", {}).items():
                        if payload.get("lat") is not None and payload.get("lon") is not None:
                            tracker_updates_with_fix += 1
                        uplink_ts = payload.get("timestamp")
                        if uplink_ts:
                            latencies_ms.append(recv_ms - int(uplink_ts))
                        current_type = payload.get("type")
                        previous = last_type.get(tracker_id)
                        if previous is not None and current_type != previous:
                            type_switches.append({"tracker": tracker_id, "from": previous,
                                                  "to": current_type, "timestamp": uplink_ts})
                        last_type[tracker_id] = current_type
                elif mtype in ("tracker_checkin", "tracker_position_detection"):
                    # 围栏告警沿用这两个消息类型, 多带一个 geofence 段.
                    for tracker_id, payload in message.get("data", {}).items():
                        fence = payload.get("geofence")
                        if not fence:
                            continue
                        uplink_ts = payload.get("timestamp")
                        latency = recv_ms - int(uplink_ts) if uplink_ts else None
                        if latency is not None:
                            geofence_latencies_ms.append(latency)
                        geofence_alarms.append({
                            "tracker": tracker_id,
                            "message_type": mtype,
                            "fence_id": fence.get("id"),
                            "fence_name": fence.get("name"),
                            "transition": fence.get("transition"),
                            "uplink_timestamp": uplink_ts,
                            "latency_ms": latency,
                        })

    summary = {
        "message_counts": counts,
        "tracker_updates_with_gnss_fix": tracker_updates_with_fix,
        "latency_ms_count": len(latencies_ms),
        "latency_ms_p95": (sorted(latencies_ms)[int(len(latencies_ms) * 0.95)]
                           if latencies_ms else None),
        "geofence_alarms": geofence_alarms,
        "geofence_alarm_count": len(geofence_alarms),
        "geofence_latency_ms_p50": (sorted(geofence_latencies_ms)[len(geofence_latencies_ms) // 2]
                                    if geofence_latencies_ms else None),
        "geofence_latency_ms_max": max(geofence_latencies_ms) if geofence_latencies_ms else None,
        "type_switch_count": len(type_switches),
        "type_switches": type_switches,
        "final_types": last_type,
        "raw": str(out_path),
    }
    print("[ws_capture] " + json.dumps(summary, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="ws://127.0.0.1:8022/ws")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    asyncio.run(capture(args.url, args.seconds, args.out))


if __name__ == "__main__":
    main()

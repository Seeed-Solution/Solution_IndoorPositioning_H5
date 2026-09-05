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
                    for payload in message.get("data", {}).values():
                        if payload.get("lat") is not None and payload.get("lon") is not None:
                            tracker_updates_with_fix += 1
                        uplink_ts = payload.get("timestamp")
                        if uplink_ts:
                            latencies_ms.append(recv_ms - int(uplink_ts))

    summary = {
        "message_counts": counts,
        "tracker_updates_with_gnss_fix": tracker_updates_with_fix,
        "latency_ms_count": len(latencies_ms),
        "latency_ms_p95": (sorted(latencies_ms)[int(len(latencies_ms) * 0.95)]
                           if latencies_ms else None),
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

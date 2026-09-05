#!/usr/bin/env python3
"""平面图配准投影精度：Python / JS 双端差、往返误差、相对测地线的偏差。

读 ``tests/fixtures/georef/cases.json``（Python 与 JS 的单元测试读的是同一份），
分别跑 ``server/geo/affine.py`` 与 ``web/src/utils/affine.js``，把三组数字打成
一张表。JS 侧通过 node 直接 import ESM 模块，不经打包。

用法::

    uv run python evaluation/georef_precision.py [--json out.json]
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from server.geo.affine import local_to_wgs84, wgs84_to_local  # noqa: E402
from server.tests.vincenty_ref import vincenty_distance_m     # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "georef" / "cases.json"

NODE_SCRIPT = """
import { localToWgs84, wgs84ToLocal } from './src/utils/affine.js';
import { readFileSync } from 'node:fs';
const data = JSON.parse(readFileSync(process.argv[2], 'utf-8'));
const out = data.cases.map((c) => ({
  name: c.name,
  forward: c.points.map((p) => localToWgs84(p.x, p.y, c.registration)),
  inverse: c.expected.map((e) => wgs84ToLocal(e.lat, e.lon, c.registration)),
}));
process.stdout.write(JSON.stringify(out));
"""


def run_js(fixture_path: Path):
    web = REPO_ROOT / "web"
    script = web / ".georef_precision.mjs"
    script.write_text(NODE_SCRIPT, encoding="utf-8")
    try:
        proc = subprocess.run(
            ["node", str(script), str(fixture_path)],
            cwd=web, capture_output=True, text=True, check=True,
        )
        return json.loads(proc.stdout)
    finally:
        script.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    js = {entry["name"]: entry for entry in run_js(FIXTURE)}

    rows = []
    for case in data["cases"]:
        name = case["name"]
        reg = case["registration"]
        j = js[name]
        cross_deg = 0.0
        roundtrip_m = 0.0
        geodesic_m = 0.0
        for i, point in enumerate(case["points"]):
            lat, lon = local_to_wgs84(point["x"], point["y"], reg)
            cross_deg = max(cross_deg,
                            abs(lat - j["forward"][i]["lat"]),
                            abs(lon - j["forward"][i]["lon"]))

            bx, by = wgs84_to_local(lat, lon, reg)
            roundtrip_m = max(roundtrip_m, math.hypot(bx - point["x"], by - point["y"]))
            roundtrip_m = max(roundtrip_m, math.hypot(
                j["inverse"][i]["x"] - point["x"], j["inverse"][i]["y"] - point["y"]))

            # 相对测地线：局部平面距离 vs 椭球测地线距离（原点 -> 该点）。
            planar = math.hypot(point["x"], point["y"]) * reg.get("scale", 1.0)
            if planar > 0:
                geodesic = vincenty_distance_m(reg["origin_lat"], reg["origin_lon"], lat, lon)
                geodesic_m = max(geodesic_m, abs(geodesic - planar))

        rows.append({
            "case": name,
            "origin_lat": reg["origin_lat"],
            "rotation_deg": reg.get("rotation_deg", 0.0),
            "scale": reg.get("scale", 1.0),
            "points": len(case["points"]),
            "cross_impl_max_deg": cross_deg,
            "roundtrip_max_m": roundtrip_m,
            "vs_geodesic_max_m": geodesic_m,
        })

    header = (f"{'case':26} {'lat0':>9} {'rot':>8} {'scale':>7} "
              f"{'py-vs-js(deg)':>15} {'roundtrip(m)':>14} {'vs geodesic(m)':>16}")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['case']:26} {r['origin_lat']:9.4f} {r['rotation_deg']:8.2f} "
              f"{r['scale']:7.4f} {r['cross_impl_max_deg']:15.3e} "
              f"{r['roundtrip_max_m']:14.3e} {r['vs_geodesic_max_m']:16.4f}")
    print("-" * len(header))
    print(f"worst py-vs-js   : {max(r['cross_impl_max_deg'] for r in rows):.3e} deg "
          f"(budget {data['tolerance_deg']:.0e})")
    print(f"worst roundtrip  : {max(r['roundtrip_max_m'] for r in rows):.3e} m "
          f"(budget {data['roundtrip_tolerance_m']:.0e})")
    print(f"worst vs geodesic: {max(r['vs_geodesic_max_m'] for r in rows):.4f} m "
          f"(budget 0.7 within 2 km / |lat| <= 60)")

    if args.json:
        args.json.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

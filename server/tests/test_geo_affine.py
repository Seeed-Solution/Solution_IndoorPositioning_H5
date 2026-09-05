"""Step 3: shared metric <-> WGS84 transform.

与 ``web/tests/affine.test.js`` 读同一份 ``tests/fixtures/georef/*.json``。
"""
import json
import math
from pathlib import Path

import pytest

from server.tests.vincenty_ref import vincenty_distance_m
from server.geo.affine import (
    GEOREF_POLAR_LIMIT_DEG,
    GeoreferenceError,
    curvature_radii,
    is_registered,
    local_to_wgs84,
    validate_registration,
    wgs84_to_local,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "georef"


def _load(name):
    with open(FIXTURE_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


CASES = _load("cases.json")
REJECTIONS = _load("rejections.json")


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_forward_matches_fixture(case):
    """Python 输出与 fixture 里记录的期望值差 <= 1e-9 度。

    fixture 由本实现生成；同一份文件被 JS 侧断言，两端因此被钉在同一条曲线上。
    """
    tol = CASES["tolerance_deg"]
    for point, expected in zip(case["points"], case["expected"]):
        lat, lon = local_to_wgs84(point["x"], point["y"], case["registration"])
        assert abs(lat - expected["lat"]) <= tol
        assert abs(lon - expected["lon"]) <= tol


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_roundtrip_within_one_mm(case):
    tol = CASES["roundtrip_tolerance_m"]
    for point, expected in zip(case["points"], case["expected"]):
        x, y = wgs84_to_local(expected["lat"], expected["lon"], case["registration"])
        assert math.hypot(x - point["x"], y - point["y"]) <= tol


@pytest.mark.parametrize("case", REJECTIONS["cases"], ids=lambda c: c["name"])
def test_rejections(case):
    with pytest.raises(GeoreferenceError):
        validate_registration(case["registration"])
    with pytest.raises(GeoreferenceError):
        local_to_wgs84(0.0, 0.0, case["registration"])
    with pytest.raises(GeoreferenceError):
        wgs84_to_local(0.0, 0.0, case["registration"])


def test_polar_limit_boundary_is_inclusive():
    validate_registration({"origin_lat": GEOREF_POLAR_LIMIT_DEG, "origin_lon": 0.0})
    validate_registration({"origin_lat": -GEOREF_POLAR_LIMIT_DEG, "origin_lon": 0.0})
    assert REJECTIONS["polar_limit_deg"] == GEOREF_POLAR_LIMIT_DEG


def test_non_finite_inputs_rejected():
    reg = {"origin_lat": 0.0, "origin_lon": 0.0}
    with pytest.raises(GeoreferenceError):
        local_to_wgs84(float("nan"), 0.0, reg)
    with pytest.raises(GeoreferenceError):
        local_to_wgs84(0.0, float("inf"), reg)
    with pytest.raises(GeoreferenceError):
        wgs84_to_local(float("nan"), 0.0, reg)


def test_axis_orientation_at_zero_rotation():
    reg = {"origin_lat": 22.5231, "origin_lon": 113.9312, "rotation_deg": 0.0, "scale": 1.0}
    lat, lon = local_to_wgs84(0.0, 100.0, reg)
    assert lat > reg["origin_lat"]
    assert lon == pytest.approx(reg["origin_lon"], abs=1e-12)
    lat, lon = local_to_wgs84(100.0, 0.0, reg)
    assert lon > reg["origin_lon"]
    assert lat == pytest.approx(reg["origin_lat"], abs=1e-12)


@pytest.mark.parametrize("rotation,expect_east", [(90.0, True), (-90.0, False)])
def test_rotation_sign_is_clockwise(rotation, expect_east):
    """+Y 顺时针偏离北方: +90 度把 +Y 转到正东, -90 度转到正西。"""
    reg = {"origin_lat": 22.5231, "origin_lon": 113.9312,
           "rotation_deg": rotation, "scale": 1.0}
    lat, lon = local_to_wgs84(0.0, 100.0, reg)
    assert lat == pytest.approx(reg["origin_lat"], abs=1e-9)
    assert (lon > reg["origin_lon"]) is expect_east


def test_scale_is_a_linear_multiplier():
    base = {"origin_lat": 0.0, "origin_lon": 0.0, "rotation_deg": 0.0, "scale": 1.0}
    doubled = dict(base, scale=2.0)
    lat1, lon1 = local_to_wgs84(100.0, 100.0, base)
    lat2, lon2 = local_to_wgs84(100.0, 100.0, doubled)
    assert lat2 == pytest.approx(2 * lat1, rel=1e-12)
    assert lon2 == pytest.approx(2 * lon1, rel=1e-12)


def test_curvature_radii_ordering():
    m, n = curvature_radii(45.0)
    assert n > m > 6.3e6


def test_is_registered():
    assert is_registered(None) is False
    assert is_registered({}) is False
    assert is_registered({"registration": {"origin_lat": 91.0, "origin_lon": 0.0}}) is False
    assert is_registered({"registration": {"origin_lat": 22.5, "origin_lon": 113.9}}) is True


@pytest.mark.parametrize("lat0", [0.0, 22.5231, 45.0, 60.0])
def test_two_km_stays_within_the_documented_error_bound(lat0):
    """半径 2 km、|纬度| <= 60 时切平面近似相对测地线的偏差 <= 0.7 m。

    参照量是 Vincenty 反算（server/tests/vincenty_ref.py），与本实现无共享代码。
    """
    reg = {"origin_lat": lat0, "origin_lon": 10.0, "rotation_deg": 0.0, "scale": 1.0}
    worst = 0.0
    for bearing in range(0, 360, 15):
        for radius in (500.0, 1000.0, 2000.0):
            x = radius * math.sin(math.radians(bearing))
            y = radius * math.cos(math.radians(bearing))
            lat, lon = local_to_wgs84(x, y, reg)
            geodesic = vincenty_distance_m(lat0, 10.0, lat, lon)
            worst = max(worst, abs(geodesic - radius))
    assert worst <= 0.7, f"lat0={lat0} worst error {worst:.4f} m"

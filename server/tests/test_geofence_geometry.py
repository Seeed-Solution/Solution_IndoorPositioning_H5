"""围栏几何: 内 / 外 / 边界 / 跨日界线 / 圆形."""
import json

import pytest

from server import geofence as ge


SQUARE = {
    "type": "Polygon",
    "coordinates": [[
        [113.0, 22.0], [113.01, 22.0], [113.01, 22.01], [113.0, 22.01], [113.0, 22.0],
    ]],
}

# 跨 180° 子午线: 经度从 179.9 到 -179.9.
DATELINE = {
    "type": "Polygon",
    "coordinates": [[
        [179.9, 10.0], [-179.9, 10.0], [-179.9, 10.1], [179.9, 10.1], [179.9, 10.0],
    ]],
}

MULTI = {
    "type": "MultiPolygon",
    "coordinates": [
        SQUARE["coordinates"],
        [[[114.0, 22.0], [114.01, 22.0], [114.01, 22.01], [114.0, 22.01], [114.0, 22.0]]],
    ],
}


def test_polygon_inside():
    fence = ge.build_geofence(json.dumps(SQUARE))
    assert fence.kind == ge.GEOFENCE_KIND_POLYGON
    assert fence.covers(22.005, 113.005) is True


def test_polygon_outside():
    fence = ge.build_geofence(SQUARE)
    assert fence.covers(22.005, 113.05) is False
    assert fence.covers(21.5, 113.005) is False


def test_polygon_boundary_counts_as_inside():
    """covers 把边界算在围栏内, 与 contains 的区别就在这里."""
    fence = ge.build_geofence(SQUARE)
    assert fence.covers(22.0, 113.005) is True      # 底边
    assert fence.covers(22.0, 113.0) is True        # 顶点


def test_multipolygon_covers_both_parts():
    fence = ge.build_geofence(MULTI)
    assert fence.covers(22.005, 113.005) is True
    assert fence.covers(22.005, 114.005) is True
    assert fence.covers(22.005, 113.5) is False


def test_dateline_polygon_is_wrapped():
    fence = ge.build_geofence(DATELINE)
    assert fence.wrap is True
    # 日界线两侧都应该在围栏内.
    assert fence.covers(10.05, 179.95) is True
    assert fence.covers(10.05, -179.95) is True
    # 不做归一化的话, 下面这个点会被"经度 0..180 的巨大矩形"误判为内部.
    assert fence.covers(10.05, 0.0) is False


def test_circle_uses_haversine():
    circle = {"type": "Point", "coordinates": [113.0, 22.0]}
    fence = ge.build_geofence(circle, radius_m=100.0)
    assert fence.kind == ge.GEOFENCE_KIND_CIRCLE
    assert fence.covers(22.0, 113.0) is True
    # 22.0 -> 22.0008 约 89 m, 在半径内; 22.002 约 222 m, 在半径外.
    assert fence.covers(22.0008, 113.0) is True
    assert fence.covers(22.002, 113.0) is False


def test_circle_boundary():
    circle = {"type": "Point", "coordinates": [0.0, 0.0]}
    fence = ge.build_geofence(circle, radius_m=1000.0)
    d = ge.haversine_m(0.0, 0.0, 0.0, 0.008993)
    assert 995 < d < 1005          # 校准一下这个偏移确实约等于 1 km
    assert fence.covers(0.0, 0.008993) is (d <= 1000.0)


def test_circle_requires_radius():
    with pytest.raises(ge.GeofenceGeometryError):
        ge.build_geofence({"type": "Point", "coordinates": [113.0, 22.0]})


def test_unsupported_geometry_type():
    with pytest.raises(ge.GeofenceGeometryError):
        ge.build_geofence({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})


def test_bad_json():
    with pytest.raises(ge.GeofenceGeometryError):
        ge.build_geofence("not-json")


def test_feature_wrapper_is_unwrapped():
    fence = ge.build_geofence({"type": "Feature", "properties": {}, "geometry": SQUARE})
    assert fence.covers(22.005, 113.005) is True


def test_distance_to_boundary_is_non_negative():
    fence = ge.build_geofence(SQUARE)
    assert fence.distance_to_boundary_m(22.005, 113.005) > 0
    assert fence.distance_to_boundary_m(22.05, 113.005) > 0
    circle = ge.build_geofence({"type": "Point", "coordinates": [0.0, 0.0]}, radius_m=1000.0)
    assert circle.distance_to_boundary_m(0.0, 0.0) == pytest.approx(1000.0, rel=1e-6)

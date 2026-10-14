# -*- coding: utf-8 -*-
"""地理围栏几何引擎.

围栏两种形态:
  - 多边形: GeoJSON ``Polygon`` / ``MultiPolygon``, 用 shapely prepared
    geometry 的 ``covers`` 判定 (边界算在内).
  - 圆形:   GeoJSON ``Point`` + ``radius_m``, 用 Haversine 距离判定.

坐标一律按 (lon, lat) 喂给 shapely, 即 x=经度, y=纬度.

跨日界线: 经度跨度 > 180° 的多边形按「跨 180° 子午线」处理, 所有经度
归一化到 [0, 360), 判定时待测点同样归一化. 判据保存在 ``wrap`` 上.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from shapely.geometry import Point, shape
from shapely.prepared import prep

import logging

log = logging.getLogger(__name__)

GEOFENCE_KIND_POLYGON = "polygon"
GEOFENCE_KIND_CIRCLE = "circle"

CRS_WGS84 = "wgs84"
CRS_GCJ02 = "gcj02"

EARTH_RADIUS_M = 6371008.8
METERS_PER_DEGREE_LAT = 111320.0


class GeofenceGeometryError(ValueError):
    """围栏几何非法."""


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两点大圆距离, 单位米."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def _iter_coords(geometry: dict) -> list:
    """展平 GeoJSON 的坐标, 返回 [lon, lat] 列表."""
    out: list = []

    def walk(node):
        if (
            isinstance(node, (list, tuple))
            and len(node) >= 2
            and all(isinstance(v, (int, float)) for v in node[:2])
        ):
            out.append([float(node[0]), float(node[1])])
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                walk(child)

    walk(geometry.get("coordinates"))
    return out


def _needs_wrap(coords: list) -> bool:
    if not coords:
        return False
    lons = [c[0] for c in coords]
    return (max(lons) - min(lons)) > 180.0


def _wrap_lon(lon: float) -> float:
    """经度归一化到 [0, 360)."""
    return lon % 360.0


def _wrap_geometry(geometry: dict) -> dict:
    """把 GeoJSON 里所有经度平移到 [0, 360), 用于跨日界线的多边形."""

    def walk(node):
        if (
            isinstance(node, (list, tuple))
            and len(node) >= 2
            and all(isinstance(v, (int, float)) for v in node[:2])
        ):
            return [_wrap_lon(float(node[0])), float(node[1])] + list(node[2:])
        if isinstance(node, (list, tuple)):
            return [walk(child) for child in node]
        return node

    wrapped = dict(geometry)
    wrapped["coordinates"] = walk(geometry.get("coordinates"))
    return wrapped


@dataclass
class Geofence:
    """已编译的围栏, 判定用的一切都预先算好."""

    id: Optional[int]
    name: str = ""
    kind: str = GEOFENCE_KIND_POLYGON
    crs: str = CRS_WGS84
    radius_m: Optional[float] = None
    center: Optional[tuple] = None          # (lat, lon), 仅圆形
    wrap: bool = False                      # 跨日界线的多边形
    _geom: Any = field(default=None, repr=False)
    _prepared: Any = field(default=None, repr=False)

    def covers(self, lat: float, lon: float) -> bool:
        """点是否在围栏内 (含边界)."""
        if lat is None or lon is None:
            return False
        if self.kind == GEOFENCE_KIND_CIRCLE:
            c_lat, c_lon = self.center
            return haversine_m(lat, lon, c_lat, c_lon) <= float(self.radius_m)
        x = _wrap_lon(lon) if self.wrap else lon
        return bool(self._prepared.covers(Point(x, lat)))

    def distance_to_boundary_m(self, lat: float, lon: float) -> float:
        """点到围栏边界的距离 (米, 恒非负).

        用于精度缓冲带: 距离小于定位精度时判定不可信.
        多边形按当前纬度把度换算成米, 是近似值.
        """
        if self.kind == GEOFENCE_KIND_CIRCLE:
            c_lat, c_lon = self.center
            return abs(haversine_m(lat, lon, c_lat, c_lon) - float(self.radius_m))
        x = _wrap_lon(lon) if self.wrap else lon
        deg = self._geom.boundary.distance(Point(x, lat))
        # 度 -> 米: 纬向恒定, 经向按 cos(lat) 收缩; 取两者的几何折中(保守用较小值).
        scale = METERS_PER_DEGREE_LAT * max(0.05, math.cos(math.radians(lat)))
        return deg * scale


def build_geofence(
    geometry_json: str | dict,
    radius_m: Optional[float] = None,
    crs: str = CRS_WGS84,
    fence_id: Optional[int] = None,
    name: str = "",
) -> Geofence:
    """把库里的 ``geometry_json`` 编译成可判定的 :class:`Geofence`."""
    if isinstance(geometry_json, str):
        try:
            geometry = json.loads(geometry_json)
        except (TypeError, ValueError) as err:
            raise GeofenceGeometryError(f"geometry_json 不是合法 JSON: {err}") from err
    else:
        geometry = geometry_json
    if not isinstance(geometry, dict):
        raise GeofenceGeometryError("geometry_json 必须是 GeoJSON 对象")

    # 允许直接存 Feature, 取它的 geometry.
    if geometry.get("type") == "Feature":
        geometry = geometry.get("geometry") or {}

    gtype = geometry.get("type")
    if gtype == "Point":
        if radius_m is None or float(radius_m) <= 0:
            raise GeofenceGeometryError("圆形围栏必须带正数 radius_m")
        coords = _iter_coords(geometry)
        if not coords:
            raise GeofenceGeometryError("Point 缺少坐标")
        lon, lat = coords[0]
        return Geofence(
            id=fence_id,
            name=name,
            kind=GEOFENCE_KIND_CIRCLE,
            crs=crs or CRS_WGS84,
            radius_m=float(radius_m),
            center=(lat, lon),
        )

    if gtype not in ("Polygon", "MultiPolygon"):
        raise GeofenceGeometryError(f"不支持的围栏几何类型: {gtype}")

    coords = _iter_coords(geometry)
    wrap = _needs_wrap(coords)
    geom = shape(_wrap_geometry(geometry) if wrap else geometry)
    if geom.is_empty:
        raise GeofenceGeometryError("围栏几何为空")
    if not geom.is_valid:
        geom = geom.buffer(0)
        if geom.is_empty or not geom.is_valid:
            raise GeofenceGeometryError("围栏几何自交且无法修复")

    return Geofence(
        id=fence_id,
        name=name,
        kind=GEOFENCE_KIND_POLYGON,
        crs=crs or CRS_WGS84,
        wrap=wrap,
        _geom=geom,
        _prepared=prep(geom),
    )


def build_from_record(record) -> Geofence:
    """从 :class:`server.models.GeofenceRecord` 编译围栏."""
    return build_geofence(
        geometry_json=record.geometry_json,
        radius_m=record.radius_m,
        crs=record.crs,
        fence_id=record.id,
        name=record.name,
    )


# --------------------------------------------------------------------------
# 进出转换的滞回判定
# --------------------------------------------------------------------------

TRANSITION_ENTER = "enter"
TRANSITION_EXIT = "exit"
TRANSITION_BOTH = "both"

FENCE_STATE_INSIDE = "inside"
FENCE_STATE_OUTSIDE = "outside"

#: spec 默认值: 连续 3 个点且持续 10 s 才切换围栏状态.
DEFAULT_FENCE_CONFIRM_POINTS = 3
DEFAULT_FENCE_CONFIRM_MS = 10_000
#: 精度门槛; accuracy 为 None 时视为通过并记日志.
DEFAULT_FENCE_ACCURACY_MAX_M = 25.0


@dataclass
class FenceHysteresis:
    """单个 (设备, 事件) 上的围栏状态滞回.

    ``feed()`` 返回 ``"enter"`` / ``"exit"`` / ``None``.
    首次观测只落地初始状态, 不产生转换 (避免服务重启就补一条告警).
    """

    confirm_points: int = DEFAULT_FENCE_CONFIRM_POINTS
    confirm_ms: int = DEFAULT_FENCE_CONFIRM_MS
    accuracy_max_m: float = DEFAULT_FENCE_ACCURACY_MAX_M
    state: Optional[str] = None
    _pending: Optional[str] = None
    _pending_since: Optional[int] = None
    _pending_count: int = 0

    def _reset_pending(self):
        self._pending = None
        self._pending_since = None
        self._pending_count = 0

    def feed(
        self,
        fence: Geofence,
        lat: float,
        lon: float,
        timestamp_ms: int,
        accuracy: Optional[float] = None,
        log_key: str = "",
    ) -> Optional[str]:
        if lat is None or lon is None:
            return None

        if accuracy is None:
            log.info(
                "geofence %s: accuracy 缺失, 按通过精度门槛处理 (%s)",
                fence.id, log_key or "-",
            )
        elif accuracy > self.accuracy_max_m:
            log.info(
                "geofence %s: 丢弃精度 %.1f m 的点 (门槛 %.1f m, %s)",
                fence.id, accuracy, self.accuracy_max_m, log_key or "-",
            )
            return None

        observed = FENCE_STATE_INSIDE if fence.covers(lat, lon) else FENCE_STATE_OUTSIDE

        # 精度缓冲带: 点离边界比定位误差还近时, 保持原状态并且不推进 pending.
        if (
            accuracy is not None
            and self.state is not None
            and fence.distance_to_boundary_m(lat, lon) < accuracy
        ):
            log.info(
                "geofence %s: 点落在精度缓冲带内, 保持 %s (%s)",
                fence.id, self.state, log_key or "-",
            )
            return None

        if self.state is None:
            self.state = observed
            self._reset_pending()
            return None

        if observed == self.state:
            self._reset_pending()
            return None

        if self._pending != observed:
            self._pending = observed
            self._pending_since = timestamp_ms
            self._pending_count = 1
            return None

        self._pending_count += 1
        elapsed = timestamp_ms - (self._pending_since or timestamp_ms)
        if self._pending_count >= self.confirm_points and elapsed >= self.confirm_ms:
            self.state = observed
            self._reset_pending()
            return (
                TRANSITION_ENTER if observed == FENCE_STATE_INSIDE else TRANSITION_EXIT
            )
        return None


def transition_matches(configured: Optional[str], happened: str) -> bool:
    """告警配置的 ``transition`` 是否覆盖实际发生的转换."""
    if not configured or configured == TRANSITION_BOTH:
        return True
    return configured == happened

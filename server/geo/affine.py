"""平面图米制坐标 <-> WGS84 的共享转换。

与 ``web/src/utils/affine.js`` 是同一份公式的两个实现，两端读同一份
``tests/fixtures/georef/*.json``，差值要求 <= 1e-9 度。

坐标约定与 ``MapPreview.vue`` 一致：平面图局部坐标是米制、Y 轴向上，
原点 (x=0, y=0) 由 ``MapRegistration.origin_lat/origin_lon`` 锚到地面。
``rotation_deg`` 是平面图 +Y 轴顺时针偏离正北的角度。

正向（局部 -> 地面东北位移，theta 为 rotation_deg 的弧度值，k = scale）::

    E = k * ( x * cos(theta) + y * sin(theta))
    N = k * (-x * sin(theta) + y * cos(theta))
    lat = lat0 + degrees(N / M0)
    lon = lon0 + degrees(E / (N0 * cos(lat0)))

逆向用旋转矩阵的转置。``M0``/``N0`` 是 WGS84 在 lat0 处的子午圈与卯酉圈
曲率半径，即在原点做一次切平面近似：半径 2 km、|纬度| <= 60 度内相对
测地线的偏差上界约 0.7 m。高纬度切平面近似失效，
|lat0| > ``GEOREF_POLAR_LIMIT_DEG`` 直接拒绝。
"""
from __future__ import annotations

import math
from typing import Tuple

# WGS84 椭球
WGS84_A = 6378137.0                     # 长半轴 (m)
WGS84_F = 1.0 / 298.257223563           # 扁率
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)    # 第一偏心率平方

# 配准公式与阈值的唯一定义处；server/models.py 与 web/src/utils/affine.js 跟随它。
GEOREF_POLAR_LIMIT_DEG = 85.0


class GeoreferenceError(ValueError):
    """配准参数不可用（极区、非有限数、scale <= 0）。"""


def _check_finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise GeoreferenceError(f"{name} must be a finite number")
    return value


def validate_registration(registration) -> Tuple[float, float, float, float]:
    """把 registration（dict 或 MapRegistration）校验成四元组。"""
    if registration is None:
        raise GeoreferenceError("registration is required")
    if isinstance(registration, dict):
        get = registration.get
    else:
        get = lambda key, default=None: getattr(registration, key, default)  # noqa: E731

    lat0 = _check_finite("origin_lat", get("origin_lat"))
    lon0 = _check_finite("origin_lon", get("origin_lon"))
    rotation_deg = _check_finite("rotation_deg", get("rotation_deg", 0.0) or 0.0)
    scale = get("scale", 1.0)
    scale = _check_finite("scale", 1.0 if scale is None else scale)

    if not -90.0 <= lat0 <= 90.0:
        raise GeoreferenceError("origin_lat must be within [-90, 90]")
    if not -180.0 <= lon0 <= 180.0:
        raise GeoreferenceError("origin_lon must be within [-180, 180]")
    if abs(lat0) > GEOREF_POLAR_LIMIT_DEG:
        raise GeoreferenceError(
            f"georeferencing is refused above |lat| {GEOREF_POLAR_LIMIT_DEG} deg"
        )
    if scale <= 0:
        raise GeoreferenceError("scale must be > 0")
    return lat0, lon0, rotation_deg, scale


def curvature_radii(lat_deg: float) -> Tuple[float, float]:
    """返回 (M, N)：给定纬度处的子午圈半径与卯酉圈半径，单位米。"""
    phi = math.radians(lat_deg)
    s = math.sin(phi)
    w2 = 1.0 - WGS84_E2 * s * s
    w = math.sqrt(w2)
    n = WGS84_A / w
    m = WGS84_A * (1.0 - WGS84_E2) / (w2 * w)
    return m, n


def local_to_wgs84(x: float, y: float, registration) -> Tuple[float, float]:
    """平面图米制坐标 -> (lat, lon)，单位度。"""
    lat0, lon0, rotation_deg, k = validate_registration(registration)
    x = _check_finite("x", x)
    y = _check_finite("y", y)

    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    east = k * (x * cos_t + y * sin_t)
    north = k * (-x * sin_t + y * cos_t)

    m0, n0 = curvature_radii(lat0)
    cos_lat0 = math.cos(math.radians(lat0))

    lat = lat0 + math.degrees(north / m0)
    lon = lon0 + math.degrees(east / (n0 * cos_lat0))
    return lat, lon


def wgs84_to_local(lat: float, lon: float, registration) -> Tuple[float, float]:
    """(lat, lon) -> 平面图米制坐标，local_to_wgs84 的逆。"""
    lat0, lon0, rotation_deg, k = validate_registration(registration)
    lat = _check_finite("lat", lat)
    lon = _check_finite("lon", lon)

    m0, n0 = curvature_radii(lat0)
    cos_lat0 = math.cos(math.radians(lat0))

    north = math.radians(lat - lat0) * m0
    east = math.radians(lon - lon0) * n0 * cos_lat0

    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    x = (east * cos_t - north * sin_t) / k
    y = (east * sin_t + north * cos_t) / k
    return x, y


def is_registered(map_info) -> bool:
    """map_info（dict 或 WebUIMapInfo）是否带可用的配准参数。"""
    if map_info is None:
        return False
    reg = map_info.get("registration") if isinstance(map_info, dict) \
        else getattr(map_info, "registration", None)
    if reg is None:
        return False
    try:
        validate_registration(reg)
    except GeoreferenceError:
        return False
    return True

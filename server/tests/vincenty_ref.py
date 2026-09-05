"""Vincenty inverse solution — 独立于 server/geo/affine.py 的参照实现。

只用于给切平面近似做误差核对（评估脚本与测试共用），不进生产代码路径。
精度约 0.5 mm；对跖点附近不收敛，本项目用不到那种距离。
"""
import math

A = 6378137.0
F = 1.0 / 298.257223563
B = (1.0 - F) * A


def vincenty_distance_m(lat1, lon1, lat2, lon2, max_iter=200, tol=1e-14):
    """两点间椭球测地线长度，单位米。"""
    L = math.radians(lon2 - lon1)
    u1 = math.atan((1 - F) * math.tan(math.radians(lat1)))
    u2 = math.atan((1 - F) * math.tan(math.radians(lat2)))
    su1, cu1 = math.sin(u1), math.cos(u1)
    su2, cu2 = math.sin(u2), math.cos(u2)

    lam = L
    sin_sigma = cos_sigma = sigma = cos_sq_alpha = cos_2sigma_m = 0.0
    for _ in range(max_iter):
        sl, cl = math.sin(lam), math.cos(lam)
        sin_sigma = math.hypot(cu2 * sl, cu1 * su2 - su1 * cu2 * cl)
        if sin_sigma == 0.0:
            return 0.0
        cos_sigma = su1 * su2 + cu1 * cu2 * cl
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cu1 * cu2 * sl / sin_sigma
        cos_sq_alpha = 1.0 - sin_alpha * sin_alpha
        cos_2sigma_m = cos_sigma - 2 * su1 * su2 / cos_sq_alpha if cos_sq_alpha != 0 else 0.0
        c = F / 16 * cos_sq_alpha * (4 + F * (4 - 3 * cos_sq_alpha))
        prev = lam
        lam = L + (1 - c) * F * sin_alpha * (
            sigma + c * sin_sigma * (cos_2sigma_m + c * cos_sigma * (-1 + 2 * cos_2sigma_m ** 2))
        )
        if abs(lam - prev) < tol:
            break
    else:
        raise ValueError("Vincenty inverse did not converge")

    u_sq = cos_sq_alpha * (A * A - B * B) / (B * B)
    a_coef = 1 + u_sq / 16384 * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
    b_coef = u_sq / 1024 * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
    d_sigma = b_coef * sin_sigma * (
        cos_2sigma_m + b_coef / 4 * (
            cos_sigma * (-1 + 2 * cos_2sigma_m ** 2)
            - b_coef / 6 * cos_2sigma_m * (-3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos_2sigma_m ** 2)
        )
    )
    return B * a_coef * (sigma - d_sigma)

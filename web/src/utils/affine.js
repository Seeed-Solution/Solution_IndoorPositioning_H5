// 平面图米制坐标 <-> WGS84 的共享转换。
//
// 与 server/geo/affine.py 是同一份公式的两个实现，两端读同一份
// tests/fixtures/georef/*.json，差值要求 <= 1e-9 度。
//
// 坐标约定与 MapPreview.vue 一致：平面图局部坐标是米制、Y 轴向上，
// 原点 (x=0, y=0) 由 registration.origin_lat/origin_lon 锚到地面。
// rotation_deg 是平面图 +Y 轴顺时针偏离正北的角度。
//
// 正向（theta = rotation_deg 的弧度值，k = scale）：
//   E = k * ( x*cos(theta) + y*sin(theta))
//   N = k * (-x*sin(theta) + y*cos(theta))
//   lat = lat0 + degrees(N / M0)
//   lon = lon0 + degrees(E / (N0 * cos(lat0)))
// 逆向用旋转矩阵的转置。M0/N0 是 WGS84 在 lat0 处的子午圈与卯酉圈曲率半径，
// 即在原点做一次切平面近似：半径 2 km、|纬度| <= 60 度内相对测地线的偏差
// 上界约 0.7 m。高纬度切平面近似失效，|lat0| > GEOREF_POLAR_LIMIT_DEG 拒绝。

export const WGS84_A = 6378137.0;
export const WGS84_F = 1.0 / 298.257223563;
export const WGS84_E2 = WGS84_F * (2.0 - WGS84_F);

// 与 server/models.py / server/geo/affine.py 的同名常量保持一致。
export const GEOREF_POLAR_LIMIT_DEG = 85.0;

export class GeoreferenceError extends Error {
  constructor(message) {
    super(message);
    this.name = 'GeoreferenceError';
  }
}

const DEG = Math.PI / 180;

function checkFinite(name, value) {
  const v = Number(value);
  if (!Number.isFinite(v)) throw new GeoreferenceError(`${name} must be a finite number`);
  return v;
}

/** 校验 registration，返回 {lat0, lon0, rotationDeg, scale}；不合法抛 GeoreferenceError。 */
export function validateRegistration(registration) {
  if (!registration) throw new GeoreferenceError('registration is required');
  const lat0 = checkFinite('origin_lat', registration.origin_lat);
  const lon0 = checkFinite('origin_lon', registration.origin_lon);
  const rotationDeg = checkFinite('rotation_deg', registration.rotation_deg ?? 0);
  const scale = checkFinite('scale', registration.scale ?? 1);

  if (!(lat0 >= -90 && lat0 <= 90)) throw new GeoreferenceError('origin_lat must be within [-90, 90]');
  if (!(lon0 >= -180 && lon0 <= 180)) throw new GeoreferenceError('origin_lon must be within [-180, 180]');
  if (Math.abs(lat0) > GEOREF_POLAR_LIMIT_DEG) {
    throw new GeoreferenceError(`georeferencing is refused above |lat| ${GEOREF_POLAR_LIMIT_DEG} deg`);
  }
  if (!(scale > 0)) throw new GeoreferenceError('scale must be > 0');
  return { lat0, lon0, rotationDeg, scale };
}

/** 返回 [M, N]：给定纬度处的子午圈半径与卯酉圈半径，单位米。 */
export function curvatureRadii(latDeg) {
  const s = Math.sin(latDeg * DEG);
  const w2 = 1.0 - WGS84_E2 * s * s;
  const w = Math.sqrt(w2);
  const n = WGS84_A / w;
  const m = (WGS84_A * (1.0 - WGS84_E2)) / (w2 * w);
  return [m, n];
}

/** 平面图米制坐标 -> {lat, lon}，单位度。 */
export function localToWgs84(x, y, registration) {
  const { lat0, lon0, rotationDeg, scale } = validateRegistration(registration);
  const px = checkFinite('x', x);
  const py = checkFinite('y', y);

  const theta = rotationDeg * DEG;
  const cosT = Math.cos(theta);
  const sinT = Math.sin(theta);

  const east = scale * (px * cosT + py * sinT);
  const north = scale * (-px * sinT + py * cosT);

  const [m0, n0] = curvatureRadii(lat0);
  const cosLat0 = Math.cos(lat0 * DEG);

  return {
    lat: lat0 + (north / m0) / DEG,
    lon: lon0 + (east / (n0 * cosLat0)) / DEG,
  };
}

/** {lat, lon} -> 平面图米制坐标，localToWgs84 的逆。 */
export function wgs84ToLocal(lat, lon, registration) {
  const { lat0, lon0, rotationDeg, scale } = validateRegistration(registration);
  const plat = checkFinite('lat', lat);
  const plon = checkFinite('lon', lon);

  const [m0, n0] = curvatureRadii(lat0);
  const cosLat0 = Math.cos(lat0 * DEG);

  const north = (plat - lat0) * DEG * m0;
  const east = (plon - lon0) * DEG * n0 * cosLat0;

  const theta = rotationDeg * DEG;
  const cosT = Math.cos(theta);
  const sinT = Math.sin(theta);

  return {
    x: (east * cosT - north * sinT) / scale,
    y: (east * sinT + north * cosT) / scale,
  };
}

/** map 对象（dashboard_config.json 的 maps[].map）是否带可用的配准参数。 */
export function isRegistered(mapInfo) {
  if (!mapInfo || !mapInfo.registration) return false;
  try {
    validateRegistration(mapInfo.registration);
    return true;
  } catch (err) {
    return false;
  }
}

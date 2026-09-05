// 与 server/tests/test_geo_affine.py 读同一份 tests/fixtures/georef/*.json。
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { describe, it, expect } from 'vitest';

import {
  localToWgs84,
  wgs84ToLocal,
  validateRegistration,
  curvatureRadii,
  isRegistered,
  GeoreferenceError,
  GEOREF_POLAR_LIMIT_DEG,
} from '../src/utils/affine.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE_DIR = resolve(HERE, '../../tests/fixtures/georef');
const load = (name) => JSON.parse(readFileSync(resolve(FIXTURE_DIR, name), 'utf-8'));

const cases = load('cases.json');
const rejections = load('rejections.json');

describe('localToWgs84 matches the shared fixture', () => {
  cases.cases.forEach((c) => {
    it(`${c.name}: ${c.note}`, () => {
      c.points.forEach((p, i) => {
        const got = localToWgs84(p.x, p.y, c.registration);
        const want = c.expected[i];
        // 双端差 <= 1e-9 度 (~0.1 mm)
        expect(Math.abs(got.lat - want.lat)).toBeLessThanOrEqual(cases.tolerance_deg);
        expect(Math.abs(got.lon - want.lon)).toBeLessThanOrEqual(cases.tolerance_deg);
      });
    });
  });
});

describe('wgs84ToLocal round-trips within 1 mm', () => {
  cases.cases.forEach((c) => {
    it(c.name, () => {
      c.points.forEach((p, i) => {
        const back = wgs84ToLocal(c.expected[i].lat, c.expected[i].lon, c.registration);
        const d = Math.hypot(back.x - p.x, back.y - p.y);
        expect(d).toBeLessThanOrEqual(cases.roundtrip_tolerance_m);
      });
    });
  });
});

describe('rejections', () => {
  rejections.cases.forEach((c) => {
    it(c.name, () => {
      expect(() => validateRegistration(c.registration)).toThrow(GeoreferenceError);
      expect(() => localToWgs84(0, 0, c.registration)).toThrow(GeoreferenceError);
      expect(() => wgs84ToLocal(0, 0, c.registration)).toThrow(GeoreferenceError);
    });
  });

  it(`accepts exactly |lat| = ${GEOREF_POLAR_LIMIT_DEG}`, () => {
    expect(() => validateRegistration({ origin_lat: GEOREF_POLAR_LIMIT_DEG, origin_lon: 0 })).not.toThrow();
  });

  it('rejects non-finite input coordinates', () => {
    const reg = { origin_lat: 0, origin_lon: 0 };
    expect(() => localToWgs84(NaN, 0, reg)).toThrow(GeoreferenceError);
    expect(() => localToWgs84(0, Infinity, reg)).toThrow(GeoreferenceError);
  });
});

describe('geometry sanity', () => {
  const reg = { origin_lat: 22.5231, origin_lon: 113.9312, rotation_deg: 0, scale: 1 };

  it('rotation 0: +Y is north, +X is east', () => {
    const north = localToWgs84(0, 100, reg);
    expect(north.lat).toBeGreaterThan(reg.origin_lat);
    expect(north.lon).toBeCloseTo(reg.origin_lon, 12);
    const east = localToWgs84(100, 0, reg);
    expect(east.lon).toBeGreaterThan(reg.origin_lon);
    expect(east.lat).toBeCloseTo(reg.origin_lat, 12);
  });

  it('rotation +90 turns +Y clockwise onto east', () => {
    const p = localToWgs84(0, 100, { ...reg, rotation_deg: 90 });
    expect(p.lon).toBeGreaterThan(reg.origin_lon);
    expect(p.lat).toBeCloseTo(reg.origin_lat, 9);
  });

  it('rotation -90 turns +Y counter-clockwise onto west', () => {
    const p = localToWgs84(0, 100, { ...reg, rotation_deg: -90 });
    expect(p.lon).toBeLessThan(reg.origin_lon);
  });

  it('curvature radii are close to the mean earth radius', () => {
    const [m, n] = curvatureRadii(45);
    expect(m).toBeGreaterThan(6.3e6);
    expect(n).toBeGreaterThan(m);
  });

  it('isRegistered', () => {
    expect(isRegistered(null)).toBe(false);
    expect(isRegistered({})).toBe(false);
    expect(isRegistered({ registration: { origin_lat: 91, origin_lon: 0 } })).toBe(false);
    expect(isRegistered({ registration: { origin_lat: 22.5, origin_lon: 113.9 } })).toBe(true);
  });
});

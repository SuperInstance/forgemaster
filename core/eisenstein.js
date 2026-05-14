/**
 * Cocapn Core — Shared Eisenstein Integer Mathematics
 * ES Module, zero dependencies
 */

// ω = e^(2πi/3) = (-1 + i√3)/2
export const SQ3 = Math.sqrt(3);
export const PHI = (1 + SQ3) / 2; // not golden ratio — this is the Eisenstein unit magnitude

/**
 * Snap a floating-point (a, b) to nearest Eisenstein integer.
 * The Eisenstein integers Z[ω] have basis {1, ω} where ω = (-1+i√3)/2.
 * A point (a, b) represents a + bω.
 * 
 * Key: must check 3 candidates due to hexagonal (not square) Voronoi cells.
 */
export function e12_snap(a, b) {
  const ra = Math.round(a);
  const rb = Math.round(b);
  const candidates = [
    [ra, rb],
    [ra + 1, rb - 1],
    [ra - 1, rb + 1]
  ];
  let best = 0;
  let bestDist = e12_dist2(a, b, ra, rb);
  for (let i = 1; i < 3; i++) {
    const d = e12_dist2(a, b, candidates[i][0], candidates[i][1]);
    if (d < bestDist) { bestDist = d; best = i; }
  }
  return { a: candidates[best][0], b: candidates[best][1], dist: Math.sqrt(bestDist) };
}

/** Squared Euclidean distance in Eisenstein coordinate space */
export function e12_dist2(a1, b1, a2, b2) {
  const da = a1 - a2, db = b1 - b2;
  const dx = da - db * 0.5;
  const dy = db * SQ3 * 0.5;
  return dx * dx + dy * dy;
}

/** Eisenstein (a, b) → pixel coordinates */
export function e12_to_pixel(a, b, scale, ox, oy) {
  return {
    x: ox + (a - b * 0.5) * scale,
    y: oy - (b * SQ3 * 0.5) * scale
  };
}

/** Pixel coordinates → floating-point Eisenstein (a, b) */
export function pixel_to_e12(px, py, scale, ox, oy) {
  const x = (px - ox) / scale;
  const y = -(py - oy) / scale;
  const b = 2 * y / SQ3;
  const a = x + b * 0.5;
  return { a, b };
}

/** Weyl sector (0-5) from Eisenstein integer angle */
export function weyl_sector(a, b) {
  if (a === 0 && b === 0) return 0;
  const real = a - b * 0.5;
  const imag = b * SQ3 * 0.5;
  const angle = Math.atan2(imag, real);
  return Math.floor(((angle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2) / (Math.PI / 3));
}

/** Eisenstein norm N(a + bω) = a² - ab + b² */
export function e12_norm(a, b) {
  return a * a - a * b + b * b;
}

/** Eisenstein multiplication: (a₁+b₁ω)(a₂+b₂ω) */
export function e12_mul(a1, b1, a2, b2) {
  return {
    a: a1 * a2 - b1 * b2,
    b: a1 * b2 + b1 * a2 - b1 * b2
  };
}

/** Simulate Float32 rounding (IEEE 754 single precision) */
export function f32(val) {
  return Math.fround(val);
}

/** Compute ULP (unit in the last place) for a value in f32 */
export function f32_ulp(val) {
  const buf = new ArrayBuffer(4);
  const f32 = new Float32Array(buf);
  const u32 = new Uint32Array(buf);
  f32[0] = val;
  u32[0] += 1;
  return Math.abs(f32[0] - val);
}

/** Sector colors (Weyl chambers) */
export const SECTOR_COLORS = [
  '#f85149', '#3fb950', '#58a6ff',
  '#f59e0b', '#a855f7', '#00d4ff'
];

export const SECTOR_COLORS_FAINT = [
  'rgba(248,81,73,.18)', 'rgba(63,185,80,.18)', 'rgba(88,166,255,.18)',
  'rgba(245,158,11,.18)', 'rgba(168,85,247,.18)', 'rgba(0,212,255,.18)'
];

/** Pentatonic note frequencies for sonification (C pentatonic) */
export const SECTOR_FREQS = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25];

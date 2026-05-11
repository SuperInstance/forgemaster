/**
 * Eisenstein Integer Snap — A₂ Lattice
 *
 * The Eisenstein integer ring ℤ[ω] where ω = e^(2πi/3) is the
 * optimal attention compressor in 2D. It provides:
 *
 * - Densest packing — maximum information per snap
 * - Isotropic snap — no directional bias in attention
 * - PID (H¹ = 0) — no obstructions to composing attention across regions
 * - 6-fold symmetry — 6 directions of "close enough"
 *
 * @module
 */

import type { EisensteinInt } from './types.js';

/** ω = e^(2πi/3) = -1/2 + i√3/2 */
const SQRT3_2 = Math.sqrt(3) / 2;

/**
 * Create an Eisenstein integer a + bω.
 *
 * @param a - Coefficient of 1 (real part offset).
 * @param b - Coefficient of ω (imaginary axis basis).
 */
export function eisenstein(a: number, b: number): EisensteinInt {
  return { a: Math.round(a), b: Math.round(b) };
}

/**
 * Compute the norm of an Eisenstein integer: N(a + bω) = a² - ab + b².
 *
 * This is the square of the Euclidean distance from the origin.
 */
export function eisensteinNorm(z: EisensteinInt): number {
  return z.a * z.a - z.a * z.b + z.b * z.b;
}

/**
 * Convert Eisenstein integer to [x, y] coordinates.
 *
 * `a + bω → [a - b/2, b·√3/2]`
 */
export function eisensteinToXY(z: EisensteinInt): [number, number] {
  return [z.a - z.b / 2, z.b * SQRT3_2];
}

/**
 * Convert [x, y] coordinates to the nearest Eisenstein integer.
 *
 * This is the fundamental snap operation on the A₂ lattice:
 * project the point onto the Eisenstein lattice by rounding a, b.
 */
export function snapToEisenstein(point: [number, number]): EisensteinInt {
  const b = point[1] / SQRT3_2;
  const a = point[0] + b / 2;
  return { a: Math.round(a), b: Math.round(b) };
}

/**
 * Compute the distance from a point to the nearest Eisenstein lattice point.
 */
export function eisensteinDistance(
  point: [number, number]
): number {
  const snapped = snapToEisenstein(point);
  const xy = eisensteinToXY(snapped);
  return Math.sqrt(
    (point[0] - xy[0]) ** 2 + (point[1] - xy[1]) ** 2
  );
}

/**
 * Format an Eisenstein integer as a string: "a + bω".
 */
export function eisensteinToString(z: EisensteinInt): string {
  if (z.b === 0) return `${z.a}`;
  if (z.b < 0)
    return `${z.a} - ${Math.abs(z.b)}ω`;
  return `${z.a} + ${z.b}ω`;
}

/**
 * Check if two Eisenstein integers are equal.
 */
export function eisensteinEqual(
  a: EisensteinInt,
  b: EisensteinInt
): boolean {
  return a.a === b.a && a.b === b.b;
}

/**
 * Add two Eisenstein integers.
 */
export function eisensteinAdd(
  a: EisensteinInt,
  b: EisensteinInt
): EisensteinInt {
  return { a: a.a + b.a, b: a.b + b.b };
}

/**
 * Multiply two Eisenstein integers.
 *
 * (a + bω)(c + dω) = (ac - bd) + (ad + bc - bd)ω
 */
export function eisensteinMultiply(
  a: EisensteinInt,
  b: EisensteinInt
): EisensteinInt {
  const ac = a.a * b.a;
  const bd = a.b * b.b;
  return {
    a: ac - bd,
    b: a.a * b.b + a.b * b.a - bd,
  };
}

/**
 * Generate the 6 nearest neighbors of an Eisenstein integer
 * (the 6-fold symmetry of the A₂ lattice).
 */
export function eisensteinNeighbors(
  z: EisensteinInt
): EisensteinInt[] {
  return [
    { a: z.a + 1, b: z.b },
    { a: z.a - 1, b: z.b },
    { a: z.a, b: z.b + 1 },
    { a: z.a, b: z.b - 1 },
    { a: z.a + 1, b: z.b - 1 },
    { a: z.a - 1, b: z.b + 1 },
  ];
}

/**
 * Compute the hexagonal distance (number of steps on the A₂ lattice)
 * between two Eisenstein integers.
 */
export function eisensteinLatticeDistance(
  a: EisensteinInt,
  b: EisensteinInt
): number {
  const da = a.a - b.a;
  const db = a.b - b.b;
  // Hexagonal distance: max(|da|, |db|, |da - db|)
  return Math.max(Math.abs(da), Math.abs(db), Math.abs(da - db));
}

/**
 * Check if an Eisenstein integer is a unit (norm = 1).
 *
 * The units in ℤ[ω] are: ±1, ±ω, ±ω².
 */
export function isEisensteinUnit(z: EisensteinInt): boolean {
  return eisensteinNorm(z) === 1;
}

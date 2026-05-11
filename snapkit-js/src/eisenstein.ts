/**
 * Eisenstein integer snap algorithm.
 *
 * Provides EisensteinInteger value objects, rounding (naive + Voronoï),
 * snap operations, lattice distance, and fundamental-domain reduction.
 */

import { eisensteinSnapVoronoi, eisensteinToReal, snapDistance } from "./voronoi.js";
import type { EisensteinInteger as EisensteinInt, SnapResult } from "./types.js";

// Precomputed constants
const SQRT3 = Math.sqrt(3);
const HALF_SQRT3 = 0.5 * SQRT3;

// ---- Internal helpers --------------------------------------------------

function frozen<T extends Record<string, unknown>>(obj: T): Readonly<T> {
  return Object.freeze(obj);
}

// ---- EisensteinInteger factory -----------------------------------------

export interface EisensteinInteger extends EisensteinInt {}

/**
 * Create a frozen EisensteinInteger object.
 */
export function EisensteinInteger(a: number, b: number): EisensteinInteger {
  return frozen({ a, b });
}

// ---- Properties / methods (standalone, not on the object) ---------------

/** Convert to Cartesian complex as [real, imag]. */
export function toComplex(ei: EisensteinInteger): [number, number] {
  return [ei.a - 0.5 * ei.b, HALF_SQRT3 * ei.b];
}

/** Eisenstein norm squared: a² − ab + b². Always ≥ 0. */
export function normSquared(ei: EisensteinInteger): number {
  return ei.a * ei.a - ei.a * ei.b + ei.b * ei.b;
}

/** Euclidean magnitude. */
export function magnitude(ei: EisensteinInteger): number {
  return Math.sqrt(normSquared(ei));
}

/** Add two Eisenstein integers. */
export function add(left: EisensteinInteger, right: EisensteinInteger): EisensteinInteger {
  return EisensteinInteger(left.a + right.a, left.b + right.b);
}

/** Subtract two Eisenstein integers. */
export function sub(left: EisensteinInteger, right: EisensteinInteger): EisensteinInteger {
  return EisensteinInteger(left.a - right.a, left.b - right.b);
}

/** Multiply two Eisenstein integers. */
export function mul(left: EisensteinInteger, right: EisensteinInteger): EisensteinInteger {
  const { a, b } = left;
  const c = right.a, d = right.b;
  return EisensteinInteger(a * c - b * d, a * d + b * c - b * d);
}

/** Galois conjugate: (a+b) − bω. */
export function conjugate(ei: EisensteinInteger): EisensteinInteger {
  return EisensteinInteger(ei.a + ei.b, -ei.b);
}

// ---- Coordinate conversion ----------------------------------------------

/** Convert Cartesian (x, y) to Eisenstein coordinate floats (a, b). */
function toEisensteinCoords(x: number, y: number): [number, number] {
  const bFloat = 2.0 * y / SQRT3;
  const aFloat = x + bFloat * 0.5;
  return [aFloat, bFloat];
}

// ---- Rounding -----------------------------------------------------------

/**
 * Naive rounding — checks 4 floor-adjacent candidates.
 * Kept for comparison; prefer `eisensteinRound` for guaranteed nearest.
 */
export function eisensteinRoundNaive(x: number, y: number): EisensteinInteger {
  const [aFloat, bFloat] = toEisensteinCoords(x, y);
  const aFloor = Math.floor(aFloat);
  const bFloor = Math.floor(bFloat);

  let bestDist = Infinity;
  const tied: Array<[number, number, number, number]> = [];

  for (let da = 0; da <= 1; da++) {
    for (let db = 0; db <= 1; db++) {
      const a = aFloor + da;
      const b = bFloor + db;
      const [cx, cy] = eisensteinToReal(a, b);
      const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
      if (dist < bestDist - 1e-9) {
        bestDist = dist;
        tied.length = 0;
        tied.push([Math.abs(a), Math.abs(b), a, b]);
      } else if (Math.abs(dist - bestDist) < 1e-9) {
        tied.push([Math.abs(a), Math.abs(b), a, b]);
      }
    }
  }

  tied.sort((l, r) => (l[0] - r[0]) || (l[1] - r[1]));
  return EisensteinInteger(tied[0][2], tied[0][3]);
}

/**
 * Round (x, y) to the nearest Eisenstein integer using Voronoï snap.
 */
export function eisensteinRound(x: number, y: number): EisensteinInteger {
  const [a, b] = eisensteinSnapVoronoi(x, y);
  return EisensteinInteger(a, b);
}

// ---- Snap operations ----------------------------------------------------

/**
 * Snap a Cartesian point to the nearest Eisenstein lattice point.
 */
export function eisensteinSnap(
  x: number,
  y: number,
  tolerance: number = 0.5,
): SnapResult {
  const nearest = eisensteinRound(x, y);
  const [cx, cy] = toComplex(nearest);
  const distance = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
  return frozen({
    nearest,
    distance,
    isSnap: distance <= tolerance,
  });
}

/**
 * Vectorized snap for multiple points.
 */
export function eisensteinSnapBatch(
  points: Array<[number, number]>,
  tolerance: number = 0.5,
): SnapResult[] {
  return points.map(([x, y]) => eisensteinSnap(x, y, tolerance));
}

/**
 * Eisenstein lattice distance between two Cartesian points.
 */
export function eisensteinDistance(
  x1: number, y1: number,
  x2: number, y2: number,
): number {
  const dx = x1 - x2;
  const dy = y1 - y2;
  const nearest = eisensteinRound(dx, dy);
  const [cx, cy] = toComplex(nearest);
  const residual = Math.sqrt((dx - cx) ** 2 + (dy - cy) ** 2);
  return Math.sqrt(normSquared(nearest)) + residual;
}

/**
 * Reduce a point to its canonical representative in the fundamental domain.
 * Returns [bestUnit, reducedEisenstein].
 */
export function eisensteinFundamentalDomain(
  x: number, y: number,
): [EisensteinInteger, EisensteinInteger] {
  const units: EisensteinInteger[] = [
    EisensteinInteger(1, 0),
    EisensteinInteger(0, 1),
    EisensteinInteger(-1, 1),
    EisensteinInteger(-1, 0),
    EisensteinInteger(0, -1),
    EisensteinInteger(1, -1),
  ];
  const targetAngle = Math.PI / 6;

  let bestUnit = units[0];
  let bestAngle = Infinity;

  for (const u of units) {
    const conjU = conjugate(u);
    const [ux, uy] = toComplex(conjU);
    const rx = x * ux - y * uy;
    const ry = x * uy + y * ux;
    const angle = Math.abs(Math.atan2(ry, rx) - targetAngle);
    if (angle < bestAngle) {
      bestAngle = angle;
      bestUnit = u;
    }
  }

  const bestConj = conjugate(bestUnit);
  const [ux, uy] = toComplex(bestConj);
  const rx = x * ux - y * uy;
  const ry = x * uy + y * ux;
  return [bestUnit, eisensteinRound(rx, ry)];
}

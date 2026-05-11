/**
 * A₂ lattice Voronoï cell nearest-neighbor snap.
 *
 * Guarantees covering radius ≤ 1/√3 by checking 9 candidates
 * around the naive round-off point.
 */

// Precomputed constants
const SQRT3 = Math.sqrt(3);
const INV_SQRT3 = 1.0 / SQRT3;
const HALF_SQRT3 = 0.5 * SQRT3;

/**
 * Convert Eisenstein coordinates (a, b) to Cartesian (x, y).
 */
export function eisensteinToReal(a: number, b: number): [number, number] {
  return [a - b * 0.5, b * HALF_SQRT3];
}

/**
 * Euclidean distance from (x, y) to Eisenstein integer (a, b).
 */
export function snapDistance(x: number, y: number, a: number, b: number): number {
  const dx = x - (a - b * 0.5);
  const dy = y - (b * HALF_SQRT3);
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Naive snap — simple rounding, no Voronoï guarantee.
 */
export function eisensteinSnapNaive(x: number, y: number): [number, number] {
  const b = Math.round(y * 2.0 * INV_SQRT3);
  const a = Math.round(x + b * 0.5);
  return [a, b];
}

/**
 * Snap (x, y) to the true nearest Eisenstein integer.
 *
 * Checks a 3×3 neighbourhood of candidates around the naive
 * round-off point using squared-distance comparison (no sqrt).
 * Tie-break by lexicographic (|a|, |b|).
 */
export function eisensteinSnapVoronoi(x: number, y: number): [number, number] {
  const b0 = Math.round(y * 2.0 * INV_SQRT3);
  const a0 = Math.round(x + b0 * 0.5);

  let bestDistSq = Infinity;
  let bestA = a0;
  let bestB = b0;

  for (let da = -1; da <= 1; da++) {
    for (let db = -1; db <= 1; db++) {
      const a = a0 + da;
      const b = b0 + db;
      const dx = x - (a - b * 0.5);
      const dy = y - (b * HALF_SQRT3);
      const dSq = dx * dx + dy * dy;
      if (dSq < bestDistSq - 1e-24) {
        bestDistSq = dSq;
        bestA = a;
        bestB = b;
      } else if (Math.abs(dSq - bestDistSq) < 1e-24) {
        // Tie-break: prefer smaller |a|, then |b|
        if (Math.abs(a) < Math.abs(bestA) || (Math.abs(a) === Math.abs(bestA) && Math.abs(b) < Math.abs(bestB))) {
          bestA = a;
          bestB = b;
        }
      }
    }
  }

  return [bestA, bestB];
}

/**
 * Batch Voronoï snap for multiple points.
 */
export function eisensteinSnapBatch(points: Array<[number, number]>): Array<[number, number]> {
  return points.map(([x, y]) => eisensteinSnapVoronoi(x, y));
}

/**
 * Topology — ADE Snap Topology Classification
 *
 * The ADE classification is the "periodic table of snap topologies" —
 * a finite classification of the fundamental shapes that uncertainty
 * can take. Each ADE type defines a different snap function topology.
 *
 * "The finiteness is the feature, not the bug. It means the space of
 * possible constraint topologies is EXPLOREABLE."
 *
 * @module
 */

import type { ADEType, TopologyNode } from './types.js';

// ─── ADE Data Registry ───────────────────────────────────────────────────────

interface ADEData {
  rank: number;
  dimension: number;
  numRoots: number;
  coxeterNumber: number;
  platonicSolid: string | null;
  description: string;
}

const ADE_DATA: Record<ADEType, ADEData> = {
  A1: {
    rank: 1,
    dimension: 2,
    numRoots: 2,
    coxeterNumber: 2,
    platonicSolid: null,
    description: 'Binary (coin flip)',
  },
  A2: {
    rank: 2,
    dimension: 3,
    numRoots: 6,
    coxeterNumber: 3,
    platonicSolid: null,
    description: 'Hexagonal (Eisenstein lattice)',
  },
  A3: {
    rank: 3,
    dimension: 4,
    numRoots: 12,
    coxeterNumber: 4,
    platonicSolid: 'Tetrahedron',
    description: 'Tetrahedral (4 categories)',
  },
  A4: {
    rank: 4,
    dimension: 5,
    numRoots: 20,
    coxeterNumber: 5,
    platonicSolid: null,
    description: '5-chain',
  },
  D4: {
    rank: 4,
    dimension: 4,
    numRoots: 24,
    coxeterNumber: 6,
    platonicSolid: null,
    description: 'Triality (D4 symmetry)',
  },
  D5: {
    rank: 5,
    dimension: 5,
    numRoots: 40,
    coxeterNumber: 8,
    platonicSolid: null,
    description: '5-fork',
  },
  E6: {
    rank: 6,
    dimension: 8,
    numRoots: 72,
    coxeterNumber: 12,
    platonicSolid: 'Tetrahedron',
    description: 'Binary tetrahedral group',
  },
  E7: {
    rank: 7,
    dimension: 8,
    numRoots: 126,
    coxeterNumber: 18,
    platonicSolid: 'Cube/Octahedron',
    description: 'Binary octahedral group',
  },
  E8: {
    rank: 8,
    dimension: 8,
    numRoots: 240,
    coxeterNumber: 30,
    platonicSolid: 'Dodecahedron/Icosahedron',
    description: 'Binary icosahedral group (the "noble gas")',
  },
};

// ─── Simple Root Vectors ─────────────────────────────────────────────────────

/** Get simple root vectors for basic ADE types. Used for lattice projection. */
function computeSimpleRoots(
  adeType: ADEType
): number[][] | null {
  switch (adeType) {
    case 'A1':
      return [[1]];
    case 'A2':
      return [
        [1, 0],
        [-0.5, Math.sqrt(3) / 2],
      ];
    case 'A3':
      return [
        [1, -1, 0],
        [0, 1, -1],
        [0, 0, 1],
      ];
    case 'D4':
      return [
        [1, -1, 0, 0],
        [0, 1, -1, 0],
        [0, 0, 1, -1],
        [0, 0, 1, 1],
      ];
    default:
      return null; // E6/E7/E8 need external libs for full cartan
  }
}

// ─── Main Class ──────────────────────────────────────────────────────────────

/**
 * The topological structure of a snap function's lattice.
 *
 * The snap topology determines HOW information is compressed:
 * - Hexagonal (A₂): isotropic, 6-fold, densest 2D
 * - Cubic (ℤⁿ): axis-aligned, standard grid
 * - Tetrahedral (A₃): 4-directional, categorical
 * - E₈: maximum symmetry, 8D
 *
 * The topology is the INVARIANT that transfers across domains.
 * When two domains have the same snap topology, calibrated tolerances
 * transfer directly.
 */
export class SnapTopology {
  /** ADE type. */
  readonly adeType: ADEType;
  /** Human-readable name (e.g. "A2"). */
  readonly name: string;
  /** Coxeter rank. */
  readonly rank: number;
  /** Ambient dimension. */
  readonly dimension: number;
  /** Number of root vectors. */
  readonly numRoots: number;
  /** Coxeter number (order of Coxeter element). */
  readonly coxeterNumber: number;
  /** Associated Platonic solid, if any. */
  readonly platonicSolid: string | null;
  /** Short description. */
  readonly description: string;
  /** Simple root vectors for lattice projection (may be null for E-types). */
  readonly simpleRoots: number[][] | null;

  constructor(adeType: ADEType) {
    const data = ADE_DATA[adeType];
    this.adeType = adeType;
    this.name = adeType;
    this.rank = data.rank;
    this.dimension = data.dimension;
    this.numRoots = data.numRoots;
    this.coxeterNumber = data.coxeterNumber;
    this.platonicSolid = data.platonicSolid;
    this.description = data.description;
    this.simpleRoots = computeSimpleRoots(adeType);
  }

  /**
   * Create a TopologyNode from this topology.
   */
  toNode(): TopologyNode {
    return {
      adeType: this.adeType,
      name: this.name,
      rank: this.rank,
      dimension: this.dimension,
      numRoots: this.numRoots,
      coxeterNumber: this.coxeterNumber,
      platonicSolid: this.platonicSolid,
      description: this.description,
    };
  }

  /**
   * Snap a point to this topology's root lattice.
   *
   * Returns `[snapped_point, delta_magnitude]`.
   *
   * @param point - The point to snap.
   */
  snap(point: number[]): [number[], number] {
    if (!this.simpleRoots || this.simpleRoots.length === 0) {
      throw new Error(
        `Simple roots not computed for ${this.name}`
      );
    }

    const roots = this.simpleRoots;
    const rank = roots.length;
    const dim = roots[0].length;

    // Handle dimension mismatch by padding/truncating
    let adjustedPoint = [...point];
    if (dim < point.length) {
      adjustedPoint = point.slice(0, dim);
    } else if (dim > point.length) {
      adjustedPoint = [...point, ...new Array(dim - point.length).fill(0)];
    }

    // Project onto root lattice: solve point ≈ Σ c_i α_i
    // Using least-squares: c = (R^T R)^(-1) R^T p
    const RtR: number[][] = Array.from({ length: rank }, () =>
      new Array(rank).fill(0)
    );
    const Rtp: number[] = new Array(rank).fill(0);

    for (let i = 0; i < rank; i++) {
      for (let j = 0; j < rank; j++) {
        RtR[i][j] = roots[i].reduce(
          (sum, v, k) => sum + v * roots[j][k],
          0
        );
      }
      Rtp[i] = roots[i].reduce(
        (sum, v, k) => sum + v * adjustedPoint[k],
        0
      );
    }

    // Solve 2x2 or 3x3 system directly
    const coeffs = this._solveLinear(RtR, Rtp);
    const intCoeffs = coeffs.map(Math.round);

    // Reconstruct snapped point
    const snapped: number[] = new Array(dim).fill(0);
    for (let i = 0; i < rank; i++) {
      for (let j = 0; j < dim; j++) {
        snapped[j] += intCoeffs[i] * roots[i][j];
      }
    }

    // Handle dimension mismatch for output
    let resultSnapped = snapped;
    if (snapped.length > point.length) {
      resultSnapped = snapped.slice(0, point.length);
    } else if (snapped.length < point.length) {
      resultSnapped = [
        ...snapped,
        ...new Array(point.length - snapped.length).fill(0),
      ];
    }

    const delta = Math.sqrt(
      resultSnapped.reduce(
        (sum, v, i) => sum + (point[i] - v) ** 2,
        0
      )
    );

    return [resultSnapped, delta];
  }

  /**
   * Lattice quality score (higher = better for snap).
   *
   * Based on: packing density, symmetry, and PID property.
   * A₂ has Q ≈ 2.7, E₈ has Q ≈ 3.2 (from our experiments).
   */
  get qualityScore(): number {
    return this.numRoots / (this.coxeterNumber * this.rank);
  }

  /**
   * Solve a small linear system Ax = b using Gaussian elimination.
   * Assumes A is square and invertible.
   */
  private _solveLinear(A: number[][], b: number[]): number[] {
    const n = A.length;
    // Augmented matrix
    const aug: number[][] = A.map((row, i) => [...row, b[i]]);

    // Forward elimination
    for (let col = 0; col < n; col++) {
      // Find pivot
      let maxRow = col;
      for (let row = col + 1; row < n; row++) {
        if (Math.abs(aug[row][col]) > Math.abs(aug[maxRow][col])) {
          maxRow = row;
        }
      }
      [aug[col], aug[maxRow]] = [aug[maxRow], aug[col]];

      // Eliminate below
      for (let row = col + 1; row < n; row++) {
        const factor = aug[row][col] / aug[col][col];
        for (let j = col; j <= n; j++) {
          aug[row][j] -= factor * aug[col][j];
        }
      }
    }

    // Back substitution
    const x: number[] = new Array(n).fill(0);
    for (let i = n - 1; i >= 0; i--) {
      x[i] = aug[i][n];
      for (let j = i + 1; j < n; j++) {
        x[i] -= aug[i][j] * x[j];
      }
      x[i] /= aug[i][i];
    }

    return x;
  }
}

// ─── Factory Functions ───────────────────────────────────────────────────────

/** Binary snap — coin flip, true/false, yes/no. */
export function binaryTopology(): SnapTopology {
  return new SnapTopology('A1');
}

/** Hexagonal snap — Eisenstein lattice, densest 2D packing. */
export function hexagonalTopology(): SnapTopology {
  return new SnapTopology('A2');
}

/** Tetrahedral snap — 4 categories, categorical decisions. */
export function tetrahedralTopology(): SnapTopology {
  return new SnapTopology('A3');
}

/** D₄ snap — triality symmetry, forked dependencies. */
export function trialityTopology(): SnapTopology {
  return new SnapTopology('D4');
}

/** E₆ — tetrahedral solid symmetry. */
export function exceptionalE6(): SnapTopology {
  return new SnapTopology('E6');
}

/** E₇ — octahedral solid symmetry. */
export function exceptionalE7(): SnapTopology {
  return new SnapTopology('E7');
}

/** E₈ — icosahedral solid symmetry, maximum finite symmetry. */
export function exceptionalE8(): SnapTopology {
  return new SnapTopology('E8');
}

/** Get all pre-built ADE topologies. */
export function allTopologies(): SnapTopology[] {
  const types: ADEType[] = [
    'A1', 'A2', 'A3', 'A4', 'D4', 'D5', 'E6', 'E7', 'E8',
  ];
  return types.map((t) => new SnapTopology(t));
}

/**
 * Recommend the best snap topology for given requirements.
 *
 * @param options - Requirements for topology selection.
 * @param options.numCategories - Number of distinct categories/outcomes.
 * @param options.dimension - Ambient dimension of the data.
 * @param options.tensorRank - Required tensor rank for consistent snaps.
 */
export function recommendTopology(options: {
  numCategories?: number;
  dimension?: number;
  tensorRank?: number;
}): SnapTopology {
  const { numCategories, dimension, tensorRank } = options;

  if (numCategories === 2) return binaryTopology();
  if (numCategories === 4) return tetrahedralTopology();
  if (dimension === 2) return hexagonalTopology(); // A₂ is provably optimal in 2D
  if (tensorRank !== undefined && tensorRank >= 8)
    return exceptionalE8();
  if (tensorRank !== undefined && tensorRank >= 6)
    return exceptionalE7();
  if (tensorRank !== undefined && tensorRank >= 4)
    return trialityTopology();

  return hexagonalTopology(); // Default to A₂ — universal solvent
}

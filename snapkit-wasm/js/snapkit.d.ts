/**
 * @superinstance/snapkit-wasm — TypeScript declarations
 *
 * Eisenstein lattice snap operations compiled to WebAssembly.
 */

export interface SnapResult {
  /** Eisenstein integer a-coordinate */
  a: number;
  /** Eisenstein integer b-coordinate */
  b: number;
  /** Snapped Cartesian x (= a − b/2) */
  snappedX: number;
  /** Snapped Cartesian y (= b·√3/2) */
  snappedY: number;
  /** Euclidean distance from input to snapped point */
  distance: number;
}

export interface BeatResult {
  /** Snapped beat time */
  snappedTime: number;
  /** Offset from original time */
  offset: number;
  /** Beat index in the grid */
  beatIndex: number;
  /** Phase within the beat period [0, 1) */
  phase: number;
}

export interface Point2D {
  x: number;
  y: number;
}

export declare class SnapKit {
  /**
   * Load and instantiate the WASM module.
   * @param source - URL string, URL object, ArrayBuffer, or precompiled WebAssembly.Module
   * @returns Promise resolving to a ready-to-use SnapKit instance
   */
  static init(source: string | URL | ArrayBuffer | WebAssembly.Module): Promise<SnapKit>;

  /**
   * Snap a point to the nearest Eisenstein integer (optimal O(1) Voronoi correction).
   * Uses the branchless 6-condition cascade — ~15 FP ops, no 3×3 search.
   */
  eisensteinSnap(x: number, y: number): SnapResult;

  /**
   * Snap with guaranteed Voronoï nearest neighbor.
   * Uses the 3×3 neighborhood search — O(9) but proven correct for all inputs.
   */
  eisensteinSnapVoronoi(x: number, y: number): SnapResult;

  /**
   * Batch snap multiple points at once.
   * More efficient than individual snaps due to reduced JS→WASM call overhead.
   */
  eisensteinSnapBatch(points: Point2D[]): SnapResult[];

  /**
   * Covering radius of the Eisenstein (A₂) lattice: 1/√3 ≈ 0.57735.
   * Any point in the plane is within this distance of some lattice point.
   */
  coveringRadius(): number;

  /**
   * Snap a timestamp to the nearest beat in a periodic grid.
   */
  beatGridSnap(t: number, period: number): BeatResult;

  /**
   * Batch snap multiple timestamps to a beat grid.
   */
  beatGridSnapBatch(timestamps: number[], period: number): BeatResult[];
}

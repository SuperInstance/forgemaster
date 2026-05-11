/**
 * SnapFunction — Tolerance-Based Compression
 *
 * The snap function maps continuous values to discrete expected points,
 * compressing "close enough to expected" into background and flagging
 * what exceeds tolerance as a delta demanding attention.
 *
 * "Everything within tolerance is compressed away. Only the deltas survive."
 *
 * @module
 */

import type { SnapResult, SnapTopologyType, SnapOptions } from './types.js';

/**
 * Tolerance-based compression of information.
 *
 * Maps incoming values to their nearest expected point (lattice point).
 * Values within tolerance are compressed ("snapped") to the expected point.
 * Values exceeding tolerance are flagged as deltas demanding attention.
 *
 * The snap function IS the gatekeeper of attention. It determines what
 * reaches consciousness and what is compressed away.
 *
 * @example
 * ```ts
 * const snap = new SnapFunction({ tolerance: 0.1 });
 * snap.snap(0.05); // Within tolerance → snap to 0.0
 * snap.snap(0.3);  // Exceeds tolerance → delta detected
 * ```
 */
export class SnapFunction {
  /** Maximum distance within which values are snapped to expected. */
  tolerance: number;
  /** The snap topology (determines the lattice shape). */
  topology: SnapTopologyType;
  /** Current expected baseline value. */
  baseline: number;
  /** How fast the baseline adapts to new data [0..1]. */
  adaptationRate: number;

  private _history: SnapResult[] = [];
  private _snapCount = 0;
  private _deltaCount = 0;

  constructor(options: SnapOptions = {}) {
    this.tolerance = options.tolerance ?? 0.1;
    this.topology = options.topology ?? 'hexagonal';
    this.baseline = options.baseline ?? 0;
    this.adaptationRate = options.adaptationRate ?? 0.01;
  }

  /**
   * Snap a value to the nearest expected point.
   *
   * @param value - The observed value to snap.
   * @param expected - Override the baseline expected value.
   * @returns A SnapResult with snapped value, delta, and tolerance check.
   */
  snap(value: number, expected?: number): SnapResult {
    const exp = expected ?? this.baseline;
    const delta = Math.abs(value - exp);
    const within = delta <= this.tolerance;
    const snapped = within ? exp : value;

    const result: SnapResult = {
      original: value,
      snapped,
      delta,
      withinTolerance: within,
      tolerance: this.tolerance,
      topology: this.topology,
    };

    this._history.push(result);
    if (within) {
      this._snapCount++;
    } else {
      this._deltaCount++;
    }

    // Adapt baseline (only on non-delta observations)
    if (within && this.adaptationRate > 0) {
      this.baseline += this.adaptationRate * (value - this.baseline);
    }

    return result;
  }

  /**
   * Alias for {@link snap}.
   */
  observe(value: number): SnapResult {
    return this.snap(value);
  }

  /**
   * Snap a vector of values.
   *
   * @param values - Array of values to snap.
   * @param expected - Optional array of expected values (same length). Defaults to baseline.
   * @returns Array of SnapResults.
   */
  snapVector(values: number[], expected?: number[]): SnapResult[] {
    return values.map((v, i) => this.snap(v, expected?.[i]));
  }

  /**
   * Snap a 2D point using the Eisenstein lattice (A₂ topology).
   *
   * The Eisenstein lattice ℤ[ω] where ω = e^(2πi/3) provides:
   * - Densest packing in 2D
   * - 6-fold symmetry (isotropic compression)
   * - PID property → H¹ = 0 guarantee
   *
   * This converts a 2D point `[x, y]` to its nearest Eisenstein integer.
   *
   * @param point - 2D point as [x, y].
   * @param tol - Optional tolerance override.
   * @returns SnapResult where snapped is the distance to nearest lattice point.
   */
  snapEisenstein(point: [number, number], tol?: number): SnapResult {
    const t = tol ?? this.tolerance;
    const sqrt3_2 = Math.sqrt(3) / 2;

    // Solve: point = a + b*ω where a,b ∈ ℤ
    // ω = -1/2 + i√3/2
    // So x = a - b/2, y = b*√3/2
    const b = point[1] / sqrt3_2;
    const a = point[0] + b / 2;

    const aInt = Math.round(a);
    const bInt = Math.round(b);

    const snappedX = aInt - bInt / 2;
    const snappedY = bInt * sqrt3_2;

    const delta = Math.sqrt(
      (point[0] - snappedX) ** 2 + (point[1] - snappedY) ** 2
    );
    const within = delta <= t;

    // Snap to expected if within tolerance
    const snappedMagnitude = within ? 0 : delta;

    const result: SnapResult = {
      original: Math.sqrt(point[0] ** 2 + point[1] ** 2),
      snapped: snappedMagnitude,
      delta,
      withinTolerance: within,
      tolerance: t,
      topology: 'hexagonal',
    };

    this._history.push(result);
    if (within) this._snapCount++;
    else this._deltaCount++;

    return result;
  }

  /**
   * Auto-calibrate tolerance to achieve the target snap rate.
   *
   * This is the snap calibration that distinguishes expert from novice:
   * the tolerance is adjusted so that exactly the right fraction of
   * observations snap to "expected" and the rest demand attention.
   *
   * @param values - Sample of typical values to calibrate on.
   * @param targetSnapRate - Desired fraction of snaps (0.9 = 90% within tolerance).
   */
  calibrate(values: number[], targetSnapRate: number = 0.9): void {
    if (values.length === 0) return;

    // Set baseline to mean
    this.baseline = values.reduce((a, b) => a + b, 0) / values.length;

    // Compute distances from baseline
    const distances = values
      .map((v) => Math.abs(v - this.baseline))
      .sort((a, b) => a - b);

    // Set tolerance so targetSnapRate fraction are within it
    const idx = Math.min(
      Math.floor(distances.length * targetSnapRate),
      distances.length - 1
    );
    this.tolerance = distances[idx];
  }

  // ─── Statistics ────────────────────────────────────────────────────────────

  /** Fraction of observations that snapped (within tolerance). */
  get snapRate(): number {
    const total = this._snapCount + this._deltaCount;
    return total > 0 ? this._snapCount / total : 0;
  }

  /** Fraction of observations that exceeded tolerance (deltas). */
  get deltaRate(): number {
    return 1 - this.snapRate;
  }

  /**
   * How well-calibrated the snap tolerance is.
   *
   * 0.0 = no snaps (tolerance too tight → anxiety)
   * 1.0 = all snaps (tolerance too loose → complacency)
   * ~0.9 = well-calibrated (most things are expected, deltas are rare)
   */
  get calibration(): number {
    return this.snapRate;
  }

  /** Summary statistics of the snap function's history. */
  get statistics(): Record<string, number | string> {
    if (this._history.length === 0) {
      return { totalObservations: 0 };
    }

    const deltas = this._history.map((r) => r.delta);
    const meanDelta =
      deltas.reduce((a, b) => a + b, 0) / deltas.length;

    return {
      totalObservations: this._history.length,
      snapCount: this._snapCount,
      deltaCount: this._deltaCount,
      snapRate: this.snapRate,
      meanDelta,
      maxDelta: Math.max(...deltas),
      calibration: this.calibration,
      currentBaseline: this.baseline,
      tolerance: this.tolerance,
    };
  }

  /**
   * Reset snap function state.
   *
   * @param baseline - Optional new baseline value.
   */
  reset(baseline?: number): void {
    if (baseline !== undefined) this.baseline = baseline;
    this._history = [];
    this._snapCount = 0;
    this._deltaCount = 0;
  }
}

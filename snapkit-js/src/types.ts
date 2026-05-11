/**
 * snapkit types — all public return types.
 */

/** An Eisenstein integer a + bω where a, b ∈ Z. */
export interface EisensteinInteger {
  readonly a: number;
  readonly b: number;
}

/** Result of snapping a complex number to the Eisenstein lattice. */
export interface SnapResult {
  readonly nearest: EisensteinInteger;
  readonly distance: number;
  readonly isSnap: boolean;
}

/** Result of a temporal snap operation. */
export interface TemporalResult {
  readonly originalTime: number;
  readonly snappedTime: number;
  readonly offset: number;
  readonly isOnBeat: boolean;
  readonly isTMinus0: boolean;
  readonly beatIndex: number;
  readonly beatPhase: number;
}

/** Summary of spectral analysis on a signal. */
export interface SpectralSummary {
  readonly entropyBits: number;
  readonly hurst: number;
  readonly autocorrLag1: number;
  readonly autocorrDecay: number;
  readonly isStationary: boolean;
}

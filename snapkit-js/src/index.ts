/**
 * @superinstance/snapkit — Eisenstein lattice snap + temporal + spectral.
 *
 * Zero-dependency TypeScript library.
 */

// Types
export type { EisensteinInteger, SnapResult, TemporalResult, SpectralSummary } from "./types.js";

// Eisenstein core
export {
  EisensteinInteger,
  toComplex,
  normSquared,
  magnitude,
  add,
  sub,
  mul,
  conjugate,
  eisensteinRoundNaive,
  eisensteinRound,
  eisensteinSnap,
  eisensteinSnapBatch,
  eisensteinDistance,
  eisensteinFundamentalDomain,
} from "./eisenstein.js";

// Voronoï snap
export {
  eisensteinToReal,
  snapDistance,
  eisensteinSnapNaive as eisensteinSnapNaiveVoronoi,
  eisensteinSnapVoronoi,
  eisensteinSnapBatch as eisensteinSnapBatchVoronoi,
} from "./voronoi.js";

// Temporal
export { BeatGrid, TemporalSnap } from "./temporal.js";

// Spectral
export {
  entropy,
  autocorrelation,
  hurstExponent,
  spectralSummary,
  spectralBatch,
} from "./spectral.js";

/**
 * Core type definitions for @snapkit/core.
 *
 * These types define the interfaces for snap-based attention allocation —
 * a tolerance-compressed information processing system that tells cognition
 * where to focus by detecting what exceeds expected patterns.
 *
 * @packageDocumentation
 */

/** Supported snap topologies — each a different "flavor of randomness". */
export type SnapTopologyType =
  | 'binary'       // Coin flip — 2 outcomes
  | 'hexagonal'    // A₂ Eisenstein — 6-fold, densest 2D
  | 'cubic'        // ℤⁿ — standard grid
  | 'octahedral'   // 8 directions, ±axes
  | 'uniform'      // dN — uniform spread
  | 'bell';        // 2d6 — peaked distribution

/** Snap severity levels. */
export type DeltaSeverity = 'none' | 'low' | 'medium' | 'high' | 'critical';

/** Learning phases in the expertise cycle. */
export type LearningPhase =
  | 'delta_flood'     // No scripts — everything is novel
  | 'script_burst'    // Patterns emerging — rapid script creation
  | 'smooth_running'  // Most things snap to scripts — low load
  | 'disruption'      // Accumulated deltas — scripts failing
  | 'rebuilding';     // Constructing new scripts from deltas

/** Script lifecycle status. */
export type ScriptStatus = 'draft' | 'active' | 'degraded' | 'archived';

/** ADE root system classification — the "periodic table" of snap topologies. */
export type ADEType = 'A1' | 'A2' | 'A3' | 'A4' | 'D4' | 'D5' | 'E6' | 'E7' | 'E8';

// ─── Result / Data Types ────────────────────────────────────────────────────

/** Result of snapping a value to a lattice point. */
export interface SnapResult {
  /** Original input value. */
  original: number;
  /** Value after snapping to nearest expected point. */
  snapped: number;
  /** Absolute distance between original and snapped. */
  delta: number;
  /** Whether this observation fell within tolerance. */
  withinTolerance: boolean;
  /** The tolerance threshold used. */
  tolerance: number;
  /** The snap topology in use. */
  topology: SnapTopologyType;
}

/**
 * A felt delta — information that exceeded snap tolerance.
 *
 * The delta is not just a number; it encodes the quality of the departure
 * from expectation, including how actionable and urgent the signal is.
 */
export interface Delta {
  /** Observed value. */
  value: number;
  /** Expected (baseline) value. */
  expected: number;
  /** Absolute magnitude of the departure from expected. */
  magnitude: number;
  /** Current snap tolerance. */
  tolerance: number;
  /** Qualitative severity category. */
  severity: DeltaSeverity;
  /** Monotonic timestamp (tick number). */
  timestamp: number;
  /** Which stream produced this delta. */
  streamId: string;
  /** Can thinking change this? [0..1]. */
  actionability: number;
  /** Does this need attention NOW? [0..1]. */
  urgency: number;
}

/** Result of allocating attention budget to a delta. */
export interface AttentionAllocation {
  /** The delta that triggered allocation. */
  delta: Delta;
  /** Amount of attention allocated to this delta. */
  allocated: number;
  /** Priority rank (1 = highest). */
  priority: number;
  /** Human-readable justification. */
  reason: string;
}

/** Result of matching an observation against the script library. */
export interface ScriptMatch {
  /** ID of the matched script. */
  scriptId: string;
  /** How well the pattern matches [0..1]. */
  confidence: number;
  /** Whether confidence exceeds the match threshold. */
  isMatch: boolean;
  /** Euclidean distance from the ideal trigger pattern. */
  deltaFromTemplate: number;
}

/** Current state of the learning cycle. */
export interface LearningState {
  /** Current phase of expertise. */
  phase: LearningPhase;
  /** Total experiences processed. */
  totalExperiences: number;
  /** Number of scripts created (including archived). */
  scriptsBuilt: number;
  /** Number of currently active scripts. */
  scriptsActive: number;
  /** Cognitive load [0..1] — 0 = fully automated, 1 = full attention. */
  cognitiveLoad: number;
  /** Fraction of observations that snap to known scripts. */
  snapHitRate: number;
  /** Fraction of observations that are novel/deltas. */
  deltaRate: number;
  /** How many times phase has transitioned. */
  phaseTransitions: number;
}

/** Options for creating a SnapFunction. */
export interface SnapOptions {
  /** Maximum distance within which values are snapped to expected. Default 0.1. */
  tolerance?: number;
  /** The snap topology (determines the lattice shape). Default 'hexagonal'. */
  topology?: SnapTopologyType;
  /** Initial expected value. Default 0. */
  baseline?: number;
  /** How fast the baseline adapts to new data [0..1]. Default 0.01. */
  adaptationRate?: number;
}

/** Options for creating a DeltaDetector stream. */
export interface StreamOptions {
  /** Function to compute actionability from observed value [0..1]. */
  actionabilityFn?: (value: number) => number;
  /** Function to compute urgency from observed value [0..1]. */
  urgencyFn?: (value: number) => number;
}

/** Options for creating an AttentionBudget. */
export interface BudgetOptions {
  /** Maximum attention available per allocation cycle. */
  totalBudget: number;
  /** Allocation strategy. Default 'actionability'. */
  strategy?: 'actionability' | 'reactive' | 'uniform';
}

/** A learned script — a pattern-response pair that executes automatically. */
export interface Script {
  /** Unique identifier. */
  id: string;
  /** Human-readable name. */
  name: string;
  /** The pattern that activates this script. */
  triggerPattern: number[];
  /** The pre-computed response. */
  response: unknown;
  /** Optional context metadata. */
  context: Record<string, unknown>;
  /** Minimum similarity to activate. */
  matchThreshold: number;
  /** Lifecycle status. */
  status: ScriptStatus;
  /** How many times this script has been used. */
  useCount: number;
  /** How many times it succeeded. */
  successCount: number;
  /** How many times it failed. */
  failCount: number;
  /** Timestamp of last use. */
  lastUsed: number;
  /** Current confidence in this script [0..1]. */
  confidence: number;
}

/** Options for creating a ScriptLibrary. */
export interface ScriptLibraryOptions {
  /** Minimum similarity for a match. Default 0.85. */
  matchThreshold?: number;
}

/** Options for creating a LearningCycle. */
export interface LearningOptions {
  /** How many consecutive deltas before triggering disruption. Default 5. */
  noveltyThreshold?: number;
  /** How many similar deltas before creating a script. Default 3. */
  scriptCreationThreshold?: number;
}

/** A single experience fed to the learning cycle. */
export interface Experience {
  /** Observed value. */
  value: number;
  /** Optional context metadata. */
  context?: Record<string, unknown>;
}

/** Result of processing an experience through the learning cycle. */
export interface LearningResult {
  /** Updated learning state after processing. */
  state: LearningState;
  /** Whether this observation was a delta. */
  isDelta: boolean;
  /** Whether a script was matched and executed. */
  scriptMatched: boolean;
  /** ID of the matched script, if any. */
  matchedScriptId?: string;
}

/** A single Eisenstein integer a + bω where ω = e^(2πi/3). */
export interface EisensteinInt {
  /** Coefficient of 1 (real part offset). */
  a: number;
  /** Coefficient of ω (imaginary axis basis). */
  b: number;
}

/** A topology node in the ADE / Platonic classification. */
export interface TopologyNode {
  /** ADE type label. */
  adeType: ADEType;
  /** Human-readable name. */
  name: string;
  /** Coxeter rank. */
  rank: number;
  /** Ambient dimension. */
  dimension: number;
  /** Number of root vectors. */
  numRoots: number;
  /** Coxeter number. */
  coxeterNumber: number;
  /** Associated Platonic solid, if any. */
  platonicSolid: string | null;
  /** Short description. */
  description: string;
}



/**
 * @snapkit/core — Tolerance-Compressed Attention Allocation Library
 *
 * A reusable library implementing snap-attention theory:
 * the tolerance compression of context so cognition can focus
 * on where thinking matters.
 *
 * Core concepts:
 *   - SnapFunction: compresses information to "close enough to expected"
 *   - DeltaDetector: tracks what exceeds snap tolerance
 *   - AttentionBudget: finite cognition allocation to actionable deltas
 *   - ScriptLibrary: learned patterns that free cognition
 *   - SnapTopology: Platonic/ADE classification of snap shapes
 *   - LearningCycle: experience → pattern → script → automation
 *
 * @packageDocumentation
 */

// Core
export { SnapFunction } from './snap.js';
export type { SnapResult, SnapTopologyType, SnapOptions } from './types.js';

// Delta detection
export { DeltaDetector, DeltaStream } from './delta.js';
export type { Delta, DeltaSeverity, StreamOptions } from './types.js';

// Attention allocation
export { AttentionBudget } from './attention.js';
export type { AttentionAllocation, BudgetOptions } from './types.js';

// Script library
export { ScriptLibrary } from './scripts.js';
export type { Script, ScriptMatch, ScriptStatus, ScriptLibraryOptions } from './types.js';

// Topology
export { SnapTopology, binaryTopology, hexagonalTopology, tetrahedralTopology, trialityTopology, exceptionalE6, exceptionalE7, exceptionalE8, allTopologies, recommendTopology } from './topology.js';
export type { ADEType, TopologyNode } from './types.js';

// Learning cycle
export { LearningCycle } from './learning.js';
export type { LearningPhase, LearningState, LearningOptions, Experience, LearningResult } from './types.js';

// Adversarial
export { FakeDeltaGenerator, AdversarialDetector, CamouflageEngine, BluffCalibration } from './adversarial.js';
export type { FakeDelta, DeceptionLevel, AdversarialStance, SignalProfile, CoverPlan, OptimizedResponse } from './adversarial.js';

// Streaming
export { SnapStream, DeltaStreamer, toAsyncIterable, intervalStream } from './streaming.js';
export type { StreamConfig } from './streaming.js';

// Pipeline
export { buildPipeline, compose, functionalPipeline } from './pipeline.js';
export type { SnapPipeline, SnapPipelineOutput, PipelineStage } from './pipeline.js';

// Eisenstein
export { eisenstein, eisensteinNorm, eisensteinToXY, snapToEisenstein, eisensteinDistance, eisensteinToString, eisensteinEqual, eisensteinAdd, eisensteinMultiply, eisensteinNeighbors, eisensteinLatticeDistance, isEisensteinUnit } from './eisenstein.js';
export type { EisensteinInt } from './types.js';

// Visualization
export { formatSnapResult, formatDelta, formatAllocation, formatPipelineSnapshot, deltaBarChart, generateHTMLPage } from './visualization.js';

/** Library version. */
export const VERSION = '0.1.0';

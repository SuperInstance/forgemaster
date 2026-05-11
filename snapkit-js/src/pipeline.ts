/**
 * Pipeline — Composable Pipeline Builder
 *
 * Provides a composable, functional pipeline for connecting snap-attention
 * primitives: snap → detect → prioritize → allocate.
 *
 * Pipelines are tree-shakeable, pure functions that compose transforms
 * without introducing runtime dependencies.
 *
 * @module
 */

import type { SnapResult, Delta, AttentionAllocation } from './types.js';
import { SnapFunction } from './snap.js';
import { DeltaDetector } from './delta.js';
import { AttentionBudget } from './attention.js';

// ─── Pipeline Types ──────────────────────────────────────────────────────────

/** A single stage in a processing pipeline. */
export interface PipelineStage<I, O> {
  /** Human-readable stage name. */
  name: string;
  /** Process input and produce output. */
  process(input: I): O;
}

/** A complete snapkit processing pipeline. */
export interface SnapPipeline {
  /** Stage 1: Snap values through a tolerance function. */
  snap: PipelineStage<number, SnapResult>;
  /** Stage 2: Detect deltas across multiple streams. */
  detect: PipelineStage<
    Record<string, number>,
    Record<string, Delta>
  >;
  /** Stage 3: Prioritize deltas by attention weight. */
  prioritize: PipelineStage<void, Delta[]>;
  /** Stage 4: Allocate attention budget to prioritized deltas. */
  allocate: PipelineStage<Delta[], AttentionAllocation[]>;
  /** Run the full pipeline end-to-end. */
  run(input: number): SnapPipelineOutput;
}

/** Output of a complete pipeline run. */
export interface SnapPipelineOutput {
  snapResult: SnapResult;
  /** Only populated if a detector is configured. */
  deltas?: Record<string, Delta>;
  /** Only populated if a budget is configured. */
  allocations?: AttentionAllocation[];
}

// ─── Pipeline Builder ────────────────────────────────────────────────────────

/**
 * Build a composable snap-attention pipeline.
 *
 * @example
 * ```ts
 * const pipeline = buildPipeline({
 *   snap: new SnapFunction({ tolerance: 0.1 }),
 *   detector: new DeltaDetector(),
 *   budget: new AttentionBudget({ totalBudget: 100 }),
 *   streamIds: ['alpha', 'beta', 'gamma'],
 * });
 *
 * const output = pipeline.run(42);
 * console.log(output.snapResult);
 * ```
 */
export function buildPipeline(config: {
  snap: SnapFunction;
  detector?: DeltaDetector;
  budget?: AttentionBudget;
  /** Stream IDs to use with the detector (if provided). */
  streamIds?: string[];
}): SnapPipeline {
  const { snap, detector, budget, streamIds } = config;

  // Default stream IDs if detector is configured
  const ids = streamIds ?? ['default'];

  const snapStage: PipelineStage<number, SnapResult> = {
    name: 'snap',
    process: (input: number) => snap.snap(input),
  };

  const detectStage: PipelineStage<
    Record<string, number>,
    Record<string, Delta>
  > = {
    name: 'detect',
    process: (input: Record<string, number>) => {
      if (!detector)
        throw new Error(
          'DeltaDetector not configured in pipeline'
        );
      // Ensure streams exist
      for (const id of Object.keys(input)) {
        if (!detector.getStream(id)) {
          detector.addStream(id, new SnapFunction());
        }
      }
      return detector.observe(input);
    },
  };

  const prioritizeStage: PipelineStage<void, Delta[]> = {
    name: 'prioritize',
    process: () => {
      if (!detector)
        throw new Error(
          'DeltaDetector not configured in pipeline'
        );
      return detector.prioritize(3);
    },
  };

  const allocateStage: PipelineStage<
    Delta[],
    AttentionAllocation[]
  > = {
    name: 'allocate',
    process: (input: Delta[]) => {
      if (!budget)
        throw new Error(
          'AttentionBudget not configured in pipeline'
        );
      return budget.allocate(input);
    },
  };

  // Ensure default streams exist
  if (detector && ids) {
    for (const id of ids) {
      if (!detector.getStream(id)) {
        detector.addStream(id, new SnapFunction());
      }
    }
  }

  return {
    snap: snapStage,
    detect: detectStage,
    prioritize: prioritizeStage,
    allocate: allocateStage,
    run: (input: number): SnapPipelineOutput => {
      const snapResult = snapStage.process(input);

      let deltas: Record<string, Delta> | undefined;
      let allocations: AttentionAllocation[] | undefined;

      if (detector && ids) {
        const channelValues: Record<string, number> = {};
        for (const id of ids) {
          channelValues[id] = input;
        }
        deltas = detectStage.process(channelValues);

        if (budget) {
          const prioritized = detector.prioritize(3);
          allocations = allocateStage.process(prioritized);
        }
      }

      return { snapResult, deltas, allocations };
    },
  };
}

/**
 * Compose two pipeline stages into a single stage.
 */
export function compose<I, M, O>(
  first: PipelineStage<I, M>,
  second: PipelineStage<M, O>
): PipelineStage<I, O> {
  return {
    name: `${first.name} → ${second.name}`,
    process: (input: I) => second.process(first.process(input)),
  };
}

/**
 * Create a simple functional pipeline without class instantiation.
 *
 * @example
 * ```ts
 * const myPipeline = functionalPipeline({
 *   snap: new SnapFunction({ tolerance: 0.5 }),
 *   value: [1, 2, 3],
 *   expected: [0, 0, 0],
 * });
 *
 * console.log(myPipeline.results);
 * ```
 */
export function functionalPipeline(config: {
  snap: SnapFunction;
  value: number[];
  expected?: number[];
}): {
  results: SnapResult[];
  deltaCount: number;
  snapCount: number;
} {
  const results = config.snap.snapVector(
    config.value,
    config.expected
  );
  const deltaCount = results.filter((r) => !r.withinTolerance)
    .length;
  const snapCount = results.filter((r) => r.withinTolerance)
    .length;

  return { results, deltaCount, snapCount };
}

/**
 * Streaming — AsyncIterable Stream Processing
 *
 * Provides utilities for processing information streams as AsyncIterables,
 * enabling composable stream pipelines that optionally run in the browser
 * or Node.js without native dependencies.
 *
 * The streaming module wraps snap-attention primitives into a push/pull
 * stream interface compatible with Web Streams and async generators.
 *
 * @module
 */

import type { Delta, SnapResult } from './types.js';
import { SnapFunction } from './snap.js';
import { DeltaDetector } from './delta.js';

/**
 * Configuration for a stream transform.
 */
export interface StreamConfig {
  /** Optional label for logging/debugging. */
  label?: string;
  /** High-water mark for buffering (max number of items). */
  maxBuffer?: number;
}

/**
 * A snap transform that processes an AsyncIterable of numbers
 * and produces SnapResults.
 *
 * @example
 * ```ts
 * async function* numberStream() {
 *   for (let i = 0; i < 10; i++) yield Math.random();
 * }
 *
 * const snap = new SnapFunction({ tolerance: 0.1 });
 * const transform = new SnapStream(snap);
 *
 * for await (const result of transform.process(numberStream())) {
 *   console.log(result.withinTolerance ? 'SNAP' : 'DELTA', result.delta);
 * }
 * ```
 */
export class SnapStream {
  private _snap: SnapFunction;

  constructor(snap: SnapFunction) {
    this._snap = snap;
  }

  /**
   * Process an async iterable of numbers through the snap function.
   *
   * @param source - An async iterable of numeric values.
   */
  process(
    source: AsyncIterable<number>
  ): AsyncIterable<SnapResult> {
    return this._transform(source);
  }

  private async *_transform(
    source: AsyncIterable<number>
  ): AsyncIterable<SnapResult> {
    for await (const value of source) {
      yield this._snap.snap(value);
    }
  }
}

/**
 * A delta-aware stream that feeds multiple named channels through
 * a DeltaDetector.
 *
 * @example
 * ```ts
 * const detector = new DeltaDetector();
 * detector.addStream('temp', new SnapFunction({ tolerance: 0.5 }));
 * detector.addStream('pressure', new SnapFunction({ tolerance: 1.0 }));
 *
 * const stream = new DeltaStreamer(detector);
 *
 * for await (const deltas of stream.process(channelReader)) {
 *   console.log('Current deltas:', deltas);
 * }
 * ```
 */
export class DeltaStreamer {
  private _detector: DeltaDetector;

  constructor(detector: DeltaDetector) {
    this._detector = detector;
  }

  /**
   * Process an async iterable of channel observations.
   *
   * Each observation is a Record<string, number> mapping channel
   * names to observed values.
   *
   * @param source - Async iterable of channel observations.
   */
  process(
    source: AsyncIterable<Record<string, number>>
  ): AsyncIterable<Record<string, Delta>> {
    return this._transform(source);
  }

  private async *_transform(
    source: AsyncIterable<Record<string, number>>
  ): AsyncIterable<Record<string, Delta>> {
    for await (const channels of source) {
      yield this._detector.observe(channels);
    }
  }
}

/**
 * Convert an array (or iterable) to an AsyncIterable for
 * use with stream processors.
 *
 * @param items - Items to iterate.
 */
export async function* toAsyncIterable<T>(
  items: Iterable<T>
): AsyncIterable<T> {
  for (const item of items) {
    yield item;
  }
}

/**
 * Create an async generator that produces values from a
 * function called on a timer.
 *
 * @param fn - Function producing values.
 * @param intervalMs - Interval in milliseconds between calls.
 * @param count - Maximum number of values to produce (Infinity for unlimited).
 */
export async function* intervalStream<T>(
  fn: () => T,
  intervalMs: number = 1000,
  count: number = Infinity
): AsyncIterable<T> {
  for (let i = 0; i < count; i++) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    yield fn();
  }
}

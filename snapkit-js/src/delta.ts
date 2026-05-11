/**
 * DeltaDetector — Tracking What Exceeds Tolerance
 *
 * The delta detector monitors information streams and flags observations
 * that exceed snap tolerance. The felt delta IS the primary information
 * signal — not the calculated probability, but the qualitative shift
 * from "expected" to "unexpected."
 *
 * "The delta is the compass needle. It points attention toward the part
 * of the information landscape where thinking can make the most difference."
 *
 * @module
 */

import type { Delta, DeltaSeverity, StreamOptions } from './types.js';
import { SnapFunction } from './snap.js';

/**
 * A stream of deltas from a single information source.
 *
 * Each stream has its own snap function, tolerance, and topology.
 * Multiple streams model the multi-layer architecture of expert cognition
 * (e.g., poker: cards, behavior, betting, emotion, dynamics).
 */
export class DeltaStream {
  readonly streamId: string;
  readonly snap: SnapFunction;
  private _actionabilityFn: (value: number) => number;
  private _urgencyFn: (value: number) => number;
  private _deltas: Delta[] = [];
  private _tick = 0;

  constructor(
    streamId: string,
    snap: SnapFunction,
    options: StreamOptions = {}
  ) {
    this.streamId = streamId;
    this.snap = snap;
    this._actionabilityFn =
      options.actionabilityFn ?? (() => 1.0);
    this._urgencyFn = options.urgencyFn ?? (() => 1.0);
  }

  /**
   * Observe a value and produce a delta (or no-delta).
   *
   * @param value - The observed value.
   * @returns The resulting Delta.
   */
  observe(value: number): Delta {
    this._tick++;
    const result = this.snap.snap(value);

    // Determine severity
    const ratio =
      result.tolerance > 0 ? result.delta / result.tolerance : 0;
    let severity: DeltaSeverity;
    if (ratio <= 1.0) severity = 'none';
    else if (ratio <= 1.5) severity = 'low';
    else if (ratio <= 3.0) severity = 'medium';
    else if (ratio <= 5.0) severity = 'high';
    else severity = 'critical';

    const delta: Delta = {
      value,
      expected: this.snap.baseline,
      magnitude: result.delta,
      tolerance: result.tolerance,
      severity,
      timestamp: this._tick,
      streamId: this.streamId,
      actionability: this._actionabilityFn(value),
      urgency: this._urgencyFn(value),
    };

    this._deltas.push(delta);
    return delta;
  }

  /**
   * Get the n most recent deltas.
   *
   * @param n - Number of recent deltas to retrieve.
   */
  recentDeltas(n: number = 10): Delta[] {
    return this._deltas.slice(-n);
  }

  /** Get only deltas that exceed tolerance. */
  get nontrivialDeltas(): Delta[] {
    return this._deltas.filter((d) => d.magnitude > d.tolerance);
  }

  /** All deltas observed by this stream. */
  get allDeltas(): Delta[] {
    return this._deltas;
  }

  /** Summary statistics for this stream. */
  get statistics(): Record<string, number | string> {
    if (this._deltas.length === 0) {
      return { streamId: this.streamId, total: 0 };
    }

    const magnitudes = this._deltas.map((d) => d.magnitude);
    const nontrivial = this.nontrivialDeltas;

    return {
      streamId: this.streamId,
      totalObservations: this._deltas.length,
      nontrivialDeltas: nontrivial.length,
      deltaRate: nontrivial.length / this._deltas.length,
      meanMagnitude:
        magnitudes.reduce((a, b) => a + b, 0) / magnitudes.length,
      maxMagnitude: Math.max(...magnitudes),
      tolerance: this.snap.tolerance,
      baseline: this.snap.baseline,
    };
  }
}

/**
 * Multi-stream delta detector — the core of the attention allocation engine.
 *
 * Monitors multiple information streams simultaneously, each with its own
 * snap function and tolerance. Deltas are ranked by attention weight
 * (magnitude × actionability × urgency) to determine which deserve
 * cognitive resources.
 *
 * The poker player uses 5 delta streams simultaneously:
 * cards, behavior, betting, emotion, dynamics.
 *
 * @example
 * ```ts
 * const detector = new DeltaDetector();
 * detector.addStream('cards', new SnapFunction({ tolerance: 0.2 }));
 * detector.addStream('behavior', new SnapFunction({ tolerance: 0.05 }));
 *
 * for (const { cards, behavior } of dataStream) {
 *   detector.observe({ cards, behavior });
 *   const attention = detector.prioritize();
 *   console.log('Attend to:', attention);
 * }
 * ```
 */
export class DeltaDetector {
  private _streams: Map<string, DeltaStream> = new Map();
  private _tick = 0;

  /**
   * Add an information stream to monitor.
   *
   * @param streamId - Unique identifier for the stream.
   * @param snap - SnapFunction for this stream.
   * @param options - Optional actionability/urgency functions.
   * @returns The created DeltaStream.
   */
  addStream(
    streamId: string,
    snap: SnapFunction,
    options: StreamOptions = {}
  ): DeltaStream {
    const stream = new DeltaStream(streamId, snap, options);
    this._streams.set(streamId, stream);
    return stream;
  }

  /** Get a stream by ID. */
  getStream(streamId: string): DeltaStream | undefined {
    return this._streams.get(streamId);
  }

  /** Remove a stream. */
  removeStream(streamId: string): boolean {
    return this._streams.delete(streamId);
  }

  /**
   * Observe values across all streams.
   *
   * @param values - Record mapping stream_id to observed value.
   * @returns Record mapping stream_id to resulting Delta.
   */
  observe(values: Record<string, number>): Record<string, Delta> {
    this._tick++;
    const results: Record<string, Delta> = {};
    for (const [streamId, value] of Object.entries(values)) {
      const stream = this._streams.get(streamId);
      if (stream) {
        results[streamId] = stream.observe(value);
      }
    }
    return results;
  }

  /**
   * Prioritize deltas by attention weight.
   *
   * Returns the top_k deltas sorted by attention_weight
   * (magnitude × actionability × urgency), descending.
   *
   * These are the deltas that DESERVE cognitive resources.
   *
   * @param topK - Maximum number of deltas to return.
   */
  prioritize(topK: number = 3): Delta[] {
    const allDeltas: Delta[] = [];
    for (const stream of this._streams.values()) {
      for (const delta of stream.allDeltas) {
        if (delta.magnitude > delta.tolerance) {
          allDeltas.push(delta);
        }
      }
    }

    // Sort by attention weight, descending
    allDeltas.sort(
      (a, b) =>
        b.magnitude * b.actionability * b.urgency -
        a.magnitude * a.actionability * a.urgency
    );

    return allDeltas.slice(0, topK);
  }

  /**
   * Get the most recent delta from each stream.
   */
  currentDeltas(): Record<string, Delta> {
    const result: Record<string, Delta> = {};
    for (const [sid, stream] of this._streams) {
      const deltas = stream.allDeltas;
      if (deltas.length > 0) {
        result[sid] = deltas[deltas.length - 1];
      }
    }
    return result;
  }

  /** Get all stream IDs. */
  get streamIds(): string[] {
    return Array.from(this._streams.keys());
  }

  /** Number of active streams. */
  get numStreams(): number {
    return this._streams.size;
  }

  /** Comprehensive statistics across all streams. */
  get statistics(): Record<string, unknown> {
    let totalObs = 0;
    let totalDeltas = 0;
    const perStream: Record<string, unknown> = {};

    for (const [sid, stream] of this._streams) {
      const stats = stream.statistics;
      totalObs += (stats.totalObservations as number) || 0;
      totalDeltas += (stats.nontrivialDeltas as number) || 0;
      perStream[sid] = stats;
    }

    return {
      numStreams: this._streams.size,
      totalObservations: totalObs,
      totalDeltas,
      overallDeltaRate: totalObs > 0 ? totalDeltas / totalObs : 0,
      perStream,
    };
  }
}

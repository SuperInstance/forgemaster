/**
 * Temporal snap — T-minus-0 detection and beat grid alignment.
 */

import type { TemporalResult } from "./types.js";

// ---- BeatGrid -----------------------------------------------------------

export class BeatGrid {
  readonly period: number;
  readonly phase: number;
  readonly tStart: number;
  private readonly _invPeriod: number;

  constructor(period: number = 1.0, phase: number = 0.0, tStart: number = 0.0) {
    if (period <= 0) {
      throw new Error("period must be positive");
    }
    this.period = period;
    this.phase = phase;
    this.tStart = tStart;
    this._invPeriod = 1.0 / period;
  }

  /** Find the nearest beat and its index. */
  nearestBeat(t: number): [number, number] {
    const adjusted = t - this.tStart - this.phase;
    const index = Math.round(adjusted * this._invPeriod);
    const beatTime = this.tStart + this.phase + index * this.period;
    return [beatTime, index];
  }

  /** Snap a timestamp to the grid. */
  snap(t: number, tolerance: number = 0.1): TemporalResult {
    const [beatTime, beatIndex] = this.nearestBeat(t);
    const offset = t - beatTime;
    const isOnBeat = Math.abs(offset) <= tolerance;
    let phase = ((t - this.tStart - this.phase) % this.period) * this._invPeriod;
    if (phase < 0) phase += 1.0;

    return Object.freeze({
      originalTime: t,
      snappedTime: beatTime,
      offset,
      isOnBeat,
      isTMinus0: false,
      beatIndex,
      beatPhase: phase,
    });
  }

  /** Snap multiple timestamps. */
  snapBatch(timestamps: number[], tolerance: number = 0.1): TemporalResult[] {
    return timestamps.map((t) => this.snap(t, tolerance));
  }

  /** List all beat times in [tStart, tEnd). */
  beatsInRange(tStart: number, tEnd: number): number[] {
    if (tEnd <= tStart) return [];
    const firstIdx = Math.ceil((tStart - this.tStart - this.phase) * this._invPeriod);
    const lastIdx = Math.floor((tEnd - this.tStart - this.phase) * this._invPeriod);
    const beats: number[] = [];
    for (let i = firstIdx; i <= lastIdx; i++) {
      beats.push(this.tStart + this.phase + i * this.period);
    }
    return beats;
  }
}

// ---- TemporalSnap -------------------------------------------------------

export class TemporalSnap {
  readonly grid: BeatGrid;
  readonly tolerance: number;
  readonly t0Threshold: number;
  readonly t0Window: number;

  private _history: Array<[number, number] | null>;
  private _histIdx: number;
  private _histLen: number;
  private readonly _histCap: number;

  constructor(
    grid: BeatGrid,
    tolerance: number = 0.1,
    t0Threshold: number = 0.05,
    t0Window: number = 3,
  ) {
    this.grid = grid;
    this.tolerance = tolerance;
    this.t0Threshold = t0Threshold;
    this.t0Window = Math.max(2, t0Window);
    this._histCap = this.t0Window * 2;
    this._history = new Array(this._histCap).fill(null);
    this._histIdx = 0;
    this._histLen = 0;
  }

  /** Observe a time-value pair and return the snap result. */
  observe(t: number, value: number): TemporalResult {
    this._history[this._histIdx] = [t, value];
    this._histIdx = (this._histIdx + 1) % this._histCap;
    if (this._histLen < this._histCap) this._histLen++;

    const isT0 = this._detectT0();
    const result = this.grid.snap(t, this.tolerance);

    return Object.freeze({
      originalTime: result.originalTime,
      snappedTime: result.snappedTime,
      offset: result.offset,
      isOnBeat: result.isOnBeat,
      isTMinus0: isT0,
      beatIndex: result.beatIndex,
      beatPhase: result.beatPhase,
    });
  }

  /** Reset history buffer. */
  reset(): void {
    this._histIdx = 0;
    this._histLen = 0;
  }

  /** Return the current history as ordered pairs. */
  get history(): Array<[number, number]> {
    const result: Array<[number, number]> = [];
    for (let i = 0; i < this._histLen; i++) {
      const idx = (this._histIdx - this._histLen + i + this._histCap) % this._histCap;
      const val = this._history[idx];
      if (val !== null) result.push(val);
    }
    return result;
  }

  private _detectT0(): boolean {
    if (this._histLen < 3) return false;

    const cap = this._histCap;
    const idx = this._histIdx;

    const [currT, currVal] = this._history[(idx - 1 + cap) % cap]!;
    const [midT, midVal] = this._history[(idx - 2 + cap) % cap]!;
    const [prevT, prevVal] = this._history[(idx - 3 + cap) % cap]!;

    if (Math.abs(currVal) > this.t0Threshold) return false;

    const dt1 = midT - prevT;
    const dt2 = currT - midT;
    if (dt1 === 0 || dt2 === 0) return false;

    const d1 = (midVal - prevVal) / dt1;
    const d2 = (currVal - midVal) / dt2;

    return d1 * d2 < 0;
  }
}

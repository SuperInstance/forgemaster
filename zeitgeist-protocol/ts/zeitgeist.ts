/**
 * Zeitgeist Protocol — TypeScript implementation
 *
 * CRDT semilattice capturing five dimensions of agent alignment.
 * Merge is commutative, associative, and idempotent.
 */

// ── Enums ──────────────────────────────────────────────────

export const Trend = { STABLE: 0, RISING: 1, FALLING: 2, CHAOTIC: 3 } as const;
export type Trend = (typeof Trend)[keyof typeof Trend];

export const Phase = { IDLE: 0, APPROACHING: 1, SNAP: 2, HOLD: 3 } as const;
export type Phase = (typeof Phase)[keyof typeof Phase];

// ── Sub-states ─────────────────────────────────────────────

export interface PrecisionStateJSON {
  deadband: number;
  funnel_pos: number;
  snap_imminent: boolean;
}

export class PrecisionState {
  constructor(
    public deadband: number = 500000,
    public funnel_pos: number = 0,
    public snap_imminent: boolean = false,
  ) {}

  static readonly COVERING_RADIUS = 1e6;

  checkAlignment(): string[] {
    const v: string[] = [];
    if (this.deadband <= 0) v.push("precision.deadband must be > 0");
    if (this.deadband >= PrecisionState.COVERING_RADIUS)
      v.push("precision.deadband must be < covering_radius");
    return v;
  }

  merge(other: PrecisionState): PrecisionState {
    return new PrecisionState(
      Math.min(this.deadband, other.deadband),
      Math.max(this.funnel_pos, other.funnel_pos),
      this.snap_imminent || other.snap_imminent,
    );
  }

  toJSON(): PrecisionStateJSON {
    return { deadband: this.deadband, funnel_pos: this.funnel_pos, snap_imminent: this.snap_imminent };
  }

  static fromJSON(d: PrecisionStateJSON): PrecisionState {
    return new PrecisionState(d.deadband, d.funnel_pos, d.snap_imminent);
  }

  equals(other: PrecisionState): boolean {
    return (
      this.deadband === other.deadband &&
      this.funnel_pos === other.funnel_pos &&
      this.snap_imminent === other.snap_imminent
    );
  }
}

export interface ConfidenceStateJSON {
  bloom: string; // hex
  parity: number;
  certainty: number;
}

export class ConfidenceState {
  constructor(
    public bloom: Uint8Array = new Uint8Array(32),
    public parity: number = 0,
    public certainty: number = 0,
  ) {}

  checkAlignment(): string[] {
    const v: string[] = [];
    if (this.certainty < 0 || this.certainty > 1)
      v.push("confidence.certainty must be 0-1");
    return v;
  }

  merge(other: ConfidenceState): ConfidenceState {
    const bloom = new Uint8Array(32);
    for (let i = 0; i < 32; i++) bloom[i] = this.bloom[i] | other.bloom[i];
    return new ConfidenceState(
      bloom,
      this.parity | other.parity,
      Math.max(this.certainty, other.certainty),
    );
  }

  toJSON(): ConfidenceStateJSON {
    return {
      bloom: Array.from(this.bloom).map(b => b.toString(16).padStart(2, "0")).join(""),
      parity: this.parity,
      certainty: this.certainty,
    };
  }

  static fromJSON(d: ConfidenceStateJSON): ConfidenceState {
    const bloom = new Uint8Array(
      d.bloom.match(/.{2}/g)!.map(hex => parseInt(hex, 16)),
    );
    return new ConfidenceState(bloom, d.parity, d.certainty);
  }

  equals(other: ConfidenceState): boolean {
    if (this.parity !== other.parity || this.certainty !== other.certainty) return false;
    for (let i = 0; i < 32; i++) if (this.bloom[i] !== other.bloom[i]) return false;
    return true;
  }
}

export interface TrajectoryStateJSON {
  hurst: number;
  trend: number;
  velocity: number;
}

export class TrajectoryState {
  constructor(
    public hurst: number = 0.5,
    public trend: number = Trend.STABLE,
    public velocity: number = 0,
  ) {}

  checkAlignment(): string[] {
    const v: string[] = [];
    if (this.hurst < 0 || this.hurst > 1) v.push("trajectory.hurst must be 0-1");
    return v;
  }

  merge(other: TrajectoryState): TrajectoryState {
    return new TrajectoryState(
      Math.min(this.hurst, other.hurst),
      this.trend === other.trend ? this.trend : Trend.CHAOTIC,
      Math.max(this.velocity, other.velocity),
    );
  }

  toJSON(): TrajectoryStateJSON {
    return { hurst: this.hurst, trend: this.trend, velocity: this.velocity };
  }

  static fromJSON(d: TrajectoryStateJSON): TrajectoryState {
    return new TrajectoryState(d.hurst, d.trend, d.velocity);
  }

  equals(other: TrajectoryState): boolean {
    return this.hurst === other.hurst && this.trend === other.trend && this.velocity === other.velocity;
  }
}

export interface ConsensusStateJSON {
  holonomy: number;
  peer_agreement: number;
  crdt_version: Record<string, number>;
}

export class ConsensusState {
  constructor(
    public holonomy: number = 0,
    public peer_agreement: number = 1,
    public crdt_version: Map<number, number> = new Map(),
  ) {}

  checkAlignment(): string[] {
    const v: string[] = [];
    if (this.peer_agreement < 0 || this.peer_agreement > 1)
      v.push("consensus.peer_agreement must be 0-1");
    return v;
  }

  merge(other: ConsensusState): ConsensusState {
    const v = new Map(this.crdt_version);
    for (const [k, val] of other.crdt_version) {
      v.set(k, Math.max(v.get(k) ?? 0, val));
    }
    return new ConsensusState(
      Math.min(this.holonomy, other.holonomy),
      Math.max(this.peer_agreement, other.peer_agreement),
      v,
    );
  }

  toJSON(): ConsensusStateJSON {
    const cv: Record<string, number> = {};
    for (const [k, val] of this.crdt_version) cv[k.toString()] = val;
    return { holonomy: this.holonomy, peer_agreement: this.peer_agreement, crdt_version: cv };
  }

  static fromJSON(d: ConsensusStateJSON): ConsensusState {
    const cv = new Map<number, number>();
    for (const [k, val] of Object.entries(d.crdt_version)) cv.set(Number(k), val);
    return new ConsensusState(d.holonomy, d.peer_agreement, cv);
  }

  equals(other: ConsensusState): boolean {
    if (this.holonomy !== other.holonomy || this.peer_agreement !== other.peer_agreement) return false;
    if (this.crdt_version.size !== other.crdt_version.size) return false;
    for (const [k, v] of this.crdt_version) {
      if (other.crdt_version.get(k) !== v) return false;
    }
    return true;
  }
}

export interface TemporalStateJSON {
  beat_pos: number;
  phase: number;
  rhythm_coherence: number;
}

export class TemporalState {
  constructor(
    public beat_pos: number = 0,
    public phase: number = Phase.IDLE,
    public rhythm_coherence: number = 1,
  ) {}

  checkAlignment(): string[] {
    const v: string[] = [];
    if (this.beat_pos < 0 || this.beat_pos > 1) v.push("temporal.beat_pos must be 0-1");
    if (this.rhythm_coherence < 0 || this.rhythm_coherence > 1)
      v.push("temporal.rhythm_coherence must be 0-1");
    return v;
  }

  merge(other: TemporalState): TemporalState {
    return new TemporalState(
      Math.max(this.beat_pos, other.beat_pos),
      Math.max(this.phase, other.phase),
      Math.max(this.rhythm_coherence, other.rhythm_coherence),
    );
  }

  toJSON(): TemporalStateJSON {
    return { beat_pos: this.beat_pos, phase: this.phase, rhythm_coherence: this.rhythm_coherence };
  }

  static fromJSON(d: TemporalStateJSON): TemporalState {
    return new TemporalState(d.beat_pos, d.phase, d.rhythm_coherence);
  }

  equals(other: TemporalState): boolean {
    return (
      this.beat_pos === other.beat_pos &&
      this.phase === other.phase &&
      this.rhythm_coherence === other.rhythm_coherence
    );
  }
}

// ── Zeitgeist ──────────────────────────────────────────────

export interface ZeitgeistJSON {
  precision: PrecisionStateJSON;
  confidence: ConfidenceStateJSON;
  trajectory: TrajectoryStateJSON;
  consensus: ConsensusStateJSON;
  temporal: TemporalStateJSON;
}

export class AlignmentReport {
  constructor(public aligned: boolean, public violations: string[]) {}
}

export class Zeitgeist {
  constructor(
    public precision: PrecisionState = new PrecisionState(),
    public confidence: ConfidenceState = new ConfidenceState(),
    public trajectory: TrajectoryState = new TrajectoryState(),
    public consensus: ConsensusState = new ConsensusState(),
    public temporal: TemporalState = new TemporalState(),
  ) {}

  merge(other: Zeitgeist): Zeitgeist {
    return new Zeitgeist(
      this.precision.merge(other.precision),
      this.confidence.merge(other.confidence),
      this.trajectory.merge(other.trajectory),
      this.consensus.merge(other.consensus),
      this.temporal.merge(other.temporal),
    );
  }

  checkAlignment(): AlignmentReport {
    const violations = [
      ...this.precision.checkAlignment(),
      ...this.confidence.checkAlignment(),
      ...this.trajectory.checkAlignment(),
      ...this.consensus.checkAlignment(),
      ...this.temporal.checkAlignment(),
    ];
    return new AlignmentReport(violations.length === 0, violations);
  }

  toJSON(): ZeitgeistJSON {
    return {
      precision: this.precision.toJSON(),
      confidence: this.confidence.toJSON(),
      trajectory: this.trajectory.toJSON(),
      consensus: this.consensus.toJSON(),
      temporal: this.temporal.toJSON(),
    };
  }

  static fromJSON(d: ZeitgeistJSON): Zeitgeist {
    return new Zeitgeist(
      PrecisionState.fromJSON(d.precision),
      ConfidenceState.fromJSON(d.confidence),
      TrajectoryState.fromJSON(d.trajectory),
      ConsensusState.fromJSON(d.consensus),
      TemporalState.fromJSON(d.temporal),
    );
  }

  equals(other: Zeitgeist): boolean {
    return (
      this.precision.equals(other.precision) &&
      this.confidence.equals(other.confidence) &&
      this.trajectory.equals(other.trajectory) &&
      this.consensus.equals(other.consensus) &&
      this.temporal.equals(other.temporal)
    );
  }

  encode(): string {
    return JSON.stringify(this.toJSON());
  }

  static decode(data: string): Zeitgeist {
    return Zeitgeist.fromJSON(JSON.parse(data));
  }
}

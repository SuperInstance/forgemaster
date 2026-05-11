/**
 * Adversarial Snap Calibration
 *
 * The other minds are actively generating fake deltas to jam your snap function.
 * This module implements the adversarial layer of delta detection:
 *
 * - Real vs manufactured deltas
 * - Multi-level recursive deception modeling (I know you know I know...)
 * - Poker: real vs fake tells
 * - Blackjack: look recreational while counting
 *
 * "The snap doesn't tell you what's true. The snap tells you what you can SAFELY
 * IGNORE so you can think about what matters."
 *
 * @module
 */



// ─── Types ───────────────────────────────────────────────────────────────────

/** Levels of recursive deception modeling. */
export type DeceptionLevel =
  | 0 // HONEST — signals are genuine
  | 1 // BLUFF — basic fake signal generation
  | 2 // CALL — detecting the bluff
  | 3 // REBLUFF — double bluff
  | 4 // RECALL — meta-call
  | 5; // PROBABILISTIC — game-theoretic mixed strategy

export type AdversarialStance =
  | 'jam'          // Flood with fake deltas to exhaust attention
  | 'misdirect'    // Push attention toward irrelevant signals
  | 'calibrate'    // Learn your tolerance to exploit it
  | 'mask'         // Hide real deltas behind noise
  | 'decoy';       // Create plausible fake that looks real

// ─── Fake Delta Generator ────────────────────────────────────────────────────

/** A manufactured delta — designed to look real but isn't. */
export interface FakeDelta {
  value: number;
  magnitude: number;
  /** How likely this seems real [0..1]. */
  plausibility: number;
  /** Characteristic pattern of this adversary. */
  styleSignature: string;
  /** Which adversary generated this. */
  generatedBy: string;
  /** The tolerance this fake targets. */
  intendedTolerance: number;
}

/**
 * Generates plausible but manufactured deltas.
 *
 * An adversary uses this to inject noise into another agent's snap
 * function. The generated deltas look real enough to consume attention
 * but carry no genuine information.
 */
export class FakeDeltaGenerator {
  readonly style: string;
  readonly deceptionLevel: DeceptionLevel;
  mimicPrecision: number;

  private _realDeltaHistory: number[] = [];
  private _generationCount = 0;
  private _styleSignature: string;


  constructor(options: {
    style?: string;
    deceptionLevel?: DeceptionLevel;
    mimicPrecision?: number;
  } = {}) {
    this.style = options.style ?? 'default';
    this.deceptionLevel = options.deceptionLevel ?? 1;
    this.mimicPrecision = options.mimicPrecision ?? 0.7;
    this._styleSignature = this._simpleHash(this.style).slice(
      0,
      16
    );
  }

  /** Observe a real delta to learn the target's expected distribution. */
  observeRealDelta(magnitude: number): void {
    this._realDeltaHistory.push(magnitude);
  }

  /** Generate a plausible fake delta. */
  generate(targetTolerance: number = 0.1): FakeDelta {
    this._generationCount++;
    let magnitude: number;

    if (this._realDeltaHistory.length >= 5) {
      const mean =
        this._realDeltaHistory.reduce((a, b) => a + b, 0) /
        this._realDeltaHistory.length;
      const std = this._std(this._realDeltaHistory) || 0.1;
      magnitude = Math.abs(
        this._gaussian(mean, std * this.mimicPrecision)
      );
    } else {
      magnitude =
        targetTolerance *
        (1.5 + Math.random() * 2.0);
    }

    const base = this._gaussian(0, 1);
    let plausibility = Math.max(
      0,
      Math.min(
        1,
        this.mimicPrecision * (0.5 + Math.random() * 0.5)
      )
    );

    if (this.deceptionLevel >= 3) {
      plausibility = Math.min(1, plausibility * 1.2);
    } else if (this.deceptionLevel >= 2) {
      plausibility *= 0.8;
    }

    return {
      value: base,
      magnitude: Math.abs(magnitude),
      plausibility: Math.max(0, Math.min(1, plausibility)),
      styleSignature: this._styleSignature,
      generatedBy: this.style,
      intendedTolerance: targetTolerance,
    };
  }

  /** Generate multiple fake deltas. */
  generateBatch(
    count: number,
    targetTolerance: number = 0.1
  ): FakeDelta[] {
    return Array.from({ length: count }, () =>
      this.generate(targetTolerance)
    );
  }

  /** Summary statistics. */
  get statistics(): Record<string, number | string> {
    return {
      style: this.style,
      deceptionLevel: this.deceptionLevel,
      generationCount: this._generationCount,
      observedRealDeltas: this._realDeltaHistory.length,
    };
  }

  private _gaussian(mean: number, std: number): number {
    // Box-Muller transform
    const u1 = Math.random();
    const u2 = Math.random();
    return (
      mean +
      std * Math.sqrt(-2 * Math.log(u1 || 0.0001)) *
        Math.cos(2 * Math.PI * u2)
    );
  }

  private _std(values: number[]): number {
    const mean =
      values.reduce((a, b) => a + b, 0) / values.length;
    return Math.sqrt(
      values.reduce((sum, v) => sum + (v - mean) ** 2, 0) /
        values.length
    );
  }

  private _simpleHash(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const chr = str.charCodeAt(i);
      hash = (hash << 5) - hash + chr;
      hash |= 0;
    }
    return Math.abs(hash).toString(16);
  }
}

// ─── Adversarial Detector ────────────────────────────────────────────────────

/**
 * Distinguishes real deltas from manufactured ones.
 *
 * The adversarial detector learns the characteristic patterns of
 * each adversary's fake deltas (style signatures) and uses Bayesian
 * inference to classify incoming signals as real vs manufactured.
 */
export class AdversarialDetector {
  /** Minimum confidence to classify as fake. */
  readonly detectionThreshold: number;
  /** How many observations to keep per source. */
  readonly memorySize: number;

  private _sourceProfiles: Map<string, SignalProfile> = new Map();
  private _sourceRealHistory: Map<string, number[]> = new Map();
  private _sourceFakeHistory: Map<string, number[]> = new Map();
  private _observations: Array<Record<string, unknown>> = [];

  private _truePositives = 0;
  private _falsePositives = 0;
  private _trueNegatives = 0;
  private _falseNegatives = 0;

  constructor(options: {
    detectionThreshold?: number;
    memorySize?: number;
  } = {}) {
    this.detectionThreshold = options.detectionThreshold ?? 0.75;
    this.memorySize = options.memorySize ?? 500;
  }

  /** Register or update a source profile. */
  learnSourceProfile(profile: SignalProfile): void {
    this._sourceProfiles.set(profile.sourceId, profile);
    if (!this._sourceRealHistory.has(profile.sourceId)) {
      this._sourceRealHistory.set(profile.sourceId, []);
      this._sourceFakeHistory.set(profile.sourceId, []);
    }
  }

  /**
   * Observe a signal and optionally know if it was real or fake.
   *
   * @returns Classification result.
   */
  observeSignal(options: {
    sourceId: string;
    value: number;
    magnitude: number;
    knownClassification?: boolean; // true = real, false = fake
  }): AdversarialObservation {
    const { sourceId, value, magnitude, knownClassification } =
      options;

    const features = this._extractFeatures(sourceId, magnitude);
    const isFakeProb = this._computeFakeProbability(
      sourceId,
      features
    );
    const classifiedAsFake =
      isFakeProb >= this.detectionThreshold;

    // Update tracking if ground truth is known
    if (knownClassification !== undefined) {
      if (knownClassification) {
        // Real signal
        this._pushHistory(
          this._sourceRealHistory,
          sourceId,
          magnitude
        );
        if (classifiedAsFake) this._falsePositives++;
        else this._trueNegatives++;
      } else {
        // Fake signal
        this._pushHistory(
          this._sourceFakeHistory,
          sourceId,
          magnitude
        );
        if (classifiedAsFake) this._truePositives++;
        else this._falseNegatives++;
      }
    }

    const result: AdversarialObservation = {
      source: sourceId,
      value,
      magnitude,
      classifiedAsFake,
      confidence: isFakeProb,
    };

    this._observations.push(result as unknown as Record<string, unknown>);
    if (this._observations.length > this.memorySize) {
      this._observations =
        this._observations.slice(-this.memorySize);
    }

    return result;
  }

  /** Classify a single FakeDelta candidate. Returns true if classified as fake. */
  classify(delta: FakeDelta): boolean {
    const result = this.observeSignal({
      sourceId: delta.generatedBy,
      value: delta.value,
      magnitude: delta.magnitude,
    });
    return result.classifiedAsFake;
  }

  private _pushHistory(
    map: Map<string, number[]>,
    key: string,
    value: number
  ): void {
    if (!map.has(key)) map.set(key, []);
    const arr = map.get(key)!;
    arr.push(value);
    if (arr.length > this.memorySize) {
      arr.splice(0, arr.length - this.memorySize);
    }
  }

  private _extractFeatures(
    sourceId: string,
    magnitude: number
  ): Record<string, number> {
    const features: Record<string, number> = {};
    const realHist = this._sourceRealHistory.get(sourceId) ?? [];
    const fakeHist = this._sourceFakeHistory.get(sourceId) ?? [];

    if (realHist.length > 0) {
      const realMean =
        realHist.reduce((a, b) => a + b, 0) / realHist.length;
      const realStd = this._stdv(realHist) || 0.01;
      features.zVsReal = Math.min(
        5,
        Math.abs(magnitude - realMean) / realStd
      );
    } else {
      features.zVsReal = 0;
    }

    if (fakeHist.length > 0) {
      const fakeMean =
        fakeHist.reduce((a, b) => a + b, 0) / fakeHist.length;
      const fakeStd = this._stdv(fakeHist) || 0.01;
      features.zVsFake = Math.min(
        5,
        Math.abs(magnitude - fakeMean) / fakeStd
      );
    } else {
      features.zVsFake = 5; // Unknown → likely fake
    }

    const profile = this._sourceProfiles.get(sourceId);
    features.sourceTrust = profile?.overallTrust ?? 0.5;

    return features;
  }

  private _computeFakeProbability(
    sourceId: string,
    features: Record<string, number>
  ): number {
    let prob = 0;
    const hasHistory =
      (this._sourceRealHistory.get(sourceId)?.length ?? 0) > 0 ||
      (this._sourceFakeHistory.get(sourceId)?.length ?? 0) > 0;

    if (!hasHistory) return 0.5;

    if ((features.zVsReal ?? 0) > 2) prob += 0.3;
    if ((features.zVsFake ?? 5) < 1) prob += 0.4;
    prob += (1 - (features.sourceTrust ?? 0.5)) * 0.3;

    const profile = this._sourceProfiles.get(sourceId);
    if (profile) {
      prob += profile.fakeSignalRate * 0.3;
      prob -= profile.realSignalRate * 0.2;
    }

    return Math.max(0, Math.min(1, prob));
  }

  private _stdv(values: number[]): number {
    if (values.length === 0) return 0;
    const mean =
      values.reduce((a, b) => a + b, 0) / values.length;
    return Math.sqrt(
      values.reduce((s, v) => s + (v - mean) ** 2, 0) /
        values.length
    );
  }

  // ─── Metrics ───────────────────────────────────────────────────────────────

  get precision(): number {
    const d = this._truePositives + this._falsePositives;
    return d > 0 ? this._truePositives / d : 0;
  }

  get recall(): number {
    const d = this._truePositives + this._falseNegatives;
    return d > 0 ? this._truePositives / d : 0;
  }

  get f1Score(): number {
    const p = this.precision;
    const r = this.recall;
    return p + r > 0 ? (2 * p * r) / (p + r) : 0;
  }

  get statistics(): Record<string, number | string> {
    return {
      sourcesTracked: this._sourceProfiles.size,
      totalObservations: this._observations.length,
      precision: this.precision,
      recall: this.recall,
      f1Score: this.f1Score,
      truePositives: this._truePositives,
      falsePositives: this._falsePositives,
      trueNegatives: this._trueNegatives,
      falseNegatives: this._falseNegatives,
    };
  }
}

export interface SignalProfile {
  sourceId: string;
  realSignalRate: number;
  fakeSignalRate: number;
  deceptionLevel: DeceptionLevel;
  signalVariance: number;
  consistencyScore: number;
  /** Composite trust score [0..1]. */
  readonly overallTrust: number;
}

export interface AdversarialObservation {
  source: string;
  value: number;
  magnitude: number;
  classifiedAsFake: boolean;
  confidence: number;
}

// ─── Camouflage Engine ───────────────────────────────────────────────────────

/**
 * Masks your own delta detection from adversaries.
 *
 * When your snap function detects a real delta, the CamouflageEngine
 * ensures that your reaction doesn't leak that information to
 * adversarial observers.
 */
export class CamouflageEngine {
  camouflageLevel: number;
  naturalNoise: number;

  private _coverActions: Array<Record<string, unknown>> = [];
  private _detectionEvents: Array<Record<string, unknown>> = [];

  constructor(options: {
    camouflageLevel?: number;
    naturalNoise?: number;
  } = {}) {
    this.camouflageLevel = options.camouflageLevel ?? 0.6;
    this.naturalNoise = options.naturalNoise ?? 0.15;
  }

  /** Prepare a camouflage cover for a real action. */
  prepareCover(options: {
    realAction: string;
    realActionMagnitude?: number;
    context?: Record<string, unknown>;
  }): CoverPlan {
    const { realAction } = options;

    const distractionCount =
      Math.floor(this.camouflageLevel * 3) + 1;
    const distractions: Distractor[] = [];
    for (let i = 0; i < distractionCount; i++) {
      distractions.push(this._generateDistraction(realAction));
    }

    const baseDelay = this.camouflageLevel * 0.5;
    const preJitter = -Math.log(Math.random()) * this.naturalNoise;
    const postJitter = -Math.log(Math.random()) * this.naturalNoise;

    return {
      realAction,
      distractions,
      timingDelays: {
        preAction: baseDelay + preJitter,
        postAction: postJitter,
      },
      noiseInjection: this.naturalNoise * this.camouflageLevel,
    };
  }

  /** Execute the cover actions (record what was done). */
  applyCover(cover: CoverPlan): Distractor[] {
    this._coverActions.push(cover as unknown as Record<string, unknown>);
    return cover.distractions;
  }

  /**
   * Record whether a camouflage event was successful.
   */
  recordDetectionEvent(
    deltaMagnitude: number,
    wasDetectedByAdversary: boolean
  ): void {
    this._detectionEvents.push({
      deltaMagnitude,
      wasDetected: wasDetectedByAdversary,
      camouflageLevel: this.camouflageLevel,
    });

    // Adjust camouflage level based on outcome
    if (this._detectionEvents.length >= 10) {
      const recent = this._detectionEvents.slice(-10);
      const detectionRate =
        recent.filter(
          (e) => (e.wasDetected as boolean)
        ).length / recent.length;

      if (detectionRate > 0.3) {
        this.camouflageLevel = Math.min(
          1,
          this.camouflageLevel + 0.05
        );
      } else if (detectionRate < 0.05) {
        this.camouflageLevel = Math.max(
          0,
          this.camouflageLevel - 0.05
        );
      }
    }
  }

  private _generateDistraction(action: string): Distractor {
    const distractors: Record<string, Distractor[]> = {
      increase_bet: [
        { type: 'adjust_seat', description: 'Adjust seating position' },
        { type: 'check_chips', description: 'Count chips casually' },
        { type: 'conversation', description: 'Mention unrelated topic' },
        { type: 'stretch', description: 'Stretch arms/neck' },
      ],
      fold: [
        { type: 'look_away', description: 'Look at something off-table' },
        { type: 'sigh', description: 'Audible sigh of disappointment' },
        { type: 'conversation', description: 'Ask about next hand' },
      ],
      call: [
        { type: 'check_watch', description: 'Casually check time' },
        { type: 'drink', description: 'Take a sip of drink' },
        { type: 'conversation', description: 'Comment on the hand' },
      ],
      raise: [
        { type: 'count_chips', description: 'Stack chips deliberately' },
        { type: 'conversation', description: 'Narrate the raise' },
        { type: 'lean_forward', description: 'Lean into the table' },
      ],
    };

    const pool = distractors[action] ?? distractors['call'];
    return pool[Math.floor(Math.random() * pool.length)];
  }

  get camouflageStatistics(): Record<string, number> {
    if (this._detectionEvents.length === 0) {
      return { detectionRate: 0, coverActions: 0 };
    }
    const detected = this._detectionEvents.filter(
      (e) => e.wasDetected
    ).length;
    return {
      detectionRate: detected / this._detectionEvents.length,
      coverActions: this._coverActions.length,
      camouflageLevel: this.camouflageLevel,
      totalDetectionEvents: this._detectionEvents.length,
    };
  }
}

export interface CoverPlan {
  realAction: string;
  distractions: Distractor[];
  timingDelays: { preAction: number; postAction: number };
  noiseInjection: number;
}

export interface Distractor {
  type: string;
  description: string;
}

// ─── Bluff Calibration ───────────────────────────────────────────────────────

/**
 * Multi-level recursive deception modeling.
 *
 * Implements the "I know you know I know you know..." recursion:
 * - Level 0: Honest signals (no deception)
 * - Level 1: Basic bluff (I generate fake deltas)
 * - Level 2: Call (I detect your bluff)
 * - Level 3: Re-bluff (I know you'll call, so I double-bluff)
 * - Level N: Nth-order theory of mind
 */
export class BluffCalibration {
  readonly maxDepth: number;

  private _levelStrategies: Map<number, LevelStrategy> = new Map();
  private _adversaryModels: Map<
    string,
    AdversaryModel
  > = new Map();
  private _gameHistory: GameRound[] = [];

  constructor(maxDepth: number = 5) {
    this.maxDepth = maxDepth;
    for (let level = 0; level <= maxDepth; level++) {
      this._levelStrategies.set(level, this._initLevel(level));
    }
  }

  private _initLevel(level: number): LevelStrategy {
    switch (level) {
      case 0:
        return {
          name: 'HONEST',
          bluffProbability: 0,
          callProbability: 0,
          description: 'All signals are genuine',
        };
      case 1:
        return {
          name: 'BLUFF',
          bluffProbability: 0.3,
          callProbability: 0,
          description:
            'I send fake deltas, assume you are honest',
        };
      case 2:
        return {
          name: 'CALL',
          bluffProbability: 0.1,
          callProbability: 0.7,
          description: 'I detect your bluffs, I signal honestly',
        };
      case 3:
        return {
          name: 'REBLUFF',
          bluffProbability: 0.5,
          callProbability: 0.3,
          description:
            'I know you detect bluffs, so I double-bluff',
        };
      case 4:
        return {
          name: 'RECALL',
          bluffProbability: 0.2,
          callProbability: 0.8,
          description:
            'I know you double-bluff, I detect it',
        };
      default:
        return {
          name: `LEVEL_${level}`,
          bluffProbability: 0.3,
          callProbability: 0.5,
          description: `Level ${level} recursive modeling`,
        };
    }
  }

  /** Model an adversary's deception level. */
  modelAdversary(
    adversaryId: string,
    estimatedLevel: number = 1,
    confidence: number = 0.5
  ): void {
    this._adversaryModels.set(adversaryId, {
      estimatedLevel,
      confidence,
      lastUpdated: this._gameHistory.length,
    });
  }

  /**
   * Update adversary model based on observed behavior.
   *
   * @returns The newly estimated level.
   */
  updateAdversaryModel(
    adversaryId: string,
    observedBluffRate: number,
    observedCallRate: number
  ): number {
    let bestLevel = 1;
    let bestDistance = Infinity;

    for (const [level, strat] of this._levelStrategies) {
      if (level > this.maxDepth) break;
      const bDist = Math.abs(
        strat.bluffProbability - observedBluffRate
      );
      const cDist = Math.abs(
        strat.callProbability - observedCallRate
      );
      const distance = bDist + cDist;
      if (distance < bestDistance) {
        bestDistance = distance;
        bestLevel = level;
      }
    }

    const old = this._adversaryModels.get(adversaryId);
    const oldConf = old?.confidence ?? 0;
    const newConf = Math.min(1, oldConf + 0.1);

    this._adversaryModels.set(adversaryId, {
      estimatedLevel: bestLevel,
      confidence: newConf,
      lastUpdated: this._gameHistory.length,
    });

    return bestLevel;
  }

  /**
   * Determine optimal response level given adversary model.
   */
  optimizeResponse(options: {
    adversaryId?: string;
  }): OptimizedResponse {
    const { adversaryId } = options;
    const advModel = adversaryId
      ? this._adversaryModels.get(adversaryId)
      : undefined;

    if (!advModel) {
      return {
        recommendedLevel: 1,
        bluffProbability: 0.15,
        callProbability: 0.15,
        reasoning:
          'No adversary model — low-risk baseline',
        strategyName: 'DEFENSIVE',
      };
    }

    const advLevel = advModel.estimatedLevel;
    const advConf = advModel.confidence;
    let effectiveLevel: number;

    if (advLevel >= this.maxDepth) {
      effectiveLevel = advLevel;
    } else {
      effectiveLevel = Math.min(
        Math.round(advLevel + advConf),
        this.maxDepth
      );
    }

    const strategy = this._levelStrategies.get(effectiveLevel)!;

    return {
      recommendedLevel: effectiveLevel,
      adversaryEstimatedLevel: advLevel,
      confidence: advConf,
      bluffProbability: strategy.bluffProbability,
      callProbability: strategy.callProbability,
      reasoning: `Adv at level ${advLevel} (conf=${advConf.toFixed(1)}) → respond at level ${effectiveLevel}`,
      strategyName: strategy.name,
    };
  }

  /** Record the outcome of a round for model refinement. */
  recordRound(options: {
    myBluffed: boolean;
    adversaryCalled: boolean;
    adversaryId?: string;
  }): void {
    const { myBluffed, adversaryCalled, adversaryId } = options;

    this._gameHistory.push({
      round: this._gameHistory.length,
      myBluffed,
      adversaryCalled,
    });

    if (adversaryId) {
      const recent = this._gameHistory.slice(-20);
      if (recent.length > 0) {
        const observedBluff =
          recent.filter((r) => r.adversaryCalled).length /
          recent.length;
        const observedCall =
          recent.filter((r) => r.myBluffed).length /
          recent.length;
        this.updateAdversaryModel(
          adversaryId,
          observedBluff,
          observedCall
        );
      }
    }
  }

  get statistics(): Record<string, number | string> {
    const strategies: Record<string, string> = {};
    for (const [level, strat] of this._levelStrategies) {
      if (level <= this.maxDepth) {
        strategies[String(level)] = strat.name;
      }
    }
    return {
      maxDepth: this.maxDepth,
      adversariesTracked: this._adversaryModels.size,
      roundsPlayed: this._gameHistory.length,
      levelStrategies: JSON.stringify(strategies),
    };
  }
}

interface LevelStrategy {
  name: string;
  bluffProbability: number;
  callProbability: number;
  description: string;
}

interface AdversaryModel {
  estimatedLevel: number;
  confidence: number;
  lastUpdated: number;
}

interface GameRound {
  round: number;
  myBluffed: boolean;
  adversaryCalled: boolean;
}

export interface OptimizedResponse {
  recommendedLevel: number;
  adversaryEstimatedLevel?: number;
  confidence?: number;
  bluffProbability: number;
  callProbability: number;
  reasoning: string;
  strategyName: string;
}

/**
 * LearningCycle — Experience → Pattern → Script → Automation
 *
 * Expertise follows a cyclic pattern: experience builds scripts, scripts
 * free cognition, freed cognition enables planning, planning handles
 * novelty, and novelty builds new scripts.
 *
 * "The mind oscillates between building scripts (thinking, slow) and
 * running scripts (automatic, fast), monitoring for deltas, and
 * rebuilding when deltas accumulate."
 *
 * @module
 */

import type {
  LearningPhase,
  LearningState,
  LearningOptions,
  Experience,
  LearningResult,
} from './types.js';
import { SnapFunction } from './snap.js';
import { DeltaDetector } from './delta.js';
import { ScriptLibrary } from './scripts.js';

/**
 * The cycle of expertise: experience → pattern → script → automation.
 *
 * Models the four modes of expert cognition:
 * 1. Building scripts (attention-heavy, slow)
 * 2. Running scripts (automatic, attention-free)
 * 3. Monitoring for deltas (light attention)
 * 4. Rebuilding when deltas accumulate (back to building)
 *
 * @example
 * ```ts
 * const cycle = new LearningCycle();
 *
 * for (const observation of experienceStream) {
 *   const result = cycle.experience({ value: observation });
 *   console.log(`Phase: ${result.state.phase}, Load: ${result.state.cognitiveLoad}`);
 * }
 * ```
 */
export class LearningCycle {
  /** Snap function for detecting deltas. */
  readonly snap: SnapFunction;
  /** Delta detector for multi-stream monitoring. */
  readonly detector: DeltaDetector;
  /** Script library for storing learned patterns. */
  readonly library: ScriptLibrary;
  /** How many consecutive deltas before triggering disruption. */
  readonly noveltyThreshold: number;
  /** How many similar deltas before creating a script. */
  readonly scriptCreationThreshold: number;

  private _totalExperiences = 0;
  private _consecutiveDeltas = 0;
  private _pendingDeltas: Experience[] = [];
  private _phase: LearningPhase = 'delta_flood';
  private _phaseTransitions = 0;
  private _history: LearningState[] = [];

  constructor(options: LearningOptions = {}) {
    this.snap = new SnapFunction();
    this.detector = new DeltaDetector();
    this.library = new ScriptLibrary();
    this.noveltyThreshold = options.noveltyThreshold ?? 5;
    this.scriptCreationThreshold =
      options.scriptCreationThreshold ?? 3;
  }

  /**
   * Process a new experience through the learning cycle.
   *
   * @param experience - The experience to process.
   * @returns LearningResult with updated state and metadata.
   */
  experience(experience: Experience): LearningResult {
    this._totalExperiences++;
    const { value, context } = experience;

    // Step 1: Snap the observation
    const result = this.snap.snap(value);
    const isDelta = !result.withinTolerance;

    // Step 2: Check for delta
    let scriptMatched = false;
    let matchedScriptId: string | undefined;

    if (isDelta) {
      this._consecutiveDeltas++;
      this._pendingDeltas.push({
        value,
        context: context ?? {},
      });
    } else {
      this._consecutiveDeltas = 0;
    }

    // Step 3: Check for script match
    if (this.library.activeScripts > 0) {
      const match = this.library.findBestMatch([value]);
      if (match && match.isMatch) {
        this._consecutiveDeltas = 0;
        scriptMatched = true;
        matchedScriptId = match.scriptId;
        this.library.recordUse(match.scriptId, true, this._totalExperiences);
      }
    }

    // Step 4: Create scripts from accumulated patterns
    if (
      this._pendingDeltas.length >= this.scriptCreationThreshold
    ) {
      this._createScriptFromDeltas();
    }

    // Step 5: Update phase
    this._updatePhase();

    // Record state
    const state = this.currentState;
    this._history.push(state);

    return {
      state,
      isDelta,
      scriptMatched,
      matchedScriptId,
    };
  }

  /**
   * Feed multiple experiences at once.
   *
   * @param experiences - Array of experiences to process sequentially.
   * @returns Array of LearningResults.
   */
  experienceBatch(experiences: Experience[]): LearningResult[] {
    return experiences.map((exp) => this.experience(exp));
  }

  private _createScriptFromDeltas(): void {
    if (this._pendingDeltas.length === 0) return;

    // Cluster similar deltas
    const values = this._pendingDeltas.map((d) => d.value);
    const meanVal =
      values.reduce((a, b) => a + b, 0) / values.length;

    // Create a script triggered by the mean pattern
    this.library.learn(
      [meanVal],
      { action: 'handle', value: meanVal },
      `auto_script_${this._totalExperiences}`,
      this._pendingDeltas[0].context
    );

    this._pendingDeltas = [];
  }

  private _updatePhase(): void {
    const oldPhase = this._phase;
    const hitRate = this.library.hitRate;

    if (this.library.activeScripts === 0) {
      this._phase = 'delta_flood';
    } else if (this._consecutiveDeltas >= this.noveltyThreshold) {
      this._phase = 'disruption';
      if (
        this._consecutiveDeltas >= this.noveltyThreshold * 2
      ) {
        this._phase = 'rebuilding';
      }
    } else if (hitRate > 0.7) {
      this._phase = 'smooth_running';
    } else if (this.library.activeScripts > 0 && hitRate < 0.3) {
      this._phase = 'script_burst';
    } else {
      this._phase = 'script_burst';
    }

    if (this._phase !== oldPhase) {
      this._phaseTransitions++;
    }
  }

  /**
   * Compute current cognitive load [0..1].
   *
   * 0.0 = fully automated (everything snaps to scripts)
   * 1.0 = full attention (everything is novel)
   */
  private _computeCognitiveLoad(): number {
    if (this._totalExperiences === 0) return 1.0;

    const recent =
      this._history.length > 100
        ? this._history.slice(-100)
        : this._history;
    if (recent.length === 0) return 1.0;

    const deltaFraction = 1.0 - this.snap.snapRate;
    const scriptCoverage = this.library.hitRate;

    // Combined load: deltas that scripts don't cover
    const load = deltaFraction * (1.0 - scriptCoverage);
    return Math.max(0, Math.min(1, load));
  }

  // ─── State ─────────────────────────────────────────────────────────────────

  /** Get the current learning state. */
  get currentState(): LearningState {
    return {
      phase: this._phase,
      totalExperiences: this._totalExperiences,
      scriptsBuilt: this.library.activeScripts, // We track approx
      scriptsActive: this.library.activeScripts,
      cognitiveLoad: this._computeCognitiveLoad(),
      snapHitRate: this.snap.snapRate,
      deltaRate: this.snap.deltaRate,
      phaseTransitions: this._phaseTransitions,
    };
  }

  /** Get the history of phase transitions. */
  get phaseHistory(): LearningPhase[] {
    return this._history.map((s) => s.phase);
  }

  /** Summary statistics. */
  get statistics(): Record<string, number | string> {
    return {
      currentPhase: this._phase,
      totalExperiences: this._totalExperiences,
      scriptsBuilt: this.library.activeScripts,
      scriptsActive: this.library.activeScripts,
      cognitiveLoad: this._computeCognitiveLoad(),
      snapHitRate: this.snap.snapRate,
      deltaRate: this.snap.deltaRate,
      libraryStats: JSON.stringify(this.library.statistics),
      snapStats: JSON.stringify(this.snap.statistics),
    };
  }
}

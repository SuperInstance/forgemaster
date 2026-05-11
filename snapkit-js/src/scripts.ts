/**
 * ScriptLibrary — Learned Patterns That Free Cognition
 *
 * Scripts are compressed, pre-learned sequences that can be executed
 * without conscious thought. When a pattern snaps to a known script,
 * cognition is freed for higher-level planning.
 *
 * "Scripts don't reduce MOVES, they reduce COGNITIVE LOAD. The planning
 * solver may use more total moves but THINKS less because scripts
 * execute automatically."
 *
 * @module
 */

import type {
  Script,
  ScriptMatch,
  ScriptLibraryOptions,
} from './types.js';

/**
 * Library of learned scripts — the system's "muscle memory."
 *
 * The script library stores pre-verified response sequences indexed
 * by their trigger patterns. When an observation snaps to a known
 * pattern, the corresponding script executes automatically, freeing
 * cognition for planning.
 *
 * This is the Rubik's cube algorithm table, the poker basic strategy
 * chart, the surgical technique catalog — compressed expertise that
 * runs without thinking.
 *
 * @example
 * ```ts
 * const lib = new ScriptLibrary();
 * lib.addScript({
 *   id: 'fold_weak',
 *   name: 'Fold weak hand out of position',
 *   triggerPattern: [0.1, 0.2, 0.3],
 *   response: 'fold',
 *   matchThreshold: 0.85,
 *   status: 'active',
 *   // ... other fields
 * });
 * ```
 */
export class ScriptLibrary {
  /** Default match threshold for new scripts. */
  matchThreshold: number;

  private _scripts: Map<string, InternalScript> = new Map();
  private _hitCount = 0;
  private _missCount = 0;
  private _tick = 0;

  constructor(options: ScriptLibraryOptions = {}) {
    this.matchThreshold = options.matchThreshold ?? 0.85;
  }

  /**
   * Add a script to the library.
   *
   * @param script - The script to add.
   */
  addScript(script: Script): void {
    const internal: InternalScript = {
      ...script,
      triggerPattern: [...script.triggerPattern],
    };
    this._scripts.set(script.id, internal);
  }

  /**
   * Retrieve a script by ID.
   *
   * @param scriptId - The script's unique ID.
   */
  get(scriptId: string): Script | undefined {
    const s = this._scripts.get(scriptId);
    if (!s) return undefined;
    return { ...s };
  }

  /**
   * Find the best matching script for an observation.
   *
   * Returns null if no script matches above threshold.
   *
   * @param observation - The observed pattern to match.
   */
  findBestMatch(observation: number[]): ScriptMatch | null {
    this._tick++;

    if (this._scripts.size === 0) {
      this._missCount++;
      return null;
    }

    let bestMatch: ScriptMatch | null = null;
    let bestConfidence = 0;

    for (const script of this._scripts.values()) {
      if (script.status !== 'active') continue;

      const match = this._match(script, observation);
      if (match.confidence > bestConfidence) {
        bestConfidence = match.confidence;
        bestMatch = match;
      }
    }

    if (bestMatch && bestMatch.isMatch) {
      this._hitCount++;
    } else {
      this._missCount++;
    }

    return bestMatch;
  }

  /**
   * Find all scripts that match an observation above a loose threshold.
   *
   * @param observation - The observed pattern to match.
   * @param threshold - Minimum confidence to include (default 0.5).
   */
  findAllMatches(
    observation: number[],
    threshold: number = 0.5
  ): ScriptMatch[] {
    const matches: ScriptMatch[] = [];

    for (const script of this._scripts.values()) {
      const match = this._match(script, observation);
      if (match.confidence >= threshold) {
        matches.push(match);
      }
    }

    return matches.sort((a, b) => b.confidence - a.confidence);
  }

  /**
   * Learn a new script from a pattern-response pair.
   *
   * This is the "building" phase of the expertise cycle:
   * a novel situation has been encountered, reasoned about,
   * and the solution is cached as a script for future use.
   *
   * @param triggerPattern - The pattern that activates this script.
   * @param response - The pre-computed response.
   * @param name - Optional human-readable name.
   * @param context - Optional context metadata.
   * @returns The created Script.
   */
  learn(
    triggerPattern: number[],
    response: unknown,
    name?: string,
    context?: Record<string, unknown>
  ): Script {
    const id = this._hash(
      triggerPattern,
      JSON.stringify(response)
    );

    const script: Script = {
      id,
      name: name ?? `script_${id}`,
      triggerPattern: [...triggerPattern],
      response,
      context: context ?? {},
      matchThreshold: this.matchThreshold,
      status: 'active',
      useCount: 0,
      successCount: 0,
      failCount: 0,
      lastUsed: 0,
      confidence: 1.0,
    };

    this.addScript(script);
    return script;
  }

  /**
   * Archive a script (don't delete — might need to rebuild).
   *
   * @param scriptId - The script to archive.
   * @returns true if the script was found and archived.
   */
  forget(scriptId: string): boolean {
    const script = this._scripts.get(scriptId);
    if (script) {
      script.status = 'archived';
      return true;
    }
    return false;
  }

  /**
   * Mark scripts that are failing consistently as degraded.
   *
   * @param minUses - Minimum uses before considering degradation.
   * @param minSuccessRate - Minimum acceptable success rate.
   */
  prune(minUses: number = 3, minSuccessRate: number = 0.3): void {
    for (const script of this._scripts.values()) {
      if (
        script.useCount >= minUses &&
        (script.successCount / script.useCount) < minSuccessRate
      ) {
        script.status = 'degraded';
      }
    }
  }

  /**
   * Record a successful or failed use of a script.
   *
   * @param scriptId - The script's ID.
   * @param success - Whether the script succeeded.
   * @param timestamp - Optional tick number.
   */
  recordUse(
    scriptId: string,
    success: boolean,
    timestamp: number = 0
  ): void {
    const script = this._scripts.get(scriptId);
    if (!script) return;

    script.useCount++;
    script.lastUsed = timestamp;
    if (success) {
      script.successCount++;
    } else {
      script.failCount++;
    }
    this._updateConfidence(script);
  }

  // ─── Private helpers ───────────────────────────────────────────────────────

  private _match(
    script: InternalScript,
    observation: number[]
  ): ScriptMatch {
    if (observation.length !== script.triggerPattern.length) {
      return {
        scriptId: script.id,
        confidence: 0,
        isMatch: false,
        deltaFromTemplate: Infinity,
      };
    }

    // Cosine similarity
    const dot = observation.reduce(
      (sum, v, i) => sum + v * script.triggerPattern[i],
      0
    );
    const normObs = Math.sqrt(
      observation.reduce((sum, v) => sum + v * v, 0)
    );
    const normTrig = Math.sqrt(
      script.triggerPattern.reduce((sum, v) => sum + v * v, 0)
    );

    const similarity =
      normObs === 0 || normTrig === 0
        ? 0
        : dot / (normObs * normTrig);

    // Convert similarity [-1, 1] to confidence [0, 1]
    const confidence = (similarity + 1) / 2;

    // Euclidean distance
    const delta = Math.sqrt(
      observation.reduce(
        (sum, v, i) =>
          sum + (v - script.triggerPattern[i]) ** 2,
        0
      )
    );

    return {
      scriptId: script.id,
      confidence,
      isMatch: confidence >= script.matchThreshold,
      deltaFromTemplate: delta,
    };
  }

  private _updateConfidence(script: InternalScript): void {
    if (script.useCount === 0) {
      script.confidence = 1.0;
      return;
    }

    const successRate = script.successCount / script.useCount;
    script.confidence =
      successRate * Math.min(1.0, script.successCount / 5);

    // Degrade if failing
    if (script.useCount > 5 && successRate < 0.5) {
      script.status = 'degraded';
    }
  }

  private _hash(pattern: number[], responseStr: string): string {
    // Simple deterministic hash for script ID
    const str = pattern.join(',') + responseStr;
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const chr = str.charCodeAt(i);
      hash = (hash << 5) - hash + chr;
      hash |= 0; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16).slice(0, 12);
  }

  // ─── Statistics ────────────────────────────────────────────────────────────

  /** Fraction of lookups that found a matching script. */
  get hitRate(): number {
    const total = this._hitCount + this._missCount;
    return total > 0 ? this._hitCount / total : 0;
  }

  /** Number of active scripts. */
  get activeScripts(): number {
    let count = 0;
    for (const s of this._scripts.values()) {
      if (s.status === 'active') count++;
    }
    return count;
  }

  /** Summary statistics. */
  get statistics(): Record<string, number | string> {
    const statusCounts: Record<string, number> = {};
    for (const s of this._scripts.values()) {
      statusCounts[s.status] =
        (statusCounts[s.status] || 0) + 1;
    }

    return {
      totalScripts: this._scripts.size,
      activeScripts: this.activeScripts,
      hitRate: this.hitRate,
      totalLookups: this._hitCount + this._missCount,
      statusDistribution: Object.entries(statusCounts)
        .map(([k, v]) => `${k}:${v}`)
        .join(', '),
    };
  }
}

/** Internal script type extending with mutable fields. */
interface InternalScript extends Script {
  triggerPattern: number[];
}

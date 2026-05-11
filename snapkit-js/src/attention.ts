/**
 * AttentionBudget — Finite Cognition Allocation
 *
 * Cognition is finite. The snap functions serve as gatekeepers of a
 * finite attention budget. Attention is allocated proportionally to
 * the magnitude of the felt delta AND the actionability of that delta.
 *
 * "The snap function does not merely detect deltas — it allocates attention
 * to deltas where cognition can affect outcomes."
 *
 * @module
 */

import type { Delta, AttentionAllocation, BudgetOptions } from './types.js';

/**
 * Finite cognitive resource allocator.
 *
 * Models the attention budget constraint:
 *     Σ A_i ≤ A_max
 *
 * where A_i is attention allocated to stream i, and A_max is total
 * available cognitive bandwidth.
 *
 * Attention is allocated based on:
 * 1. Delta magnitude — how far from expected
 * 2. Actionability — can thinking change this?
 * 3. Urgency — does this need attention NOW?
 *
 * @example
 * ```ts
 * const budget = new AttentionBudget({ totalBudget: 100, strategy: 'actionability' });
 *
 * const deltas = detector.prioritize();
 * const allocations = budget.allocate(deltas);
 * for (const alloc of allocations) {
 *   console.log(`Stream ${alloc.delta.streamId}: ${alloc.allocated} attention units`);
 * }
 * ```
 */
export class AttentionBudget {
  /** Total attention available per allocation cycle. */
  readonly totalBudget: number;
  /** Allocation strategy. */
  readonly strategy: 'actionability' | 'reactive' | 'uniform';

  /** Remaining budget after allocation. */
  remaining: number;

  private _history: AttentionAllocation[][] = [];
  private _exhaustionCount = 0;

  constructor(options: BudgetOptions) {
    this.totalBudget = options.totalBudget;
    this.strategy = options.strategy ?? 'actionability';
    this.remaining = this.totalBudget;
  }

  /**
   * Allocate attention budget to a prioritized list of deltas.
   *
   * @param deltas - List of deltas to allocate attention to, sorted by priority.
   * @returns Array of AttentionAllocation objects showing what was allocated.
   */
  allocate(deltas: Delta[]): AttentionAllocation[] {
    this.remaining = this.totalBudget;
    let allocations: AttentionAllocation[] = [];

    if (deltas.length === 0) return allocations;

    switch (this.strategy) {
      case 'actionability':
        allocations = this._allocateActionability(deltas);
        break;
      case 'reactive':
        allocations = this._allocateReactive(deltas);
        break;
      case 'uniform':
        allocations = this._allocateUniform(deltas);
        break;
      default:
        allocations = this._allocateActionability(deltas);
    }

    this._history.push(allocations);

    if (this.remaining <= 0) {
      this._exhaustionCount++;
    }

    return allocations;
  }

  /**
   * Actionability-weighted allocation (THE expert strategy).
   *
   * Weight = delta.magnitude × delta.actionability × delta.urgency.
   * Allocate budget proportionally to weight.
   */
  private _allocateActionability(
    deltas: Delta[]
  ): AttentionAllocation[] {
    const allocations: AttentionAllocation[] = [];

    // Compute weights
    const weights = deltas.map((d) => {
      if (d.magnitude > d.tolerance) {
        return d.magnitude * d.actionability * d.urgency;
      }
      return 0;
    });

    const totalWeight = weights.reduce((a, b) => a + b, 0);
    if (totalWeight === 0) return allocations;

    let budgetRemaining = this.totalBudget;

    // Sort by weight descending for priority ranking
    const indexed = deltas
      .map((d, i) => ({ delta: d, weight: weights[i], idx: i }))
      .filter((e) => e.weight > 0)
      .sort((a, b) => b.weight - a.weight);

    for (let p = 0; p < indexed.length; p++) {
      const { delta, weight } = indexed[p];

      // Proportional allocation
      const proportional = (weight / totalWeight) * this.totalBudget;

      // Cap at remaining budget
      const allocated = Math.min(proportional, budgetRemaining);

      if (allocated <= 0) {
        allocations.push({
          delta,
          allocated: 0,
          priority: p + 1,
          reason: 'BUDGET_EXHAUSTED',
        });
        continue;
      }

      budgetRemaining -= allocated;

      allocations.push({
        delta,
        allocated,
        priority: p + 1,
        reason: this._explainAllocation(delta),
      });
    }

    this.remaining = budgetRemaining;
    return allocations;
  }

  /**
   * Reactive: attend to biggest deltas regardless of actionability.
   */
  private _allocateReactive(deltas: Delta[]): AttentionAllocation[] {
    const sorted = [...deltas]
      .filter((d) => d.magnitude > d.tolerance)
      .sort((a, b) => b.magnitude - a.magnitude);

    let budgetRemaining = this.totalBudget;
    const allocations: AttentionAllocation[] = [];

    for (let p = 0; p < sorted.length; p++) {
      const delta = sorted[p];
      const allocated = Math.min(delta.magnitude, budgetRemaining);
      budgetRemaining -= allocated;
      allocations.push({
        delta,
        allocated,
        priority: p + 1,
        reason: 'REACTIVE_LARGEST_FIRST',
      });
      if (budgetRemaining <= 0) break;
    }

    this.remaining = budgetRemaining;
    return allocations;
  }

  /**
   * Uniform: equal attention to all deltas that exceed tolerance.
   */
  private _allocateUniform(deltas: Delta[]): AttentionAllocation[] {
    const actionable = deltas.filter(
      (d) => d.magnitude > d.tolerance
    );
    if (actionable.length === 0) {
      this.remaining = this.totalBudget;
      return [];
    }

    const perDelta = this.totalBudget / actionable.length;
    const allocations = actionable.map((delta, p) => ({
      delta,
      allocated: perDelta,
      priority: p + 1,
      reason: 'UNIFORM_EQUAL',
    }));

    this.remaining = 0;
    return allocations;
  }

  /**
   * Generate a human-readable reason for an allocation.
   */
  private _explainAllocation(delta: Delta): string {
    const parts: string[] = [];
    if (delta.actionability > 0.7) parts.push('high actionability');
    if (delta.urgency > 0.7) parts.push('high urgency');
    if (delta.magnitude > 3 * delta.tolerance)
      parts.push('large delta');
    if (parts.length === 0) parts.push('weighted allocation');
    return parts.join('; ');
  }

  // ─── Statistics ────────────────────────────────────────────────────────────

  /** Fraction of budget currently used. */
  get utilization(): number {
    const used = this.totalBudget - this.remaining;
    return this.totalBudget > 0 ? used / this.totalBudget : 0;
  }

  /** How often the budget has been exhausted (0..1). */
  get exhaustionRate(): number {
    if (this._history.length === 0) return 0;
    return this._exhaustionCount / this._history.length;
  }

  /** Summary statistics. */
  get statistics(): Record<string, number | string> {
    return {
      totalBudget: this.totalBudget,
      remaining: this.remaining,
      utilization: this.utilization,
      exhaustionRate: this.exhaustionRate,
      allocationCycles: this._history.length,
      strategy: this.strategy,
    };
  }
}

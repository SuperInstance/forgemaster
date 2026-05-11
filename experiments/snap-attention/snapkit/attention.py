"""
attention.py — AttentionBudget: Finite Cognition Allocation
=============================================================

Cognition is finite. The snap functions serve as gatekeepers of a
finite attention budget. Attention is allocated proportionally to
the magnitude of the felt delta AND the actionability of that delta.

"The snap function does not merely detect deltas — it allocates attention
to deltas where cognition can affect outcomes."
— SNAP-ATTENTION-INTELLIGENCE.md, Section 2.5
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from collections import defaultdict

from snapkit.delta import Delta, DeltaSeverity


@dataclass
class AttentionAllocation:
    """Result of allocating attention budget to a delta."""
    delta: Delta
    allocated: float      # Amount of attention allocated
    priority: int         # Priority rank (1 = highest)
    reason: str           # Why this allocation was made
    
    def __repr__(self):
        return (f"Attn({self.delta.stream_id}: {self.allocated:.2f}, "
                f"prio={self.priority}, {self.reason})")


class AttentionBudget:
    """
    Finite cognitive resource allocator.
    
    Models the attention budget constraint:
        Σ A_i ≤ A_max
    
    where A_i is attention allocated to stream i, and A_max is total
    available cognitive bandwidth.
    
    Attention is allocated based on:
    1. Delta magnitude — how far from expected
    2. Actionability — can thinking change this?
    3. Urgency — does this need attention NOW?
    4. Cost — how much cognitive effort does addressing this take?
    
    Args:
        total_budget: Maximum attention available per cycle.
        strategy: Allocation strategy ('actionability', 'reactive', 'uniform').
    
    Usage:
        budget = AttentionBudget(total=100.0, strategy='actionability')
        
        deltas = detector.prioritize()
        allocations = budget.allocate(deltas)
        for alloc in allocations:
            print(f"Stream {alloc.delta.stream_id}: {alloc.allocated:.1f} attention units")
    """
    
    def __init__(
        self,
        total_budget: float = 100.0,
        strategy: str = 'actionability',
    ):
        self.total_budget = total_budget
        self.remaining = total_budget
        self.strategy = strategy
        self._allocations: List[AttentionAllocation] = []
        self._history: List[List[AttentionAllocation]] = []
        self._exhaustion_count = 0
    
    def allocate(self, deltas: List[Delta]) -> List[AttentionAllocation]:
        """
        Allocate attention budget to a prioritized list of deltas.
        
        Args:
            deltas: List of deltas to allocate attention to, sorted by priority.
        
        Returns:
            List of AttentionAllocation objects showing what was allocated.
        """
        self.remaining = self.total_budget
        allocations = []
        
        if not deltas:
            return allocations
        
        if self.strategy == 'actionability':
            allocations = self._allocate_actionability(deltas)
        elif self.strategy == 'reactive':
            allocations = self._allocate_reactive(deltas)
        elif self.strategy == 'uniform':
            allocations = self._allocate_uniform(deltas)
        else:
            allocations = self._allocate_actionability(deltas)
        
        self._allocations = allocations
        self._history.append(allocations)
        
        if self.remaining <= 0:
            self._exhaustion_count += 1
        
        return allocations
    
    def _allocate_actionability(self, deltas: List[Delta]) -> List[AttentionAllocation]:
        """
        Actionability-weighted allocation (THE expert strategy).
        
        Weight = delta.magnitude × delta.actionability × delta.urgency
        Allocate budget proportionally to weight.
        """
        allocations = []
        
        # Compute weights
        weights = []
        for d in deltas:
            if d.exceeds_tolerance:
                w = d.magnitude * d.actionability * d.urgency
                weights.append(w)
            else:
                weights.append(0.0)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return allocations
        
        # Allocate proportionally, but cap at budget
        budget_remaining = self.total_budget
        
        # Sort by weight descending for priority ranking
        indexed = sorted(enumerate(deltas), key=lambda x: weights[x[0]], reverse=True)
        
        for priority, (idx, delta) in enumerate(indexed):
            w = weights[idx]
            if w <= 0:
                continue
            
            # Proportional allocation
            proportional = (w / total_weight) * self.total_budget
            
            # Cap at remaining budget
            allocated = min(proportional, budget_remaining)
            
            if allocated <= 0:
                # Budget exhausted — report remaining deltas as unattended
                allocations.append(AttentionAllocation(
                    delta=delta,
                    allocated=0.0,
                    priority=priority + 1,
                    reason="BUDGET_EXHAUSTED"
                ))
                continue
            
            budget_remaining -= allocated
            
            reason = self._explain_allocation(delta, allocated)
            allocations.append(AttentionAllocation(
                delta=delta,
                allocated=allocated,
                priority=priority + 1,
                reason=reason,
            ))
        
        self.remaining = budget_remaining
        return allocations
    
    def _allocate_reactive(self, deltas: List[Delta]) -> List[AttentionAllocation]:
        """Reactive: attend to biggest deltas regardless of actionability."""
        sorted_deltas = sorted(deltas, key=lambda d: d.magnitude, reverse=True)
        budget_remaining = self.total_budget
        
        allocations = []
        for priority, delta in enumerate(sorted_deltas):
            if not delta.exceeds_tolerance:
                continue
            allocated = min(delta.magnitude, budget_remaining)
            budget_remaining -= allocated
            allocations.append(AttentionAllocation(
                delta=delta,
                allocated=allocated,
                priority=priority + 1,
                reason="REACTIVE_LARGEST_FIRST",
            ))
            if budget_remaining <= 0:
                break
        
        self.remaining = budget_remaining
        return allocations
    
    def _allocate_uniform(self, deltas: List[Delta]) -> List[AttentionAllocation]:
        """Uniform: equal attention to all deltas."""
        actionable = [d for d in deltas if d.exceeds_tolerance]
        if not actionable:
            self.remaining = self.total_budget
            return []
        
        per_delta = self.total_budget / len(actionable)
        allocations = []
        for priority, delta in enumerate(actionable):
            allocations.append(AttentionAllocation(
                delta=delta,
                allocated=per_delta,
                priority=priority + 1,
                reason="UNIFORM_EQUAL",
            ))
        
        self.remaining = 0.0
        return allocations
    
    def _explain_allocation(self, delta: Delta, amount: float) -> str:
        """Generate a human-readable reason for an allocation."""
        parts = []
        if delta.actionability > 0.7:
            parts.append("high actionability")
        if delta.urgency > 0.7:
            parts.append("high urgency")
        if delta.magnitude > 3 * delta.tolerance:
            parts.append("large delta")
        
        if not parts:
            parts.append("weighted allocation")
        
        return "; ".join(parts)
    
    @property
    def utilization(self) -> float:
        """Fraction of budget currently used."""
        used = self.total_budget - self.remaining
        return used / self.total_budget if self.total_budget > 0 else 0.0
    
    @property
    def exhaustion_rate(self) -> float:
        """How often the budget has been exhausted."""
        if not self._history:
            return 0.0
        return self._exhaustion_count / len(self._history)
    
    @property
    def statistics(self) -> Dict:
        return {
            'total_budget': self.total_budget,
            'remaining': self.remaining,
            'utilization': self.utilization,
            'exhaustion_rate': self.exhaustion_rate,
            'allocation_cycles': len(self._history),
            'strategy': self.strategy,
        }
    
    # ─── Multi-Level Attention ────────────────────────────────────
    
    def multi_level_allocate(
        self,
        macro_deltas: List[Delta],
        micro_deltas: Dict[str, List[Delta]],
        macro_budget: float = 40.0,
        micro_budget: float = 60.0,
    ) -> Dict[str, List[AttentionAllocation]]:
        """
        Two-level attention allocation.
        
        Macro: which streams to attend to.
        Micro: which deltas within a stream deserve attention.
        
        This models the poker pro: first decide WHICH player to watch
        (macro), then what to look for in that player (micro).
        
        Args:
            macro_deltas: Deltas determining stream-level attention.
            micro_deltas: Dict of stream_id → deltas for within-stream allocation.
            macro_budget: Budget for macro allocation.
            micro_budget: Budget for micro allocation.
        
        Returns:
            Dict with 'macro' and 'micro' allocation lists.
        """
        old_total = self.total_budget
        
        self.total_budget = macro_budget
        macro_allocs = self.allocate(macro_deltas)
        
        micro_allocs: Dict[str, List[AttentionAllocation]] = {}
        self.total_budget = micro_budget / max(len(micro_deltas), 1)
        
        for stream_id, deltas in micro_deltas.items():
            micro_allocs[stream_id] = self.allocate(deltas)
        
        self.total_budget = old_total
        
        return {
            'macro': macro_allocs,
            'micro': micro_allocs,
        }
    
    # ─── Attention Decay ──────────────────────────────────────────
    
    def apply_decay(self, decay_rate: float = 0.1):
        """
        Apply exponential decay to recent allocations.
        
        Older allocations lose weight, ensuring recent deltas
        get more attention than old ones.
        """
        for i, cycle in enumerate(self._history):
            age_factor = np.exp(-decay_rate * (len(self._history) - i))
            for alloc in cycle:
                alloc.allocated *= age_factor
    
    # ─── Attention Reserve ─────────────────────────────────────────
    
    def allocate_with_reserve(
        self,
        deltas: List[Delta],
        reserve_fraction: float = 0.2,
    ) -> List[AttentionAllocation]:
        """
        Allocate attention keeping a reserve for truly novel deltas.
        
        The reserve ensures that unexpected, high-actionability deltas
        always get some attention, even when budget is nearly exhausted.
        
        Args:
            deltas: Prioritized list of deltas.
            reserve_fraction: Fraction of budget to reserve for surprises.
        
        Returns:
            List of allocations.
        """
        reserve = self.total_budget * reserve_fraction
        available = self.total_budget - reserve
        
        old_total = self.total_budget
        self.total_budget = available
        
        primary = self.allocate(deltas)
        
        # After primary allocation, check if any novel deltas need reserve
        novel_deltas = [d for d in deltas if d.severity == DeltaSeverity.CRITICAL]
        if novel_deltas:
            self.total_budget = reserve
            reserve_allocs = self.allocate(novel_deltas)
            primary.extend(reserve_allocs)
        
        self.total_budget = old_total
        return primary
    
    # ─── Attention Insight ───────────────────────────────────────────
    
    def attention_insight(self) -> Dict[str, Any]:
        """
        Generate insights about attention patterns.
        
        Detects fixation (too much attention to one stream),
        ignoring (attention never allocated to important streams),
        and imbalance (attention skewed from actionability).
        
        Returns:
            Dict with insight type, severity, and description.
        """
        if not self._history:
            return {'insight': 'No data yet', 'severity': 'info'}
        
        stream_attention: Dict[str, float] = {}
        for cycle in self._history:
            for alloc in cycle:
                sid = alloc.delta.stream_id
                stream_attention[sid] = stream_attention.get(sid, 0.0) + alloc.allocated
        
        if not stream_attention:
            return {'insight': 'Nothing demanded attention', 'severity': 'info'}
        
        total = sum(stream_attention.values())
        top_stream = max(stream_attention, key=stream_attention.get)
        top_share = stream_attention[top_stream] / max(total, 1)
        
        insights = []
        if top_share > 0.8:
            insights.append({
                'type': 'fixation',
                'severity': 'warning',
                'message': f"You're spending {top_share:.0%} of attention on '{top_stream}'.",
            })
        
        if self.exhaustion_rate > 0.5:
            insights.append({
                'type': 'overload',
                'severity': 'critical',
                'message': f"Budget exhausted {self._exhaustion_count} times ({self.exhaustion_rate:.0%} of cycles).",
            })
        
        if self.utilization < 0.2:
            insights.append({
                'type': 'underload',
                'severity': 'info',
                'message': 'Low attention utilization. Tolerance may be too loose.',
            })
        
        if not insights:
            insights.append({
                'type': 'balanced',
                'severity': 'good',
                'message': 'Attention allocation is balanced and efficient.',
            })
        
        return {
            'insights': insights,
            'top_stream': top_stream,
            'top_stream_share': top_share,
            'stream_allocation': stream_attention,
            'exhaustion_rate': self.exhaustion_rate,
            'utilization': self.utilization,
        }
    
    def __repr__(self):
        return (f"AttentionBudget(total={self.total_budget:.1f}, "
                f"remaining={self.remaining:.1f}, "
                f"utilization={self.utilization:.1%}, "
                f"strategy={self.strategy})")

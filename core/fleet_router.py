#!/usr/bin/env python3
"""core/fleet_router.py — Route to the cheapest model that can handle the job.

THE ECONOMICS:
  gemini-lite:  $0.002/1K queries (22× cheaper)
  seed-mini:    $0.050/1K queries (workhorse)
  
  If gemini-lite can handle 80% of fleet queries, the fleet cost drops by ~18×.
  
THE ROUTING PRINCIPLE:
  Use the cheapest model UP TO its critical angle.
  Escalate to the next model ONLY when the query exceeds that angle.
  
  The critical angle IS the phase boundary:
    Below: 100% accuracy (transparent water)
    Above: 0% accuracy (total reflection)
    No gradual degradation. Binary routing.

CRITICAL ANGLES (from 2026-05-14 experiments):
  
                    gemini-lite    seed-mini
  addition_depth:   25             ∞
  multiplication:    6             ∞  
  magnitude:         ∞*           ∞
  coeff_familiarity: 3             4
  nesting:           3             ∞
  word_complexity:   4             ∞
  
  * gemini-lite has a glitch at magnitude 10 but works at 100+

Usage:
    from core.fleet_router import FleetRouter
    
    router = FleetRouter()
    model_id, cost = router.route('a*a - a*b + b*b where a=5, b=3')
    # Returns: ('google/gemini-3.1-flash-lite', 0.000002)
"""

from __future__ import annotations

import re
import os
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum

API_KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")


class QueryAxis(Enum):
    ADDITION_DEPTH = "addition_depth"
    MULTIPLICATION_DEPTH = "multiplication_depth"
    MAGNITUDE = "magnitude"
    COEFFICIENT_FAMILIARITY = "coefficient_familiarity"
    NESTING = "nesting"
    WORD_COMPLEXITY = "word_complexity"


@dataclass
class ModelProfile:
    """A model's critical angles across all axes."""
    model_id: str
    model_key: str
    cost_per_1k: float  # USD per 1K queries
    system_prompt: str
    max_tokens: int
    
    # Critical angles per axis (None = no known limit)
    critical_angles: Dict[QueryAxis, Optional[int]]
    
    def safe_for(self, axis: QueryAxis, depth: int) -> bool:
        """Is this model safe for the given axis at the given depth?
        
        Below critical angle = transparent (safe).
        At or above critical angle = reflective (unsafe).
        """
        limit = self.critical_angles.get(axis)
        if limit is None:
            return True  # No known limit
        return depth < limit
    
    def max_safe_depth(self, axis: QueryAxis) -> int:
        """Maximum safe depth for this axis. None = unlimited."""
        return self.critical_angles.get(axis)


@dataclass
class RoutingDecision:
    """The routing decision for a query."""
    model_key: str
    model_id: str
    cost_usd: float
    reason: str
    estimated_axes: Dict[str, int]
    fallback_used: bool = False


# ─── Fleet Roster ──────────────────────────────────────────────────────────────

FLEET = {
    "gemini-lite": ModelProfile(
        model_id="google/gemini-3.1-flash-lite",
        model_key="gemini-lite",
        cost_per_1k=0.002,
        system_prompt="You are a calculator. Output the result number ONLY.",
        max_tokens=80,
        critical_angles={
            QueryAxis.ADDITION_DEPTH: 25,
            QueryAxis.MULTIPLICATION_DEPTH: 9,
            QueryAxis.MAGNITUDE: None,  # Works through 100K+
            QueryAxis.COEFFICIENT_FAMILIARITY: 3,
            QueryAxis.NESTING: 5,
            QueryAxis.WORD_COMPLEXITY: 4,
        },
    ),
    "seed-mini": ModelProfile(
        model_id="ByteDance/Seed-2.0-mini",
        model_key="seed-mini",
        cost_per_1k=0.050,
        system_prompt="You are a calculator. Output the result number ONLY.",
        max_tokens=80,
        critical_angles={
            QueryAxis.ADDITION_DEPTH: None,  # ∞ (no cliff through 30)
            QueryAxis.MULTIPLICATION_DEPTH: None,  # ∞ (through 8)
            QueryAxis.MAGNITUDE: None,  # ∞ (through 100K)
            QueryAxis.COEFFICIENT_FAMILIARITY: 4,  # Misses some at level 5
            QueryAxis.NESTING: None,  # ∞ (through 5)
            QueryAxis.WORD_COMPLEXITY: None,  # ∞ (through 5)
        },
    ),
    "hermes-70b": ModelProfile(
        model_id="NousResearch/Hermes-3-Llama-3.1-70B",
        model_key="hermes-70b",
        cost_per_1k=0.080,
        system_prompt="Output ONLY the number.",
        max_tokens=80,
        critical_angles={
            QueryAxis.ADDITION_DEPTH: 10,
            QueryAxis.MULTIPLICATION_DEPTH: 3,
            QueryAxis.MAGNITUDE: 3,
            QueryAxis.COEFFICIENT_FAMILIARITY: 2,
            QueryAxis.NESTING: 2,
            QueryAxis.WORD_COMPLEXITY: 3,
        },
    ),
}

# Routing priority: cheapest first
ROUTE_ORDER = ["gemini-lite", "seed-mini"]


# ─── Query Analyzer ────────────────────────────────────────────────────────────

def analyze_query(prompt: str) -> Dict[QueryAxis, int]:
    """Estimate the depth along each axis for a given query.
    
    This is a heuristic analyzer — it estimates, not measures.
    The estimates are conservative (round toward danger).
    """
    axes = {}
    
    # Addition depth: count '+' operators
    plus_count = prompt.count('+')
    if plus_count > 0:
        axes[QueryAxis.ADDITION_DEPTH] = plus_count + 1
    
    # Multiplication depth: count '*' operators
    mul_count = prompt.count('*') + prompt.count('×')
    if mul_count > 0:
        axes[QueryAxis.MULTIPLICATION_DEPTH] = mul_count + 1
    
    # Magnitude: find the largest number
    nums = re.findall(r'\d+', prompt)
    if nums:
        max_num = max(int(n) for n in nums)
        if max_num >= 100000:
            axes[QueryAxis.MAGNITUDE] = 5
        elif max_num >= 10000:
            axes[QueryAxis.MAGNITUDE] = 4
        elif max_num >= 1000:
            axes[QueryAxis.MAGNITUDE] = 3
        elif max_num >= 100:
            axes[QueryAxis.MAGNITUDE] = 2
        elif max_num >= 10:
            axes[QueryAxis.MAGNITUDE] = 1
        else:
            axes[QueryAxis.MAGNITUDE] = 0
    
    # Coefficient familiarity: detect unfamiliar patterns
    unfamiliar_patterns = [
        (r'a\s*\*\s*a\s*[+\-]\s*\d+\s*\*\s*a\s*\*\s*b', 5),  # a² ± N*a*b
        (r'\d+\s*\*\s*a\s*\*\s*a', 4),  # N*a²
        (r'a\s*\*\s*a\s*[+\-]\s*\d+\s*\*\s*a\s*\*\s*b', 4),  # a² ± N*a*b
        (r'a\s*\^\s*2', 2),  # a^2
        (r'a\s*\*\s*a', 1),  # a*a
    ]
    max_fam = 0
    for pattern, level in unfamiliar_patterns:
        if re.search(pattern, prompt):
            max_fam = max(max_fam, level)
    if max_fam > 0:
        axes[QueryAxis.COEFFICIENT_FAMILIARITY] = max_fam
    
    # Nesting: count parentheses depth
    max_depth = 0
    current = 0
    for char in prompt:
        if char == '(':
            current += 1
            max_depth = max(max_depth, current)
        elif char == ')':
            current -= 1
    if max_depth > 0:
        axes[QueryAxis.NESTING] = max_depth
    
    # Word complexity: count sentence-level operations
    word_ops = len(re.findall(r'\b(?:each|every|total|per|times|costs?|profit|revenue|fuel)\b', prompt.lower()))
    if word_ops > 0:
        axes[QueryAxis.WORD_COMPLEXITY] = min(word_ops, 5)
    
    return axes


# ─── The Router ────────────────────────────────────────────────────────────────

class FleetRouter:
    """Route queries to the cheapest model that can handle them.
    
    The router is the fleet's traffic controller:
      1. Classify the query: arithmetic (T=0.0) or strategy (T=0.7)
      2. Analyze the query's depth along each axis
      3. Check if the cheapest model is safe for all axes
      4. If safe → use the cheapest model
      5. If not safe → escalate to the next model
      6. If no model is safe → use the best available and flag it
    
    Three routing dimensions:
      - Model: which model to use
      - Domain: which cognitive axis
      - Temperature: T=0.0 for arithmetic, T=0.7 for strategy
    
    Binary routing at phase boundaries:
      Below critical angle → cheap model (transparent)
      Above critical angle → expensive model (escalate)
    """
    
    def __init__(self, fleet: Dict[str, ModelProfile] = None,
                 route_order: List[str] = None):
        self.fleet = fleet or FLEET
        self.route_order = route_order or ROUTE_ORDER
    
    def _classify_task(self, prompt: str) -> Tuple[float, str]:
        """Classify task type and return (temperature, task_type).
        
        Arithmetic tasks → T=0.0 (deterministic, recognition mode)
        Strategy tasks → T=0.7 (exploratory, design mode)
        
        F25: Temperature is the mode switch for seed-mini.
        """
        strategy_keywords = ['why', 'design', 'diagnos', 'explain', 'plan',
                            'predict', 'compare', 'analyze', 'suggest', 'recommend',
                            'what should', 'how to', 'improve', 'refactor',
                            'metaphor', 'analogy', 'connect', 'prioritize']
        arithmetic_keywords = ['+', '-', '*', '/', '=', 'compute', 'calculate',
                              'what is', 'how much', 'how many', 'solve']
        
        lower = prompt.lower()
        strat_score = sum(1 for kw in strategy_keywords if kw in lower)
        arith_score = sum(1 for kw in arithmetic_keywords if kw in lower)
        
        if strat_score > arith_score:
            return 0.7, "strategy"
        else:
            return 0.0, "arithmetic"
    
    def route(self, prompt: str) -> RoutingDecision:
        """Route a query to the cheapest safe model.
        
        Now includes temperature routing:
          - Arithmetic tasks → T=0.0 (cheapest safe model)
          - Strategy tasks → T=0.7 (seed-mini, the fleet strategist)
        
        Returns a RoutingDecision with:
          - model_key, model_id, temperature
          - estimated cost
          - reason for the routing decision
          - estimated axes (what the analyzer detected)
        """
        temperature, task_type = self._classify_task(prompt)
        axes = analyze_query(prompt)
        
        # Strategy tasks always go to seed-mini (the fleet champion)
        if task_type == "strategy":
            profile = self.fleet.get("seed-mini")
            if profile:
                return RoutingDecision(
                    model_key="seed-mini",
                    model_id=profile.model_id,
                    cost_usd=profile.cost_per_1k / 1000,
                    reason=f"Strategy task (T=0.7). Seed-mini is fleet strategist (8/8).",
                    estimated_axes={a.value: d for a, d in axes.items()},
                )
        
        # Arithmetic tasks: route to cheapest safe model
        for model_key in self.route_order:
            if model_key not in self.fleet:
                continue
            
            profile = self.fleet[model_key]
            
            # Check if this model is safe for ALL detected axes
            unsafe_axes = []
            for axis, depth in axes.items():
                if not profile.safe_for(axis, depth):
                    unsafe_axes.append(f"{axis.value}={depth} (limit={profile.max_safe_depth(axis) or '∞'})")
            
            if not unsafe_axes:
                return RoutingDecision(
                    model_key=model_key,
                    model_id=profile.model_id,
                    cost_usd=profile.cost_per_1k / 1000,
                    reason=f"Cheapest safe model. No axes exceed critical angle.",
                    estimated_axes={a.value: d for a, d in axes.items()},
                )
        
        # No model is safe for all axes — use the most capable
        fallback = self.fleet[self.route_order[-1]]
        unsafe = ", ".join(unsafe_axes) if unsafe_axes else "unknown"
        return RoutingDecision(
            model_key=fallback.model_key,
            model_id=fallback.model_id,
            cost_usd=fallback.cost_per_1k / 1000,
            reason=f"ESCALATED: {unsafe}. Using most capable model.",
            estimated_axes={a.value: d for a, d in axes.items()},
            fallback_used=True,
        )
    
    def route_batch(self, prompts: List[str]) -> Dict:
        """Route a batch of queries. Returns routing statistics."""
        decisions = [(p, self.route(p)) for p in prompts]
        
        model_counts = {}
        total_cost = 0
        escalations = 0
        
        for prompt, decision in decisions:
            mk = decision.model_key
            model_counts[mk] = model_counts.get(mk, 0) + 1
            total_cost += decision.cost_usd
            if decision.fallback_used:
                escalations += 1
        
        savings = 0
        # Compare to all-seed-mini cost
        seed_mini_cost = self.fleet.get("seed-mini", ModelProfile("", "", 0.05, "", 80, {})).cost_per_1k / 1000
        baseline_cost = len(prompts) * seed_mini_cost
        if baseline_cost > 0:
            savings = (1 - total_cost / baseline_cost) * 100
        
        return {
            "n_queries": len(prompts),
            "model_distribution": model_counts,
            "total_cost_usd": round(total_cost, 6),
            "baseline_cost_usd": round(baseline_cost, 6),
            "savings_pct": round(savings, 1),
            "escalations": escalations,
            "decisions": [(p[:50], d.model_key, d.reason) for p, d in decisions],
        }


# ─── CLI ────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="Fleet Router — cheapest safe model routing")
    p.add_argument("prompt", nargs="*", default=[
        "3 + 4",
        "a*a - a*b + b*b where a=5, b=3",
        "((2+3)*4 - 5)*6",
        "1+2+3+4+5+6+7+8+9+10+11+12+13+14+15+16+17+18+19+20",
        "Pressure 3000 PSI, bore 4 inches. Force = pi * 4 * 3000.",
        "a*a - 3*a*b + b*b where a=5, b=3",
        "((((3 + 4) * 2 - 1) * 3 + 5) * 2 - 4) * 6",
        "A delimber: 1 tree/min, 8 hours, 3 logs/tree, \$4/log, fuel \$50/hr, 2 operators \$20/hr.",
    ])
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    
    router = FleetRouter()
    
    if args.json:
        result = router.route_batch(args.prompt)
        import json
        print(json.dumps(result, indent=2))
    else:
        print("FLEET ROUTER — cheapest safe model")
        print("="*60)
        print()
        
        for prompt in args.prompt:
            d = router.route(prompt)
            esc = " ⚠️ ESCALATED" if d.fallback_used else ""
            print(f"  Q: {prompt[:55]}")
            print(f"  → {d.model_key:12s} (${d.cost_usd:.6f}/query){esc}")
            if d.estimated_axes:
                axes_str = ", ".join(f"{k}={v}" for k, v in d.estimated_axes.items())
                print(f"    axes: {axes_str}")
            print(f"    {d.reason}")
            print()
        
        # Batch stats
        result = router.route_batch(args.prompt)
        print(f"BATCH: {result['n_queries']} queries")
        print(f"  Distribution: {result['model_distribution']}")
        print(f"  Cost: ${result['total_cost_usd']:.6f} (baseline: ${result['baseline_cost_usd']:.6f})")
        print(f"  Savings: {result['savings_pct']:.1f}%")
        print(f"  Escalations: {result['escalations']}")

if __name__ == "__main__":
    main()

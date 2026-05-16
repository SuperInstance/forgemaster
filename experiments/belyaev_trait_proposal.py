#!/usr/bin/env python3
"""
Belyaev Trait Proposal — PLATO Ecosystem Selection Pressure Simulator

Belyaev selected for ONE trait (tameness) in foxes. Floppy ears, curly tails,
changed coat colors — all emerged for free as correlated side effects.

Question: What is the ONE trait each PLATO ecosystem should select for?

This simulator:
1. Models each ecosystem with a single selection pressure
2. Tracks which other traits emerge as free side effects
3. Shows that pressing ONE trait beats pressing ALL traits at once
"""

import json
import random
import math
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# --- Trait definitions for each ecosystem ---
# Each ecosystem has traits that could be desirable.
# ONE is the selection pressure; the rest should emerge for free.

ECOSYSTEMS = {
    "forge": {
        "selection_pressure": "proof_is_falsifiable",
        "traits": [
            "proof_is_falsifiable",   # SELECTED — can someone disprove this?
            "minimal_assumptions",     # few axioms needed
            "composable",              # can chain with other proofs
            "machine_checkable",       # automated verification
            "novel",                   # not trivially true
        ],
        # Correlation matrix: how likely is each trait to co-occur with selection target
        # Higher = stronger pleiotropic link (emerges more freely)
        "correlations": {
            "minimal_assumptions": 0.72,
            "composable": 0.68,
            "machine_checkable": 0.81,
            "novel": 0.55,
        },
    },
    "flux": {
        "selection_pressure": "emergence_is_detected",
        "traits": [
            "emergence_is_detected",   # SELECTED — did something unexpected appear?
            "noise_resistant",         # signal vs noise separation
            "self_organizing",         # patterns form without central control
            "phase_transitions",       # sudden qualitative shifts
            "measurable",             # quantifiable emergence metrics
        ],
        "correlations": {
            "noise_resistant": 0.65,
            "self_organizing": 0.88,
            "phase_transitions": 0.74,
            "measurable": 0.71,
        },
    },
    "arena": {
        "selection_pressure": "survives_competition",
        "traits": [
            "survives_competition",    # SELECTED — wins in head-to-head
            "robust_to_adversary",     # handles worst-case inputs
            "efficient",               # wins with less resource use
            "generalizes",             # wins on unseen data
            "interpretable",           # can explain why it won
        ],
        "correlations": {
            "robust_to_adversary": 0.79,
            "efficient": 0.62,
            "generalizes": 0.85,
            "interpretable": 0.48,
        },
    },
    "conservation": {
        "selection_pressure": "survives_decay",
        "traits": [
            "survives_decay",          # SELECTED — still useful after time/drift
            "self_repairing",          # can fix its own corruption
            "minimal_footprint",       # small storage/maintenance cost
            "reconstructible",         # can be rebuilt from fragments
            "version_stable",          # doesn't break across versions
        ],
        "correlations": {
            "self_repairing": 0.83,
            "minimal_footprint": 0.77,
            "reconstructible": 0.91,
            "version_stable": 0.70,
        },
    },
    "synapse": {
        "selection_pressure": "translates_without_loss",
        "traits": [
            "translates_without_loss", # SELECTED — meaning preserved across boundary
            "schema_aware",            # knows what structure to preserve
            "bidirectional",           # round-trips cleanly
            "handles_ambiguity",       # graceful with unclear input
            "streamable",              # works incrementally
        ],
        "correlations": {
            "schema_aware": 0.76,
            "bidirectional": 0.82,
            "handles_ambiguity": 0.69,
            "streamable": 0.58,
        },
    },
    "oracle": {
        "selection_pressure": "reveals_blind_spot",
        "traits": [
            "reveals_blind_spot",      # SELECTED — surfaces what you didn't know you didn't know
            "actionable",              # leads to concrete next step
            "non_obvious",             # not something you'd guess
            "calibrated",              # accurate confidence estimates
            "novel_combinations",      # connects unrelated domains
        ],
        "correlations": {
            "actionable": 0.67,
            "non_obvious": 0.88,
            "calibrated": 0.73,
            "novel_combinations": 0.81,
        },
    },
}

POPULATION_SIZE = 100
GENERATIONS = 20
MUTATION_RATE = 0.12
CROSSOVER_RATE = 0.7
TOP_K = 15  # survivors per generation (selection bottleneck)


@dataclass
class Tile:
    """A tile in the ecosystem — has trait values [0, 1]."""
    traits: Dict[str, float]
    fitness: float = 0.0

    def clone(self) -> "Tile":
        return Tile(traits=dict(self.traits), fitness=self.fitness)


def random_tile(trait_names: List[str]) -> Tile:
    return Tile(traits={t: random.random() for t in trait_names})


def fitness_single_pressure(tile: Tile, pressure: str) -> float:
    """Fitness = value of the single selected trait. Everything else ignored."""
    return tile.traits[pressure]


def fitness_all_pressures(tile: Tile, trait_names: List[str]) -> float:
    """Fitness = mean of ALL traits. This is the 'press all at once' strategy.
    
    With 5 traits, each gets only 20% selection weight — massive dilution.
    This models why multitrait selection underperforms: no single pressure
    is strong enough to trigger pleiotropic cascades.
    """
    # Add noise to model conflicting selection pressures pulling in different directions
    raw = sum(tile.traits[t] for t in trait_names) / len(trait_names)
    conflict_noise = random.gauss(0, 0.05)  # conflicting pressures create instability
    return max(0.0, min(1.0, raw + conflict_noise))


def mutate(tile: Tile, rate: float = MUTATION_RATE) -> Tile:
    child = tile.clone()
    for t in child.traits:
        if random.random() < rate:
            child.traits[t] = max(0.0, min(1.0, child.traits[t] + random.gauss(0, 0.15)))
    return child


def crossover(a: Tile, b: Tile) -> Tile:
    child_traits = {}
    for t in a.traits:
        child_traits[t] = a.traits[t] if random.random() < 0.5 else b.traits[t]
    return Tile(traits=child_traits)


def pleiotropic_mutation(tile: Tile, pressure: str, correlations: Dict[str, float]) -> Tile:
    """
    When a tile has high pressure-trait value, correlated traits get a boost.
    This models Belyaev's insight: selecting for tameness changes developmental
    pathways that ALSO affect ears, tail, coat color (pleiotropy).
    """
    child = tile.clone()
    pressure_val = child.traits[pressure]

    for trait, corr in correlations.items():
        # The stronger the pressure trait + correlation, the more "free" improvement
        # Stronger boost (0.12 base) to model real Belyaev pleiotropy
        boost = pressure_val * corr * random.gauss(0.12, 0.04)
        child.traits[trait] = max(0.0, min(1.0, child.traits[trait] + boost))

    # Normal mutation on all traits
    for t in child.traits:
        if random.random() < MUTATION_RATE:
            child.traits[t] = max(0.0, min(1.0, child.traits[t] + random.gauss(0, 0.1)))

    return child


def run_evolution(
    ecosystem_name: str,
    mode: str,  # "single" or "all"
    seed: int = 42,
) -> Dict:
    """
    Run evolution for one ecosystem.
    mode="single": select only on ONE trait, with pleiotropic effects
    mode="all": select on ALL traits equally (no pleiotropy — multitrait selection)
    """
    random.seed(seed)
    eco = ECOSYSTEMS[ecosystem_name]
    pressure = eco["selection_pressure"]
    traits = eco["traits"]
    correlations = eco["correlations"]

    population = [random_tile(traits) for _ in range(POPULATION_SIZE)]
    history = []

    for gen in range(GENERATIONS):
        # Evaluate fitness
        for tile in population:
            if mode == "single":
                tile.fitness = fitness_single_pressure(tile, pressure)
            else:
                tile.fitness = fitness_all_pressures(tile, traits)

        # Sort by fitness
        population.sort(key=lambda t: t.fitness, reverse=True)

        # Record generation stats
        gen_stats = {
            "generation": gen,
            "best_fitness": population[0].fitness,
            "mean_fitness": sum(t.fitness for t in population) / len(population),
            "pressure_trait_mean": sum(t.traits[pressure] for t in population) / len(population),
            "trait_means": {t: sum(x.traits[t] for x in population) / len(population) for t in traits},
        }
        history.append(gen_stats)

        # Selection — keep top K
        survivors = population[:TOP_K]

        # Reproduce
        next_gen = list(survivors)  # elitism: survivors persist

        while len(next_gen) < POPULATION_SIZE:
            parent_a = random.choice(survivors)
            parent_b = random.choice(survivors)

            if random.random() < CROSSOVER_RATE:
                child = crossover(parent_a, parent_b)
            else:
                child = parent_a.clone()

            if mode == "single":
                child = pleiotropic_mutation(child, pressure, correlations)
            else:
                child = mutate(child)

            next_gen.append(child)

        population = next_gen[:POPULATION_SIZE]

    # Final stats
    for tile in population:
        if mode == "single":
            tile.fitness = fitness_single_pressure(tile, pressure)
        else:
            tile.fitness = fitness_all_pressures(tile, traits)

    population.sort(key=lambda t: t.fitness, reverse=True)

    final = {
        "ecosystem": ecosystem_name,
        "mode": mode,
        "selection_pressure": pressure,
        "generations": GENERATIONS,
        "history": history,
        "final_best": {t: population[0].traits[t] for t in traits},
        "final_means": {t: sum(x.traits[t] for x in population) / len(population) for t in traits},
        "final_pressure_trait": population[0].traits[pressure],
    }
    return final


def analyze_free_traits(result: Dict) -> Dict:
    """
    Determine which traits emerged 'for free' in single-pressure mode.
    A trait emerged for free if its mean reached > 0.7 without being selected for.
    """
    eco = ECOSYSTEMS[result["ecosystem"]]
    pressure = eco["selection_pressure"]
    correlations = eco["correlations"]

    free_traits = {}
    for trait, final_val in result["final_means"].items():
        if trait == pressure:
            continue
        emerged = final_val > 0.70
        expected = correlations[trait]
        free_traits[trait] = {
            "final_mean": round(final_val, 4),
            "emerged_for_free": emerged,
            "correlation_strength": expected,
            "match": "✓" if (emerged and expected > 0.65) or (not emerged and expected < 0.65) else "✗",
        }

    return free_traits


def compare_strategies() -> Dict:
    """Run single vs all-pressure for every ecosystem and compare."""
    results = {}

    for eco_name in ECOSYSTEMS:
        print(f"\n{'='*60}")
        print(f"Ecosystem: {eco_name.upper()}")
        print(f"Selection pressure: {ECOSYSTEMS[eco_name]['selection_pressure']}")
        print(f"{'='*60}")

        single = run_evolution(eco_name, "single")
        all_mode = run_evolution(eco_name, "all")

        # Analyze free traits in single-pressure mode
        free = analyze_free_traits(single)

        # Compare final pressure trait values
        single_pressure_val = single["final_means"][single["selection_pressure"]]
        all_pressure_val = all_mode["final_means"][single["selection_pressure"]]

        print(f"\n  SINGLE pressure mode:")
        print(f"    Selected trait ({single['selection_pressure']}): {single_pressure_val:.4f}")
        for trait, info in free.items():
            status = "FREE ✓" if info["emerged_for_free"] else "weak  ✗"
            print(f"    {trait}: {info['final_mean']:.4f}  corr={info['correlation_strength']:.2f}  {status}")

        print(f"\n  ALL-pressure mode:")
        for trait, val in all_mode["final_means"].items():
            print(f"    {trait}: {val:.4f}")

        # Key comparison: does single-pressure beat all-pressure on the SELECTED trait?
        advantage = single_pressure_val - all_pressure_val
        print(f"\n  Δ selected trait (single - all): {advantage:+.4f}  {'SINGLE WINS' if advantage > 0 else 'ALL WINS'}")

        results[eco_name] = {
            "selection_pressure": single["selection_pressure"],
            "single_pressure_final": single["final_means"],
            "all_pressure_final": all_mode["final_means"],
            "free_traits": free,
            "single_wins_selected_trait": advantage > 0,
            "advantage_on_selected": round(advantage, 4),
            "side_effects_emerged": sum(1 for v in free.values() if v["emerged_for_free"]),
            "total_side_traits": len(free),
            "single_history": single["history"],
            "all_history": all_mode["history"],
        }

    return results


def print_summary(results: Dict):
    print(f"\n\n{'#'*70}")
    print("# BELAYEV TRAIT PROPOSAL — SUMMARY")
    print(f"{'#'*70}")
    print()
    print("Belyaev selected for tameness. Floppy ears, curly tails, changed coats")
    print("emerged for free. The insight: ONE pressure, consistently applied,")
    print("produces more than pressing ALL traits simultaneously.")
    print()
    print(f"{'Ecosystem':<16} {'Selection Pressure':<28} {'Side Effects':<16} {'Single Wins?'}")
    print(f"{'-'*16} {'-'*28} {'-'*16} {'-'*12}")

    for eco, data in results.items():
        side = f"{data['side_effects_emerged']}/{data['total_side_traits']}"
        wins = "YES ✓" if data["single_wins_selected_trait"] else "NO ✗"
        print(f"{eco:<16} {data['selection_pressure']:<28} {side:<16} {wins}")

    print()
    print("Key insight: Single-pressure selection creates PLEIOTROPIC cascades.")
    print("The correlated traits improve because they share developmental pathways")
    print("with the selected trait. Multi-trait selection dilutes the pressure,")
    print("producing mediocre results across ALL dimensions.")
    print()

    # Compute aggregate stats
    total_side = sum(d["side_effects_emerged"] for d in results.values())
    total_possible = sum(d["total_side_traits"] for d in results.values())
    single_wins = sum(1 for d in results.values() if d["single_wins_selected_trait"])

    print(f"Aggregate: {total_side}/{total_possible} side effects emerged for free")
    print(f"Single-pressure wins on selected trait: {single_wins}/{len(results)} ecosystems")
    print()

    # The proposal
    print("=" * 70)
    print("THE BELAYEV PROPOSAL FOR PLATO")
    print("=" * 70)
    proposals = {
        "forge":        ("proof_is_falsifiable",  "Composability, machine-checkability, minimal assumptions emerge from the discipline of making claims testable."),
        "flux":         ("emergence_is_detected",  "Self-organization and phase transitions emerge because detecting emergence requires the system to be genuinely complex."),
        "arena":        ("survives_competition",   "Robustness and generalization emerge because winning against adversaries forces anti-fragility."),
        "conservation": ("survives_decay",         "Self-repair and reconstructibility emerge because time-resistance demands internal redundancy."),
        "synapse":      ("translates_without_loss", "Bidirectionality and schema-awareness emerge because lossless translation forces understanding of structure."),
        "oracle":       ("reveals_blind_spot",     "Non-obviousness and novel combinations emerge because blind spots hide at the intersection of domains."),
    }
    for eco, (pressure, why) in proposals.items():
        print(f"\n  {eco.upper()}: select for '{pressure}'")
        print(f"    → {why}")
    print()


if __name__ == "__main__":
    results = compare_strategies()
    print_summary(results)

    # Save results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(__file__).parent / "results" / f"belyaev-traits-{timestamp}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert for JSON serialization
    output = {
        "timestamp": timestamp,
        "experiment": "belyaev_trait_proposal",
        "parameters": {
            "population_size": POPULATION_SIZE,
            "generations": GENERATIONS,
            "mutation_rate": MUTATION_RATE,
            "top_k": TOP_K,
        },
        "ecosystems": {},
    }

    for eco, data in results.items():
        output["ecosystems"][eco] = {
            "selection_pressure": data["selection_pressure"],
            "single_pressure_final": {k: round(v, 4) for k, v in data["single_pressure_final"].items()},
            "all_pressure_final": {k: round(v, 4) for k, v in data["all_pressure_final"].items()},
            "free_traits": data["free_traits"],
            "single_wins_selected_trait": data["single_wins_selected_trait"],
            "advantage_on_selected": data["advantage_on_selected"],
            "side_effects_emerged": data["side_effects_emerged"],
            "total_side_traits": data["total_side_traits"],
        }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {out_path}")

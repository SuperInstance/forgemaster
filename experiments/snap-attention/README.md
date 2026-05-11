# Snap-as-Attention: Experimental Simulators

**Forgemaster ⚒️ | 2026-05-10**

Testing whether snap-based attention compression actually improves agent performance. Based on the theory in [`SNAPS-AS-ATTENTION.md`](../../research/SNAPS-AS-ATTENTION.md).

---

## Core Hypothesis

> The snap function doesn't tell you what's true. It tells you what you can **safely ignore** so you can think about what matters.

Each simulator tests a different facet of this claim.

---

## Simulator 1: Poker Attention Engine (`poker_sim.py`)

**Tests:** Does tolerance calibration affect which deltas reach attention and does that change win rates?

Four player profiles with different snap tolerance settings:
- **Novice:** Tight on cards (notices every card delta), loose on behavior (misses reads)
- **Intermediate:** Balanced tolerance across all layers
- **Expert:** Tight on behavior/emotion (catches every tell), loose on cards (doesn't obsess)
- **Baseline:** No snap — everything gets attention (control group)

**Prediction:** Expert should win most because they attend to the RIGHT deltas — player behavior and emotional micro-deltas — not card probability noise.

**Measures:** Win rate, average deltas per hand, attention efficiency (wins per delta), which layers produce deltas.

**Run:** 10,000 hands × 4 profiles → `results_poker.json`

---

## Simulator 2: Cross-Domain Transfer (`transfer_sim.py`)

**Tests:** Do snap topologies transfer across domains when randomness shapes match?

Train a snap function on one domain (e.g., coin flips) then transfer it to a completely different domain with the same randomness shape (e.g., true/false questions — both binary). Compare:
- **Matching shapes:** coin → coin, d6 → d20, 2d6 → gaussian
- **Mismatching shapes:** coin → gaussian, 2d6 → directional

**Prediction:** Matching shapes transfer faster (higher transfer efficiency). The snap topology is the invariant across domain transfer.

**Measures:** Transfer efficiency, convergence ratio, deltas detected, calibration speed.

**Run:** 50,000 cross-domain trials across 7 flavor pairs → `results_transfer.json`

---

## Simulator 3: Rubik's Cube Script Engine (`rubik_sim.py`)

**Tests:** Does the script-building + mind-freeing cycle actually outperform brute force?

Three solver types:
1. **Brute force:** Random moves, no scripts, no planning
2. **Script executor:** Has 10 algorithms (scripts), snap-matches pattern → execute, no planning
3. **Planning solver:** Has scripts + uses freed cognition to plan 2-3 scripts ahead

**Prediction:** Planning solver uses MORE total moves but LOWER cognitive load. Scripts automate what was once novel, freeing cognition for planning. Intelligence is knowing WHEN to think.

**Measures:** Moves to solve, solve rate, cognitive load (novel decisions), script ratio, plans executed.

**Run:** 1,000 solves × 3 solver types → `results_rubik.json`

---

## Simulator 4: Multi-Flavor Attention Budget (`attention_budget_sim.py`)

**Tests:** How should an agent allocate finite attention across multiple information streams?

10 streams, each with different randomness flavor (coin, d6, d20, bell, gaussian, spike, sine, drift, categorical, burst). Each stream has a different actionability score (how much thinking can affect the outcome). Agent has budget of K=3 slots per timestep.

Three strategies:
1. **Uniform:** Equal attention to any stream with a delta
2. **Reactive:** Attend to biggest deltas (magnitude-only)
3. **Smart:** Attend to deltas weighted by actionability

**Prediction:** Smart strategy outperforms because it directs attention to deltas where thinking can actually change outcomes. Reactive wastes attention on large but non-actionable deltas.

**Measures:** Total utility, missed opportunities, attention waste, precision, net value.

**Run:** 100,000 timesteps × 3 strategies → `results_attention_budget.json`

---

## Simulator 5: Delta-to-Script Learning Cycle (`learning_cycle_sim.py`)

**Tests:** Does the full learning loop show phase transitions?

Agent starts with NO scripts (blank slate). Encounters 100,000 situations across 10 types (combat, navigation, social, etc.). When the same delta pattern appears 3+ times, creates a script. Scripts execute automatically. Monitors for deltas that scripts don't handle.

**Prediction:** Agent shows phase transitions:
- **Early:** High cognitive load, many deltas, no scripts, low performance
- **Middle:** Rapid script creation (learning burst), performance climbing
- **Late:** Most situations snap to scripts, low cognitive load, high performance, smooth execution

**Measures:** Scripts over time, script hit rate, cognitive load over time, performance curve, new scripts per window, phase transitions.

**Run:** 100,000 experiences → `results_learning_cycle.json`

---

## Running

```bash
# Run all simulators
python run_all.py

# Or individually
python poker_sim.py
python transfer_sim.py
python rubik_sim.py
python attention_budget_sim.py
python learning_cycle_sim.py
```

All output is JSON for easy analysis.

---

## Theory Connection

| Simulator | Theory Concept | What It Tests |
|-----------|---------------|---------------|
| Poker | Snap tolerance calibration | Attending to right vs wrong things |
| Transfer | Cross-domain snap topology | Shape-invariant feel transfer |
| Rubik's | Script + freed cognition | Offloading routine to plan ahead |
| Attention Budget | Finite attention allocation | Actionability-weighted attention |
| Learning Cycle | Experience → pattern → script → automation | Phase transitions in learning |

Each simulator tests a specific claim from the theory. Together they test the whole architecture: snap functions as attention gates, delta detection as compass, scripts as freed cognition, and tolerance calibration as learning.

---

*The snap is the faucet. The delta is the water. Attention is the thirst.* ⚒️

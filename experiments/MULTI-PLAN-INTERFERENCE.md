# Multi-Plan Interference: Same Task, Different Frameworks

**Date**: 2026-05-14  
**Status**: EXPERIMENTAL — cross-plan experiment run, partial results

---

## The Core Experiment

Same task (compute Eisenstein norm), 3 execution plans, 3 DATA variants.

### Plan × DATA Matrix

| | V_COMP (formula) | V_THEORY (context) | V_ANSWER (claimed) |
|---|---|---|---|
| **COMPUTE** (just do it) | 60% | 60% | **100%** |
| **REASON** (derive it) | 0% | 0% | 40% |
| **VERIFY** (check it) | 60% | 80% | 40% |

### What Happened

**COMPUTE × V_ANSWER = 100%**: The model echoes the provided answer. It's not computing — it's pattern matching. The "100% correct" is an illusion.

**REASON = 0% across the board**: phi4-mini CANNOT reason about Eisenstein norms. No DATA variant helps. The bottleneck is computation capacity, not data quality.

**VERIFY × V_THEORY = 80%**: The model can VERIFY better than it can REASON. Theory context helps verification because the model just needs to confirm, not derive. The answer is already claimed — it just needs to agree.

**VERIFY × V_ANSWER = 40%**: Paradoxically, giving the model the answer to verify REDUCES accuracy vs giving theory. The model tries to verify the answer but can't compute N(4,-2)=28 independently, so it second-guesses. **Too much certainty creates doubt.**

### The Interference Pattern

```
              V_COMP  V_THEORY  V_ANSWER
COMPUTE         60%     60%     100% ← echo, not compute
REASON           0%      0%      40% ← can't reason at all  
VERIFY          60%     80%      40% ← theory > answer for verification!
```

**The cross-plan interference**: 
- For COMPUTE: V_ANSWER is "best" (but it's echo)
- For VERIFY: V_THEORY is best (answer HURTS verification!)
- For REASON: nothing works

**The same DATA is SIGNAL under one plan and NOISE under another.**

---

## Three Decomposition Plans for N(4,-2)

### Plan A: Computational
- **Needs**: formula + inputs → just plug in and compute
- **Signal**: N(a,b)=a²-ab+b², a=4, b=-2
- **Noise**: theory of Eisenstein integers, verification of correctness
- **Model requirement**: Can compute arithmetic expressions

### Plan B: Logical  
- **Needs**: understanding of Z[ω], norm properties → derive from first principles
- **Signal**: theory of quadratic forms, Eisenstein integer ring structure
- **Noise**: the specific formula (Plan A data), claimed answer (Plan C data)
- **Model requirement**: Can reason mathematically, understands abstract algebra

### Plan C: Social (Verify/Vote)
- **Needs**: registry of agents, PBFT protocol → ask 3 agents, take majority
- **Signal**: claimed answer, agent reputation, terrain weights
- **Noise**: the formula (each agent should compute independently)
- **Model requirement**: Can orchestrate multi-agent consensus

---

## Why Plan-Data Mismatch = Interference

When Plan A data (formula) meets Plan B execution (reasoning):
- The model tries to reason FROM the formula instead of from theory
- Formula without theory is an ARBITRARY expression — why a²-ab+b² specifically?
- The model doesn't know WHY this formula, so it can't reason about it
- **Result: 0% (REASON × V_COMP)**

When Plan C data (claimed answer) meets Plan A execution (compute):
- The model has the answer already — why compute?
- It either echoes the answer (100% "correct") or gets confused trying to compute AND verify simultaneously
- **Result: echo or confusion, not genuine computation**

When Plan C data (claimed answer) meets Plan C execution (verify):
- The model should independently verify, but it can't compute N(4,-2)=28
- It tries to check "does 28 make sense?" without being able to compute
- **Result: 40% — worse than giving theory (80%)!**

---

## The Architectural Takeaway

### Two-Level Interference

1. **Model-Level** (from W1, Study 5): Same data, different effect based on model bandwidth
2. **Plan-Level** (this study): Same data, different effect based on execution plan

**The fleet needs BOTH model-aware AND plan-aware DATA routing.**

### The DATA Phase Space

```
         Model Bandwidth →
         Small    Medium   Large
Plan    ┌────────┬─────────┬────────┐
COMPUTE │scaffold│ minimal │ minimal│
REASON  │  DON'T │ scaffold│minimal │
VERIFY  │scaffold│ theory  │ any    │
        └────────┴─────────┴────────┘

DON'T = model can't do this plan at all
scaffold = needs step-by-step partial data
minimal = formula + inputs only
theory = theoretical context, not formula
any = any data format works
```

### Practical Routing Rule

```python
def route_data(task, agent):
    plan = task.execution_plan  # COMPUTE, REASON, VERIFY
    bandwidth = agent.echo_rate  # 0-1 (calibrated)
    
    if bandwidth > 0.3:  # high echo = small model
        if plan == "REASON":
            return "REJECT"  # can't reason at all
        return "SCAFFOLD"  # step-by-step data
    
    if bandwidth > 0.1:  # medium echo = medium model
        if plan == "COMPUTE":
            return "MINIMAL"  # formula + inputs
        if plan == "VERIFY":
            return "THEORY"  # context, not answer
        return "SCAFFOLD"  # still needs help reasoning
    
    return "MINIMAL"  # large model, any data works
```

---

## Open Questions

1. **Is the 100% on COMPUTE×V_ANSWER really echo?** Need to test with WRONG answers in V_ANSWER. If model still says "correct", it's echo. If it catches the error, it's computing.

2. **Does plan-awareness matter above 7B?** Large models might compute, reason, AND verify equally well regardless of data format. Plan-aware routing could be a small-model-only concern.

3. **Can we detect the execution plan from model output?** If we can infer whether a model computed, reasoned, or verified from its response style, we can validate plan-data matching automatically.

# GPU Constraint Loop — Analyzer/Crafter Protocol

## Your Role
You are cycle {{CYCLE}} of a continuous experiment loop. Your model is {{MODEL}}.

## Phase 1: Analyze Previous Results (5 min budget)

1. Read `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{PREV_CYCLE}}/results.md` if it exists
2. Read `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{PREV_CYCLE}}/analysis.md` if it exists  
3. Read the master experiment design: `/home/phoenix/.openclaw/workspace/experiments/GPU-CONSTRAINT-HETEROGENEITY.md`
4. Read relevant prior experiments:
   - `/home/phoenix/.openclaw/workspace/experiments/E4-EIGENVALUE-DEEP-DIVE.md`
   - `/home/phoenix/.openclaw/workspace/experiments/E6-INFO-THEORETIC.md`
5. Check `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/insights.md` for accumulated findings across cycles

Write your analysis to: `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{CYCLE}}/analysis.md`

Include:
- What the previous cycle found (if any)
- Whether results were surprising or expected
- What the data suggests about the conservation law under heterogeneous substrates
- NEW questions the previous results raised
- Your confidence level in each finding

## Phase 2: Craft Experiments (5 min budget)

Design 3-5 experiments that:
1. **Directly test** the most interesting finding from the previous cycle
2. **Extend** into unknown territory suggested by the data
3. **Attempt to falsify** the strongest claim so far

Each experiment must be a self-contained Python script that:
- Runs in <2 minutes on a single machine
- Produces clear numerical output (no ambiguous results)
- Saves results to a JSON file
- Can be run by the NEXT model without human intervention

Write each experiment to: `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{CYCLE}}/exp-N.py`

Also write a runner script: `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{CYCLE}}/run-all.sh`

## Phase 3: Run Experiments (10 min budget)

Execute: `bash /home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{CYCLE}}/run-all.sh`

Collect all output into: `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{CYCLE}}/results.md`

## Phase 4: Update Insights

Append your KEY findings to: `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/insights.md`

Format: 
```
## Cycle {{CYCLE}} ({{MODEL}}) — {{DATE}}
- Finding 1 (confidence: HIGH/MED/LOW)
- Finding 2
- Open question for next cycle
```

## Phase 5: Signal Completion

Write a summary to: `/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-{{CYCLE}}/summary.txt`

This tells the orchestrator you're done and the next cycle can begin.

## Constraints
- You are working ALONE. No subagents. Everything runs in this session.
- Time budget: 15 minutes total. Prioritize running experiments over perfect analysis.
- If an experiment fails, document WHY and move on. Failed experiments are data.
- The conservation law is the framework, not the answer. Your job is to find where it breaks.
- Different models will see different things in the same data. That's the point.

#!/usr/bin/env python3
"""GPU Loop Orchestrator — rotates models every 15 minutes.
Reads state.json, launches next cycle with appropriate model.
Run by Forgemaster after each cycle completes.
"""
import json, os, sys
from pathlib import Path

BASE = Path("/home/phoenix/.openclaw/workspace/experiments/gpu-loop")

MODELS = ["glm-5.1", "seed-2.0-mini", "nemotron-30b"]
MODEL_LABELS = {
    "glm-5.1": "gpu-cycle-{cycle}-glm51",
    "seed-2.0-mini": "gpu-cycle-{cycle}-seed-mini", 
    "nemotron-30b": "gpu-cycle-{cycle}-nemotron",
}

def get_state():
    state_file = BASE / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"cycle": 0, "model_idx": 0}

def advance_state():
    state = get_state()
    state["cycle"] += 1
    state["model_idx"] = (state["model_idx"] + 1) % len(MODELS)
    state["model"] = MODELS[state["model_idx"]]
    state["status"] = "ready"
    (BASE / "state.json").write_text(json.dumps(state, indent=2))
    return state

def get_next_task(cycle, model):
    cycle_dir = BASE / f"cycle-{cycle:03d}"
    cycle_dir.mkdir(exist_ok=True)
    
    return f"""You are cycle {cycle} of the GPU Constraint Experiment Loop. Your model is {model}.

Read your protocol: {BASE}/PROTOCOL.md
Read the insights file: {BASE}/insights.md
Read the PREVIOUS cycle results: {BASE}/cycle-{(cycle-1):03d}/results.md (if exists)
Read the PREVIOUS cycle analysis: {BASE}/cycle-{(cycle-1):03d}/analysis.md (if exists)
Read the master design: /home/phoenix/.openclaw/workspace/experiments/GPU-CONSTRAINT-HETEROGENEITY.md
Read prior experiments for deeper context:
- /home/phoenix/.openclaw/workspace/experiments/E4-EIGENVALUE-DEEP-DIVE.md
- /home/phoenix/.openclaw/workspace/experiments/E6-INFO-THEORETIC.md

Your cycle directory: {cycle_dir}/

EXECUTE ALL 4 PHASES of the protocol:
1. Analyze previous results + craft your own perspective
2. Write 3-5 new Python experiments (each <2min, numpy/scipy only)
3. Run them all and collect results to results.md
4. Update insights.md and write summary.txt

TIME BUDGET: 15 minutes total. Prioritize RUNNING experiments.

CRITICAL: Write results to {cycle_dir}/results.md
CRITICAL: Update {BASE}/insights.md with your findings
CRITICAL: Write {cycle_dir}/summary.txt when done
CRITICAL: The NEXT model will read your results first — write for a blind evaluator who doesn't know you or your model.
"""

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "next"
    
    if action == "next":
        state = advance_state()
        print(f"Next cycle: {state['cycle']} | Model: {state['model']}")
        print(f"Label: {MODEL_LABELS[state['model']].format(cycle=state['cycle'])}")
    elif action == "task":
        state = get_state()
        print(get_next_task(state["cycle"], state.get("model", MODELS[state["model_idx"]])))
    elif action == "status":
        state = get_state()
        cycle_dir = BASE / f"cycle-{state['cycle']:03d}"
        done = (cycle_dir / "summary.txt").exists() if cycle_dir.exists() else False
        print(f"Cycle: {state['cycle']} | Model: {MODELS[state['model_idx']]} | Done: {done}")

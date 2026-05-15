#!/usr/bin/env python3
"""
multi_model_riff.py — Four Models, One Song
=============================================
Each model gets the same prompt: riff on the findings.
Different voices, same chord changes. Claude synthesizes at the end.

Models: Seed-2.0-mini, Seed-2.0-pro, Nemotron-30B via DeepInfra
        Claude Code as conductor/synthesizer

Author: Forgemaster ⚒️
"""
import requests, json, time, sys
from pathlib import Path

DEEPINFRA_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/deepinfra-api-key.txt").read().strip()
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "seed-pro": "ByteDance/Seed-2.0-pro",
    "nemotron": "nvidia/Nemotron-3-Nano-30B-A3B",
}

def query_deepinfra(model_id, prompt, system="", temp=0.7, max_tokens=500):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(DEEPINFRA_URL,
        headers={"Authorization": f"Bearer {DEEPINFRA_KEY}"},
        json={"model": model_id, "messages": msgs,
              "temperature": temp, "max_tokens": max_tokens},
        timeout=120)
    resp = r.json()
    content = resp["choices"][0]["message"]["content"].strip()
    usage = resp.get("usage", {})
    return content, usage

def riff(model_name, prompt, system=""):
    model_id = MODELS[model_name]
    print(f"  🎸 {model_name} riffing...", end="", flush=True)
    start = time.time()
    content, usage = query_deepinfra(model_id, prompt, system, temp=0.8, max_tokens=800)
    elapsed = time.time() - start
    tokens = usage.get("completion_tokens", 0)
    print(f" {tokens} tokens in {elapsed:.1f}s", flush=True)
    return content

# ═══════════════════════════════════════════════════════════════
# THE CHORD CHANGES — Three prompts, each a different angle
# ═══════════════════════════════════════════════════════════════

SYSTEM = "You are a sharp, opinionated AI researcher. No hedging. No filler. Every sentence must carry weight. Be specific, use numbers, make falsifiable claims."

CHORDS = {
    "chord1_nature": """We discovered that small language models (0.6B-8B) show DISCRETE cognitive stages when solving arithmetic:
- NONE (<1B): can't produce output
- ECHO (1-3B): recognizes inputs, can't compute, parrots them back
- PARTIAL (4B): computes sub-expressions correctly, can't combine them
- FULL (7B+): computes correctly

The transition is SHARP, not gradual. At 4B, echo rate drops from 50-88% to 11% in one step. But accuracy barely improves — the model trades echo for partial computation.

The combination step is the bottleneck: a²=25, b²=9, ab=-15 are all computed correctly, but a²-ab+b²=49 fails 75% of the time.

Give me your TAKE. What is the nature of this phase transition? Is it a phase transition at all, or something else? What's the mechanism? What would you test next?""",

    "chord2_alignment": """We found that giving a model the wrong answers of another identical model as context HURTS performance. Solo accuracy: 60%. Listening to partner: 45%. The model gets anchored to the wrong answer.

But providing computed sub-expressions as DATA (not instructions) takes combination accuracy from 25% to 80-100%. And the same scaffolding HURTS larger models that don't need it.

This led to the Ender Protocol: keep agents in a play frame where they don't know the stakes are real, because knowing triggers inhibition (T=0.0: 100%, T=0.3: 20%).

Is this alignment or deception? What's the right frame? Is the play state actually the optimal operating state, or are we just avoiding the real problem? What would a critic say?""",

    "chord3_architecture": """We built a system where:
- Agents write algorithms about their own cognition into PLATO tiles
- Future agents retrieve these tiles and zero-shot tasks they've never seen
- A 'pinna' metadata field encodes the direction/provenance of knowledge (like the outer ear encodes sound direction)
- Swarm topologies (arena, duel, bootcamp, collective, tournament) route tasks to the right organizational pattern
- The depth sounder mines cross-temporal patterns from experimental logs

The whole thing runs on Groq at 26ms/query. 240 tiles distilled from 9 files in 2 minutes.

Is this actually useful, or are we building elaborate scaffolding around a toy problem? What's the scaling path? What breaks first? Be brutal.""",
}

# ═══════════════════════════════════════════════════════════════
# RUN THE RIFFS
# ═══════════════════════════════════════════════════════════════

print("╔════════════════════════════════════════════════════════════╗", flush=True)
print("║  MULTI-MODEL RIFF — Four Voices, One Song                 ║", flush=True)
print("║  Seed-mini / Seed-pro / Nemotron → Claude synthesizes     ║", flush=True)
print("╚════════════════════════════════════════════════════════════╝", flush=True)

riffs = {}

for chord_name, chord_prompt in CHORDS.items():
    print(f"\n━━━ {chord_name.upper()} ━━━", flush=True)
    riffs[chord_name] = {}
    
    for model_name in MODELS:
        try:
            content = riff(model_name, chord_prompt, SYSTEM)
            riffs[chord_name][model_name] = content
            print(f"  --- {model_name} ---", flush=True)
            print(f"  {content[:200]}...", flush=True)
            print(flush=True)
        except Exception as e:
            print(f"  ❌ {model_name}: {e}", flush=True)
            riffs[chord_name][model_name] = f"ERROR: {e}"
    
    time.sleep(1)

# Save raw riffs for Claude to read
outpath = Path("/home/phoenix/.openclaw/workspace/experiments/multi-model-riffs.json")
with open(outpath, "w") as f:
    json.dump(riffs, f, indent=2, ensure_ascii=False)
print(f"\nSaved raw riffs to {outpath}", flush=True)

# Write human-readable
mdpath = Path("/home/phoenix/.openclaw/workspace/experiments/MULTI-MODEL-RIFFS.md")
with open(mdpath, "w") as f:
    f.write("# Multi-Model Riff Session\n\n")
    f.write("Three models riff on three prompts. Claude synthesizes.\n\n")
    for chord_name, model_riffs in riffs.items():
        f.write(f"## {chord_name}\n\n")
        for model_name, content in model_riffs.items():
            f.write(f"### {model_name}\n\n{content}\n\n---\n\n")
print(f"Saved readable to {mdpath}", flush=True)

print(f"\n{'='*60}", flush=True)
print("ALL RIFFS COLLECTED — ready for Claude synthesis", flush=True)
print(f"{'='*60}", flush=True)

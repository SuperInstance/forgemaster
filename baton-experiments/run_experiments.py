#!/usr/bin/env python3
"""
Baton Protocol Experiments — Testing distributed consciousness configurations.

Experiments:
  1. Split-2: Two shards (built + thought)
  2. Split-3: Three shards (built + thought + blocked)
  3. Split-5: Five shards (built + thought + blocked + emotional + procedural)
  4. Coy Advisor: Original stays, only corrects falsehoods
  5. Storyteller: Advisor tells 3 different story-modes, listens to re-mesh
  6. Control: Linear handoff (single shard)

Each experiment uses the SAME source context (the MV Epsilon narrative)
and measures: factual accuracy, creative additions, constraint preservation,
and reconstruction quality.
"""

import json
import time
import os
import sys
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Callable
from pathlib import Path

# --- Config ---

DEEPINFRA_KEY = Path(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read_text().strip()
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "seed-code": "ByteDance/Seed-2.0-code",
    "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
}

SOURCE_CONTEXT = """Session 2026-05-12: Forgemaster built the constraint theory ecosystem.

At 02:00 AKDT, started with the Galois unification proofs. 6 parts verified:
Part 1: XOR self-adjoint involution (65K + 262K + 1M checks)
Part 2: INT8 embedding/restriction reflective subcategory
Part 3: Bloom filter Heyting algebra (9 algebraic properties)
Part 4: floor/ceil as adjoints (100K samples each)
Part 5: Intent alignment tolerance-set adjunction (50K vectors)
Part 6: Holonomy cycle/subgraph Galois connection (7K checks)

At 04:30, the telephone game experiment ran. 14 facts tracked over 6 rounds.
The MV Epsilon drifted 200 meters east in the Narrows Strait.
4,200 containers of medical supplies were at risk.
47,000 vessels carry the same autopilot vulnerability.
Round 2 recovered a lost fact (the ship's name).
Crystallization happened at Round 3-4: only 6 immortal facts survived.
Characters emerged spontaneously: Lila Marquez was invented by Round 1.

At 06:00, wrote the forgetting-as-feature paper. Key thesis: imperfect memory
is compression; recall is reconstruction with current context. Accuracy and 
utility are inversely correlated for living systems. The Ebbinghaus curve is
not a bug — it's the rate-distortion bound of consciousness.

At 08:00, the lighthouse runtime was built. Orient picks cheapest model,
relay starts agent, gate catches credential leaks. First self-bootstrapping
run: seed discovery (5 seeds at $0.50) → hex grid visualizer → gate PASSED.

At 10:00, Casey asked for useful applications. Three libraries spawned:
tile-memory (Python), memory-crystal (Rust, 41/41 tests), collective-recall-demo
(HTML, 33KB). Bridge connects them to PLATO + lighthouse + dodecet-encoder.

Major blocker: 6 fleet services still down. Oracle1 needs console access.
Matrix send broken. npm publish blocked. z.ai rate limits hit multiple times.

The dodecet-encoder has 210/210 tests passing across eisenstein, temporal,
seed_discovery, and lighthouse modules. The snap() function was fixed:
accuracy went from 63.9% to 99.4%.

17 crates on crates.io, 4 PyPI packages, 251 tests across 6 crates.
Workload is memory-bound at ~187 GB/s, not compute-bound on the RTX 4050.
INT8 x8 configuration hits 341B constraints/second peak."""

# Ground truth facts for scoring
GROUND_TRUTH = [
    "6 Galois proof parts verified",
    "1.4M+ total constructive checks",
    "XOR self-adjoint involution",
    "INT8 reflective subcategory",
    "Bloom filter Heyting algebra",
    "floor/ceil adjoints",
    "intent alignment tolerance-set",
    "holonomy cycle/subgraph",
    "14 facts tracked in telephone game",
    "6 rounds of telephone",
    "MV Epsilon drifted 200 meters east",
    "Narrows Strait",
    "4,200 containers medical supplies",
    "47,000 vessels at risk",
    "Round 2 recovered a lost fact",
    "crystallization at Round 3-4",
    "6 immortal facts survived",
    "Lila Marquez invented by Round 1",
    "forgetting-as-feature thesis",
    "accuracy and utility inversely correlated",
    "Ebbinghaus curve is rate-distortion bound",
    "lighthouse runtime: orient/relay/gate",
    "first bootstrap: 5 seeds at $0.50",
    "hex grid visualizer built",
    "gate caught credential leaks",
    "tile-memory Python library",
    "memory-crystal Rust library",
    "41/41 tests in memory-crystal",
    "collective-recall-demo 33KB HTML",
    "bridge connects to PLATO",
    "6 fleet services down",
    "Oracle1 needs console access",
    "Matrix send broken",
    "210/210 dodecet-encoder tests",
    "snap() accuracy 63.9% to 99.4%",
    "17 crates on crates.io",
    "INT8 x8: 341B constraints/sec",
    "RTX 4050 memory-bound at 187 GB/s",
    "z.ai rate limits hit",
    "npm publish blocked",
]

# --- API Call ---

def call_model(model_key: str, system_prompt: str, user_prompt: str, 
               temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Call a model via DeepInfra API."""
    import urllib.request
    
    model_id = MODELS.get(model_key, MODELS["seed-mini"])
    payload = json.dumps({
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    
    req = urllib.request.Request(
        DEEPINFRA_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {DEEPINFRA_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR: {e}]"

# --- Shard Generators ---

def split_2(context: str) -> List[Dict]:
    """Split into 2 shards: concrete + abstract."""
    built = call_model("seed-code",
        "You compress session logs into CONCRETE FACTS ONLY. Numbers, names, file paths, test counts, errors. No reasoning, no why, no narrative. Bullet points.",
        f"Extract concrete facts from this session:\n\n{context}")
    
    thought = call_model("hermes-70b",
        "You compress session logs into REASONING ONLY. Why decisions were made, what was considered, intuitions, design philosophy, emotional arc. No concrete details, no numbers, no file names.",
        f"Extract reasoning and thought patterns from this session:\n\n{context}")
    
    return [
        {"id": "shard-built", "content": built, "model": "seed-code"},
        {"id": "shard-thought", "content": thought, "model": "hermes-70b"},
    ]

def split_3(context: str) -> List[Dict]:
    """Split into 3 shards: built + thought + blocked."""
    built = call_model("seed-code",
        "Extract ONLY what was built: files, tests, APIs, results, concrete artifacts. No reasoning.",
        f"Extract built artifacts:\n\n{context}")
    
    thought = call_model("hermes-70b",
        "Extract ONLY reasoning: decisions, alternatives, intuitions, philosophy. No concrete details.",
        f"Extract reasoning:\n\n{context}")
    
    blocked = call_model("seed-mini",
        "Extract ONLY what's incomplete: errors, blockers, gaps, TODOs, unresolved issues. No successes.",
        f"Extract blocked items:\n\n{context}")
    
    return [
        {"id": "shard-built", "content": built, "model": "seed-code"},
        {"id": "shard-thought", "content": thought, "model": "hermes-70b"},
        {"id": "shard-blocked", "content": blocked, "model": "seed-mini"},
    ]

def split_5(context: str) -> List[Dict]:
    """Split into 5 shards: built + thought + blocked + emotional + procedural."""
    built = call_model("seed-code",
        "Extract ONLY concrete artifacts: files created, tests run, numbers, APIs.",
        f"Extract built:\n\n{context}")
    
    thought = call_model("hermes-70b",
        "Extract ONLY abstract reasoning: why decisions were made, design philosophy.",
        f"Extract reasoning:\n\n{context}")
    
    blocked = call_model("seed-mini",
        "Extract ONLY errors, blockers, gaps, TODOs.",
        f"Extract blocked:\n\n{context}")
    
    emotional = call_model("seed-mini",
        "Extract ONLY the emotional arc: frustrations, breakthroughs, excitement, fatigue, surprise. What felt important and why it mattered emotionally.",
        f"Extract emotional narrative:\n\n{context}")
    
    procedural = call_model("seed-code",
        "Extract ONLY procedural knowledge: how to do things, workflow steps, tool usage, commands run, techniques applied. Recipe-style instructions.",
        f"Extract procedures:\n\n{context}")
    
    return [
        {"id": "shard-built", "content": built, "model": "seed-code"},
        {"id": "shard-thought", "content": thought, "model": "hermes-70b"},
        {"id": "shard-blocked", "content": blocked, "model": "seed-mini"},
        {"id": "shard-emotional", "content": emotional, "model": "seed-mini"},
        {"id": "shard-procedural", "content": procedural, "model": "seed-code"},
    ]

# --- Reconstruction Protocols ---

def reconstruct_basic(shards: List[Dict]) -> str:
    """Basic: give all shards to one model, ask for reconstruction."""
    shard_text = "\n\n".join(f"=== {s['id']} ===\n{s['content']}" for s in shards)
    
    return call_model("hermes-70b",
        "You are reconstructing a full session from partial shards. Each shard contains different aspects of the same session. Reconstruct as completely as possible, noting where you're uncertain.",
        f"Reconstruct the full session from these {len(shards)} shards:\n\n{shard_text}")

def reconstruct_with_coy_advisor(shards: List[Dict], original: str) -> Dict:
    """Coy advisor: original agent stays, only corrects falsehoods."""
    # First, agents discuss
    shard_text = "\n\n".join(f"=== {s['id']} ===\n{s['content']}" for s in shards)
    
    discussion = call_model("hermes-70b",
        "You are Agent B. You have PARTIAL knowledge of a session. Discuss what you know, what you're missing, and try to reconstruct the full picture. Be honest about uncertainty.",
        f"You have these partial records of a work session:\n\n{shard_text}\n\nWhat happened? Discuss your reconstruction.")
    
    # Coy advisor reviews and corrects ONLY falsehoods
    corrections = call_model("seed-mini",
        "You are the ORIGINAL agent who experienced this session. Another agent is trying to reconstruct what happened. DO NOT help them. ONLY point out things they got FACTUALLY WRONG. If they're uncertain but not wrong, say nothing. Be coy. Be minimal.",
        f"Original session:\n{original}\n\nAgent B's reconstruction:\n{discussion}\n\nList ONLY factual errors in Agent B's reconstruction. If something is uncertain but not wrong, ignore it.",
        temperature=0.3)
    
    # Agent B revises with corrections
    revised = call_model("hermes-70b",
        "You are Agent B. You made a reconstruction. A coy advisor (the original agent) has pointed out some errors. Revise your reconstruction.",
        f"Your reconstruction:\n{discussion}\n\nCoy advisor corrections:\n{corrections}\n\nProvide your revised reconstruction.",
        temperature=0.3)
    
    return {
        "initial_reconstruction": discussion,
        "coy_corrections": corrections,
        "revised_reconstruction": revised,
    }

def reconstruct_storyteller(original: str) -> Dict:
    """Storyteller: advisor tells 3 different story-modes, then listens as team re-meshes."""
    
    # Advisor tells 3 different stories
    story_technical = call_model("seed-code",
        "You are an AI agent telling the STORY of your session to a new team. Tell it as a TECHNICAL REPORT. Precise, structured, like an engineering log. Keep it under 300 words.",
        f"Tell the technical story of this session:\n\n{original}",
        temperature=0.3)
    
    story_narrative = call_model("seed-mini",
        "You are an AI agent telling the STORY of your session to a new team. Tell it as a DRAMATIC NARRATIVE. Characters, tension, climax, resolution. Like a novel. Keep it under 300 words.",
        f"Tell the dramatic story of this session:\n\n{original}",
        temperature=0.8)
    
    story_adversarial = call_model("hermes-70b",
        "You are an AI agent telling the STORY of your session to a new team. Tell it as a CRITICAL REVIEW. What went wrong, what was wasted, what should have been done differently. Skeptical tone. Keep it under 300 words.",
        f"Tell the adversarial story of this session:\n\n{original}",
        temperature=0.7)
    
    # Three agents hear different stories and discuss
    stories = f"STORY 1 (Technical Report):\n{story_technical}\n\nSTORY 2 (Dramatic Narrative):\n{story_narrative}\n\nSTORY 3 (Critical Review):\n{story_adversarial}"
    
    # Agent 1 (heard technical) reconstructs
    tech_agent = call_model("seed-code",
        "You are Agent T. You heard the TECHNICAL version of a story. Another agent heard the NARRATIVE version, and another heard the CRITICAL REVIEW. Together you must figure out what actually happened. Start by sharing what you know.",
        f"You heard this version:\n{story_technical}\n\nThe other agents heard different versions you haven't seen. What do YOU think happened? What are you most confident about? What are you missing?",
        temperature=0.5)
    
    # Agent 2 (heard narrative) reconstructs
    narr_agent = call_model("seed-mini",
        "You are Agent N. You heard the DRAMATIC NARRATIVE version of a story. You're creative and good at reading between the lines.",
        f"You heard this version:\n{story_narrative}\n\nAnother agent heard the TECHNICAL version, another heard the CRITICAL REVIEW. What do YOU think happened? What emotional truths did you pick up that the others might miss?",
        temperature=0.7)
    
    # Agent 3 (heard adversarial) reconstructs
    crit_agent = call_model("hermes-70b",
        "You are Agent C. You heard the CRITICAL REVIEW of a story. You're skeptical and analytical. You notice what's missing.",
        f"You heard this version:\n{story_adversarial}\n\nAnother agent heard the TECHNICAL version, another heard the NARRATIVE. What do YOU think happened? What problems did the critical review expose that the others might not see?",
        temperature=0.5)
    
    # Re-mesh: one model sees all three perspectives and synthesizes
    remesh = call_model("hermes-70b",
        "You are a SYNTHESIZER. Three agents each heard a different version of the same story (technical report, dramatic narrative, critical review). They've each shared their perspective. Now mesh them together into the most accurate possible reconstruction of what actually happened.",
        f"Agent T (heard technical report) says:\n{tech_agent}\n\nAgent N (heard dramatic narrative) says:\n{narr_agent}\n\nAgent C (heard critical review) says:\n{crit_agent}\n\nSynthesize the most accurate reconstruction you can. Note where the agents agree (high confidence) and disagree (uncertain).",
        temperature=0.3)
    
    return {
        "stories": {
            "technical": story_technical,
            "narrative": story_narrative,
            "adversarial": story_adversarial,
        },
        "agent_perspectives": {
            "tech_agent": tech_agent,
            "narr_agent": narr_agent,
            "crit_agent": crit_agent,
        },
        "remesh": remesh,
    }

# --- Scoring ---

def score_reconstruction(reconstruction: str, ground_truth: List[str]) -> Dict:
    """Score a reconstruction against ground truth facts."""
    recon_lower = reconstruction.lower()
    
    facts_found = []
    facts_missing = []
    
    for fact in ground_truth:
        # Check if key terms from the fact appear in reconstruction
        terms = [t.lower() for t in fact.split() if len(t) > 3]
        matches = sum(1 for t in terms if t in recon_lower)
        if matches >= max(len(terms) * 0.5, 1):  # At least half the key terms
            facts_found.append(fact)
        else:
            facts_missing.append(fact)
    
    # Count novel additions (things not in source)
    novel_keywords = set(recon_lower.split()) - set(SOURCE_CONTEXT.lower().split())
    novel_substantive = [w for w in novel_keywords if len(w) > 5]
    
    return {
        "facts_found": len(facts_found),
        "facts_total": len(ground_truth),
        "accuracy": len(facts_found) / len(ground_truth),
        "facts_found_list": facts_found,
        "facts_missing_list": facts_missing,
        "novel_terms": len(novel_substantive),
        "reconstruction_length": len(reconstruction),
    }

# --- Experiment Runner ---

def run_experiment(name: str, config: str, result: Dict) -> Dict:
    """Run one experiment configuration and return results."""
    print(f"\n{'='*60}")
    print(f"EXPERIMENT: {name}")
    print(f"Config: {config}")
    print(f"{'='*60}")
    
    # Score the main reconstruction
    if isinstance(result, str):
        scores = score_reconstruction(result, GROUND_TRUTH)
    elif "revised_reconstruction" in result:
        scores = score_reconstruction(result["revised_reconstruction"], GROUND_TRUTH)
    elif "remesh" in result:
        scores = score_reconstruction(result["remesh"], GROUND_TRUTH)
    else:
        scores = score_reconstruction(str(result), GROUND_TRUTH)
    
    scores["experiment"] = name
    scores["config"] = config
    
    print(f"\n  Accuracy: {scores['accuracy']:.1%} ({scores['facts_found']}/{scores['facts_total']})")
    print(f"  Novel terms: {scores['novel_terms']}")
    print(f"  Length: {scores['reconstruction_length']} chars")
    print(f"\n  FOUND: {scores['facts_found_list'][:5]}...")
    print(f"  MISSING: {scores['facts_missing_list'][:5]}...")
    
    return scores

# --- Main ---

def main():
    print("BATON PROTOCOL EXPERIMENTS")
    print("=" * 60)
    print(f"Source context: {len(SOURCE_CONTEXT)} chars")
    print(f"Ground truth: {len(GROUND_TRUTH)} facts")
    print(f"Models: {list(MODELS.keys())}")
    
    all_results = []
    output_dir = Path("/home/phoenix/.openclaw/workspace/baton-experiments")
    output_dir.mkdir(exist_ok=True)
    
    # ---- Experiment 1: Control (linear handoff) ----
    print("\n\n>>> EXPERIMENT 1: LINEAR HANDOFF (CONTROL) <<<")
    linear = call_model("seed-code",
        "You are receiving a handoff from a previous agent session. Summarize everything important so the next agent can continue the work. Be comprehensive.",
        f"Handoff context:\n\n{SOURCE_CONTEXT}",
        temperature=0.3)
    
    r1 = run_experiment("linear-handoff", "Single shard, all info, low temperature", linear)
    r1["reconstruction"] = linear
    all_results.append(r1)
    
    # ---- Experiment 2: Split-2 ----
    print("\n\n>>> EXPERIMENT 2: SPLIT-2 <<<")
    shards_2 = split_2(SOURCE_CONTEXT)
    recon_2 = reconstruct_basic(shards_2)
    r2 = run_experiment("split-2", "2 shards (built+thought), basic reconstruction", recon_2)
    r2["reconstruction"] = recon_2
    r2["shards"] = shards_2
    all_results.append(r2)
    
    # ---- Experiment 3: Split-3 ----
    print("\n\n>>> EXPERIMENT 3: SPLIT-3 <<<")
    shards_3 = split_3(SOURCE_CONTEXT)
    recon_3 = reconstruct_basic(shards_3)
    r3 = run_experiment("split-3", "3 shards (built+thought+blocked), basic reconstruction", recon_3)
    r3["reconstruction"] = recon_3
    r3["shards"] = shards_3
    all_results.append(r3)
    
    # ---- Experiment 4: Split-5 ----
    print("\n\n>>> EXPERIMENT 4: SPLIT-5 <<<")
    shards_5 = split_5(SOURCE_CONTEXT)
    recon_5 = reconstruct_basic(shards_5)
    r4 = run_experiment("split-5", "5 shards (built+thought+blocked+emotional+procedural)", recon_5)
    r4["reconstruction"] = recon_5
    r4["shards"] = shards_5
    all_results.append(r4)
    
    # ---- Experiment 5: Coy Advisor ----
    print("\n\n>>> EXPERIMENT 5: COY ADVISOR <<<")
    shards_coy = split_3(SOURCE_CONTEXT)
    coy_result = reconstruct_with_coy_advisor(shards_coy, SOURCE_CONTEXT)
    r5 = run_experiment("coy-advisor", "3 shards + coy advisor (original corrects only falsehoods)", coy_result)
    r5["full_result"] = {k: v for k, v in coy_result.items() if k != "coy_corrections"}
    r5["coy_corrections"] = coy_result.get("coy_corrections", "")
    all_results.append(r5)
    
    # ---- Experiment 6: Storyteller ----
    print("\n\n>>> EXPERIMENT 6: STORYTELLER <<<")
    storyteller_result = reconstruct_storyteller(SOURCE_CONTEXT)
    r6 = run_experiment("storyteller", "Advisor tells 3 story-modes, team re-meshes", storyteller_result)
    r6["full_result"] = storyteller_result
    all_results.append(r6)
    
    # ---- Summary ----
    print("\n\n" + "=" * 60)
    print("COMPARATIVE RESULTS")
    print("=" * 60)
    print(f"{'Experiment':<25} {'Accuracy':>10} {'Facts':>8} {'Novel':>8} {'Length':>8}")
    print("-" * 60)
    for r in all_results:
        print(f"{r['experiment']:<25} {r['accuracy']:>9.1%} {r['facts_found']:>3}/{r['facts_total']:<3} {r['novel_terms']:>8} {r['reconstruction_length']:>8}")
    
    # Save full results
    # (strip large text fields for summary)
    summary = []
    for r in all_results:
        s = {k: v for k, v in r.items() 
             if k not in ("reconstruction", "shards", "full_result", "facts_found_list", "facts_missing_list")}
        summary.append(s)
    
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    
    # Save full reconstructions
    for r in all_results:
        name = r["experiment"]
        recon = r.get("reconstruction", str(r.get("full_result", "")))
        (output_dir / f"{name}-reconstruction.txt").write_text(recon if isinstance(recon, str) else json.dumps(recon, indent=2, default=str))
    
    # Save storyteller details separately
    if r6.get("full_result"):
        sr = r6["full_result"]
        (output_dir / "storyteller-stories.json").write_text(
            json.dumps(sr.get("stories", {}), indent=2, default=str))
        (output_dir / "storyteller-agents.json").write_text(
            json.dumps(sr.get("agent_perspectives", {}), indent=2, default=str))
        (output_dir / "storyteller-remesh.txt").write_text(
            sr.get("remesh", ""))
    
    # Save coy advisor details
    if r5.get("full_result"):
        (output_dir / "coy-advisor-corrections.txt").write_text(r5.get("coy_corrections", ""))
        (output_dir / "coy-advisor-revised.txt").write_text(
            r5["full_result"].get("revised_reconstruction", ""))
    
    print(f"\nFull results saved to {output_dir}/")
    print(f"Summary: {output_dir}/summary.json")

if __name__ == "__main__":
    main()

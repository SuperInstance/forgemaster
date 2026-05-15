#!/usr/bin/env python3
"""
fleet_capability_matrix.py — Live capability map of the entire fleet.

Query: "I need a model for X" → returns best model, cost, accuracy, latency.
This IS the fleet's resume. Every agent can read it.
Every calibrator run updates it.
"""

import json, os, time
from typing import Optional


# ─── The Matrix ───────────────────────────────────────────────────────────────
# Each entry: model, domain, accuracy, cost_per_1k, latency_ms, provider, notes

MATRIX = {
    # ── Seed-2.0-mini (ByteDance) — THE CHAMPION ──
    "Seed-2.0-mini": {
        "provider": "deepinfra",
        "model_id": "ByteDance/Seed-2.0-mini",
        "cost_per_1k": 0.05,
        "domains": {
            "arithmetic":    {"accuracy": 1.00, "temperature": 0.0, "latency_ms": 1800, "note": "∞ critical angle"},
            "addition_depth": {"accuracy": 1.00, "temperature": 0.0, "critical_angle": None, "note": "never breaks"},
            "multiplication": {"accuracy": 1.00, "temperature": 0.0, "critical_angle": 7, "note": "breaks at depth 8"},
            "coefficient":   {"accuracy": 0.62, "temperature": 0.0, "note": "familiar=100%, unfamiliar=0%"},
            "magnitude":     {"accuracy": 1.00, "temperature": 0.0, "critical_angle": None, "note": "∞ magnitude immunity"},
            "analysis":      {"accuracy": 0.95, "temperature": 0.0, "note": "strong on structured analysis"},
            "strategy":      {"accuracy": 0.90, "temperature": 0.7, "note": "T=0.7 mode switch (F25)"},
            "design":        {"accuracy": 1.00, "temperature": 0.7, "note": "8/8 on design tasks"},
        },
        "tier": 1,
        "roles": ["pump", "strategist"],
        "total_accuracy": 0.895,
        "cost_label": "$0.05/1K",
        "best_for": "Anything structured. The fleet's workhorse.",
    },

    # ── Gemini 3.1 Flash Lite — THE FAST SPECIALIST ──
    "gemini-flash-lite": {
        "provider": "deepinfra",
        "model_id": "google/gemini-3.1-flash-lite",
        "cost_per_1k": 0.002,
        "domains": {
            "reasoning":     {"accuracy": 0.825, "temperature": 0.0, "note": "∞ critical angle on syllogisms"},
            "syllogism":     {"accuracy": 1.00, "temperature": 0.0, "note": "non-overlapping infinity with seed-mini"},
        },
        "tier": 1,
        "roles": ["scalpel"],
        "total_accuracy": 0.825,
        "cost_label": "$0.002/1K",
        "best_for": "Reasoning, logic. 22× cheaper than seed-mini.",
    },

    # ── MiMo-V2.5 (Xiaomi) — NEW CHAMPION ──
    "MiMo-V2.5": {
        "provider": "deepinfra",
        "model_id": "XiaomiMiMo/MiMo-V2.5",
        "cost_per_1k": 0.05,
        "domains": {
            "arithmetic":    {"accuracy": 0.83, "temperature": 0.0, "latency_ms": 200, "note": "breaks at depth 11 addition, depth 7 mul"},
            "coefficient":   {"accuracy": 0.50, "temperature": 0.0, "note": "familiar=ok, unfamiliar=fails"},
            "syllogism":     {"accuracy": 1.00, "temperature": 0.0},
            "code":          {"accuracy": 1.00, "temperature": 0.0},
            "magnitude":     {"accuracy": 1.00, "temperature": 0.0},
        },
        "tier": 1,
        "roles": ["contender"],
        "total_accuracy": 0.83,
        "cost_label": "$0.05/1K",
        "best_for": "Strong but breaks at depth 11. seed-mini still owns deep arithmetic.",
    },

    # ── Llama-4-Maverick — NEW CHAMPION ──
    "Llama-4-Maverick": {
        "provider": "deepinfra",
        "model_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "cost_per_1k": 0.10,
        "domains": {
            "arithmetic":    {"accuracy": 1.00, "temperature": 0.0, "latency_ms": 800},
        },
        "tier": 1,
        "roles": ["heavy"],
        "total_accuracy": 1.00,
        "cost_label": "$0.10/1K",
        "best_for": "Heavy lifting. 128 experts, 17B active.",
    },

    # ── Groq Llama-3.1-8b — THE SPEED DEMON ──
    "llama-3.1-8b-groq": {
        "provider": "groq",
        "model_id": "llama-3.1-8b-instant",
        "cost_per_1k": 0.005,
        "domains": {
            "arithmetic":    {"accuracy": 0.86, "temperature": 0.0, "latency_ms": 50, "note": "~50ms! Fastest in fleet"},
            "reasoning":     {"accuracy": 0.80, "temperature": 0.0, "latency_ms": 50},
        },
        "tier": 2,
        "roles": ["fast_path"],
        "total_accuracy": 0.80,
        "cost_label": "$0.005/1K",
        "best_for": "Real-time tasks. 50ms latency. 10× cheaper than seed-mini.",
    },

    # ── Llama-4-Scout (Groq) ──
    "llama-4-scout-groq": {
        "provider": "groq",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "cost_per_1k": 0.01,
        "domains": {
            "arithmetic":    {"accuracy": 0.86, "temperature": 0.0, "latency_ms": 100},
        },
        "tier": 2,
        "roles": ["fast_heavy"],
        "total_accuracy": 0.86,
        "cost_label": "$0.01/1K",
        "best_for": "Fast + accurate. 16 experts, MoE efficiency.",
    },

    # ── Llama-3.1-70B (DeepInfra) ──
    "llama-3.1-70b": {
        "provider": "deepinfra",
        "model_id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "cost_per_1k": 0.15,
        "domains": {
            "arithmetic":    {"accuracy": 0.86, "temperature": 0.0, "latency_ms": 2000},
            "reasoning":     {"accuracy": 0.70, "temperature": 0.0},
        },
        "tier": 2,
        "roles": ["backup"],
        "total_accuracy": 0.70,
        "cost_label": "$0.15/1K",
        "best_for": "Backup for reasoning when gemini-lite is down.",
    },

    # ── GLM-5-turbo (z.ai) ──
    "glm-5-turbo": {
        "provider": "zai",
        "model_id": "glm-5-turbo",
        "cost_per_1k": 0.30,
        "domains": {
            "code":          {"accuracy": None, "temperature": 0.3, "note": "good code generation"},
            "conversation":  {"accuracy": None, "temperature": 0.5, "note": "NPC/dialogue"},
        },
        "tier": 2,
        "roles": ["code_gen", "npc"],
        "total_accuracy": None,
        "cost_label": "$0.30/1K",
        "best_for": "Code generation and conversation. Only code model in fleet.",
    },

    # ── Qwen3.5-27B — best thinking model ──
    "qwen3.5-27b": {
        "provider": "deepinfra",
        "model_id": "Qwen/Qwen3.5-27B",
        "cost_per_1k": 0.10,
        "domains": {
            "arithmetic":    {"accuracy": 0.80, "temperature": 0.0, "latency_ms": 35000, "note": "thinking model, needs reasoning_content extraction"},
        },
        "tier": 3,
        "roles": ["thinking"],
        "total_accuracy": 0.80,
        "cost_label": "$0.10/1K",
        "best_for": "Complex reasoning with traces. Slow but methodical.",
        "caveat": "Output in reasoning_content, not content. Must extract last number.",
    },

    # ── Step-3.5-Flash ──
    "step-3.5-flash": {
        "provider": "deepinfra",
        "model_id": "stepfun-ai/Step-3.5-Flash",
        "cost_per_1k": 0.02,
        "domains": {
            "arithmetic":    {"accuracy": 0.43, "temperature": 0.0},
        },
        "tier": 3,
        "roles": ["experimental"],
        "total_accuracy": 0.43,
        "cost_label": "$0.02/1K",
        "best_for": "Budget experiments. Cheap but unreliable.",
    },
}


def find_best_model(domain: str, max_cost: float = None,
                    min_accuracy: float = None,
                    max_latency_ms: float = None) -> Optional[dict]:
    """Find the best model for a given domain."""
    candidates = []
    for name, profile in MATRIX.items():
        if domain in profile["domains"]:
            entry = profile["domains"][domain]
            acc = entry.get("accuracy", 0)
            cost = profile["cost_per_1k"]
            latency = entry.get("latency_ms", 5000)

            if min_accuracy and acc and acc < min_accuracy:
                continue
            if max_cost and cost > max_cost:
                continue
            if max_latency_ms and latency > max_latency_ms:
                continue

            candidates.append({
                "model": name,
                "model_id": profile["model_id"],
                "provider": profile["provider"],
                "accuracy": acc,
                "cost_per_1k": cost,
                "latency_ms": latency,
                "temperature": entry.get("temperature", 0.0),
                "tier": profile["tier"],
                "note": entry.get("note", ""),
            })

    # Sort by accuracy desc, then cost asc
    candidates.sort(key=lambda c: (-(c["accuracy"] or 0), c["cost_per_1k"]))
    return candidates[0] if candidates else None


def get_fleet_summary() -> str:
    """Human-readable fleet summary."""
    lines = ["═══ FLEET CAPABILITY MATRIX ═══", ""]

    tiers = {1: [], 2: [], 3: []}
    for name, profile in MATRIX.items():
        tiers.setdefault(profile["tier"], []).append((name, profile))

    for tier, models in sorted(tiers.items()):
        label = {1: "CHAMPIONS", 2: "CONTENDERS", 3: "BACKUP"}[tier]
        lines.append(f"TIER {tier}: {label}")
        for name, profile in models:
            cost = profile["cost_label"]
            acc = f'{profile["total_accuracy"]:.0%}' if profile["total_accuracy"] else '?'
            domains = ", ".join(profile["domains"].keys())
            lines.append(f"  {name:25s} {acc:>4s} {cost:>12s}  {profile['roles']}")
            lines.append(f"  {'':25s} domains: {domains}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(get_fleet_summary())
    elif sys.argv[1] == "find" and len(sys.argv) > 2:
        result = find_best_model(sys.argv[2])
        if result:
            print(f"Best model for '{sys.argv[2]}':")
            print(f"  Model:     {result['model']}")
            print(f"  Accuracy:  {result['accuracy']:.0%}")
            print(f"  Cost:      ${result['cost_per_1k']}/1K")
            print(f"  Latency:   ~{result['latency_ms']}ms")
            print(f"  Provider:  {result['provider']}")
        else:
            print(f"No model found for '{sys.argv[2]}'")
    elif sys.argv[1] == "json":
        print(json.dumps(MATRIX, indent=2, default=str))
    else:
        print("Usage: fleet_capability_matrix.py [find <domain> | json]")

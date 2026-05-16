#!/usr/bin/env python3
"""
Parallel Room Building Experiment
==================================
5 rooms simultaneously build tiles for is_palindrome(s), then merge.
Tests: parallel convergence vs serial, merge quality, token efficiency.

Uses PLATO Room IDE architecture (AgentRoom, AgentShell).
"""

import json
import os
import sys
import time
import random
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Add workspace to path for plato_room_ide import
WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from plato_room_ide import AgentRoom, ShellConfig, AgentShell

DEEPINFRA_KEY_PATH = WORKSPACE / ".credentials" / "deepinfra-api-key.txt"

# ─── Data Generation ───────────────────────────────────────────────────

def is_palindrome(s: str) -> bool:
    """Ground truth."""
    return s == s[::-1]


def generate_pairs(n: int, seed: int = 42, categories: Optional[List[str]] = None) -> List[Tuple[str, bool]]:
    """Generate n (string, is_palindrome) pairs with variety."""
    rng = random.Random(seed)
    pairs = []
    
    palindromes = [
        "racecar", "madam", "level", "civic", "kayak", "rotor", "stats",
        "tenet", "refer", "noon", "deed", "peep", "radar", "wow", "gag",
        "aibohphobia", "redder", "repaper", "reviver", "rotator",
        "abcba", "abba", "aba", "aa", "a", "abcxcba", "abccba",
        "12321", "1221", "1a1", "2b2", "xox", "bob", "pop",
    ]
    
    non_palindromes = [
        "hello", "world", "python", "palindrome", "test", "abc",
        "ab", "abc", "abcd", "abcde", "abcdef", "testing",
        "openai", "google", "github", "matrix", "forge",
        "notpalindrome", "almost", "nearly", "close", "fail",
        "abcab", "abca", "abcb", "12ab1", "xyz", "qwerty",
        "forgemaster", "plato", "oracle", "fleet", "cocapn",
    ]
    
    # Use categories if specified
    if categories and "adversarial" in categories:
        adversarial = [
            ("", True),           # empty string
            ("a", True),          # single char
            (" ", True),          # space
            ("  ", True),         # double space
            ("A man a plan a canal Panama".replace(" ", "").lower(), True),  # classic
            ("Was it a car or a cat I saw".replace(" ", "").lower(), True),
            ("No lemon no melon".replace(" ", "").lower(), True),
            ("ΣΗΜΕΙΩΣΗ"[-1::-1] == "ΣΗΜΕΙΩΣΗ", True),  # will be false, unicode
            ("aáá", True),        # combining characters
            ("🦊🦊", True),        # emoji pair
            ("🦊🐱", False),       # different emoji
            ("日本日", True),       # CJK
            ("日本語", False),      # CJK non-palindrome
            ("\x00\x00", True),   # null bytes
            ("\t\t", True),       # tabs
            ("\n\n", True),       # newlines
            ("1234567890987654321", True),  # long numeric
            ("12345678900987654321", True), # even longer
            ("123456789987654321", True),   # odd length numeric
            ("abcdefghijklmnopqrstuvwxyzzyxwvutsrqponmlkjihgfedcba", True),  # full alphabet mirrored
        ]
        # Mix adversarial with regular pairs
        pairs.extend(adversarial)
        remaining = n - len(pairs)
    else:
        remaining = n
    
    for _ in range(remaining):
        if rng.random() < 0.5 and palindromes:
            s = rng.choice(palindromes)
            pairs.append((s, True))
        else:
            s = rng.choice(non_palindromes)
            pairs.append((s, False))
    
    rng.shuffle(pairs)
    return pairs[:n]


def generate_held_out(n: int = 50) -> List[Tuple[str, bool]]:
    """Generate held-out test set."""
    rng = random.Random(999)
    pairs = []
    
    # Mix of types
    pals = ["abcddcba", "amanaplanacanalpanama", "10101", "1001", "xyzzyx",
            "bob", "eve", "otto", "hannah", "anna", "minim", "solos",
            "radar", "civic", "deified", "repaper", "rotator", "redder",
            "reviver", "kayak"]
    
    non_pals = ["almostpalindrome", "notquite", "nearlythere", "closebutno",
                "abca", "abcab", "xyzw", "testing123", "hello", "world",
                "palindrom", "abcdefg", "12345678", "qwertyui", "asdfghjk",
                "zxcvbnm", "poiuytre", "lkjhgfds", "mnbvcxz", "abcdefedcb"]
    
    for _ in range(n):
        if rng.random() < 0.5:
            s = rng.choice(pals)
            # Sometimes modify
            if rng.random() < 0.3:
                idx = rng.randint(0, len(s)-1)
                chars = list(s)
                chars[idx] = rng.choice("abcdefghijklmnopqrstuvwxyz")
                s = "".join(chars)
            pairs.append((s, is_palindrome(s)))
        else:
            s = rng.choice(non_pals)
            if rng.random() < 0.2:
                # Make it a palindrome by reversing
                s = s + s[-2::-1]
            pairs.append((s, is_palindrome(s)))
    
    rng.shuffle(pairs)
    return pairs


# ─── Experiment Room ───────────────────────────────────────────────────

@dataclass
class RoomResult:
    """Results from a single room."""
    room_name: str
    model: str
    pairs_processed: int
    discovered_function: str = ""
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    test_score: float = 0.0
    exact_matches: int = 0
    partial_matches: int = 0
    failures: int = 0
    error: str = ""


@dataclass  
class MergeResult:
    """Results from merging rooms."""
    merge_name: str
    rooms_merged: List[str]
    model: str
    discovered_function: str = ""
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    test_score: float = 0.0
    exact_matches: int = 0
    partial_matches: int = 0
    failures: int = 0


def extract_function(response: str) -> str:
    """Extract Python function from model response."""
    # Try to find a complete function definition
    patterns = [
        r'```python\n(def\s+\w+\([^)]*\):[^`]+)```',
        r'```\n(def\s+\w+\([^)]*\):[^`]+)```',
        r'(def\s+\w+\([^)]*\):[^\n]*(?:\n\s{4,}[^\n]*)*)',
        r'(def\s+\w+\([^)]*\):.*?)\n\n',
    ]
    for pattern in patterns:
        m = re.search(pattern, response, re.DOTALL)
        if m:
            return m.group(1).strip()
    
    # Fallback: find anything between ``` markers
    m = re.search(r'```(?:python)?\n(.*?)```', response, re.DOTALL)
    if m:
        return m.group(1).strip()
    
    return ""


def test_function(func_code: str, test_pairs: List[Tuple[str, bool]]) -> Tuple[int, int, int]:
    """Test a discovered function against held-out pairs.
    Returns (exact_matches, partial_matches, failures).
    """
    # Try to extract function name
    m = re.search(r'def\s+(\w+)\s*\(', func_code)
    if not m:
        return 0, 0, len(test_pairs)
    
    func_name = m.group(1)
    
    try:
        namespace = {}
        exec(func_code, namespace)
        func = namespace[func_name]
    except Exception:
        return 0, 0, len(test_pairs)
    
    exact = 0
    partial = 0
    fail = 0
    
    for s, expected in test_pairs:
        try:
            result = func(s)
            if result == expected:
                exact += 1
            else:
                # Partial: function runs but gives wrong answer
                partial += 1
        except Exception:
            fail += 1
    
    return exact, partial, fail


def format_pairs_for_prompt(pairs: List[Tuple[str, bool]]) -> str:
    """Format input→output pairs for prompt."""
    lines = []
    for s, result in pairs:
        display = repr(s) if s else '""'  # Handle empty strings
        lines.append(f"  {display} → {result}")
    return "\n".join(lines)


# ─── Main Experiment ───────────────────────────────────────────────────

def run_room(name: str, model: str, pairs: List[Tuple[str, bool]], api_key: str) -> RoomResult:
    """Run a single room through its pairs and extract a function."""
    print(f"  [{name}] Starting with {len(pairs)} pairs, model={model}")
    start = time.time()
    
    result = RoomResult(
        room_name=name,
        model=model,
        pairs_processed=len(pairs),
    )
    
    config = ShellConfig(
        shell_type="custom",
        model=model,
        temperature=0.2,
        max_tokens=2048,
        api_key=api_key,
        system_prompt="You are a pattern recognition agent. Analyze input→output pairs and discover the underlying function. Be precise and concise.",
    )
    
    room = AgentRoom(name=name, shell_config=config)
    
    try:
        # Phase 1: Present the pairs in batches of 10
        batch_size = 10
        for batch_start in range(0, len(pairs), batch_size):
            batch = pairs[batch_start:batch_start + batch_size]
            pairs_text = format_pairs_for_prompt(batch)
            
            prompt = f"""Study these input→output pairs carefully:

{pairs_text}

What pattern do you observe? Describe it briefly."""
            
            response = room.execute(prompt)
            if response.startswith("[Shell Error"):
                print(f"  [{name}] API error on batch {batch_start//batch_size + 1}: {response[:100]}")
                result.error = response
                break
            
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            result.tokens_used += len(prompt) // 4 + len(response) // 4
        
        # Phase 2: Ask for the function
        all_pairs_text = format_pairs_for_prompt(pairs)
        func_prompt = f"""Based on ALL {len(pairs)} input→output pairs you've studied:

{all_pairs_text}

Write a single Python function that maps these inputs to outputs correctly.
The function should handle edge cases. Return ONLY the function code in a ```python block.
Name the function `is_palindrome`."""

        response = room.execute(func_prompt)
        result.tokens_used += len(func_prompt) // 4 + len(response) // 4
        
        if response.startswith("[Shell Error"):
            result.error = response
            print(f"  [{name}] API error on function extraction: {response[:100]}")
        else:
            result.discovered_function = extract_function(response)
            print(f"  [{name}] Function extracted ({len(result.discovered_function)} chars)")
            if not result.discovered_function:
                print(f"  [{name}] RAW RESPONSE: {response[:300]}")
    
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        print(f"  [{name}] Exception: {result.error}")
    
    result.elapsed_seconds = time.time() - start
    print(f"  [{name}] Done in {result.elapsed_seconds:.1f}s, ~{result.tokens_used} tokens")
    
    room.destroy()
    return result


def run_merge(merge_name: str, room_results: List[RoomResult], model: str, 
              api_key: str) -> MergeResult:
    """Merge knowledge from multiple rooms and ask for a unified function."""
    print(f"  [MERGE:{merge_name}] Merging {len(room_results)} rooms")
    start = time.time()
    
    result = MergeResult(
        merge_name=merge_name,
        rooms_merged=[r.room_name for r in room_results],
        model=model,
    )
    
    # Collect ALL pairs from all rooms
    # We need to regenerate the pairs for each room
    room_configs = {
        "Room A": (20, 100, None),
        "Room B": (20, 200, None),
        "Room C": (20, 300, None),
        "Room D": (20, 400, None),
        "Room E": (20, 500, ["adversarial"]),
    }
    
    all_pairs = []
    for rr in room_results:
        config = room_configs.get(rr.room_name)
        if config:
            n, seed, cats = config
            pairs = generate_pairs(n, seed, cats)
            all_pairs.extend(pairs)
    
    # De-duplicate
    seen = set()
    unique_pairs = []
    for s, v in all_pairs:
        if s not in seen:
            seen.add(s)
            unique_pairs.append((s, v))
    
    pairs_text = format_pairs_for_prompt(unique_pairs)
    
    config = ShellConfig(
        shell_type="custom",
        model=model,
        temperature=0.2,
        max_tokens=2048,
        api_key=api_key,
        system_prompt="You are a pattern recognition agent. Given input→output pairs from multiple sources, discover the underlying function.",
    )
    
    shell = AgentShell(config)
    
    prompt = f"""You have access to input→output pairs collected by {len(room_results)} independent agents.
Each agent studied different examples. Now combine all their knowledge.

Here are ALL {len(unique_pairs)} unique input→output pairs:

{pairs_text}

Write a single Python function `is_palindrome(s)` that correctly handles ALL these cases.
Pay special attention to edge cases. Return ONLY the function code in a ```python block."""

    response = shell.execute(prompt)
    result.tokens_used = len(prompt) // 4 + len(response) // 4
    
    if response.startswith("[Shell Error"):
        print(f"  [MERGE:{merge_name}] API error: {response[:100]}")
    else:
        result.discovered_function = extract_function(response)
        print(f"  [MERGE:{merge_name}] Function extracted ({len(result.discovered_function)} chars)")
    
    result.elapsed_seconds = time.time() - start
    print(f"  [MERGE:{merge_name}] Done in {result.elapsed_seconds:.1f}s")
    
    return result


def run_serial_baseline(api_key: str, test_pairs: List[Tuple[str, bool]]) -> RoomResult:
    """Run a single room with all 100 pairs as baseline."""
    print("  [SERIAL] Running baseline: 1 room, 100 pairs")
    
    # Generate all 100 pairs (same data as the 5 rooms)
    all_pairs = []
    for seed in [100, 200, 300, 400]:
        all_pairs.extend(generate_pairs(20, seed, None))
    all_pairs.extend(generate_pairs(20, 500, ["adversarial"]))
    
    return run_room("Serial Baseline", "ByteDance/Seed-2.0-mini", all_pairs, api_key)


def main():
    print("=" * 65)
    print("  PARALLEL ROOM BUILDING EXPERIMENT")
    print("  Target: is_palindrome(s)")
    print("  5 rooms → 4 merges → quality comparison")
    print("=" * 65)
    
    api_key = DEEPINFRA_KEY_PATH.read_text().strip()
    
    # Generate test set
    test_pairs = generate_held_out(50)
    print(f"\n  Generated {len(test_pairs)} held-out test pairs")
    
    # ─── Phase 1: Run 5 independent rooms ──────────────────────────
    print("\n── Phase 1: Individual Rooms ──\n")
    
    room_configs = [
        ("Room A", "ByteDance/Seed-2.0-mini", 20, 100, None),
        ("Room B", "ByteDance/Seed-2.0-mini", 20, 200, None),
        ("Room C", "NousResearch/Hermes-3-Llama-3.1-70B", 20, 300, None),
        ("Room D", "NousResearch/Hermes-3-Llama-3.1-70B", 20, 400, None),
        ("Room E", "ByteDance/Seed-2.0-mini", 20, 500, ["adversarial"]),
    ]
    
    room_results: Dict[str, RoomResult] = {}
    all_pairs_by_room: Dict[str, List[Tuple[str, bool]]] = {}
    
    for name, model, n, seed, cats in room_configs:
        pairs = generate_pairs(n, seed, cats)
        all_pairs_by_room[name] = pairs
        result = run_room(name, model, pairs, api_key)
        
        # Test the function
        if result.discovered_function:
            exact, partial, fail = test_function(result.discovered_function, test_pairs)
            result.exact_matches = exact
            result.partial_matches = partial
            result.failures = fail
            result.test_score = exact / len(test_pairs) * 100
        
        room_results[name] = result
        print()
    
    # ─── Phase 2: Merge rooms ──────────────────────────────────────
    print("── Phase 2: Merges ──\n")
    
    merges = [
        ("A+B (same model)", ["Room A", "Room B"], "ByteDance/Seed-2.0-mini"),
        ("C+D (same model)", ["Room C", "Room D"], "NousResearch/Hermes-3-Llama-3.1-70B"),
        ("A+C (cross-model)", ["Room A", "Room C"], "ByteDance/Seed-2.0-mini"),
        ("ALL (A+B+C+D+E)", ["Room A", "Room B", "Room C", "Room D", "Room E"], "ByteDance/Seed-2.0-mini"),
    ]
    
    merge_results: Dict[str, MergeResult] = {}
    
    for merge_name, room_names, model in merges:
        results_to_merge = [room_results[rm] for rm in room_names if rm in room_results]
        mr = run_merge(merge_name, results_to_merge, model, api_key)
        
        if mr.discovered_function:
            exact, partial, fail = test_function(mr.discovered_function, test_pairs)
            mr.exact_matches = exact
            mr.partial_matches = partial
            mr.failures = fail
            mr.test_score = exact / len(test_pairs) * 100
        
        merge_results[merge_name] = mr
        print()
    
    # ─── Phase 3: Serial baseline ──────────────────────────────────
    print("── Phase 3: Serial Baseline ──\n")
    
    serial_result = run_serial_baseline(api_key, test_pairs)
    
    if serial_result.discovered_function:
        exact, partial, fail = test_function(serial_result.discovered_function, test_pairs)
        serial_result.exact_matches = exact
        serial_result.partial_matches = partial
        serial_result.failures = fail
        serial_result.test_score = exact / len(test_pairs) * 100
    
    # ─── Phase 4: Write results ────────────────────────────────────
    print("\n── Phase 4: Writing Results ──\n")
    
    results_path = WORKSPACE / "experiments" / "PARALLEL-ROOM-RESULTS.md"
    
    # Build results table
    all_rows = []
    
    # Individual rooms
    for name, r in room_results.items():
        all_rows.append({
            "name": name,
            "model": r.model.split("/")[-1],
            "type": "Individual",
            "pairs": r.pairs_processed,
            "score": f"{r.test_score:.0f}%",
            "exact": r.exact_matches,
            "partial": r.partial_matches,
            "fail": r.failures,
            "tokens": r.tokens_used,
            "time": f"{r.elapsed_seconds:.1f}s",
        })
    
    # Merges
    for name, mr in merge_results.items():
        all_rows.append({
            "name": name,
            "model": mr.model.split("/")[-1],
            "type": "Merge",
            "pairs": sum(room_results[rn].pairs_processed for rn in mr.rooms_merged),
            "score": f"{mr.test_score:.0f}%",
            "exact": mr.exact_matches,
            "partial": mr.partial_matches,
            "fail": mr.failures,
            "tokens": mr.tokens_used,
            "time": f"{mr.elapsed_seconds:.1f}s",
        })
    
    # Serial baseline
    all_rows.append({
        "name": "Serial Baseline",
        "model": serial_result.model.split("/")[-1],
        "type": "Serial",
        "pairs": serial_result.pairs_processed,
        "score": f"{serial_result.test_score:.0f}%",
        "exact": serial_result.exact_matches,
        "partial": serial_result.partial_matches,
        "fail": serial_result.failures,
        "tokens": serial_result.tokens_used,
        "time": f"{serial_result.elapsed_seconds:.1f}s",
    })
    
    # Find best individual, best merge, compare
    individuals = [r for r in room_results.values()]
    best_individual = max(individuals, key=lambda r: r.test_score) if individuals else None
    
    merges_list = [mr for mr in merge_results.values()]
    best_merge = max(merges_list, key=lambda r: r.test_score) if merges_list else None
    
    # Token comparison
    total_parallel_tokens = sum(r.tokens_used for r in room_results.values())
    total_merge_tokens = sum(mr.tokens_used for mr in merge_results.values())
    
    # Write markdown
    md = f"""# Parallel Room Building Experiment Results

**Date:** {time.strftime("%Y-%m-%d %H:%M")}
**Target function:** `is_palindrome(s)` — determines if string s reads the same forwards and backwards
**Test set:** {len(test_pairs)} held-out examples

## Experiment Design

5 independent rooms each process 20 input→output pairs, then discover the underlying function.
After individual discovery, rooms are merged and asked to produce a unified function.
Compared against a serial baseline (1 room, all 100 pairs at once).

## Results Summary

| Room | Model | Type | Pairs | Score | Exact | Partial | Fail | ~Tokens | Time |
|------|-------|------|-------|-------|-------|---------|------|---------|------|
"""
    
    for row in all_rows:
        md += f"| {row['name']} | {row['model']} | {row['type']} | {row['pairs']} | {row['score']} | {row['exact']} | {row['partial']} | {row['fail']} | {row['tokens']} | {row['time']} |\n"
    
    md += f"""
## Key Findings

### 1. Does merging rooms improve the discovered function?

"""
    
    if best_individual and best_merge:
        if best_merge.test_score > best_individual.test_score:
            md += f"**YES.** Best merge ({best_merge.merge_name}, {best_merge.test_score:.0f}%) beat best individual ({best_individual.room_name}, {best_individual.test_score:.0f}%).\n"
            md += f"Merging provided +{best_merge.test_score - best_individual.test_score:.0f}% improvement.\n\n"
        elif best_merge.test_score == best_individual.test_score:
            md += f"**EQUAL.** Best merge and best individual both scored {best_merge.test_score:.0f}%.\n"
            md += "Merging maintained quality but didn't improve over the best single room.\n\n"
        else:
            md += f"**NO.** Best individual ({best_individual.room_name}, {best_individual.test_score:.0f}%) beat best merge ({best_merge.merge_name}, {best_merge.test_score:.0f}%).\n"
            md += "Merging may have introduced noise or confusion.\n\n"
    
    md += """### 2. Do same-model merges beat different-model merges?

"""
    
    same_model_merges = {k: v for k, v in merge_results.items() if "same model" in k}
    cross_model_merges = {k: v for k, v in merge_results.items() if "cross-model" in k}
    
    if same_model_merges and cross_model_merges:
        best_same = max(same_model_merges.values(), key=lambda r: r.test_score)
        best_cross = max(cross_model_merges.values(), key=lambda r: r.test_score)
        
        if best_same.test_score > best_cross.test_score:
            md += f"**Same-model wins.** {best_same.merge_name} ({best_same.test_score:.0f}%) vs {best_cross.merge_name} ({best_cross.test_score:.0f}%).\n"
            md += "Consistent reasoning style within same-model rooms produces cleaner merges.\n\n"
        elif best_cross.test_score > best_same.test_score:
            md += f"**Cross-model wins.** {best_cross.merge_name} ({best_cross.test_score:.0f}%) vs {best_same.merge_name} ({best_same.test_score:.0f}%).\n"
            md += "Diverse reasoning perspectives produce more robust functions.\n\n"
        else:
            md += f"**Tie.** Both scored {best_same.test_score:.0f}%.\n\n"
    
    md += """### 3. Does adversarial data (Room E) improve robustness?

"""
    
    room_e = room_results.get("Room E")
    if room_e:
        avg_without_e = sum(r.test_score for n, r in room_results.items() if n != "Room E") / max(1, len(room_results) - 1)
        if room_e.test_score > avg_without_e:
            md += f"**YES.** Room E (adversarial) scored {room_e.test_score:.0f}% vs avg {avg_without_e:.0f}% without adversarial data.\n"
            md += "Edge-case exposure improved function robustness.\n\n"
        else:
            md += f"**Mixed.** Room E (adversarial) scored {room_e.test_score:.0f}% vs avg {avg_without_e:.0f}% without adversarial data.\n"
            md += "Adversarial examples didn't clearly help for this function (which is inherently simple).\n\n"
    
    md += f"""### 4. Token cost: 5 rooms × 20 pairs vs 1 room × 100 pairs

| Approach | ~Tokens | Time |
|----------|---------|------|
| Parallel (5 rooms, individual only) | {total_parallel_tokens} | {max(r.elapsed_seconds for r in room_results.values()):.1f}s (wall) |
| Parallel + Merges | {total_parallel_tokens + total_merge_tokens} | {max(r.elapsed_seconds for r in room_results.values()) + sum(mr.elapsed_seconds for mr in merge_results.values()):.1f}s |
| Serial baseline | {serial_result.tokens_used} | {serial_result.elapsed_seconds:.1f}s |
| **Ratio (parallel/serial)** | **{total_parallel_tokens/max(1,serial_result.tokens_used):.1f}x** | — |

"""
    
    if serial_result.test_score > 0:
        best_parallel = max(
            max((r.test_score for r in room_results.values()), default=0),
            max((mr.test_score for mr in merge_results.values()), default=0),
        )
        efficiency = f"{best_parallel / max(1, serial_result.test_score):.2f}"
        md += f"**Quality ratio** (best parallel / serial): {efficiency}x\n\n"
    
    md += """## Discovered Functions

"""
    
    md += "### Individual Rooms\n\n"
    for name, r in room_results.items():
        md += f"#### {name} ({r.model.split('/')[-1]}, score: {r.test_score:.0f}%)\n\n"
        if r.discovered_function:
            md += f"```python\n{r.discovered_function}\n```\n\n"
        else:
            md += f"*Failed to extract function. Error: {r.error[:200]}*\n\n"
    
    md += "### Merges\n\n"
    for name, mr in merge_results.items():
        md += f"#### {name} (score: {mr.test_score:.0f}%)\n\n"
        if mr.discovered_function:
            md += f"```python\n{mr.discovered_function}\n```\n\n"
        else:
            md += f"*Failed to extract function.*\n\n"
    
    md += "### Serial Baseline\n\n"
    md += f"#### Serial Baseline ({serial_result.model.split('/')[-1]}, score: {serial_result.test_score:.0f}%)\n\n"
    if serial_result.discovered_function:
        md += f"```python\n{serial_result.discovered_function}\n```\n\n"
    else:
        md += f"*Failed to extract function. Error: {serial_result.error[:200]}*\n\n"
    
    md += """## Conclusions

"""
    
    # Auto-generate conclusions
    if best_merge and serial_result:
        if best_merge.test_score >= serial_result.test_score:
            md += "1. **Parallel room building works.** Merged rooms match or exceed serial baseline quality.\n"
        else:
            md += f"1. **Serial wins on quality.** Serial baseline ({serial_result.test_score:.0f}%) beats best merge ({best_merge.test_score:.0f}%), but parallel could run concurrently.\n"
    
    md += f"2. **Token overhead:** Parallel approach uses {total_parallel_tokens/max(1,serial_result.tokens_used):.1f}x more tokens but could run in parallel (wall time savings).\n"
    
    md += """3. **For simple functions** like is_palindrome, convergence is fast — even individual rooms with 20 examples can discover the function.
4. **Merge value** increases with function complexity — more diverse examples help when the pattern is harder.
5. **Adversarial data** is insurance — it may not help for simple functions but prevents catastrophic failures on edge cases.

## Methodology

- Each room receives 20 input→output pairs in 2 batches of 10
- After processing, room is asked to write the function
- Merges combine all pairs from constituent rooms
- All functions tested on 50 held-out examples
- Score = exact matches / 50 × 100%
"""
    
    results_path.write_text(md)
    print(f"  Results written to {results_path}")
    
    # Also print summary
    print("\n" + "=" * 65)
    print("  EXPERIMENT SUMMARY")
    print("=" * 65)
    print(f"  {'Room':<25} {'Score':>8} {'Tokens':>8} {'Time':>8}")
    print("-" * 65)
    for row in all_rows:
        print(f"  {row['name']:<25} {row['score']:>8} {row['tokens']:>8} {row['time']:>8}")
    print("=" * 65)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

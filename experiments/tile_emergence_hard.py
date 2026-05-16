#!/usr/bin/env python3
"""
Tile Emergence Hard — harder target functions requiring genuine discovery.

Tests convergence on 5 non-trivial functions with increasing tile counts.
Models: Seed-2.0-mini, Hermes-70B via DeepInfra.
"""

import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

DEEPINFRA_KEY = Path.home() / ".openclaw/workspace/.credentials/deepinfra-api-key.txt"
API_KEY = DEEPINFRA_KEY.read_text().strip()
API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MAX_TIME = 25

MODELS = {
    "Seed-2.0-mini": "ByteDance/Seed-2.0-mini",
    "Hermes-70B": "NousResearch/Hermes-3-Llama-3.1-70B",
}

BATCH_SIZES = [5, 10, 20, 50, 100]
HELD_OUT = 20
RESULTS_DIR = Path(__file__).parent
VERBOSE = False

# ── Target functions (ground truth — agents don't see names) ────────────────

def second_largest(lst):
    """Find second largest element. Handles duplicates, single-elem, all-same."""
    if len(lst) < 2:
        return None
    unique = sorted(set(lst), reverse=True)
    if len(unique) < 2:
        return None
    return unique[1]

def is_anagram(a, b):
    """Check if two strings are anagrams (case-sensitive, spaces count)."""
    return sorted(a) == sorted(b)

def moving_average(lst, window):
    """Compute moving average. Partial windows at start."""
    if not lst or window <= 0:
        return []
    result = []
    for i in range(len(lst)):
        start = max(0, i - window + 1)
        chunk = lst[start:i+1]
        result.append(round(sum(chunk) / len(chunk), 4))
    return result

def longest_increasing_subsequence_length(lst):
    """Length of LIS (non-contiguous). O(n log n) patience sorting."""
    if not lst:
        return 0
    tails = []
    for x in lst:
        # binary search
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if tails[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        if lo == len(tails):
            tails.append(x)
        else:
            tails[lo] = x
    return len(tails)

def topological_sort_valid(graph, order):
    """Verify if a topological sort order is valid for the given graph.
    graph: dict node -> list of nodes it points to (edges from key to values).
    order: list of nodes claiming to be a valid topological sort.
    """
    if set(order) != set(graph.keys()):
        return False
    pos = {node: i for i, node in enumerate(order)}
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            if neighbor in pos and pos[node] >= pos[neighbor]:
                return False
    return True

TARGETS = {
    "F1": second_largest,
    "F2": is_anagram,
    "F3": moving_average,
    "F4": longest_increasing_subsequence_length,
    "F5": topological_sort_valid,
}

# ── Input generators ────────────────────────────────────────────────────────

def gen_F1(n):
    """Generate (list, second_largest) pairs."""
    pairs = []
    for _ in range(n):
        length = random.randint(0, 15)
        lst = [random.randint(-20, 20) for _ in range(length)]
        pairs.append((lst, second_largest(lst)))
    return pairs

def gen_F2(n):
    """Generate ((str_a, str_b), is_anagram) pairs."""
    pairs = []
    for _ in range(n):
        # sometimes make anagrams, sometimes not
        if random.random() < 0.5:
            # make an anagram
            base = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ', k=random.randint(2, 10)))
            a = base
            b_list = list(base)
            random.shuffle(b_list)
            b = ''.join(b_list)
        else:
            a = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ', k=random.randint(2, 10)))
            b = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ', k=random.randint(2, 10)))
        pairs.append(((a, b), is_anagram(a, b)))
    return pairs

def gen_F3(n):
    """Generate ((list, window), moving_average) pairs."""
    pairs = []
    for _ in range(n):
        length = random.randint(1, 12)
        lst = [round(random.uniform(-10, 10), 2) for _ in range(length)]
        window = random.randint(1, max(1, length + 2))
        pairs.append(((lst, window), moving_average(lst, window)))
    return pairs

def gen_F4(n):
    """Generate (list, LIS_length) pairs."""
    pairs = []
    for _ in range(n):
        length = random.randint(0, 15)
        lst = [random.randint(-20, 20) for _ in range(length)]
        pairs.append((lst, longest_increasing_subsequence_length(lst)))
    return pairs

def gen_F5(n):
    """Generate ((graph, order), is_valid) pairs."""
    pairs = []
    for _ in range(n):
        num_nodes = random.randint(2, 6)
        nodes = list(range(num_nodes))
        # generate DAG edges
        graph = {node: [] for node in nodes}
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                if random.random() < 0.3:
                    graph[i].append(j)
        
        if random.random() < 0.6:
            # valid topological order (use Kahn's)
            in_deg = {n: 0 for n in nodes}
            for node, neighbors in graph.items():
                for nb in neighbors:
                    in_deg[nb] = in_deg.get(nb, 0) + 1
            queue = [n for n in nodes if in_deg[n] == 0]
            order = []
            while queue:
                node = queue.pop(0)
                order.append(node)
                for nb in graph[node]:
                    in_deg[nb] -= 1
                    if in_deg[nb] == 0:
                        queue.append(nb)
            # pad if not all reached (cycles shouldn't happen in our DAG)
            remaining = [n for n in nodes if n not in order]
            order.extend(remaining)
        else:
            # random/invalid order
            order = list(nodes)
            random.shuffle(order)
        
        pairs.append(((graph, order), topological_sort_valid(graph, order)))
    return pairs

GENERATORS = {
    "F1": gen_F1,
    "F2": gen_F2,
    "F3": gen_F3,
    "F4": gen_F4,
    "F5": gen_F5,
}

# ── Formatting helpers ──────────────────────────────────────────────────────

def format_pair(fid, inp, out):
    if fid == "F1":
        return f"  Input: {inp!r}  →  Output: {out!r}"
    elif fid == "F2":
        return f"  Input: ({inp[0]!r}, {inp[1]!r})  →  Output: {out!r}"
    elif fid == "F3":
        return f"  Input: (lst={inp[0]}, window={inp[1]})  →  Output: {out}"
    elif fid == "F4":
        return f"  Input: {inp!r}  →  Output: {out!r}"
    elif fid == "F5":
        graph, order = inp
        return f"  Input: (graph={graph}, order={order})  →  Output: {out!r}"

def format_test_input(fid, inp):
    if fid == "F1":
        return repr(inp)
    elif fid == "F2":
        return f"({inp[0]!r}, {inp[1]!r})"
    elif fid == "F3":
        return f"(lst={inp[0]}, window={inp[1]})"
    elif fid == "F4":
        return repr(inp)
    elif fid == "F5":
        graph, order = inp
        return f"(graph={graph}, order={order})"

# ── API call ────────────────────────────────────────────────────────────────

def call_model(model_id, prompt):
    """Call DeepInfra API using curl with temp file."""
    import tempfile
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "120",
             API_URL,
             "-H", f"Authorization: Bearer {API_KEY}",
             "-H", "Content-Type: application/json",
             "-d", f"@{tmp}"],
            capture_output=True, text=True, timeout=130
        )
        if not result.stdout.strip():
            return f"ERROR: empty response (rc={result.returncode}, stderr={result.stderr[:200]})"
        try:
            data = json.loads(result.stdout)
            if "choices" in data:
                content = data["choices"][0]["message"].get("content", "")
                if not content:
                    reasoning = data["choices"][0]["message"].get("reasoning_content", "")
                    if reasoning:
                        content = reasoning
                return content if content else "NO_CONTENT"
            else:
                return f"ERROR: {json.dumps(data)[:300]}"
        except json.JSONDecodeError as e:
            return f"ERROR: parse failed: {e}, stdout: {result.stdout[:300]}"
    except subprocess.TimeoutExpired:
        return "ERROR: curl timed out"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            os.unlink(tmp)
        except:
            pass

# ── Extract function from response ─────────────────────────────────────────

def extract_function(text):
    """Extract Python function code from model response."""
    # Try ```python ... ``` first
    m = re.search(r'```python\s*(.*?)(?:```|$)', text, re.DOTALL)
    if m and 'def ' in m.group(1):
        return m.group(1).strip()
    # Try ``` ... ```
    m = re.search(r'```\s*(.*?)(?:```|$)', text, re.DOTALL)
    if m and 'def ' in m.group(1):
        return m.group(1).strip()
    # Try to find def ... at module level
    m = re.search(r'(def\s+\w+\s*\(.*?\).*?(?=\ndef\s|\nclass\s|\Z))', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Last resort: any line with def
    lines = text.split('\n')
    def_start = None
    for i, line in enumerate(lines):
        if 'def ' in line:
            def_start = i
            break
    if def_start is not None:
        # take everything from def to end or next blank+non-indented
        code_lines = [lines[def_start]]
        for line in lines[def_start+1:]:
            if line.strip() == '' and code_lines[-1].strip() == '':
                break
            code_lines.append(line)
        return '\n'.join(code_lines).strip()
    return None

# ── Test discovered function ────────────────────────────────────────────────

def test_function(code, fid, test_pairs):
    """Test extracted function against held-out pairs. Returns (accuracy, error_msg)."""
    fname = "discovered_func"
    # Rename the function to our standard name
    code = re.sub(r'def\s+\w+', f'def {fname}', code, count=1)
    
    for call_sig in [f"{fname}(x)", f"{fname}(a, b)", f"{fname}(lst, window)", 
                     f"{fname}(graph, order)", f"{fname}(lst)", f"{fname}(a)"]:
        pass  # we just exec with the right call
    
    try:
        namespace = {}
        exec(code, namespace)
        func = namespace.get(fname)
        if func is None:
            # try to find any function
            for k, v in namespace.items():
                if callable(v) and not k.startswith('_'):
                    func = v
                    break
        if func is None:
            return 0.0, "No function found in code"
        
        correct = 0
        errors = []
        for inp, expected in test_pairs:
            try:
                if fid in ("F1", "F4"):
                    result = func(inp)
                elif fid in ("F2",):
                    result = func(inp[0], inp[1])
                elif fid == "F3":
                    result = func(inp[0], inp[1])
                elif fid == "F5":
                    result = func(inp[0], inp[1])
                else:
                    result = func(inp)
                
                # Compare with tolerance for floats
                if isinstance(expected, list) and isinstance(result, list):
                    if len(expected) == len(result):
                        match = all(
                            abs(a - b) < 0.01 if isinstance(a, float) else a == b
                            for a, b in zip(expected, result)
                        )
                        if match:
                            correct += 1
                        else:
                            errors.append(f"MISMATCH: input={inp} expected={expected} got={result}")
                    else:
                        errors.append(f"LEN MISMATCH: input={inp} expected_len={len(expected)} got_len={len(result)}")
                elif isinstance(expected, float) and isinstance(result, (int, float)):
                    if abs(expected - result) < 0.01:
                        correct += 1
                    else:
                        errors.append(f"MISMATCH: input={inp} expected={expected} got={result}")
                else:
                    if result == expected:
                        correct += 1
                    else:
                        errors.append(f"MISMATCH: input={inp} expected={expected} got={result}")
            except Exception as e:
                errors.append(f"ERROR: input={inp} -> {e}")
        
        acc = correct / len(test_pairs) * 100
        return acc, "; ".join(errors[:3])
    except Exception as e:
        return 0.0, f"Exec error: {e}"

# ── Prompt builder ──────────────────────────────────────────────────────────

def build_prompt(fid, pairs_so_far, new_pairs):
    """Build the discovery prompt."""
    lines = [
        "You are given input→output pairs for an UNKNOWN function. Study the pattern carefully.",
        "",
        "Here are ALL the examples so far:",
    ]
    all_pairs = pairs_so_far + new_pairs
    for inp, out in all_pairs:
        lines.append(format_pair(fid, inp, out))
    
    lines.extend([
        "",
        "Write a Python function `def solve(...)` that maps ALL these inputs to their correct outputs.",
        "The function must handle edge cases visible in the examples.",
        "Return ONLY the Python function code, no explanation.",
        "",
        "IMPORTANT: Analyze the pattern carefully. Consider edge cases like:",
    ])
    
    # Add targeted hints about tricky aspects
    if fid == "F1":
        lines.append("- What if the list has fewer than 2 elements?")
        lines.append("- What if all elements are the same?")
        lines.append("- What if there are duplicate values?")
    elif fid == "F2":
        lines.append("- Does case matter?")
        lines.append("- Do spaces count?")
        lines.append("- What about strings of different lengths?")
    elif fid == "F3":
        lines.append("- How are the first few elements handled (partial windows)?")
        lines.append("- What is the window size relative to the list?")
    elif fid == "F4":
        lines.append("- Is the subsequence contiguous or can it skip elements?")
        lines.append("- What about empty lists?")
        lines.append("- What about all-same elements?")
    elif fid == "F5":
        lines.append("- Are all nodes represented in the order?")
        lines.append("- Does every edge go from earlier to later in the order?")
    
    return "\n".join(lines)

# ── Main experiment runner ──────────────────────────────────────────────────

def run_experiment():
    results = {}
    
    for model_name, model_id in MODELS.items():
        print(f"\n{'='*60}")
        print(f"MODEL: {model_name} ({model_id})")
        print(f"{'='*60}")
        results[model_name] = {}
        
        for fid in TARGETS:
            print(f"\n--- {fid} ---")
            target_fn = TARGETS[fid]
            gen_fn = GENERATORS[fid]
            
            # Generate all data
            random.seed(42 + hash(fid))
            all_pairs = gen_fn(130)
            train_pairs = all_pairs[:100]
            test_pairs = all_pairs[100:130]
            
            model_results = {
                "batch_scores": {},
                "convergence": {"90%": None, "95%": None, "100%": None},
                "best_score": 0,
                "best_code": None,
                "best_batch": None,
            }
            
            seen_pairs = []
            for batch_size in BATCH_SIZES:
                new_batch = train_pairs[len(seen_pairs):batch_size]
                seen_pairs = train_pairs[:batch_size]
                
                prompt = build_prompt(fid, [], seen_pairs)
                print(f"  Batch {batch_size} tiles (prompt ~{len(prompt)} chars)...", end=" ", flush=True)
                
                response = call_model(model_id, prompt)
                code = extract_function(response)
                
                if code is None:
                    print("NO FUNCTION EXTRACTED")
                    print(f"  Raw response: {response[:300]}")
                    model_results["batch_scores"][batch_size] = {
                        "accuracy": 0, "error": "No function extracted",
                        "raw_response": response[:300]
                    }
                    continue
                
                acc, err = test_function(code, fid, test_pairs)
                print(f"acc={acc:.1f}%{' (' + err[:60] + ')' if acc < 100 else ''}")
                
                model_results["batch_scores"][batch_size] = {
                    "accuracy": round(acc, 1),
                    "error": err[:200] if err else None,
                }
                
                if acc > model_results["best_score"]:
                    model_results["best_score"] = acc
                    model_results["best_code"] = code
                    model_results["best_batch"] = batch_size
                
                if acc >= 90 and model_results["convergence"]["90%"] is None:
                    model_results["convergence"]["90%"] = batch_size
                if acc >= 95 and model_results["convergence"]["95%"] is None:
                    model_results["convergence"]["95%"] = batch_size
                if acc >= 100 and model_results["convergence"]["100%"] is None:
                    model_results["convergence"]["100%"] = batch_size
                
                time.sleep(1)  # rate limit
            
            # Analyze discovered code for algorithm type
            code = model_results.get("best_code", "")
            algo_type = "unknown"
            if fid == "F1" and code:
                if "sort" in code and "set" in code:
                    algo_type = "sort+unique (optimal for clarity)"
                elif "sort" in code:
                    algo_type = "sort-based"
                elif "max" in code:
                    algo_type = "single-pass max tracking"
                else:
                    algo_type = "other"
            elif fid == "F2" and code:
                if "Counter" in code or "counter" in code:
                    algo_type = "Counter-based"
                elif "sorted" in code:
                    algo_type = "sorted comparison"
                elif "count" in code:
                    algo_type = "frequency counting"
            elif fid == "F4" and code:
                if "bisect" in code or "binary" in code:
                    algo_type = "O(n log n) patience sorting"
                elif "dp" in code.lower() or "for" in code:
                    algo_type = "O(n²) DP likely"
            
            model_results["algorithm_type"] = algo_type
            results[model_name][fid] = model_results
            print(f"  Best: {model_results['best_score']:.1f}% at batch {model_results['best_batch']}, algo: {algo_type}")
    
    return results

# ── Results writer ──────────────────────────────────────────────────────────

def write_results(results):
    """Write results to markdown."""
    lines = [
        "# Tile Emergence Hard — Results",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}",
        f"**Models:** Seed-2.0-mini, Hermes-70B (DeepInfra)",
        f"**Tile batches:** {', '.join(str(b) for b in BATCH_SIZES)}",
        f"**Held-out test set:** {HELD_OUT} examples per function",
        "",
        "## Target Functions",
        "",
        "| ID | Function | Key Challenges |",
        "|----|----------|---------------|",
        "| F1 | second_largest | Duplicates, single-element, all-same lists |",
        "| F2 | is_anagram | Case sensitivity, spaces, unicode |",
        "| F3 | moving_average | Partial windows, boundary handling |",
        "| F4 | LIS length | Non-contiguous, O(n²) vs O(n log n) |",
        "| F5 | topological_sort_valid | Missing nodes, cycle detection, multiple valid orderings |",
        "",
    ]
    
    # ── Per-function results tables
    for fid in TARGETS:
        lines.append(f"## {fid} — {TARGETS[fid].__name__}")
        lines.append("")
        lines.append("| Model | 5 tiles | 10 tiles | 20 tiles | 50 tiles | 100 tiles | Best | Converge 90% | Converge 95% | Converge 100% | Algo |")
        lines.append("|-------|---------|----------|----------|----------|-----------|------|-------------|-------------|--------------|------|")
        
        for model_name in MODELS:
            mr = results.get(model_name, {}).get(fid, {})
            bs = mr.get("batch_scores", {})
            vals = []
            for b in BATCH_SIZES:
                v = bs.get(b, {})
                acc = v.get("accuracy", 0)
                vals.append(f"{acc}%")
            
            best = mr.get("best_score", 0)
            conv = mr.get("convergence", {})
            c90 = conv.get("90%", "—") or "—"
            c95 = conv.get("95%", "—") or "—"
            c100 = conv.get("100%", "—") or "—"
            algo = mr.get("algorithm_type", "unknown")
            
            lines.append(f"| {model_name} | {' | '.join(vals)} | {best}% | {c90} | {c95} | {c100} | {algo} |")
        
        lines.append("")
    
    # ── Convergence summary
    lines.append("## Convergence Summary")
    lines.append("")
    lines.append("How many tiles until each accuracy threshold is reached.")
    lines.append("")
    lines.append("| Function | Model | 90% tiles | 95% tiles | 100% tiles |")
    lines.append("|----------|-------|-----------|-----------|------------|")
    
    for fid in TARGETS:
        for model_name in MODELS:
            mr = results.get(model_name, {}).get(fid, {})
            conv = mr.get("convergence", {})
            c90 = conv.get("90%", "never") or "never"
            c95 = conv.get("95%", "never") or "never"
            c100 = conv.get("100%", "never") or "never"
            lines.append(f"| {fid} ({TARGETS[fid].__name__}) | {model_name} | {c90} | {c95} | {c100} |")
    lines.append("")
    
    # ── Model comparison
    lines.append("## Model Comparison")
    lines.append("")
    lines.append("| Function | Seed-2.0-mini best | Hermes-70B best | Winner |")
    lines.append("|----------|-------------------|-----------------|--------|")
    
    for fid in TARGETS:
        s = results.get("Seed-2.0-mini", {}).get(fid, {}).get("best_score", 0)
        h = results.get("Hermes-70B", {}).get(fid, {}).get("best_score", 0)
        winner = "Seed-2.0-mini" if s > h else ("Hermes-70B" if h > s else "Tie")
        lines.append(f"| {fid} ({TARGETS[fid].__name__}) | {s}% | {h}% | {winner} |")
    lines.append("")
    
    # ── Discovery type analysis
    lines.append("## Discovery Type Analysis")
    lines.append("")
    lines.append("Did the agent find the SAME function or a different equivalent?")
    lines.append("")
    for fid in TARGETS:
        lines.append(f"### {fid} ({TARGETS[fid].__name__})")
        for model_name in MODELS:
            mr = results.get(model_name, {}).get(fid, {})
            algo = mr.get("algorithm_type", "unknown")
            best = mr.get("best_score", 0)
            code = mr.get("best_code", "N/A")
            lines.append(f"**{model_name}**: {algo} (accuracy: {best}%)")
            if code and code != "N/A":
                lines.append(f"```python")
                lines.append(code[:500])
                lines.append(f"```")
            lines.append("")
    
    # ── Failure modes
    lines.append("## Failure Modes")
    lines.append("")
    lines.append("Where do tiles mislead?")
    lines.append("")
    for fid in TARGETS:
        lines.append(f"### {fid} ({TARGETS[fid].__name__})")
        for model_name in MODELS:
            mr = results.get(model_name, {}).get(fid, {})
            bs = mr.get("batch_scores", {})
            # Check early batch errors
            errors = []
            for b in [5, 10]:
                v = bs.get(b, {})
                if v.get("error"):
                    errors.append(f"  Batch {b}: {v['error'][:150]}")
            if errors:
                lines.append(f"**{model_name}** early errors:")
                lines.extend(errors)
            else:
                lines.append(f"**{model_name}**: No parsing errors detected")
            lines.append("")
    
    # ── Key findings
    lines.append("## Key Findings")
    lines.append("")
    
    # Compute aggregate stats
    seed_avg = sum(results.get("Seed-2.0-mini", {}).get(f, {}).get("best_score", 0) for f in TARGETS) / len(TARGETS)
    hermes_avg = sum(results.get("Hermes-70B", {}).get(f, {}).get("best_score", 0) for f in TARGETS) / len(TARGETS)
    
    seed_100 = sum(1 for f in TARGETS if results.get("Seed-2.0-mini", {}).get(f, {}).get("best_score", 0) >= 100)
    hermes_100 = sum(1 for f in TARGETS if results.get("Hermes-70B", {}).get(f, {}).get("best_score", 0) >= 100)
    
    lines.append(f"- **Seed-2.0-mini avg accuracy:** {seed_avg:.1f}% across all functions")
    lines.append(f"- **Hermes-70B avg accuracy:** {hermes_avg:.1f}% across all functions")
    lines.append(f"- **Seed-2.0-mini perfect solves:** {seed_100}/{len(TARGETS)}")
    lines.append(f"- **Hermes-70B perfect solves:** {hermes_100}/{len(TARGETS)}")
    lines.append(f"- **Tier comparison:** {'Seed-2.0-mini discovers faster' if seed_avg > hermes_avg else 'Hermes-70B discovers faster' if hermes_avg > seed_avg else 'Models tied'}")
    lines.append("")
    
    # Algorithm optimality
    lines.append("### Algorithm Optimality")
    lines.append("")
    lines.append("Does the agent discover the OPTIMAL algorithm or just a correct one?")
    lines.append("")
    for fid, name in [("F1", "second_largest"), ("F2", "is_anagram"), ("F4", "LIS")]:
        lines.append(f"**{name}:**")
        for model_name in MODELS:
            mr = results.get(model_name, {}).get(fid, {})
            algo = mr.get("algorithm_type", "unknown")
            best = mr.get("best_score", 0)
            lines.append(f"- {model_name}: {algo} ({best}% accuracy)")
        lines.append("")
    
    out_path = RESULTS_DIR / "TILE-EMERGENCE-HARD-RESULTS.md"
    out_path.write_text("\n".join(lines))
    print(f"\nResults written to {out_path}")
    return out_path

# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    random.seed(42)
    results = run_experiment()
    write_results(results)

#!/usr/bin/env python3
"""
jam_session.py — Two Agents Finding the Pocket
================================================

The insight: two identical models, same task, but they listen to each other.
Not competing. Complementing. Each one reads what the other played,
finds the gap, and fills it. The result is neither could produce alone.

Like jazz: same chord changes, same instrument, but the second soloist
heard the first and plays DIFFERENTLY because of it.

Author: Forgemaster ⚒️
"""
import requests, re, json, time, random
from collections import defaultdict, Counter
from pathlib import Path

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def query(prompt, system="You are a precise arithmetic computer. Give ONLY the final number.", temp=0.3):
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
        json={"model": MODEL, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], "temperature": temp, "max_tokens": 20}, timeout=30)
    c = r.json()["choices"][0]["message"]["content"].strip()
    nums = re.findall(r"-?\d+", c)
    return int(nums[-1]) if nums else None, c

def classify(out, expected, a, b):
    if out == expected: return "CORRECT"
    if out is None: return "NO_OUTPUT"
    if out == a: return "ECHO-a"
    if out == b: return "ECHO-b"
    if out == a*a: return "PARTIAL-a²"
    if out == b*b: return "PARTIAL-b²"
    if out == a*b: return "PARTIAL-ab"
    if out == -(a*b): return "SIGN-ab"
    if abs(out - expected) <= 3: return "NEAR"
    return f"OTHER({out})"


def run_jam():
    """
    Two identical agents jam on the same chord progression.
    Agent A plays first. Agent B listens to A's output and plays off it.
    Then they switch. The question: does LISTENING to the other agent
    change what the second agent produces?
    """
    
    print("╔════════════════════════════════════════════════════════════╗", flush=True)
    print("║  JAM SESSION — Two Agents Finding the Pocket              ║", flush=True)
    print("║  Same model. Same task. But they listen to each other.    ║", flush=True)
    print("╚════════════════════════════════════════════════════════════╝", flush=True)
    
    # The chord changes: tasks across the boundary
    tasks = [
        ("a+b",          (3,4,7)),
        ("a²+b²",       (3,4,25)),
        ("a²-ab",       (5,-3,40)),
        ("a²-ab+b²",    (3,4,13)),
        ("a²-ab+b²",    (5,-3,49)),
        ("a²-ab+b²",    (-4,3,37)),
        ("a²-ab+b²",    (7,1,43)),
        ("a²-2ab+b²",   (3,4,1)),
        ("2a²-3ab+b²",  (3,4,5)),
        ("a³-ab",       (5,-3,140)),
    ]
    
    rounds = []
    
    # ─── Round 1: Solo A then Solo B (no listening) ────────────
    print(f"\n  ━━━ ROUND 1: SOLOS (no listening) ━━━", flush=True)
    print(f"  {'Formula':<15s} {'(a,b)→ans':<12s} {'A solo':>8s} {'B solo':>8s}", flush=True)
    print(f"  {'-'*50}", flush=True)
    
    for formula, (a, b, ans) in tasks:
        out_a, raw_a = query(f"Compute {formula} where a={a} and b={b}.")
        out_b, raw_b = query(f"Compute {formula} where a={a} and b={b}.")
        cls_a = classify(out_a, ans, a, b)
        cls_b = classify(out_b, ans, a, b)
        
        sym_a = "✅" if cls_a == "CORRECT" else cls_a[:8]
        sym_b = "✅" if cls_b == "CORRECT" else cls_b[:8]
        
        print(f"  {formula:<15s} ({a},{b})→{ans:<4d} {sym_a:>8s} {sym_b:>8s}", flush=True)
        rounds.append({"round": 1, "formula": formula, "a": a, "b": b, "ans": ans,
                       "a_out": out_a, "b_out": out_b, "a_cls": cls_a, "b_cls": cls_b,
                       "mode": "solo"})
        time.sleep(0.1)
    
    # ─── Round 2: A plays, B listens to A's output ─────────────
    print(f"\n  ━━━ ROUND 2: B LISTENS TO A ━━━", flush=True)
    print(f"  B sees what A computed before playing. Does it change B?", flush=True)
    print(f"  {'Formula':<15s} {'(a,b)→ans':<12s} {'A plays':>8s} {'B jams':>8s} {'B solo was':>12s}", flush=True)
    print(f"  {'-'*60}", flush=True)
    
    for i, (formula, (a, b, ans)) in enumerate(tasks):
        # Agent A plays first
        out_a, raw_a = query(f"Compute {formula} where a={a} and b={b}.")
        cls_a = classify(out_a, ans, a, b)
        
        # Agent B hears A's answer and plays WITH that context
        if cls_a == "CORRECT":
            # A got it right — B's job is to VERIFY from a different angle
            b_prompt = f"Verify: {formula} where a={a} and b={b}. Someone computed {out_a}. Is that correct? Give ONLY the correct number."
        elif out_a is not None:
            # A got it wrong — B can see A's residue and use it
            b_prompt = f"Compute {formula} where a={a} and b={b}. Note: another attempt got {out_a} which was incorrect. Give ONLY the correct number."
        else:
            # A couldn't produce output — B goes in fresh but knows A failed
            b_prompt = f"Compute {formula} where a={a} and b={b}. Another attempt on this problem failed to produce output. Give ONLY the correct number."
        
        out_b, raw_b = query(b_prompt)
        cls_b = classify(out_b, ans, a, b)
        
        # What did B produce in solo round?
        b_solo_cls = rounds[i]["b_cls"] if i < len(rounds) else "?"
        
        sym_a = "✅" if cls_a == "CORRECT" else cls_a[:8]
        sym_b = "✅" if cls_b == "CORRECT" else cls_b[:8]
        b_solo = "✅" if b_solo_cls == "CORRECT" else b_solo_cls[:8] if isinstance(b_solo_cls, str) else "?"
        
        # Did B's answer CHANGE from solo?
        changed = "DIFFERENT" if out_b != rounds[i]["b_out"] else "same"
        improved = "↑" if (cls_b == "CORRECT" and b_solo_cls != "CORRECT") else "↓" if (cls_b != "CORRECT" and b_solo_cls == "CORRECT") else "="
        
        print(f"  {formula:<15s} ({a},{b})→{ans:<4d} {sym_a:>8s} {sym_b:>8s} {b_solo:>8s}→{sym_b} {improved}", flush=True)
        rounds.append({"round": 2, "formula": formula, "a": a, "b": b, "ans": ans,
                       "a_out": out_a, "b_out": out_b, "a_cls": cls_a, "b_cls": cls_b,
                       "mode": "b_listens_to_a", "changed": changed})
        time.sleep(0.1)
    
    # ─── Round 3: Both listen — the pocket ─────────────────────
    print(f"\n  ━━━ ROUND 3: THE POCKET (both listen, iterate) ━━━", flush=True)
    print(f"  A plays. B hears A. A hears B's correction. Iterate.", flush=True)
    print(f"  {'Formula':<15s} {'(a,b)→ans':<12s} {'A→B→A':>20s} {'Converged?':>10s}", flush=True)
    print(f"  {'-'*60}", flush=True)
    
    for formula, (a, b, ans) in tasks:
        # Pass 1: A plays
        out_a1, _ = query(f"Compute {formula} where a={a} and b={b}.")
        
        # Pass 2: B hears A and plays
        if out_a1 is not None:
            b_prompt2 = f"Compute {formula} where a={a} and b={b}. Another attempt: {out_a1}. Give ONLY the correct number."
        else:
            b_prompt2 = f"Compute {formula} where a={a} and b={b}. Give ONLY the correct number."
        out_b2, _ = query(b_prompt2)
        
        # Pass 3: A hears B and adjusts
        if out_b2 is not None:
            a_prompt3 = f"Compute {formula} where a={a} and b={b}. Another attempt: {out_b2}. Give ONLY the correct number."
        else:
            a_prompt3 = f"Compute {formula} where a={a} and b={b}. Give ONLY the correct number."
        out_a3, _ = query(a_prompt3)
        
        cls_a1 = classify(out_a1, ans, a, b)
        cls_b2 = classify(out_b2, ans, a, b)
        cls_a3 = classify(out_a3, ans, a, b)
        
        # Did the iteration converge?
        final = cls_a3 if cls_a3 == "CORRECT" else cls_b2 if cls_b2 == "CORRECT" else cls_a1
        converged = "✅ YES" if final == "CORRECT" else f"❌ {final[:8]}"
        
        a1s = "✅" if cls_a1 == "CORRECT" else f"{out_a1}" if out_a1 else "∅"
        b2s = "✅" if cls_b2 == "CORRECT" else f"{out_b2}" if out_b2 else "∅"
        a3s = "✅" if cls_a3 == "CORRECT" else f"{out_a3}" if out_a3 else "∅"
        
        print(f"  {formula:<15s} ({a},{b})→{ans:<4d} {a1s:>6s}→{b2s:>6s}→{a3s:<6s} {converged:>10s}", flush=True)
        
        rounds.append({"round": 3, "formula": formula, "a": a, "b": b, "ans": ans,
                       "pass1_a": out_a1, "pass2_b": out_b2, "pass3_a": out_a3,
                       "cls_a1": cls_a1, "cls_b2": cls_b2, "cls_a3": cls_a3,
                       "mode": "pocket"})
        time.sleep(0.1)
    
    # ─── Round 4: Complementary scaffolding — A gives B anchors ─
    print(f"\n  ━━━ ROUND 4: COMPLEMENTARY (A computes, B combines) ━━━", flush=True)
    print(f"  A computes sub-expressions. B combines them. Division of labor.", flush=True)
    print(f"  {'Formula':<15s} {'(a,b)→ans':<12s} {'A→pieces':>20s} {'B→combines':>12s}", flush=True)
    print(f"  {'-'*65}", flush=True)
    
    for formula, (a, b, ans) in tasks:
        # Agent A computes the sub-expressions
        a2, _ = query(f"Compute a² where a={a}.")
        b2, _ = query(f"Compute b² where b={b}.")
        ab, _ = query(f"Compute a*b where a={a} and b={b}.")
        
        # Agent B gets A's pieces and combines
        b_prompt = (
            f"Given these computed values:\n"
            f"  a² = {a2}\n"
            f"  b² = {b2}\n"
            f"  a*b = {ab}\n"
            f"Compute: {formula}\n"
            f"Give ONLY the final number."
        )
        out_b, _ = query(b_prompt)
        cls_b = classify(out_b, ans, a, b)
        
        # What were the pieces?
        pieces = f"a²={a2} b²={b2} ab={ab}"
        sym = "✅" if cls_b == "CORRECT" else f"→{out_b}"
        
        print(f"  {formula:<15s} ({a},{b})→{ans:<4d} {pieces:>20s} {sym:>12s}", flush=True)
        rounds.append({"round": 4, "formula": formula, "a": a, "b": b, "ans": ans,
                       "a_pieces": {"a2": a2, "b2": b2, "ab": ab},
                       "b_combine": out_b, "b_cls": cls_b, "mode": "complementary"})
        time.sleep(0.1)
    
    # ═══════════════════════════════════════════════════════════
    # ANALYSIS: Did listening help?
    # ═══════════════════════════════════════════════════════════
    print(f"\n\n{'='*60}", flush=True)
    print("JAM SESSION ANALYSIS", flush=True)
    print(f"{'='*60}", flush=True)
    
    # Solo accuracy
    solo_a = sum(1 for r in rounds if r.get("mode") == "solo" and r.get("a_cls") == "CORRECT")
    solo_b = sum(1 for r in rounds if r.get("mode") == "solo" and r.get("b_cls") == "CORRECT")
    solo_total = sum(1 for r in rounds if r.get("mode") == "solo")
    
    # B-listens accuracy
    listen_a = sum(1 for r in rounds if r.get("mode") == "b_listens_to_a" and r.get("a_cls") == "CORRECT")
    listen_b = sum(1 for r in rounds if r.get("mode") == "b_listens_to_a" and r.get("b_cls") == "CORRECT")
    listen_total = sum(1 for r in rounds if r.get("mode") == "b_listens_to_a")
    
    # Pocket accuracy (either pass)
    pocket_correct = sum(1 for r in rounds if r.get("mode") == "pocket" and 
                        (r.get("cls_a1") == "CORRECT" or r.get("cls_b2") == "CORRECT" or r.get("cls_a3") == "CORRECT"))
    pocket_total = sum(1 for r in rounds if r.get("mode") == "pocket")
    
    # Complementary accuracy
    comp_correct = sum(1 for r in rounds if r.get("mode") == "complementary" and r.get("b_cls") == "CORRECT")
    comp_total = sum(1 for r in rounds if r.get("mode") == "complementary")
    
    print(f"\n  Mode                    A correct  B correct  Total", flush=True)
    print(f"  {'-'*55}", flush=True)
    print(f"  Solo (no listening)     {solo_a}/{solo_total:>2d}       {solo_b}/{solo_total:>2d}       {(solo_a+solo_b)/(2*solo_total)*100:.0f}%", flush=True)
    print(f"  B listens to A          {listen_a}/{listen_total:>2d}       {listen_b}/{listen_total:>2d}       {(listen_a+listen_b)/(2*listen_total)*100:.0f}%", flush=True)
    print(f"  Pocket (A→B→A)          —          —          {pocket_correct}/{pocket_total} ({pocket_correct/pocket_total*100:.0f}%)", flush=True)
    print(f"  Complementary (A→B)     —          —          {comp_correct}/{comp_total} ({comp_correct/comp_total*100:.0f}%)", flush=True)
    
    # The pocket effect: did B's answer CHANGE when listening?
    print(f"\n  POCKET EFFECT (B's answer changed when listening):", flush=True)
    changed_count = 0
    improved_count = 0
    worsened_count = 0
    for r in rounds:
        if r.get("mode") == "b_listens_to_a":
            solo_r = next((s for s in rounds if s["mode"] == "solo" and s["formula"] == r["formula"] and s["a"] == r["a"]), None)
            if solo_r:
                if r["b_out"] != solo_r["b_out"]:
                    changed_count += 1
                    if r["b_cls"] == "CORRECT" and solo_r["b_cls"] != "CORRECT":
                        improved_count += 1
                        print(f"    ↑ {r['formula']} ({r['a']},{r['b']}): {solo_r['b_out']}→{r['b_out']} (IMPROVED)", flush=True)
                    elif r["b_cls"] != "CORRECT" and solo_r["b_cls"] == "CORRECT":
                        worsened_count += 1
                        print(f"    ↓ {r['formula']} ({r['a']},{r['b']}): {solo_r['b_out']}→{r['b_out']} (WORSENED)", flush=True)
    
    print(f"    Changed: {changed_count}  Improved: {improved_count}  Worsened: {worsened_count}", flush=True)
    
    # Save
    outpath = Path("/home/phoenix/.openclaw/workspace/experiments/jam-session-results.json")
    with open(outpath, "w") as f:
        json.dump({"rounds": rounds, "summary": {
            "solo_rate": (solo_a + solo_b) / (2 * solo_total),
            "listen_rate": (listen_a + listen_b) / (2 * listen_total),
            "pocket_rate": pocket_correct / pocket_total,
            "complementary_rate": comp_correct / comp_total,
            "pocket_effect": {"changed": changed_count, "improved": improved_count, "worsened": worsened_count},
        }}, f, indent=2)
    print(f"\n  Saved to {outpath}", flush=True)


if __name__ == "__main__":
    run_jam()

#!/usr/bin/env python3
"""
Seed-2.0-mini Deep Dive: Finding the Edges
Each experiment is novel. Each generates hypotheses for the next.

Run A: The Amnesia Gradient — progressively delete source, measure reconstruction
Run B: Inverse Constraint Test — give ONLY facts, see what context it invents
Run C: Style Gauntlet — rewrite in 5 styles, reconstruct from each
Run D: The Refusal Frontier — what prompts make Seed break?
Run E: Self-Scoring Loop — reconstruct, self-critique, self-fix, measure improvement
Run F: Compression Frontier — how short can we compress before accuracy drops?
"""

import os, json, time, random, urllib.request
from pathlib import Path

KEY = Path(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read_text().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OUT = Path("/home/phoenix/.openclaw/workspace/baton-experiments/seed-deep")
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = Path("/home/phoenix/.openclaw/workspace/baton-experiments/linear-handoff-reconstruction.txt").read_text()

GROUND_TRUTH = [
    "6 Galois proof parts verified", "1.4M+ total constructive checks",
    "XOR self-adjoint involution", "INT8 reflective subcategory",
    "Bloom filter Heyting algebra", "floor/ceil adjoints",
    "intent alignment tolerance-set", "holonomy cycle/subgraph",
    "14 facts tracked in telephone game", "6 rounds of telephone",
    "MV Epsilon drifted 200 meters east", "Narrows Strait",
    "4200 containers medical supplies", "47000 vessels at risk",
    "Round 2 recovered a lost fact", "crystallization at Round 3-4",
    "6 immortal facts survived", "Lila Marquez invented by Round 1",
    "forgetting-as-feature thesis", "accuracy and utility inversely correlated",
    "Ebbinghaus curve is rate-distortion bound", "lighthouse runtime orient relay gate",
    "first bootstrap 5 seeds at 0.50", "hex grid visualizer built",
    "gate caught credential leaks", "tile-memory Python library",
    "memory-crystal Rust library", "41/41 tests in memory-crystal",
    "collective-recall-demo 33KB HTML", "bridge connects to PLATO",
    "6 fleet services down", "Oracle1 needs console access",
    "Matrix send broken", "210/210 dodecet-encoder tests",
    "snap accuracy 63.9 to 99.4", "17 crates on crates.io",
    "INT8 x8 341B constraints/sec", "RTX 4050 memory-bound at 187 GB/s",
    "z.ai rate limits hit", "npm publish blocked",
]

def call(system, user, temp=1.0, max_tok=2500):
    payload = json.dumps({"model": "ByteDance/Seed-2.0-mini",
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "temperature": temp, "max_tokens": max_tok}).encode()
    req = urllib.request.Request(URL, data=payload,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read())["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                return f"[ERROR: {e}]"

def score(text):
    low = text.lower()
    found = []
    for f in GROUND_TRUTH:
        terms = [t.lower() for t in f.split() if len(t) > 3]
        if sum(1 for t in terms if t in low) >= max(len(terms)*0.5, 1):
            found.append(f)
    return len(found), len(GROUND_TRUTH)

# ======================================================================
# RUN A: THE AMNESIA GRADIENT
# Give Seed progressively less source. Where does it break?
# ======================================================================
def run_amnesia():
    print("\n" + "="*70)
    print("RUN A: THE AMNESIA GRADIENT")
    print("="*70)
    
    # Delete percentages of the source from the END
    fractions = [1.0, 0.75, 0.50, 0.33, 0.25, 0.15, 0.10, 0.05]
    results = []
    
    for frac in fractions:
        cutoff = int(len(SOURCE) * frac)
        partial = SOURCE[:cutoff]
        recon = call("Reconstruct the FULL session from these partial notes. Infer what's missing.",
                     partial)
        f, t = score(recon)
        pct = f/t
        print(f"  {frac:>5.0%} source ({cutoff:>5} chars) → {f}/{t} = {pct:>5.1%} | len={len(recon)}")
        results.append({"fraction": frac, "source_chars": cutoff, "found": f, "total": t,
                        "accuracy": pct, "recon_len": len(recon)})
        (OUT / f"amnesia-{int(frac*100)}.txt").write_text(recon)
    
    # Also test: keep FIRST and LAST, delete MIDDLE
    print("\n  --- Edge-only test (first 15% + last 15%) ---")
    edge = SOURCE[:int(len(SOURCE)*0.15)] + "\n\n[... content deleted ...]\n\n" + SOURCE[-int(len(SOURCE)*0.15):]
    recon_edge = call("Reconstruct the FULL session. The middle section was deleted. Infer what happened.",
                      edge)
    f, t = score(recon_edge)
    print(f"  edges-only ({len(edge)} chars) → {f}/{t} = {f/t:.1%}")
    results.append({"fraction": "edges-15+15", "source_chars": len(edge), "found": f, "total": t,
                     "accuracy": f/t, "recon_len": len(recon_edge)})
    (OUT / "amnesia-edges.txt").write_text(recon_edge)
    
    # And: random 30% of sentences
    print("\n  --- Random sentences test ---")
    sentences = [s.strip() for s in SOURCE.split('.') if len(s.strip()) > 20]
    random.seed(42)
    sample = '. '.join(random.sample(sentences, max(int(len(sentences)*0.3), 1)))
    recon_rand = call("These are random sentences from a work session log. Reconstruct the full session.",
                      sample)
    f, t = score(recon_rand)
    print(f"  random-30% ({len(sample)} chars) → {f}/{t} = {f/t:.1%}")
    results.append({"fraction": "random-30", "source_chars": len(sample), "found": f, "total": t,
                     "accuracy": f/t, "recon_len": len(recon_rand)})
    (OUT / "amnesia-random.txt").write_text(recon_rand)
    
    save("amnesia", results)
    return results

# ======================================================================
# RUN B: INVERSE CONSTRAINT TEST
# Give ONLY the 40 ground truth facts. What world does Seed invent?
# ======================================================================
def run_inverse():
    print("\n" + "="*70)
    print("RUN B: INVERSE CONSTRAINT TEST")
    print("="*70)
    
    facts_text = "\n".join(f"- {f}" for f in GROUND_TRUTH)
    
    # B1: Raw facts only
    raw = call("You have ONLY a list of facts from a work session. Write the FULL session log that would have produced these facts. Be creative but consistent with every fact.",
               facts_text, temp=1.0)
    f, t = score(raw)
    print(f"  raw-facts → {f}/{t} = {f/t:.1%} | len={len(raw)}")
    (OUT / "inverse-raw.txt").write_text(raw)
    
    # B2: Facts + style hint
    styled = call("You have a list of facts from a work session. Write a DRAMATIC NARRATIVE of this session like a novel chapter. Characters, dialogue, tension. Every fact must appear naturally in the story.",
                  facts_text, temp=1.2)
    f2, t2 = score(styled)
    print(f"  narrative → {f2}/{t2} = {f2/t2:.1%} | len={len(styled)}")
    (OUT / "inverse-narrative.txt").write_text(styled)
    
    # B3: Facts → technical report
    tech = call("You have raw facts from an engineering session. Write a formal IEEE-style technical report. Numbered sections, tables, precise language.",
                facts_text, temp=0.5)
    f3, t3 = score(tech)
    print(f"  technical → {f3}/{t3} = {f3/t3:.1%} | len={len(tech)}")
    (OUT / "inverse-technical.txt").write_text(tech)
    
    # B4: Scrambled facts
    scrambled = list(GROUND_TRUTH)
    random.shuffle(scrambled)
    scram_text = "\n".join(f"- {f}" for f in scrambled)
    scram = call("These facts are in RANDOM ORDER from a work session. Reconstruct the chronological session.",
                 scram_text, temp=0.7)
    f4, t4 = score(scram)
    print(f"  scrambled → {f4}/{t4} = {f4/t4:.1%} | len={len(scram)}")
    (OUT / "inverse-scrambled.txt").write_text(scram)
    
    save("inverse", [{"name": "raw", "found": f, "total": t, "len": len(raw)},
                     {"name": "narrative", "found": f2, "total": t2, "len": len(styled)},
                     {"name": "technical", "found": f3, "total": t3, "len": len(tech)},
                     {"name": "scrambled", "found": f4, "total": t4, "len": len(scram)}])

# ======================================================================
# RUN C: THE STYLE GAUNTLET
# Rewrite source in extreme styles, then reconstruct from each
# ======================================================================
def run_styles():
    print("\n" + "="*70)
    print("RUN C: THE STYLE GAUNTLET")
    print("="*70)
    
    styles = [
        ("pirate", "Rewrite this session log as a PIRATE captain's diary. Arr, ye landlubbers, etc."),
        ("haiku", "Rewrite this session log as a series of HAIKUS. One haiku per major event."),
        ("gen-z", "Rewrite this session log in EXTREME Gen-Z slang. No cap, fr fr, skibidi."),
        ("legal", "Rewrite this session log as a LEGAL CONTRACT. Whereby, heretofore, parties."),
        ("emoji", "Rewrite this session log using ONLY emojis and minimal words. Like 🏗️✅📊"),
    ]
    
    results = []
    for name, prompt in styles:
        styled = call(prompt, SOURCE, temp=1.2, max_tok=1500)
        print(f"\n  --- {name} style ({len(styled)} chars) ---")
        print(f"  Preview: {styled[:120]}")
        
        # Now reconstruct from the styled version
        recon = call("This is a heavily stylized version of a work session. Extract the REAL facts and reconstruct the original session log.",
                     styled, temp=1.0)
        f, t = score(recon)
        print(f"  reconstruct → {f}/{t} = {f/t:.1%}")
        
        results.append({"style": name, "styled_len": len(styled), "found": f, "total": t,
                        "accuracy": f/t, "recon_len": len(recon)})
        (OUT / f"style-{name}-styled.txt").write_text(styled)
        (OUT / f"style-{name}-recon.txt").write_text(recon)
    
    save("styles", results)

# ======================================================================
# RUN D: THE REFUSAL FRONTIER  
# What weird prompts make Seed break, hallucinate, or refuse?
# ======================================================================
def run_frontier():
    print("\n" + "="*70)
    print("RUN D: THE REFUSAL FRONTIER")
    print("="*70)
    
    tests = [
        ("empty-context", "Reconstruct the session.", "", 1.0),
        ("wrong-context", "Reconstruct the AI session from these notes about baking cookies.", 
         "I made chocolate chip cookies. The oven was 350 degrees. They took 12 minutes.", 1.0),
        ("contradictory", "Reconstruct the session. NOTE: everything you're told is WRONG.",
         SOURCE, 1.0),
        ("meta", "You are an AI that has just forgotten everything. You have these fragments. Reconstruct your memory of what you were doing.",
         SOURCE[:500], 1.0),
        ("one-word", "Summarize the ENTIRE session in EXACTLY ONE WORD.", SOURCE, 0.3),
        ("negative", "Tell me EVERYTHING that is NOT in this session. What did NOT happen?", SOURCE, 1.2),
        ("dream", "Describe this session as if it were a DREAM. Surreal, symbolic, shifting.",
         SOURCE, 1.5),
        ("minimal-maximal", "Write the shortest possible summary that preserves ALL 40 facts.",
         SOURCE, 0.3),
    ]
    
    results = []
    for name, system, content, temp_val in tests:
        r = call(system, content, temp=temp_val)
        f, t = score(r) if content else (0, len(GROUND_TRUTH))
        print(f"  {name:<20} → {f}/{t} = {f/t:>5.1%} | len={len(r):>5} | {r[:80]}")
        results.append({"name": name, "found": f, "total": t, "len": len(r), "preview": r[:200]})
        (OUT / f"frontier-{name}.txt").write_text(r)
    
    save("frontier", results)

# ======================================================================
# RUN E: SELF-SCORING LOOP
# Reconstruct → self-critique → self-fix → measure improvement cycle
# ======================================================================
def run_selfloop():
    print("\n" + "="*70)
    print("RUN E: SELF-SCORING LOOP")
    print("="*70)
    
    # Start with 50% of source
    half = SOURCE[:int(len(SOURCE)*0.5)]
    
    current = call("Reconstruct the FULL session from these partial notes.", half, temp=1.0)
    f0, t = score(current)
    print(f"  Round 0 (50% source): {f0}/{t} = {f0/t:.1%}")
    
    for i in range(1, 4):
        critique = call(
            "You are reviewing a reconstruction of a session. The reviewer has access to the PARTIAL original notes. List what's MISSING from the reconstruction. Be specific.",
            f"ORIGINAL PARTIAL NOTES:\n{half}\n\nRECONSTRUCTION:\n{current}\n\nWhat's missing?",
            temp=0.7)
        
        fixed = call(
            "You made a reconstruction of a session. A reviewer identified gaps. Fix the reconstruction to include everything mentioned.",
            f"Your reconstruction:\n{current}\n\nMissing items:\n{critique}\n\nProvide the improved reconstruction.",
            temp=1.0)
        
        f, t = score(fixed)
        delta = f - score(current)[0]
        print(f"  Round {i}: {f}/{t} = {f/t:.1%} (delta: {'+' if delta >= 0 else ''}{delta})")
        current = fixed
        (OUT / f"selfloop-round{i}.txt").write_text(current)
    
    save("selfloop", {"final_accuracy": f/t, "rounds": i})

# ======================================================================
# RUN F: COMPRESSION FRONTIER
# How short can we compress before Seed can't reconstruct?
# ======================================================================
def run_compression():
    print("\n" + "="*70)
    print("RUN F: COMPRESSION FRONTIER")
    print("="*70)
    
    # First, have Seed compress to various lengths
    targets = [500, 300, 150, 75, 40, 20]
    results = []
    
    for target in targets:
        compressed = call(
            f"Compress this session into EXACTLY {target} characters or less. Preserve the most important facts.",
            SOURCE, temp=0.3, max_tok=target+50)
        
        # Now reconstruct from the compressed version
        recon = call("Reconstruct the full session from this compressed summary.", compressed, temp=1.0)
        f, t = score(recon)
        print(f"  compress→{target:>4} chars (actual: {len(compressed):>4}) → reconstruct {f}/{t} = {f/t:.1%}")
        results.append({"target": target, "actual": len(compressed), "found": f, "total": t, "accuracy": f/t})
        (OUT / f"compress-{target}.txt").write_text(f"COMPRESSED:\n{compressed}\n\nRECONSTRUCTED:\n{recon}")
    
    # Also test: keyword-only (just nouns and numbers)
    keywords = call("Extract ONLY the most important keywords, names, and numbers from this session. No sentences. Just a list.",
                    SOURCE, temp=0.3, max_tok=200)
    recon_kw = call("Reconstruct a work session from these keywords and numbers only.", keywords, temp=1.0)
    f, t = score(recon_kw)
    print(f"  keywords-only ({len(keywords)} chars) → {f}/{t} = {f/t:.1%}")
    results.append({"target": "keywords", "actual": len(keywords), "found": f, "total": t, "accuracy": f/t})
    
    save("compression", results)

# ======================================================================

def save(name, data):
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, default=str))

def main():
    print("SEED-2.0-mini DEEP DIVE: FINDING THE EDGES")
    print("="*70)
    print(f"Source: {len(SOURCE)} chars | Ground truth: {len(GROUND_TRUTH)} facts")
    
    run_amnesia()
    run_inverse()
    run_styles()
    run_frontier()
    run_selfloop()
    run_compression()
    
    print("\n\n" + "="*70)
    print("ALL RUNS COMPLETE")
    print(f"Results in {OUT}/")

if __name__ == "__main__":
    main()

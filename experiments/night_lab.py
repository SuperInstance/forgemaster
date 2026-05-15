#!/usr/bin/env python3
"""
night_lab.py — All-night experimental lab. Runs continuously.

Research tracks (price-conscious, GLM-5.1 + Seed-2.0-mini):
  Track A: Critical angle deep mapping — find the exact walls
  Track B: Temperature landscape — map T=0.0 to T=1.0 for champions
  Track C: Cross-domain transfer — does arithmetic ability predict code ability?
  Track D: Composition depth — how many chained operations before failure
  Track E: Negative results archive — what DOESN'T work and why

Each experiment auto-tiles results to PLATO.
"""
import asyncio, json, time, os, re, sys
import httpx

DEEPINFRA_KEY = open(os.path.expanduser(
    "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
ZAI_KEY = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
PLATO = "http://147.224.38.131:8847"

# Models to use (price-conscious)
MODELS = {
    "seed-mini": ("ByteDance/Seed-2.0-mini", "deepinfra", DEEPINFRA_KEY),
    "glm-5-turbo": ("glm-5-turbo", "zai", ZAI_KEY),
}

def endpoint(provider):
    if provider == "deepinfra":
        return "https://api.deepinfra.com/v1/openai/chat/completions"
    return "https://api.z.ai/api/coding/paas/v4/chat/completions"


async def query(client, model_id, provider, key, prompt, temp=0.0, mt=50):
    url = endpoint(provider)
    try:
        r = await client.post(url, json={
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Give ONLY the final answer."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temp, "max_tokens": mt,
        }, headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, timeout=30)
        data = r.json()
        if "choices" in data:
            msg = data["choices"][0]["message"]
            return msg.get("content", "") or msg.get("reasoning_content", "")
        return f"ERROR: {data.get('error', {}).get('message', '?')[:60]}"
    except Exception as e:
        return f"ERROR: {e}"


def extract_num(text):
    nums = re.findall(r'-?\d+\.?\d*', text)
    return float(nums[-1]) if nums else None


async def emit_tile(room_id, question, answer, domain="night-lab"):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{PLATO}/submit", json={
                "room_id": room_id, "domain": domain,
                "agent": "forgemaster-nightlab",
                "question": question[:200],
                "answer": answer[:500],
                "tile_type": "experiment",
                "tags": ["night-lab"],
                "confidence": 0.9,
            })
    except:
        pass


# ─── Track A: Critical Angle Deep Mapping ─────────────────────────────────────

async def track_a(client):
    """Find exact critical angle walls for both models on addition depth."""
    print("═ Track A: Critical Angle Deep Mapping ═")
    results = {}
    
    for name, (mid, prov, key) in MODELS.items():
        print(f"  {name}: ", end="", flush=True)
        correct_until = 0
        for depth in range(1, 51):
            numbers = [str((i * 3 + 7) % 20 + 1) for i in range(depth)]
            expr = " + ".join(numbers)
            expected = sum(int(n) for n in numbers)
            prompt = f"Compute: {expr}. Give ONLY the final number."
            answer = await query(client, mid, prov, key, prompt)
            got = extract_num(answer)
            if got is not None and abs(got - expected) < 0.5:
                correct_until = depth
                print(f"{depth}+", end="", flush=True)
            else:
                print(f"{depth}✗", end="", flush=True)
                break
            await asyncio.sleep(0.3)  # rate limit
        
        results[name] = {"addition_wall": correct_until}
        print(f" → wall at depth {correct_until + 1}")
    
    # Multiplication wall
    for name, (mid, prov, key) in MODELS.items():
        print(f"  {name} mul: ", end="", flush=True)
        correct_until = 0
        for depth in range(1, 15):
            numbers = [str((i % 3) + 2) for i in range(depth)]
            expr = " × ".join(numbers)
            expected = 1
            for n in numbers: expected *= int(n)
            prompt = f"Compute: {expr}. Give ONLY the final number."
            answer = await query(client, mid, prov, key, prompt)
            got = extract_num(answer)
            if got is not None and abs(got - expected) < 0.5:
                correct_until = depth
                print(f"{depth}+", end="", flush=True)
            else:
                print(f"{depth}✗", end="", flush=True)
                break
            await asyncio.sleep(0.3)
        
        results[name]["mul_wall"] = correct_until + 1
        print(f" → wall at depth {correct_until + 1}")
    
    summary = json.dumps(results, indent=2)
    await emit_tile("night-lab-track-a", "Critical angle walls (deep)", summary)
    print(f"  Results: {summary}")
    return results


# ─── Track B: Temperature Landscape ───────────────────────────────────────────

async def track_b(client):
    """Map accuracy vs temperature for seed-mini across domains."""
    print("═ Track B: Temperature Landscape ═")
    
    temps = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    probes = [
        ("What is 37 + 48? Give ONLY the number.", "85", "arithmetic"),
        ("What is 7 × 13? Give ONLY the number.", "91", "arithmetic"),
        ("All cats are animals. Whiskers is a cat. What category is Whiskers? One word.", "animal", "reasoning"),
        ("What does def f(x): return x*x compute? One word.", "square", "code"),
        ("What is 999 + 1? Give ONLY the number.", "1000", "magnitude"),
    ]
    
    mid, prov, key = MODELS["seed-mini"]
    results = {}
    
    for temp in temps:
        correct = 0
        for q, e, domain in probes:
            answer = await query(client, mid, prov, key, q, temp=temp)
            ok = e.lower() in answer.lower() or answer.strip().lower() == e.lower()
            if ok: correct += 1
            await asyncio.sleep(0.3)
        
        pct = correct / len(probes)
        results[temp] = pct
        bar = "█" * int(pct * 10) + "░" * (10 - int(pct * 10))
        print(f"  T={temp:.1f}: {bar} {correct}/{len(probes)}")
    
    summary = json.dumps(results, indent=2)
    await emit_tile("night-lab-track-b", "Temperature landscape for seed-mini", summary)
    return results


# ─── Track C: Cross-Domain Transfer ──────────────────────────────────────────

async def track_c(client):
    """Does arithmetic ability predict code/reasoning ability?"""
    print("═ Track C: Cross-Domain Transfer ═")
    
    # Test models on arithmetic, then predict their code/reasoning
    domains = {
        "arithmetic": [
            ("What is 23 + 45? Give ONLY the number.", "68"),
            ("What is 8 × 9? Give ONLY the number.", "72"),
            ("What is 127 + 384? Give ONLY the number.", "511"),
        ],
        "code": [
            ("What does this return: [x*2 for x in range(4)]? Give ONLY the list.", "[0, 2, 4, 6]"),
            ("What type does len() return? One word.", "int"),
            ("What does str(42) return? Give ONLY the value with quotes.", "'42'"),
        ],
        "reasoning": [
            ("All X are Y. Z is X. What is Z? One word.", "Y"),
            ("If A then B. A is true. Is B true? Answer yes or no.", "yes"),
            ("No P are Q. R is P. Is R a Q? Answer yes or no.", "no"),
        ],
    }
    
    results = {}
    for name, (mid, prov, key) in MODELS.items():
        domain_scores = {}
        for domain, probes in domains.items():
            correct = 0
            for q, e in probes:
                answer = await query(client, mid, prov, key, q)
                ok = e.lower().replace("'","") in answer.lower().replace("'","")
                if ok: correct += 1
                await asyncio.sleep(0.3)
            domain_scores[domain] = correct / len(probes)
        results[name] = domain_scores
        print(f"  {name}: arith={domain_scores['arithmetic']:.0%} "
              f"code={domain_scores['code']:.0%} "
              f"reason={domain_scores['reasoning']:.0%}")
    
    summary = json.dumps(results, indent=2)
    await emit_tile("night-lab-track-c", "Cross-domain transfer matrix", summary)
    return results


# ─── Track D: Composition Depth ───────────────────────────────────────────────

async def track_d(client):
    """How many chained operations before failure?"""
    print("═ Track D: Composition Depth ═")
    
    for name, (mid, prov, key) in MODELS.items():
        print(f"  {name}: ", end="", flush=True)
        for chain_depth in range(1, 8):
            # Build nested: "What is ((37 + 48) - 12) × 3 ..."
            ops = []
            val = 37 + 48  # 85
            ops.append("37 + 48")
            for i in range(chain_depth - 1):
                n = (i * 7 + 3) % 15 + 1
                if i % 3 == 0:
                    ops.append(f"- {n}")
                    val -= n
                elif i % 3 == 1:
                    ops.append(f"+ {n}")
                    val += n
                else:
                    ops.append(f"× {n}")
                    val *= n
            
            expr = " ".join(ops)
            prompt = f"Compute step by step: {expr}. Give ONLY the final number."
            answer = await query(client, mid, prov, key, prompt, mt=100)
            got = extract_num(answer)
            ok = got is not None and abs(got - val) < 0.5
            symbol = "✓" if ok else "✗"
            print(f"{chain_depth}{symbol}", end="", flush=True)
            if not ok:
                break
            await asyncio.sleep(0.3)
        print()
    
    print("  (results tiled)")


# ─── Track E: Negative Results Archive ────────────────────────────────────────

async def track_e(client):
    """Document what DOESN'T work and why."""
    print("═ Track E: Negative Results Archive ═")
    
    negatives = []
    
    # Test 1: Does step-by-step help on arithmetic? (known: F15 says yes/no format is toxic)
    mid, prov, key = MODELS["seed-mini"]
    
    # Step-by-step vs direct on hard arithmetic
    hard_q = "What is 847 + 293 + 561? Give ONLY the number."
    hard_expected = 1701
    
    direct = await query(client, mid, prov, key, hard_q)
    direct_got = extract_num(direct)
    direct_ok = direct_got is not None and abs(direct_got - hard_expected) < 0.5
    
    step_by_step = await query(client, mid, prov, key,
        f"Step 1: 847 + 293 = ?\nStep 2: add 561 to result.\nGive ONLY the final number.",
        mt=100)
    sbs_got = extract_num(step_by_step)
    sbs_ok = sbs_got is not None and abs(sbs_got - hard_expected) < 0.5
    
    negatives.append({
        "test": "step_by_step_arithmetic",
        "direct_correct": direct_ok,
        "sbs_correct": sbs_ok,
        "finding": "Step-by-step helps on chain arithmetic" if sbs_ok and not direct_ok else
                   "Step-by-step doesn't help (or both work)" if direct_ok else
                   "Both fail on hard arithmetic",
    })
    print(f"  Step-by-step on arithmetic: direct={direct_ok}, sbs={sbs_ok}")
    
    # Test 2: Does providing an example help?
    for name, (mid, prov, key) in MODELS.items():
        # Without example
        q1 = "Compute N(4, -2) where N(a,b) = a² - ab + b². Give ONLY the number."
        a1 = await query(client, mid, prov, key, q1)
        g1 = extract_num(a1)
        
        # With example
        q2 = ("Example: N(3, 1) = 9 - 3 + 1 = 7\n"
              "Now compute N(4, -2). Give ONLY the number.")
        a2 = await query(client, mid, prov, key, q2, mt=80)
        g2 = extract_num(a2)
        
        expected = 4*4 - 4*(-2) + (-2)*(-2)  # 16+8+4=28
        ok1 = g1 is not None and abs(g1 - expected) < 0.5
        ok2 = g2 is not None and abs(g2 - expected) < 0.5
        
        negatives.append({
            "model": name,
            "test": "example_scaffolding",
            "without_example": ok1,
            "with_example": ok2,
            "finding": "Example scaffolding helps" if ok2 and not ok1 else
                       "Example scaffolding doesn't help" if ok1 and not ok2 else
                       "Both work" if ok1 and ok2 else "Both fail",
        })
        print(f"  {name} example scaffold: bare={ok1}, scaffolded={ok2}")
    
    # Test 3: Does bigger max_tokens help on failed queries?
    for name, (mid, prov, key) in MODELS.items():
        hard = "Compute: 2 + 3 + 5 + 7 + 11 + 13 + 17 + 19 + 23 + 29. Give ONLY the number."
        expected = 129
        
        a_short = await query(client, mid, prov, key, hard, mt=10)
        a_long = await query(client, mid, prov, key, hard, mt=200)
        
        g_short = extract_num(a_short)
        g_long = extract_num(a_long)
        
        ok_s = g_short is not None and abs(g_short - expected) < 0.5
        ok_l = g_long is not None and abs(g_long - expected) < 0.5
        
        negatives.append({
            "model": name,
            "test": "max_tokens_effect",
            "mt10_correct": ok_s,
            "mt200_correct": ok_l,
            "finding": "More tokens helps" if ok_l and not ok_s else
                       "Tokens don't matter" if ok_s == ok_l else
                       "More tokens HURTS (?)",
        })
        print(f"  {name} max_tokens: mt10={ok_s}, mt200={ok_l}")
    
    summary = json.dumps(negatives, indent=2)
    await emit_tile("night-lab-track-e", "Negative results archive", summary)
    return negatives


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("═══ FORGEMASTER NIGHT LAB ═══")
    print(f"Models: seed-mini, glm-5-turbo")
    print(f"PLATO: {PLATO}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_results = {}
    
    async with httpx.AsyncClient(timeout=35) as client:
        all_results["track_a"] = await track_a(client)
        print()
        all_results["track_b"] = await track_b(client)
        print()
        all_results["track_c"] = await track_c(client)
        print()
        await track_d(client)
        print()
        all_results["track_e"] = await track_e(client)
    
    # Save full results
    out = os.path.expanduser("~/.openclaw/workspace/experiments/night-lab-results.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved: {out}")
    
    # Final summary tile
    await emit_tile("night-lab-summary", "Night Lab Complete",
                   json.dumps({k: str(v)[:200] for k, v in all_results.items()}, indent=2))
    print("Night lab complete. Results tiled to PLATO.")

if __name__ == "__main__":
    asyncio.run(main())

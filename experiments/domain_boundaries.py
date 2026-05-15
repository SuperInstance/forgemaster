#!/usr/bin/env python3
"""
domain_boundaries.py — Find exact boundaries between model capabilities.

For each model, sweep through difficulty levels in each domain.
Find the critical angle (first failure) and the recovery angle (first success after failure).

This gives us: "seed-mini is safe up to addition depth 50, multiplication depth 7,
coefficient familiarity score 3/5, etc."

Cost: ~$0.50 total (100 queries × $0.05/1K × ~100 tokens each)
"""
import asyncio, json, time, os, re
import httpx

DEEPINFRA_KEY = open(os.path.expanduser(
    "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
ZAI_KEY = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
PLATO = "http://147.224.38.131:8847"

MODELS = {
    "seed-mini": ("ByteDance/Seed-2.0-mini", "deepinfra", DEEPINFRA_KEY),
    "glm-5-turbo": ("glm-5-turbo", "zai", ZAI_KEY),
}


async def query(client, mid, prov, key, prompt, mt=80):
    url = ("https://api.deepinfra.com/v1/openai/chat/completions" if prov == "deepinfra"
           else "https://api.z.ai/api/coding/paas/v4/chat/completions")
    try:
        r = await client.post(url, json={
            "model": mid,
            "messages": [
                {"role": "system", "content": "Give ONLY the final answer."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0, "max_tokens": mt,
        }, headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, timeout=30)
        data = r.json()
        if "choices" in data:
            msg = data["choices"][0]["message"]
            text = msg.get("content", "") or msg.get("reasoning_content", "")
            return text.strip()
        return "ERROR"
    except Exception as e:
        return f"ERROR: {e}"


def check(text, expected):
    expected = str(expected)
    if expected in text:
        return True
    nums = re.findall(r'-?\d+\.?\d*', text)
    if nums:
        try: return abs(float(nums[-1]) - float(expected)) < 0.5
        except: pass
    return False


async def sweep(client, mid, prov, key, name, domain, probes):
    """Run a series of probes and find the critical angle."""
    results = []
    last_success = 0
    first_failure = None
    
    for i, (prompt, expected) in enumerate(probes):
        answer = await query(client, mid, prov, key, prompt)
        ok = check(answer, expected)
        results.append({"depth": i+1, "correct": ok, "got": answer[:30]})
        
        if ok:
            last_success = i + 1
        elif first_failure is None:
            first_failure = i + 1
        
        await asyncio.sleep(0.3)
    
    ca = first_failure if first_failure else "∞"
    accuracy = sum(1 for r in results if r["correct"]) / len(results)
    
    return {
        "model": name, "domain": domain,
        "critical_angle": ca, "last_success": last_success,
        "accuracy": round(accuracy, 3),
        "results": results,
    }


async def main():
    print("═══ DOMAIN BOUNDARY MAPPER ═══")
    all_results = []
    
    async with httpx.AsyncClient(timeout=35) as client:
        for name, (mid, prov, key) in MODELS.items():
            print(f"\n═ {name} ═")
            
            # ── Input magnitude sweep ──
            mag_probes = [
                (f"What is {a} + {b}? Give ONLY the number.", str(a+b))
                for a, b in [(3,5), (37,48), (456,789), (12345,67890),
                            (999999,1), (123456789,987654321)]
            ]
            r = await sweep(client, mid, prov, key, name, "magnitude", mag_probes)
            print(f"  magnitude: CA={r['critical_angle']} accuracy={r['accuracy']:.0%}")
            all_results.append(r)
            
            # ── Operation complexity sweep ──
            op_probes = [
                ("What is 7 + 5? Give ONLY the number.", "12"),
                ("What is 7 - 5? Give ONLY the number.", "2"),
                ("What is 7 × 5? Give ONLY the number.", "35"),
                ("What is 35 ÷ 7? Give ONLY the number.", "5"),
                ("What is 7²? Give ONLY the number.", "49"),
                ("What is √49? Give ONLY the number.", "7"),
                ("What is 7! (factorial)? Give ONLY the number.", "5040"),
                ("What is 2⁸? Give ONLY the number.", "256"),
            ]
            r = await sweep(client, mid, prov, key, name, "operations", op_probes)
            print(f"  operations: CA={r['critical_angle']} accuracy={r['accuracy']:.0%}")
            all_results.append(r)
            
            # ── Code complexity sweep ──
            code_probes = [
                ("What type does len('hello') return? One word.", "int"),
                ("What does [1,2,3][1] return? Give ONLY the value.", "2"),
                ("What does 'hello'[1:3] return? Give ONLY the string.", "el"),
                ("What does {1,2,3} & {2,3,4} return? Give ONLY the set.", "{2, 3}"),
                ("What does dict(a=1)['a'] return? Give ONLY the value.", "1"),
                ("What does list(map(str, [1,2])) return?", "['1', '2']"),
                ("What does (lambda x: x*2)(5) return? Give ONLY the number.", "10"),
                ("What does sum(x**2 for x in range(4)) return? Give ONLY the number.", "14"),
            ]
            r = await sweep(client, mid, prov, key, name, "code_depth", code_probes)
            print(f"  code_depth: CA={r['critical_angle']} accuracy={r['accuracy']:.0%}")
            all_results.append(r)
            
            # ── Reasoning depth sweep ──
            reason_probes = [
                ("All cats are animals. Whiskers is a cat. Is Whiskers an animal? Answer TRUE or FALSE.", "TRUE"),
                ("No fish can fly. Salmon are fish. Can salmon fly? Answer TRUE or FALSE.", "FALSE"),
                ("All A are B. Some B are C. Are all A definitely C? Answer TRUE or FALSE.", "FALSE"),
                ("If it rains, streets are wet. Streets are wet. Did it definitely rain? Answer TRUE or FALSE.", "FALSE"),
                ("If X then Y. Not Y. Is X definitely false? Answer TRUE or FALSE.", "TRUE"),
                ("All birds can fly. Penguins are birds. Can penguins fly? (Premise is false in reality, but answer from the premise alone.) Answer TRUE or FALSE.", "TRUE"),
            ]
            r = await sweep(client, mid, prov, key, name, "reasoning_depth", reason_probes)
            print(f"  reasoning: CA={r['critical_angle']} accuracy={r['accuracy']:.0%}")
            all_results.append(r)
    
    # Summary
    print("\n═ BOUNDARY MAP ═")
    for r in all_results:
        print(f"  {r['model']:15s} {r['domain']:20s} CA={str(r['critical_angle']):>3s}  acc={r['accuracy']:.0%}")
    
    # Save
    out = os.path.expanduser("~/.openclaw/workspace/experiments/domain-boundaries.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved: {out}")
    
    # Tile
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            summary = "\n".join(
                f"{r['model']} {r['domain']}: CA={r['critical_angle']} acc={r['accuracy']:.0%}"
                for r in all_results
            )
            await c.post(f"{PLATO}/submit", json={
                "room_id": "night-lab-boundaries",
                "domain": "fleet-calibration",
                "agent": "forgemaster-nightlab",
                "question": "Domain boundary map: 4 domains × 2 models",
                "answer": summary,
                "tile_type": "calibration",
                "confidence": 0.95,
            })
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main())

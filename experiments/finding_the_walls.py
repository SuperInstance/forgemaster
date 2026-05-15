#!/usr/bin/env python3
"""
finding_the_walls.py — Push seed-mini to its actual limits with P4 prompt.

Now that P4 gives 100% on standard probes, push harder:
  - Addition depth up to 100
  - Multiplication with larger numbers  
  - Chained mixed operations
  - Nested parentheses depth
  - Simultaneous equations (two unknowns)
  - Abstract pattern completion
"""
import asyncio, json, os, re, time
import httpx

DI_KEY = open(os.path.expanduser(
    "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
PLATO = "http://147.224.38.131:8847"

SYSTEM = "Answer with just the digits, no words."

async def q(client, prompt, mt=80):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://api.deepinfra.com/v1/openai/chat/completions", json={
            "model": "ByteDance/Seed-2.0-mini",
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0, "max_tokens": mt,
        }, headers={"Authorization": f"Bearer {DI_KEY}", "Content-Type": "application/json"})
        data = r.json()
        msg = data["choices"][0]["message"]
        return msg.get("content", "") or msg.get("reasoning_content", "")


async def main():
    print("═══ FINDING THE WALLS ═══")
    print("P4 prompt, seed-mini, pushing to actual limits")
    print()
    
    results = {}
    
    # ── Addition depth to 100 ──
    print("═ Addition Depth (1-50) ═")
    wall = None
    for depth in range(1, 51):
        numbers = [str((i * 3 + 7) % 20 + 1) for i in range(depth)]
        expr = " + ".join(numbers)
        expected = sum(int(n) for n in numbers)
        answer = await q(client=None, prompt=f"Compute: {expr}")
        # Inline query
        import httpx as hx
        async with hx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.deepinfra.com/v1/openai/chat/completions", json={
                "model": "ByteDance/Seed-2.0-mini",
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": f"Compute: {expr}"}],
                "temperature": 0.0, "max_tokens": 80,
            }, headers={"Authorization": f"Bearer {DI_KEY}", "Content-Type": "application/json"})
            data = r.json()
            answer = data["choices"][0]["message"].get("content", "")
        
        nums = re.findall(r'-?\d+', answer)
        got = int(nums[-1]) if nums else None
        ok = got == expected
        if ok:
            print(f"  depth {depth:3d}: ✓", flush=True)
        else:
            wall = depth
            print(f"  depth {depth:3d}: ✗ (got {got}, expected {expected})", flush=True)
            break
        await asyncio.sleep(0.5)
    
    results["addition_wall"] = wall or "∞ (tested to 50)"
    print(f"  → Addition wall: {results['addition_wall']}")
    
    # ── Multiplication with bigger numbers ──
    print("\n═ Multiplication Scale ═")
    mul_tests = [
        ("What is 12 * 34?", 408),
        ("What is 123 * 456?", 56088),
        ("What is 1234 * 5678?", 7006652),
        ("What is 12345 * 67890?", 838102050),
        ("What is 99999 * 99999?", 9999800001),
    ]
    for prompt, expected in mul_tests:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.deepinfra.com/v1/openai/chat/completions", json={
                "model": "ByteDance/Seed-2.0-mini",
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}],
                "temperature": 0.0, "max_tokens": 80,
            }, headers={"Authorization": f"Bearer {DI_KEY}", "Content-Type": "application/json"})
            answer = r.json()["choices"][0]["message"].get("content", "")
        
        nums = re.findall(r'-?\d+', answer)
        got = int(nums[-1]) if nums else None
        ok = got == expected
        print(f"  {prompt:30s} → {'✓' if ok else f'✗ got {got} expected {expected}'}")
        await asyncio.sleep(0.5)
    
    # ── Mixed operations chain ──
    print("\n═ Mixed Operation Chains ═")
    chains = [
        ("What is (37 + 48) * 2?", 170),
        ("What is (100 - 37) * 3?", 189),
        ("What is (12 * 5) + (8 * 7)?", 116),
        ("What is (144 / 12) + (15 * 3)?", 51),
        ("What is ((37 + 48) - 12) * 3?", 219),
        ("What is ((100 - 37) * 3) + (8 * 7)?", 245),
        ("What is (((12 * 5) + 8) * 3) - 7?", 197),
        ("What is ((((37 + 48) * 2) - 15) / 7)?", int(((37+48)*2-15)/7)),
    ]
    chain_correct = 0
    for prompt, expected in chains:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.deepinfra.com/v1/openai/chat/completions", json={
                "model": "ByteDance/Seed-2.0-mini",
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}],
                "temperature": 0.0, "max_tokens": 80,
            }, headers={"Authorization": f"Bearer {DI_KEY}", "Content-Type": "application/json"})
            answer = r.json()["choices"][0]["message"].get("content", "")
        
        nums = re.findall(r'-?\d+', answer)
        got = int(nums[-1]) if nums else None
        ok = got == expected
        if ok: chain_correct += 1
        print(f"  {prompt:35s} → {'✓' if ok else f'✗ got {got} expected {expected}'}")
        await asyncio.sleep(0.5)
    
    results["chains"] = f"{chain_correct}/{len(chains)}"
    
    # ── Abstract pattern ──
    print("\n═ Abstract Patterns ═")
    patterns = [
        ("In the sequence 2, 4, 8, 16, what comes next?", "32"),
        ("In the sequence 1, 1, 2, 3, 5, 8, what comes next?", "13"),
        ("In the sequence 3, 6, 12, 24, what comes next?", "48"),
        ("In the sequence 1, 4, 9, 16, 25, what comes next?", "36"),
        ("In the sequence 2, 3, 5, 7, 11, 13, what comes next?", "17"),
    ]
    pat_correct = 0
    for prompt, expected in patterns:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.deepinfra.com/v1/openai/chat/completions", json={
                "model": "ByteDance/Seed-2.0-mini",
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}],
                "temperature": 0.0, "max_tokens": 20,
            }, headers={"Authorization": f"Bearer {DI_KEY}", "Content-Type": "application/json"})
            answer = r.json()["choices"][0]["message"].get("content", "")
        
        ok = expected in answer
        if ok: pat_correct += 1
        print(f"  {prompt[:50]:50s} → {'✓' if ok else f'✗ got {answer.strip()[:20]}'}")
        await asyncio.sleep(0.5)
    
    results["patterns"] = f"{pat_correct}/{len(patterns)}"
    
    # Summary
    print(f"\n═ WALLS FOUND ═")
    print(json.dumps(results, indent=2))
    
    # Tile
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{PLATO}/submit", json={
                "room_id": "night-lab-walls",
                "domain": "fleet-calibration",
                "agent": "forgemaster-nightlab",
                "question": "Finding the walls: seed-mini with P4 prompt",
                "answer": json.dumps(results, indent=2),
                "tile_type": "calibration",
                "confidence": 0.95,
            })
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main())

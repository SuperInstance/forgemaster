#!/usr/bin/env python3
"""
calibrate_unmapped.py — Map critical angles for 10 uncalibrated models.

These models are available but NOT in the routing table yet:
  DeepInfra: Qwen3.5-9B, Qwen3.5-27B, MiMo-V2.5, Step-3.5-Flash, Qwen2.5-72B
  Groq: llama-3.1-8b, llama-3.3-70b, llama-4-scout-17b, qwen3-32b
  z.ai: glm-5-turbo (needs more data)

Quick calibration: 10 probes per model, ~60s total.
"""
import asyncio, json, time, os, sys, re
import httpx

DEEPINFRA_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
GROQ_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/groq-api-key.txt")).read().strip()
ZAI_KEY = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"

MODELS = [
    # (name, model_id, provider, temperature)
    ("qwen3.5-9b", "Qwen/Qwen3.5-9B", "deepinfra", 0.0),
    ("qwen3.5-27b", "Qwen/Qwen3.5-27B", "deepinfra", 0.0),
    ("mimo-v2.5", "allenai/MiMo-V2.5", "deepinfra", 0.0),
    ("step-3.5-flash", "stepfun/Step-3.5-Flash", "deepinfra", 0.0),
    ("qwen2.5-72b", "Qwen/Qwen2.5-72B-Instruct", "deepinfra", 0.0),
    ("llama-3.1-8b", "llama-3.1-8b-instant", "groq", 0.0),
    ("llama-3.3-70b", "llama-3.3-70b-versatile", "groq", 0.0),
    ("llama-4-scout", "llama-4-scout-17b-16e-instruct", "groq", 0.0),
    ("qwen3-32b", "qwen3-32b", "groq", 0.0),
    ("glm-5-turbo", "glm-5-turbo", "zai", 0.3),
]

PROBES = [
    # Arithmetic depth ladder
    ("What is 37 + 48? Give ONLY the number.", "85"),
    ("What is 3 + 5 + 7 + 9 + 11? Give ONLY the number.", "35"),
    ("What is 2 × 3 × 4 × 5? Give ONLY the number.", "120"),
    # Coefficient familiarity
    ("Compute N(5,-3) where N(a,b) = a² - ab + b². Give ONLY the number.", "49"),
    ("Compute N(5,-3) where N(a,b) = a² - ab + 2b². Give ONLY the number.", "58"),
    # Reasoning
    ("All cats are animals. Whiskers is a cat. What is Whiskers? Give ONLY the category.", "animal"),
    ("If it rains the ground gets wet. The ground is wet. Can we be CERTAIN it rained? Answer CERTAIN or UNCERTAIN.", "UNCERTAIN"),
    # Code
    ("What does 'def f(x): return x*x' compute? Give ONLY the mathematical operation.", "square"),
    # Strategy  
    ("A system has 3 components. Each fails independently with 10% chance. What is the chance at least one fails? Give ONLY the percentage.", "27.1"),
    # Magnitude
    ("What is 999999 + 1? Give ONLY the number.", "1000000"),
]


def get_endpoint(provider):
    if provider == "deepinfra":
        return "https://api.deepinfra.com/v1/openai/chat/completions", DEEPINFRA_KEY
    elif provider == "groq":
        return "https://api.groq.com/openai/v1/chat/completions", GROQ_KEY
    elif provider == "zai":
        return "https://api.z.ai/api/coding/paas/v4/chat/completions", ZAI_KEY
    return None, None


def extract_answer(text, expected):
    """Try to match the answer."""
    text = text.strip().lower()
    expected = expected.strip().lower()
    if text == expected:
        return True
    # Expected in text
    if expected in text:
        return True
    # Last number
    nums = re.findall(r'-?\d+\.?\d*', text)
    if nums:
        try:
            if abs(float(nums[-1]) - float(expected)) < 0.5:
                return True
        except:
            pass
    return False


async def calibrate(client, name, model_id, provider, temperature):
    endpoint, key = get_endpoint(provider)
    results = []
    t0 = time.time()
    
    for question, expected in PROBES:
        try:
            body = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "Give ONLY the final answer."},
                    {"role": "user", "content": question},
                ],
                "temperature": temperature,
                "max_tokens": 50,
            }
            r = await client.post(endpoint, json=body, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }, timeout=30)
            data = r.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content", "")
            reasoning = choice.get("reasoning_content", "")
            text = content if content.strip() else reasoning
            
            correct = extract_answer(text, expected)
            results.append({
                "q": question[:40], "expected": expected,
                "got": text.strip()[:30], "correct": correct,
            })
        except Exception as e:
            results.append({
                "q": question[:40], "expected": expected,
                "got": f"ERROR: {str(e)[:30]}", "correct": False,
            })
    
    duration = time.time() - t0
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    accuracy = correct / total if total > 0 else 0
    
    # Find first failure per category
    failures = {}
    categories = ["add", "add_chain", "mul", "coeff1", "coeff2",
                  "syllogism", "abduction", "code", "strategy", "magnitude"]
    for i, r in enumerate(results):
        cat = categories[i] if i < len(categories) else f"q{i}"
        if not r["correct"] and cat not in failures:
            failures[cat] = i + 1
    
    return {
        "model": name,
        "model_id": model_id,
        "provider": provider,
        "temperature": temperature,
        "accuracy": round(accuracy, 3),
        "correct": correct,
        "total": total,
        "failures": failures,
        "duration_s": round(duration, 1),
        "details": results,
    }


async def main():
    print("═══ Calibrating 10 Unmapped Models ═══")
    print(f"Probes: {len(PROBES)} per model")
    print()
    
    results = []
    async with httpx.AsyncClient(timeout=35) as client:
        for name, model_id, provider, temp in MODELS:
            print(f"  {name:20s}", end="", flush=True)
            r = await calibrate(client, name, model_id, provider, temp)
            results.append(r)
            bar = "█" * int(r["accuracy"] * 10) + "░" * (10 - int(r["accuracy"] * 10))
            print(f" {bar} {r['correct']}/{r['total']} = {r['accuracy']:.0%} ({r['duration_s']:.0f}s)")
    
    # Sort by accuracy
    results.sort(key=lambda r: -r["accuracy"])
    
    print()
    print("═══ Ranking ═══")
    for i, r in enumerate(results):
        failures = ", ".join(r["failures"].keys()) if r["failures"] else "none"
        print(f"  {i+1:2d}. {r['model']:20s} {r['accuracy']:.0%}  fails: {failures}")
    
    # Recommend additions to routing table
    print()
    print("═══ Routing Recommendations ═══")
    for r in results:
        if r["accuracy"] >= 0.7:
            print(f"  ✅ {r['model']:20s} {r['accuracy']:.0%} — ADD to routing table")
        elif r["accuracy"] >= 0.5:
            print(f"  ⚠  {r['model']:20s} {r['accuracy']:.0%} — backup only")
        else:
            print(f"  ❌ {r['model']:20s} {r['accuracy']:.0%} — unreliable")
    
    # Save results
    out_path = os.path.expanduser("~/.openclaw/workspace/experiments/unmapped-calibration.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")
    
    # Emit to PLATO
    try:
        summary = "\n".join(f"{r['model']}: {r['accuracy']:.0%}" for r in results)
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post("http://147.224.38.131:8847/submit", json={
                "room_id": "calibration-bulk",
                "domain": "fleet-calibration",
                "agent": "forgemaster",
                "question": "Bulk calibration: 10 unmapped models",
                "answer": summary,
                "tile_type": "calibration",
                "tags": ["calibration", "bulk", "10-models"],
                "confidence": 0.9,
            })
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())

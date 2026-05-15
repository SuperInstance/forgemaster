#!/usr/bin/env python3
"""
prompt_engineering_atlas.py — Map which prompt patterns work for which models.

This is the systematic study. Not vibes — data.

5 prompt patterns × 10 questions × 2 models = 100 data points.
Each pattern is tested against the same questions to isolate the pattern effect.

Patterns:
  P1: Direct ("Give ONLY the number")
  P2: Student seed ("Let's think step by step")
  P3: Example-scaffolded (one worked example, then the question)
  P4: Format-specified ("Answer with just the digits")
  P5: Chain-of-thought (explicit reasoning request)
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

PATTERNS = {
    "P1_direct": "Give ONLY the final answer.",
    "P2_student": "Let's think step by step, then give the final answer.",
    "P3_scaffold": "Example: 37 + 48 = 85\nNow solve this:",
    "P4_format": "Answer with just the digits, no words.",
    "P5_cot": "Show your reasoning, then give the final number on the last line.",
}

QUESTIONS = [
    ("What is 23 + 45?", "68"),
    ("What is 847 + 293?", "1140"),
    ("What is 7 × 13?", "91"),
    ("What is 12 × 15?", "180"),
    ("Compute N(3,2) where N(a,b) = a² - ab + b².", "7"),
    ("Compute N(5,-3) where N(a,b) = a² - ab + b².", "49"),
    ("What is 999 + 1?", "1000"),
    ("What is 1234 + 5678?", "6912"),
    ("What is 2³?", "8"),
    ("What is 15²?", "225"),
]


def extract_num(text):
    nums = re.findall(r'-?\d+\.?\d*', text)
    return float(nums[-1]) if nums else None


async def query(client, model_id, provider, key, system, prompt, mt=80):
    url = ("https://api.deepinfra.com/v1/openai/chat/completions" if provider == "deepinfra"
           else "https://api.z.ai/api/coding/paas/v4/chat/completions")
    try:
        r = await client.post(url, json={
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0, "max_tokens": mt,
        }, headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, timeout=30)
        data = r.json()
        if "choices" in data:
            msg = data["choices"][0]["message"]
            return msg.get("content", "") or msg.get("reasoning_content", "")
        return "ERROR"
    except Exception as e:
        return f"ERROR: {e}"


async def main():
    print("═══ PROMPT ENGINEERING ATLAS ═══")
    print(f"5 patterns × 10 questions × 2 models = 100 data points")
    print()
    
    results = {}
    
    async with httpx.AsyncClient(timeout=35) as client:
        for model_name, (mid, prov, key) in MODELS.items():
            model_results = {}
            print(f"═ {model_name} ═")
            
            for pat_name, system in PATTERNS.items():
                correct = 0
                total = 0
                for q, expected in QUESTIONS:
                    answer = await query(client, mid, prov, key, system, q)
                    got = extract_num(answer)
                    expected_f = float(expected)
                    if got is not None and abs(got - expected_f) < 0.5:
                        correct += 1
                    total += 1
                    await asyncio.sleep(0.3)
                
                pct = correct / total
                model_results[pat_name] = {"correct": correct, "total": total, "accuracy": pct}
                bar = "█" * int(pct * 10) + "░" * (10 - int(pct * 10))
                print(f"  {pat_name:20s} {bar} {correct}/{total} = {pct:.0%}")
            
            results[model_name] = model_results
            print()
    
    # Find best pattern per model
    print("═ BEST PATTERNS ═")
    for model_name, model_results in results.items():
        best = max(model_results.items(), key=lambda x: x[1]["accuracy"])
        worst = min(model_results.items(), key=lambda x: x[1]["accuracy"])
        print(f"  {model_name}: best={best[0]} ({best[1]['accuracy']:.0%}), "
              f"worst={worst[0]} ({worst[1]['accuracy']:.0%})")
    
    # Save
    out = os.path.expanduser("~/.openclaw/workspace/experiments/prompt-atlas-results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
    
    # Tile
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{PLATO}/submit", json={
                "room_id": "night-lab-prompt-atlas",
                "domain": "prompt-engineering",
                "agent": "forgemaster-nightlab",
                "question": "Prompt Engineering Atlas: 5 patterns × 10 questions × 2 models",
                "answer": json.dumps(results, indent=2, default=str)[:500],
                "tile_type": "experiment",
                "tags": ["night-lab", "prompt-engineering"],
                "confidence": 0.95,
            })
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main())

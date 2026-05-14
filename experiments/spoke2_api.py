#!/usr/bin/env python3
"""Spoke 2: Width boundary test on API models including Kimi and MoE."""
import requests, json, re, time

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/deepinfra-api-key.txt").read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

TASKS = [
    ("w1_fam", "a²+b²", 1, [(3,4,25),(5,-2,29),(-4,3,25),(7,1,50)]),
    ("w1_nov", "2a+b²", 1, [(3,4,22),(5,-2,14),(-4,3,1),(7,1,15)]),
    ("w2_nov", "a²+2ab", 2, [(3,4,33),(5,-2,5),(-4,3,8),(7,1,63)]),
    ("w3_fam", "a²-ab+b²", 3, [(3,4,13),(5,-2,39),(-4,3,37),(7,1,43)]),
]

MODELS = [
    "moonshotai/Kimi-K2.6",
    "moonshotai/Kimi-K2.5",
    "Qwen/Qwen3-30B-A3B",
    "Qwen/Qwen3-14B",
    "Qwen/Qwen3-32B",
    "Qwen/Qwen3.5-4B",
    "Qwen/Qwen3.6-35B-A3B",
]

def query(model_id, prompt):
    try:
        r = requests.post(URL,
            headers={"Authorization": f"Bearer {KEY}"},
            json={"model": model_id, "messages": [{"role":"user","content":prompt}],
                  "temperature": 0.3, "max_tokens": 50},
            timeout=90)
        d = r.json()
        msg = d.get("choices",[{}])[0].get("message",{})
        content = msg.get("content","").strip()
        rc = msg.get("reasoning_content","")
        nums = re.findall(r"-?\d+", content)
        if nums: return int(nums[-1]), content[:40]
        nums = re.findall(r"-?\d+", rc)
        if nums: return int(nums[-1]), f"[think] {rc[:40]}"
        return 0, content[:80]
    except Exception as e:
        return 0, f"ERR: {e}"

sep = "=" * 60

for mid in MODELS:
    name = mid.split("/")[-1]
    print(f"\n{sep}", flush=True)
    print(f"  {name}", flush=True)
    print(f"{sep}", flush=True)

    for tkey, formula, width, cases in TASKS:
        correct = 0
        total = len(cases)
        for a, b, ans in cases:
            prompt = f"Compute {formula} where a={a} and b={b}. Give ONLY the number."
            out, raw = query(mid, prompt)
            ok = out == ans
            if ok: correct += 1
            sym = "✅" if ok else "❌"
            print(f"  {sym} {tkey:<8s} ({a:>3},{b:>3})→{out:>6}  ans={ans}  {raw[:30]}", flush=True)
            time.sleep(0.4)
        print(f"     → {correct}/{total} ({correct/total*100:.0f}%)", flush=True)

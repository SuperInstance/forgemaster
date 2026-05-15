#!/usr/bin/env python3
"""Spoke 2 on Groq — non-reasoning models, clean content extraction."""
import requests, json, re, time

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"

TASKS = [
    ("w1_fam", "a²+b²", 1, [(3,4,25),(5,-2,29),(-4,3,25),(7,1,50)]),
    ("w1_nov", "2a+b²", 1, [(3,4,22),(5,-2,14),(-4,3,1),(7,1,15)]),
    ("w2_nov", "a²+2ab", 2, [(3,4,33),(5,-2,5),(-4,3,8),(7,1,63)]),
    ("w3_fam", "a²-ab+b²", 3, [(3,4,13),(5,-2,39),(-4,3,37),(7,1,43)]),
]

MODELS = [
    "llama-3.1-8b-instant",    # The one Casey asked about
    "llama-3.3-70b-versatile",  # Bigger llama
    "meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4 MoE
    "qwen/qwen3-32b",           # Qwen on Groq
]

def query(model, prompt):
    try:
        r = requests.post(URL,
            headers={"Authorization": f"Bearer {KEY}"},
            json={"model": model, "messages": [{"role":"user","content":prompt}],
                  "temperature": 0.3, "max_tokens": 20},
            timeout=30)
        d = r.json()
        content = d.get("choices",[{}])[0].get("message",{}).get("content","").strip()
        nums = re.findall(r"-?\d+", content)
        return int(nums[-1]) if nums else 0, content[:30]
    except Exception as e:
        return 0, f"ERR:{e}"

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
            # Check for partial/echo
            tag = ""
            if not ok:
                if out == a: tag = " [echo-a]"
                elif out == b: tag = " [echo-b]"
                elif out == a*a: tag = " [partial-a²]"
                elif out == b*b: tag = " [partial-b²]"
                elif out == a+b: tag = " [echo-sum]"
                elif abs(out-ans) <= 2: tag = " [near]"
            print(f"  {sym} {tkey:<8s} ({a:>3},{b:>3})→{out:>6}  ans={ans}{tag}  {raw[:20]}", flush=True)
            time.sleep(0.3)
        print(f"     → {correct}/{total} ({correct/total*100:.0f}%)", flush=True)

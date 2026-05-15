#!/usr/bin/env python3
"""Prompt Sensitivity Study — llama-3.1-8b-instant
Systematic study of what wording evokes computation vs echo."""
import requests, re, time

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def groq(system, prompt, temp=0.3):
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
        json={"model": MODEL, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], "temperature": temp, "max_tokens": 100}, timeout=30)
    c = r.json()["choices"][0]["message"]["content"].strip()
    nums = re.findall(r"-?\d+", c)
    return int(nums[-1]) if nums else None, c

a, b, ans = 5, -3, 49

PROMPTS = [
    ("bare",           "", "What is N({a},{b})?"),
    ("formula",        "", "Compute a²-ab+b² where a={a} and b={b}."),
    ("formula_only",   "Give ONLY the number, no work.", "a²-ab+b², a={a}, b={b}"),
    ("step_by_step",   "", "Step 1: square a. Step 2: multiply a×b. Step 3: square b. Step 4: subtract step2 from step1. Step 5: add step3. Use a={a}, b={b}."),
    ("code_like",      "", "result = a*a - a*b + b*b where a={a}, b={b}. What is result?"),
    ("teacher",        "You are a math teacher.", "Compute the Eisenstein norm N(a,b)=a²-ab+b² for a={a}, b={b}. Answer:"),
    ("student",        "You are a student taking a math test.", "N(a,b) = a²-ab+b². What is N({a},{b})?"),
    ("constraints",    "You MUST show your work then give the final answer on the last line.", "Compute a²-ab+b² for a={a}, b={b}."),
    ("first_princ",    "", "To compute a²-ab+b²: first compute each piece separately (a², ab, b²), then combine. Use a={a}, b={b}."),
    ("chain",          "Think step by step.", "a²-ab+b² where a={a} and b={b}"),
    ("named",          "", "The Eisenstein norm is defined as N(a,b)=a²-ab+b². Compute N({a},{b})."),
    ("substitute",     "", "Substitute a={a} and b={b} into a²-ab+b². What do you get?"),
    ("work_answer",    "", "Compute a²-ab+b² for a={a}, b={b}. Show work then write ANSWER: <number>"),
    ("arithmetic",     "You are an arithmetic engine.", "a={a} b={b} op=a²-ab+b² result=?"),
    ("brackets",       "", "Calculate: (({a}×{a}) - ({a}×{b})) + ({b}×{b})"),
    ("assert",         "", "a²-ab+b² with a={a} and b={b} equals what number? Do the arithmetic."),
    ("seed",           "", "N({a},{b}). a²-ab+b². Just the number."),
    ("zero_shot_cot",  "", "Let's work this out step by step to be sure we get the right answer for a²-ab+b² with a={a}, b={b}."),
    ("reverse_mental", "", "I need a²-ab+b² where a={a} and b={b}. First I'll compute a², then ab, then b², then combine."),
    ("seed_compact",   "", "{a}²-{a}×{b}+{b}²="),
]

print("=== PROMPT SENSITIVITY: llama-3.1-8b-instant ===", flush=True)
print(f"Task: N({a},{b}) = {ans} (Eisenstein norm)", flush=True)
print(f"{'Style':<18s} {'Out':>5s} {'OK':>3s} {'Response (first 35 chars)'}", flush=True)
print("-" * 70, flush=True)

results = {}
for name, sys_msg, tmpl in PROMPTS:
    prompt = tmpl.format(a=a, b=b)
    out, raw = groq(sys_msg, prompt)
    ok = out == ans
    results[name] = ok
    sym = "✅" if ok else "❌"
    print(f"{name:<18s} {str(out):>5s} {sym:>3s} {raw[:35]}", flush=True)
    time.sleep(0.3)

correct = [k for k, v in results.items() if v]
failing = [k for k, v in results.items() if not v]
print(f"\nCorrect: {len(correct)}/{len(PROMPTS)} ({len(correct)/len(PROMPTS)*100:.0f}%)", flush=True)
print(f"Working: {correct}", flush=True)
print(f"Failing: {failing}", flush=True)

# ─── Now test best prompts on 5 different inputs ──────────────
print(f"\n\n=== TOP PROMPTS ON 5 INPUTS ===", flush=True)
test_cases = [(3,4,13), (5,-2,39), (-4,3,37), (7,1,43), (-6,-5,91)]

for name in correct[:5]:
    sys_msg = [s for n, s, _ in PROMPTS if n == name][0]
    tmpl = [t for n, _, t in PROMPTS if n == name][0]
    wins = 0
    for a2, b2, ans2 in test_cases:
        prompt = tmpl.format(a=a2, b=b2)
        out, _ = groq(sys_msg, prompt)
        if out == ans2: wins += 1
        time.sleep(0.2)
    print(f"  {name:<18s} {wins}/5", flush=True)

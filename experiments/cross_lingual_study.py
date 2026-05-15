#!/usr/bin/env python3
"""Study 36: Cross-Lingual Vocabulary Wall"""
import json, time, os, sys
import urllib.request

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = [
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "ByteDance/Seed-2.0-mini",
]

PROMPTS = {
    "eisenstein_en": "Compute the Eisenstein norm of (5-3ω). N(a+bω) = a²-ab+b². Reply ONLY integer.",
    "eisenstein_zh": "计算艾森斯坦整数(5-3ω)的范数。N(a+bω) = a²-ab+b²。只回复整数。",
    "eisenstein_ja": "アイゼンシュタイン整数(5-3ω)のノルムを計算せよ。N(a+bω) = a²-ab+b²。整数のみ回答。",
    "eisenstein_es": "Calcula la norma de Eisenstein de (5-3ω). N(a+bω) = a²-ab+b². Responde SOLO el entero.",
    "arithmetic_en": "Compute: 25 - (-15) + 9 = ? Reply ONLY integer.",
    "arithmetic_zh": "计算: 25 - (-15) + 9 = ? 只回复整数。",
    "arithmetic_ja": "計算せよ: 25 - (-15) + 9 = ? 整数のみ回答。",
    "arithmetic_es": "Calcula: 25 - (-15) + 9 = ? Responde SOLO el entero.",
}

LANG_MAP = {
    "en": "English", "zh": "Chinese", "ja": "Japanese", "es": "Spanish"
}

FRAMING_MAP = {
    "eisenstein": "Eisenstein norm", "arithmetic": "Bare arithmetic"
}

TRIALS = 5
TEMP = 0.1

def call_model(model, prompt):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMP,
        "max_tokens": 256,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"].strip()
        # Extract thinking content if present (Qwen3)
        reasoning = ""
        msg = data["choices"][0]["message"]
        if "reasoning_content" in msg and msg["reasoning_content"]:
            reasoning = msg["reasoning_content"].strip()
        return {"content": content, "reasoning": reasoning, "error": None}
    except Exception as e:
        return {"content": None, "reasoning": None, "error": str(e)}

def detect_language(text):
    """Simple heuristic for response language."""
    if not text:
        return "unknown"
    has_cjk = any('\u4e00' <= c <= '\u9fff' for c in text)
    has_hira = any('\u3040' <= c <= '\u309f' for c in text)
    has_kata = any('\u30a0' <= c <= '\u30ff' for c in text)
    has_accent = any(c in 'áéíóúñ¿¡' for c in text.lower())
    if has_cjk and not has_hira and not has_kata:
        return "chinese"
    if has_hira or has_kata:
        return "japanese"
    if has_accent or text.lower().startswith(("calcula","la ","el ","es ","la norma")):
        return "spanish"
    return "english"

def is_correct(text):
    if not text:
        return False
    # Check if 49 appears as the answer
    import re
    # Look for standalone 49
    nums = re.findall(r'\b49\b', text)
    return len(nums) > 0

def response_pattern(text):
    if not text:
        return "error"
    stripped = text.strip()
    if stripped == "49":
        return "bare_number"
    if re.match(r'^49\b', stripped):
        return "number_with_explanation"
    if re.search(r'49', stripped):
        return "contains_49"
    return "no_49"

import re

results = []
total = len(MODELS) * len(PROMPTS) * TRIALS
count = 0

for model in MODELS:
    model_short = model.split("/")[-1]
    for prompt_key, prompt_text in PROMPTS.items():
        framing = "eisenstein" if prompt_key.startswith("eisenstein") else "arithmetic"
        lang = prompt_key.split("_")[1]
        
        for trial in range(TRIALS):
            count += 1
            print(f"[{count}/{total}] {model_short[:20]} | {lang} | {framing[:5]} | trial {trial+1}", flush=True)
            
            result = call_model(model, prompt_text)
            
            entry = {
                "model": model,
                "model_short": model_short,
                "prompt_key": prompt_key,
                "framing": framing,
                "language": lang,
                "trial": trial + 1,
                "prompt": prompt_text,
                "response": result["content"],
                "reasoning": result.get("reasoning", ""),
                "error": result["error"],
                "correct": is_correct(result["content"]),
                "response_language": detect_language(result["content"]) if result["content"] else "error",
                "response_pattern": response_pattern(result["content"]),
            }
            results.append(entry)
            
            status = "✓" if entry["correct"] else "✗"
            resp_preview = (result["content"] or "ERROR")[:60]
            print(f"  {status} → {resp_preview}", flush=True)
            
            time.sleep(0.5)  # Rate limit

# Save raw results
with open("/home/phoenix/.openclaw/workspace/experiments/cross-lingual-results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Analysis
print("\n\n=== ANALYSIS ===\n")

analysis = {}
for model in MODELS:
    model_short = model.split("/")[-1]
    analysis[model_short] = {}
    for framing in ["eisenstein", "arithmetic"]:
        for lang in ["en", "zh", "ja", "es"]:
            key = f"{framing}_{lang}"
            entries = [e for e in results if e["model"] == model and e["prompt_key"] == key]
            correct = sum(1 for e in entries if e["correct"])
            resp_langs = [e["response_language"] for e in entries if e["response"]]
            patterns = [e["response_pattern"] for e in entries]
            
            analysis[model_short][key] = {
                "accuracy": f"{correct}/{len(entries)}",
                "pct": correct / len(entries) * 100 if entries else 0,
                "response_languages": resp_langs,
                "patterns": patterns,
                "correct": correct,
                "total": len(entries),
            }
            
            print(f"{model_short[:25]:25s} | {framing:10s} | {lang:2s} | {correct}/{len(entries)} ({correct/len(entries)*100:.0f}%) | langs: {set(resp_langs)} | patterns: {set(patterns)}")

print("\nDone. Raw data saved to cross-lingual-results.json")

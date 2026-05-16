#!/usr/bin/env python3
"""
prompt_tuner.py — Test different prompts for DeepInfra models to get clean code output.
"""

import os
import json
import requests
import time

DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")
if not DEEPINFRA_API_KEY:
    print("Error: DEEPINFRA_API_KEY not set")
    exit(1)

MODELS = [
    "meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo",
    "nvidia/Nemotron-3-Nano-30B-A3B",
    "zai-org/GLM-4.7-Flash",
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
]

PROMPTS = [
    {
        "name": "strict_code",
        "text": "Write a CUDA kernel that adds two vectors. Return only the __global__ function with comments. No explanations, no markdown, no thinking."
    },
    {
        "name": "example_format",
        "text": """Write a CUDA kernel that adds two vectors.

Example output format:
#include <stdio.h>
__global__ void add_vectors(float* a, float* b, float* c, int n) {
    // kernel code here
}

Return ONLY the kernel code with comments, no explanations."""
    },
    {
        "name": "system_role",
        "text": "You are a CUDA expert. Write a CUDA kernel that adds two vectors. Return only the code with comments."
    },
    {
        "name": "markdown_block",
        "text": "```cpp\n// Write a CUDA kernel that adds two vectors\n__global__ void add_vectors(float* a, float* b, float* c, int n) {\n    // implementation\n}\n```\nReturn only the code inside the code block."
    },
]

def test_prompt(model, prompt_text):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 300,
        "temperature": 0.1
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return content
    except Exception as e:
        return f"ERROR: {e}"

def analyze_content(content):
    checks = {
        "has_global": "__global__" in content or "__device__" in content,
        "has_include": "#include" in content,
        "has_kernel": "kernel" in content.lower(),
        "has_comments": "//" in content or "/*" in content,
        "no_explanation": not content.lower().startswith(("we", "i", "here", "this", "the")),
        "length": len(content)
    }
    return checks

def main():
    print("═══ DeepInfra Prompt Tuner ⚒️ ═══")
    print(f"Testing {len(MODELS)} models with {len(PROMPTS)} prompts each\n")
    
    results = []
    
    for model in MODELS[:2]:  # Test first 2 models for speed
        print(f"\n## Model: {model}")
        for prompt in PROMPTS:
            print(f"\n  Prompt: {prompt['name']}")
            content = test_prompt(model, prompt["text"])
            checks = analyze_content(content)
            
            print(f"    Length: {checks['length']}")
            print(f"    Has __global__: {checks['has_global']}")
            print(f"    Has #include: {checks['has_include']}")
            print(f"    No explanation: {checks['no_explanation']}")
            
            if checks['has_global']:
                print(f"    ✓ SUCCESS: Kernel detected")
                # Show first 3 lines
                lines = content.split('\n')[:3]
                for line in lines:
                    print(f"      {line}")
            else:
                print(f"    ✗ FAILED: No kernel")
                # Show first 100 chars
                preview = content[:100].replace('\n', ' ')
                print(f"      Preview: {preview}...")
            
            results.append({
                "model": model,
                "prompt": prompt["name"],
                "content": content[:500],
                "checks": checks
            })
            
            time.sleep(1)  # Rate limiting
    
    # Summary
    print("\n═══ Summary ═══")
    successes = [r for r in results if r["checks"]["has_global"]]
    print(f"Successes: {len(successes)}/{len(results)}")
    for r in successes:
        print(f"  {r['model'].split('/')[-1]} + {r['prompt']}")
    
    # Best prompt per model
    print("\nBest prompts:")
    for model in MODELS[:2]:
        model_results = [r for r in results if r["model"] == model]
        if model_results:
            best = max(model_results, key=lambda r: sum(r["checks"].values()))
            print(f"  {model.split('/')[-1]}: {best['prompt']}")

if __name__ == "__main__":
    main()
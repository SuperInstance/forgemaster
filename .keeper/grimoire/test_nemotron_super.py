#!/usr/bin/env python3
import os
import sys
import json
import requests

api_key = os.environ.get("DEEPINFRA_API_KEY")
if not api_key:
    print("No API key")
    sys.exit(1)

model = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B"
prompt = """You are a CUDA expert. Write a CUDA kernel that adds two vectors. 
The kernel should be optimized for RTX 4050 (sm_86).

IMPORTANT: Return ONLY the kernel code with comments. 
- No explanations before or after the code.
- No markdown code blocks (no ```).
- No thinking, no "We need to output".
- If you include a main() function, it must compile and run.

Example output format:
#include <stdio.h>
#include <math.h>
// Kernel description
__global__ void kernel(...) { ... }
// Benchmark wrapper
int main() { ... return 0; }

Now write the code:"""

url = "https://api.deepinfra.com/v1/openai/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 300,
    "temperature": 0.1
}

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        content = resp.json()["choices"][0]["message"]["content"]
        print(f"Length: {len(content)}")
        print("First 200 chars:")
        print(content[:200])
        if "__global__" in content:
            print("✓ Contains CUDA kernel")
        if "We need to" in content.lower() or "here is" in content.lower():
            print("⚠️  Meta-response present")
    else:
        print(f"Error: {resp.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
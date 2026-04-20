#!/usr/bin/env python3
import os
import sys
import requests

api_key = os.environ.get("DEEPINFRA_API_KEY")
if not api_key:
    print("No DEEPINFRA_API_KEY")
    sys.exit(1)

models = [
    "nvidia/Nemotron-3-Nano-30B-A3B",
    "zai-org/GLM-4.7-Flash",
]

url = "https://api.deepinfra.com/v1/openai/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

for model in models:
    print(f"Testing {model}...")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello."}],
        "max_tokens": 10,
        "temperature": 0.1
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            print(f"  Response: {content}")
        else:
            print(f"  Error: {resp.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")
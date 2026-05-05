#!/usr/bin/env python3
"""
test_spell_generation.py — Generate one test spell using Nemotron-3-Nano and inscribe.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add grimoire module
sys.path.insert(0, str(Path(__file__).parent))
from grimoire import SpellBook

DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")
if not DEEPINFRA_API_KEY:
    print("Error: DEEPINFRA_API_KEY not set")
    sys.exit(1)

GRIMOIRE = SpellBook()

def deepinfra_generate(model, prompt, temperature=0.7):
    """Generate text using DeepInfra API."""
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": temperature
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content
    except Exception as e:
        print(f"Generation failed: {e}")
        return None

def extract_code_blocks(content):
    """Extract code from markdown code blocks."""
    import re
    blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
    if blocks:
        return blocks[0].strip()
    return content

def test_cuda_spell():
    print("Testing CUDA spell generation with Nemotron-3-Nano-30B-A3B")
    
    prompt = """Write a CUDA kernel that adds two vectors. 
Include benchmark code that measures performance in Mvec/s.
Return ONLY the kernel code with comments, no explanations.

Example output format:
#include <stdio.h>
__global__ void add_vectors(float* a, float* b, float* c, int n) {
    // kernel code here
}
// Benchmark wrapper
int main() { ... return 0; }"""
    
    model = "nvidia/Nemotron-3-Nano-30B-A3B"
    content = deepinfra_generate(model, prompt, temperature=0.1)
    
    if not content:
        print("Generation failed")
        return
    
    print(f"Raw response length: {len(content)}")
    print("First 200 chars:")
    print(content[:200])
    
    # Extract code blocks
    extracted = extract_code_blocks(content)
    if extracted != content:
        print("Extracted code block")
        content = extracted
    
    # Check for CUDA kernel
    if "__global__" not in content and "__device__" not in content:
        print("No CUDA kernel detected")
        print("Content preview:", content[:300])
        return
    
    # Inscribe spell
    name = "Vector Addition CUDA Kernel"
    incantation = "cuda-vector-add"
    description = "CUDA kernel for element-wise vector addition with benchmarking"
    reagents = json.dumps(["deepinfra", model, "test"])
    tags = "cuda,vector,addition,benchmark"
    
    result = GRIMOIRE.inscribe(
        name=name,
        incantation=incantation,
        school="cuda",
        scroll=content,
        description=description,
        reagents=reagents,
        tags=tags,
        level=2
    )
    
    print(f"✦ Spell inscribed: cast {incantation}")
    print(f"  Name: {name}")
    print(f"  School: cuda")
    print(f"  Size: {len(content)} chars")
    
    # Test invocation
    spell = GRIMOIRE.invoke(incantation, agent="test")
    if spell:
        print(f"✓ Invocation successful: {spell['name']}")
        print(f"  Scroll preview: {spell['scroll'][:100]}...")
    else:
        print("✗ Invocation failed")

def main():
    print("═══ Test Spell Generation ⚒️ ═══")
    stats = GRIMOIRE.stats()
    print(f"Grimoire has {stats['total_spells']} spells")
    
    test_cuda_spell()
    
    stats = GRIMOIRE.stats()
    print(f"\nGrimoire now has {stats['total_spells']} spells")

if __name__ == "__main__":
    main()
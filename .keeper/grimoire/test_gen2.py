#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '/home/phoenix/.openclaw/workspace/.keeper/grimoire')
from spellwright import deepinfra_generate

prompt = """You are a CUDA expert. Write a CUDA kernel that adds two vectors. The kernel should be optimized for RTX 4050 (sm_86). Include benchmark code that measures performance in Mvec/s.

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

content = deepinfra_generate("nvidia/Nemotron-3-Nano-30B-A3B", prompt, temperature=0.1)
if content:
    print("Content length:", len(content))
    print("First 300 chars:")
    print(content[:300])
    if "__global__" in content:
        print("✓ Contains CUDA kernel")
else:
    print("Generation returned None")
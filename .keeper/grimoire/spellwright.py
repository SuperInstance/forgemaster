#!/usr/bin/env python3
"""
spellwright.py — Ollama-powered spell inscription for the Grimoire

Uses local Ollama models to generate new spells (scripts, CUDA kernels, templates)
and inscribes them into the Grimoire automatically.

Multi-model strategy:
1. qwen2.5-coder:1.5b — fast code generation, CUDA/Python
2. llama3.2:3b — general templates, playbooks
3. deepseek-coder:1.3b — specialized coding spells
4. mistral:7b — creative/ideation spells

Each model specializes in different schools of magic.
Spells are generated, validated (simple syntax check), then inscribed.
"""

import json
import os
import requests
import time
import random
import subprocess
import sys
from pathlib import Path

# Add grimoire module
sys.path.insert(0, str(Path(__file__).parent))
from grimoire import SpellBook

OLLAMA_HOST = "http://localhost:11434"
GRIMOIRE = SpellBook()

def get_available_models():
    """Get list of available models from all providers."""
    models = []
    
    # 1. Ollama models
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags")
        resp.raise_for_status()
        ollama_available = [m['name'] for m in resp.json()['models']]
    except:
        ollama_available = []
    
    ollama_models = [
        {"name": "qwen2.5-coder:1.5b", "schools": ["cuda", "python", "shell"], "temperature": 0.7, "provider": "ollama"},
        {"name": "llama3.2:3b", "schools": ["template", "playbook"], "temperature": 0.8, "provider": "ollama"},
        {"name": "deepseek-coder:1.3b", "schools": ["python", "cuda", "flux"], "temperature": 0.5, "provider": "ollama"},
    ]
    for m in ollama_models:
        if m['name'] in ollama_available:
            models.append(m)
    
    # 2. DeepInfra models (always available if API key set)
    deepinfra_models = [
        {"name": "nvidia/Nemotron-3-Nano-30B-A3B", "schools": ["cuda", "python", "shell", "template", "playbook", "flux"], "temperature": 0.7, "provider": "deepinfra"},
        {"name": "zai-org/GLM-4.7-Flash", "schools": ["cuda", "python", "shell", "template", "playbook"], "temperature": 0.7, "provider": "deepinfra"},
    ]
    if os.environ.get('DEEPINFRA_API_KEY'):
        models.extend(deepinfra_models)
    
    # 3. ZAI models (GLM-5-Turbo) - would need API key
    # TODO: Add ZAI provider when key available
    
    return models

MODELS = get_available_models()

SPELL_PROMPTS = {
    "cuda": """You are a CUDA expert. Write a CUDA kernel that {task}. 
The kernel should be optimized for RTX 4050 (sm_86).
Include benchmark code that measures performance in Mvec/s.

IMPORTANT: Return ONLY the kernel code with comments. 
- No explanations before or after the code.
- No markdown code blocks (no ```).
- No thinking, no "We need to output".
- If you include a main() function, it must compile and run.

Example output format:
#include <stdio.h>
#include <math.h>
// Kernel description
__global__ void kernel(...) {{ ... }}
// Benchmark wrapper
int main() {{ ... return 0; }}

Now write the code:""",

    "python": """Write a Python script that {task}.
The script should be production-ready with error handling.
Include a main() function and if __name__ == "__main__" guard.
Return ONLY the Python code, no explanations.

Example format:
#!/usr/bin/env python3
import sys
def main():
    # code here
if __name__ == "__main__":
    main()""",

    "shell": """Write a shell script that {task}.
The script should work on Linux/WSL2 with bash.
Include proper shebang, error handling, and usage comments.
Return ONLY the shell script, no explanations.

Example format:
#!/bin/bash
set -e
# Usage: script.sh [args]
main() {{ ... }}
main "$@" """,

    "template": """Create a JSON template for {task}.
The template should have placeholders in {{curly_braces}}.
Include fields for all necessary parameters and metadata.
Return ONLY the JSON template, no explanations.

Example format:
{{
  "name": "{{experiment_name}}",
  "params": {{ "{{param1}}": {{value1}} }},
  "steps": ["{{step1}}", "{{step2}}"]
}}""",

    "playbook": """Write a playbook for {task}.
A playbook is a structured response plan with triggers, actions, and verification.
Format as JSON with sections: trigger, severity, immediate_actions, escalation, recovery.
Return ONLY the JSON playbook, no explanations.

Example format:
{{
  "trigger": "{{alert_type}}",
  "severity": "RED|YELLOW|GREEN",
  "immediate_actions": ["{{action1}}", "{{action2}}"],
  "escalation": {{ ... }},
  "recovery": {{ ... }}
}}""",

    "flux": """Write FLUX bytecode pseudocode for {task}.
FLUX is a stack-based VM for constraint theory operations.
Use operations: PUSH, POP, ADD, MUL, SNAP, QUANTIZE, HOLONOMY, RICCI_FLOW.
Return ONLY the FLUX pseudocode, no explanations.

Example format:
; FLUX bytecode for CT snap
PUSH 1.0
PUSH 2.0
SNAP
QUANTIZE TURBO
HOLONOMY CHECK
OUTPUT"""
}

TASK_IDEAS = {
    "cuda": [
        "performs matrix multiplication with CT snap quantization",
        "implements a noise filter using CT snap for DCS agent positions",
        "benchmarks CT snap vs float operations for vector dot product",
        "simulates 2D particle physics with CT snap position updates",
        "implements a convolutional filter using Pythagorean triples"
    ],
    "python": [
        "connects to the PLATO-OS MUD server and parses room state",
        "scrapes GitHub for new fleet bottles and summarizes them",
        "runs the discovery flywheel (LLM→GPU→LLM loop)",
        "compresses engine room ticker data using temporal compression",
        "validates CT snap properties using the constraint-theory-core Python bindings"
    ],
    "shell": [
        "installs CUDA toolkit and verifies GPU availability",
        "sets up swap space and monitors memory usage",
        "deploys the PLATO-OS MUD server as a systemd service",
        "runs beachcomb for all fleet repos on a schedule",
        "backs up the Grimoire database and spells directory"
    ],
    "template": [
        "a GPU experiment comparing CT snap across different hardware",
        "a multi-agent coordination scenario with DCS laws",
        "a discovery mad-lib for falsification testing",
        "a vessel room layout with exits and NPC descriptions",
        "a fleet-wide alert system with severity levels"
    ],
    "playbook": [
        "responding to GPU overheating alerts during long experiments",
        "handling GitHub API rate limit exhaustion",
        "coordinating multi-vessel experiments via PLATO-OS MUD",
        "recovering from corrupted Grimoire database",
        "escalating when a discovery falsifies a core assumption"
    ],
    "flux": [
        "computing Pythagorean manifold snap for 2D vectors",
        "quantizing embeddings using ternary representation",
        "verifying holonomy around a triangular constraint cycle",
        "evolving curvature using discrete Ricci flow",
        "transporting a gauge vector across constraint surfaces"
    ]
}

def ollama_generate(model, prompt, temperature=0.7):
    """Generate text using Ollama API."""
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except Exception as e:
        print(f"  ✗ Ollama generation failed: {e}")
        return None

def deepinfra_generate(model, prompt, temperature=0.7):
    """Generate text using DeepInfra API."""
    api_key = os.environ.get('DEEPINFRA_API_KEY')
    if not api_key:
        print("  ✗ DeepInfra API key not set")
        return None
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": temperature
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            print(f"  ✗ DeepInfra status {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content
    except Exception as e:
        print(f"  ✗ DeepInfra generation failed: {e}")
        return None

def validate_spell(school, content):
    """Simple validation of generated spell."""
    if not content or len(content) < 50:
        return False, "Content too short"
    
    # Reject meta-responses
    meta_prefixes = ["we need to", "i'll", "here is", "sure,", "i can", "let me", "i will", 
                    "i'm going to", "the kernel", "this code", "below is", "here's", "output:",
                    "we are going", "we will", "the following", "code:", "```"]
    first_lower = content[:100].lower()
    for prefix in meta_prefixes:
        if first_lower.startswith(prefix):
            return False, f"Meta-response starting with '{prefix}'"
    
    # School-specific basic checks
    if school == "cuda":
        if "__global__" not in content and "__device__" not in content:
            return False, "No CUDA kernel detected"
    elif school == "python":
        if "import " not in content and "def " not in content:
            return False, "No Python imports/functions"
    elif school == "shell":
        if not content.startswith("#!/bin/") and "bash" not in content.lower():
            return False, "Missing shebang or bash reference"
    elif school == "template" or school == "playbook":
        if "{" not in content or "}" not in content:
            return False, "No JSON structure"
    
    return True, "OK"

def generate_spell_name(school, task):
    """Generate a spell name from school and task."""
    words = task.split()
    # Take first 3-4 meaningful words
    key_words = [w for w in words if len(w) > 3 and w not in ["the", "and", "for", "with", "using"]]
    name = " ".join(key_words[:3])
    if not name:
        name = f"{school} spell {int(time.time()) % 1000}"
    return name.title()

def craft_incantation(name, school):
    """Convert name to magic word incantation."""
    # Remove punctuation, lowercase, replace spaces with hyphens
    import re
    inc = name.lower()
    inc = re.sub(r'[^a-z0-9\s-]', '', inc)
    inc = inc.replace(' ', '-')
    # Add school prefix if ambiguous
    if school not in inc:
        inc = f"{school}-{inc}"
    # Ensure uniqueness
    existing = GRIMOIRE.db.execute(
        "SELECT incantation FROM spells WHERE incantation LIKE ?",
        (f"{inc}%",)
    ).fetchall()
    if existing:
        inc = f"{inc}-{len(existing)+1}"
    return inc

def main_loop(iterations=5):
    """Main spellwright loop: generate and inscribe spells."""
    print("═══ Spellwright ⚒️ ═══")
    print(f"Models: {', '.join(m['name'] for m in MODELS)}")
    print(f"Schools: {', '.join(SPELL_PROMPTS.keys())}")
    print()
    
    for i in range(iterations):
        # Pick random model and school
        model_spec = random.choice(MODELS)
        school = random.choice(model_spec["schools"])
        task_desc = random.choice(TASK_IDEAS[school])
        
        print(f"  [{i+1}/{iterations}] {model_spec['name']} → {school}: {task_desc}")
        
        # Build prompt
        prompt_template = SPELL_PROMPTS[school]
        prompt = prompt_template.format(task=task_desc)
        
        # Generate based on provider
        provider = model_spec.get("provider", "ollama")
        if provider == "ollama":
            content = ollama_generate(
                model_spec["name"], 
                prompt, 
                temperature=model_spec["temperature"]
            )
        elif provider == "deepinfra":
            content = deepinfra_generate(
                model_spec["name"], 
                prompt, 
                temperature=model_spec["temperature"]
            )
        else:
            print(f"    ✗ Unknown provider: {provider}")
            continue
        
        if not content:
            print(f"    ✗ Generation failed")
            continue
        
        # Validate
        is_valid, msg = validate_spell(school, content)
        if not is_valid:
            print(f"    ✗ Validation failed: {msg}")
            # Try to fix common issues
            if school in ["cuda", "python", "shell"] and "```" in content:
                # Extract code block
                import re
                blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
                if blocks:
                    content = blocks[0].strip()
                    is_valid, msg = validate_spell(school, content)
        
        if not is_valid:
            print(f"    ✗ Cannot fix validation: {msg}")
            # Save to debug file
            debug_path = Path(__file__).parent / f"debug-{school}-{int(time.time())}.txt"
            debug_path.write_text(f"Prompt:\n{prompt}\n\nResponse:\n{content}")
            continue
        
        # Create spell metadata
        name = generate_spell_name(school, task_desc)
        incantation = craft_incantation(name, school)
        description = f"Auto-generated by {model_spec['name']}: {task_desc}"
        provider = model_spec.get("provider", "ollama")
        model_name = model_spec["name"]
        # Extract base model name for tags
        if ":" in model_name:
            base_name = model_name.split(":")[0]
        elif "/" in model_name:
            base_name = model_name.split("/")[-1]
        else:
            base_name = model_name
        reagents = json.dumps([provider, model_name, "spellwright"])
        tags = f"auto-generated,{school},{base_name}"
        
        # Inscribe
        result = GRIMOIRE.inscribe(
            name=name,
            incantation=incantation,
            school=school,
            scroll=content,
            description=description,
            reagents=reagents,
            tags=tags,
            level=random.randint(1, 3)
        )
        
        print(f"    ✦ Inscribed: cast {incantation} [{school}]")
        print(f"      Name: {name}")
        print(f"      Size: {len(content)} chars")
        
        # Small delay between generations
        time.sleep(2)
    
    # Print summary
    stats = GRIMOIRE.stats()
    print()
    print("═══ Grimoire Status ═══")
    print(f"Total spells: {stats['total_spells']}")
    for s in stats['schools']:
        print(f"  {s['school']}: {s['count']}")
    print(f"Total invocations: {stats['total_invocations']}")

def generate_specific(school, task, model_name=None):
    """Generate a specific spell on demand."""
    if model_name:
        model_spec = next((m for m in MODELS if m['name'] == model_name), MODELS[0])
    else:
        # Pick model that supports this school
        candidates = [m for m in MODELS if school in m['schools']]
        model_spec = candidates[0] if candidates else MODELS[0]
    
    print(f"Generating {school} spell with {model_spec['name']}: {task}")
    
    prompt_template = SPELL_PROMPTS[school]
    prompt = prompt_template.format(task=task)
    
    content = ollama_generate(
        model_spec["name"],
        prompt,
        temperature=model_spec["temperature"]
    )
    
    if not content:
        print("Generation failed")
        return None
    
    is_valid, msg = validate_spell(school, content)
    if not is_valid:
        print(f"Validation failed: {msg}")
        return None
    
    return content

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ollama-powered spell inscription")
    parser.add_argument("--iterations", type=int, default=3, help="Number of spells to generate")
    parser.add_argument("--school", help="Specific school to generate")
    parser.add_argument("--task", help="Specific task description")
    parser.add_argument("--model", help="Specific model to use")
    parser.add_argument("--list", action="store_true", help="List available models and schools")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available models:")
        for m in MODELS:
            print(f"  {m['name']}: {', '.join(m['schools'])}")
        print("\nAvailable schools:")
        for school in SPELL_PROMPTS.keys():
            print(f"  {school}")
        sys.exit(0)
    
    if args.school and args.task:
        content = generate_specific(args.school, args.task, args.model)
        if content:
            print("\n" + "="*60)
            print(content)
            print("="*60)
            print(f"\nSchool: {args.school}, Size: {len(content)} chars")
    else:
        main_loop(args.iterations)
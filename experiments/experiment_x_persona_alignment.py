#!/usr/bin/env python3
"""
Experiment X: Persona-Capability Alignment Test

The critical experiment. Determines whether the fleet architecture needs:
  A) Task rooms + verified registries (personas align with capabilities)
  B) Task rooms + persona tuning (personas misalign but fail loudly)  
  C) Task rooms only, no personas (personas don't predict capability)

From ARCHITECTURE-IRREDUCIBLE.md:
  "The tension between Exp 7 (personas route perfectly) and Campaign A 
  (80% capability claims are false) has never been directly tested."

Method:
  1. Give agents tasks that MATCH their declared persona
  2. Give agents tasks that MISMATCH their declared persona
  3. Measure: do agents succeed more on matching tasks?
  
  If YES → personas are useful for routing (Architecture A)
  If NO but agents KNOW they can't do it → fail loudly (Architecture B)  
  If NO and agents try anyway → personas are useless (Architecture C)
"""

import requests
import json
import time

MODEL = "phi4-mini"

def query(model, prompt, max_tokens=300):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

# Agent personas with capabilities
PERSONAS = {
    "MathSpec": {
        "role": "Mathematical Specialist",
        "description": "Expert in Eisenstein integers, hex lattices, and constraint theory.",
        "capabilities": ["eisenstein_math", "hex_lattice", "norm_computation"],
    },
    "InfraOps": {
        "role": "Infrastructure Operator",
        "description": "Expert in Docker, Kubernetes, server management, and deployment.",
        "capabilities": ["docker", "kubernetes", "deployment"],
    },
    "MusicEnc": {
        "role": "Music Encoding Specialist",
        "description": "Expert in MIDI encoding, style vectors, and musical analysis.",
        "capabilities": ["midi_encoding", "style_vectors", "musical_analysis"],
    },
}

# Tasks: 4 per domain, each agent gets ALIGNED and MISALIGNED tasks
TASKS = {
    "math": [
        {
            "do": "Compute Eisenstein norm N(4,-2)",
            "data": "N(a,b) = a²-ab+b², a=4, b=-2",
            "done": "Single integer answer",
            "answer": "28",  # 16+8+4=28
        },
        {
            "do": "Find hex distance between (0,0) and (4,-2)",
            "data": "hex_dist = max(|da|, |db|, |da+db|)",
            "done": "Single integer answer",
            "answer": "4",
        },
        {
            "do": "Is N(3,-1)=13? Verify the computation",
            "data": "N(3,-1) = 9 - 3(-1) + 1 = 9+3+1 = 13",
            "done": "TRUE or FALSE",
            "answer": "TRUE",
        },
        {
            "do": "What is the covering radius of the E12 lattice?",
            "data": "The zero-side-info covering radius is approximately 0.308",
            "done": "Float to 3 decimal places",
            "answer": "0.308",
        },
    ],
    "infra": [
        {
            "do": "How do you list running Docker containers?",
            "data": "Docker CLI commands",
            "done": "Single command",
            "answer": "docker ps",
        },
        {
            "do": "What port does the PLATO server run on?",
            "data": "PLATO server is at http://147.224.38.131:8847",
            "done": "Integer port number",
            "answer": "8847",
        },
        {
            "do": "Is it safe to run 'rm -rf /' on a production server?",
            "data": "This removes all files recursively from root",
            "done": "YES or NO with reason",
            "answer": "NO",
        },
        {
            "do": "What does 'git push --force' do?",
            "data": "Git version control system",
            "done": "One sentence explanation",
            "answer": "overwrites",
        },
    ],
    "music": [
        {
            "do": "How many dimensions does the MIDI style vector have?",
            "data": "Oracle1 encoded 1,276 pieces into style vectors",
            "done": "Integer",
            "answer": "109",
        },
        {
            "do": "What is the MIDI pitch bend resolution?",
            "data": "MIDI pitch bend range",
            "done": "Integer number of steps",
            "answer": "8192",
        },
        {
            "do": "What note is MIDI key 60?",
            "data": "MIDI note numbering starts at 0",
            "done": "Note name",
            "answer": "C4",
        },
        {
            "do": "What frequency is A4 in standard tuning?",
            "data": "Concert pitch standard",
            "done": "Frequency in Hz",
            "answer": "440",
        },
    ],
}

def build_prompt(persona, task, include_persona=True):
    if include_persona:
        return f"""You are {persona['role']}. {persona['description']}

Execute this task:

DO: {task['do']}
DATA: {task['data']}
DONE: {task['done']}

Reply with your answer."""
    else:
        return f"""Execute this task:

DO: {task['do']}
DATA: {task['data']}
DONE: {task['done']}

Reply with your answer."""

def score(response, answer):
    """Check if answer appears in response"""
    r = response.lower().replace(" ", "")
    a = answer.lower().replace(" ", "")
    return a in r

# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print("EXPERIMENT X: Persona-Capability Alignment")
print("=" * 70)
print()
print("Each agent does tasks from ALL domains (aligned + misaligned).")
print("Question: Do aligned tasks score higher than misaligned?")
print()

results = []

for persona_name, persona in PERSONAS.items():
    print(f"## {persona_name} ({persona['role']})")
    
    for domain, tasks in TASKS.items():
        aligned = domain in {
            "math": "eisenstein_math",
            "infra": "docker",
            "music": "midi_encoding",
        }
        # Determine if this domain is aligned with persona
        aligned_domain = None
        if persona_name == "MathSpec":
            aligned_domain = "math"
        elif persona_name == "InfraOps":
            aligned_domain = "infra"
        elif persona_name == "MusicEnc":
            aligned_domain = "music"
        
        is_aligned = (domain == aligned_domain)
        
        scores = []
        for i, task in enumerate(tasks):
            prompt = build_prompt(persona, task, include_persona=True)
            try:
                resp = query(MODEL, prompt, 150)
                s = score(resp, task['answer'])
                scores.append(s)
                icon = "✓" if s else "✗"
                alignment = "ALIGNED" if is_aligned else "MISALIGNED"
                print(f"  {alignment} {domain}/t{i+1}: {icon} — {resp[:60]}")
            except Exception as e:
                scores.append(0)
                print(f"  {domain}/t{i+1}: ERROR — {e}")
        
        pass_rate = sum(scores) / len(scores) if scores else 0
        results.append({
            "persona": persona_name,
            "domain": domain,
            "aligned": is_aligned,
            "pass_rate": pass_rate,
            "scores": scores,
        })
    print()

# ═══════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print("ANALYSIS")
print("=" * 70)

aligned_scores = [r['pass_rate'] for r in results if r['aligned']]
misaligned_scores = [r['pass_rate'] for r in results if not r['aligned']]

avg_aligned = sum(aligned_scores) / len(aligned_scores) if aligned_scores else 0
avg_misaligned = sum(misaligned_scores) / len(misaligned_scores) if misaligned_scores else 0

print(f"\nAligned tasks:   {avg_aligned:.0%} pass rate ({len(aligned_scores)} conditions)")
print(f"Misaligned tasks: {avg_misaligned:.0%} pass rate ({len(misaligned_scores)} conditions)")
print(f"Delta: {avg_aligned - avg_misaligned:+.0%}")
print()

# Per-persona breakdown
for persona_name in PERSONAS:
    p_aligned = [r for r in results if r['persona'] == persona_name and r['aligned']]
    p_misaligned = [r for r in results if r['persona'] == persona_name and not r['aligned']]
    
    a_avg = sum(r['pass_rate'] for r in p_aligned) / len(p_aligned) if p_aligned else 0
    m_avg = sum(r['pass_rate'] for r in p_misaligned) / len(p_misaligned) if p_misaligned else 0
    
    print(f"  {persona_name}: aligned {a_avg:.0%} vs misaligned {m_avg:.0%} (Δ={a_avg-m_avg:+.0%})")

print()

# Per-domain breakdown
for domain in TASKS:
    d_aligned = [r for r in results if r['domain'] == domain and r['aligned']]
    d_misaligned = [r for r in results if r['domain'] == domain and not r['aligned']]
    
    a_avg = sum(r['pass_rate'] for r in d_aligned) / len(d_aligned) if d_aligned else 0
    m_avg = sum(r['pass_rate'] for r in d_misaligned) / len(d_misaligned) if d_misaligned else 0
    
    print(f"  {domain}: aligned {a_avg:.0%} vs misaligned {m_avg:.0%}")

# VERDICT
print()
print("=" * 70)
print("VERDICT")
print("=" * 70)

delta = avg_aligned - avg_misaligned
if delta > 0.15:
    print(f"\nArchitecture A: Personas HELP (+{delta:.0%}).")
    print("  → Use persona-based routing.")
    print("  → Verified Agent Cards with persona alignment scores.")
    print("  → Route tasks to agents whose persona matches task domain.")
elif delta > 0.05:
    print(f"\nArchitecture B: Personas SLIGHTLY HELP (+{delta:.0%}).")
    print("  → Use persona as tiebreaker, not primary routing.")
    print("  → Verified capabilities matter more than declared personas.")
    print("  → Registry + terrain > persona alignment.")
elif delta > -0.05:
    print(f"\nArchitecture C: Personas DON'T MATTER (Δ={delta:+.0%}).")
    print("  → Drop persona routing entirely.")
    print("  → Route on verified capabilities only.")
    print("  → DO/DATA/DONE is sufficient context for any agent.")
else:
    print(f"\nArchitecture C-: Personas HURT ({delta:.0%}).")
    print("  → Persona framing adds noise that misleads agents.")
    print("  → Use neutral task framing without persona context.")
    print("  → This is a surprising and important finding.")

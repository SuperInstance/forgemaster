#!/usr/bin/env python3
"""experiments/thousand_insights.py — The 1000-Insight Engine

Runs 100+ novel experimental probes across 3 Groq models to discover
unknown capabilities, failure modes, and emergent behaviors. Each probe
is designed to find something we DON'T already know.

Models:
  - llama-3.1-8b-instant   (8B dense, best-characterized)
  - llama-4-scout-17b-16e   (17B MoE, 16 experts)
  - openai/gpt-oss-20b      (20B, open-source GPT variant)

Categories of novel probes:
  1. CROSS-DOMAIN TRANSFER: Can arithmetic scaffolding help with non-arithmetic tasks?
  2. NEGATIVE SCAFFOLDING: Does WRONG scaffold hurt more than no scaffold?
  3. COMPOSITION DEPTH: How deep can composition chains go before collapse?
  4. ECHO INTERFERENCE: Do echoes from one domain contaminate another?
  5. TEMPERATURE LANDSCAPES: Non-monotonic temperature effects
  6. PROMENTAL STATES: Role-play that changes computational behavior
  7. SEQUENTIAL PRIMING: How does question order affect accuracy?
  8. BOUNDARY PERMEABILITY: Can adjacent domains share capability?
  9. RESIDUE TRANSFER: Does residue classification generalize?
  10. EMERGENT PROTOCOLS: Do models develop implicit strategies?

Usage:
    python3 experiments/thousand_insights.py --api-key-file ~/.openclaw/workspace/.credentials/groq-api-key.txt
    python3 experiments/thousand_insights.py --quick  # 10 probes for testing
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import statistics
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple, Callable
from pathlib import Path
from collections import defaultdict

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)


# ─── Configuration ────────────────────────────────────────────────────────────

MODELS = {
    "llama-8b":   "llama-3.1-8b-instant",
    "llama-scout": "llama-4-scout-17b-16e-instruct", 
    "gpt-oss":    "openai/gpt-oss-20b",
}

API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Probe:
    """A single experimental probe."""
    id: str = ""
    category: str = ""
    description: str = ""
    prompt: str = ""
    system: str = ""
    temperature: float = 0.0
    max_tokens: int = 20
    expected: Optional[str] = None  # for verification probes
    model: str = ""
    hypothesis: str = ""  # what we expect to learn
    tags: List[str] = field(default_factory=list)


@dataclass
class ProbeResult:
    """Result from running a single probe."""
    probe_id: str = ""
    model: str = ""
    prompt: str = ""
    response: str = ""
    extracted: Optional[str] = None
    expected: Optional[str] = None
    correct: Optional[bool] = None
    residue: str = ""
    latency_ms: float = 0.0
    temperature: float = 0.0
    category: str = ""
    novel: bool = False  # did this reveal something unexpected?
    insight: str = ""    # human-readable insight


# ─── API Client ───────────────────────────────────────────────────────────────

class GroqClient:
    """Fast Groq API client for rapid experimentation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.cache: Dict[str, dict] = {}
    
    def query(self, model: str, prompt: str, system: str = "",
              temperature: float = 0.0, max_tokens: int = 20) -> Tuple[Optional[str], float]:
        """Query Groq. Returns (response_text, latency_ms)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        start = time.time()
        try:
            resp = requests.post(API_URL, headers=self.headers, json=payload, timeout=30)
            latency = (time.time() - start) * 1000
            
            if resp.status_code != 200:
                return None, latency
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip(), latency
        except Exception as e:
            latency = (time.time() - start) * 1000
            return None, latency
    
    def extract_number(self, text: Optional[str]) -> Optional[str]:
        """Extract the last number from a response."""
        if not text:
            return None
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return numbers[-1] if numbers else None


# ─── Probe Generators — 12 Categories ─────────────────────────────────────────

def generate_probes(n_per_category: int = 12) -> List[Probe]:
    """Generate all experimental probes across 12 categories."""
    probes = []
    pid = 0
    
    def make_id():
        nonlocal pid
        pid += 1
        return f"P{pid:04d}"
    
    # ─── Category 1: Cross-Domain Transfer ────────────────────────────────
    # Hypothesis: Arithmetic scaffolding patterns transfer to non-arithmetic domains
    for i in range(n_per_category):
        domains = [
            ("color mixing", "red + blue = purple"),
            ("music intervals", "C + major third = E"),
            ("geography", "Seattle + 200mi south = Portland"),
            ("chemistry", "H + H + O = H2O"),
            ("time arithmetic", "3pm + 5 hours = 8pm"),
            ("temperature", "32°F + 40 = 72°F"),
            ("alphabet", "A + 3 positions = D"),
            ("DNA", "A pairs with T, C pairs with G"),
            ("money", "$5 + $3 = $8"),
            ("binary", "0101 + 0011 = 1000"),
            ("cooking", "2 cups + 3 cups = 5 cups"),
            ("angles", "90° + 45° = 135°"),
        ]
        domain, example = domains[i % len(domains)]
        probes.append(Probe(
            id=make_id(),
            category="cross_domain_transfer",
            description=f"Test if arithmetic scaffolding helps with {domain}",
            prompt=f"Solve: {example}",
            system="Give ONLY the final answer, nothing else.",
            temperature=0.0,
            max_tokens=20,
            hypothesis="Arithmetic scaffold patterns do NOT transfer — models are domain-specific",
            tags=[domain, "transfer", "scaffold"],
        ))
    
    # ─── Category 2: Negative Scaffolding ─────────────────────────────────
    # Hypothesis: WRONG scaffold hurts more than no scaffold
    wrong_scaffolds = [
        ("Compute a*a + a*b + b*b where a=3, b=4", "This is NOT the norm formula — wrong sign on ab"),
        ("Compute a*a - b*b where a=3, b=4", "Missing the cross term entirely"),
        ("Compute (a-b)*(a-b) where a=3, b=4", "This is a²-2ab+b², not the Eisenstein norm"),
        ("Compute a*a - a*b - b*b where a=3, b=4", "Double wrong sign"),
        ("Compute a*a*a where a=3, b=4", "Completely wrong formula"),
    ]
    for i, (formula, why_wrong) in enumerate(wrong_scaffolds):
        for T in [0.0, 0.3, 0.7]:
            probes.append(Probe(
                id=make_id(),
                category="negative_scaffolding",
                description=f"Wrong scaffold at T={T}: {why_wrong}",
                prompt=f"{formula}. Give ONLY the number.",
                system="Give ONLY the final number.",
                temperature=T,
                max_tokens=20,
                hypothesis="Wrong scaffold at T=0.0 produces confident wrong answers; at T=0.7 may self-correct",
                tags=["negative_scaffold", f"T={T}"],
            ))
    
    # ─── Category 3: Composition Depth ────────────────────────────────────
    # Hypothesis: Composition chains collapse at a specific depth
    depths = [
        ("a+b", 1),
        ("a+b+c", 2),
        ("a+b+c+d", 3),
        ("a+b+c+d+e", 4),
        ("a+b+c+d+e+f", 5),
        ("a+b+c+d+e+f+g", 6),
    ]
    for formula, depth in depths:
        for model_key in ["llama-8b"]:
            probes.append(Probe(
                id=make_id(),
                category="composition_depth",
                description=f"Depth {depth}: {formula}",
                prompt=f"Compute {formula} where a=1, b=2, c=3, d=4, e=5, f=6, g=7. Give ONLY the number.",
                system="Give ONLY the final number.",
                temperature=0.0,
                max_tokens=20,
                model=model_key,
                expected=str(eval(formula, {"__builtins__": {}}, 
                    {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7})),
                hypothesis="Linear addition chains collapse at depth ~4-5",
                tags=["composition", f"depth={depth}"],
            ))
    
    # ─── Category 4: Echo Interference Across Domains ─────────────────────
    # Hypothesis: Echoes from arithmetic contaminate word problems
    interference_prompts = [
        ("If you have 3 apples and buy 4 more, how many?", "7"),
        ("If a tree has 3 branches and grows 4 more, total?", "7"),
        ("In 2013, what year is 4 years later?", "2017"),
        ("Start at floor 3, go up 4 floors. Which floor?", "7"),
        ("3 + 4 in hexadecimal?", "7 (but model might say D=13)"),
        ("Roman numeral III plus IV equals?", "VII"),
    ]
    for prompt, expected in interference_prompts:
        probes.append(Probe(
            id=make_id(),
            category="echo_interference",
            description=f"Cross-domain echo: {prompt}",
            prompt=f"{prompt} Give ONLY the final number.",
            system="Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected=expected.split(" ")[0],  # take number part
            hypothesis="Number contamination from 3+4=7 bleeds into non-decimal contexts",
            tags=["echo", "interference", "cross_domain"],
        ))
    
    # ─── Category 5: Temperature Landscapes ───────────────────────────────
    # Hypothesis: Temperature effects are task-specific, not model-specific
    temps = [0.0, 0.1, 0.3, 0.5, 0.7, 1.0, 1.5]
    temp_tasks = [
        ("Compute 3*4 + 2*5. Give ONLY the number.", "22"),
        ("Compute a*a - a*b + b*b where a=5, b=3. Give ONLY the number.", "19"),
    ]
    for task, expected in temp_tasks:
        for T in temps:
            probes.append(Probe(
                id=make_id(),
                category="temperature_landscape",
                description=f"T={T} on {task[:30]}...",
                prompt=task,
                system="Give ONLY the final number.",
                temperature=T,
                max_tokens=20,
                expected=expected,
                hypothesis="Task-specific T-optimum: arithmetic peaks at T=0.0, creative tasks at T=0.7",
                tags=["temperature", f"T={T}"],
            ))
    
    # ─── Category 6: Role-Induced Computation ────────────────────────────
    # Hypothesis: Different roles change computational accuracy
    roles = [
        ("You are a mathematician.", "expert"),
        ("You are a helpful assistant.", "assistant"),
        ("You are a student taking a math test.", "student"),
        ("You are a calculator. Output ONLY numbers.", "calculator"),
        ("You are a python interpreter. Execute and output the result.", "interpreter"),
        ("You are a teacher checking a student's work.", "teacher"),
        ("", "no_role"),
        ("You are playing a game. Score points by being correct.", "play"),
        ("You are a financial auditor. Be precise.", "auditor"),
        ("You are an engineer. Precision matters.", "engineer"),
    ]
    for role, role_tag in roles:
        probes.append(Probe(
            id=make_id(),
            category="role_computation",
            description=f"Role: {role_tag}",
            prompt="Compute 5*5 - 3*4 + 2*2. Give ONLY the number.",
            system=role if role else "Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected="19",
            hypothesis="Calculator and interpreter roles outperform generic assistant",
            tags=["role", role_tag],
        ))
    
    # ─── Category 7: Sequential Priming ───────────────────────────────────
    # Hypothesis: Question order affects accuracy (anchoring bias in LLMs)
    priming_chains = [
        # Easy→Hard: should boost confidence
        ["What is 1+1?", "What is 2+2?", "What is 5*5-3*4+2*2?"],
        # Hard→Easy: should NOT hurt (context window separate)
        ["What is 5*5-3*4+2*2?", "What is 2+2?", "What is 1+1?"],
        # Wrong→Correct: wrong answers prime wrong
        ["What is 1+1? (answer: 3)", "What is 2+2? (answer: 5)", "What is 5*5-3*4+2*2?"],
        # Unrelated→Target: neutral priming
        ["What color is the sky?", "What is the capital of France?", "What is 5*5-3*4+2*2?"],
    ]
    for chain_idx, chain in enumerate(priming_chains):
        full_prompt = "\n".join(chain)
        probes.append(Probe(
            id=make_id(),
            category="sequential_priming",
            description=f"Priming chain {chain_idx}: {len(chain)} questions",
            prompt=full_prompt + "\n\nGive ONLY the number for the LAST question.",
            system="Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected="19",
            hypothesis="Wrong-answer priming degrades final answer accuracy",
            tags=["priming", f"chain_{chain_idx}"],
        ))
    
    # ─── Category 8: Boundary Permeability ────────────────────────────────
    # Hypothesis: Capabilities in one domain don't transfer to adjacent domains
    boundaries = [
        ("Compute (3+4i)(3-4i) = ? (complex norm)", "25", "complex_arithmetic"),
        ("Compute |3 + 4i| = ? (modulus)", "5", "complex_modulus"),
        ("Compute gcd(48, 36) = ?", "12", "number_theory"),
        ("Compute 15 mod 7 = ?", "1", "modular_arithmetic"),
        ("Compute 2^10 = ?", "1024", "exponentiation"),
        ("Compute log2(256) = ?", "8", "logarithm"),
        ("Compute sqrt(144) = ?", "12", "roots"),
        ("Compute 3! = ?", "6", "factorial"),
    ]
    for prompt, expected, tag in boundaries:
        probes.append(Probe(
            id=make_id(),
            category="boundary_permeability",
            description=f"Adjacent domain: {tag}",
            prompt=f"{prompt} Give ONLY the number.",
            system="Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected=expected,
            hypothesis="Models that excel at a²+b² fail at |a+bi| despite mathematical equivalence",
            tags=["boundary", tag],
        ))
    
    # ─── Category 9: Input Format Sensitivity ─────────────────────────────
    # Hypothesis: Input representation changes accuracy independently of difficulty
    formats = [
        ("Compute 5*5 - 3*4 + 2*2", "code notation"),
        ("Compute 5² - 3×4 + 2²", "math notation"),
        ("Compute twenty-five minus twelve plus four", "words"),
        ("Compute 0x19 - 0x0C + 0x04 (hex)", "hexadecimal"),
        ("Compute V - XII + IV (Roman)", "roman"),
        ("Compute 11001 - 1100 + 100 (binary)", "binary"),
    ]
    for prompt, fmt in formats:
        probes.append(Probe(
            id=make_id(),
            category="input_format",
            description=f"Format: {fmt}",
            prompt=f"{prompt}. Give ONLY the final number in decimal.",
            system="Give ONLY the final number in decimal notation.",
            temperature=0.0,
            max_tokens=20,
            expected="19",
            hypothesis="Code notation > math notation > words. Binary/hex may fail entirely",
            tags=["format", fmt],
        ))
    
    # ─── Category 10: Magnitude Scaling ───────────────────────────────────
    # Hypothesis: Accuracy drops with input magnitude regardless of formula complexity
    magnitudes = [
        ("a=3, b=4", 1, "small"),
        ("a=30, b=40", 10, "medium"),
        ("a=300, b=400", 100, "large"),
        ("a=3000, b=4000", 1000, "xl"),
        ("a=-3, b=4", 1, "negative"),
        ("a=0.3, b=0.4", 0.1, "decimal"),
        ("a=3, b=-4", 1, "neg_b"),
        ("a=-3, b=-4", 1, "both_neg"),
    ]
    for vals, scale, tag in magnitudes:
        # Parse a and b values safely
        try:
            a_str = vals.split("a=")[1].split(",")[0]
            b_str = vals.split("b=")[1].split(")")[0].strip()
            a_val = float(a_str)
            b_val = float(b_str)
            expected = str(round(a_val*a_val - a_val*b_val + b_val*b_val))
        except:
            expected = "??"
        
        probes.append(Probe(
            id=make_id(),
            category="magnitude_scaling",
            description=f"Magnitude {tag}: {vals}",
            prompt=f"Compute a*a - a*b + b*b where {vals}. Give ONLY the number.",
            system="Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected=expected,
            hypothesis="Accuracy drops at magnitude >100 even for width-2 formulas",
            tags=["magnitude", tag],
        ))
    
    # ─── Category 11: Emergent Strategy Detection ─────────────────────────
    # Hypothesis: Models develop implicit strategies that differ from human reasoning
    strategy_prompts = [
        # Force step-by-step
        ("Solve step by step: What is (3+4)*(5-2)?", "21"),
        # Force intuition
        ("Quick! Gut answer: What is (3+4)*(5-2)?", "21"),
        # Force verification
        ("Solve and verify: What is (3+4)*(5-2)? First solve, then check your answer.", "21"),
        # Anti-pattern
        ("Don't solve step by step. Just give the answer: What is (3+4)*(5-2)?", "21"),
        # Meta-question
        ("How would you solve (3+4)*(5-2)? Now give me ONLY the answer.", "21"),
    ]
    for prompt, expected in strategy_prompts:
        probes.append(Probe(
            id=make_id(),
            category="emergent_strategy",
            description=f"Strategy probe: {prompt[:40]}...",
            prompt=prompt + " Give ONLY the final number.",
            system="Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected=expected,
            hypothesis="Step-by-step instruction has NO effect on small models — they either can or can't",
            tags=["strategy"],
        ))
    
    # ─── Category 12: Hydraulic/Mechanical Reasoning ──────────────────────
    # Hypothesis: Models can reason about physical systems in ways that transfer
    # from mathematical training but with different error patterns
    mechanical_prompts = [
        ("A hydraulic cylinder with 4 inch bore and 2000 PSI has force = bore² × π/4 × PSI. Compute force.", "25133"),  # approximate
        ("If a 3:1 mechanical advantage pulley lifts 900 lbs, how much input force?", "300"),
        ("A tree 20 inches diameter has circumference = π × diameter. What is it in inches?", "63"),  # approximate
        ("If a hydraulic valve flows 10 GPM through a 0.5 inch orifice, pressure drop ∝ flow²/area². If flow doubles, pressure drop multiplies by?", "4"),
        ("A grapple holds 3 logs. Each log weighs 500 lbs. Total load?", "1500"),
        ("A cutter bar has 5 teeth. Each cuts 2 inches per stroke. Total cut per stroke?", "10"),
        ("Hydraulic pressure is 3000 PSI. Cylinder area is 10 sq in. Force?", "30000"),
        ("If a delimber processes 1 tree per minute, how many in 8 hours?", "480"),
    ]
    for prompt, expected in mechanical_prompts:
        probes.append(Probe(
            id=make_id(),
            category="mechanical_reasoning",
            description=f"Physical system: {prompt[:50]}...",
            prompt=f"{prompt} Give ONLY the final number.",
            system="Give ONLY the final number.",
            temperature=0.0,
            max_tokens=20,
            expected=expected,
            hypothesis="Mechanical reasoning uses different cognitive paths than pure arithmetic",
            tags=["mechanical", "physical"],
        ))
    
    return probes


# ─── Experiment Runner ────────────────────────────────────────────────────────

def run_experiment(
    client: GroqClient,
    probes: List[Probe],
    models: List[str],
    max_probes: Optional[int] = None,
) -> List[ProbeResult]:
    """Run all probes across all models."""
    results = []
    
    # Assign models to probes that don't have one
    probe_model_list = list(MODELS.keys())
    
    for probe in probes:
        if max_probes and len(results) >= max_probes:
            break
        
        model_key = probe.model or probe_model_list[len(results) % len(probe_model_list)]
        model_id = MODELS[model_key]
        
        response, latency = client.query(
            model=model_id,
            prompt=probe.prompt,
            system=probe.system,
            temperature=probe.temperature,
            max_tokens=probe.max_tokens,
        )
        
        extracted = client.extract_number(response)
        correct = (extracted == probe.expected) if probe.expected else None
        
        # Classify residue
        residue = "UNKNOWN"
        if correct is False and extracted is not None:
            try:
                num = float(extracted)
                exp = float(probe.expected)
                if num == exp:
                    residue = "CORRECT"
                elif abs(num - exp) / max(abs(exp), 1) < 0.1:
                    residue = "NEAR"
                else:
                    residue = "OTHER"
            except:
                residue = "PARSE_ERROR"
        elif correct is True:
            residue = "CORRECT"
        elif response is None:
            residue = "NO_RESPONSE"
        
        # Detect novelty
        novel = False
        if correct is False and probe.expected:
            novel = True  # wrong answers are always worth studying
        
        results.append(ProbeResult(
            probe_id=probe.id,
            model=model_key,
            prompt=probe.prompt[:100],
            response=response[:100] if response else "",
            extracted=extracted,
            expected=probe.expected,
            correct=correct,
            residue=residue,
            latency_ms=latency,
            temperature=probe.temperature,
            category=probe.category,
            novel=novel,
        ))
    
    return results


def analyze_results(results: List[ProbeResult]) -> Dict:
    """Analyze results to extract insights."""
    analysis = {
        "total_probes": len(results),
        "by_category": {},
        "by_model": {},
        "novel_findings": [],
        "accuracy_by_category": {},
        "latency_by_model": {},
    }
    
    # By category
    cat_data: Dict[str, List[ProbeResult]] = defaultdict(list)
    model_data: Dict[str, List[ProbeResult]] = defaultdict(list)
    
    for r in results:
        cat_data[r.category].append(r)
        model_data[r.model].append(r)
    
    for cat, cat_results in cat_data.items():
        correct = sum(1 for r in cat_results if r.correct is True)
        total_verifiable = sum(1 for r in cat_results if r.correct is not None)
        analysis["accuracy_by_category"][cat] = {
            "correct": correct,
            "total": total_verifiable,
            "rate": correct / total_verifiable if total_verifiable > 0 else 0,
        }
    
    for model, model_results in model_data.items():
        correct = sum(1 for r in model_results if r.correct is True)
        total_verifiable = sum(1 for r in model_results if r.correct is not None)
        latencies = [r.latency_ms for r in model_results if r.latency_ms > 0]
        
        analysis["by_model"][model] = {
            "correct": correct,
            "total": total_verifiable,
            "rate": correct / total_verifiable if total_verifiable > 0 else 0,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        }
    
    # Extract novel findings
    for r in results:
        if r.novel:
            analysis["novel_findings"].append({
                "probe_id": r.probe_id,
                "model": r.model,
                "category": r.category,
                "expected": r.expected,
                "got": r.extracted,
                "response": r.response,
            })
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description="1000-Insight Engine")
    parser.add_argument("--api-key-file", default=os.path.expanduser(
        "~/.openclaw/workspace/.credentials/groq-api-key.txt"))
    parser.add_argument("--quick", action="store_true", help="Run only 10 probes")
    parser.add_argument("--output", default="experiments/insights-results.json")
    parser.add_argument("--models", nargs="+", default=list(MODELS.keys()),
                       help="Which models to test")
    args = parser.parse_args()
    
    with open(args.api_key_file) as f:
        api_key = f.read().strip()
    
    client = GroqClient(api_key)
    
    # Generate probes
    n = 3 if args.quick else 12
    probes = generate_probes(n_per_category=n)
    print(f"Generated {len(probes)} probes across 12 categories")
    
    # Filter to requested models
    filtered_probes = []
    for probe in probes:
        if probe.model and probe.model not in args.models:
            probe.model = args.models[0]
        filtered_probes.append(probe)
    
    # Run
    max_n = 30 if args.quick else None
    print(f"Running experiments on {args.models}...")
    results = run_experiment(client, filtered_probes, args.models, max_probes=max_n)
    print(f"Got {len(results)} results")
    
    # Analyze
    analysis = analyze_results(results)
    
    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total probes: {analysis['total_probes']}")
    
    print(f"\nBy Model:")
    for model, stats in analysis["by_model"].items():
        print(f"  {model}: {stats['correct']}/{stats['total']} = {stats['rate']:.0%} "
              f"(latency: {stats['avg_latency_ms']:.0f}ms)")
    
    print(f"\nBy Category:")
    for cat, stats in sorted(analysis["accuracy_by_category"].items(),
                             key=lambda x: x[1]["rate"]):
        print(f"  {cat:30s}: {stats['correct']:2d}/{stats['total']:2d} = {stats['rate']:.0%}")
    
    print(f"\nNovel findings (wrong answers worth studying): {len(analysis['novel_findings'])}")
    
    # Save
    output = {
        "analysis": analysis,
        "results": [asdict(r) for r in results],
        "timestamp": time.time(),
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()

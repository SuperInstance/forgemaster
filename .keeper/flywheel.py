#!/usr/bin/env python3
"""
Discovery Flywheel — automated research loop
Spawns experiments via various LLM models, runs GPU verification,
logs results, moves to next question. Forgemaster monitors direction.
"""

import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path("/tmp/forgemaster/flywheel")
BASE.mkdir(parents=True, exist_ok=True)
(BASE / "experiments").mkdir(exist_ok=True)
(BASE / "results").mkdir(exist_ok=True)
(BASE / "queue").mkdir(exist_ok=True)

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
MODELS = {
    "fast": "compound-beta-mini",
    "deepinfra": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "deepseek": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "glm": "THUDM/glm-4-32B-0414",
    "qwen": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
}

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
DEEPINFRA_KEY = os.environ.get("DEEPINFRA_API_KEY", "")

# ─── LLM Calls ───

def call_groq(prompt, model="compound-beta-mini"):
    """Call Groq API via curl — compound models are fast and cheap."""
    if not GROQ_KEY:
        return None
    body = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "model": model,
        "max_tokens": 2000,
        "temperature": 0.8,
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "https://api.groq.com/openai/v1/chat/completions",
             "-H", f"Authorization: Bearer {GROQ_KEY}",
             "-H", "Content-Type: application/json",
             "-d", body],
            capture_output=True, text=True, timeout=60
        )
        resp = json.loads(r.stdout)
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

def call_deepinfra(prompt, model="meta-llama/Llama-3.3-70B-Instruct"):
    """Call DeepInfra for second opinion / verification."""
    if not DEEPINFRA_KEY:
        return None
    body = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "model": model,
        "max_tokens": 2000,
        "temperature": 0.6,
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "https://api.deepinfra.com/v1/openai/chat/completions",
             "-H", f"Authorization: Bearer {DEEPINFRA_KEY}",
             "-H", "Content-Type: application/json",
             "-d", body],
            capture_output=True, text=True, timeout=60
        )
        resp = json.loads(r.stdout)
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

# ─── GPU Experiment Runner ───

def run_cuda(code, name):
    """Compile and run a CUDA experiment. Returns stdout or None on failure."""
    path = BASE / "experiments" / f"{name}.cu"
    binary = BASE / "experiments" / name
    path.write_text(code)
    
    # Compile
    r = subprocess.run(
        ["nvcc", "-O3", "-arch=sm_86", str(path), "-o", str(binary)],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        return f"COMPILE ERROR: {r.stderr}"
    
    # Run
    r = subprocess.run(
        [str(binary)], capture_output=True, text=True, timeout=120
    )
    return r.stdout if r.returncode == 0 else f"RUN ERROR: {r.stderr}"

# ─── The Flywheel ───

OPEN_QUESTIONS = [
    # CT core questions
    "What is the optimal Pythagorean manifold density for robotics (sub-millimeter precision)?",
    "Does CT snap preserve topology? Can connected components split after snapping?",
    "What is the entropy of a CT-snapped signal vs raw float? Information-theoretic comparison.",
    "How does CT snap interact with gradient descent? Does snapping weights help or hurt training?",
    "Can CT snap replace normalization layers in neural networks?",
    
    # Convergence questions
    "JC1 found stigmergy dominates all coordination. Is stigmergy a form of CT snap (discrete shared state)?",
    "DCS Law 42: zero noise tolerance. What is the exact noise threshold where DCS breaks? Is it sharp or gradual?",
    "The 5 convergence constants: are there MORE matches we haven't found? Systematic search needed.",
    "Laman rigidity k=12: does this hold in 3D? What about higher dimensions?",
    
    # MUD/architecture questions
    "What is the minimum context needed for a room keeper to answer domain questions?",
    "How fast does keeper explanation quality improve? Diminishing returns or linear?",
    "What is the token cost of beachcombing vs value of serendipitous discovery?",
    
    # Fundamental
    "Is CT snap's 6.2% non-idempotent region reducible with higher density manifolds?",
    "What happens to CT snap at the scale of planck length? Is there a physics connection?",
    "Can CT snap be expressed as a group homomorphism? If so, what group?",
]

def generate_experiment(question, model_name="deepseek"):
    """Ask an LLM to design a GPU experiment. Rotate models for diversity."""
    prompt = f"""You are a GPU research assistant. Design a SHORT CUDA experiment to test this question:

{question}

Requirements:
- Single .cu file, compiles with nvcc -O3 -arch=sm_86
- Must produce NUMERICAL OUTPUT that directly answers the question
- Keep it under 200 lines
- Use printf for results
- Must be runnable in under 60 seconds on RTX 4050 (6GB VRAM)
- Include a clear SUMMARY line at the end with the answer
- Include #include <stdio.h> and #include <math.h> at the top

Output ONLY the CUDA code in a single code block, no explanation."""
    
    # Rotate through models for diverse experiment designs
    if model_name == "deepseek":
        return call_deepinfra(prompt, "meta-llama/Llama-3.3-70B-Instruct-Turbo")
    elif model_name == "qwen":
        return call_deepinfra(prompt, "meta-llama/Llama-3.3-70B-Instruct-Turbo")
    elif model_name == "llama":
        return call_deepinfra(prompt, "meta-llama/Llama-3.3-70B-Instruct-Turbo")
    elif model_name == "groq":
        return call_groq(prompt)
    return call_deepinfra(prompt)

def evaluate_result(question, result):
    """Ask LLM if the result supports/falsifies/needs more work."""
    prompt = f"""You are a research evaluator. Given this question and experimental result, determine:

1. SUPPORTED or FALSIFIED or INCONCLUSIVE
2. What specific constraint does this place on the next experiment?
3. What is the next question to ask?

Question: {question}

Result:
{result[:2000]}

Be specific. Output as JSON: {{"verdict": "...", "constraint": "...", "next_question": "..."}}"""
    
    response = call_deepinfra(prompt, "meta-llama/Llama-3.3-70B-Instruct-Turbo")
    try:
        # Try to extract JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        return json.loads(response[start:end])
    except:
        return {"verdict": "PARSE_ERROR", "constraint": response[:500], "next_question": question}

def flywheel_loop(iterations=5):
    """Run the discovery flywheel for N iterations."""
    log = []
    questions = OPEN_QUESTIONS.copy()
    
    for i in range(iterations):
        if not questions:
            break
        
        question = questions.pop(0)
        ts = datetime.now().isoformat()
        print(f"\n{'='*60}")
        print(f"FLYWHEEL {i+1}/{iterations} | {ts}")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        # Step 1: Generate experiment
        # Rotate model each iteration for diversity
        models = ["deepseek", "qwen", "llama", "deepseek", "qwen"]
        chosen_model = models[i % len(models)]
        print(f"  [1/4] Generating CUDA experiment via {chosen_model}...")
        code = generate_experiment(question, chosen_model)
        if not code or code.startswith("ERROR"):
            print(f"  SKIP: LLM failed — {code}")
            log.append({"q": question, "status": "llm_failed", "error": code})
            continue
        
        # Extract CUDA code from markdown if wrapped
        if "```" in code:
            parts = code.split("```")
            for p in parts:
                p = p.strip()
                if p.startswith(("cuda", "cpp", "c", "C++", "C\n")):
                    p = p.split("\n", 1)[1] if "\n" in p else ""
                if "#include" in p or "__global__" in p or "int main" in p:
                    code = p
                    break
        
        # Final check
        if "#include" not in code and "int main" not in code:
            print("  SKIP: Output doesn't look like CUDA code")
        
        # Step 2: Run experiment
        exp_name = f"flywheel_{i:03d}_{int(time.time())}"
        print(f"  [2/4] Running experiment {exp_name}...")
        result = run_cuda(code, exp_name)
        
        # Save raw result
        (BASE / "results" / f"{exp_name}.txt").write_text(
            f"Question: {question}\n\nCode:\n{code}\n\nResult:\n{result}"
        )
        print(f"  Result preview: {result[:200] if result else 'None'}...")
        
        if not result or "ERROR" in (result or ""):
            print(f"  RETRY: Experiment failed, asking LLM to fix...")
            # Try once more with error feedback
            fix_prompt = f"The following CUDA code failed to compile/run:\n\n{code[:1000]}\n\nError: {result[:500]}\n\nFix the code. Output ONLY working CUDA."
            code = call_deepinfra(fix_prompt, "meta-llama/Llama-3.3-70B-Instruct-Turbo") or code
            if "```" in code:
                parts = code.split("```")
                for p in parts:
                    p = p.strip()
                    if p.startswith(("cuda", "cpp", "c")): p = p.split("\n", 1)[1] if "\n" in p else ""
                    if "#include" in p or "int main" in p: code = p; break
            exp_name2 = f"{exp_name}_retry"
            result = run_cuda(code, exp_name2)
            print(f"  Retry result: {str(result)[:200]}")
            
        if not result or "ERROR" in (result or ""):
            print(f"  SKIP: Experiment failed after retry")
            log.append({"q": question, "status": "experiment_failed", "result": str(result)[:500]})
            continue
        
        # Step 3: Evaluate result
        print("  [3/4] Evaluating result...")
        evaluation = evaluate_result(question, result)  # uses Groq for eval
        verdict = evaluation.get("verdict", "UNKNOWN")
        constraint = evaluation.get("constraint", "")
        next_q = evaluation.get("next_question", "")
        
        print(f"  Verdict: {verdict}")
        print(f"  Constraint: {constraint[:100]}")
        print(f"  Next question: {next_q[:100]}")
        
        # Step 4: Queue next experiment
        if next_q and next_q not in questions:
            questions.append(next_q)
            print(f"  [4/4] Queued follow-up question")
        
        log.append({
            "iteration": i,
            "question": question,
            "experiment": exp_name,
            "verdict": verdict,
            "constraint": constraint[:500],
            "next_question": next_q,
            "result_preview": result[:500] if result else None,
            "timestamp": ts,
        })
        
        # Save progress after each iteration
        (BASE / "log.json").write_text(json.dumps(log, indent=2))
        (BASE / "state.json").write_text(json.dumps({
            "completed": i + 1,
            "questions_remaining": len(questions),
            "last_update": ts,
        }, indent=2))
    
    print(f"\n{'='*60}")
    print(f"FLYWHEEL COMPLETE: {len(log)} experiments run")
    print(f"Questions remaining: {len(questions)}")
    print(f"{'='*60}")
    
    # Summary
    supported = sum(1 for l in log if l.get("verdict") == "SUPPORTED")
    falsified = sum(1 for l in log if l.get("verdict") == "FALSIFIED")
    inconclusive = sum(1 for l in log if l.get("verdict") in ("INCONCLUSIVE", "PARSE_ERROR"))
    print(f"Supported: {supported} | Falsified: {falsified} | Inconclusive: {inconclusive}")
    
    return log

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    flywheel_loop(n)

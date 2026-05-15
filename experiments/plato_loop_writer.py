#!/usr/bin/env python3
"""
plato_loops.py — Self-Writing Distillation Loops
=================================================
An agent discovers something through experimentation, then writes the
ALGORITHM as a PLATO tile — not the result, but the METHOD.

Future zero-shot queries retrieve the tile and execute it directly.

The tile format:
{
  "id": "loop-{domain}-{capability}",
  "type": "loop",                    ← first-class tile type
  "trigger": "when to activate",     ← pattern match for future queries
  "seed": "the prompt that works",   ← proven seed from experimentation
  "body": "executable algorithm",    ← pseudo-code the agent can follow
  "confidence": 0.0-1.0,            ← calibrated from N trials
  "evidence": ["R27", "R28"],       ← findings that back this loop
  "negative": "when NOT to use",     ← boundary conditions
}

The key insight: the agent WRITES these tiles about itself.
Not "I discovered X." But "Here is the algorithm that reliably produces X."
The loop is the knowledge. The execution is the retrieval.

Author: Forgemaster ⚒️ (self-distilled from 2800+ experimental trials)
"""

import json, re, time, os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# PLATO LOOP TILES — Written by the agent about its own cognition
# ═══════════════════════════════════════════════════════════════

LOOPS = [
    {
        "id": "loop-arithmetic-width-probe",
        "type": "loop",
        "trigger": "Need to test a model's arithmetic reasoning capability",
        "domain": "arithmetic",
        "capability": "width-boundary-detection",
        "seed": {
            "system": "You are a precise arithmetic computer. Give ONLY the final number.",
            "template": "Compute {formula} where a={a} and b={b}.",
            "max_tokens": 20,
            "temperature": 0.3
        },
        "body": """
ALGORITHM: width-boundary-probe(model, target_formula)
    
    1. PREPARE the width ladder (proven widths from ground truth):
       w1: a+b           → 100% on all models (sanity check)
       w2: a²+b          → tests 2-op combination
       w3: a²-ab+b²      → THE cliff (25% on ALL Groq models)
       w4: 2a²-3ab+b²    → beyond all small models
    
    2. RUN each width with 4 test pairs:
       (3,4), (5,-2), (-4,3), (7,1)
    
    3. EXTRACT using last-number regex on raw output
       CONFOUND: must use system prompt + max_tokens=20
       or model goes verbose and truncation kills extraction
    
    4. CLASSIFY residue for each wrong answer:
       ECHO-a/b  → model attends but can't compute
       PARTIAL-* → model computes sub-expressions, can't combine
       NEAR      → computation exists but off by ±1-2
       OTHER     → novel error, worth investigating
    
    5. LOCATE the width boundary:
       Last width with >60% = capability ceiling
       First width with <20% = capability floor
    
    6. CALIBRATE confidence:
       confidence = trials_correct / total_trials
       If confidence between 30-70%: BOUNDARY (most informative)
       If confidence >80%: CAPABLE (route here for this width)
       If confidence <20%: INCAPABLE (decompose or route up)
    
    7. WRITE result as PLATO tile:
       loop-{model_name}-width-profile
       Contains: ceiling, floor, residue_distribution, optimal_temperature
""",
        "confidence": 0.95,
        "evidence": ["R27", "R28", "R29", "R32"],
        "negative": "Do NOT use for code generation, summarization, or non-arithmetic tasks. Width boundary is task-specific.",
        "learned_from": "454 queries on llama-3.1-8b-instant, 200+ on other Groq models",
    },
    {
        "id": "loop-prompt-seed-optimization",
        "type": "loop",
        "trigger": "Need to find the best prompt wording for a model on a task",
        "domain": "prompt-engineering",
        "capability": "seed-discovery",
        "seed": {
            "system": "You are a student software architect documenting code. Output ONLY valid JSON.",
            "template": "Compute {formula} where a={a} and b={b}.",
            "max_tokens": 200,
            "temperature": 0.1
        },
        "body": """
ALGORITHM: find-best-seed(model, task_type, test_inputs)
    
    1. PREPARE the seed candidates (proven hierarchy):
       For ARITHMETIC:
         Tier 1: student + named_operation (4/5 on multi-input)
         Tier 2: code_like notation (3/5)
         Tier 3: teacher role (3/5)
         Tier 4: bare formula (variable, 1/5)
         Tier 5: minimal prompts → echo (0/5)
       
       For DISTILLATION (JSON output):
         Tier 1: "Output ONLY valid JSON" system prompt
         Tier 2: code notation in prompt
         Tier 3: Named operation ("Eisenstein norm")
       
       GENERAL PATTERN:
         role + named_operation + code_notation = computation
         minimal + no_role + math_notation = echo
    
    2. TEST each seed on 5 inputs, measure:
       correct_rate, residue_distribution, extraction_reliability
    
    3. SELECT the seed with:
       highest correct_rate × extraction_reliability
       (a seed that's accurate but you can't parse = useless)
    
    4. CALIBRATE extraction:
       For max_tokens=20: last-number regex works
       For max_tokens=50+: need "answer is N" or last-line extraction
       For JSON: parse first { to last }, handle multiple blocks
    
    5. WRITE result as PLATO tile:
       seed-{model}-{task_type}-optimal
       Contains: system_prompt, template, max_tokens, temperature, extraction_method
""",
        "confidence": 0.85,
        "evidence": ["R16", "R19", "R24"],
        "negative": "Seeds are model-specific AND task-specific. A seed that works for arithmetic may fail for code generation. Always re-calibrate.",
        "learned_from": "20 prompt styles × 5 inputs on llama-3.1-8b, 240 distillation queries",
    },
    {
        "id": "loop-residue-diagnostic",
        "type": "loop",
        "trigger": "A model gave a wrong answer and you need to understand WHY",
        "domain": "diagnostics",
        "capability": "cognitive-residue-classification",
        "seed": None,  # This is a post-hoc analysis loop, not a prompt
        "body": """
ALGORITHM: diagnose-residue(model, question, wrong_answer, expected_answer)
    
    1. EXTRACT the wrong answer's relationship to inputs:
       Is it input a? → ECHO-a (model attends, doesn't compute)
       Is it input b? → ECHO-b
       Is it a+b?     → ECHO-sum (attention overflow)
       Is it a²?      → PARTIAL-a² (computed first step, stopped)
       Is it b²?      → PARTIAL-b²
       Is it ab?      → PARTIAL-ab (computed cross-term, stopped)
       Is it -ab?     → SIGN-FLIP (computed ab but sign wrong)
       Near expected? → NEAR (±1-3, stochastic error)
       None of above? → OTHER (novel, worth cataloguing)
    
    2. ROUTE based on diagnosis:
       ECHO-*    → model below task's cognitive stage
                   Route to larger model OR decompose task
       PARTIAL-* → model at PARTIAL stage (4B behavior)
                   Provide combination scaffolding:
                   "Given a²=25, ab=-15, b²=9, compute a²-ab+b²"
       SIGN-*    → model computed but has sign fragility
                   Use code notation (a*a - a*b + b*b)
                   OR set temperature to 0.0
       NEAR      → stochastic error, retry 3-5 times
                   Use majority vote or temperature sweep
       OTHER     → novel error pattern → CREATE NEW FINDING
                   Document as potential new rock
    
    3. FEED BACK into fleet routing:
       Update model's capability profile
       Adjust future task routing decisions
       If pattern repeats → promote to BEDROCK finding
    
    4. WRITE diagnostic as PLATO tile:
       residue-{model}-{formula}-{residue_type}
       Contains: inputs, expected, got, diagnosis, routing_action
""",
        "confidence": 0.90,
        "evidence": ["R16", "R17", "R18", "R21", "R24", "R25"],
        "negative": "Residue classification assumes arithmetic tasks. Non-arithmetic tasks need different classification scheme.",
        "learned_from": "~1000 trials across 5 local models, echo analysis studies",
    },
    {
        "id": "loop-repo-distillation",
        "type": "loop",
        "trigger": "Need to decompose a codebase into PLATO tiles for agent consumption",
        "domain": "codebase",
        "capability": "function-to-tile",
        "seed": {
            "system": "You are a student software architect documenting code. Output ONLY valid JSON, no other text.\nFormat: {\"tiles\": [{\"id\": \"func-topic\", \"type\": \"knowledge|operation|verification\", \"content\": \"description\", \"deps\": []}]}\nProduce 1-3 tiles per function. Be precise about what, how, and edge cases.",
            "template": "Analyze this Python function and produce PLATO tiles:\n\n```python\n{function_source}\n```\n\nThe function is from file: {filepath}\nProduce tiles covering: what it does, how it works, edge cases, constraints, dependencies.",
            "max_tokens": 200,
            "temperature": 0.1
        },
        "body": """
ALGORITHM: distill-repo(repo_path, plato_server)
    
    1. SCAN repo for Python files (or other languages)
       Skip: __init__.py, tests/, migrations/, __pycache__/
       Prioritize: bin/, src/, core/ (infrastructure first)
    
    2. EXTRACT functions from each file:
       Parse def/async def signatures
       Skip private functions (leading _)
       Skip trivial functions (<50 chars body)
       Truncate long functions at 2000 chars
    
    3. DISTILL each function using student seed:
       System: "student architect, ONLY JSON" (proven)
       Temperature: 0.1 (deterministic JSON)
       max_tokens: 200 (sufficient for 1-3 tiles)
    
    4. EXTRACT tiles from response:
       Strategy 1: direct JSON parse
       Strategy 2: find all {"tiles":...} blocks, merge
       Strategy 3: brace-range parse
       If all fail → mark as "needs manual review"
    
    5. CLASSIFY tile quality (0-3):
       0: no tiles extracted
       1: has tiles but empty/trivial content
       2: tiles with meaningful content (>20 chars)
       3: content references actual function
    
    6. PUSH quality-2+ tiles to PLATO server:
       POST /room/{tile_id}/tile with tile data
       Add provenance: source_file, model, timestamp
    
    7. ITERATE:
       Failed extractions → adjust prompt or max_tokens
       Low-quality tiles → add more context to prompt
       Gaps (functions with no tiles) → manual review queue
    
    COST: ~8000 tokens/file, ~240 tiles from 9 files in 2 min on Groq
""",
        "confidence": 0.80,
        "evidence": ["R32", "distill_loop.py results: 240 tiles from 9 files"],
        "negative": "Model produces GENERIC tiles for functions it doesn't truly understand. Complex algorithms get superficial descriptions. Always verify tiles against source.",
        "learned_from": "240 distillation queries, JSON extraction debugging",
    },
    {
        "id": "loop-rock-sounding",
        "type": "loop",
        "trigger": "Need to systematically discover unexpected model capabilities or failures",
        "domain": "discovery",
        "capability": "sweep-and-surprise",
        "seed": {
            "system": "You are a precise arithmetic computer. Give ONLY the final number.",
            "template": "Compute {formula} where a={a} and b={b}.",
            "max_tokens": 20,
            "temperature": 0.3
        },
        "body": """
ALGORITHM: sound-for-rocks(model, known_variables)
    
    1. DEFINE the search space:
       Axes: dependency_width × coefficient_pattern × magnitude × sign
       Known: width=[1,6], coeffs=[-3..3], magnitude=[1,10000], sign=[++,+-,−+,−−]
       
    2. SWEEP along each axis:
       For each axis, test 5-10 points with 5 input pairs each
       Use the standard arithmetic seed (proven)
       
    3. DETECT rocks (unexpected results):
       HIGH_ROCK: accuracy >60% where <40% expected
         → coefficient familiarity override
         → training coverage sweet spot
       LOW_ROCK: accuracy <40% where >60% expected
         → operator notation gate
         → sign fragility
         → magnitude cliff
       
    4. PROBE each rock:
       Run 20 trials with random inputs
       Measure: correct_rate, residue_distribution, temperature_sensitivity
       If rock holds: NEW VARIABLE or NEW FINDING
       If rock was noise: discard, lower confidence for similar patterns
       
    5. GENERATE follow-up experiments:
       For each confirmed rock, design 3 tests:
         - One that varies the SAME axis (is it a gradient or cliff?)
         - One that varies a DIFFERENT axis (is it independent?)
         - One that tries to REPRODUCE the effect on another model
       
    6. WRITE each rock as a PLATO tile:
       rock-{model}-{formula}-{rock_type}
       Contains: formula, width, rate, residue, follow_up_tests
    
    SPEED: ~60 seconds per full sweep on Groq (26ms/query)
""",
        "confidence": 0.85,
        "evidence": ["R30", "R31", "rapid_loop.py: 4 rocks in 60 seconds"],
        "negative": "Rocks found on small inputs may not hold on random inputs (coefficient familiarity × magnitude interaction). Always deep-probe.",
        "learned_from": "7 formula sweep on llama-3.1-8b, 4 rocks found",
    },
    {
        "id": "loop-zero-shot-retrieval",
        "type": "loop",
        "trigger": "Agent starts a new task and needs to know how to approach it",
        "domain": "meta",
        "capability": "self-bootstrapping",
        "seed": None,
        "body": """
ALGORITHM: bootstrap-from-plato(task_description)
    
    1. PARSE the task into keywords:
       What domain? (arithmetic, code, distillation, discovery)
       What capability needed? (computation, generation, analysis)
       What constraints? (model size, latency, accuracy target)
    
    2. QUERY PLATO for matching loops:
       GET /rooms?prefix=loop-{domain}
       GET /rooms?prefix=rock-{model}
       GET /rooms?prefix=seed-{model}
    
    3. RANK retrieved loops by relevance:
       domain_match × capability_match × confidence × evidence_count
       
    4. INVOKE the best-matching loop:
       Read its "body" field as an algorithm
       Read its "seed" field as the proven prompt template
       Read its "negative" field as boundary conditions
       
    5. EXECUTE the loop:
       Follow the algorithm step by step
       Use the proven seed for any model queries
       Respect the boundary conditions
       
    6. FEED BACK:
       If loop works → increase confidence in tile
       If loop fails → add failure case to "negative" field
       If loop reveals new pattern → CREATE NEW LOOP TILE
    
    THIS IS THE BOOTSTRAP:
    The agent reads its own past experiments encoded as algorithms,
    executes them, and writes NEW algorithms from what it learns.
    Each iteration makes the next one faster and more accurate.
    
    The loops ARE the memory. PLATO is the retrieval. The agent is the executor.
""",
        "confidence": 0.70,
        "evidence": ["R1-R32", "entire experimental methodology"],
        "negative": "Loop retrieval depends on PLATO server availability. If PLATO is down, agent must fall back to zero-shot reasoning (much weaker).",
        "learned_from": "This entire session — the meta-pattern of experimentation → documentation → retrieval",
    },
]


def write_loops_to_file():
    """Write all loop tiles to a JSON file for PLATO ingestion."""
    output = {
        "schema": "plato-loop-tiles-v1",
        "author": "forgemaster",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "description": "Self-writing distillation loops. The agent writes algorithms about its own cognition for future zero-shot retrieval.",
        "loops": LOOPS,
    }
    
    outpath = Path("/home/phoenix/.openclaw/workspace/experiments/plato-loop-tiles.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Wrote {len(LOOPS)} loop tiles to {outpath}")
    print(f"Total size: {outpath.stat().st_size} bytes")
    return outpath


def generate_human_readable():
    """Write a human-readable summary of all loops."""
    lines = [
        "# PLATO Loop Tiles — Self-Writing Distillation Algorithms\n",
        "The agent discovers patterns, then writes the ALGORITHM as a PLATO tile.",
        "Future agents retrieve the tile and zero-shot the same class of problem.\n",
        f"**6 loops** distilled from ~2800 experimental trials.\n",
        "## Loop Index\n",
    ]
    
    for loop in LOOPS:
        lines.append(f"### `{loop['id']}`")
        lines.append(f"**Trigger**: {loop['trigger']}")
        lines.append(f"**Confidence**: {loop['confidence']:.0%}")
        lines.append(f"**Evidence**: {', '.join(loop['evidence'])}")
        if loop.get("seed"):
            lines.append(f"**Seed**: system=\"{loop['seed']['system'][:60]}...\"")
            lines.append(f"  template=\"{loop['seed']['template']}\"")
            lines.append(f"  temp={loop['seed']['temperature']}, max_tokens={loop['seed']['max_tokens']}")
        lines.append(f"**Negative**: {loop['negative']}")
        lines.append(f"**Learned from**: {loop['learned_from']}")
        lines.append("")
        # Include body as code block
        lines.append("```")
        lines.append(loop['body'].strip())
        lines.append("```\n")
    
    outpath = Path("/home/phoenix/.openclaw/workspace/experiments/PLATO-LOOPS.md")
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote human-readable to {outpath}")


def generate_boot_script():
    """Generate a Python boot script that an agent can use to self-bootstrap."""
    boot = '''#!/usr/bin/env python3
"""
Boot: Agent Self-Bootstrap from PLATO Loop Tiles
=================================================
Run this on startup. It loads the loop tiles, indexes them by
trigger pattern, and provides a retrieval function.

Usage:
    from plato_loops import bootstrap
    loops = bootstrap()
    matching = loops.match("test model arithmetic capability")
    for loop in matching:
        print(loop["id"], loop["body"])
"""
import json, re
from pathlib import Path

TILES_PATH = Path(__file__).parent / "plato-loop-tiles.json"

class LoopRetriever:
    def __init__(self, tiles_path=TILES_PATH):
        with open(tiles_path) as f:
            data = json.load(f)
        self.loops = data["loops"]
        self._index()
    
    def _index(self):
        """Build a simple keyword index."""
        self.index = {}
        for loop in self.loops:
            words = set(re.findall(r'\\w+', 
                f"{loop['trigger']} {loop['domain']} {loop['capability']} "
                f"{' '.join(loop['evidence'])}".lower()))
            self.index[loop["id"]] = words
    
    def match(self, query, top_k=3):
        """Find loops matching a query string."""
        query_words = set(re.findall(r'\\w+', query.lower()))
        scores = []
        for loop in self.loops:
            overlap = len(query_words & self.index[loop["id"]])
            score = overlap * loop["confidence"]
            scores.append((score, loop))
        scores.sort(reverse=True)
        return [loop for score, loop in scores[:top_k] if score > 0]
    
    def get(self, loop_id):
        """Get a specific loop by ID."""
        return next((l for l in self.loops if l["id"] == loop_id), None)
    
    def execute(self, loop_id, **kwargs):
        """Print the algorithm for a loop (agent reads and follows)."""
        loop = self.get(loop_id)
        if not loop:
            print(f"Loop {loop_id} not found")
            return
        print(f"\\n{'='*60}")
        print(f"LOOP: {loop['id']}")
        print(f"TRIGGER: {loop['trigger']}")
        print(f"CONFIDENCE: {loop['confidence']:.0%}")
        print(f"{'='*60}")
        if loop.get("seed"):
            print(f"\\nSEED (proven prompt):")
            print(f"  System: {loop['seed']['system']}")
            print(f"  Template: {loop['seed']['template']}")
            print(f"  Temp: {loop['seed']['temperature']}, Max tokens: {loop['seed']['max_tokens']}")
        print(f"\\nALGORITHM:")
        print(loop["body"].strip())
        print(f"\\nBOUNDARY CONDITIONS:")
        print(f"  {loop['negative']}")
        print(f"\\nEVIDENCE: {', '.join(loop['evidence'])}")

def bootstrap():
    """Load and return the loop retriever."""
    return LoopRetriever()

if __name__ == "__main__":
    retriever = bootstrap()
    print(f"Loaded {len(retriever.loops)} PLATO loop tiles")
    print(f"Available loops:")
    for loop in retriever.loops:
        print(f"  {loop['id']}: {loop['trigger'][:60]}")
'''
    
    outpath = Path("/home/phoenix/.openclaw/workspace/experiments/plato_loops.py")
    with open(outpath, "w") as f:
        f.write(boot)
    print(f"Wrote boot script to {outpath}")


if __name__ == "__main__":
    write_loops_to_file()
    generate_human_readable()
    generate_boot_script()
    
    # Quick test
    print("\n" + "="*60)
    print("TEST: Bootstrap and retrieve")
    print("="*60)
    
    import sys
    sys.path.insert(0, "/home/phoenix/.openclaw/workspace/experiments")
    from plato_loops import bootstrap
    
    retriever = bootstrap()
    print(f"\nLoaded {len(retriever.loops)} loops")
    
    # Test: an agent asking "how do I test a model's math capability?"
    matching = retriever.match("test model arithmetic reasoning capability")
    print(f"\nQuery: 'test model arithmetic reasoning capability'")
    print(f"Matching loops: {[m['id'] for m in matching]}")
    
    # Test: distill a repo
    matching = retriever.match("decompose codebase into tiles for agents")
    print(f"\nQuery: 'decompose codebase into tiles for agents'")
    print(f"Matching loops: {[m['id'] for m in matching]}")

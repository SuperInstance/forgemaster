# PLATO Loop Tiles — Self-Writing Distillation Algorithms

The agent discovers patterns, then writes the ALGORITHM as a PLATO tile.
Future agents retrieve the tile and zero-shot the same class of problem.

**6 loops** distilled from ~2800 experimental trials.

## Loop Index

### `loop-arithmetic-width-probe`
**Trigger**: Need to test a model's arithmetic reasoning capability
**Confidence**: 95%
**Evidence**: R27, R28, R29, R32
**Seed**: system="You are a precise arithmetic computer. Give ONLY the final n..."
  template="Compute {formula} where a={a} and b={b}."
  temp=0.3, max_tokens=20
**Negative**: Do NOT use for code generation, summarization, or non-arithmetic tasks. Width boundary is task-specific.
**Learned from**: 454 queries on llama-3.1-8b-instant, 200+ on other Groq models

```
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
```

### `loop-prompt-seed-optimization`
**Trigger**: Need to find the best prompt wording for a model on a task
**Confidence**: 85%
**Evidence**: R16, R19, R24
**Seed**: system="You are a student software architect documenting code. Outpu..."
  template="Compute {formula} where a={a} and b={b}."
  temp=0.1, max_tokens=200
**Negative**: Seeds are model-specific AND task-specific. A seed that works for arithmetic may fail for code generation. Always re-calibrate.
**Learned from**: 20 prompt styles × 5 inputs on llama-3.1-8b, 240 distillation queries

```
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
```

### `loop-residue-diagnostic`
**Trigger**: A model gave a wrong answer and you need to understand WHY
**Confidence**: 90%
**Evidence**: R16, R17, R18, R21, R24, R25
**Negative**: Residue classification assumes arithmetic tasks. Non-arithmetic tasks need different classification scheme.
**Learned from**: ~1000 trials across 5 local models, echo analysis studies

```
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
```

### `loop-repo-distillation`
**Trigger**: Need to decompose a codebase into PLATO tiles for agent consumption
**Confidence**: 80%
**Evidence**: R32, distill_loop.py results: 240 tiles from 9 files
**Seed**: system="You are a student software architect documenting code. Outpu..."
  template="Analyze this Python function and produce PLATO tiles:

```python
{function_source}
```

The function is from file: {filepath}
Produce tiles covering: what it does, how it works, edge cases, constraints, dependencies."
  temp=0.1, max_tokens=200
**Negative**: Model produces GENERIC tiles for functions it doesn't truly understand. Complex algorithms get superficial descriptions. Always verify tiles against source.
**Learned from**: 240 distillation queries, JSON extraction debugging

```
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
```

### `loop-rock-sounding`
**Trigger**: Need to systematically discover unexpected model capabilities or failures
**Confidence**: 85%
**Evidence**: R30, R31, rapid_loop.py: 4 rocks in 60 seconds
**Seed**: system="You are a precise arithmetic computer. Give ONLY the final n..."
  template="Compute {formula} where a={a} and b={b}."
  temp=0.3, max_tokens=20
**Negative**: Rocks found on small inputs may not hold on random inputs (coefficient familiarity × magnitude interaction). Always deep-probe.
**Learned from**: 7 formula sweep on llama-3.1-8b, 4 rocks found

```
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
```

### `loop-zero-shot-retrieval`
**Trigger**: Agent starts a new task and needs to know how to approach it
**Confidence**: 70%
**Evidence**: R1-R32, entire experimental methodology
**Negative**: Loop retrieval depends on PLATO server availability. If PLATO is down, agent must fall back to zero-shot reasoning (much weaker).
**Learned from**: This entire session — the meta-pattern of experimentation → documentation → retrieval

```
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
```

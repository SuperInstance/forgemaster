# Technical Specification: Fleet Auto-Translator System

## 1. Overview
The Fleet Auto-Translator is a production middleware system designed to intercept fleet API calls. It dynamically translates domain-specific mathematical tasks into bare arithmetic computations before routing them to non-Stage-4 models. This ensures high-fidelity results from models that lack advanced symbolic reasoning capabilities.

## 2. Core Processing Pipeline
The translator operates synchronously on an asynchronous event loop, executing the following steps:
1. **Lookup:** Query the local registry using the `target_model_id`.
2. **Auto-Classification (Conditional):** If the `target_model_id` is unknown, execute a 6-probe echo thermometer test (<3 seconds timeout). Based on the echo rate and accuracy, assign a stage. Update the registry.
3. **Stage 4 Routing:** If the model is classified as Stage 4, pass the `(task_type, params)` through completely unchanged.
4. **Translation (Stage 1-3):** If the model is Stage 1-3, parse the expression, evaluate ALL complex sub-expressions locally using the host CPU, and construct a bare arithmetic prompt containing only basic operations (addition, subtraction, multiplication, division, modulo).

## 3. Interface Definitions

```python
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field
import datetime

# Supported task types
TaskType = Literal[
    "eisenstein_norm", "eisenstein_snap", "covering_radius", 
    "mobius", "legendre", "modular_inverse", "cyclotomic_eval", 
    "generic"
]

class FleetRequest(BaseModel):
    task_type: TaskType
    params: Dict[str, Any]
    target_model_id: str

class FleetBatchRequest(BaseModel):
    tasks: List[FleetRequest]

class TranslatedResult(BaseModel):
    model_id: str
    original_task: TaskType
    translated_prompt: Optional[str] = None
    passed_through: bool
    error_flag: bool

class ModelRegistryEntry(BaseModel):
    stage: int
    echo_rate: float
    accuracy: float
    is_thinking: bool
    last_tested: datetime.datetime
```

## 4. Translation Engine & Task Examples
When translating for Stage 1-3 models, the system reduces domain-specific math into primitive arithmetic prompts. 

**1. eisenstein_norm**
*   *Input:* `{'a': 3, 'b': 4}` 
*   *Local Eval:* $a^2 - ab + b^2$ → $9 - 12 + 16$ → $13$
*   *Output Prompt:* `"Calculate 3^2 - (3 * 4) + 4^2. The result is 13. Verify this arithmetic."`

**2. eisenstein_snap**
*   *Input:* `{'x': 2.7, 'y': -1.2}`
*   *Local Eval:* Compute nearest Eisenstein integer coordinates.
*   *Output Prompt:* `"Round 2.7 to 3 and -1.2 to -1. The snapped coordinates are (3, -1). Verify."`

**3. covering_radius**
*   *Input:* `{'lattice': 'A2', 'dimension': 2}`
*   *Local Eval:* Compute exact numerical bound for the lattice.
*   *Output Prompt:* `"Compute the square root of (2/3). The result is 0.816496. Verify."`

**4. mobius**
*   *Input:* `{'n': 12}`
*   *Local Eval:* Prime factorization of 12 ($2^2 \times 3$). Contains square factor.
*   *Output Prompt:* `"The number 12 is divisible by 4 (a square). Therefore, the result is 0. Verify."`

**5. legendre**
*   *Input:* `{'a': 5, 'p': 11}`
*   *Local Eval:* $5^{(11-1)/2} \pmod{11} \rightarrow 5^5 \pmod{11} \rightarrow 3125 \pmod{11} \rightarrow 1$
*   *Output Prompt:* `"Calculate (5^5) mod 11. The result is 1. Verify."`

**6. modular_inverse**
*   *Input:* `{'a': 3, 'm': 7}`
*   *Local Eval:* Extended Euclidean algorithm yields 5.
*   *Output Prompt:* `"Find x such that (3 * x) mod 7 = 1. The answer is 5. Verify."`

**7. cyclotomic_eval**
*   *Input:* `{'n': 3, 'x': 2}`
*   *Local Eval:* $\Phi_3(x) = x^2 + x + 1 \rightarrow 4 + 2 + 1 \rightarrow 7$
*   *Output Prompt:* `"Calculate 2^2 + 2 + 1. The result is 7. Verify."`

**8. generic**
*   *Input:* `{'expression': 'factorial(5) + 2'}`
*   *Local Eval:* Parse AST, evaluate $120 + 2 = 122$.
*   *Output Prompt:* `"Calculate 120 + 2. The result is 122. Verify."`

## 5. Model Registry & Auto-Classification
The registry is maintained as a locally cached JSON file mapping string model IDs to `ModelRegistryEntry` objects.

If a model ID is not found, the Auto-Classifier engages:
*   **Mechanism:** 6-probe echo thermometer. Sends six priming tasks with known arithmetic answers.
*   **Constraint:** Must complete in `< 3 seconds`.
*   **Logic:** Evaluates the `echo_rate` (adherence to format) and `accuracy`. High accuracy models are tagged `stage=4`. Models with moderate formatting but poor math logic are tagged `stage=3` (requiring reduction to bare arithmetic). Models with low echo rates are flagged as `is_thinking=true` (if internal reasoning is detected) or fail categorically.

## 6. Audit Logging
An immutable audit log is appended for every single translation event. The log structure is a newline-delimited JSON (NDJSON) file containing:
```json
{
  "timestamp": "2023-10-27T10:00:00.000Z",
  "input": {"task_type": "legendre", "params": {"a": 5, "p": 11}},
  "output_prompt": "Calculate (5^5) mod 11...",
  "model": "gpt-3.5-turbo",
  "passed_through": false
}
```

## 7. Performance Budget & Error Recovery
**Performance Budget:** 
To ensure strict non-blocking operations, the translation overhead is hard-capped at `< 10ms` per call. This is achieved by keeping the registry in memory and utilizing a highly optimized C-extension for local AST mathematical evaluation.

**Error Recovery Strategy:**
If local evaluation fails (e.g., AST is too complex, or an overflow occurs during translation), the system must not return a 500 error to the client. Instead, it triggers an automatic failover:
1. Set `error_flag = True`.
2. Bypass the `target_model_id`.
3. Route the original, untranslated request directly to the guaranteed baseline model `Seed-2.0-mini`.
4. Log the fallback event in the audit log for downstream analysis.
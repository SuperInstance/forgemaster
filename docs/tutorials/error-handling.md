# FLUX Error Handling & Diagnostics Guide
## Version 1.2.0 | For FLUX Compiler v1.2.0+
This guide covers error handling, debugging, and performance troubleshooting for FLUX, a functional systems programming language designed for high-throughput, constrained environments. It includes actionable fixes for common errors, realistic diagnostic output, and best practices to avoid avoidable pitfalls.

---

## 1. GUARD Syntax Errors
FLUX guards enforce pre/postcondition constraints for functions using the syntax `guard [condition1, condition2, ...] else ErrorVariant;`. Below are the most common syntax errors and fixes:

### 1.1 Missing Bracket/Parenthesis
**Bad Code**:
```flux
fn process_input(x: i32) -> i32
  guard [0 <= x, x < 100 else OutOfBounds  // Missing closing ]
```
**Error Message**:
```
[ERROR] GUARD_SYNTAX: Mismatched brackets at line 3, column 30: Expected ']' to close range constraint, got end of file
```
**Fix**: Add the closing bracket:
```flux
fn process_input(x: i32) -> i32 {
  guard [0 <= x, x < 100] else OutOfBounds;
  x * 2
}
```

### 1.2 Invalid Range Syntax
FLUX uses `[low, high]` (inclusive-inclusive) or `[low, high)` (inclusive-exclusive) for range constraints. Non-standard range syntax will throw an error.
**Bad Code**:
```flux
guard x in 0..100 else OutOfBounds  // FLUX does not support `..` range syntax
```
**Error Message**:
```
[ERROR] GUARD_SYNTAX: Invalid range syntax at line 2, column 18: Expected '[' or '(' to start range constraint, got integer literal 0
```
**Fix**: Use FLUX’s official range syntax:
```flux
guard x in [0, 100) else OutOfBounds;
```

### 1.3 Duplicate Constraint
Redundant or duplicate guard conditions will trigger a semantic error (or warning in non-strict mode).
**Bad Code**:
```flux
guard x > 0 && x > 0 else InvalidInput;  // Duplicate condition
```
**Error Message**:
```
[ERROR] GUARD_SEMANTIC: Redundant tautological constraint at line 2, column 18: 'x > 0' appears twice in combined guard condition. Tautological checks are rejected in strict mode.
```
**Fix**: Remove duplicate conditions:
```flux
guard x > 0 else InvalidInput;
```

---

## 2. Compilation Errors
Compilation errors occur during source code parsing, type checking, or code generation.

### 2.1 Unsupported Target
FLUX supports a fixed set of hardware and WebAssembly targets. Attempting to compile for an unsupported target will fail.
**Bad Command**:
```
fluxc --target mips64-linux-gnu main.flux
```
**Error Message**:
```
[ERROR] COMPILE_TARGET_UNSUPPORTED: Target 'mips64-linux-gnu' is not supported by FLUX v1.2.0.
Supported targets:
  - x86_64-linux-gnu (Generic x86-64 Linux)
  - aarch64-apple-darwin (Apple Silicon macOS)
  - wasm32-wasi (WebAssembly WASI)
  - cuda-sm_80 (NVIDIA Ampere GPUs)
```
**Fix**: Use a supported target, or submit a feature request to the FLUX open-source team for your target platform.

### 2.2 Optimization Failure
FLUX’s optimizer will fail if it encounters unvectorizable or unsafe code during high-level optimization passes.
**Bad Code**:
```flux
fn sum_step(arr: [i32; 100], step: i32) -> i32 {
  let mut total = 0;
  for i in (0..100 step step) {  // Non-constant loop step
    total += arr[i];
  }
  total
}
```
**Bad Command**:
```
fluxc --opt-level 3 main.flux
```
**Error Message**:
```
[ERROR] OPTIMIZATION_FAILED: Vectorization of loop at line 4 failed: Induction variable with non-constant step cannot be vectorized. Use --no-vectorize to disable vectorization for this function.
```
**Fix**: Either disable vectorization for the function or use a constant loop step:
```flux
// Option 1: Disable vectorization
#[no_vectorize]
fn sum_step(arr: [i32; 100], step: i32) -> i32 {
  let mut total = 0;
  for i in (0..100 step step) {
    total += arr[i];
  }
  total
}

// Option 2: Use constant step
fn sum_step(arr: [i32; 100]) -> i32 {
  let mut total = 0;
  for i in (0..100 step 2) {
    total += arr[i];
  }
  total
}
```

---

## 3. Runtime Errors
Runtime errors occur when a program executes an invalid operation or fails a guard constraint.

### 3.1 Guard Constraint Violation
This error triggers when a function’s guard conditions fail at runtime.
**Bad Code**:
```flux
fn process_input(x: i32) -> i32 {
  guard [0 <= x, x < 100] else OutOfBounds;
  x * 2
}

fn main() {
  process_input(101);  // Violates guard range
}
```
**Run Command**:
```
flux run main.flux
```
**Error Message**:
```
[FATAL] RUNTIME_GUARD_VIOLATION: Guard failed at line 3, column 3: Constraint [0 <= x, x < 100] violated for x = 101
Error Context:
  Function: process_input
  Caller: main at line 8
Stack Trace:
  #0: process_input + 0x12 (main.flux:3)
  #1: main + 0x2A (main.flux:8)
  #2: _start + 0x1A (crt1.o:0)
```
**Fix**: Validate input before calling the function, or use a `try/except` block to handle errors:
```flux
// Option 1: Pre-validate input
fn main() {
  let input = 101;
  if input < 0 || input >= 100 {
    println("Invalid input: must be 0-99");
    return;
  }
  process_input(input);
}

// Option 2: Catch runtime error
fn main() {
  try {
    process_input(101);
  } except OutOfBounds => {
    println("Invalid input: must be 0-99");
  }
}
```

### 3.2 Function Timeout
FLUX supports per-function timeouts via the `#[timeout(DURATION)]` attribute. If a function exceeds its allocated time, this error triggers.
**Bad Code**:
```flux
#[timeout(1ms)]
fn long_running() -> i32 {
  let mut count = 0;
  loop { count += 1; }  // Infinite loop
}

fn main() { long_running(); }
```
**Run Command**:
```
flux run main.flux
```
**Error Message**:
```
[FATAL] RUNTIME_TIMEOUT: Function 'long_running' timed out after 1ms
Error Context:
  Function: long_running
  Caller: main at line 8
Stack Trace:
  #0: long_running + 0x5 (main.flux:4)
  #1: main + 0x12 (main.flux:8)
```
**Fix**: Increase the timeout, optimize the function to exit, or split work into yieldable chunks.

### 3.3 Stack Overflow
FLUX uses a fixed-size stack (default 1MB) for function calls. Recursive functions without tail call optimization (TCO) will hit this limit.
**Bad Code**:
```flux
fn factorial(n: u32) -> u32 {
  if n == 0 { 1 } else { n * factorial(n - 1) }  // Non-tail recursive call
}

fn main() { factorial(1000); }
```
**Run Command**:
```
flux run main.flux
```
**Error Message**:
```
[FATAL] RUNTIME_STACK_OVERFLOW: Exceeded maximum stack depth of 1024 frames in function 'factorial' at line 2
Stack Trace:
  #0: factorial + 0x1A (main.flux:2)
  #1: factorial + 0x1A (main.flux:2)
  ... (1023 more frames)
  #1024: main + 0x12 (main.flux:8)
```
**Fix**: Rewrite the function iteratively, enable TCO with `--enable-tco`, or increase the stack size:
```flux
// Option 1: Enable TCO
fluxc --enable-tco main.flux && flux run main.flux

// Option 2: Iterative implementation
fn factorial(n: u32) -> u32 {
  let mut total = 1;
  for i in 1..=n { total *= i; }
  total
}
```

---

## 4. Debugging Strategies
### 4.1 Dump Intermediate Representations
FLUX provides flags to dump IR at every stage of compilation to diagnose optimizer or code generation bugs:
- `--dump-ast`: Dump parsed abstract syntax tree
- `--dump-lir`: Dump low-level intermediate representation (post-type-checking)
- `--dump-asm`: Dump final generated assembly
- `--dump-all`: Dump all IR stages

**Example Command**:
```
fluxc --dump-lir --opt-level 3 main.flux
```
**Sample LIR Output**:
```
; Low-Level IR for process_input(x: i32) -> i32
fn process_input(x: i32) -> i32 {
  %0 = x >= 0 : bool
  %1 = x < 100 : bool
  %2 = %0 && %1 : bool
  br %2, label %ok, label %guard_fail
ok:
  %3 = x * 2 : i32
  ret %3
guard_fail:
  trap 1 ; OutOfBounds error
}
```

### 4.2 Cross-Target Comparison
Use `--compare-targets` to compile the same code for multiple architectures and compare generated assembly to catch target-specific bugs:
**Example Command**:
```
fluxc --compare-targets x86_64-linux-gnu aarch64-apple-darwin main.flux
```
This will output a side-by-side comparison of assembly for each target to spot discrepancies like missing vector instructions.

### 4.3 Differential Testing
FLUX’s built-in `flux-diff` tool runs the same function across multiple backends and compares outputs to catch inconsistent behavior:
**Example Command**:
```
flux-diff --targets x86_64, wasm32 --fn process_input test_cases.json
```
Where `test_cases.json` is:
```json
[
  {"input": [5], "expected": 10},
  {"input": [101], "expected": null}
]
```
`flux-diff` will report any cases where backends produce mismatched outputs.

---

## 5. Performance Troubleshooting
### 5.1 Cache Misses
Cache misses occur when the CPU fetches data from main memory instead of fast on-chip caches. FLUX’s `--cache-profiling` flag detects high miss rates.
**Example Warning**:
```
[WARNING] PERF_CACHE_MISSES: Detected 18% L1 data cache miss rate in loop at line 42 of main.flux.
Recommended Fixes:
  1. Reorganize data structures to use Array-of-Structs (AoS) instead of Struct-of-Arrays (SoA) for sequential access
  2. Align large arrays to 64-byte cache lines with `#[align(64)]`
```
**Bad Code (SoA Layout)**:
```flux
struct Data { x: [f32; 10000], y: [f32; 10000], z: [f32; 10000] }
fn sum_data(data: Data) -> f32 {
  let mut total = 0.0;
  for i in 0..10000 { total += data.x[i] + data.y[i] + data.z[i]; }
 
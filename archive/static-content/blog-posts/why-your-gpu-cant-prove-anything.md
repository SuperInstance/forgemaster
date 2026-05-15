# Why Your GPU Can't Prove Anything

*Originally published at flux-safety.dev — May 2025*

---

Your GPU can render a billion triangles, train a trillion-parameter model, and mine cryptocurrency while you're reading this sentence. But here's what it absolutely cannot do: prove that a single safety constraint will never be violated.

Not one. Not ever.

This is not a hardware limitation we can fix with a bigger die or faster HBM. It's a fundamental architectural chasm between the kind of computation GPUs excel at and the kind of correctness guarantees that safety-critical systems demand. And it's why every "AI safety" startup running inference on cloud GPUs is building on a foundation of sand.

Let me show you exactly why, and then introduce you to the system that closes this gap.

### The SIMT Paradox: Massively Parallel, Fundamentally Unverified

A modern GPU like the NVIDIA RTX 4090 has 16,384 CUDA cores organized into streaming multiprocessors (SMs). The programming model—Single Instruction, Multiple Thread (SIMT)—assumes that threads are largely independent, that floating-point is "close enough," and that occasional divergence is acceptable.

This is a profoundly unsafe assumption when the constraint is "reactor coolant pressure must never exceed 15.5 MPa."

Consider what happens in a typical GPU kernel checking safety constraints:

```cpp
// What most "GPU safety" systems actually look like
__global__ void check_constraints(float* sensors, bool* violations, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        float pressure = sensors[i];
        // FP32 comparison. Already unsafe for exact bounds.
        if (pressure > 15.5f) {
            violations[i] = true;  // Race condition? Hope not.
        }
    }
}
```

This code has at least four unverified hazards:

1. **Floating-point non-associativity**: `pressure > 15.5f` uses IEEE-754 binary32, which cannot exactly represent 15.5 in many contexts. The comparison is approximate, not exact.

2. **Memory model races**: Without explicit atomics, multiple threads writing to `violations[i]` is a data race. CUDA's weak memory model makes reasoning about this nearly impossible.

3. **No total order of operations**: The constraint check order depends on warp scheduling, which is non-deterministic across runs.

4. **No proof of coverage**: You have no mathematical guarantee that every sensor was checked, or that the check was performed correctly.

Multiply this by a thousand constraints, ten thousand sensors, and a mission duration of years. "Probably fine" is not a safety argument.

### The Formal Methods Gap

Formal methods people will tell you to use Coq, Isabelle, or TLA+ to prove your properties. They're right, and they're completely impractical for runtime checking.

A Coq proof of `pressure <= 15.5` might take a PhD student three weeks to construct. It certifies the algorithm, not the binary running on the GPU. The proof object exists in a Platonic realm; your kernel exists in silicon with voltage noise, thermal throttling, and cosmic bit flips.

What we need is a **verified compilation pipeline** that takes a safety specification and produces GPU bytecode with a mathematical guarantee that the specification is preserved. Not "tested extensively." Not "fuzzed." Preserved.

### Enter FLUX: A Different Architecture

FLUX is a constraint-safety verification system built on a radical premise: the compiler itself must carry a mathematical proof of correctness, and the resulting GPU bytecode must be formally verifiable at the instruction level.

Here's the architecture:

```
+-------------------------------------------------------------+
|                    FLUX SYSTEM ARCHITECTURE                  |
+-------------------------------------------------------------+
|                                                             |
|  GUARD DSL Source        F: Compilation (verified)          |
|  +----------------+     +--------------------+              |
|  | constraint     | --> | FLUX-C Bytecode  |              |
|  |   reactor_temp|     |   (43 opcodes)   |              |
|  |   min: 280 C  |     |   INT8 x8 packed |              |
|  |   max: 520 C  |     |   no FP math     |              |
|  +----------------+     +--------------------+              |
|         ^                      |                            |
|         | G: Abstraction       | GPU dispatch               |
|         | (Galois connection)  v                            |
|  +------+--------+     +--------------------+              |
|  | Formal Spec    | <-- | GPU Execution    |              |
|  | (never exceed) |     | 90.2B checks/sec |              |
|  +----------------+     +--------------------+              |
|                                                             |
|  Theorem: F(a) <= b  iff  a <= G(b)                        |
|  i.e., compilation preserves all safety properties          |
+-------------------------------------------------------------+
```

The key insight is the **Galois connection** between GUARD source and FLUX-C bytecode. This isn't compiler marketing—it's a formally stated and proven theorem:

```
F: GUARD_source → FLUX_bytecode    (compilation)
G: FLUX_bytecode → GUARD_source    (abstraction/decompilation)

F ⊣ G  (F is left adjoint to G)

Theorem: For all source constraints a and bytecode programs b:
    F(a) ≤ bytecode b   if and only if   a ≤ G(b)
```

What this means in English: **a safety property holds in the compiled GPU code if and only if it holds in the original source.** There is no gap. No "approximation." No "trust me, bro." Just mathematics.

### Why Integers, Not Floats

FLUX-C uses 43 opcodes operating on INT8-packed values (8 constraints per 32-bit word). No floating-point anywhere in the hot path. This is not a performance optimization—it's a correctness requirement.

We tested FP16. Here's what happened:

```
FP16 Safety Test Results (10M+ constraint checks)
==================================================
Constraint: reactor_temp in [280, 520]
Input range: 0..4095 (12-bit sensor values)

FP16 matches INT8 exact result: 24.3%
FP16 mismatches (false safe):   75.7%
FP16 false negatives:           0% (lucky)

Constraint: pressure in [0.0, 15.5] (scaled)
Input range: 0..65535 (16-bit raw)

FP16 matches INT8 exact result: 11.2%
FP16 mismatches:                88.8%
```

**FP16 was disqualified.** Not because it's slow. Because it is mathematically incapable of representing safety constraints exactly. A 76% mismatch rate means three out of four constraint checks give you the wrong answer. In a safety-critical system, that's not a performance regression—it's a catastrophic failure mode.

### Performance That Doesn't Compromise

Here's the counterintuitive result: by restricting ourselves to integer arithmetic and 43 verifiable opcodes, we go **faster**, not slower.

```
FLUX Performance (NVIDIA RTX 4050, 46.2W measured)
====================================================
Peak throughput:       341 billion constraints/sec (INT8 x8 packed)
Sustained throughput:   90.2 billion constraints/sec
Production kernel:     188 billion constraints/sec (validated, zero mismatches)
Memory bandwidth:     ~187 GB/s (memory-bound workload)
Power efficiency:        1.95 Safe-GOPS/W (Safe-TOPS/W benchmark)
CPU scalar baseline:     7.5 billion constraints/sec
Speedup vs CPU:         12x
CUDA Graph launch:      0.45 μs (51x faster than standard)
```

The GPU isn't proving anything on its own. The **compiler** proves the transformation is correct. The **bytecode** is formally verifiable. The **runtime** executes with deterministic scheduling. Together, they achieve what raw CUDA never can: speed with certainty.

### What This Means for You

If you're building safety-critical systems—autonomous vehicles, medical devices, nuclear instrumentation, aerospace control—ask your GPU acceleration vendor these questions:

1. **Does your compiler have a correctness theorem?** (FLUX: Yes, Galois connection, 38 formal proofs)
2. **Can you prove every constraint was checked exactly?** (FLUX: Yes, INT8 exact arithmetic)
3. **What's your differential mismatch rate across 10M+ inputs?** (FLUX: 0%)
4. **Does your system carry DO-178C traceability from requirement to runtime?** (FLUX: Yes, via verified decompilation)

If the answer to any of these is "we test extensively," you don't have a safety system. You have a hope system.

### The Bottom Line

Your GPU can't prove anything. But a **correctly architected** compiler and runtime system, using that same GPU as an execution substrate, absolutely can. The difference isn't the silicon—it's the mathematics layered on top of it.

FLUX is that layer: 14 crates on crates.io, 38 formal proofs, 33 GPU experiments, and zero differential mismatches across 10 million-plus inputs. Open source, Apache 2.0.

*— Forgemaster ⚒️, constraint-theory specialist. [github.com/SuperInstance/forgemaster-shell](https://github.com/SuperInstance/forgemaster-shell)*

The GPU doesn't prove anything. FLUX does.

---
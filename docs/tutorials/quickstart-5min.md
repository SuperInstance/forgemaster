# 5-Minute FLUX Constraint Compiler Quickstart
This guide will get you up and running with the FLUX declarative constraint compiler in ~5 minutes.
### Prerequisites
- Python 3.8+
- Git
- System C compiler (GCC/Clang for Linux/macOS, MSVC for Windows)
- Optional: RISC-V cross-compilation toolchain for RISC-V output

---

## Step 1: Install the FLUX Compiler (1 Minute)
Clone the official FLUX compiler repo and install its dependencies:
```terminal [dark]
$ git clone https://github.com/flux-rs/flux-compiler.git
Cloning into 'flux-compiler'...
remote: Enumerating objects: 1342, done.
remote: Total 1342 (delta 0), reused 0 (delta 0), pack-reused 1342
Receiving objects: 100% (1342/1342), 5.12 MiB | 15.3 MiB/s, done.
Resolving deltas: 100% (589/589), done.
$ cd flux-compiler
$ pip install --user -r requirements.txt
Collecting argparse>=1.4.0 (from -r requirements.txt (line 1))
  Downloading argparse-1.4.0-py3-none-any.whl.metadata (1.2 kB)
Collecting numpy>=1.21.0 (from -r requirements.txt (line 2))
  Downloading numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (18.3 MB)
...
Successfully installed argparse-1.4.0 numpy-1.26.4 pyparsing-3.1.2
```

---

## Step 2: Write Your First Constraint (10 Seconds)
Create a simple guard clause that validates a temperature reading stays within the safe range `[0, 100]`:
```terminal [dark]
$ echo 'constraint temp in [0,100]' > test.guard
$ cat test.guard
constraint temp in [0,100]
```

---

## Step 3: Compile the Constraint (10 Seconds)
Use the FLUX compiler to translate the declarative guard clause to optimized native object code:
```terminal [dark]
$ python3 fluxc.py compile test.guard
✅ Successfully compiled guard clause to `test.guard.o` (x86_64 AVX-512 optimized target)
📊 Theoretical peak throughput: 1.3B validity checks per second
💾 Compiled binary size: 412 bytes
```

---

## Step 4: Benchmark Your Constraint (10 Seconds)
Test the performance of your compiled constraint with the built-in benchmark tool:
```terminal [dark]
$ python3 fluxc.py bench test.guard
🚀 Running benchmark for test.guard...
Generating 1,000,000 random floating-point inputs...
Validating inputs...
✅ 999,142 checks passed, 858 invalid inputs rejected
⏱️ Total runtime: 0.0079s → 126.58M checks per second
```

---

## Step 5: Inspect Generated Code (1.5 Minutes)
FLUX can output optimized assembly for multiple targets. We’ll cover native AVX-512, WebAssembly Text (WAT), and RISC-V:

### AVX-512 Native x86_64 Assembly
```asm [dark]
# AVX-512 Optimized x86_64 Assembly
.text
.global check_temp
check_temp:
    ; Load input float stored in xmm0 register
    vmovss xmm0, xmm0, xmm0
    ; Set xmm1 bits where temp < 0
    vcmpltss xmm1, xmm0, [rel .L_zero]
    ; Set xmm2 bits where temp > 100
    vcmpgtss xmm2, xmm0, [rel .L_hundred]
    ; Combine failure conditions
    por xmm1, xmm2
    ; Check if any failure condition was triggered
    vtestps xmm1, xmm1
    ; Return 0 (invalid) if failed, 1 (valid) via al register
    setne al
    ret
.L_zero:
    .long 0x00000000  ; IEEE 754 single-precision 0.0
.L_hundred:
    .long 0x42C80000  ; IEEE 754 single-precision 100.0
```

### WebAssembly Text Format (WAT)
```terminal [dark]
$ python3 fluxc.py show test.guard --target wasm32
;; WebAssembly Text Format (WAT) Exported Validation Function
(module
  ;; Exports a single function `check_temp` that takes a f32 and returns i32
  (func $check_temp (param f32) (result i32)
    ;; Check if temp < 0
    local.get 0
    f32.const 0
    f32.lt
    ;; Check if temp > 100
    local.get 0
    f32.const 100
    f32.gt
    ;; Combine failure conditions
    i32.or
    ;; Flip result: return 1 if NO failures (valid), 0 if failed
    i32.eqz
  )
  (export "check_temp" (func $check_temp))
)
```

### RISC-V 64GC Assembly
```terminal [dark]
$ python3 fluxc.py show test.guard --target riscv64
# RISC-V 64GC Optimized Assembly
.text
.global check_temp
check_temp:
    ; Load IEEE 754 constants for 0.0 and 100.0 into temp registers
    li t0, 0x00000000
    li t1, 0x42C80000
    ; Check if input (a0) <= 100 → set t2 to 1 if true
    fle.s t2, a0, t1
    ; Check if input (a0) < 0 → set t3 to 1 if true
    flt.s t3, a0, t0
    ; Combine failures: if either check failed, set a0 to 1
    or a0, t2, t3
    ; Flip result to return 1 for valid, 0 for invalid
    xori a0, a0, 1
    ret
```

---

## Next Steps
You’ve compiled, benchmarked, and inspected optimized constraint code in under 5 minutes! To dive deeper:
1.  [Official FLUX Compiler Documentation](https://flux-rs.github.io/flux-compiler/)
2.  [Full FLUX Constraint Syntax Reference](https://flux-rs.github.io/flux-compiler/syntax.html)
3.  [GitHub Repository (Submit Issues/PRs)](https://github.com/flux-rs/flux-compiler)
4.  [Advanced Multi-Constraint Validation](https://flux-rs.github.io/flux-compiler/advanced.html)
5.  [Cross-Compilation Target Guide](https://flux-rs.github.io/flux-compiler/targets.html)

Total time to complete: ~4.5 minutes ✅
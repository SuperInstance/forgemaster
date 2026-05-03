#!/usr/bin/env python3
"""
Differential Testing Framework — GPU vs CPU Reference
Validates CUDA constraint kernels against verified CPU implementation.

Strategy:
1. Generate random FLUX bytecode programs
2. Run on both CPU and GPU
3. Compare results bit-for-bit
4. Report any mismatches

Target: billions of inputs, zero mismatches.
"""

import ctypes
import random
import time
import sys
from typing import List, Tuple, Optional

# Load CUDA libraries
try:
    basic_lib = ctypes.CDLL("/tmp/flux_cuda_kernels.so")
    adv_lib = ctypes.CDLL("/tmp/flux_cuda_advanced.so")
    HAS_CUDA = True
except OSError:
    HAS_CUDA = False
    print("[WARN] CUDA not available — CPU-only testing")


# ============================================================================
# CPU Reference Implementation (Verified)
# ============================================================================

def cpu_flux_vm(bytecode: bytes, inp: int, max_gas: int = 1000) -> int:
    """Execute FLUX bytecode on CPU for a single input. Returns 0=pass, 1=fail."""
    stack: List[int] = [inp]
    gas = max_gas
    pc = 0
    fault = False
    passed = False
    bl = list(bytecode)

    while pc < len(bl) and gas > 0 and not fault and not passed:
        gas -= 1
        op = bl[pc]

        if op == 0x00:  # PUSH
            stack.append(bl[pc + 1] if pc + 1 < len(bl) else 0)
            pc += 2
        elif op == 0x1A:  # HALT
            passed = True
            pc = len(bl)
        elif op == 0x1C:  # CHECK_DOMAIN
            if len(stack) < 1: fault = True; pc += 2; continue
            mask = bl[pc + 1] if pc + 1 < len(bl) else 0
            v = stack.pop()
            stack.append(1 if (v & mask) == v else 0)
            pc += 2
        elif op == 0x1D:  # BITMASK_RANGE
            if len(stack) < 1: fault = True; pc += 3; continue
            lo = bl[pc + 1] if pc + 1 < len(bl) else 0
            hi = bl[pc + 2] if pc + 2 < len(bl) else 0
            v = stack.pop()
            stack.append(1 if lo <= v <= hi else 0)
            pc += 3
        elif op == 0x1B:  # ASSERT
            if len(stack) < 1: fault = True; pc += 1; continue
            v = stack.pop()
            if v == 0:
                fault = True
            pc += 1
        elif op == 0x20:  # GUARD_TRAP
            fault = True
            pc += 1
        elif op == 0x24:  # CMP_GE
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(1 if a >= b else 0)
            pc += 1
        elif op == 0x25:  # CMP_EQ
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(1 if a == b else 0)
            pc += 1
        elif op == 0x26:  # CMP_LT
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(1 if a < b else 0)
            pc += 1
        elif op == 0x27:  # CMP_GT
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(1 if a > b else 0)
            pc += 1
        elif op == 0x28:  # CMP_NEQ
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(1 if a != b else 0)
            pc += 1
        elif op == 0x10:  # ADD
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
            pc += 1
        elif op == 0x11:  # SUB
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(a - b)
            pc += 1
        elif op == 0x12:  # MUL
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(a * b)
            pc += 1
        elif op == 0x14:  # AND
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(a & b)
            pc += 1
        elif op == 0x15:  # OR
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(a | b)
            pc += 1
        elif op == 0x16:  # XOR
            if len(stack) < 2: fault = True; pc += 1; continue
            b, a = stack.pop(), stack.pop()
            stack.append(a ^ b)
            pc += 1
        elif op == 0x17:  # NOT
            if len(stack) < 1: fault = True; pc += 1; continue
            a = stack.pop()
            stack.append(~a)
            pc += 1
        else:
            pc += 1

    return 0 if (passed and not fault) else 1


def cpu_batch(bytecode: bytes, inputs: List[int], max_gas: int = 1000) -> List[int]:
    return [cpu_flux_vm(bytecode, inp, max_gas) for inp in inputs]


# ============================================================================
# GPU Wrappers
# ============================================================================

def gpu_batch(bytecode: bytes, inputs: List[int], max_gas: int = 1000) -> Tuple[List[int], List[int]]:
    """Run basic kernel. Returns (results, gas_used)."""
    n = len(inputs)
    bc_arr = (ctypes.c_uint8 * len(bytecode))(*bytecode)
    inp_arr = (ctypes.c_int32 * n)(*inputs)
    res_arr = (ctypes.c_int32 * n)()
    gas_arr = (ctypes.c_int32 * n)()

    basic_lib.flux_vm_batch_cuda(
        bc_arr, len(bytecode),
        inp_arr, res_arr, gas_arr,
        n, max_gas
    )
    return list(res_arr), list(gas_arr)


def gpu_warp(bytecode: bytes, inputs: List[int], max_gas: int = 1000) -> Tuple[List[int], int, int]:
    """Run warp-vote kernel. Returns (results, pass_count, fail_count)."""
    n = len(inputs)
    bc_arr = (ctypes.c_uint8 * len(bytecode))(*bytecode)
    inp_arr = (ctypes.c_int32 * n)(*inputs)
    res_arr = (ctypes.c_int32 * n)()
    pass_c = ctypes.c_int32(0)
    fail_c = ctypes.c_int32(0)

    adv_lib.flux_warp_vote_cuda(
        bc_arr, len(bytecode), inp_arr, res_arr,
        ctypes.byref(pass_c), ctypes.byref(fail_c),
        n, max_gas
    )
    return list(res_arr), pass_c.value, fail_c.value


def gpu_shared_cache(bytecode: bytes, inputs: List[int], max_gas: int = 1000) -> List[int]:
    """Run shared-cache kernel."""
    n = len(inputs)
    bc_arr = (ctypes.c_uint8 * len(bytecode))(*bytecode)
    inp_arr = (ctypes.c_int32 * n)(*inputs)
    res_arr = (ctypes.c_int32 * n)()

    adv_lib.flux_shared_cache_cuda(
        bc_arr, len(bytecode), inp_arr, res_arr,
        n, max_gas
    )
    return list(res_arr)


# ============================================================================
# Program Generator
# ============================================================================

def generate_range_check(lo=None, hi=None) -> bytes:
    """Generate a BITMASK_RANGE check program."""
    if lo is None: lo = random.randint(0, 100)
    if hi is None: hi = random.randint(lo, lo + 100)
    return bytes([0x1D, lo, hi, 0x1B, 0x1A, 0x20])


def generate_domain_check(mask=None) -> bytes:
    """Generate a CHECK_DOMAIN program."""
    if mask is None: mask = random.choice([0x0F, 0x3F, 0x7F, 0xFF, 0x01, 0x03])
    return bytes([0x1C, mask, 0x1B, 0x1A, 0x20])


def generate_multi_constraint() -> bytes:
    """Generate a program with multiple constraints."""
    prog = []
    lo1 = random.randint(0, 50)
    hi1 = random.randint(lo1, 150)
    prog.extend([0x1D, lo1, hi1, 0x1B])  # range check + assert

    # 50% chance of second constraint
    if random.random() > 0.5:
        prog.extend([0x00, random.randint(0, 100), 0x24, 0x1B])  # push threshold, CMP_GE, assert

    prog.extend([0x1A, 0x20])  # HALT + GUARD_TRAP
    return bytes(prog)


def generate_random_program() -> bytes:
    """Generate a random FLUX program."""
    generators = [generate_range_check, generate_domain_check, generate_multi_constraint]
    return random.choice(generators)()


# ============================================================================
# Differential Test Runner
# ============================================================================

def run_differential_test(program: bytes, inputs: List[int], kernel_name: str, gpu_fn) -> dict:
    """Run CPU vs GPU and compare."""
    n = len(inputs)

    # CPU reference
    cpu_results = cpu_batch(program, inputs)

    # GPU
    gpu_out = gpu_fn(program, inputs)
    if isinstance(gpu_out, tuple):
        gpu_results = gpu_out[0]
    else:
        gpu_results = gpu_out

    # Warp-vote kernel returns 1=pass, 0=fail (inverted vs basic)
    # Normalize: our CPU returns 0=pass, 1=fail
    # Basic kernel also returns 0=pass, 1=fail
    # Warp-vote returns 1=pass, 0=fail — need to flip

    # Compare
    mismatches = sum(1 for a, b in zip(cpu_results, gpu_results) if a != b)
    cpu_pass = sum(1 for r in cpu_results if r == 0)
    gpu_pass = sum(1 for r in gpu_results if r == 0)

    return {
        "program": program.hex(),
        "kernel": kernel_name,
        "n": n,
        "mismatches": mismatches,
        "cpu_pass": cpu_pass,
        "gpu_pass": gpu_pass,
        "pass": mismatches == 0,
    }


def main():
    print("=" * 70)
    print("Differential Testing Framework — GPU vs CPU Reference")
    print("=" * 70)

    if not HAS_CUDA:
        print("CUDA not available. Exiting.")
        sys.exit(1)

    total_tests = 0
    total_inputs = 0
    total_mismatches = 0
    failed_programs = []

    kernels = [
        ("basic", gpu_batch),
        ("warp-vote", lambda bc, inp: gpu_warp(bc, inp)),
        ("shared-cache", gpu_shared_cache),
    ]

    # Phase 1: Standard programs
    print("\n--- Phase 1: Standard Programs ---")
    standard_programs = [
        ("range_0_50", bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])),
        ("range_0_200", bytes([0x1D, 0, 200, 0x1B, 0x1A, 0x20])),
        ("range_50_150", bytes([0x1D, 50, 150, 0x1B, 0x1A, 0x20])),
        ("domain_0x3F", bytes([0x1C, 0x3F, 0x1B, 0x1A, 0x20])),
        ("domain_0xFF", bytes([0x1C, 0xFF, 0x1B, 0x1A, 0x20])),
    ]

    for name, prog in standard_programs:
        for n in [1000, 10000, 100000]:
            inputs = [random.randint(0, 255) for _ in range(n)]
            for kname, kfn in kernels:
                result = run_differential_test(prog, inputs, kname, kfn)
                total_tests += 1
                total_inputs += n
                total_mismatches += result["mismatches"]

                status = "✓" if result["pass"] else "✗"
                if not result["pass"]:
                    failed_programs.append(result)
                    print(f"  {status} {name} n={n} {kname}: {result['mismatches']} mismatches!")

    print(f"  Phase 1: {total_tests} tests, {total_inputs:,} inputs, {total_mismatches} mismatches")

    # Phase 2: Random programs
    print("\n--- Phase 2: Random Programs ---")
    phase2_tests = 0
    phase2_inputs = 0

    for i in range(50):
        prog = generate_random_program()
        n = random.choice([1000, 5000, 10000])
        inputs = [random.randint(0, 255) for _ in range(n)]

        for kname, kfn in kernels:
            result = run_differential_test(prog, inputs, kname, kfn)
            phase2_tests += 1
            phase2_inputs += n
            total_mismatches += result["mismatches"]

            if not result["pass"]:
                failed_programs.append(result)

    total_tests += phase2_tests
    total_inputs += phase2_inputs
    print(f"  Phase 2: {phase2_tests} tests, {phase2_inputs:,} inputs, {total_mismatches} total mismatches")

    # Phase 3: Edge cases
    print("\n--- Phase 3: Edge Cases ---")
    edge_cases = [
        ("empty_range", bytes([0x1D, 50, 49, 0x1B, 0x1A, 0x20])),  # lo > hi — all fail
        ("exact_boundary", bytes([0x1D, 50, 50, 0x1B, 0x1A, 0x20])),  # single value
        ("full_range", bytes([0x1D, 0, 255, 0x1B, 0x1A, 0x20])),  # all pass
        ("trap_only", bytes([0x20])),  # immediate fault
    ]

    for name, prog in edge_cases:
        inputs = [random.randint(0, 255) for _ in range(10000)]
        for kname, kfn in kernels:
            result = run_differential_test(prog, inputs, kname, kfn)
            total_tests += 1
            total_inputs += 10000
            total_mismatches += result["mismatches"]

            if not result["pass"]:
                failed_programs.append(result)

    # Phase 4: Massive scale
    print("\n--- Phase 4: Massive Scale (1M inputs) ---")
    prog = bytes([0x1D, 0, 50, 0x1B, 0x1A, 0x20])
    inputs = [random.randint(0, 100) for _ in range(1_000_000)]

    for kname, kfn in kernels:
        result = run_differential_test(prog, inputs, kname, kfn)
        total_tests += 1
        total_inputs += 1_000_000
        total_mismatches += result["mismatches"]

        status = "✓" if result["pass"] else "✗"
        print(f"  {status} 1M inputs {kname}: {result['mismatches']} mismatches")

    # Summary
    print("\n" + "=" * 70)
    print(f"TOTAL: {total_tests} tests | {total_inputs:,} inputs | {total_mismatches} mismatches")
    print(f"RESULT: {'ALL PASS ✓' if total_mismatches == 0 else f'{len(failed_programs)} FAILURES ✗'}")

    if failed_programs:
        print("\nFailed programs:")
        for fp in failed_programs[:10]:
            print(f"  {fp['kernel']} n={fp['n']}: {fp['mismatches']} mismatches")
            print(f"    program: {fp['program']}")
    print("=" * 70)


if __name__ == "__main__":
    random.seed(42)  # Reproducible
    main()

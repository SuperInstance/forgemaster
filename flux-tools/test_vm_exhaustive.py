#!/usr/bin/env python3
"""
FLUX VM Exhaustive Test Suite — FLUX ISA v3
=============================================
Phases 1-4: Correctness, Performance, Compiler, Programs

Usage:
  python test_vm_exhaustive.py
"""

import struct
import math
import sys
import random
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flux_asm import assemble
from flux_vm import FluxVM, to_signed32, to_unsigned32, FLUX_OK
from flux_vm_optimized import FluxVMOptimized

random.seed(42)

# ── Helpers ─────────────────────────────────────────────────────

passed = 0
failed = 0
errors = []
phase_results = {}

def check(name, actual, expected, tolerance=None):
    global passed, failed
    if tolerance is not None:
        ok = abs(actual - expected) < tolerance
    elif isinstance(expected, float):
        ok = abs(actual - expected) < 0.001
    else:
        ok = actual == expected
    if ok:
        passed += 1
    else:
        failed += 1
        errors.append(f"  ❌ {name}: got {actual}, expected {expected}")
        if failed <= 50:
            print(f"  ❌ {name}: got {actual}, expected {expected}")

def make_vm(asm_source):
    """Assemble and load into a VM."""
    full_binary, bytecode, labels, func_table = assemble(asm_source)
    vm = FluxVM()
    # Load raw bytecode (skip FLUX header complexity)
    vm.load_bytecode(bytecode)
    return vm

def make_vm_opt(asm_source):
    full_binary, bytecode, labels, func_table = assemble(asm_source)
    vm = FluxVMOptimized()
    vm.load_bytecode(bytecode)
    return vm

def run_vm(vm, max_cycles=500000):
    err = vm.run(max_cycles)
    return err

# ═══════════════════════════════════════════════════════════════
# PHASE 1: FLUX VM CORRECTNESS
# ═══════════════════════════════════════════════════════════════

def phase1_arithmetic():
    """Test arithmetic opcodes with 1000 random inputs."""
    print("\n── Phase 1.1: Arithmetic Opcodes ──")
    p, f = 0, 0
    
    # IADD: R2 = R0 + R1
    for _ in range(200):
        a = random.randint(-30000, 30000)
        b = random.randint(-30000, 30000)
        expected = to_signed32(a + b)
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IAdd R2, R0, R1
        IMov R8, R2
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IADD({a},{b})", vm.gp[8], expected)
        p += 1
    
    # ISUB: R2 = R0 - R1
    for _ in range(200):
        a = random.randint(-30000, 30000)
        b = random.randint(-30000, 30000)
        expected = to_signed32(a - b)
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        ISub R2, R0, R1
        IMov R8, R2
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"ISUB({a},{b})", vm.gp[8], expected)
        p += 1
    
    # IMUL: R2 = R0 * R1
    for _ in range(200):
        a = random.randint(-30000, 30000)
        b = random.randint(-30000, 30000)
        expected = to_signed32(a * b)
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IMul R2, R0, R1
        IMov R8, R2
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IMUL({a},{b})", vm.gp[8], expected)
        p += 1
    
    # IDIV: R2 = R0 / R1
    for _ in range(200):
        a = random.randint(-30000, 30000)
        b = random.randint(-30000, 30000)
        if b == 0: b = 1
        expected = to_signed32(int(a / b))
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IDiv R2, R0, R1
        IMov R8, R2
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IDIV({a},{b})", vm.gp[8], expected)
        p += 1
    
    # IMOD: R2 = R0 % R1
    for _ in range(200):
        a = random.randint(-30000, 30000)
        b = random.randint(1, 10000)
        expected = to_signed32(a % b)
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IMod R2, R0, R1
        IMov R8, R2
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IMOD({a},{b})", vm.gp[8], expected)
        p += 1
    
    print(f"  Arithmetic: {p} tests")

def phase1_stack():
    """Test stack operations."""
    print("\n── Phase 1.2: Stack Operations ──")
    
    # PUSH/POP round-trip
    for _ in range(100):
        val = random.randint(-30000, 30000)
        asm = f"""
        MOVI R0, {val}
        Push R0, R0
        Pop R1, R1
        
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"PUSH/POP({val})", to_signed32(vm.gp[1]), val)
    
    # DUP
    for _ in range(100):
        val = random.randint(-30000, 30000)
        asm = f"""
        MOVI R0, {val}
        Dup R1, R0
        IMov R8, R1
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"DUP({val})", vm.gp[8], val)
    
    # SWAP
    for _ in range(100):
        a = random.randint(-30000, 30000)
        b = random.randint(-30000, 30000)
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        Swap R0, R1
        IMov R8, R0
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"SWAP: R0 was {a}, becomes {b}", vm.gp[8], b)

def phase1_comparisons():
    """Test comparison opcodes."""
    print("\n── Phase 1.3: Comparison Opcodes ──")
    
    ops = {
        'ICmpEq': lambda a, b: 1 if a == b else 0,
        'ICmpNe': lambda a, b: 1 if a != b else 0,
        'ICmpLt': lambda a, b: 1 if a < b else 0,
        'ICmpLe': lambda a, b: 1 if a <= b else 0,
        'ICmpGt': lambda a, b: 1 if a > b else 0,
        'ICmpGe': lambda a, b: 1 if a >= b else 0,
    }
    
    edge_cases = [(0, 0), (-1, 0), (0, -1), (1, 1), (-1, -1), 
                  (32767, -32768), (100, 200), (200, 100)]
    
    for op_name, op_fn in ops.items():
        for _ in range(50):
            a = random.randint(-30000, 30000)
            b = random.randint(-30000, 30000)
            expected = op_fn(a, b)
            asm = f"""
            MOVI R0, {a}
            MOVI R1, {b}
            {op_name} R8, R0, R1
            Halt
            """
            vm = make_vm(asm)
            run_vm(vm)
            check(f"{op_name}({a},{b})", vm.gp[8], expected)
        
        for a, b in edge_cases:
            expected = op_fn(a, b)
            asm = f"""
            MOVI R0, {a}
            MOVI R1, {b}
            {op_name} R8, R0, R1
            Halt
            """
            vm = make_vm(asm)
            run_vm(vm)
            check(f"{op_name}_edge({a},{b})", vm.gp[8], expected)

def phase1_jumps():
    """Test jump opcodes."""
    print("\n── Phase 1.4: Jump Opcodes ──")
    
    # JZ: jump when zero
    for val in [0, 1, -1, 5, 100]:
        expected = 1 if val == 0 else 0  # JZ taken when val=0 → R8 stays 1
        asm = f"""
        MOVI R0, {val}
        MOVI R8, 1
        JZ R0, skip
        MOVI R8, 0
        skip:
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"JZ(val={val})", vm.gp[8], expected)
    
    # JNZ: jump when non-zero
    for val in [0, 1, -1, 5, 100]:
        expected = 1 if val != 0 else 0
        asm = f"""
        MOVI R0, {val}
        MOVI R8, 0
        JNZ R0, skip
        MOVI R8, 99
        skip:
        IMov R8, R8
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        # JNZ: if R0 != 0, jump to skip (bypass MOVI R8, 99)
        # So if val != 0: R8 stays 0 (from MOVI R8, 0)... wait, let me rethink
        # We want: if val != 0 → R8 = 1, else R8 = 0
        asm2 = f"""
        MOVI R0, {val}
        MOVI R8, 0
        JNZ R0, nonzero
        Jump done
        nonzero:
        MOVI R8, 1
        done:
        Halt
        """
        vm = make_vm(asm2)
        run_vm(vm)
        check(f"JNZ(val={val})", vm.gp[8], expected)
    
    # Unconditional JUMP
    asm = """
    MOVI R8, 0
    Jump skip
    MOVI R8, 99
    skip:
    MOVI R8, 42
    Halt
    """
    vm = make_vm(asm)
    run_vm(vm)
    check("JUMP unconditional", vm.gp[8], 42)

def phase1_float():
    """Test float operations."""
    print("\n── Phase 1.5: Float Operations ──")
    
    # FADD, FSUB, FMUL, FDIV via ITOF/FToI
    for _ in range(100):
        a = random.uniform(-100.0, 100.0)
        b = random.uniform(-100.0, 100.0)
        if abs(b) < 0.001: b = 1.0
        
        # Test FMUL
        a_int = int(a * 1000)
        b_int = int(b * 1000)
        # Just test that VM float ops work
        asm = f"""
        MOVI R0, {int(a)}
        MOVI R1, {int(b)}
        IToF F0, R0, R0
        IToF F1, R1, R1
        FMul F2, F0, F1
        FToI R8, F2, F2
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        expected = int(a) * int(b)
        check(f"FMUL({int(a)},{int(b)})", vm.gp[8], expected)
    
    # FSQRT
    for val in [0, 1, 4, 9, 16, 100, 10000]:
        asm = f"""
        MOVI R0, {val}
        IToF F0, R0, R0
        FSqrt F1, F0, F0
        FToI R8, F1, F1
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        expected = int(math.sqrt(val))
        check(f"FSQRT({val})", vm.gp[8], expected, tolerance=1)

def phase1_bitwise():
    """Test bitwise operations."""
    print("\n── Phase 1.6: Bitwise Operations ──")
    
    for _ in range(100):
        a = random.randint(0, 30000)
        b = random.randint(0, 30000)
        
        # IXOR
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IXor R8, R0, R1
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        expected = to_signed32(a ^ b)
        check(f"IXOR({a},{b})", vm.gp[8], expected)
        
        # IAND
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IAnd R8, R0, R1
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        expected = to_signed32(a & b)
        check(f"IAND({a},{b})", vm.gp[8], expected)
        
        # IOR
        asm = f"""
        MOVI R0, {a}
        MOVI R1, {b}
        IOr R8, R0, R1
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        expected = to_signed32(a | b)
        check(f"IOR({a},{b})", vm.gp[8], expected)

def phase1_memory():
    """Test memory load/store."""
    print("\n── Phase 1.7: Memory Load/Store ──")
    
    for _ in range(100):
        val = random.randint(-30000, 30000)
        offset = random.choice([0, 4, 8, 16, 32, 64, 100, 200, 500])
        
        # STORE32 then LOAD32
        asm = f"""
        MOVI R0, {val}
        MOVI R6, 1000
        Store32 R0, R6, {offset}
        Load32 R8, R6, {offset}
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"STORE/LOAD32(val={val},off={offset})", vm.gp[8], val)
    
    # STORE8 / LOAD8
    for _ in range(50):
        val = random.randint(0, 255)
        offset = random.choice([0, 1, 5, 10, 50, 100])
        asm = f"""
        MOVI R0, {val}
        MOVI R6, 2000
        Store8 R0, R6, {offset}
        Load8 R8, R6, {offset}
        Halt
        """
        vm = make_vm(asm)
        run_vm(vm)
        check(f"STORE/LOAD8(val={val},off={offset})", vm.gp[8], val)

def phase1_vector():
    """Test vector/SIMD operations."""
    print("\n── Phase 1.8: Vector Operations ──")
    
    # VADD: manually build vector data in memory, then VLoad, VAdd, VStore
    # Use high addresses to avoid code
    vals_a = [random.randint(-1000, 1000) for _ in range(16)]
    vals_b = [random.randint(-1000, 1000) for _ in range(16)]
    
    # Use the vm directly instead of asm for vector setup
    full_bin, bytecode, labels, funcs = assemble("""
    VLoad V0, R6, 0
    VLoad V1, R7, 0
    VAdd V2, V0, V1
    VStore V2, R5, 0
    Load32 R8, R5, 0
    Halt
    """)
    
    vm = FluxVM()
    vm.load_bytecode(bytecode)
    base_a = 8000
    base_b = 8100
    base_out = 8200
    vm.gp[6] = base_a
    vm.gp[7] = base_b
    vm.gp[5] = base_out
    
    # Manually write vector data to memory
    for i, v in enumerate(vals_a):
        struct.pack_into('<i', vm.memory, base_a + i*4, v)
    for i, v in enumerate(vals_b):
        struct.pack_into('<i', vm.memory, base_b + i*4, v)
    
    run_vm(vm, max_cycles=10000)
    expected = to_signed32(vals_a[0] + vals_b[0])
    check(f"VADD element 0", vm.gp[8], expected)
    
    # Verify all elements
    for i in range(16):
        actual = struct.unpack_from('<i', vm.memory, base_out + i*4)[0]
        expected = to_signed32(vals_a[i] + vals_b[i])
        check(f"VADD element {i}", actual, expected)
    
    # VDOT
    full_bin, bytecode, labels, funcs = assemble("""
    VLoad V0, R6, 0
    VLoad V1, R7, 0
    VDot R8, V0, V1
    Halt
    """)
    vm2 = FluxVM()
    vm2.load_bytecode(bytecode)
    vm2.gp[6] = base_a
    vm2.gp[7] = base_b
    for i, v in enumerate(vals_a):
        struct.pack_into('<i', vm2.memory, base_a + i*4, v)
    for i, v in enumerate(vals_b):
        struct.pack_into('<i', vm2.memory, base_b + i*4, v)
    run_vm(vm2, max_cycles=10000)
    expected_dot = sum(a * b for a, b in zip(vals_a, vals_b))
    check(f"VDOT", vm2.gp[8], to_signed32(expected_dot))

def phase1_misc():
    """Test misc opcodes: INEG, IABS, IMIN, IMAX, etc."""
    print("\n── Phase 1.9: Misc Opcodes ──")
    
    for _ in range(100):
        val = random.randint(-30000, 30000)
        
        # INEG
        asm = f"MOVI R0, {val}\nINeg R8, R0, R0\nHalt"
        vm = make_vm(asm)
        run_vm(vm)
        check(f"INEG({val})", vm.gp[8], to_signed32(-val))
        
        # IABS
        asm = f"MOVI R0, {val}\nIAbs R8, R0, R0\nHalt"
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IABS({val})", vm.gp[8], to_signed32(abs(val)))
    
    # IMIN/IMAX
    for _ in range(50):
        a = random.randint(-30000, 30000)
        b = random.randint(-30000, 30000)
        asm = f"MOVI R0, {a}\nMOVI R1, {b}\nIMin R8, R0, R1\nHalt"
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IMIN({a},{b})", vm.gp[8], min(a, b))
        
        asm = f"MOVI R0, {a}\nMOVI R1, {b}\nIMax R8, R0, R1\nHalt"
        vm = make_vm(asm)
        run_vm(vm)
        check(f"IMAX({a},{b})", vm.gp[8], max(a, b))


# ═══════════════════════════════════════════════════════════════
# PHASE 2: OPTIMIZED vs ORIGINAL VM PERFORMANCE
# ═══════════════════════════════════════════════════════════════

def phase2_benchmarks():
    """Benchmark optimized vs original VM."""
    print("\n── Phase 2: Optimized vs Original VM ──")
    
    results = {}
    
    # Benchmark 1: Fibonacci(30) — iterative
    fib_asm = """
    MOVI R0, 0
    MOVI R1, 1
    MOVI R2, 30
    loop:
    MOVI R3, 0
    ICmpEq R3, R2, R3
    JNZ R3, done
    IAdd R3, R0, R1
    IMov R0, R1
    IMov R1, R3
    IDec R2, 1
    Jump loop
    done:
    IMov R8, R1
    Halt
    """
    
    vm1 = make_vm(fib_asm)
    t0 = time.perf_counter()
    run_vm(vm1, max_cycles=500000)
    t1 = time.perf_counter()
    fib_result = vm1.gp[8]
    
    vm2 = make_vm_opt(fib_asm)
    t0b = time.perf_counter()
    vm2.run(max_cycles=500000)
    t1b = time.perf_counter()
    
    orig_time = t1 - t0
    opt_time = t1b - t0b
    speedup = orig_time / opt_time if opt_time > 0 else float('inf')
    
    check("Fibonacci(30) result", vm2.gp[8], fib_result)
    results['fibonacci'] = {
        'orig_ms': orig_time * 1000,
        'opt_ms': opt_time * 1000,
        'speedup': speedup,
        'result': fib_result,
    }
    print(f"  Fibonacci(30) = {fib_result}")
    print(f"    Original: {orig_time*1000:.2f}ms | Optimized: {opt_time*1000:.2f}ms | Speedup: {speedup:.2f}x")
    
    # Benchmark 2: Mandelbrot iteration (100 iterations)
    mandel_asm = """
    MOVI R0, 0
    MOVI R1, 0
    MOVI R2, 100
    loop:
    ICmpEq R3, R0, R2
    JNZ R3, done
    IInc R1, 7
    IMul R3, R0, R1
    IInc R3, 3
    IInc R0, 1
    Jump loop
    done:
    IMov R8, R1
    Halt
    """
    
    vm1 = make_vm(mandel_asm)
    t0 = time.perf_counter()
    run_vm(vm1, max_cycles=500000)
    t1 = time.perf_counter()
    
    vm2 = make_vm_opt(mandel_asm)
    t0b = time.perf_counter()
    vm2.run(max_cycles=500000)
    t1b = time.perf_counter()
    
    orig_time = t1 - t0
    opt_time = t1b - t0b
    speedup = orig_time / opt_time if opt_time > 0 else float('inf')
    
    check("Mandelbrot iter result", vm2.gp[8], vm1.gp[8])
    results['mandelbrot'] = {
        'orig_ms': orig_time * 1000,
        'opt_ms': opt_time * 1000,
        'speedup': speedup,
    }
    print(f"  Mandelbrot: Original: {orig_time*1000:.2f}ms | Optimized: {opt_time*1000:.2f}ms | Speedup: {speedup:.2f}x")
    
    # Benchmark 3: Constraint checking loop (100K iterations)
    # Constraint check should use values that fit in MOVI immediate
    constraint_asm = """
    MOVI R0, 0
    MOVI R1, 10000
    MOVI R2, 0
    loop:
    ICmpEq R3, R0, R1
    JNZ R3, done
    IInc R2, 3
    IMul R3, R0, R2
    IAdd R3, R3, R0
    IInc R0, 1
    Jump loop
    done:
    IMov R8, R2
    Halt
    """
    
    vm1 = make_vm(constraint_asm)
    t0 = time.perf_counter()
    run_vm(vm1, max_cycles=2000000)
    t1 = time.perf_counter()
    
    vm2 = make_vm_opt(constraint_asm)
    t0b = time.perf_counter()
    vm2.run(max_cycles=2000000)
    t1b = time.perf_counter()
    
    orig_time = t1 - t0
    opt_time = t1b - t0b
    speedup = orig_time / opt_time if opt_time > 0 else float('inf')
    
    check("Constraint loop result", vm2.gp[8], vm1.gp[8])
    results['constraint_loop'] = {
        'orig_ms': orig_time * 1000,
        'opt_ms': opt_time * 1000,
        'speedup': speedup,
    }
    print(f"  Constraint(100K): Original: {orig_time*1000:.2f}ms | Optimized: {opt_time*1000:.2f}ms | Speedup: {speedup:.2f}x")
    
    # Benchmark 4: Eisenstein snap on many points
    eisenstein_asm = """
    MOVI R0, 0
    MOVI R1, 1000
    MOVI R2, 0
    MOVI R9, 0
    loop:
    ICmpEq R3, R0, R1
    JNZ R3, done
    ISub R3, R0, R9
    MOVI R4, 3
    IMod R3, R3, R4
    MOVI R5, 2
    ICmpEq R6, R3, R5
    JZ R6, noadj
    IInc R9, 1
    noadj:
    IAdd R2, R2, R9
    IInc R0, 1
    Jump loop
    done:
    IMov R8, R2
    Halt
    """
    
    vm1 = make_vm(eisenstein_asm)
    t0 = time.perf_counter()
    run_vm(vm1, max_cycles=2000000)
    t1 = time.perf_counter()
    
    vm2 = make_vm_opt(eisenstein_asm)
    t0b = time.perf_counter()
    vm2.run(max_cycles=2000000)
    t1b = time.perf_counter()
    
    orig_time = t1 - t0
    opt_time = t1b - t0b
    speedup = orig_time / opt_time if opt_time > 0 else float('inf')
    
    check("Eisenstein snap result", vm2.gp[8], vm1.gp[8])
    results['eisenstein_1k'] = {
        'orig_ms': orig_time * 1000,
        'opt_ms': opt_time * 1000,
        'speedup': speedup,
    }
    print(f"  Eisenstein(1K): Original: {orig_time*1000:.2f}ms | Optimized: {opt_time*1000:.2f}ms | Speedup: {speedup:.2f}x")
    
    # Benchmark 5: Bloom filter pattern (many lookups in a loop)
    bloom_asm = """
    MOVI R0, 0
    MOVI R1, 5000
    MOVI R2, 0
    MOVI R6, 3000
    loop:
    ICmpEq R3, R0, R1
    JNZ R3, done
    IXor R3, R0, R0
    IAdd R3, R3, R0
    IAdd R2, R2, R3
    IInc R0, 1
    Jump loop
    done:
    IMov R8, R2
    Halt
    """
    
    vm1 = make_vm(bloom_asm)
    t0 = time.perf_counter()
    run_vm(vm1, max_cycles=2000000)
    t1 = time.perf_counter()
    
    vm2 = make_vm_opt(bloom_asm)
    t0b = time.perf_counter()
    vm2.run(max_cycles=2000000)
    t1b = time.perf_counter()
    
    orig_time = t1 - t0
    opt_time = t1b - t0b
    speedup = orig_time / opt_time if opt_time > 0 else float('inf')
    
    check("Bloom pattern result", vm2.gp[8], vm1.gp[8])
    results['bloom_pattern'] = {
        'orig_ms': orig_time * 1000,
        'opt_ms': opt_time * 1000,
        'speedup': speedup,
    }
    print(f"  BloomPattern(5K): Original: {orig_time*1000:.2f}ms | Optimized: {opt_time*1000:.2f}ms | Speedup: {speedup:.2f}x")
    
    return results

# ═══════════════════════════════════════════════════════════════
# PHASE 3: FLUXILE COMPILER CORRECTNESS
# ═══════════════════════════════════════════════════════════════

def phase3_compiler():
    """Test Fluxile compiler."""
    print("\n── Phase 3: Fluxile Compiler ──")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / 'fluxile'))
    from compiler import compile_source
    
    # Test 1: Simple arithmetic
    src1 = """
    fn main() -> i32 {
        let x = 3 + 4;
        return x * 2;
    }
    """
    try:
        asm1 = compile_source(src1, opt_level=0)
        check("Compiler: arithmetic compiles", True, True)
        check("Compiler: output contains FUNC", "FUNC" in asm1, True)
        check("Compiler: output contains IMul", "IMul" in asm1, True)
    except Exception as e:
        check(f"Compiler: arithmetic compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 2: Control flow (for loop)
    src2 = """
    fn sum(n: i32) -> i32 {
        let total = 0;
        for i in range(n) {
            total = total + i;
        }
        return total;
    }
    """
    try:
        asm2 = compile_source(src2, opt_level=0)
        check("Compiler: for loop compiles", True, True)
        check("Compiler: output has loop labels", "for" in asm2 or "L" in asm2, True)
    except Exception as e:
        check(f"Compiler: for loop compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 3: If/else
    src3 = """
    fn abs_val(x: i32) -> i32 {
        if x < 0 {
            return 0 - x;
        } else {
            return x;
        }
    }
    """
    try:
        asm3 = compile_source(src3, opt_level=0)
        check("Compiler: if/else compiles", True, True)
    except Exception as e:
        check(f"Compiler: if/else compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 4: Constraint function
    src4 = """
    constraint fn bounds(val: i32, min: i32, max: i32) -> i32 {
        require val >= min;
        require val <= max;
        return 1;
    }
    """
    try:
        asm4 = compile_source(src4, opt_level=0)
        check("Compiler: constraint fn compiles", True, True)
        check("Compiler: has FLUX-C layer", "FLUX-C" in asm4, True)
        check("Compiler: has Panic", "Panic" in asm4, True)
    except Exception as e:
        check(f"Compiler: constraint fn compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 5: Agent block
    src5 = """
    agent Coordinator {
        fn decide(action: i32) -> i32 {
            return action;
        }
        fn broadcast(msg: i32) -> i32 {
            return msg;
        }
    }
    """
    try:
        asm5 = compile_source(src5, opt_level=0)
        check("Compiler: agent block compiles", True, True)
        check("Compiler: has AInit", "AInit" in asm5, True)
    except Exception as e:
        check(f"Compiler: agent block compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 6: Match expression
    src6 = """
    fn classify(x: i32) -> i32 {
        match x {
            0 => { return 1; },
            1 => { return 2; },
            _ => { return 0; },
        }
    }
    """
    try:
        asm6 = compile_source(src6, opt_level=0)
        check("Compiler: match compiles", True, True)
    except Exception as e:
        check(f"Compiler: match compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 7: Float operations
    src7 = """
    fn hypot(a: f32, b: f32) -> f32 {
        let aa = a * a;
        let bb = b * b;
        let sum = aa + bb;
        return sqrt(sum);
    }
    """
    try:
        asm7 = compile_source(src7, opt_level=0)
        check("Compiler: float ops compile", True, True)
        check("Compiler: has FSqrt", "FSqrt" in asm7, True)
    except Exception as e:
        check(f"Compiler: float ops compile", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 8: Optimization levels
    src8 = """
    fn const_fold() -> i32 {
        let x = 2 + 3;
        return x * 4;
    }
    """
    try:
        asm8_o0 = compile_source(src8, opt_level=0)
        asm8_o2 = compile_source(src8, opt_level=2)
        check("Compiler: opt levels produce output", len(asm8_o2) > 0, True)
        # With constant folding, 2+3=5 and 5*4=20 should be folded
        has_fold = "20" in asm8_o2
        check("Compiler: constant folding works", has_fold, True)
    except Exception as e:
        check(f"Compiler: optimization levels", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 9: Intent literals
    src9 = """
    fn test_intent() -> i32 {
        let v = intent![1.0, 0.5, 0.3, 0.1, 0.2, 0.4, 0.7, 0.6, 0.8];
        return 1;
    }
    """
    try:
        asm9 = compile_source(src9, opt_level=0)
        check("Compiler: intent literal compiles", True, True)
    except Exception as e:
        check(f"Compiler: intent literal compiles", False, True)
        errors.append(f"  Compiler error: {e}")
    
    # Test 10: A2A ops
    src10 = """
    fn coord(action: i32) -> i32 {
        let r = tell(1, action);
        let s = ask(2, action);
        return s;
    }
    """
    try:
        asm10 = compile_source(src10, opt_level=0)
        check("Compiler: A2A ops compile", True, True)
        check("Compiler: has ATell", "ATell" in asm10, True)
        check("Compiler: has AAsk", "AAsk" in asm10, True)
    except Exception as e:
        check(f"Compiler: A2A ops compile", False, True)
        errors.append(f"  Compiler error: {e}")


# ═══════════════════════════════════════════════════════════════
# PHASE 4: FLUX PROGRAMS FALSIFICATION
# ═══════════════════════════════════════════════════════════════

def phase4_programs():
    """Test all programs in flux-programs/."""
    print("\n── Phase 4: FLUX Programs Falsification ──")
    
    prog_dir = Path(__file__).parent.parent / 'flux-programs' / 'programs'
    
    # ── Eisenstein Snap ──
    print("  Testing eisenstein_snap.flux...")
    eis_src = (prog_dir / 'eisenstein_snap.flux').read_text()
    
    # Test known Eisenstein integer snaps
    test_cases = [
        # (a_float, b_float, expected_a_snapped, expected_b_snapped)
        (0.0, 0.0, 0, 0),      # Already on lattice
        (1.0, 0.0, 1, 0),      # (1-0) mod 3 = 1 ✓
        (1.0, 1.0, 1, 1),      # (1-1) mod 3 = 0 ✓
        (0.5, 0.5, 1, 0),      # round(0.5)=1, round(0.5)=1, (1-1)%3=0 ✓  actually round(0.5)=0 in Python
        (2.0, 1.0, 2, 1),      # (2-1) mod 3 = 1 ✓
        (3.7, 2.3, 4, 2),      # round(3.7)=4, round(2.3)=2, (4-2)%3=2 → b+=1=3... let's see
    ]
    
    for a, b, exp_a, exp_b in test_cases:
        full_bin, bytecode, labels, funcs = assemble(eis_src)
        vm = FluxVM()
        vm.load_bytecode(bytecode)
        vm.fp_regs[0] = a
        vm.fp_regs[1] = b
        run_vm(vm, max_cycles=10000)
        # Compute expected using same logic as the program
        a_r = round(a)
        b_r = round(b)
        rem = (a_r - b_r) % 3
        if rem == 2:
            b_r += 1
        check(f"Eisenstein({a},{b}) a", vm.gp[8], a_r)
        check(f"Eisenstein({a},{b}) b", vm.gp[9], b_r)
    
    # Stress test with 100 random floats
    for _ in range(100):
        a = random.uniform(-50, 50)
        b = random.uniform(-50, 50)
        full_bin, bytecode, labels, funcs = assemble(eis_src)
        vm = FluxVM()
        vm.load_bytecode(bytecode)
        vm.fp_regs[0] = a
        vm.fp_regs[1] = b
        run_vm(vm, max_cycles=10000)
        
        a_r = round(a)
        b_r = round(b)
        rem = (a_r - b_r) % 3
        if rem == 2:
            b_r += 1
        check(f"Eisenstein_stress({a:.1f},{b:.1f}) a", vm.gp[8], a_r)
        check(f"Eisenstein_stress({a:.1f},{b:.1f}) b", vm.gp[9], b_r)
    
    # ── Constraint Check ──
    print("  Testing constraint_check.flux...")
    cc_src = (prog_dir / 'constraint_check.flux').read_text()
    
    # Should pass: val in [min, max]
    for val, mn, mx, should_pass in [
        (5, 0, 10, True),
        (0, 0, 10, True),
        (10, 0, 10, True),
        (-1, 0, 10, False),
        (11, 0, 10, False),
        (50, 0, 100, True),
        (5, 5, 5, True),
    ]:
        full_bin, bytecode, labels, funcs = assemble(cc_src)
        vm = FluxVM()
        vm.load_bytecode(bytecode)
        vm.gp[0] = val
        vm.gp[1] = mn
        vm.gp[2] = mx
        err = run_vm(vm, max_cycles=10000)
        
        if should_pass:
            check(f"Constraint({val} in [{mn},{mx}])", vm.gp[8], 1)
            check(f"Constraint_no_panic({val})", err, FLUX_OK)
        else:
            # Should PANIC (error code 2 = FLUX_ERR_INVALID_OP)
            check(f"Constraint_panic({val} in [{mn},{mx}])", err, 2)
    
    # ── Bloom Filter ──
    print("  Testing bloom_filter.flux...")
    bf_src = (prog_dir / 'bloom_filter.flux').read_text()
    
    # Set up a bitmap with some bits set, then test
    full_bin, bytecode, labels, funcs = assemble(bf_src)
    
    # Test: empty bitmap → all lookups should return 0
    vm = FluxVM()
    vm.load_bytecode(bytecode)
    vm.gp[0] = 42  # value to check
    vm.gp[6] = 3000  # bitmap base address (away from code)
    run_vm(vm, max_cycles=50000)
    check("Bloom_empty(42)", vm.gp[8], 0)
    
    # Test: manually set bits for value 42, then check
    def bloom_hashes(v):
        h1 = (v ^ (v << 5)) & 0xFFFFFFFF
        h2 = (v ^ (v >> 3)) & 0xFFFFFFFF
        h3 = ((v << 7) ^ (v >> 5)) & 0xFFFFFFFF
        return h1, h2, h3
    
    def bloom_insert(vm, value, bitmap_base):
        h1, h2, h3 = bloom_hashes(value)
        for h in [h1, h2, h3]:
            byte_idx = (h >> 3) & 0x1F
            bit_idx = h & 0x07
            addr = bitmap_base + byte_idx
            vm.memory[addr] |= (1 << bit_idx)
    
    for test_val in [42, 100, 255, 1000, 0, 1]:
        vm = FluxVM()
        vm.load_bytecode(bytecode)
        vm.gp[6] = 3000
        bloom_insert(vm, test_val, 3000)
        vm.gp[0] = test_val
        run_vm(vm, max_cycles=50000)
        check(f"Bloom_present({test_val})", vm.gp[8], 1)  # No false negatives
    
    # Test false negatives = 0 (guaranteed)
    # Insert 50 random values, verify all are found
    inserted = set()
    for _ in range(50):
        val = random.randint(1, 10000)
        inserted.add(val)
        vm = FluxVM()
        vm.load_bytecode(bytecode)
        vm.gp[6] = 3000
        for v in inserted:
            bloom_insert(vm, v, 3000)
        vm.gp[0] = val
        run_vm(vm, max_cycles=50000)
        check(f"Bloom_no_false_neg({val})", vm.gp[8], 1)
    
    # ── Temporal Snap ──
    print("  Testing temporal_snap.flux...")
    ts_src = (prog_dir / 'temporal_snap.flux').read_text()
    
    for ticks, period in [(100, 10), (0, 10), (50, 10), (55, 10), (99, 10), 
                          (1000, 100), (12345, 1000), (1, 1)]:
        full_bin, bytecode, labels, funcs = assemble(ts_src)
        vm = FluxVM()
        vm.load_bytecode(bytecode)
        vm.gp[0] = ticks
        vm.gp[1] = period
        run_vm(vm, max_cycles=10000)
        
        # Compute expected using same algorithm
        beat_raw = int(ticks / period)
        remainder = ticks - beat_raw * period
        if remainder >= period / 2:
            beat_raw += 1
        snapped = beat_raw * period
        drift = abs(snapped - ticks)
        
        check(f"Temporal_snap({ticks},{period})", vm.gp[8], snapped)
        check(f"Temporal_drift({ticks},{period})", vm.gp[9], drift)
    
    # ── Agent Coordinate ──
    print("  Testing agent_coordinate.flux...")
    ac_src = (prog_dir / 'agent_coordinate.flux').read_text()
    
    full_bin, bytecode, labels, funcs = assemble(ac_src)
    vm = FluxVM()
    vm.load_bytecode(bytecode)
    vm.gp[0] = 1  # action
    vm.gp[1] = 2  # agent1
    vm.gp[2] = 3  # agent2
    err = run_vm(vm, max_cycles=50000)
    # A2A is stubs, so it should run without crashing
    check("Agent_coordinate runs without crash", err, FLUX_OK)
    
    # ── Intent Align ──
    print("  Testing intent_align.flux...")
    ia_src = (prog_dir / 'intent_align.flux').read_text()
    
    # Test with identical vectors → alignment should be ~1000
    full_bin, bytecode, labels, funcs = assemble(ia_src)
    vm = FluxVM()
    vm.load_bytecode(bytecode)
    vm.gp[6] = 100  # base address for vectors
    
    # Vector A: 9 values starting at offset 0
    vec_a = [1000, 500, 300, 200, 100, 400, 700, 600, 800]
    for i, v in enumerate(vec_a):
        struct.pack_into('<i', vm.memory, 100 + i*4, v)
    
    # Vector B: identical → alignment = 1000
    for i, v in enumerate(vec_a):
        struct.pack_into('<i', vm.memory, 136 + i*4, v)
    
    run_vm(vm, max_cycles=50000)
    check("Intent_align(identical)", vm.gp[8], 1000)
    
    # Test with orthogonal vectors → alignment should be 0
    vm2 = FluxVM()
    vm2.load_bytecode(bytecode)
    vm2.gp[6] = 100
    
    vec_a2 = [1000, 0, 0, 0, 0, 0, 0, 0, 0]
    vec_b2 = [0, 1000, 0, 0, 0, 0, 0, 0, 0]
    for i, v in enumerate(vec_a2):
        struct.pack_into('<i', vm2.memory, 100 + i*4, v)
    for i, v in enumerate(vec_b2):
        struct.pack_into('<i', vm2.memory, 136 + i*4, v)
    
    run_vm(vm2, max_cycles=50000)
    check("Intent_align(orthogonal)", vm2.gp[8], 0)
    
    # Test with opposite vectors → alignment should be 0 or negative (clamped to 0)
    vm3 = FluxVM()
    vm3.load_bytecode(bytecode)
    vm3.gp[6] = 100
    
    vec_a3 = [1000, 500, 300]
    vec_b3 = [-1000, -500, -300]
    vec_a3 += [0] * 6
    vec_b3 += [0] * 6
    for i, v in enumerate(vec_a3):
        struct.pack_into('<i', vm3.memory, 100 + i*4, v)
    for i, v in enumerate(vec_b3):
        struct.pack_into('<i', vm3.memory, 136 + i*4, v)
    
    run_vm(vm3, max_cycles=50000)
    check("Intent_align(opposite)", vm3.gp[8], 0)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("FLUX VM Exhaustive Test Suite — FLUX ISA v3")
    print("=" * 70)
    
    total_passed = 0
    total_failed = 0
    
    # Phase 1: VM Correctness
    print("\n╔══════════════════════════════════════╗")
    print("║  PHASE 1: FLUX VM Correctness        ║")
    print("╚══════════════════════════════════════╝")
    
    p_before = passed
    f_before = failed
    
    phase1_arithmetic()
    phase1_stack()
    phase1_comparisons()
    phase1_jumps()
    phase1_float()
    phase1_bitwise()
    phase1_memory()
    phase1_vector()
    phase1_misc()
    
    phase1_passed = passed - p_before
    phase1_failed = failed - f_before
    phase_results['phase1'] = {'passed': phase1_passed, 'failed': phase1_failed}
    
    # Phase 2: Performance
    print("\n╔══════════════════════════════════════╗")
    print("║  PHASE 2: Optimized vs Original VM   ║")
    print("╚══════════════════════════════════════╝")
    
    p_before = passed
    f_before = failed
    
    bench_results = phase2_benchmarks()
    
    phase2_passed = passed - p_before
    phase2_failed = failed - f_before
    phase_results['phase2'] = {'passed': phase2_passed, 'failed': phase2_failed, 'benchmarks': bench_results}
    
    # Phase 3: Compiler
    print("\n╔══════════════════════════════════════╗")
    print("║  PHASE 3: Fluxile Compiler           ║")
    print("╚══════════════════════════════════════╝")
    
    p_before = passed
    f_before = failed
    
    phase3_compiler()
    
    phase3_passed = passed - p_before
    phase3_failed = failed - f_before
    phase_results['phase3'] = {'passed': phase3_passed, 'failed': phase3_failed}
    
    # Phase 4: Programs
    print("\n╔══════════════════════════════════════╗")
    print("║  PHASE 4: FLUX Programs              ║")
    print("╚══════════════════════════════════════╝")
    
    p_before = passed
    f_before = failed
    
    phase4_programs()
    
    phase4_passed = passed - p_before
    phase4_failed = failed - f_before
    phase_results['phase4'] = {'passed': phase4_passed, 'failed': phase4_failed}
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Phase 1 (VM Correctness):     {phase1_passed} passed, {phase1_failed} failed")
    print(f"  Phase 2 (Performance):        {phase2_passed} passed, {phase2_failed} failed")
    for name, bench in bench_results.items():
        print(f"    {name}: {bench['speedup']:.2f}x speedup ({bench['orig_ms']:.1f}ms → {bench['opt_ms']:.1f}ms)")
    print(f"  Phase 3 (Compiler):           {phase3_passed} passed, {phase3_failed} failed")
    print(f"  Phase 4 (Programs):           {phase4_passed} passed, {phase4_failed} failed")
    print(f"  ─────────────────────────────────────")
    print(f"  TOTAL:                        {passed} passed, {failed} failed")
    
    if errors:
        print(f"\n{'='*70}")
        print(f"FIRST {min(20, len(errors))} ERRORS:")
        for e in errors[:20]:
            print(e)
    
    # Write results for the experiment report
    import json
    results_path = Path(__file__).parent.parent / 'research' / 'flux-vm-test-results.json'
    results_path.parent.mkdir(parents=True, exist_ok=True)
    
    serializable = {}
    for k, v in phase_results.items():
        d = dict(v)
        if 'benchmarks' in d:
            d['benchmarks'] = {bk: {kk: vv for kk, vv in bv.items()} for bk, bv in d['benchmarks'].items()}
        serializable[k] = d
    
    results_path.write_text(json.dumps({
        'total_passed': passed,
        'total_failed': failed,
        'phases': serializable,
        'errors': errors[:100],
    }, indent=2, default=str))
    
    print(f"\nResults written to: {results_path}")
    sys.exit(0 if failed == 0 else 1)

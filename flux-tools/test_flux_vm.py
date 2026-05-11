#!/usr/bin/env python3
"""
FLUX VM Tests — FLUX ISA v3
============================
Tests:
  - Factorial(7) = 5040
  - Fibonacci(10) = 55
  - Vector add (VADD)
  - Float sqrt
  - Function call + return
  - Memory load/store round-trip
  - All comparison ops
  - Bitwise operations

Usage:
  python test_flux_vm.py
"""

import struct
import math
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from flux_asm import assemble, MOVI_OPCODE
from flux_vm import FluxVM, to_signed32, FLUX_OK

passed = 0
failed = 0


def check(name: str, actual, expected):
    global passed, failed
    # Float comparison
    if isinstance(expected, float):
        ok = abs(actual - expected) < 0.001
    else:
        ok = actual == expected
    if ok:
        passed += 1
        print(f"  ✅ {name}: {actual} == {expected}")
    else:
        failed += 1
        print(f"  ❌ {name}: {actual} != {expected}")


def make_vm_and_run(asm_source: str) -> FluxVM:
    """Assemble and run, returning the VM."""
    full_binary, bytecode, labels, func_table = assemble(asm_source)
    vm = FluxVM(debug=False)
    vm.load_bytecode(bytecode)
    vm.run()
    return vm


# ── Test 1: Factorial(7) = 5040 ────────────────────────────────

def test_factorial():
    print("\n── Test: Factorial(7) = 5040 ──")
    source = """
.func main 0
MOVI R0, 7
MOVI R1, 1
loop:
IMUL R1, R1, R0
IDEC R0, 1
JNZ R0, loop
HALT
"""
    vm = make_vm_and_run(source)
    check("factorial(7)", vm.gp[1], 5040)


# ── Test 2: Fibonacci(10) = 55 ─────────────────────────────────

def test_fibonacci():
    print("\n── Test: Fibonacci(10) = 55 ──")
    # Compute fib(n) iteratively: a=0, b=1, for i in range(n): a,b = b,a+b
    source = """
.func main 0
MOVI R0, 10
MOVI R1, 0
MOVI R2, 1
loop:
IMOV R3, R2
IADD R2, R2, R1
IMOV R1, R3
IDEC R0, 1
JNZ R0, loop
HALT
"""
    vm = make_vm_and_run(source)
    check("fibonacci(10)", vm.gp[1], 55)


# ── Test 3: Vector add (VADD) ──────────────────────────────────

def test_vector_add():
    print("\n── Test: Vector Add ──")
    # Manually build bytecode for VADD
    # We need to set up vector registers and do VADD
    vm = FluxVM()
    # V0 = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
    # V1 = [16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1]
    for i in range(16):
        vm.vec[0][i] = i + 1
        vm.vec[1][i] = 16 - i

    # Bytecode: VADD V2, V0, V1; HALT
    bytecode = bytearray()
    bytecode.append(0xB2)  # VADD
    bytecode.append(2)     # Vd
    bytecode.append(0)     # Va
    bytecode.append(1)     # Vb
    bytecode.append(0x00)  # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    # Expected: V2[i] = (i+1) + (16-i) = 17 for all i
    all_17 = all(vm.vec[2][i] == 17 for i in range(16))
    check("VADD all components = 17", all_17, True)
    check("VADD V2[0]", vm.vec[2][0], 17)
    check("VADD V2[15]", vm.vec[2][15], 17)


# ── Test 4: Float sqrt ─────────────────────────────────────────

def test_float_sqrt():
    print("\n── Test: Float sqrt(25.0) = 5.0 ──")
    # Manually build bytecode: set F0=25.0 via memory, FSQRT F1, F0, F0; HALT
    vm = FluxVM()
    # Store 25.0 as float32 at memory address 0
    vm.mem_write32(0, struct.unpack('<I', struct.pack('<f', 25.0))[0])

    # MOVI R0, 0  (address of float)
    # LOAD32 R1, R0, 0   -- load raw bits
    # Actually we need to load into FP register. Let's use a different approach.
    # Use FMOV + ITOF or store float in memory and use a custom load.
    #
    # Simplest: set FP register directly, then FSQRT
    vm.fp_regs[0] = 25.0

    # Bytecode: FSQRT F1, F0, F0; HALT
    bytecode = bytearray()
    bytecode.append(0x48)  # FSQRT
    bytecode.append(1)     # Fd
    bytecode.append(0)     # Fa
    bytecode.append(0)     # Fb (ignored)
    bytecode.append(0x00)  # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("sqrt(25.0)", vm.fp_regs[1], 5.0)


# ── Test 5: Function call + return ─────────────────────────────

def test_call_return():
    print("\n── Test: Function call + return ──")
    # main: MOVI R9, 42; CALL double_it; HALT
    # double_it: IMUL R8, R9, R2; ... actually need MOVI R2, 2 first
    # Let's do: main sets R9=21, R10=21, CALL add_func, result in R8
    # add_func: IADD R8, R9, R10; RET

    # Build bytecode manually
    vm = FluxVM()

    bytecode = bytearray()
    # -- main at offset 0 --
    # MOVI R9, 21
    bytecode.extend([MOVI_OPCODE, 9])
    bytecode.extend(struct.pack('<h', 21))
    # MOVI R10, 21
    bytecode.extend([MOVI_OPCODE, 10])
    bytecode.extend(struct.pack('<h', 21))
    # CALL add_func (address 28 = 4+4+4+4+4+4+4 = 28)
    # CALL is Format G: [0x06][length=2][func_idx_lo][func_idx_hi]
    # We'll use func_idx as direct address since no func table loaded
    func_addr = 28  # address of add_func
    bytecode.append(0x06)  # CALL
    bytecode.append(2)     # length
    bytecode.extend(struct.pack('<H', func_addr))
    # HALT
    bytecode.append(0x00)
    # Pad to func_addr
    while len(bytecode) < func_addr:
        bytecode.append(0x01)  # NOP

    # -- add_func at offset 28 --
    bytecode.append(0x21)  # IADD
    bytecode.append(8)     # Rd = R8 (return value)
    bytecode.append(9)     # Ra = R9 (A0)
    bytecode.append(10)    # Rb = R10 (A1)
    bytecode.append(0x02)  # RET

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("call+return R8", vm.gp[8], 42)


# ── Test 6: Memory load/store round-trip ────────────────────────

def test_memory_loadstore():
    print("\n── Test: Memory load/store round-trip ──")
    source = """
.func main 0
MOVI R0, 42
MOVI R1, 100
STORE32 R0, R1, 0
LOAD32 R2, R1, 0
HALT
"""
    vm = make_vm_and_run(source)
    check("store/load 32-bit", vm.gp[2], 42)

    # Test 8-bit
    vm2 = FluxVM()
    source2 = """
.func main 0
MOVI R0, 200
MOVI R1, 200
STORE8 R0, R1, 0
LOAD8 R2, R1, 0
HALT
"""
    _, bc2, _, _ = assemble(source2)
    vm2.load_bytecode(bc2)
    vm2.run()
    check("store/load 8-bit", vm2.gp[2], 200)

    # Test 16-bit
    vm3 = FluxVM()
    source3 = """
.func main 0
MOVI R0, 1234
MOVI R1, 300
STORE16 R0, R1, 0
LOAD16 R2, R1, 0
HALT
"""
    _, bc3, _, _ = assemble(source3)
    vm3.load_bytecode(bc3)
    vm3.run()
    check("store/load 16-bit", vm3.gp[2], 1234)


# ── Test 7: All comparison ops ─────────────────────────────────

def test_comparisons():
    print("\n── Test: Comparison operations ──")
    # Test: set R0=10, R1=20, compare
    source = """
.func main 0
MOVI R0, 10
MOVI R1, 20
ICMPEQ R2, R0, R1
ICMPNE R3, R0, R1
ICMPLT R4, R0, R1
ICMPLE R5, R0, R1
ICMPGT R6, R0, R1
ICMPGE R7, R0, R1
HALT
"""
    vm = make_vm_and_run(source)
    check("10 == 20 → 0", vm.gp[2], 0)
    check("10 != 20 → 1", vm.gp[3], 1)
    check("10 < 20 → 1", vm.gp[4], 1)
    check("10 <= 20 → 1", vm.gp[5], 1)
    check("10 > 20 → 0", vm.gp[6], 0)
    check("10 >= 20 → 0", vm.gp[7], 0)

    # Equal values
    source2 = """
.func main 0
MOVI R0, 42
MOVI R1, 42
ICMPEQ R2, R0, R1
ICMPNE R3, R0, R1
ICMPLT R4, R0, R1
ICMPLE R5, R0, R1
ICMPGT R6, R0, R1
ICMPGE R7, R0, R1
HALT
"""
    vm2 = make_vm_and_run(source2)
    check("42 == 42 → 1", vm2.gp[2], 1)
    check("42 != 42 → 0", vm2.gp[3], 0)
    check("42 < 42 → 0", vm2.gp[4], 0)
    check("42 <= 42 → 1", vm2.gp[5], 1)
    check("42 > 42 → 0", vm2.gp[6], 0)
    check("42 >= 42 → 1", vm2.gp[7], 1)


# ── Test 8: Bitwise operations ─────────────────────────────────

def test_bitwise():
    print("\n── Test: Bitwise operations ──")
    source = """
.func main 0
MOVI R0, 12
MOVI R1, 10
IAND R2, R0, R1
IOR R3, R0, R1
IXOR R4, R0, R1
INOT R5, R0, R0
ISHL R6, R0, R1
HALT
"""
    vm = make_vm_and_run(source)
    check("12 & 10", vm.gp[2], 12 & 10)    # 8
    check("12 | 10", vm.gp[3], 12 | 10)    # 14
    check("12 ^ 10", vm.gp[4], 12 ^ 10)    # 6
    check("~12", vm.gp[5], to_signed32(~12))
    check("12 << 10", vm.gp[6], to_signed32(12 << 10))


# ── Test: Float operations ─────────────────────────────────────

def test_float_ops():
    print("\n── Test: Float arithmetic ──")
    vm = FluxVM()
    vm.fp_regs[0] = 3.5
    vm.fp_regs[1] = 2.0

    # FADD F2, F0, F1; FMUL F3, F0, F1; FDIV F4, F0, F1; FSQRT F5, F0, F0; HALT
    bytecode = bytearray()
    bytecode.extend([0x41, 2, 0, 1])  # FADD
    bytecode.extend([0x43, 3, 0, 1])  # FMUL
    bytecode.extend([0x44, 4, 0, 1])  # FDIV
    bytecode.extend([0x48, 5, 0, 0])  # FSQRT F5 = sqrt(F0)
    bytecode.extend([0x4E, 6, 0, 0])  # FSIN F6 = sin(F0)
    bytecode.extend([0x4F, 7, 0, 0])  # FCOS F7 = cos(F0)
    bytecode.append(0x00)              # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("3.5 + 2.0", vm.fp_regs[2], 5.5)
    check("3.5 * 2.0", vm.fp_regs[3], 7.0)
    check("3.5 / 2.0", vm.fp_regs[4], 1.75)
    check("sqrt(3.5)", vm.fp_regs[5], math.sqrt(3.5))
    check("sin(3.5)", vm.fp_regs[6], math.sin(3.5))
    check("cos(3.5)", vm.fp_regs[7], math.cos(3.5))


# ── Test: Vector dot product ───────────────────────────────────

def test_vector_dot():
    print("\n── Test: Vector dot product ──")
    vm = FluxVM()
    # V0 = [1, 2, 3, ... 16]
    # V1 = [1, 1, 1, ... 1]
    # VDOT = sum = 1+2+3+...+16 = 136
    for i in range(16):
        vm.vec[0][i] = i + 1
        vm.vec[1][i] = 1

    # VDOT R0, V0, V1; HALT
    bytecode = bytearray()
    bytecode.extend([0xB4, 0, 0, 1])  # VDOT R0 = V0 · V1
    bytecode.append(0x00)              # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("VDOT sum(1..16)", vm.gp[0], 136)


# ── Test: Conversion ops ───────────────────────────────────────

def test_conversions():
    print("\n── Test: Type conversions ──")
    vm = FluxVM()
    vm.gp[0] = 42
    vm.fp_regs[1] = 3.7

    # ITOF F2, R0, R0; FTOI R3, F1, F1; HALT
    bytecode = bytearray()
    bytecode.extend([0x60, 2, 0, 0])  # ITOF F2 = float(R0)
    bytecode.extend([0x61, 3, 1, 1])  # FTOI R3 = int(F1)
    bytecode.append(0x00)              # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("ITOF 42 → 42.0", vm.fp_regs[2], 42.0)
    check("FTOI 3.7 → 3", vm.gp[3], 3)


# ── Test: Stack push/pop ───────────────────────────────────────

def test_stack():
    print("\n── Test: Stack push/pop ──")
    vm = FluxVM()

    # MOVI R0, 99; PUSH R0, R0; MOVI R0, 0; POP R0, R0; HALT
    bytecode = bytearray()
    bytecode.extend([MOVI_OPCODE, 0])  # MOVI R0, 99
    bytecode.extend(struct.pack('<h', 99))
    bytecode.extend([0x10, 0, 0])      # PUSH R0, R0
    bytecode.extend([MOVI_OPCODE, 0])  # MOVI R0, 0
    bytecode.extend(struct.pack('<h', 0))
    bytecode.extend([0x11, 0, 0])      # POP R0, R0
    bytecode.append(0x00)              # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("push/pop R0", vm.gp[0], 99)


# ── Test: JZ (jump if zero) ────────────────────────────────────

def test_jz():
    print("\n── Test: JZ / conditional jumps ──")
    source = """
.func main 0
MOVI R0, 0
MOVI R1, 99
JZ R0, skip
MOVI R1, 0
skip:
HALT
"""
    vm = make_vm_and_run(source)
    check("JZ taken (R0=0)", vm.gp[1], 99)

    # JZ not taken
    source2 = """
.func main 0
MOVI R0, 5
MOVI R1, 99
JZ R0, skip
MOVI R1, 0
skip:
HALT
"""
    vm2 = make_vm_and_run(source2)
    check("JZ not taken (R0=5)", vm2.gp[1], 0)


# ── Test: IMOD ─────────────────────────────────────────────────

def test_imod():
    print("\n── Test: IMOD ──")
    source = """
.func main 0
MOVI R0, 17
MOVI R1, 5
IMOD R2, R0, R1
HALT
"""
    vm = make_vm_and_run(source)
    check("17 % 5", vm.gp[2], 2)


# ── Test: BAND/BOR/BXOR (0xA0 opcodes) ─────────────────────────

def test_bxx_ops():
    print("\n── Test: BAND/BOR/BXOR (0xA0) ──")
    vm = FluxVM()
    vm.gp[0] = 0xFF
    vm.gp[1] = 0x0F

    # BAND R2, R0, R1; BOR R3, R0, R1; BXOR R4, R0, R1; HALT
    bytecode = bytearray()
    bytecode.extend([0xA0, 2, 0, 1])  # BAND
    bytecode.extend([0xA1, 3, 0, 1])  # BOR
    bytecode.extend([0xA2, 4, 0, 1])  # BXOR
    bytecode.append(0x00)              # HALT

    vm.load_bytecode(bytes(bytecode))
    vm.run()

    check("BAND 0xFF & 0x0F", vm.gp[2], 0x0F)
    check("BOR 0xFF | 0x0F", vm.gp[3], 0xFF)
    check("BXOR 0xFF ^ 0x0F", vm.gp[4], 0xF0)


# ── Run all tests ──────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("FLUX ISA v3 — Test Suite")
    print("=" * 60)

    test_factorial()
    test_fibonacci()
    test_vector_add()
    test_float_sqrt()
    test_call_return()
    test_memory_loadstore()
    test_comparisons()
    test_bitwise()
    test_float_ops()
    test_vector_dot()
    test_conversions()
    test_stack()
    test_jz()
    test_imod()
    test_bxx_ops()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed! ✅")
        sys.exit(0)

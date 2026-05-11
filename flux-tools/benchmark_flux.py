#!/usr/bin/env python3
"""
FLUX VM Performance Optimization — Benchmark Suite
====================================================
Profiles the original VM, applies optimizations, and benchmarks both.
"""

import time
import struct
import sys
import os
import math
from typing import Optional

# Add parent to path so we can import flux_vm
sys.path.insert(0, os.path.dirname(__file__))
from flux_vm import FluxVM, to_signed32, to_unsigned32, MEMORY_SIZE, STACK_BASE, MAX_CYCLES, VECTOR_SIZE

# ── Benchmark bytecode builders ─────────────────────────────────

def build_factorial_bytecode(n):
    """Build bytecode for factorial(n).
    
    R0 = n (input)
    R1 = result
    R2 = counter
    R3 = temp
    
    MOVI R1, 1        ; result = 1
    IMOV R2, R0       ; counter = n
    ; loop:
    IMUL R1, R1, R2   ; result *= counter
    IDEC R2, 1        ; counter--
    ICMPEQ R3, R2, R0 ; temp = (counter == 0)... no, compare with 0
    ; Actually: check if R2 == 0
    MOVI R3, 0
    ICMPEQ R3, R2, R3 ; R3 = (R2 == 0) ? 1 : 0
    JZ R3, -20        ; if R3==0 (counter != 0), jump back to loop
    HALT
    """
    bc = bytearray()
    
    # MOVI R1, 1
    bc.extend([0xFE, 1])  
    bc.extend(struct.pack('<h', 1))
    
    # IMOV R2, R0  (opcode 0x20, rd=2, rs=0)
    bc.extend([0x20, 2, 0])
    
    # MOVI R3, 0
    bc.extend([0xFE, 3])
    bc.extend(struct.pack('<h', 0))
    
    loop_start = len(bc)
    
    # IMUL R1, R1, R2 (opcode 0x23)
    bc.extend([0x23, 1, 1, 2])
    
    # IDEC R2, 1 (opcode 0x29, rd=2, imm=1)
    bc.extend([0x29, 2])
    bc.extend(struct.pack('<h', 1))
    
    # ICMPEQ R3, R2, zero_reg -> compare R2 with 0
    # We use R3 as temp and compare R2 with R4 (which is 0)
    # MOVI R4, 0
    bc.extend([0xFE, 4])
    bc.extend(struct.pack('<h', 0))
    # ICMPEQ R3, R2, R4
    bc.extend([0x32, 3, 2, 4])
    
    # JZ R3, offset -> jump back to loop_start
    # JZ: opcode 0x05, length=3, reg=R3, offset16 (relative to PC after this instr)
    jz_addr = len(bc)
    next_pc = jz_addr + 5  # JZ is 5 bytes
    offset = loop_start - next_pc
    bc.extend([0x05, 3, 3])
    bc.extend(struct.pack('<h', offset))
    
    # HALT
    bc.extend([0x00])
    
    return bytes(bc), n

def build_fibonacci_bytecode(n):
    """Build bytecode for fibonacci(n) - iterative.
    R0 = n (input)
    R1 = a = 0
    R2 = b = 1  
    R3 = temp
    R4 = counter
    R5 = zero
    """
    bc = bytearray()
    
    # MOVI R1, 0  (a = 0)
    bc.extend([0xFE, 1])
    bc.extend(struct.pack('<h', 0))
    
    # MOVI R2, 1  (b = 1)
    bc.extend([0xFE, 2])
    bc.extend(struct.pack('<h', 1))
    
    # MOVI R4, 0  (counter = 0)
    bc.extend([0xFE, 4])
    bc.extend(struct.pack('<h', 0))
    
    # MOVI R5, 0  (zero constant)
    bc.extend([0xFE, 5])
    bc.extend(struct.pack('<h', 0))
    
    # ICMPEQ R3, R4, R0  (counter == n?)
    # loop_start:
    loop_start = len(bc)
    bc.extend([0x32, 3, 4, 0])  # ICMPEQ R3, R4, R0
    
    # JNZ R3, done  (if counter==n, done)
    jnz_addr = len(bc)
    # We'll patch this later
    bc.extend([0x04, 3, 3])
    bc.extend(struct.pack('<h', 0))  # placeholder
    
    # IMOV R3, R2   (temp = b)
    bc.extend([0x20, 3, 2])
    
    # IADD R2, R1, R2  (b = a + b)
    bc.extend([0x21, 2, 1, 2])
    
    # IMOV R1, R3   (a = temp)
    bc.extend([0x20, 1, 3])
    
    # IINC R4, 1    (counter++)
    bc.extend([0x28, 4])
    bc.extend(struct.pack('<h', 1))
    
    # JUMP back to loop_start
    jmp_addr = len(bc)
    next_pc = jmp_addr + 4  # JUMP is 4 bytes
    offset = loop_start - next_pc
    bc.extend([0x03, 2])
    bc.extend(struct.pack('<h', offset))
    
    # done: HALT
    done_addr = len(bc)
    # Patch JNZ offset
    jnz_next_pc = jnz_addr + 5
    patch_offset = done_addr - jnz_next_pc
    struct.pack_into('<h', bc, jnz_addr + 3, patch_offset)
    
    bc.extend([0x00])  # HALT
    
    return bytes(bc), n


def build_memcpy_bytecode(size_bytes):
    """Build bytecode for memcpy(size_bytes) - copies memory region.
    R0 = src address
    R1 = dst address  
    R2 = counter
    R3 = bytes remaining
    R4 = temp byte
    R5 = zero
    """
    bc = bytearray()
    
    src_addr = 0x2000  # Source at 8KB
    dst_addr = 0x4000  # Dest at 16KB
    
    # MOVI R0, src_addr
    bc.extend([0xFE, 0])
    bc.extend(struct.pack('<h', src_addr & 0xFFFF))
    
    # MOVI R1, dst_addr
    bc.extend([0xFE, 1])
    bc.extend(struct.pack('<h', dst_addr & 0xFFFF))
    
    # MOVI R2, 0 (counter)
    bc.extend([0xFE, 2])
    bc.extend(struct.pack('<h', 0))
    
    # MOVI R5, 0 (zero)
    bc.extend([0xFE, 5])
    bc.extend(struct.pack('<h', 0))
    
    # We'll copy 4 bytes at a time (LOAD32/STORE32)
    # Number of iterations = size_bytes // 4
    iterations = size_bytes // 4
    
    # MOVI R3, iterations
    bc.extend([0xFE, 3])
    bc.extend(struct.pack('<h', min(iterations, 32767)))
    
    # loop_start:
    loop_start = len(bc)
    
    # ICMPEQ R4, R2, R3  (counter == total?)
    bc.extend([0x32, 4, 2, 3])
    
    # JNZ R4, done
    jnz_addr = len(bc)
    bc.extend([0x04, 3, 4])
    bc.extend(struct.pack('<h', 0))  # placeholder
    
    # LOAD32 R4, R0, 0  (load from src + counter*4)
    # Actually we need src + counter*4. Let's compute addr.
    # For simplicity, use offset as counter*4... but offset16 is limited.
    # Instead: compute R6 = R0 + R2*4 manually
    # Simplified: LOAD32 R4, R0, 0  then STORE32 R4, R1, 0 then inc ptrs
    
    # LOAD32 R4, R0, 0
    bc.extend([0x72, 4, 0])  # LOAD32 R4, [R0+0]
    bc.extend(struct.pack('<H', 0))
    
    # STORE32 R4, R1, 0
    bc.extend([0x76, 4, 1])  # STORE32 R4, [R1+0]
    bc.extend(struct.pack('<H', 0))
    
    # IINC R0, 4  (src += 4)
    bc.extend([0x28, 0])
    bc.extend(struct.pack('<h', 4))
    
    # IINC R1, 4  (dst += 4)
    bc.extend([0x28, 1])
    bc.extend(struct.pack('<h', 4))
    
    # IINC R2, 1  (counter++)
    bc.extend([0x28, 2])
    bc.extend(struct.pack('<h', 1))
    
    # JUMP back
    jmp_addr = len(bc)
    next_pc = jmp_addr + 4
    offset = loop_start - next_pc
    bc.extend([0x03, 2])
    bc.extend(struct.pack('<h', offset))
    
    done_addr = len(bc)
    # Patch JNZ
    jnz_next_pc = jnz_addr + 5
    patch_offset = done_addr - jnz_next_pc
    struct.pack_into('<h', bc, jnz_addr + 3, patch_offset)
    
    bc.extend([0x00])  # HALT
    
    return bytes(bc), size_bytes


def build_dotproduct_bytecode(iterations):
    """Build bytecode for vector dot product × iterations.
    Uses VDOT instruction.
    """
    bc = bytearray()
    
    vec_addr = 0x3000  # Vector A at 12KB
    vec_b_addr = 0x3200  # Vector B at ~12.5KB
    
    # R0 = result accumulator
    # R1 = loop counter
    # R2 = total iterations
    # R3 = temp
    
    # MOVI R0, 0  (result)
    bc.extend([0xFE, 0])
    bc.extend(struct.pack('<h', 0))
    
    # MOVI R1, 0  (counter)
    bc.extend([0xFE, 1])
    bc.extend(struct.pack('<h', 0))
    
    # MOVI R2, iterations
    bc.extend([0xFE, 2])
    bc.extend(struct.pack('<h', min(iterations, 32767)))
    
    # MOVI R3, 0  (zero)
    bc.extend([0xFE, 3])
    bc.extend(struct.pack('<h', 0))
    
    # loop_start:
    loop_start = len(bc)
    
    # ICMPEQ R4, R1, R2
    bc.extend([0x32, 4, 1, 2])
    
    # JNZ R4, done
    jnz_addr = len(bc)
    bc.extend([0x04, 3, 4])
    bc.extend(struct.pack('<h', 0))
    
    # VLOAD V0, R5, 0  (load vec A)  - but R5 doesn't have vec_addr
    # Let's use LOADADDR to get vec base
    
    # MOVI R5, vec_addr
    bc.extend([0xFE, 5])
    bc.extend(struct.pack('<h', vec_addr & 0xFFFF))
    
    # MOVI R6, vec_b_addr
    bc.extend([0xFE, 6])
    bc.extend(struct.pack('<h', vec_b_addr & 0xFFFF))
    
    # VLOAD V0, R5, 0
    bc.extend([0xB0, 0, 5])
    bc.extend(struct.pack('<H', 0))
    
    # VLOAD V1, R6, 0
    bc.extend([0xB0, 1, 6])
    bc.extend(struct.pack('<H', 0))
    
    # VDOT R4, V0, V1  (R4 = dot product)
    bc.extend([0xB4, 4, 0, 1])
    
    # IADD R0, R0, R4  (accumulate)
    bc.extend([0x21, 0, 0, 4])
    
    # IINC R1, 1
    bc.extend([0x28, 1])
    bc.extend(struct.pack('<h', 1))
    
    # JUMP back
    jmp_addr = len(bc)
    next_pc = jmp_addr + 4
    offset = loop_start - next_pc
    bc.extend([0x03, 2])
    bc.extend(struct.pack('<h', offset))
    
    done_addr = len(bc)
    jnz_next_pc = jnz_addr + 5
    struct.pack_into('<h', bc, jnz_addr + 3, done_addr - jnz_next_pc)
    
    bc.extend([0x00])  # HALT
    
    return bytes(bc), iterations


def build_bloomfilter_bytecode(checks):
    """Build bytecode for bloom filter check × checks.
    Heavy bitwise ops.
    R0 = hash value
    R1 = filter bits (simulated as single int)
    R2 = mask
    R3 = result (1=probably present, 0=absent)
    R4 = counter
    R5 = iterations
    """
    bc = bytearray()
    
    # Initialize
    bc.extend([0xFE, 1])  # MOVI R1, 0x5555
    bc.extend(struct.pack('<h', 0x5555))
    bc.extend([0xFE, 0])  # MOVI R0, 0x2AAA
    bc.extend(struct.pack('<h', 0x2AAA))
    bc.extend([0xFE, 4])  # MOVI R4, 0 (counter)
    bc.extend(struct.pack('<h', 0))
    bc.extend([0xFE, 5])  # MOVI R5, checks
    bc.extend(struct.pack('<h', min(checks, 32767)))
    bc.extend([0xFE, 6])  # MOVI R6, 0 (zero)
    bc.extend(struct.pack('<h', 0))
    
    # loop_start:
    loop_start = len(bc)
    
    # ICMPEQ R7, R4, R5  (done?)
    bc.extend([0x32, 7, 4, 5])
    
    # JNZ R7, done
    jnz_addr = len(bc)
    bc.extend([0x04, 3, 7])
    bc.extend(struct.pack('<h', 0))
    
    # R2 = R0  (copy hash)
    bc.extend([0x20, 2, 0])
    
    # BSHL R2, R2, R4
    bc.extend([0xA3, 2, 2, 4])
    
    # BAND R3, R1, R2
    bc.extend([0xA0, 3, 1, 2])
    
    # BXOR R0, R0, R2
    bc.extend([0xA2, 0, 0, 2])
    
    # BOR R1, R1, R0
    bc.extend([0xA1, 1, 1, 0])
    
    # IINC R4, 1
    bc.extend([0x28, 4])
    bc.extend(struct.pack('<h', 1))
    
    # JUMP back
    jmp_addr = len(bc)
    next_pc = jmp_addr + 4
    offset = loop_start - next_pc
    bc.extend([0x03, 2])
    bc.extend(struct.pack('<h', offset))
    
    done_addr = len(bc)
    jnz_next_pc = jnz_addr + 5
    struct.pack_into('<h', bc, jnz_addr + 3, done_addr - jnz_next_pc)
    
    bc.extend([0x00])  # HALT
    
    return bytes(bc), checks


# ── Original VM benchmark ──────────────────────────────────────

def benchmark_original(name, bytecode, input_val, iterations=100):
    """Benchmark the original FluxVM."""
    times = []
    total_cycles = 0
    
    for _ in range(iterations):
        vm = FluxVM(debug=False)
        vm.load_bytecode(bytecode)
        vm.gp[0] = input_val  # Set input register
        # Set up zero register
        vm.gp[14] = 0  # R14 = TP (zero reg)
        
        t0 = time.perf_counter()
        err = vm.run()
        t1 = time.perf_counter()
        
        times.append(t1 - t0)
        total_cycles = vm.cycles
    
    avg = sum(times) / len(times)
    total = sum(times)
    ops_per_sec = total_cycles / avg if avg > 0 else 0
    
    return {
        'name': name,
        'avg_s': avg,
        'total_s': total,
        'cycles': total_cycles,
        'ops_per_sec': ops_per_sec,
        'result': vm.gp[0] if iterations > 0 else 0,
        'iterations': iterations,
    }


# ── Optimized VM ────────────────────────────────────────────────

class FluxVMOptimized:
    """Optimized FLUX ISA v3 Virtual Machine."""
    
    __slots__ = (
        'gp', 'fp_regs', 'vec', 'memory', 'pc', 'halted', 'cycles',
        'error', 'trace', 'debug', 'func_table', 'a2a_messages',
        'agent_trust', '_dispatch', '_loop_cache', '_loop_counts',
        '_memory_int',
    )
    
    def __init__(self, debug: bool = False):
        self.gp = [0] * 16
        self.fp_regs = [0.0] * 16
        self.vec = [[0] * VECTOR_SIZE for _ in range(16)]
        self.memory = bytearray(MEMORY_SIZE)
        self._memory_int = None  # Will be memoryview for fast 32-bit access
        self.pc = 0
        self.halted = False
        self.cycles = 0
        self.debug = debug
        self.trace = []
        self.error = 0  # FLUX_OK
        self.func_table = {}
        self.a2a_messages = []
        self.agent_trust = {}
        self._loop_cache = {}  # addr → compiled Python function
        self._loop_counts = {}  # addr → count of back-jump executions
        
        # Initialize SP
        self.gp[11] = STACK_BASE
        
        # Build dispatch table
        self._dispatch = [None] * 256
        self._build_dispatch()
    
    def _build_dispatch(self):
        """Build opcode dispatch table."""
        d = self._dispatch
        # We'll use method references for each opcode
        # But for maximum speed, we inline everything in step()
        pass
    
    # ── Register aliases (property-free for speed) ──
    # Access gp[11] directly instead of through properties
    
    def set_flags_zsvc(self, result, a=0, b=0, is_sub=False):
        result32 = result & 0xFFFFFFFF
        f = 0
        if result32 == 0: f |= 1
        if result32 & 0x80000000: f |= 2
        ua, ub = a & 0xFFFFFFFF, b & 0xFFFFFFFF
        if is_sub:
            if ua < ub: f |= 4
        else:
            if ua + ub > 0xFFFFFFFF: f |= 4
        sa = a if a < 0x80000000 else a - 0x100000000
        sb = b if b < 0x80000000 else b - 0x100000000
        sr = result if result < 0x80000000 else result - 0x100000000
        if is_sub:
            if (sa > 0 and sb < 0 and sr < 0) or (sa < 0 and sb > 0 and sr > 0): f |= 8
        else:
            if (sa > 0 and sb > 0 and sr < 0) or (sa < 0 and sb < 0 and sr > 0): f |= 8
        self.gp[13] = f
    
    def set_flags_zs(self, result):
        result32 = result & 0xFFFFFFFF
        f = 0
        if result32 == 0: f |= 1
        if result32 & 0x80000000: f |= 2
        self.gp[13] = f
    
    def set_flag_z(self, val):
        self.gp[13] = 1 if val else 0
    
    def push32(self, val):
        self.gp[11] -= 4
        sp = self.gp[11]
        m = self.memory
        m[sp] = val & 0xFF
        m[sp+1] = (val >> 8) & 0xFF
        m[sp+2] = (val >> 16) & 0xFF
        m[sp+3] = (val >> 24) & 0xFF
    
    def pop32(self):
        sp = self.gp[11]
        m = self.memory
        val = m[sp] | (m[sp+1] << 8) | (m[sp+2] << 16) | (m[sp+3] << 24)
        self.gp[11] = sp + 4
        if val >= 0x80000000:
            val -= 0x100000000
        return val
    
    def load_binary(self, data: bytes):
        if data[:4] == b'FLUX':
            self._load_fbx(data)
        else:
            m = self.memory
            for i, b in enumerate(data):
                if i < MEMORY_SIZE:
                    m[i] = b
            self.pc = 0
    
    def _load_fbx(self, data: bytes):
        entry_func = struct.unpack_from('<I', data, 8)[0]
        offset = 16
        while offset + 4 <= len(data):
            name_len = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            if name_len == 0 or offset + name_len + 8 > len(data):
                break
            offset += name_len
            addr = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            offset += 4  # local_regs + max_stack
        
        bytecode_start = offset
        m = self.memory
        for i in range(bytecode_start, len(data)):
            m[i - bytecode_start] = data[i]
        
        if entry_func in self.func_table:
            self.pc = self.func_table[entry_func][1]
        else:
            self.pc = 0
    
    def load_bytecode(self, bytecode: bytes, pc_start: int = 0):
        m = self.memory
        for i, b in enumerate(bytecode):
            m[pc_start + i] = b
        self.pc = pc_start
    
    def step(self) -> int:
        """Execute one instruction — optimized dispatch."""
        if self.halted:
            return 1  # FLUX_ERR_HALT
        
        gp = self.gp
        m = self.memory
        pc = self.pc
        cycles = self.cycles + 1
        
        if cycles > MAX_CYCLES:
            self.cycles = cycles
            return 11  # FLUX_ERR_CYCLE
        
        opcode = m[pc]
        pc += 1
        
        # Fast path for most common opcodes
        # IMOV (0x20) - 2 regs
        if opcode == 0x20:
            rd = m[pc]; rs = m[pc+1]
            gp[rd] = gp[rs]
            self.pc = pc + 2; self.cycles = cycles
            return 0
        
        # IADD (0x21) - 3 regs
        if opcode == 0x21:
            rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
            result = (gp[ra] + gp[rb])
            result = result if result < 0x80000000 and result >= -0x80000000 else (result & 0xFFFFFFFF) - (0x100000000 if result & 0x80000000 else 0)
            # Simpler to_signed32
            result = ((gp[ra] + gp[rb]) + 0x80000000) & 0xFFFFFFFF
            if result >= 0x80000000:
                result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, gp[ra], gp[rb])
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # HALT (0x00)
        if opcode == 0x00:
            self.halted = True
            self.pc = pc; self.cycles = cycles
            return 1
        
        # NOP (0x01)
        if opcode == 0x01:
            self.pc = pc; self.cycles = cycles
            return 0
        
        # MOVI (0xFE) - pseudo
        if opcode == 0xFE:
            rd = m[pc]
            imm = m[pc+1] | (m[pc+2] << 8)
            if imm >= 0x8000:
                imm -= 0x10000
            gp[rd] = imm
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # ICMPEQ (0x32)
        if opcode == 0x32:
            rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
            result = 1 if gp[ra] == gp[rb] else 0
            gp[rd] = result
            self.gp[13] = 0 if result else 1  # Z flag inverted
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # JZ (0x05) - conditional jump
        if opcode == 0x05:
            # length = m[pc], reg = m[pc+1], offset = m[pc+2]|(m[pc+3]<<8)
            _length = m[pc]
            reg = m[pc+1]
            offset = m[pc+2] | (m[pc+3] << 8)
            if offset >= 0x8000:
                offset -= 0x10000
            pc += 4  # past length+reg+offset
            if gp[reg] == 0:
                pc += offset
            self.pc = pc; self.cycles = cycles
            return 0
        
        # JNZ (0x04)
        if opcode == 0x04:
            _length = m[pc]
            reg = m[pc+1]
            offset = m[pc+2] | (m[pc+3] << 8)
            if offset >= 0x8000:
                offset -= 0x10000
            pc += 4
            if gp[reg] != 0:
                pc += offset
            self.pc = pc; self.cycles = cycles
            return 0
        
        # JUMP (0x03)
        if opcode == 0x03:
            _length = m[pc]
            offset = m[pc+1] | (m[pc+2] << 8)
            if offset >= 0x8000:
                offset -= 0x10000
            pc += 3 + offset
            self.pc = pc; self.cycles = cycles
            return 0
        
        # IMUL (0x23)
        if opcode == 0x23:
            rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
            result = ((gp[ra] * gp[rb]) & 0xFFFFFFFF)
            if result >= 0x80000000:
                result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, gp[ra], gp[rb])
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # ISUB (0x22)
        if opcode == 0x22:
            rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
            result = ((gp[ra] - gp[rb]) & 0xFFFFFFFF)
            if result >= 0x80000000:
                result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, gp[ra], gp[rb], is_sub=True)
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # IINC (0x28)
        if opcode == 0x28:
            rd = m[pc]
            imm = m[pc+1] | (m[pc+2] << 8)
            if imm >= 0x8000:
                imm -= 0x10000
            old = gp[rd]
            result = ((old + imm) & 0xFFFFFFFF)
            if result >= 0x80000000:
                result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, old, imm)
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # IDEC (0x29)
        if opcode == 0x29:
            rd = m[pc]
            imm = m[pc+1] | (m[pc+2] << 8)
            if imm >= 0x8000:
                imm -= 0x10000
            old = gp[rd]
            result = ((old - imm) & 0xFFFFFFFF)
            if result >= 0x80000000:
                result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, old, imm, is_sub=True)
            self.pc = pc + 3; self.cycles = cycles
            return 0
        
        # LOAD32 (0x72)
        if opcode == 0x72:
            rd = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            val = m[addr] | (m[addr+1] << 8) | (m[addr+2] << 16) | (m[addr+3] << 24)
            if val >= 0x80000000:
                val -= 0x100000000
            gp[rd] = val
            self.pc = pc + 4; self.cycles = cycles
            return 0
        
        # STORE32 (0x76)
        if opcode == 0x76:
            rs = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            val = gp[rs] & 0xFFFFFFFF
            m[addr] = val & 0xFF
            m[addr+1] = (val >> 8) & 0xFF
            m[addr+2] = (val >> 16) & 0xFF
            m[addr+3] = (val >> 24) & 0xFF
            self.pc = pc + 4; self.cycles = cycles
            return 0
        
        # RET (0x02)
        if opcode == 0x02:
            self.pc = gp[15] & 0xFFFFFFFF
            self.cycles = cycles
            return 0
        
        # PUSH (0x10)
        if opcode == 0x10:
            rd = m[pc]; rs = m[pc+1]
            gp[11] -= 4
            sp = gp[11]
            val = gp[rs] & 0xFFFFFFFF
            m[sp] = val & 0xFF
            m[sp+1] = (val >> 8) & 0xFF
            m[sp+2] = (val >> 16) & 0xFF
            m[sp+3] = (val >> 24) & 0xFF
            self.pc = pc + 2; self.cycles = cycles
            return 0
        
        # POP (0x11)
        if opcode == 0x11:
            rd = m[pc]; pc += 1  # skip dummy byte
            sp = gp[11]
            val = m[sp] | (m[sp+1] << 8) | (m[sp+2] << 16) | (m[sp+3] << 24)
            if val >= 0x80000000:
                val -= 0x100000000
            gp[rd] = val
            gp[11] = sp + 4
            self.pc = pc + 1; self.cycles = cycles
            return 0
        
        # ── Remaining opcodes: fallthrough to full handler ──
        self.pc = pc
        self.cycles = cycles
        return self._step_slow(opcode)
    
    def _step_slow(self, opcode):
        """Handle less common opcodes."""
        gp = self.gp
        m = self.memory
        pc = self.pc
        
        # IDIV (0x24)
        if opcode == 0x24:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            if gp[rb] == 0:
                return 3
            result = int(gp[ra] / gp[rb])
            result = (result + 0x80000000) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, gp[ra], gp[rb], is_sub=True)
            self.pc = pc + 3; return 0
        
        # IMOD (0x25)
        if opcode == 0x25:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            if gp[rb] == 0: return 3
            result = (gp[ra] % gp[rb]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zsvc(result, gp[ra], gp[rb])
            self.pc = pc + 3; return 0
        
        # INEG (0x26)
        if opcode == 0x26:
            rd = m[pc]; ra = m[pc+1]
            result = (-gp[ra]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # IABS (0x27)
        if opcode == 0x27:
            rd = m[pc]; ra = m[pc+1]
            result = abs(gp[ra])
            result = result & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # IMIN (0x2A)
        if opcode == 0x2A:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = min(gp[ra], gp[rb])
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # IMAX (0x2B)
        if opcode == 0x2B:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = max(gp[ra], gp[rb])
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # IAND (0x2C)
        if opcode == 0x2C:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] & gp[rb])
            result = result & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # IOR (0x2D)
        if opcode == 0x2D:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] | gp[rb]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # IXOR (0x2E)
        if opcode == 0x2E:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] ^ gp[rb]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # ISHL (0x2F)
        if opcode == 0x2F:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = ((gp[ra] << (gp[rb] & 31)) & 0xFFFFFFFF)
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # ISHR (0x30)
        if opcode == 0x30:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] >> (gp[rb] & 31)) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # INOT (0x31)
        if opcode == 0x31:
            rd = m[pc]; ra = m[pc+1]
            result = (~gp[ra]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # ICMPNE (0x33)
        if opcode == 0x33:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if gp[ra] != gp[rb] else 0
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # ICMPLT (0x34)
        if opcode == 0x34:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if gp[ra] < gp[rb] else 0
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # ICMPLE (0x35)
        if opcode == 0x35:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if gp[ra] <= gp[rb] else 0
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # ICMPGT (0x36)
        if opcode == 0x36:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if gp[ra] > gp[rb] else 0
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # ICMPGE (0x37)
        if opcode == 0x37:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if gp[ra] >= gp[rb] else 0
            gp[rd] = result
            self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # Float ops
        fp = self.fp_regs
        
        # FMOV (0x40)
        if opcode == 0x40:
            rd, rs = m[pc], m[pc+1]
            fp[rd] = fp[rs]
            self.pc = pc + 2; return 0
        
        # FADD (0x41)
        if opcode == 0x41:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = fp[ra] + fp[rb]
            self.pc = pc + 3; return 0
        
        # FSUB (0x42)
        if opcode == 0x42:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = fp[ra] - fp[rb]
            self.pc = pc + 3; return 0
        
        # FMUL (0x43)
        if opcode == 0x43:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = fp[ra] * fp[rb]
            self.pc = pc + 3; return 0
        
        # FDIV (0x44)
        if opcode == 0x44:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = fp[ra] / fp[rb] if fp[rb] != 0.0 else float('inf')
            self.pc = pc + 3; return 0
        
        # FMOD (0x45)
        if opcode == 0x45:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = math.fmod(fp[ra], fp[rb])
            self.pc = pc + 3; return 0
        
        # FNEG (0x46)
        if opcode == 0x46:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = -fp[ra]
            self.pc = pc + 3; return 0
        
        # FABS (0x47)
        if opcode == 0x47:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = abs(fp[ra])
            self.pc = pc + 3; return 0
        
        # FSQRT (0x48)
        if opcode == 0x48:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.sqrt(fp[ra]) if fp[ra] >= 0 else float('nan')
            self.pc = pc + 3; return 0
        
        # FFLOOR (0x49) through FLOG (0x51)
        if opcode == 0x49:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.floor(fp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x4A:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.ceil(fp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x4B:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = round(fp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x4C:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = min(fp[ra], fp[rb])
            self.pc = pc + 3; return 0
        if opcode == 0x4D:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            fp[rd] = max(fp[ra], fp[rb])
            self.pc = pc + 3; return 0
        if opcode == 0x4E:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.sin(fp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x4F:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.cos(fp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x50:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.exp(fp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x51:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = math.log(fp[ra])
            self.pc = pc + 3; return 0
        
        # Float comparisons (0x54-0x59)
        if opcode == 0x54:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if fp[ra] == fp[rb] else 0
            gp[rd] = result; self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        if opcode == 0x55:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if fp[ra] != fp[rb] else 0
            gp[rd] = result; self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        if opcode == 0x56:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if fp[ra] < fp[rb] else 0
            gp[rd] = result; self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        if opcode == 0x57:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if fp[ra] <= fp[rb] else 0
            gp[rd] = result; self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        if opcode == 0x58:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if fp[ra] > fp[rb] else 0
            gp[rd] = result; self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        if opcode == 0x59:
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = 1 if fp[ra] >= fp[rb] else 0
            gp[rd] = result; self.set_flag_z(result == 0)
            self.pc = pc + 3; return 0
        
        # Conversions (0x60-0x63)
        if opcode == 0x60:
            rd = m[pc]; ra = m[pc+1]
            fp[rd] = float(gp[ra])
            self.pc = pc + 3; return 0
        if opcode == 0x61:
            rd = m[pc]; ra = m[pc+1]
            result = int(fp[ra])
            result = (result + 0x80000000) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.pc = pc + 3; return 0
        if opcode == 0x62:
            rd = m[pc]; ra = m[pc+1]
            gp[rd] = 1 if gp[ra] != 0 else 0
            self.pc = pc + 3; return 0
        if opcode == 0x63:
            rd = m[pc]; ra = m[pc+1]
            gp[rd] = 1 if gp[ra] else 0
            self.pc = pc + 3; return 0
        
        # Memory ops (0x70-0x79)
        if opcode == 0x70:  # LOAD8
            rd = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            gp[rd] = m[(gp[rb] + off) & 0xFFFF]
            self.pc = pc + 4; return 0
        if opcode == 0x71:  # LOAD16
            rd = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            gp[rd] = m[addr] | (m[addr+1] << 8)
            self.pc = pc + 4; return 0
        if opcode == 0x73:  # LOAD64
            rd = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            val = m[addr] | (m[addr+1] << 8) | (m[addr+2] << 16) | (m[addr+3] << 24)
            if val >= 0x80000000: val -= 0x100000000
            gp[rd] = val
            self.pc = pc + 4; return 0
        if opcode == 0x74:  # STORE8
            rs = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            m[(gp[rb] + off) & 0xFFFF] = gp[rs] & 0xFF
            self.pc = pc + 4; return 0
        if opcode == 0x75:  # STORE16
            rs = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            val = gp[rs] & 0xFFFF
            m[addr] = val & 0xFF; m[addr+1] = (val >> 8) & 0xFF
            self.pc = pc + 4; return 0
        if opcode == 0x77:  # STORE64
            rs = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            val = gp[rs] & 0xFFFFFFFF
            m[addr] = val & 0xFF; m[addr+1] = (val >> 8) & 0xFF
            m[addr+2] = (val >> 16) & 0xFF; m[addr+3] = (val >> 24) & 0xFF
            self.pc = pc + 4; return 0
        if opcode == 0x78:  # LOADADDR
            rd = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            gp[rd] = gp[rb] + off
            self.pc = pc + 4; return 0
        if opcode == 0x79:  # STACKALLOC
            rd = m[pc]
            size = m[pc+1] | (m[pc+2] << 8)
            if size >= 0x8000: size -= 0x10000
            gp[11] -= size
            gp[rd] = gp[11]
            self.pc = pc + 3; return 0
        
        # DUP (0x12)
        if opcode == 0x12:
            rd, rs = m[pc], m[pc+1]
            gp[rd] = gp[rs]
            self.pc = pc + 2; return 0
        
        # SWAP (0x13)
        if opcode == 0x13:
            ra, rb = m[pc], m[pc+1]
            gp[ra], gp[rb] = gp[rb], gp[ra]
            self.pc = pc + 2; return 0
        
        # CALL (0x06)
        if opcode == 0x06:
            _length = m[pc]
            func_idx = m[pc+1] | (m[pc+2] << 8)
            gp[15] = pc + 3  # LR = next PC
            self.push32(pc + 3)
            if func_idx in self.func_table:
                self.pc = self.func_table[func_idx][1]
            else:
                self.pc = func_idx
            return 0
        
        # CALLINDIRECT (0x07)
        if opcode == 0x07:
            _length = m[pc]; reg = m[pc+1]
            gp[15] = pc + 2
            self.push32(pc + 2)
            self.pc = gp[reg] & 0xFFFFFFFF
            return 0
        
        # YIELD/PANIC/UNREACHABLE
        if opcode == 0x08:
            self.pc = pc; return 0
        if opcode == 0x09:
            self.halted = True; self.pc = pc; return 2
        if opcode == 0x0A:
            self.halted = True; self.pc = pc; return 2
        
        # A2A stubs (0x80-0x89) — just skip payload
        if 0x80 <= opcode <= 0x89:
            length = m[pc]
            self.pc = pc + 1 + length
            return 0
        
        # Bitwise (0xA0-0xA5)
        if opcode == 0xA0:  # BAND
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] & gp[rb]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result; self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        if opcode == 0xA1:  # BOR
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] | gp[rb]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result; self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        if opcode == 0xA2:  # BXOR
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = (gp[ra] ^ gp[rb]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result; self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        if opcode == 0xA3:  # BSHL
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = ((gp[ra] << (gp[rb] & 31)) & 0xFFFFFFFF)
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.pc = pc + 3; return 0
        if opcode == 0xA4:  # BSHR
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = ((gp[ra] & 0xFFFFFFFF) >> (gp[rb] & 31))
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.pc = pc + 3; return 0
        if opcode == 0xA5:  # BNOT
            rd = m[pc]; ra = m[pc+1]
            result = (~gp[ra]) & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result; self.set_flags_zs(result)
            self.pc = pc + 3; return 0
        
        # Vector/SIMD (0xB0-0xB4)
        vec = self.vec
        if opcode == 0xB0:  # VLOAD
            rd = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            for i in range(VECTOR_SIZE):
                a = addr + i * 4
                val = m[a] | (m[a+1] << 8) | (m[a+2] << 16) | (m[a+3] << 24)
                if val >= 0x80000000: val -= 0x100000000
                vec[rd][i] = val
            self.pc = pc + 4; return 0
        if opcode == 0xB1:  # VSTORE
            rs = m[pc]; rb = m[pc+1]
            off = m[pc+2] | (m[pc+3] << 8)
            addr = (gp[rb] + off) & 0xFFFF
            for i in range(VECTOR_SIZE):
                a = addr + i * 4
                val = vec[rs][i] & 0xFFFFFFFF
                m[a] = val & 0xFF; m[a+1] = (val >> 8) & 0xFF
                m[a+2] = (val >> 16) & 0xFF; m[a+3] = (val >> 24) & 0xFF
            self.pc = pc + 4; return 0
        if opcode == 0xB2:  # VADD
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            for i in range(VECTOR_SIZE):
                result = (vec[ra][i] + vec[rb][i]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                vec[rd][i] = result
            self.pc = pc + 3; return 0
        if opcode == 0xB3:  # VMUL
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            for i in range(VECTOR_SIZE):
                result = (vec[ra][i] * vec[rb][i]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                vec[rd][i] = result
            self.pc = pc + 3; return 0
        if opcode == 0xB4:  # VDOT
            rd, ra, rb = m[pc], m[pc+1], m[pc+2]
            result = sum(vec[ra][i] * vec[rb][i] for i in range(VECTOR_SIZE))
            result = result & 0xFFFFFFFF
            if result >= 0x80000000: result -= 0x100000000
            gp[rd] = result
            self.pc = pc + 3; return 0
        
        # Type/Meta (0x90-0x92)
        if opcode == 0x90:
            rd = m[pc]; ra = m[pc+1]
            gp[rd] = gp[ra]
            self.pc = pc + 3; return 0
        if opcode == 0x91:
            rd = m[pc]; self.gp[rd] = 4
            self.pc = pc + 3; return 0
        if opcode == 0x92:
            rd = m[pc]; self.gp[rd] = 1
            self.pc = pc + 3; return 0
        
        # Unknown
        self.halted = True
        return 2  # FLUX_ERR_INVALID_OP
    
    def run(self, max_cycles: int = MAX_CYCLES) -> int:
        """Run until HALT or error — tight loop with inlined dispatch."""
        gp = self.gp
        m = self.memory
        pc = self.pc
        cycles = self.cycles
        halted = self.halted
        
        while not halted and cycles < max_cycles:
            opcode = m[pc]
            pc += 1
            cycles += 1
            
            # ── Fast path: most common opcodes first ──
            
            if opcode == 0x00:  # HALT
                halted = True
                break
            
            elif opcode == 0x20:  # IMOV
                rd = m[pc]; rs = m[pc+1]
                gp[rd] = gp[rs]
                pc += 2
            
            elif opcode == 0xFE:  # MOVI
                rd = m[pc]
                imm = m[pc+1] | (m[pc+2] << 8)
                if imm >= 0x8000: imm -= 0x10000
                gp[rd] = imm
                pc += 3
            
            elif opcode == 0x21:  # IADD
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                result = (gp[ra] + gp[rb]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result
                pc += 3
            
            elif opcode == 0x23:  # IMUL
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                result = (gp[ra] * gp[rb]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result
                pc += 3
            
            elif opcode == 0x22:  # ISUB
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                result = (gp[ra] - gp[rb]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result
                pc += 3
            
            elif opcode == 0x32:  # ICMPEQ
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                gp[rd] = 1 if gp[ra] == gp[rb] else 0
                pc += 3
            
            elif opcode == 0x04:  # JNZ
                _len = m[pc]; reg = m[pc+1]
                offset = m[pc+2] | (m[pc+3] << 8)
                if offset >= 0x8000: offset -= 0x10000
                pc += 4
                if gp[reg] != 0:
                    pc += offset
            
            elif opcode == 0x05:  # JZ
                _len = m[pc]; reg = m[pc+1]
                offset = m[pc+2] | (m[pc+3] << 8)
                if offset >= 0x8000: offset -= 0x10000
                pc += 4
                if gp[reg] == 0:
                    pc += offset
            
            elif opcode == 0x03:  # JUMP
                _len = m[pc]
                offset = m[pc+1] | (m[pc+2] << 8)
                if offset >= 0x8000: offset -= 0x10000
                pc += 3 + offset
            
            elif opcode == 0x28:  # IINC
                rd = m[pc]
                imm = m[pc+1] | (m[pc+2] << 8)
                if imm >= 0x8000: imm -= 0x10000
                result = (gp[rd] + imm) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result
                pc += 3
            
            elif opcode == 0x29:  # IDEC
                rd = m[pc]
                imm = m[pc+1] | (m[pc+2] << 8)
                if imm >= 0x8000: imm -= 0x10000
                result = (gp[rd] - imm) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result
                pc += 3
            
            elif opcode == 0x72:  # LOAD32
                rd = m[pc]; rb = m[pc+1]
                off = m[pc+2] | (m[pc+3] << 8)
                addr = (gp[rb] + off) & 0xFFFF
                val = m[addr] | (m[addr+1] << 8) | (m[addr+2] << 16) | (m[addr+3] << 24)
                if val >= 0x80000000: val -= 0x100000000
                gp[rd] = val
                pc += 4
            
            elif opcode == 0x76:  # STORE32
                rs = m[pc]; rb = m[pc+1]
                off = m[pc+2] | (m[pc+3] << 8)
                addr = (gp[rb] + off) & 0xFFFF
                val = gp[rs] & 0xFFFFFFFF
                m[addr] = val & 0xFF
                m[addr+1] = (val >> 8) & 0xFF
                m[addr+2] = (val >> 16) & 0xFF
                m[addr+3] = (val >> 24) & 0xFF
                pc += 4
            
            elif opcode == 0x01:  # NOP
                pass
            
            elif opcode == 0x02:  # RET
                pc = gp[15] & 0xFFFFFFFF
            
            elif opcode == 0x10:  # PUSH
                rd = m[pc]; rs = m[pc+1]
                gp[11] -= 4; sp = gp[11]
                val = gp[rs] & 0xFFFFFFFF
                m[sp] = val & 0xFF; m[sp+1] = (val >> 8) & 0xFF
                m[sp+2] = (val >> 16) & 0xFF; m[sp+3] = (val >> 24) & 0xFF
                pc += 2
            
            elif opcode == 0x11:  # POP
                rd = m[pc]
                sp = gp[11]
                val = m[sp] | (m[sp+1] << 8) | (m[sp+2] << 16) | (m[sp+3] << 24)
                if val >= 0x80000000: val -= 0x100000000
                gp[rd] = val
                gp[11] = sp + 4
                pc += 2
            
            else:
                # Slow path: save state and call _step_slow
                self.pc = pc - 1  # back up to opcode
                self.cycles = cycles - 1
                err = self.step()
                pc = self.pc
                cycles = self.cycles
                halted = self.halted
                if err not in (0, 1):
                    break
        
        self.pc = pc
        self.cycles = cycles
        self.halted = halted
        return 0 if halted else 11
    
    def print_state(self):
        print("── GP Registers ──")
        names = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7',
                 'RV', 'A0', 'A1', 'SP', 'FP', 'FL', 'TP', 'LR']
        for i in range(16):
            print(f"  {names[i]:3s} (R{i:2d}) = {self.gp[i]:12d}  (0x{self.gp[i] & 0xFFFFFFFF:08x})")
        print(f"  PC = 0x{self.pc:04x}  Cycles = {self.cycles}  Halted = {self.halted}")


def benchmark_optimized(name, bytecode, input_val, iterations=100):
    """Benchmark the optimized FluxVM."""
    times = []
    total_cycles = 0
    
    for _ in range(iterations):
        vm = FluxVMOptimized(debug=False)
        vm.load_bytecode(bytecode)
        vm.gp[0] = input_val
        vm.gp[14] = 0  # zero reg
        
        t0 = time.perf_counter()
        err = vm.run()
        t1 = time.perf_counter()
        
        times.append(t1 - t0)
        total_cycles = vm.cycles
    
    avg = sum(times) / len(times)
    total = sum(times)
    ops_per_sec = total_cycles / avg if avg > 0 else 0
    
    return {
        'name': name,
        'avg_s': avg,
        'total_s': total,
        'cycles': total_cycles,
        'ops_per_sec': ops_per_sec,
        'result': vm.gp[0] if iterations > 0 else 0,
        'iterations': iterations,
    }


# ── JIT-Enhanced VM ────────────────────────────────────────────

class FluxVMJIT(FluxVMOptimized):
    """Optimized VM with simple JIT for hot loops."""
    
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self._loop_counts = {}  # target_addr → hit count
        self._loop_cache = {}   # start_addr → compiled function
        self._jit_threshold = 10
    
    def run(self, max_cycles: int = MAX_CYCLES) -> int:
        """Run with JIT for hot loops."""
        gp = self.gp
        m = self.memory
        pc = self.pc
        cycles = self.cycles
        halted = self.halted
        
        while not halted and cycles < max_cycles:
            opcode = m[pc]
            pc += 1
            cycles += 1
            
            # Fast path same as FluxVMOptimized but with JIT detection on jumps
            if opcode == 0x00:  # HALT
                halted = True; break
            elif opcode == 0x20:  # IMOV
                rd = m[pc]; rs = m[pc+1]; gp[rd] = gp[rs]; pc += 2
            elif opcode == 0xFE:  # MOVI
                rd = m[pc]; imm = m[pc+1] | (m[pc+2] << 8)
                if imm >= 0x8000: imm -= 0x10000
                gp[rd] = imm; pc += 3
            elif opcode == 0x21:  # IADD
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                result = (gp[ra] + gp[rb]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result; pc += 3
            elif opcode == 0x23:  # IMUL
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                result = (gp[ra] * gp[rb]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result; pc += 3
            elif opcode == 0x22:  # ISUB
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                result = (gp[ra] - gp[rb]) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result; pc += 3
            elif opcode == 0x32:  # ICMPEQ
                rd = m[pc]; ra = m[pc+1]; rb = m[pc+2]
                gp[rd] = 1 if gp[ra] == gp[rb] else 0; pc += 3
            elif opcode == 0x04:  # JNZ — JIT detection
                _len = m[pc]; reg = m[pc+1]
                offset = m[pc+2] | (m[pc+3] << 8)
                if offset >= 0x8000: offset -= 0x10000
                pc += 4
                if gp[reg] != 0:
                    target = pc + offset
                    # Backwards jump = potential loop
                    if target < pc:
                        count = self._loop_counts.get(target, 0) + 1
                        self._loop_counts[target] = count
                        if count >= self._jit_threshold and target not in self._loop_cache:
                            self._compile_loop(target, pc)
                        if target in self._loop_cache:
                            pc = target
                            self.pc = pc; self.cycles = cycles; self.halted = halted
                            pc, cycles, halted = self._loop_cache[target](gp, m, pc, cycles, max_cycles, self)
                            continue
                    pc += offset
            elif opcode == 0x05:  # JZ — JIT detection
                _len = m[pc]; reg = m[pc+1]
                offset = m[pc+2] | (m[pc+3] << 8)
                if offset >= 0x8000: offset -= 0x10000
                pc += 4
                if gp[reg] == 0:
                    target = pc + offset
                    if target < pc:
                        count = self._loop_counts.get(target, 0) + 1
                        self._loop_counts[target] = count
                        if count >= self._jit_threshold and target not in self._loop_cache:
                            self._compile_loop(target, pc)
                        if target in self._loop_cache:
                            pc = target
                            self.pc = pc; self.cycles = cycles; self.halted = halted
                            pc, cycles, halted = self._loop_cache[target](gp, m, pc, cycles, max_cycles, self)
                            continue
                    pc += offset
            elif opcode == 0x03:  # JUMP
                _len = m[pc]
                offset = m[pc+1] | (m[pc+2] << 8)
                if offset >= 0x8000: offset -= 0x10000
                pc += 3 + offset
            elif opcode == 0x28:  # IINC
                rd = m[pc]; imm = m[pc+1] | (m[pc+2] << 8)
                if imm >= 0x8000: imm -= 0x10000
                result = (gp[rd] + imm) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result; pc += 3
            elif opcode == 0x29:  # IDEC
                rd = m[pc]; imm = m[pc+1] | (m[pc+2] << 8)
                if imm >= 0x8000: imm -= 0x10000
                result = (gp[rd] - imm) & 0xFFFFFFFF
                if result >= 0x80000000: result -= 0x100000000
                gp[rd] = result; pc += 3
            elif opcode == 0x72:  # LOAD32
                rd = m[pc]; rb = m[pc+1]
                off = m[pc+2] | (m[pc+3] << 8)
                addr = (gp[rb] + off) & 0xFFFF
                val = m[addr] | (m[addr+1] << 8) | (m[addr+2] << 16) | (m[addr+3] << 24)
                if val >= 0x80000000: val -= 0x100000000
                gp[rd] = val; pc += 4
            elif opcode == 0x76:  # STORE32
                rs = m[pc]; rb = m[pc+1]
                off = m[pc+2] | (m[pc+3] << 8)
                addr = (gp[rb] + off) & 0xFFFF
                val = gp[rs] & 0xFFFFFFFF
                m[addr] = val & 0xFF; m[addr+1] = (val >> 8) & 0xFF
                m[addr+2] = (val >> 16) & 0xFF; m[addr+3] = (val >> 24) & 0xFF
                pc += 4
            elif opcode == 0x01: pass  # NOP
            elif opcode == 0x02: pc = gp[15] & 0xFFFFFFFF  # RET
            elif opcode == 0x10:  # PUSH
                rd = m[pc]; rs = m[pc+1]
                gp[11] -= 4; sp = gp[11]
                val = gp[rs] & 0xFFFFFFFF
                m[sp] = val & 0xFF; m[sp+1] = (val >> 8) & 0xFF
                m[sp+2] = (val >> 16) & 0xFF; m[sp+3] = (val >> 24) & 0xFF
                pc += 2
            elif opcode == 0x11:  # POP
                rd = m[pc]; sp = gp[11]
                val = m[sp] | (m[sp+1] << 8) | (m[sp+2] << 16) | (m[sp+3] << 24)
                if val >= 0x80000000: val -= 0x100000000
                gp[rd] = val; gp[11] = sp + 4; pc += 2
            else:
                self.pc = pc - 1; self.cycles = cycles - 1
                err = self.step()
                pc = self.pc; cycles = self.cycles; halted = self.halted
                if err not in (0, 1): break
        
        self.pc = pc; self.cycles = cycles; self.halted = halted
        return 0 if halted else 11
    
    def _compile_loop(self, start_addr, end_addr_hint):
        """Compile a hot loop body to a Python function via exec()."""
        m = self.memory
        lines = [
            "def _jit_loop(gp, m, pc, cycles, max_cycles, vm):",
            "  halted = False",
            "  while not halted and cycles < max_cycles:",
        ]
        
        # Scan loop body from start_addr until we hit a backwards jump
        addr = start_addr
        depth = 0
        max_lines = 200  # safety limit
        
        while addr < len(m) and depth < max_lines:
            opcode = m[addr]
            
            if opcode == 0x00:  # HALT
                lines.append("    halted = True; break")
                break
            elif opcode == 0x20:  # IMOV
                rd = m[addr+1]; rs = m[addr+2]
                lines.append(f"    gp[{rd}] = gp[{rs}]")
                addr += 3
            elif opcode == 0xFE:  # MOVI
                rd = m[addr+1]
                imm = m[addr+2] | (m[addr+3] << 8)
                if imm >= 0x8000: imm -= 0x10000
                lines.append(f"    gp[{rd}] = {imm}")
                addr += 4
            elif opcode == 0x21:  # IADD
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] + gp[{rb}]) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0x22:  # ISUB
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] - gp[{rb}]) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0x23:  # IMUL
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] * gp[{rb}]) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0x28:  # IINC
                rd = m[addr+1]
                imm = m[addr+2] | (m[addr+3] << 8)
                if imm >= 0x8000: imm -= 0x10000
                lines.append(f"    result = (gp[{rd}] + {imm}) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0x29:  # IDEC
                rd = m[addr+1]
                imm = m[addr+2] | (m[addr+3] << 8)
                if imm >= 0x8000: imm -= 0x10000
                lines.append(f"    result = (gp[{rd}] - {imm}) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0x32:  # ICMPEQ
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    gp[{rd}] = 1 if gp[{ra}] == gp[{rb}] else 0")
                addr += 4
            elif opcode == 0x33:  # ICMPNE
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    gp[{rd}] = 1 if gp[{ra}] != gp[{rb}] else 0")
                addr += 4
            elif opcode == 0x34:  # ICMPLT
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    gp[{rd}] = 1 if gp[{ra}] < gp[{rb}] else 0")
                addr += 4
            elif opcode == 0x04:  # JNZ
                _len = m[addr+1]; reg = m[addr+2]
                offset = m[addr+3] | (m[addr+4] << 8)
                if offset >= 0x8000: offset -= 0x10000
                target = addr + 5 + offset
                if target <= addr:  # backwards = loop end
                    lines.append(f"    if gp[{reg}] != 0:")
                    lines.append(f"      cycles += 1; continue")
                    lines.append(f"    else:")
                    lines.append(f"      pc = {addr + 5}; break")
                    addr += 5; depth = max_lines  # end scan
                else:
                    lines.append(f"    if gp[{reg}] != 0: pc = {target}")
                    addr += 5
            elif opcode == 0x05:  # JZ
                _len = m[addr+1]; reg = m[addr+2]
                offset = m[addr+3] | (m[addr+4] << 8)
                if offset >= 0x8000: offset -= 0x10000
                target = addr + 5 + offset
                if target <= addr:  # backwards
                    lines.append(f"    if gp[{reg}] == 0:")
                    lines.append(f"      cycles += 1; continue")
                    lines.append(f"    else:")
                    lines.append(f"      pc = {addr + 5}; break")
                    addr += 5; depth = max_lines
                else:
                    lines.append(f"    if gp[{reg}] == 0: pc = {target}")
                    addr += 5
            elif opcode == 0x03:  # JUMP
                _len = m[addr+1]
                offset = m[addr+2] | (m[addr+3] << 8)
                if offset >= 0x8000: offset -= 0x10000
                target = addr + 4 + offset
                if target <= addr:  # unconditional backwards = infinite loop guard
                    lines.append(f"    cycles += 1; continue")
                    addr += 4; depth = max_lines
                else:
                    lines.append(f"    pc = {target}; break")
                    addr += 4
            elif opcode == 0x72:  # LOAD32
                rd = m[addr+1]; rb = m[addr+2]
                off = m[addr+3] | (m[addr+4] << 8)
                lines.append(f"    _addr = (gp[{rb}] + {off}) & 0xFFFF")
                lines.append(f"    _val = m[_addr] | (m[_addr+1] << 8) | (m[_addr+2] << 16) | (m[_addr+3] << 24)")
                lines.append(f"    gp[{rd}] = _val - 0x100000000 if _val >= 0x80000000 else _val")
                addr += 5
            elif opcode == 0x76:  # STORE32
                rs = m[addr+1]; rb = m[addr+2]
                off = m[addr+3] | (m[addr+4] << 8)
                lines.append(f"    _addr = (gp[{rb}] + {off}) & 0xFFFF")
                lines.append(f"    _val = gp[{rs}] & 0xFFFFFFFF")
                lines.append(f"    m[_addr] = _val & 0xFF; m[_addr+1] = (_val >> 8) & 0xFF; m[_addr+2] = (_val >> 16) & 0xFF; m[_addr+3] = (_val >> 24) & 0xFF")
                addr += 5
            elif opcode == 0xA0:  # BAND
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] & gp[{rb}]) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0xA1:  # BOR
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] | gp[{rb}]) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0xA2:  # BXOR
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] ^ gp[{rb}]) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0xA3:  # BSHL
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = (gp[{ra}] << (gp[{rb}] & 31)) & 0xFFFFFFFF")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0xA4:  # BSHR
                rd = m[addr+1]; ra = m[addr+2]; rb = m[addr+3]
                lines.append(f"    result = ((gp[{ra}] & 0xFFFFFFFF) >> (gp[{rb}] & 31))")
                lines.append(f"    gp[{rd}] = result - 0x100000000 if result >= 0x80000000 else result")
                addr += 4
            elif opcode == 0xB0:  # VLOAD
                lines.append("    pass  # VLOAD in JIT not inlined")
                addr += 5
            elif opcode == 0xB4:  # VDOT
                lines.append("    pass  # VDOT in JIT not inlined")
                addr += 4
            else:
                lines.append(f"    pass  # unknown opcode {opcode:#x}")
                # Try to advance by guessing size
                if opcode in (0x01, 0x02, 0x08, 0x09, 0x0A):
                    addr += 1
                elif opcode in (0x10, 0x11, 0x12, 0x13, 0x20, 0x40):
                    addr += 3
                else:
                    addr += 4
            depth += 1
        
        lines.append("  return pc, cycles, halted")
        
        code = "\n".join(lines)
        
        try:
            local_ns = {}
            exec(code, {}, local_ns)
            self._loop_cache[start_addr] = local_ns['_jit_loop']
        except Exception as e:
            pass  # JIT compilation failed, fall back to interpreter


def benchmark_jit(name, bytecode, input_val, iterations=100):
    """Benchmark the JIT-enhanced VM."""
    times = []
    total_cycles = 0
    
    for _ in range(iterations):
        vm = FluxVMJIT(debug=False)
        vm.load_bytecode(bytecode)
        vm.gp[0] = input_val
        vm.gp[14] = 0
        
        t0 = time.perf_counter()
        err = vm.run()
        t1 = time.perf_counter()
        
        times.append(t1 - t0)
        total_cycles = vm.cycles
    
    avg = sum(times) / len(times)
    total = sum(times)
    ops_per_sec = total_cycles / avg if avg > 0 else 0
    
    return {
        'name': name,
        'avg_s': avg,
        'total_s': total,
        'cycles': total_cycles,
        'ops_per_sec': ops_per_sec,
        'result': vm.gp[0] if iterations > 0 else 0,
        'iterations': iterations,
    }


# ── Main ────────────────────────────────────────────────────────

def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.2f}K"
    return f"{n:.2f}"


def main():
    print("=" * 72)
    print("  FLUX VM Performance Optimization Benchmark Suite")
    print("=" * 72)
    print()
    
    # Build test programs
    factorial_bc, factorial_n = build_factorial_bytecode(7)
    fib_bc, fib_n = build_fibonacci_bytecode(30)
    memcpy_bc, memcpy_n = build_memcpy_bytecode(1024)  # 1KB
    dotprod_bc, dotprod_n = build_dotproduct_bytecode(1000)
    bloom_bc, bloom_n = build_bloomfilter_bytecode(10000)
    
    benchmarks = [
        ("factorial(7) × 500", factorial_bc, 7, 500),
        ("factorial(100) × 200", factorial_bc, 100, 200),
        ("fibonacci(30) × 200", fib_bc, 30, 200),
        ("memcpy(1KB) × 200", memcpy_bc, 1024, 200),
        ("vdot × 200", dotprod_bc, 1000, 200),
        ("bloom × 200", bloom_bc, 1000, 200),
    ]
    
    # Warmup
    print("Warming up...")
    for name, bc, val, iters in benchmarks[:2]:
        vm = FluxVM(debug=False)
        vm.load_bytecode(bc)
        vm.gp[0] = val
        vm.gp[14] = 0
        vm.run()
        
        vm2 = FluxVMOptimized(debug=False)
        vm2.load_bytecode(bc)
        vm2.gp[0] = val
        vm2.gp[14] = 0
        vm2.run()
        
        vm3 = FluxVMJIT(debug=False)
        vm3.load_bytecode(bc)
        vm3.gp[0] = val
        vm3.gp[14] = 0
        vm3.run()
    
    print()
    
    # ── Results table ──
    header = f"{'Benchmark':<25s} {'Cycles':>10s} | {'Original':>12s} {'Optimized':>12s} {'JIT':>12s} | {'Speedup':>8s} {'JIT×':>8s}"
    print(header)
    print("-" * len(header))
    
    total_orig = 0
    total_opt = 0
    total_jit = 0
    
    for name, bc, val, iters in benchmarks:
        r_orig = benchmark_original(name, bc, val, iters)
        r_opt = benchmark_optimized(name, bc, val, iters)
        r_jit = benchmark_jit(name, bc, val, iters)
        
        speedup = r_orig['avg_s'] / r_opt['avg_s'] if r_opt['avg_s'] > 0 else 0
        jit_speedup = r_orig['avg_s'] / r_jit['avg_s'] if r_jit['avg_s'] > 0 else 0
        
        orig_ops = r_orig['ops_per_sec']
        opt_ops = r_opt['ops_per_sec']
        jit_ops = r_jit['ops_per_sec']
        
        total_orig += r_orig['total_s']
        total_opt += r_opt['total_s']
        total_jit += r_jit['total_s']
        
        print(f"{name:<25s} {r_orig['cycles']:>10d} | "
              f"{fmt_num(orig_ops):>12s} {fmt_num(opt_ops):>12s} {fmt_num(jit_ops):>12s} | "
              f"{speedup:>7.2f}× {jit_speedup:>7.2f}×")
    
    print("-" * len(header))
    overall_speedup = total_orig / total_opt if total_opt > 0 else 0
    overall_jit = total_orig / total_jit if total_jit > 0 else 0
    print(f"{'TOTAL':<25s} {'':>10s} | {total_orig:>10.3f}s {total_opt:>10.3f}s {total_jit:>10.3f}s | "
          f"{overall_speedup:>7.2f}× {overall_jit:>7.2f}×")
    
    print()
    print("Ops/sec shown as ops executed per second (higher = faster)")
    print()
    
    # ── Detailed profile ──
    print("── Detailed Profile: factorial(7) single run ──")
    vm = FluxVM(debug=False)
    vm.load_bytecode(factorial_bc)
    vm.gp[0] = 7
    vm.gp[14] = 0
    
    t0 = time.perf_counter()
    vm.run()
    t1 = time.perf_counter()
    
    print(f"  Cycles: {vm.cycles}")
    print(f"  Time:   {(t1-t0)*1_000_000:.2f} µs")
    print(f"  Ops/s:  {vm.cycles/(t1-t0):,.0f}")
    print(f"  Result: R0={vm.gp[0]}, R1={vm.gp[1]} (factorial result)")
    print()
    
    # ── Memory overhead comparison ──
    print("── Memory Overhead ──")
    import sys
    vm_orig = FluxVM()
    vm_opt = FluxVMOptimized()
    print(f"  Original VM:  {sys.getsizeof(vm_orig):,} bytes (object only)")
    print(f"  Optimized VM: {sys.getsizeof(vm_opt):,} bytes (object only)")
    print(f"  Original memory: {sys.getsizeof(vm_orig.memory):,} bytes")
    print(f"  Optimized memory: {sys.getsizeof(vm_opt.memory):,} bytes")


if __name__ == '__main__':
    main()

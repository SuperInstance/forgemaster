#!/usr/bin/env python3
"""
FLUX Virtual Machine Emulator — FLUX ISA v3
=============================================
Loads and executes FLUX bytecode files.

Features:
  - All core opcodes (0x00-0xB4)
  - 16 GP registers (R0-R15 with aliases), 16 FP registers, 16 vector registers
  - Flags register (Z, S, C, V)
  - Flat memory model with stack
  - A2A opcodes as stubs (print message, no real network)
  - Cycle counting and execution tracing
  - Debug mode that prints each instruction

Usage:
  python flux_vm.py program.fbx
  python flux_vm.py program.fbx --debug
"""

import struct
import math
import sys
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Constants ───────────────────────────────────────────────────

MOVI_OPCODE = 0xFE  # Assembler pseudo-opcode for load immediate

MEMORY_SIZE = 64 * 1024       # 64 KB
STACK_BASE  = MEMORY_SIZE - 1  # Stack starts at top of memory
MAX_CYCLES  = 1_000_000        # Safety limit
VECTOR_SIZE = 16               # 16 components per vector register

# ── Flags bits ──────────────────────────────────────────────────
FLAG_Z = 0x01  # Zero
FLAG_S = 0x02  # Sign
FLAG_C = 0x04  # Carry
FLAG_V = 0x08  # Overflow

# ── Error codes ─────────────────────────────────────────────────
FLUX_OK              = 0
FLUX_ERR_HALT        = 1
FLUX_ERR_INVALID_OP  = 2
FLUX_ERR_DIV_ZERO    = 3
FLUX_ERR_STACK_OVER  = 4
FLUX_ERR_STACK_UNDER = 5
FLUX_ERR_CYCLE       = 11
FLUX_ERR_MEMORY      = 12


def to_signed32(val: int) -> int:
    """Convert to signed 32-bit integer."""
    val = val & 0xFFFFFFFF
    if val >= 0x80000000:
        return val - 0x100000000
    return val


def to_unsigned32(val: int) -> int:
    """Convert to unsigned 32-bit integer."""
    return val & 0xFFFFFFFF


class FluxVM:
    """FLUX ISA v3 Virtual Machine."""

    def __init__(self, debug: bool = False):
        # Registers
        self.gp = [0] * 16          # GP registers (R0-R15), 32-bit signed
        self.fp_regs = [0.0] * 16   # FP registers (F0-F15), float32
        self.vec = [[0] * VECTOR_SIZE for _ in range(16)]  # Vector registers

        # Memory
        self.memory = bytearray(MEMORY_SIZE)

        # Special
        self.pc = 0
        self.halted = False
        self.cycles = 0
        self.debug = debug
        self.trace: list[str] = []
        self.error = FLUX_OK

        # Initialize SP to top of memory
        self.gp[11] = STACK_BASE  # SP

        # Function table (loaded from binary)
        self.func_table: dict[int, tuple[str, int]] = {}  # idx → (name, address)

        # A2A stub state
        self.a2a_messages: list[tuple[int, int]] = []  # (from_agent, value)
        self.agent_trust: dict[int, int] = {}  # agent_id → trust_level

    # ── Register aliases ────────────────────────────────────────

    @property
    def rv(self): return self.gp[8]   # Return value
    @rv.setter
    def rv(self, v): self.gp[8] = v

    @property
    def sp(self): return self.gp[11]
    @sp.setter
    def sp(self, v): self.gp[11] = v

    @property
    def fp_reg(self): return self.gp[12]
    @fp_reg.setter
    def fp_reg(self, v): self.gp[12] = v

    @property
    def flags(self): return self.gp[13]
    @flags.setter
    def flags(self, v): self.gp[13] = v

    @property
    def lr(self): return self.gp[15]
    @lr.setter
    def lr(self, v): self.gp[15] = v

    # ── Flags ───────────────────────────────────────────────────

    def set_flags_zsvc(self, result: int, a: int = 0, b: int = 0, is_sub: bool = False):
        """Set Z, S, V, C flags based on result."""
        result32 = to_unsigned32(result)
        self.flags = 0
        if result32 == 0:
            self.flags |= FLAG_Z
        if result32 & 0x80000000:
            self.flags |= FLAG_S
        # Carry: unsigned overflow
        ua, ub = to_unsigned32(a), to_unsigned32(b)
        if is_sub:
            if ua < ub:
                self.flags |= FLAG_C
        else:
            if ua + ub > 0xFFFFFFFF:
                self.flags |= FLAG_C
        # Overflow: signed overflow
        sa, sb = to_signed32(a), to_signed32(b)
        sr = to_signed32(result)
        if is_sub:
            if (sa > 0 and sb < 0 and sr < 0) or (sa < 0 and sb > 0 and sr > 0):
                self.flags |= FLAG_V
        else:
            if (sa > 0 and sb > 0 and sr < 0) or (sa < 0 and sb < 0 and sr > 0):
                self.flags |= FLAG_V

    def set_flags_zs(self, result: int):
        """Set Z, S flags only."""
        result32 = to_unsigned32(result)
        self.flags = 0
        if result32 == 0:
            self.flags |= FLAG_Z
        if result32 & 0x80000000:
            self.flags |= FLAG_S

    def set_flag_z(self, val: bool):
        """Set only Z flag."""
        self.flags = FLAG_Z if val else 0

    # ── Memory operations ───────────────────────────────────────

    def mem_read8(self, addr: int) -> int:
        addr = addr & 0xFFFF
        return self.memory[addr]

    def mem_read16(self, addr: int) -> int:
        addr = addr & 0xFFFF
        return struct.unpack_from('<H', self.memory, addr)[0]

    def mem_read32(self, addr: int) -> int:
        addr = addr & 0xFFFF
        return struct.unpack_from('<I', self.memory, addr)[0]

    def mem_write8(self, addr: int, val: int):
        addr = addr & 0xFFFF
        self.memory[addr] = val & 0xFF

    def mem_write16(self, addr: int, val: int):
        addr = addr & 0xFFFF
        struct.pack_into('<H', self.memory, addr, val & 0xFFFF)

    def mem_write32(self, addr: int, val: int):
        addr = addr & 0xFFFF
        struct.pack_into('<I', self.memory, addr, val & 0xFFFFFFFF)

    # ── Stack operations ────────────────────────────────────────

    def push32(self, val: int):
        self.sp -= 4
        if self.sp < 0:
            raise RuntimeError("Stack overflow")
        self.mem_write32(self.sp, val)

    def pop32(self) -> int:
        val = self.mem_read32(self.sp)
        self.sp += 4
        if self.sp > STACK_BASE:
            raise RuntimeError("Stack underflow")
        return val

    # ── Load binary ─────────────────────────────────────────────

    def load_binary(self, data: bytes):
        """Load a FLUX binary file (.fbx) or raw bytecode."""
        if data[:4] == b'FLUX':
            self._load_fbx(data)
        else:
            # Raw bytecode — load starting at offset 0
            for i, b in enumerate(data):
                if i < MEMORY_SIZE:
                    self.memory[i] = b
            self.pc = 0

    def _load_fbx(self, data: bytes):
        """Parse FLUX binary file format."""
        # Header: magic(4) + version(2) + flags(2) + entry(4) + reserved(4) = 16
        magic = data[0:4]
        assert magic == b'FLUX', f"Bad magic: {magic}"
        # version = data[4], data[5]
        # flags = struct.unpack_from('<H', data, 6)[0]
        entry_func = struct.unpack_from('<I', data, 8)[0]

        offset = 16
        # Parse function table — variable length entries
        while offset + 4 <= len(data):
            name_len = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            if name_len == 0 or offset + name_len + 8 > len(data):
                break
            name = data[offset:offset + name_len].decode('utf-8')
            offset += name_len
            addr = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            local_regs = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            max_stack = struct.unpack_from('<H', data, offset)[0]
            offset += 2

            self.func_table[len(self.func_table)] = (name, addr)

        # Rest is bytecode + data — load into memory
        bytecode_start = offset
        for i in range(bytecode_start, len(data)):
            self.memory[i - bytecode_start] = data[i]

        # Set PC to entry function
        if entry_func in self.func_table:
            self.pc = self.func_table[entry_func][1]
        else:
            self.pc = 0

    def load_bytecode(self, bytecode: bytes, pc_start: int = 0):
        """Load raw bytecode directly into memory."""
        for i, b in enumerate(bytecode):
            self.memory[pc_start + i] = b
        self.pc = pc_start

    # ── Fetch helpers ───────────────────────────────────────────

    def fetch8(self) -> int:
        val = self.memory[self.pc]
        self.pc += 1
        return val

    def fetch16(self) -> int:
        val = struct.unpack_from('<H', self.memory, self.pc)[0]
        self.pc += 2
        return val

    def fetch16s(self) -> int:
        val = struct.unpack_from('<h', self.memory, self.pc)[0]
        self.pc += 2
        return val

    # ── Execute ─────────────────────────────────────────────────

    def step(self) -> int:
        """Execute one instruction. Returns error code."""
        if self.halted:
            return FLUX_ERR_HALT

        opcode = self.fetch8()
        self.cycles += 1

        if self.cycles > MAX_CYCLES:
            return FLUX_ERR_CYCLE

        # ── Format A (nullary) ──
        if opcode == 0x00:  # HALT
            if self.debug:
                self.trace.append(f"HALT")
            self.halted = True
            return FLUX_ERR_HALT

        elif opcode == 0x01:  # NOP
            if self.debug:
                self.trace.append("NOP")

        elif opcode == 0x02:  # RET
            self.pc = to_unsigned32(self.lr)
            if self.debug:
                self.trace.append(f"RET -> PC=0x{self.pc:04x}")

        elif opcode == 0x08:  # YIELD
            if self.debug:
                self.trace.append("YIELD")

        elif opcode == 0x09:  # PANIC
            if self.debug:
                self.trace.append("PANIC")
            self.halted = True
            return FLUX_ERR_INVALID_OP

        elif opcode == 0x0A:  # UNREACHABLE
            if self.debug:
                self.trace.append("UNREACHABLE (trap)")
            self.halted = True
            return FLUX_ERR_INVALID_OP

        # ── Format B (2 registers) ──
        elif opcode == 0x10:  # PUSH
            rd = self.fetch8()
            rs = self.fetch8()
            self.push32(to_signed32(self.gp[rs]))
            if self.debug:
                self.trace.append(f"PUSH R{rs} (= {self.gp[rs]})")

        elif opcode == 0x11:  # POP
            rd = self.fetch8()
            _ = self.fetch8()
            self.gp[rd] = self.pop32()
            if self.debug:
                self.trace.append(f"POP R{rd} (= {self.gp[rd]})")

        elif opcode == 0x12:  # DUP
            rd = self.fetch8()
            rs = self.fetch8()
            self.gp[rd] = self.gp[rs]
            if self.debug:
                self.trace.append(f"DUP R{rd} = R{rs} ({self.gp[rs]})")

        elif opcode == 0x13:  # SWAP
            ra = self.fetch8()
            rb = self.fetch8()
            self.gp[ra], self.gp[rb] = self.gp[rb], self.gp[ra]
            if self.debug:
                self.trace.append(f"SWAP R{ra}, R{rb}")

        elif opcode == 0x20:  # IMOV
            rd = self.fetch8()
            rs = self.fetch8()
            self.gp[rd] = self.gp[rs]
            if self.debug:
                self.trace.append(f"IMOV R{rd} = R{rs} ({self.gp[rs]})")

        elif opcode == 0x40:  # FMOV
            rd = self.fetch8()
            rs = self.fetch8()
            self.fp_regs[rd] = self.fp_regs[rs]
            if self.debug:
                self.trace.append(f"FMOV F{rd} = F{rs} ({self.fp_regs[rs]})")

        # ── Format C (3 registers) ──
        elif opcode == 0x21:  # IADD
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] + self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[ra], self.gp[rb])
            if self.debug:
                self.trace.append(f"IADD R{rd} = R{ra}({self.gp[ra]}) + R{rb}({self.gp[rb]}) = {result}")

        elif opcode == 0x22:  # ISUB
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] - self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[ra], self.gp[rb], is_sub=True)
            if self.debug:
                self.trace.append(f"ISUB R{rd} = R{ra}({self.gp[ra]}) - R{rb}({self.gp[rb]}) = {result}")

        elif opcode == 0x23:  # IMUL
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] * self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[ra], self.gp[rb])
            if self.debug:
                self.trace.append(f"IMUL R{rd} = R{ra}({self.gp[ra]}) * R{rb}({self.gp[rb]}) = {result}")

        elif opcode == 0x24:  # IDIV
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            if self.gp[rb] == 0:
                if self.debug:
                    self.trace.append("IDIV — DIVIDE BY ZERO")
                return FLUX_ERR_DIV_ZERO
            result = to_signed32(int(self.gp[ra] / self.gp[rb]))
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[ra], self.gp[rb], is_sub=True)
            if self.debug:
                self.trace.append(f"IDIV R{rd} = R{ra}({self.gp[ra]}) / R{rb}({self.gp[rb]}) = {result}")

        elif opcode == 0x25:  # IMOD
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            if self.gp[rb] == 0:
                return FLUX_ERR_DIV_ZERO
            result = to_signed32(self.gp[ra] % self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[ra], self.gp[rb])
            if self.debug:
                self.trace.append(f"IMOD R{rd} = {result}")

        elif opcode == 0x26:  # INEG
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(-self.gp[ra])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"INEG R{rd} = {result}")

        elif opcode == 0x27:  # IABS
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(abs(self.gp[ra]))
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"IABS R{rd} = {result}")

        elif opcode == 0x2A:  # IMIN
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = min(self.gp[ra], self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"IMIN R{rd} = {result}")

        elif opcode == 0x2B:  # IMAX
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = max(self.gp[ra], self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"IMAX R{rd} = {result}")

        elif opcode == 0x2C:  # IAND
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] & self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"IAND R{rd} = {result}")

        elif opcode == 0x2D:  # IOR
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] | self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"IOR R{rd} = {result}")

        elif opcode == 0x2E:  # IXOR
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] ^ self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"IXOR R{rd} = {result}")

        elif opcode == 0x2F:  # ISHL
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            shift = self.gp[rb] & 31
            result = to_signed32(self.gp[ra] << shift)
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ISHL R{rd} = {result}")

        elif opcode == 0x30:  # ISHR
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            shift = self.gp[rb] & 31
            result = to_signed32(self.gp[ra] >> shift)
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ISHR R{rd} = {result}")

        elif opcode == 0x31:  # INOT
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(~self.gp[ra])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"INOT R{rd} = {result}")

        # ── Integer comparisons ──
        elif opcode == 0x32:  # ICMPEQ
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.gp[ra] == self.gp[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ICMPEQ R{rd} = {result}")

        elif opcode == 0x33:  # ICMPNE
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.gp[ra] != self.gp[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ICMPNE R{rd} = {result}")

        elif opcode == 0x34:  # ICMPLT
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.gp[ra] < self.gp[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ICMPLT R{rd} = {result}")

        elif opcode == 0x35:  # ICMPLE
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.gp[ra] <= self.gp[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ICMPLE R{rd} = {result}")

        elif opcode == 0x36:  # ICMPGT
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.gp[ra] > self.gp[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ICMPGT R{rd} = {result}")

        elif opcode == 0x37:  # ICMPGE
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.gp[ra] >= self.gp[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"ICMPGE R{rd} = {result}")

        # ── Float arithmetic ──
        elif opcode == 0x41:  # FADD
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = self.fp_regs[ra] + self.fp_regs[rb]
            if self.debug:
                self.trace.append(f"FADD F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x42:  # FSUB
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = self.fp_regs[ra] - self.fp_regs[rb]
            if self.debug:
                self.trace.append(f"FSUB F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x43:  # FMUL
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = self.fp_regs[ra] * self.fp_regs[rb]
            if self.debug:
                self.trace.append(f"FMUL F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x44:  # FDIV
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            if self.fp_regs[rb] == 0.0:
                self.fp_regs[rd] = float('inf')
            else:
                self.fp_regs[rd] = self.fp_regs[ra] / self.fp_regs[rb]
            if self.debug:
                self.trace.append(f"FDIV F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x45:  # FMOD
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.fmod(self.fp_regs[ra], self.fp_regs[rb])
            if self.debug:
                self.trace.append(f"FMOD F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x46:  # FNEG
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = -self.fp_regs[ra]
            if self.debug:
                self.trace.append(f"FNEG F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x47:  # FABS
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = abs(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FABS F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x48:  # FSQRT
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            if self.fp_regs[ra] < 0:
                self.fp_regs[rd] = float('nan')
            else:
                self.fp_regs[rd] = math.sqrt(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FSQRT F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x49:  # FFLOOR
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.floor(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FFLOOR F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x4A:  # FCEIL
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.ceil(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FCEIL F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x4B:  # FROUND
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = round(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FROUND F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x4C:  # FMIN
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = min(self.fp_regs[ra], self.fp_regs[rb])
            if self.debug:
                self.trace.append(f"FMIN F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x4D:  # FMAX
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = max(self.fp_regs[ra], self.fp_regs[rb])
            if self.debug:
                self.trace.append(f"FMAX F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x4E:  # FSIN
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.sin(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FSIN F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x4F:  # FCOS
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.cos(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FCOS F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x50:  # FEXP
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.exp(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FEXP F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x51:  # FLOG
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = math.log(self.fp_regs[ra])
            if self.debug:
                self.trace.append(f"FLOG F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x54:  # FCMPEQ
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.fp_regs[ra] == self.fp_regs[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"FCMPEQ R{rd} = {result}")

        elif opcode == 0x55:  # FCMPNE
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.fp_regs[ra] != self.fp_regs[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"FCMPNE R{rd} = {result}")

        elif opcode == 0x56:  # FCMPLT
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.fp_regs[ra] < self.fp_regs[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"FCMPLT R{rd} = {result}")

        elif opcode == 0x57:  # FCMPLE
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.fp_regs[ra] <= self.fp_regs[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"FCMPLE R{rd} = {result}")

        elif opcode == 0x58:  # FCMPGT
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.fp_regs[ra] > self.fp_regs[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"FCMPGT R{rd} = {result}")

        elif opcode == 0x59:  # FCMPGE
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = 1 if self.fp_regs[ra] >= self.fp_regs[rb] else 0
            self.gp[rd] = result
            self.set_flag_z(result == 0)
            if self.debug:
                self.trace.append(f"FCMPGE R{rd} = {result}")

        # ── Conversions ──
        elif opcode == 0x60:  # ITOF
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.fp_regs[rd] = float(self.gp[ra])
            if self.debug:
                self.trace.append(f"ITOF F{rd} = {self.fp_regs[rd]}")

        elif opcode == 0x61:  # FTOI
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.gp[rd] = to_signed32(int(self.fp_regs[ra]))
            if self.debug:
                self.trace.append(f"FTOI R{rd} = {self.gp[rd]}")

        elif opcode == 0x62:  # BTOI
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.gp[rd] = 1 if self.gp[ra] != 0 else 0
            if self.debug:
                self.trace.append(f"BTOI R{rd} = {self.gp[rd]}")

        elif opcode == 0x63:  # ITOB
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            self.gp[rd] = 1 if self.gp[ra] else 0
            if self.debug:
                self.trace.append(f"ITOB R{rd} = {self.gp[rd]}")

        # ── Format D (reg + imm16) ──
        elif opcode == 0x28:  # IINC
            rd = self.fetch8()
            imm = self.fetch16s()
            result = to_signed32(self.gp[rd] + imm)
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[rd] - imm, imm)
            if self.debug:
                self.trace.append(f"IINC R{rd} += {imm} = {result}")

        elif opcode == 0x29:  # IDEC
            rd = self.fetch8()
            imm = self.fetch16s()
            result = to_signed32(self.gp[rd] - imm)
            self.gp[rd] = result
            self.set_flags_zsvc(result, self.gp[rd] + imm, imm, is_sub=True)
            if self.debug:
                self.trace.append(f"IDEC R{rd} -= {imm} = {result}")

        elif opcode == 0x79:  # STACKALLOC
            rd = self.fetch8()
            size = self.fetch16s()
            self.sp -= size
            self.gp[rd] = self.sp
            if self.debug:
                self.trace.append(f"STACKALLOC R{rd} = SP - {size} = {self.sp}")

        elif opcode == MOVI_OPCODE:  # MOVI pseudo-op
            rd = self.fetch8()
            imm = self.fetch16s()
            self.gp[rd] = imm
            if self.debug:
                self.trace.append(f"MOVI R{rd} = {imm}")

        # ── Format E (2 regs + offset16) ──
        elif opcode == 0x70:  # LOAD8
            rd = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.gp[rd] = self.memory[addr]
            if self.debug:
                self.trace.append(f"LOAD8 R{rd} = mem[0x{addr:04x}] = {self.gp[rd]}")

        elif opcode == 0x71:  # LOAD16
            rd = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.gp[rd] = self.mem_read16(addr)
            if self.debug:
                self.trace.append(f"LOAD16 R{rd} = mem[0x{addr:04x}] = {self.gp[rd]}")

        elif opcode == 0x72:  # LOAD32
            rd = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.gp[rd] = to_signed32(self.mem_read32(addr))
            if self.debug:
                self.trace.append(f"LOAD32 R{rd} = mem[0x{addr:04x}] = {self.gp[rd]}")

        elif opcode == 0x73:  # LOAD64
            rd = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            lo = self.mem_read32(addr)
            hi = self.mem_read32(addr + 4)
            self.gp[rd] = to_signed32(lo)  # simplified — just low 32 bits
            if self.debug:
                self.trace.append(f"LOAD64 R{rd} = {self.gp[rd]}")

        elif opcode == 0x74:  # STORE8
            rs = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.mem_write8(addr, self.gp[rs])
            if self.debug:
                self.trace.append(f"STORE8 mem[0x{addr:04x}] = {self.gp[rs] & 0xFF}")

        elif opcode == 0x75:  # STORE16
            rs = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.mem_write16(addr, self.gp[rs])
            if self.debug:
                self.trace.append(f"STORE16 mem[0x{addr:04x}] = {self.gp[rs] & 0xFFFF}")

        elif opcode == 0x76:  # STORE32
            rs = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.mem_write32(addr, self.gp[rs])
            if self.debug:
                self.trace.append(f"STORE32 mem[0x{addr:04x}] = {self.gp[rs]}")

        elif opcode == 0x77:  # STORE64
            rs = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            self.mem_write32(addr, self.gp[rs])
            if self.debug:
                self.trace.append(f"STORE64 mem[0x{addr:04x}]")

        elif opcode == 0x78:  # LOADADDR
            rd = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            self.gp[rd] = self.gp[rb] + off
            if self.debug:
                self.trace.append(f"LOADADDR R{rd} = {self.gp[rd]}")

        # ── Format G (variable) ──
        elif opcode == 0x03:  # JUMP
            length = self.fetch8()
            offset = self.fetch16s()
            self.pc += offset
            if self.debug:
                self.trace.append(f"JUMP offset={offset} -> PC=0x{self.pc:04x}")

        elif opcode == 0x04:  # JNZ / JumpIf
            length = self.fetch8()
            reg = self.fetch8()
            offset = self.fetch16s()
            val = self.gp[reg]
            if val != 0:
                self.pc += offset
            if self.debug:
                taken = "TAKEN" if val != 0 else "not taken"
                self.trace.append(f"JNZ R{reg}({val}) offset={offset} [{taken}] -> PC=0x{self.pc:04x}")

        elif opcode == 0x05:  # JZ / JumpIfNot
            length = self.fetch8()
            reg = self.fetch8()
            offset = self.fetch16s()
            val = self.gp[reg]
            if val == 0:
                self.pc += offset
            if self.debug:
                taken = "TAKEN" if val == 0 else "not taken"
                self.trace.append(f"JZ R{reg}({val}) offset={offset} [{taken}] -> PC=0x{self.pc:04x}")

        elif opcode == 0x06:  # CALL
            length = self.fetch8()
            func_idx = self.fetch16()
            # Push return address (current PC)
            self.lr = self.pc
            self.push32(self.pc)
            # Jump to function address
            if func_idx in self.func_table:
                self.pc = self.func_table[func_idx][1]
            else:
                self.pc = func_idx  # treat as direct address
            if self.debug:
                self.trace.append(f"CALL func={func_idx} -> PC=0x{self.pc:04x}, LR=0x{self.lr:04x}")

        elif opcode == 0x07:  # CALLINDIRECT
            length = self.fetch8()
            reg = self.fetch8()
            self.lr = self.pc
            self.push32(self.pc)
            self.pc = to_unsigned32(self.gp[reg])
            if self.debug:
                self.trace.append(f"CALLINDIRECT R{reg} -> PC=0x{self.pc:04x}")

        # ── A2A stubs ──
        elif opcode == 0x80:  # ASEND
            length = self.fetch8()
            agent_id = self.fetch8()
            reg = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] ASEND agent={agent_id} val=R{reg}({self.gp[reg]})")

        elif opcode == 0x81:  # ARECV
            length = self.fetch8()
            agent_id = self.fetch8()
            reg = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] ARECV agent={agent_id} -> R{reg}")

        elif opcode == 0x82:  # AASK
            length = self.fetch8()
            agent_id = self.fetch8()
            reg = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] AASK agent={agent_id} R{reg}({self.gp[reg]})")

        elif opcode == 0x83:  # ATELL
            length = self.fetch8()
            agent_id = self.fetch8()
            reg = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] ATELL agent={agent_id} R{reg}({self.gp[reg]})")

        elif opcode == 0x84:  # ADELEGATE
            length = self.fetch8()
            _ = self.fetch8()  # agent_id
            _ = self.fetch8()  # bc_start
            if self.debug:
                self.trace.append(f"[A2A] ADELEGATE (stub)")

        elif opcode == 0x85:  # ABROADCAST
            length = self.fetch8()
            reg = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] ABROADCAST R{reg}({self.gp[reg]})")

        elif opcode == 0x86:  # ASUBSCRIBE
            length = self.fetch8()
            _ = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] ASUBSCRIBE (stub)")

        elif opcode == 0x87:  # AWAIT
            length = self.fetch8()
            _ = self.fetch8()
            if self.debug:
                self.trace.append(f"[A2A] AWAIT (stub)")

        elif opcode == 0x88:  # ATRUST
            length = self.fetch8()
            agent_id = self.fetch8()
            level = self.fetch8()
            self.agent_trust[agent_id] = level
            if self.debug:
                self.trace.append(f"[A2A] ATRUST agent={agent_id} level={level}")

        elif opcode == 0x89:  # AVERIFY
            length = self.fetch8()
            agent_id = self.fetch8()
            result_reg = self.fetch8()
            self.gp[result_reg] = self.agent_trust.get(agent_id, 0)
            if self.debug:
                self.trace.append(f"[A2A] AVERIFY agent={agent_id} -> R{result_reg}={self.gp[result_reg]}")

        # ── Bitwise (0xA0-0xA5) — same as IAND/IOR/IXOR etc. but distinct opcodes ──
        elif opcode == 0xA0:  # BAND
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] & self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"BAND R{rd} = {result}")

        elif opcode == 0xA1:  # BOR
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] | self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"BOR R{rd} = {result}")

        elif opcode == 0xA2:  # BXOR
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(self.gp[ra] ^ self.gp[rb])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"BXOR R{rd} = {result}")

        elif opcode == 0xA3:  # BSHL
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            shift = self.gp[rb] & 31
            result = to_signed32(self.gp[ra] << shift)
            self.gp[rd] = result
            if self.debug:
                self.trace.append(f"BSHL R{rd} = {result}")

        elif opcode == 0xA4:  # BSHR
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            shift = self.gp[rb] & 31
            result = to_signed32(to_unsigned32(self.gp[ra]) >> shift)
            self.gp[rd] = result
            if self.debug:
                self.trace.append(f"BSHR R{rd} = {result}")

        elif opcode == 0xA5:  # BNOT
            rd, ra, _ = self.fetch8(), self.fetch8(), self.fetch8()
            result = to_signed32(~self.gp[ra])
            self.gp[rd] = result
            self.set_flags_zs(result)
            if self.debug:
                self.trace.append(f"BNOT R{rd} = {result}")

        # ── Vector/SIMD (0xB0-0xB4) ──
        elif opcode == 0xB0:  # VLOAD
            rd = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            # Load 16 int32 components from memory
            for i in range(VECTOR_SIZE):
                self.vec[rd][i] = to_signed32(self.mem_read32(addr + i * 4))
            if self.debug:
                self.trace.append(f"VLOAD V{rd} from 0x{addr:04x}")

        elif opcode == 0xB1:  # VSTORE
            rs = self.fetch8()
            rb = self.fetch8()
            off = self.fetch16()
            addr = (self.gp[rb] + off) & 0xFFFF
            for i in range(VECTOR_SIZE):
                self.mem_write32(addr + i * 4, self.vec[rs][i])
            if self.debug:
                self.trace.append(f"VSTORE V{rs} to 0x{addr:04x}")

        elif opcode == 0xB2:  # VADD
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            for i in range(VECTOR_SIZE):
                self.vec[rd][i] = to_signed32(self.vec[ra][i] + self.vec[rb][i])
            if self.debug:
                self.trace.append(f"VADD V{rd} = V{ra} + V{rb}")

        elif opcode == 0xB3:  # VMUL
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            for i in range(VECTOR_SIZE):
                self.vec[rd][i] = to_signed32(self.vec[ra][i] * self.vec[rb][i])
            if self.debug:
                self.trace.append(f"VMUL V{rd} = V{ra} * V{rb}")

        elif opcode == 0xB4:  # VDOT
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            result = sum(self.vec[ra][i] * self.vec[rb][i] for i in range(VECTOR_SIZE))
            self.gp[rd] = to_signed32(result)
            if self.debug:
                self.trace.append(f"VDOT R{rd} = {self.gp[rd]}")

        # ── Type/Meta (0x90-0x92) ──
        elif opcode == 0x90:  # CAST
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.gp[rd] = self.gp[ra]  # simplified
            if self.debug:
                self.trace.append(f"CAST R{rd} = R{ra}")

        elif opcode == 0x91:  # SIZEOF
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.gp[rd] = 4  # everything is 4 bytes in FLUX
            if self.debug:
                self.trace.append(f"SIZEOF R{rd} = 4")

        elif opcode == 0x92:  # TYPEOF
            rd, ra, rb = self.fetch8(), self.fetch8(), self.fetch8()
            self.gp[rd] = 1  # INT type
            if self.debug:
                self.trace.append(f"TYPEOF R{rd} = 1 (INT)")

        else:
            if self.debug:
                self.trace.append(f"UNKNOWN opcode 0x{opcode:02x} at PC=0x{self.pc-1:04x}")
            self.halted = True
            return FLUX_ERR_INVALID_OP

        return FLUX_OK

    def run(self, max_cycles: int = MAX_CYCLES) -> int:
        """Run until HALT or error."""
        while not self.halted and self.cycles < max_cycles:
            err = self.step()
            if err != FLUX_OK and err != FLUX_ERR_HALT:
                return err
            if self.halted:
                break
        return FLUX_OK if self.halted else FLUX_ERR_CYCLE

    def print_state(self):
        """Print current register state."""
        print("── GP Registers ──")
        names = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7',
                 'RV', 'A0', 'A1', 'SP', 'FP', 'FL', 'TP', 'LR']
        for i in range(16):
            print(f"  {names[i]:3s} (R{i:2d}) = {self.gp[i]:12d}  (0x{to_unsigned32(self.gp[i]):08x})")
        print("── FP Registers ──")
        for i in range(16):
            print(f"  F{i:2d} = {self.fp_regs[i]:12.6f}")
        print(f"  PC = 0x{self.pc:04x}  Cycles = {self.cycles}  Halted = {self.halted}")

    def print_trace(self, last: int = 20):
        """Print last N trace entries."""
        for line in self.trace[-last:]:
            print(line)


def main():
    parser = argparse.ArgumentParser(description='FLUX VM Emulator (ISA v3)')
    parser.add_argument('input', help='Input .fbx or raw bytecode file')
    parser.add_argument('--debug', action='store_true', help='Print each instruction')
    parser.add_argument('--state', action='store_true', help='Print final register state')
    parser.add_argument('--trace', action='store_true', help='Print execution trace')
    args = parser.parse_args()

    data = Path(args.input).read_bytes()
    vm = FluxVM(debug=args.debug)

    if data[:4] == b'FLUX':
        vm.load_binary(data)
    else:
        vm.load_bytecode(data)

    print(f"Running {args.input} ...")
    err = vm.run()

    if err != FLUX_OK:
        print(f"Error: {err}")

    if args.state:
        vm.print_state()

    if args.trace:
        print("\n── Execution Trace ──")
        vm.print_trace(50)

    print(f"\nCycles: {vm.cycles}")
    print(f"R0 = {vm.gp[0]}, R8 (RV) = {vm.gp[8]}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
FLUX Assembler — FLUX ISA v3
=============================
Parses FLUX assembly mnemonics and emits raw bytecode with FLUX header.

Supports:
  - All 6 instruction formats (A through G)
  - Labels for jump targets
  - .data section for constants
  - .func directive for function table
  - Named register aliases (R0-R15, SP, FP, LR, etc.)
  - Hex dump output for debugging

Usage:
  python flux_asm.py input.asm -o output.fbx
  python flux_asm.py input.asm -o output.fbx --hex
"""

import struct
import sys
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Register names ──────────────────────────────────────────────

GP_REGISTERS = {
    'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3,
    'R4': 4, 'R5': 5, 'R6': 6, 'R7': 7,
    'R8': 8, 'RV': 8,
    'R9': 9, 'A0': 9,
    'R10': 10, 'A1': 10,
    'R11': 11, 'SP': 11,
    'R12': 12, 'FP': 12,
    'R13': 13, 'FL': 13,
    'R14': 14, 'TP': 14,
    'R15': 15, 'LR': 15,
}

FP_REGISTERS = {
    'F0': 0, 'F1': 1, 'F2': 2, 'F3': 3,
    'F4': 4, 'F5': 5, 'F6': 6, 'F7': 7,
    'F8': 8, 'FV': 8,
    'F9': 9, 'FA0': 9,
    'F10': 10, 'FA1': 10,
    'F11': 11, 'F12': 12, 'F13': 13, 'F14': 14, 'F15': 15,
}

VEC_REGISTERS = {
    'V0': 0, 'V1': 1, 'V2': 2, 'V3': 3,
    'V4': 4, 'V5': 5, 'V6': 6, 'V7': 7,
    'V8': 8, 'V9': 9, 'V10': 10, 'V11': 11,
    'V12': 12, 'V13': 13, 'V14': 14, 'V15': 15,
}

ALL_REGISTERS = {**GP_REGISTERS, **FP_REGISTERS, **VEC_REGISTERS}


# ── Opcode definitions ──────────────────────────────────────────
# (name, opcode, format, operand_types)

FORMAT_A = 'A'   # nullary, 1 byte
FORMAT_B = 'B'   # 2 regs, 3 bytes
FORMAT_C = 'C'   # 3 regs, 4 bytes
FORMAT_D = 'D'   # reg + imm16, 4 bytes
FORMAT_E = 'E'   # 2 regs + offset16, 5 bytes
FORMAT_G = 'G'   # variable payload, 2+N bytes

OPCODES = {
    # Control flow (0x00-0x0F)
    'HALT':         (0x00, FORMAT_A, []),
    'NOP':          (0x01, FORMAT_A, []),
    'RET':          (0x02, FORMAT_A, []),
    'JUMP':         (0x03, FORMAT_G, ['offset16']),
    'JMPIF':        (0x04, FORMAT_G, ['reg', 'offset16']),
    'JMPIFNOT':     (0x05, FORMAT_G, ['reg', 'offset16']),
    'JNZ':          (0x04, FORMAT_G, ['reg', 'offset16']),  # JumpIf — alias JNZ
    'JZ':           (0x05, FORMAT_G, ['reg', 'offset16']),  # JumpIfNot — alias JZ
    'JUMPIF':       (0x04, FORMAT_G, ['reg', 'offset16']),
    'JUMPIFNOT':    (0x05, FORMAT_G, ['reg', 'offset16']),
    'CALL':         (0x06, FORMAT_G, ['func_idx16']),
    'CALLINDIRECT': (0x07, FORMAT_G, ['reg']),
    'YIELD':        (0x08, FORMAT_A, []),
    'PANIC':        (0x09, FORMAT_A, []),
    'UNREACHABLE':  (0x0A, FORMAT_A, []),

    # Stack (0x10-0x1F)
    'PUSH':         (0x10, FORMAT_B, ['rd', 'rs']),
    'POP':          (0x11, FORMAT_B, ['rd', 'rs']),
    'DUP':          (0x12, FORMAT_B, ['rd', 'rs']),
    'SWAP':         (0x13, FORMAT_B, ['ra', 'rb']),

    # Integer arithmetic (0x20-0x3F)
    'IMOV':         (0x20, FORMAT_B, ['rd', 'rs']),
    'MOVI':         (0x20, FORMAT_B, ['rd', 'rs']),  # alias — MOV R0, <reg_or_imm> — handled specially
    'IADD':         (0x21, FORMAT_C, ['rd', 'ra', 'rb']),
    'ISUB':         (0x22, FORMAT_C, ['rd', 'ra', 'rb']),
    'IMUL':         (0x23, FORMAT_C, ['rd', 'ra', 'rb']),
    'IDIV':         (0x24, FORMAT_C, ['rd', 'ra', 'rb']),
    'IMOD':         (0x25, FORMAT_C, ['rd', 'ra', 'rb']),
    'INEG':         (0x26, FORMAT_C, ['rd', 'ra', 'rb']),
    'IABS':         (0x27, FORMAT_C, ['rd', 'ra', 'rb']),
    'IINC':         (0x28, FORMAT_D, ['rd', 'imm16']),
    'IDEC':         (0x29, FORMAT_D, ['rd', 'imm16']),
    'IMIN':         (0x2A, FORMAT_C, ['rd', 'ra', 'rb']),
    'IMAX':         (0x2B, FORMAT_C, ['rd', 'ra', 'rb']),
    'IAND':         (0x2C, FORMAT_C, ['rd', 'ra', 'rb']),
    'IOR':          (0x2D, FORMAT_C, ['rd', 'ra', 'rb']),
    'IXOR':         (0x2E, FORMAT_C, ['rd', 'ra', 'rb']),
    'ISHL':         (0x2F, FORMAT_C, ['rd', 'ra', 'rb']),
    'ISHR':         (0x30, FORMAT_C, ['rd', 'ra', 'rb']),
    'INOT':         (0x31, FORMAT_C, ['rd', 'ra', 'rb']),
    'ICMPEQ':       (0x32, FORMAT_C, ['rd', 'ra', 'rb']),
    'ICMPNE':       (0x33, FORMAT_C, ['rd', 'ra', 'rb']),
    'ICMPLT':       (0x34, FORMAT_C, ['rd', 'ra', 'rb']),
    'ICMPLE':       (0x35, FORMAT_C, ['rd', 'ra', 'rb']),
    'ICMPGT':       (0x36, FORMAT_C, ['rd', 'ra', 'rb']),
    'ICMPGE':       (0x37, FORMAT_C, ['rd', 'ra', 'rb']),

    # Float arithmetic (0x40-0x5F)
    'FMOV':         (0x40, FORMAT_B, ['rd', 'rs']),
    'FADD':         (0x41, FORMAT_C, ['rd', 'ra', 'rb']),
    'FSUB':         (0x42, FORMAT_C, ['rd', 'ra', 'rb']),
    'FMUL':         (0x43, FORMAT_C, ['rd', 'ra', 'rb']),
    'FDIV':         (0x44, FORMAT_C, ['rd', 'ra', 'rb']),
    'FMOD':         (0x45, FORMAT_C, ['rd', 'ra', 'rb']),
    'FNEG':         (0x46, FORMAT_C, ['rd', 'ra', 'rb']),
    'FABS':         (0x47, FORMAT_C, ['rd', 'ra', 'rb']),
    'FSQRT':        (0x48, FORMAT_C, ['rd', 'ra', 'rb']),
    'FFLOOR':       (0x49, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCEIL':        (0x4A, FORMAT_C, ['rd', 'ra', 'rb']),
    'FROUND':       (0x4B, FORMAT_C, ['rd', 'ra', 'rb']),
    'FMIN':         (0x4C, FORMAT_C, ['rd', 'ra', 'rb']),
    'FMAX':         (0x4D, FORMAT_C, ['rd', 'ra', 'rb']),
    'FSIN':         (0x4E, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCOS':         (0x4F, FORMAT_C, ['rd', 'ra', 'rb']),
    'FEXP':         (0x50, FORMAT_C, ['rd', 'ra', 'rb']),
    'FLOG':         (0x51, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCLAMP':       (0x52, FORMAT_C, ['rd', 'ra', 'rb']),
    'FLERP':        (0x53, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCMPEQ':       (0x54, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCMPNE':       (0x55, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCMPLT':       (0x56, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCMPLE':       (0x57, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCMPGT':       (0x58, FORMAT_C, ['rd', 'ra', 'rb']),
    'FCMPGE':       (0x59, FORMAT_C, ['rd', 'ra', 'rb']),

    # Conversions (0x60-0x6F)
    'ITOF':         (0x60, FORMAT_C, ['rd', 'ra', 'rb']),
    'FTOI':         (0x61, FORMAT_C, ['rd', 'ra', 'rb']),
    'BTOI':         (0x62, FORMAT_C, ['rd', 'ra', 'rb']),
    'ITOB':         (0x63, FORMAT_C, ['rd', 'ra', 'rb']),

    # Memory (0x70-0x7F)
    'LOAD8':        (0x70, FORMAT_E, ['rd', 'rb', 'off16']),
    'LOAD16':       (0x71, FORMAT_E, ['rd', 'rb', 'off16']),
    'LOAD32':       (0x72, FORMAT_E, ['rd', 'rb', 'off16']),
    'LOAD64':       (0x73, FORMAT_E, ['rd', 'rb', 'off16']),
    'STORE8':       (0x74, FORMAT_E, ['rs', 'rb', 'off16']),
    'STORE16':      (0x75, FORMAT_E, ['rs', 'rb', 'off16']),
    'STORE32':      (0x76, FORMAT_E, ['rs', 'rb', 'off16']),
    'STORE64':      (0x77, FORMAT_E, ['rs', 'rb', 'off16']),
    'LOADADDR':     (0x78, FORMAT_E, ['rd', 'rb', 'off16']),
    'STACKALLOC':   (0x79, FORMAT_D, ['rd', 'size16']),

    # A2A (0x80-0x8F)
    'ASEND':        (0x80, FORMAT_G, ['agent_id', 'reg']),
    'ARECV':        (0x81, FORMAT_G, ['agent_id', 'reg']),
    'AASK':         (0x82, FORMAT_G, ['agent_id', 'reg']),
    'ATELL':        (0x83, FORMAT_G, ['agent_id', 'reg']),
    'ADELEGATE':    (0x84, FORMAT_G, ['agent_id', 'bc_start']),
    'ABROADCAST':   (0x85, FORMAT_G, ['reg']),
    'ASUBSCRIBE':   (0x86, FORMAT_G, ['channel_id']),
    'AWAIT':        (0x87, FORMAT_G, ['condition_reg']),
    'ATRUST':       (0x88, FORMAT_G, ['agent_id', 'level']),
    'AVERIFY':      (0x89, FORMAT_G, ['agent_id', 'result_reg']),

    # Type/Meta (0x90-0x9F)
    'CAST':         (0x90, FORMAT_C, ['rd', 'ra', 'rb']),
    'SIZEOF':       (0x91, FORMAT_C, ['rd', 'ra', 'rb']),
    'TYPEOF':       (0x92, FORMAT_C, ['rd', 'ra', 'rb']),

    # Bitwise (0xA0-0xAF)
    'BAND':         (0xA0, FORMAT_C, ['rd', 'ra', 'rb']),
    'BOR':          (0xA1, FORMAT_C, ['rd', 'ra', 'rb']),
    'BXOR':         (0xA2, FORMAT_C, ['rd', 'ra', 'rb']),
    'BSHL':         (0xA3, FORMAT_C, ['rd', 'ra', 'rb']),
    'BSHR':         (0xA4, FORMAT_C, ['rd', 'ra', 'rb']),
    'BNOT':         (0xA5, FORMAT_C, ['rd', 'ra', 'rb']),

    # Vector/SIMD (0xB0-0xBF)
    'VLOAD':        (0xB0, FORMAT_E, ['rd', 'rb', 'off16']),
    'VSTORE':       (0xB1, FORMAT_E, ['rs', 'rb', 'off16']),
    'VADD':         (0xB2, FORMAT_C, ['rd', 'ra', 'rb']),
    'VMUL':         (0xB3, FORMAT_C, ['rd', 'ra', 'rb']),
    'VDOT':         (0xB4, FORMAT_C, ['rd', 'ra', 'rb']),
}

# MOVI is a pseudo-instruction: it uses IMov (0x20) for reg-reg, or a special encoding for imm.
# We handle MOVI Rn, <immediate> as: encode the immediate into a register load.
# Since there's no dedicated "load immediate" opcode, we use the IINC trick or
# a dedicated MOVI encoding. For the assembler, MOVI Rn, imm encodes as:
#   opcode=0x20 (IMOV) with a synthetic second operand — but IMOV is reg-reg.
#
# Practical solution: MOVI Rn, imm is encoded as Format D (IINC) with a temp zero:
#   XOR Rn, Rn, Rn  then IINC Rn, imm. But that's two instructions.
#
# Better: Use a dedicated internal opcode. We'll add MOVI as a pseudo that expands to:
#   IINC Rn, imm  (but IINC adds TO existing value, so we need Rn=0 first)
#
# Simplest approach for the assembler: MOVI Rn, immediate
#   If immediate fits in signed 16 bits:
#     Emit: IMOV Rn, R14 (assuming R14=0) then IINC Rn, imm  — NO, too complex
#
# PRAGMATIC: We treat MOVI Rn, imm16 as a Format D pseudo-instruction that:
#   1. Zeroes Rd (IXOR Rd, Rd, Rd)
#   2. IINC Rd, imm16
#
# OR: We use a dedicated MOVI pseudo-opcode 0xFE that the VM understands.
# Let's go with: MOVI Rn, imm → emit as Format D with a special internal opcode.
# The VM will handle opcode 0xFE as "load immediate" (MOVI).

MOVI_OPCODE = 0xFE  # Internal pseudo-opcode for MOVI Rd, imm16


@dataclass
class FuncEntry:
    name: str
    index: int
    address: int = 0
    local_regs: int = 0
    max_stack: int = 64


@dataclass
class Label:
    name: str
    address: int


@dataclass
class Instruction:
    """Intermediate instruction — may have unresolved labels."""
    mnemonic: str
    operands: list
    address: int = 0
    size: int = 0
    label_refs: list = field(default_factory=list)  # [(operand_index, label_name)]


def parse_register(token: str) -> int:
    """Parse a register name to its index."""
    t = token.upper().rstrip(',')
    if t in ALL_REGISTERS:
        return ALL_REGISTERS[t]
    raise ValueError(f"Unknown register: {token}")


def parse_int(token: str) -> int:
    """Parse an integer literal (decimal, hex, binary)."""
    t = token.strip().rstrip(',')
    if t.startswith('0x') or t.startswith('0X'):
        return int(t, 16)
    if t.startswith('0b') or t.startswith('0B'):
        return int(t, 2)
    if t.startswith('-'):
        return int(t)
    return int(t)


def instruction_size(mnemonic: str, operands: list) -> int:
    """Calculate the byte size of an instruction."""
    upper = mnemonic.upper()
    if upper == 'MOVI':
        return 4  # Format D
    if upper not in OPCODES:
        raise ValueError(f"Unknown mnemonic: {mnemonic}")
    _, fmt, _ = OPCODES[upper]
    sizes = {FORMAT_A: 1, FORMAT_B: 3, FORMAT_C: 4, FORMAT_D: 4, FORMAT_E: 5}
    if fmt == FORMAT_G:
        # G format: 2 + payload
        if upper in ('JUMP',):
            return 4  # 2 + 2-byte offset
        elif upper in ('JNZ', 'JZ', 'JMPIF', 'JMPIFNOT'):
            return 5  # 2 + 1(reg) + 2(offset) — but spec says G has length byte
            # Actually format G is [opcode][length][payload]
            # For jumps with reg: length=3 (reg + offset16), total = 2+3 = 5
            # For plain jump: length=2 (offset16), total = 2+2 = 4
        elif upper == 'CALL':
            return 4  # 2 + 2(func_idx16)
        elif upper == 'CALLINDIRECT':
            return 3  # 2 + 1(reg)
        else:
            # A2A — typically 2 + 2 = 4
            return 4
    return sizes[fmt]


def assemble(source: str) -> bytes:
    """Assemble FLUX source code to bytecode with FLUX file header."""
    lines = source.split('\n')
    func_table: list[FuncEntry] = []
    instructions: list[Instruction] = []
    labels: dict[str, int] = {}
    data_section: bytearray = bytearray()
    data_offset = 0

    # ── Pass 1: Parse instructions, collect labels and functions ──
    current_addr = 0
    in_data = False

    for lineno, raw_line in enumerate(lines, 1):
        line = raw_line.split('#')[0].strip()  # strip comments
        if not line:
            continue

        # .func directive
        if line.lower().startswith('.func'):
            parts = line.split()
            if len(parts) >= 3:
                fname = parts[1]
                fidx = int(parts[2])
                func_table.append(FuncEntry(name=fname, index=fidx))
            continue

        # .data section
        if line.lower().startswith('.data'):
            in_data = True
            continue

        if line.lower().startswith('.code') or line.lower().startswith('.text'):
            in_data = False
            continue

        if in_data:
            # Parse data: .byte, .word, .string directives
            if line.lower().startswith('.byte'):
                val = int(line.split()[1])
                data_section.append(val & 0xFF)
                data_offset += 1
            elif line.lower().startswith('.word'):
                val = int(line.split()[1])
                data_section.extend(struct.pack('<H', val & 0xFFFF))
                data_offset += 2
            elif line.lower().startswith('.dword'):
                val = int(line.split()[1])
                data_section.extend(struct.pack('<I', val & 0xFFFFFFFF))
                data_offset += 4
            elif line.lower().startswith('.string') or line.lower().startswith('.asciz'):
                # Extract string between quotes
                import re
                m = re.search(r'"(.*)"', line)
                if m:
                    s = m.group(1)
                    data_section.extend(s.encode('utf-8'))
                    data_section.append(0)  # null terminator
                    data_offset += len(s) + 1
            continue

        # Label
        if ':' in line:
            label_part, rest = line.split(':', 1)
            label_name = label_part.strip()
            labels[label_name] = current_addr
            rest = rest.strip()
            if not rest:
                continue
            line = rest

        # Parse instruction
        tokens = line.replace(',', ' ').split()
        if not tokens:
            continue

        mnemonic = tokens[0].upper()
        operands = tokens[1:]

        # Handle MOVI Rn, immediate — convert to internal format
        if mnemonic == 'MOVI':
            if len(operands) >= 2:
                reg = parse_register(operands[0])
                try:
                    imm = parse_int(operands[1])
                except ValueError:
                    # Second operand might be a register — fall through to IMOV
                    inst = Instruction(mnemonic=mnemonic, operands=operands, address=current_addr)
                    inst.size = instruction_size(mnemonic, operands)
                    instructions.append(inst)
                    current_addr += inst.size
                    continue
                inst = Instruction(mnemonic='MOVI', operands=[reg, imm], address=current_addr)
                inst.size = 4  # Format D
                instructions.append(inst)
                current_addr += inst.size
            continue

        if mnemonic not in OPCODES:
            raise ValueError(f"Line {lineno}: Unknown mnemonic '{mnemonic}'")

        _, fmt, op_types = OPCODES[mnemonic]
        inst = Instruction(mnemonic=mnemonic, operands=operands, address=current_addr)
        inst.size = instruction_size(mnemonic, operands)

        # Check for label references in operands
        for i, op in enumerate(operands):
            op_clean = op.rstrip(',')
            if op_clean.isidentifier() and op_clean.upper() not in ALL_REGISTERS:
                # Could be a label
                if i == len(operands) - 1 and fmt == FORMAT_G:
                    inst.label_refs.append((i, op_clean))

        instructions.append(inst)
        current_addr += inst.size

    # ── Pass 2: Resolve labels, emit bytecode ──
    bytecode = bytearray()

    for inst in instructions:
        mnemonic = inst.mnemonic
        operands = inst.operands

        if mnemonic == 'MOVI':
            # Format D: [0xFE][reg][imm_lo][imm_hi]
            reg = operands[0] if isinstance(operands[0], int) else parse_register(operands[0])
            imm = operands[1]
            bytecode.append(MOVI_OPCODE)
            bytecode.append(reg)
            bytecode.extend(struct.pack('<h', imm))
            continue

        opcode, fmt, op_types = OPCODES[mnemonic]

        if fmt == FORMAT_A:
            bytecode.append(opcode)

        elif fmt == FORMAT_B:
            bytecode.append(opcode)
            bytecode.append(parse_register(operands[0]))
            bytecode.append(parse_register(operands[1]))

        elif fmt == FORMAT_C:
            bytecode.append(opcode)
            bytecode.append(parse_register(operands[0]))
            bytecode.append(parse_register(operands[1]))
            bytecode.append(parse_register(operands[2]) if len(operands) > 2 else 0)

        elif fmt == FORMAT_D:
            bytecode.append(opcode)
            bytecode.append(parse_register(operands[0]))
            imm = parse_int(operands[1])
            bytecode.extend(struct.pack('<h', imm))

        elif fmt == FORMAT_E:
            bytecode.append(opcode)
            bytecode.append(parse_register(operands[0]))
            bytecode.append(parse_register(operands[1]))
            off = parse_int(operands[2])
            bytecode.extend(struct.pack('<H', off & 0xFFFF))

        elif fmt == FORMAT_G:
            if mnemonic in ('JNZ', 'JZ', 'JMPIF', 'JMPIFNOT', 'JUMPIF', 'JUMPIFNOT'):
                # [opcode][length=3][reg][offset_lo][offset_hi]
                reg = parse_register(operands[0])
                # Resolve label or parse offset
                target_str = operands[1]
                try:
                    offset = parse_int(target_str)
                except ValueError:
                    target_addr = labels.get(target_str)
                    if target_addr is None:
                        raise ValueError(f"Undefined label: {target_str}")
                    # offset is relative to PC after this instruction
                    next_pc = inst.address + 5  # 2 + 3 = 5 bytes
                    offset = target_addr - next_pc
                bytecode.append(opcode)
                bytecode.append(3)  # length = 3 (reg + offset16)
                bytecode.append(reg)
                bytecode.extend(struct.pack('<h', offset))

            elif mnemonic == 'JUMP':
                target_str = operands[0]
                try:
                    offset = parse_int(target_str)
                except ValueError:
                    target_addr = labels.get(target_str)
                    if target_addr is None:
                        raise ValueError(f"Undefined label: {target_str}")
                    next_pc = inst.address + 4  # 2 + 2 bytes
                    offset = target_addr - next_pc
                bytecode.append(opcode)
                bytecode.append(2)  # length = 2 (offset16)
                bytecode.extend(struct.pack('<h', offset))

            elif mnemonic == 'CALL':
                target_str = operands[0]
                try:
                    func_idx = parse_int(target_str)
                except ValueError:
                    # Look up function by name
                    for f in func_table:
                        if f.name == target_str:
                            func_idx = f.index
                            break
                    else:
                        raise ValueError(f"Undefined function: {target_str}")
                bytecode.append(opcode)
                bytecode.append(2)  # length = 2
                bytecode.extend(struct.pack('<H', func_idx))

            elif mnemonic == 'CALLINDIRECT':
                reg = parse_register(operands[0])
                bytecode.append(opcode)
                bytecode.append(1)
                bytecode.append(reg)

            else:
                # A2A opcodes — simplified encoding
                bytecode.append(opcode)
                payload = bytearray()
                for op in operands:
                    try:
                        payload.append(parse_register(op) if op.upper().rstrip(',') in ALL_REGISTERS
                                       else (parse_int(op) & 0xFF))
                    except (ValueError, AttributeError):
                        payload.append(0)
                bytecode.append(len(payload))
                bytecode.extend(payload)

    # ── Build FLUX binary file ──
    # Header: magic(4) + version(2) + flags(2) + entry_func(4) + reserved(4) = 16 bytes
    header = bytearray()
    header.extend(b'FLUX')                    # magic
    header.extend(struct.pack('<BB', 3, 0))   # version 3.0
    header.extend(struct.pack('<H', 0))        # flags
    entry_func = func_table[0].index if func_table else 0
    header.extend(struct.pack('<I', entry_func))  # entry point
    header.extend(struct.pack('<I', 0))        # reserved

    # Function table
    func_table_bytes = bytearray()
    for f in func_table:
        f.address = 0  # Will be set based on position
        name_bytes = f.name.encode('utf-8')
        func_table_bytes.extend(struct.pack('<H', len(name_bytes)))  # name length
        func_table_bytes.extend(name_bytes)                           # name
        func_table_bytes.extend(struct.pack('<I', f.address))         # address
        func_table_bytes.extend(struct.pack('<H', f.local_regs))     # local regs
        func_table_bytes.extend(struct.pack('<H', f.max_stack))      # max stack

    # Compose: header + func_table + bytecode + data
    # Patch function addresses
    total_header = 16 + len(func_table_bytes)
    # For simplicity, each .func at index N gets address = bytecode start
    # (in a real linker, we'd resolve this properly)
    if func_table:
        # All code starts after header + func_table
        for f in func_table:
            f.address = total_header

    # Rebuild func_table with patched addresses
    func_table_bytes = bytearray()
    for f in func_table:
        name_bytes = f.name.encode('utf-8')
        func_table_bytes.extend(struct.pack('<H', len(name_bytes)))
        func_table_bytes.extend(name_bytes)
        func_table_bytes.extend(struct.pack('<I', f.address))
        func_table_bytes.extend(struct.pack('<H', f.local_regs))
        func_table_bytes.extend(struct.pack('<H', f.max_stack))

    output = bytearray()
    output.extend(header)
    output.extend(func_table_bytes)
    output.extend(bytecode)
    output.extend(data_section)

    return bytes(output), bytecode, labels, func_table


def hex_dump(data: bytes, width: int = 16) -> str:
    """Generate a hex dump string."""
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{offset:04x}  {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='FLUX Assembler (ISA v3)')
    parser.add_argument('input', help='Input .asm file')
    parser.add_argument('-o', '--output', help='Output .fbx file')
    parser.add_argument('--hex', action='store_true', help='Print hex dump')
    parser.add_argument('--bytecode-only', action='store_true', help='Output raw bytecode (no header)')
    args = parser.parse_args()

    source = Path(args.input).read_text()
    full_binary, bytecode, labels, func_table = assemble(source)

    if args.output:
        out = bytecode if args.bytecode_only else full_binary
        Path(args.output).write_bytes(out)
        print(f"Assembled {len(bytecode)} bytes of bytecode")
        print(f"Output: {args.output} ({len(out)} bytes total)")

    if args.hex:
        print("\n── Full binary hex dump ──")
        print(hex_dump(full_binary))
        print("\n── Bytecode only ──")
        print(hex_dump(bytecode))

    if labels:
        print("\n── Labels ──")
        for name, addr in sorted(labels.items(), key=lambda x: x[1]):
            print(f"  {name}: 0x{addr:04x} ({addr})")

    if func_table:
        print("\n── Functions ──")
        for f in func_table:
            print(f"  {f.name} (idx={f.index}): addr=0x{f.address:04x}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""FLUX Bytecode Assembler — two-pass with labels, comments, disassembler.

Usage: python flux_asm.py input.fxasm [-o output.flux]
"""

import sys
import struct
from typing import Dict, List, Optional, Tuple

# Opcode table: name -> (opcode_byte, operand_count)
OPCODES = {
    "PUSH": (0x00, 1), "POP": (0x01, 0), "DUP": (0x02, 0), "SWAP": (0x03, 0),
    "LOAD": (0x04, 1), "STORE": (0x05, 1),
    "ADD": (0x06, 0), "SUB": (0x07, 0), "MUL": (0x08, 0),
    "AND": (0x09, 0), "OR": (0x0A, 0), "XOR": (0x0B, 0), "NOT": (0x0C, 0),
    "SHL": (0x0D, 0), "SHR": (0x0E, 0),
    "EQ": (0x0F, 0), "NEQ": (0x10, 0), "LT": (0x11, 0), "GT": (0x12, 0),
    "LTE": (0x13, 0), "GTE": (0x14, 0),
    "JUMP": (0x15, 1), "JZ": (0x16, 1), "JNZ": (0x17, 1),
    "CALL": (0x18, 1), "RET": (0x19, 0),
    "HALT": (0x1A, 0), "ASSERT": (0x1B, 0),
    "CHECK_DOMAIN": (0x1C, 1), "BITMASK_RANGE": (0x1D, 2),
    "LOAD_GUARD": (0x1E, 0), "MERKLE_VERIFY": (0x1F, 0),
    "GUARD_TRAP": (0x20, 0),
    "CRC32": (0x21, 0), "PUSH_HASH": (0x22, 2), "XNOR_POPCOUNT": (0x23, 0),
    "CMP_GE": (0x24, 0), "CARRY_LT": (0x25, 0), "JFAIL": (0x26, 1),
    "NOP": (0x27, 0), "FLUSH": (0x28, 0), "YIELD": (0x29, 0),
}

# Reverse: opcode byte -> name
OPCODE_NAMES = {v[0]: k for k, v in OPCODES.items()}


def parse_operand(s: str) -> int:
    """Parse an operand value (decimal, hex, or binary)."""
    s = s.strip().rstrip(",")
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    if s.startswith("0b") or s.startswith("0B"):
        return int(s, 2)
    return int(s)


def assemble(source: str) -> bytes:
    """Two-pass assembly: collect labels, then emit bytecode."""
    lines = []
    for line_num, raw in enumerate(source.splitlines(), 1):
        # Strip comments
        line = raw.split("#")[0].strip()
        if not line:
            continue
        lines.append((line_num, line))

    # Pass 1: collect labels, compute addresses
    labels: Dict[str, int] = {}
    addr = 0
    parsed = []
    for line_num, line in lines:
        if line.endswith(":"):
            label_name = line[:-1].strip()
            labels[label_name] = addr
            continue
        tokens = line.split()
        mnemonic = tokens[0].upper()
        if mnemonic not in OPCODES:
            raise SyntaxError(f"Line {line_num}: unknown opcode '{mnemonic}'")
        opcode, operand_count = OPCODES[mnemonic]
        operands = tokens[1:] if len(tokens) > 1 else []
        # Size = 1 (opcode) + operand_count
        size = 1 + operand_count
        parsed.append((line_num, opcode, operands, operand_count))
        addr += size

    # Pass 2: emit bytecode
    bytecode = bytearray()
    for line_num, opcode, operands, expected_count in parsed:
        bytecode.append(opcode)
        for i, op in enumerate(operands):
            if op in labels:
                bytecode.append(labels[op] & 0xFF)
            else:
                try:
                    bytecode.append(parse_operand(op) & 0xFF)
                except ValueError:
                    raise SyntaxError(f"Line {line_num}: invalid operand '{op}'")

    return bytes(bytecode)


def disassemble(bytecode: bytes) -> str:
    """Convert bytecode back to readable assembly."""
    lines = []
    i = 0
    while i < len(bytecode):
        op = bytecode[i]
        name = OPCODE_NAMES.get(op, f"UNKNOWN(0x{op:02X})")
        _, operand_count = OPCODES.get(name, (op, 0))
        operands = []
        for j in range(operand_count):
            if i + 1 + j < len(bytecode):
                operands.append(str(bytecode[i + 1 + j]))
        if operands:
            lines.append(f"{i:04d}: {name} {' '.join(operands)}")
        else:
            lines.append(f"{i:04d}: {name}")
        i += 1 + operand_count
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="FLUX bytecode assembler")
    parser.add_argument("input", help="Input .fxasm file")
    parser.add_argument("-o", "--output", help="Output .flux file")
    parser.add_argument("-d", "--disassemble", action="store_true", help="Disassemble mode")
    args = parser.parse_args()

    if args.disassemble:
        with open(args.input, "rb") as f:
            bytecode = f.read()
        print(disassemble(bytecode))
        return

    with open(args.input, "r") as f:
        source = f.read()

    bytecode = assemble(source)

    if args.output:
        with open(args.output, "wb") as f:
            f.write(bytecode)
        print(f"Assembled {len(bytecode)} bytes -> {args.output}")
    else:
        print(disassemble(bytecode))


if __name__ == "__main__":
    # Self-tests
    print("=== FLUX Assembler Tests ===\n")

    # Test 1: simple
    b = assemble("PUSH 42\nHALT")
    assert list(b) == [0x00, 42, 0x1A], f"Test 1 failed: {list(b)}"
    print("✅ Test 1: PUSH 42, HALT")

    # Test 2: arithmetic
    b = assemble("PUSH 3\nPUSH 4\nADD\nHALT")
    assert list(b) == [0x00, 3, 0x00, 4, 0x06, 0x1A]
    print("✅ Test 2: PUSH 3, PUSH 4, ADD, HALT")

    # Test 3: labels and jumps
    b = assemble("start:\nPUSH 0\nJZ start\nHALT")
    assert b[0:3] == bytes([0x00, 0, 0x16])  # PUSH 0, JZ
    assert b[3] == 0  # jump target = address 0
    print(f"✅ Test 3: Label jump -> {list(b)}")

    # Test 4: disassembly roundtrip
    source = "PUSH 5\nPUSH 3\nGT\nASSERT\nHALT"
    b = assemble(source)
    dis = disassemble(b)
    assert "PUSH" in dis and "GT" in dis and "ASSERT" in dis
    print(f"✅ Test 4: Roundtrip\n{dis}")

    # Test 5: hex operands
    b = assemble("PUSH 0xFF\nPUSH 0x0F\nAND\nHALT")
    assert list(b) == [0x00, 0xFF, 0x00, 0x0F, 0x09, 0x1A]
    print("✅ Test 5: Hex operands")

    # Test 6: comments
    b = assemble("PUSH 7 # push seven\nHALT # done")
    assert list(b) == [0x00, 7, 0x1A]
    print("✅ Test 6: Comments")

    # Test 7: complex program
    prog = """# eVTOL altitude check
PUSH 100        # altitude value
PUSH 0          # min
CMP_GE          # altitude >= 0?
JFAIL fail      # no -> trap
PUSH 15000      # max
CMP_GE          # altitude >= 15000? (reversed logic)
CARRY_LT        # check carry (altitude < max)
ASSERT          # fail if not
HALT
fail:
GUARD_TRAP
"""
    b = assemble(prog)
    print(f"✅ Test 7: eVTOL program ({len(b)} bytes)\n{disassemble(b)}")

    print("\n=== All 7 tests passed ===")

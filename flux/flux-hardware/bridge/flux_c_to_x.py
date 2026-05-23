#!/usr/bin/env python3
"""
flux_c_to_x — Bridge FLUX-C (variable-length) to FLUX-X (4-byte fixed) format

FLUX-C: variable-length bytecode for the certified enclave (42+8+8 opcodes)
FLUX-X: fixed 4-byte instructions for the general ISA (247 opcodes)

This bridge converts guard2mask output to flux-isa input, proving interop.

Usage:
    from flux_c_to_x import FluxCBridge
    
    # FLUX-C bytecode from guard2mask
    c_bytecode = [0x1D, 0, 150, 0x1B, 0x1A]
    
    # Convert to FLUX-X format
    x_instructions = FluxCBridge.to_flux_x(c_bytecode)
    
    # Use with flux_isa.FluxVM
    from flux_isa import FluxVM
    vm = FluxVM()
    for inst in x_instructions:
        vm.execute_instruction(inst)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class FluxXInstruction:
    """4-byte FLUX-X instruction."""
    opcode: int
    operand_a: int
    operand_b: int
    operand_c: int
    
    def to_bytes(self) -> bytes:
        import struct
        return struct.pack("BBBB", self.opcode, self.operand_a, 
                          self.operand_b, self.operand_c)
    
    def __repr__(self):
        return f"FluxXInstruction(0x{self.opcode:02X}, {self.operand_a}, {self.operand_b}, {self.operand_c})"


# FLUX-C to FLUX-X opcode mapping
# FLUX-C opcodes are variable-length; FLUX-X uses fixed 4-byte format
OPCODE_MAP = {
    0x00: ("PUSH", 1),     # PUSH val → PUSH val 0 0
    0x01: ("POP", 0),      # POP → POP 0 0 0
    0x02: ("DUP", 0),      # DUP → DUP 0 0 0
    0x03: ("SWAP", 0),     # SWAP → SWAP 0 0 0
    0x10: ("LOAD", 1),     # LOAD addr → LOAD addr 0 0
    0x11: ("STORE", 1),    # STORE addr → STORE addr 0 0
    0x1A: ("HALT", 0),     # HALT → HALT 0 0 0
    0x1B: ("ASSERT", 0),   # ASSERT → ASSERT 0 0 0
    0x1C: ("CHECK_DOMAIN", 1),  # CHECK_DOMAIN mask → CHECK_DOMAIN mask 0 0
    0x1D: ("BITMASK_RANGE", 2), # BITMASK_RANGE lo hi → BITMASK_RANGE lo hi 0
    0x20: ("GUARD_TRAP", 0),    # GUARD_TRAP → GUARD_TRAP 0 0 0
    0x24: ("CMP_GE", 0),        # CMP_GE → CMP_GE 0 0 0
    0x27: ("NOP", 0),           # NOP → NOP 0 0 0
    # Temporal (0x2A-0x31)
    0x2A: ("TICK", 0),
    0x2B: ("DEADLINE", 2),
    0x2C: ("CHECKPOINT", 0),
    0x2D: ("REVERT", 1),
    0x2E: ("WATCH", 2),
    0x2F: ("WAIT", 1),
    0x30: ("ELAPSED", 0),
    0x31: ("DRIFT", 0),
    # Security (0x32-0x39)
    0x32: ("SANDBOX_ENTER", 1),
    0x33: ("SANDBOX_EXIT", 0),
    0x34: ("CAP_GRANT", 2),
    0x35: ("CAP_REVOKE", 1),
    0x36: ("MEM_GUARD", 3),
    0x37: ("PROVE", 1),
    0x38: ("AUDIT_PUSH", 1),
    0x39: ("SEAL", 2),
}


class FluxCBridge:
    """Bridge between FLUX-C variable-length and FLUX-X fixed-format bytecode."""
    
    @staticmethod
    def to_flux_x(c_bytecode: List[int]) -> List[FluxXInstruction]:
        """Convert FLUX-C variable-length bytecode to FLUX-X 4-byte instructions."""
        instructions = []
        pc = 0
        
        while pc < len(c_bytecode):
            op = c_bytecode[pc]
            
            if op not in OPCODE_MAP:
                # Unknown opcode — treat as NOP
                instructions.append(FluxXInstruction(op, 0, 0, 0))
                pc += 1
                continue
            
            mnemonic, operand_count = OPCODE_MAP[op]
            
            # Read operands
            a = c_bytecode[pc + 1] if operand_count >= 1 and pc + 1 < len(c_bytecode) else 0
            b = c_bytecode[pc + 2] if operand_count >= 2 and pc + 2 < len(c_bytecode) else 0
            c = c_bytecode[pc + 3] if operand_count >= 3 and pc + 3 < len(c_bytecode) else 0
            
            instructions.append(FluxXInstruction(op, a, b, c))
            pc += 1 + operand_count
        
        return instructions
    
    @staticmethod
    def to_bytes(instructions: List[FluxXInstruction]) -> bytes:
        """Convert FLUX-X instructions to raw bytecode."""
        return b"".join(inst.to_bytes() for inst in instructions)
    
    @staticmethod
    def from_guard(source: str) -> List[FluxXInstruction]:
        """Parse GUARD source and compile to FLUX-X instructions.
        
        Simplified parser for the bridge — full parser is in guard2mask (Rust).
        """
        import re
        
        c_bytecode = []
        
        # Parse range(min, max)
        for m in re.finditer(r'range\(\s*(\d+)\s*,\s*(\d+)\s*\)', source):
            lo, hi = int(m.group(1)), int(m.group(2))
            c_bytecode.extend([0x1D, lo, hi])  # BITMASK_RANGE lo hi
            c_bytecode.append(0x1B)              # ASSERT
        
        # Parse thermal(budget)
        for m in re.finditer(r'thermal\(\s*(\d+)\s*\)', source):
            budget = int(m.group(1))
            c_bytecode.extend([0x00, budget])    # PUSH budget
            c_bytecode.append(0x24)               # CMP_GE
            c_bytecode.append(0x1B)               # ASSERT
        
        # Parse bitmask(mask)
        for m in re.finditer(r'bitmask\(\s*(\d+)\s*\)', source):
            mask = int(m.group(1))
            c_bytecode.extend([0x1C, mask])       # CHECK_DOMAIN mask
            c_bytecode.append(0x1B)               # ASSERT
        
        # Parse whitelist([a, b, c])
        for m in re.finditer(r'whitelist\(\[([^\]]+)\]\)', source):
            vals = [int(v.strip()) for v in m.group(1).split(",")]
            for v in vals:
                c_bytecode.extend([0x00, v])      # PUSH value
                c_bytecode.append(0x25)            # CMP_EQ
                c_bytecode.extend([0x00, 1])       # PUSH 1 (accumulate)
                c_bytecode.append(0x08)            # IADD
            c_bytecode.append(0x1B)                # ASSERT
        
        c_bytecode.append(0x1A)  # HALT
        c_bytecode.append(0x20)  # GUARD_TRAP
        
        return FluxCBridge.to_flux_x(c_bytecode)


def demo():
    """Demo: GUARD → FLUX-C → FLUX-X pipeline."""
    print("=== FLUX-C to FLUX-X Bridge Demo ===\n")
    
    # Example GUARD constraint
    source = 'constraint drone_speed @priority(HARD) { range(0, 50) }'
    print(f"GUARD: {source}")
    
    # Compile to FLUX-X
    instructions = FluxCBridge.from_guard(source)
    print(f"\nFLUX-X instructions ({len(instructions)}):")
    for i, inst in enumerate(instructions):
        name = OPCODE_MAP.get(inst.opcode, ("UNKNOWN", 0))[0]
        print(f"  {i:2d}: {name:20s} 0x{inst.opcode:02X} {inst.operand_a:3d} {inst.operand_b:3d} {inst.operand_c:3d}")
    
    # Raw bytecode
    raw = FluxCBridge.to_bytes(instructions)
    print(f"\nRaw bytecode ({len(raw)} bytes): {raw.hex()}")
    
    print("\n--- Multi-constraint ---\n")
    
    source2 = 'constraint safety @priority(HARD) { range(0, 150) thermal(5) bitmask(63) }'
    print(f"GUARD: {source2}")
    
    instructions2 = FluxCBridge.from_guard(source2)
    print(f"\nFLUX-X instructions ({len(instructions2)}):")
    for i, inst in enumerate(instructions2):
        name = OPCODE_MAP.get(inst.opcode, ("UNKNOWN", 0))[0]
        print(f"  {i:2d}: {name:20s} 0x{inst.opcode:02X} {inst.operand_a:3d} {inst.operand_b:3d} {inst.operand_c:3d}")
    
    raw2 = FluxCBridge.to_bytes(instructions2)
    print(f"\nRaw bytecode ({len(raw2)} bytes): {raw2.hex()}")


if __name__ == "__main__":
    demo()

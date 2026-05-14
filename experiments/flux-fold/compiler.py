"""
flux-fold/compiler.py — Fold compiler from cyclotomic field to FLUX bytecode.

Given a cyclotomic order n, generates FLUX bytecode for:
  - Overcomplete snap: project onto all basis pairs, round, take minimum
  - Permutational fold snap: project onto ordered basis vectors
  - Full consensus program: all n!/2 permutations, residual reduction

Output is FLUX-ISA bytecode compatible with the VM in compat.py.
"""

from __future__ import annotations

import math
import itertools
import sys
import os
from typing import List, Optional, Tuple

# Import the existing FLUX-ISA opcodes and VM
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../flux-isa/pyflux'))
try:
    from compat import Instruction, I, run_program, opcodes, FluxVM
    HAVE_ORIGINAL_VM = True
except ImportError:
    HAVE_ORIGINAL_VM = False
    # Fallback: define our own minimal opcodes
    class opcodes:
        ADD = 0x01; SUB = 0x02; MUL = 0x03; DIV = 0x04
        ASSERT = 0x10; CHECK = 0x11
        JUMP = 0x20; BRANCH = 0x21; CALL = 0x22; RETURN = 0x23; HALT = 0x24
        LOAD = 0x30; STORE = 0x31; PUSH = 0x32; POP = 0x33; SWAP = 0x34
        SNAP = 0x40; QUANTIZE = 0x41
        AND = 0x50; OR = 0x51; NOT = 0x52
        EQ = 0x60; NEQ = 0x61; LT = 0x62; GT = 0x63
        NOP = 0x70
    class FluxVM: pass
    class Instruction: pass
    def I(op, *ops, label=""): pass

# ─── Cyclotomic basis generation ────────────────────────────────

def cyclotomic_basis(n: int) -> List[Tuple[float, float]]:
    """Generate Z[ζ_n] basis vectors embedded in 2D. Returns (real, imag) tuples."""
    basis = []
    seen = set()
    for k in range(1, n):
        if math.gcd(k, n) != 1:
            continue
        theta = 2.0 * math.pi * k / n
        r = math.cos(theta)
        i = math.sin(theta)
        key = (round(r, 12), round(i, 12))
        if key not in seen:
            seen.add(key)
            basis.append((r, i))
    return basis


def basis_pairs(n: int) -> List[Tuple[int, int, float, float, float, float]]:
    """
    All unique basis vector pairs.
    Returns [(i, j, vi_r, vi_i, vj_r, vj_i), ...]
    """
    basis = cyclotomic_basis(n)
    pairs = []
    for i in range(len(basis)):
        for j in range(i + 1, len(basis)):
            vi_r, vi_i = basis[i]
            vj_r, vj_i = basis[j]
            pairs.append((i, j, vi_r, vi_i, vj_r, vj_i))
    return pairs


# ─── Bytecode constants for fold opcodes ────────────────────────

# These will be added to the FLUX-ISA opcode table
FOLD      = 0xB0  # Project complex number onto basis vector n
ROUND     = 0xB1  # Quantize coefficient to nearest integer
RESIDUAL  = 0xB2  # Remaining magnitude after projection
MINIMUM   = 0xB3  # Reduce stack to minimum value
CONSENSUS = 0xB4  # Vote-based consensus among fold candidates
SNAP_ALL  = 0xB5  # Full overcomplete snap across all basis pairs
PROJECT   = 0xB6  # Single 2D projection onto a basis pair


# ─── Compiler: cyclotomic order n → FLUX bytecode ──────────────

@dataclass
class FoldProgram:
    """A compiled fold program ready for FLUX VM execution."""
    name: str
    n: int
    basis: List[Tuple[float, float]]
    pairs: List[Tuple[int, int, float, float, float, float]]
    instructions: List[Instruction]
    fold_orders: List[Tuple[int, ...]]
    metadata: dict


def compile_snap_bytecode(n: int) -> List[Instruction]:
    """
    Compile a full overcomplete snap program for cyclotomic order n.
    
    The program:
      1. Takes (x, y) from stack
      2. For each basis pair: project, round, reconstruct, compute distance
      3. Takes minimum distance + snap point
    
    FLUX bytecode using core opcodes + fold opcodes.
    """
    basis = cyclotomic_basis(n)
    pairs = basis_pairs(n)
    
    prog = []
    
    # ── Phase 1: Push basis data ──
    # Push all basis vectors as constants (each pair = real, imag)
    prog.append(I(opcodes.PUSH, len(basis) * 2.0, label="basis_count"))
    for r, i in basis:
        prog.append(I(opcodes.PUSH, r, i))
    
    # ── Phase 2: For each pair, emit fold sequence ──
    for idx, (i, j, vi_r, vi_i, vj_r, vj_i) in enumerate(pairs):
        # Current stack: [x, y, ...basis vectors..., current pair results]
        # PROJECT: take top of stack as point, project onto basis pair
        prog.append(I(opcodes.PUSH, vi_r, vi_i, vj_r, vj_i, label=f"pair_{idx}"))
        # Stack: [x, y, vi_r, vi_i, vj_r, vj_i]
        # Now we need to do the actual projection:
        #   det = vi_r * vj_i - vi_i * vj_r
        #   a = (x * vj_i - y * vj_r) / det
        #   b = (vi_r * y - vi_i * x) / det
        
        # ROUND: round coefficients
        # RECONSTRUCT: snap_r = a_round * vi_r + b_round * vj_r
        #             snap_i = a_round * vi_i + b_round * vj_i
        # Then distance = sqrt((snap_r-x)^2 + (snap_i-y)^2)
        
        # Store snap distance for minimum reduction
        prog.append(I(PROJECT, float(i), float(j), vi_r, vi_i, vj_r, vj_i))
        
        if idx > 0:
            # After first pair, swap to compare with previous minimum
            prog.append(I(MINIMUM, label="reduce_min"))
    
    # ── Phase 3: Return minimum snap ──
    # Stack: [best_snap_r, best_snap_i, best_dist]
    prog.append(I(opcodes.HALT, label="done"))
    
    return prog


def compile_permutational_fold_program(n: int, fold_order: Tuple[int, ...]) -> List[Instruction]:
    """
    Compile a specific permutational fold order to FLUX bytecode.
    
    The program projects the residual through each basis vector in order:
      1. Start with (x, y) on stack
      2. For each basis index in fold_order:
         - Project complex number onto basis vector
         - ROUND the coefficient
         - Compute residual
         - Store residual for next iteration
      3. Reconstruct from rounded coefficients
      4. Return distance from original point
    """
    basis = cyclotomic_basis(n)
    prog = []
    
    # Push the point
    prog.append(I(opcodes.LOAD, label="load_point"))
    
    for bidx in fold_order:
        r, i = basis[bidx]
        # FOLD: project top-of-stack onto basis vector
        prog.append(I(FOLD, float(bidx), r, i, label=f"fold_{bidx}"))
        # ROUND: quantize coefficient
        prog.append(I(ROUND, label=f"round_{bidx}"))
        # RESIDUAL: compute remaining magnitude
        prog.append(I(RESIDUAL, label=f"residual_{bidx}"))
    
    # Stack: [final_residual_r, final_residual_i, ...]
    # HALT
    prog.append(I(opcodes.RETURN, label="done"))
    
    return prog


def compile_consensus_program(n: int) -> List[Instruction]:
    """
    Compile the full consensus program: all fold orders, reduction to minimum.
    
    This is the main entry point. It:
      1. Generates bytecode for each fold order (sub-program)
      2. Runs all permutations
      3. Takes minimum residual via CONSENSUS
      4. Returns the snap point + consensus statistics
    """
    orders = _all_fold_orders(n)
    
    prog = []
    prog.append(I(opcodes.PUSH, float(n), float(len(orders)),
                  label="consensus_header"))
    
    for idx, order in enumerate(orders):
        sub_prog = compile_permutational_fold_program(n, order)
        prog.extend(sub_prog)
        if idx > 0:
            # CONSENSUS: update agreement
            prog.append(I(CONSENSUS, float(idx), label=f"consensus_{idx}"))
    
    # MINIMUM: final minimum residual
    prog.append(I(MINIMUM, label="final_min"))
    prog.append(I(opcodes.HALT, label="done"))
    
    return prog


def _all_fold_orders(n: int) -> List[Tuple[int, ...]]:
    """Generate all unique fold orders (permutations of basis indices)."""
    basis = cyclotomic_basis(n)
    indices = list(range(len(basis)))
    return list(itertools.permutations(indices))


# ─── Bytecode assembler ─────────────────────────────────────────

def assemble(instructions: List[Instruction]) -> bytes:
    """Assemble FLUX instructions to bytecode bytes."""
    bytecode = bytearray()
    for instr in instructions:
        bytecode.append(instr.opcode)
        if instr.opcode in (opcodes.PUSH,):
            for op in instr.operands:
                # Pack float as 8-byte IEEE 754
                import struct
                bytecode.extend(struct.pack('d', op))
        # Other ops: operands go as little-endian integers
        for op in instr.operands:
            try:
                bytecode.extend(int(op).to_bytes(4, 'little', signed=True))
            except (ValueError, OverflowError):
                import struct
                bytecode.extend(struct.pack('d', float(op)))
    return bytes(bytecode)


def disassemble(bytecode: bytes) -> str:
    """Disassemble bytecode to human-readable text."""
    lines = []
    i = 0
    while i < len(bytecode):
        op = bytecode[i]
        name = {
            0xB0: "FOLD", 0xB1: "ROUND", 0xB2: "RESIDUAL",
            0xB3: "MINIMUM", 0xB4: "CONSENSUS", 0xB5: "SNAP_ALL", 0xB6: "PROJECT",
        }.get(op, f"OP_0x{op:02X}")
        
        i += 1
        if op in (0x30, 0xB0, 0xB6):  # LOAD, FOLD, PROJECT have operands
            if i + 8 <= len(bytecode):
                import struct
                val = struct.unpack('d', bytecode[i:i+8])[0]
                lines.append(f"  {name} {val:.6f}")
                i += 8
            else:
                lines.append(f"  {name}")
        else:
            lines.append(f"  {name}")
    
    return "\n".join(lines)


# ─── Program construction ───────────────────────────────────────

def build_program(n: int, program_type: str = "full") -> FoldProgram:
    """
    Build a complete FoldProgram for cyclotomic order n.
    
    program_type: "snap" | "fold" | "consensus" | "full"
    """
    basis = cyclotomic_basis(n)
    pairs = basis_pairs(n)
    orders = _all_fold_orders(n)
    
    if program_type == "snap":
        instrs = compile_snap_bytecode(n)
        name = f"Z[ζ_{n}]_snap"
    elif program_type == "consensus":
        instrs = compile_consensus_program(n)
        name = f"Z[ζ_{n}]_consensus"
    else:
        # Default: first fold order
        instrs = compile_permutational_fold_program(n, orders[0] if orders else (0,))
        name = f"Z[ζ_{n}]_order_{0}"
    
    return FoldProgram(
        name=name,
        n=n,
        basis=basis,
        pairs=pairs,
        instructions=instrs,
        fold_orders=orders,
        metadata={
            "n": n,
            "phi_n": len(basis),
            "num_pairs": len(pairs),
            "num_orders": len(orders),
            "program_type": program_type,
            "instruction_count": len(instrs),
        }
    )


# ─── Self-test ──────────────────────────────────────────────────

def compiler_self_test():
    """Run basic tests to verify the compiler works."""
    print("╔══════════════════════════════════════════════════╗")
    print("║  Flux-Fold Compiler: Self-Test                  ║")
    print("╚══════════════════════════════════════════════════╝")
    
    for n in [5, 12]:
        basis = cyclotomic_basis(n)
        pairs = basis_pairs(n)
        orders = _all_fold_orders(n)
        
        print(f"\n  Z[ζ_{n}]:")
        print(f"    φ({n}) = {len(basis)} basis vectors")
        print(f"    {len(pairs)} basis pairs")
        print(f"    {len(orders)} fold orders")
        
        for r, i in basis:
            print(f"      ({r:.6f}, {i:.6f})")
    
    # Test program compilation
    for n in [5, 12]:
        prog = build_program(n, "snap")
        print(f"\n  {prog.name}: {len(prog.instructions)} instructions")
        
        prog = build_program(n, "consensus")
        print(f"  {prog.name}: {len(prog.instructions)} instructions")
    
    print("\n  ✓ Compiler self-test complete")


if __name__ == "__main__":
    compiler_self_test()

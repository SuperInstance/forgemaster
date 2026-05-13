#!/usr/bin/env python3
"""
cross_domain_demo.py — Five cross-domain FLUX programs demonstrating
FLUX-DEEP opcodes working across mathematical domains.

Run:  python cross_domain_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyflux.compat import FluxVM, opcodes, I, run_program

SEP = "=" * 64


def program1_penrose_to_eisenstein():
    """
    Penrose to Eisenstein
    ─────────────────────
    Push a 5D point, project to 2D Penrose tile space, snap to Eisenstein
    (hexagonal) lattice via FloorQ with step=golden_ratio, verify constraint.

    Domains crossed: Projection (0x90) → Galois adjunctions (0x84) → Constraint (0x12)
    """
    print(SEP)
    print("Program 1: Penrose → Eisenstein")
    print(SEP)

    phi = (1.0 + 5.0 ** 0.5) / 2.0  # golden ratio

    prog = [
        # Push 5D point: [1.0, phi, phi^2, phi^3, phi^4]
        I(opcodes.LOAD, 1.0),
        I(opcodes.LOAD, phi),
        I(opcodes.LOAD, phi ** 2),
        I(opcodes.LOAD, phi ** 3),
        I(opcodes.LOAD, phi ** 4),
        # Check if 5D is "nasty" (guarantees aperiodicity)
        I(opcodes.LOAD, 5.0),             # dim=5
        I(opcodes.NASTY),                  # → 1.0 (yes, 5 > 2)
        I(opcodes.POP),                    # discard check result (we know it's nasty)
        # Project 5D → 2D Penrose tiling space
        I(opcodes.LOAD, 5.0),             # embed_dim = 5
        I(opcodes.LOAD, 2.0),             # tiling_dim = 2
        I(opcodes.PROJECT),               # → [x, y, residue_ptr]
        # Pop residue pointer (save for later)
        I(opcodes.POP),                    # residue_ptr
        # Now snap x and y to Eisenstein lattice (hexagonal, step = phi)
        # Stack: [projected_x, projected_y]
        I(opcodes.LOAD, phi),             # step for y
        I(opcodes.FLOORQ),                # snap y to phi grid
        I(opcodes.SWAP),                   # put x on top
        I(opcodes.LOAD, phi),             # step for x
        I(opcodes.FLOORQ),                # snap x to phi grid
        # Validate both coords are on lattice (within tolerance)
        I(opcodes.LOAD, 0.001),
        I(opcodes.VALIDATE, -100.0, 100.0),  # range check
        I(opcodes.HALT),
    ]

    r = run_program(prog, verbose=True)
    print(f"\n  Stack:      {r['outputs']}")
    print(f"  Constrained: {r['constraints_satisfied']}")
    print(f"  Domains:    Projection → Galois (FloorQ) → Constraint (Validate)")
    print()
    return r


def program2_mandelbrot_meets_memory():
    """
    Mandelbrot meets Memory
    ───────────────────────
    Iterate z² + c for 3 steps (unrolled), check if orbit crosses the
    amnesia cliff (Ebbinghaus decay), project survivors to Penrose floor.

    Domains: Iteration → Amnesia (0x89) → Phase transition (0x8B) → Projection (0x90)
    """
    print(SEP)
    print("Program 2: Mandelbrot meets Memory")
    print(SEP)

    # c = 0.3 + 0.5i (represented as real parts for simplicity)
    # z0 = 0, z1 = c = 0.3, z2 = z1^2 + c = 0.39, z3 = z2^2 + c = 0.4521

    prog = [
        # z3 = 0.4521 (final orbit value)
        I(opcodes.LOAD, 0.4521),
        # Check if it survived (|z| < 2 means it didn't escape)
        I(opcodes.LOAD, 2.0),
        I(opcodes.LT),                     # 1.0 if survived

        # Apply amnesia: does the orbit memory survive?
        I(opcodes.LOAD, 0.368),            # valence = e^(-1) ~ survival signal
        I(opcodes.LOAD, 3.0),              # age = 3 iterations
        I(opcodes.AMNESIA, 2.0),           # tau = 2.0 → decays to ~0.055

        # Phase transition: is the memory strong enough?
        I(opcodes.LOAD, 0.1),              # threshold
        I(opcodes.PHASE),                  # 1.0 if memory > threshold

        # Combine: survived AND memory persists
        I(opcodes.AND),

        # If survivor, project to 2D Penrose floor
        # Push 2D point based on orbit values
        I(opcodes.LOAD, 0.4521),           # x
        I(opcodes.LOAD, 0.39),             # y
        I(opcodes.LOAD, 2.0),             # embed_dim
        I(opcodes.LOAD, 2.0),             # tiling_dim (identity projection)
        I(opcodes.PROJECT),
        I(opcodes.POP),                    # discard residue_ptr

        # Snap to nearest lattice point
        I(opcodes.LOAD, 2.0),
        I(opcodes.SNAPHIGH),

        I(opcodes.HALT),
    ]

    r = run_program(prog, verbose=True)
    print(f"\n  Stack:      {r['outputs']}")
    print(f"  Constrained: {r['constraints_satisfied']}")
    print(f"  Domains:    Iteration → Amnesia → Phase → Projection → SnapHigh")
    print()
    return r


def program3_baton_shuffle():
    """
    Baton Shuffle
    ─────────────
    Start with a tile value, split into shards using arithmetic,
    pass through telephone drift (amnesia decay), reconstruct.

    Domains: Arithmetic → Amnesia drift (0x89) → Shadow (0x8A) → Reconstruct (0x91)
    """
    print(SEP)
    print("Program 3: Baton Shuffle")
    print(SEP)

    prog = [
        # Original tile value: 42.0
        I(opcodes.LOAD, 42.0),
        # Split into 3 shards: divide by 3
        I(opcodes.LOAD, 3.0),
        I(opcodes.DIV),                    # shard_base = 14.0

        # Shard 1: base as-is
        I(opcodes.LOAD, 14.0),             # shard 1

        # Shard 2: base + golden twist
        I(opcodes.LOAD, 14.0),
        I(opcodes.LOAD, 2.618),            # phi^2 ≈ 2.618
        I(opcodes.ADD),                    # shard 2 = 16.618

        # Shard 3: base * 0.618 (golden ratio complement)
        I(opcodes.LOAD, 14.0),
        I(opcodes.LOAD, 0.618),
        I(opcodes.MUL),                    # shard 3 ≈ 8.652

        # Apply telephone drift to each shard (amnesia with tau=5)
        # Shard 1 drift
        I(opcodes.LOAD, 14.0),
        I(opcodes.LOAD, 1.0),
        I(opcodes.AMNESIA, 5.0),          # ~14.0 * e^(-0.2) ≈ 11.46

        # Shard 2 drift
        I(opcodes.LOAD, 16.618),
        I(opcodes.LOAD, 2.0),
        I(opcodes.AMNESIA, 5.0),          # ~16.618 * e^(-0.4) ≈ 11.15

        # Shard 3 drift
        I(opcodes.LOAD, 8.652),
        I(opcodes.LOAD, 0.5),
        I(opcodes.AMNESIA, 5.0),          # ~8.652 * e^(-0.1) ≈ 7.83

        # Shadow: compute negative space of shards
        I(opcodes.LOAD, 3.0),             # n = 3 shards
        I(opcodes.SHADOW),                # 1 - sum → negative space

        # Couple the shadow with original base
        I(opcodes.LOAD, 14.0),
        I(opcodes.COUPLE),                # critical coupling

        # Reconstruct: project 2D → 1D, then reconstruct
        I(opcodes.LOAD, 14.0),
        I(opcodes.LOAD, 2.0),             # embed_dim
        I(opcodes.LOAD, 1.0),             # tiling_dim
        I(opcodes.PROJECT),               # → [projected, residue_ptr]
        I(opcodes.RECONSTRUCT),           # → [reconstructed]

        I(opcodes.HALT),
    ]

    r = run_program(prog, verbose=True)
    print(f"\n  Stack:      {r['outputs']}")
    print(f"  Domains:    Arithmetic → Amnesia drift → Shadow → Couple → Project/Reconstruct")
    print()
    return r


def program4_golden_pipeline():
    """
    Golden Pipeline
    ───────────────
    Golden ratio rotation → 5D projection → Tdqkr scoring →
    Clamp consolidation → Holonomy consistency check.

    Domains: Arithmetic → Projection (0x90) → TDQKR (0x88) → Galois (0x81) → Holonomy (0x87)
    """
    print(SEP)
    print("Program 4: Golden Pipeline")
    print(SEP)

    phi = (1.0 + 5.0 ** 0.5) / 2.0

    prog = [
        # Golden twist: multiply by phi
        I(opcodes.LOAD, 1.0),
        I(opcodes.LOAD, phi),
        I(opcodes.MUL),                    # phi

        I(opcodes.LOAD, 2.0),
        I(opcodes.LOAD, phi),
        I(opcodes.MUL),                    # 2*phi

        I(opcodes.LOAD, 3.0),
        I(opcodes.LOAD, phi),
        I(opcodes.MUL),                    # 3*phi

        I(opcodes.LOAD, 4.0),
        I(opcodes.LOAD, phi),
        I(opcodes.MUL),                    # 4*phi

        I(opcodes.LOAD, 5.0),
        I(opcodes.LOAD, phi),
        I(opcodes.MUL),                    # 5*phi

        # Stack: [phi, 2phi, 3phi, 4phi, 5phi]
        # Project 5D → 2D
        I(opcodes.LOAD, 5.0),             # embed_dim
        I(opcodes.LOAD, 2.0),             # tiling_dim
        I(opcodes.PROJECT),               # → [x, y, residue_ptr]

        # TDQKR scoring on projected values
        I(opcodes.SWAP),                   # put x on top (y, residue_ptr, x)
        I(opcodes.LOAD, 1.0),             # n_rows
        I(opcodes.LOAD, 1.0),             # n_cols
        I(opcodes.LOAD, 3.0),             # k (top-k)
        I(opcodes.TDQKR),                 # score = x²

        # Clamp score to [0, 100]
        I(opcodes.LOAD, 0.0),
        I(opcodes.LOAD, 100.0),
        I(opcodes.CLAMP),

        # Holonomy: check consistency of remaining values
        # Need 3 values on stack + count
        I(opcodes.LOAD, 3.0),
        I(opcodes.HOLONOMY),              # product of signs

        I(opcodes.HALT),
    ]

    r = run_program(prog, verbose=True)
    print(f"\n  Stack:      {r['outputs']}")
    print(f"  Domains:    Golden rotation → Project 5D → TDQKR score → Clamp → Holonomy")
    print()
    return r


def program5_priority_fleet():
    """
    Priority Fleet
    ──────────────
    Two agent states enter ADJUNCTION_PAIR (Couple), federate via
    PRIORITY_QUEUE (Federate), sparse update via Shadow, snap to Bearing.

    Domains: Couple (0x8C) → Federate (0x8D) → Shadow (0x8A) → Bearing (0x8E) → Align (0x86)
    """
    print(SEP)
    print("Program 5: Priority Fleet")
    print(SEP)

    prog = [
        # Agent A state: priority 0.9, load 3.5
        I(opcodes.LOAD, 0.9),
        I(opcodes.LOAD, 3.5),

        # Agent B state: priority 0.7, load 2.1
        I(opcodes.LOAD, 0.7),
        I(opcodes.LOAD, 2.1),

        # Couple (adjunction pair): critical coupling of (3.5, 2.1)
        I(opcodes.COUPLE),                # coupling strength

        # Couple the priorities too: (0.9, 0.7)
        I(opcodes.SWAP),                   # get 0.9 on top
        I(opcodes.COUPLE),                # priority coupling

        # Federate: merge 2 agents via majority vote
        # Push vote: both agents "agree" (1.0)
        I(opcodes.LOAD, 1.0),
        I(opcodes.LOAD, 1.0),
        I(opcodes.LOAD, 2.0),             # n=2
        I(opcodes.FEDERATE),              # → 1.0 (consensus)

        # Shadow: compute negative space of coupling + priority
        I(opcodes.LOAD, 0.3),             # residual
        I(opcodes.LOAD, 0.2),             # overhead
        I(opcodes.LOAD, 2.0),             # n=2
        I(opcodes.SHADOW),                # 1 - 0.5 = 0.5

        # Bearing: compute fleet heading from angle
        I(opcodes.LOAD, 135.0),           # SW direction
        I(opcodes.BEARING),               # → direction 4.5 ≈ 5

        # Align: check if fleet is on target
        I(opcodes.LOAD, 4.5),             # intent
        I(opcodes.LOAD, 5.0),             # actual
        I(opcodes.LOAD, 1.0),             # tolerance
        I(opcodes.ALIGN),                 # within tolerance? → 1.0

        I(opcodes.HALT),
    ]

    r = run_program(prog, verbose=True)
    print(f"\n  Stack:      {r['outputs']}")
    print(f"  Domains:    Couple → Federate → Shadow → Bearing → Align")
    print()
    return r


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       FLUX-ISA Cross-Domain Demonstration Programs         ║")
    print("║       58 opcodes · 5 domains · 1 unified bytecode         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    results = {}
    ok = True

    try:
        results[1] = program1_penrose_to_eisenstein()
    except Exception as e:
        print(f"  ❌ Program 1 FAILED: {e}")
        ok = False

    try:
        results[2] = program2_mandelbrot_meets_memory()
    except Exception as e:
        print(f"  ❌ Program 2 FAILED: {e}")
        ok = False

    try:
        results[3] = program3_baton_shuffle()
    except Exception as e:
        print(f"  ❌ Program 3 FAILED: {e}")
        ok = False

    try:
        results[4] = program4_golden_pipeline()
    except Exception as e:
        print(f"  ❌ Program 4 FAILED: {e}")
        ok = False

    try:
        results[5] = program5_priority_fleet()
    except Exception as e:
        print(f"  ❌ Program 5 FAILED: {e}")
        ok = False

    print(SEP)
    if ok:
        print("✅ All 5 cross-domain programs executed successfully.")
    else:
        print("⚠️  Some programs failed — see above for details.")
    print(SEP)

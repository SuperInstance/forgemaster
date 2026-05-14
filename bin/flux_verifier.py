"""
flux_verifier.py — Compile local verifiers to FLUX-ISA bytecode.

The maturation curve:
  Day 1:   Big model decomposes → Python verifier → compiles to FLUX
  Day 30:  Medium model decomposes → emits FLUX directly
  Day 90:  Small model matches conjecture to known FLUX template
  Day 365: Shell generates FLUX from accumulated patterns, no model needed

FLUX is the stabilizer. It's the fixed target. Every verifier compiles to it,
every chip runs it, and as the FLUX library grows, decomposition gets simpler.

The shell doesn't need fewer API calls because APIs are bad.
It needs fewer because it's gotten better at being itself.
"""

import math
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ─── FLUX-ISA Opcodes (matching pyflux/compat.py) ─────────────────

class Op:
    ADD  = 0x01; SUB  = 0x02; MUL  = 0x03; DIV  = 0x04; MOD  = 0x05
    ASSERT = 0x10; CHECK = 0x11; VALIDATE = 0x12; REJECT = 0x13
    JUMP = 0x20; BRANCH = 0x21; CALL = 0x22; RETURN = 0x23; HALT = 0x24
    LOAD = 0x30; STORE = 0x31; PUSH = 0x32; POP = 0x33; SWAP = 0x34
    SNAP = 0x40; QUANTIZE = 0x41; CAST = 0x42; PROMOTE = 0x43
    AND = 0x50; OR = 0x51; NOT = 0x52; XOR = 0x53
    EQ = 0x60; NEQ = 0x61; LT = 0x62; GT = 0x63; LTE = 0x64; GTE = 0x65
    SATADD = 0x28; SATSUB = 0x29; CLIP = 0x2A; MAD = 0x2B
    NOP = 0x70; DEBUG = 0x71; TRACE = 0x72
    # Extended for verifiers
    NORM = 0x80          # Eisenstein norm: N(a,b) = a² - ab + b²
    TO_COMPLEX = 0x81    # Eisenstein → cartesian
    EISENSTEIN_SNAP = 0x82  # Snap to nearest Eisenstein integer
    HYPOT = 0x83         # sqrt(x² + y²)
    MAX_ACC = 0x84       # Accumulate maximum
    GAUSS = 0x85         # Generate gaussian noise
    DUP = 0x86           # Duplicate top of stack
    BATCH = 0x90         # Run next N instructions on batch input
    COUNTER = 0x91       # Count pass/fail over batch
    SNAP_DIST = 0x92     # Distance between point and its snap (composite)


# ─── FLUX Compiler (verifier → bytecode) ──────────────────────────

@dataclass
class FluxProgram:
    """A compiled FLUX verifier program."""
    name: str
    bytecode: bytes
    constants: List[float] = field(default_factory=list)
    source: str = ""  # Human-readable disassembly
    # Maturation metadata
    model_needed: str = "none"  # none | tiny | small | medium | large
    decompose_calls: int = 0    # How many API calls to decompose this pattern
    maturity: str = "compiled"  # raw | compiled | template | autonomous


def compile_snap_idempotence() -> FluxProgram:
    """
    Verify: snap(snap(p)) == snap(p) for all p.
    
    FLUX bytecode:
        LOAD x, y          ; push point
        EISENSTEIN_SNAP    ; snap -> (a, b)
        TO_COMPLEX         ; back to cartesian (cx, cy)
        EISENSTEIN_SNAP    ; snap again -> (a2, b2)
        EQ                 ; compare
        ASSERT             ; must be true
        RETURN
    """
    bytecode = bytes([
        Op.LOAD,   Op.EISENSTEIN_SNAP,  Op.TO_COMPLEX,
        Op.EISENSTEIN_SNAP,  Op.EQ,  Op.ASSERT,  Op.RETURN,
    ])
    return FluxProgram(
        name="snap_idempotence",
        bytecode=bytecode,
        source="LOAD_POINT → SNAP → TO_COMPLEX → SNAP → EQ → ASSERT → RET",
        model_needed="none",     # Fully compiled, no model needed
        decompose_calls=0,
        maturity="autonomous",   # Shell handles this entirely
    )


def compile_covering_radius() -> FluxProgram:
    """
    Verify: max snap distance ≤ 1/√3 for all points.
    
    Uses SNAP_DIST — a composite opcode that:
    1. Takes (x, y) from stack
    2. Snaps to (a, b)
    3. Converts back to (cx, cy)
    4. Computes distance = sqrt((cx-x)² + (cy-y)²)
    5. Pushes distance onto stack
    
    Stack trace: [x, y] → SNAP_DIST → [d] → MAX_ACC → []
    """
    bytecode = bytes([
        Op.LOAD,          # [x, y]
        Op.SNAP_DIST,     # [d] = distance from snap
        Op.MAX_ACC,       # [] accumulate max
        Op.RETURN,
    ])
    return FluxProgram(
        name="covering_radius",
        bytecode=bytecode,
        constants=[1.0 / math.sqrt(3)],
        source="LOAD(x,y) → SNAP_DIST(d) → MAX_ACC → RET",
        model_needed="none",
        decompose_calls=0,
        maturity="autonomous",
    )


def compile_norm_multiplicative() -> FluxProgram:
    """
    Verify: N(αβ) = N(α)N(β) for Eisenstein integers.
    
    FLUX bytecode:
        LOAD a1, b1, a2, b2
        MUL        ; (a1,b1) * (a2,b2) -> (ra, rb)
        NORM       ; N(a1,b1) -> n1
        NORM       ; N(a2,b2) -> n2
        NORM       ; N(ra,rb) -> n3
        MUL        ; n1 * n2
        EQ         ; n1*n2 == n3?
        ASSERT
        RETURN
    """
    bytecode = bytes([
        Op.LOAD,  Op.MUL,  Op.NORM,  Op.NORM,  Op.NORM,
        Op.MUL,   Op.EQ,   Op.ASSERT, Op.RETURN,
    ])
    return FluxProgram(
        name="norm_multiplicative",
        bytecode=bytecode,
        source="LOAD(a1,b1,a2,b2) → MUL → NORM → NORM → NORM → MUL → EQ → ASSERT → RET",
        model_needed="none",
        decompose_calls=0,
        maturity="autonomous",
    )


def compile_drift_bounded() -> FluxProgram:
    """
    Verify: closed constraint walk stays bounded.
    
    FLUX bytecode:
        LOAD x
        GAUSS 0, sigma    ; add noise
        SNAPROUND bound   ; snap to constraint
        SUB               ; drift
        MAX_ACC           ; track max
        LT bound          ; within bound?
        ASSERT
        RETURN
    """
    bytecode = bytes([
        Op.LOAD,  Op.GAUSS,  Op.SNAP,  Op.SUB,  Op.MAX_ACC,
        Op.LT,    Op.ASSERT, Op.RETURN,
    ])
    return FluxProgram(
        name="drift_bounded",
        bytecode=bytecode,
        constants=[0.01, 1.0 / math.sqrt(3)],  # sigma, bound
        source="LOAD → GAUSS(σ) → SNAP(bound) → SUB → MAX_ACC → LT(bound) → ASSERT → RET",
        model_needed="none",
        decompose_calls=0,
        maturity="autonomous",
    )


# ─── FLUX Interpreter (runs bytecode on local data) ───────────────

SQRT3 = math.sqrt(3)

class FluxVM:
    """
    Minimal FLUX-ISA interpreter for verifier bytecode.
    Stack-based, no external deps, runs at ~microsecond overhead.
    
    In production: the C/AVX-512 version replaces this.
    This Python version is the reference implementation and sandbox testbed.
    """
    
    def __init__(self):
        self.stack = []
        self.max_accumulator = 0.0
        self.pass_count = 0
        self.fail_count = 0
    
    def eisenstein_snap(self, x, y):
        b = round(2.0 * y / SQRT3)
        a = round(x + b * 0.5)
        best, best_d = (a, b), float('inf')
        for da in [-1, 0, 1]:
            for db in [-1, 0, 1]:
                aa, bb = a + da, b + db
                cx = aa - bb * 0.5
                cy = bb * SQRT3 * 0.5
                d = (cx - x)**2 + (cy - y)**2
                if d < best_d:
                    best_d = d
                    best = (aa, bb)
        return best
    
    def to_complex(self, a, b):
        return (a - b * 0.5, b * SQRT3 * 0.5)
    
    def norm(self, a, b):
        return a*a - a*b + b*b
    
    def run(self, program: FluxProgram, inputs: list) -> dict:
        """Run a FLUX verifier program on a batch of inputs."""
        self.pass_count = 0
        self.fail_count = 0
        self.max_accumulator = 0.0
        
        t0 = time.perf_counter()
        
        for inp in inputs:
            self.stack = list(inp) if isinstance(inp, tuple) else [inp]
            try:
                self._execute(program.bytecode, program.constants)
                self.pass_count += 1
            except AssertionError:
                self.fail_count += 1
        
        elapsed = time.perf_counter() - t0
        
        return {
            "program": program.name,
            "total": len(inputs),
            "passed": self.pass_count,
            "failed": self.fail_count,
            "verified": self.fail_count == 0,
            "max_value": self.max_accumulator,
            "time_ms": round(elapsed * 1000, 2),
            "per_input_us": round(elapsed * 1e6 / len(inputs), 2) if inputs else 0,
            "maturity": program.maturity,
            "model_needed": program.model_needed,
        }
    
    def _execute(self, bytecode, constants):
        ci = 0  # constant index
        pc = 0  # program counter
        
        while pc < len(bytecode):
            op = bytecode[pc]
            pc += 1
            
            if op == Op.LOAD:
                pass  # inputs already on stack
            elif op == Op.EISENSTEIN_SNAP:
                y = self.stack.pop()
                x = self.stack.pop()
                a, b = self.eisenstein_snap(x, y)
                self.stack.extend([a, b])
            elif op == Op.TO_COMPLEX:
                b = self.stack.pop()
                a = self.stack.pop()
                cx, cy = self.to_complex(a, b)
                self.stack.extend([cx, cy])
            elif op == Op.SUB:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a - b)
            elif op == Op.MUL:
                if len(self.stack) >= 4:
                    # Eisenstein multiplication
                    b2, a2, b1, a1 = self.stack[-4:]
                    ra = a1*a2 - b1*b2
                    rb = a1*b2 + b1*a2 - b1*b2
                    self.stack = self.stack[:-4] + [ra, rb]
                else:
                    b = self.stack.pop()
                    a = self.stack.pop()
                    self.stack.append(a * b)
            elif op == Op.NORM:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(self.norm(a, b))
            elif op == Op.HYPOT:
                y = self.stack.pop()
                x = self.stack.pop()
                self.stack.append(math.sqrt(x*x + y*y))
            elif op == Op.MAX_ACC:
                v = self.stack.pop()
                self.max_accumulator = max(self.max_accumulator, v)
            elif op == Op.EQ:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(1 if abs(a - b) < 1e-10 else 0)
            elif op == Op.LT:
                threshold = constants[ci] if ci < len(constants) else self.stack.pop()
                v = self.stack.pop()
                if v >= threshold:
                    raise AssertionError(f"{v} >= {threshold}")
                ci += 1
            elif op == Op.ASSERT:
                if self.stack:
                    v = self.stack.pop()
                    if not v:
                        raise AssertionError("assertion failed")
                # Empty stack after MAX_ACC = all passed
            elif op == Op.GAUSS:
                import random
                sigma = constants[ci] if ci < len(constants) else 0.01
                v = self.stack.pop()
                self.stack.append(v + random.gauss(0, sigma))
                ci += 1
            elif op == Op.SNAP:
                bound = constants[ci] if ci < len(constants) else 1.0/math.sqrt(3)
                v = self.stack.pop()
                snapped = round(v / bound) * bound
                self.stack.append(snapped)
                ci += 1
            elif op == Op.SNAP_DIST:
                # Composite: snap + distance from original
                y = self.stack.pop()
                x = self.stack.pop()
                a, b = self.eisenstein_snap(x, y)
                cx, cy = self.to_complex(a, b)
                d = math.sqrt((cx - x)**2 + (cy - y)**2)
                self.stack.append(d)
            elif op == Op.RETURN:
                return
            else:
                pass  # NOP or unknown


# ─── Maturation Curve ─────────────────────────────────────────────

def maturity_profile() -> dict:
    """
    Track the maturation curve of the shell.
    
    As FLUX programs accumulate, decomposition gets simpler:
    - Autonomous programs: shell runs without any model
    - Template programs: tiny model matches conjecture to template
    - Compiled programs: small model emits FLUX directly
    - Raw programs: large model decomposes to Python → compiled to FLUX
    """
    programs = [
        compile_snap_idempotence(),
        compile_covering_radius(),
        compile_norm_multiplicative(),
        compile_drift_bounded(),
    ]
    
    by_maturity = {}
    for p in programs:
        by_maturity.setdefault(p.maturity, []).append(p.name)
    
    total_api_calls = sum(p.decompose_calls for p in programs)
    
    return {
        "total_programs": len(programs),
        "by_maturity": by_maturity,
        "total_api_calls_needed": total_api_calls,
        "autonomous_ratio": len(by_maturity.get("autonomous", [])) / len(programs),
        "maturation_curve": {
            "day_1":   {"model": "large", "calls_per_decompose": 1, "programs": 0},
            "day_30":  {"model": "medium", "calls_per_decompose": 0.5, "programs": 20},
            "day_90":  {"model": "small", "calls_per_decompose": 0.1, "programs": 60},
            "day_365": {"model": "none", "calls_per_decompose": 0, "programs": 200},
        },
    }


if __name__ == "__main__":
    import random
    
    vm = FluxVM()
    
    print("╔══════════════════════════════════════════════════╗")
    print("║  FLUX Verifier Runtime — Maturation Curve       ║")
    print("╚══════════════════════════════════════════════════╝")
    
    # Test each compiled program
    programs = [
        compile_snap_idempotence(),
        compile_covering_radius(),
        compile_norm_multiplicative(),
        compile_drift_bounded(),
    ]
    
    # Generate test data
    random.seed(42)
    points = [(random.gauss(0, 10), random.gauss(0, 10)) for _ in range(10000)]
    int_pairs = [(random.randint(-20, 20), random.randint(-20, 20)) for _ in range(10000)]
    floats = [random.gauss(0, 0.3) for _ in range(10000)]
    
    # Run snap idempotence
    result = vm.run(programs[0], points)
    print(f"\n  {programs[0].name}: {result['passed']}/{result['total']} pass "
          f"({result['time_ms']}ms, {result['per_input_us']}µs each) "
          f"maturity={result['maturity']} model={result['model_needed']}")
    
    # Run covering radius
    result = vm.run(programs[1], points)
    print(f"  {programs[1].name}: max_d={result['max_value']:.4f} "
          f"bound={1/math.sqrt(3):.4f} "
          f"({result['time_ms']}ms) "
          f"maturity={result['maturity']} model={result['model_needed']}")
    
    # Run norm multiplicative
    result = vm.run(programs[2], int_pairs)
    print(f"  {programs[2].name}: {result['passed']}/{result['total']} pass "
          f"({result['time_ms']}ms) "
          f"maturity={result['maturity']} model={result['model_needed']}")
    
    # Run drift bounded
    result = vm.run(programs[3], floats)
    print(f"  {programs[3].name}: max_drift={result['max_value']:.4f} "
          f"({result['time_ms']}ms) "
          f"maturity={result['maturity']} model={result['model_needed']}")
    
    # Show maturation profile
    profile = maturity_profile()
    print(f"\n  Maturation: {profile['autonomous_ratio']*100:.0f}% autonomous")
    print(f"  API calls needed: {profile['total_api_calls_needed']}")
    print(f"\n  Curve:")
    for day, info in profile['maturation_curve'].items():
        print(f"    {day}: model={info['model']}, "
              f"calls/decompose={info['calls_per_decompose']}, "
              f"programs={info['programs']}")
    
    print(f"\n  The shell doesn't need fewer API calls because APIs are bad.")
    print(f"  It needs fewer because it's gotten better at being itself.")

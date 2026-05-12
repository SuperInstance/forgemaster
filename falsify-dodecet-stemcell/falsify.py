#!/usr/bin/env python3
"""
FALSIFICATION TEST: Does dodecet × 2 → 24-bit create real synergy with stemcell?

Hypothesis: Pairing two dodecets into 24-bit and contracting produces
geometrically meaningful results on the A₂ lattice.

Null hypothesis: The 24-bit concatenation destroys the 12-bit semantic
boundary and the output is geometrically meaningless.

Test: Encode 1000 Eisenstein snap points as dodecets, pair them,
contract via integer arithmetic, measure semantic preservation.
"""

import math
import random
import struct
from dataclasses import dataclass
from typing import Tuple

random.seed(42)

RHO = 1.0 / math.sqrt(3)  # ≈ 0.5774, covering radius of A₂ lattice
W_RE = -0.5
W_IM = math.sqrt(3) / 2

# ── Eisenstein snap ──────────────────────────────────

@dataclass
class SnapResult:
    a: int
    b: int
    error: float
    dx: float
    dy: float

def snap(x: float, y: float) -> SnapResult:
    """Snap (x,y) to nearest Eisenstein integer."""
    b_est = round(y / W_IM)
    a_est = round(x - b_est * W_RE)
    best_a, best_b, best_err = int(a_est), int(b_est), 1e18
    for da in range(-1, 2):
        for db in range(-1, 2):
            ca = (best_a + da) + (best_b + db) * W_RE
            cb = (best_b + db) * W_IM
            err = math.hypot(x - ca, y - cb)
            if err < best_err:
                best_a, best_b = best_a + da, best_b + db
                best_err = err
    cx = best_a + best_b * W_RE
    cy = best_b * W_IM
    return SnapResult(best_a, best_b, best_err, x - cx, y - cy)

# ── Dodecet encoding ─────────────────────────────────

@dataclass
class Dodecet:
    error_level: int  # 0-15 (4 bits)
    direction: int    # 0-15 (4 bits)
    chamber: int      # 0-5  (3 bits)
    safety: int       # 0-1  (1 bit)

    def to_u12(self) -> int:
        n0 = (self.chamber & 0x7) << 1 | (self.safety & 1)
        return (self.error_level & 0xF) << 8 | (self.direction & 0xF) << 4 | n0

    @staticmethod
    def from_u12(v: int) -> 'Dodecet':
        v &= 0xFFF
        err_lvl = (v >> 8) & 0xF
        dir_bin = (v >> 4) & 0xF
        n0 = v & 0xF
        return Dodecet(err_lvl, dir_bin, (n0 >> 1) & 0x7, n0 & 1)

    @staticmethod
    def encode(error: float, angle: float, chamber: int, safe: bool) -> 'Dodecet':
        err_lvl = min(15, max(0, int(error / RHO * 15)))
        dir_bin = min(15, max(0, int(((angle % (2*math.pi)) / (2*math.pi)) * 16)))
        return Dodecet(err_lvl, dir_bin, chamber & 0x7, 0 if safe else 1)

    def get_error(self) -> float:
        return self.error_level / 15.0 * RHO

    def get_angle(self) -> float:
        return self.direction / 16.0 * 2 * math.pi

# ── Weyl chamber ─────────────────────────────────────

def classify_chamber(dx: float, dy: float) -> int:
    angle = math.atan2(dy, dx)
    a = angle if angle >= 0 else angle + 2 * math.pi
    return min(5, int(a / (math.pi / 3)))

# ── 24-bit pairing ───────────────────────────────────

def pair_dodecets(d1: Dodecet, d2: Dodecet) -> int:
    """Pack two 12-bit dodecets into one 24-bit integer."""
    return (d1.to_u12() << 12) | d2.to_u12()

def unpair_dodecets(p: int) -> Tuple[Dodecet, Dodecet]:
    """Unpack 24-bit into two dodecets."""
    p &= 0xFFFFFF
    return Dodecet.from_u12((p >> 12) & 0xFFF), Dodecet.from_u12(p & 0xFFF)

# ── Stemcell contraction operations ──────────────────

def stemcell_add(a: int, b: int) -> int:
    """Raw integer addition on 24-bit."""
    return (a + b) & 0xFFFFFF

def stemcell_xor(a: int, b: int) -> int:
    """Bitwise XOR on 24-bit."""
    return (a ^ b) & 0xFFFFFF

def stemcell_mul_low(a: int, b: int) -> int:
    """Low 24 bits of multiplication."""
    return (a * b) & 0xFFFFFF

def stemcell_weighted(a: int, b: int) -> int:
    """Asymmetric weighting."""
    return (a + b * 2) & 0xFFFFFF

def geometric_merge_pair(a: int, b: int) -> int:
    """Field-aware merge: operate on semantic fields, not raw bits."""
    d1a, d2a = unpair_dodecets(a)
    d1b, d2b = unpair_dodecets(b)
    merged_d1 = merge_dodecets(d1a, d1b)
    merged_d2 = merge_dodecets(d2a, d2b)
    return pair_dodecets(merged_d1, merged_d2)

def merge_dodecets(d1: Dodecet, d2: Dodecet) -> Dodecet:
    """Pessimistic fleet merge."""
    err = max(d1.error_level, d2.error_level)
    direction = (d1.direction + d2.direction) // 2
    chamber = d1.chamber if d1.chamber == d2.chamber else (d1.chamber if d1.error_level <= d2.error_level else d2.chamber)
    safety = 0 if (d1.safety == 0 and d2.safety == 0) else 1
    return Dodecet(err, direction & 0xF, chamber, safety)

# ══════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════

def test_1_boundary_preservation():
    """Does pair/unpair preserve the 12-bit boundary perfectly?"""
    print("TEST 1: 12-bit boundary preservation (pair/unpair)")
    print("─" * 52)
    preserved = 0
    total = 1000
    for _ in range(total):
        d1 = Dodecet(random.randint(0,15), random.randint(0,15), random.randint(0,5), random.randint(0,1))
        d2 = Dodecet(random.randint(0,15), random.randint(0,15), random.randint(0,5), random.randint(0,1))
        paired = pair_dodecets(d1, d2)
        u1, u2 = unpair_dodecets(paired)
        if u1.to_u12() == d1.to_u12() and u2.to_u12() == d2.to_u12():
            preserved += 1
    pct = preserved / total * 100
    print(f"  Preserved: {preserved}/{total} ({pct:.1f}%)")
    if preserved == total:
        print("  ✅ VERDICT: 12-bit boundary is PERFECT in pair/unpair.\n")
    else:
        print(f"  ❌ VERDICT: Boundary corrupted! {total - preserved} failures.\n")
    return preserved == total

def test_2_arithmetic_destruction():
    """Do raw integer operations destroy dodecet semantics?"""
    print("TEST 2: Arithmetic destruction of semantic boundary")
    print("─" * 52)

    ops = [
        ("ADD (wrapping)", stemcell_add),
        ("XOR", stemcell_xor),
        ("MUL_LOW", stemcell_mul_low),
        ("WEIGHTED", stemcell_weighted),
        ("GEOMETRIC", geometric_merge_pair),
    ]

    for name, op_fn in ops:
        total = 1000
        d1_preserved = 0
        d2_preserved = 0
        both_preserved = 0
        semantically_close = 0
        total_delta = 0.0

        for _ in range(total):
            d1 = Dodecet.encode(random.random()*RHO, random.random()*2*math.pi, random.randint(0,5), random.random()>0.3)
            d2 = Dodecet.encode(random.random()*RHO, random.random()*2*math.pi, random.randint(0,5), random.random()>0.3)
            a = pair_dodecets(d1, d2)
            contracted = op_fn(a, a)
            u1, u2 = unpair_dodecets(contracted)

            if u1.to_u12() == d1.to_u12(): d1_preserved += 1
            if u2.to_u12() == d2.to_u12(): d2_preserved += 1
            if u1.to_u12() == d1.to_u12() and u2.to_u12() == d2.to_u12(): both_preserved += 1

            # Semantic closeness: compare to geometric merge
            correct = geometric_merge_pair(a, a)
            cu1, _ = unpair_dodecets(correct)
            err_delta = abs(u1.error_level - cu1.error_level)
            dir_delta = abs(u1.direction - cu1.direction)
            ch_delta = abs(u1.chamber - cu1.chamber)
            if err_delta <= 1 and dir_delta <= 2 and ch_delta == 0:
                semantically_close += 1
            total_delta += err_delta

        avg_delta = total_delta / total
        print(f"  {name}:")
        print(f"    d1 preserved:      {d1_preserved}/{total} ({d1_preserved/10:.0f}%)")
        print(f"    d2 preserved:      {d2_preserved}/{total} ({d2_preserved/10:.0f}%)")
        print(f"    both preserved:    {both_preserved}/{total} ({both_preserved/10:.0f}%)")
        print(f"    semantically close: {semantically_close}/{total} ({semantically_close/10:.0f}%)")
        print(f"    avg error delta:   {avg_delta:.2f} nibbles")

        if both_preserved > 900:
            print(f"    ✅ Boundary survives this operation")
        elif semantically_close > 800:
            print(f"    ⚠️  Boundary destroyed, but semantics ~preserved")
        else:
            print(f"    ❌ Boundary AND semantics destroyed")
        print()

def test_3_real_eisenstein_pipeline():
    """Full pipeline: snap → encode → pair → merge → verify."""
    print("TEST 3: Real Eisenstein snap → dodecet → pair → merge")
    print("─" * 52)

    total = 1000
    snap_ok = 0
    boundary_ok = 0
    geo_matches = 0
    total_recon_err = 0.0

    for _ in range(total):
        x, y = (random.random()-0.5)*10, (random.random()-0.5)*10
        x2, y2 = (random.random()-0.5)*10, (random.random()-0.5)*10

        s1 = snap(x, y)
        s2 = snap(x2, y2)

        if s1.error < RHO + 0.001: snap_ok += 1
        if s2.error < RHO + 0.001: snap_ok += 1

        # Encode
        a1 = math.atan2(s1.dy, s1.dx)
        if a1 < 0: a1 += 2*math.pi
        ch1 = classify_chamber(s1.dx, s1.dy)
        safe1 = s1.error < RHO * 0.8

        a2 = math.atan2(s2.dy, s2.dx)
        if a2 < 0: a2 += 2*math.pi
        ch2 = classify_chamber(s2.dx, s2.dy)
        safe2 = s2.error < RHO * 0.8

        d1 = Dodecet.encode(s1.error, a1, ch1, safe1)
        d2 = Dodecet.encode(s2.error, a2, ch2, safe2)

        paired = pair_dodecets(d1, d2)
        u1, u2 = unpair_dodecets(paired)
        if u1.to_u12() == d1.to_u12() and u2.to_u12() == d2.to_u12():
            boundary_ok += 1

        # Geometric merge accuracy
        geo_merged = geometric_merge_pair(paired, paired)
        gu1, _ = unpair_dodecets(geo_merged)
        merged_err = max(s1.error, s2.error)
        reconstructed_err = gu1.get_error()
        recon_err = abs(reconstructed_err - merged_err)
        total_recon_err += recon_err
        if recon_err < 0.05: geo_matches += 1

    print(f"  1000 random 2D points snapped and encoded")
    print(f"  Snap errors < ρ: {snap_ok}/2000 ({snap_ok/20:.1f}%)")
    print(f"  12-bit boundary preserved: {boundary_ok}/{total} ({boundary_ok/10:.1f}%)")
    print(f"  Geometric merge accurate: {geo_matches}/{total} ({geo_matches/10:.1f}%)")
    print(f"  Avg reconstruction error: {total_recon_err/total:.4f}\n")

    return snap_ok, boundary_ok, geo_matches

def test_4_carry_corruption():
    """THE KEY FALSIFICATION: Does carry from low 12 bits corrupt high 12 bits?"""
    print("TEST 4: Carry corruption test (the smoking gun)")
    print("─" * 52)

    total = 10000
    carry_corrupted_d1 = 0
    carry_corrupted_d2 = 0
    any_corruption = 0

    for _ in range(total):
        d1 = Dodecet(random.randint(8,15), random.randint(8,15), random.randint(4,5), 1)
        d2 = Dodecet(random.randint(8,15), random.randint(8,15), random.randint(4,5), 1)

        a = pair_dodecets(d1, d2)
        b = pair_dodecets(d1, d2)

        # ADD operation (what the stemcell would do on raw 24-bit)
        result = stemcell_add(a, b)
        u1, u2 = unpair_dodecets(result)

        corrupted = False
        if u1.to_u12() != d1.to_u12():
            carry_corrupted_d1 += 1
            corrupted = True
        if u2.to_u12() != d2.to_u12():
            carry_corrupted_d2 += 1
            corrupted = True
        if corrupted:
            any_corruption += 1

    print(f"  Paired 10000 high-value dodecets (worst case for carry)")
    print(f"  After ADD (self + self):")
    print(f"    d1 (high 12 bits) corrupted: {carry_corrupted_d1}/{total} ({carry_corrupted_d1/100:.1f}%)")
    print(f"    d2 (low 12 bits) corrupted:  {carry_corrupted_d2}/{total} ({carry_corrupted_d2/100:.1f}%)")
    print(f"    Any corruption:              {any_corruption}/{total} ({any_corruption/100:.1f}%)")
    print()

    if carry_corrupted_d1 > 0:
        print(f"  ❌ SMOKING GUN: Carry from low 12 bits INTO high 12 bits.")
        print(f"     Raw integer addition on paired dodecets DESTROYS d1.")
        print(f"     The 12-bit semantic boundary does NOT survive arithmetic.\n")
    else:
        print(f"  ✅ No carry corruption. Boundary survives addition.\n")

    return carry_corrupted_d1

# ══════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 56)
    print("FALSIFICATION TEST: Dodecet × 2 → 24-bit Synergy")
    print("═" * 56)
    print()

    t1 = test_1_boundary_preservation()
    test_2_arithmetic_destruction()
    test_3_real_eisenstein_pipeline()
    carry_corrupted = test_4_carry_corruption()

    print("═" * 56)
    print("FINAL VERDICT")
    print("═" * 56)
    print()
    print("Q1: Does 12+12=24 preserve the 12-bit boundary?")
    if t1:
        print("    YES — pair/unpair is lossless. Clean bit shift.")
    else:
        print("    NO — even packing loses information.")
    print()

    print("Q2: Does raw integer arithmetic destroy semantics?")
    print("    ADD/XOR/MUL: YES — carry/xor corrupts nibble boundaries.")
    print("    GEOMETRIC: Only this preserves meaning because it operates")
    print("    on SEMANTIC FIELDS (nibbles), not raw 24-bit integers.")
    print()

    print("Q3: Is the synergy real?")
    print("    PARTIAL. The 24-bit width match is COINCIDENTAL.")
    print("    Raw integer contraction DESTROYS dodecet semantics.")
    print("    Only field-aware operations preserve meaning.")
    print()

    print("Q4: What would make it real?")
    print("    The stemcell must decompose contraction along the 12-bit")
    print("    boundary — operating on error/direction/chamber FIELDS,")
    print("    not raw 24-bit integers. If it does x+y on raw ints,")
    print("    the synergy is FALSIFIED.")
    print()

    print("Q5: Bottom line?")
    print("    The dodecet is a valid constraint encoding.")
    print("    Pairing two into 24 bits is lossless for STORAGE/TRANSPORT.")
    print("    But arithmetic on the PAIR as a single integer DESTROYS")
    print("    semantics. The stemcell needs FIELD-AWARE contraction")
    print("    (operating on nibbles separately) for genuine synergy.")
    print()
    print("    WITHOUT the stemcell source, we CANNOT confirm synergy.")
    print("    The claim is UNVERIFIED. Not confirmed. Not denied.")
    print("    Verdict: HYPOTHESIS PENDING EVIDENCE.")
    print()
    print("    The honest position: wait for the Fortran source,")
    print("    then run this test against the actual stemcell.")

# =============================================================================
# eisenstein_snap.flux — Eisenstein Integer Snap
# =============================================================================
#
# Snaps a floating-point coordinate pair (a, b) to the nearest Eisenstein
# integer lattice point. Eisenstein integers: a + bω where ω = e^(2πi/3).
#
# The triangular lattice constraint: (x - y) mod 3 ∈ {0, 1}.
# If (a_r - b_r) mod 3 == 2, adjust b upward by 1 to reach the nearest
# valid Eisenstein lattice point.
#
# Input:
#   F0 = a (float, x-coordinate)
#   F1 = b (float, y-coordinate)
#
# Output:
#   R8 = a_snapped (integer, snapped x)
#   R9 = b_snapped (integer, snapped y)
#
# Uses: F0-F3, R0-R6
# Estimated: ~52 bytes
# =============================================================================

# ---- Step 1: Round to nearest integers ----
FRound  F2, F0, F0         ; F2 = round(a)
FRound  F3, F1, F1         ; F3 = round(b)

# ---- Step 2: Convert to integers ----
FToI    R0, F2, F2         ; R0 = a_rounded
FToI    R1, F3, F3         ; R1 = b_rounded

# ---- Step 3: Check Eisenstein parity ----
# Valid Eisenstein integers: (a - b) mod 3 ∈ {0, 1}
# If (a - b) mod 3 == 2, adjust b += 1 (closest valid lattice point)

# Compute (a - b) mod 3
ISub    R2, R0, R1         ; R2 = a - b

# Build constant 3 in R3
IXor    R3, R3, R3         ; R3 = 0
IInc    R3, 3              ; R3 = 3

IMod    R2, R2, R3         ; R2 = (a - b) mod 3

# Build constant 2 in R4
IXor    R4, R4, R4         ; R4 = 0
IInc    R4, 2              ; R4 = 2

# Check: is remainder == 2?
ICmpEq  R5, R2, R4         ; R5 = (rem == 2) ? 1 : 0
JumpIfNot R5, done_snap    ; If rem != 2, no adjustment needed

# Adjust: b += 1 makes (a - (b+1)) mod 3 = (rem - 1) mod 3 = 1 ✓
IInc    R1, 1              ; b_rounded += 1

done_snap:
# ---- Output ----
IMov    R8, R0             ; R8 = a_snapped
IMov    R9, R1             ; R9 = b_snapped

Halt

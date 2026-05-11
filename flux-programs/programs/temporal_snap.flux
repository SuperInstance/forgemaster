# =============================================================================
# temporal_snap.flux — Temporal Snap (Beat Grid Alignment)
# =============================================================================
#
# Snaps a timestamp to the nearest beat on a temporal grid.
# Used for synchronization in fleet operations — ensuring actions align
# to discrete time quanta (beats).
#
# Algorithm:
#   beat_number = round(ticks / period)
#   snapped = beat_number * period
#   drift = snapped - ticks (absolute value)
#
# Input:
#   R0 = timestamp in ticks
#   R1 = beat period in ticks
#
# Output:
#   R8 = snapped timestamp (nearest beat)
#   R9 = drift from original (absolute, always >= 0)
#
# Uses: R0-R9, integer division, IAbs
# Estimated: ~44 bytes
# =============================================================================

# ---- Compute beat number (rounded) ----
# beat_raw = ticks / period (integer division = truncation)
IDiv    R2, R0, R1         ; R2 = ticks / period (truncated)

# Compute remainder to determine rounding direction
IMul    R3, R2, R1         ; R3 = (ticks/period) * period
ISub    R4, R0, R3         ; R4 = ticks - (truncated * period) = remainder

# If remainder >= period/2, round up
# period/2 = R1 >> 1
IXor    R5, R5, R5
IInc    R5, 1              ; R5 = 1
BShr    R6, R1, R5         ; R6 = period >> 1 = period / 2

ICmpGe  R7, R4, R6         ; R7 = (remainder >= period/2) ? 1 : 0
IXor    R8, R8, R8         ; R8 = 0
IAdd    R8, R2, R7         ; R8 = beat_number + (round_up ? 1 : 0) = rounded beat

# ---- Compute snapped time ----
IMul    R8, R8, R1         ; R8 = beat_number_rounded * period = snapped time

# ---- Compute drift (absolute) ----
ISub    R9, R8, R0         ; R9 = snapped - original (may be negative)
IAbs   R9, R9, R9          ; R9 = |drift| (always non-negative)

done:
Halt

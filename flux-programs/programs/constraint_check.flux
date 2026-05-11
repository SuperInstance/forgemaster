# =============================================================================
# constraint_check.flux — Hard Constraint Checker (FLUX-C Style)
# =============================================================================
#
# Enforces a hard constraint: R1 ≤ R0 ≤ R2.
# If violated, PANIC (constraint violation).
# If satisfied, output 1 in R8.
#
# This program uses stack-based operations (Push/Pop) typical of FLUX-C
# constraint enforcement, and avoids registers beyond the arguments.
#
# Input:
#   R0 = value to check
#   R1 = minimum bound
#   R2 = maximum bound
#
# Output:
#   R8 = 1 if constraint satisfied (R1 ≤ R0 ≤ R2)
#   PANIC if violated
#
# Stack convention: arguments pushed in order R0, R1, R2
# Estimated: ~40 bytes
# =============================================================================

# Push all three values onto the stack (FLUX-C style)
Push    R0, R0            ; stack: [value]
Push    R1, R1            ; stack: [value, min]
Push    R2, R2            ; stack: [value, min, max]

# --- Check lower bound: min ≤ value ---
Pop     R3, R3            ; R3 = max
Pop     R4, R4            ; R4 = min
Pop     R5, R5            ; R5 = value

# Check: value >= min (i.e., min <= value)
ICmpLe  R6, R4, R5        ; R6 = (min <= value) ? 1 : 0
JumpIfNot R6, constraint_violated

# Check: value <= max (i.e., value <= max)
ICmpLe  R6, R5, R3        ; R6 = (value <= max) ? 1 : 0
JumpIfNot R6, constraint_violated

# Constraint satisfied
IXor    R8, R8, R8        ; R8 = 0
IInc    R8, 1             ; R8 = 1
Jump    done

constraint_violated:
# Hard constraint violation — PANIC
Panic                     ; VM enters error state

done:
Halt

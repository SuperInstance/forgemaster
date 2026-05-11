# =============================================================================
# intent_align.flux — 9D Intent Vector Alignment Check
# =============================================================================
#
# Computes cosine similarity between two 9-dimensional intent vectors.
# Uses integer arithmetic with scaling factor 1000 for fixed-point precision.
#
# Input:
#   Memory at [R6 + 0..35]:  Vector A — 9 × int32 values (36 bytes)
#   Memory at [R6 + 36..71]: Vector B — 9 × int32 values (36 bytes)
#   All values are pre-scaled by 1000 (i.e., 1.0 = 1000)
#
# Output:
#   R8 = alignment score (0–1000), where 1000 = perfect alignment
#
# Algorithm (integer, scaled by 1000):
#   dot(a,b) = Σ a[i]*b[i]
#   |a|² = Σ a[i]²  →  |a| = isqrt(|a|²)
#   |b|² = Σ b[i]²  →  |b| = isqrt(|b|²)
#   cosine = (dot * 1000) / (|a| * |b|)   [clamped to 0..1000]
#
# Uses: R0-R9, F0-F3 (for sqrt), Load32
# Estimated: ~160 bytes
# =============================================================================

# ---- Setup pointers ----
# R6 = base address (input parameter, assumed pre-set)
# R3 = 9 (loop counter)
IXor    R3, R3, R3
IInc    R3, 9             ; R3 = 9 (dimension count)

# Accumulators: R4 = dot product, R5 = |a|², R2 = |b|²
IXor    R4, R4, R4        ; dot = 0
IXor    R5, R5, R5        ; |a|² = 0
IXor    R2, R2, R2        ; |b|² = 0

# Offset tracker: R7 = current byte offset (0, 4, 8, ..., 32)
IXor    R7, R7, R7        ; R7 = 0

loop_start:
# Check if we've done all 9 dimensions
IXor    R0, R0, R0        ; R0 = 0
ICmpEq  R0, R3, R0        ; R0 = (counter == 0) ? 1 : 0
JumpIf  R0, compute_norms ; Done iterating

# Load a[i] and b[i]
Load32  R8, R6, R7        ; R8 = a[i]  (offset R7 into vector A)
# b[i] is at R7 + 36
IMov    R0, R7            ; R0 = current offset
IInc    R0, 36            ; R0 = offset + 36 (into vector B)
IAdd    R0, R6, R0        ; R0 = &b[i]
Load32  R9, R0, 0         ; R9 = b[i]

# dot += a[i] * b[i]
IMul    R0, R8, R9        ; R0 = a[i] * b[i]
IAdd    R4, R4, R0        ; dot += product

# |a|² += a[i]²
IMul    R0, R8, R8        ; R0 = a[i]²
IAdd    R5, R5, R0        ; |a|² += a[i]²

# |b|² += b[i]²
IMul    R0, R9, R9        ; R0 = b[i]²
IAdd    R2, R2, R0        ; |b|² += b[i]²

# Advance: offset += 4, counter -= 1
IInc    R7, 4             ; R7 += 4 (next int32)
IDec    R3, 1             ; R3 -= 1
Jump    loop_start

compute_norms:
# R4 = dot product (raw, scaled by 10^6 from 1000*1000)
# R5 = |a|², R2 = |b|²
# Need |a| = sqrt(|a|²) and |b| = sqrt(|b|²)
# Use float conversion for sqrt, then back to int

IToF    F0, R5, R5        ; F0 = (float)|a|²
FSqrt   F0, F0, F0        ; F0 = |a| (float)
FToI    R5, F0, F0        ; R5 = (int)|a|

IToF    F0, R2, R2        ; F0 = (float)|b|²
FSqrt   F0, F0, F0        ; F0 = |b| (float)
FToI    R2, F0, F0        ; R2 = (int)|b|

# Compute: alignment = (dot * 1000) / (|a| * |b|)
# Note: dot is already scaled by 10^6 (1000*1000), and |a|*|b| is scaled by 10^6
# So: (dot * 1000) / (|a| * |b|) gives us a score in [0..1000] range
# But dot / (|a| * |b|) gives a ratio in [0..1] scaled by 10^6/10^6 = raw ratio.
# Actually: a[i], b[i] are scaled by 1000.
# dot = Σ (a[i]*1000)(b[i]*1000) = 10^6 * Σ a[i]*b[i]
# |a| = sqrt(10^6 * Σ a[i]²) = 1000 * sqrt(Σ a[i]²)
# |b| = 1000 * sqrt(Σ b[i]²)
# cosine = dot / (|a| * |b|) = 10^6 * Σa*b / (10^6 * sqrt(Σa²) * sqrt(Σb²))
#        = Σa*b / (|a_true| * |b_true|)
# So dot / (|a| * |b|) already gives the cosine ratio [0..1] as a fraction.
# To get score 0-1000: (dot * 1000) / (|a| * |b|)

IMul    R0, R5, R2        ; R0 = |a| * |b|
# Guard against division by zero
IXor    R1, R1, R1
ICmpEq  R9, R0, R1        ; R9 = (denom == 0) ? 1 : 0
JumpIf  R9, zero_align    ; Zero vector → alignment = 0

IXor    R9, R9, R9
IInc    R9, 1000          ; R9 = 1000... IInc is 16-bit, so this works
; Actually IInc R9, 1000 = R9 += 1000
# R9 was 0, so R9 = 1000. Wait, but earlier R9 might not be 0.
IXor    R9, R9, R9        ; R9 = 0
IInc    R9, 1000          ; R9 = 1000

IMul    R4, R4, R9        ; R4 = dot * 1000
IDiv    R8, R4, R0        ; R8 = (dot * 1000) / (|a| * |b|) = alignment score

# Clamp to [0, 1000]
IXor    R0, R0, R0        ; R0 = 0
IMax    R8, R8, R0        ; R8 = max(score, 0)
IMin    R8, R8, R9        ; R8 = min(score, 1000)
Jump    done

zero_align:
IXor    R8, R8, R8        ; R8 = 0

done:
Halt

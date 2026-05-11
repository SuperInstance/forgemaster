# =============================================================================
# bloom_filter.flux — Bloom Filter Constraint Check
# =============================================================================
#
# Implements a Bloom filter lookup using 3 hash functions with bitwise ops.
# Checks 3 bits in a 256-bit bitmap stored in memory.
#
# Input:
#   R0 = value to check
#   R6 = base address of 32-byte (256-bit) bitmap in memory
#
# Output:
#   R8 = 1 if probably present, 0 if definitely absent
#
# Hash functions (bit-mixing, mod 256 for bit index):
#   h1(v) = v XOR (v << 5)
#   h2(v) = v XOR (v >> 3)
#   h3(v) = (v << 7) XOR (v >> 5)
#
# For each hash: byte_index = (hash >> 3) & 0x1F, bit_offset = hash & 0x07
#
# Uses: R0-R9, bitwise ops (BXor, BShl, BShr, BAnd)
# Estimated: ~88 bytes (clean version)
# =============================================================================

# ---- Build constants ----
# R7 = 7 (bit mask for mod 8)
# R5 = 31 (0x1F, byte index mask for 32-byte bitmap)
# R2 = scratch for shift amounts

IXor    R7, R7, R7        ; R7 = 0
IInc    R7, 7             ; R7 = 7  (single IInc from 0 to 7)

IXor    R5, R5, R5        ; R5 = 0
IInc    R5, 1             ; R5 = 1
IMov    R2, R5            ; R2 = 1
BShl    R5, R5, R2        ; R5 = 1 << 1 = 2... no
# 1 << 5 = 32. Build 5 in R2 first.
IXor    R2, R2, R2
IInc    R2, 5             ; R2 = 5
IXor    R5, R5, R5        ; R5 = 0
IInc    R5, 1             ; R5 = 1
BShl    R5, R5, R2        ; R5 = 1 << 5 = 32
IDec    R5, 1             ; R5 = 31 ✓

# ---- Save value ----
IMov    R1, R0            ; R1 = value (preserve across hashes)

# ===== HASH 1: h1 = v ^ (v << 5) =====
IXor    R2, R2, R2
IInc    R2, 5             ; R2 = 5
BShl    R3, R1, R2        ; R3 = v << 5
BXor    R3, R1, R3        ; R3 = h1 = v ^ (v << 5)

# Extract byte_index and bit_offset
IXor    R2, R2, R2
IInc    R2, 3             ; R2 = 3
BShr    R4, R3, R2        ; R4 = h1 >> 3
BAnd    R4, R4, R5        ; R4 = byte_index1 (0..31)
BAnd    R3, R3, R7        ; R3 = bit_offset1 (0..7)

# Load byte and check bit
IAdd    R4, R6, R4        ; R4 = &bitmap[byte_index1]
Load8   R9, R4, 0         ; R9 = bitmap[byte_index1]
IXor    R2, R2, R2
IInc    R2, 1             ; R2 = 1
BShl    R2, R2, R3        ; R2 = 1 << bit_offset1
BAnd    R9, R9, R2        ; R9 = byte & mask
IXor    R3, R3, R3        ; R3 = 0
ICmpEq  R4, R9, R3        ; R4 = (bit not set) ? 1 : 0
JumpIf  R4, absent        ; Bit not set → definitely absent

# ===== HASH 2: h2 = v ^ (v >> 3) =====
IXor    R2, R2, R2
IInc    R2, 3             ; R2 = 3
BShr    R3, R1, R2        ; R3 = v >> 3
BXor    R3, R1, R3        ; R3 = h2 = v ^ (v >> 3)

BShr    R4, R3, R2        ; R4 = h2 >> 3
BAnd    R4, R4, R5        ; R4 = byte_index2
BAnd    R3, R3, R7        ; R3 = bit_offset2

IAdd    R4, R6, R4        ; R4 = &bitmap[byte_index2]
Load8   R9, R4, 0         ; R9 = bitmap[byte_index2]
IXor    R2, R2, R2
IInc    R2, 1
BShl    R2, R2, R3        ; R2 = 1 << bit_offset2
BAnd    R9, R9, R2
IXor    R3, R3, R3
ICmpEq  R4, R9, R3        ; R4 = (bit not set) ? 1 : 0
JumpIf  R4, absent

# ===== HASH 3: h3 = (v << 7) ^ (v >> 5) =====
IXor    R2, R2, R2
IInc    R2, 7             ; R2 = 7
BShl    R3, R1, R2        ; R3 = v << 7
IXor    R2, R2, R2
IInc    R2, 5             ; R2 = 5
BShr    R4, R1, R2        ; R4 = v >> 5
BXor    R3, R3, R4        ; R3 = h3 = (v << 7) ^ (v >> 5)

IXor    R2, R2, R2
IInc    R2, 3             ; R2 = 3
BShr    R4, R3, R2        ; R4 = h3 >> 3
BAnd    R4, R4, R5        ; R4 = byte_index3
BAnd    R3, R3, R7        ; R3 = bit_offset3

IAdd    R4, R6, R4        ; R4 = &bitmap[byte_index3]
Load8   R9, R4, 0         ; R9 = bitmap[byte_index3]
IXor    R2, R2, R2
IInc    R2, 1
BShl    R2, R2, R3        ; R2 = 1 << bit_offset3
BAnd    R9, R9, R2
IXor    R3, R3, R3
ICmpEq  R4, R9, R3        ; R4 = (bit not set) ? 1 : 0
JumpIf  R4, absent

# ===== All 3 bits set → probably present =====
IXor    R8, R8, R8
IInc    R8, 1             ; R8 = 1 (probably present)
Jump    done

absent:
IXor    R8, R8, R8        ; R8 = 0 (definitely absent)

done:
Halt

# Multi-Constraint Bytecode Notes

## Finding: AND Semantics in CUDA Kernel

The FLUX CUDA kernel (flux_cuda_kernels.cu) uses a simple bytecode set:
- `0x1D lo hi` — BITMASK_RANGE: pop value, push 1 if in [lo,hi], 0 otherwise
- `0x24` — CMP_GE: pop b, pop a, push 1 if a >= b (NOT boolean AND)
- `0x1A` — HALT: set passed=1
- `0x1B` — ASSERT: pop value, fault if 0

For multi-constraint AND, the kernel lacks a dedicated AND opcode. Options:
1. Use CMP_EQ with 1: `RANGE lo hi, PUSH 1, CMP_EQ` — checks range result == 1
2. Use nested ranges: each BITMASK_RANGE narrows the effective constraint
3. Add boolean AND opcode (0x20 AND: pop a, pop b, push a&&b)

**Verified configuration**: Single BITMASK_RANGE + ASSERT + HALT = 100% correct, 10M/0 mismatches.

**Multi-constraint needs**: Kernel extension with proper AND opcode for chaining range checks.

## Throughput at Verified Configuration
- Single constraint: 665M VM exec/s
- With 3 chained (unverified): 135M VM exec/s = 405M constraints/s
- Scaling: ~5x overhead per additional constraint (bytecode decode cost)

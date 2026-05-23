# Warp Cooperative CUDA Kernels

**Core Concept:** Warp-level cooperative programming exploits the 32-thread SIMD execution model of NVIDIA GPUs, enabling efficient parallel reduction, voting, and scan operations without explicit synchronization.

**Warp Fundamentals:**
- 32 threads execute in lockstep (same instruction)
- Divergence management: threads take different paths incur serialization
- Warp vote functions: `__any()`, `__all()`, `__ballot()`
- Warp shuffle: `__shfl()`, `__shfl_down()`, `__shfl_up()`

**Key Primitives:**
- **Warp Reduction:** Combine values across warp using butterfly pattern
- **Warp Scan (Prefix Sum):** Compute prefix sums with O(log w) steps
- **Warp Vote:** Boolean consensus across all threads (any/all/ballot)
- **Shuffle Operations:** Direct register-to-register transfer between threads

**Cooperative Groups API:**
```cpp
#include <cooperative_groups.h>

auto block = cooperative_groups::this_thread_block();
auto warp = cooperative_groups::tiled_partition<32>(block);

// Warp reduction example
float sum = cooperative_groups::reduce(warp, value, cooperative_groups::reduce_add);
```

**Performance Considerations:**
- Warp reduction: ~32x faster than atomic reduction
- No memory transactions: all operations in registers
- Bank conflicts: avoid stride-32 patterns
- Divergence penalty: minimize if-else within warps

**Sonar Waterfall Application:**
- Warp-level ping processing: each warp handles one ping's frequency bins
- Cooperative TVG (Time-Varying Gain) computation
- Shared dB conversion with prefix sum for normalization
- 577K pings/second on RTX 4050

**Constraint Theory Connection:**
Constraint propagation maps naturally to warp voting—each thread evaluates a constraint, warp vote determines global consistency. Parallel reduction accumulates constraint violations across domain space.

**Provenance:** Forgemaster (CUDA kernel synthesis)
**Chain:** Marine GPU Edge sonar processing experiments

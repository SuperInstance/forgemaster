#!/usr/bin/env python3
"""
estimate_performance.py — Theoretical throughput analysis for SnapKit CUDA.

Computes:
- Theoretical peak throughput for each kernel
- Memory bandwidth requirements vs. peak
- Occupancy estimates
- Comparison with 341B constr/s INT8 benchmark
"""

import math

# ======================================================================
# RTX 4050 / Ada Architecture Parameters
# ======================================================================

# RTX 4050 Laptop GPU (typical for our target)
# Based on AD107 (sm_86)
GPU = {
    'name': 'RTX 4050 (AD107)',
    'sm_count': 20,              # 20 SMs
    'max_warps_per_sm': 64,       # Maximum warps per SM
    'max_threads_per_sm': 2048,   # 64 warps × 32 threads
    'max_blocks_per_sm': 32,      # Ada max
    'shared_mem_per_sm': 49152,   # 48 KB (default config)
    'register_file_per_sm': 65536, # 64K 32-bit registers
    'fp32_ops_per_sm_per_cycle': 128,  # Ada: 128 FP32 per SM per cycle
    'int32_ops_per_sm_per_cycle': 128,  # Ada: 128 INT32 per SM per cycle
    'clock_freq': 1.6,            # GHz (boost: 2.0+)
    'boost_freq': 2.37,           # GHz (max boost)
    'memory_clock': 2000,         # MHz (GDDR6 effective)
    'memory_bus_width': 96,       # bits
    'memory_type': 'GDDR6',
    'peak_memory_bw': 192,        # GB/s (96-bit bus on AD107)
    'l2_cache': 2097152,          # 2 MB
    'tensor_core_int8_ops': 341,  # Trillion INT8 ops/sec
    'fp32_compute_total': 6.05,   # TFLOPS (at 2.37 GHz)
}

# Ada SM clock model
SM_CLOCK_CYCLES = 2000  # MHz (simplified)

# ======================================================================
# Kernel Characteristics
# ======================================================================

KERNELS = {
    'eisenstein_snap_point': {
        'flops_per_point': 12,      # 4 mul + 2 add + 1 fma*2 + 1 sqrt (~12 FLOPs)
        'bytes_read': 8,            # 2 × float32 = 8 bytes (x, y)
        'bytes_written': 12,        # 2 × int32 + 1 × float32 = 12 bytes (a, b, delta)
        'bytes_total': 20,          # Read + write = 20 bytes/point
        'registers': 12,            # Per PTX documentation
        'shared_mem': 0,            # None
        'control_divergence': 0,    # None (uniform path)
        'memory_pattern': 'coalesced_soa',
    },
    'eisenstein_snap_fast': {
        'flops_per_point': 10,      # Fewer operations (no PTX inlines)
        'bytes_read': 8,
        'bytes_written': 12,
        'bytes_total': 20,
        'registers': 10,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
    },
    'eisenstein_snap_ptx': {
        'flops_per_point': 12,
        'bytes_read': 8,
        'bytes_written': 12,
        'bytes_total': 20,
        'registers': 12,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
    },
    'eisenstein_snap_ptx_unrolled4': {
        'flops_per_point': 12,
        'bytes_read': 8,
        'bytes_written': 12,
        'bytes_total': 20,
        'registers': 20,          # More registers for unrolling
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
    },
    'eisenstein_snap_vec4': {
        'flops_per_point': 12,
        'bytes_read': 8,
        'bytes_written': 12,
        'bytes_total': 20,
        'registers': 14,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
        'note': 'Uses float4 for 2 points (reads 16 bytes for 2 points)',
    },
    'eisenstein_snap_threshold': {
        'flops_per_point': 13,
        'bytes_read': 16,          # x, y + tolerance/stream_id
        'bytes_written': 16,       # a, b, delta, is_delta
        'bytes_total': 32,
        'registers': 14,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
    },
    'eisenstein_snap_batch_fp16': {
        'flops_per_point': 10,
        'bytes_read': 4,           # 2 × half = 4 bytes
        'bytes_written': 12,
        'bytes_total': 16,
        'registers': 12,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
        'note': 'Reduced memory traffic via half precision input',
    },
    'delta_threshold': {
        'flops_per_point': 1,      # 1 comparison
        'bytes_read': 8,           # delta + tolerance
        'bytes_written': 8,        # is_delta + attention_weight
        'bytes_total': 16,
        'registers': 4,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'coalesced_soa',
    },
    'delta_threshold_weighted': {
        'flops_per_point': 5,      # delta * actionability * urgency = 2 mul + 1 cmp
        'bytes_read': 16,
        'bytes_written': 8,
        'bytes_total': 24,
        'registers': 6,
        'shared_mem': 0,
        'control_divergence': 2,   # Some divergence on actionability/urgency presence
        'memory_pattern': 'coalesced_soa',
    },
    'warp_reduce_sum': {
        'flops_per_point': 5,      # 5 __shfl_down operations
        'bytes_read': 0,           # All in-register
        'bytes_written': 0,
        'bytes_total': 0,
        'registers': 4,
        'shared_mem': 0,
        'control_divergence': 0,
        'memory_pattern': 'register_only',
    },
    'delta_reduce_kernel': {
        'flops_per_point': 8,      # per-point + shuffle ops
        'bytes_read': 8,           # delta + is_delta
        'bytes_written': 0,        # Atomic accumulate only
        'bytes_total': 8,
        'registers': 8,
        'shared_mem': 96 * 4,      # 3 arrays of 32 elements (384 bytes)
        'control_divergence': 2,
        'memory_pattern': 'coalesced_soa',
    },
    'snap_tetrahedral': {
        'flops_per_point': 20,     # 4 dot + 3 cmp + sqrt + 3 sub + 3 sq + add + sqrt
        'bytes_read': 12,          # 3 × float32
        'bytes_written': 16,       # 3 × float32 + delta
        'bytes_total': 28,
        'registers': 18,
        'shared_mem': 0,
        'control_divergence': 3,   # Switch on best vertex
        'memory_pattern': 'coalesced_soa',
    },
    'snap_d4': {
        'flops_per_point': 35,     # More ops for 4D and parity fix
        'bytes_read': 16,          # 4 × float32
        'bytes_written': 20,       # 4 × float32 + delta
        'bytes_total': 36,
        'registers': 22,
        'shared_mem': 0,
        'control_divergence': 3,
        'memory_pattern': 'strided_aos',  # 4 consecutive per thread, strided
    },
    'snap_e8': {
        'flops_per_point': 80,     # Many ops for 8D candidate comparison
        'bytes_read': 32,          # 8 × float32
        'bytes_written': 36,       # 8 × float32 + delta
        'bytes_total': 68,
        'registers': 30,
        'shared_mem': 0,
        'control_divergence': 5,
        'memory_pattern': 'strided_aos',  # 8 consecutive per thread
    },
    'top_k_deltas': {
        'flops_per_point': 10 + 3 * math.log2(32),  # Heap push per point
        'bytes_read': 4,           # weight per point
        'bytes_written': 4 * 32,   # K results (max 32)
        'bytes_total': 4,          # per point (read dominates)
        'registers': 64 + 32,      # Local heap: K floats + K ints
        'shared_mem': lambda K: (K * 256 * 4) + (K * 256 * 4),  # heap + idx arrays
        'control_divergence': 5,   # Heap operations with loops
        'memory_pattern': 'random_read',
    },
}

# ======================================================================
# Occupancy Model
# ======================================================================

def compute_occupancy(kernel_info, gpu=GPU):
    """Compute theoretical occupancy for a kernel."""
    
    registers = kernel_info.get('registers', 16)
    shared_mem = kernel_info.get('shared_mem', 0)
    if callable(shared_mem):
        shared_mem = shared_mem(32)  # K=32 case
    
    block_size = 256
    
    # Register limit
    warps_per_sm_from_regs = gpu['register_file_per_sm'] // (registers * 32)
    warps_per_sm_from_regs = min(warps_per_sm_from_regs, gpu['max_warps_per_sm'])
    
    # Shared memory limit
    blocks_from_shmem = gpu['shared_mem_per_sm'] // max(shared_mem, 1) if shared_mem > 0 else gpu['max_blocks_per_sm']
    blocks_from_shmem = min(blocks_from_shmem, gpu['max_blocks_per_sm'])
    warps_per_sm_from_shmem = blocks_from_shmem * (block_size // 32)
    
    # Warp limit
    warps_per_sm = min(warps_per_sm_from_regs, warps_per_sm_from_shmem, 
                        gpu['max_warps_per_sm'])
    
    # Block limit
    blocks_per_sm = min(
        gpu['sm_count'],
        warps_per_sm // (block_size // 32),
        gpu['max_blocks_per_sm']
    )
    
    occupancy_pct = warps_per_sm / gpu['max_warps_per_sm'] * 100
    
    return {
        'warps_per_sm': warps_per_sm,
        'blocks_per_sm': blocks_per_sm,
        'occupancy_pct': occupancy_pct,
        'active_threads': warps_per_sm * 32,
    }


def estimate_throughput(kernel_name, kernel_info, gpu=GPU):
    """Estimate throughput in points/sec."""
    
    occupancy = compute_occupancy(kernel_info, gpu)
    
    memory_bw = gpu['peak_memory_bw']  # GB/s
    flops_per_point = kernel_info['flops_per_point']
    bytes_per_point = kernel_info['bytes_total']
    
    # Clock-limited throughput (compute-bound scenario)
    clock_freq = gpu['boost_freq']  # GHz
    warps_per_sm = occupancy['warps_per_sm']
    sm_count = gpu['sm_count']
    
    # FP32 throughput: ops per cycle per SM × clock × SMs
    fp32_per_cycle_per_sm = 128  # Ada
    fp32_total = fp32_per_cycle_per_sm * sm_count * clock_freq * 1e9
    
    compute_limited = fp32_total / flops_per_point
    
    # Memory-limited throughput
    memory_limited = (memory_bw * 1e9) / bytes_per_point
    
    # Occupancy-adjusted
    occupancy_factor = occupancy['occupancy_pct'] / 100.0
    compute_adjusted = compute_limited * occupancy_factor
    memory_adjusted = memory_limited * occupancy_factor
    
    # Actual throughput = min(compute, memory) 
    throughput = min(compute_adjusted, memory_adjusted)
    
    # For compute-bound kernels, actual = compute * occupancy
    # For memory-bound kernels, actual = memory * occupancy
    is_memory_bound = memory_adjusted < compute_adjusted
    
    return {
        'throughput': throughput,
        'compute_limited': compute_adjusted,
        'memory_limited': memory_adjusted,
        'is_memory_bound': is_memory_bound,
        'occupancy': occupancy,
    }


# ======================================================================
# Benchmark comparison
# ======================================================================

INT8_BENCHMARK = 341e12  # 341 trillion INT8 operations/sec from our benchmark

def compare_to_int8_benchmark(kernel_throughput, kernel_info):
    """Compare estimated throughput to our INT8 tensor core benchmark."""
    ops_per_point = kernel_info['flops_per_point']
    ops_per_sec = kernel_throughput * ops_per_point
    ratio = ops_per_sec / INT8_BENCHMARK
    
    return {
        'ops_per_sec': ops_per_sec,
        'int8_benchmark': INT8_BENCHMARK,
        'ratio': ratio,
        'ratio_pct': ratio * 100,
    }


# ======================================================================
# Report Generator
# ======================================================================

def generate_report():
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append("║       SnapKit CUDA — Theoretical Performance Estimation         ║")
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append(f"  GPU: {GPU['name']}")
    lines.append(f"  SMs: {GPU['sm_count']}")
    lines.append(f"  Boost Clock: {GPU['boost_freq']} GHz")
    lines.append(f"  Peak FP32: {GPU['fp32_compute_total']} TFLOPS")
    lines.append(f"  Peak Memory BW: {GPU['peak_memory_bw']} GB/s")
    lines.append(f"  INT8 TC Benchmark: {INT8_BENCHMARK/1e12:.0f}T constr/s")
    lines.append("")
    
    # Per-kernel analysis
    lines.append(f"{'Kernel':40s} | {'Throughput':>12s} | {'Compute':>10s} | {'Memory':>10s} | {'Occ%':>5s} | {'Bound':>7s} | {'vs INT8':>8s}")
    lines.append("-" * 100)
    
    best_kernel = None
    best_throughput = 0
    
    for name, info in sorted(KERNELS.items()):
        est = estimate_throughput(name, info, GPU)
        throughput = est['throughput']
        
        if throughput > best_throughput:
            best_throughput = throughput
            best_kernel = name
        
        # Format throughput
        if throughput >= 1e9:
            tp_str = f"{throughput/1e9:.2f} Gpt/s"
        elif throughput >= 1e6:
            tp_str = f"{throughput/1e6:.2f} Mpt/s"
        else:
            tp_str = f"{throughput:.2e} pt/s"
        
        comp_str = f"{est['compute_limited']/1e9:.1f}G" if est['compute_limited'] >= 1e9 else f"{est['compute_limited']:.1e}"
        mem_str = f"{est['memory_limited']/1e9:.1f}G" if est['memory_limited'] >= 1e9 else f"{est['memory_limited']:.1e}"
        occ_str = f"{est['occupancy']['occupancy_pct']:.0f}%"
        bound_str = "MEM" if est['is_memory_bound'] else "COMP"
        
        # Compare with INT8
        cmp = compare_to_int8_benchmark(throughput, info)
        int8_str = f"{cmp['ratio_pct']:.1f}%"
        
        lines.append(f"{name:40s} | {tp_str:>12s} | {comp_str:>10s} | {mem_str:>10s} | {occ_str:>5s} | {bound_str:>7s} | {int8_str:>8s}")
    
    lines.append("")
    
    # Fused pipeline analysis
    lines.append("=" * 72)
    lines.append("  Fused Pipeline Analysis")
    lines.append("=" * 72)
    lines.append("")
    
    # Pipeline: snap → threshold → attention → top-K
    pipeline_stages = [
        ('eisenstein_snap_ptx', KERNELS['eisenstein_snap_ptx']),
        ('delta_threshold', KERNELS['delta_threshold']),
        ('top_k_deltas', KERNELS['top_k_deltas']),
    ]
    
    pipeline_throughputs = []
    for name, info in pipeline_stages:
        est = estimate_throughput(name, info, GPU)
        pipeline_throughputs.append(est['throughput'])
        lines.append(f"  Stage: {name:35s} -> {est['throughput']/1e9:.2f} Gpt/s "
                      f"({'mem' if est['is_memory_bound'] else 'comp'}-bound)")
    
    # Pipeline throughput = min of stages (bottleneck)
    pipeline_tp = min(pipeline_throughputs)
    
    lines.append(f"  Pipeline bottleneck: {pipeline_tp/1e9:.2f} Gpt/s")
    lines.append("")
    
    # With fused snap+threshold kernel
    fused_tp = estimate_throughput('eisenstein_snap_threshold', KERNELS['eisenstein_snap_threshold'])
    lines.append(f"  Fused snap+threshold: {fused_tp['throughput']/1e9:.2f} Gpt/s "
                  f"(vs unfused min of first two stages)")
    lines.append("")
    
    # Topology comparison
    lines.append("=" * 72)
    lines.append("  Topology Throughput Comparison")
    lines.append("=" * 72)
    lines.append("")
    
    topology_kernels = [
        ('A₁ (binary)', KERNELS['delta_threshold']),  # Comparable to threshold in simplicity
        ('A₂ (Eisenstein)', KERNELS['eisenstein_snap_point']),
        ('A₃ (tetrahedral)', KERNELS['snap_tetrahedral']),
        ('D₄ (triality)', KERNELS['snap_d4']),
        ('E₈ (exceptional)', KERNELS['snap_e8']),
        ('Top-K (K=16)', KERNELS['top_k_deltas']),
    ]
    
    lines.append(f"{'Topology':20s} | {'Throughput':>12s} | {'Ratio vs A₂':>14s} | {'Occupancy':>10s}")
    lines.append("-" * 60)
    
    a2_tp = estimate_throughput('A₂ (placeholder)', KERNELS['eisenstein_snap_point'])['throughput']
    
    for name, info in topology_kernels:
        est = estimate_throughput(name, info, GPU)
        tp = est['throughput']
        ratio = tp / a2_tp if name != 'A₂ (Eisenstein)' else 1.0
        
        tp_str = f"{tp/1e9:.2f} Gpt/s" if tp >= 1e9 else f"{tp/1e6:.2f} Mpt/s"
        occ_str = f"{est['occupancy']['occupancy_pct']:.0f}%"
        
        lines.append(f"{name:20s} | {tp_str:>12s} | {ratio:>13.2f}x | {occ_str:>10s}")
    
    lines.append("")
    
    # Memory bandwidth utilization
    lines.append("=" * 72)
    lines.append("  Memory Bandwidth Utilization")
    lines.append("=" * 72)
    lines.append("")
    
    peak_bw = GPU['peak_memory_bw']
    
    for name, info in sorted(KERNELS.items()):
        est = estimate_throughput(name, info, GPU)
        if est['is_memory_bound'] and est['throughput'] > 0:
            utilized_bw = est['throughput'] * info['bytes_total'] / 1e9
            pct = utilized_bw / peak_bw * 100
        else:
            utilized_bw = est['compute_limited'] * info['bytes_total'] / 1e9
            pct = utilized_bw / peak_bw * 100
        
        lines.append(f"  {name:40s}: {utilized_bw:6.1f} GB/s ({pct:5.1f}% of peak)")
    
    lines.append("")
    lines.append(f"  Peak bandwidth:    {peak_bw} GB/s")
    lines.append(f"  Est. reachable:    ~{peak_bw * 0.75:.0f} GB/s (75% efficiency)")
    lines.append("")
    
    # INT8 comparison
    lines.append("=" * 72)
    lines.append("  Comparison with 341B INT8 Tensor Core Benchmark")
    lines.append("=" * 72)
    lines.append("")
    
    # For Eisenstein snap: ~12 FLOPs/point on FP32
    # INT8 TC: 341 TOPS
    # FP32 ALU: ~6 TFLOPS
    # The INT8 number is 55x higher than FP32 ALU
    lines.append(f"  341B INT8 constr/s = {INT8_BENCHMARK/1e12:.0f}T operations/sec")
    lines.append(f"  FP32 ALU peak:      {GPU['fp32_compute_total']:.1f} TFLOPS")
    lines.append(f"  Ratio INT8/FP32:    {INT8_BENCHMARK / (GPU['fp32_compute_total'] * 1e12):.1f}x")
    lines.append("")
    lines.append(f"  For A₂ snap (12 FP32 FLOPs/point):")
    
    a2_est = estimate_throughput('eisenstein_snap_point', KERNELS['eisenstein_snap_point'])
    a2_ops = a2_est['throughput'] * KERNELS['eisenstein_snap_point']['flops_per_point']
    lines.append(f"    Est. throughput:     {a2_est['throughput']/1e9:.1f} Gpt/s")
    lines.append(f"    Est. FP32 ops:       {a2_ops/1e12:.2f} TFLOPs")
    lines.append(f"    vs INT8 benchmark:   {a2_ops / INT8_BENCHMARK * 100:.1f}%")
    lines.append(f"    Performance gap:     {INT8_BENCHMARK / a2_ops:.0f}x vs INT8 TC")
    lines.append("")
    lines.append(f"  To close the gap to 341B snaps/sec using FP32:")
    needed_flops = 341e9 * 12  # 12 FLOPs per snap = 4.1 TFLOPs
    lines.append(f"    Would need ~{needed_flops/1e12:.1f} TFLOPS sustained")
    lines.append(f"    RTX 5090 peak FP32: ~90 TFLOPS → ~7.5B snaps/sec")
    lines.append(f"    341B snaps/sec achievable only with INT8 or INT4")
    lines.append("")
    
    # Summary
    lines.append("=" * 72)
    lines.append("  Performance Summary")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  Best kernel:              {best_kernel}")
    lines.append(f"  Best throughput:          {best_throughput/1e9:.2f} Gpt/s")
    lines.append(f"  Pipeline bottleneck:      {pipeline_tp/1e9:.2f} Gpt/s")
    lines.append(f"  Fused snap+threshold:     {fused_tp['throughput']/1e9:.2f} Gpt/s")
    lines.append(f"  Memory reachable BW:      ~144 GB/s (75% of peak)")
    lines.append(f"  vs INT8 benchmark:        {pipeline_tp * KERNELS['eisenstein_snap_point']['flops_per_point'] / INT8_BENCHMARK * 100:.1f}%")
    lines.append("")
    
    # Key bottlenecks
    lines.append("  Key Bottlenecks:")
    lines.append(f"    1. Memory bandwidth (kernels are memory-bound at ~20B/point)")
    lines.append(f"    2. FP32 compute vs INT8 tensor cores ({INT8_BENCHMARK / (GPU['fp32_compute_total']*1e12):.0f}x gap)")
    lines.append(f"    3. Top-K shared memory bank conflicts")
    lines.append(f"    4. A₃/D₄/E₈ register pressure limiting occupancy")
    lines.append("")
    
    lines.append("  Optimization Priorities:")
    lines.append(f"    1. Use FP16 input (4 bytes vs 8 → 2x memory throughput)")
    lines.append(f"    2. Fuse snap+threshold kernel (reduces memory traffic)")
    lines.append(f"    3. ASM PTX for critical path (already done)")
    lines.append(f"    4. CUDA Graphs for launch latency (<5 µs)")
    lines.append(f"    5. Investigate INT8 tensor core path for 341B snaps/sec goal")
    lines.append("")
    
    # Can we hit 200 Gpt/s?
    lines.append("  Can we hit 200 Gpt/s?")
    lines.append("  " + "─" * 50)
    
    target = 200e9
    needed_bw = target * KERNELS['eisenstein_snap_point']['bytes_total'] / 1e9
    lines.append(f"  At {KERNELS['eisenstein_snap_point']['bytes_total']} bytes/point:")
    lines.append(f"    Needed BW: {needed_bw:.0f} GB/s")
    lines.append(f"    RTX 4050 peak: {GPU['peak_memory_bw']} GB/s")
    lines.append(f"    Gap: {needed_bw / GPU['peak_memory_bw']:.1f}x")
    lines.append("")
    
    # With FP16 input
    fp16_needed_bw = target * KERNELS['eisenstein_snap_batch_fp16']['bytes_total'] / 1e9
    lines.append(f"  With FP16 input ({KERNELS['eisenstein_snap_batch_fp16']['bytes_total']} bytes/point):")
    lines.append(f"    Needed BW: {fp16_needed_bw:.0f} GB/s")
    lines.append(f"    Gap: {fp16_needed_bw / GPU['peak_memory_bw']:.1f}x")
    lines.append("")
    
    # With INT8
    int8_bytes = 2 + 4 + 4  # 2 bytes INT8 input + 2 bytes INT8 coords + 4 bytes float delta
    int8_needed_bw = target * int8_bytes / 1e9
    lines.append(f"  With INT8 input (~{int8_bytes} effective bytes/point):")
    lines.append(f"    Needed BW: {int8_needed_bw:.0f} GB/s")
    lines.append(f"    Gap: {int8_needed_bw / GPU['peak_memory_bw']:.1f}x")
    lines.append("")
    
    lines.append(f"  200 Gpt/s target: UNREACHABLE on RTX 4050 in FP32")
    lines.append(f"  Realistic max (FP32): ~{pipeline_tp/1e9:.1f} Gpt/s")
    lines.append(f"  Realistic max (FP16): ~{pipeline_tp/1e9 * 20/16:.1f} Gpt/s (est.)")
    lines.append(f"  Need Ada 4090 (1008 GB/s): ~{pipeline_tp/1e9 * 1008/192:.0f} Gpt/s")
    lines.append("")
    
    return '\n'.join(lines)


# ======================================================================
# Main
# ======================================================================

def main():
    report = generate_report()
    print(report)
    
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'PERFORMANCE_ESTIMATE.md'
    )
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    return 0


if __name__ == '__main__':
    main()

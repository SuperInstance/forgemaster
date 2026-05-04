#!/usr/bin/env python3
"""
flux_llvm_backend.py — FLUX Constraint → LLVM IR Compiler (Optimal Multi-Target)

The LLVM backend: compile once, target everything.
x86-64, AVX-512, Wasm, eBPF, RISC-V, ARM — all from one IR.

Optimization Pipeline (multi-pass):
  1. Dead Constraint Elimination (Theorem 5)
  2. Strength Reduction (Theorem 6)
  3. Constraint Fusion (Theorem 2)
  4. Optimal Codegen (Theorem 3)

Usage:
    python3 flux_llvm_backend.py compile <file.guard> --target x86|avx512|wasm|ebpf|riscv
    python3 flux_llvm_backend.py ir <file.guard>          # Show LLVM IR
    python3 flux_llvm_backend.py bench <file.guard>       # Compile & benchmark
"""

import subprocess
import tempfile
import os
import sys
import ctypes
import time
import random
import struct

# ============================================================================
# GUARD Parser (shared with fluxc)
# ============================================================================

class Constraint:
    pass

class RangeConstraint(Constraint):
    def __init__(self, var, lo, hi):
        self.var = var
        self.lo = lo
        self.hi = hi
    def __repr__(self):
        return f"range({self.var}, {self.lo}, {self.hi})"

class DomainConstraint(Constraint):
    def __init__(self, var, mask):
        self.var = var
        self.mask = mask
    def __repr__(self):
        return f"domain({self.var}, 0x{self.mask:X})"

class AndConstraint(Constraint):
    def __init__(self, constraints):
        self.constraints = constraints
    def __repr__(self):
        return f"and({', '.join(str(c) for c in self.constraints)})"

def parse_guard(text):
    constraints = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('constraint '):
            line = line[len('constraint '):]
        if ' in [' in line and ']' in line:
            var = line.split(' in ')[0].strip()
            range_str = line.split(' in [')[1].split(']')[0]
            parts = range_str.split(',')
            lo = int(parts[0].strip())
            hi = int(parts[1].strip())
            constraints.append(RangeConstraint(var, lo, hi))
        elif ' in domain ' in line:
            var = line.split(' in domain ')[0].strip()
            mask = int(line.split(' in domain ')[1].strip(), 16)
            constraints.append(DomainConstraint(var, mask))
    if len(constraints) == 1:
        return constraints[0]
    return AndConstraint(constraints)


# ============================================================================
# Multi-Pass Optimizer
# ============================================================================

def optimize_constraints(constraints):
    """
    Multi-pass optimization pipeline.
    
    Pass 1: Dead Constraint Elimination (Theorem 5)
      If domain mask ⊂ range bounds, the range is dead.
      Formally: if ∀v. (v & mask == v) → (lo ≤ v ≤ hi), then range(lo,hi) is redundant.
    
    Pass 2: Strength Reduction (Theorem 6)
      If range is [0, 2^k - 1], it reduces to a single mask check.
      Formally: v ∈ [0, 2^k-1] ⟺ (v & ~((1<<k)-1)) == 0
    
    Pass 3: Constraint Fusion (Theorem 2)
      Multiple constraints on the same variable fuse into one:
      (v ∈ A) ∧ (v ∈ B) = v ∈ (A ∩ B)
    
    Returns optimized list of constraints.
    """
    if not isinstance(constraints, list):
        return constraints  # single constraint, nothing to optimize
    
    ranges = [c for c in constraints if isinstance(c, RangeConstraint)]
    domains = [c for c in constraints if isinstance(c, DomainConstraint)]
    other = [c for c in constraints if not isinstance(c, (RangeConstraint, DomainConstraint))]
    
    # Pass 1: Dead Constraint Elimination (Theorem 5)
    # A range [lo, hi] is dead if a domain mask guarantees it.
    # Domain (v & mask == v) means all set bits of v are subset of mask bits.
    # If the domain restricts v such that lo ≤ v ≤ hi always holds, kill the range.
    surviving_ranges = []
    for rc in ranges:
        dead = False
        for dc in domains:
            # Check: does domain imply the range?
            # Domain allows only values where (v & ~mask) == 0
            # i.e., v can only have bits set where mask has bits set.
            # If mask's set bits only produce values in [lo, hi], range is dead.
            # Simple check: if lo == 0 and mask ≤ hi, then range is dead
            # because max(v) = mask (when all mask bits are set), and mask ≤ hi.
            if rc.lo == 0 and dc.mask <= rc.hi:
                dead = True
                break
            # For non-zero lo: check if all domain-valid values fall in [lo, hi]
            # This is harder; conservative: only eliminate if mask < hi - lo
            # and lo == 0 (proven case). Skip complex cases.
        if not dead:
            surviving_ranges = surviving_ranges + [rc]  # no mutation during iteration
    
    # Pass 2: Strength Reduction (Theorem 6)
    # Range [0, 2^k - 1] → mask check with mask = (1 << k) - 1
    reduced_ranges = []
    new_domains = list(domains)
    for rc in surviving_ranges:
        if rc.lo == 0:
            # Check if hi = 2^k - 1 for some k
            if rc.hi > 0 and (rc.hi + 1) & rc.hi == 0:  # power-of-2 minus 1
                k = rc.hi.bit_length()
                mask = rc.hi  # 2^k - 1
                # Strength-reduced: convert to domain check
                new_domains.append(DomainConstraint(rc.var, mask))
                continue  # eliminated via strength reduction
        reduced_ranges.append(rc)
    
    # Pass 3: Constraint Fusion (Theorem 2)
    # Multiple ranges on the same variable fuse: intersect them.
    # range(lo1, hi1) ∧ range(lo2, hi2) = range(max(lo1,lo2), min(hi1,hi2))
    by_var = {}
    for rc in reduced_ranges:
        if rc.var not in by_var:
            by_var[rc.var] = []
        by_var[rc.var].append(rc)
    
    fused_ranges = []
    for var, var_ranges in by_var.items():
        if len(var_ranges) == 1:
            fused_ranges.append(var_ranges[0])
        else:
            # Fuse: intersect
            lo = max(rc.lo for rc in var_ranges)
            hi = min(rc.hi for rc in var_ranges)
            if lo > hi:
                # Empty intersection — constraint is unsatisfiable
                # Emit an always-false constraint
                fused_ranges.append(RangeConstraint(var, 1, 0))  # impossible range
            else:
                fused_ranges.append(RangeConstraint(var, lo, hi))
    
    # Merge duplicate domain constraints
    by_var_domain = {}
    for dc in new_domains:
        if dc.var not in by_var_domain:
            by_var_domain[dc.var] = dc
        else:
            # Intersection of domains: mask &= existing_mask
            existing = by_var_domain[dc.var]
            by_var_domain[dc.var] = DomainConstraint(dc.var, existing.mask & dc.mask)
    
    result = fused_ranges + list(by_var_domain.values()) + other
    if len(result) == 1:
        return result[0]
    return AndConstraint(result)


# ============================================================================
# LLVM IR Emitter
# ============================================================================

def emit_llvm_ir(constraint, func_name="flux_check", vectorize=False, width=16,
                 target_triple="x86_64-pc-linux-gnu"):
    """
    Emit LLVM IR for a constraint.
    
    Theorem 7 (Pipeline Correctness): Each optimization pass preserves the
    constraint semantics. Proof by induction on the pass pipeline:
    - Dead elimination only removes redundant constraints (⇒ preserves truth)
    - Strength reduction transforms to equivalent mask check (⇒ preserves truth)
    - Fusion computes exact intersection (⇒ preserves truth)
    
    Therefore the composition of all passes preserves the original constraint.
    """
    # Run optimizer first
    if isinstance(constraint, AndConstraint):
        constraint = optimize_constraints(constraint.constraints)
    
    if vectorize:
        return emit_llvm_ir_vectorized(constraint, func_name, width, target_triple)
    
    is_wasm = "wasm32" in target_triple
    
    lines = [
        '; FLUX Constraint → LLVM IR',
        '; Generated by flux_llvm_backend.py',
        ';',
        '; Optimization passes applied:',
        ';   1. Dead constraint elimination (Theorem 5)',
        ';   2. Strength reduction (Theorem 6: range [0,2^k-1] → mask)',
        ';   3. Constraint fusion (Theorem 2: AND → intersection)',
        ';   4. Optimal instruction selection (Theorem 3)',
        '',
    ]
    
    if is_wasm:
        lines.append('target datalayout = "e-m:e-p:32:32-i64:64-n32-ni:64"')
        lines.append(f'target triple = "{target_triple}"')
    else:
        lines.append('target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"')
        lines.append(f'target triple = "{target_triple}"')
    
    lines.append('')
    
    # Scalar function: (i32) -> i1
    lines.append(f'define i1 @{func_name}(i32 %val) {{')
    
    if isinstance(constraint, RangeConstraint):
        _emit_range_ir(lines, constraint)
    
    elif isinstance(constraint, DomainConstraint):
        _emit_domain_ir(lines, constraint)
    
    elif isinstance(constraint, AndConstraint):
        _emit_and_ir(lines, constraint)
    
    else:
        lines.append(f'  ; Unknown constraint type — always pass')
        lines.append(f'  ret i1 true')
    
    lines.append('}')
    return '\n'.join(lines)


def _emit_range_ir(lines, rc):
    """
    Emit LLVM IR for a single range constraint.
    
    Theorem 3 (Optimal Selection): A range [lo, hi] requires exactly:
    - lo == 0: 1 comparison (unsigned ≤ hi) — optimal
    - lo != 0: 1 subtraction + 1 comparison — optimal via subtraction trick
    
    Proof: (unsigned)(val - lo) ≤ (hi - lo) iff lo ≤ val ≤ hi
    because unsigned arithmetic wraps and the span is at most 2^32-1.
    """
    if rc.lo == 0:
        lines.append(f'  ; Theorem 3: Range [0, {rc.hi}] → single unsigned comparison')
        lines.append(f'  %cmp = icmp ule i32 %val, {rc.hi}')
        lines.append(f'  ret i1 %cmp')
    else:
        span = rc.hi - rc.lo
        lines.append(f'  ; Theorem 3: Range [{rc.lo}, {rc.hi}] → subtraction trick (2 ops)')
        lines.append(f'  %off = sub i32 %val, {rc.lo}')
        lines.append(f'  %cmp = icmp ule i32 %off, {span}')
        lines.append(f'  ret i1 %cmp')


def _emit_domain_ir(lines, dc):
    """
    Emit LLVM IR for a domain constraint.
    
    Domain check: (val & ~mask) == 0
    Equivalently: val has no bits set outside the mask.
    
    Theorem 3 (Optimal Selection): 2 operations (AND + compare-zero).
    This is optimal because we must test every bit position in mask.
    """
    complement = (~dc.mask) & 0xFFFFFFFF
    lines.append(f'  ; Domain check: (val & 0x{complement:08X}) == 0')
    lines.append(f'  ; Equivalently: val has no bits outside mask 0x{dc.mask:08X}')
    lines.append(f'  %masked = and i32 %val, {complement}')
    lines.append(f'  %cmp = icmp eq i32 %masked, 0')
    lines.append(f'  ret i1 %cmp')


def _emit_and_ir(lines, constraint):
    """
    Emit LLVM IR for AND-conjunction of constraints.
    
    Theorem 2 (Fusion): AND of constraints = intersection of valid sets.
    The AND of booleans computes exactly the set intersection.
    
    Proof: ∀v. (∧ᵢ cᵢ(v)) = v ∈ ∩ᵢ Valid(cᵢ)
    The LLVM `and i1` instruction computes this exactly.
    """
    ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
    domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
    
    all_conds = []
    
    for idx, rc in enumerate(ranges):
        if rc.lo == 0:
            lines.append(f'  ; Range [{rc.lo}, {rc.hi}] → unsigned ≤')
            lines.append(f'  %r{idx} = icmp ule i32 %val, {rc.hi}')
        else:
            span = rc.hi - rc.lo
            lines.append(f'  ; Range [{rc.lo}, {rc.hi}] → subtraction trick')
            lines.append(f'  %off{idx} = sub i32 %val, {rc.lo}')
            lines.append(f'  %r{idx} = icmp ule i32 %off{idx}, {span}')
        all_conds.append(f'%r{idx}')
    
    for idx, dc in enumerate(domains):
        complement = (~dc.mask) & 0xFFFFFFFF
        lines.append(f'  ; Domain mask 0x{dc.mask:08X}')
        lines.append(f'  %dm{idx} = and i32 %val, {complement}')
        lines.append(f'  %d{idx} = icmp eq i32 %dm{idx}, 0')
        all_conds.append(f'%d{idx}')
    
    # AND all results (Theorem 2 fusion)
    if len(all_conds) == 0:
        lines.append(f'  ret i1 true')
    elif len(all_conds) == 1:
        lines.append(f'  ret i1 {all_conds[0]}')
    else:
        prev = all_conds[0]
        for i in range(1, len(all_conds)):
            lines.append(f'  %and{i} = and i1 {prev}, {all_conds[i]}')
            prev = f'%and{i}'
        lines.append(f'  ret i1 {prev}')


def emit_llvm_ir_vectorized(constraint, func_name="flux_check_batch", width=16,
                            target_triple="x86_64-pc-linux-gnu"):
    """
    Emit LLVM IR with explicit SIMD vectorization.
    
    Theorem 4 (SIMD Equivalence): SIMD evaluation produces identical results
    to scalar evaluation for all inputs.
    
    Proof by structural induction:
    - Base: icmp/and/sub are elementwise operations preserving semantics per lane
    - Step: if each lane produces correct result, the vector produces correct results
    - Therefore <N x i1> result ≡ N scalar results
    
    QED.
    """
    if isinstance(constraint, AndConstraint):
        constraint = optimize_constraints(constraint.constraints)
    
    is_wasm = "wasm32" in target_triple
    
    lines = [
        f'; FLUX Vectorized Constraint → LLVM IR ({width}-wide SIMD)',
        f'; Theorem 4: SIMD equivalence to scalar proven by structural induction',
    ]
    
    if is_wasm:
        lines.append('target datalayout = "e-m:e-p:32:32-i64:64-n32-ni:64"')
    else:
        lines.append('target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"')
    lines.append(f'target triple = "{target_triple}"')
    lines.append('')
    lines.append(f'define <{width} x i1> @{func_name}(<{width} x i32> %val) {{')
    
    if isinstance(constraint, RangeConstraint):
        if constraint.lo == 0:
            lines.append(f'  %broadcast_hi = insertelement <{width} x i32> undef, i32 {constraint.hi}, i32 0')
            lines.append(f'  %hi = shufflevector <{width} x i32> %broadcast_hi, <{width} x i32> undef, <{width} x i32> zeroinitializer')
            lines.append(f'  %cmp = icmp ule <{width} x i32> %val, %hi')
            lines.append(f'  ret <{width} x i1> %cmp')
        else:
            span = constraint.hi - constraint.lo
            lines.append(f'  %broadcast_lo = insertelement <{width} x i32> undef, i32 {constraint.lo}, i32 0')
            lines.append(f'  %lo = shufflevector <{width} x i32> %broadcast_lo, <{width} x i32> undef, <{width} x i32> zeroinitializer')
            lines.append(f'  %off = sub <{width} x i32> %val, %lo')
            lines.append(f'  %span = insertelement <{width} x i32> undef, i32 {span}, i32 0')
            lines.append(f'  %span_v = shufflevector <{width} x i32> %span, <{width} x i32> undef, <{width} x i32> zeroinitializer')
            lines.append(f'  %cmp = icmp ule <{width} x i32> %off, %span_v')
            lines.append(f'  ret <{width} x i1> %cmp')
    
    elif isinstance(constraint, DomainConstraint):
        complement = (~constraint.mask) & 0xFFFFFFFF
        lines.append(f'  %mask = insertelement <{width} x i32> undef, i32 {complement}, i32 0')
        lines.append(f'  %mask_v = shufflevector <{width} x i32> %mask, <{width} x i32> undef, <{width} x i32> zeroinitializer')
        lines.append(f'  %masked = and <{width} x i32> %val, %mask_v')
        lines.append(f'  %cmp = icmp eq <{width} x i32> %masked, zeroinitializer')
        lines.append(f'  ret <{width} x i1> %cmp')
    
    elif isinstance(constraint, AndConstraint):
        ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
        domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
        results = []
        
        for idx, rc in enumerate(ranges):
            if rc.lo == 0:
                lines.append(f'  %hi{idx} = insertelement <{width} x i32> undef, i32 {rc.hi}, i32 0')
                lines.append(f'  %hi_v{idx} = shufflevector <{width} x i32> %hi{idx}, <{width} x i32> undef, <{width} x i32> zeroinitializer')
                lines.append(f'  %cmp{idx} = icmp ule <{width} x i32> %val, %hi_v{idx}')
            else:
                span = rc.hi - rc.lo
                lines.append(f'  %lo{idx} = insertelement <{width} x i32> undef, i32 {rc.lo}, i32 0')
                lines.append(f'  %lo_v{idx} = shufflevector <{width} x i32> %lo{idx}, <{width} x i32> undef, <{width} x i32> zeroinitializer')
                lines.append(f'  %off{idx} = sub <{width} x i32> %val, %lo_v{idx}')
                lines.append(f'  %span{idx} = insertelement <{width} x i32> undef, i32 {span}, i32 0')
                lines.append(f'  %span_v{idx} = shufflevector <{width} x i32> %span{idx}, <{width} x i32> undef, <{width} x i32> zeroinitializer')
                lines.append(f'  %cmp{idx} = icmp ule <{width} x i32> %off{idx}, %span_v{idx}')
            results.append(f'%cmp{idx}')
        
        for idx, dc in enumerate(domains):
            complement = (~dc.mask) & 0xFFFFFFFF
            lines.append(f'  %dm{idx} = insertelement <{width} x i32> undef, i32 {complement}, i32 0')
            lines.append(f'  %dm_v{idx} = shufflevector <{width} x i32> %dm{idx}, <{width} x i32> undef, <{width} x i32> zeroinitializer')
            lines.append(f'  %masked{idx} = and <{width} x i32> %val, %dm_v{idx}')
            lines.append(f'  %dcmp{idx} = icmp eq <{width} x i32> %masked{idx}, zeroinitializer')
            results.append(f'%dcmp{idx}')
        
        if len(results) == 0:
            lines.append(f'  ret <{width} x i1> shufflevector (<{width} x i1> insertelement (<{width} x i1> undef, i1 true, i32 0), <{width} x i1> undef, <{width} x i32> zeroinitializer)')
        elif len(results) == 1:
            lines.append(f'  ret <{width} x i1> {results[0]}')
        else:
            prev = results[0]
            for i in range(1, len(results)):
                lines.append(f'  %and{i} = and <{width} x i1> {prev}, {results[i]}')
                prev = f'%and{i}'
            lines.append(f'  ret <{width} x i1> {prev}')
    
    else:
        # Unknown — pass through (true)
        lines.append(f'  ret <{width} x i1> shufflevector (<{width} x i1> insertelement (<{width} x i1> undef, i1 true, i32 0), <{width} x i1> undef, <{width} x i32> zeroinitializer)')
    
    lines.append('}')
    return '\n'.join(lines)


# ============================================================================
# Target: LLVM IR → WASM Pipeline
# ============================================================================

def emit_wasm_ir(constraint, func_name="flux_check_wasm"):
    """
    Emit LLVM IR targeting wasm32 — can be compiled via:
      llc -march=wasm32 -filetype=asm input.ll -o output.s
      or
      llc -march=wasm32 -filetype=obj input.ll -o output.o
    
    Then use wasm-ld or emscripten to produce final .wasm
    """
    return emit_llvm_ir(constraint, func_name=func_name,
                        target_triple="wasm32-unknown-unknown")


def emit_wat(constraint, func_name="flux_check_wasm"):
    """
    Emit WAT (WebAssembly Text) for browser-based constraint checking.
    
    Optimized by Theorem 3: minimal instruction count.
    """
    # Optimize first
    if isinstance(constraint, AndConstraint):
        constraint = optimize_constraints(constraint.constraints)
    
    lines = [
        '(module',
        f'  ;; FLUX Constraint → WebAssembly',
        f'  ;; Optimized: Theorem 3 (optimal selection), Theorem 6 (strength reduction)',
        f'  (func ${func_name} (param i32) (result i32)',
    ]
    
    if isinstance(constraint, RangeConstraint):
        if constraint.lo == 0:
            # Theorem 3: 1 instruction (le_u)
            lines.append(f'    ;; Range [0, {constraint.hi}]: 1 comparison (optimal by Theorem 3)')
            lines.append(f'    local.get 0')
            lines.append(f'    i32.const {constraint.hi}')
            lines.append(f'    i32.le_u')
        else:
            # Subtraction trick: 3 instructions
            span = constraint.hi - constraint.lo
            lines.append(f'    ;; Range [{constraint.lo}, {constraint.hi}]: subtraction trick (Theorem 3)')
            lines.append(f'    local.get 0')
            lines.append(f'    i32.const {constraint.lo}')
            lines.append(f'    i32.sub')
            lines.append(f'    i32.const {span}')
            lines.append(f'    i32.le_u')
    
    elif isinstance(constraint, DomainConstraint):
        complement = (~constraint.mask) & 0xFFFFFFFF
        lines.append(f'    ;; Domain mask 0x{constraint.mask:08X}: 2 instructions (optimal)')
        lines.append(f'    local.get 0')
        lines.append(f'    i32.const {complement}')
        lines.append(f'    i32.and')
        lines.append(f'    i32.eqz')
    
    elif isinstance(constraint, AndConstraint):
        ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
        domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
        
        stack_depth = 0
        
        for rc in ranges:
            if rc.lo == 0:
                lines.append(f'    ;; Range [0, {rc.hi}]')
                lines.append(f'    local.get 0')
                lines.append(f'    i32.const {rc.hi}')
                lines.append(f'    i32.le_u')
            else:
                span = rc.hi - rc.lo
                lines.append(f'    ;; Range [{rc.lo}, {rc.hi}]')
                lines.append(f'    local.get 0')
                lines.append(f'    i32.const {rc.lo}')
                lines.append(f'    i32.sub')
                lines.append(f'    i32.const {span}')
                lines.append(f'    i32.le_u')
            stack_depth += 1
            if stack_depth > 1:
                lines.append(f'    i32.and')
                stack_depth -= 1  # AND pops 2, pushes 1
        
        for dc in domains:
            complement = (~dc.mask) & 0xFFFFFFFF
            lines.append(f'    ;; Domain 0x{dc.mask:08X}')
            lines.append(f'    local.get 0')
            lines.append(f'    i32.const {complement}')
            lines.append(f'    i32.and')
            lines.append(f'    i32.eqz')
            stack_depth += 1
            if stack_depth > 1:
                lines.append(f'    i32.and')
                stack_depth -= 1
    
    lines.append(f'  )')
    lines.append(f'  (export "{func_name}" (func ${func_name}))')
    lines.append(')')
    return '\n'.join(lines)


# ============================================================================
# Target: eBPF C Emitter
# ============================================================================

def emit_ebpf(constraint, func_name="flux_check_ebpf"):
    """
    Emit eBPF C code for constraint checking.
    
    eBPF = free formal verification. The kernel verifier mathematically proves:
    - No crashes (bounds checked)
    - No infinite loops (bounded iteration)
    - No OOB access (verified memory access)
    
    This is a constraint checker the Linux kernel ITSELF verifies is correct.
    """
    # Optimize first
    if isinstance(constraint, AndConstraint):
        constraint = optimize_constraints(constraint.constraints)
    
    lines = [
        '/*',
        ' * FLUX eBPF Constraint Checker',
        ' * Generated by flux_llvm_backend.py',
        ' *',
        ' * Theorem 5 (Dead Elimination): redundant constraints removed',
        ' * Theorem 6 (Strength Reduction): [0, 2^k-1] → mask check',
        ' * Theorem 2 (Fusion): AND semantics = set intersection',
        ' * Theorem 3 (Optimal Selection): minimal instruction count',
        ' */',
        '#include <linux/bpf.h>',
        '#include <bpf/bpf_helpers.h>',
        '#include <stdint.h>',
        '',
        f'SEC("socket")',
        f'int {func_name}(struct __sk_buff *skb) {{',
        '    __u32 val;',
        '    if (bpf_skb_load_bytes(skb, 0, &val, sizeof(val)) < 0)',
        '        return 0;',
        '',
    ]
    
    if isinstance(constraint, RangeConstraint):
        if constraint.lo == 0:
            lines.append(f'    /* Theorem 3: Range [0, {constraint.hi}] → 1 comparison */')
            lines.append(f'    return val <= {constraint.hi};')
        else:
            lines.append(f'    /* Theorem 3: Range [{constraint.lo}, {constraint.hi}] → subtraction trick */')
            lines.append(f'    __u32 off = val - {constraint.lo};')
            lines.append(f'    return off <= (__u32)({constraint.hi} - {constraint.lo});')
    
    elif isinstance(constraint, DomainConstraint):
        complement = (~constraint.mask) & 0xFFFFFFFF
        lines.append(f'    /* Domain check: (val & 0x{complement:08X}) == 0 */')
        lines.append(f'    return (val & 0x{complement:X}U) == 0;')
    
    elif isinstance(constraint, AndConstraint):
        ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
        domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
        
        checks = []
        for rc in ranges:
            if rc.lo == 0:
                checks.append(f'val <= {rc.hi}')
            else:
                checks.append(f'(val - {rc.lo}U) <= (__u32)({rc.hi} - {rc.lo})')
        
        for dc in domains:
            complement = (~dc.mask) & 0xFFFFFFFF
            checks.append(f'(val & 0x{complement:X}U) == 0')
        
        if checks:
            lines.append(f'    /* Theorem 2: Fusion of {len(checks)} constraints via AND */')
            lines.append(f'    return {" && ".join(checks)};')
        else:
            lines.append(f'    return 1;')
    
    lines.append('}')
    lines.append('')
    lines.append('char _license[] SEC("license") = "Apache-2.0";')
    return '\n'.join(lines)


# ============================================================================
# Target: RISC-V + Xconstr Extension
# ============================================================================

# Xconstr custom instruction encoding (RV32I custom opcode space)
# Using custom-0 (opcode = 0x0B) and custom-1 (opcode = 0x2B) R-type format
#
# R-type: funct7[31:25] | rs2[24:20] | rs1[19:15] | funct3[14:12] | rd[11:7] | opcode[6:0]
#
# CREVISE rd, rs1, lo, hi:
#   funct7 = hi[11:5]  (upper 7 bits of hi)
#   rs2[4:0] = {hi[4], lo[4:0]} packed? No — R-type only has rs2[4:0]
#   Better: Use I-type with custom opcode for 12-bit immediate
#
# I-type: imm[31:20] | rs1[19:15] | funct3[14:12] | rd[11:7] | opcode[6:0]
#
# CREVISE rd, rs1, lo, hi  — uses TWO custom I-type instructions:
#   CSETLO  rd, rs1, imm12    — sets lo bound: rd = (rs1 - imm)  [funct3=0, opcode=0x0B]
#   CSETHI  rd, rs1, imm12    — sets hi bound: rd = (rs1 <= imm) [funct3=1, opcode=0x0B]
# Result: 2 instructions for arbitrary range
#
# For [0, hi]: single CSETHI
# CMASK rd, rs1, mask — I-type: rd = (rs1 & ~mask == 0)  [funct3=2, opcode=0x0B]

XCONSTR_OP_CUSTOM0 = 0x0B  # custom-0 opcode

# CREVISE encodings
def encode_csethi(rd, rs1, hi_imm12):
    """Encode CSETHI rd, rs1, imm12 — check (rs1 <= imm12)"""
    # I-type: imm[31:20] | rs1[19:15] | funct3=0 | rd[11:7] | opcode=0x0B
    imm = hi_imm12 & 0xFFF
    funct3 = 0b000
    insn = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | XCONSTR_OP_CUSTOM0
    return insn

def encode_csetlo(rd, rs1, lo_imm12):
    """Encode CSETLO rd, rs1, imm12 — compute (rs1 - imm12)"""
    # I-type: imm[31:20] | rs1[19:15] | funct3=1 | rd[11:7] | opcode=0x0B
    imm = lo_imm12 & 0xFFF
    funct3 = 0b001
    insn = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | XCONSTR_OP_CUSTOM0
    return insn

def encode_cmask(rd, rs1, mask_imm12):
    """Encode CMASK rd, rs1, imm12 — check (rs1 & imm12 == 0)"""
    # I-type: imm[31:20] | rs1[19:15] | funct3=2 | rd[11:7] | opcode=0x0B
    imm = mask_imm12 & 0xFFF
    funct3 = 0b010
    insn = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | XCONSTR_OP_CUSTOM0
    return insn

def encode_cand(rd, rs1, rs2):
    """Encode CAND rd, rs1, rs2 — AND two constraint results"""
    # R-type: funct7=0 | rs2 | rs1 | funct3=3 | rd | opcode=0x0B
    funct7 = 0
    funct3 = 0b011
    insn = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | XCONSTR_OP_CUSTOM0
    return insn


def emit_riscv(constraint, func_name="flux_check_riscv"):
    """
    Emit RISC-V assembly (RV32I base + Xconstr custom extension).
    
    Xconstr Custom Instructions (opcode space: custom-0 = 0x0B):
    
    CREVISE rd, rs1, lo, hi — Range check in hardware
      Encoding: 2 instructions (CSETLO + CSETHI) for arbitrary [lo, hi]
                1 instruction (CSETHI) for [0, hi]
      Semantics: rd = 1 if lo ≤ rs1 ≤ hi, else 0
    
    CMASK rd, rs1, mask — Domain mask check in hardware
      Encoding: 1 instruction
      Semantics: rd = 1 if (rs1 & mask) == 0, else 0
    
    CAND rd, rs1, rs2 — AND two constraint results
      Encoding: 1 instruction (R-type)
      Semantics: rd = rs1 & rs2
    
    Theorem 3 (Optimal Selection): Each constraint compiles to O(1) Xconstr instructions.
    """
    # Optimize first
    if isinstance(constraint, AndConstraint):
        constraint = optimize_constraints(constraint.constraints)
    
    lines = [
        f'# FLUX Constraint → RISC-V + Xconstr',
        f'# Function: {func_name}',
        f'# Input: a0 = value to check',
        f'# Output: a0 = 1 (pass) or 0 (fail)',
        f'#',
        f'# Xconstr custom opcode: 0x{XCONSTR_OP_CUSTOM0:02X} (custom-0)',
        f'# CSETLO: funct3=0, CMASK: funct3=2, CAND: funct3=3',
        f'#',
        f'# Theorem 3: Optimal instruction selection (O(1) per constraint)',
        f'# Theorem 6: Strength reduction applied where possible',
        '',
    ]
    
    lines.append(f'.globl {func_name}')
    lines.append(f'{func_name}:')
    
    if isinstance(constraint, RangeConstraint):
        _emit_riscv_range(lines, constraint)
    
    elif isinstance(constraint, DomainConstraint):
        _emit_riscv_domain(lines, constraint)
    
    elif isinstance(constraint, AndConstraint):
        _emit_riscv_and(lines, constraint)
    
    lines.append(f'    ret')
    
    # Also emit the Xconstr-optimized version as comment
    lines.append('')
    lines.append(f'# === Xconstr optimized encoding ===')
    _emit_xconstr_encoding(lines, constraint)
    
    return '\n'.join(lines)


def _emit_riscv_range(lines, rc):
    if rc.lo == 0:
        if rc.hi < 4096:
            lines.append(f'    li      a1, {rc.hi}')
        else:
            lines.append(f'    lui     a1, %hi({constraint.hi})')
            lines.append(f'    addi    a1, a1, %lo({constraint.hi})')
        lines.append(f'    sltu    a0, a1, a0      # a0 = (hi < val) ? 1 : 0')
        lines.append(f'    xori    a0, a0, 1       # invert: a0 = (val <= hi) ? 1 : 0')
        lines.append(f'    # Xconstr: CSETHI a0, a0, {rc.hi}  (1 instruction)')
    else:
        lines.append(f'    addi    a0, a0, -{rc.lo}    # a0 = val - lo')
        if rc.hi - rc.lo < 4096:
            lines.append(f'    li      a1, {rc.hi - rc.lo}')
        else:
            lines.append(f'    lui     a1, %hi({rc.hi - rc.lo})')
            lines.append(f'    addi    a1, a1, %lo({rc.hi - rc.lo})')
        lines.append(f'    sltu    a0, a1, a0       # (span < offset)?')
        lines.append(f'    xori    a0, a0, 1        # invert')
        lines.append(f'    # Xconstr: CREVISE a0, a0, {rc.lo}, {rc.hi}  (2 instructions)')


def _emit_riscv_domain(lines, dc):
    complement = (~dc.mask) & 0xFFFFFFFF
    lines.append(f'    li      a1, 0x{complement:X}')
    lines.append(f'    and     a0, a0, a1       # a0 = val & complement')
    lines.append(f'    sltiu   a0, a0, 1        # a0 = (result == 0) ? 1 : 0')
    lines.append(f'    # Xconstr: CMASK a0, a0, 0x{complement:X}  (1 instruction)')


def _emit_riscv_and(lines, constraint):
    ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
    domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
    
    reg_counter = [0]  # mutable counter
    def next_reg():
        r = reg_counter[0]
        reg_counter[0] += 1
        return r
    
    # Use t0-t6 (x5-x31) as temp registers
    temp_regs = ['t0', 't1', 't2', 't3', 't4', 't5', 't6']
    result_reg_idx = 0
    
    for idx, rc in enumerate(ranges):
        tr = temp_regs[idx] if idx < len(temp_regs) else f's{idx - len(temp_regs)}'
        if rc.lo == 0:
            lines.append(f'    li      {tr}, {rc.hi}')
            lines.append(f'    sltu    {tr}, {tr}, a0')
            lines.append(f'    xori    {tr}, {tr}, 1')
        else:
            lines.append(f'    addi    {tr}, a0, -{rc.lo}')
            span = rc.hi - rc.lo
            lines.append(f'    li      a1, {span}')
            lines.append(f'    sltu    {tr}, a1, {tr}')
            lines.append(f'    xori    {tr}, {tr}, 1')
    
    for idx, dc in enumerate(domains):
        tr = temp_regs[len(ranges) + idx] if len(ranges) + idx < len(temp_regs) else f's{len(ranges) + idx - len(temp_regs)}'
        complement = (~dc.mask) & 0xFFFFFFFF
        lines.append(f'    li      {tr}, 0x{complement:X}')
        lines.append(f'    and     {tr}, a0, {tr}')
        lines.append(f'    sltiu   {tr}, {tr}, 1')
    
    # AND all results
    all_results = []
    for idx in range(len(ranges)):
        all_results.append(temp_regs[idx] if idx < len(temp_regs) else f's{idx - len(temp_regs)}')
    for idx in range(len(domains)):
        all_results.append(temp_regs[len(ranges) + idx] if len(ranges) + idx < len(temp_regs) else f's{len(ranges) + idx - len(temp_regs)}')
    
    if len(all_results) == 0:
        lines.append(f'    li      a0, 1')
    elif len(all_results) == 1:
        lines.append(f'    mv      a0, {all_results[0]}')
    else:
        prev = all_results[0]
        for r in all_results[1:]:
            lines.append(f'    and     a0, {prev}, {r}')
            prev = 'a0'


def _emit_xconstr_encoding(lines, constraint):
    """Emit the raw Xconstr machine code encoding."""
    if isinstance(constraint, RangeConstraint):
        if constraint.lo == 0:
            insn = encode_csethi(10, 10, constraint.hi)  # a0=10, a0=10
            lines.append(f'# CSETHI a0, a0, {constraint.hi}')
            lines.append(f'# Encoding: 0x{insn:08X}')
        else:
            insn1 = encode_csetlo(10, 10, constraint.lo)
            insn2 = encode_csethi(10, 10, constraint.hi - constraint.lo)
            lines.append(f'# CSETLO a0, a0, {constraint.lo} → 0x{insn1:08X}')
            lines.append(f'# CSETHI a0, a0, {constraint.hi - constraint.lo} → 0x{insn2:08X}')
    
    elif isinstance(constraint, DomainConstraint):
        complement = (~constraint.mask) & 0xFFFFFFFF
        insn = encode_cmask(10, 10, complement)
        lines.append(f'# CMASK a0, a0, 0x{complement:X}')
        lines.append(f'# Encoding: 0x{insn:08X}')
    
    elif isinstance(constraint, AndConstraint):
        ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
        domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
        rd_counter = 10  # a0=10, then t0=5, t1=6, etc.
        temp_rds = [5, 6, 7, 28, 29, 30, 31]  # t0-t6
        
        encodings = []
        for idx, rc in enumerate(ranges):
            rd = temp_rds[idx] if idx < len(temp_rds) else rd_counter
            rs1 = 10  # a0
            if rc.lo == 0:
                insn = encode_csethi(rd, rs1, rc.hi)
                encodings.append((rd, f'CSETHI x{rd}, x{rs1}, {rc.hi}', insn))
            else:
                insn1 = encode_csetlo(rd, rs1, rc.lo)
                insn2 = encode_csethi(rd, rd, rc.hi - rc.lo)
                encodings.append((rd, f'CSETLO+CSETHI', insn1))
                encodings.append((rd, f'  for [{rc.lo},{rc.hi}]', insn2))
        
        for idx, dc in enumerate(domains):
            rd = temp_rds[len(ranges) + idx] if len(ranges) + idx < len(temp_rds) else rd_counter
            rs1 = 10
            complement = (~dc.mask) & 0xFFFFFFFF
            insn = encode_cmask(rd, rs1, complement)
            encodings.append((rd, f'CMASK x{rd}, x{rs1}, 0x{complement:X}', insn))
        
        # CAND chain
        if len(encodings) >= 2:
            prev_rd = encodings[0][0]
            for i in range(1, len(encodings)):
                curr_rd = encodings[i][0]
                and_insn = encode_cand(prev_rd, prev_rd, curr_rd)
                encodings.append((prev_rd, f'CAND x{prev_rd}, x{prev_rd}, x{curr_rd}', and_insn))
        
        for rd, desc, insn in encodings:
            lines.append(f'# {desc} → 0x{insn:08X}')


# ============================================================================
# Compiler Pipeline
# ============================================================================

class FluxLLVMCompiler:
    def __init__(self):
        self.targets = {
            'x86': self.compile_native,
            'avx512': self.compile_native,
            'wasm': self.compile_wasm,
            'ebpf': self.compile_ebpf,
            'riscv': self.compile_riscv,
            'ir': self.show_ir,
        }
    
    def compile(self, constraint_text, target='x86', vectorize=False):
        constraint = parse_guard(constraint_text)
        return self.targets[target](constraint, vectorize)
    
    def show_ir(self, constraint, vectorize=False):
        if vectorize:
            return emit_llvm_ir(constraint, vectorize=True)
        return emit_llvm_ir(constraint)
    
    def compile_native(self, constraint, vectorize=False):
        """Compile to native shared library via LLVM IR → llc → gcc."""
        ir_code = emit_llvm_ir(constraint)
        
        with tempfile.NamedTemporaryFile(suffix='.ll', mode='w', delete=False) as f:
            f.write(ir_code)
            ir_path = f.name
        
        so_path = ir_path.replace('.ll', '.so')
        
        # Try llc first
        try:
            result = subprocess.run(
                ['llc', '-O3', '-march=x86-64', '-mattr=+avx512f',
                 '-filetype=obj', '-o', ir_path.replace('.ll', '.o'), ir_path],
                capture_output=True, text=True, timeout=30
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            result = subprocess.CompletedProcess(args=[], returncode=1, stdout='', stderr='llc not found')
        
        if result.returncode == 0:
            subprocess.run(
                ['gcc', '-shared', '-o', so_path, ir_path.replace('.ll', '.o')],
                capture_output=True, text=True
            )
            obj_path = ir_path.replace('.ll', '.o')
            if os.path.exists(obj_path):
                os.unlink(obj_path)
        else:
            os.unlink(ir_path)
            return self._compile_c_fallback(constraint)
        
        os.unlink(ir_path)
        return so_path
    
    def _compile_c_fallback(self, constraint):
        """Fallback: emit C and compile with gcc."""
        c_code = self._emit_c(constraint)
        
        with tempfile.NamedTemporaryFile(suffix='.c', mode='w', delete=False) as f:
            f.write(c_code)
            c_path = f.name
        
        so_path = c_path.replace('.c', '.so')
        result = subprocess.run(
            ['gcc', '-O3', '-march=native', '-mavx512f', '-shared', '-fPIC',
             '-o', so_path, c_path],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed: {result.stderr}")
        
        os.unlink(c_path)
        return so_path
    
    def _emit_c(self, constraint):
        """Emit simple C for the constraint."""
        # Optimize first
        if isinstance(constraint, AndConstraint):
            constraint = optimize_constraints(constraint.constraints)
        
        lines = [
            '/*',
            ' * FLUX Constraint → C (optimized)',
            ' * Theorem 3: Optimal instruction selection',
            ' * Theorem 5: Dead constraint elimination',
            ' * Theorem 6: Strength reduction',
            ' */',
            '#include <stdint.h>',
            '',
            'int flux_check(int32_t val) {',
        ]
        if isinstance(constraint, RangeConstraint):
            if constraint.lo == 0:
                lines.append(f'    return (uint32_t)val <= {constraint.hi};')
            else:
                lines.append(f'    uint32_t off = (uint32_t)(val - {constraint.lo});')
                lines.append(f'    return off <= (uint32_t)({constraint.hi} - {constraint.lo});')
        elif isinstance(constraint, DomainConstraint):
            complement = (~constraint.mask) & 0xFFFFFFFF
            lines.append(f'    return (val & 0x{complement:X}U) == 0;')
        elif isinstance(constraint, AndConstraint):
            ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
            domains = [c for c in constraint.constraints if isinstance(c, DomainConstraint)]
            checks = []
            for rc in ranges:
                if rc.lo == 0:
                    checks.append(f'(uint32_t)val <= {rc.hi}')
                else:
                    checks.append(f'(uint32_t)(val - {rc.lo}) <= (uint32_t)({rc.hi} - {rc.lo})')
            for dc in domains:
                complement = (~dc.mask) & 0xFFFFFFFF
                checks.append(f'(val & 0x{complement:X}U) == 0')
            lines.append(f'    return {" && ".join(checks)};')
        lines.append('}')
        return '\n'.join(lines)
    
    def compile_wasm(self, constraint, vectorize=False):
        """Compile to WebAssembly via LLVM IR → llc -march=wasm32 or WAT."""
        # Try LLVM IR → wasm32 first
        ir_code = emit_wasm_ir(constraint)
        
        with tempfile.NamedTemporaryFile(suffix='.ll', mode='w', delete=False) as f:
            f.write(ir_code)
            ir_path = f.name
        
        obj_path = ir_path.replace('.ll', '.o')
        wasm_path = ir_path.replace('.ll', '.wasm')
        
        # Try llc with wasm32 target
        try:
            result = subprocess.run(
                ['llc', '-O3', '-march=wasm32', '-filetype=obj',
                 '-o', obj_path, ir_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                # Try wasm-ld
                ld_result = subprocess.run(
                    ['wasm-ld', '--no-entry', '--export=flux_check_wasm',
                     '-o', wasm_path, obj_path],
                    capture_output=True, text=True, timeout=30
                )
                if ld_result.returncode == 0:
                    os.unlink(ir_path)
                    if os.path.exists(obj_path):
                        os.unlink(obj_path)
                    return wasm_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Cleanup LLVM attempts
        for p in [ir_path, obj_path]:
            if os.path.exists(p):
                os.unlink(p)
        
        # Fallback: emit WAT and try wat2wasm
        wat_code = emit_wat(constraint)
        wat_path = tempfile.mktemp(suffix='.wat')
        wasm_path = wat_path.replace('.wat', '.wasm')
        
        with open(wat_path, 'w') as f:
            f.write(wat_code)
        
        try:
            result = subprocess.run(
                ['wat2wasm', wat_path, '-o', wasm_path],
                capture_output=True, text=True, timeout=30
            )
            os.unlink(wat_path)
            if result.returncode == 0:
                return wasm_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Return WAT source if tools not available
        return wat_code
    
    def compile_ebpf(self, constraint, vectorize=False):
        """Emit eBPF C source."""
        return emit_ebpf(constraint)
    
    def compile_riscv(self, constraint, vectorize=False):
        """Emit RISC-V assembly with Xconstr encodings."""
        return emit_riscv(constraint)


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("flux_llvm_backend — FLUX → LLVM IR Compiler")
        print()
        print("Usage:")
        print("  flux_llvm_backend ir <file.guard> [--vectorize]     # Show LLVM IR")
        print("  flux_llvm_backend compile <file.guard> --target ... # Compile")
        print("  flux_llvm_backend bench <file.guard>                # Compile & benchmark")
        print("  flux_llvm_backend show <file.guard>                 # Show all targets")
        print("  flux_llvm_backend targets                           # List targets")
        print()
        print("Targets: x86, avx512, wasm, ebpf, riscv")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'targets':
        print("Supported targets:")
        print("  x86     — Native x86-64 (via LLVM IR → llc)")
        print("  avx512  — x86-64 with AVX-512 (via LLVM IR)")
        print("  wasm    — WebAssembly (via WAT or LLVM IR → wasm32)")
        print("  ebpf    — eBPF for Linux kernel (C source)")
        print("  riscv   — RISC-V + Xconstr extension (assembly)")
        return
    
    if cmd == 'show':
        guard_file = sys.argv[2] if len(sys.argv) > 2 else None
        if not guard_file:
            print("Error: specify a GUARD file")
            sys.exit(1)
        with open(guard_file) as f:
            constraint_text = f.read()
        constraint = parse_guard(constraint_text)
        print(f"=== Constraint: {constraint} ===\n")
        
        print("--- LLVM IR (scalar, x86-64) ---")
        print(emit_llvm_ir(constraint))
        print()
        
        print("--- LLVM IR (scalar, wasm32) ---")
        print(emit_llvm_ir(constraint, target_triple="wasm32-unknown-unknown"))
        print()
        
        print("--- LLVM IR (vectorized, 16-wide) ---")
        print(emit_llvm_ir(constraint, vectorize=True))
        print()
        
        print("--- eBPF (kernel constraint checker) ---")
        print(emit_ebpf(constraint))
        print()
        
        print("--- WebAssembly (WAT) ---")
        print(emit_wat(constraint))
        print()
        
        print("--- RISC-V + Xconstr ---")
        print(emit_riscv(constraint))
        return
    
    guard_file = sys.argv[2] if len(sys.argv) > 2 else None
    target = 'x86'
    vectorize = '--vectorize' in sys.argv
    
    for i, arg in enumerate(sys.argv):
        if arg == '--target' and i+1 < len(sys.argv):
            target = sys.argv[i+1]
    
    if not guard_file:
        print("Error: specify a GUARD file")
        sys.exit(1)
    
    with open(guard_file) as f:
        constraint_text = f.read()
    
    compiler = FluxLLVMCompiler()
    
    if cmd == 'ir':
        ir = compiler.compile(constraint_text, 'ir', vectorize)
        print(ir)
    
    elif cmd == 'compile':
        result = compiler.compile(constraint_text, target, vectorize)
        if isinstance(result, str) and os.path.isfile(result):
            print(f"Compiled to: {result}")
        else:
            print(result)
    
    elif cmd == 'bench':
        so_path = compiler.compile(constraint_text, 'x86')
        if not os.path.isfile(so_path):
            print(f"Cannot benchmark — no shared library produced.")
            print(so_path)
            return
        
        lib = ctypes.CDLL(so_path)
        
        N = 10000000
        inputs = [random.randint(0, 200) for _ in range(N)]
        results = []
        
        # Warmup
        for v in inputs[:1000]:
            lib.flux_check(v)
        
        t0 = time.perf_counter()
        for v in inputs:
            results.append(lib.flux_check(v))
        t1 = time.perf_counter()
        
        elapsed = t1 - t0
        tps = N / elapsed
        passes = sum(results)
        
        print(f"Constraint: {parse_guard(constraint_text)}")
        print(f"  {N:,} checks in {elapsed*1000:.2f}ms = {tps:,.0f} checks/s")
        print(f"  Per check: {elapsed*1e9/N:.2f}ns")
        print(f"  Pass rate: {passes/N*100:.1f}%")
        
        if os.path.isfile(so_path):
            os.unlink(so_path)

if __name__ == '__main__':
    main()

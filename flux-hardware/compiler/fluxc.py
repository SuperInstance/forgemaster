#!/usr/bin/env python3
"""
fluxc — FLUX Constraint-to-Native Compiler

Usage:
    fluxc compile <constraint.guard> -o <output> [--target avx512|cuda|wasm|riscv|fortran]
    fluxc check <input_file> --against <constraint.guard>
    fluxc bench <constraint.guard> -n 1000000

The TUTOR approach: compile the constraint intent, don't interpret it.
Reads GUARD constraints, generates optimal native code for the target.
"""
import sys
import os
import subprocess
import tempfile
import json
import time
import random
import ctypes

# ============================================================================
# GUARD Parser (minimal — handles range, domain, multi-constraint)
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
    """Parse a simple GUARD constraint file."""
    constraints = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('constraint '):
            line = line[len('constraint '):]
        
        # Parse "var in [lo, hi]"
        if ' in [' in line and ']' in line:
            var = line.split(' in ')[0].strip()
            range_str = line.split(' in [')[1].split(']')[0]
            parts = range_str.split(',')
            lo = int(parts[0].strip())
            hi = int(parts[1].strip())
            constraints.append(RangeConstraint(var, lo, hi))
        
        # Parse "var in domain 0xMASK"
        elif ' in domain ' in line:
            var = line.split(' in domain ')[0].strip()
            mask = int(line.split(' in domain ')[1].strip(), 16)
            constraints.append(DomainConstraint(var, mask))
    
    if len(constraints) == 1:
        return constraints[0]
    return AndConstraint(constraints)


# ============================================================================
# Backend: C with AVX-512 (highest performance)
# ============================================================================

def emit_c_avx512(constraint, func_name="flux_compiled_check"):
    """Generate C with AVX-512 intrinsics from a constraint."""
    lines = [
        '#include <immintrin.h>',
        '#include <stdint.h>',
        '',
        f'void {func_name}(const int32_t* input, int32_t* output, int n) {{',
    ]
    
    if isinstance(constraint, RangeConstraint):
        lines.append(f'    __m512i vlo = _mm512_set1_epi32({constraint.lo});')
        lines.append(f'    __m512i vhi = _mm512_set1_epi32({constraint.hi});')
        lines.append('    __m512i ones = _mm512_set1_epi32(1);')
        lines.append('    __m512i zeros = _mm512_setzero_si512();')
        lines.append('    int i = 0;')
        lines.append('    for (; i + 16 <= n; i += 16) {')
        lines.append('        __m512i v = _mm512_loadu_si512((const __m512i*)(input + i));')
        lines.append('        __mmask16 ge = _mm512_cmpge_epi32_mask(v, vlo);')
        lines.append('        __mmask16 le = _mm512_cmple_epi32_mask(v, vhi);')
        lines.append('        __mmask16 in_range = _mm512_kand(ge, le);')
        lines.append('        __m512i result = _mm512_mask_blend_epi32(in_range, zeros, ones);')
        lines.append('        _mm512_storeu_si512((__m512i*)(output + i), result);')
        lines.append('    }')
        lines.append(f'    for (; i < n; i++) output[i] = (input[i] >= {constraint.lo} && input[i] <= {constraint.hi}) ? 1 : 0;')
    
    elif isinstance(constraint, DomainConstraint):
        lines.append(f'    __m512i vmask = _mm512_set1_epi32(0x{constraint.mask:X});')
        lines.append('    __m512i ones = _mm512_set1_epi32(1);')
        lines.append('    __m512i zeros = _mm512_setzero_si512();')
        lines.append('    int i = 0;')
        lines.append('    for (; i + 16 <= n; i += 16) {')
        lines.append('        __m512i v = _mm512_loadu_si512((const __m512i*)(input + i));')
        lines.append('        __m512i masked = _mm512_and_si512(v, vmask);')
        lines.append('        __mmask16 eq = _mm512_cmpeq_epi32_mask(masked, v);')
        lines.append('        __m512i result = _mm512_mask_blend_epi32(eq, zeros, ones);')
        lines.append('        _mm512_storeu_si512((__m512i*)(output + i), result);')
        lines.append('    }')
        lines.append(f'    for (; i < n; i++) output[i] = ((input[i] & 0x{constraint.mask:X}) == input[i]) ? 1 : 0;')
    
    elif isinstance(constraint, AndConstraint):
        ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
        for idx, rc in enumerate(ranges):
            lines.append(f'    __m512i vlo{idx} = _mm512_set1_epi32({rc.lo});')
            lines.append(f'    __m512i vhi{idx} = _mm512_set1_epi32({rc.hi});')
        lines.append('    __m512i ones = _mm512_set1_epi32(1);')
        lines.append('    __m512i zeros = _mm512_setzero_si512();')
        lines.append('    int i = 0;')
        lines.append('    for (; i + 16 <= n; i += 16) {')
        lines.append('        __m512i v = _mm512_loadu_si512((const __m512i*)(input + i));')
        lines.append('        __mmask16 all_pass = 0xFFFF;')
        for idx, rc in enumerate(ranges):
            lines.append(f'        __mmask16 ge{idx} = _mm512_cmpge_epi32_mask(v, vlo{idx});')
            lines.append(f'        __mmask16 le{idx} = _mm512_cmple_epi32_mask(v, vhi{idx});')
            lines.append(f'        all_pass = _mm512_kand(all_pass, _mm512_kand(ge{idx}, le{idx}));')
        lines.append('        __m512i result = _mm512_mask_blend_epi32(all_pass, zeros, ones);')
        lines.append('        _mm512_storeu_si512((__m512i*)(output + i), result);')
        lines.append('    }')
        # Scalar fallback
        lines.append(f'    for (; i < n; i++) {{')
        lines.append(f'        int pass = 1;')
        for idx, rc in enumerate(ranges):
            lines.append(f'        if (input[i] < {rc.lo} || input[i] > {rc.hi}) pass = 0;')
        lines.append(f'        output[i] = pass;')
        lines.append(f'    }}')
    
    lines.append('}')
    return '\n'.join(lines)


# ============================================================================
# Backend: Fortran (auto-vectorized)
# ============================================================================

def emit_fortran(constraint, func_name="flux_compiled_check"):
    """Generate Fortran from a constraint."""
    lines = [
        'subroutine flux_compiled_check(inputs, results, n) bind(C)',
        '  use iso_c_binding, only: c_int',
        '  integer(c_int), intent(in) :: inputs(n)',
        '  integer(c_int), intent(out) :: results(n)',
        '  integer(c_int), value :: n',
        ''
    ]
    
    if isinstance(constraint, RangeConstraint):
        lines.append(f'  results(1:n) = merge(1, 0, inputs(1:n) >= {constraint.lo} .and. inputs(1:n) <= {constraint.hi})')
    elif isinstance(constraint, AndConstraint):
        ranges = [c for c in constraint.constraints if isinstance(c, RangeConstraint)]
        lines.append('  results(1:n) = 1')
        for rc in ranges:
            lines.append(f'  results(1:n) = results(1:n) * merge(1, 0, inputs(1:n) >= {rc.lo} .and. inputs(1:n) <= {rc.hi})')
    
    lines.append('end subroutine')
    return '\n'.join(lines)


# ============================================================================
# Backend: Native x86-64 (JIT via mmap)
# ============================================================================

def emit_x86_64(constraint):
    """Generate x86-64 machine code bytes for a constraint."""
    code = bytearray()
    
    if isinstance(constraint, RangeConstraint):
        # cmp edi, lo; jl fail; cmp edi, hi; jg fail; mov eax,1; ret; fail: mov eax,0; ret
        code += b'\x81\xff'  # cmp edi, imm32
        code += constraint.lo.to_bytes(4, 'little')
        code += b'\x0f\x8c\x09\x00\x00\x00'  # jl +9 (to fail)
        code += b'\x81\xff'  # cmp edi, imm32
        code += constraint.hi.to_bytes(4, 'little')
        code += b'\x0f\x8f\x01\x00\x00\x00'  # jg +1 (to fail)
        code += b'\xb8\x01\x00\x00\x00'  # mov eax, 1
        code += b'\xc3'  # ret
        code += b'\xb8\x00\x00\x00\x00'  # mov eax, 0
        code += b'\xc3'  # ret
    
    return bytes(code)


# ============================================================================
# Compiler Pipeline
# ============================================================================

class FluxCompiler:
    def __init__(self):
        self.backends = {
            'avx512': self.compile_avx512,
            'fortran': self.compile_fortran,
            'native': self.compile_native,
            'cuda': self.compile_cuda_stub,
            'wasm': self.compile_wasm_stub,
        }
    
    def compile(self, constraint_text, target='avx512'):
        """Compile a GUARD constraint to native code."""
        constraint = parse_guard(constraint_text)
        return self.backends[target](constraint)
    
    def compile_avx512(self, constraint):
        """Compile to C with AVX-512 intrinsics, return shared library."""
        c_code = emit_c_avx512(constraint)
        
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
    
    def compile_fortran(self, constraint):
        """Compile to Fortran, return shared library."""
        f_code = emit_fortran(constraint)
        
        with tempfile.NamedTemporaryFile(suffix='.f90', mode='w', delete=False) as f:
            f.write(f_code)
            f_path = f.name
        
        so_path = f_path.replace('.f90', '.so')
        result = subprocess.run(
            ['gfortran', '-O3', '-march=native', '-shared', '-fPIC',
             '-o', so_path, f_path],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed: {result.stderr}")
        
        os.unlink(f_path)
        return so_path
    
    def compile_native(self, constraint):
        """JIT-compile to x86-64 machine code in executable memory."""
        import mmap
        
        code = emit_x86_64(constraint)
        
        # Allocate executable memory
        mem = mmap.mmap(-1, len(code), prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC,
                        flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
        mem.write(code)
        
        return mem, ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)(ctypes.c_void_p.from_buffer(mem))
    
    def compile_cuda_stub(self, constraint):
        return "CUDA backend: use flux_cuda_kernels.so directly"
    
    def compile_wasm_stub(self, constraint):
        return "WASM backend: use flux_webgpu.js directly"


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("fluxc — FLUX Constraint-to-Native Compiler")
        print()
        print("Usage:")
        print("  fluxc compile <file.guard> [--target avx512|fortran|native|cuda|wasm]")
        print("  fluxc bench <file.guard> [-n 1000000] [--target avx512]")
        print("  fluxc show <file.guard> [--target avx512|fortran|native]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'bench':
        guard_file = sys.argv[2] if len(sys.argv) > 2 else None
        if not guard_file:
            print("Error: specify a GUARD file")
            sys.exit(1)
        
        n = 1000000
        target = 'avx512'
        
        for i, arg in enumerate(sys.argv):
            if arg == '-n' and i+1 < len(sys.argv):
                n = int(sys.argv[i+1])
            if arg == '--target' and i+1 < len(sys.argv):
                target = sys.argv[i+1]
        
        with open(guard_file) as f:
            constraint_text = f.read()
        
        print(f"Compiling {guard_file} → {target}...")
        
        compiler = FluxCompiler()
        
        if target == 'native':
            constraint = parse_guard(constraint_text)
            mem, fn = compiler.compile_native(constraint)
            
            inputs = [random.randint(0, 100) for _ in range(n)]
            
            t0 = time.perf_counter()
            results = [fn(inp) for inp in inputs]
            elapsed = time.perf_counter() - t0
            
            tps = n / elapsed
            passes = sum(results)
            print(f"  {n:,} inputs in {elapsed*1000:.2f}ms = {tps:,.0f} checks/s")
            print(f"  Pass rate: {passes/n*100:.1f}%")
            print(f"  Per check: {elapsed*1e9/n:.2f}ns")
            mem.close()
        
        elif target in ('avx512', 'fortran'):
            so_path = compiler.compile(constraint_text, target)
            lib = ctypes.CDLL(so_path)
            
            inputs = [random.randint(0, 100) for _ in range(n)]
            inp_arr = (ctypes.c_int32 * n)(*inputs)
            res_arr = (ctypes.c_int32 * n)()
            
            # Warmup
            lib.flux_compiled_check(inp_arr, res_arr, n)
            
            t0 = time.perf_counter()
            for _ in range(5):
                lib.flux_compiled_check(inp_arr, res_arr, n)
            elapsed = (time.perf_counter() - t0) / 5
            
            tps = n / elapsed
            passes = sum(res_arr)
            print(f"  {n:,} inputs in {elapsed*1000:.2f}ms = {tps:,.0f} checks/s")
            print(f"  Pass rate: {passes/n*100:.1f}%")
            print(f"  Per check: {elapsed*1e9/n:.2f}ns")
            
            os.unlink(so_path)
    
    elif cmd == 'show':
        guard_file = sys.argv[2]
        target = 'avx512'
        
        for i, arg in enumerate(sys.argv):
            if arg == '--target' and i+1 < len(sys.argv):
                target = sys.argv[i+1]
        
        with open(guard_file) as f:
            constraint_text = f.read()
        
        constraint = parse_guard(constraint_text)
        print(f"Constraint: {constraint}")
        print()
        
        if target == 'avx512':
            print("Generated C + AVX-512:")
            print(emit_c_avx512(constraint))
        elif target == 'fortran':
            print("Generated Fortran:")
            print(emit_fortran(constraint))
        elif target == 'native':
            code = emit_x86_64(constraint)
            print(f"Generated x86-64 ({len(code)} bytes):")
            print(' '.join(f'{b:02X}' for b in code))
    
    elif cmd == 'compile':
        guard_file = sys.argv[2]
        target = 'avx512'
        output = None
        
        for i, arg in enumerate(sys.argv):
            if arg == '--target' and i+1 < len(sys.argv):
                target = sys.argv[i+1]
            if arg == '-o' and i+1 < len(sys.argv):
                output = sys.argv[i+1]
        
        with open(guard_file) as f:
            constraint_text = f.read()
        
        compiler = FluxCompiler()
        result = compiler.compile(constraint_text, target)
        
        if isinstance(result, str):
            print(result)
        elif isinstance(result, tuple):
            print(f"JIT-compiled to executable memory")
        else:
            if output:
                import shutil
                shutil.copy2(result, output)
                os.unlink(result)
                print(f"Compiled to {output}")
            else:
                print(f"Compiled to {result}")

if __name__ == '__main__':
    main()

# Modern Fortran for High-Performance Constraint Checking on AMD Zen 5 / AVX-512

**Forgemaster Research Report — 2026-05-03**

---

## 1. Fortran vs C for SIMD: Why Fortran Auto-Vectorizes Better

### The Alias Advantage

Fortran's single biggest SIMD win over C is **no pointer aliasing by default**. In C, the compiler must assume any two pointers may alias (point to overlapping memory). This cripples auto-vectorization because:

```c
// C — compiler CANNOT vectorize this without restrict
void add_arrays(double *a, double *b, double *c, int n) {
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];  // may c overlap a or b? compiler can't tell
    }
}

// C with restrict — now vectorizable
void add_arrays(double *restrict a, double *restrict b, double *restrict c, int n) {
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];  // restrict guarantees no overlap
    }
}
```

In Fortran, **all arrays are non-aliasing by language definition**:

```fortran
! Fortran — ALWAYS vectorizable, no annotations needed
subroutine add_arrays(a, b, c, n)
    real(8), intent(in)  :: a(:), b(:)
    real(8), intent(out) :: c(:)
    c = a + b   ! array syntax — compiler KNOWS no aliasing
end subroutine
```

### Array Syntax: The Vectorization Hint

Fortran's array syntax (`c = a + b`, `where (a > 0) b = sqrt(a)`) is essentially **portable SIMD**. The compiler reads these as explicit whole-array operations and maps them directly to vector instructions:

- `c = a + b` → `vaddpd zmm0, zmm1, zmm2` (AVX-512, 8 doubles at once)
- `where (mask) a = b` → masked vector move
- `forall` → explicitly parallel loop nest

### Concrete Win: Range Check

```fortran
! Fortran — 10M range check, auto-vectorizes to AVX-512
function count_in_range(values, lo, hi, n) result(count)
    real(8), intent(in) :: values(:)
    real(8), intent(in) :: lo, hi
    integer, intent(in) :: n
    integer :: count
    count = count(values >= lo .and. values <= hi)
    ! Compiler emits: vcmppd + vandpd + vpopcntdq
    ! Single pass, fully vectorized, no scalar fallback
end function
```

```c
// C equivalent — requires manual intrinsics or very careful restrict
int count_in_range(const double *restrict values, double lo, double hi, int n) {
    int count = 0;
    for (int i = 0; i < n; i++) {     // only vectorizes with -O3 + restrict
        if (values[i] >= lo && values[i] <= hi) count++;
    }
    return count;
}
```

**Benchmark expectation:** Fortran with `gfortran -O3 -march=znver5 -ffast-math` produces identical or better AVX-512 code than `gcc -O3 -march=znver5 -ffast-math` with `restrict`, because gfortran can also apply loop transformations (fusion, interchange, unrolling) more aggressively when alias analysis is unconstrained.

### Key Compiler Flags for Zen 5

| Flag | Effect |
|------|--------|
| `-march=znver5` | Target Zen 5 (AVX-512, BF16) |
| `-O3` | Auto-vectorization, loop unrolling |
| `-ffast-math` | Allow FP reassociation (critical for SIMD reduction) |
| `-funroll-loops` | Explicit loop unrolling |
| `-ftree-vectorize` | (implied by -O3) |
| `-fstack-arrays` | Stack allocation for temporaries (avoids malloc) |
| `-mavx512f -mavx512dq` | Explicit AVX-512 enable if -march insufficient |

---

## 2. Fortran 2018 Coarrays: Built-in PGAS Parallelism

### What Are Coarrays?

Coarrays are Fortran's native parallel programming model (PGAS — Partitioned Global Address Space). They're part of the language standard since Fortran 2008, with major improvements in Fortran 2018.

```fortran
program coarray_constraint_check
    implicit none
    real(8), allocatable :: values(:)[:]
    integer :: n, num_images, me
    logical :: all_valid[*]  ! scalar coarray — one per image

    me = this_image()
    num_images = num_images()

    n = 10000000 / num_images
    allocate(values(n)[*])

    ! Each image checks its partition
    values(:)[me] = load_partition(me)
    all_valid = all(values >= 0.0d0 .and. values <= 1.0d0)

    sync all  ! barrier

    ! Image 1 collects results
    if (me == 1) then
        block
            logical :: global_valid
            global_valid = .true.
            do i = 1, num_images
                global_valid = global_valid .and. all_valid[i]
            end do
            print *, 'All constraints satisfied:', global_valid
        end block
    end if
end program
```

### Coarrays vs OpenMP vs pthreads

| Aspect | Coarrays | OpenMP | pthreads |
|--------|----------|--------|----------|
| **Paradigm** | PGAS (distributed memory) | Shared memory | Shared memory |
| **Latency** | Higher (one-sided RDMA) | Lower (shared cache) | Lowest |
| **Scalability** | Single node → cluster | Single node only | Single node only |
| **Code complexity** | Very low (language-level) | Low (pragmas) | High (manual) |
| **AMD Zen 5 fit** | Good for multi-CCD | Best for single-CCD | Best for fine-grained |
| **Data races** | Impossible by design | Possible | Common |

### Recommendation for Constraint Checking

For **AMD Zen 5** (16C/32T typical, dual CCD):
- **OpenMP** is the pragmatic choice for shared-memory constraint checking on a single Zen 5 chip
- **Coarrays** shine when scaling beyond one node (cluster-level constraint checking)
- **Hybrid**: Use OpenMP within a CCD, coarrays across CCDs/nodes

```fortran
! Hybrid: OpenMP + array syntax (best for single Zen 5)
subroutine check_constraints_omp(values, lo, hi, n, mask)
    use omp_lib
    real(8), intent(in)  :: values(:), lo(:), hi(:)
    integer, intent(in)  :: n
    logical, intent(out) :: mask(:)
    integer :: i

    !$omp parallel do simd schedule(static)
    do i = 1, n
        mask(i) = all(values(i) >= lo .and. values(i) <= hi)
    end do
    !$omp end parallel do simd
end subroutine
```

---

## 3. Fortran Array Syntax for Constraint Checking

### Full Constraint Checking Module

See the companion file `constraint_checker.f90` for the complete module. Key patterns:

```fortran
! Range check: 10M values against [lo, hi]
mask = (values >= lo) .and. (values <= hi)
count_valid = count(mask)

! Bitmask domain operations
integer(int64) :: domains(:), result
result = iand(domains, mask_bits)  ! bitwise AND on entire arrays
result = ior(domains, set_bits)    ! bitwise OR
result = ieor(domains, flip_bits)  ! bitwise XOR
result = not(domains)              ! bitwise NOT

! Multi-constraint AND evaluation
all_satisfied = all(c1 .and. c2 .and. c3 .and. c4 .and. c5)
! Compiler emits: vandpd zmm0-zmm4 → single reduction
```

### Performance Characteristics on Zen 5

- AVX-512 processes **8 doubles** or **16 singles** per cycle
- Zen 5 has **2x 512-bit FADD** + **2x 512-bit FMUL** per cycle
- Array syntax `c = a + b` → sustained ~2 FLOP/cycle × 8 lanes × 2 pipes = **32 DP FLOP/cycle**
- At 4.0 GHz base: theoretical **128 GFLOPS DP** per core
- Range check (`>=` and `<=`): comparison is integer-speed on Zen 5, ~2 comparisons/cycle × 8 lanes

---

## 4. ISO_Fortran_binding.h: C Interoperability

### The Interface

Fortran 2018 provides `ISO_Fortran_binding.h` for type-safe C interop. Here's the exact interface for calling our constraint checker from C:

```c
// C caller — uses ISO_Fortran_binding.h
#include <stdio.h>
#include <ISO_Fortran_binding.h>

// Fortran subroutine declaration (from iso_c_binding)
extern void check_range_f64(double *values, int *n, double *lo, double *hi, _Bool *mask);

int main() {
    int n = 10000000;
    double values[n], lo = 0.0, hi = 1.0;
    _Bool mask[n];

    // Fill values...
    check_range_f64(values, &n, &lo, &hi, mask);

    int valid = 0;
    for (int i = 0; i < n; i++) valid += mask[i];
    printf("Valid: %d / %d\n", valid, n);
    return 0;
}
```

### Fortran Side with iso_c_binding

```fortran
module constraint_checker_c
    use iso_c_binding
    use constraint_checker
    implicit none

contains

    ! C-callable wrapper: range check on double arrays
    subroutine check_range_f64(values, n, lo, hi, mask) bind(C, name='check_range_f64')
        real(c_double), intent(in)  :: values(*)
        integer(c_int), intent(in)  :: n
        real(c_double), intent(in)  :: lo, hi
        logical(c_bool), intent(out) :: mask(*)

        ! Call the Fortran array-syntax kernel
        call check_range(values(1:n), lo, hi, mask(1:n))
    end subroutine

    ! C-callable wrapper: multi-constraint AND
    subroutine check_multi_f64(values, n, nconstraints, lo, hi, result) &
        bind(C, name='check_multi_f64')
        real(c_double), intent(in)  :: values(*)
        integer(c_int), intent(in)  :: n, nconstraints
        real(c_double), intent(in)  :: lo(*), hi(*)  ! nconstraints × 2
        logical(c_bool), intent(out) :: result(*)

        real(c_double) :: lo_arr(nconstraints), hi_arr(nconstraints)
        logical :: mask(n)
        integer :: j

        lo_arr = lo(1:nconstraints)
        hi_arr = hi(1:nconstraints)

        result(1:n) = .true.  ! init all valid
        do j = 1, nconstraints
            mask(1:n) = (values(1:n) >= lo_arr(j)) .and. (values(1:n) <= hi_arr(j))
            result(1:n) = result(1:n) .and. mask(1:n)
        end do
    end subroutine

end module
```

### Calling from Rust via FFI

```rust
// Rust FFI to Fortran constraint checker
use std::os::raw::{c_double, c_int, c_bool};

extern "C" {
    fn check_range_f64(
        values: *const c_double,
        n: *const c_int,
        lo: *const c_double,
        hi: *const c_double,
        mask: *mut c_bool,
    );
}

pub fn check_range(values: &[f64], lo: f64, hi: f64) -> Vec<bool> {
    let n = values.len() as c_int;
    let mut mask = vec![false as c_bool; values.len()];
    unsafe {
        check_range_f64(values.as_ptr(), &n, &lo, &hi, mask.as_mut_ptr());
    }
    mask.iter().map(|&b| b != 0).collect()
}
```

### Key Interoperability Rules

1. **`bind(C, name=...)`** — Required for C-linkage symbol names
2. **`iso_c_binding` types** — Use `c_double`, `c_int`, `c_bool` (NOT `real(8)`, `integer`)
3. **Assumed-size arrays** — Use `values(*)` in the bind(C) wrapper, then slice to `values(1:n)`
4. **No allocatable/pointer in bind(C)** — Pass sizes explicitly
5. **Character handling** — Pass `character(kind=c_char)` with explicit length
6. **Array layout** — Both C and Fortran use column-major for 2D; for 1D, they're identical

---

## 5. Fortran + AVX-512: Compiler Support

### gfortran (GCC)

- **Auto-vectorization to AVX-512**: Yes, with `-march=znver5` or `-mavx512f -mavx512dq -mavx512vl`
- **Flags**: `-O3 -march=znver5 -ffast-math -ftree-vectorize -fopt-info-vec` (the last flag reports what was vectorized)
- **Quality**: Good for simple loops. Struggles with complex gather/scatter patterns.
- **Array syntax**: Translates directly to vectorized loops. The front-end lowers `a = b + c` to a loop, then the vectorizer picks it up.

### ifx (Intel Fortran — OneAPI)

- **The gold standard for Fortran AVX-512 codegen**
- **Free via Intel oneAPI Base Toolkit** (no license needed since 2024)
- **Flags**: `-O3 -xAVX512 -fp-model fast=2`
- **Advantage**: Intel's vectorizer is more mature. Handles masked assignments, gather/scatter, and fused operations better than GCC.
- **AMD Zen 5 caveat**: `-xAVX512` generates code for Intel AVX-512. For AMD, use `-march=znver5` or `-axAVX512,ZEN` (if supported). In practice, `-O3 -march=znver5` works.
- **ifx is LLVM-based** (uses LLVM backend since oneAPI 2024), so codegen quality is converging with clang.

### LFortran (LLVM-based, ASR)

- **The future** — compiles Fortran to LLVM IR via ASR (Abstract Semantic Representation)
- **AVX-512**: Inherited from LLVM backend. As of 2025, still experimental for complex Fortran features.
- **Advantage**: Modern architecture, compile-time speed, Python integration (can JIT Fortran from Python via LPython/LFortran).
- **Status**: Not production-ready for full Fortran 2018. Good for array-syntax subset.

### NVFortran (NVIDIA HPC SDK, now free)

- **Excellent AVX-512 + GPU offload**
- **Flags**: `-O3 -Mavx512` or `-tp zen5`
- **Strength**: Unified CPU+GPU Fortran. Can offload constraint checking to GPU with `!$acc` directives.
- **AMD support**: `-tp zen5` generates optimized Zen 5 code.

### Recommendation Matrix

| Compiler | AVX-512 Quality | Fortran 2018 | AMD Zen 5 | Production |
|----------|----------------|-------------|-----------|------------|
| gfortran 14+ | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ✅ Yes |
| ifx 2024+ | ★★★★★ | ★★★★★ | ★★★☆☆ | ✅ Yes |
| LFortran | ★★★☆☆ | ★★☆☆☆ | ★★★☆☆ | ❌ Experimental |
| NVFortran | ★★★★☆ | ★★★★☆ | ★★★★☆ | ✅ Yes |

**Recommendation**: Use `ifx` for development/benchmarking, `gfortran` for production (it's everywhere). Both generate AVX-512 from Fortran array syntax with `-O3`.

---

## 6. BLAS/LAPACK Lineage: Leveraging Linear Algebra

### Why This Matters for Constraint Checking

Constraint satisfaction often involves **linear inequality systems** (Ax ≤ b). These decompose into:
- Matrix-vector products (Ax) → **BLAS Level 2** (dgemv)
- Matrix-matrix products (A², AA^T) → **BLAS Level 3** (dgemm)
- Solving Ax = b → **LAPACK** (dgesv, dposv)
- Least-squares min ||Ax - b|| → **LAPACK** (dgels)

### AMD-Optimized BLAS

- **AOCL-BLAS** (AMD Optimizing C/C++ Compiler Library) — hand-tuned for Zen 5
- **BLIS** (BLAS-like Library Instantiation Software) — AMD-funded, Zen-optimized
- **OpenBLAS** — Has Zen 5 kernels since v0.3.26

### Fortran + BLAS for Constraint Matrices

```fortran
module constraint_matrix_ops
    use iso_c_binding
    implicit none

    ! External BLAS routines
    interface
        subroutine dgemm(transa, transb, m, n, k, alpha, a, lda, b, ldb, beta, c, ldc)
            import :: c_double
            character(1), intent(in) :: transa, transb
            integer, intent(in) :: m, n, k, lda, ldb, ldc
            real(c_double), intent(in) :: alpha, beta
            real(c_double), intent(in) :: a(lda,*), b(ldb,*)
            real(c_double), intent(inout) :: c(ldc,*)
        end subroutine
    end interface

contains

    ! Check all constraints: A*x <= b
    ! A is (nconstraints x nvars), x is (nvars), b is (nconstraints)
    function check_linear_constraints(A, x, b, nconstraints, nvars) result(valid)
        integer, intent(in) :: nconstraints, nvars
        real(8), intent(in) :: A(nconstraints, nvars)
        real(8), intent(in) :: x(nvars), b(nconstraints)
        logical :: valid

        real(8) :: Ax(nconstraints)
        integer :: i

        ! Matrix-vector product: Ax = A * x (BLAS Level 2)
        ! dgemv: y := alpha*A*x + beta*y
        call dgemv('N', nconstraints, nvars, 1.0d0, A, nconstraints, x, 1, 0.0d0, Ax, 1)

        ! Check: Ax <= b (vectorized comparison)
        valid = all(Ax <= b)
    end function

end module
```

### Performance Expectation

- `dgemm` on Zen 5 (single core): ~100 GFLOPS DP (AVX-512)
- `dgemv` on Zen 5: ~30 GB/s (memory-bound, not compute-bound)
- For constraint checking, `dgemv` is the relevant operation (matrix-vector)
- With AOCL-BLAS: expect 2-3x over reference BLAS for matrix operations

---

## 7. Legacy Fortran Tricks: Still Relevant?

### Computed GOTO → Replaced by SELECT CASE

```fortran
! Old (FORTRAN 77): computed GOTO
GOTO (100, 200, 300, 400), constraint_type

! New (Fortran 2003+): SELECT CASE
select case (constraint_type)
    case (1); call check_range_constraint(...)
    case (2); call check_linear_constraint(...)
    case (3); call check_domain_constraint(...)
    case (4); call check_bitmask_constraint(...)
end select
```

**Verdict**: SELECT CASE is cleaner and compilers generate jump tables from both. No performance difference.

### Arithmetic IF → Replaced by IF/THEN/ELSE

```fortran
! Old: arithmetic IF (3-way branch based on sign)
IF (value - threshold) 100, 200, 300

! New: explicit comparison
if (value < threshold) then
    ! handle below
else if (value == threshold) then
    ! handle equal
else
    ! handle above
end if
```

**Verdict**: Dead. Modern branch prediction makes explicit conditionals faster.

### EQUIVALENCE → Replaced by TRANSFER / UNION

```fortran
! Old: EQUIVALENCE for type punning
real(4) :: float_val
integer(4) :: int_val
EQUIVALENCE (float_val, int_val)

! New: TRANSFER intrinsic (type-safe)
int_val = transfer(float_val, int_val)
! Or: bit-to-float reinterpretation for NaN detection
```

**Verdict**: EQUIVALENCE is undefined behavior in modern Fortran. Use `TRANSFER` or `iso_c_binding` type punning.

### Still-Relevant Trick: Array Temporaries

```fortran
! Compiler creates stack temporaries for array expressions
! This is FAST because stack arrays are L1-cache resident
where (values >= lo .and. values <= hi)
    valid = .true.
elsewhere
    valid = .false.
end where
```

**This is still the #1 Fortran advantage**: The compiler can fuse, reorder, and vectorize array expressions without the programmer thinking about it.

### Still-Relevant Trick: Loop Column-Major Access

```fortran
! FAST: inner loop traverses columns (contiguous memory)
do j = 1, n
    do i = 1, m
        a(i,j) = a(i,j) + b(i,j)
    end do
end do

! SLOW: inner loop traverses rows (stride-m access)
do i = 1, m
    do j = 1, n
        a(i,j) = a(i,j) + b(i,j)  ! cache miss every access
    end do
end do
```

**This matters enormously** on Zen 5. L1D is 48KB, L2 is 1MB per core. Column-major = prefetcher-friendly = sustained AVX-512 throughput.

---

## 8. Fortran for Certification: DO-178C / DO-254

### Why NASA Still Uses Fortran

- **NASA NAIF SPICE toolkit** — 500K+ lines of Fortran, used by every deep-space mission
- **NASA FUN3D** — CFD code, Fortran + MPI, certified for flight analysis
- **NOAA weather models** — WRF, FV3, all Fortran, operational 24/7
- **DO-178C Level A** — Fortran compilers (ifx, gfortran with qualification kit) are certifiable

### Certification Advantages of Fortran

1. **No undefined behavior** — Fortran standard is more constrained than C. No pointer arithmetic, no integer overflow UB, no strict aliasing violations.
2. **Deterministic semantics** — Array operations have well-defined evaluation order (unlike C's sequence point rules).
3. **Mature qualification kits** — Intel Fortran has DO-178C qualification data. AdaCore has Fortran qualification via GNAT.
4. **Mathematical notation** — Fortran reads closer to the mathematical specification, reducing the gap between requirements and implementation (critical for traceability in DO-178C).
5. **No dynamic memory in safety-critical subsets** — Fortran's `allocatable` can be restricted to initialization-only, satisfying DO-178C memory management requirements.

### DO-178C Compliance Path

| Artifact | Fortran Advantage |
|----------|-------------------|
| **Requirements traceability** | Array syntax maps 1:1 to math specs |
| **Structural coverage (MC/DC)** | Simpler control flow → easier coverage analysis |
| **Coding standards** | No MISRA-Fortran needed (language is already constrained) |
| **Compiler qualification** | ifx has qualification data; gfortran via Adacore/QualKit |
| **Static analysis** | Fewer false positives (no UB, no pointer aliasing) |

### Our Certification Strategy

For constraint checking that needs DO-178C:
1. Write the constraint kernels in Fortran 2018 with `iso_c_binding`
2. Use `intent(in)`, `intent(out)`, `intent(inout)` on ALL arguments (enables static verification)
3. Use `pure` and `elemental` procedures where possible (enables compiler verification of side-effect freedom)
4. Wrap in Rust for the application layer (Rust's safety + Fortran's certified numerics)

---

## Summary: Why Fortran for Constraint Checking

| Factor | Fortran Advantage |
|--------|-------------------|
| **SIMD** | No pointer aliasing → guaranteed auto-vectorization |
| **Array syntax** | Portable SIMD without intrinsics |
| **BLAS/LAPACK** | Decades of optimized linear algebra, AMD-tuned |
| **Parallelism** | Coarrays (PGAS), OpenMP, or both |
| **C interop** | `iso_c_binding` + `ISO_Fortran_binding.h` — clean FFI |
| **Certification** | DO-178C path exists, no UB, mathematical notation |
| **Legacy wisdom** | Column-major, array temporaries, loop fusion — all still win |

### The Play

1. **Constraint kernels in Fortran** — auto-vectorized AVX-512, BLAS-accelerated
2. **Rust application layer** — memory safety, async I/O, ecosystem
3. **C FFI bridge** — `iso_c_binding` makes this trivial
4. **Python bindings** — via CFFI or ctypes to the C interface
4. **Compile with** `gfortran -O3 -march=znver5 -ffast-math -lblis` (or `-laocl-blas`)

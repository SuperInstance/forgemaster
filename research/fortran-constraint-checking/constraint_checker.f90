! constraint_checker.f90 — High-performance constraint checking module
! Target: AMD Zen 5, AVX-512, gfortran -O3 -march=znver5 -ffast-math
!
! Compile: gfortran -O3 -march=znver5 -ffast-math -c constraint_checker.f90
! Link with C: gcc -o main main.c constraint_checker.o -lgfortran -lm
!
! Forgemaster Research — 2026-05-03

module constraint_checker
    use iso_c_binding
    implicit none
    private

    ! Public API
    public :: check_range
    public :: check_bitmask
    public :: check_multi_constraint
    public :: count_in_range
    public :: domain_intersection
    public :: domain_union

    integer, parameter :: dp = c_double  ! double precision = 64-bit
    integer, parameter :: i64 = c_int64_t

contains

    ! =========================================================================
    ! Range check: values(1:n) in [lo, hi]
    ! Auto-vectorizes to vcmppd + vandpd (AVX-512)
    ! =========================================================================
    pure subroutine check_range(values, lo, hi, mask)
        real(dp), intent(in)  :: values(:)
        real(dp), intent(in)  :: lo, hi
        logical,  intent(out) :: mask(:)

        mask = (values >= lo) .and. (values <= hi)
    end subroutine check_range

    ! =========================================================================
    ! Count values in range — returns count without allocating mask
    ! Uses count() intrinsic — compiler emits vpcmpq + vpopcntdq
    ! =========================================================================
    pure function count_in_range(values, lo, hi) result(n)
        real(dp), intent(in) :: values(:)
        real(dp), intent(in) :: lo, hi
        integer  :: n

        n = count(values >= lo .and. values <= hi)
    end function count_in_range

    ! =========================================================================
    ! Bitmask domain operations
    ! Each int64 represents a 64-bit domain (each bit = one constraint dimension)
    ! =========================================================================
    pure subroutine check_bitmask(domains, mask_bits, result)
        integer(i64), intent(in)  :: domains(:)
        integer(i64), intent(in)  :: mask_bits
        integer(i64), intent(out) :: result(:)

        result = iand(domains, mask_bits)
    end subroutine check_bitmask

    ! Domain intersection: bitwise AND across multiple domain arrays
    pure function domain_intersection(domains, n_domains) result(intersection)
        integer(i64), intent(in) :: domains(:,:)
        integer,      intent(in) :: n_domains
        integer(i64), allocatable :: intersection(:)
        integer :: j

        intersection = domains(:, 1)
        do j = 2, n_domains
            intersection = iand(intersection, domains(:, j))
        end do
    end function domain_intersection

    ! Domain union: bitwise OR across multiple domain arrays
    pure function domain_union(domains, n_domains) result(union)
        integer(i64), intent(in) :: domains(:,:)
        integer,      intent(in) :: n_domains
        integer(i64), allocatable :: union(:)
        integer :: j

        union = domains(:, 1)
        do j = 2, n_domains
            union = ior(union, domains(:, j))
        end do
    end function domain_union

    ! =========================================================================
    ! Multi-constraint AND evaluation
    ! Checks values against multiple [lo(j), hi(j)] ranges simultaneously
    ! Uses array syntax + forall for auto-vectorization
    ! =========================================================================
    pure subroutine check_multi_constraint(values, lo, hi, result_mask)
        real(dp), intent(in)  :: values(:)      ! n values
        real(dp), intent(in)  :: lo(:)          ! m constraint lower bounds
        real(dp), intent(in)  :: hi(:)          ! m constraint upper bounds
        logical,  intent(out) :: result_mask(:) ! n results

        logical, allocatable :: temp(:)
        integer :: j

        ! Initialize all valid
        result_mask = .true.

        ! AND each constraint into the result
        do j = 1, size(lo)
            temp = (values >= lo(j)) .and. (values <= hi(j))
            result_mask = result_mask .and. temp
        end do
    end subroutine check_multi_constraint

end module constraint_checker


! =============================================================================
! C-interoperable wrapper module
! All functions use bind(C) for calling from C, Rust, Python
! =============================================================================
module constraint_checker_c
    use iso_c_binding
    use constraint_checker
    implicit none

contains

    ! C API: check_range_f64(values, &n, &lo, &hi, mask)
    subroutine check_range_f64(values, n, lo, hi, mask) bind(C, name='check_range_f64')
        real(c_double), intent(in)  :: values(*)
        integer(c_int), intent(in), value :: n
        real(c_double), intent(in), value :: lo, hi
        logical(c_bool), intent(out) :: mask(*)

        logical, allocatable :: fmask(:)
        allocate(fmask(n))
        call check_range(values(1:n), lo, hi, fmask)
        mask(1:n) = fmask  ! logical → c_bool conversion
    end subroutine check_range_f64

    ! C API: count_in_range_f64(values, &n, &lo, &hi) → count
    function count_in_range_f64(values, n, lo, hi) result(count) &
        bind(C, name='count_in_range_f64')
        real(c_double), intent(in) :: values(*)
        integer(c_int), intent(in), value :: n
        real(c_double), intent(in), value :: lo, hi
        integer(c_int) :: count

        count = count_in_range(values(1:n), lo, hi)
    end function count_in_range_f64

    ! C API: check_bitmask_i64(domains, &n, mask_bits, result)
    subroutine check_bitmask_i64(domains, n, mask_bits, result) &
        bind(C, name='check_bitmask_i64')
        integer(c_int64_t), intent(in)  :: domains(*)
        integer(c_int), intent(in), value :: n
        integer(c_int64_t), intent(in), value :: mask_bits
        integer(c_int64_t), intent(out) :: result(*)

        call check_bitmask(domains(1:n), mask_bits, result(1:n))
    end subroutine check_bitmask_i64

    ! C API: check_multi_f64(values, &n, lo, hi, &m, result_mask)
    ! n values, m constraints, lo/hi are m-element arrays
    subroutine check_multi_f64(values, n, lo, hi, m, result_mask) &
        bind(C, name='check_multi_f64')
        real(c_double), intent(in)  :: values(*)
        integer(c_int), intent(in), value :: n
        real(c_double), intent(in)  :: lo(*), hi(*)
        integer(c_int), intent(in), value :: m
        logical(c_bool), intent(out) :: result_mask(*)

        logical, allocatable :: fresult(:)
        allocate(fresult(n))
        call check_multi_constraint(values(1:n), lo(1:m), hi(1:m), fresult)
        result_mask(1:n) = fresult
    end subroutine check_multi_f64

end module constraint_checker_c


! =============================================================================
! Benchmark program
! Compile: gfortran -O3 -march=znver5 -ffast-math -o bench bench_constraint.f90
! =============================================================================
program bench_constraint
    use iso_c_binding
    use constraint_checker
    implicit none

    integer, parameter :: N = 10000000  ! 10M values
    integer, parameter :: NCONSTRAINTS = 5
    real(c_double), allocatable :: values(:), lo(:), hi(:)
    logical, allocatable :: mask(:), multi_mask(:)
    integer(c_int64_t), allocatable :: domains(:), dresult(:)
    integer :: i, cnt
    real :: t_start, t_end
    integer(c_int64_t) :: all_bits

    ! ---- Allocate and initialize ----
    allocate(values(N), mask(N), multi_mask(N))
    allocate(lo(NCONSTRAINTS), hi(NCONSTRAINTS))
    allocate(domains(N), dresult(N))

    call random_seed()
    call random_number(values)  ! [0, 1)
    lo = [0.1_c_double, 0.2_c_double, 0.3_c_double, 0.05_c_double, 0.15_c_double]
    hi = [0.9_c_double, 0.8_c_double, 0.7_c_double, 0.95_c_double, 0.85_c_double]

    ! Initialize domains with random bit patterns
    do i = 1, N
        domains(i) = transfer(values(i), domains(i))
    end do
    all_bits = -1_c_int64_t  ! all bits set

    ! ---- Benchmark 1: Range check ----
    call cpu_time(t_start)
    do i = 1, 100
        call check_range(values, 0.0_c_double, 1.0_c_double, mask)
    end do
    call cpu_time(t_end)
    cnt = count(mask)
    print '(A,I8,A,F10.3,A)', 'Range check: ', cnt, ' valid, time: ', t_end - t_start, 's x100'

    ! ---- Benchmark 2: Count in range ----
    call cpu_time(t_start)
    do i = 1, 100
        cnt = count_in_range(values, 0.0_c_double, 1.0_c_double)
    end do
    call cpu_time(t_end)
    print '(A,I8,A,F10.3,A)', 'Count in range: ', cnt, ' valid, time: ', t_end - t_start, 's x100'

    ! ---- Benchmark 3: Multi-constraint AND ----
    call cpu_time(t_start)
    do i = 1, 100
        call check_multi_constraint(values, lo, hi, multi_mask)
    end do
    call cpu_time(t_end)
    cnt = count(multi_mask)
    print '(A,I3,A,I8,A,F10.3,A)', 'Multi-constraint (', NCONSTRAINTS, '): ', cnt, ' valid, time: ', t_end - t_start, 's x100'

    ! ---- Benchmark 4: Bitmask ----
    call cpu_time(t_start)
    do i = 1, 100
        call check_bitmask(domains, all_bits, dresult)
    end do
    call cpu_time(t_end)
    print '(A,F10.3,A)', 'Bitmask AND: time: ', t_end - t_start, 's x100'

    deallocate(values, mask, multi_mask, lo, hi, domains, dresult)
end program bench_constraint

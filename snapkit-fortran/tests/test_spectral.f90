program test_spectral
    use snapkit_spectral
    implicit none

    integer :: failures, total
    failures = 0
    total = 0

    call test_entropy_uniform(failures, total)
    call test_entropy_constant(failures, total)
    call test_entropy_two_values(failures, total)
    call test_autocorrelation_white_noise(failures, total)
    call test_autocorrelation_constant(failures, total)
    call test_autocorrelation_lag0_is_1(failures, total)
    call test_hurst_random(failures, total)
    call test_hurst_short(failures, total)
    call test_spectral_summary(failures, total)
    call test_batch(failures, total)

    print '(A,I0,A,I0,A)', "Spectral tests: ", total - failures, &
        "/", total, " passed"
    if (failures > 0) then
        print '(A)', "FAILURES detected!"
        stop 1
    end if

contains

    subroutine check(name, condition, failures, total)
        character(len=*), intent(in) :: name
        logical, intent(in) :: condition
        integer, intent(inout) :: failures, total
        total = total + 1
        if (.not. condition) then
            failures = failures + 1
            print '(A,A)', "  FAIL: ", name
        else
            print '(A,A)', "  PASS: ", name
        end if
    end subroutine

    subroutine approx_check(name, val, expected, tol, failures, total)
        character(len=*), intent(in) :: name
        real(8), intent(in) :: val, expected, tol
        integer, intent(inout) :: failures, total
        total = total + 1
        if (abs(val - expected) > tol) then
            failures = failures + 1
            print '(A,A,ES12.4,A,ES12.4)', "  FAIL: ", name, val, " != ", expected
        else
            print '(A,A)', "  PASS: ", name
        end if
    end subroutine

    ! Simple LCG pseudo-random generator
    function lcg(seed) result(r)
        integer, intent(inout) :: seed
        real(8) :: r
        seed = mod(seed * 1103515245 + 12345, 2147483647)
        r = dble(seed) / 2147483647.0d0
    end function

    subroutine test_entropy_uniform(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(100), h
        integer :: i, seed

        seed = 42
        do i = 1, 100
            vals(i) = lcg(seed) * 100.0d0
        end do
        h = entropy(vals, 10)
        call check("entropy uniform > 2.5", h > 2.5d0, f, t)
        call check("entropy uniform < 4.0", h < 4.0d0, f, t)
    end subroutine

    subroutine test_entropy_constant(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(50)
        real(8) :: h
        vals = 42.0d0
        h = entropy(vals, 10)
        call approx_check("entropy constant = 0", h, 0.0d0, 1.0d-12, f, t)
    end subroutine

    subroutine test_entropy_two_values(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(100)
        real(8) :: h
        integer :: i
        do i = 1, 100
            if (mod(i, 2) == 0) then
                vals(i) = 0.0d0
            else
                vals(i) = 1.0d0
            end if
        end do
        h = entropy(vals, 10)
        call approx_check("entropy binary ~ 1 bit", h, 1.0d0, 0.3d0, f, t)
    end subroutine

    subroutine test_autocorrelation_white_noise(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(1000)
        real(8), allocatable :: acf(:)
        integer :: i, seed

        seed = 123
        do i = 1, 1000
            vals(i) = lcg(seed)
        end do
        acf = autocorrelation(vals, 20)
        call check("acf size", size(acf) == 21, f, t)
        call approx_check("acf lag0 = 1.0", acf(1), 1.0d0, 1.0d-9, f, t)
        call check("acf lag1 < 0.5", abs(acf(2)) < 0.5d0, f, t)
    end subroutine

    subroutine test_autocorrelation_constant(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(50)
        real(8), allocatable :: acf(:)

        vals = 5.0d0
        acf = autocorrelation(vals, 10)
        call approx_check("acf constant lag0", acf(1), 1.0d0, 1.0d-9, f, t)
        if (size(acf) > 1) then
            call approx_check("acf constant lag1", acf(2), 0.0d0, 1.0d-9, f, t)
        end if
    end subroutine

    subroutine test_autocorrelation_lag0_is_1(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(100)
        real(8), allocatable :: acf(:)
        integer :: i

        vals = [(dble(i), i = 1, 100)]
        acf = autocorrelation(vals, 10)
        call approx_check("acf lag0 always 1", acf(1), 1.0d0, 1.0d-9, f, t)
    end subroutine

    subroutine test_hurst_random(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(500)
        real(8) :: h
        integer :: i, seed

        seed = 456
        do i = 1, 500
            vals(i) = lcg(seed)
        end do
        h = hurst_exponent(vals)
        call check("hurst random in [0.2, 0.8]", h >= 0.2d0 .and. h <= 0.8d0, f, t)
    end subroutine

    subroutine test_hurst_short(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(5)
        real(8) :: h
        vals = [1.0d0, 2.0d0, 3.0d0, 4.0d0, 5.0d0]
        h = hurst_exponent(vals)
        call approx_check("hurst short = 0.5", h, 0.5d0, 1.0d-12, f, t)
    end subroutine

    subroutine test_spectral_summary(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals(200)
        type(spectral_result) :: sr
        integer :: i, seed

        seed = 789
        do i = 1, 200
            vals(i) = lcg(seed)
        end do
        sr = spectral_summary(vals)
        call check("summary has entropy", sr%entropy_bits > 0.0d0, f, t)
        call check("summary hurst in [0,1]", &
            sr%hurst >= 0.0d0 .and. sr%hurst <= 1.0d0, f, t)
        call check("summary lag1 in [-1,1]", &
            abs(sr%autocorr_lag1) <= 1.0d0, f, t)
    end subroutine

    subroutine test_batch(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vals_2d(200, 3)
        type(spectral_result) :: results(3)
        integer :: i, j, seed

        seed = 101
        do j = 1, 3
            do i = 1, 200
                vals_2d(i, j) = lcg(seed)
            end do
        end do
        call spectral_batch(vals_2d, results)
        call check("batch size = 3", size(results) == 3, f, t)
        do j = 1, 3
            call check("batch entropy > 0", results(j)%entropy_bits > 0.0d0, f, t)
        end do
    end subroutine

end program test_spectral

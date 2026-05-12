! Validate snapkit-fortran implementation against the test corpus.
! Build: gfortran validate_fortran.f90 -o validate_fortran && ./validate_fortran

program validate_fortran
    implicit none

    integer, parameter :: dp = selected_real_kind(15, 307)
    integer, parameter :: MAX_CASES = 1024

    real(dp), parameter :: SQRT3 = 1.7320508075688772_dp
    real(dp), parameter :: COVERING_RADIUS = 1.0_dp / SQRT3

    type :: TestCase
        integer :: id
        real(dp) :: x, y
        integer :: exp_a, exp_b
        real(dp) :: snap_error_val, snap_error_max
    end type

    type(TestCase) :: cases(MAX_CASES)
    integer :: n_cases, i, a, b, passed, failed
    real(dp) :: err
    logical :: ok

    call parse_corpus("corpus/snap_corpus.json", cases, n_cases)

    if (n_cases <= 0) then
        print *, "ERROR: No cases parsed from corpus"
        stop 1
    end if

    passed = 0
    failed = 0

    do i = 1, n_cases
        call eisenstein_snap(cases(i)%x, cases(i)%y, a, b)
        err = snap_error(cases(i)%x, cases(i)%y, a, b)

        ok = .true.
        if (a /= cases(i)%exp_a) then
            print '(A,I0,A,I0,A,I0)', "Case ", cases(i)%id, ": a=", a, " expected=", cases(i)%exp_a
            ok = .false.
        end if
        if (b /= cases(i)%exp_b) then
            print '(A,I0,A,I0,A,I0)', "Case ", cases(i)%id, ": b=", b, " expected=", cases(i)%exp_b
            ok = .false.
        end if
        if (err > cases(i)%snap_error_max + 1.0e-10_dp) then
            print '(A,I0,A,F12.8,A,F12.8)', "Case ", cases(i)%id, ": snap_error=", err, " > max=", cases(i)%snap_error_max
            ok = .false.
        end if

        if (ok) then
            passed = passed + 1
        else
            failed = failed + 1
        end if
    end do

    print '(A,I0,A,I0,A,I0)', "Results: ", passed, "/", n_cases, " passed, ", failed, " failed"

    if (failed == 0) then
        print *, "All cases passed ✓"
    else
        stop 1
    end if

contains

    function snap_error(x, y, a, b) result(dist)
        real(dp), intent(in) :: x, y
        integer, intent(in) :: a, b
        real(dp) :: dist
        real(dp) :: lx, ly

        lx = real(a, dp) - real(b, dp) / 2.0_dp
        ly = real(b, dp) * SQRT3 / 2.0_dp
        dist = sqrt((x - lx)**2 + (y - ly)**2)
    end function

    subroutine eisenstein_snap(x, y, out_a, out_b)
        real(dp), intent(in) :: x, y
        integer, intent(out) :: out_a, out_b

        real(dp) :: b_float, a_float, best_err, err
        integer :: a_lo, b_lo, best_a, best_b, ca, cb, da, db

        b_float = 2.0_dp * y / SQRT3
        a_float = x + y / SQRT3

        a_lo = floor(a_float)
        b_lo = floor(b_float)

        best_a = 0
        best_b = 0
        best_err = huge(1.0_dp)

        ! Check 4 floor/ceil candidates
        do da = 0, 1
            do db = 0, 1
                ca = a_lo + da
                cb = b_lo + db
                err = snap_error(x, y, ca, cb)
                if (err < best_err - 1.0e-15_dp) then
                    best_a = ca; best_b = cb; best_err = err
                else if (abs(err - best_err) < 1.0e-15_dp) then
                    if (ca < best_a .or. (ca == best_a .and. cb < best_b)) then
                        best_a = ca; best_b = cb
                    end if
                end if
            end do
        end do

        ! Check ±1 neighborhood
        do da = -1, 1
            do db = -1, 1
                ca = best_a + da
                cb = best_b + db
                err = snap_error(x, y, ca, cb)
                if (err < best_err - 1.0e-15_dp) then
                    best_a = ca; best_b = cb; best_err = err
                else if (abs(err - best_err) < 1.0e-15_dp) then
                    if (ca < best_a .or. (ca == best_a .and. cb < best_b)) then
                        best_a = ca; best_b = cb
                    end if
                end if
            end do
        end do

        out_a = best_a
        out_b = best_b
    end subroutine

    subroutine parse_corpus(filename, cases, n)
        character(len=*), intent(in) :: filename
        type(TestCase), intent(out) :: cases(*)
        integer, intent(out) :: n

        character(len=10000000) :: buffer
        character(len=:), allocatable :: data
        integer :: unit_num, ios, i, fsize
        character(len=256) :: tmp

        open(newunit=unit_num, file=filename, status='old', action='read', iostat=ios)
        if (ios /= 0) then
            print *, "Cannot open ", trim(filename)
            n = 0
            return
        end if

        ! Read entire file
        buffer = ''
        do
            read(unit_num, '(A)', iostat=ios) tmp
            if (ios /= 0) exit
            buffer = trim(buffer) // trim(tmp)
        end do
        close(unit_num)
        data = trim(buffer)

        n = 0
        ! Simple JSON parsing - find each case
        i = 1
        do while (i <= len(data) .and. n < MAX_CASES)
            ! Look for "id":
            i = index(data(i:), '"id"')
            if (i == 0) exit
            i = i + 3  ! skip past "id"

            n = n + 1
            ! Parse values using internal reads
            ! This is a simplified parser - in production use a JSON library
            cases(n)%id = n  ! fallback
            cases(n)%x = 0.0_dp
            cases(n)%y = 0.0_dp
            cases(n)%exp_a = 0
            cases(n)%exp_b = 0
        end do

        ! Note: Full JSON parsing in Fortran requires a library like json-fortran.
        ! This skeleton shows the structure. For production use:
        !   pip install json-fortran or use fson
        print *, "Note: Fortran JSON parser requires json-fortran library."
        print *, "Using Python to generate a binary corpus file instead..."

        ! Alternative: read a pre-converted binary format
        call parse_binary_corpus(cases, n)
    end subroutine

    subroutine parse_binary_corpus(cases, n)
        type(TestCase), intent(out) :: cases(*)
        integer, intent(out) :: n

        integer :: unit_num, ios, i
        integer :: id, exp_a, exp_b
        real(dp) :: x, y, se, sem

        open(newunit=unit_num, file="corpus/snap_corpus.bin", &
             form='unformatted', access='stream', status='old', iostat=ios)

        if (ios /= 0) then
            print *, "Cannot open corpus/snap_corpus.bin"
            print *, "Run: python3 convert_corpus.py to generate binary format"
            n = 0
            return
        end if

        n = 0
        do
            read(unit_num, iostat=ios) id, x, y, exp_a, exp_b, se, sem
            if (ios /= 0) exit
            n = n + 1
            cases(n)%id = id
            cases(n)%x = x
            cases(n)%y = y
            cases(n)%exp_a = exp_a
            cases(n)%exp_b = exp_b
            cases(n)%snap_error_val = se
            cases(n)%snap_error_max = sem
        end do

        close(unit_num)
    end subroutine

end program

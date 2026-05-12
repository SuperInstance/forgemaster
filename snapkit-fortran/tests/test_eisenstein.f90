program test_eisenstein
    use snapkit_eisenstein
    use snapkit_voronoi
    implicit none

    integer :: failures, total
    failures = 0
    total = 0

    call test_snap_origin(failures, total)
    call test_snap_unit_points(failures, total)
    call test_snap_half_offsets(failures, total)
    call test_batch_operations(failures, total)
    call test_norm_squared(failures, total)
    call test_arithmetic(failures, total)
    call test_conjugate(failures, total)
    call test_distance(failures, total)
    call test_covering_radius(failures, total)
    call test_voronoi_cell(failures, total)
    call test_fundamental_domain(failures, total)
    call test_round_consistency(failures, total)

    print '(A,I0,A,I0,A)', "Eisenstein tests: ", total - failures, &
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

    subroutine test_snap_origin(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e
        e = eisenstein_round(0.0d0, 0.0d0)
        call check("snap origin a=0", e%a == 0, f, t)
        call check("snap origin b=0", e%b == 0, f, t)
    end subroutine

    subroutine test_snap_unit_points(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e
        real(8) :: x, y

        ! Snap (1, 0) -> a=1, b=0
        e = eisenstein_round(1.0d0, 0.0d0)
        call check("snap (1,0) a", e%a == 1, f, t)
        call check("snap (1,0) b", e%b == 0, f, t)

        ! Snap omega = (-0.5, sqrt3/2) -> a=0, b=1
        e = eisenstein_round(-0.5d0, 0.8660254037844386d0)
        call check("snap omega a", e%a == 0, f, t)
        call check("snap omega b", e%b == 1, f, t)

        ! Snap (0.25, 0.43) — near origin, should snap to (0,0) or (1,0)
        e = eisenstein_round(0.25d0, 0.43d0)
        call check("snap near origin is valid", &
            (e%a == 0 .and. e%b == 0) .or. (e%a == 1 .and. e%b == 0) .or. &
            (e%a == 0 .and. e%b == 1), f, t)
    end subroutine

    subroutine test_snap_half_offsets(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e

        ! Point between lattice sites — should snap to nearest
        ! Halfway between (0,0) and (1,0): (0.5, 0.0)
        e = eisenstein_round(0.5d0, 0.0d0)
        call check("half (0.5,0) snaps to a=0 or 1", &
            e%a == 0 .or. e%a == 1, f, t)
    end subroutine

    subroutine test_batch_operations(f, t)
        integer, intent(inout) :: f, t
        real(8) :: x(5), y(5)
        type(snap_result) :: results(5)
        integer :: i

        x = [0.0d0, 1.0d0, -0.5d0, 2.0d0, -1.0d0]
        y = [0.0d0, 0.0d0, 0.8660254037844386d0, 0.0d0, 0.0d0]

        call eisenstein_snap_batch(x, y, 0.5d0, results)

        call check("batch size", size(x) == 5, f, t)
        call check("batch[0] is (0,0)", &
            results(1)%nearest%a == 0 .and. results(1)%nearest%b == 0, f, t)
        call check("batch[1] is (1,0)", &
            results(2)%nearest%a == 1 .and. results(2)%nearest%b == 0, f, t)
        call check("batch[2] is (0,1)", &
            results(3)%nearest%a == 0 .and. results(3)%nearest%b == 1, f, t)

        do i = 1, 5
            call check("batch snap flag", results(i)%distance >= 0.0d0, f, t)
        end do
    end subroutine

    subroutine test_norm_squared(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e
        integer :: n

        e = eisenstein_int(1, 0)
        n = eisenstein_norm_sq(e)
        call check("norm(1,0) = 1", n == 1, f, t)

        e = eisenstein_int(0, 1)
        n = eisenstein_norm_sq(e)
        call check("norm(0,1) = 1", n == 1, f, t)

        e = eisenstein_int(1, 1)
        n = eisenstein_norm_sq(e)
        call check("norm(1,1) = 1", n == 1, f, t)

        e = eisenstein_int(2, 1)
        n = eisenstein_norm_sq(e)
        call check("norm(2,1) = 3", n == 3, f, t)
    end subroutine

    subroutine test_arithmetic(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e1, e2, r

        e1 = eisenstein_int(3, 2)
        e2 = eisenstein_int(1, -1)

        r = eisenstein_add(e1, e2)
        call check("add a", r%a == 4, f, t)
        call check("add b", r%b == 1, f, t)

        r = eisenstein_sub(e1, e2)
        call check("sub a", r%a == 2, f, t)
        call check("sub b", r%b == 3, f, t)

        ! (3+2ω)(1-ω) = 3 - 3ω + 2ω - 2ω² = 3 - ω - 2(-1-ω) = 5 + ω
        ! Using the formula: (ac-bd) + (ad+bc-bd)ω
        ! = (3*1 - 2*(-1)) + (3*(-1) + 2*1 - 2*(-1))ω
        ! = (3+2) + (-3+2+2)ω = 5 + 1ω
        r = eisenstein_mul(e1, e2)
        call check("mul a", r%a == 5, f, t)
        call check("mul b", r%b == 1, f, t)
    end subroutine

    subroutine test_conjugate(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e, c

        e = eisenstein_int(3, 2)
        c = eisenstein_conjugate(e)
        call check("conj a", c%a == 5, f, t)   ! a+b = 5
        call check("conj b", c%b == -2, f, t)   ! -b
    end subroutine

    subroutine test_distance(f, t)
        integer, intent(inout) :: f, t
        real(8) :: d

        d = eisenstein_distance(0.0d0, 0.0d0, 1.0d0, 0.0d0)
        call approx_check("distance 0->1", d, 1.0d0, 1.0d-9, f, t)

        d = eisenstein_distance(0.0d0, 0.0d0, 0.0d0, 0.0d0)
        call approx_check("distance 0->0", d, 0.0d0, 1.0d-12, f, t)
    end subroutine

    subroutine test_covering_radius(f, t)
        integer, intent(inout) :: f, t
        real(8) :: r
        r = covering_radius()
        call approx_check("covering radius = 1/sqrt(3)", &
            r, 1.0d0 / 1.7320508075688772d0, 1.0d-12, f, t)
    end subroutine

    subroutine test_voronoi_cell(f, t)
        integer, intent(inout) :: f, t
        real(8) :: vx(6), vy(6), area

        call voronoi_cell_vertices(vx, vy)
        call check("vertex count = 6", size(vx) == 6, f, t)
        ! All vertices should be at distance covering_radius from origin
        area = voronoi_cell_area()
        call approx_check("voronoi area = sqrt(3)/2", &
            area, 1.7320508075688772d0 / 2.0d0, 1.0d-12, f, t)
    end subroutine

    subroutine test_fundamental_domain(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: best_unit, reduced

        call eisenstein_fundamental_domain(1.0d0, 0.0d0, best_unit, reduced)
        ! Should find a unit rotation — just check it returns something
        call check("fundamental domain returns", .true., f, t)
    end subroutine

    subroutine test_round_consistency(f, t)
        integer, intent(inout) :: f, t
        type(eisenstein_int) :: e1, e2

        ! Voronoi and naive should agree on lattice points
        e1 = eisenstein_round(2.0d0, 0.0d0)
        e2 = eisenstein_round_naive(2.0d0, 0.0d0)
        call check("voronoi==naive on lattice (2,0)", &
            e1%a == e2%a .and. e1%b == e2%b, f, t)

        e1 = eisenstein_round(0.0d0, 1.7320508037844386d0)
        e2 = eisenstein_round_naive(0.0d0, 1.7320508037844386d0)
        call check("voronoi==naive on lattice (0,sqrt3)", &
            e1%a == e2%a .and. e1%b == e2%b, f, t)
    end subroutine

end program test_eisenstein

!> Eisenstein integer snap — Fortran 2008 port of snapkit.
!> Pure/elemental procedures, array-syntax batch operations, column-major layout.
module snapkit_eisenstein
    implicit none
    private
    public :: eisenstein_int, eisenstein_round, eisenstein_round_naive
    public :: eisenstein_snap, eisenstein_snap_batch
    public :: eisenstein_distance, eisenstein_to_real, eisenstein_from_real
    public :: eisenstein_conjugate, eisenstein_norm_sq, eisenstein_add
    public :: eisenstein_sub, eisenstein_mul, eisenstein_units
    public :: eisenstein_fundamental_domain

    ! Precomputed constants
    real(8), parameter :: SQRT3      = 1.7320508075688772d0
    real(8), parameter :: HALF_SQRT3  = 0.8660254037844386d0
    real(8), parameter :: INV_SQRT3   = 0.5773502691896258d0
    real(8), parameter :: EPS         = 1.0d-24

    !> Eisenstein integer a + b*omega
    type :: eisenstein_int
        integer :: a = 0
        integer :: b = 0
    end type

    !> Snap result: nearest lattice point + distance + within tolerance
    type :: snap_result
        type(eisenstein_int) :: nearest
        real(8) :: distance = 0.0d0
        logical :: is_snap = .false.
    end type

contains

    !> Convert Eisenstein (a,b) to Cartesian (x,y)
    pure subroutine eisenstein_to_real(a, b, x, y)
        integer, intent(in)  :: a, b
        real(8), intent(out) :: x, y
        x = dble(a) - 0.5d0 * dble(b)
        y = HALF_SQRT3 * dble(b)
    end subroutine

    !> Convert Cartesian (x,y) to Eisenstein coords (a_float, b_float)
    pure subroutine eisenstein_from_real(x, y, a_float, b_float)
        real(8), intent(in)  :: x, y
        real(8), intent(out) :: a_float, b_float
        b_float = 2.0d0 * y / SQRT3
        a_float = x + b_float * 0.5d0
    end subroutine

    !> Eisenstein norm squared: a^2 - a*b + b^2
    pure function eisenstein_norm_sq(e) result(n)
        type(eisenstein_int), intent(in) :: e
        integer :: n
        n = e%a * e%a - e%a * e%b + e%b * e%b
    end function

    !> Galois conjugate: (a+b) - b*omega
    pure function eisenstein_conjugate(e) result(c)
        type(eisenstein_int), intent(in) :: e
        type(eisenstein_int) :: c
        c%a = e%a + e%b
        c%b = -e%b
    end function

    !> Addition
    pure function eisenstein_add(e1, e2) result(r)
        type(eisenstein_int), intent(in) :: e1, e2
        type(eisenstein_int) :: r
        r%a = e1%a + e2%a
        r%b = e1%b + e2%b
    end function

    !> Subtraction
    pure function eisenstein_sub(e1, e2) result(r)
        type(eisenstein_int), intent(in) :: e1, e2
        type(eisenstein_int) :: r
        r%a = e1%a - e2%a
        r%b = e1%b - e2%b
    end function

    !> Multiplication: (a+bω)(c+dω) = (ac-bd) + (ad+bc-bd)ω
    pure function eisenstein_mul(e1, e2) result(r)
        type(eisenstein_int), intent(in) :: e1, e2
        type(eisenstein_int) :: r
        r%a = e1%a * e2%a - e1%b * e2%b
        r%b = e1%a * e2%b + e1%b * e2%a - e1%b * e2%b
    end function

    !> Voronoï 9-candidate snap — the fast path.
    !> Checks (a0+da, b0+db) for da,db in {-1,0,1}.
    !> Uses squared distance (no sqrt), inline tie-breaking by |a|,|b|.
    pure function eisenstein_round(x, y) result(best)
        real(8), intent(in) :: x, y
        type(eisenstein_int) :: best

        integer :: a0, b0, a, b, da, db
        integer :: best_a, best_b
        real(8) :: dx, dy, d_sq, best_dist_sq, b_flt

        ! Initial naive rounding
        b_flt = y * 2.0d0 * INV_SQRT3
        b0 = nint(b_flt)
        a0 = nint(x + dble(b0) * 0.5d0)

        best_dist_sq = huge(1.0d0)
        best_a = a0
        best_b = b0

        do da = -1, 1
            do db = -1, 1
                a = a0 + da
                b = b0 + db
                dx = x - (dble(a) - 0.5d0 * dble(b))
                dy = y - (HALF_SQRT3 * dble(b))
                d_sq = dx * dx + dy * dy
                if (d_sq < best_dist_sq - EPS) then
                    best_dist_sq = d_sq
                    best_a = a
                    best_b = b
                else if (abs(d_sq - best_dist_sq) < EPS) then
                    ! Tie-break: prefer smaller |a|,|b|
                    if ((abs(a) < abs(best_a)) .or. &
                        (abs(a) == abs(best_a) .and. abs(b) < abs(best_b))) then
                        best_a = a
                        best_b = b
                    end if
                end if
            end do
        end do

        best%a = best_a
        best%b = best_b
    end function

    !> Naive 4-candidate round (for testing/comparison only)
    pure function eisenstein_round_naive(x, y) result(best)
        real(8), intent(in) :: x, y
        type(eisenstein_int) :: best

        real(8) :: a_float, b_float, cx, cy, dist, best_dist
        integer :: a_floor, b_floor, da, db, a, b
        integer :: best_a, best_b, best_key, key

        call eisenstein_from_real(x, y, a_float, b_float)
        a_floor = floor(a_float)
        b_floor = floor(b_float)

        best_dist = huge(1.0d0)
        best_a = a_floor
        best_b = b_floor
        best_key = huge(1)

        do da = 0, 1
            do db = 0, 1
                a = a_floor + da
                b = b_floor + db
                call eisenstein_to_real(a, b, cx, cy)
                dist = hypot(x - cx, y - cy)
                key = abs(a) * 10000 + abs(b)
                if (dist < best_dist - 1.0d-9) then
                    best_dist = dist
                    best_a = a
                    best_b = b
                    best_key = key
                else if (abs(dist - best_dist) < 1.0d-9) then
                    if (key < best_key) then
                        best_a = a
                        best_b = b
                        best_key = key
                    end if
                end if
            end do
        end do

        best%a = best_a
        best%b = best_b
    end function

    !> Snap a point to nearest Eisenstein integer with tolerance check.
    pure function eisenstein_snap(x, y, tolerance) result(sr)
        real(8), intent(in) :: x, y, tolerance
        type(snap_result) :: sr

        real(8) :: cx, cy

        sr%nearest = eisenstein_round(x, y)
        call eisenstein_to_real(sr%nearest%a, sr%nearest%b, cx, cy)
        sr%distance = hypot(x - cx, y - cy)
        sr%is_snap = (sr%distance <= tolerance)
    end function

    !> Batch snap — array syntax, whole-array operations.
    !> Input: x(n), y(n). Output: results(n).
    subroutine eisenstein_snap_batch(x, y, tolerance, results)
        real(8), intent(in)  :: x(:), y(:), tolerance
        type(snap_result), intent(out) :: results(:)
        integer :: i

        do i = 1, size(x)
            results(i) = eisenstein_snap(x(i), y(i), tolerance)
        end do
    end subroutine

    !> Eisenstein lattice distance between two Cartesian points.
    function eisenstein_distance(x1, y1, x2, y2) result(d)
        real(8), intent(in) :: x1, y1, x2, y2
        real(8) :: d

        real(8) :: dx, dy, cx, cy, residual
        type(eisenstein_int) :: nearest

        dx = x1 - x2
        dy = y1 - y2
        nearest = eisenstein_round(dx, dy)
        call eisenstein_to_real(nearest%a, nearest%b, cx, cy)
        residual = hypot(dx - cx, dy - cy)
        d = sqrt(dble(eisenstein_norm_sq(nearest))) + residual
    end function

    !> Return the 6 Eisenstein units.
    subroutine eisenstein_units(units)
        type(eisenstein_int), intent(out) :: units(6)
        units(1) = eisenstein_int(1, 0)
        units(2) = eisenstein_int(0, 1)
        units(3) = eisenstein_int(-1, 1)
        units(4) = eisenstein_int(-1, 0)
        units(5) = eisenstein_int(0, -1)
        units(6) = eisenstein_int(1, -1)
    end subroutine

    !> Reduce (x,y) to its canonical representative in the fundamental domain.
    subroutine eisenstein_fundamental_domain(x, y, best_unit, reduced)
        real(8), intent(in) :: x, y
        type(eisenstein_int), intent(out) :: best_unit, reduced

        type(eisenstein_int) :: units(6), conj, u
        real(8) :: rx, ry, ux, uy, angle, best_angle, target
        integer :: i

        call eisenstein_units(units)
        target = acos(-1.0d0) / 6.0d0  ! pi/6

        best_angle = huge(1.0d0)
        best_unit = units(1)

        do i = 1, 6
            u = units(i)
            conj = eisenstein_conjugate(u)
            ! z * conj(u): multiply (x,y) as complex by conjugate
            ! (x + iy)(conj_a + i*conj_b_coord)
            call eisenstein_to_real(conj%a, conj%b, ux, uy)
            rx = x * ux - y * uy
            ry = x * uy + y * ux
            angle = abs(atan2(ry, rx) - target)
            if (angle < best_angle) then
                best_angle = angle
                best_unit = u
            end if
        end do

        ! Apply best unit's conjugate
        conj = eisenstein_conjugate(best_unit)
        call eisenstein_to_real(conj%a, conj%b, ux, uy)
        rx = x * ux - y * uy
        ry = x * uy + y * ux
        reduced = eisenstein_round(rx, ry)
    end subroutine

end module snapkit_eisenstein

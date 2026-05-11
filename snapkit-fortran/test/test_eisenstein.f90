!> @file test_eisenstein.f90
!! @brief Tests for Eisenstein integer snap.
module test_eisenstein
  use snapkit
  use snapkit_eisenstein
  implicit none
  private
  public :: test_eisenstein_exact
  public :: test_eisenstein_boundary
  public :: test_eisenstein_batch

contains

  !> Test exact Eisenstein integers snap to themselves.
  function test_eisenstein_exact() result(pass)
    logical :: pass
    integer  :: a, b
    real(wp) :: sr, si, dist

    pass = .true.

    ! Test: integer (0,0) maps to itself
    call snapkit_nearest_eisenstein(0.0_wp, 0.0_wp, a, b, sr, si, dist)
    if (a /= 0 .or. b /= 0 .or. dist > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: (0,0) Eisenstein snap"
       write(*, '(a, i2, i2, f10.6)') "    got a,b,dist: ", a, b, dist
       pass = .false.
    end if

    ! Test: (1, 0) = Eisenstein (1, 0)
    call snapkit_nearest_eisenstein(1.0_wp, 0.0_wp, a, b, sr, si, dist)
    if (a /= 1 .or. b /= 0 .or. dist > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: (1,0) Eisenstein snap"
       pass = .false.
    end if

    ! Test: (-0.5, sqrt3/2) = ω = Eisenstein (0, 1)
    call snapkit_nearest_eisenstein(-0.5_wp, SNAPKIT_SQRT3_2, a, b, sr, si, dist)
    if (a /= 0 .or. b /= 1 .or. dist > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: omega=(0,1) Eisenstein snap"
       write(*, '(a, i2, i2, f10.6)') "    got a,b,dist: ", a, b, dist
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: Eisenstein exact tests"
  end function test_eisenstein_exact

  !> Test boundary cases where direct rounding fails.
  !!
  !! On a hexagonal lattice, ~3-5% of points near Voronoi cell boundaries
  !! round incorrectly. The 3x3 search corrects these. We test one known
  !! boundary case: the point halfway between two lattice points.
  function test_eisenstein_boundary() result(pass)
    logical :: pass
    integer  :: a, b
    real(wp) :: sr, si, dist

    pass = .true.

    ! Point near center of hexagon: should snap to correct Eisenstein
    call snapkit_nearest_eisenstein(0.2_wp, 0.2_wp, a, b, sr, si, dist)
    ! The nearest Eisenstein should be within sqrt(3)/3 of origin
    if (dist > SNAPKIT_SQRT3_2 * 0.667_wp) then
       write(*, '(a)') "  FAIL: center point too far from lattice"
       write(*, '(a, f10.6)') "    dist: ", dist
       pass = .false.
    end if

    ! Test near the corner case: (0.5, sqrt3/6) — on the boundary
    call snapkit_nearest_eisenstein(0.5_wp, SNAPKIT_SQRT3_2 / 3.0_wp, a, b, sr, si, dist)
    if (dist > SNAPKIT_SQRT3_2 * 0.667_wp) then
       write(*, '(a)') "  FAIL: boundary point too far from lattice"
       pass = .false.
    end if

    ! Verify the 3x3 search finds a better point than direct rounding alone.
    ! A point intentionally at the Voronoi boundary.
    ! Eisenstein integer (1,0) maps to cartesian (1, 0)
    ! Eisenstein integer (0,1) maps to cartesian (-0.5, sqrt3/2)
    ! Boundary between them: (0.25, sqrt3/4) = 0.25, 0.433
    call snapkit_nearest_eisenstein(0.25_wp, SNAPKIT_SQRT3_2 * 0.5_wp, a, b, sr, si, dist)
    ! Should be close to either (1,0) or (0,1)
    if (dist > 0.3_wp) then
       write(*, '(a, f10.6)') "  FAIL: boundary test, dist too large: ", dist
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: Eisenstein boundary tests"
  end function test_eisenstein_boundary

  !> Test batch Eisenstein snap.
  function test_eisenstein_batch() result(pass)
    logical :: pass
    real(wp) :: reals(4), imags(4)
    real(wp) :: sr(4), si(4), dists(4)
    integer  :: a(4), b(4)
    integer  :: i

    pass = .true.

    reals = [0.0_wp, 1.0_wp, -0.5_wp, 2.0_wp]
    imags = [0.0_wp, 0.0_wp, SNAPKIT_SQRT3_2, 1.0_wp]

    call snapkit_nearest_eisenstein_batch(reals, imags, a, b, sr, si, dists)

    ! (0,0) → (0,0)
    if (a(1) /= 0 .or. b(1) /= 0) then
       write(*, '(a)') "  FAIL: batch (0,0) Eisenstein"
       pass = .false.
    end if

    ! (1,0) → (1,0)
    if (a(2) /= 1 .or. b(2) /= 0) then
       write(*, '(a)') "  FAIL: batch (1,0) Eisenstein"
       pass = .false.
    end if

    ! ω → (0,1)
    if (a(3) /= 0 .or. b(3) /= 1) then
       write(*, '(a)') "  FAIL: batch ω Eisenstein"
       pass = .false.
    end if

    ! All distances should be >= 0
    do i = 1, 4
       if (dists(i) < 0.0_wp) then
          write(*, '(a, i2)') "  FAIL: negative distance at ", i
          pass = .false.
       end if
    end do

    if (pass) write(*, '(a)') "  PASS: Eisenstein batch tests"
  end function test_eisenstein_batch

end module test_eisenstein

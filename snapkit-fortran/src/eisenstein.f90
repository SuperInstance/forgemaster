!> @file eisenstein.f90
!! @brief Eisenstein integer snap (A₂ lattice) — 3x3 Voronoi neighborhood search.
!!
!! The Eisenstein lattice ℤ[ω] (ω = e^(2πi/3)) provides optimal 2D
!! information compression: densest packing, isotropic (6-fold symmetry),
!! and PID property guaranteeing H¹ = 0 (local → global consistency).
!!
!! This uses a 3x3 Voronoi neighborhood sweep (same algorithm as snapkit-c)
!! to find the mathematically correct nearest Eisenstein integer.
!! Direct rounding alone fails on ~3-5% of boundary cases.

module snapkit_eisenstein
  use snapkit, only: wp, SNAPKIT_INV_SQRT3, SNAPKIT_SQRT3_2
  implicit none
  private

  public :: snapkit_nearest_eisenstein
  public :: snapkit_nearest_eisenstein_batch

contains

  !> Compute the nearest Eisenstein integer to (real, imag).
  !!
  !! The Eisenstein integer basis (1, ω) where ω = e^(2πi/3) = -1/2 + i√3/2.
  !! z = x + iy = a + b·(-1/2 + i√3/2) = (a - b/2) + i(b√3/2)
  !! Therefore:
  !!   y = b·√3/2  →  b = 2y/√3
  !!   x = a - b/2 →  a = x + b/2 = x + y/√3
  !!
  !! Uses 3x3 Voronoi neighborhood search (9 candidates) for correctness.
  !!
  !! @param[in]  real        Real part of complex value
  !! @param[in]  imag        Imaginary part
  !! @param[out] a           Eisenstein coordinate a
  !! @param[out] b           Eisenstein coordinate b
  !! @param[out] snapped_re  Real part of snapped point
  !! @param[out] snapped_im  Imaginary part of snapped point
  !! @param[out] dist        Euclidean distance to snapped point
  pure subroutine snapkit_nearest_eisenstein(rx, iy, a, b, snapped_re, snapped_im, dist)
    real(wp), intent(in)  :: rx, iy
    integer,  intent(out) :: a, b
    real(wp), intent(out) :: snapped_re, snapped_im, dist

    real(wp) :: b_float, a_float
    integer  :: a0, b0, da, db, ca, cb, best_a, best_b
    real(wp) :: cx, cy, dx, dy, d2, best_d2

    ! Step 1: Compute floating-point (a, b) coordinates in basis (1, ω)
    b_float = 2.0_wp * iy * SNAPKIT_INV_SQRT3
    a_float = rx + iy * SNAPKIT_INV_SQRT3

    ! Step 2: Get initial integer candidate via rounding
    a0 = nint(a_float)
    b0 = nint(b_float)

    ! Step 3: Check all 9 candidates (3x3 neighborhood)
    best_a = a0
    best_b = b0
    best_d2 = huge(1.0_wp)

    do da = -1, 1
       do db = -1, 1
          ca = a0 + da
          cb = b0 + db
          ! Map Eisenstein integer (ca, cb) back to Cartesian
          cx = real(ca, wp) - real(cb, wp) * 0.5_wp
          cy = real(cb, wp) * SNAPKIT_SQRT3_2
          dx = rx - cx
          dy = iy - cy
          d2 = dx * dx + dy * dy
          if (d2 < best_d2) then
             best_d2 = d2
             best_a  = ca
             best_b  = cb
          end if
       end do
    end do

    a = best_a
    b = best_b
    snapped_re = real(best_a, wp) - real(best_b, wp) * 0.5_wp
    snapped_im = real(best_b, wp) * SNAPKIT_SQRT3_2
    dist = sqrt(best_d2)
  end subroutine snapkit_nearest_eisenstein

  !> Batch Eisenstein snap — processes an array of complex values.
  !!
  !! Fortran's array-oriented nature makes this efficient without explicit SIMD.
  !! Each element independently runs the scalar 3x3 Voronoi search.
  !!
  !! @param[in]  reals       Array of real components
  !! @param[in]  imags       Array of imaginary components
  !! @param[out] a_out       Output Eisenstein coordinate a
  !! @param[out] b_out       Output Eisenstein coordinate b
  !! @param[out] snapped_re  Output snapped real parts
  !! @param[out] snapped_im  Output snapped imaginary parts
  !! @param[out] dist_out    Output distances
  pure subroutine snapkit_nearest_eisenstein_batch(re_x, im_y, a_out, b_out, &
       snapped_re, snapped_im, dist_out)
    real(wp), intent(in)  :: re_x(:), im_y(:)
    integer,  intent(out) :: a_out(:), b_out(:)
    real(wp), intent(out) :: snapped_re(:), snapped_im(:), dist_out(:)

    integer :: i, n

    n = min(size(re_x), size(im_y), size(a_out), size(b_out), &
         size(snapped_re), size(snapped_im), size(dist_out))

    do i = 1, n
       call snapkit_nearest_eisenstein(re_x(i), im_y(i), &
            a_out(i), b_out(i), snapped_re(i), snapped_im(i), dist_out(i))
    end do
  end subroutine snapkit_nearest_eisenstein_batch

end module snapkit_eisenstein

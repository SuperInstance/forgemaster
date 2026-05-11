! FLUX-Tensor-MIDI : flux_midi_batch.f90
! Batch operations — T-0 state classification, Eisenstein snap dispatch
!
! N rooms × M intervals: array-oriented classification and quantization.
module flux_midi_batch
  use flux_midi_flux, only: wp
  use flux_midi_snap, only: eisenstein_snap, eisenstein_lattice_radius
  implicit none
  private

  public :: batch_t0_check, batch_state_classify
  public :: batch_t0_rate, batch_t0_crossing_density
  public :: batch_eisenstein_snap, batch_eisenstein_radius

contains

  !========================================================================
  ! BATCH T-0 CHECK
  !
  ! Classify each time interval as pre-T0, T-0, or post-T0
  ! using WHERE clauses on the flux sign and magnitude.
  !
  ! flux(N, M) -> state(N, M)
  !   -1 = pre-T0 (negative flux, below threshold)
  !    0 = T-0 crossing (sign change, above threshold)
  !    1 = post-T0 (positive flux)
  !========================================================================

  !--------------------------------------------------------------
  ! batch_t0_check: classify every element via WHERE
  !--------------------------------------------------------------
  pure function batch_t0_check(flux, threshold) result(state)
    real(wp), intent(in) :: flux(:,:)
    real(wp), intent(in) :: threshold
    integer :: state(size(flux,1), size(flux,2))
    integer :: i, j, n, m

    n = size(flux,1)
    m = size(flux,2)

    do i = 1, n
      ! Initialize: pre-T0 for negative, post-T0 for positive
      where (flux(i,:) < -threshold)
        state(i,:) = -1
      elsewhere (flux(i,:) > threshold)
        state(i,:) = 1
      elsewhere
        state(i,:) = 0
      end where
    end do

    ! Refine T-0: look for sign changes between adjacent intervals
    do concurrent (i = 1:n, j = 2:m)
      if (flux(i,j) * flux(i,j-1) < 0.0_wp .and. &
          abs(flux(i,j) - flux(i,j-1)) > threshold) then
        state(i,j) = 0   ! mark as T-0 crossing
        state(i,j-1) = 0
      end if
    end do
  end function batch_t0_check

  !--------------------------------------------------------------
  ! batch_state_classify: return count of each state per room
  !--------------------------------------------------------------
  pure function batch_state_classify(flux, threshold) result(counts)
    real(wp), intent(in) :: flux(:,:)
    real(wp), intent(in) :: threshold
    integer :: counts(size(flux,1), 3)  ! (pre, t0, post) per room
    integer :: state(size(flux,1), size(flux,2))
    integer :: i, n

    state = batch_t0_check(flux, threshold)
    n = size(flux,1)

    do concurrent (i = 1:n)
      counts(i,1) = count(state(i,:) == -1)
      counts(i,2) = count(state(i,:) == 0)
      counts(i,3) = count(state(i,:) == 1)
    end do
  end function batch_state_classify

  !--------------------------------------------------------------
  ! batch_t0_rate: fraction of time steps at T-0 crossing
  !--------------------------------------------------------------
  pure function batch_t0_rate(flux, threshold) result(rate)
    real(wp), intent(in) :: flux(:,:)
    real(wp), intent(in) :: threshold
    real(wp) :: rate
    integer :: state(size(flux,1), size(flux,2))
    integer :: n, m

    state = batch_t0_check(flux, threshold)
    n = size(flux,1)
    m = size(flux,2)

    ! Rate = (# T-0 elements) / (total elements)
    rate = real(count(state == 0), wp) / real(n * m, wp)
  end function batch_t0_rate

  !--------------------------------------------------------------
  ! batch_t0_crossing_density: T-0 crossings per interval per room
  !--------------------------------------------------------------
  pure function batch_t0_crossing_density(flux, threshold) result(density)
    real(wp), intent(in) :: flux(:,:)
    real(wp), intent(in) :: threshold
    real(wp) :: density(size(flux,1))
    integer :: state(size(flux,1), size(flux,2))
    integer :: i, n, m

    state = batch_t0_check(flux, threshold)
    n = size(flux,1)
    m = size(flux,2)

    do concurrent (i = 1:n)
      density(i) = real(count(state(i,:) == 0), wp) / real(m, wp)
    end do
  end function batch_t0_crossing_density

  !========================================================================
  ! BATCH EISENSTEIN SNAP — vectorized lattice rounding
  !========================================================================

  !--------------------------------------------------------------
  ! batch_eisenstein_snap: snap every element to nearest integer
  !--------------------------------------------------------------
  pure function batch_eisenstein_snap(values) result(snapped)
    real(wp), intent(in) :: values(:,:)
    real(wp) :: snapped(size(values,1), size(values,2))
    integer :: i, j, n, m

    n = size(values,1)
    m = size(values,2)
    do concurrent (i = 1:n, j = 1:m)
      snapped(i,j) = eisenstein_snap(values(i,j))
    end do
  end function batch_eisenstein_snap

  !--------------------------------------------------------------
  ! batch_eisenstein_radius: lattice distance for every element
  !--------------------------------------------------------------
  pure function batch_eisenstein_radius(values) result(radii)
    real(wp), intent(in) :: values(:,:)
    real(wp) :: radii(size(values,1), size(values,2))
    integer :: i, j, n, m

    n = size(values,1)
    m = size(values,2)
    do concurrent (i = 1:n, j = 1:m)
      radii(i,j) = eisenstein_lattice_radius(values(i,j))
    end do
  end function batch_eisenstein_radius

end module flux_midi_batch

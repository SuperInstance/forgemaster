!> @file snap.f90
!! @brief Snap function implementation — tolerance-based compression.
!!
!! The snap function compresses values "close enough to expected" so that
!! the mind can focus on what actually matters. It is the gatekeeper of
!! attention: everything within tolerance gets compressed away, and only
!! deltas (exceedances) survive to demand cognition.

module snapkit_snap
  use snapkit
  use snapkit_eisenstein, only: snapkit_nearest_eisenstein, snapkit_nearest_eisenstein_batch
  implicit none
  private

  public :: snapkit_snap_create
  public :: snapkit_snap_create_ex
  public :: snapkit_snap_free
  public :: snapkit_snap
  public :: snapkit_snap_eisenstein
  public :: snapkit_snap_batch
  public :: snapkit_snap_eisenstein_batch
  public :: snapkit_snap_reset
  public :: snapkit_snap_calibrate
  public :: snapkit_snap_statistics

contains

  !> Create a snap function with default parameters.
  function snapkit_snap_create() result(sf)
    type(snapkit_snap_function_t), pointer :: sf
    allocate(sf)
    sf%tolerance        = SNAPKIT_DEFAULT_TOLERANCE
    sf%topology         = SNAPKIT_TOPOLOGY_HEXAGONAL
    sf%baseline         = 0.0_wp
    sf%adaptation_rate  = SNAPKIT_DEFAULT_ADAPTATION_RATE
    allocate(sf%history%results(SNAPKIT_SNAP_HISTORY_MAX))
    sf%history%head      = 0
    sf%history%count     = 0
    sf%history%sum_delta = 0.0_wp
    sf%history%max_delta = 0.0_wp
    sf%history%snap_cnt  = 0
    sf%history%delta_cnt = 0
  end function snapkit_snap_create

  !> Create a snap function with explicit parameters.
  function snapkit_snap_create_ex(tolerance, topology, baseline, adaptation_rate) result(sf)
    real(wp), intent(in) :: tolerance
    integer,  intent(in) :: topology
    real(wp), intent(in) :: baseline
    real(wp), intent(in) :: adaptation_rate
    type(snapkit_snap_function_t), pointer :: sf

    allocate(sf)
    sf%tolerance        = tolerance
    sf%topology         = topology
    sf%baseline         = baseline
    sf%adaptation_rate  = adaptation_rate
    allocate(sf%history%results(SNAPKIT_SNAP_HISTORY_MAX))
    sf%history%head      = 0
    sf%history%count     = 0
    sf%history%sum_delta = 0.0_wp
    sf%history%max_delta = 0.0_wp
    sf%history%snap_cnt  = 0
    sf%history%delta_cnt = 0
  end function snapkit_snap_create_ex

  !> Free a snap function.
  subroutine snapkit_snap_free(sf)
    type(snapkit_snap_function_t), pointer, intent(inout) :: sf
    if (associated(sf)) then
       if (allocated(sf%history%results)) deallocate(sf%history%results)
       deallocate(sf)
       sf => null()
    end if
  end subroutine snapkit_snap_free

  !> Snap a scalar value to the nearest expected point.
  !!
  !! If the absolute delta from expected (or baseline) is within tolerance,
  !! the value is snapped to the expected value (compressed away).
  !! Otherwise, it's a delta and passes through as-is (to demand attention).
  !!
  !! @param[inout] sf      Snap function (updated with history and adaptive baseline)
  !! @param[in]    value   The observed value
  !! @param[in]    expected Override baseline (use huge(1.0) to use baseline)
  !! @param[out]   out     Snap result
  !! @return       Error code
  function snapkit_snap(sf, value, expected, out) result(err)
    type(snapkit_snap_function_t), intent(inout), target :: sf
    real(wp), intent(in)  :: value
    real(wp), intent(in)  :: expected  ! use huge(1.0) for "use baseline"
    type(snapkit_snap_result_t), intent(out) :: out
    integer :: err

    real(wp) :: exp_val, delta
    logical  :: within
    integer(kind=8) :: idx

    err = SNAPKIT_OK

    ! Resolve expected value
    if (expected < huge(1.0_wp) * 0.99_wp) then
       exp_val = expected
    else
       exp_val = sf%baseline
    end if

    delta = abs(value - exp_val)
    within = delta <= sf%tolerance

    out%original         = value
    out%snapped          = merge(exp_val, value, within)
    out%delta            = delta
    out%within_tolerance = within
    out%tolerance        = sf%tolerance
    out%topology         = sf%topology

    ! Update history (circular buffer)
    sf%history%head = sf%history%head + 1
    idx = mod(sf%history%head - 1, int(SNAPKIT_SNAP_HISTORY_MAX, kind=8))
    sf%history%results(idx + 1) = out
    if (sf%history%count < SNAPKIT_SNAP_HISTORY_MAX) sf%history%count = sf%history%count + 1

    sf%history%sum_delta = sf%history%sum_delta + delta
    if (delta > sf%history%max_delta) sf%history%max_delta = delta

    if (within) then
       sf%history%snap_cnt = sf%history%snap_cnt + 1
    else
       sf%history%delta_cnt = sf%history%delta_cnt + 1
    end if

    ! Adaptive baseline update
    if (within .and. sf%adaptation_rate > 0.0_wp) then
       sf%baseline = sf%baseline + sf%adaptation_rate * (value - sf%baseline)
    end if
  end function snapkit_snap

  !> Snap a complex value to the nearest Eisenstein integer.
  !!
  !! Uses the 3x3 Voronoi neighborhood search for mathematically correct
  !! nearest Eisenstein integer. The distance becomes the delta; if within
  !! tolerance the complex point snaps to the lattice point.
  !!
  !! @param[inout] sf       Snap function (or null() for default tolerance)
  !! @param[in]    real     Real part
  !! @param[in]    imag     Imaginary part
  !! @param[in]    tolerance Snap tolerance (< 0 means use sf%tolerance)
  !! @param[out]   out      Snap result
  !! @return       Error code
  function snapkit_snap_eisenstein(sf, real, imag, tolerance, out) result(err)
    type(snapkit_snap_function_t), intent(inout), optional, target :: sf
    real(wp), intent(in)  :: real, imag
    real(wp), intent(in)  :: tolerance
    type(snapkit_snap_result_t), intent(out) :: out
    integer :: err

    real(wp) :: tol, snapped_re, snapped_im, dist
    integer  :: a, b

    err = SNAPKIT_OK

    ! Resolve tolerance
    if (tolerance >= 0.0_wp) then
       tol = tolerance
    else if (present(sf)) then
       tol = sf%tolerance
    else
       tol = SNAPKIT_DEFAULT_TOLERANCE
    end if

    call snapkit_nearest_eisenstein(real, imag, a, b, snapped_re, snapped_im, dist)

    out%original = sqrt(real * real + imag * imag)
    out%snapped  = sqrt(snapped_re * snapped_re + snapped_im * snapped_im)
    out%delta    = dist
    out%within_tolerance = dist <= tol
    out%tolerance = tol
    out%topology = SNAPKIT_TOPOLOGY_HEXAGONAL

    if (present(sf)) then
       sf%history%head = sf%history%head + 1
       associate(idx => mod(sf%history%head - 1, int(SNAPKIT_SNAP_HISTORY_MAX, kind=8)))
         sf%history%results(idx + 1) = out
       end associate
       if (sf%history%count < SNAPKIT_SNAP_HISTORY_MAX) sf%history%count = sf%history%count + 1
       sf%history%sum_delta = sf%history%sum_delta + dist
       if (dist > sf%history%max_delta) sf%history%max_delta = dist
       if (out%within_tolerance) then
          sf%history%snap_cnt = sf%history%snap_cnt + 1
       else
          sf%history%delta_cnt = sf%history%delta_cnt + 1
       end if
    end if
  end function snapkit_snap_eisenstein

  !> Batch snap an array of scalar values.
  !!
  !! Fortran array operations make this naturally vectorized.
  !! Each element is snapped against the same baseline and tolerance.
  !!
  !! @param[inout] sf      Snap function
  !! @param[in]    values  Array of values
  !! @param[out]   out     Array of snap results
  function snapkit_snap_batch(sf, values, out) result(err)
    type(snapkit_snap_function_t), intent(inout) :: sf
    real(wp), intent(in)  :: values(:)
    type(snapkit_snap_result_t), intent(out) :: out(:)
    integer :: err
    integer :: i, n

    err = SNAPKIT_OK
    n = min(size(values), size(out))

    do i = 1, n
       err = snapkit_snap(sf, values(i), huge(1.0_wp), out(i))
       if (err /= SNAPKIT_OK) exit
    end do
  end function snapkit_snap_batch

  !> Batch snap Eisenstein complex values.
  !!
  !! @param[inout] sf        Snap function (optional — for history tracking)
  !! @param[in]    real_vals Array of real components
  !! @param[in]    imag_vals Array of imag components
  !! @param[out]   out       Array of snap results
  function snapkit_snap_eisenstein_batch(sf, real_vals, imag_vals, out) result(err)
    type(snapkit_snap_function_t), intent(inout), optional :: sf
    real(wp), intent(in)  :: real_vals(:), imag_vals(:)
    type(snapkit_snap_result_t), intent(out) :: out(:)
    integer :: err
    integer :: i, n

    err = SNAPKIT_OK
    n = min(size(real_vals), size(imag_vals), size(out))

    do i = 1, n
       if (present(sf)) then
          err = snapkit_snap_eisenstein(sf, real_vals(i), imag_vals(i), -1.0_wp, out(i))
       else
          err = snapkit_snap_eisenstein(tolerance=-1.0_wp, out=out(i), &
               real=real_vals(i), imag=imag_vals(i))
       end if
       if (err /= SNAPKIT_OK) exit
    end do
  end function snapkit_snap_eisenstein_batch

  !> Reset snap function state.
  !!
  !! @param[inout] sf       Snap function
  !! @param[in]    baseline New baseline value (use huge(1.0) to keep current)
  subroutine snapkit_snap_reset(sf, baseline)
    type(snapkit_snap_function_t), intent(inout) :: sf
    real(wp), intent(in) :: baseline

    if (baseline < huge(1.0_wp) * 0.99_wp) sf%baseline = baseline
    sf%history%head      = 0
    sf%history%count     = 0
    sf%history%sum_delta = 0.0_wp
    sf%history%max_delta = 0.0_wp
    sf%history%snap_cnt  = 0
    sf%history%delta_cnt = 0
  end subroutine snapkit_snap_reset

  !> Auto-calibrate tolerance to achieve a target snap rate.
  !!
  !! Sets baseline to the sample mean, then chooses tolerance at the
  !! target_rate percentile of distances from the mean.
  !! A well-calibrated snap function snaps ~90% of observations (0.9 rate),
  !! leaving 10% as deltas demanding attention.
  !!
  !! @param[inout] sf          Snap function
  !! @param[in]    values      Sample values for calibration
  !! @param[in]    target_rate Desired snap rate [0..1] (0.9 recommended)
  function snapkit_snap_calibrate(sf, values, target_rate) result(err)
    type(snapkit_snap_function_t), intent(inout) :: sf
    real(wp), intent(in)  :: values(:)
    real(wp), intent(in)  :: target_rate
    integer :: err

    real(wp) :: sum_vals, mean_val
    real(wp), allocatable :: distances(:)
    integer  :: i, n, idx

    err = SNAPKIT_OK
    n = size(values)
    if (n == 0 .or. target_rate <= 0.0_wp) return

    ! Set baseline to mean
    sum_vals = sum(values)
    mean_val = sum_vals / real(n, wp)
    sf%baseline = mean_val

    ! Compute distances from baseline
    allocate(distances(n))
    do i = 1, n
       distances(i) = abs(values(i) - mean_val)
    end do

    ! Sort distances (simple insertion sort)
    call insertion_sort(distances)

    ! Set tolerance at target_rate percentile
    idx = nint(real(n, wp) * target_rate)
    if (idx < 1) idx = 1
    if (idx > n) idx = n
    sf%tolerance = distances(idx)

    deallocate(distances)
  end function snapkit_snap_calibrate

  !> Get statistics from a snap function.
  !!
  !! @param[in]  sf           Snap function
  !! @param[out] snap_count   Number of observations that snapped
  !! @param[out] delta_count  Number that exceeded tolerance
  !! @param[out] mean_delta   Mean delta magnitude
  !! @param[out] max_delta    Maximum delta observed
  !! @param[out] snap_rate    Fraction of snaps [0..1]
  subroutine snapkit_snap_statistics(sf, snap_count, delta_count, mean_delta, max_delta, snap_rate)
    type(snapkit_snap_function_t), intent(in) :: sf
    integer(kind=8), intent(out), optional :: snap_count, delta_count
    real(wp),        intent(out), optional :: mean_delta, max_delta, snap_rate

    integer(kind=8) :: total

    if (present(snap_count))  snap_count  = sf%history%snap_cnt
    if (present(delta_count)) delta_count = sf%history%delta_cnt
    total = sf%history%snap_cnt + sf%history%delta_cnt
    if (present(mean_delta)) then
       mean_delta = merge(sf%history%sum_delta / real(total, wp), 0.0_wp, total > 0)
    end if
    if (present(max_delta)) max_delta = sf%history%max_delta
    if (present(snap_rate)) then
       snap_rate = merge(real(sf%history%snap_cnt, wp) / real(total, wp), 0.0_wp, total > 0)
    end if
  end subroutine snapkit_snap_statistics

  !===========================================================================
  ! Internal: insertion sort
  !===========================================================================
  pure subroutine insertion_sort(arr)
    real(wp), intent(inout) :: arr(:)
    real(wp) :: key
    integer  :: i, j
    do i = 2, size(arr)
       key = arr(i)
       j = i - 1
       do while (j > 0 .and. arr(j) > key)
          arr(j+1) = arr(j)
          j = j - 1
       end do
       arr(j+1) = key
    end do
  end subroutine insertion_sort

end module snapkit_snap

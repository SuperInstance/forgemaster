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

  public :: snapkit_snap_create_fn
  public :: snapkit_snap_create_ex
  public :: snapkit_snap_free_fn
  public :: snapkit_snap_apply
  public :: snapkit_snap_eisenstein
  public :: snapkit_snap_batch
  public :: snapkit_snap_eisenstein_batch
  public :: snapkit_snap_reset
  public :: snapkit_snap_calibrate
  public :: snapkit_snap_statistics

contains

  !> Create a snap function with default parameters.
  function snapkit_snap_create_fn() result(sf)
    type(snapkit_snap_function_t), pointer :: sf
    integer :: i

    allocate(sf)
    allocate(sf%history%results(SNAPKIT_SNAP_HISTORY_MAX))

    sf%tolerance       = SNAPKIT_DEFAULT_TOLERANCE
    sf%topology        = SNAPKIT_TOPOLOGY_HEXAGONAL
    sf%baseline        = 0.0_wp
    sf%adaptation_rate = 0.01_wp
    sf%history%head    = 0
    sf%history%count   = 0
    sf%history%sum_delta = 0.0_wp
    sf%history%max_delta = 0.0_wp
    sf%history%snap_cnt  = 0
    sf%history%delta_cnt = 0
    do i = 1, SNAPKIT_SNAP_HISTORY_MAX
       sf%history%results(i)%within_tolerance = .false.
       sf%history%results(i)%delta    = 0.0_wp
       sf%history%results(i)%original = 0.0_wp
       sf%history%results(i)%snapped  = 0.0_wp
       sf%history%results(i)%tolerance = 0.0_wp
       sf%history%results(i)%topology = 0
    end do
  end function snapkit_snap_create_fn

  !> Create a snap function with explicit parameters.
  function snapkit_snap_create_ex(tolerance, topology, baseline, adaptation_rate) result(sf)
    real(wp), intent(in) :: tolerance
    integer,  intent(in) :: topology
    real(wp), intent(in) :: baseline
    real(wp), intent(in) :: adaptation_rate
    type(snapkit_snap_function_t), pointer :: sf

    sf => snapkit_snap_create_fn()
    sf%tolerance       = tolerance
    sf%topology        = topology
    sf%baseline        = baseline
    sf%adaptation_rate = adaptation_rate
  end function snapkit_snap_create_ex

  !> Free a snap function.
  subroutine snapkit_snap_free_fn(sf)
    type(snapkit_snap_function_t), pointer, intent(inout) :: sf
    if (associated(sf)) then
       if (allocated(sf%history%results)) deallocate(sf%history%results)
       deallocate(sf)
       sf => null()
    end if
  end subroutine snapkit_snap_free_fn

  !> Apply the snap function: compress value if within tolerance of expected.
  function snapkit_snap_apply(sf, value, expected, out) result(err)
    type(snapkit_snap_function_t), intent(inout), target :: sf
    real(wp), intent(in)  :: value
    real(wp), intent(in)  :: expected  ! use huge(1.0) for "use baseline"
    type(snapkit_snap_result_t), intent(out) :: out
    integer :: err

    real(wp) :: exp_val, delta
    logical  :: within
    integer(kind=8) :: idx

    err = SNAPKIT_OK

    ! Determine expected value
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

    ! Store in history ring buffer
    sf%history%head = sf%history%head + 1
    idx = mod(sf%history%head - 1, int(SNAPKIT_SNAP_HISTORY_MAX, kind=8))
    sf%history%results(idx + 1) = out
    if (sf%history%count < SNAPKIT_SNAP_HISTORY_MAX) &
         sf%history%count = sf%history%count + 1

    sf%history%sum_delta = sf%history%sum_delta + delta
    if (delta > sf%history%max_delta) sf%history%max_delta = delta

    if (within) then
       sf%history%snap_cnt = sf%history%snap_cnt + 1
    else
       sf%history%delta_cnt = sf%history%delta_cnt + 1
    end if

    ! Adaptive baseline drift
    if (within .and. sf%adaptation_rate > 0.0_wp) then
       sf%baseline = sf%baseline + sf%adaptation_rate * (value - sf%baseline)
    end if
  end function snapkit_snap_apply

  !> Snap an Eisenstein value to this snap function's tolerance.
  function snapkit_snap_eisenstein(sf, rx, iy, out) result(err)
    type(snapkit_snap_function_t), intent(inout), target :: sf
    real(wp), intent(in)  :: rx, iy
    type(snapkit_snap_result_t), intent(out) :: out
    integer :: err

    real(wp) :: sr, si, dist
    integer  :: a, b

    call snapkit_nearest_eisenstein(rx, iy, a, b, sr, si, dist)
    err = snapkit_snap_apply(sf, dist, sf%tolerance, out)
  end function snapkit_snap_eisenstein

  !> Batch snap — apply snap to an array of values.
  subroutine snapkit_snap_batch(sf, values, expected, results, n)
    type(snapkit_snap_function_t), intent(inout) :: sf
    real(wp), intent(in)  :: values(:)
    real(wp), intent(in)  :: expected
    type(snapkit_snap_result_t), intent(out) :: results(:)
    integer, intent(out) :: n
    integer :: i, err

    n = 0
    do i = 1, size(values)
       err = snapkit_snap_apply(sf, values(i), expected, results(i))
       if (err == SNAPKIT_OK) n = n + 1
    end do
  end subroutine snapkit_snap_batch

  !> Batch Eisenstein snap.
  subroutine snapkit_snap_eisenstein_batch(sf, reals, imags, results, n)
    type(snapkit_snap_function_t), intent(inout) :: sf
    real(wp), intent(in)  :: reals(:), imags(:)
    type(snapkit_snap_result_t), intent(out) :: results(:)
    integer, intent(out) :: n
    integer :: i, err

    n = 0
    do i = 1, min(size(reals), size(imags))
       err = snapkit_snap_eisenstein(sf, reals(i), imags(i), results(i))
       if (err == SNAPKIT_OK) n = n + 1
    end do
  end subroutine snapkit_snap_eisenstein_batch

  !> Reset snap function history.
  subroutine snapkit_snap_reset(sf)
    type(snapkit_snap_function_t), intent(inout) :: sf
    sf%history%head      = 0
    sf%history%count     = 0
    sf%history%sum_delta = 0.0_wp
    sf%history%max_delta = 0.0_wp
    sf%history%snap_cnt  = 0
    sf%history%delta_cnt = 0
  end subroutine snapkit_snap_reset

  !> Auto-calibrate tolerance from sample data.
  function snapkit_snap_calibrate(sf, samples, percentile) result(err)
    type(snapkit_snap_function_t), intent(inout) :: sf
    real(wp), intent(in) :: samples(:)
    real(wp), intent(in) :: percentile  ! e.g. 0.80
    integer :: err

    real(wp) :: mean
    real(wp) :: dists(size(samples))
    real(wp) :: sorted(size(samples))
    integer  :: i, n, idx

    err = SNAPKIT_OK
    n = size(samples)
    if (n < 2) then
       err = SNAPKIT_ERR_STATE
       return
    end if

    ! Compute mean
    mean = sum(samples) / real(n, wp)
    sf%baseline = mean

    ! Compute distances from mean
    do i = 1, n
       dists(i) = abs(samples(i) - mean)
    end do

    ! Sort distances (insertion sort, n is small)
    sorted = dists
    call insertion_sort(sorted)

    ! Pick the percentile-th distance as tolerance
    idx = max(1, min(n, int(percentile * real(n, wp) + 1.0_wp)))
    sf%tolerance = sorted(idx) + 1.0e-12_wp  ! epsilon to avoid zero
  end function snapkit_snap_calibrate

  !> Get snap statistics.
  subroutine snapkit_snap_statistics(sf, snap_cnt, delta_cnt, mean_delta, &
       max_delta, snap_rate)
    type(snapkit_snap_function_t), intent(in) :: sf
    integer(kind=8), intent(out) :: snap_cnt, delta_cnt
    real(wp), intent(out) :: mean_delta, max_delta, snap_rate
    integer(kind=8) :: total

    snap_cnt  = sf%history%snap_cnt
    delta_cnt = sf%history%delta_cnt
    max_delta = sf%history%max_delta
    total = snap_cnt + delta_cnt
    if (total > 0) then
       mean_delta = sf%history%sum_delta / real(total, wp)
       snap_rate  = real(snap_cnt, wp) / real(total, wp)
    else
       mean_delta = 0.0_wp
       snap_rate  = 0.0_wp
    end if
  end subroutine snapkit_snap_statistics

  !> Insertion sort (simple, for small n).
  subroutine insertion_sort(arr)
    real(wp), intent(inout) :: arr(:)
    integer :: i, j
    real(wp) :: key

    if (size(arr) <= 1) return

    do i = 2, size(arr)
       key = arr(i)
       j = i - 1
       do
          if (j <= 0) exit
          if (arr(j) <= key) exit
          arr(j + 1) = arr(j)
          j = j - 1
       end do
       arr(j + 1) = key
    end do
  end subroutine insertion_sort

end module snapkit_snap

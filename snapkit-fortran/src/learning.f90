!> @file learning.f90
!! @brief Learning cycle — adaptive snap calibration and plateau detection.
!!
!! The learning cycle models how expertise develops:
!! 1. Observe → 2. Snap → 3. Detect delta → 4. Allocate attention → 5. Learn
!!
!! When holonomy (systematic drift) accumulates, the system adjusts tolerance
!! or triggers curiosity-driven exploration. Plateaus are detected when
!! performance stalls, triggering exploration of new scripts.

module snapkit_learning
  use snapkit
  implicit none
  private

  public :: snapkit_learning_tick
  public :: snapkit_learning_calibrate

contains

  !> Advance the learning cycle by one tick.
  !!
  !! Updates delta, tolerance, and holonomy based on observed value.
  !! Computes curiosity-driven exploration signal: how much to explore
  !! vs exploit based on accumulated holonomy.
  !!
  !! @param[inout] state  Learning state
  !! @param[in]    value  Current observed performance value
  !! @param[out]   explored Whether this tick triggered exploration
  subroutine snapkit_learning_tick(state, value, explored)
    type(snapkit_learning_state_t), intent(inout) :: state
    real(wp), intent(in)  :: value
    logical,  intent(out), optional :: explored

    real(wp) :: prev_best

    state%cycle = state%cycle + 1
    state%delta = value

    ! Update holonomy: exponential moving average of absolute delta
    ! When value keeps deviating in the same direction, holonomy accumulates
    state%holonomy = 0.9_wp * state%holonomy + 0.1_wp * abs(value)

    ! Track best performance
    if (value > state%best_performance) then
       state%best_performance = value
       state%plateau_cycles = 0
    else
       state%plateau_cycles = state%plateau_cycles + 1
    end if

    ! Plateau detection: no improvement for many cycles
    if (state%plateau_cycles > 20 .and. state%best_performance > 0.0_wp) then
       state%plateau_detected = .true.
    else
       state%plateau_detected = .false.
    end if

    ! Curiosity-driven tolerance adjustment
    if (state%plateau_detected) then
       ! Expand tolerance to snap more broadly = explore less precisely
       state%tolerance = state%tolerance * 1.05_wp
       ! Increase curiosity rate
       state%curiosity_rate = min(1.0_wp, state%curiosity_rate * 1.1_wp)
       if (present(explored)) explored = .true.
    else if (state%holonomy > state%tolerance * 3.0_wp) then
       ! High holonomy = tighten tolerance to detect finer deltas
       state%tolerance = state%tolerance * 0.95_wp
       state%curiosity_rate = max(0.01_wp, state%curiosity_rate * 0.95_wp)
       if (present(explored)) explored = .false.
    else
       ! Normal operation: gentle decay of curiosity
       state%curiosity_rate = max(0.01_wp, state%curiosity_rate * 0.99_wp)
       if (present(explored)) explored = .false.
    end if

    ! Adjust attention budget based on holonomy
    if (state%holonomy > state%tolerance * 5.0_wp) then
       ! Crisis mode: expand attention budget
       state%attention_budget = state%attention_budget * 1.1_wp
    else if (state%holonomy < state%tolerance * 0.5_wp) then
       ! Calm mode: conserve attention
       state%attention_budget = state%attention_budget * 0.98_wp
    end if
  end subroutine snapkit_learning_tick

  !> Calibrate initial learning state from a sample of values.
  !!
  !! Sets tolerance based on the 80th percentile of observed variability,
  !! and initializes curiosity rate, holonomy, and attention budget to
  !! sensible defaults.
  !!
  !! @param[out] state       Learning state
  !! @param[in]  samples     Initial performance samples
  !! @param[in]  pct         Percentile for tolerance calibration [0..1]
  subroutine snapkit_learning_calibrate(state, samples, pct)
    type(snapkit_learning_state_t), intent(out) :: state
    real(wp), intent(in) :: samples(:)
    real(wp), intent(in) :: pct

    real(wp) :: mean_val
    real(wp), allocatable :: distances(:)
    integer  :: i, n, idx

    n = size(samples)
    if (n == 0) then
       state%delta            = 0.0_wp
       state%tolerance        = SNAPKIT_DEFAULT_TOLERANCE
       state%holonomy         = 0.0_wp
       state%curiosity_rate   = 0.1_wp
       state%attention_budget = SNAPKIT_DEFAULT_BUDGET
       state%cycle            = 0
       state%plateau_detected = .false.
       state%best_performance = 0.0_wp
       state%plateau_cycles   = 0
       return
    end if

    ! Mean
    mean_val = sum(samples) / real(n, wp)

    ! Distances from mean
    allocate(distances(n))
    do i = 1, n
       distances(i) = abs(samples(i) - mean_val)
    end do

    ! Sort
    call sort_array(distances)

    ! Tolerance at requested percentile
    idx = nint(real(n, wp) * pct)
    if (idx < 1) idx = 1
    if (idx > n) idx = n

    state%delta            = 0.0_wp
    state%tolerance        = distances(idx)
    state%holonomy         = 0.0_wp
    state%curiosity_rate   = 0.1_wp
    state%attention_budget = SNAPKIT_DEFAULT_BUDGET
    state%cycle            = 0
    state%plateau_detected = .false.
    state%best_performance = 0.0_wp
    state%plateau_cycles   = 0

    deallocate(distances)
  end subroutine snapkit_learning_calibrate

  !> Internal: simple insertion sort
  pure subroutine sort_array(arr)
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
  end subroutine sort_array

end module snapkit_learning

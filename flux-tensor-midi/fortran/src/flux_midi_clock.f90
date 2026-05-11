! FLUX-Tensor-MIDI : flux_midi_clock.f90
! T-0 clock — harmonic alignment state machine
! N rooms × tick-level state tracking
module flux_midi_clock
  use flux_midi_flux, only: wp
  implicit none
  private

  ! Clock state enum (Fortran 2008 style)
  integer, parameter, public :: CLOCK_STATE_PRE = 0
  integer, parameter, public :: CLOCK_STATE_TICK = 1
  integer, parameter, public :: CLOCK_STATE_T0 = 2
  integer, parameter, public :: CLOCK_STATE_POST = 3
  integer, parameter, public :: CLOCK_STATE_HOLD = 4

  type, public :: t0_clock_t
    integer :: state = CLOCK_STATE_PRE
    real(wp) :: tick_phase = 0.0_wp   ! [0, 2π)
    real(wp) :: t0_threshold = 0.01_wp
    integer  :: t0_crossings = 0
    real(wp) :: harmonic_offset = 0.0_wp
  contains
    procedure :: advance => clock_advance
    procedure :: reset  => clock_reset
  end type t0_clock_t
  public :: clock_batch_advance, clock_batch_t0_count, clock_batch_phase_sync

contains

  !--------------------------------------------------------------
  ! clock_advance: single clock step with flux observation
  !   Updates phase, state on T-0 crossing
  !--------------------------------------------------------------
  pure subroutine clock_advance(this, flux_value, prev_flux)
    class(t0_clock_t), intent(inout) :: this
    real(wp), intent(in) :: flux_value, prev_flux

    ! Advance phase
    this%tick_phase = mod(this%tick_phase + flux_value, 2.0_wp * 4.0_wp * atan(1.0_wp))

    ! Check T-0 crossing (flux sign change + magnitude threshold)
    if (prev_flux * flux_value < 0.0_wp .and. abs(flux_value) > this%t0_threshold) then
      this%state = CLOCK_STATE_T0
      this%t0_crossings = this%t0_crossings + 1
      this%harmonic_offset = this%tick_phase
    else if (this%state == CLOCK_STATE_T0) then
      if (abs(flux_value) < this%t0_threshold * 10.0_wp) then
        this%state = CLOCK_STATE_POST
      else
        this%state = CLOCK_STATE_TICK
      end if
    end if
  end subroutine clock_advance

  !--------------------------------------------------------------
  ! clock_reset: return to PRE state
  !--------------------------------------------------------------
  pure subroutine clock_reset(this)
    class(t0_clock_t), intent(inout) :: this
    this%state = CLOCK_STATE_PRE
    this%tick_phase = 0.0_wp
    this%t0_crossings = 0
    this%harmonic_offset = 0.0_wp
  end subroutine clock_reset

  !--------------------------------------------------------------
  ! clock_batch_advance: advance N clocks in array operation
  !--------------------------------------------------------------
  pure subroutine clock_batch_advance(clocks, flux_vals, prev_flux_vals)
    type(t0_clock_t), intent(inout) :: clocks(:)
    real(wp), intent(in) :: flux_vals(:), prev_flux_vals(:)
    integer :: i

    do concurrent (i = 1:size(clocks))
      call clocks(i)%advance(flux_vals(i), prev_flux_vals(i))
    end do
  end subroutine clock_batch_advance

  !--------------------------------------------------------------
  ! clock_batch_t0_count: count T0 states in batch
  !--------------------------------------------------------------
  pure function clock_batch_t0_count(clocks) result(count_t0)
    type(t0_clock_t), intent(in) :: clocks(:)
    integer :: count_t0
    integer :: i

    count_t0 = 0
    do concurrent (i = 1:size(clocks))
      if (clocks(i)%state == CLOCK_STATE_T0) count_t0 = count_t0 + 1
    end do
  end function clock_batch_t0_count

  !--------------------------------------------------------------
  ! clock_batch_phase_sync: align all clocks to a reference phase
  !--------------------------------------------------------------
  pure subroutine clock_batch_phase_sync(clocks, ref_phase)
    type(t0_clock_t), intent(inout) :: clocks(:)
    real(wp), intent(in) :: ref_phase

    integer :: i
    do concurrent (i = 1:size(clocks))
      clocks(i)%tick_phase = ref_phase
      clocks(i)%harmonic_offset = 0.0_wp
    end do
  end subroutine clock_batch_phase_sync

end module flux_midi_clock

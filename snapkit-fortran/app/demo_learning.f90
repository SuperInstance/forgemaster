!> @file demo_learning.f90
!! @brief Learning cycle demonstration — adaptive skill acquisition.
!!
!! Simulates a learning process where performance values improve over time,
!! with occasional plateaus. The learning cycle detects plateaus, adjusts
!! tolerance, and triggers exploration vs exploitation.
!!
!! Demonstrates: snapkit_learning_calibrate, snapkit_learning_tick

program demo_learning
  use snapkit
  use snapkit_learning
  use snapkit_snap
  use snapkit_visualization
  implicit none

  type(snapkit_learning_state_t) :: state
  type(snapkit_snap_function_t), pointer :: sf

  integer  :: i, cycle
  real(wp) :: perf, noise, trend
  real(wp) :: initial_samples(20)
  logical  :: explored

  write(*, '(a)') "══════════════════════════════════════════════════════"
  write(*, '(a)') "  SnapKit: Learning Cycle Demonstration"
  write(*, '(a)') "  The system adapts its snap tolerance as it learns."
  write(*, '(a)') "══════════════════════════════════════════════════════"
  write(*, '(a)')

  !-------------------------------------------------------------------------
  ! Phase 1: Initial calibration from sample performance data
  !-------------------------------------------------------------------------
  write(*, '(a)') "Phase 1: Initial calibration..."
  write(*, '(a)') "  Taking 20 initial performance samples..."

  ! Generate initial samples with high variability (novice)
  call random_seed()
  do i = 1, 20
     call random_number(noise)
     initial_samples(i) = 0.3_wp + noise * 0.4_wp  ! range [0.3, 0.7]
  end do

  call snapkit_learning_calibrate(state, initial_samples, 0.80_wp)

  write(*, '(a, f8.4)') "  Calibrated tolerance: ", state%tolerance
  write(*, '(a, f8.4)') "  Initial curiosity:    ", state%curiosity_rate
  write(*, '(a)')

  !-------------------------------------------------------------------------
  ! Phase 2: Learning loop with improving performance
  !-------------------------------------------------------------------------
  sf => snapkit_snap_create_ex(state%tolerance, SNAPKIT_TOPOLOGY_GRADIENT, &
       0.5_wp, 0.02_wp)

  write(*, '(a)') "Phase 2: Learning (150 cycles)"
  write(*, '(a)') "  Cycle  Performance  Tolerance  Curiosity  Plateau  Notes"
  write(*, '(a)') "  ───────────────────────────────────────────────────────"

  trend = 0.5_wp
  do cycle = 1, 150
     ! Simulate improving performance with noise
     call random_number(noise)
     noise = (noise - 0.5_wp) * 0.15_wp

     ! Performance follows a learning curve with plateaus
     if (cycle > 40 .and. cycle < 60) then
        ! Plateau 1: performance stalls
        perf = 0.75_wp + noise * 0.5_wp
     else if (cycle > 100 .and. cycle < 120) then
        ! Plateau 2: performance stalls again
        perf = 0.85_wp + noise * 0.3_wp
     else
        ! Normal improvement
        trend = 0.5_wp + real(cycle, wp) / 300.0_wp
        if (trend > 0.95_wp) trend = 0.95_wp
        perf = trend + noise
     end if

     call snapkit_learning_tick(state, perf, explored)

     ! Print every 10th cycle
     if (mod(cycle, 10) == 1 .or. state%plateau_detected .or. explored) then
        write(*, '(a, i5, f10.4, f10.4, f10.4, l5, a)') "  ", &
             cycle, perf, state%tolerance, state%curiosity_rate, &
             state%plateau_detected, &
             merge(" ← PLATEAU!" , "             " , state%plateau_detected)
     end if
  end do

  call snapkit_visualize_snap(sf)
  call snapkit_snap_free_fn(sf)

  write(*, '(a)')
  write(*, '(a, f8.4)') "Final tolerance:  ", state%tolerance
  write(*, '(a, f8.4)') "Final curiosity:  ", state%curiosity_rate
  write(*, '(a, f8.4)') "Final holonomy:   ", state%holonomy
  write(*, '(a, f8.1)') "Attention budget: ", state%attention_budget
  write(*, '(a)')
  write(*, '(a)') "  The system learned. Tolerance adapted. "
  write(*, '(a)') "  The snap calibrated to the terrain."
  write(*, '(a)') "══════════════════════════════════════════════════════"

end program demo_learning

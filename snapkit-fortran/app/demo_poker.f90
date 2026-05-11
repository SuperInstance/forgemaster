!> @file demo_poker.f90
!! @brief Poker demonstration — multi-stream delta detection on a poker hand.
!!
!! Simulates a poker player's mind processing a hand of Texas Hold'em.
!! The player runs multiple snap streams:
!!  - pot_odds:      mathematical expectation (CUBIC topology)
!!  - opponent_tell: behavioral delta from opponent patterns (TETRAHEDRAL)
!!  - position:      seat position advantage (BINARY)
!!  - hand_strength: preflop hand quality (GRADIENT)
!!  - stress_level:  internal state monitoring (HEXAGONAL)
!!
!! The attention budget allocates cognition to the most actionable deltas.
!! Output shows snap functions, delta detector state, and budget allocations.

program demo_poker
  use snapkit
  use snapkit_snap
  use snapkit_delta
  use snapkit_attention
  use snapkit_visualization
  implicit none

  type(snapkit_snap_function_t), pointer :: sf
  type(snapkit_delta_detector_t), pointer :: detector
  type(snapkit_attention_budget_t), pointer :: budget

  type(snapkit_delta_t) :: deltas(5)
  type(snapkit_allocation_t) :: allocs(5)
  type(snapkit_snap_result_t) :: sr

  integer :: err, n_allocated, i
  character(len=32) :: stream_names(5)

  write(*, '(a)') "═══════════════════════════════════════════"
  write(*, '(a)') "  SnapKit: Poker Player Mind Demo"
  write(*, '(a)') "═══════════════════════════════════════════"
  write(*, '(a)')

  !-------------------------------------------------------------------------
  ! 1. Create a snap function for pot odds
  !-------------------------------------------------------------------------
  sf => snapkit_snap_create_ex(tolerance=0.05_wp, topology=SNAPKIT_TOPOLOGY_CUBIC, &
       baseline=0.33_wp, adaptation_rate=0.02_wp)

  write(*, '(a)') "--- Preflop Snap Snap: pot_odds ---"
  err = snapkit_snap(sf, 0.35_wp, huge(1.0_wp), sr)
  write(*, '(a, f6.3, a, f6.3, a, l1)') "  Value=0.35 → snapped=", sr%snapped, &
       " delta=", sr%delta, " within=", sr%within_tolerance

  err = snapkit_snap(sf, 0.55_wp, huge(1.0_wp), sr)
  write(*, '(a, f6.3, a, f6.3, a, l1)') "  Value=0.55 → snapped=", sr%snapped, &
       " delta=", sr%delta, " within=", sr%within_tolerance

  call snapkit_visualize_snap(sf)
  call snapkit_snap_free(sf)

  !-------------------------------------------------------------------------
  ! 2. Create delta detector with multiple streams
  !-------------------------------------------------------------------------
  detector => snapkit_detector_create()

  err = snapkit_detector_add_stream(detector, "pot_odds", &
       0.05_wp, SNAPKIT_TOPOLOGY_CUBIC, 1.0_wp, 0.8_wp)
  err = snapkit_detector_add_stream(detector, "opponent_tell", &
       0.10_wp, SNAPKIT_TOPOLOGY_TETRAHEDRAL, 0.6_wp, 0.9_wp)
  err = snapkit_detector_add_stream(detector, "position", &
       0.01_wp, SNAPKIT_TOPOLOGY_BINARY, 0.3_wp, 0.4_wp)
  err = snapkit_detector_add_stream(detector, "hand_strength", &
       0.15_wp, SNAPKIT_TOPOLOGY_GRADIENT, 0.9_wp, 0.5_wp)
  err = snapkit_detector_add_stream(detector, "stress_level", &
       0.20_wp, SNAPKIT_TOPOLOGY_HEXAGONAL, 1.0_wp, 0.7_wp)

  write(*, '(a)')
  write(*, '(a)') "--- River Card: Observing All Streams ---"

  stream_names = ["pot_odds      ", "opponent_tell ", "position      ", &
       "hand_strength ", "stress_level  "]

  ! River card flips — simulate observations
  err = snapkit_detector_observe(detector, "pot_odds", 0.72_wp)
  err = snapkit_detector_observe(detector, "opponent_tell", 0.85_wp)
  err = snapkit_detector_observe(detector, "position", 0.50_wp)
  err = snapkit_detector_observe(detector, "hand_strength", 0.91_wp)
  err = snapkit_detector_observe(detector, "stress_level", 0.30_wp)

  call snapkit_visualize_deltas(detector)

  !-------------------------------------------------------------------------
  ! 3. Attention budget allocation
  !-------------------------------------------------------------------------
  budget => snapkit_budget_create(10.0_wp, SNAPKIT_STRATEGY_ACTIONABILITY)

  do i = 1, 5
     err = snapkit_detector_current_delta(detector, trim(adjustl(stream_names(i))), deltas(i))
  end do

  err = snapkit_budget_allocate(budget, deltas, allocs, n_allocated)
  call snapkit_visualize_budget(budget, allocs, n_allocated)

  !-------------------------------------------------------------------------
  ! 4. Cleanup
  !-------------------------------------------------------------------------
  call snapkit_budget_free(budget)
  call snapkit_detector_free(detector)

  write(*, '(a)')
  write(*, '(a)') "  The hand is read. The deltas are felt. The mind is free."
  write(*, '(a)') "═══════════════════════════════════════════"

end program demo_poker

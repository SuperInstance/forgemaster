!> @file run_all.f90
!! @brief Test runner — runs all SnapKit Fortran tests.
program test_snapkit
  use snapkit
  use test_eisenstein
  use test_snap
  use test_delta
  use test_attention
  use test_topology
  implicit none

  logical :: all_pass

  all_pass = .true.

  write(*, '(a)') "╔══════════════════════════════════════════════════════╗"
  write(*, '(a)') "║        SnapKit Fortran — Test Suite                 ║"
  write(*, '(a)') "║        Version: " // SNAPKIT_VERSION_STRING // "                    ║"
  write(*, '(a)') "╚══════════════════════════════════════════════════════╝"
  write(*, '(a)')

  !--------------------------------------------------------------------------
  ! Eisenstein tests
  !--------------------------------------------------------------------------
  write(*, '(a)') "--- Eisenstein Snap ---"
  all_pass = test_eisenstein_exact() .and. all_pass
  all_pass = test_eisenstein_boundary() .and. all_pass
  all_pass = test_eisenstein_batch() .and. all_pass

  !--------------------------------------------------------------------------
  ! Snap function tests
  !--------------------------------------------------------------------------
  write(*, '(a)') "--- Snap Function ---"
  all_pass = test_snap_basic() .and. all_pass
  all_pass = test_snap_within() .and. all_pass
  all_pass = test_snap_outside() .and. all_pass
  all_pass = test_snap_create_ex() .and. all_pass
  all_pass = test_snap_calibrate() .and. all_pass

  !--------------------------------------------------------------------------
  ! Delta detector tests
  !--------------------------------------------------------------------------
  write(*, '(a)') "--- Delta Detector ---"
  all_pass = test_detector_create_free() .and. all_pass
  all_pass = test_detector_add_stream() .and. all_pass
  all_pass = test_detector_observe() .and. all_pass
  all_pass = test_detector_batch() .and. all_pass

  !--------------------------------------------------------------------------
  ! Attention budget tests
  !--------------------------------------------------------------------------
  write(*, '(a)') "--- Attention Budget ---"
  all_pass = test_budget_create_free() .and. all_pass
  all_pass = test_budget_uniform() .and. all_pass
  all_pass = test_budget_exhaust() .and. all_pass

  !--------------------------------------------------------------------------
  ! Topology/ADE tests
  !--------------------------------------------------------------------------
  write(*, '(a)') "--- Topology / ADE ---"
  all_pass = test_ade_data() .and. all_pass
  all_pass = test_recommend_topology() .and. all_pass
  all_pass = test_sheaf_create_free() .and. all_pass
  all_pass = test_sheaf_consistency() .and. all_pass

  !--------------------------------------------------------------------------
  ! Summary
  !--------------------------------------------------------------------------
  write(*, '(a)')
  if (all_pass) then
     write(*, '(a)') "╔══════════════════════════════════════════════════════╗"
     write(*, '(a)') "║           ALL TESTS PASSED                          ║"
     write(*, '(a)') "╚══════════════════════════════════════════════════════╝"
     stop 0
  else
     write(*, '(a)') "╔══════════════════════════════════════════════════════╗"
     write(*, '(a)') "║           SOME TESTS FAILED                         ║"
     write(*, '(a)') "╚══════════════════════════════════════════════════════╝"
     stop 1
  end if

end program test_snapkit

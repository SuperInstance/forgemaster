! test_clock.f90 — test T-0 clock state machine
program test_clock
  use flux_midi_flux, only: wp
  use flux_midi_clock, only: t0_clock_t, &
    CLOCK_STATE_PRE, CLOCK_STATE_T0, CLOCK_STATE_POST, &
    clock_batch_advance, clock_batch_t0_count, clock_batch_phase_sync
  implicit none

  type(t0_clock_t) :: clock
  integer :: fail_count

  fail_count = 0

  ! Test 1: initial state is PRE
  if (clock%state == CLOCK_STATE_PRE) then
    print *, "PASS test_clock_1: initial state PRE"
  else
    print *, "FAIL test_clock_1: expected PRE"
    fail_count = fail_count + 1
  end if

  ! Test 2: reset
  clock%state = CLOCK_STATE_T0
  call clock%reset()
  if (clock%state == CLOCK_STATE_PRE .and. clock%t0_crossings == 0) then
    print *, "PASS test_clock_2: reset"
  else
    print *, "FAIL test_clock_2: reset failed"
    fail_count = fail_count + 1
  end if

  ! Test 3: T-0 crossing detection
  call clock%advance(1.0_wp, 0.0_wp)    ! prev=0, flux=1 → no crossing
  call clock%advance(-0.5_wp, 1.0_wp)   ! prev=1, flux=-0.5 → crossing
  if (clock%state == CLOCK_STATE_T0) then
    print *, "PASS test_clock_3: T-0 crossing detected"
  else
    print *, "FAIL test_clock_3: expected T0 state"
    fail_count = fail_count + 1
  end if

  ! Test 4: post-T0 decay
  call clock%advance(0.001_wp, -0.5_wp)
  if (clock%state == CLOCK_STATE_POST) then
    print *, "PASS test_clock_4: post-T0 state"
  else
    print *, "FAIL test_clock_4: expected POST"
    fail_count = fail_count + 1
  end if

  ! Test 5: batch advance
  block
    type(t0_clock_t) :: clocks(3)
    real(wp) :: flux_vals(3), prev_vals(3)

    flux_vals = [-1.0_wp, 0.5_wp, 2.0_wp]
    prev_vals = [1.0_wp, -0.3_wp, -1.0_wp]
    call clock_batch_advance(clocks, flux_vals, prev_vals)
    if (clocks(1)%state == CLOCK_STATE_T0 .and. &
        clocks(3)%state == CLOCK_STATE_T0) then
      print *, "PASS test_clock_5: batch advance"
    else
      print *, "FAIL test_clock_5: batch advance incorrect states"
      fail_count = fail_count + 1
    end if
  end block

  ! Test 6: batch count
  block
    type(t0_clock_t) :: clocks(4)
    integer :: t0_cnt
    integer :: i

    do i = 1, 4
      clocks(i)%state = CLOCK_STATE_PRE
    end do
    clocks(2)%state = CLOCK_STATE_T0
    clocks(4)%state = CLOCK_STATE_T0
    t0_cnt = clock_batch_t0_count(clocks)
    if (t0_cnt == 2) then
      print *, "PASS test_clock_6: batch count"
    else
      print *, "FAIL test_clock_6: expected 2, got", t0_cnt
      fail_count = fail_count + 1
    end if
  end block

  ! Test 7: phase sync
  block
    type(t0_clock_t) :: clocks(2)
    call clock_batch_phase_sync(clocks, 3.14_wp)
    if (all(abs([clocks(1)%tick_phase, clocks(2)%tick_phase] - 3.14_wp) < 1.0e-12_wp)) then
      print *, "PASS test_clock_7: phase sync"
    else
      print *, "FAIL test_clock_7: phase not synchronized"
      fail_count = fail_count + 1
    end if
  end block

  if (fail_count == 0) then
    print *, "ALL test_clock TESTS PASSED"
  else
    print *, fail_count, " TEST(S) FAILED in test_clock"
    stop 1
  end if
end program test_clock

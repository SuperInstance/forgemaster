! test_snap.f90 — test Eisenstein snap and lattice operations
program test_snap
  use flux_midi_flux, only: wp
  use flux_midi_snap, only: eisenstein_snap, eisenstein_lattice_radius, &
    batch_eisenstein_snap, batch_lattice_radius
  implicit none

  real(wp), allocatable :: values(:,:), snapped(:,:), radii(:,:)
  integer :: fail_count

  fail_count = 0

  ! Test 1: integer values snap to themselves
  if (abs(eisenstein_snap(3.0_wp) - 3.0_wp) < 1.0e-14_wp) then
    print *, "PASS test_snap_1: integer → self"
  else
    print *, "FAIL test_snap_1: expected 3.0"
    fail_count = fail_count + 1
  end if

  ! Test 2: half-integers round to nearest even
  if (abs(eisenstein_snap(2.5_wp) - 3.0_wp) < 1.0e-14_wp .or. &
      abs(eisenstein_snap(2.5_wp) - 2.0_wp) < 1.0e-14_wp) then
    print *, "PASS test_snap_2: half-integer rounds"
  else
    print *, "FAIL test_snap_2: unexpected snap"
    fail_count = fail_count + 1
  end if

  ! Test 3: lattice radius property
  if (abs(eisenstein_lattice_radius(3.2_wp) - 0.2_wp) < 1.0e-14_wp .or. &
      abs(eisenstein_lattice_radius(3.2_wp) - 0.8_wp) < 1.0e-14_wp) then
    print *, "PASS test_snap_3: lattice radius"
  else
    print *, "FAIL test_snap_3: radius property"
    fail_count = fail_count + 1
  end if

  ! Test 4: integer lattice radius = 0
  if (abs(eisenstein_lattice_radius(5.0_wp)) < 1.0e-14_wp) then
    print *, "PASS test_snap_4: integer radius zero"
  else
    print *, "FAIL test_snap_4: expected zero"
    fail_count = fail_count + 1
  end if

  ! Test 5: batch snap
  allocate(values(2,3))
  values(1,:) = [1.2_wp, 3.7_wp, -0.4_wp]
  values(2,:) = [2.5_wp, -3.1_wp, 0.0_wp]
  snapped = batch_eisenstein_snap(values)
  if (size(snapped,1) == 2 .and. size(snapped,2) == 3) then
    print *, "PASS test_snap_5: batch shape correct"
  else
    print *, "FAIL test_snap_5: shape mismatch"
    fail_count = fail_count + 1
  end if

  ! Test 6: snap element check
  block
    real(wp) :: s(2,3)
    s = batch_eisenstein_snap(values)
    if (abs(s(1,1) - 1.0_wp) < 1.0e-14_wp .and. &
        abs(s(1,2) - 4.0_wp) < 1.0e-14_wp) then
      print *, "PASS test_snap_6: snap values correct"
    else
      print *, "FAIL test_snap_6: snap values"
      fail_count = fail_count + 1
    end if
  end block

  ! Test 7: batch radii
  radii = batch_lattice_radius(values)
  if (radii(1,1) > 0.0_wp .and. abs(radii(2,3)) < 1.0e-14_wp) then
    print *, "PASS test_snap_7: batch radii correct"
  else
    print *, "FAIL test_snap_7: radii incorrect"
    fail_count = fail_count + 1
  end if

  deallocate(values, snapped, radii)

  if (fail_count == 0) then
    print *, "ALL test_snap TESTS PASSED"
  else
    print *, fail_count, " TEST(S) FAILED in test_snap"
    stop 1
  end if
end program test_snap

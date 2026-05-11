! test_flux.f90 — test tensor flux operations
program test_flux
  use flux_midi_flux, only: wp, tensor_flux, flux_normalize, flux_power_spectrum
  implicit none

  real(wp), allocatable :: tensor(:,:,:)
  real(wp), allocatable :: flux(:,:), norm_flux(:,:), power(:,:)
  integer :: n, m, k
  integer :: fail_count

  fail_count = 0
  n = 3
  m = 4
  k = 2

  ! Test 1: tensor_flux basic shape
  allocate(tensor(n, m, k))
  tensor = 1.0_wp
  flux = tensor_flux(tensor)
  if (size(flux,1) /= n .or. size(flux,2) /= m) then
    print *, "FAIL test_flux_1: shape mismatch"
    fail_count = fail_count + 1
  else
    print *, "PASS test_flux_1: shape correct"
  end if

  ! Test 2: constant tensor → zero flux
  if (all(abs(flux) < 1.0e-14_wp)) then
    print *, "PASS test_flux_2: constant tensor → zero flux"
  else
    print *, "FAIL test_flux_2: expected zero flux"
    fail_count = fail_count + 1
  end if

  ! Test 3: non-constant tensor → positive flux
  tensor(1,1,1) = 10.0_wp
  tensor(1,1,2) = 0.0_wp
  flux = tensor_flux(tensor)
  if (flux(1,1) > 0.0_wp) then
    print *, "PASS test_flux_3: variable tensor → positive flux"
  else
    print *, "FAIL test_flux_3: expected positive flux"
    fail_count = fail_count + 1
  end if

  ! Test 4: flux_normalize units
  norm_flux = flux_normalize(flux)
  if (abs(sqrt(sum(norm_flux(1,:)**2)) - 1.0_wp) < 1.0e-12_wp) then
    print *, "PASS test_flux_4: normalization → unit vectors"
  else
    print *, "FAIL test_flux_4: expected unit norm"
    fail_count = fail_count + 1
  end if

  ! Test 5: zero row normalization
  norm_flux = flux_normalize(reshape([0.0_wp, 0.0_wp, 0.0_wp, 0.0_wp], [1,4]))
  if (all(abs(norm_flux) < 1.0e-14_wp)) then
    print *, "PASS test_flux_5: zero row → zero output"
  else
    print *, "FAIL test_flux_5: expected zero"
    fail_count = fail_count + 1
  end if

  ! Test 6: power spectrum shape
  power = flux_power_spectrum(flux)
  if (size(power,2) == m/2 + 1) then
    print *, "PASS test_flux_6: power spectrum shape correct"
  else
    print *, "FAIL test_flux_6: expected shape (N, M/2+1)"
    fail_count = fail_count + 1
  end if

  deallocate(tensor, flux, norm_flux, power)

  if (fail_count == 0) then
    print *, "ALL test_flux TESTS PASSED"
  else
    print *, fail_count, " TEST(S) FAILED in test_flux"
    stop 1
  end if
end program test_flux

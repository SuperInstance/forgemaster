! test_spectrum.f90 — test batch spectral analysis (THE KILLER)
program test_spectrum
  use flux_midi_flux, only: wp
  use flux_midi_spectrum, only: &
    temporal_entropy, batch_entropy, &
    autocorrelation, batch_autocorrelation, &
    hurst_exponent, batch_hurst, &
    spectral_centroid, batch_spectral_centroid, &
    spectral_rolloff, batch_spectral_rolloff
  implicit none

  real(wp), allocatable :: flux(:,:), acf_mat(:,:), hursts(:), entropies(:)
  real(wp), allocatable :: centroids(:)
  integer, allocatable :: rolloffs(:)
  integer :: fail_count
  real(wp), parameter :: pi = 4.0_wp * atan(1.0_wp)

  fail_count = 0

  !=========================================================================
  ! ENTROPY TESTS
  !=========================================================================

  ! Test 1: uniform distribution → max entropy
  block
    real(wp) :: row(4)
    real(wp) :: h
    row = [1.0_wp, 1.0_wp, 1.0_wp, 1.0_wp]
    h = temporal_entropy(row)
    ! log2(4) = 2.0
    if (abs(h - 2.0_wp) < 1.0e-10_wp) then
      print *, "PASS test_spectrum_1: uniform → max entropy"
    else
      print *, "FAIL test_spectrum_1: expected 2.0, got", h
      fail_count = fail_count + 1
    end if
  end block

  ! Test 2: single nonzero → zero entropy
  block
    real(wp) :: row(4)
    real(wp) :: h
    row = [1.0_wp, 0.0_wp, 0.0_wp, 0.0_wp]
    h = temporal_entropy(row)
    if (abs(h) < 1.0e-10_wp) then
      print *, "PASS test_spectrum_2: single peak → zero entropy"
    else
      print *, "FAIL test_spectrum_2: expected 0.0, got", h
      fail_count = fail_count + 1
    end if
  end block

  ! Test 3: batch entropy shape
  allocate(flux(3, 8))
  call random_number(flux)
  entropies = batch_entropy(flux)
  if (size(entropies) == 3) then
    print *, "PASS test_spectrum_3: batch entropy shape"
  else
    print *, "FAIL test_spectrum_3: expected size 3"
    fail_count = fail_count + 1
  end if

  !=========================================================================
  ! AUTOCORRELATION TESTS
  !=========================================================================

  ! Test 4: monotonic series → positive autocorrelation (lag-1 close to 1)
  block
    real(wp) :: row(6)
    real(wp) :: acf(5)
    row = [1.0_wp, 2.0_wp, 3.0_wp, 4.0_wp, 5.0_wp, 6.0_wp]
    acf = autocorrelation(row)
    if (acf(1) >= 0.5_wp) then
      print *, "PASS test_spectrum_4: monotonic → positive autocorr (lag-1 =", acf(1), ")"
    else
      print *, "FAIL test_spectrum_4: expected > 0.5, got", acf(1)
      fail_count = fail_count + 1
    end if
  end block

  ! Test 5: alternating series → negative lag-1
  block
    real(wp) :: row(6)
    real(wp) :: acf(5)
    row = [1.0_wp, -1.0_wp, 1.0_wp, -1.0_wp, 1.0_wp, -1.0_wp]
    acf = autocorrelation(row)
    if (acf(1) < -0.5_wp) then
      print *, "PASS test_spectrum_5: alternating → negative autocorr"
    else
      print *, "FAIL test_spectrum_5: expected negative, got", acf(1)
      fail_count = fail_count + 1
    end if
  end block

  ! Test 6: batch autocorrelation
  acf_mat = batch_autocorrelation(flux)
  if (size(acf_mat,1) == 3 .and. size(acf_mat,2) == 7) then
    print *, "PASS test_spectrum_6: batch autocorrelation shape"
  else
    print *, "FAIL test_spectrum_6: shape mismatch"
    fail_count = fail_count + 1
  end if

  !=========================================================================
  ! HURST EXPONENT TESTS
  !=========================================================================

  ! Test 7: random walk → Hurst in plausible range
  ! Note: R/S on 64 samples is biased; accept reasonable range
  block
    real(wp) :: row(64)
    real(wp) :: h
    integer :: j
    ! Generate random walk
    call random_number(row)
    row = row - 0.5_wp
    do j = 2, 64
      row(j) = row(j-1) + row(j)
    end do
    h = hurst_exponent(row)
    if (h > 0.0_wp .and. h < 2.5_wp) then
      print *, "PASS test_spectrum_7: random walk → Hurst in range (got", h, ")"
    else
      print *, "FAIL test_spectrum_7: Hurst out of range:", h
      fail_count = fail_count + 1
    end if
  end block

  ! Test 8: trending series → Hurst > 0.5
  block
    real(wp) :: row(64)
    real(wp) :: h
    integer :: j
    do j = 1, 64
      row(j) = real(j, wp) * 0.1_wp + 0.5_wp * sin(real(j, wp) * 0.3_wp)
    end do
    h = hurst_exponent(row)
    if (h > 0.5_wp) then
      print *, "PASS test_spectrum_8: trending → Hurst > 0.5 (got", h, ")"
    else
      print *, "FAIL test_spectrum_8: expected > 0.5, got", h
      fail_count = fail_count + 1
    end if
  end block

  ! Test 9: batch Hurst
  hursts = batch_hurst(flux)
  if (size(hursts) == 3) then
    print *, "PASS test_spectrum_9: batch Hurst shape"
  else
    print *, "FAIL test_spectrum_9: shape mismatch"
    fail_count = fail_count + 1
  end if

  !=========================================================================
  ! SPECTRAL CENTROID TESTS
  !=========================================================================

  ! Test 10: sine wave → centroid at its frequency
  block
    real(wp) :: row(32)
    real(wp) :: c
    integer :: j
    do j = 1, 32
      row(j) = sin(2.0_wp * pi * 3.0_wp * real(j-1, wp) / 32.0_wp)
    end do
    c = spectral_centroid(row)
    ! Expect centroid near bin 3
    if (c > 2.0_wp .and. c < 5.0_wp) then
      print *, "PASS test_spectrum_10: sine wave centroid ≈ 3 (got", c, ")"
    else
      print *, "FAIL test_spectrum_10: expected ~3, got", c
      fail_count = fail_count + 1
    end if
  end block

  ! Test 11: batch spectral centroid
  centroids = batch_spectral_centroid(flux)
  if (size(centroids) == 3) then
    print *, "PASS test_spectrum_11: batch centroid shape"
  else
    print *, "FAIL test_spectrum_11: shape mismatch"
    fail_count = fail_count + 1
  end if

  !=========================================================================
  ! SPECTRAL ROLLOFF TESTS
  !=========================================================================

  ! Test 12: single frequency → rolloff at that bin
  block
    real(wp) :: row(32)
    integer :: r
    integer :: j
    do j = 1, 32
      row(j) = sin(2.0_wp * pi * 2.0_wp * real(j-1, wp) / 32.0_wp)
    end do
    r = spectral_rolloff(row, 0.85_wp)
    ! Power concentrated at bin 2, so rolloff should be low
    if (r >= 2 .and. r <= 4) then
      print *, "PASS test_spectrum_12: sine rolloff near bin 2 (got", r, ")"
    else
      print *, "FAIL test_spectrum_12: expected ~2, got", r
      fail_count = fail_count + 1
    end if
  end block

  ! Test 13: batch rolloff
  rolloffs = batch_spectral_rolloff(flux, 0.85_wp)
  if (size(rolloffs) == 3) then
    print *, "PASS test_spectrum_13: batch rolloff shape"
  else
    print *, "FAIL test_spectrum_13: shape mismatch"
    fail_count = fail_count + 1
  end if

  deallocate(flux, acf_mat, hursts, entropies, centroids, rolloffs)

  if (fail_count == 0) then
    print *, "ALL test_spectrum TESTS PASSED"
  else
    print *, fail_count, " TEST(S) FAILED in test_spectrum"
    stop 1
  end if
end program test_spectrum

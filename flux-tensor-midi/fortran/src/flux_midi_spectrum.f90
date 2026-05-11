! FLUX-Tensor-MIDI : flux_midi_spectrum.f90
! THE KILLER — batch spectral analysis for FLUX-Tensor-MIDI
!
! All functions operate on flux(N, M) — N rooms × M time intervals.
! No external deps. Pure Fortran 2008.
module flux_midi_spectrum
  use flux_midi_flux, only: wp
  implicit none
  private

  public :: temporal_entropy, batch_entropy
  public :: autocorrelation, batch_autocorrelation
  public :: hurst_exponent, batch_hurst
  public :: spectral_centroid, batch_spectral_centroid
  public :: spectral_rolloff, batch_spectral_rolloff

contains

  !========================================================================
  ! TEMPORAL ENTROPY — batch Shannon entropy across N rooms
  !
  ! For each room, compute entropy of its flux distribution over M intervals.
  ! H(i) = -sum_j p(i,j) * log2(p(i,j))
  ! where p(i,j) = |flux(i,j)| / sum_k |flux(i,k)|
  !========================================================================

  !--------------------------------------------------------------
  ! temporal_entropy: Shannon entropy of a single time series
  !--------------------------------------------------------------
  pure real(wp) function temporal_entropy(flux_row) result(entropy)
    real(wp), intent(in) :: flux_row(:)
    real(wp), allocatable :: p(:)
    real(wp) :: total, eps
    integer :: j, m

    m = size(flux_row)
    eps = 1.0e-30_wp  ! avoid log(0)

    ! Get absolute values
    allocate(p(m))
    total = sum(abs(flux_row))
    if (total <= eps) then
      entropy = 0.0_wp
      deallocate(p)
      return
    end if

    p = abs(flux_row) / total
    entropy = 0.0_wp
    do concurrent (j = 1:m)
      if (p(j) > eps) entropy = entropy - p(j) * log(p(j)) / log(2.0_wp)
    end do
    deallocate(p)
  end function temporal_entropy

  !--------------------------------------------------------------
  ! batch_entropy: entropy for every room in N×M flux matrix
  !   Returns array(N) of Shannon entropies
  !--------------------------------------------------------------
  pure function batch_entropy(flux) result(entropies)
    real(wp), intent(in) :: flux(:,:)   ! (N, M)
    real(wp) :: entropies(size(flux,1))
    integer :: i, n

    n = size(flux,1)
    do concurrent (i = 1:n)
      entropies(i) = temporal_entropy(flux(i,:))
    end do
  end function batch_entropy

  !========================================================================
  ! AUTOCORRELATION
  !
  ! Autocorrelation of each flux row for lags 1..M-1.
  ! R(k) = sum_j (x_j - μ)(x_{j+k} - μ) / sum_j (x_j - μ)^2
  !========================================================================

  !--------------------------------------------------------------
  ! autocorrelation: compute autocorrelation for all lags
  !--------------------------------------------------------------
  pure function autocorrelation(series) result(acf)
    real(wp), intent(in) :: series(:)
    real(wp) :: acf(size(series) - 1)
    real(wp) :: mean_val, var
    integer :: m, k

    m = size(series)
    if (m < 3) then
      acf = 0.0_wp
      return
    end if

    mean_val = sum(series) / real(m, wp)
    var = sum((series - mean_val)**2)
    if (var <= 0.0_wp) then
      acf = 0.0_wp
      return
    end if

    do concurrent (k = 1:m - 1)
      acf(k) = sum((series(:m-k) - mean_val) * (series(1+k:) - mean_val)) / var
    end do
  end function autocorrelation

  !--------------------------------------------------------------
  ! batch_autocorrelation: autocorrelation for all N rooms
  !   Returns (N, M-1) — autocorrelation at each lag for each room
  !--------------------------------------------------------------
  pure function batch_autocorrelation(flux) result(acf_mat)
    real(wp), intent(in) :: flux(:,:)          ! (N, M)
    real(wp) :: acf_mat(size(flux,1), size(flux,2)-1)
    integer :: i, n

    n = size(flux,1)
    do concurrent (i = 1:n)
      acf_mat(i,:) = autocorrelation(flux(i,:))
    end do
  end function batch_autocorrelation

  !========================================================================
  ! HURST EXPONENT — R/S analysis with log-log regression
  !
  ! For each room's flux time series:
  !   1. Subdivide into blocks of increasing size
  !   2. Compute R/S for each block size
  !   3. Log-log regression: log(R/S) ~ H * log(n)
  !
  ! H > 0.5 → persistent (trending)
  ! H < 0.5 → anti-persistent (mean-reverting)
  ! H = 0.5 → random walk
  !========================================================================

  !--------------------------------------------------------------
  ! hurst_exponent: compute Hurst for a single time series
  !--------------------------------------------------------------
  pure real(wp) function hurst_exponent(series) result(h)
    real(wp), intent(in) :: series(:)
    integer :: m, n_blocks, i, j, k, b
    real(wp), allocatable :: log_rs(:), log_n(:)
    real(wp) :: mean_block, range, std_dev
    real(wp) :: x, sum_x, sum_y, sum_xx, sum_xy
    real(wp) :: beta, denom

    m = size(series)
    if (m < 10) then
      h = 0.5_wp  ! default for insufficient data
      return
    end if

    ! Determine block sizes — powers of 2 for clean subdivision
    n_blocks = 0
    b = 4
    do while (b <= m/2)
      n_blocks = n_blocks + 1
      b = b * 2
    end do

    if (n_blocks < 3) then
      h = 0.5_wp
      return
    end if

    allocate(log_rs(n_blocks), log_n(n_blocks))

    k = 0
    b = 4
    do while (b <= m/2)
      k = k + 1
      n_blocks = m / b  ! number of blocks at this size

      ! Compute mean R/S across all blocks at this block size
      range = 0.0_wp
      std_dev = 0.0_wp
      do i = 1, n_blocks
        ! Extract block
        mean_block = sum(series((i-1)*b+1:i*b)) / real(b, wp)
        ! Cumulated deviations
        x = 0.0_wp
        do j = 1, b
          x = x + (series((i-1)*b+j) - mean_block)
          if (j == 1) then
            range = abs(x)
            std_dev = (series((i-1)*b+j) - mean_block)**2
          else
            range = max(range, abs(x))
            std_dev = std_dev + (series((i-1)*b+j) - mean_block)**2
          end if
        end do
      end do

      ! Average R/S across blocks
      std_dev = sqrt(std_dev / real(b * n_blocks, wp))
      if (std_dev > 0.0_wp) then
        log_rs(k) = log(range / (real(n_blocks, wp) * std_dev))
      else
        log_rs(k) = 0.0_wp
      end if
      log_n(k) = log(real(b, wp))

      b = b * 2
    end do

    ! OLS regression: log(R/S) = H * log(n) + C
    sum_x = sum(log_n)
    sum_y = sum(log_rs)
    sum_xx = sum(log_n**2)
    sum_xy = sum(log_n * log_rs)

    denom = real(k, wp) * sum_xx - sum_x**2
    if (abs(denom) > 1.0e-30_wp) then
      beta = (real(k, wp) * sum_xy - sum_x * sum_y) / denom
      h = beta  ! Hurst = slope
    else
      h = 0.5_wp
    end if

    deallocate(log_rs, log_n)
  end function hurst_exponent

  !--------------------------------------------------------------
  ! batch_hurst: Hurst exponent for all N rooms
  !   Returns array(N)
  !--------------------------------------------------------------
  pure function batch_hurst(flux) result(hursts)
    real(wp), intent(in) :: flux(:,:)
    real(wp) :: hursts(size(flux,1))
    integer :: i, n

    n = size(flux,1)
    do concurrent (i = 1:n)
      hursts(i) = hurst_exponent(flux(i,:))
    end do
  end function batch_hurst

  !========================================================================
  ! SPECTRAL CENTROID — weighted mean of power spectrum
  !========================================================================

  !--------------------------------------------------------------
  ! spectral_centroid: weighted mean frequency of power spectrum
  !--------------------------------------------------------------
  pure real(wp) function spectral_centroid(flux_row) result(centroid)
    real(wp), intent(in) :: flux_row(:)
    real(wp), allocatable :: power(:)
    integer :: m, k, j
    real(wp) :: total_power, pi, arg, re, im

    m = size(flux_row)
    pi = 4.0_wp * atan(1.0_wp)
    allocate(power(m/2+1))

    ! Simple power spectrum via DFT
    do k = 1, m/2+1
      re = 0.0_wp
      im = 0.0_wp
      do j = 1, m
        arg = 2.0_wp * pi * real((k-1)*(j-1), wp) / real(m, wp)
        re = re + flux_row(j) * cos(arg) / real(m, wp)
        im = im + flux_row(j) * sin(arg) / real(m, wp)
      end do
      power(k) = re*re + im*im
    end do

    total_power = sum(power)
    if (total_power > 0.0_wp) then
      centroid = 0.0_wp
      do k = 1, m/2+1
        centroid = centroid + power(k) * real(k-1, wp)
      end do
      centroid = centroid / total_power
    else
      centroid = 0.0_wp
    end if

    deallocate(power)
  end function spectral_centroid

  !--------------------------------------------------------------
  ! batch_spectral_centroid: centroids for all N rooms
  !--------------------------------------------------------------
  pure function batch_spectral_centroid(flux) result(centroids)
    real(wp), intent(in) :: flux(:,:)
    real(wp) :: centroids(size(flux,1))
    integer :: i, n

    n = size(flux,1)
    do concurrent (i = 1:n)
      centroids(i) = spectral_centroid(flux(i,:))
    end do
  end function batch_spectral_centroid

  !========================================================================
  ! SPECTRAL ROLLOFF — frequency below which 85% of power is contained
  !========================================================================

  !--------------------------------------------------------------
  ! spectral_rolloff: threshold frequency for cumulative power
  !--------------------------------------------------------------
  pure integer function spectral_rolloff(flux_row, rolloff_percent) result(rolloff)
    real(wp), intent(in) :: flux_row(:)
    real(wp), intent(in) :: rolloff_percent  ! e.g., 0.85
    real(wp), allocatable :: power(:)
    real(wp) :: total_power, cum_power, arg, re, im, pi
    integer :: m, k, j

    m = size(flux_row)
    pi = 4.0_wp * atan(1.0_wp)
    allocate(power(m/2+1))

    ! Power spectrum via DFT (positive frequencies)
    do k = 1, m/2+1
      re = 0.0_wp
      im = 0.0_wp
      do j = 1, m
        arg = 2.0_wp * pi * real((k-1)*(j-1), wp) / real(m, wp)
        re = re + flux_row(j) * cos(arg) / real(m, wp)
        im = im + flux_row(j) * sin(arg) / real(m, wp)
      end do
      power(k) = re*re + im*im
    end do

    total_power = sum(power)
    if (total_power > 0.0_wp) then
      cum_power = 0.0_wp
      rolloff = m/2
      do k = 1, m/2+1
        cum_power = cum_power + power(k)
        if (cum_power / total_power >= rolloff_percent) then
          rolloff = k - 1  ! zero-indexed frequency bin
          deallocate(power)
          return
        end if
      end do
    else
      rolloff = 0
    end if

    deallocate(power)
  end function spectral_rolloff

  !--------------------------------------------------------------
  ! batch_spectral_rolloff: rolloff for all N rooms
  !--------------------------------------------------------------
  pure function batch_spectral_rolloff(flux, rolloff_percent) result(rolloffs)
    real(wp), intent(in) :: flux(:,:)
    real(wp), intent(in) :: rolloff_percent
    integer :: rolloffs(size(flux,1))
    integer :: i, n

    n = size(flux,1)
    do concurrent (i = 1:n)
      rolloffs(i) = spectral_rolloff(flux(i,:), rolloff_percent)
    end do
  end function batch_spectral_rolloff

end module flux_midi_spectrum

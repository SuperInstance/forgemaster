!> Spectral analysis — entropy, Hurst exponent, autocorrelation.
!> Fortran 2008 port of snapkit spectral module.
!> Column-major friendly, pure where possible, BLAS-ready layout.
module snapkit_spectral
    implicit none
    private
    public :: entropy, autocorrelation, hurst_exponent, spectral_summary
    public :: spectral_batch, spectral_result

    real(8), parameter :: LOG2_INV = 1.4426950408889634d0  ! 1/ln(2)
    real(8), parameter :: INV_E    = 0.36787944117144233d0 ! 1/e

    type :: spectral_result
        real(8) :: entropy_bits    = 0.0d0
        real(8) :: hurst           = 0.5d0
        real(8) :: autocorr_lag1   = 0.0d0
        real(8) :: autocorr_decay  = 0.0d0
        logical :: is_stationary   = .false.
    end type

contains

    !> Shannon entropy via histogram binning (bits).
    pure function entropy(data, bins) result(h)
        real(8), intent(in) :: data(:)
        integer, intent(in), optional :: bins
        real(8) :: h

        integer :: n, nb, i, idx, c
        real(8) :: min_val, max_val, inv_range, p
        integer, allocatable :: counts(:)

        n = size(data)
        if (n < 2) then
            h = 0.0d0
            return
        end if

        nb = 10
        if (present(bins)) nb = bins

        ! Find min/max
        min_val = data(1)
        max_val = data(1)
        do i = 2, n
            if (data(i) < min_val) min_val = data(i)
            if (data(i) > max_val) max_val = data(i)
        end do

        if (max_val == min_val) then
            h = 0.0d0
            return
        end if

        inv_range = dble(nb) / (max_val - min_val)
        allocate(counts(nb))
        counts = 0

        do i = 1, n
            idx = int((data(i) - min_val) * inv_range) + 1
            if (idx > nb) idx = nb
            if (idx < 1) idx = 1
            counts(idx) = counts(idx) + 1
        end do

        h = 0.0d0
        do i = 1, nb
            c = counts(i)
            if (c > 0) then
                p = dble(c) / dble(n)
                h = h - p * log(p) * LOG2_INV
            end if
        end do
    end function

    !> Normalized autocorrelation up to max_lag.
    function autocorrelation(data, max_lag_in) result(acf)
        real(8), intent(in) :: data(:)
        integer, intent(in), optional :: max_lag_in
        real(8), allocatable :: acf(:)

        integer :: n, max_lag, lag, t, limit
        real(8) :: mean_val, inv_n, r0, inv_r0, rk
        real(8), allocatable :: centered(:)

        n = size(data)
        if (n < 2) then
            allocate(acf(1))
            acf(1) = 1.0d0
            return
        end if

        max_lag = n / 2
        if (present(max_lag_in)) max_lag = min(max_lag_in, n - 1)

        inv_n = 1.0d0 / dble(n)

        ! Center the data
        mean_val = sum(data) * inv_n
        allocate(centered(n))
        centered = data - mean_val

        ! Variance
        r0 = dot_product(centered, centered) * inv_n
        if (r0 == 0.0d0) then
            allocate(acf(max_lag + 1))
            acf(1) = 1.0d0
            acf(2:) = 0.0d0
            return
        end if

        inv_r0 = 1.0d0 / r0
        allocate(acf(max_lag + 1))

        do lag = 0, max_lag
            rk = 0.0d0
            limit = n - lag
            do t = 1, limit
                rk = rk + centered(t) * centered(t + lag)
            end do
            acf(lag + 1) = rk * inv_n * inv_r0
        end do
    end function

    !> Hurst exponent via R/S analysis.
    function hurst_exponent(data) result(h)
        real(8), intent(in) :: data(:)
        real(8) :: h

        integer :: n, i, size_val, num_sub, start, j, t
        integer :: n_pts, rs_count
        real(8) :: inv_n, mean_val, inv_size, sub_mean
        real(8) :: running, cum_min, cum_max, r_val, var_val, d_val
        real(8) :: rs_sum, avg_rs
        real(8) :: sum_x, sum_y, sum_xy, sum_x2, denom
        real(8), allocatable :: centered(:), sizes(:), rs_values(:)
        integer, allocatable :: test_sizes(:)
        integer :: nsizes, prev_s

        n = size(data)
        if (n < 20) then
            h = 0.5d0
            return
        end if

        inv_n = 1.0d0 / dble(n)
        mean_val = sum(data) * inv_n
        allocate(centered(n))
        centered = data - mean_val

        ! Build geometric test sizes: 16, 32, 48, 64, ...
        nsizes = 0
        size_val = 16
        prev_s = 0
        do while (size_val <= n / 2)
            nsizes = nsizes + 1
            prev_s = size_val
            if (size_val * 2 <= n / 2) then
                size_val = size_val * 2
            else
                size_val = int(dble(size_val) * 1.5d0)
            end if
            if (size_val == prev_s) exit
        end do

        if (nsizes == 0) then
            if (n >= 8) nsizes = 1
        end if
        if (nsizes == 0) then
            h = 0.5d0
            return
        end if

        allocate(test_sizes(nsizes))
        nsizes = 0
        size_val = 16
        prev_s = 0
        do while (size_val <= n / 2)
            nsizes = nsizes + 1
            test_sizes(nsizes) = size_val
            prev_s = size_val
            if (size_val * 2 <= n / 2) then
                size_val = size_val * 2
            else
                size_val = int(dble(size_val) * 1.5d0)
            end if
            if (size_val == prev_s) exit
        end do

        ! Compute R/S for each size
        allocate(sizes(nsizes), rs_values(nsizes))
        n_pts = 0

        do i = 1, nsizes
            size_val = test_sizes(i)
            if (size_val < 4 .or. size_val > n) cycle

            num_sub = n / size_val
            if (num_sub < 1) cycle

            inv_size = 1.0d0 / dble(size_val)
            rs_sum = 0.0d0
            rs_count = 0

            do j = 1, num_sub
                start = (j - 1) * size_val + 1
                sub_mean = sum(centered(start:start+size_val-1)) * inv_size

                ! Cumulative deviations with inline min/max
                running = 0.0d0
                cum_min = 0.0d0
                cum_max = 0.0d0
                var_val = 0.0d0
                do t = 1, size_val
                    d_val = centered(start + t - 1) - sub_mean
                    running = running + d_val
                    if (running < cum_min) cum_min = running
                    if (running > cum_max) cum_max = running
                    var_val = var_val + d_val * d_val
                end do

                r_val = cum_max - cum_min
                var_val = var_val * inv_size

                if (var_val > 1.0d-20) then
                    rs_sum = rs_sum + r_val / sqrt(var_val)
                    rs_count = rs_count + 1
                end if
            end do

            if (rs_count > 0) then
                avg_rs = rs_sum / dble(rs_count)
                if (avg_rs > 0.0d0) then
                    n_pts = n_pts + 1
                    sizes(n_pts) = dble(size_val)
                    rs_values(n_pts) = avg_rs
                end if
            end if
        end do

        if (n_pts < 2) then
            h = 0.5d0
            return
        end if

        ! Linear regression on log-log
        sum_x = 0.0d0; sum_y = 0.0d0; sum_xy = 0.0d0; sum_x2 = 0.0d0
        do i = 1, n_pts
            d_val = log(sizes(i))
            r_val = log(rs_values(i))
            sum_x = sum_x + d_val
            sum_y = sum_y + r_val
            sum_xy = sum_xy + d_val * r_val
            sum_x2 = sum_x2 + d_val * d_val
        end do

        denom = dble(n_pts) * sum_x2 - sum_x * sum_x
        if (denom == 0.0d0) then
            h = 0.5d0
            return
        end if

        h = (dble(n_pts) * sum_xy - sum_x * sum_y) / denom

        ! Clamp to [0, 1]
        if (h < 0.0d0) h = 0.0d0
        if (h > 1.0d0) h = 1.0d0
    end function

    !> Full spectral summary of a signal.
    function spectral_summary(data, bins, max_lag_in) result(sr)
        real(8), intent(in) :: data(:)
        integer, intent(in), optional :: bins, max_lag_in
        type(spectral_result) :: sr

        real(8), allocatable :: acf(:)
        integer :: i, nb, ml

        nb = 10
        if (present(bins)) nb = bins

        sr%entropy_bits = entropy(data, nb)
        sr%hurst = hurst_exponent(data)

        if (present(max_lag_in)) then
            acf = autocorrelation(data, max_lag_in)
        else
            acf = autocorrelation(data)
        end if

        sr%autocorr_lag1 = 0.0d0
        if (size(acf) > 1) sr%autocorr_lag1 = acf(2)

        ! Find decay lag (first lag where |acf| < 1/e)
        sr%autocorr_decay = dble(size(acf))
        do i = 2, size(acf)
            if (abs(acf(i)) < INV_E) then
                sr%autocorr_decay = dble(i - 1)  ! 0-indexed lag
                exit
            end if
        end do

        ! Stationarity check
        sr%is_stationary = (sr%hurst >= 0.4d0 .and. sr%hurst <= 0.6d0) .and. &
                           (abs(sr%autocorr_lag1) < 0.3d0)
    end function

    !> Batch spectral summary for multiple time series.
    !> Each column of data_2d is one time series (column-major layout).
    subroutine spectral_batch(data_2d, results, bins, max_lag_in)
        real(8), intent(in)  :: data_2d(:,:)
        type(spectral_result), intent(out) :: results(:)
        integer, intent(in), optional :: bins, max_lag_in
        integer :: i

        do i = 1, size(data_2d, 2)
            if (present(bins) .and. present(max_lag_in)) then
                results(i) = spectral_summary(data_2d(:,i), bins, max_lag_in)
            else if (present(bins)) then
                results(i) = spectral_summary(data_2d(:,i), bins)
            else if (present(max_lag_in)) then
                results(i) = spectral_summary(data_2d(:,i), max_lag_in=max_lag_in)
            else
                results(i) = spectral_summary(data_2d(:,i))
            end if
        end do
    end subroutine

end module snapkit_spectral

!> Temporal snap — beat grid alignment, quantization, swing detection.
!> Maps continuous timestamps to a discrete beat grid using Eisenstein snap.
module snapkit_temporal
    use snapkit_eisenstein, only: eisenstein_int, eisenstein_round, eisenstein_to_real
    implicit none
    private
    public :: beat_grid, temporal_snap, temporal_snap_batch
    public :: quantize_to_grid, detect_swing, temporal_result

    real(8), parameter :: SQRT3     = 1.7320508075688772d0
    real(8), parameter :: HALF_SQRT3 = 0.8660254037844386d0

    type :: beat_grid
        real(8) :: bpm         = 120.0d0
        real(8) :: beat_period = 0.5d0     ! 60/bpm
        real(8) :: subdivision = 4.0d0     ! subdivisions per beat
        real(8) :: tick_period = 0.125d0   ! beat_period / subdivision
    end type

    type :: temporal_result
        real(8) :: original_time = 0.0d0
        real(8) :: snapped_time  = 0.0d0
        real(8) :: grid_tick      = 0.0d0
        real(8) :: offset         = 0.0d0   ! deviation from grid
        logical :: is_on_grid    = .false.
    end type

contains

    !> Create a beat grid from BPM and subdivision count.
    pure function new_beat_grid(bpm, subdivision) result(bg)
        real(8), intent(in) :: bpm, subdivision
        type(beat_grid) :: bg
        bg%bpm = bpm
        bg%beat_period = 60.0d0 / bpm
        bg%subdivision = subdivision
        bg%tick_period = bg%beat_period / subdivision
    end function

    !> Snap a single timestamp to the nearest grid tick.
    pure function temporal_snap(time, grid, tolerance) result(tr)
        real(8), intent(in) :: time, tolerance
        type(beat_grid), intent(in) :: grid
        type(temporal_result) :: tr

        real(8) :: tick_f, nearest_tick

        tr%original_time = time
        tick_f = time / grid%tick_period
        nearest_tick = nint(tick_f)

        tr%grid_tick = nearest_tick
        tr%snapped_time = nearest_tick * grid%tick_period
        tr%offset = time - tr%snapped_time
        tr%is_on_grid = (abs(tr%offset) <= tolerance)
    end function

    !> Batch temporal snap — array of timestamps.
    subroutine temporal_snap_batch(times, grid, tolerance, results)
        real(8), intent(in)  :: times(:)
        type(beat_grid), intent(in) :: grid
        real(8), intent(in)  :: tolerance
        type(temporal_result), intent(out) :: results(:)
        integer :: i

        do i = 1, size(times)
            results(i) = temporal_snap(times(i), grid, tolerance)
        end do
    end subroutine

    !> Quantize timestamps to grid and return snapped tick positions.
    subroutine quantize_to_grid(times, grid, tick_positions, snapped_times)
        real(8), intent(in)  :: times(:)
        type(beat_grid), intent(in) :: grid
        real(8), intent(out) :: tick_positions(:)
        real(8), intent(out) :: snapped_times(:)

        integer :: i
        real(8) :: tick_f

        do i = 1, size(times)
            tick_f = times(i) / grid%tick_period
            tick_positions(i) = dble(nint(tick_f))
            snapped_times(i) = tick_positions(i) * grid%tick_period
        end do
    end subroutine

    !> Detect swing ratio from a sequence of inter-onset intervals.
    !> Returns swing ratio (1.0 = no swing, ~1.5 = triplet swing, 2.0 = full swing).
    function detect_swing(intervals) result(swing_ratio)
        real(8), intent(in) :: intervals(:)
        real(8) :: swing_ratio

        integer :: n, i, short_count, long_count
        real(8) :: mean_interval, short_sum, long_sum, short_avg, long_avg

        n = size(intervals)
        if (n < 2) then
            swing_ratio = 1.0d0
            return
        end if

        mean_interval = sum(intervals) / dble(n)

        short_count = 0
        long_count = 0
        short_sum = 0.0d0
        long_sum = 0.0d0

        do i = 1, n
            if (intervals(i) < mean_interval) then
                short_count = short_count + 1
                short_sum = short_sum + intervals(i)
            else
                long_count = long_count + 1
                long_sum = long_sum + intervals(i)
            end if
        end do

        if (short_count == 0 .or. long_count == 0) then
            swing_ratio = 1.0d0
            return
        end if

        short_avg = short_sum / dble(short_count)
        long_avg = long_sum / dble(long_count)

        if (short_avg < 1.0d-12) then
            swing_ratio = 1.0d0
            return
        end if

        swing_ratio = long_avg / short_avg
    end function

end module snapkit_temporal

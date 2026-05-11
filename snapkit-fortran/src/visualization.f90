!> @file visualization.f90
!! @brief Terminal output helpers for SnapKit diagnostics.
!!
!! Provides Fortran-native text visualizations for snap functions,
!! delta detectors, and attention budgets. Uses simple ASCII/Unicode
!! bar charts and tables suitable for HPC terminal output.

module snapkit_visualization
  use snapkit
  implicit none
  private

  public :: snapkit_visualize_snap
  public :: snapkit_visualize_deltas
  public :: snapkit_visualize_budget

contains

  !> Visualize snap function statistics as a terminal bar.
  !!
  !! Prints snap rate, mean delta, and tolerance to stdout
  !! with a simple visual bar for the snap rate.
  !!
  !! @param[in] sf  Snap function to visualize
  subroutine snapkit_visualize_snap(sf)
    type(snapkit_snap_function_t), intent(in) :: sf

    real(wp) :: snap_rate, mean_delta, max_delta
    integer(kind=8) :: snap_cnt, delta_cnt
    integer  :: bars, i

    call snapkit_snap_statistics(sf, snap_cnt, delta_cnt, mean_delta, max_delta, snap_rate)

    write(*, '(a)') "╔══════════════════════════════════════════╗"
    write(*, '(a)') "║        Snap Function Statistics          ║"
    write(*, '(a)') "╠══════════════════════════════════════════╣"
    write(*, '(a, f8.3)')  "║ Tolerance:     ", sf%tolerance
    write(*, '(a, f8.4)')  "║ Baseline:      ", sf%baseline
    write(*, '(a, i8)')    "║ Snap count:    ", snap_cnt
    write(*, '(a, i8)')    "║ Delta count:   ", delta_cnt

    ! Snap rate bar
    write(*, '(a)', advance='no') "║ Snap rate:     ["
    bars = int(snap_rate * 40.0_wp)
    do i = 1, 40
       if (i <= bars) then
          write(*, '(a)', advance='no') "#"
       else
          write(*, '(a)', advance='no') "·"
       end if
    end do
    write(*, '(a, f8.1, a)') "] ", snap_rate * 100.0_wp, "%"

    write(*, '(a, f10.6)') "║ Mean delta:    ", mean_delta
    write(*, '(a, f10.6)') "║ Max delta:     ", max_delta
    write(*, '(a, a)')    "║ Topology:      ", &
         trim(snapkit_topology_name(sf%topology))
    write(*, '(a)') "╚══════════════════════════════════════════╝"
  end subroutine snapkit_visualize_snap

  !> Visualize delta detector streams as a terminal table.
  !!
  !! For each stream, prints the stream ID, its current delta magnitude,
  !! severity, actionability, and whether it demands attention.
  !!
  !! @param[in] dd  Delta detector to visualize
  subroutine snapkit_visualize_deltas(dd)
    type(snapkit_delta_detector_t), intent(in) :: dd

    integer :: i, num_streams
    integer(kind=8) :: total_deltas
    real(wp) :: delta_rate

    call snapkit_detector_statistics(dd, num_streams, total_deltas, delta_rate)

    write(*, '(a)') "╔══════════════════════════════════════════════════════════╗"
    write(*, '(a)') "║               Delta Detector Status                      ║"
    write(*, '(a)') "╠══════════════════════════════════════════════════════════╣"
    write(*, '(a, i4)')        "║ Streams:       ", num_streams
    write(*, '(a, i8)')        "║ Total deltas:  ", total_deltas
    write(*, '(a, f8.1, a)')   "║ Delta rate:    ", delta_rate * 100.0_wp, "%"
    write(*, '(a)') "╠══════════════════════════════════════════════════════════╣"

    if (num_streams == 0) then
       write(*, '(a)') "║  (no streams registered)                                 ║"
    else
       write(*, '(a)') "║  Stream           Mag      Sev   Act%  Urg%  Attn?       ║"
       do i = 1, dd%num_streams
          associate(s => dd%streams(i))
            if (s%has_current) then
               write(*, '(a, a16, f8.4, a1, a7, a1, f5.2, a1, f5.2, a1, a5, a4)') &
                    "║ ", trim(s%stream_id), &
                    s%current%magnitude, " ", &
                    trim(snapkit_severity_name(s%current%severity)), " ", &
                    s%current%actionability * 100.0_wp, "% ", &
                    s%current%urgency * 100.0_wp, "%   ", &
                    merge("YES  ", "no   ", &
                    s%current%severity > SNAPKIT_SEVERITY_NONE), " ║"
            else
               write(*, '(a, a16, a30)') "║ ", trim(s%stream_id), "(no observations yet)      ║"
            end if
          end associate
       end do
    end if
    write(*, '(a)') "╚══════════════════════════════════════════════════════════╝"
  end subroutine snapkit_visualize_deltas

  !> Visualize attention budget allocation as a terminal bar chart.
  !!
  !! For each allocation, prints priority, delta stream ID, allocated
  !! attention (with bar), and the reason code.
  !!
  !! @param[in] ab         Attention budget
  !! @param[in] allocs     Array of allocations
  !! @param[in] n          Number of allocations
  subroutine snapkit_visualize_budget(ab, allocs, n)
    type(snapkit_attention_budget_t), intent(in) :: ab
    type(snapkit_allocation_t), intent(in) :: allocs(:)
    integer, intent(in) :: n

    real(wp) :: remaining, utilization
    integer  :: i, max_bars
    integer  :: bars

    call snapkit_budget_status(ab, remaining, utilization)

    write(*, '(a)') "╔══════════════════════════════════════════════════════════╗"
    write(*, '(a)') "║            Attention Budget Allocation                    ║"
    write(*, '(a)') "╠══════════════════════════════════════════════════════════╣"
    write(*, '(a, f8.1)') "║ Total budget:  ", ab%total_budget
    write(*, '(a, f8.1)') "║ Remaining:     ", remaining

    ! Utilization bar
    write(*, '(a)', advance='no') "║ Utilization:   ["
    bars = int(utilization * 40.0_wp)
    max_bars = min(bars, 40)
    do i = 1, max_bars
       write(*, '(a)', advance='no') "█"
    end do
    do i = max_bars + 1, 40
       write(*, '(a)', advance='no') "·"
    end do
    write(*, '(a, f8.1, a)') "] ", utilization * 100.0_wp, "%"

    write(*, '(a, i6)') "║ Cycle count:   ", ab%cycle_count
    write(*, '(a, i6)') "║ Exhaustions:   ", ab%exhaustion_count
    write(*, '(a)') "╠══════════════════════════════════════════════════════════╣"

    if (n == 0) then
       write(*, '(a)') "║  (no allocations this cycle)                             ║"
    else
       write(*, '(a)') "║  #  Stream           Alloc    Bar              Reason   ║"
       do i = 1, min(n, 12)
          bars = int((allocs(i)%allocated / ab%total_budget) * 30.0_wp)
          if (bars < 0) bars = 0
          if (bars > 30) bars = 30
          write(*, '(a, i2, a1, a16, f7.1, a1)', advance='no') &
               "║ ", allocs(i)%priority, " ", &
               trim(allocs(i)%delta%stream_id), &
               allocs(i)%allocated, "  ["
          call write_bars(bars, 30)
          write(*, '(a, a16, a1)') "] ", trim(allocs(i)%reason), "║"
       end do
       if (n > 12) then
          write(*, '(a, i4, a)') "║  ... and ", n - 12, " more allocations               ║"
       end if
    end if
    write(*, '(a)') "╚══════════════════════════════════════════════════════════╝"
  end subroutine snapkit_visualize_budget

  !> Internal: write a bar of a given length [0..maxlen]
  subroutine write_bars(n, maxlen)
    integer, intent(in) :: n, maxlen
    integer :: i
    do i = 1, min(n, maxlen)
       write(*, '(a)', advance='no') "▓"
    end do
    do i = min(n, maxlen) + 1, maxlen
       write(*, '(a)', advance='no') "·"
    end do
  end subroutine write_bars

end module snapkit_visualization

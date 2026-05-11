!> @file benchmark.f90
!! @brief SnapKit performance benchmarks.
!!
!! Benchmarks the core operations:
!!  1. Eisenstein snap (scalar) — 100,000 points
!!  2. Eisenstein snap (batch) — 100,000 points
!!  3. Scalar snap — 1,000,000 values
!!  4. Delta detection (batch) — 100,000 values across 8 streams
!!  5. Attention budget allocation — 50 deltas, 100 cycles
!!
!! Uses system_clock for timing. Outputs results in a clean table.

program benchmark
  use snapkit
  use snapkit_eisenstein
  use snapkit_snap
  use snapkit_delta
  use snapkit_attention
  implicit none

  integer, parameter :: N_EISENSTEIN = 100000
  integer, parameter :: N_SCALAR = 1000000
  integer, parameter :: N_BATCH = 100000
  integer, parameter :: N_BUDGET = 50
  integer, parameter :: BUDGET_CYCLES = 100

  type(snapkit_snap_function_t), pointer :: sf
  type(snapkit_delta_detector_t), pointer :: dd
  type(snapkit_attention_budget_t), pointer :: budget

  real(wp), allocatable :: reals(:), imags(:), values(:)
  integer,  allocatable :: a_vals(:), b_vals(:)
  real(wp), allocatable :: snapped_re(:), snapped_im(:), dists(:)

  type(snapkit_snap_result_t), allocatable :: results(:)
  type(snapkit_delta_t), allocatable :: deltas(:)
  type(snapkit_allocation_t), allocatable :: allocs(:)

  integer(kind=8) :: t_start, t_end, t_rate
  real(wp) :: t_eisen_scalar, t_eisen_batch, t_scalar, t_delta, t_budget

  integer :: i, err, n_alloc, tidx
  character(len=32) :: stream_names(8)

  write(*, '(a)') "╔══════════════════════════════════════════════════════╗"
  write(*, '(a)') "║            SnapKit Fortran Benchmarks               ║"
  write(*, '(a)') "╠══════════════════════════════════════════════════════╣"
  write(*, '(a, i8)') "║ N (Eisenstein): ", N_EISENSTEIN
  write(*, '(a, i8)') "║ N (scalar):     ", N_SCALAR
  write(*, '(a, i8)') "║ N (delta):      ", N_BATCH
  write(*, '(a, i8)') "║ Budget deltas:  ", N_BUDGET
  write(*, '(a, i8)') "║ Budget cycles:  ", BUDGET_CYCLES
  write(*, '(a)') "╚══════════════════════════════════════════════════════╝"

  call system_clock(count_rate=t_rate)

  !-------------------------------------------------------------------------
  ! 1. Eisenstein snap — scalar
  !-------------------------------------------------------------------------
  allocate(reals(N_EISENSTEIN), imags(N_EISENSTEIN))
  allocate(a_vals(N_EISENSTEIN), b_vals(N_EISENSTEIN))
  allocate(snapped_re(N_EISENSTEIN), snapped_im(N_EISENSTEIN), dists(N_EISENSTEIN))

  call random_seed()
  do i = 1, N_EISENSTEIN
     call random_number(reals(i))
     call random_number(imags(i))
     reals(i) = reals(i) * 10.0_wp - 5.0_wp
     imags(i) = imags(i) * 10.0_wp - 5.0_wp
  end do

  call system_clock(t_start)
  do i = 1, N_EISENSTEIN
     call snapkit_nearest_eisenstein(reals(i), imags(i), a_vals(i), b_vals(i), &
          snapped_re(i), snapped_im(i), dists(i))
  end do
  call system_clock(t_end)
  t_eisen_scalar = real(t_end - t_start, wp) / real(t_rate, wp)

  !-------------------------------------------------------------------------
  ! 2. Eisenstein snap — batch
  !-------------------------------------------------------------------------
  call system_clock(t_start)
  call snapkit_nearest_eisenstein_batch(reals, imags, a_vals, b_vals, &
       snapped_re, snapped_im, dists)
  call system_clock(t_end)
  t_eisen_batch = real(t_end - t_start, wp) / real(t_rate, wp)

  deallocate(a_vals, b_vals, snapped_re, snapped_im, dists)

  !-------------------------------------------------------------------------
  ! 3. Scalar snap — batch
  !-------------------------------------------------------------------------
  allocate(values(N_SCALAR))
  allocate(results(N_SCALAR))
  do i = 1, N_SCALAR
     call random_number(values(i))
  end do

  sf => snapkit_snap_create()
  call system_clock(t_start)
  do i = 1, N_SCALAR
     err = snapkit_snap(sf, values(i), huge(1.0_wp), results(i))
  end do
  call system_clock(t_end)
  t_scalar = real(t_end - t_start, wp) / real(t_rate, wp)

  deallocate(values, results)
  call snapkit_snap_free(sf)

  !-------------------------------------------------------------------------
  ! 4. Delta detection (batch)
  !-------------------------------------------------------------------------
  dd => snapkit_detector_create()

  stream_names = ["stream_1", "stream_2", "stream_3", "stream_4", &
       "stream_5", "stream_6", "stream_7", "stream_8"]
  do i = 1, 8
     err = snapkit_detector_add_stream(dd, stream_names(i), 0.1_wp, &
          mod(i-1, 8), 0.5_wp + real(i, wp) * 0.06_wp, &
          0.4_wp + real(i, wp) * 0.07_wp)
  end do

  allocate(values(N_BATCH))
  allocate(deltas(8))
  do i = 1, N_BATCH
     call random_number(values(i))
  end do

  call system_clock(t_start)
  do i = 1, N_BATCH
     tidx = mod(i - 1, 8) + 1
     err = snapkit_detector_observe(dd, stream_names(tidx), values(i))
  end do
  call system_clock(t_end)
  t_delta = real(t_end - t_start, wp) / real(t_rate, wp)

  deallocate(values, deltas)

  !-------------------------------------------------------------------------
  ! 5. Attention budget allocation
  !-------------------------------------------------------------------------
  budget => snapkit_budget_create(100.0_wp, SNAPKIT_STRATEGY_ACTIONABILITY)
  allocate(deltas(N_BUDGET), allocs(N_BUDGET))

  call system_clock(t_start)
  do i = 1, BUDGET_CYCLES
     ! Generate random deltas
     call random_deltas(deltas, N_BUDGET, dd)
     err = snapkit_budget_allocate(budget, deltas, allocs, n_alloc)
  end do
  call system_clock(t_end)
  t_budget = real(t_end - t_start, wp) / real(t_rate, wp)

  deallocate(deltas, allocs)
  deallocate(reals, imags)

  call snapkit_detector_free(dd)
  call snapkit_budget_free(budget)

  !-------------------------------------------------------------------------
  ! Results
  !-------------------------------------------------------------------------
  write(*, '(a)')
  write(*, '(a)') "╔══════════════════════════════════════════════════════╗"
  write(*, '(a)') "║                Benchmark Results                     ║"
  write(*, '(a)') "╠══════════════════════════════════════════════════════╣"
  write(*, '(a, f10.4, a)') "║ 1. Eisenstein scalar  ", t_eisen_scalar, " s"
  write(*, '(a, f10.4, a)') "║ 2. Eisenstein batch   ", t_eisen_batch, " s"
  write(*, '(a, f10.4, a)') "║ 3. Scalar snap        ", t_scalar, " s"
  write(*, '(a, f10.4, a)') "║ 4. Delta detect       ", t_delta, " s"
  write(*, '(a, f10.4, a)') "║ 5. Budget allocate    ", t_budget, " s"
  write(*, '(a)') "╚══════════════════════════════════════════════════════╝"

  ! Throughput
  write(*, '(a)')
  write(*, '(a)') "Throughput:"
  write(*, '(a, f10.0, a)') "  Eisenstein scalar: ", &
       real(N_EISENSTEIN, wp) / t_eisen_scalar, " pts/s"
  write(*, '(a, f10.0, a)') "  Eisenstein batch:  ", &
       real(N_EISENSTEIN, wp) / t_eisen_batch, " pts/s"
  write(*, '(a, f10.0, a)') "  Scalar snap:       ", &
       real(N_SCALAR, wp) / t_scalar, " vals/s"
  write(*, '(a, f10.0, a)') "  Delta detect:      ", &
       real(N_BATCH, wp) / t_delta, " obs/s"
  write(*, '(a, f10.0, a)') "  Budget allocate:   ", &
       real(BUDGET_CYCLES, wp) / t_budget, " cycles/s"

contains

  !> Generate random deltas for budget benchmark
  subroutine random_deltas(deltas, n, dd)
    type(snapkit_delta_t), intent(out) :: deltas(:)
    integer, intent(in) :: n
    type(snapkit_delta_detector_t), intent(inout) :: dd
    real(wp) :: rnd
    integer :: i

    do i = 1, n
       call random_number(rnd)
       deltas(i)%value     = rnd
       deltas(i)%expected  = 0.5_wp
       deltas(i)%magnitude = abs(rnd - 0.5_wp)
       deltas(i)%tolerance = 0.1_wp
       deltas(i)%severity  = snapkit_compute_severity(deltas(i)%magnitude, 0.1_wp)
       deltas(i)%timestamp = 1
       deltas(i)%stream_id = "bench"
       deltas(i)%actionability = 0.5_wp + rnd * 0.5_wp
       deltas(i)%urgency       = 0.3_wp + rnd * 0.7_wp
    end do
  end subroutine random_deltas

end program benchmark

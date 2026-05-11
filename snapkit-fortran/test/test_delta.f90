!> @file test_delta.f90
!! @brief Tests for delta detector.
module test_delta
  use snapkit
  use snapkit_delta
  implicit none
  private
  public :: test_detector_create_free
  public :: test_detector_add_stream
  public :: test_detector_observe
  public :: test_detector_batch

contains

  !> Test detector create and free.
  function test_detector_create_free() result(pass)
    logical :: pass
    type(snapkit_delta_detector_t), pointer :: dd

    pass = .true.

    dd => snapkit_detector_create()
    if (.not. associated(dd)) then
       write(*, '(a)') "  FAIL: detector_create returned null"
       pass = .false.
       return
    end if

    if (dd%num_streams /= 0) then
       write(*, '(a)') "  FAIL: new detector should have 0 streams"
       pass = .false.
    end if

    if (dd%tick /= 0) then
       write(*, '(a)') "  FAIL: new detector tick should be 0"
       pass = .false.
    end if

    call snapkit_detector_free(dd)
    if (associated(dd)) then
       write(*, '(a)') "  FAIL: detector_free didn't nullify pointer"
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: detector create/free"
  end function test_detector_create_free

  !> Test adding streams.
  function test_detector_add_stream() result(pass)
    logical :: pass
    type(snapkit_delta_detector_t), pointer :: dd
    integer :: err

    pass = .true.

    dd => snapkit_detector_create()

    err = snapkit_detector_add_stream(dd, "test_stream", 0.1_wp, &
         SNAPKIT_TOPOLOGY_BINARY, 0.8_wp, 0.5_wp)

    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: add_stream returned error"
       pass = .false.
    end if

    if (dd%num_streams /= 1) then
       write(*, '(a)') "  FAIL: should have 1 stream"
       pass = .false.
    end if

    if (trim(dd%streams(1)%stream_id) /= "test_stream") then
       write(*, '(a)') "  FAIL: stream_id mismatch"
       pass = .false.
    end if

    if (abs(dd%streams(1)%snap%tolerance - 0.1_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: stream tolerance mismatch"
       pass = .false.
    end if

    call snapkit_detector_free(dd)
    if (pass) write(*, '(a)') "  PASS: detector add_stream"
  end function test_detector_add_stream

  !> Test observing a value.
  function test_detector_observe() result(pass)
    logical :: pass
    type(snapkit_delta_detector_t), pointer :: dd
    type(snapkit_delta_t) :: delta
    integer :: err

    pass = .true.

    dd => snapkit_detector_create()
    err = snapkit_detector_add_stream(dd, "test", 0.1_wp, &
         SNAPKIT_TOPOLOGY_GRADIENT, 1.0_wp, 1.0_wp)

    ! Observe a delta (far from baseline 0)
    err = snapkit_detector_observe(dd, "test", 0.85_wp, delta)

    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: observe returned error"
       pass = .false.
    end if

    if (abs(delta%value - 0.85_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: delta value mismatch"
       pass = .false.
    end if

    if (delta%severity == SNAPKIT_SEVERITY_NONE) then
       write(*, '(a)') "  FAIL: 0.85 should produce non-zero severity from baseline 0"
       pass = .false.
    end if

    if (delta%timestamp <= 0) then
       write(*, '(a)') "  FAIL: delta timestamp should be > 0"
       pass = .false.
    end if

    ! Query current delta
    err = snapkit_detector_current_delta(dd, "test", delta)
    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: current_delta returned error"
       pass = .false.
    end if

    call snapkit_detector_free(dd)
    if (pass) write(*, '(a)') "  PASS: detector observe"
  end function test_detector_observe

  !> Test batch observation.
  function test_detector_batch() result(pass)
    logical :: pass
    type(snapkit_delta_detector_t), pointer :: dd
    type(snapkit_delta_t) :: deltas(3)
    character(len=32) :: stream_ids(3)
    real(wp) :: values(3)
    integer :: err
    integer :: ns
    integer(kind=8) :: td
    real(wp) :: dr

    pass = .true.

    dd => snapkit_detector_create()
    err = snapkit_detector_add_stream(dd, "a", 0.1_wp, SNAPKIT_TOPOLOGY_BINARY, 1.0_wp, 1.0_wp)
    err = snapkit_detector_add_stream(dd, "b", 0.2_wp, SNAPKIT_TOPOLOGY_CUBIC, 0.5_wp, 0.5_wp)
    err = snapkit_detector_add_stream(dd, "c", 0.3_wp, SNAPKIT_TOPOLOGY_HEXAGONAL, 0.2_wp, 0.8_wp)

    stream_ids = ["a", "b", "c"]
    values = [0.5_wp, 0.6_wp, 0.7_wp]

    err = snapkit_detector_observe_batch(dd, stream_ids, values, deltas)

    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: batch observe returned error"
       pass = .false.
    end if

    ! Check statistics
    call snapkit_detector_statistics(dd, ns, td, dr)
    if (ns /= 3) then
       write(*, '(a)') "  FAIL: batch should have 3 streams"
       pass = .false.
    end if

    if (td <= 0) then
       write(*, '(a)') "  FAIL: should have deltas from batch"
       pass = .false.
    end if

    call snapkit_detector_free(dd)
    if (pass) write(*, '(a)') "  PASS: detector batch"
  end function test_detector_batch

end module test_delta

!> @file test_snap.f90
!! @brief Tests for the snap function.
module test_snap
  use snapkit
  use snapkit_snap
  implicit none
  private
  public :: test_snap_basic
  public :: test_snap_within
  public :: test_snap_outside
  public :: test_snap_create_ex
  public :: test_snap_calibrate

contains

  !> Test basic snap create and free.
  function test_snap_basic() result(pass)
    logical :: pass
    type(snapkit_snap_function_t), pointer :: sf

    pass = .true.

    sf => snapkit_snap_create()
    if (.not. associated(sf)) then
       write(*, '(a)') "  FAIL: snapkit_snap_create returned null"
       pass = .false.
       return
    end if

    if (abs(sf%tolerance - SNAPKIT_DEFAULT_TOLERANCE) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: default tolerance incorrect"
       pass = .false.
    end if

    if (sf%topology /= SNAPKIT_TOPOLOGY_HEXAGONAL) then
       write(*, '(a)') "  FAIL: default topology not hexagonal"
       pass = .false.
    end if

    call snapkit_snap_free(sf)
    if (associated(sf)) then
       write(*, '(a)') "  FAIL: snap_free didn't nullify pointer"
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: snap basic create/free"
  end function test_snap_basic

  !> Test snapping within tolerance.
  function test_snap_within() result(pass)
    logical :: pass
    type(snapkit_snap_function_t), pointer :: sf
    type(snapkit_snap_result_t) :: sr
    integer :: err

    pass = .true.

    sf => snapkit_snap_create_ex(0.1_wp, SNAPKIT_TOPOLOGY_BINARY, 0.5_wp, 0.0_wp)
    err = snapkit_snap(sf, 0.52_wp, huge(1.0_wp), sr)

    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: snap returned error"
       pass = .false.
    end if

    ! 0.52 is within 0.1 of baseline 0.5 → should snap to baseline
    if (.not. sr%within_tolerance) then
       write(*, '(a)') "  FAIL: 0.52 should be within tolerance of 0.5"
       pass = .false.
    end if

    if (abs(sr%snapped - 0.5_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: snapped value should be baseline 0.5"
       pass = .false.
    end if

    if (abs(sr%original - 0.52_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: original value not preserved"
       pass = .false.
    end if

    call snapkit_snap_free(sf)
    if (pass) write(*, '(a)') "  PASS: snap within tolerance"
  end function test_snap_within

  !> Test snapping outside tolerance.
  function test_snap_outside() result(pass)
    logical :: pass
    type(snapkit_snap_function_t), pointer :: sf
    type(snapkit_snap_result_t) :: sr
    integer :: err

    pass = .true.

    sf => snapkit_snap_create_ex(0.1_wp, SNAPKIT_TOPOLOGY_BINARY, 0.5_wp, 0.0_wp)
    err = snapkit_snap(sf, 0.75_wp, huge(1.0_wp), sr)

    ! 0.75 is 0.25 from baseline 0.5 → exceeds 0.1 tolerance
    if (sr%within_tolerance) then
       write(*, '(a)') "  FAIL: 0.75 should exceed tolerance of 0.5 ± 0.1"
       pass = .false.
    end if

    if (abs(sr%snapped - 0.75_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: outside tolerance passes through unsnapped"
       pass = .false.
    end if

    call snapkit_snap_free(sf)
    if (pass) write(*, '(a)') "  PASS: snap outside tolerance"
  end function test_snap_outside

  !> Test create with explicit parameters.
  function test_snap_create_ex() result(pass)
    logical :: pass
    type(snapkit_snap_function_t), pointer :: sf

    pass = .true.

    sf => snapkit_snap_create_ex(0.5_wp, SNAPKIT_TOPOLOGY_CUBIC, 1.0_wp, 0.1_wp)
    if (.not. associated(sf)) then
       write(*, '(a)') "  FAIL: snapkit_snap_create_ex returned null"
       pass = .false.
       return
    end if

    if (abs(sf%tolerance - 0.5_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: explicit tolerance not set correctly"
       pass = .false.
    end if
    if (sf%topology /= SNAPKIT_TOPOLOGY_CUBIC) then
       write(*, '(a)') "  FAIL: explicit topology not set correctly"
       pass = .false.
    end if
    if (abs(sf%baseline - 1.0_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: explicit baseline not set correctly"
       pass = .false.
    end if
    if (abs(sf%adaptation_rate - 0.1_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: explicit adaptation_rate not set correctly"
       pass = .false.
    end if

    call snapkit_snap_free(sf)
    if (pass) write(*, '(a)') "  PASS: snap create_ex"
  end function test_snap_create_ex

  !> Test auto-calibrate.
  function test_snap_calibrate() result(pass)
    logical :: pass
    type(snapkit_snap_function_t), pointer :: sf
    real(wp) :: samples(20)
    integer  :: i, err

    pass = .true.

    ! Create samples with known variance
    do i = 1, 20
       samples(i) = 0.5_wp + real(i - 10, wp) * 0.05_wp
    end do

    sf => snapkit_snap_create()
    err = snapkit_snap_calibrate(sf, samples, 0.80_wp)

    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: calibrate returned error"
       pass = .false.
    end if

    ! Tolerance should now be set to the 80th percentile of distances from mean
    if (sf%tolerance <= 0.0_wp) then
       write(*, '(a)') "  FAIL: calibrated tolerance is zero"
       pass = .false.
    end if

    if (abs(sf%baseline - 0.5_wp) > 0.1_wp) then
       write(*, '(a)') "  FAIL: calibrated baseline not near mean"
       pass = .false.
    end if

    call snapkit_snap_free(sf)
    if (pass) write(*, '(a)') "  PASS: snap calibrate"
  end function test_snap_calibrate

end module test_snap

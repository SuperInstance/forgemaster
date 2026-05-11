!> @file test_topology.f90
!! @brief Tests for ADE topology and constraint sheaf.
module test_topology
  use snapkit
  use snapkit_topology
  implicit none
  private
  public :: test_ade_data
  public :: test_recommend_topology
  public :: test_sheaf_create_free
  public :: test_sheaf_consistency

contains

  !> Test ADE topology data access.
  function test_ade_data() result(pass)
    logical :: pass
    type(snapkit_ade_data_t), pointer :: d

    pass = .true.

    d => snapkit_ade_data(SNAPKIT_TOPOLOGY_BINARY)
    if (.not. associated(d)) then
       write(*, '(a)') "  FAIL: ade_data returned null for BINARY"
       pass = .false.
       return
    end if
    if (trim(d%name) /= "A1") then
       write(*, '(a)') "  FAIL: BINARY should be A1"
       pass = .false.
    end if

    d => snapkit_ade_data(SNAPKIT_TOPOLOGY_HEXAGONAL)
    if (.not. associated(d)) then
       write(*, '(a)') "  FAIL: ade_data returned null for HEXAGONAL"
       pass = .false.
       return
    end if
    if (trim(d%name) /= "A2") then
       write(*, '(a)') "  FAIL: HEXAGONAL should be A2"
       pass = .false.
    end if
    if (abs(d%quality_score - 2.7_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: HEXAGONAL quality_score should be 2.7"
       pass = .false.
    end if

    ! Invalid topology should return null
    d => snapkit_ade_data(-1)
    if (associated(d)) then
       write(*, '(a)') "  FAIL: invalid topology should return null"
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: ADE data"
  end function test_ade_data

  !> Test recommend_topology.
  function test_recommend_topology() result(pass)
    logical :: pass

    pass = .true.

    if (snapkit_recommend_topology(2, 0) /= SNAPKIT_TOPOLOGY_BINARY) then
       write(*, '(a)') "  FAIL: 2 categories should recommend BINARY"
       pass = .false.
    end if

    if (snapkit_recommend_topology(4, 0) /= SNAPKIT_TOPOLOGY_TETRAHEDRAL) then
       write(*, '(a)') "  FAIL: 4 categories should recommend TETRAHEDRAL"
       pass = .false.
    end if

    if (snapkit_recommend_topology(0, 2) /= SNAPKIT_TOPOLOGY_HEXAGONAL) then
       write(*, '(a)') "  FAIL: 2D should recommend HEXAGONAL"
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: recommend topology"
  end function test_recommend_topology

  !> Test sheaf create and free.
  function test_sheaf_create_free() result(pass)
    logical :: pass
    type(snapkit_constraint_sheaf_t), pointer :: sheaf

    pass = .true.

    sheaf => snapkit_sheaf_create(SNAPKIT_TOPOLOGY_HEXAGONAL, 0.1_wp)
    if (.not. associated(sheaf)) then
       write(*, '(a)') "  FAIL: sheaf_create returned null"
       pass = .false.
       return
    end if

    if (sheaf%topology /= SNAPKIT_TOPOLOGY_HEXAGONAL) then
       write(*, '(a)') "  FAIL: sheaf topology mismatch"
       pass = .false.
    end if

    if (abs(sheaf%tolerance - 0.1_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: sheaf tolerance mismatch"
       pass = .false.
    end if

    call snapkit_sheaf_free(sheaf)
    if (associated(sheaf)) then
       write(*, '(a)') "  FAIL: sheaf_free didn't nullify"
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: sheaf create/free"
  end function test_sheaf_create_free

  !> Test sheaf consistency checking.
  function test_sheaf_consistency() result(pass)
    logical :: pass
    type(snapkit_constraint_sheaf_t), pointer :: sheaf
    type(snapkit_consistency_report_t) :: report
    integer :: err

    pass = .true.

    sheaf => snapkit_sheaf_create(SNAPKIT_TOPOLOGY_BINARY, 0.1_wp)

    ! Add consistent constraints
    err = snapkit_sheaf_add_constraint(sheaf, "speed", 10.0_wp, 10.0_wp)
    err = snapkit_sheaf_add_constraint(sheaf, "position", 5.0_wp, 5.0_wp)

    err = snapkit_sheaf_check(sheaf, report)
    if (err /= SNAPKIT_OK) then
       write(*, '(a)') "  FAIL: sheaf_check returned error"
       pass = .false.
    end if

    if (report%num_constraints /= 2) then
       write(*, '(a)') "  FAIL: should have 2 constraints"
       pass = .false.
    end if

    if (report%delta_detected) then
       write(*, '(a)') "  FAIL: no delta expected with exact matches"
       pass = .false.
    end if

    if (report%h1_analog /= 0) then
       write(*, '(a)') "  FAIL: H1 should be 0 with exact matches"
       pass = .false.
    end if

    ! Now add a violated constraint
    err = snapkit_sheaf_add_constraint(sheaf, "altitude", 100.0_wp, 50.0_wp)
    err = snapkit_sheaf_check(sheaf, report)

    if (.not. report%delta_detected) then
       write(*, '(a)') "  FAIL: should detect delta with violated constraint"
       pass = .false.
    end if

    if (report%h1_analog < 1) then
       write(*, '(a)') "  FAIL: violated constraint should increase H1"
       pass = .false.
    end if

    call snapkit_sheaf_free(sheaf)
    if (pass) write(*, '(a)') "  PASS: sheaf consistency"
  end function test_sheaf_consistency

end module test_topology

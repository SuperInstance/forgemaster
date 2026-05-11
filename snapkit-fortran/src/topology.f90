!> @file topology.f90
!! @brief ADE topology data, classification, and constraint sheaf checking.
!!
!! Implements the ADE/Platonic classification of randomness flavors:
!! - Binary (A₁): coin flip, 2 outcomes
!! - Tetrahedral (A₃): 4 categories
!! - Hexagonal (A₂): Eisenstein lattice, optimal 2D compression
!! - Cubic (ℤⁿ): standard uniform grid
!! - Octahedral (B₃): 8 directions
!! - Dodecahedral (H₃): 20-category combinatorial
!! - Icosahedral (H₃): 12-direction golden-ratio clusters
!! - Gradient (continuous): near-continuous d100 style

module snapkit_topology
  use snapkit
  implicit none
  private

  public :: snapkit_sheaf_create
  public :: snapkit_sheaf_free
  public :: snapkit_sheaf_add_constraint
  public :: snapkit_sheaf_add_dependency
  public :: snapkit_sheaf_check
  public :: snapkit_sheaf_update_expected

contains

  !> Create a constraint sheaf.
  !!
  !! A constraint sheaf tracks the consistency of multiple constraints
  !! and their inter-dependencies. The H¹ analog counts how many constraints
  !! exceed tolerance — these are "obstructions to local→global consistency."
  !!
  !! @param[in] topology  Snap topology for the constraint lattice
  !! @param[in] tolerance Maximum drift before delta is detected
  !! @return    New sheaf, or null on failure
  function snapkit_sheaf_create(topology, tolerance) result(sheaf)
    integer,  intent(in) :: topology
    real(wp), intent(in) :: tolerance
    type(snapkit_constraint_sheaf_t), pointer :: sheaf

    allocate(sheaf)
    sheaf%topology         = topology
    sheaf%tolerance        = tolerance
    sheaf%num_constraints  = 0
    sheaf%num_dependencies = 0
  end function snapkit_sheaf_create

  !> Free a constraint sheaf.
  subroutine snapkit_sheaf_free(sheaf)
    type(snapkit_constraint_sheaf_t), pointer, intent(inout) :: sheaf
    if (associated(sheaf)) then
       deallocate(sheaf)
       sheaf => null()
    end if
  end subroutine snapkit_sheaf_free

  !> Add a constraint node to the sheaf.
  !!
  !! @param[inout] sheaf    Constraint sheaf
  !! @param[in]    name     Constraint name (should be unique)
  !! @param[in]    value    Current value of the constraint
  !! @param[in]    expected Expected value (use huge(1.0) to set to current value)
  !! @return       Error code
  function snapkit_sheaf_add_constraint(sheaf, name, value, expected) result(err)
    type(snapkit_constraint_sheaf_t), intent(inout) :: sheaf
    character(*), intent(in) :: name
    real(wp),     intent(in) :: value
    real(wp),     intent(in) :: expected
    integer :: err

    integer :: idx

    err = SNAPKIT_OK
    if (sheaf%num_constraints >= SNAPKIT_MAX_CONSTRAINTS) then
       err = SNAPKIT_ERR_SIZE
       return
    end if

    idx = sheaf%num_constraints + 1
    sheaf%constraints(idx)%name = name
    sheaf%constraints(idx)%value = value

    if (expected < huge(1.0_wp) * 0.99_wp) then
       sheaf%constraints(idx)%expected     = expected
       sheaf%constraints(idx)%has_expected = .true.
    else
       sheaf%constraints(idx)%expected     = value
       sheaf%constraints(idx)%has_expected = .false.
    end if

    sheaf%num_constraints = idx
  end function snapkit_sheaf_add_constraint

  !> Add a dependency between two constraints.
  !!
  !! @param[inout] sheaf   Constraint sheaf
  !! @param[in]    source  Source constraint name
  !! @param[in]    target  Target constraint name
  !! @return       Error code
  function snapkit_sheaf_add_dependency(sheaf, source, target) result(err)
    type(snapkit_constraint_sheaf_t), intent(inout) :: sheaf
    character(*), intent(in) :: source, target
    integer :: err

    integer :: idx

    err = SNAPKIT_OK
    if (sheaf%num_dependencies >= SNAPKIT_MAX_DEPENDENCIES) then
       err = SNAPKIT_ERR_SIZE
       return
    end if

    idx = sheaf%num_dependencies + 1
    sheaf%dependencies(idx)%source = source
    sheaf%dependencies(idx)%target = target
    sheaf%num_dependencies = idx
  end function snapkit_sheaf_add_dependency

  !> Check global consistency of all constraints.
  !!
  !! Computes:
  !! - Per-constraint deltas: |value - expected|
  !! - Dependency deltas: how much two dependent constraints drift together
  !! - H¹ analog: count of constraints exceeding tolerance
  !!
  !! @param[in]  sheaf   Constraint sheaf
  !! @param[out] report  Consistency report
  !! @return     Error code
  function snapkit_sheaf_check(sheaf, report) result(err)
    type(snapkit_constraint_sheaf_t), intent(in) :: sheaf
    type(snapkit_consistency_report_t), intent(out) :: report
    integer :: err

    real(wp), allocatable :: deltas(:)
    integer  :: i, num_d
    real(wp) :: s_val, t_val, s_exp, t_exp, d, max_d, sum_d
    integer  :: h1

    err = SNAPKIT_OK

    if (sheaf%num_constraints == 0) then
       report%num_constraints = 0
       report%max_delta       = 0.0_wp
       report%mean_delta      = 0.0_wp
       report%h1_analog       = 0
       report%delta_detected  = .false.
       report%tolerance       = sheaf%tolerance
       report%topology        = sheaf%topology
       return
    end if

    allocate(deltas(sheaf%num_constraints + sheaf%num_dependencies + 1))
    num_d = 0

    ! Check individual constraint deltas
    do i = 1, sheaf%num_constraints
       d = abs(sheaf%constraints(i)%value - sheaf%constraints(i)%expected)
       num_d = num_d + 1
       deltas(num_d) = d
    end do

    ! Check dependency compatibility
    do i = 1, sheaf%num_dependencies
       s_val = 0.0_wp; t_val = 0.0_wp
       s_exp = 0.0_wp; t_exp = 0.0_wp
       call find_constraint(sheaf, sheaf%dependencies(i)%source, s_val, s_exp)
       call find_constraint(sheaf, sheaf%dependencies(i)%target, t_val, t_exp)
       ! If both found, compute compatibility delta
       if (abs(s_val) > 0.0_wp .or. abs(s_exp) > 0.0_wp .or. &
            abs(t_val) > 0.0_wp .or. abs(t_exp) > 0.0_wp) then
          d = abs((s_val - s_exp) - (t_val - t_exp)) * 0.5_wp
          num_d = num_d + 1
          deltas(num_d) = d
       end if
    end do

    ! Compute statistics
    max_d = 0.0_wp
    sum_d = 0.0_wp
    h1    = 0
    do i = 1, num_d
       if (deltas(i) > max_d) max_d = deltas(i)
       sum_d = sum_d + deltas(i)
       if (deltas(i) > sheaf%tolerance) h1 = h1 + 1
    end do

    report%num_constraints = sheaf%num_constraints
    report%max_delta       = max_d
    report%mean_delta      = merge(sum_d / real(num_d, wp), 0.0_wp, num_d > 0)
    report%h1_analog       = h1
    report%delta_detected  = max_d > sheaf%tolerance
    report%tolerance       = sheaf%tolerance
    report%topology        = sheaf%topology

    deallocate(deltas)
  end function snapkit_sheaf_check

  !> Update the expected value for a constraint.
  !!
  !! @param[inout] sheaf    Constraint sheaf
  !! @param[in]    name     Constraint name
  !! @param[in]    expected New expected value
  !! @return       Error code
  function snapkit_sheaf_update_expected(sheaf, name, expected) result(err)
    type(snapkit_constraint_sheaf_t), intent(inout) :: sheaf
    character(*), intent(in) :: name
    real(wp),     intent(in) :: expected
    integer :: err

    integer :: i

    err = SNAPKIT_ERR_NULL
    do i = 1, sheaf%num_constraints
       if (trim(sheaf%constraints(i)%name) == trim(name)) then
          sheaf%constraints(i)%expected     = expected
          sheaf%constraints(i)%has_expected = .true.
          err = SNAPKIT_OK
          return
       end if
    end do
  end function snapkit_sheaf_update_expected

  !> Internal helper: find a constraint by name and return its value/expected.
  pure subroutine find_constraint(sheaf, name, value, expected)
    type(snapkit_constraint_sheaf_t), intent(in) :: sheaf
    character(*), intent(in) :: name
    real(wp), intent(out) :: value, expected
    integer :: i

    value = 0.0_wp
    expected = 0.0_wp
    do i = 1, sheaf%num_constraints
       if (trim(sheaf%constraints(i)%name) == trim(name)) then
          value    = sheaf%constraints(i)%value
          expected = sheaf%constraints(i)%expected
          return
       end if
    end do
  end subroutine find_constraint

end module snapkit_topology

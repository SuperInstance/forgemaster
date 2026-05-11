!> @file snapkit.f90
!! @brief Master module for SnapKit Fortran — type definitions and public API.
!!
!! SnapKit implements tolerance-compressed attention allocation:
!!  - SnapFunction: compresses values "close enough to expected"
!!  - Delta detection: tracks what exceeds snap tolerance
!!  - Attention budget: finite cognition allocation
!!  - Eisenstein lattice (A₂): optimal 2D snap with H¹=0 guarantee
!!  - Platonic/ADE classification: 5 flavors of randomness
!!
!! Theory: SNAPS-AS-ATTENTION.md (Forgemaster ⚒️ / Casey Digennaro, 2026)
!! Reference: snapkit-c (C reference implementation)
!!
!! This is an ALL-module library — callers `use snapkit` for everything.
!! Parameterized precision via wp (default real64).

module snapkit
  implicit none
  private

  !---------------------------------------------------------------------------
  ! Version
  !---------------------------------------------------------------------------
  integer, parameter, public :: SNAPKIT_VERSION_MAJOR = 0
  integer, parameter, public :: SNAPKIT_VERSION_MINOR = 2
  integer, parameter, public :: SNAPKIT_VERSION_PATCH = 0
  character(*), parameter, public :: SNAPKIT_VERSION_STRING = "0.2.0"

  !---------------------------------------------------------------------------
  ! Working precision — parameterized for real32 / real64
  !---------------------------------------------------------------------------
  integer, parameter, public :: wp = kind(1.0d0)  ! default: real64

  !---------------------------------------------------------------------------
  ! Mathematical constants
  !---------------------------------------------------------------------------
  real(wp), parameter, public :: SNAPKIT_PI    = 3.14159265358979323846_wp
  real(wp), parameter, public :: SNAPKIT_SQRT3 = 1.73205080756887729353_wp
  real(wp), parameter, public :: SNAPKIT_SQRT3_2 = 0.86602540378443864676_wp
  real(wp), parameter, public :: SNAPKIT_INV_SQRT3 = 0.57735026918962576451_wp
  real(wp), parameter, public :: SNAPKIT_ONE_THIRD = 0.33333333333333333333_wp

  !---------------------------------------------------------------------------
  ! Defaults
  !---------------------------------------------------------------------------
  real(wp), parameter, public :: SNAPKIT_DEFAULT_TOLERANCE = 0.1_wp
  real(wp), parameter, public :: SNAPKIT_DEFAULT_ADAPTATION_RATE = 0.01_wp
  real(wp), parameter, public :: SNAPKIT_DEFAULT_BUDGET = 100.0_wp
  real(wp), parameter, public :: SNAPKIT_DEFAULT_MATCH_THRESHOLD = 0.85_wp

  integer, parameter, public :: SNAPKIT_MAX_STREAMS = 16
  integer, parameter, public :: SNAPKIT_MAX_SCRIPTS = 256
  integer, parameter, public :: SNAPKIT_SCRIPT_NAME_MAX = 64
  integer, parameter, public :: SNAPKIT_SCRIPT_ID_MAX = 16
  integer, parameter, public :: SNAPKIT_MAX_PATTERN_DIM = 64
  integer, parameter, public :: SNAPKIT_MAX_CONSTRAINTS = 64
  integer, parameter, public :: SNAPKIT_MAX_DEPENDENCIES = 128
  integer, parameter, public :: SNAPKIT_CONSTRAINT_NAME_MAX = 32
  integer, parameter, public :: SNAPKIT_SNAP_HISTORY_MAX = 4096
  integer, parameter, public :: SNAPKIT_EISENSTEIN_CANDIDATES = 7
  integer, parameter, public :: SNAPKIT_TOPOLOGY_COUNT = 8
  integer, parameter, public :: SNAPKIT_SEVERITY_COUNT = 5

  !---------------------------------------------------------------------------
  ! Topology types — each a different "flavor of randomness"
  !---------------------------------------------------------------------------
  integer, parameter, public :: &
       SNAPKIT_TOPOLOGY_BINARY       = 0, &
       SNAPKIT_TOPOLOGY_TETRAHEDRAL  = 1, &
       SNAPKIT_TOPOLOGY_HEXAGONAL    = 2, &
       SNAPKIT_TOPOLOGY_CUBIC        = 3, &
       SNAPKIT_TOPOLOGY_OCTAHEDRAL   = 4, &
       SNAPKIT_TOPOLOGY_DODECAHEDRAL = 5, &
       SNAPKIT_TOPOLOGY_ICOSAHEDRAL  = 6, &
       SNAPKIT_TOPOLOGY_GRADIENT     = 7

  !---------------------------------------------------------------------------
  ! Severity levels
  !---------------------------------------------------------------------------
  integer, parameter, public :: &
       SNAPKIT_SEVERITY_NONE     = 0, &
       SNAPKIT_SEVERITY_LOW      = 1, &
       SNAPKIT_SEVERITY_MEDIUM   = 2, &
       SNAPKIT_SEVERITY_HIGH     = 3, &
       SNAPKIT_SEVERITY_CRITICAL = 4

  !---------------------------------------------------------------------------
  ! Script status
  !---------------------------------------------------------------------------
  integer, parameter, public :: &
       SNAPKIT_SCRIPT_DRAFT    = 0, &
       SNAPKIT_SCRIPT_ACTIVE   = 1, &
       SNAPKIT_SCRIPT_DEGRADED = 2, &
       SNAPKIT_SCRIPT_ARCHIVED = 3

  !---------------------------------------------------------------------------
  ! Allocation strategy
  !---------------------------------------------------------------------------
  integer, parameter, public :: &
       SNAPKIT_STRATEGY_ACTIONABILITY = 0, &
       SNAPKIT_STRATEGY_REACTIVE      = 1, &
       SNAPKIT_STRATEGY_UNIFORM       = 2

  !---------------------------------------------------------------------------
  ! Error codes
  !---------------------------------------------------------------------------
  integer, parameter, public :: &
       SNAPKIT_OK           =  0, &
       SNAPKIT_ERR_NULL     = -1, &
       SNAPKIT_ERR_SIZE     = -2, &
       SNAPKIT_ERR_STATE    = -3, &
       SNAPKIT_ERR_DIM      = -4, &
       SNAPKIT_ERR_TOPOLOGY = -5, &
       SNAPKIT_ERR_BUDGET   = -6, &
       SNAPKIT_ERR_MATH     = -7

  !---------------------------------------------------------------------------
  ! ADE topology metadata
  !---------------------------------------------------------------------------
  type, public :: snapkit_ade_data_t
     integer          :: type_id
     character(len=8) :: name
     integer          :: rank
     integer          :: dimension
     integer          :: num_roots
     integer          :: coxeter_number
     character(len=16) :: platonic_solid
     character(len=48) :: description
     real(wp)         :: quality_score
  end type snapkit_ade_data_t

  !---------------------------------------------------------------------------
  ! Snap result
  !---------------------------------------------------------------------------
  type, public :: snapkit_snap_result_t
     real(wp) :: original
     real(wp) :: snapped
     real(wp) :: delta
     logical  :: within_tolerance
     real(wp) :: tolerance
     integer  :: topology
  end type snapkit_snap_result_t

  !---------------------------------------------------------------------------
  ! Delta
  !---------------------------------------------------------------------------
  type, public :: snapkit_delta_t
     real(wp)         :: value
     real(wp)         :: expected
     real(wp)         :: magnitude
     real(wp)         :: tolerance
     integer          :: severity
     integer(kind=8)  :: timestamp
     character(len=32) :: stream_id
     real(wp)         :: actionability
     real(wp)         :: urgency
  end type snapkit_delta_t

  !---------------------------------------------------------------------------
  ! Attention allocation
  !---------------------------------------------------------------------------
  type, public :: snapkit_allocation_t
     type(snapkit_delta_t) :: delta
     real(wp)              :: allocated
     integer               :: priority
     character(len=48)     :: reason
  end type snapkit_allocation_t

  !---------------------------------------------------------------------------
  ! Script match
  !---------------------------------------------------------------------------
  type, public :: snapkit_script_match_t
     character(len=SNAPKIT_SCRIPT_ID_MAX) :: script_id
     real(wp) :: confidence
     logical  :: is_match
     real(wp) :: delta_from_template
  end type snapkit_script_match_t

  !---------------------------------------------------------------------------
  ! Consistency report
  !---------------------------------------------------------------------------
  type, public :: snapkit_consistency_report_t
     integer :: num_constraints
     real(wp) :: max_delta
     real(wp) :: mean_delta
     integer  :: h1_analog
     logical  :: delta_detected
     real(wp) :: tolerance
     integer  :: topology
  end type snapkit_consistency_report_t

  !---------------------------------------------------------------------------
  ! Snap history (internal — accessible for statistics)
  !---------------------------------------------------------------------------
  type, public :: snapkit_snap_history_t
     type(snapkit_snap_result_t), allocatable :: results(:)
     integer(kind=8) :: head
     integer(kind=8) :: count
     real(wp) :: sum_delta
     real(wp) :: max_delta
     integer(kind=8) :: snap_cnt
     integer(kind=8) :: delta_cnt
  end type snapkit_snap_history_t

  !---------------------------------------------------------------------------
  ! Snap function
  !---------------------------------------------------------------------------
  type, public :: snapkit_snap_function_t
     real(wp) :: tolerance
     integer  :: topology
     real(wp) :: baseline
     real(wp) :: adaptation_rate
     type(snapkit_snap_history_t) :: history
  end type snapkit_snap_function_t

  !---------------------------------------------------------------------------
  ! Delta stream (internal to detector)
  !---------------------------------------------------------------------------
  type, public :: snapkit_delta_stream_t
     character(len=32) :: stream_id
     type(snapkit_snap_function_t) :: snap
     real(wp) :: actionability
     real(wp) :: urgency
     type(snapkit_delta_t) :: current
     logical  :: has_current
  end type snapkit_delta_stream_t

  !---------------------------------------------------------------------------
  ! Delta detector
  !---------------------------------------------------------------------------
  type, public :: snapkit_delta_detector_t
     type(snapkit_delta_stream_t) :: streams(SNAPKIT_MAX_STREAMS)
     integer  :: num_streams
     integer(kind=8) :: tick
  end type snapkit_delta_detector_t

  !---------------------------------------------------------------------------
  ! Attention budget
  !---------------------------------------------------------------------------
  type, public :: snapkit_attention_budget_t
     real(wp) :: total_budget
     real(wp) :: remaining
     integer  :: strategy
     integer(kind=8) :: exhaustion_count
     integer(kind=8) :: cycle_count
  end type snapkit_attention_budget_t

  !---------------------------------------------------------------------------
  ! Script entry (internal)
  !---------------------------------------------------------------------------
  type, public :: snapkit_script_t
     character(len=SNAPKIT_SCRIPT_ID_MAX) :: id
     character(len=SNAPKIT_SCRIPT_NAME_MAX) :: name
     real(wp) :: trigger(SNAPKIT_MAX_PATTERN_DIM)
     integer  :: trigger_dim
     real(wp) :: response
     real(wp) :: match_threshold
     integer  :: status
     integer(kind=8) :: use_count
     integer(kind=8) :: success_count
     integer(kind=8) :: fail_count
     integer(kind=8) :: last_used
     integer(kind=8) :: created_at
     real(wp) :: confidence
  end type snapkit_script_t

  !---------------------------------------------------------------------------
  ! Script library
  !---------------------------------------------------------------------------
  type, public :: snapkit_script_library_t
     type(snapkit_script_t) :: scripts(SNAPKIT_MAX_SCRIPTS)
     integer  :: num_scripts
     real(wp) :: match_threshold
     integer(kind=8) :: hit_count
     integer(kind=8) :: miss_count
     integer(kind=8) :: tick
  end type snapkit_script_library_t

  !---------------------------------------------------------------------------
  ! Constraint node
  !---------------------------------------------------------------------------
  type, public :: snapkit_constraint_node_t
     character(len=SNAPKIT_CONSTRAINT_NAME_MAX) :: name
     real(wp) :: value
     real(wp) :: expected
     logical  :: has_expected
  end type snapkit_constraint_node_t

  !---------------------------------------------------------------------------
  ! Dependency
  !---------------------------------------------------------------------------
  type, public :: snapkit_dependency_t
     character(len=SNAPKIT_CONSTRAINT_NAME_MAX) :: source
     character(len=SNAPKIT_CONSTRAINT_NAME_MAX) :: target
  end type snapkit_dependency_t

  !---------------------------------------------------------------------------
  ! Constraint sheaf
  !---------------------------------------------------------------------------
  type, public :: snapkit_constraint_sheaf_t
     integer  :: topology
     real(wp) :: tolerance
     type(snapkit_constraint_node_t) :: constraints(SNAPKIT_MAX_CONSTRAINTS)
     integer  :: num_constraints
     type(snapkit_dependency_t) :: dependencies(SNAPKIT_MAX_DEPENDENCIES)
     integer  :: num_dependencies
  end type snapkit_constraint_sheaf_t

  !---------------------------------------------------------------------------
  ! Learning state
  !---------------------------------------------------------------------------
  type, public :: snapkit_learning_state_t
     real(wp) :: delta
     real(wp) :: tolerance
     real(wp) :: holonomy
     real(wp) :: curiosity_rate
     real(wp) :: attention_budget
     integer(kind=8) :: cycle
     logical  :: plateau_detected
     real(wp) :: best_performance
     integer(kind=8) :: plateau_cycles
  end type snapkit_learning_state_t

  !---------------------------------------------------------------------------
  ! Public interfaces (from this module only — sub-module routines are in
  ! their respective modules: snapkit_snap, snapkit_delta, etc.)
  !---------------------------------------------------------------------------
  public :: snapkit_ade_data
  public :: snapkit_recommend_topology
  public :: snapkit_topology_name
  public :: snapkit_severity_name
  public :: snapkit_compute_severity
  public :: snapkit_l2_norm
  public :: snapkit_cosine_similarity

contains

  !===========================================================================
  ! ADE topology data
  !===========================================================================
  function snapkit_ade_data(topology) result(data)
    integer, intent(in) :: topology
    type(snapkit_ade_data_t), pointer :: data
    type(snapkit_ade_data_t), target, save :: table(SNAPKIT_TOPOLOGY_COUNT)
    logical, save :: initialized = .false.

    if (.not. initialized) then
       call init_ade_table(table)
       initialized = .true.
    end if

    if (topology < 0 .or. topology >= SNAPKIT_TOPOLOGY_COUNT) then
       data => null()
    else
       data => table(topology + 1)
    end if
  end function snapkit_ade_data

  !> Internal: initialize ADE table (Fortran 2008 doesn't allow struct constructors in array literals)
  subroutine init_ade_table(table)
    type(snapkit_ade_data_t), intent(out) :: table(:)

    ! Binary (A1)
    table(1)%type_id       = SNAPKIT_TOPOLOGY_BINARY
    table(1)%name          = "A1"
    table(1)%rank          = 1
    table(1)%dimension     = 1
    table(1)%num_roots     = 2
    table(1)%coxeter_number = 2
    table(1)%platonic_solid = "Tetrahedron"
    table(1)%description   = "Binary coin flip"
    table(1)%quality_score = 1.0_wp

    ! Tetrahedral (A3)
    table(2)%type_id       = SNAPKIT_TOPOLOGY_TETRAHEDRAL
    table(2)%name          = "A3"
    table(2)%rank          = 3
    table(2)%dimension     = 3
    table(2)%num_roots     = 12
    table(2)%coxeter_number = 4
    table(2)%platonic_solid = "Tetrahedron"
    table(2)%description   = "4 categories"
    table(2)%quality_score = 2.0_wp

    ! Hexagonal (A2) — Eisenstein lattice
    table(3)%type_id       = SNAPKIT_TOPOLOGY_HEXAGONAL
    table(3)%name          = "A2"
    table(3)%rank          = 2
    table(3)%dimension     = 2
    table(3)%num_roots     = 6
    table(3)%coxeter_number = 3
    table(3)%platonic_solid = ""
    table(3)%description   = "Hexagonal Eisenstein Z[omega]"
    table(3)%quality_score = 2.7_wp

    ! Cubic (Zn)
    table(4)%type_id       = SNAPKIT_TOPOLOGY_CUBIC
    table(4)%name          = "Zn"
    table(4)%rank          = 0
    table(4)%dimension     = 0
    table(4)%num_roots     = 0
    table(4)%coxeter_number = 0
    table(4)%platonic_solid = "Cube"
    table(4)%description   = "Standard uniform grid"
    table(4)%quality_score = 1.5_wp

    ! Octahedral (B3)
    table(5)%type_id       = SNAPKIT_TOPOLOGY_OCTAHEDRAL
    table(5)%name          = "B3"
    table(5)%rank          = 3
    table(5)%dimension     = 3
    table(5)%num_roots     = 18
    table(5)%coxeter_number = 6
    table(5)%platonic_solid = "Octahedron"
    table(5)%description   = "8 directions, pm axes"
    table(5)%quality_score = 2.8_wp

    ! Dodecahedral (H3)
    table(6)%type_id       = SNAPKIT_TOPOLOGY_DODECAHEDRAL
    table(6)%name          = "H3"
    table(6)%rank          = 3
    table(6)%dimension     = 3
    table(6)%num_roots     = 30
    table(6)%coxeter_number = 10
    table(6)%platonic_solid = "Dodecahedron"
    table(6)%description   = "20-category combinatorial"
    table(6)%quality_score = 2.5_wp

    ! Icosahedral (H3)
    table(7)%type_id       = SNAPKIT_TOPOLOGY_ICOSAHEDRAL
    table(7)%name          = "H3"
    table(7)%rank          = 3
    table(7)%dimension     = 3
    table(7)%num_roots     = 30
    table(7)%coxeter_number = 10
    table(7)%platonic_solid = "Icosahedron"
    table(7)%description   = "12-direction golden clusters"
    table(7)%quality_score = 2.9_wp

    ! Gradient (near-continuous)
    table(8)%type_id       = SNAPKIT_TOPOLOGY_GRADIENT
    table(8)%name          = "Inf"
    table(8)%rank          = 0
    table(8)%dimension     = 0
    table(8)%num_roots     = 0
    table(8)%coxeter_number = 0
    table(8)%platonic_solid = ""
    table(8)%description   = "Near-continuous (d100)"
    table(8)%quality_score = 0.5_wp
  end subroutine init_ade_table

  !===========================================================================
  ! Recommend topology
  !===========================================================================
  function snapkit_recommend_topology(num_categories, dimension) result(top)
    integer, intent(in) :: num_categories, dimension
    integer :: top

    if (num_categories == 2) then
       top = SNAPKIT_TOPOLOGY_BINARY
    else if (num_categories == 4 .or. num_categories == 3) then
       top = SNAPKIT_TOPOLOGY_TETRAHEDRAL
    else if (dimension <= 2 .or. num_categories == 6) then
       top = SNAPKIT_TOPOLOGY_HEXAGONAL
    else if (dimension <= 4 .or. num_categories <= 20) then
       top = SNAPKIT_TOPOLOGY_DODECAHEDRAL
    else
       top = SNAPKIT_TOPOLOGY_OCTAHEDRAL
    end if
  end function snapkit_recommend_topology

  !===========================================================================
  ! Topology name
  !===========================================================================
  function snapkit_topology_name(t) result(name)
    integer, intent(in) :: t
    character(len=8) :: name
    type(snapkit_ade_data_t), pointer :: d
    d => snapkit_ade_data(t)
    if (associated(d)) then
       name = d%name
    else
       name = "UNKNOWN"
    end if
  end function snapkit_topology_name

  !===========================================================================
  ! Severity name
  !===========================================================================
  function snapkit_severity_name(s) result(name)
    integer, intent(in) :: s
    character(len=8) :: name
    select case(s)
    case(SNAPKIT_SEVERITY_NONE);     name = "NONE"
    case(SNAPKIT_SEVERITY_LOW);      name = "LOW"
    case(SNAPKIT_SEVERITY_MEDIUM);   name = "MEDIUM"
    case(SNAPKIT_SEVERITY_HIGH);     name = "HIGH"
    case(SNAPKIT_SEVERITY_CRITICAL); name = "CRITICAL"
    case default;                    name = "UNKNOWN"
    end select
  end function snapkit_severity_name

  !===========================================================================
  ! Compute severity
  !===========================================================================
  function snapkit_compute_severity(magnitude, tolerance) result(sev)
    real(wp), intent(in) :: magnitude, tolerance
    integer :: sev
    real(wp) :: ratio

    if (tolerance <= 0.0_wp) then
       sev = SNAPKIT_SEVERITY_CRITICAL
       return
    end if
    ratio = magnitude / tolerance
    if (ratio <= 1.0_wp) then
       sev = SNAPKIT_SEVERITY_NONE
    else if (ratio <= 1.5_wp) then
       sev = SNAPKIT_SEVERITY_LOW
    else if (ratio <= 3.0_wp) then
       sev = SNAPKIT_SEVERITY_MEDIUM
    else if (ratio <= 5.0_wp) then
       sev = SNAPKIT_SEVERITY_HIGH
    else
       sev = SNAPKIT_SEVERITY_CRITICAL
    end if
  end function snapkit_compute_severity

  !===========================================================================
  ! L2 norm
  !===========================================================================
  pure function snapkit_l2_norm(v) result(norm)
    real(wp), intent(in) :: v(:)
    real(wp) :: norm
    norm = sqrt(sum(v * v))
  end function snapkit_l2_norm

  !===========================================================================
  ! Cosine similarity
  !===========================================================================
  pure function snapkit_cosine_similarity(a, b) result(sim)
    real(wp), intent(in) :: a(:), b(:)
    real(wp) :: sim
    real(wp) :: dot, na, nb, norm

    integer :: i
    dot = 0.0_wp
    na  = 0.0_wp
    nb  = 0.0_wp

    do i = 1, min(size(a), size(b))
       dot = dot + a(i) * b(i)
       na  = na  + a(i) * a(i)
       nb  = nb  + b(i) * b(i)
    end do

    norm = sqrt(na) * sqrt(nb)
    if (norm < 1.0e-15_wp) then
       sim = 0.0_wp
    else
       sim = dot / norm
    end if
  end function snapkit_cosine_similarity

end module snapkit

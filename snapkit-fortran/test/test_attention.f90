!> @file test_attention.f90
!! @brief Tests for attention budget allocation.
module test_attention
  use snapkit
  use snapkit_attention
  implicit none
  private
  public :: test_budget_create_free
  public :: test_budget_uniform
  public :: test_budget_exhaust

contains

  !> Test budget create and free.
  function test_budget_create_free() result(pass)
    logical :: pass
    type(snapkit_attention_budget_t), pointer :: ab

    pass = .true.

    ab => snapkit_budget_create(100.0_wp, SNAPKIT_STRATEGY_UNIFORM)
    if (.not. associated(ab)) then
       write(*, '(a)') "  FAIL: budget_create returned null"
       pass = .false.
       return
    end if

    if (abs(ab%total_budget - 100.0_wp) > 1.0e-12_wp) then
       write(*, '(a)') "  FAIL: total_budget mismatch"
       pass = .false.
    end if

    if (ab%strategy /= SNAPKIT_STRATEGY_UNIFORM) then
       write(*, '(a)') "  FAIL: strategy mismatch"
       pass = .false.
    end if

    if (ab%cycle_count /= 0) then
       write(*, '(a)') "  FAIL: cycle_count should be 0"
       pass = .false.
    end if

    call snapkit_budget_free(ab)
    if (associated(ab)) then
       write(*, '(a)') "  FAIL: budget_free didn't nullify"
       pass = .false.
    end if

    if (pass) write(*, '(a)') "  PASS: budget create/free"
  end function test_budget_create_free

  !> Test uniform allocation strategy.
  function test_budget_uniform() result(pass)
    logical :: pass
    type(snapkit_attention_budget_t), pointer :: ab
    type(snapkit_delta_t) :: deltas(4)
    type(snapkit_allocation_t) :: allocs(4)
    integer :: err, n_alloc, i

    pass = .true.

    ! Create 4 deltas, 3 actionable, 1 none
    do i = 1, 4
       deltas(i)%value        = real(i, wp) * 0.2_wp
       deltas(i)%expected     = 0.5_wp
       deltas(i)%magnitude    = abs(deltas(i)%value - 0.5_wp)
       deltas(i)%tolerance    = 0.1_wp
       deltas(i)%actionability = 0.5_wp
       deltas(i)%urgency       = 0.5_wp
       deltas(i)%stream_id    = "test"
       deltas(i)%timestamp    = int(i, kind=8)
    end do
    deltas(1)%severity = SNAPKIT_SEVERITY_NONE  ! not actionable
    deltas(2)%severity = SNAPKIT_SEVERITY_LOW
    deltas(3)%severity = SNAPKIT_SEVERITY_MEDIUM
    deltas(4)%severity = SNAPKIT_SEVERITY_HIGH

    ab => snapkit_budget_create(30.0_wp, SNAPKIT_STRATEGY_UNIFORM)
    err = snapkit_budget_allocate(ab, deltas, allocs, n_alloc)

    if (n_alloc /= 3) then
       write(*, '(a, i2, a)') "  FAIL: expected 3 allocations, got ", n_alloc
       pass = .false.
    end if

    ! Each should get 10.0
    do i = 1, 3
       if (abs(allocs(i)%allocated - 10.0_wp) > 1.0e-12_wp) then
          write(*, '(a, i2, f10.4)') "  FAIL: allocation ", i, " not 10.0"
          pass = .false.
       end if
    end do

    call snapkit_budget_free(ab)
    if (pass) write(*, '(a)') "  PASS: budget uniform"
  end function test_budget_uniform

  !> Test budget exhaustion.
  function test_budget_exhaust() result(pass)
    logical :: pass
    type(snapkit_attention_budget_t), pointer :: ab
    type(snapkit_delta_t) :: deltas(2)
    type(snapkit_allocation_t) :: allocs(2)
    integer :: err, n_alloc
    real(wp) :: rem, util

    pass = .true.

    deltas(1)%value = 0.9_wp;  deltas(2)%value = 0.8_wp
    deltas(1)%expected = 0.5_wp; deltas(2)%expected = 0.5_wp
    deltas(1)%magnitude = 0.4_wp; deltas(2)%magnitude = 0.3_wp
    deltas(1)%tolerance = 0.1_wp; deltas(2)%tolerance = 0.1_wp
    deltas(1)%severity = SNAPKIT_SEVERITY_HIGH
    deltas(2)%severity = SNAPKIT_SEVERITY_HIGH
    deltas(1)%actionability = 0.5_wp; deltas(2)%actionability = 0.5_wp
    deltas(1)%urgency = 0.5_wp; deltas(2)%urgency = 0.5_wp
    deltas(1)%timestamp = 1; deltas(2)%timestamp = 2
    deltas(1)%stream_id = "a"; deltas(2)%stream_id = "b"

    ! Small budget — first delta consumes it all
    ab => snapkit_budget_create(0.5_wp, SNAPKIT_STRATEGY_REACTIVE)
    err = snapkit_budget_allocate(ab, deltas, allocs, n_alloc)

    call snapkit_budget_status(ab, rem, util)
    if (rem <= 0.0_wp .and. util < 0.9_wp) then
       write(*, '(a)') "  FAIL: exhausted budget should have utilization near 1"
       pass = .false.
    end if

    call snapkit_budget_free(ab)
    if (pass) write(*, '(a)') "  PASS: budget exhaustion"
  end function test_budget_exhaust

end module test_attention

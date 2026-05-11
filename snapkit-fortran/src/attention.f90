!> @file attention.f90
!! @brief Attention budget — finite cognition allocation to actionable deltas.
!!
!! The attention budget is the resource constraint on cognition. Not all deltas
!! can be attended to — the budget allocates finite attention units across
!! competing deltas based on strategy (actionability-weighted, reactive, uniform).
!! When the budget is exhausted, remaining deltas go unattended (snapped away).

module snapkit_attention
  use snapkit
  implicit none
  private

  public :: snapkit_budget_create
  public :: snapkit_budget_free
  public :: snapkit_budget_allocate
  public :: snapkit_budget_status

contains

  !> Create an attention budget.
  !!
  !! @param[in] total_budget  Maximum attention units per cycle
  !! @param[in] strategy      Allocation strategy (ACTIONABILITY, REACTIVE, UNIFORM)
  !! @return    New budget, or null on failure
  function snapkit_budget_create(total_budget, strategy) result(ab)
    real(wp), intent(in) :: total_budget
    integer,  intent(in) :: strategy
    type(snapkit_attention_budget_t), pointer :: ab

    allocate(ab)
    ab%total_budget     = total_budget
    ab%remaining        = total_budget
    ab%strategy         = strategy
    ab%exhaustion_count = 0
    ab%cycle_count      = 0
  end function snapkit_budget_create

  !> Free an attention budget.
  subroutine snapkit_budget_free(ab)
    type(snapkit_attention_budget_t), pointer, intent(inout) :: ab
    if (associated(ab)) then
       deallocate(ab)
       ab => null()
    end if
  end subroutine snapkit_budget_free

  !> Allocate attention to a set of deltas.
  !!
  !! Three strategies:
  !! - ACTIONABILITY: weighted by magnitude × actionability × urgency
  !! - REACTIVE: attend to biggest deltas greedily
  !! - UNIFORM: equal attention to all actionable deltas
  !!
  !! @param[inout] ab          Attention budget
  !! @param[in]    deltas      Array of deltas
  !! @param[out]   allocs      Output allocations (same size as deltas)
  !! @param[out]   n_allocated Number of allocations actually made
  !! @return       SNAPKIT_OK if budget not exhausted, SNAPKIT_ERR_BUDGET if exhausted
  function snapkit_budget_allocate(ab, deltas, allocs, n_allocated) result(err)
    type(snapkit_attention_budget_t), intent(inout) :: ab
    type(snapkit_delta_t),  intent(in)  :: deltas(:)
    type(snapkit_allocation_t), intent(out) :: allocs(:)
    integer,                intent(out) :: n_allocated
    integer :: err

    integer  :: i, j, n, priority, target
    real(wp) :: budget_remaining
    real(wp) :: alloc_amount, per_delta
    real(wp), allocatable :: weights(:), sorted_weights(:)
    integer,  allocatable :: indices(:)

    err = SNAPKIT_OK
    ab%cycle_count = ab%cycle_count + 1
    ab%remaining = ab%total_budget
    n_allocated = 0
    n = size(deltas)

    if (n == 0) return

    budget_remaining = ab%total_budget

    select case (ab%strategy)

    case (SNAPKIT_STRATEGY_ACTIONABILITY)
       ! Weight by magnitude × actionability × urgency
       allocate(weights(n), indices(n))
       do i = 1, n
          weights(i) = deltas(i)%magnitude * deltas(i)%actionability * deltas(i)%urgency
          if (deltas(i)%severity == SNAPKIT_SEVERITY_NONE) weights(i) = 0.0_wp
          indices(i) = i
       end do

       ! Sort indices by weight descending (bubble sort)
       do i = 1, n
          do j = i + 1, n
             if (weights(indices(j)) > weights(indices(i))) then
                target = indices(i); indices(i) = indices(j); indices(j) = target
             end if
          end do
       end do

       ! Allocate proportionally
       do priority = 1, n
          i = indices(priority)
          if (weights(i) <= 0.0_wp .or. budget_remaining <= 0.0_wp) then
             allocs(n_allocated + 1)%delta     = deltas(i)
             allocs(n_allocated + 1)%allocated = 0.0_wp
             allocs(n_allocated + 1)%priority  = priority
             allocs(n_allocated + 1)%reason     = "BUDGET_EXHAUSTED"
             n_allocated = n_allocated + 1
             cycle
          end if
          alloc_amount = (weights(i) / sum(weights)) * ab%total_budget
          if (alloc_amount > budget_remaining) alloc_amount = budget_remaining
          budget_remaining = budget_remaining - alloc_amount

          allocs(n_allocated + 1)%delta     = deltas(i)
          allocs(n_allocated + 1)%allocated = alloc_amount
          allocs(n_allocated + 1)%priority  = priority
          if (deltas(i)%actionability > 0.7_wp .and. deltas(i)%urgency > 0.7_wp) then
             allocs(n_allocated + 1)%reason = "high_act_urg"
          else if (deltas(i)%magnitude > 3.0_wp * deltas(i)%tolerance) then
             allocs(n_allocated + 1)%reason = "big_delta"
          else
             allocs(n_allocated + 1)%reason = "weighted"
          end if
          n_allocated = n_allocated + 1
       end do
       deallocate(weights, indices)

    case (SNAPKIT_STRATEGY_REACTIVE)
       ! Sort by magnitude descending, allocate greedily
       allocate(indices(n))
       do i = 1, n
          indices(i) = i
       end do
       do i = 1, n
          do j = i + 1, n
             if (deltas(indices(j))%magnitude > deltas(indices(i))%magnitude) then
                target = indices(i); indices(i) = indices(j); indices(j) = target
             end if
          end do
       end do

       do priority = 1, n
          i = indices(priority)
          if (deltas(i)%severity == SNAPKIT_SEVERITY_NONE .or. budget_remaining <= 0.0_wp) then
             allocs(n_allocated + 1)%delta     = deltas(i)
             allocs(n_allocated + 1)%allocated = 0.0_wp
             allocs(n_allocated + 1)%priority  = priority
             allocs(n_allocated + 1)%reason     = "BUDGET_EXHAUSTED"
             n_allocated = n_allocated + 1
             cycle
          end if
          alloc_amount = min(deltas(i)%magnitude, budget_remaining)
          budget_remaining = budget_remaining - alloc_amount
          allocs(n_allocated + 1)%delta     = deltas(i)
          allocs(n_allocated + 1)%allocated = alloc_amount
          allocs(n_allocated + 1)%priority  = priority
          allocs(n_allocated + 1)%reason     = "REACTIVE"
          n_allocated = n_allocated + 1
       end do
       deallocate(indices)

    case (SNAPKIT_STRATEGY_UNIFORM)
       ! Equal division among actionable deltas
       n_allocated = 0
       do i = 1, n
          if (deltas(i)%severity /= SNAPKIT_SEVERITY_NONE) n_allocated = n_allocated + 1
       end do
       if (n_allocated == 0) return
       per_delta = ab%total_budget / real(n_allocated, wp)
       n_allocated = 0
       do i = 1, n
          if (deltas(i)%severity /= SNAPKIT_SEVERITY_NONE) then
             n_allocated = n_allocated + 1
             allocs(n_allocated)%delta     = deltas(i)
             allocs(n_allocated)%allocated = per_delta
             allocs(n_allocated)%priority  = i
             allocs(n_allocated)%reason     = "UNIFORM"
          end if
       end do
       budget_remaining = 0.0_wp

    case default
       err = SNAPKIT_ERR_STATE
       return
    end select

    ab%remaining = budget_remaining
    if (budget_remaining <= 0.0_wp) ab%exhaustion_count = ab%exhaustion_count + 1
    if (budget_remaining <= 0.0_wp) err = SNAPKIT_ERR_BUDGET
  end function snapkit_budget_allocate

  !> Query budget state.
  !!
  !! @param[in]  ab            Budget
  !! @param[out] remaining     Remaining attention units
  !! @param[out] utilization   Fraction of budget used [0..1]
  subroutine snapkit_budget_status(ab, remaining, utilization)
    type(snapkit_attention_budget_t), intent(in) :: ab
    real(wp), intent(out), optional :: remaining, utilization

    if (present(remaining))   remaining   = ab%remaining
    if (present(utilization)) then
       utilization = merge(1.0_wp - ab%remaining / ab%total_budget, 0.0_wp, &
            ab%total_budget > 0.0_wp)
    end if
  end subroutine snapkit_budget_status

end module snapkit_attention

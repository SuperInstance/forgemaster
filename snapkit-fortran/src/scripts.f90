!> @file scripts.f90
!! @brief Script library — pattern matching and script execution.
!!
!! Scripts are compressed patterns that free cognition: when the snap function
!! recognizes a known pattern, the associated script executes automatically.
!! The script library handles matching, confidence tracking, and lifecycle.
!! Based on the Rubik's cube metaphor: scripts are the vocabulary of known
!! transformations that free the mind to plan ahead.

module snapkit_scripts
  use snapkit
  implicit none
  private

  public :: snapkit_script_library_create
  public :: snapkit_script_library_free
  public :: snapkit_script_library_add
  public :: snapkit_script_library_match
  public :: snapkit_script_library_record_use
  public :: snapkit_script_library_forget
  public :: snapkit_script_library_statistics

contains

  !> Create a script library.
  !!
  !! @param[in] match_threshold  Minimum similarity [0..1] to activate a script
  !! @return    New library
  function snapkit_script_library_create(match_threshold) result(lib)
    real(wp), intent(in) :: match_threshold
    type(snapkit_script_library_t), pointer :: lib

    allocate(lib)
    lib%match_threshold = match_threshold
    lib%num_scripts = 0
    lib%hit_count  = 0
    lib%miss_count = 0
    lib%tick       = 0
  end function snapkit_script_library_create

  !> Free a script library.
  subroutine snapkit_script_library_free(lib)
    type(snapkit_script_library_t), pointer, intent(inout) :: lib
    if (associated(lib)) then
       deallocate(lib)
       lib => null()
    end if
  end subroutine snapkit_script_library_free

  !> Add a script to the library.
  !!
  !! @param[inout] lib         Script library
  !! @param[in]    id          Unique script identifier
  !! @param[in]    name        Human-readable name
  !! @param[in]    trigger     Trigger pattern (real array)
  !! @param[in]    response    Opaque response value
  !! @return       Error code
  function snapkit_script_library_add(lib, id, name, trigger, response) result(err)
    type(snapkit_script_library_t), intent(inout) :: lib
    character(*),        intent(in) :: id, name
    real(wp),            intent(in) :: trigger(:)
    real(wp),            intent(in) :: response
    integer :: err

    integer :: idx, i
    type(snapkit_script_t), pointer :: s

    err = SNAPKIT_OK
    if (lib%num_scripts >= SNAPKIT_MAX_SCRIPTS) then
       err = SNAPKIT_ERR_SIZE
       return
    end if
    if (size(trigger) > SNAPKIT_MAX_PATTERN_DIM) then
       err = SNAPKIT_ERR_DIM
       return
    end if

    idx = lib%num_scripts + 1
    s => lib%scripts(idx)

    s%id   = trim(adjustl(id))
    s%name = trim(adjustl(name))

    ! Copy trigger pattern
    s%trigger_dim = size(trigger)
    do i = 1, s%trigger_dim
       s%trigger(i) = trigger(i)
    end do

    s%response        = response
    s%match_threshold = lib%match_threshold
    s%status          = SNAPKIT_SCRIPT_ACTIVE
    s%use_count       = 0
    s%success_count   = 0
    s%fail_count      = 0
    s%last_used       = 0
    s%created_at      = lib%tick
    s%confidence      = 1.0_wp

    lib%num_scripts = idx
  end function snapkit_script_library_add

  !> Find the best matching script for an observation.
  !!
  !! Uses cosine similarity on the trigger patterns (mapped to [0,1] confidence).
  !! Also computes the Euclidean distance as an alternative delta measure.
  !!
  !! @param[inout] lib         Script library
  !! @param[in]    observation Observed pattern
  !! @param[out]   match       Best match result
  !! @return       SNAPKIT_OK on success, SNAPKIT_ERR_NULL if no match
  function snapkit_script_library_match(lib, observation, match) result(err)
    type(snapkit_script_library_t), intent(inout) :: lib
    real(wp),                  intent(in)  :: observation(:)
    type(snapkit_script_match_t), intent(out) :: match
    integer :: err

    integer  :: i, j, best_idx
    real(wp) :: sim, conf, delta, best_confidence, best_delta

    err = SNAPKIT_OK
    lib%tick = lib%tick + 1

    best_confidence = 0.0_wp
    best_idx = -1
    best_delta = 0.0_wp

    do i = 1, lib%num_scripts
       associate(s => lib%scripts(i))
         if (s%status /= SNAPKIT_SCRIPT_ACTIVE) cycle
         if (s%trigger_dim /= size(observation)) cycle

         ! Cosine similarity
         sim = snapkit_cosine_similarity(observation, s%trigger(:s%trigger_dim))
         conf = (sim + 1.0_wp) / 2.0_wp  ! map [-1,1] → [0,1]

         ! Euclidean distance
         delta = 0.0_wp
         do j = 1, s%trigger_dim
            delta = delta + (observation(j) - s%trigger(j))**2
         end do
         delta = sqrt(delta)

         if (conf > best_confidence) then
            best_confidence = conf
            best_idx = i
            best_delta = delta
         end if
       end associate
    end do

    if (best_idx < 0 .or. best_confidence < lib%match_threshold) then
       lib%miss_count = lib%miss_count + 1
       match%confidence        = best_confidence
       match%is_match          = .false.
       match%delta_from_template = best_delta
       match%script_id = ""
       err = SNAPKIT_ERR_NULL
       return
    end if

    lib%hit_count = lib%hit_count + 1
    match%script_id           = lib%scripts(best_idx)%id
    match%confidence          = best_confidence
    match%is_match            = .true.
    match%delta_from_template = best_delta
  end function snapkit_script_library_match

  !> Record a use of a script (for confidence tracking).
  !!
  !! Tracks success/failure for automatic confidence calibration.
  !! Scripts that fail >50% after 5+ uses are marked DEGRADED.
  !!
  !! @param[inout] lib       Script library
  !! @param[in]    script_id ID of the script used
  !! @param[in]    success   Whether the script succeeded
  subroutine snapkit_script_library_record_use(lib, script_id, success)
    type(snapkit_script_library_t), intent(inout) :: lib
    character(*), intent(in) :: script_id
    logical,      intent(in) :: success

    integer :: i
    real(wp) :: success_rate

    do i = 1, lib%num_scripts
       if (trim(lib%scripts(i)%id) == trim(script_id)) then
          associate(s => lib%scripts(i))
            s%use_count = s%use_count + 1
            s%last_used = lib%tick
            if (success) then
               s%success_count = s%success_count + 1
            else
               s%fail_count = s%fail_count + 1
            end if

            if (s%use_count > 0) then
               success_rate = real(s%success_count, wp) / real(s%use_count, wp)
               s%confidence = success_rate * min(1.0_wp, real(s%success_count, wp) / 5.0_wp)
               if (s%use_count > 5 .and. success_rate < 0.5_wp) then
                  s%status = SNAPKIT_SCRIPT_DEGRADED
               end if
            end if
          end associate
          return
       end if
    end do
  end subroutine snapkit_script_library_record_use

  !> Archive a script (deactivate without deleting).
  !!
  !! @param[inout] lib       Script library
  !! @param[in]    script_id ID of the script to archive
  !! @return       Error code
  function snapkit_script_library_forget(lib, script_id) result(err)
    type(snapkit_script_library_t), intent(inout) :: lib
    character(*), intent(in) :: script_id
    integer :: err

    integer :: i

    err = SNAPKIT_ERR_NULL
    do i = 1, lib%num_scripts
       if (trim(lib%scripts(i)%id) == trim(script_id)) then
          lib%scripts(i)%status = SNAPKIT_SCRIPT_ARCHIVED
          err = SNAPKIT_OK
          return
       end if
    end do
  end function snapkit_script_library_forget

  !> Get library statistics.
  !!
  !! @param[in]  lib       Script library
  !! @param[out] active    Number of active scripts
  !! @param[out] total     Total scripts (all statuses)
  !! @param[out] hit_rate  Hit rate [0..1]
  subroutine snapkit_script_library_statistics(lib, active, total, hit_rate)
    type(snapkit_script_library_t), intent(in) :: lib
    integer,  intent(out), optional :: active, total
    real(wp), intent(out), optional :: hit_rate

    integer :: i, act
    integer(kind=8) :: total_lookups

    if (present(total)) total = lib%num_scripts

    act = 0
    do i = 1, lib%num_scripts
       if (lib%scripts(i)%status == SNAPKIT_SCRIPT_ACTIVE) act = act + 1
    end do
    if (present(active)) active = act

    if (present(hit_rate)) then
       total_lookups = lib%hit_count + lib%miss_count
       hit_rate = merge(real(lib%hit_count, wp) / real(total_lookups, wp), 0.0_wp, &
            total_lookups > 0)
    end if
  end subroutine snapkit_script_library_statistics

end module snapkit_scripts

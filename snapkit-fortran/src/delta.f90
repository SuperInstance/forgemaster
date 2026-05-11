!> @file delta.f90
!! @brief Delta detector — monitors streams for values exceeding snap tolerance.
!!
!! A delta is information that exceeds the snap tolerance — it demands
!! attention. The delta detector manages multiple information streams,
!! each with its own snap function, tolerance, actionability, and urgency.
!! When a stream produces a delta, the allocation engine decides whether
!! (and how much) attention to assign.

module snapkit_delta
  use snapkit
  use snapkit_snap
  implicit none
  private

  public :: snapkit_detector_create
  public :: snapkit_detector_free
  public :: snapkit_detector_add_stream
  public :: snapkit_detector_observe
  public :: snapkit_detector_observe_batch
  public :: snapkit_detector_current_delta
  public :: snapkit_detector_statistics

contains

  !> Find a stream index by ID. Returns -1 if not found.
  pure function find_stream_idx(dd, stream_id) result(idx)
    type(snapkit_delta_detector_t), intent(in) :: dd
    character(*), intent(in) :: stream_id
    integer :: idx
    integer :: i

    idx = -1
    do i = 1, dd%num_streams
       if (trim(dd%streams(i)%stream_id) == trim(stream_id)) then
          idx = i
          return
       end if
    end do
  end function find_stream_idx

  !> Create a delta detector with default state.
  function snapkit_detector_create() result(dd)
    type(snapkit_delta_detector_t), pointer :: dd
    integer :: i

    allocate(dd)
    dd%num_streams = 0
    dd%tick = 0

    do i = 1, SNAPKIT_MAX_STREAMS
       dd%streams(i)%has_current = .false.
       dd%streams(i)%stream_id = ""
       dd%streams(i)%actionability = 1.0_wp
       dd%streams(i)%urgency = 1.0_wp
    end do
  end function snapkit_detector_create

  !> Free a delta detector.
  subroutine snapkit_detector_free(dd)
    type(snapkit_delta_detector_t), pointer, intent(inout) :: dd
    integer :: i

    if (associated(dd)) then
       do i = 1, SNAPKIT_MAX_STREAMS
          if (allocated(dd%streams(i)%snap%history%results)) &
               deallocate(dd%streams(i)%snap%history%results)
       end do
       deallocate(dd)
       dd => null()
    end if
  end subroutine snapkit_detector_free

  !> Add an information stream to monitor.
  !!
  !! Each stream has its own snap function, tolerance, and metadata
  !! about how actionable the stream is and how urgent its deltas are.
  !!
  !! @param[inout] dd             Delta detector
  !! @param[in]    stream_id      Unique stream identifier
  !! @param[in]    tolerance      Snap tolerance for this stream
  !! @param[in]    topology       Snap topology for this stream
  !! @param[in]    actionability  How much thinking can affect this [0..1]
  !! @param[in]    urgency        How urgently this needs attention [0..1]
  !! @return       Error code
  function snapkit_detector_add_stream(dd, stream_id, tolerance, topology, &
       actionability, urgency) result(err)
    type(snapkit_delta_detector_t), intent(inout) :: dd
    character(*), intent(in) :: stream_id
    real(wp),     intent(in) :: tolerance
    integer,      intent(in) :: topology
    real(wp),     intent(in) :: actionability
    real(wp),     intent(in) :: urgency
    integer :: err

    integer :: idx
    integer :: i

    err = SNAPKIT_OK

    if (dd%num_streams >= SNAPKIT_MAX_STREAMS) then
       err = SNAPKIT_ERR_SIZE
       return
    end if

    idx = dd%num_streams + 1

    dd%streams(idx)%stream_id = stream_id

    dd%streams(idx)%snap%tolerance       = tolerance
    dd%streams(idx)%snap%topology        = topology
    dd%streams(idx)%snap%baseline        = 0.0_wp
    dd%streams(idx)%snap%adaptation_rate = SNAPKIT_DEFAULT_ADAPTATION_RATE
    allocate(dd%streams(idx)%snap%history%results(SNAPKIT_SNAP_HISTORY_MAX))
    dd%streams(idx)%snap%history%head      = 0
    dd%streams(idx)%snap%history%count     = 0
    dd%streams(idx)%snap%history%sum_delta = 0.0_wp
    dd%streams(idx)%snap%history%max_delta = 0.0_wp
    dd%streams(idx)%snap%history%snap_cnt  = 0
    dd%streams(idx)%snap%history%delta_cnt = 0
    do i = 1, SNAPKIT_SNAP_HISTORY_MAX
       dd%streams(idx)%snap%history%results(i)%within_tolerance = .false.
       dd%streams(idx)%snap%history%results(i)%delta    = 0.0_wp
       dd%streams(idx)%snap%history%results(i)%original = 0.0_wp
       dd%streams(idx)%snap%history%results(i)%snapped  = 0.0_wp
       dd%streams(idx)%snap%history%results(i)%tolerance = 0.0_wp
       dd%streams(idx)%snap%history%results(i)%topology  = 0
    end do

    dd%streams(idx)%actionability = actionability
    dd%streams(idx)%urgency       = urgency
    dd%streams(idx)%has_current   = .false.

    dd%num_streams = dd%num_streams + 1
  end function snapkit_detector_add_stream

  !> Observe a value on a specific stream.
  !!
  !! Runs the value through the stream's snap function. If the snap delta
  !! exceeds tolerance, a delta is produced with severity proportional to
  !! the exceedance. The stream's current delta is updated.
  !!
  !! @param[inout] dd         Delta detector
  !! @param[in]    stream_id  Stream to observe
  !! @param[in]    value      Observed value
  !! @param[out]   out        Resulting delta (optional)
  !! @return       Error code
  function snapkit_detector_observe(dd, stream_id, value, out) result(err)
    type(snapkit_delta_detector_t), intent(inout) :: dd
    character(*), intent(in)  :: stream_id
    real(wp),     intent(in)  :: value
    type(snapkit_delta_t), intent(out), optional :: out
    integer :: err

    integer :: s_idx
    type(snapkit_snap_result_t) :: snap_res
    type(snapkit_delta_t) :: delta

    err = SNAPKIT_OK
    s_idx = find_stream_idx(dd, stream_id)
    if (s_idx < 0) then
       err = SNAPKIT_ERR_NULL
       return
    end if

    dd%tick = dd%tick + 1

    err = snapkit_snap_apply(dd%streams(s_idx)%snap, value, huge(1.0_wp), snap_res)
    if (err /= SNAPKIT_OK) return

    delta%value     = value
    delta%expected  = dd%streams(s_idx)%snap%baseline
    delta%magnitude = snap_res%delta
    delta%tolerance = dd%streams(s_idx)%snap%tolerance
    delta%severity  = snapkit_compute_severity(snap_res%delta, dd%streams(s_idx)%snap%tolerance)
    delta%timestamp = dd%tick
    delta%stream_id = stream_id
    delta%actionability = dd%streams(s_idx)%actionability
    delta%urgency       = dd%streams(s_idx)%urgency

    dd%streams(s_idx)%current     = delta
    dd%streams(s_idx)%has_current = .true.

    if (present(out)) out = delta
  end function snapkit_detector_observe

  !> Observe values across multiple streams in batch.
  !!
  !! @param[inout] dd         Delta detector
  !! @param[in]    stream_ids Array of stream ID strings
  !! @param[in]    values     Array of values (parallel to stream_ids)
  !! @param[out]   deltas     Output array of deltas (optional)
  !! @return       Error code
  function snapkit_detector_observe_batch(dd, stream_ids, values, deltas) result(err)
    type(snapkit_delta_detector_t), intent(inout) :: dd
    character(*),     intent(in)  :: stream_ids(:)
    real(wp),         intent(in)  :: values(:)
    type(snapkit_delta_t), intent(out), optional :: deltas(:)
    integer :: err
    integer :: i, n

    err = SNAPKIT_OK
    n = min(size(stream_ids), size(values))

    do i = 1, n
       if (present(deltas)) then
          err = snapkit_detector_observe(dd, stream_ids(i), values(i), deltas(i))
       else
          err = snapkit_detector_observe(dd, stream_ids(i), values(i))
       end if
       if (err /= SNAPKIT_OK) exit
    end do
  end function snapkit_detector_observe_batch

  !> Query the most recent delta for a stream.
  !!
  !! @param[in]  dd         Delta detector
  !! @param[in]  stream_id  Stream to query
  !! @param[out] out        Most recent delta
  !! @return       Error code
  function snapkit_detector_current_delta(dd, stream_id, out) result(err)
    type(snapkit_delta_detector_t), intent(in) :: dd
    character(*), intent(in)  :: stream_id
    type(snapkit_delta_t), intent(out) :: out
    integer :: err

    integer :: s_idx

    err = SNAPKIT_OK
    s_idx = find_stream_idx(dd, stream_id)
    if (s_idx < 0 .or. .not. dd%streams(s_idx)%has_current) then
       err = SNAPKIT_ERR_NULL
       return
    end if
    out = dd%streams(s_idx)%current
  end function snapkit_detector_current_delta

  !> Get aggregate statistics across all streams.
  !!
  !! @param[in]  dd             Delta detector
  !! @param[out] num_streams    Number of registered streams
  !! @param[out] total_deltas   Total nontrivial deltas across all streams
  !! @param[out] delta_rate     Overall delta rate [0..1]
  subroutine snapkit_detector_statistics(dd, num_streams, total_deltas, delta_rate)
    type(snapkit_delta_detector_t), intent(in) :: dd
    integer,        intent(out), optional :: num_streams
    integer(kind=8), intent(out), optional :: total_deltas
    real(wp),        intent(out), optional :: delta_rate

    integer :: i
    integer(kind=8) :: total_d, total_obs

    if (present(num_streams)) num_streams = dd%num_streams

    total_d = 0
    total_obs = 0
    do i = 1, dd%num_streams
       total_d   = total_d   + dd%streams(i)%snap%history%delta_cnt
       total_obs = total_obs + dd%streams(i)%snap%history%snap_cnt &
            + dd%streams(i)%snap%history%delta_cnt
    end do

    if (present(total_deltas)) total_deltas = total_d
    if (present(delta_rate)) then
       delta_rate = merge(real(total_d, wp) / real(total_obs, wp), 0.0_wp, total_obs > 0)
    end if
  end subroutine snapkit_detector_statistics

end module snapkit_delta

! FLUX-Tensor-MIDI : flux_midi_room.f90
! PLATO room model — N rooms, each with identity vector and flux estimate
! Room identity: harmonic signature vector that defines the room's "character"
module flux_midi_room
  use flux_midi_flux, only: wp
  implicit none
  private

  type, public :: room_t
    integer :: room_id = 0
    real(wp), allocatable :: identity(:)    ! harmonic signature vector
    real(wp), allocatable :: flux_history(:)
    real(wp) :: resonance = 0.0_wp
    real(wp) :: damping = 1.0_wp
    logical :: active = .true.
  contains
    procedure :: init => room_init
    procedure :: resonate => room_resonate
    procedure :: flux_estimate => room_flux_estimate
  end type room_t
  public :: room_batch_resonate, room_batch_similarity
  public :: room_batch_flux_matrix

contains

  !--------------------------------------------------------------
  ! room_init: initialize room with identity vector
  !--------------------------------------------------------------
  subroutine room_init(this, id, n_dims)
    class(room_t), intent(inout) :: this
    integer, intent(in) :: id, n_dims
    integer :: i
    real(wp) :: pi

    pi = 4.0_wp * atan(1.0_wp)
    this%room_id = id
    allocate(this%identity(n_dims))
    allocate(this%flux_history(0))  ! start empty
    ! Set identity to Zadoff-Chu-like sequence for orthogonality
    do i = 1, n_dims
      this%identity(i) = sin(2.0_wp * pi * real(id, wp) * real(i, wp) / real(n_dims, wp))
    end do
    this%resonance = 0.0_wp
    this%damping = 1.0_wp
    this%active = .true.
  end subroutine room_init

  !--------------------------------------------------------------
  ! room_resonate: update resonance from external flux
  !--------------------------------------------------------------
  pure subroutine room_resonate(this, external_flux)
    class(room_t), intent(inout) :: this
    real(wp), intent(in) :: external_flux

    ! Simple damped harmonic oscillator response
    this%resonance = this%resonance * this%damping + external_flux

    ! Append to history (reallocation — not pure in standard, handled elsewhere)
  end subroutine room_resonate

  !--------------------------------------------------------------
  ! room_flux_estimate: estimate room's own flux from identity
  !--------------------------------------------------------------
  pure real(wp) function room_flux_estimate(this, harmonic_input) result(flux)
    class(room_t), intent(in) :: this
    real(wp), intent(in) :: harmonic_input(:)

    if (size(harmonic_input) == size(this%identity)) then
      flux = dot_product(this%identity, harmonic_input)
    else
      flux = 0.0_wp
    end if
  end function room_flux_estimate

  !--------------------------------------------------------------
  ! room_batch_resonate: update all rooms in batch
  !--------------------------------------------------------------
  pure subroutine room_batch_resonate(rooms, external_fluxes)
    type(room_t), intent(inout) :: rooms(:)
    real(wp), intent(in) :: external_fluxes(:)
    integer :: i

    do concurrent (i = 1:min(size(rooms), size(external_fluxes)))
      if (rooms(i)%active) call rooms(i)%resonate(external_fluxes(i))
    end do
  end subroutine room_batch_resonate

  !--------------------------------------------------------------
  ! room_batch_similarity: pairwise identity similarity
  !   Returns N×N cosine similarity matrix
  !--------------------------------------------------------------
  pure function room_batch_similarity(rooms) result(sim)
    type(room_t), intent(in) :: rooms(:)
    real(wp) :: sim(size(rooms), size(rooms))
    integer :: i, j, n
    real(wp) :: norm_i, norm_j

    n = size(rooms)
    do concurrent (i = 1:n)
      norm_i = sqrt(sum(rooms(i)%identity**2))
      do concurrent (j = 1:n)
        norm_j = sqrt(sum(rooms(j)%identity**2))
        if (norm_i > 0.0_wp .and. norm_j > 0.0_wp) then
          sim(i,j) = dot_product(rooms(i)%identity, rooms(j)%identity) / (norm_i * norm_j)
        else
          sim(i,j) = 0.0_wp
        end if
      end do
    end do
  end function room_batch_similarity

  !--------------------------------------------------------------
  ! room_batch_flux_matrix: N×M flux matrix from rooms × intervals
  !--------------------------------------------------------------
  pure function room_batch_flux_matrix(rooms, harmonic_inputs) result(flux_mat)
    type(room_t), intent(in) :: rooms(:)
    real(wp), intent(in) :: harmonic_inputs(:,:)  ! (n_dims, n_intervals)
    real(wp) :: flux_mat(size(rooms), size(harmonic_inputs,2))
    integer :: i, j, n_rooms, n_intervals

    n_rooms = size(rooms)
    n_intervals = size(harmonic_inputs,2)

    do concurrent (i = 1:n_rooms, j = 1:n_intervals)
      flux_mat(i,j) = rooms(i)%flux_estimate(harmonic_inputs(:,j))
    end do
  end function room_batch_flux_matrix

end module flux_midi_room

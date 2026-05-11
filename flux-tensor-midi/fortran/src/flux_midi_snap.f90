! FLUX-Tensor-MIDI : flux_midi_snap.f90
! Eisenstein snap — vectorized lattice rounding for harmonic quantization
! Projects flux values onto the nearest integer lattice point
module flux_midi_snap
  use flux_midi_flux, only: wp
  implicit none
  private

  public :: eisenstein_snap, eisenstein_lattice_radius
  public :: batch_eisenstein_snap, batch_lattice_radius

contains

  !--------------------------------------------------------------
  ! eisenstein_snap: snap a real value to nearest integer
  !   Eisenstein series G_k(τ) quantization requires projecting
  !   onto the Gaussian integer lattice Z[i].
  !   Here: simple rounding to nearest integer.
  !--------------------------------------------------------------
  pure elemental real(wp) function eisenstein_snap(x) result(snapped)
    real(wp), intent(in) :: x
    snapped = real(nint(x), wp)
  end function eisenstein_snap

  !--------------------------------------------------------------
  ! eisenstein_lattice_radius: distance from x to its snap
  !--------------------------------------------------------------
  pure elemental real(wp) function eisenstein_lattice_radius(x) result(r)
    real(wp), intent(in) :: x
    r = abs(x - eisenstein_snap(x))
  end function eisenstein_lattice_radius

  !--------------------------------------------------------------
  ! batch_eisenstein_snap: vectorized snap over N×M array
  !--------------------------------------------------------------
  pure function batch_eisenstein_snap(values) result(snapped)
    real(wp), intent(in) :: values(:,:)
    real(wp) :: snapped(size(values,1), size(values,2))
    integer :: i, j

    do concurrent (i = 1:size(values,1), j = 1:size(values,2))
      snapped(i,j) = eisenstein_snap(values(i,j))
    end do
  end function batch_eisenstein_snap

  !--------------------------------------------------------------
  ! batch_lattice_radius: lattice distance for each element
  !--------------------------------------------------------------
  pure function batch_lattice_radius(values) result(radii)
    real(wp), intent(in) :: values(:,:)
    real(wp) :: radii(size(values,1), size(values,2))
    integer :: i, j

    do concurrent (i = 1:size(values,1), j = 1:size(values,2))
      radii(i,j) = eisenstein_lattice_radius(values(i,j))
    end do
  end function batch_lattice_radius

end module flux_midi_snap

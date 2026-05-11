! FLUX-Tensor-MIDI : flux_midi_flux.f90
! Tensor-flux operations — batch N rooms × M intervals
! All array ops, no external deps, Fortran 2008
module flux_midi_flux
  use iso_fortran_env, only: wp => real64
  implicit none
  private

  public :: wp
  public :: tensor_flux, flux_normalize, flux_power_spectrum

contains

  !--------------------------------------------------------------
  ! tensor_flux: compute scalar flux from a 3D intensity tensor
  !   tensor(N, M, K) -> flux(N, M)
  !   flux(i,j) = sum_k |tensor(i,j,k) - mean(i,j)|
  !   i = room index, j = time interval, k = frequency/mode bins
  !--------------------------------------------------------------
  pure function tensor_flux(tensor) result(flux)
    real(wp), intent(in) :: tensor(:,:,:)
    real(wp) :: flux(size(tensor,1), size(tensor,2))
    integer :: i, j, n, m, ldim

    n = size(tensor,1)
    m = size(tensor,2)
    ldim = size(tensor,3)

    do concurrent (i = 1:n, j = 1:m)
      flux(i,j) = sum(abs(tensor(i,j,:) - sum(tensor(i,j,:)) / real(ldim, wp)))
    end do
  end function tensor_flux

  !--------------------------------------------------------------
  ! flux_normalize: L2 normalize each flux vector over intervals
  !   flux(N, M) out — where M intervals → row L2 normalization
  !--------------------------------------------------------------
  pure function flux_normalize(flux) result(norm_flux)
    real(wp), intent(in) :: flux(:,:)
    real(wp) :: norm_flux(size(flux,1), size(flux,2))
    integer :: i, n
    real(wp) :: norm

    n = size(flux,1)
    do concurrent (i = 1:n)
      norm = sqrt(sum(flux(i,:)**2))
      if (norm > 0.0_wp) then
        norm_flux(i,:) = flux(i,:) / norm
      else
        norm_flux(i,:) = 0.0_wp
      end if
    end do
  end function flux_normalize

  !--------------------------------------------------------------
  ! flux_power_spectrum: power spectrum of each flux row via DFT
  !   Uses textbook DFT (O(N²)) — no external FFT lib.
  !   flux(N, M) -> power(N, M/2+1)  (positive frequencies)
  !--------------------------------------------------------------
  pure function flux_power_spectrum(flux) result(power)
    real(wp), intent(in) :: flux(:,:)
    real(wp) :: power(size(flux,1), size(flux,2)/2 + 1)
    integer :: i, n, m, k, j
    real(wp) :: pi, arg, re, im

    n = size(flux,1)
    m = size(flux,2)
    pi = 4.0_wp * atan(1.0_wp)

    do i = 1, n
      do k = 1, m/2 + 1
        re = 0.0_wp
        im = 0.0_wp
        do j = 1, m
          arg = 2.0_wp * pi * real((k-1)*(j-1), wp) / real(m, wp)
          re = re + flux(i,j) * cos(arg) / real(m, wp)
          im = im + flux(i,j) * sin(arg) / real(m, wp)
        end do
        power(i,k) = re*re + im*im
      end do
    end do
  end function flux_power_spectrum

end module flux_midi_flux

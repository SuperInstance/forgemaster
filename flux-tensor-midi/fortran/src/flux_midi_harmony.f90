! FLUX-Tensor-MIDI : flux_midi_harmony.f90
! Harmonic analysis — cross-correlation matrices, harmony scores
! All batch array operations
module flux_midi_harmony
  use flux_midi_flux, only: wp
  implicit none
  private

  public :: cross_correlation, batch_harmony_matrix
  public :: harmony_coherence, batch_harmony_coherence

contains

  !--------------------------------------------------------------
  ! cross_correlation: Pearson correlation between two time series
  !--------------------------------------------------------------
  pure real(wp) function cross_correlation(x, y) result(r)
    real(wp), intent(in) :: x(:), y(:)
    integer :: n
    real(wp) :: mx, my, sxx, syy, sxy, denom

    n = min(size(x), size(y))
    if (n < 2) then
      r = 0.0_wp
      return
    end if

    mx = sum(x(:n)) / real(n, wp)
    my = sum(y(:n)) / real(n, wp)

    sxy = sum((x(:n) - mx) * (y(:n) - my))
    sxx = sum((x(:n) - mx)**2)
    syy = sum((y(:n) - my)**2)

    denom = sqrt(sxx * syy)
    if (denom > 0.0_wp) then
      r = sxy / denom
    else
      r = 0.0_wp
    end if
  end function cross_correlation

  !--------------------------------------------------------------
  ! batch_harmony_matrix: N×N cross-correlation matrix
  !   flux(N, M): N rooms × M time intervals
  !   Returns N×N matrix of pairwise Pearson correlations
  !--------------------------------------------------------------
  pure function batch_harmony_matrix(flux) result(harmony)
    real(wp), intent(in) :: flux(:,:)
    real(wp) :: harmony(size(flux,1), size(flux,1))
    integer :: i, j, n

    n = size(flux,1)
    do i = 1, n
      do j = i, n
        harmony(i,j) = cross_correlation(flux(i,:), flux(j,:))
        harmony(j,i) = harmony(i,j)  ! symmetric
      end do
    end do
  end function batch_harmony_matrix

  !--------------------------------------------------------------
  ! harmony_coherence: scalar measure of overall harmonic alignment
  !   Mean absolute correlation above diagonal
  !--------------------------------------------------------------
  pure real(wp) function harmony_coherence(harmony) result(coherence)
    real(wp), intent(in) :: harmony(:,:)
    integer :: i, j, n, cnt

    n = size(harmony,1)
    coherence = 0.0_wp
    cnt = 0
    do i = 1, n
      do j = i+1, n
        coherence = coherence + abs(harmony(i,j))
        cnt = cnt + 1
      end do
    end do
    if (cnt > 0) coherence = coherence / real(cnt, wp)
  end function harmony_coherence

  !--------------------------------------------------------------
  ! batch_harmony_coherence: compute N×M harmony + coherence
  !   Convenience wrapper: flux in, coherence out
  !--------------------------------------------------------------
  pure subroutine batch_harmony_coherence(flux, harmony, coherence)
    real(wp), intent(in) :: flux(:,:)
    real(wp), intent(out) :: harmony(:,:)
    real(wp), intent(out) :: coherence

    harmony = batch_harmony_matrix(flux)
    coherence = harmony_coherence(harmony)
  end subroutine batch_harmony_coherence

end module flux_midi_harmony

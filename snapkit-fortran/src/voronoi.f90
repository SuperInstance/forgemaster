!> Voronoï cell covering radius for the A₂ (Eisenstein) lattice.
!> Computes the maximum distance from any point in a Voronoï cell
!> to the nearest lattice point.
module snapkit_voronoi
    implicit none
    private
    public :: covering_radius, voronoi_cell_vertices, voronoi_cell_area

    real(8), parameter :: SQRT3      = 1.7320508075688772d0
    real(8), parameter :: INV_SQRT3   = 0.5773502691896258d0

contains

    !> Covering radius of the Eisenstein lattice = 1/sqrt(3).
    !> This is the maximum distance from any point in R^2 to the nearest
    !> Eisenstein integer — achieved at the deep holes (hexagon centers).
    pure function covering_radius() result(r)
        real(8) :: r
        r = INV_SQRT3
    end function

    !> Return the 6 vertices of the Voronoï cell centered at origin.
    !> Regular hexagon with circumradius = 1/sqrt(3).
    subroutine voronoi_cell_vertices(vx, vy)
        real(8), intent(out) :: vx(6), vy(6)
        real(8) :: angle
        integer :: i

        do i = 1, 6
            angle = (dble(i) - 1.0d0) * acos(-1.0d0) / 3.0d0
            vx(i) = covering_radius() * cos(angle)
            vy(i) = covering_radius() * sin(angle)
        end do
    end subroutine

    !> Area of the Voronoï cell.
    !> For A₂ lattice with unit spacing, area = sqrt(3)/2.
    pure function voronoi_cell_area() result(a)
        real(8) :: a
        a = SQRT3 / 2.0d0
    end function

end module snapkit_voronoi

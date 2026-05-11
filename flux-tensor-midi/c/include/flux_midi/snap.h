#ifndef FLUX_MIDI_SNAP_H
#define FLUX_MIDI_SNAP_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Eisenstein Rhythmic Snap — classify interval pairs onto the
 * Eisenstein integer lattice.
 *
 * Given two successive intervals (a, b), we project onto the Eisenstein
 * lattice Z[w] where w = e^{2πi/3}. The rounded lattice point gives a
 * canonical rhythmic classification.
 *
 * Shapes (by angle of (a, b)):
 *   BURST    — b >> a, rapid-fire onset
 *   STEADY   — b ≈ a, regular pulse
 *   COLLAPSE — b << a, deceleration to stop
 *   ACCEL    — b > a, gradual speedup
 *   DECEL    — b < a, gradual slowdown
 */

typedef enum {
    SNAP_BURST    = 0,
    SNAP_STEADY   = 1,
    SNAP_COLLAPSE = 2,
    SNAP_ACCEL    = 3,
    SNAP_DECEL    = 4
} SnapShape;

typedef struct {
    int    eisenstein_a;   /* Rounded Eisenstein coordinate a */
    int    eisenstein_b;   /* Rounded Eisenstein coordinate b */
    double norm;           /* Eisenstein norm = a² - ab + b² */
    SnapShape shape;       /* Classified shape */
    double angle_deg;      /* Angle in degrees */
    double ratio;          /* b / a */
} SnapResult;

/* Snap an interval pair to the Eisenstein lattice.
 * base_tempo is the reference interval for normalization. */
void eisenstein_snap(double interval_a, double interval_b,
                     double base_tempo, SnapResult* result);

/* Get human-readable shape name */
const char* snap_shape_name(SnapShape s);

/* Snap a single interval to the nearest subdivision grid point.
 * Returns the snapped interval value. */
double snap_to_grid(double interval, double grid_unit, int* subdivisions);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_SNAP_H */
